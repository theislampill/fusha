#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED fixture for QAMUS-RICH-SEG-001 — 83:26:5 «فَلْيَتَنَافَسِ».

This is a DOM-free data/assertion fixture. It runs one completeness battery over two
payloads and proves the collapse is real:

  - against the current public-equivalent [FA, STEM] payload the battery MUST FAIL
    (the imperative lām لْ and the imperfect prefix يَ are swallowed by the STEM);
  - against the corrected 4-segment record the battery MUST PASS.

The battery asserts, per the ANDON:
  surface preservation · exact address · فَ role · imperative لـ role · imperfect verb
  prefix · Form VI · active · jussive · 3ms · governor relation from the imperative lām ·
  learner contributions so/then / let / compete-strive · atomic Arabic textContent ·
  separate tooltip rows.

Fails closed (exit 1) unless the malformed payload is RED and the corrected payload is GREEN.

Run: python tools/test_rich_seg_83_26_5.py
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.validate_segment_completeness import (  # noqa: E402
    build_correct_record, build_malformed_record, SURFACE_83_26_5,
)

WS = set(" \t\n\r ")


def _seg_by_role(rec, role):
    return [s for s in (rec.get("segments") or []) if s.get("role") == role]


def battery(rec):
    """Return a list of failure strings. Empty == the record is complete and correct."""
    f = []
    sarf = rec.get("sarf") or {}
    nahw = rec.get("nahw") or {}
    segs = rec.get("segments") or []
    display_segs = ((rec.get("display") or {}).get("segments")) or []

    # 1. surface preservation — segments concatenate to the exact written token.
    joined = "".join(s.get("surface", "") for s in segs)
    if joined != rec.get("surface") or rec.get("surface") != SURFACE_83_26_5:
        f.append("surface not preserved: segments join to %r, surface=%r" % (joined, rec.get("surface")))

    # 2. exact address.
    if rec.get("loc") != "83:26:5":
        f.append("loc must be 83:26:5")
    if rec.get("wbw_loc") != "wbw:83:26:5":
        f.append("wbw_loc must be wbw:83:26:5")

    # 3. فَ resumption role, contributing so/then.
    fa = _seg_by_role(rec, "prefix_resumption_fa")
    if not fa:
        f.append("missing فَ resumption segment (prefix_resumption_fa)")
    elif "so" not in (fa[0].get("gloss_contribution") or "").lower():
        f.append("فَ must contribute so/then")

    # 4. imperative لـ role, contributing let.
    lam = _seg_by_role(rec, "prefix_imperative_lam")
    if not lam:
        f.append("missing imperative lām segment (prefix_imperative_lam)")
    elif "let" not in (lam[0].get("gloss_contribution") or "").lower():
        f.append("imperative lām must contribute let")

    # 5. imperfect verb prefix يَ.
    pfx = _seg_by_role(rec, "verb_prefix")
    if not pfx:
        f.append("missing imperfect verb prefix segment (verb_prefix)")

    # 6-9. sarf facts: Form VI, active, jussive, 3ms.
    if sarf.get("verb_form") != "VI":
        f.append("verb_form must be VI (got %r)" % sarf.get("verb_form"))
    if sarf.get("voice") != "active":
        f.append("voice must be active (got %r)" % sarf.get("voice"))
    if sarf.get("mood") != "jussive":
        f.append("mood must be jussive (got %r)" % sarf.get("mood"))
    if not (sarf.get("person") == "3" and sarf.get("number") == "singular"
            and sarf.get("gender") == "masculine"):
        f.append("agreement must be 3ms (got person=%r number=%r gender=%r)"
                 % (sarf.get("person"), sarf.get("number"), sarf.get("gender")))

    # 10. governor relation from the imperative lām.
    if nahw.get("governed_by") != "imperative_lam":
        f.append("nahw.governed_by must be imperative_lam (got %r)" % nahw.get("governed_by"))

    # 11. learner contributions so/then, let, compete/strive present.
    contribs = " ".join((s.get("gloss_contribution") or "") for s in segs).lower()
    must = ["so", "let", "compete"]
    for token in must:
        if token not in contribs:
            f.append("learner contribution %r missing from segment glosses" % token)

    # 12. atomic Arabic textContent — the visible token carries no whitespace (renderer safety proxy).
    if any(ch in WS for ch in (rec.get("surface") or "")):
        f.append("surface must be a single atomic Arabic run (no whitespace)")
    if any(any(ch in WS for ch in (s.get("surface") or "")) for s in segs):
        f.append("segment surfaces must be whitespace-free")

    # 13. separate tooltip rows — one display row per segment, all four grammatical pieces distinct.
    if len(display_segs) != len(segs):
        f.append("display rows must align 1:1 with segments (%d rows vs %d segments)"
                 % (len(display_segs), len(segs)))
    if len(segs) < 4:
        f.append("must expose four separate tooltip rows (فَ · لْ · يَ · stem); got %d" % len(segs))

    return f


def main():
    correct = build_correct_record()
    malformed = build_malformed_record()

    red = battery(malformed)
    green = battery(correct)

    print("RED  (current [FA, STEM] payload): %d battery failures" % len(red))
    for r in red:
        print("       - " + r)
    print("GREEN (corrected 4-segment record): %d battery failures" % len(green))
    for g in green:
        print("       - " + g)

    problems = []
    if not red:
        problems.append("expected the malformed [FA, STEM] payload to FAIL the battery, but it passed")
    else:
        # The collapse must be caught specifically: swallowed lām, swallowed prefix, lost Form VI/jussive.
        joined = " ".join(red)
        for needle in ("imperative lām", "verb prefix", "verb_form must be VI", "mood must be jussive"):
            if needle not in joined:
                problems.append("malformed payload did not fail on the expected symptom: %r" % needle)
    if green:
        problems.append("expected the corrected record to PASS the battery, but it failed: %s" % green)

    if problems:
        print("FAIL:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("PASS - 83:26:5 red fixture: [FA, STEM] is RED, the corrected 4-segment record is GREEN")


if __name__ == "__main__":
    main()
