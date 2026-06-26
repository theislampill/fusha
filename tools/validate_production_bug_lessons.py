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
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
DECISION = re.compile(r"^decision:")
EDIT_INTENT = re.compile(r"^edit-intent:")
ENTRY_SENSE = re.compile(r"^qamus:.+#sense=\d+$")
BLOCKER = re.compile(r"^blocker:")
BUG_CLASS = re.compile(r"^[a-z0-9_]+$")
LEVELS = {"beginner", "intermediate", "advanced"}
SCOPES = {"token_only", "parse_family", "entry_sense", "unsafe"}
GATES = {"token_review", "auto_safe_after_preview", "two_vote_required", "human_review_required",
         "owner_review_required", "never_auto"}
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
    "source_addresses",
]


def repo_path_exists(relpath):
    return os.path.exists(os.path.join(ROOT, relpath.replace("/", os.sep)))


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
        if not BUG_CLASS.match(str(row.get("bug_class") or "")):
            errors.append("line %d: bug_class must be snake_case" % line_no)
        for loc in row.get("token_addresses") or []:
            if not LOC.match(str(loc)):
                errors.append("line %d: bad token address %r" % (line_no, loc))
        source_addresses = row.get("source_addresses") or []
        for addr in source_addresses:
            if not (LOC.match(str(addr)) or WBW.match(str(addr))):
                errors.append("line %d: bad source address %r" % (line_no, addr))
        for loc in row.get("token_addresses") or []:
            if loc not in source_addresses:
                errors.append("line %d: source_addresses missing %s" % (line_no, loc))
            wbw = "wbw:" + str(loc).split(":", 1)[1]
            if wbw not in source_addresses:
                errors.append("line %d: source_addresses missing %s" % (line_no, wbw))
        if row.get("level") not in LEVELS:
            errors.append("line %d: bad level %r" % (line_no, row.get("level")))
        if row.get("edit_intent_id") is not None and not EDIT_INTENT.match(str(row.get("edit_intent_id"))):
            errors.append("line %d: bad edit_intent_id %r" % (line_no, row.get("edit_intent_id")))
        if row.get("requested_scope") is not None and row.get("requested_scope") not in SCOPES:
            errors.append("line %d: bad requested_scope %r" % (line_no, row.get("requested_scope")))
        if row.get("parse_id") is not None and not PARSE.match(str(row.get("parse_id"))):
            errors.append("line %d: bad parse_id %r" % (line_no, row.get("parse_id")))
        if row.get("decision_id") is not None and not DECISION.match(str(row.get("decision_id"))):
            errors.append("line %d: bad decision_id %r" % (line_no, row.get("decision_id")))
        if row.get("entry_sense") is not None and not ENTRY_SENSE.match(str(row.get("entry_sense"))):
            errors.append("line %d: bad entry_sense %r" % (line_no, row.get("entry_sense")))
        if row.get("gate") is not None and row.get("gate") not in GATES:
            errors.append("line %d: bad gate %r" % (line_no, row.get("gate")))
        if row.get("blocker") is not None and not BLOCKER.match(str(row.get("blocker"))):
            errors.append("line %d: bad blocker %r" % (line_no, row.get("blocker")))
        procedure_links = row.get("procedure_links") or []
        if not any(str(p).startswith(("sarf/", "nahw/", "qamus/")) for p in procedure_links):
            errors.append("line %d: procedure_links must point into sarf/nahw/qamus" % line_no)
        for relpath in procedure_links:
            if not repo_path_exists(str(relpath)):
                errors.append("line %d: procedure link missing: %s" % (line_no, relpath))
        for relpath in (row.get("regression_fixture_link"), row.get("validator_link")):
            if relpath and not repo_path_exists(str(relpath)):
                errors.append("line %d: linked file missing: %s" % (line_no, relpath))
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
            "source_addresses": ["quran:33:63:1", "wbw:33:63:1"],
            "edit_intent_id": "edit-intent:token-33-63-1",
            "requested_scope": "token_only",
            "target_address": "wbw:33:63:1",
            "parse_id": "parse:aaaaaaaa",
            "decision_id": "decision:token-33-63-1",
            "entry_sense": "qamus:5935ecfb1ec5#sense=2",
            "gate": "token_review",
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
