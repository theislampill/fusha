#!/usr/bin/env python3
"""Adopt a reviewed Qamus qword crosswalk packet into source-clean shards.

This tool consumes private executor evidence (resolved/unresolved crosswalk
JSONL) and writes only the source-clean projection into the committed
largelexicon crosswalk table. It does not create live Qamus payloads.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from largelexicon_common import (
    atomic_promote_shards,
    PUBLIC_BOUNDARY,
    QWORD_CROSSWALK_MANIFEST,
    QWORD_CROSSWALK_SHARD_DIR,
    QWORD_DENOMINATOR_MANIFEST,
    FULL_TABLE_META,
    generation_fingerprint,
    git_value,
    repo_rel,
    rollback_generation,
    sha256_file,
    sha256_jsonl_rows,
    verify_generation,
    write_json,
    write_json_atomic,
    write_jsonl,
)


ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = "canonical_crosswalk_accepted"
PACKET = "source_crosswalk_packet_ready"
RESOLUTION_FIELDS = (
    "resolution_method",
    "resolution_confidence",
    "resolution_normalizer",
    "resolution_source",
    "resolution_wbw_lookup_built_at",
    "resolution_wbw_lookup_sha256",
    "resolved_word_index",
    "resolved_surface",
    "resolved_surface_norm_strict",
    "candidate_word_indices",
)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl_map(path: Path, *, status_name: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            qword_id = row.get("qword_row_id")
            if not qword_id:
                raise ValueError(f"{path}:{line_no}: missing qword_row_id")
            if qword_id in rows:
                raise ValueError(f"{path}:{line_no}: duplicate qword_row_id {qword_id}")
            if row.get("public_boundary") != PUBLIC_BOUNDARY:
                raise ValueError(f"{path}:{line_no}: non source-clean public_boundary")
            if row.get("live_mutation_allowed") is not False:
                raise ValueError(f"{path}:{line_no}: live_mutation_allowed must be false")
            if not row.get("source_dependencies"):
                raise ValueError(f"{path}:{line_no}: missing source_dependencies")
            rows[qword_id] = row
    if not rows:
        raise ValueError(f"{status_name} file is empty: {path}")
    return rows


def _copy_resolution_fields(target: dict[str, Any], evidence: dict[str, Any]) -> None:
    for field in RESOLUTION_FIELDS:
        if field in evidence:
            target[field] = evidence.get(field)


def adopted_row(row: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    if not evidence.get("canonical_quran_loc") or not evidence.get("canonical_wbw_loc"):
        raise ValueError(f"{row.get('row_id')}: resolved evidence lacks canonical loc")
    out = dict(row)
    out["canonical_quran_loc"] = evidence["canonical_quran_loc"]
    out["canonical_wbw_loc"] = evidence["canonical_wbw_loc"]
    out["match_status"] = evidence.get("match_status") or "resolved_arabic_surface_match"
    out["status"] = ACCEPTED
    out["packet_class"] = None
    out["terminal_gate_code"] = None
    out["next_action"] = None
    out["transclusion_route"] = "entry_card_qword_to_canonical_crosswalk_accepted"
    out["source_dependencies"] = evidence.get("source_dependencies") or row.get("source_dependencies") or []
    out["public_boundary"] = dict(PUBLIC_BOUNDARY)
    out["live_mutation_allowed"] = False
    _copy_resolution_fields(out, evidence)
    return out


def unresolved_row(row: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["canonical_quran_loc"] = None
    out["canonical_wbw_loc"] = None
    out["match_status"] = evidence.get("match_status") or "unresolved_arabic_surface_match"
    out["status"] = PACKET
    out["packet_class"] = evidence.get("packet_class") or "source_address_crosswalk_packet"
    out["terminal_gate_code"] = evidence.get("terminal_gate_code") or "canonical_quran_wbw_loc_unresolved"
    out["next_action"] = evidence.get("next_action") or (
        "Repair source-card/displayed-token/canonical-WBW crosswalk; require uniqueness before promotion."
    )
    out["transclusion_route"] = "entry_card_qword_to_canonical_crosswalk_packet"
    out["source_dependencies"] = evidence.get("source_dependencies") or row.get("source_dependencies") or []
    out["public_boundary"] = dict(PUBLIC_BOUNDARY)
    out["live_mutation_allowed"] = False
    _copy_resolution_fields(out, evidence)
    return out


def _iter_manifest_rows(manifest: dict[str, Any], root: Path) -> Iterable[tuple[dict[str, Any], list[dict[str, Any]]]]:
    for shard in manifest.get("shards") or []:
        path = root / shard["path"]
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        yield shard, rows


def adopt(
    *,
    resolved_path: Path,
    unresolved_path: Path,
    summary_path: Path | None,
    out_report: Path,
    dry_run: bool = False,
    root: Path = ROOT,
    manifest_path: Path = QWORD_CROSSWALK_MANIFEST,
) -> dict[str, Any]:
    resolved = read_jsonl_map(resolved_path, status_name="resolved")
    unresolved = read_jsonl_map(unresolved_path, status_name="unresolved")
    overlap = set(resolved) & set(unresolved)
    if overlap:
        sample = ", ".join(sorted(overlap)[:5])
        raise ValueError(f"resolved/unresolved overlap: {sample}")

    shard_dir = root / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk"
    input_generation_fingerprint = generation_fingerprint(shard_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current_generation = verify_generation(shard_dir)
    if not current_generation["ok"]:
        raise ValueError(f"current crosswalk generation is mixed or corrupt: {current_generation['errors']}")
    status_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    adopted_count = 0
    unresolved_count = 0
    unchanged_count = 0
    adopted_ids: set[str] = set()
    unresolved_ids: set[str] = set()
    new_shards: list[dict[str, Any]] = []
    shard_payloads: dict[str, list[dict[str, Any]]] = {}

    for shard, rows in _iter_manifest_rows(manifest, root):
        next_rows: list[dict[str, Any]] = []
        for row in rows:
            qword_id = row.get("qword_row_id")
            if qword_id in resolved:
                next_row = adopted_row(row, resolved[qword_id])
                adopted_count += 1
                adopted_ids.add(qword_id)
                method_counts[str(next_row.get("resolution_method"))] += 1
            elif qword_id in unresolved:
                next_row = unresolved_row(row, unresolved[qword_id])
                unresolved_count += 1
                unresolved_ids.add(qword_id)
                method_counts[str(next_row.get("resolution_method"))] += 1
            else:
                next_row = dict(row)
                unchanged_count += 1
            status_counts[str(next_row.get("status"))] += 1
            next_rows.append(next_row)

        shard_out = dict(shard)
        shard_path = root / shard["path"]
        try:
            shard_name = shard_path.relative_to(shard_dir).as_posix()
        except ValueError as exc:
            raise ValueError(f"crosswalk shard is outside its generation directory: {shard_path}") from exc
        shard_payloads[shard_name] = next_rows
        shard_out["row_count"] = len(next_rows)
        shard_out["sha256"] = sha256_jsonl_rows(next_rows)
        shard_out["first_row_id"] = next_rows[0].get("row_id") if next_rows else None
        shard_out["last_row_id"] = next_rows[-1].get("row_id") if next_rows else None
        new_shards.append(shard_out)

    missing_resolved = set(resolved) - adopted_ids
    missing_unresolved = set(unresolved) - unresolved_ids
    if missing_resolved:
        raise ValueError(f"resolved evidence has {len(missing_resolved)} qword ids absent from manifest")
    if missing_unresolved:
        raise ValueError(f"unresolved evidence has {len(missing_unresolved)} qword ids absent from manifest")

    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path else {}
    generated_at = now_iso()
    manifest.update(
        {
            "generated_at": generated_at,
            "generated_by": "tools/adopt_largelexicon_qword_crosswalk.py",
            "source_head": git_value("rev-parse", "HEAD"),
            "source_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
            "status": "active",
            "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
            "row_count": sum(shard["row_count"] for shard in new_shards),
            "shard_count": len(new_shards),
            "status_counts": dict(status_counts),
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "claim_boundary": (
                "Source-clean crosswalk projection only; accepted locs are internal support evidence, "
                "not live Qamus hover closure."
            ),
            "transclusion_contract": {
                "join_key": "qword_row_id",
                "canonical_keys": ["canonical_quran_loc", "canonical_wbw_loc"],
                "requires_source_dependencies": True,
                "forbidden_binding_keys": ["missing-loc|*", "sarf:surface:*"],
                "surface_only_fanout_allowed": False,
                "position_only_join_allowed": False,
            },
            "adoption": {
                "evidence_schema": summary.get("schema"),
                "evidence_generated_at": summary.get("generated_at"),
                "evidence_run_id": "qamus-crosswalk-parallel-20260703T112901Z",
                "evidence_counts": summary.get("counts") or {},
                "evidence_resolution_methods": summary.get("resolution_methods") or {},
                "evidence_sha256": summary.get("sha256") or {},
                "normalizer": summary.get("normalizer"),
                "resolved_rows_adopted": adopted_count,
                "unresolved_rows_recorded": unresolved_count,
                "unchanged_rows": unchanged_count,
                "adopted_at": generated_at,
                "private_path_redacted": True,
            },
            "shards": new_shards,
        }
    )
    if not dry_run:
        def install_sidecars(_generation: dict[str, Any]) -> None:
            _update_full_table_meta(root=root, crosswalk_manifest=manifest)
            # Install the authoritative external table manifest last.
            write_json_atomic(manifest_path, manifest)

        atomic_promote_shards(
            shard_dir,
            shard_payloads,
            writer_id="tools/adopt_largelexicon_qword_crosswalk.py",
            after_promote=install_sidecars,
            expected_current_fingerprint=input_generation_fingerprint,
        )

    report = {
        "schema": "qamus/largelexicon-crosswalk-adoption-report@1",
        "ok": True,
        "dry_run": dry_run,
        "generated_at": generated_at,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "resolved_rows_adopted": adopted_count,
        "unresolved_rows_recorded": unresolved_count,
        "unchanged_rows": unchanged_count,
        "status_counts": dict(status_counts),
        "resolution_method_counts": dict(method_counts),
        "manifest_path": repo_rel(manifest_path) if manifest_path.is_relative_to(ROOT) else str(manifest_path),
        "claim_boundary": manifest["claim_boundary"],
    }
    if not dry_run:
        write_json_atomic(out_report, report)
    return report


def _update_full_table_meta(*, root: Path, crosswalk_manifest: dict[str, Any]) -> None:
    full_table_meta = root / "qamus" / "indexes" / "largelexicon" / "source-clean-fact-tables.meta.json"
    if not full_table_meta.exists():
        return
    meta = json.loads(full_table_meta.read_text(encoding="utf-8"))
    meta["generated_at"] = crosswalk_manifest.get("generated_at")
    meta["generated_by"] = "tools/adopt_largelexicon_qword_crosswalk.py"
    freshness = meta.setdefault("freshness", {})
    freshness.update(
        {
            "generated_at": crosswalk_manifest.get("generated_at"),
            "generated_by": "tools/adopt_largelexicon_qword_crosswalk.py",
            "source_head": crosswalk_manifest.get("source_head"),
            "source_branch": crosswalk_manifest.get("source_branch"),
            "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
            "status": "active",
        }
    )
    meta["qword_crosswalk_manifest"] = crosswalk_manifest
    write_json_atomic(full_table_meta, meta)


def _refresh_manifest_after_rollback(*, root: Path, manifest_path: Path) -> None:
    """Make the external consumer manifest describe the restored shard bytes."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status_counts: Counter[str] = Counter()
    row_count = 0
    for shard in manifest.get("shards") or []:
        path = root / shard["path"]
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        shard["row_count"] = len(rows)
        shard["sha256"] = sha256_file(path)
        shard["first_row_id"] = rows[0].get("row_id") if rows else None
        shard["last_row_id"] = rows[-1].get("row_id") if rows else None
        row_count += len(rows)
        status_counts.update(str(row.get("status")) for row in rows)
    manifest.update(
        {
            "generated_at": now_iso(),
            "generated_by": "tools/adopt_largelexicon_qword_crosswalk.py --rollback",
            "row_count": row_count,
            "shard_count": len(manifest.get("shards") or []),
            "status_counts": dict(status_counts),
        }
    )
    _update_full_table_meta(root=root, crosswalk_manifest=manifest)
    write_json_atomic(manifest_path, manifest)


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        shard_dir = root / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk"
        shard_dir.mkdir(parents=True)
        rows = [
            {
                "schema": "qamus/largelexicon-qword-crosswalk@1",
                "row_id": "llx-crosswalk-llx-qword-aaaaaaaaaaaa-01-01-001",
                "qword_row_id": "llx-qword-aaaaaaaaaaaa-01-01-001",
                "entry_id": "aaaaaaaaaaaa",
                "canonical_quran_loc": None,
                "canonical_wbw_loc": None,
                "status": PACKET,
                "match_status": "pending_arabic_surface_match",
                "packet_class": "source_address_crosswalk_packet",
                "source_dependencies": [{"kind": "qword_denominator_row", "id": "llx-qword-aaaaaaaaaaaa-01-01-001"}],
                "public_boundary": dict(PUBLIC_BOUNDARY),
                "live_mutation_allowed": False,
            },
            {
                "schema": "qamus/largelexicon-qword-crosswalk@1",
                "row_id": "llx-crosswalk-llx-qword-bbbbbbbbbbbb-01-01-001",
                "qword_row_id": "llx-qword-bbbbbbbbbbbb-01-01-001",
                "entry_id": "bbbbbbbbbbbb",
                "canonical_quran_loc": None,
                "canonical_wbw_loc": None,
                "status": PACKET,
                "match_status": "pending_arabic_surface_match",
                "packet_class": "source_address_crosswalk_packet",
                "source_dependencies": [{"kind": "qword_denominator_row", "id": "llx-qword-bbbbbbbbbbbb-01-01-001"}],
                "public_boundary": dict(PUBLIC_BOUNDARY),
                "live_mutation_allowed": False,
            },
        ]
        shard = shard_dir / "sample.jsonl"
        write_jsonl(shard, rows)
        manifest_path = root / "qamus" / "indexes" / "largelexicon" / "qamus-qword-crosswalk.manifest.json"
        write_json(
            manifest_path,
            {
                "schema": "qamus/largelexicon-qword-crosswalk-manifest@1",
                "row_count": 2,
                "shard_count": 1,
                "public_boundary": dict(PUBLIC_BOUNDARY),
                "shards": [{"path": "qamus/indexes/largelexicon/qword-crosswalk/sample.jsonl", "row_count": 2, "sha256": sha256_file(shard)}],
            },
        )
        resolved = root / "resolved.jsonl"
        unresolved = root / "unresolved.jsonl"
        summary = root / "summary.json"
        write_jsonl(
            resolved,
            [
                {
                    **rows[0],
                    "status": "resolved_crosswalk_candidate",
                    "match_status": "resolved_arabic_surface_match",
                    "canonical_quran_loc": "1:1:1",
                    "canonical_wbw_loc": "1:1:1",
                    "resolution_method": "card_exact_subsequence",
                    "resolution_confidence": "deterministic",
                }
            ],
        )
        write_jsonl(unresolved, [{**rows[1], "match_status": "unresolved_arabic_surface_match"}])
        write_json(
            summary,
            {
                "schema": "qamus/crosswalk-parallel-resolution-summary@1",
                "generated_at": "2026-07-03T00:00:00Z",
                "counts": {"input_rows": 2, "resolved_rows": 1, "unresolved_rows": 1},
                "resolution_methods": {"card_exact_subsequence": 1},
            },
        )
        report = adopt(
            resolved_path=resolved,
            unresolved_path=unresolved,
            summary_path=summary,
            out_report=root / "report.json",
            root=root,
            manifest_path=manifest_path,
        )
        adopted = [json.loads(line) for line in shard.read_text(encoding="utf-8").splitlines()]
        ok = (
            report["resolved_rows_adopted"] == 1
            and report["unresolved_rows_recorded"] == 1
            and adopted[0]["status"] == ACCEPTED
            and adopted[0]["packet_class"] is None
            and adopted[1]["status"] == PACKET
            and json.loads(manifest_path.read_text(encoding="utf-8"))["status_counts"][ACCEPTED] == 1
            and verify_generation(shard_dir, allow_legacy=False)["ok"]
        )
        print(json.dumps({"ok": ok, "report": report}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved", type=Path)
    parser.add_argument("--unresolved", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--out-report", type=Path, default=ROOT / "qamus" / "reports" / "largelexicon-crosswalk-adoption-20260703.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--rollback", action="store_true", help="swap qword-crosswalk.prev back into service")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.rollback:
        result = rollback_generation(
            QWORD_CROSSWALK_SHARD_DIR,
            writer_id="tools/adopt_largelexicon_qword_crosswalk.py --rollback",
            after_rollback=lambda: _refresh_manifest_after_rollback(
                root=ROOT, manifest_path=QWORD_CROSSWALK_MANIFEST
            ),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not args.resolved or not args.unresolved:
        parser.error("--resolved and --unresolved are required unless --self-test is used")
    report = adopt(
        resolved_path=args.resolved,
        unresolved_path=args.unresolved,
        summary_path=args.summary,
        out_report=args.out_report,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
