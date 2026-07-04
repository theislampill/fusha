#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate hover-row renderer completeness - no silent renderer gaps (FUSHA plan P1-D).

A public hover row is "renderer-complete" only when the renderer has everything it
needs to draw every segment with no silent gap. Repeated live failures were
stem-only hovers, dropped clitics, and a morphline out of sync with the segments -
each renders "plausibly" while hiding a piece. This gate FAILs those.

Enforced per row (public_payload):
  - every segment has a role in the allowed set, and a NON-empty surface, gloss, qg_class;
  - segment surfaces concatenate EXACTLY to the visible surface (no dropped/hidden piece);
  - morphline, when present, has one role-token per segment IN ORDER (renderer + segments
    cannot silently disagree);
  - learner_explanation is present (the renderer's fallback text);
  - public fields stay source-clean (reuses the canonical FORBIDDEN_LABELS).

Additive; dry-run; deterministic; source-clean. Touches no existing data - it is the
contract the projection/compiler output is validated against. No live Qamus is read.
See FUSHA_TRANSCLUSION_P0_P1_P2_PLAN P1-D (fablehardening).
"""
import argparse
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.validate_public_private_boundary import FORBIDDEN_LABELS  # noqa: E402

ROLES = {"ART", "PFX", "STEM", "SUFF", "POSS", "OBJ", "PART", "N", "V", "FUNC"}


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_row(row):
    e = []
    if not isinstance(row, dict):
        return ["hover row must be a JSON object"]
    pp = row.get("public_payload")
    if not isinstance(pp, dict):
        return ["public_payload object is required"]
    segs = pp.get("segments")
    if not isinstance(segs, list) or not segs:
        return ["public_payload.segments must be a non-empty array (renderer gap)"]
    for i, s in enumerate(segs):
        if not isinstance(s, dict):
            e.append("segment[%d] must be an object" % i); continue
        if s.get("role") not in ROLES:
            e.append("segment[%d] role %r not in allowed renderer roles" % (i, s.get("role")))
        for f in ("surface", "gloss", "qg_class"):
            if not (str(s.get(f) or "")).strip():
                e.append("segment[%d] %s must be non-empty (silent renderer gap)" % (i, f))
    surface = row.get("surface") or row.get("surface_norm") or row.get("visible_surface")
    concat = "".join(str(s.get("surface", "")) for s in segs)
    if surface is not None and concat != surface:
        e.append("segment surfaces %r must concatenate exactly to visible surface %r "
                 "(dropped/hidden segment)" % (concat, surface))
    morphline = pp.get("morphline")
    if morphline:
        parts = [p for p in str(morphline).replace("-", "+").split("+") if p]
        if len(parts) != len(segs):
            e.append("morphline has %d role-tokens but %d segments (renderer/segments out of sync)"
                     % (len(parts), len(segs)))
        else:
            for i, (p, s) in enumerate(zip(parts, segs)):
                if p.strip().upper() != str(s.get("role", "")).strip().upper():
                    e.append("morphline[%d]=%r disagrees with segment role %r"
                             % (i, p, s.get("role")))
    if not str(pp.get("learner_explanation") or "").strip():
        e.append("learner_explanation must be present (renderer fallback text)")
    blob = json.dumps(pp, ensure_ascii=False).lower()
    for label in FORBIDDEN_LABELS:
        if label in blob:
            e.append("public_payload leaks forbidden label %r" % label)
    return e


def validate_rows(rows):
    errors = []
    for i, row in enumerate(rows):
        for m in validate_row(row):
            errors.append("row[%d]: %s" % (i, m))
    return errors


def _good():
    return {
        "surface": "الكتاب",
        "public_payload": {
            "src": "qamus", "kind": "authored", "lang": "en",
            "token_contribution_gloss": "the book", "morphline": "ART+STEM",
            "segments": [
                {"role": "ART", "surface": "ال", "qg_class": "definite_article", "gloss": "the"},
                {"role": "STEM", "surface": "كتاب", "qg_class": "noun", "gloss": "book"},
            ],
            "learner_explanation": "definite article + noun",
        },
    }


def self_test():
    g = _good()
    if validate_row(g):
        print("SELF-TEST FAIL good:", validate_row(g)); return 1
    # FAIL: empty segment gloss (stem-only-style gap)
    bad = _good(); bad["public_payload"]["segments"][1]["gloss"] = ""
    if not any("non-empty" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL empty-gloss not caught"); return 1
    # FAIL: dropped segment (concat mismatch)
    bad = _good(); bad["public_payload"]["segments"].pop()
    bad["public_payload"]["morphline"] = "ART"
    if not any("concatenate exactly" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL dropped-segment not caught"); return 1
    # FAIL: morphline/segments length mismatch
    bad = _good(); bad["public_payload"]["morphline"] = "ART+STEM+SUFF"
    if not any("out of sync" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL morphline-length not caught"); return 1
    # FAIL: morphline role disagreement
    bad = _good(); bad["public_payload"]["morphline"] = "PFX+STEM"
    if not any("disagrees with segment role" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL morphline-role not caught"); return 1
    # FAIL: bad role
    bad = _good(); bad["public_payload"]["segments"][0]["role"] = "XYZ"
    if not any("not in allowed renderer roles" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL bad-role not caught"); return 1
    # FAIL: missing learner_explanation
    bad = _good(); bad["public_payload"]["learner_explanation"] = ""
    if not any("learner_explanation" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL missing-explanation not caught"); return 1
    # FAIL: leak
    bad = _good(); bad["public_payload"]["segments"][1]["gloss"] = "book (tafsir)"
    if not any("forbidden label" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL leak not caught"); return 1
    print("PASS - renderer completeness gate self-test")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Validate hover-row renderer completeness.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        ap.error("path is required unless --self-test")
    errors = validate_rows(read_jsonl(args.path))
    if errors:
        print("FAIL:")
        for e in errors[:80]:
            print("  - " + e)
        raise SystemExit(1)
    print("PASS - hover rows are renderer-complete and source-clean")


if __name__ == "__main__":
    main()
