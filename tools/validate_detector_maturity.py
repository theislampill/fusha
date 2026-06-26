#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Phase 2 shadow-graph detector maturity claims.

This is a fail-closed guard against reading detector-zero counts as proof of
absence. It accepts either:
  - a standalone JSON detector-maturity record, or
  - JSONL rows with apply_policy.detector_maturity, such as review-pack rows.

It does not inspect, rebuild, or mutate live Qamus data.
"""
import argparse
import io
import json
import os
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "detector-maturity.schema.json")

EXPECTED = {
    "two_vote_required": "partial_shadow_gate",
    "source_disagreement": "reserved_detector_gap",
    "zero_count_policy": "zero_does_not_prove_absence",
}
FORBIDDEN_COMPLETION_VALUES = {
    "complete",
    "trusted_complete",
    "absence_proven",
    "no_cases_exist",
    "none_exist",
    "detector_complete",
}
REQUIRED_POLICY = {
    "zero_counts_are_detector_outputs_only": True,
    "zero_counts_must_not_claim_absence": True,
    "requires_live_readonly_shadow_graph": True,
}


def read_json_or_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        text = handle.read().strip()
    if not text:
        return []
    if path.endswith(".jsonl"):
        rows = []
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((line_no, json.loads(line)))
            except Exception as exc:
                rows.append((line_no, {"__json_error__": str(exc)}))
        return rows
    return [(1, json.loads(text))]


def maturity_from_row(row):
    if not isinstance(row, dict):
        return None, None
    if "detectors" in row:
        return row.get("detectors"), row.get("reporting_policy")
    policy = row.get("apply_policy")
    if isinstance(policy, dict) and "detector_maturity" in policy:
        return policy.get("detector_maturity"), None
    if "detector_maturity" in row:
        return row.get("detector_maturity"), None
    return None, None


def validate_record(row, line_no, errors):
    if "__json_error__" in row:
        errors.append("line %d: bad JSON (%s)" % (line_no, row["__json_error__"]))
        return

    detectors, reporting_policy = maturity_from_row(row)
    if detectors is None:
        errors.append("line %d: no detector maturity object found" % line_no)
        return
    if not isinstance(detectors, dict):
        errors.append("line %d: detector maturity must be an object" % line_no)
        return

    for key, expected in sorted(EXPECTED.items()):
        value = detectors.get(key)
        if value != expected:
            errors.append("line %d: %s must be %r, got %r" % (line_no, key, expected, value))
        if str(value).lower() in FORBIDDEN_COMPLETION_VALUES:
            errors.append("line %d: %s overclaims detector completion: %r" % (line_no, key, value))

    for key, value in detectors.items():
        if str(value).lower() in FORBIDDEN_COMPLETION_VALUES:
            errors.append("line %d: %s overclaims detector completion: %r" % (line_no, key, value))

    if reporting_policy is not None:
        if not isinstance(reporting_policy, dict):
            errors.append("line %d: reporting_policy must be an object" % line_no)
        else:
            for key, expected in sorted(REQUIRED_POLICY.items()):
                if reporting_policy.get(key) is not expected:
                    errors.append("line %d: reporting_policy.%s must be %r" % (line_no, key, expected))


def validate(path):
    errors = []
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    rows = read_json_or_jsonl(path)
    if not rows:
        errors.append("zero detector maturity rows")
    for line_no, row in rows:
        validate_record(row, line_no, errors)
    return len(rows), errors


def standalone_record():
    return {
        "schema_version": "qamus-detector-maturity@1",
        "applies_to": ["phase2_shadow_graph", "shadow_closure_queue", "shadow_review_pack"],
        "detectors": EXPECTED,
        "reporting_policy": REQUIRED_POLICY,
    }


def review_pack_row():
    return {
        "id": "queue:parse_aaaaaaaa",
        "apply_policy": {
            "detector_maturity": EXPECTED,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "live_mutation_allowed": False,
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
        },
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="detector-maturity-") as td:
        good_json = os.path.join(td, "good.json")
        good_jsonl = os.path.join(td, "good.jsonl")
        bad_json = os.path.join(td, "bad.json")
        with io.open(good_json, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(standalone_record(), handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        with io.open(good_jsonl, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(review_pack_row(), ensure_ascii=False, sort_keys=True) + "\n")
        bad = standalone_record()
        bad["detectors"] = dict(bad["detectors"])
        bad["detectors"]["source_disagreement"] = "complete"
        with io.open(bad_json, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(bad, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")

        for path in (good_json, good_jsonl):
            count, errors = validate(path)
            if count != 1 or errors:
                print("SELF-TEST FAIL good %s: %s" % (os.path.basename(path), errors))
                return 1
        count, errors = validate(bad_json)
        if count != 1 or not any("source_disagreement" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
    print("PASS — detector maturity validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        parser.error("path is required unless --self-test is used")
    count, errors = validate(args.path)
    print("checked %d detector maturity rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — detector maturity preserves Phase 2 zero-count warning")


if __name__ == "__main__":
    main()
