#!/usr/bin/env python3
"""Build source-clean crosswalk status shards for the qword denominator."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from largelexicon_common import (
    PUBLIC_BOUNDARY,
    QWORD_CROSSWALK_MANIFEST,
    QWORD_CROSSWALK_SHARD_DIR,
    QWORD_DENOMINATOR_MANIFEST,
    freshness,
    qword_shard_label,
    repo_rel,
    sha256_file,
    sha256_text,
    write_json,
    write_jsonl,
)
from largelexicon_table_reader import LargelexiconQwordTable


ROOT = Path(__file__).resolve().parents[1]
CROSSWALK_SHARD_SIZE = 10


def _shard_sort_key(label: str) -> tuple[int, int, str]:
    if not label or label == "misc":
        return (9, 0, label or "")
    first = label.split("-", 1)[0]
    prefix = first[:1]
    try:
        number = int(first[1:])
    except ValueError:
        number = 0
    return ({"p": 0, "v": 1, "n": 2}.get(prefix, 9), number, label)


def _dependency_for_row(row: dict[str, Any], denominator_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    row_fingerprint = sha256_text(json.dumps(row, ensure_ascii=False, sort_keys=True))
    return [
        {"kind": "qword_denominator_row", "id": row.get("row_id"), "sha256": row_fingerprint},
        {"kind": "entry", "id": row.get("entry_id")},
        {"kind": "source_card", "id": row.get("card_id"), "sha256": row.get("card_text_sha256")},
        {
            "kind": "table_manifest",
            "id": "qamus-qword-denominator",
            "source_head": denominator_manifest.get("source_head"),
            "row_count": denominator_manifest.get("row_count"),
        },
    ]


def crosswalk_row(row: dict[str, Any], denominator_manifest: dict[str, Any]) -> dict[str, Any]:
    has_quran = bool(row.get("canonical_quran_loc"))
    has_wbw = bool(row.get("canonical_wbw_loc"))
    accepted = has_quran and has_wbw
    status = "canonical_crosswalk_accepted" if accepted else "source_crosswalk_packet_ready"
    return {
        "schema": "qamus/largelexicon-qword-crosswalk@1",
        "row_id": f"llx-crosswalk-{row.get('row_id')}",
        "qword_row_id": row.get("row_id"),
        "entry_id": row.get("entry_id"),
        "source_keys": row.get("source_keys") or [],
        "card_id": row.get("card_id"),
        "usage_index": row.get("usage_index"),
        "example_index": row.get("example_index"),
        "qword_index": row.get("qword_index"),
        "visible_surface": row.get("visible_surface"),
        "visible_surface_norm_strict": row.get("visible_surface_norm_strict"),
        "quran_ref": row.get("quran_ref"),
        "canonical_quran_loc": row.get("canonical_quran_loc"),
        "canonical_wbw_loc": row.get("canonical_wbw_loc"),
        "match_status": "accepted_existing_loc" if accepted else "pending_arabic_surface_match",
        "status": status,
        "packet_class": None if accepted else "source_address_crosswalk_packet",
        "terminal_gate_code": None if accepted else "canonical_quran_wbw_loc_missing",
        "next_action": None
        if accepted
        else "match visible Arabic surface inside the cited ayah; require uniqueness or emit duplicate-surface packet",
        "source_dependencies": _dependency_for_row(row, denominator_manifest),
        "transclusion_route": "entry_card_qword_to_canonical_crosswalk",
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "live_mutation_allowed": False,
    }


def build(root: Path = ROOT) -> dict[str, Any]:
    table = LargelexiconQwordTable.from_repo(root)
    denominator_manifest = json.loads(QWORD_DENOMINATOR_MANIFEST.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ranges: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    for row in table.iter_rows():
        cw = crosswalk_row(row, denominator_manifest)
        label, range_info = qword_shard_label(row, shard_size=CROSSWALK_SHARD_SIZE)
        grouped[label].append(cw)
        ranges[label] = range_info
        status_counts[cw["status"]] += 1

    QWORD_CROSSWALK_SHARD_DIR.mkdir(parents=True, exist_ok=True)
    for stale in QWORD_CROSSWALK_SHARD_DIR.glob("*.jsonl"):
        stale.unlink()

    shards: list[dict[str, Any]] = []
    total = 0
    for label in sorted(grouped, key=_shard_sort_key):
        rows = grouped[label]
        path = QWORD_CROSSWALK_SHARD_DIR / f"{label}.jsonl"
        write_jsonl(path, rows)
        total += len(rows)
        shards.append(
            {
                "path": repo_rel(path),
                "schema": "qamus/largelexicon-qword-crosswalk@1",
                "row_count": len(rows),
                "sha256": sha256_file(path),
                "first_row_id": rows[0].get("row_id"),
                "last_row_id": rows[-1].get("row_id"),
                "source_key_range": ranges[label],
            }
        )

    manifest = {
        "schema": "qamus/largelexicon-qword-crosswalk-manifest@1",
        **freshness(status="active", stale_after="qamus_qword_denominator_or_canonical_source_change"),
        "table_id": "qamus-qword-crosswalk",
        "denominator_manifest_path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
        "denominator_row_count": denominator_manifest.get("row_count"),
        "row_count": total,
        "shard_count": len(shards),
        "status_counts": dict(sorted(status_counts.items())),
        "shard_strategy": f"qamus_source_key_prefix_ordinal_ranges_{CROSSWALK_SHARD_SIZE}",
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "claim_boundary": "Crosswalk status table only; null-loc rows are packets, not deployable hovers.",
        "transclusion_contract": {
            "requires_source_dependencies": True,
            "forward_trace": "entry/card/qword -> crosswalk status -> packet/candidate",
            "reverse_trace": "crosswalk row -> qword_row_id -> entry/card/source dependencies",
        },
        "shards": shards,
    }
    write_json(QWORD_CROSSWALK_MANIFEST, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    manifest = build()
    print(
        json.dumps(
            {
                "ok": True,
                "row_count": manifest["row_count"],
                "shard_count": manifest["shard_count"],
                "status_counts": manifest["status_counts"],
                "manifest_path": repo_rel(QWORD_CROSSWALK_MANIFEST),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
