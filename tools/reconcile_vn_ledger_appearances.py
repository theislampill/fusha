#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile vn-ledger.jsonl + vn-graph-metrics.json with the appearance index.

When ``qamus/indexes/occurrence-appearances.jsonl`` is repaired/regenerated
(e.g. the per-selected-token reciprocity repair in
``build_occurrence_appearance_index.py --repair-reciprocity``), the committed
ledger rows pin appearance-derived fields (``appearance_count``,
``appearance_entry_relationships``, ``reverse_entry_relationship_present``)
and the metrics report pins their aggregates.  This tool recomputes exactly
those fields as the pure functions the ledger builder uses — no whitelist
input is required — and rewrites both artifacts so
``tools/validate_vn_ledger.py`` stays green.

Never invents rows; never touches missing_edges, join methods, tranches, or
any non-appearance-derived field.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.build_entry_card_word_ledger import (  # noqa: E402
    _appearance_index_complete,
    _reverse_entry_present,
)


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def reconcile(ledger_rows, metrics, index_records):
    by_loc = {record["loc"]: record for record in index_records}
    changed_rows = 0
    reverse_complete = 0
    reciprocity_failures = 0
    appearance_complete = 0
    canonical_complete = 0
    for row in ledger_rows:
        loc = str(row.get("occurrence_id") or "").strip()
        occurrence = by_loc.get(loc) if loc else None
        before = (
            row.get("appearance_count"),
            row.get("appearance_entry_relationships"),
            row.get("reverse_entry_relationship_present"),
        )
        if occurrence is not None:
            row["appearance_count"] = occurrence.get("appearance_count")
            row["appearance_entry_relationships"] = sorted(
                occurrence.get("entry_relationships") or []
            )
            row["reverse_entry_relationship_present"] = bool(
                _reverse_entry_present(occurrence, str(row.get("entry_id") or "").strip())
            )
        after = (
            row.get("appearance_count"),
            row.get("appearance_entry_relationships"),
            row.get("reverse_entry_relationship_present"),
        )
        if before != after:
            changed_rows += 1
        if row.get("reverse_entry_relationship_present"):
            reverse_complete += 1
        if loc and not row.get("reverse_entry_relationship_present"):
            reciprocity_failures += 1
        appearance_complete += bool(row.get("appearance_index_complete"))
        canonical_complete += bool(row.get("canonical_occurrence_trace_complete"))
        if occurrence is not None:
            # structural completeness is index-derived too; keep it honest
            complete = bool(_appearance_index_complete(occurrence))
            row["appearance_index_complete"] = complete
            row["canonical_occurrence_trace_complete"] = complete

    total_appearances = sum(
        int(record.get("appearance_count", 0)) for record in index_records
    )
    repeated_appearances = sum(
        max(0, int(record.get("appearance_count", 0)) - 1) for record in index_records
    )
    metrics["reverse_trace_complete_rows"] = reverse_complete
    metrics["entry_occurrence_reciprocity_failures"] = reciprocity_failures
    metrics["denominators"]["D4_total_appearances"] = total_appearances
    metrics["denominators"]["D4_repeated_appearances"] = repeated_appearances
    metrics["denominators"]["D4_unique_canonical_occurrences"] = len(index_records)
    metrics["appearance_index_complete_rows"] = sum(
        bool(row.get("appearance_index_complete")) for row in ledger_rows
    )
    metrics["canonical_occurrence_trace_complete_rows"] = sum(
        bool(row.get("canonical_occurrence_trace_complete")) for row in ledger_rows
    )
    return {
        "ledger_rows": len(ledger_rows),
        "changed_rows": changed_rows,
        "reverse_trace_complete_rows": reverse_complete,
        "entry_occurrence_reciprocity_failures": reciprocity_failures,
        "D4_total_appearances": total_appearances,
        "D4_repeated_appearances": repeated_appearances,
    }


def self_test():
    index = [{
        "loc": "7:40:17",
        "unique": True,
        "appearances": [
            {"surface_kind": "reader"},
            {"entry_id": "entry-jamal", "surface_kind": "entry_example"},
            {"entry_id": "entry-khayt", "surface_kind": "entry_example"},
        ],
        "appearance_count": 3,
        "entry_relationships": ["entry-jamal", "entry-khayt"],
        "projection_hash": "0" * 64,
    }]
    ledger = [{
        "occurrence_id": "7:40:17",
        "entry_id": "entry-jamal",
        "appearance_count": 2,
        "appearance_entry_relationships": ["entry-khayt"],
        "reverse_entry_relationship_present": False,
        "appearance_index_complete": True,
        "canonical_occurrence_trace_complete": True,
    }]
    metrics = {"denominators": {}}
    summary = reconcile(ledger, metrics, index)
    ok = (
        summary["changed_rows"] == 1
        and ledger[0]["reverse_entry_relationship_present"] is True
        and ledger[0]["appearance_count"] == 3
        and ledger[0]["appearance_entry_relationships"] == ["entry-jamal", "entry-khayt"]
        and metrics["entry_occurrence_reciprocity_failures"] == 0
        and metrics["denominators"]["D4_total_appearances"] == 3
    )
    print("VN LEDGER APPEARANCE RECONCILE SELF-TEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger")
    parser.add_argument("--metrics")
    parser.add_argument("--index")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not (args.ledger and args.metrics and args.index):
        parser.error("provide --ledger, --metrics and --index, or use --self-test")
    ledger_rows = _read_jsonl(args.ledger)
    with open(args.metrics, encoding="utf-8") as handle:
        metrics = json.load(handle)
    index_records = _read_jsonl(args.index)
    summary = reconcile(ledger_rows, metrics, index_records)
    with open(args.ledger, "w", encoding="utf-8", newline="\n") as handle:
        for row in ledger_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")
    with open(args.metrics, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
