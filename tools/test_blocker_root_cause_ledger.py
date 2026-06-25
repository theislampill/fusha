#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for blocker-root-cause safe-tier classification."""
import json
from pathlib import Path

import build_blocker_root_cause_ledger as ledger


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "qamus/reports/closure-2092/blocker-root-cause-ledger.jsonl"


def rows():
    out = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("loc"):
            continue
        out[row["loc"]] = row
    return out


def main():
    assert "جيء" in ledger.root_key_variants("جيأ")
    data = rows()
    for loc in ("9:7:4", "14:5:2", "17:7:6"):
        if loc in data:
            assert data[loc].get("safe_tier") != "A_safe", (loc, data[loc])
    if "19:43:4" in data:
        assert data["19:43:4"].get("root_entry") == "484b4fb9beba", data["19:43:4"]
        assert data["19:43:4"].get("root_cause") == "already_entry_form_present_index_miss", data["19:43:4"]
        assert data["19:43:4"].get("safe_tier") is None, data["19:43:4"]
    for row in data.values():
        if row.get("safe_tier") == "A_safe":
            assert row.get("qac_surface_match") is True, row
            assert row.get("qac_loc_surface_conflict") is False, row
            assert row.get("qac_pos") == "V", row
    print("PASS blocker-root-cause safe-tier regressions")


if __name__ == "__main__":
    main()
