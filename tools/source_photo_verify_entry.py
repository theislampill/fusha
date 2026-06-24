#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify a live Qamus entry field against a value read from its source photo. READ-ONLY decision helper.

The visual read (by a human or a vision model) is the AUTHORITY; this tool just records the comparison and the
certification verdict for a field, producing a repair-candidate row when live != source. It does NOT mutate the
live store (entry repair goes through the owner-gated edit_entry_record path).

Usage (programmatic): verify_field(entry_id, field, live_value, source_value) -> {match, verdict, ...}
CLI self-test: python tools/source_photo_verify_entry.py --self-test
"""
import json
import sys


def verify_field(entry_id, field, live_value, source_value, source_ref=None):
    match = str(live_value).strip() == str(source_value).strip()
    return {
        "entry_id": entry_id, "field": field,
        "live_value": live_value, "source_value": source_value,
        "source_ref": source_ref,
        "match": match,
        "verdict": "verified_correct" if match else "repair_candidate",
        "certified_from": "existing_source_photo",
    }


def _selftest():
    # the live ب ي ن total_uses (523) matches the photo's "523" -> verified_correct
    r = verify_field("df6af97d5e93", "total_uses", 523, "523", "intake_13/IMG_7784.jpeg")
    assert r["match"] and r["verdict"] == "verified_correct", r
    # a mismatch -> repair_candidate
    r2 = verify_field("x", "total_uses", 100, "101", "pgNNN")
    assert (not r2["match"]) and r2["verdict"] == "repair_candidate", r2
    print("PASS — verify_field: ب ي ن total_uses 523==523 verified; mismatch -> repair_candidate")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _selftest()
    else:
        print("use --self-test or import verify_field()")
