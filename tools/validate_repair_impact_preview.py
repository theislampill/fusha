#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Qamus graph-addressed repair impact preview JSONL rows.

Repair previews are allowed to guide future entry/sense/hover edits only when
they are exact-addressed, non-mutating, rollback-aware, and source-clean at the
public boundary. This is a repo/fixture validator; it does not inspect or write
live Qamus state.
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "repair-impact-preview.schema.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
FIELD = re.compile(r"^qamus:.+#field=")
PREVIEW = re.compile(r"^repair-preview:[A-Za-z0-9_.:-]+$")
SCOPES = {"token_only", "parse_family", "entry_sense", "unsafe"}
GATES = {
    "token_review",
    "auto_safe_after_preview",
    "two_vote_required",
    "human_review_required",
    "owner_review_required",
    "never_auto",
}
FORBIDDEN_PUBLIC_LABELS = (
    "informed_by",
    "mcp",
    "qac",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
)
REQUIRED = [
    "preview_id",
    "target_address",
    "scope",
    "before",
    "after",
    "changed_fields",
    "affected_tokens",
    "affected_hover_slots",
    "affected_parse_keys",
    "gate",
    "rollback",
    "live_mutation_allowed",
    "public_boundary",
]


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except Exception as exc:
                yield line_no, {"__json_error__": str(exc)}


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def public_boundary_errors(boundary):
    errors = []
    if not isinstance(boundary, dict):
        return ["public_boundary must be an object"]
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            errors.append("public_boundary.%s must be %r" % (key, value))
    blob = json.dumps(boundary, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in blob:
            errors.append("public_boundary leaks forbidden label %r" % label)
    return errors


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return

    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    if not PREVIEW.match(str(row.get("preview_id") or "")):
        _err(errors, line_no, "preview_id must be repair-preview:<id>")
    if not str(row.get("target_address") or "").startswith("qamus:"):
        _err(errors, line_no, "target_address must be qamus-addressed")
    scope = row.get("scope")
    if scope not in SCOPES:
        _err(errors, line_no, "bad scope %r" % scope)
    gate = row.get("gate")
    if gate not in GATES:
        _err(errors, line_no, "bad gate %r" % gate)
    if row.get("live_mutation_allowed") is not False:
        _err(errors, line_no, "live_mutation_allowed must be false")

    changed_fields = row.get("changed_fields") or []
    if not changed_fields:
        _err(errors, line_no, "changed_fields must be non-empty")
    for address in changed_fields:
        if not FIELD.match(str(address)):
            _err(errors, line_no, "bad changed field address %r" % address)

    tokens = row.get("affected_tokens") or []
    hovers = row.get("affected_hover_slots") or []
    parses = row.get("affected_parse_keys") or []
    for loc in tokens:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad affected token %r" % loc)
    for loc in hovers:
        if not WBW.match(str(loc)):
            _err(errors, line_no, "bad affected hover slot %r" % loc)
    for parse in parses:
        if not PARSE.match(str(parse)):
            _err(errors, line_no, "bad affected parse key %r" % parse)
    if scope != "unsafe" and (not tokens or not hovers):
        _err(errors, line_no, "safe preview scopes must list affected tokens and hover slots")
    if scope == "token_only" and (len(tokens) != 1 or len(hovers) != 1):
        _err(errors, line_no, "token_only preview must affect exactly one token and one hover")
    if scope == "parse_family" and len(set(parses)) != 1:
        _err(errors, line_no, "parse_family preview must cite exactly one parse family")
    if scope == "entry_sense" and not parses:
        _err(errors, line_no, "entry_sense preview must list affected parse keys")
    if scope == "unsafe" and gate != "never_auto":
        _err(errors, line_no, "unsafe preview must use never_auto gate")

    rollback = row.get("rollback") or {}
    if not isinstance(rollback, dict):
        _err(errors, line_no, "rollback must be an object")
        rollback = {}
    if rollback.get("strategy") not in {"append_only_revert", "restore_backup", "no_apply_preview_only"}:
        _err(errors, line_no, "rollback.strategy is invalid")
    if not rollback.get("artifact"):
        _err(errors, line_no, "rollback.artifact is required")

    for msg in public_boundary_errors(row.get("public_boundary")):
        _err(errors, line_no, msg)


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero repair impact preview rows")
    return count, errors


def good_row(scope="token_only"):
    base = {
        "preview_id": "repair-preview:sample-token",
        "target_address": "qamus:5935ecfb1ec5#field=senses[2].gloss",
        "scope": scope,
        "before": {"gloss": "to ask, question"},
        "after": {"gloss": "ask you"},
        "changed_fields": ["qamus:5935ecfb1ec5#field=senses[2].gloss"],
        "affected_tokens": ["quran:33:63:1"],
        "affected_hover_slots": ["wbw:33:63:1"],
        "affected_parse_keys": ["parse:aaaaaaaa"],
        "gate": "token_review",
        "rollback": {"strategy": "append_only_revert", "artifact": "decision:<new>#revert"},
        "live_mutation_allowed": False,
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_source_names_public": False,
            "internal_provenance_public": False,
            "public_fields": ["gloss", "src", "kind", "lang"],
            "private_fields": ["internal_evidence", "adapter_labels"],
        },
    }
    if scope == "parse_family":
        base.update({
            "preview_id": "repair-preview:sample-family",
            "scope": "parse_family",
            "affected_tokens": ["quran:22:18:13", "quran:22:18:14"],
            "affected_hover_slots": ["wbw:22:18:13", "wbw:22:18:14"],
            "affected_parse_keys": ["parse:bbbbbbbb"],
            "gate": "auto_safe_after_preview",
        })
    elif scope == "entry_sense":
        base.update({
            "preview_id": "repair-preview:sample-entry",
            "scope": "entry_sense",
            "target_address": "qamus:8f8d49c8fd17#field=senses[1].gloss",
            "changed_fields": ["qamus:8f8d49c8fd17#field=senses[1].gloss"],
            "affected_tokens": ["quran:33:63:1", "quran:44:14:2"],
            "affected_hover_slots": ["wbw:33:63:1", "wbw:44:14:2"],
            "affected_parse_keys": ["parse:aaaaaaaa", "parse:cccccccc"],
            "gate": "two_vote_required",
            "rollback": {"strategy": "restore_backup", "artifact": "backup:<entry-json-before>"},
        })
    return base


def self_test():
    with tempfile.TemporaryDirectory(prefix="repair-impact-preview-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        with io.open(good, "w", encoding="utf-8", newline="\n") as handle:
            for scope in ("token_only", "parse_family", "entry_sense"):
                handle.write(json.dumps(good_row(scope), ensure_ascii=False, sort_keys=True) + "\n")
        bad_row = good_row()
        bad_row["affected_tokens"] = ["33:63:1"]
        with io.open(bad, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(bad_row, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(good)
        if count != 3 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        count, errors = validate(bad)
        if count != 1 or not any("bad affected token" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
    print("PASS — repair impact preview validator self-test")
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
    print("checked %d repair impact preview rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — repair impact previews are exact-addressed and non-mutating")


if __name__ == "__main__":
    main()
