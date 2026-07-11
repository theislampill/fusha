#!/usr/bin/env python3
"""Resolve mechanically provable T10 Lane A crosswalk gaps in bounded waves."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import normalize_ar as N  # noqa: E402
from tools.largelexicon_common import (  # noqa: E402
    atomic_promote_shards,
    generation_fingerprint,
    rollback_generation,
    sha256_file,
    sha256_jsonl_rows,
    verify_generation,
    write_json_atomic,
)


QUEUE_SCHEMA = "qamus.crosswalk_gap_queue_row.v1"
ACCEPTED = "canonical_crosswalk_accepted"
METHOD = "unique_exact_ayah_surface_v1"
QUARANTINED_AYAHS = {
    "2:214", "2:274", "3:152", "4:64", "12:37", "19:67", "48:15",
    "92:3", "93:3", "98:1",
}
LOC_RE = re.compile(r"^(\d+):(\d+):(\d+)$")
EXPECTED_BASELINE_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
EXPECTED_CORPUS_SHA256 = "f2e079dcdce01148074a238e3937314cf02222298f91f83ed66dcbb599697ca7"
WAVE_SIZE = 365
SHADOW_SAMPLE_SIZE = 1
QUEUE_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "crosswalk-gap"
QUEUE_PATH = QUEUE_DIR / "crosswalk-gap-queue.jsonl"
QUEUE_MANIFEST_PATH = QUEUE_DIR / "crosswalk-gap-queue.manifest.json"
CROSSWALK_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk"
CROSSWALK_MANIFEST_PATH = (
    ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-crosswalk.manifest.json"
)
DENOMINATOR_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "qword-denominator"
SIDECAR_PATHS = {
    "generation": CROSSWALK_DIR / "GENERATION.json",
    "crosswalk_manifest": CROSSWALK_MANIFEST_PATH,
    "full_table_meta": (
        ROOT / "qamus" / "indexes" / "largelexicon" / "source-clean-fact-tables.meta.json"
    ),
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def sha256_row(row: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(row)).hexdigest()


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def loc_key(loc: str) -> tuple[int, int, int]:
    match = LOC_RE.fullmatch(loc)
    if not match:
        raise ValueError(f"invalid canonical location: {loc!r}")
    return tuple(int(part) for part in match.groups())


def hash_or_none(path: Path) -> str | None:
    return sha256_file(path) if path.exists() else None


def sidecar_hashes() -> dict[str, str | None]:
    return {name: hash_or_none(path) for name, path in SIDECAR_PATHS.items()}


def snapshot_files(paths: Iterable[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def restore_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        temporary = path.with_name(f".{path.name}.restore-{os.getpid()}")
        temporary.write_bytes(content)
        os.replace(temporary, path)


def verify_manifest_inputs(*, baseline: Path, corpus: Path) -> dict[str, Any]:
    manifest = json.loads(QUEUE_MANIFEST_PATH.read_text(encoding="utf-8"))
    baseline_sha = sha256_file(baseline)
    corpus_sha = sha256_file(corpus)
    if baseline_sha != EXPECTED_BASELINE_SHA256 or baseline_sha != manifest.get("baseline_sha256"):
        raise RuntimeError(f"baseline sha256 mismatch: {baseline_sha}")
    if corpus_sha != EXPECTED_CORPUS_SHA256 or corpus_sha != manifest.get("loc_surfaces_sha256"):
        raise RuntimeError(f"corpus index sha256 mismatch: {corpus_sha}")
    queue_sha = sha256_file(QUEUE_PATH)
    if queue_sha != manifest.get("queue_sha256"):
        raise RuntimeError(f"queue sha256 mismatch: {queue_sha}")
    for name, expected in (manifest.get("denominator_files") or {}).items():
        actual = sha256_file(DENOMINATOR_DIR / name)
        if actual != expected:
            raise RuntimeError(f"denominator shard hash mismatch: {name}: {actual} != {expected}")
    for name, expected in (manifest.get("crosswalk_files") or {}).items():
        actual = sha256_file(CROSSWALK_DIR / name)
        if actual != expected:
            raise RuntimeError(f"crosswalk shard hash mismatch: {name}: {actual} != {expected}")
    generation = verify_generation(CROSSWALK_DIR)
    if not generation["ok"]:
        raise RuntimeError(f"crosswalk generation invalid: {generation['errors']}")
    return {
        "baseline_sha256": baseline_sha,
        "corpus_sha256": corpus_sha,
        "queue_sha256": queue_sha,
        "queue_rows": manifest.get("queue_rows"),
        "queue_family_counts": manifest.get("family_counts"),
        "crosswalk_shard_sha256": dict(sorted((manifest.get("crosswalk_files") or {}).items())),
        "crosswalk_generation_fingerprint": generation_fingerprint(CROSSWALK_DIR),
    }


def load_corpus(path: Path) -> tuple[
    dict[str, str], dict[str, list[tuple[str, str]]], dict[str, tuple[str, ...]]
]:
    by_loc: dict[str, str] = {}
    grouped: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for row in read_jsonl(path):
        loc = row.get("loc")
        surface = row.get("surface")
        if not isinstance(loc, str) or not isinstance(surface, str) or loc in by_loc:
            raise ValueError(f"invalid or duplicate corpus row: {row!r}")
        surah, ayah, word = loc_key(loc)
        ayah_ref = f"{surah}:{ayah}"
        by_loc[loc] = surface
        grouped[ayah_ref].append((word, loc, N.norm_strict(surface)))
    by_ayah: dict[str, list[tuple[str, str]]] = {}
    raw_by_ayah: dict[str, tuple[str, ...]] = {}
    for ayah_ref, rows in grouped.items():
        ordered = sorted(rows)
        expected_words = list(range(1, len(ordered) + 1))
        if [word for word, _loc, _norm in ordered] != expected_words:
            raise ValueError(f"non-contiguous corpus locations for {ayah_ref}")
        by_ayah[ayah_ref] = [(loc, norm) for _word, loc, norm in ordered]
        raw_by_ayah[ayah_ref] = tuple(by_loc[loc] for _word, loc, _norm in ordered)
    return by_loc, by_ayah, raw_by_ayah


def verify_dataset_quarantine(raw_corpus_by_ayah: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    dataset_variants: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    entries_path = ROOT / "qamus" / "data" / "current" / "entries.jsonl"
    for entry in read_jsonl(entries_path):
        for usage in entry.get("usage") or []:
            for example in usage.get("examples") or []:
                ref = example.get("ref")
                arabic = example.get("ar")
                if not isinstance(ref, str) or not isinstance(arabic, str):
                    continue
                if ref.count(":") != 1 or not all(part.isdigit() for part in ref.split(":")):
                    continue
                tokens = tuple(token for token in arabic.split() if N.norm_strict(token) or token == "...")
                dataset_variants[ref].add(tokens)

    unmatched = {
        ref for ref, tokens in raw_corpus_by_ayah.items()
        if tokens not in dataset_variants.get(ref, set())
    }
    placeholder_ayahs = {
        ref for ref, tokens in raw_corpus_by_ayah.items() if "..." in tokens
    }
    divergences = unmatched | placeholder_ayahs
    if divergences != QUARANTINED_AYAHS:
        raise RuntimeError(
            "dataset/live corpus divergence set changed: "
            f"actual={sorted(divergences)} expected={sorted(QUARANTINED_AYAHS)}"
        )
    return {
        "dataset_ayah_refs": len(dataset_variants),
        "live_index_ayah_refs": len(raw_corpus_by_ayah),
        "unmatched_ayah_refs": sorted(unmatched),
        "placeholder_ayah_refs": sorted(placeholder_ayahs),
        "quarantined_ayah_refs": sorted(divergences),
    }


def load_denominator() -> tuple[
    dict[str, dict[str, Any]], dict[tuple[str, str], list[str]]
]:
    by_id: dict[str, dict[str, Any]] = {}
    candidates: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in sorted(DENOMINATOR_DIR.glob("*.jsonl")):
        for row in read_jsonl(path):
            row_id = row.get("row_id")
            if not row_id or row_id in by_id:
                raise ValueError(f"missing or duplicate denominator row_id: {row_id!r}")
            by_id[row_id] = row
            key = (row.get("quran_ref"), row.get("visible_surface_norm_strict"))
            if all(isinstance(part, str) and part for part in key):
                candidates[key].append(row_id)
    return by_id, {key: sorted(ids) for key, ids in candidates.items()}


def load_crosswalk() -> tuple[
    dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]
]:
    by_id: dict[str, dict[str, Any]] = {}
    shards: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(CROSSWALK_DIR.glob("*.jsonl")):
        rows = read_jsonl(path)
        shards[path.name] = rows
        for row in rows:
            qword_id = row.get("qword_row_id")
            if not qword_id or qword_id in by_id:
                raise ValueError(f"missing or duplicate crosswalk qword_row_id: {qword_id!r}")
            by_id[qword_id] = row
    return by_id, shards


def apply_accepted_decisions(
    shards: dict[str, list[dict[str, Any]]],
    decisions: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    replacements = {
        decision["qword_row_id"]: decision["row"]
        for decision in decisions if decision["status"] == "accepted"
    }
    found: set[str] = set()
    output: dict[str, list[dict[str, Any]]] = {}
    for name in sorted(shards):
        next_rows: list[dict[str, Any]] = []
        for row in shards[name]:
            qword_id = row.get("qword_row_id")
            if qword_id in replacements:
                next_rows.append(copy.deepcopy(replacements[qword_id]))
                found.add(qword_id)
            else:
                next_rows.append(copy.deepcopy(row))
        output[name] = next_rows
    missing = set(replacements) - found
    if missing:
        raise RuntimeError(f"accepted decisions absent from crosswalk shards: {sorted(missing)[:5]}")
    return output


def shard_payload_sha256(shards: dict[str, list[dict[str, Any]]]) -> str:
    digest = hashlib.sha256()
    for name in sorted(shards):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_jsonl_rows(shards[name]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_crosswalk_manifest(
    *, wave: int, promoted_at: str, shards: dict[str, list[dict[str, Any]]],
    accepted_count: int, decision_sha256: str,
) -> dict[str, Any]:
    manifest = json.loads(CROSSWALK_MANIFEST_PATH.read_text(encoding="utf-8"))
    existing = {Path(row["path"]).name: row for row in manifest.get("shards") or []}
    if set(existing) != set(shards):
        raise RuntimeError("crosswalk manifest/shard name set mismatch")
    status_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    new_shards: list[dict[str, Any]] = []
    for name in sorted(shards):
        rows = shards[name]
        status_counts.update(str(row.get("status")) for row in rows)
        resolution_counts.update(
            str(row.get("resolution_method")) for row in rows
            if row.get("resolution_method")
        )
        item = copy.deepcopy(existing[name])
        item.update({
            "row_count": len(rows),
            "sha256": sha256_jsonl_rows(rows),
            "first_row_id": rows[0].get("row_id") if rows else None,
            "last_row_id": rows[-1].get("row_id") if rows else None,
        })
        new_shards.append(item)
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()
    manifest.update({
        "generated_at": promoted_at,
        "generated_by": "tools/resolve_gap_lane_a.py",
        "source_head": head,
        "source_branch": branch,
        "status": "active",
        "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
        "row_count": sum(len(rows) for rows in shards.values()),
        "shard_count": len(shards),
        "status_counts": dict(sorted(status_counts.items())),
        "shards": new_shards,
        "lane_a_promotion": {
            "wave": wave,
            "accepted_rows": accepted_count,
            "decision_sha256": decision_sha256,
            "resolution_method": METHOD,
            "resolution_wbw_lookup_sha256": EXPECTED_CORPUS_SHA256,
            "promoted_at": promoted_at,
            "mechanical_crosswalk_only": True,
            "resolution_method_counts": dict(sorted(resolution_counts.items())),
        },
    })
    return manifest


def update_full_table_meta(crosswalk_manifest: dict[str, Any]) -> None:
    path = SIDECAR_PATHS["full_table_meta"]
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["generated_at"] = crosswalk_manifest["generated_at"]
    meta["generated_by"] = "tools/resolve_gap_lane_a.py"
    freshness = meta.setdefault("freshness", {})
    freshness.update({
        "generated_at": crosswalk_manifest["generated_at"],
        "generated_by": "tools/resolve_gap_lane_a.py",
        "source_head": crosswalk_manifest["source_head"],
        "source_branch": crosswalk_manifest["source_branch"],
        "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
        "status": "active",
    })
    meta["qword_crosswalk_manifest"] = crosswalk_manifest
    write_json_atomic(path, meta)


def prior_processed_locations(wave: int) -> set[str]:
    processed: set[str] = set()
    for earlier in range(1, wave):
        path = QUEUE_DIR / f"lane-a-wave-{earlier:02d}.report.json"
        if not path.exists():
            raise RuntimeError(f"wave {wave:02d} requires finalized prior report: {path}")
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("state") != "finalized":
            raise RuntimeError(f"prior report is not finalized: {path}")
        processed.update(row["canonical_location"] for row in report.get("decisions") or [])
    return processed


def build_wave_plan(
    *, wave: int, baseline: Path, corpus: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = verify_manifest_inputs(baseline=baseline, corpus=corpus)
    queue = read_jsonl(QUEUE_PATH)
    if len(queue) != inputs["queue_rows"]:
        raise RuntimeError(f"queue row_count mismatch: {len(queue)} != {inputs['queue_rows']}")
    corpus_by_loc, corpus_by_ayah, raw_by_ayah = load_corpus(corpus)
    dataset_proof = verify_dataset_quarantine(raw_by_ayah)
    denominator_by_id, candidates = load_denominator()
    crosswalk_by_id, shards = load_crosswalk()

    quarantined_rows = sorted(
        (row["canonical_location"] for row in queue
         if ":".join(row["canonical_location"].split(":")[:2]) in QUARANTINED_AYAHS),
        key=loc_key,
    )
    lane_a_rows = [
        row for row in queue
        if row.get("primary_resolution_family") == "unique_qword_candidate"
        and row.get("ayah_surface_unique") is True
    ]
    processed = prior_processed_locations(wave)
    eligible = sorted(
        (row for row in lane_a_rows
         if ":".join(row["canonical_location"].split(":")[:2]) not in QUARANTINED_AYAHS
         and row["canonical_location"] not in processed),
        key=lambda row: loc_key(row["canonical_location"]),
    )
    selected = eligible[:WAVE_SIZE]
    if len(selected) != WAVE_SIZE:
        raise RuntimeError(f"wave {wave:02d} expected {WAVE_SIZE} rows, found {len(selected)}")

    decisions = evaluate_rows(
        selected,
        denominator_by_id=denominator_by_id,
        crosswalk_by_id=crosswalk_by_id,
        corpus_by_loc=corpus_by_loc,
        corpus_by_ayah=corpus_by_ayah,
        candidates_by_ayah_surface=candidates,
        corpus_sha256=inputs["corpus_sha256"],
    )
    accepted_count = sum(row["status"] == "accepted" for row in decisions)
    skipped_reasons = Counter(
        row["reason"] for row in decisions if row["status"] == "skipped"
    )
    report_decisions = [
        {key: decision.get(key) for key in (
            "canonical_location", "status", "reason", "qword_row_id"
        ) if decision.get(key) is not None}
        for decision in decisions
    ]
    report = {
        "schema": "qamus/lane-a-wave-report@1",
        "state": "dry_run",
        "wave": wave,
        "wave_size": WAVE_SIZE,
        "promotion_timestamp": now_iso(),
        "resolution_method": METHOD,
        "inputs": inputs,
        "dataset_corpus_proof": dataset_proof,
        "quarantined_divergent_ayah_refs": {
            "ayah_refs": sorted(QUARANTINED_AYAHS),
            "queue_rows": quarantined_rows,
            "queue_row_count": len(quarantined_rows),
            "lane_a_rows": sorted(
                (row["canonical_location"] for row in lane_a_rows
                 if ":".join(row["canonical_location"].split(":")[:2]) in QUARANTINED_AYAHS),
                key=loc_key,
            ),
        },
        "counts": {
            "selected": len(selected),
            "accepted": accepted_count,
            "skipped": len(selected) - accepted_count,
            "skipped_reasons": dict(sorted(skipped_reasons.items())),
            "queue_before": len(queue),
            "queue_expected_after": len(queue) - accepted_count,
        },
        "sidecar_sha256": {"before": sidecar_hashes(), "after": None},
        "decisions": report_decisions,
        "decision_sha256": hashlib.sha256(canonical_json_bytes(report_decisions)).hexdigest(),
    }
    return report, {
        "decisions": decisions,
        "shards": shards,
    }


def write_dry_run(*, wave: int, baseline: Path, corpus: Path) -> dict[str, Any]:
    report, _runtime = build_wave_plan(wave=wave, baseline=baseline, corpus=corpus)
    report_path = QUEUE_DIR / f"lane-a-wave-{wave:02d}.report.json"
    write_json_atomic(report_path, report)
    return report


def run_materialized_validator() -> None:
    command = [sys.executable, str(ROOT / "tools" / "validate_largelexicon_qword_crosswalk.py")]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        raise RuntimeError(
            "crosswalk validator rejected promoted generation:\n"
            + (run.stdout or "")[-4000:] + (run.stderr or "")[-4000:]
        )


def shadow_counts(baseline: Path) -> dict[str, Any]:
    from tools import compile_canonical_hover_whitelist_packet as compile_mod
    from tools import run_shadow_compile as shadow

    live_rows = shadow.read_jsonl(str(baseline))
    live_by_loc: dict[str, dict[str, Any]] = {}
    for row in live_rows:
        loc = compile_mod.canonical_public_loc(row)
        if loc:
            live_by_loc.setdefault(loc, row)
    rows, shared, pending = shadow.construct_input_rows(
        str(ROOT), live_by_loc, compile_mod.public_content,
        compile_mod.canonical_public_loc,
    )
    with tempfile.TemporaryDirectory(prefix="lane-a-shadow-") as td:
        compile_report, summary, sha1, sha2, paths = shadow.run_pipeline(
            str(ROOT), rows, str(baseline), td, SHADOW_SAMPLE_SIZE,
        )
        rowdiff = shadow.read_jsonl(str(Path(td) / "g8-rowdiff.jsonl"))
    if sha1 != sha2:
        raise RuntimeError("shadow compile is not byte-reproducible")
    classifications = {
        name: details["count"] for name, details in summary["classifications"].items()
    }
    return {
        "binding_count": compile_report.get("input_bindings"),
        "packet_sha256": sha1,
        "counts": classifications,
        "build_conflicts": paths["build_conflicts"],
        "shared_live_parity": shared,
        "pending_placeholder": pending,
        "classification_by_loc": {
            row["canonical_wbw_loc"]: row["classification"] for row in rowdiff
        },
    }


def t5_cardinalities() -> dict[str, int]:
    from tools.build_canonical_hover_payload_table import build
    from tools.compile_canonical_hover_whitelist_packet import compile_packet

    rows: list[dict[str, Any]] = []
    for path in sorted(CROSSWALK_DIR.glob("*.jsonl")):
        for source in read_jsonl(path):
            if source.get("status") != ACCEPTED:
                continue
            surface = source["visible_surface_norm_strict"]
            dependency_blob = json.dumps(
                source.get("source_dependencies") or [], ensure_ascii=False,
                sort_keys=True, separators=(",", ":"),
            )
            dependencies = [{
                "id": source["row_id"],
                "sha256": hashlib.sha256(dependency_blob.encode("utf-8")).hexdigest(),
            }]
            rows.append({
                "schema": "qamus.canonical_hover_compiler_input.v1",
                "source_key": "qamus",
                "source_row_id": source["row_id"],
                "source_artifact_sha256": source["resolution_wbw_lookup_sha256"],
                "source_dependencies": dependencies,
                "surface_norm": surface,
                "root": None,
                "pos": "unknown",
                "pattern": None,
                "lemma_status": "missing",
                "sarf_certification": "missing",
                "nahw_certification": "missing",
                "public_payload": {
                    "src": "qamus", "kind": "authored", "lang": "en",
                    "token_contribution_gloss": "dry-run carrier preview",
                    "contextual_phrase_gloss": None,
                    "morphline": "STEM",
                    "segments": [{
                        "role": "STEM", "surface": surface,
                        "qg_class": "unknown", "gloss": "dry-run",
                    }],
                    "learner_explanation": "dry-run carrier preview",
                },
                "canonical_quran_loc": source["canonical_quran_loc"],
                "canonical_wbw_loc": source["canonical_wbw_loc"],
                "entry_id": source["entry_id"],
                "card_id": source["card_id"],
                "qword_row_id": source["qword_row_id"],
                "visible_surface": source["visible_surface"],
                "source_dependency_sha256": hashlib.sha256(json.dumps(
                    dependencies, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")).hexdigest(),
            })
    payloads, bindings, repairs, conflicts, _report = build(rows)
    whitelist, no_ops, compile_conflicts, _compile_report = compile_packet(
        payloads, bindings, [], [],
    )
    if conflicts or compile_conflicts:
        raise RuntimeError(
            f"T5 cardinality build produced conflicts: {len(conflicts)} + {len(compile_conflicts)}"
        )
    return {
        "input_rows": len(rows),
        "bindings": len(bindings),
        "whitelist": len(whitelist) + len(no_ops),
    }


def rebuild_queue(*, baseline: Path, corpus: Path, expected_rows: int) -> dict[str, Any]:
    from tools.build_crosswalk_gap_queue import build_queue, write_outputs

    with tempfile.TemporaryDirectory(prefix="lane-a-queue-") as td:
        manifest, queue = build_queue(
            str(ROOT), str(baseline), loc_surfaces_path=str(corpus),
        )
        if len(queue) != expected_rows:
            raise RuntimeError(f"queue rebuild mismatch: {len(queue)} != {expected_rows}")
        qpath, mpath, final_manifest = write_outputs(td, manifest, queue)
        os.replace(qpath, QUEUE_PATH)
        os.replace(mpath, QUEUE_MANIFEST_PATH)
    if sha256_file(QUEUE_PATH) != final_manifest["queue_sha256"]:
        raise RuntimeError("installed queue hash does not match rebuilt manifest")
    return final_manifest


def promote_wave(*, wave: int, baseline: Path, corpus: Path) -> dict[str, Any]:
    report_path = QUEUE_DIR / f"lane-a-wave-{wave:02d}.report.json"
    if not report_path.exists():
        raise RuntimeError(f"dry-run report is required before promotion: {report_path}")
    dry_report = json.loads(report_path.read_text(encoding="utf-8"))
    if dry_report.get("state") != "dry_run" or dry_report.get("wave") != wave:
        raise RuntimeError("wave report is not the matching dry-run state")

    current_report, runtime = build_wave_plan(wave=wave, baseline=baseline, corpus=corpus)
    for field in ("decision_sha256", "counts"):
        if current_report[field] != dry_report[field]:
            raise RuntimeError(f"dry-run drift in {field}")
    if sidecar_hashes() != dry_report["sidecar_sha256"]["before"]:
        raise RuntimeError("generated sidecar bytes changed after dry run")
    if current_report["inputs"] != dry_report["inputs"]:
        raise RuntimeError("wave inputs changed after dry run")

    decisions = runtime["decisions"]
    accepted = [row for row in decisions if row["status"] == "accepted"]
    if not accepted:
        raise RuntimeError("wave has zero accepted rows; refusing empty promotion")
    shards = runtime["shards"]
    promoted_shards = apply_accepted_decisions(shards, accepted)
    reverse_shards = apply_accepted_decisions(shards, reversed(accepted))
    promoted_digest = shard_payload_sha256(promoted_shards)
    if promoted_digest != shard_payload_sha256(reverse_shards):
        raise RuntimeError("promoted shard bytes depend on decision input ordering")

    promoted_at = dry_report["promotion_timestamp"]
    manifest = build_crosswalk_manifest(
        wave=wave,
        promoted_at=promoted_at,
        shards=promoted_shards,
        accepted_count=len(accepted),
        decision_sha256=dry_report["decision_sha256"],
    )
    before_t5 = t5_cardinalities()
    before_shadow = shadow_counts(baseline)
    snapshots = snapshot_files([
        *SIDECAR_PATHS.values(), QUEUE_PATH, QUEUE_MANIFEST_PATH,
    ])
    promoted = False
    try:
        def install_sidecars(_generation: dict[str, Any]) -> None:
            update_full_table_meta(manifest)
            write_json_atomic(CROSSWALK_MANIFEST_PATH, manifest)

        atomic_promote_shards(
            CROSSWALK_DIR,
            promoted_shards,
            writer_id="tools/resolve_gap_lane_a.py",
            promoted_at=promoted_at,
            after_promote=install_sidecars,
            expected_current_fingerprint=dry_report["inputs"]["crosswalk_generation_fingerprint"],
        )
        promoted = True
        run_materialized_validator()
        after_shadow = shadow_counts(baseline)
        accepted_locs = {row["canonical_location"] for row in accepted}
        bad_locs = sorted(
            loc for loc in accepted_locs
            if after_shadow["classification_by_loc"].get(loc) != "no_op"
        )
        if bad_locs:
            raise RuntimeError(f"promoted locations are not all shadow no_op: {bad_locs[:10]}")
        for forbidden in ("modify", "conflict", "blocked"):
            if after_shadow["counts"].get(forbidden, 0):
                raise RuntimeError(
                    f"shadow stop condition: {forbidden}={after_shadow['counts'][forbidden]}"
                )
        if not build_conflicts_reconciled(
            before_shadow["build_conflicts"], after_shadow["build_conflicts"]
        ):
            raise RuntimeError(
                "shadow build-conflict count changed: "
                f"{before_shadow['build_conflicts']} -> {after_shadow['build_conflicts']}"
            )
        expected_noop = before_shadow["counts"]["no_op"] + len(accepted)
        if after_shadow["counts"]["no_op"] != expected_noop:
            raise RuntimeError(
                "shadow no_op reconciliation failed: "
                f"{after_shadow['counts']['no_op']} != {expected_noop}"
            )

        queue_manifest = rebuild_queue(
            baseline=baseline,
            corpus=corpus,
            expected_rows=dry_report["counts"]["queue_expected_after"],
        )
        if dry_report["counts"]["queue_before"] - queue_manifest["queue_rows"] != len(accepted):
            raise RuntimeError("queue accepted-count reconciliation failed")
        after_t5 = t5_cardinalities()
        if after_t5["input_rows"] != before_t5["input_rows"] + len(accepted):
            raise RuntimeError("T5 input-row arithmetic failed")
        if after_t5["bindings"] != before_t5["bindings"] + len(accepted):
            raise RuntimeError("T5 binding arithmetic failed")

        final_report = copy.deepcopy(dry_report)
        final_report.update({
            "state": "promoted_pending_harness",
            "promoted_shard_payload_sha256": promoted_digest,
            "sidecar_sha256": {
                "before": dry_report["sidecar_sha256"]["before"],
                "after": sidecar_hashes(),
            },
            "crosswalk_shard_sha256": {
                "before": dry_report["inputs"]["crosswalk_shard_sha256"],
                "after": dict(sorted(queue_manifest["crosswalk_files"].items())),
            },
            "shadow": {
                "before": {key: value for key, value in before_shadow.items()
                           if key != "classification_by_loc"},
                "after": {key: value for key, value in after_shadow.items()
                          if key != "classification_by_loc"},
            },
            "queue_after": {
                "rows": queue_manifest["queue_rows"],
                "family_counts": queue_manifest["family_counts"],
                "sha256": queue_manifest["queue_sha256"],
            },
            "harness_cardinalities": {
                "before": before_t5,
                "after": after_t5,
                "arithmetic": {
                    "accepted": len(accepted),
                    "input_rows_delta": after_t5["input_rows"] - before_t5["input_rows"],
                    "bindings_delta": after_t5["bindings"] - before_t5["bindings"],
                    "whitelist_delta": after_t5["whitelist"] - before_t5["whitelist"],
                },
            },
        })
        write_json_atomic(report_path, final_report)
        return final_report
    except BaseException:
        if promoted:
            rollback_generation(
                CROSSWALK_DIR,
                writer_id="tools/resolve_gap_lane_a.py --rollback",
                after_rollback=lambda: restore_files({
                    path: content for path, content in snapshots.items()
                    if path in SIDECAR_PATHS.values()
                }),
            )
        restore_files({
            path: content for path, content in snapshots.items()
            if path in (QUEUE_PATH, QUEUE_MANIFEST_PATH)
        })
        raise


def expected_cardinalities(
    input_rows: int,
    whitelist_rows: int,
    accepted_rows: int,
    new_payload_rows: int,
) -> tuple[int, int]:
    return input_rows + accepted_rows, whitelist_rows + new_payload_rows


def build_conflicts_reconciled(before: int, after: int) -> bool:
    return after == before


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    run = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        errors="replace",
    )
    if run.returncode != 0:
        raise RuntimeError(
            f"command failed ({run.returncode}): {' '.join(command)}\n"
            + (run.stdout or "")[-6000:] + (run.stderr or "")[-6000:]
        )
    return run


def run_artifact_classifier_readonly() -> None:
    taxonomy = ROOT / "qamus" / "reports" / "artifact-taxonomy.md"
    snapshot = snapshot_files([taxonomy])
    try:
        run_checked([sys.executable, str(ROOT / "tools" / "classify_artifacts.py")])
    finally:
        restore_files(snapshot)
    if taxonomy.read_bytes() != snapshot[taxonomy]:
        raise RuntimeError("artifact classifier taxonomy restoration failed")


def finalize_wave(*, wave: int) -> dict[str, Any]:
    report_path = QUEUE_DIR / f"lane-a-wave-{wave:02d}.report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("state") not in {"promoted_pending_harness", "finalized"}:
        raise RuntimeError("wave report is not promotable/finalized verification state")
    if sidecar_hashes() != report["sidecar_sha256"]["after"]:
        raise RuntimeError("generated sidecars changed after promotion")
    queue_manifest = json.loads(QUEUE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if sha256_file(QUEUE_PATH) != report["queue_after"]["sha256"]:
        raise RuntimeError("queue bytes changed after promotion")
    if queue_manifest.get("crosswalk_files") != report["crosswalk_shard_sha256"]["after"]:
        raise RuntimeError("queue manifest crosswalk hashes changed after promotion")
    run_materialized_validator()

    self_test_run = run_checked([
        sys.executable, str(ROOT / "tools" / "resolve_gap_lane_a.py"), "--self-test",
    ])
    harness = run_checked([
        sys.executable, str(ROOT / "tools" / "check_regressions.py"),
    ])
    ok_count = sum(line.startswith("ok   ") for line in harness.stdout.splitlines())
    if ok_count != 1066 or "ALL REGRESSION CHECKS PASS" not in harness.stdout:
        raise RuntimeError(
            f"unexpected harness success shape: ok_count={ok_count}, final marker missing="
            f"{'ALL REGRESSION CHECKS PASS' not in harness.stdout}"
        )

    before_report = report_path.read_bytes()
    try:
        report["state"] = "finalized"
        report["verification"] = {
            "resolver_self_test": {
                "command": "python tools/resolve_gap_lane_a.py --self-test",
                "result": "pass",
                "final_marker": "LANE A RESOLVER SELF-TEST PASS",
            },
            "full_harness": {
                "command": "python tools/check_regressions.py",
                "result": "pass",
                "ok_count": ok_count,
                "failure_count": 0,
                "final_marker": "ALL REGRESSION CHECKS PASS",
            },
            "materialized_crosswalk_validator": "pass",
            "artifact_ergonomics": "pass",
            "artifact_classifier_readonly": "pass",
            "diff_check": "pass",
        }
        write_json_atomic(report_path, report)
        run_checked([sys.executable, str(ROOT / "tools" / "check_artifact_ergonomics.py")])
        run_artifact_classifier_readonly()
        run_checked(["git", "diff", "--check"])
        return report
    except BaseException:
        temporary = report_path.with_name(f".{report_path.name}.restore-{os.getpid()}")
        temporary.write_bytes(before_report)
        os.replace(temporary, report_path)
        raise


def evaluate_candidate(
    queue_row: dict[str, Any],
    *,
    denominator_by_id: dict[str, dict[str, Any]],
    crosswalk_by_id: dict[str, dict[str, Any]],
    corpus_by_loc: dict[str, str],
    corpus_by_ayah: dict[str, list[tuple[str, str]]],
    candidates_by_ayah_surface: dict[tuple[str, str], list[str]],
    corpus_sha256: str,
) -> dict[str, Any]:
    """Return one deterministic accepted/skipped decision."""
    loc = queue_row.get("canonical_location")

    def skipped(reason: str) -> dict[str, Any]:
        return {"canonical_location": loc, "status": "skipped", "reason": reason}

    match = LOC_RE.fullmatch(str(loc or ""))
    if not match:
        return skipped("invalid_location")
    surah, ayah, word = (int(part) for part in match.groups())
    ayah_ref = f"{surah}:{ayah}"
    if ayah_ref in QUARANTINED_AYAHS:
        return skipped("quarantined_divergent_ayah_ref")

    if queue_row.get("schema") != QUEUE_SCHEMA:
        return skipped("queue_schema_mismatch")
    if queue_row.get("primary_resolution_family") != "unique_qword_candidate":
        return skipped("not_lane_a_family")
    if queue_row.get("morphline_state") != "present":
        return skipped("live_payload_not_compilable")

    ayah_rows = corpus_by_ayah.get(ayah_ref) or []
    if word < 1 or word > len(ayah_rows) or loc not in corpus_by_loc:
        return skipped("invalid_location")
    live_norm = (queue_row.get("source_normalization") or {}).get("norm_strict")
    corpus_surface = corpus_by_loc[loc]
    corpus_norm = N.norm_strict(corpus_surface)
    if not live_norm or corpus_norm != live_norm:
        return skipped("surface_mismatch_at_loc")

    same_surface_locs = [row_loc for row_loc, norm in ayah_rows if norm == live_norm]
    if same_surface_locs != [loc]:
        return skipped("ayah_surface_not_unique")

    carriers = queue_row.get("full_carrier_candidates") or []
    if len(carriers) != 1:
        return skipped("carrier_incomplete")
    carrier = carriers[0]
    carrier_fields = ("entry_id", "card_id", "qword_row_id", "row_id")
    if any(not carrier.get(field) for field in carrier_fields):
        return skipped("carrier_incomplete")
    qword_id = carrier["qword_row_id"]
    if carrier["row_id"] != qword_id:
        return skipped("carrier_incomplete")

    denominator = denominator_by_id.get(qword_id)
    if not denominator:
        return skipped("candidate_missing_at_runtime")
    for field in ("entry_id", "card_id"):
        if denominator.get(field) != carrier.get(field):
            return skipped("carrier_mismatch_at_runtime")
    if denominator.get("visible_surface_norm_strict") != corpus_norm:
        return skipped("surface_mismatch_at_loc")
    dependency_hash = (queue_row.get("dependency_hashes") or {}).get(qword_id)
    if not dependency_hash or dependency_hash != denominator.get("card_text_sha256"):
        return skipped("dependency_hash_mismatch")

    runtime_candidates = candidates_by_ayah_surface.get((ayah_ref, corpus_norm)) or []
    if runtime_candidates != [qword_id]:
        return skipped("competing_candidate")

    crosswalk = crosswalk_by_id.get(qword_id)
    if not crosswalk:
        return skipped("crosswalk_row_missing")
    required_crosswalk_fields = (
        "row_id", "qword_row_id", "entry_id", "card_id", "quran_ref",
        "visible_surface", "visible_surface_norm_strict", "source_dependencies",
        "public_boundary", "resolution_normalizer", "resolution_source",
    )
    if any(crosswalk.get(field) in (None, "", []) for field in required_crosswalk_fields):
        return skipped("accepted_shape_not_derivable")
    if crosswalk.get("quran_ref") != ayah_ref:
        return skipped("carrier_mismatch_at_runtime")

    accepted = copy.deepcopy(crosswalk)
    accepted.update({
        "canonical_quran_loc": loc,
        "canonical_wbw_loc": loc,
        "match_status": "resolved_arabic_surface_match",
        "status": ACCEPTED,
        "packet_class": None,
        "terminal_gate_code": None,
        "next_action": None,
        "transclusion_route": "entry_card_qword_to_canonical_crosswalk_accepted",
        "resolution_method": METHOD,
        "resolution_confidence": "deterministic",
        "resolution_wbw_lookup_sha256": corpus_sha256,
        "resolved_word_index": word,
        "resolved_surface": corpus_surface,
        "resolved_surface_norm_strict": corpus_norm,
    })
    accepted.pop("candidate_word_indices", None)
    return {
        "canonical_location": loc,
        "status": "accepted",
        "reason": None,
        "qword_row_id": qword_id,
        "row": accepted,
    }


def evaluate_rows(rows: Iterable[dict[str, Any]], **context: Any) -> list[dict[str, Any]]:
    decisions = [evaluate_candidate(row, **context) for row in rows]
    return sorted(decisions, key=lambda item: loc_key(item["canonical_location"]))


def _fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    qword_id = "llx-qword-aaaaaaaaaaaa-01-01-001"
    denominator = {
        "schema": "qamus/largelexicon-qword-denominator@1",
        "row_id": qword_id,
        "entry_id": "aaaaaaaaaaaa",
        "card_id": "aaaaaaaaaaaa:u1:e1",
        "quran_ref": "1:1",
        "qword_index": 1,
        "visible_surface": "بِسْمِ",
        "visible_surface_norm_strict": N.norm_strict("بِسْمِ"),
        "card_text_sha256": "a" * 64,
    }
    crosswalk = {
        "schema": "qamus/largelexicon-qword-crosswalk@1",
        "row_id": f"llx-crosswalk-{qword_id}",
        "qword_row_id": qword_id,
        "entry_id": denominator["entry_id"],
        "card_id": denominator["card_id"],
        "quran_ref": "1:1",
        "qword_index": 1,
        "visible_surface": denominator["visible_surface"],
        "visible_surface_norm_strict": denominator["visible_surface_norm_strict"],
        "status": "source_crosswalk_packet_ready",
        "packet_class": "source_address_crosswalk_packet",
        "terminal_gate_code": "canonical_quran_wbw_loc_unresolved",
        "next_action": "repair source crosswalk",
        "canonical_quran_loc": None,
        "canonical_wbw_loc": None,
        "match_status": "unresolved_arabic_surface_match",
        "resolution_normalizer": "arabic_surface_norm_v2_dagger_alif_to_alif",
        "resolution_source": "local_wbw_lookup_surface_alignment",
        "resolution_wbw_lookup_built_at": "2026-07-01T18:40:03Z",
        "resolution_wbw_lookup_sha256": "b" * 64,
        "source_dependencies": [
            {"kind": "qword_denominator_row", "id": qword_id,
             "sha256": sha256_row(denominator)},
            {"kind": "source_card", "id": denominator["card_id"],
             "sha256": denominator["card_text_sha256"]},
        ],
        "public_boundary": {"src": "qamus", "kind": "authored", "lang": "en"},
        "live_mutation_allowed": False,
    }
    queue = {
        "schema": QUEUE_SCHEMA,
        "canonical_location": "1:1:1",
        "primary_resolution_family": "unique_qword_candidate",
        "ayah_surface_unique": True,
        "candidate_count": 1,
        "candidate_entry_ids": [denominator["entry_id"]],
        "candidate_card_ids": [denominator["card_id"]],
        "candidate_qword_row_ids": [qword_id],
        "full_carrier_candidates": [{
            "entry_id": denominator["entry_id"],
            "card_id": denominator["card_id"],
            "qword_row_id": qword_id,
            "row_id": qword_id,
        }],
        "dependency_hashes": {qword_id: denominator["card_text_sha256"]},
        "morphline_state": "present",
        "source_normalization": {
            "live_surface": "بِسْمِ",
            "norm_strict": N.norm_strict("بِسْمِ"),
            "join_key": "1:1|" + N.norm_strict("بِسْمِ"),
        },
    }
    return queue, {"denominator": denominator, "crosswalk": crosswalk}


def self_test() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool) -> None:
        print(("ok   " if condition else "FAIL ") + label)
        if not condition:
            failures.append(label)

    queue, rows = _fixture()
    qword_id = rows["denominator"]["row_id"]
    corpus_sha = "c" * 64
    context = {
        "denominator_by_id": {qword_id: rows["denominator"]},
        "crosswalk_by_id": {qword_id: rows["crosswalk"]},
        "corpus_by_loc": {"1:1:1": "بِسْمِ"},
        "corpus_by_ayah": {"1:1": [("1:1:1", N.norm_strict("بِسْمِ"))]},
        "candidates_by_ayah_surface": {("1:1", N.norm_strict("بِسْمِ")): [qword_id]},
        "corpus_sha256": corpus_sha,
    }

    good = evaluate_candidate(queue, **context)
    check("positive control accepted", good["status"] == "accepted")

    bad_context = copy.deepcopy(context)
    bad_context["corpus_by_loc"]["1:1:1"] = "ٱلْحَمْدُ"
    decision = evaluate_candidate(queue, **bad_context)
    check("RED wrong surface at loc is skipped", decision == {
        "canonical_location": "1:1:1", "status": "skipped",
        "reason": "surface_mismatch_at_loc"})

    bad_context = copy.deepcopy(context)
    bad_context["corpus_by_ayah"]["1:1"].append(
        ("1:1:2", N.norm_strict("بِسْمِ")))
    decision = evaluate_candidate(queue, **bad_context)
    check("RED repeated ayah surface is skipped", decision["status"] == "skipped"
          and decision["reason"] == "ayah_surface_not_unique")

    bad_queue = copy.deepcopy(queue)
    bad_queue["full_carrier_candidates"][0]["card_id"] = ""
    decision = evaluate_candidate(bad_queue, **context)
    check("RED missing carrier field is skipped", decision["status"] == "skipped"
          and decision["reason"] == "carrier_incomplete")

    bad_queue = copy.deepcopy(queue)
    bad_queue["dependency_hashes"][qword_id] = "d" * 64
    decision = evaluate_candidate(bad_queue, **context)
    check("RED dependency hash mismatch is skipped", decision["status"] == "skipped"
          and decision["reason"] == "dependency_hash_mismatch")

    bad_context = copy.deepcopy(context)
    bad_context["candidates_by_ayah_surface"][("1:1", N.norm_strict("بِسْمِ"))].append(
        "llx-qword-bbbbbbbbbbbb-01-01-001")
    decision = evaluate_candidate(queue, **bad_context)
    check("RED competing runtime candidate is skipped", decision["status"] == "skipped"
          and decision["reason"] == "competing_candidate")

    bad_queue = copy.deepcopy(queue)
    bad_queue["morphline_state"] = "empty"
    decision = evaluate_candidate(bad_queue, **context)
    check("RED non-compilable live payload is skipped",
          decision["status"] == "skipped"
          and decision["reason"] == "live_payload_not_compilable")

    quarantined = copy.deepcopy(queue)
    quarantined["canonical_location"] = "2:214:1"
    decision = evaluate_candidate(quarantined, **context)
    check("RED divergent ayah is quarantined before proofing",
          decision["status"] == "skipped"
          and decision["reason"] == "quarantined_divergent_ayah_ref")

    check("harness cardinality arithmetic",
          expected_cardinalities(100, 40, 3, 2) == (103, 42))

    shuffled = [copy.deepcopy(queue), copy.deepcopy(queue)]
    shuffled[1]["canonical_location"] = "1:1:2"
    a = evaluate_rows(shuffled, **context)
    random.Random(19).shuffle(shuffled)
    b = evaluate_rows(shuffled, **context)
    check("RED deterministic decisions under input reordering",
          canonical_json_bytes(a) == canonical_json_bytes(b))
    accepted_decisions = [good, copy.deepcopy(good)]
    accepted_decisions[1]["qword_row_id"] = "llx-qword-bbbbbbbbbbbb-01-01-001"
    accepted_decisions[1]["row"]["qword_row_id"] = accepted_decisions[1]["qword_row_id"]
    shard_rows = {
        "fixture.jsonl": [
            rows["crosswalk"],
            {**copy.deepcopy(rows["crosswalk"]),
             "qword_row_id": accepted_decisions[1]["qword_row_id"]},
        ]
    }
    first_payload = apply_accepted_decisions(shard_rows, accepted_decisions)
    second_payload = apply_accepted_decisions(shard_rows, reversed(accepted_decisions))
    check("promoted shard bytes deterministic under decision reordering",
          shard_payload_sha256(first_payload) == shard_payload_sha256(second_payload))
    check("shadow reporter sample size satisfies CLI minimum", SHADOW_SAMPLE_SIZE >= 1)
    check("pre-existing shadow build conflicts must remain unchanged",
          build_conflicts_reconciled(30, 30))
    try:
        decode_probe = run_checked([
            sys.executable, "-c", "import os; os.write(1, bytes([0x97]))",
        ])
        decode_safe = isinstance(decode_probe.stdout, str) and "\ufffd" in decode_probe.stdout
    except Exception:
        decode_safe = False
    check("subprocess capture tolerates non-UTF8 Windows output", decode_safe)

    if failures:
        print(f"\n{len(failures)} SELF-TEST FAILURE(S)")
        return 1
    print("\nLANE A RESOLVER SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--wave", type=int, choices=(1, 2, 3))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--loc-surfaces", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.dry_run:
        if not args.wave or not args.baseline or not args.loc_surfaces:
            parser.error("--dry-run requires --wave, --baseline, and --loc-surfaces")
        report = write_dry_run(
            wave=args.wave,
            baseline=args.baseline.resolve(),
            corpus=args.loc_surfaces.resolve(),
        )
        print(json.dumps({
            "wave": args.wave,
            "state": report["state"],
            "counts": report["counts"],
            "decision_sha256": report["decision_sha256"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    if args.promote:
        if not args.wave or not args.baseline or not args.loc_surfaces:
            parser.error("--promote requires --wave, --baseline, and --loc-surfaces")
        report = promote_wave(
            wave=args.wave,
            baseline=args.baseline.resolve(),
            corpus=args.loc_surfaces.resolve(),
        )
        print(json.dumps({
            "wave": args.wave,
            "state": report["state"],
            "counts": report["counts"],
            "queue_after": report["queue_after"],
            "harness_cardinalities": report["harness_cardinalities"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    if args.finalize:
        if not args.wave:
            parser.error("--finalize requires --wave")
        report = finalize_wave(wave=args.wave)
        print(json.dumps({
            "wave": args.wave,
            "state": report["state"],
            "counts": report["counts"],
            "verification": report["verification"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    parser.error("choose --self-test, --dry-run, --promote, or --finalize")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
