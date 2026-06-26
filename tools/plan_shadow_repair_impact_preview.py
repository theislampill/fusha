#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create read-only repair impact previews from hover edit intents.

This Phase 3 helper is a bridge from "what the editor wants to change" to
"what a future apply path must preview before changing anything". It validates
both sides and never writes live Qamus data.
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_INTENTS = os.path.join(ROOT, "qamus", "examples", "hover_edit_intent.sample.jsonl")
ENTRY_SENSE = re.compile(r"^(?P<entry>qamus:.+)#sense=(?P<sense>\d+)$")
QURAN = re.compile(r"^quran:(?P<loc>\d{1,3}:\d{1,3}:\d{1,3})$")


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def emit_jsonl(rows):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def quran_to_wbw(quran_loc):
    match = QURAN.match(quran_loc)
    if not match:
        raise SystemExit("expected quran:S:A:W, got %s" % quran_loc)
    return "wbw:%s" % match.group("loc")


def entry_base(entry_sense):
    if not entry_sense:
        raise SystemExit("edit intent lacks identity_chain.entry_sense; cannot build qamus field preview")
    match = ENTRY_SENSE.match(entry_sense)
    if not match:
        raise SystemExit("expected qamus:<id>#sense=<n>, got %s" % entry_sense)
    return match.group("entry")


def sense_field(entry_sense):
    match = ENTRY_SENSE.match(entry_sense)
    if not match:
        raise SystemExit("expected qamus:<id>#sense=<n>, got %s" % entry_sense)
    return "%s#field=senses[%s].gloss" % (match.group("entry"), match.group("sense"))


def sample_tokens(intent):
    preview = intent.get("impact_preview") or {}
    tokens = preview.get("sample_tokens") or []
    if tokens:
        return tokens
    chain = intent.get("identity_chain") or {}
    quran_loc = chain.get("quran_loc")
    if quran_loc:
        return [quran_loc]
    raise SystemExit("edit intent has no sample token or identity_chain.quran_loc: %s" % intent.get("edit_intent_id"))


def changed_field_for_intent(intent):
    scope = intent.get("requested_scope")
    target = intent.get("target_address")
    chain = intent.get("identity_chain") or {}
    entry_sense = chain.get("entry_sense")
    if scope == "token_only":
        wbw_loc = chain.get("wbw_loc")
        if not wbw_loc:
            raise SystemExit("token_only edit intent lacks identity_chain.wbw_loc")
        if not entry_sense:
            return "qamus:hover-overrides#field=token_overrides[%s].gloss" % wbw_loc
        return "%s#field=token_overrides[%s].gloss" % (entry_base(entry_sense), wbw_loc)
    if scope == "parse_family":
        if not str(target or "").startswith("qamus:") or "#field=" not in str(target):
            raise SystemExit("parse_family edit intent target must be qamus field-addressed")
        return target
    if scope == "entry_sense":
        return sense_field(target if "#sense=" in str(target) else entry_sense)
    raise SystemExit("unsupported repair preview scope: %s" % scope)


def rollback_for_intent(intent, changed_field):
    scope = intent.get("requested_scope")
    if scope == "entry_sense":
        return {
            "strategy": "restore_backup",
            "artifact": "backup:%s" % changed_field.split("#", 1)[0],
        }
    return {
        "strategy": "append_only_revert",
        "artifact": "%s#revert" % intent.get("edit_intent_id"),
    }


def to_repair_preview(intent):
    chain = intent.get("identity_chain") or {}
    intent_preview = intent.get("impact_preview") or {}
    tokens = sample_tokens(intent)
    hovers = [quran_to_wbw(loc) for loc in tokens]
    parse_id = chain.get("parse_id")
    changed_field = changed_field_for_intent(intent)
    affected_token_count = int(intent_preview.get("affected_token_count") or len(tokens))
    affected_hover_count = int(intent_preview.get("affected_hover_count") or len(hovers))
    affected_parse_key_count = int(intent_preview.get("affected_parse_key_count") or (1 if parse_id else 0))
    return {
        "preview_id": intent_preview.get("preview_id")
        or "repair-preview:%s" % str(intent.get("edit_intent_id")).split(":", 1)[-1],
        "target_address": changed_field if intent.get("requested_scope") != "entry_sense" else intent.get("target_address"),
        "scope": intent.get("requested_scope"),
        "before": {"gloss": intent.get("current_visible_hover")},
        "after": {"gloss": intent.get("proposed_public_hover")},
        "changed_fields": [changed_field],
        "affected_token_count": affected_token_count,
        "affected_hover_count": affected_hover_count,
        "affected_parse_key_count": affected_parse_key_count,
        "affected_tokens": tokens,
        "affected_hover_slots": hovers,
        "affected_parse_keys": [parse_id] if parse_id else [],
        "sample_tokens_are_complete": len(tokens) == affected_token_count and len(hovers) == affected_hover_count,
        "gate": intent.get("gate"),
        "rollback": rollback_for_intent(intent, changed_field),
        "live_mutation_allowed": False,
        "public_boundary": intent.get("public_boundary"),
    }


def validate_intents(path):
    import validate_hover_edit_intent
    count, errors = validate_hover_edit_intent.validate(path)
    if count == 0 or errors:
        raise SystemExit("input edit intents failed validation: %s" % errors)
    return count


def validate_previews(rows):
    import validate_repair_impact_preview
    with tempfile.TemporaryDirectory(prefix="shadow-repair-preview-") as td:
        path = os.path.join(td, "preview.jsonl")
        write_jsonl(path, rows)
        count, errors = validate_repair_impact_preview.validate(path)
        if count != len(rows) or errors:
            raise SystemExit("repair previews failed validation: %s" % errors)


def plan_previews(intent_jsonl):
    validate_intents(intent_jsonl)
    rows = [to_repair_preview(row) for row in iter_jsonl(intent_jsonl)]
    validate_previews(rows)
    return rows


def self_test():
    rows = plan_previews(SAMPLE_INTENTS)
    if len(rows) != 3:
        print("SELF-TEST FAIL: expected 3 preview rows, got %d" % len(rows))
        return 1
    if any(row["affected_token_count"] < len(row["affected_tokens"]) for row in rows):
        print("SELF-TEST FAIL: preview counts are smaller than listed affected tokens")
        return 1
    if rows[1]["sample_tokens_are_complete"] is not True:
        print("SELF-TEST FAIL: sample fixture parse-family preview should be complete")
        return 1
    if rows[0]["target_address"] != "qamus:5935ecfb1ec5#field=token_overrides[wbw:33:63:1].gloss":
        print("SELF-TEST FAIL: token-only target was not qamus field-addressed")
        return 1
    if rows[1]["scope"] != "parse_family" or rows[1]["gate"] != "auto_safe_after_preview":
        print("SELF-TEST FAIL: parse-family scope/gate was not preserved")
        return 1
    if rows[2]["changed_fields"] != ["qamus:5935ecfb1ec5#field=senses[2].gloss"]:
        print("SELF-TEST FAIL: entry/sense changed field was not explicit")
        return 1
    if any(row["live_mutation_allowed"] for row in rows):
        print("SELF-TEST FAIL: repair preview allowed live mutation")
        return 1
    no_entry_intent = dict(next(iter_jsonl(SAMPLE_INTENTS)))
    no_entry_intent["identity_chain"] = dict(no_entry_intent["identity_chain"])
    no_entry_intent["identity_chain"]["entry_sense"] = None
    no_entry_rows = [to_repair_preview(no_entry_intent)]
    validate_previews(no_entry_rows)
    if no_entry_rows[0]["target_address"] != "qamus:hover-overrides#field=token_overrides[wbw:33:63:1].gloss":
        print("SELF-TEST FAIL: no-entry token override did not use hover override namespace")
        return 1
    print("PASS — shadow repair impact preview planner self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent-jsonl", default=SAMPLE_INTENTS)
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    rows = plan_previews(args.intent_jsonl)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, rows)
    else:
        emit_jsonl(rows)


if __name__ == "__main__":
    main()
