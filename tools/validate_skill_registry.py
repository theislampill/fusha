#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed validator for the versioned skill rule registry (gate 8).

Validates qamus/skills/rule-registry.jsonl against
qamus/schemas/skill-rule-registry-row.schema.json and the registry invariants.

FAILS CLOSED (non-zero exit) on any of:
  * unknown_rule_id            - a `cites` relationship targets a registry id not present
  * dangling_supersede_extend  - a `supersedes`/`extends` relationship targets a registry id not present
  * duplicate_accepted_id      - a skill_rule_id occurs more than once and >=1 occurrence is accepted
  * accepted_missing_evidence  - status == accepted but evidence_addresses is empty
  * invalid_state_transition   - the (skill_version, status) pair is not an allowed transition
  * missing_skill_version      - skill_version absent/blank/malformed, or disagrees with `skill`
  * schema_violation           - a row is missing a required field / bad enum / bad type

Deterministic, stdlib only, no network, no writes.

  python tools/validate_skill_registry.py               # validate the live registry
  python tools/validate_skill_registry.py --self-test   # red-first fixtures then live registry
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REGISTRY = os.path.join(ROOT, "qamus", "skills", "rule-registry.jsonl")

REQUIRED = [
    "skill_rule_id", "skill", "skill_version", "status", "fact_family", "scope",
    "evidence_addresses", "positive_examples", "negative_or_boundary_examples",
    "defeaters", "abstention_condition", "gate", "code_references",
    "test_references", "relationships", "provenance",
]
SKILLS = {"sarf", "nahw"}
STATUSES = {"accepted", "candidate", "blocked"}
REL_TYPES = {"supersedes", "extends", "cites"}
REL_KINDS = {"registry", "external"}
# Allowed (version-suffix, status) transitions. @2 v-next and the @2.1 / @2.2 increments may not be
# `accepted` (unreleased, drafted forward); @1 baseline may not be `blocked`.
ALLOWED_TRANSITIONS = {
    ("1", "accepted"), ("1", "candidate"),
    ("2", "candidate"), ("2", "blocked"),
    ("2.1", "candidate"), ("2.1", "blocked"),
    ("2.2", "candidate"), ("2.2", "blocked"),
}
# Recognized version suffixes (the part after '@'), per skill.
VERSION_SUFFIXES = ("1", "2", "2.1", "2.2")


def _err(errors, code, rid, msg):
    errors.append({"code": code, "rule_id": rid, "msg": msg})


def validate_rows(rows):
    """Return a list of error dicts. Empty list == valid."""
    errors = []
    ids = [r.get("skill_rule_id") for r in rows if isinstance(r, dict)]
    id_set = set(ids)

    # duplicate_accepted_id
    seen_status = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        rid = r.get("skill_rule_id")
        seen_status.setdefault(rid, []).append(r.get("status"))
    for rid, sts in seen_status.items():
        if len(sts) > 1 and any(s == "accepted" for s in sts):
            _err(errors, "duplicate_accepted_id", rid,
                 "id occurs %d times with an accepted row" % len(sts))

    for r in rows:
        if not isinstance(r, dict):
            _err(errors, "schema_violation", None, "row is not a JSON object")
            continue
        rid = r.get("skill_rule_id")

        # schema_violation: required fields present
        for k in REQUIRED:
            if k not in r:
                _err(errors, "schema_violation", rid, "missing required field '%s'" % k)
        if not isinstance(rid, str) or not rid:
            _err(errors, "schema_violation", rid, "skill_rule_id must be a non-empty string")
        if r.get("skill") not in SKILLS:
            _err(errors, "schema_violation", rid, "skill must be one of %s" % sorted(SKILLS))
        if r.get("status") not in STATUSES:
            _err(errors, "schema_violation", rid, "status must be one of %s" % sorted(STATUSES))
        for k in ("evidence_addresses", "positive_examples", "negative_or_boundary_examples",
                  "defeaters", "code_references", "test_references", "relationships"):
            if k in r and not isinstance(r[k], list):
                _err(errors, "schema_violation", rid, "field '%s' must be a list" % k)
        if not isinstance(r.get("fact_family"), str) or not r.get("fact_family"):
            _err(errors, "schema_violation", rid, "fact_family must be a non-empty string")
        if not isinstance(r.get("gate"), str) or not r.get("gate"):
            _err(errors, "schema_violation", rid, "gate must be a non-empty string")

        # missing_skill_version
        sv = r.get("skill_version")
        skill = r.get("skill")
        ok_sv = (isinstance(sv, str) and skill in SKILLS
                 and sv in tuple(skill + "@" + suf for suf in VERSION_SUFFIXES))
        if not ok_sv:
            _err(errors, "missing_skill_version", rid,
                 "skill_version %r absent/malformed or disagrees with skill %r" % (sv, skill))

        # invalid_state_transition
        status = r.get("status")
        if ok_sv and status in STATUSES:
            suffix = sv.split("@", 1)[1]  # version part after '@' (e.g. "1", "2", "2.1")
            if (suffix, status) not in ALLOWED_TRANSITIONS:
                _err(errors, "invalid_state_transition", rid,
                     "(%s, %s) is not an allowed transition" % (sv, status))

        # accepted_missing_evidence
        if status == "accepted":
            ev = r.get("evidence_addresses")
            if not isinstance(ev, list) or len([x for x in ev if x]) == 0:
                _err(errors, "accepted_missing_evidence", rid,
                     "accepted rule has empty evidence_addresses")

        # relationship targets: unknown_rule_id / dangling_supersede_extend
        for rel in r.get("relationships", []) or []:
            if not isinstance(rel, dict):
                _err(errors, "schema_violation", rid, "relationship must be an object")
                continue
            rtype = rel.get("type")
            kind = rel.get("target_kind")
            tgt = rel.get("target_id")
            if rtype not in REL_TYPES:
                _err(errors, "schema_violation", rid, "relationship.type invalid: %r" % rtype)
            if kind not in REL_KINDS:
                _err(errors, "schema_violation", rid, "relationship.target_kind invalid: %r" % kind)
            if not isinstance(tgt, str) or not tgt:
                _err(errors, "schema_violation", rid, "relationship.target_id must be non-empty string")
                continue
            if kind == "registry" and tgt not in id_set:
                if rtype in ("supersedes", "extends"):
                    _err(errors, "dangling_supersede_extend", rid,
                         "%s target '%s' not present in registry" % (rtype, tgt))
                else:  # cites
                    _err(errors, "unknown_rule_id", rid,
                         "cites unknown rule id '%s'" % tgt)

    return errors


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, ln in enumerate(f, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError as e:
                rows.append({"__parse_error__": "line %d: %s" % (i, e)})
    return rows


def validate_file(path):
    if not os.path.exists(path):
        print("FAIL missing registry file: %s" % path)
        return ["missing_file"]
    rows = load_rows(path)
    bad = [r for r in rows if isinstance(r, dict) and "__parse_error__" in r]
    if bad:
        for b in bad:
            print("FAIL parse " + b["__parse_error__"])
        return ["parse_error"]
    errors = validate_rows(rows)
    from collections import Counter
    counts = Counter(e["code"] for e in errors)
    print("registry: %d rows, %d errors" % (len(rows), len(errors)))
    if errors:
        for code in sorted(counts):
            print("FAIL %s x%d" % (code, counts[code]))
        for e in errors[:20]:
            print("   - [%s] %s: %s" % (e["code"], e["rule_id"], e["msg"]))
    return [e["code"] for e in errors]


# --------------------------------------------------------------------------- #
# Self-test: red-first fixtures (each trips exactly one fail-closed case),     #
# then a green fixture, then the live registry.                               #
# --------------------------------------------------------------------------- #
def _row(**over):
    """A minimal VALID @1 accepted row; override to break one invariant."""
    base = {
        "skill_rule_id": "sarf-base-ok",
        "skill": "sarf",
        "skill_version": "sarf@1",
        "status": "accepted",
        "fact_family": "fam",
        "scope": "scope",
        "evidence_addresses": ["sarf/SKILL.md:1"],
        "positive_examples": [],
        "negative_or_boundary_examples": [],
        "defeaters": [],
        "abstention_condition": None,
        "gate": "baseline@1-accepted",
        "code_references": [],
        "test_references": [],
        "relationships": [],
        "provenance": {"origin": "test"},
    }
    base.update(over)
    return base


def self_test():
    checks = []

    def expect(name, rows, want_code):
        codes = set(e["code"] for e in validate_rows(rows))
        ok = want_code in codes
        checks.append((name, ok))
        print(("ok   RED  " if ok else "FAIL RED  ") + name +
              ("" if ok else "  (expected %s, got %s)" % (want_code, sorted(codes))))

    def expect_clean(name, rows):
        codes = validate_rows(rows)
        ok = len(codes) == 0
        checks.append((name, ok))
        print(("ok   GREEN " if ok else "FAIL GREEN ") + name +
              ("" if ok else "  (unexpected %s)" % [c["code"] for c in codes]))

    # 1. unknown_rule_id  (cites a non-existent registry rule)
    expect("unknown_rule_id (cites dangling)",
           [_row(skill_rule_id="so-x", skill_version="sarf@2", status="candidate",
                 relationships=[{"type": "cites", "target_id": "nope-not-here",
                                 "target_kind": "registry"}])],
           "unknown_rule_id")
    # 2. dangling_supersede_extend  (extends a non-existent registry rule)
    expect("dangling_supersede_extend (extends dangling)",
           [_row(skill_rule_id="so-y", skill_version="sarf@2", status="candidate",
                 relationships=[{"type": "extends", "target_id": "ghost-rule",
                                 "target_kind": "registry"}])],
           "dangling_supersede_extend")
    # 3. duplicate_accepted_id
    expect("duplicate_accepted_id",
           [_row(skill_rule_id="dup"), _row(skill_rule_id="dup")],
           "duplicate_accepted_id")
    # 4. accepted_missing_evidence
    expect("accepted_missing_evidence",
           [_row(evidence_addresses=[])],
           "accepted_missing_evidence")
    # 5. invalid_state_transition  (@2 cannot be accepted)
    expect("invalid_state_transition (@2 accepted)",
           [_row(skill_rule_id="so-z", skill_version="sarf@2", status="accepted",
                 gate="x", evidence_addresses=["a"])],
           "invalid_state_transition")
    # 5b. invalid_state_transition  (@1 cannot be blocked)
    expect("invalid_state_transition (@1 blocked)",
           [_row(skill_rule_id="so-b1", skill_version="sarf@1", status="blocked", gate="x")],
           "invalid_state_transition")
    # 5c. invalid_state_transition  (@2.1 increment cannot be accepted)
    expect("invalid_state_transition (@2.1 accepted)",
           [_row(skill_rule_id="so-inc-acc", skill_version="sarf@2.1", status="accepted",
                 gate="x", evidence_addresses=["a"])],
           "invalid_state_transition")
    # 5d. invalid_state_transition  (@2.2 increment cannot be accepted)
    expect("invalid_state_transition (@2.2 accepted)",
           [_row(skill_rule_id="so-inc22-acc", skill_version="sarf@2.2", status="accepted",
                 gate="x", evidence_addresses=["a"])],
           "invalid_state_transition")
    # 6. missing_skill_version
    expect("missing_skill_version (blank)",
           [_row(skill_version="")],
           "missing_skill_version")
    # 6b. missing_skill_version (skill/version disagree)
    expect("missing_skill_version (skill mismatch)",
           [_row(skill="nahw", skill_version="sarf@1")],
           "missing_skill_version")
    # 7. schema_violation (missing required field)
    bad = _row()
    del bad["gate"]
    expect("schema_violation (missing field)", [bad], "schema_violation")

    # GREEN fixtures
    expect_clean("green: valid @1 accepted + @2 candidate w/ resolvable extends", [
        _row(skill_rule_id="sarf-target"),
        _row(skill_rule_id="so-ext", skill_version="sarf@2", status="candidate",
             gate="@2-candidate", evidence_addresses=["quran:1:1:1"],
             relationships=[{"type": "extends", "target_id": "sarf-target",
                             "target_kind": "registry"}]),
    ])
    expect_clean("green: external supersede target is exempt from dangling", [
        _row(skill_rule_id="so-sup", skill_version="sarf@2", status="candidate",
             gate="@2", evidence_addresses=["x"],
             relationships=[{"type": "supersedes",
                             "target_id": "sarf §3 output-contract enum, SKILL.md:90",
                             "target_kind": "external"}]),
    ])
    expect_clean("green: blocked @2 rule with no positive example is valid", [
        _row(skill_rule_id="so-qglam", skill_version="sarf@2", status="blocked",
             gate="@2-blocked", evidence_addresses=["x"], positive_examples=[]),
    ])
    expect_clean("green: @2.1 increment candidate w/ resolvable extends is valid", [
        _row(skill_rule_id="sarf-inc-target"),
        _row(skill_rule_id="so-inc21", skill="nahw", skill_version="nahw@2.1", status="candidate",
             gate="@2.1-candidate", evidence_addresses=["quran:2:40:3"],
             relationships=[{"type": "extends", "target_id": "sarf-inc-target",
                             "target_kind": "registry"}]),
    ])
    expect_clean("green: @2.2 increment candidate w/ resolvable extends is valid", [
        _row(skill_rule_id="sarf-inc22-target"),
        _row(skill_rule_id="so-inc22", skill="sarf", skill_version="sarf@2.2", status="candidate",
             gate="@2.2-candidate", evidence_addresses=["quran:38:14:6"],
             relationships=[{"type": "extends", "target_id": "sarf-inc22-target",
                             "target_kind": "registry"}]),
    ])

    print("-" * 60)
    live_codes = validate_file(REGISTRY)
    live_ok = len(live_codes) == 0
    checks.append(("live registry clean", live_ok))
    print(("ok   GREEN " if live_ok else "FAIL GREEN ") + "live registry validates clean")

    failed = [n for n, ok in checks if not ok]
    print("=" * 60)
    print("self-test: %d/%d checks passed" % (len(checks) - len(failed), len(checks)))
    if not failed:
        print("skill registry self-test OK")
    return 0 if not failed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--registry", default=REGISTRY)
    args = ap.parse_args()
    if args.self_test:
        sys.exit(self_test())
    codes = validate_file(args.registry)
    sys.exit(0 if not codes else 1)


if __name__ == "__main__":
    main()
