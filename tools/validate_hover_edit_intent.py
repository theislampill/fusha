#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate graph-addressed Qamus hover edit intent JSONL rows.

Edit intents are the pre-preview contract for future admin/editor workflows.
They must start from exact token/hover addresses and remain non-mutating until
a repair-impact preview, gate, backup, rebuild, and readback path exists.
"""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "hover-edit-intent.schema.json")
EDIT = re.compile(r"^edit-intent:[A-Za-z0-9_.:-]+$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
DECISION = re.compile(r"^decision:")
ENTRY_SENSE = re.compile(r"^qamus:.+#sense=\d+$")
TARGET = re.compile(r"^(wbw:\d{1,3}:\d{1,3}:\d{1,3}|qamus:.+#field=|qamus:.+#sense=|decision:)")
PREVIEW = re.compile(r"^repair-preview:")
SCOPES = {"token_only", "parse_family", "entry_sense", "unsafe"}
SOURCE_VIEWS = {"hover_inspector", "entry_backlinks", "parse_family_view", "blocker_queue", "repair_preview"}
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
    "edit_intent_id",
    "source_view",
    "requested_scope",
    "target_address",
    "identity_chain",
    "current_visible_hover",
    "proposed_public_hover",
    "impact_preview",
    "propagation_policy",
    "gate",
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

    if not EDIT.match(str(row.get("edit_intent_id") or "")):
        _err(errors, line_no, "edit_intent_id must be edit-intent:<id>")
    if row.get("source_view") not in SOURCE_VIEWS:
        _err(errors, line_no, "bad source_view %r" % row.get("source_view"))
    scope = row.get("requested_scope")
    if scope not in SCOPES:
        _err(errors, line_no, "bad requested_scope %r" % scope)
    if not TARGET.match(str(row.get("target_address") or "")):
        _err(errors, line_no, "target_address must be exact wbw/decision/qamus field/sense address")
    if row.get("gate") not in GATES:
        _err(errors, line_no, "bad gate %r" % row.get("gate"))
    if row.get("live_mutation_allowed") is not False:
        _err(errors, line_no, "live_mutation_allowed must be false")
    if not row.get("current_visible_hover"):
        _err(errors, line_no, "current_visible_hover must be non-empty")

    chain = row.get("identity_chain") or {}
    if not isinstance(chain, dict):
        _err(errors, line_no, "identity_chain must be an object")
        chain = {}
    if not WBW.match(str(chain.get("wbw_loc") or "")):
        _err(errors, line_no, "identity_chain.wbw_loc must be wbw:S:A:W")
    if not QURAN.match(str(chain.get("quran_loc") or "")):
        _err(errors, line_no, "identity_chain.quran_loc must be quran:S:A:W")
    if not PARSE.match(str(chain.get("parse_id") or "")):
        _err(errors, line_no, "identity_chain.parse_id must be parse:<hash>")
    decision_id = chain.get("decision_id")
    if decision_id is not None and not DECISION.match(str(decision_id)):
        _err(errors, line_no, "identity_chain.decision_id must be decision:<id> or null")
    entry_sense = chain.get("entry_sense")
    if entry_sense is not None and not ENTRY_SENSE.match(str(entry_sense)):
        _err(errors, line_no, "identity_chain.entry_sense must be qamus:<id>#sense=<n> or null")
    blocker = chain.get("blocker")
    if blocker is not None and not str(blocker).startswith("blocker:"):
        _err(errors, line_no, "identity_chain.blocker must be blocker:<reason> or null")

    preview = row.get("impact_preview") or {}
    if not isinstance(preview, dict):
        _err(errors, line_no, "impact_preview must be an object")
        preview = {}
    if preview.get("required_before_apply") is not True:
        _err(errors, line_no, "impact_preview.required_before_apply must be true")
    preview_id = preview.get("preview_id")
    if preview_id is not None and not PREVIEW.match(str(preview_id)):
        _err(errors, line_no, "impact_preview.preview_id must be repair-preview:<id> or null")
    affected_token_count = preview.get("affected_token_count")
    if not isinstance(affected_token_count, int) or affected_token_count < 0:
        _err(errors, line_no, "impact_preview.affected_token_count must be a nonnegative integer")
    affected_hover_count = preview.get("affected_hover_count")
    if affected_hover_count is not None and (not isinstance(affected_hover_count, int) or affected_hover_count < 0):
        _err(errors, line_no, "impact_preview.affected_hover_count must be a nonnegative integer")
    affected_parse_count = preview.get("affected_parse_key_count")
    if affected_parse_count is not None and (not isinstance(affected_parse_count, int) or affected_parse_count < 0):
        _err(errors, line_no, "impact_preview.affected_parse_key_count must be a nonnegative integer")
    sample_tokens = preview.get("sample_tokens") or []
    for loc in sample_tokens:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad sample token %r" % loc)
    if isinstance(affected_token_count, int) and sample_tokens and len(sample_tokens) > affected_token_count:
        _err(errors, line_no, "sample_tokens cannot exceed affected_token_count")

    policy = row.get("propagation_policy") or {}
    if not isinstance(policy, dict):
        _err(errors, line_no, "propagation_policy must be an object")
        policy = {}
    if policy.get("exact_token_identity_required") is not True:
        _err(errors, line_no, "exact_token_identity_required must be true")
    if policy.get("raw_surface_identity_allowed") is not False:
        _err(errors, line_no, "raw_surface_identity_allowed must be false")
    if policy.get("parse_key_primary_identity") is not False:
        _err(errors, line_no, "parse_key_primary_identity must be false")
    if policy.get("norm_only_certification_allowed") is not False:
        _err(errors, line_no, "norm_only_certification_allowed must be false")
    family_allowed = policy.get("family_propagation_allowed")
    if not isinstance(family_allowed, bool):
        _err(errors, line_no, "family_propagation_allowed must be boolean")
    collision_required = policy.get("collision_free_required")
    if not isinstance(collision_required, bool):
        _err(errors, line_no, "collision_free_required must be boolean")

    if scope == "token_only":
        if family_allowed:
            _err(errors, line_no, "token_only edit cannot allow family propagation")
        if affected_token_count != 1:
            _err(errors, line_no, "token_only edit intent must preview exactly one affected token")
    if scope == "parse_family":
        if not family_allowed or not collision_required:
            _err(errors, line_no, "parse_family edit requires family propagation and collision-free preview")
        if row.get("gate") not in {"auto_safe_after_preview", "two_vote_required", "human_review_required"}:
            _err(errors, line_no, "parse_family edit must use an explicit family gate")
    if scope == "entry_sense" and entry_sense is None:
        _err(errors, line_no, "entry_sense edit requires identity_chain.entry_sense")
    if scope == "unsafe":
        if row.get("gate") != "never_auto":
            _err(errors, line_no, "unsafe edit intent must use never_auto gate")
        if family_allowed:
            _err(errors, line_no, "unsafe edit intent cannot allow family propagation")

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
        errors.append("zero hover edit intent rows")
    return count, errors


def base_row(scope="token_only"):
    row = {
        "edit_intent_id": "edit-intent:token-33-63-1",
        "source_view": "hover_inspector",
        "requested_scope": scope,
        "target_address": "wbw:33:63:1",
        "identity_chain": {
            "wbw_loc": "wbw:33:63:1",
            "quran_loc": "quran:33:63:1",
            "parse_id": "parse:aaaaaaaa",
            "decision_id": "decision:token-33-63-1",
            "entry_sense": "qamus:5935ecfb1ec5#sense=2",
            "blocker": None,
        },
        "current_visible_hover": "to ask, question",
        "proposed_public_hover": "ask you",
        "impact_preview": {
            "required_before_apply": True,
            "preview_id": "repair-preview:token-33-63-1",
            "affected_token_count": 1,
            "affected_hover_count": 1,
            "affected_parse_key_count": 1,
            "sample_tokens": ["quran:33:63:1"],
        },
        "propagation_policy": {
            "exact_token_identity_required": True,
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
            "norm_only_certification_allowed": False,
            "family_propagation_allowed": False,
            "collision_free_required": False,
        },
        "gate": "token_review",
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
        row.update({
            "edit_intent_id": "edit-intent:family-22-18-conj-art-n",
            "source_view": "parse_family_view",
            "requested_scope": "parse_family",
            "target_address": "qamus:a23a0c853dd8#field=parse_family[parse:bbbbbbbb].hover_pattern",
            "current_visible_hover": "host-only or article-omitting noun hover",
            "proposed_public_hover": "and + the + host noun",
            "gate": "auto_safe_after_preview",
        })
        row["identity_chain"] = {
            "wbw_loc": "wbw:22:18:13",
            "quran_loc": "quran:22:18:13",
            "parse_id": "parse:bbbbbbbb",
            "decision_id": None,
            "entry_sense": "qamus:a23a0c853dd8#sense=1",
            "blocker": None,
        }
        row["impact_preview"].update({
            "preview_id": "repair-preview:family-22-18-conj-art-n",
            "affected_token_count": 3,
            "affected_hover_count": 3,
            "affected_parse_key_count": 1,
            "sample_tokens": ["quran:22:18:13", "quran:22:18:14", "quran:22:18:17"],
        })
        row["propagation_policy"].update({
            "family_propagation_allowed": True,
            "collision_free_required": True,
        })
    elif scope == "entry_sense":
        row.update({
            "edit_intent_id": "edit-intent:entry-5935ecfb1ec5-sense-2",
            "source_view": "entry_backlinks",
            "requested_scope": "entry_sense",
            "target_address": "qamus:5935ecfb1ec5#sense=2",
            "current_visible_hover": "to ask, question",
            "proposed_public_hover": "ask; ask about; ask someone",
            "gate": "two_vote_required",
        })
        row["impact_preview"].update({
            "preview_id": "repair-preview:entry-5935ecfb1ec5-sense-2",
            "affected_token_count": 2,
            "affected_hover_count": 2,
            "affected_parse_key_count": 2,
            "sample_tokens": ["quran:33:63:1", "quran:44:14:2"],
        })
    return row


def self_test():
    with tempfile.TemporaryDirectory(prefix="hover-edit-intent-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        with io.open(good, "w", encoding="utf-8", newline="\n") as handle:
            for scope in ("token_only", "parse_family", "entry_sense"):
                handle.write(json.dumps(base_row(scope), ensure_ascii=False, sort_keys=True) + "\n")
        bad_row = base_row()
        bad_row["propagation_policy"]["raw_surface_identity_allowed"] = True
        with io.open(bad, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(bad_row, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(good)
        if count != 3 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        count, errors = validate(bad)
        if count != 1 or not any("raw_surface_identity_allowed must be false" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
    print("PASS — hover edit intent validator self-test")
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
    print("checked %d hover edit intent rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — hover edit intents are graph-addressed and non-mutating")


if __name__ == "__main__":
    main()
