#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for index-miss reindex candidate/plan generation."""
import json
import tempfile
from pathlib import Path

import build_index_miss_reindex_plan as B


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        table = root / "table.jsonl"
        out = root / "candidates.jsonl"
        plan = root / "plan.md"
        write_jsonl(table, [
            {
                "loc": "2:2:2",
                "surface_ar": "ذَهَبَ",
                "strict_nk": "ذهب",
                "root_cause": "already_entry_form_present_index_miss",
                "qamus_entry_candidate": "abc",
                "qamus_entry_headword": "ذَهَبَ",
                "qamus_entry_match_type": "exact_form",
                "pos_agreement": "agree",
                "suggested_lane": "form_variant",
                "gate": "two_vote",
                "blocker_if_not_resolved": "already_entry_form_present_index_miss: requires resolver review",
            },
            {"loc": "2:2:3", "root_cause": "other"},
        ])
        summary = B.build_plan(str(table), str(out), str(plan), live_status="blocked_host_key")
        assert summary["candidate_rows"] == 1
        row = json.loads(out.read_text(encoding="utf-8").strip())
        assert row["live_apply_gate"] == "owner"
        assert row["reindex_class"] == "exact_form_index_miss"
        assert "blocked_host_key" in plan.read_text(encoding="utf-8")
    print("index-miss reindex plan self-test OK")


if __name__ == "__main__":
    main()
