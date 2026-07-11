#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate per-loc iʿrāb token decisions before apply (fail-closed).

Each decision must: have a valid quran loc (S:A:W), a non-empty authored gloss, public record
exactly {src:qamus, kind:authored}, NO public provenance leak (no source name / informed_by in the
PUBLIC fields), and a recorded internal provenance (separate). Any case/mood claim must additionally
carry non-empty reasoning and a gate of at least two_vote_required. Usage:
  python3 tools/validate_token_irab_decisions.py <decisions.jsonl>
"""
import json, re, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LOC = re.compile(r"^\d+:\d+:\d+$")
LEAK = re.compile(r"(tafsir|mcp|quran\.?com|tanzil|qac|informed_by|/srv/|/tmp/)", re.I)
PUBLIC_FIELDS = ("loc", "gloss", "surface", "key", "state_id", "src", "kind", "lang", "decision_state")
ACCEPTED_CASE_GATES = {"two_vote", "two_vote_required", "human_source_review_required", "never_auto", "never_auto_resolve"}


def _case_mood_claim(d):
    direct = ("case", "mood", "case_mood", "claimed_case", "claimed_mood", "claimed_case_mood")
    if any(d.get(key) not in (None, "", "unknown") for key in direct):
        return True
    irab = d.get("irab")
    return isinstance(irab, dict) and any(irab.get(key) not in (None, "", "unknown") for key in ("case", "mood", "case_mood", "mabni"))


def validate_decision(d, row_number):
    errs = []
    if not LOC.match(d.get("loc", "")): errs.append(f"{row_number}: bad loc {d.get('loc')!r}")
    if not (d.get("gloss") or "").strip(): errs.append(f"{row_number}: empty gloss")
    if d.get("src") != "qamus" or d.get("kind") != "authored":
        errs.append(f"{row_number}: public record not {{src:qamus,kind:authored}}")
    pub_blob = json.dumps({k: d.get(k) for k in PUBLIC_FIELDS if k in d}, ensure_ascii=False)
    if LEAK.search(pub_blob): errs.append(f"{row_number}: provenance leak in public fields")
    if not isinstance(d.get("internal_provenance"), dict): errs.append(f"{row_number}: missing internal_provenance")
    if _case_mood_claim(d):
        irab = d.get("irab") if isinstance(d.get("irab"), dict) else {}
        reasoning = d.get("reasoning") or d.get("nahw_reasoning") or d.get("claimed_reasoning") or irab.get("reasoning")
        if not isinstance(reasoning, str) or not reasoning.strip():
            errs.append(f"{row_number}: case/mood claim missing reasoning")
        gate = d.get("gate") or d.get("required_gate") or irab.get("gate")
        if gate not in ACCEPTED_CASE_GATES:
            errs.append(f"{row_number}: case/mood claim gate below two_vote_required (got {gate!r})")
    return errs

def main():
    path = sys.argv[1]
    errs = []; n = 0
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line: continue
        n += 1
        d = json.loads(line)
        errs.extend(validate_decision(d, i))
    print(f"checked {n} iʿrāb decisions")
    if errs:
        print(f"FAIL ({len(errs)}):"); [print("  -", e) for e in errs[:20]]; sys.exit(1)
    print("VALIDATE OK — iʿrāb token decisions public-safe and reasoning-gated")

if __name__ == "__main__":
    main()
