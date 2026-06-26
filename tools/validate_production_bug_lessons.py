#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate production bug lesson JSONL fixtures."""
import argparse
import io
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOC = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
LEVELS = {"beginner", "intermediate", "advanced"}
REQUIRED = [
    "bug_class",
    "token_addresses",
    "visible_bad_hover",
    "corrected_hover_or_pending_reason",
    "what_failed",
    "sarf_lesson",
    "nahw_lesson",
    "learner_explanation",
    "drill_prompt",
    "level",
    "procedure_links",
    "regression_fixture_link",
    "validator_link",
]


def validate(path):
    errors = []
    count = 0
    for line_no, line in enumerate(io.open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        count += 1
        try:
            row = json.loads(line)
        except Exception as exc:
            errors.append("line %d: bad JSON (%s)" % (line_no, exc))
            continue
        for field in REQUIRED:
            if field not in row or row[field] in ("", [], None):
                errors.append("line %d: missing %s" % (line_no, field))
        for loc in row.get("token_addresses") or []:
            if not LOC.match(str(loc)):
                errors.append("line %d: bad token address %r" % (line_no, loc))
        if row.get("level") not in LEVELS:
            errors.append("line %d: bad level %r" % (line_no, row.get("level")))
        if not any(str(p).startswith(("sarf/", "nahw/", "qamus/")) for p in row.get("procedure_links") or []):
            errors.append("line %d: procedure_links must point into sarf/nahw/qamus" % line_no)
    if count == 0:
        errors.append("zero bug lessons")
    return count, errors


def self_test():
    with tempfile.TemporaryDirectory(prefix="bug-lesson-") as td:
        path = os.path.join(td, "lessons.jsonl")
        good = {
            "bug_class": "verb_object_suffix_omitted",
            "token_addresses": ["quran:33:63:1"],
            "visible_bad_hover": "to ask, question",
            "corrected_hover_or_pending_reason": "ask you",
            "what_failed": "The suffix object pronoun was omitted.",
            "sarf_lesson": "Segment the imperfect verb host and attached object pronoun.",
            "nahw_lesson": "The explicit following subject does not erase the attached object.",
            "learner_explanation": "The final kaaf means you.",
            "drill_prompt": "Find the object pronoun in يَسْأَلُكَ.",
            "level": "beginner",
            "procedure_links": ["sarf/procedures/clitic-and-host-morphology.md"],
            "regression_fixture_link": "qamus/examples/production_bug_lesson.sample.jsonl",
            "validator_link": "tools/validate_production_bug_lessons.py",
        }
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(good, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(path)
        if count != 1 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
    print("PASS — production bug lesson validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.jsonl:
        parser.error("jsonl path is required unless --self-test is used")
    count, errors = validate(args.jsonl)
    print("checked %d production bug lessons" % count)
    if errors:
        print("FAIL:")
        for err in errors[:40]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — production bug lessons are complete and address-linked")


if __name__ == "__main__":
    main()
