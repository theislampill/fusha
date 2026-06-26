#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build graph-addressed production bug lesson rows from hover edit intents.

This is a repo-only Phase 3.5 bridge: it turns a validated hover edit intent
into a validated production-bug lesson skeleton. The lesson prose still comes
from the reviewer/author, but the token, hover slot, parse, entry/sense, gate,
and target addresses are inherited from the graph-addressed intent instead of
being rediscovered by Arabic surface text.
"""
import argparse
import io
import json
import os
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_INTENTS = os.path.join(ROOT, "qamus", "examples", "hover_edit_intent.sample.jsonl")
DEFAULT_VALIDATOR = "tools/validate_production_bug_lessons.py"


def load_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def emit_jsonl(rows):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def wbw_from_quran(quran_loc):
    return "wbw:%s" % str(quran_loc).split(":", 1)[1]


def select_intent(rows, edit_intent_id=None, index=0):
    if edit_intent_id:
        for row in rows:
            if row.get("edit_intent_id") == edit_intent_id:
                return row
        raise SystemExit("edit intent not found: %s" % edit_intent_id)
    if index < 0 or index >= len(rows):
        raise SystemExit("intent index out of range: %s" % index)
    return rows[index]


def derive_token_addresses(intent):
    impact = intent.get("impact_preview") or {}
    samples = impact.get("sample_tokens") or []
    quran_loc = (intent.get("identity_chain") or {}).get("quran_loc")
    tokens = []
    if quran_loc:
        tokens.append(quran_loc)
    for sample in samples:
        if sample not in tokens:
            tokens.append(sample)
    return tokens


def derive_source_addresses(intent, tokens):
    identity = intent.get("identity_chain") or {}
    source_addresses = []
    for token in tokens:
        if token not in source_addresses:
            source_addresses.append(token)
        wbw = wbw_from_quran(token)
        if wbw not in source_addresses:
            source_addresses.append(wbw)
    for addr in (identity.get("quran_loc"), identity.get("wbw_loc")):
        if addr and addr not in source_addresses:
            source_addresses.append(addr)
    return source_addresses


def build_lesson(intent, args):
    identity = intent.get("identity_chain") or {}
    tokens = derive_token_addresses(intent)
    if not tokens:
        raise SystemExit("edit intent has no quran token addresses")
    corrected = args.corrected_hover_or_pending_reason
    if corrected is None:
        corrected = intent.get("proposed_public_hover")
    if not corrected:
        raise SystemExit("--corrected-hover-or-pending-reason is required when intent has no proposed hover")
    row = {
        "bug_class": args.bug_class,
        "token_addresses": tokens,
        "visible_bad_hover": args.visible_bad_hover or intent.get("current_visible_hover") or "(pending)",
        "corrected_hover_or_pending_reason": corrected,
        "what_failed": args.what_failed,
        "sarf_lesson": args.sarf_lesson,
        "nahw_lesson": args.nahw_lesson,
        "learner_explanation": args.learner_explanation,
        "drill_prompt": args.drill_prompt,
        "level": args.level,
        "procedure_links": args.procedure_link,
        "regression_fixture_link": args.regression_fixture_link,
        "validator_link": args.validator_link,
        "source_addresses": derive_source_addresses(intent, tokens),
        "edit_intent_id": intent.get("edit_intent_id"),
        "requested_scope": intent.get("requested_scope"),
        "target_address": intent.get("target_address"),
        "parse_id": identity.get("parse_id"),
        "decision_id": identity.get("decision_id"),
        "entry_sense": identity.get("entry_sense"),
        "gate": intent.get("gate"),
    }
    if identity.get("blocker"):
        row["blocker"] = identity.get("blocker")
    return row


def validate_rows(rows):
    import validate_production_bug_lessons
    with tempfile.TemporaryDirectory(prefix="production-bug-lesson-build-") as td:
        path = os.path.join(td, "lessons.jsonl")
        write_jsonl(path, rows)
        count, errors = validate_production_bug_lessons.validate(path)
        if count != len(rows) or errors:
            raise SystemExit("built production bug lesson failed validation: %s" % errors)


def self_test():
    rows = load_jsonl(SAMPLE_INTENTS)
    class Args:
        bug_class = "verb_object_suffix_omitted"
        visible_bad_hover = None
        corrected_hover_or_pending_reason = None
        what_failed = "A lemma gloss was used for a composed token and the object suffix disappeared."
        sarf_lesson = "Segment the imperfect host and attached object pronoun before proposing a hover."
        nahw_lesson = "The following explicit subject does not erase the attached object pronoun."
        learner_explanation = "The final kaaf contributes you."
        drill_prompt = "In يَسْأَلُكَ, mark the prefix, stem, and attached object pronoun."
        level = "beginner"
        procedure_link = ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/pronoun-attachment.md"]
        regression_fixture_link = "qamus/examples/production_bug_lesson.sample.jsonl"
        validator_link = DEFAULT_VALIDATOR
    lesson = build_lesson(select_intent(rows, edit_intent_id="edit-intent:token-33-63-1"), Args)
    validate_rows([lesson])
    if lesson["token_addresses"] != ["quran:33:63:1"]:
        print("SELF-TEST FAIL: token address not inherited from intent")
        return 1
    if "wbw:33:63:1" not in lesson["source_addresses"]:
        print("SELF-TEST FAIL: wbw source address missing")
        return 1
    if lesson["parse_id"] != "parse:aaaaaaaa":
        print("SELF-TEST FAIL: parse id not preserved")
        return 1
    if lesson["requested_scope"] != "token_only":
        print("SELF-TEST FAIL: requested scope not preserved")
        return 1
    print("PASS — production bug lesson builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent-jsonl", default=SAMPLE_INTENTS)
    parser.add_argument("--edit-intent-id")
    parser.add_argument("--intent-index", type=int, default=0)
    parser.add_argument("--bug-class")
    parser.add_argument("--visible-bad-hover")
    parser.add_argument("--corrected-hover-or-pending-reason")
    parser.add_argument("--what-failed")
    parser.add_argument("--sarf-lesson")
    parser.add_argument("--nahw-lesson")
    parser.add_argument("--learner-explanation")
    parser.add_argument("--drill-prompt")
    parser.add_argument("--level", choices=["beginner", "intermediate", "advanced"])
    parser.add_argument("--procedure-link", action="append")
    parser.add_argument("--regression-fixture-link")
    parser.add_argument("--validator-link", default=DEFAULT_VALIDATOR)
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    for field in ("bug_class", "what_failed", "sarf_lesson", "nahw_lesson",
                  "learner_explanation", "drill_prompt", "level",
                  "procedure_link", "regression_fixture_link", "validator_link"):
        if not getattr(args, field):
            parser.error("--%s is required" % field.replace("_", "-"))
    rows = load_jsonl(args.intent_jsonl)
    intent = select_intent(rows, edit_intent_id=args.edit_intent_id, index=args.intent_index)
    lesson = build_lesson(intent, args)
    validate_rows([lesson])
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, [lesson])
    else:
        emit_jsonl([lesson])


if __name__ == "__main__":
    main()
