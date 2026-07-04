#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate certified-lemma rows and the fanout gates they authorize (steps 1-2).

This guard exists because RH-LIVE rollout proved two OPPOSITE failure modes:
solved tokens that failed to fan out to obvious peers, AND weak surface-only /
stem-only hovers that fanned out to the wrong occurrence. The answer is neither
"fan out every same surface" nor "never fan out": it is CERTIFIED fanout.

Hard properties enforced here (not just the schema):
  1. lemma_id is content-addressed (lemma:sha256[:16] over lemma_ar+root+pos+pattern);
     a wrong id FAILs, and two distinct-meaning homographs (mIn vs man) get DIFFERENT
     ids by construction, so they cannot collide on one identity.
  2. fanout_allowed=true is impossible unless certification_status=certified.
  3. a particle may fan out only via source_address_exact or function_context,
     never lemma_pattern_pos alone (particles are function/context-sensitive).
  4. surface-only fanout is impossible: there is no surface-only gate value, and a
     legacy `never_surface_only` value FAILs the closed enum.
  5. public fields (lemma_ar/root/pos/pattern/fanout_gate) stay source-clean; QAC/MCP
     and other external labels never leak (reuses the canonical FORBIDDEN_LABELS list).
  6. fanout_allowed requires public_safe=true.

Dry-run; deterministic; source-clean. No live Qamus is inspected or mutated.
See CERTIFIED_LEMMA_GATED_FANOUT_PLAN (fablehardening) + its second-pass addendum.
"""
import argparse
import hashlib
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "qamus", "schemas", "certified-lemma.schema.json")
SAMPLE_PATH = os.path.join(ROOT, "qamus", "examples", "certified_lemma.sample.jsonl")

sys.path.insert(0, ROOT)
from tools.validate_public_private_boundary import FORBIDDEN_LABELS  # noqa: E402

PUBLIC_FIELDS = ("lemma_ar", "root", "pos", "pattern", "fanout_gate")

# Enums + required fields are read FROM the schema so schema and validator cannot drift
# (the repo mini-validator does not fully cover draft-2020-12; explicit checks are the gate).
with io.open(SCHEMA_PATH, encoding="utf-8") as _h:
    _SCHEMA = json.load(_h)
REQUIRED = _SCHEMA["required"]
_PROPS = _SCHEMA["properties"]
ENUMS = {k: _PROPS[k]["enum"] for k in ("pos", "certification_status", "source_scope", "fanout_gate")}


def compute_lemma_id(row):
    canonical = json.dumps(
        {
            "lemma_ar": row.get("lemma_ar"),
            "root": row.get("root"),
            "pos": row.get("pos"),
            "pattern": row.get("pattern"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "lemma:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_row(row):
    errors = []
    if not isinstance(row, dict):
        return ["certified-lemma row must be a JSON object"]

    # explicit structural checks (schema-derived; the mini-validator is unreliable here)
    for field in REQUIRED:
        if field not in row:
            errors.append("missing required field %r" % field)
    if row.get("schema") != "qamus.certified_lemma.v1":
        errors.append("schema must be 'qamus.certified_lemma.v1'")
    for key, allowed in ENUMS.items():
        if key in row and row.get(key) not in allowed:
            errors.append("%s=%r not in enum %s" % (key, row.get(key), allowed))
    for boolean in ("public_safe", "fanout_allowed"):
        if boolean in row and not isinstance(row.get(boolean), bool):
            errors.append("%s must be a boolean" % boolean)
    extra = set(row) - set(_PROPS)
    if extra:
        errors.append("unexpected field(s): %s" % sorted(extra))

    expected_id = compute_lemma_id(row)
    if row.get("lemma_id") != expected_id:
        errors.append(
            "lemma_id must be content-addressed %r (got %r)" % (expected_id, row.get("lemma_id"))
        )

    if row.get("fanout_allowed") is True and row.get("certification_status") != "certified":
        errors.append("fanout_allowed=true requires certification_status=certified")

    if row.get("fanout_allowed") is True and row.get("public_safe") is not True:
        errors.append("fanout_allowed=true requires public_safe=true")

    if (
        row.get("pos") == "particle"
        and row.get("fanout_allowed") is True
        and row.get("fanout_gate") not in ("source_address_exact", "function_context")
    ):
        errors.append(
            "particle fanout requires source_address_exact or function_context gate, "
            "not lemma_pattern_pos (particles are function/context-sensitive)"
        )

    public_blob = json.dumps(
        {k: row.get(k) for k in PUBLIC_FIELDS}, ensure_ascii=False
    ).lower()
    for label in FORBIDDEN_LABELS:
        if label in public_blob:
            errors.append("public field leaks forbidden label %r" % label)
    return errors


def validate_rows(rows):
    errors = []
    for index, row in enumerate(rows):
        for err in validate_row(row):
            errors.append("row[%d]: %s" % (index, err))
    # batch homograph-collision guard: one lemma_id must map to one (lemma_ar,pos,root)
    identity = {}
    for index, row in enumerate(rows):
        lid = row.get("lemma_id")
        sig = (row.get("lemma_ar"), row.get("pos"), row.get("root"), row.get("pattern"))
        if lid in identity and identity[lid] != sig:
            errors.append(
                "row[%d]: lemma_id %r collides on two distinct meanings %r vs %r "
                "(homograph over-grouping)" % (index, lid, identity[lid], sig)
            )
        else:
            identity[lid] = sig
    return errors


def _good_noun():
    row = {
        "schema": "qamus.certified_lemma.v1",
        "lemma_ar": "كِتاب",
        "root": "كتب",
        "pos": "noun",
        "pattern": "فِعال",
        "certification_status": "certified",
        "source_scope": "qamus_entry",
        "public_safe": True,
        "evidence_private": [],
        "fanout_allowed": True,
        "fanout_gate": "lemma_pattern_pos",
    }
    row["lemma_id"] = compute_lemma_id(row)
    return row


def self_test():
    good = _good_noun()
    errors = validate_row(good)
    if errors:
        print("SELF-TEST FAIL good noun:", errors)
        return 1

    # good: exact-loc particle (source_address_exact is always safe, even for particles)
    good_prep = {
        "schema": "qamus.certified_lemma.v1",
        "lemma_ar": "مِن",  # min (preposition)
        "root": None,
        "pos": "particle",
        "pattern": None,
        "certification_status": "certified",
        "source_scope": "qamus_entry",
        "public_safe": True,
        "evidence_private": [],
        "fanout_allowed": True,
        "fanout_gate": "source_address_exact",
    }
    good_prep["lemma_id"] = compute_lemma_id(good_prep)
    if validate_row(good_prep):
        print("SELF-TEST FAIL good particle:", validate_row(good_prep))
        return 1

    # FAIL: uncertified fanout
    bad = _good_noun()
    bad["certification_status"] = "candidate"
    if not any("requires certification_status=certified" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL uncertified-fanout not caught")
        return 1

    # FAIL: particle gated only by lemma_pattern_pos
    bad = dict(good_prep)
    bad["fanout_gate"] = "lemma_pattern_pos"
    bad["lemma_id"] = compute_lemma_id(bad)
    if not any("particle fanout requires" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL particle-lemma-gate not caught")
        return 1

    # FAIL: legacy never_surface_only value rejected by the closed enum
    bad = _good_noun()
    bad["fanout_gate"] = "never_surface_only"
    if not validate_row(bad):
        print("SELF-TEST FAIL never_surface_only accepted")
        return 1

    # FAIL: public leak (QAC label echoed into a public field)
    bad = _good_noun()
    bad["pattern"] = "informed_by qac"
    bad["lemma_id"] = compute_lemma_id(bad)
    if not any("forbidden label" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL public-leak not caught")
        return 1

    # FAIL: wrong (non content-addressed) lemma_id
    bad = _good_noun()
    bad["lemma_id"] = "lemma:0000000000000000"
    if not any("content-addressed" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL wrong-lemma-id not caught")
        return 1

    # homograph mIn (prep) vs man (relative): DIFFERENT ids, no collision
    man = {
        "schema": "qamus.certified_lemma.v1",
        "lemma_ar": "مَن",  # man (relative/conditional)
        "root": None,
        "pos": "particle",
        "pattern": None,
        "certification_status": "certified",
        "source_scope": "qamus_entry",
        "public_safe": True,
        "evidence_private": [],
        "fanout_allowed": True,
        "fanout_gate": "function_context",
    }
    man["lemma_id"] = compute_lemma_id(man)
    if good_prep["lemma_id"] == man["lemma_id"]:
        print("SELF-TEST FAIL homograph min/man share an id")
        return 1
    if validate_rows([good_prep, man]):
        print("SELF-TEST FAIL homograph pair rejected:", validate_rows([good_prep, man]))
        return 1
    # forced collision: same id, different meaning -> must FAIL
    collide = dict(man)
    collide["lemma_id"] = good_prep["lemma_id"]
    if not any("collides on two distinct meanings" in e for e in validate_rows([good_prep, collide])):
        print("SELF-TEST FAIL homograph collision not caught")
        return 1

    print("PASS - certified-lemma fanout validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate certified-lemma fanout rows.")
    parser.add_argument("path", nargs="?", help="JSONL of certified-lemma rows")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        parser.error("path is required unless --self-test is used")
    errors = validate_rows(read_jsonl(args.path))
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  - " + err)
        raise SystemExit(1)
    print("PASS - certified-lemma rows are certified, source-clean, and homograph-safe")


if __name__ == "__main__":
    main()
