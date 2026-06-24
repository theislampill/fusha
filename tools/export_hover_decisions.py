#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 — export 2-vote-confirmed authored-gloss decisions to the qamus_wbw hover payload.

Reads a JSONL of authored decisions ({norm_strict, surface, decision, gloss_en, confidence, confirmed?}) and
emits `fusha-hover-decisions.tsv` (`norm_strict<TAB>gloss`) — the surface-keyed authoring layer the live
expand.py `fusha` pass reads. ONLY decision=='authored_gloss' rows that are confirmed (or --no-verify) export.

Public-safety guards (assert, abort on violation):
  * the gloss carries no external-source name / informed_by / provenance text;
  * no Arabic homograph that the verifier rejected;
  * output is just surface→gloss (no src/provenance keys — expand.py stamps src=qamus).
"""
import argparse
import io
import json
import re
import sys

BANNED = re.compile(r"informed_by|quran\.com|corpus\.quran|tanzil|\bqac\b|data-prov|/srv/|/static/", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", required=True, help="JSONL of authored decisions")
    ap.add_argument("--out", required=True, help="output fusha-hover-decisions.tsv")
    ap.add_argument("--no-verify", action="store_true", help="export even unconfirmed (NOT for live)")
    ap.add_argument("--min-conf", default="medium", choices=["high", "medium", "low"])
    a = ap.parse_args()
    order = {"high": 3, "medium": 2, "low": 1}
    seen = {}
    exported = skipped = 0
    for line in io.open(a.decisions, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        ns, gloss = d.get("norm_strict"), (d.get("gloss_en") or "").strip()
        if d.get("decision") != "authored_gloss" or not ns or not gloss:
            skipped += 1
            continue
        if not (a.no_verify or d.get("confirmed")):
            skipped += 1
            continue
        if order.get(d.get("confidence", "low"), 1) < order[a.min_conf]:
            skipped += 1
            continue
        assert not BANNED.search(gloss), "ABORT: gloss would leak provenance/path: %r" % gloss
        assert "\t" not in gloss and "\n" not in gloss, "gloss must be single-line"
        # keep the highest-confidence gloss per surface
        if ns not in seen or order[d.get("confidence", "low")] > seen[ns][1]:
            seen[ns] = (gloss, order.get(d.get("confidence", "low"), 1))
    with io.open(a.out, "w", encoding="utf-8") as f:
        for ns, (gloss, _) in sorted(seen.items()):
            f.write("%s\t%s\n" % (ns, gloss))
            exported += 1
    print("exported %d surface→gloss rows (skipped %d); out=%s" % (exported, skipped, a.out))


if __name__ == "__main__":
    main()
