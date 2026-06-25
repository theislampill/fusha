#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build index-miss reindex candidate list and owner-gated plan."""
import argparse
import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                             "pending-source-triangulation-table.jsonl")
DEFAULT_OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                           "index-miss-reindex-candidates.jsonl")
DEFAULT_PLAN = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                            "index-miss-reindex-plan.md")


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def classify(row):
    if row.get("qamus_entry_match_type") == "exact_form":
        return "exact_form_index_miss"
    return "existing_entry_form_family_review"


def build_plan(table_path=DEFAULT_TABLE, out_path=DEFAULT_OUT, plan_path=DEFAULT_PLAN,
               live_status="not_checked"):
    rows = []
    for row in read_jsonl(table_path):
        if row.get("root_cause") != "already_entry_form_present_index_miss":
            continue
        rows.append({
            "loc": row.get("loc"),
            "surface_ar": row.get("surface_ar") or "",
            "key": row.get("strict_nk") or row.get("nk") or "",
            "qamus_entry_candidate": row.get("qamus_entry_candidate"),
            "qamus_entry_headword": row.get("qamus_entry_headword"),
            "qamus_entry_match_type": row.get("qamus_entry_match_type"),
            "pos_agreement": row.get("pos_agreement"),
            "suggested_lane": row.get("suggested_lane"),
            "gate": row.get("gate"),
            "reindex_class": classify(row),
            "live_apply_gate": "owner",
            "safe_without_live_resolver_change": False,
            "required_check": "dry-run live resolver against this loc; keep homograph quarantine; require +N/-0/~0 diff",
            "blocker_if_not_resolved": row.get("blocker_if_not_resolved"),
        })
    rows.sort(key=lambda row: (row["reindex_class"], row["loc"] or ""))
    write_jsonl(out_path, rows)

    by_class = collections.Counter(row["reindex_class"] for row in rows)
    by_match = collections.Counter(row["qamus_entry_match_type"] for row in rows)
    by_lane = collections.Counter(row["suggested_lane"] for row in rows)
    summary = {
        "_generator": "tools/build_index_miss_reindex_plan.py",
        "source_table": os.path.relpath(table_path, ROOT),
        "candidates": os.path.relpath(out_path, ROOT),
        "candidate_rows": len(rows),
        "by_class": dict(sorted(by_class.items())),
        "by_match_type": dict(sorted(by_match.items())),
        "by_lane": dict(sorted(by_lane.items())),
        "live_status": live_status,
        "status": "owner_gated_not_applied",
    }

    os.makedirs(os.path.dirname(plan_path), exist_ok=True)
    lines = [
        "# Index-Miss Reindex Plan",
        "",
        "Owner-gated, not applied. This is resolver/index work, not new hover authoring.",
        "",
        "| metric | value |",
        "|---|---:|",
        "| candidate rows | %d |" % len(rows),
        "| exact-form index misses | %d |" % by_class.get("exact_form_index_miss", 0),
        "| existing-entry family review | %d |" % by_class.get("existing_entry_form_family_review", 0),
        "",
        "## Live Access Status",
        "",
        "`%s`" % live_status,
        "",
        "## Required Dry-Run",
        "",
        "1. Run the live resolver against each candidate without changing entry data.",
        "2. Split candidates into safe-relaxable vs correctly quarantined homograph/multi-root rows.",
        "3. Apply only owner-approved resolver changes with diff `+N / -0 / ~0`.",
        "4. Rebuild, health-check, and regenerate the hover audit before claiming coverage.",
        "",
        "Public provenance remains unchanged: `src=qamus`, `kind=authored`.",
    ]
    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-table", default=DEFAULT_TABLE)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--plan", default=DEFAULT_PLAN)
    parser.add_argument("--live-status", default="not_checked")
    args = parser.parse_args()
    summary = build_plan(args.from_table, args.out, args.plan, args.live_status)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
