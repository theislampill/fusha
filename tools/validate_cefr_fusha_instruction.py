#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_cefr_fusha_instruction — conformance gate for the CEFR-aligned Fusha instruction levels (P2b).

CEFR here is SCAFFOLDING, NEVER CERTIFICATION. Each level record (curriculum/cefr-fusha-levels.json) is validated against
qamus/schemas/cefr-fusha-level.schema.json, then the FAIL conditions:

  CEFR-1  level off the 7-value enum.
  CEFR-2  a certification / assessment OVERCLAIM in any field except forbidden_overclaims (which legitimately names what
          must NOT be claimed). Guards "claiming official CEFR assessment".
  CEFR-3  a descriptor / note that trips leak_sot.scan(), OR a suspiciously long (likely copied) descriptor — authored
          adaptations are short and original; CoE descriptor prose is never reproduced.
  CEFR-4  a BEGINNER band (pre_A1/A1/A2) whose metalanguage_exposure is not none|minimal, OR whose diagnostic_visibility
          lists an iʿrāb-sensitive class. Guards "dumping C2 iʿrāb terminology on A1 learners".
  CEFR-5  forbidden_overclaims empty (every level must enumerate what it must NOT claim).
  CEFR-6  an enum field (metalanguage_exposure / correction_aggressiveness / hint_depth / example_difficulty) off its set.
  CEFR-7  public_boundary const violated (not source-clean).

CLI: python3 tools/validate_cefr_fusha_instruction.py [levels.json] | --self-test. Stdlib only; exit non-zero on any violation.
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools.validate_linguistic_decisions import validate_schema  # noqa: E402
from tools import leak_sot  # noqa: E402
from tools.fusha_check import IRAB_SENSITIVE_ISSUE_CLASSES  # noqa: E402

SCHEMA_PATH = os.path.join(_REPO, "qamus", "schemas", "cefr-fusha-level.schema.json")
LEVELS_PATH = os.path.join(_REPO, "curriculum", "cefr-fusha-levels.json")
_SCHEMA = json.load(open(SCHEMA_PATH, encoding="utf-8"))
_LEVELS = set(_SCHEMA["properties"]["level"]["enum"])
_META = set(_SCHEMA["properties"]["metalanguage_exposure"]["enum"])
_AGGR = set(_SCHEMA["properties"]["correction_aggressiveness"]["enum"])
_DEPTH = set(_SCHEMA["properties"]["hint_depth"]["enum"])
_DIFF = set(_SCHEMA["properties"]["example_difficulty"]["enum"])
_BEGINNER = {"pre_A1", "A1", "A2"}
# a certification / assessment OVERCLAIM (CEFR is a scaffold, not a certificate). Broad on purpose: this layer never
# assesses or certifies, so ANY assess*/certif* form, a CEFR-certificate phrase, or a guarantee-a-level claim is forbidden.
_CERT_RE = re.compile(r"\bcertif\w*\b|official\s+cefr|cefr\s+certificate|\bassess\w*\b|proficiency\s+certificate"
                      r"|guarantee[^.]*\blevel\b|\baccredit\w*\b", re.I)
_MAX_DESCRIPTOR_LEN = 280  # authored adaptations are short; a long run smells like copied CoE prose


def _text_fields(rec):
    """Every authored string field EXCEPT forbidden_overclaims (which legitimately states the negatives)."""
    yield "arabic_adaptation_note", rec.get("arabic_adaptation_note", "") or ""
    for k, v in (rec.get("descriptors") or {}).items():
        yield "descriptors.%s" % k, v or ""
    for c in rec.get("learner_capabilities") or []:
        yield "learner_capabilities", c or ""


def validate_level(rec):
    errors = []
    lvl = rec.get("level", "?")
    for e in validate_schema(rec, _SCHEMA):
        errors.append(("schema", "%s: %s" % (lvl, e)))
    # CEFR-1
    if rec.get("level") not in _LEVELS:
        errors.append(("CEFR-1", "%s: level off the 7-value enum" % lvl))
    # CEFR-2: certification overclaim (excluding forbidden_overclaims)
    for label, s in _text_fields(rec):
        if _CERT_RE.search(s):
            errors.append(("CEFR-2", "%s: %s makes a CEFR certification/assessment overclaim" % (lvl, label)))
    # CEFR-3: leak or copied-prose
    for label, s in _text_fields(rec):
        if leak_sot.is_leak(s):
            errors.append(("CEFR-3", "%s: %s leaks a source/provenance/path string" % (lvl, label)))
        if len(s) > _MAX_DESCRIPTOR_LEN:
            errors.append(("CEFR-3", "%s: %s is suspiciously long (likely copied descriptor prose)" % (lvl, label)))
    # CEFR-4: beginner bands must stay free of heavy metalanguage / iʿrāb-sensitive diagnostics
    if rec.get("level") in _BEGINNER:
        if rec.get("metalanguage_exposure") not in ("none", "minimal"):
            errors.append(("CEFR-4", "%s: a beginner band exposes %r metalanguage" % (lvl, rec.get("metalanguage_exposure"))))
        for c in rec.get("diagnostic_visibility") or []:
            if c in IRAB_SENSITIVE_ISSUE_CLASSES:
                errors.append(("CEFR-4", "%s: a beginner band surfaces the iʿrāb-sensitive class %r" % (lvl, c)))
    # CEFR-5
    if not (rec.get("forbidden_overclaims") or []):
        errors.append(("CEFR-5", "%s: forbidden_overclaims is empty" % lvl))
    # CEFR-6
    if rec.get("metalanguage_exposure") not in _META:
        errors.append(("CEFR-6", "%s: metalanguage_exposure off-set" % lvl))
    if rec.get("correction_aggressiveness") not in _AGGR:
        errors.append(("CEFR-6", "%s: correction_aggressiveness off-set" % lvl))
    if rec.get("hint_depth") not in _DEPTH:
        errors.append(("CEFR-6", "%s: hint_depth off-set" % lvl))
    if rec.get("example_difficulty") not in _DIFF:
        errors.append(("CEFR-6", "%s: example_difficulty off-set" % lvl))
    # CEFR-7
    pb = rec.get("public_boundary") or {}
    if pb.get("public_gloss_src") != "qamus" or pb.get("external_source_names_public") is not False:
        errors.append(("CEFR-7", "%s: public_boundary not source-clean" % lvl))
    return errors


def validate_file(path):
    levels = json.load(open(path, encoding="utf-8"))
    n, errs = 0, []
    for rec in levels:
        n += 1
        errs.extend(validate_level(rec))
    return n, errs


def _bad_levels():
    base = json.load(open(LEVELS_PATH, encoding="utf-8"))
    c2 = next(r for r in base if r["level"] == "C2")
    a1 = next(r for r in base if r["level"] == "A1")
    out = []
    b = json.loads(json.dumps(c2)); b["level"] = "C3"
    out.append(("CEFR-1", b))
    b = json.loads(json.dumps(c2)); b["descriptors"]["grammar"] = "Learner is officially assessed at CEFR level C2."
    out.append(("CEFR-2", b))
    b = json.loads(json.dumps(c2)); b["descriptors"]["reading"] = "see the QAC tagset at /srv/data"
    out.append(("CEFR-3", b))
    b = json.loads(json.dumps(a1)); b["diagnostic_visibility"] = ["weak_irab_reasoning"]
    out.append(("CEFR-4", b))
    b = json.loads(json.dumps(a1)); b["metalanguage_exposure"] = "full"
    out.append(("CEFR-4", b))
    b = json.loads(json.dumps(c2)); b["forbidden_overclaims"] = []
    out.append(("CEFR-5", b))
    b = json.loads(json.dumps(c2)); b["hint_depth"] = "give_answer"
    out.append(("CEFR-6", b))
    b = json.loads(json.dumps(c2)); b["public_boundary"]["external_source_names_public"] = True
    out.append(("CEFR-7", b))
    return out


def _self_test():
    failures = []
    n, errs = validate_file(LEVELS_PATH)
    if n != 7:
        failures.append("expected 7 authored levels, found %d" % n)
    if errs:
        failures.append("authored levels should validate clean but: %s" % errs[:3])
    for cond, rec in _bad_levels():
        conds = {c for c, _ in validate_level(rec)}
        if cond not in conds:
            failures.append("bad level should trip %s but tripped %s" % (cond, sorted(conds)))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_cefr_fusha_instruction self-test: 7 authored levels clean; CEFR-1..7 reject (no certification, no copied prose, beginner-safe)")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate the CEFR-aligned Fusha instruction levels (scaffold, not certification).")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    path = a.path or LEVELS_PATH
    n, errs = validate_file(path)
    for cond, msg in errs:
        print("FAIL [%s] %s" % (cond, msg))
    print("checked %d level(s), %d violation(s)" % (n, len(errs)))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
