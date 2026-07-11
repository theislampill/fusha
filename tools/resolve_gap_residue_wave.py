#!/usr/bin/env python3
"""Resolve T10 residue rows and execute the authorized RM-36 demotion wave."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from largelexicon_common import (  # noqa: E402
    atomic_promote_shards,
    generation_fingerprint,
    rollback_generation,
    sha256_file,
    sha256_jsonl_rows,
    verify_generation,
    write_json_atomic,
)
from normalize_ar import bare, norm_strict  # noqa: E402
from reverify_crosswalk_fallback import (  # noqa: E402
    DEMOTION as RM36_DEMOTION_BUCKET,
    classify_rows as reverify_rows,
)
from validate_largelexicon_denominator_join import _join_surface_key  # noqa: E402


BASELINE_HEAD = "446a536a432cc819ddfcfcf1bd61dd7601996c94"
BASELINE_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
CORPUS_SHA256 = "f2e079dcdce01148074a238e3937314cf02222298f91f83ed66dcbb599697ca7"
QUEUE_SHA256 = "bde1d5f84d20ba0f4e2bc7099acf5c35f9c44882257e1ce239c489111905fbc7"
LANEB_SHA256 = "10de3214aea4f6a100d5f19b5cabd3830b744ed35002644ee72e273d80ffafaf"
RM36_FAILING_SHA256 = "b2fbf42c959662d5421f55d6343e070b077274434cd84c2db2fafb66122e086f"

ACCEPTED = "canonical_crosswalk_accepted"
PACKET = "source_crosswalk_packet_ready"
DEMOTED = "canonical_crosswalk_demoted"
DEMOTION_WAVE = "rm36-demotion-01"
DEMOTION_REASON = "vowel_preserving_ayah_uniqueness_failed"
REINSTATEMENT_CONDITION = (
    "uniqueness re-proof under _join_surface_key or reviewed occurrence adjudication"
)
PROMOTION_METHOD = "multi_binding_exact_ayah_surface_v1"
QUARANTINED_AYAHS = {
    "4:64", "12:37", "19:67", "2:214", "2:274", "3:152", "48:15",
    "92:3", "93:3", "98:1",
}

INDEX_ROOT = ROOT / "qamus" / "indexes" / "largelexicon"
CROSSWALK_DIR = INDEX_ROOT / "qword-crosswalk"
CROSSWALK_MANIFEST = INDEX_ROOT / "qamus-qword-crosswalk.manifest.json"
FULL_TABLE_META = INDEX_ROOT / "source-clean-fact-tables.meta.json"
DENOMINATOR_DIR = INDEX_ROOT / "qword-denominator"
QUEUE_DIR = INDEX_ROOT / "crosswalk-gap"
QUEUE_PATH = QUEUE_DIR / "crosswalk-gap-queue.jsonl"
QUEUE_MANIFEST = QUEUE_DIR / "crosswalk-gap-queue.manifest.json"
LANEB_PATH = QUEUE_DIR / "laneb-classification.jsonl"
RESIDUE_REPORT = QUEUE_DIR / "residue-wave-01.report.json"
RM36_DIR = ROOT / "qamus" / "reports" / "rm36-fallback-reverification"
RM36_FAILING = RM36_DIR / "failing-rows.jsonl"
DEMOTION_REPORT = RM36_DIR / "demotion-wave.report.json"
UNVERIFIED_BUCKETS = RM36_DIR / "unverified-buckets.jsonl"


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: row is not an object")
            rows.append(row)
    return rows


def write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def canonical_json_sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ayah_of(loc: str) -> str:
    return ":".join(loc.split(":")[:2])


def loc_key(loc: str) -> tuple[int, int, int]:
    parts = loc.split(":")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid location: {loc!r}")
    return tuple(int(part) for part in parts)


def load_corpus(path: Path) -> tuple[
    list[dict[str, str]], dict[str, str], dict[str, list[tuple[str, str]]]
]:
    rows: list[dict[str, str]] = []
    by_loc: dict[str, str] = {}
    by_ayah: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in read_jsonl(path):
        loc = row.get("loc")
        surface = row.get("surface")
        if not isinstance(loc, str) or not isinstance(surface, str) or loc in by_loc:
            raise ValueError(f"invalid or duplicate corpus row: {row!r}")
        loc_key(loc)
        rows.append({"loc": loc, "surface": surface})
        by_loc[loc] = surface
        by_ayah[ayah_of(loc)].append((loc, norm_strict(surface)))
    for values in by_ayah.values():
        values.sort(key=lambda item: loc_key(item[0]))
    return rows, by_loc, dict(by_ayah)


def load_table(directory: Path, id_field: str) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_id: dict[str, dict[str, Any]] = {}
    shards: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(directory.glob("*.jsonl")):
        shard_rows = read_jsonl(path)
        shards[path.name] = shard_rows
        for row in shard_rows:
            row_id = row.get(id_field)
            if not isinstance(row_id, str) or not row_id or row_id in by_id:
                raise ValueError(f"missing or duplicate {id_field}: {row_id!r}")
            by_id[row_id] = row
    return by_id, shards


def build_co_citation_promotions(
    queue_row: dict[str, Any],
    *,
    denominator_by_id: dict[str, dict[str, Any]] | None = None,
    crosswalk_by_id: dict[str, dict[str, Any]] | None = None,
    corpus_by_loc: dict[str, str] | None = None,
    corpus_by_ayah: dict[str, list[tuple[str, str]]] | None = None,
    corpus_sha256: str = CORPUS_SHA256,
) -> list[dict[str, Any]]:
    """Return every full carrier only when the Lane-A proof set agrees."""
    if queue_row.get("ayah_surface_unique") is not True:
        return []
    loc = str(queue_row.get("canonical_location") or "")
    if not loc or ayah_of(loc) in QUARANTINED_AYAHS:
        return []
    carriers = queue_row.get("full_carrier_candidates") or []
    if len(carriers) < 2:
        return []
    if denominator_by_id is None:
        return [copy.deepcopy(row) for row in carriers]
    if crosswalk_by_id is None or corpus_by_loc is None or corpus_by_ayah is None:
        raise ValueError("runtime proof inputs are incomplete")
    surface = corpus_by_loc.get(loc)
    live_norm = (queue_row.get("source_normalization") or {}).get("norm_strict")
    if not surface or norm_strict(surface) != live_norm:
        return []
    positions = [position for position, key in corpus_by_ayah.get(ayah_of(loc), []) if key == live_norm]
    if positions != [loc]:
        return []
    promoted: list[dict[str, Any]] = []
    for carrier in carriers:
        required = ("entry_id", "card_id", "qword_row_id", "row_id")
        if any(not carrier.get(field) for field in required):
            return []
        qword_id = carrier["qword_row_id"]
        if carrier["row_id"] != qword_id:
            return []
        denominator = denominator_by_id.get(qword_id)
        crosswalk = crosswalk_by_id.get(qword_id)
        if not denominator or not crosswalk or crosswalk.get("status") != PACKET:
            return []
        if any(denominator.get(field) != carrier.get(field) for field in ("entry_id", "card_id")):
            return []
        dependency_sha = (queue_row.get("dependency_hashes") or {}).get(qword_id)
        if not dependency_sha or dependency_sha != denominator.get("card_text_sha256"):
            return []
        if denominator.get("visible_surface_norm_strict") != live_norm:
            return []
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
            "resolution_method": PROMOTION_METHOD,
            "resolution_confidence": "deterministic",
            "resolution_wbw_lookup_sha256": corpus_sha256,
            "resolved_word_index": loc_key(loc)[2],
            "resolved_surface": surface,
            "resolved_surface_norm_strict": live_norm,
        })
        accepted.pop("candidate_word_indices", None)
        promoted.append(accepted)
    return sorted(promoted, key=lambda row: row["qword_row_id"])


def disposition_unique_residue(row: dict[str, Any]) -> dict[str, Any]:
    loc = row["canonical_location"]
    if ayah_of(loc) in QUARANTINED_AYAHS:
        family = "quarantined_nf_t10_1"
        next_action = "NF-T10-1"
    elif "live_surface_not_in_ayah_index" in (row.get("secondary_conditions") or []):
        family = "normalization_mismatch"
        next_action = "normalization_review"
    elif row.get("morphline_state") != "present":
        family = "morphline_missing"
        next_action = "lane_d_authoring"
    elif row.get("ayah_surface_unique") is False:
        family = "surface_repeats"
        next_action = "two_vote_occurrence_queue"
    else:
        family = "source_identity_unproved"
        next_action = "source_identity_review"
    return {
        "canonical_location": loc,
        "failure_family": family,
        "next_action": next_action,
        "qword_row_ids": list(row.get("candidate_qword_row_ids") or []),
        "visible_surface": (row.get("source_normalization") or {}).get("live_surface"),
    }


def classify_unverified(row: dict[str, Any]) -> tuple[str, str]:
    if row.get("bucket") == "unverifiable_divergent_ayah":
        return "nf_t10_1_dependent", "ayah belongs to the pinned NF-T10-1 divergence set"
    indexed = row.get("indexed_location_surface")
    visible = row.get("visible_surface")
    if indexed is None:
        return "needs_full_quran_index", "canonical location is absent from the pinned Quran index"
    if isinstance(visible, str) and norm_strict(visible) == norm_strict(str(indexed)):
        return "normalization_correction", "strict consonantal identity agrees but vowel-preserving identity differs"
    if row.get("canonical_quran_loc"):
        return "missing_source_identity", "indexed location does not establish the recorded source surface"
    return "permanent_exception_candidate", "no recoverable canonical source identity"


def build_unverified_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if row.get("bucket") == RM36_DEMOTION_BUCKET:
            continue
        classification, reason = classify_unverified(row)
        output.append({
            "schema": "fusha/rm36-unverified-identity@1",
            "bucket": row.get("bucket"),
            "classification": classification,
            "classification_reason": reason,
            "canonical_quran_loc": row.get("canonical_quran_loc"),
            "quran_ref": row.get("quran_ref"),
            "row_id": row.get("row_id"),
            "qword_row_id": row.get("qword_row_id"),
            "entry_id": row.get("entry_id"),
            "card_id": row.get("card_id"),
            "visible_surface": row.get("visible_surface"),
            "indexed_location_surface": row.get("indexed_location_surface"),
            "row_surface_join_key": row.get("row_surface_join_key"),
            "indexed_location_surface_join_key": row.get("indexed_location_surface_join_key"),
            "matching_positions": list(row.get("matching_positions") or []),
        })
    return sorted(output, key=lambda row: (loc_key(row["canonical_quran_loc"]), row["row_id"]))


def demote_rows(
    candidates: list[dict[str, Any]],
    *,
    crosswalk_by_id: dict[str, dict[str, Any]],
    corpus_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        if ayah_of(candidate["canonical_quran_loc"]) in QUARANTINED_AYAHS:
            raise RuntimeError("RM-36 demotion intersects NF-T10-1 quarantine")
        row = crosswalk_by_id.get(candidate["qword_row_id"])
        if not row or row.get("status") != ACCEPTED:
            raise RuntimeError(f"demotion source row is not currently accepted: {candidate['qword_row_id']}")
        if row.get("row_id") != candidate.get("row_id"):
            raise RuntimeError(f"demotion row identity drift: {candidate['row_id']}")
        source_rows.append(row)
    runtime = reverify_rows(source_rows, corpus_rows, QUARANTINED_AYAHS)
    verified = runtime[RM36_DEMOTION_BUCKET]
    expected = sorted(row["row_id"] for row in candidates)
    actual = sorted(row["row_id"] for row in verified)
    if actual != expected:
        raise RuntimeError("RM-36 runtime demotion set changed")
    evidence_by_id = {row["row_id"]: row for row in verified}
    demoted_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for source in source_rows:
        evidence = evidence_by_id[source["row_id"]]
        positions = list(evidence["matching_positions"])
        out = copy.deepcopy(source)
        out["status"] = DEMOTED
        out["demotion"] = {
            "wave": DEMOTION_WAVE,
            "reason": DEMOTION_REASON,
            "evidence": {"positions": positions},
            "prior_status": ACCEPTED,
            "demoted_at_head": BASELINE_HEAD,
            "reinstatement_condition": REINSTATEMENT_CONDITION,
        }
        demoted_rows.append(out)
        evidence_rows.append({
            "canonical_quran_loc": source["canonical_quran_loc"],
            "row_id": source["row_id"],
            "qword_row_id": source["qword_row_id"],
            "visible_surface": source["visible_surface"],
            "positions": positions,
        })
    return demoted_rows, sorted(evidence_rows, key=lambda row: (loc_key(row["canonical_quran_loc"]), row["row_id"]))


def apply_replacements(
    shards: dict[str, list[dict[str, Any]]], replacements: Iterable[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    by_id = {row["qword_row_id"]: row for row in replacements}
    found: set[str] = set()
    output: dict[str, list[dict[str, Any]]] = {}
    for name, rows in sorted(shards.items()):
        next_rows: list[dict[str, Any]] = []
        for row in rows:
            replacement = by_id.get(row.get("qword_row_id"))
            if replacement is None:
                next_rows.append(copy.deepcopy(row))
            else:
                next_rows.append(copy.deepcopy(replacement))
                found.add(replacement["qword_row_id"])
        output[name] = next_rows
    if found != set(by_id):
        raise RuntimeError(f"replacement rows absent from shards: {sorted(set(by_id) - found)[:5]}")
    return output


def accepted_arithmetic(shards: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    bindings: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    for rows in shards.values():
        for row in rows:
            status_counts[str(row.get("status"))] += 1
            if row.get("status") == ACCEPTED:
                bindings[str(row.get("canonical_wbw_loc"))] += 1
    return {
        "accepted_bindings": sum(bindings.values()),
        "modeled_locations": len(bindings),
        "accepted_bindings_by_location": bindings,
        "status_counts": dict(sorted(status_counts.items())),
    }


def build_manifest(
    shards: dict[str, list[dict[str, Any]]], *, promoted_at: str, decision_sha256: str
) -> dict[str, Any]:
    manifest = json.loads(CROSSWALK_MANIFEST.read_text(encoding="utf-8"))
    existing = {Path(item["path"]).name: item for item in manifest["shards"]}
    if set(existing) != set(shards):
        raise RuntimeError("crosswalk manifest/shard set mismatch")
    status_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    for name, rows in sorted(shards.items()):
        status_counts.update(str(row.get("status")) for row in rows)
        resolution_counts.update(str(row.get("resolution_method")) for row in rows if row.get("resolution_method"))
        item = copy.deepcopy(existing[name])
        item.update({
            "row_count": len(rows),
            "sha256": sha256_jsonl_rows(rows),
            "first_row_id": rows[0].get("row_id") if rows else None,
            "last_row_id": rows[-1].get("row_id") if rows else None,
        })
        items.append(item)
    manifest.update({
        "generated_at": promoted_at,
        "generated_by": "tools/resolve_gap_residue_wave.py",
        "source_head": BASELINE_HEAD,
        "source_branch": subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True, encoding="utf-8"
        ).strip(),
        "status": "active",
        "row_count": sum(len(rows) for rows in shards.values()),
        "shard_count": len(shards),
        "status_counts": dict(sorted(status_counts.items())),
        "shards": items,
        "residue_wave": {
            "wave": "t10-residue-rm36-01",
            "promoted_bindings": 47,
            "demoted_bindings": 37,
            "decision_sha256": decision_sha256,
            "promoted_at": promoted_at,
            "resolution_method_counts": dict(sorted(resolution_counts.items())),
            "mechanical_crosswalk_only": True,
        },
    })
    return manifest


def update_full_meta(manifest: dict[str, Any]) -> None:
    meta = json.loads(FULL_TABLE_META.read_text(encoding="utf-8"))
    meta["generated_at"] = manifest["generated_at"]
    meta["generated_by"] = "tools/resolve_gap_residue_wave.py"
    meta["freshness"] = {
        **(meta.get("freshness") or {}),
        "generated_at": manifest["generated_at"],
        "generated_by": "tools/resolve_gap_residue_wave.py",
        "source_head": BASELINE_HEAD,
        "source_branch": manifest["source_branch"],
        "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
        "status": "active",
    }
    meta["qword_crosswalk_manifest"] = manifest
    write_json_atomic(FULL_TABLE_META, meta)


def snapshot(paths: Iterable[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def restore(files: dict[Path, bytes | None]) -> None:
    for path, content in files.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def rebuild_queue(baseline: Path, corpus: Path) -> dict[str, Any]:
    from tools.build_crosswalk_gap_queue import build_queue, write_outputs

    manifest, rows = build_queue(str(ROOT), str(baseline), str(corpus))
    with tempfile.TemporaryDirectory(prefix="residue-queue-") as td:
        queue_path, manifest_path, final = write_outputs(td, manifest, rows)
        os.replace(queue_path, QUEUE_PATH)
        os.replace(manifest_path, QUEUE_MANIFEST)
    return final


def execute(baseline: Path, corpus: Path) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != BASELINE_HEAD:
        raise RuntimeError(f"HEAD drift: {head} != {BASELINE_HEAD}")
    pinned = {
        baseline: BASELINE_SHA256,
        corpus: CORPUS_SHA256,
        QUEUE_PATH: QUEUE_SHA256,
        LANEB_PATH: LANEB_SHA256,
        RM36_FAILING: RM36_FAILING_SHA256,
    }
    for path, expected in pinned.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"input hash mismatch: {path}: {actual} != {expected}")
    generation = verify_generation(CROSSWALK_DIR)
    if not generation["ok"]:
        raise RuntimeError(f"invalid current crosswalk generation: {generation['errors']}")
    fingerprint = generation_fingerprint(CROSSWALK_DIR)

    queue = read_jsonl(QUEUE_PATH)
    queue_by_loc = {row["canonical_location"]: row for row in queue}
    laneb = read_jsonl(LANEB_PATH)
    corpus_rows, corpus_by_loc, corpus_by_ayah = load_corpus(corpus)
    denominator_by_id, _denominator_shards = load_table(DENOMINATOR_DIR, "row_id")
    crosswalk_by_id, shards = load_table(CROSSWALK_DIR, "qword_row_id")

    co_classes = {"same_occurrence_multi_entry_co_citation", "same_entry_multi_card"}
    co_rows = [row for row in laneb if row.get("laneb_classification") in co_classes]
    if len(co_rows) != 19:
        raise RuntimeError(f"co-citation location count drift: {len(co_rows)}")
    promotions: list[dict[str, Any]] = []
    promotion_decisions: list[dict[str, Any]] = []
    for classified in sorted(co_rows, key=lambda row: loc_key(row["canonical_location"])):
        loc = classified["canonical_location"]
        promoted = build_co_citation_promotions(
            queue_by_loc[loc],
            denominator_by_id=denominator_by_id,
            crosswalk_by_id=crosswalk_by_id,
            corpus_by_loc=corpus_by_loc,
            corpus_by_ayah=corpus_by_ayah,
        )
        expected_ids = sorted(classified["evidence"]["candidate_qword_row_ids"])
        if [row["qword_row_id"] for row in promoted] != expected_ids:
            raise RuntimeError(f"co-citation proof failed closed at {loc}")
        promotions.extend(promoted)
        promotion_decisions.append({
            "canonical_location": loc,
            "classification": classified["laneb_classification"],
            "binding_count": len(promoted),
            "qword_row_ids": expected_ids,
            "status": "promoted",
        })
    if len(promotions) != 47:
        raise RuntimeError(f"co-citation binding count drift: {len(promotions)}")

    normalization_rows = [row for row in laneb if row.get("laneb_classification") == "normalization_collision"]
    if len(normalization_rows) != 3:
        raise RuntimeError(f"normalization row count drift: {len(normalization_rows)}")
    normalization_decisions: list[dict[str, Any]] = []
    for row in sorted(normalization_rows, key=lambda item: loc_key(item["canonical_location"])):
        loc = row["canonical_location"]
        indexed = corpus_by_loc.get(loc)
        live = row["evidence"]["source_normalization"]["live_surface"]
        normalization_decisions.append({
            "canonical_location": loc,
            "status": "routed_to_review",
            "failure_family": "normalization_equivalence_unproved",
            "next_action": "normalization_review",
            "evidence": {
                "live_surface": live,
                "indexed_location_surface": indexed,
                "norm_strict_equal": bool(indexed and norm_strict(live) == norm_strict(indexed)),
                "bare_equal": bool(indexed and bare(live) == bare(indexed)),
                "source_location_present": indexed is not None,
            },
        })

    unique_rows = [row for row in queue if row.get("primary_resolution_family") == "unique_qword_candidate"]
    if len(unique_rows) != 51:
        raise RuntimeError(f"unique residue row count drift: {len(unique_rows)}")
    dispositions = [disposition_unique_residue(row) for row in sorted(unique_rows, key=lambda row: loc_key(row["canonical_location"]))]

    failing = read_jsonl(RM36_FAILING)
    demotion_candidates = [row for row in failing if row.get("bucket") == RM36_DEMOTION_BUCKET]
    if len(demotion_candidates) != 37:
        raise RuntimeError(f"demotion candidate count drift: {len(demotion_candidates)}")
    demotions, demotion_evidence = demote_rows(
        demotion_candidates, crosswalk_by_id=crosswalk_by_id, corpus_rows=corpus_rows
    )
    unverified = build_unverified_rows(failing)
    bucket_counts = Counter(row["bucket"] for row in unverified)
    if bucket_counts != Counter({"unverifiable_divergent_ayah": 63, "surface_not_in_indexed_ayah": 396}):
        raise RuntimeError(f"unverified bucket count drift: {dict(bucket_counts)}")

    before = accepted_arithmetic(shards)
    replacements = [*promotions, *demotions]
    if len({row["qword_row_id"] for row in replacements}) != len(replacements):
        raise RuntimeError("promotion/demotion replacement overlap")
    promoted_shards = apply_replacements(shards, replacements)
    after = accepted_arithmetic(promoted_shards)
    demoted_by_loc = Counter(row["canonical_quran_loc"] for row in demotions)
    lost_locations = sorted(
        (
            loc for loc, count in demoted_by_loc.items()
            if before["accepted_bindings_by_location"][loc] - count == 0
        ),
        key=loc_key,
    )
    if lost_locations:
        raise RuntimeError(f"unexpected modeled locations lost: {lost_locations}")
    if after["accepted_bindings"] != 86980 or after["modeled_locations"] != 42084:
        raise RuntimeError(f"accepted arithmetic drift: {after['accepted_bindings']}/{after['modeled_locations']}")

    promoted_at = now_iso()
    decisions_digest = canonical_json_sha({
        "promotions": promotion_decisions,
        "normalization": normalization_decisions,
        "dispositions": dispositions,
        "demotions": demotion_evidence,
        "unverified": unverified,
    })
    manifest = build_manifest(promoted_shards, promoted_at=promoted_at, decision_sha256=decisions_digest)
    residue_report = {
        "schema": "qamus/t10-residue-wave-report@1",
        "generated_by": "tools/resolve_gap_residue_wave.py",
        "generated_at": promoted_at,
        "baseline_head": BASELINE_HEAD,
        "state": "promoted_pending_harness",
        "quarantine_ayah_refs": sorted(QUARANTINED_AYAHS),
        "counts": {
            "co_citation_locations_promoted": 19,
            "co_citation_bindings_promoted": 47,
            "normalization_rows_promoted": 0,
            "normalization_rows_routed_to_review": 3,
            "unique_residue_rows_dispositioned": 51,
        },
        "disposition_counts": dict(sorted(Counter(row["failure_family"] for row in dispositions).items())),
        "promotions": promotion_decisions,
        "normalization_decisions": normalization_decisions,
        "unique_residue_dispositions": dispositions,
        "decision_sha256": decisions_digest,
    }
    demotion_report = {
        "schema": "fusha/rm36-demotion-wave-report@1",
        "generated_by": "tools/resolve_gap_residue_wave.py",
        "generated_at": promoted_at,
        "wave": DEMOTION_WAVE,
        "state": "promoted_pending_harness",
        "baseline_head": BASELINE_HEAD,
        "reason": DEMOTION_REASON,
        "counts": {
            "bindings_demoted": 37,
            "affected_locations": len(demoted_by_loc),
            "locations_losing_all_bindings": len(lost_locations),
        },
        "locations_losing_all_bindings": lost_locations,
        "accepted_arithmetic": {
            "before_bindings": before["accepted_bindings"],
            "promoted_bindings": len(promotions),
            "demoted_bindings": len(demotions),
            "after_bindings": after["accepted_bindings"],
            "before_modeled_locations": before["modeled_locations"],
            "promoted_locations": len(promotion_decisions),
            "demoted_locations_lost": len(lost_locations),
            "after_modeled_locations": after["modeled_locations"],
        },
        "expected_shadow_delta": {
            "live_only": len(lost_locations),
            "no_op": len(promotion_decisions),
            "binding_count": len(promotions) - len(demotions),
        },
        "status_enumerators_updated": [
            "tools/adopt_largelexicon_qword_crosswalk.py:VALID_STATUSES",
            "tools/validate_largelexicon_qword_crosswalk.py:VALID_STATUSES",
        ],
        "accepted_only_consumers_verified": [
            "tools/build_append_queue.py",
            "tools/build_crosswalk_gap_queue.py",
            "tools/check_regressions.py:T5_G1",
            "tools/reverify_crosswalk_fallback.py",
            "tools/run_shadow_compile.py",
            "tools/validate_largelexicon_denominator_join.py",
        ],
        "demotions": demotion_evidence,
    }

    mutable = [CROSSWALK_MANIFEST, FULL_TABLE_META, QUEUE_PATH, QUEUE_MANIFEST, RESIDUE_REPORT, DEMOTION_REPORT, UNVERIFIED_BUCKETS]
    files_before = snapshot(mutable)
    promoted = False
    try:
        def install_sidecars(_generation: dict[str, Any]) -> None:
            update_full_meta(manifest)
            write_json_atomic(CROSSWALK_MANIFEST, manifest)

        atomic_promote_shards(
            CROSSWALK_DIR,
            promoted_shards,
            writer_id="tools/resolve_gap_residue_wave.py",
            promoted_at=promoted_at,
            after_promote=install_sidecars,
            expected_current_fingerprint=fingerprint,
        )
        promoted = True
        validator = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_largelexicon_qword_crosswalk.py")],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        if validator.returncode:
            raise RuntimeError("materialized crosswalk validation failed:\n" + validator.stdout + validator.stderr)
        queue_manifest = rebuild_queue(baseline, corpus)
        if queue_manifest["queue_rows"] != 5502 or queue_manifest["modeled_locations"] != 42084:
            raise RuntimeError(f"queue reconciliation failed: {queue_manifest}")
        write_jsonl_atomic(UNVERIFIED_BUCKETS, unverified)
        write_json_atomic(RESIDUE_REPORT, {**residue_report, "queue_after": {
            "rows": queue_manifest["queue_rows"],
            "family_counts": queue_manifest["family_counts"],
            "sha256": queue_manifest["queue_sha256"],
        }})
        write_json_atomic(DEMOTION_REPORT, demotion_report)
    except BaseException:
        if promoted:
            rollback_generation(CROSSWALK_DIR, writer_id="tools/resolve_gap_residue_wave.py:rollback")
        restore(files_before)
        raise
    return {
        "promoted_bindings": len(promotions),
        "demoted_bindings": len(demotions),
        "modeled_locations_after": after["modeled_locations"],
        "accepted_bindings_after": after["accepted_bindings"],
        "locations_lost": len(lost_locations),
        "queue_rows_after": 5502,
        "unverified_rows": len(unverified),
    }


def self_test() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool) -> None:
        print(("ok   " if condition else "FAIL ") + label)
        if not condition:
            failures.append(label)

    queue_row = {
        "canonical_location": "1:1:1",
        "ayah_surface_unique": True,
        "full_carrier_candidates": [
            {"qword_row_id": "q1"},
            {"qword_row_id": "q2"},
        ],
    }
    check(
        "co-citation preserves every carrier",
        [row["qword_row_id"] for row in build_co_citation_promotions(queue_row)] == ["q1", "q2"],
    )
    check(
        "RED repeated ayah surface blocks co-citation promotion",
        build_co_citation_promotions({**queue_row, "ayah_surface_unique": False}) == [],
    )
    normalization_row = {
        "bucket": "surface_not_in_indexed_ayah",
        "visible_surface": "مِنْ",
        "indexed_location_surface": "مِن",
        "canonical_quran_loc": "1:1:1",
    }
    classification, _reason = classify_unverified(normalization_row)
    check("normalization correction is classified but never promoted", classification == "normalization_correction")
    demoted = {"status": DEMOTED}
    accepted = {"status": ACCEPTED}
    compiler_inputs = [row for row in [accepted, demoted] if row.get("status") == ACCEPTED]
    check("demoted row excluded from compiler-input construction", compiler_inputs == [accepted])
    dispositions = [
        disposition_unique_residue({
            "canonical_location": "2:214:1", "candidate_qword_row_ids": [],
            "source_normalization": {}, "secondary_conditions": [], "morphline_state": "present",
        }),
        disposition_unique_residue({
            "canonical_location": "1:1:1", "candidate_qword_row_ids": [],
            "source_normalization": {}, "secondary_conditions": ["live_surface_not_in_ayah_index"],
            "morphline_state": "present",
        }),
        disposition_unique_residue({
            "canonical_location": "1:1:2", "candidate_qword_row_ids": [],
            "source_normalization": {}, "secondary_conditions": [], "morphline_state": "empty",
        }),
    ]
    check(
        "residue dispositions have concrete family and next action",
        all(row["failure_family"] and row["next_action"] for row in dispositions),
    )
    if failures:
        print(f"\n{len(failures)} RESIDUE WAVE SELF-TEST FAILURE(S)")
        return 1
    print("\nRESIDUE WAVE SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--loc-surfaces", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.apply or not args.baseline or not args.loc_surfaces:
        parser.error("--apply, --baseline, and --loc-surfaces are required")
    result = execute(args.baseline.resolve(), args.loc_surfaces.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
