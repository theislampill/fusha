#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan graph-addressed hover edit intents from a shadow admin/debug pack.

This is a read-only Phase 3 helper. It creates *intent rows* that future admin
or editor UI can review before any repair/apply path exists. It does not write
live Qamus data, rebuild WBW, or author hover decisions.
"""
import argparse
import copy
import io
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_PACK = os.path.join(ROOT, "qamus", "examples", "shadow_admin_debug_pack.sample.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def emit_jsonl(rows):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def quran_from_address(address):
    if QURAN.match(address):
        return address
    if WBW.match(address):
        return "quran:%s" % address.split(":", 1)[1]
    if re.match(r"^\d{1,3}:\d{1,3}:\d{1,3}$", address):
        return "quran:%s" % address
    raise SystemExit("expected quran:S:A:W, wbw:S:A:W, or S:A:W; got %s" % address)


def wbw_from_quran(quran_loc):
    return "wbw:%s" % quran_loc.split(":", 1)[1]


def public_boundary(pack):
    return pack.get("public_boundary") or {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
        "public_fields": ["gloss", "src", "kind", "lang"],
        "private_fields": ["internal_evidence", "adapter_labels", "reviewer_notes"],
    }


def indexes(pack):
    inspectors_by_quran = {}
    parse_by_id = {}
    entries_by_id = {}
    for row in pack.get("hover_inspectors") or []:
        inspectors_by_quran[row.get("quran_loc")] = row
    for row in pack.get("parse_family_views") or []:
        parse_by_id[row.get("parse_id")] = row
    for row in pack.get("entry_backlinks") or []:
        entries_by_id[row.get("entry_id")] = row
    return inspectors_by_quran, parse_by_id, entries_by_id


def first_entry_sense(inspector, fallback_entry=None):
    candidates = inspector.get("entry_candidates") or {}
    entries = candidates.get("whole_token_candidates") or []
    entry = fallback_entry or (entries[0] if entries else None)
    if not entry:
        return None
    if "#sense=" in entry:
        return entry
    return "%s#sense=1" % entry


def make_identity(inspector, entry_sense=None):
    return {
        "wbw_loc": inspector.get("wbw_loc"),
        "quran_loc": inspector.get("quran_loc"),
        "parse_id": inspector.get("parse_id"),
        "decision_id": (inspector.get("decision_ids") or [None])[-1],
        "entry_sense": entry_sense,
        "blocker": inspector.get("blocker"),
    }


def propagation_policy(family_allowed, collision_free):
    return {
        "exact_token_identity_required": True,
        "raw_surface_identity_allowed": False,
        "parse_key_primary_identity": False,
        "norm_only_certification_allowed": False,
        "family_propagation_allowed": bool(family_allowed),
        "collision_free_required": bool(collision_free),
    }


def token_only_intent(pack, address, proposed_hover):
    inspectors_by_quran, _parse_by_id, _entries_by_id = indexes(pack)
    quran_loc = quran_from_address(address)
    inspector = inspectors_by_quran.get(quran_loc)
    if not inspector:
        raise SystemExit("token not present in admin debug pack: %s" % address)
    wbw_loc = wbw_from_quran(quran_loc)
    entry_sense = first_entry_sense(inspector)
    return {
        "edit_intent_id": "edit-intent:token-%s" % quran_loc.split(":", 1)[1].replace(":", "-"),
        "source_view": "hover_inspector",
        "requested_scope": "token_only",
        "target_address": wbw_loc,
        "identity_chain": make_identity(inspector, entry_sense),
        "current_visible_hover": inspector.get("current_visible_hover") or "(pending)",
        "proposed_public_hover": proposed_hover,
        "impact_preview": {
            "required_before_apply": True,
            "preview_id": "repair-preview:token-%s" % quran_loc.split(":", 1)[1].replace(":", "-"),
            "affected_token_count": 1,
            "affected_hover_count": 1,
            "affected_parse_key_count": 1 if inspector.get("parse_id") else 0,
            "sample_tokens": [quran_loc],
        },
        "propagation_policy": propagation_policy(False, False),
        "gate": "token_review",
        "live_mutation_allowed": False,
        "public_boundary": public_boundary(pack),
    }


def parse_family_intent(pack, parse_id, proposed_hover, gate=None):
    inspectors_by_quran, parse_by_id, _entries_by_id = indexes(pack)
    family = parse_by_id.get(parse_id)
    if not family:
        raise SystemExit("parse family not present in admin debug pack: %s" % parse_id)
    propagation_allowed = bool(family.get("propagation_allowed"))
    if not propagation_allowed:
        raise SystemExit(
            "parse family is not propagation-safe; use token_only or human_review workflow: %s" % parse_id
        )
    resolved_gate = gate or ("auto_safe_after_preview" if propagation_allowed else "two_vote_required")
    sample_tokens = family.get("seen_locs_sample") or []
    if not sample_tokens:
        raise SystemExit("parse family has no sample tokens: %s" % parse_id)
    inspector = inspectors_by_quran.get(sample_tokens[0])
    if not inspector:
        raise SystemExit("parse family first sample has no hover inspector: %s" % sample_tokens[0])
    entry_sense = first_entry_sense(inspector)
    return {
        "edit_intent_id": "edit-intent:parse-family-%s" % parse_id.split(":", 1)[1],
        "source_view": "parse_family_view",
        "requested_scope": "parse_family",
        "target_address": "%s#field=parse_family[%s].hover_pattern" % ((entry_sense or "qamus:unknown#sense=1").split("#", 1)[0], parse_id),
        "identity_chain": make_identity(inspector, entry_sense),
        "current_visible_hover": inspector.get("current_visible_hover") or "(pending)",
        "proposed_public_hover": proposed_hover,
        "impact_preview": {
            "required_before_apply": True,
            "preview_id": "repair-preview:parse-family-%s" % parse_id.split(":", 1)[1],
            "affected_token_count": int(family.get("family_size") or len(sample_tokens)),
            "affected_hover_count": int(family.get("family_size") or len(sample_tokens)),
            "affected_parse_key_count": 1,
            "sample_tokens": sample_tokens,
        },
        "propagation_policy": propagation_policy(propagation_allowed, propagation_allowed),
        "gate": resolved_gate,
        "live_mutation_allowed": False,
        "public_boundary": public_boundary(pack),
    }


def entry_sense_intent(pack, entry_id, proposed_hover, gate="two_vote_required"):
    inspectors_by_quran, parse_by_id, entries_by_id = indexes(pack)
    entry = entries_by_id.get(entry_id)
    if not entry:
        raise SystemExit("entry not present in admin debug pack: %s" % entry_id)
    sample_tokens = entry.get("sample_tokens") or []
    if not sample_tokens:
        raise SystemExit("entry has no sample tokens: %s" % entry_id)
    inspector = None
    for sample_token in sample_tokens:
        inspector = inspectors_by_quran.get(sample_token)
        if inspector:
            break
    if not inspector:
        raise SystemExit("entry sample tokens have no hover inspector: %s" % entry_id)
    parse_ids = entry.get("sample_parse_keys") or []
    entry_sense = "%s#sense=1" % entry_id if "#sense=" not in entry_id else entry_id
    return {
        "edit_intent_id": "edit-intent:entry-%s-sense-1" % entry_id.replace(":", "-"),
        "source_view": "entry_backlinks",
        "requested_scope": "entry_sense",
        "target_address": entry_sense,
        "identity_chain": make_identity(inspector, entry_sense),
        "current_visible_hover": inspector.get("current_visible_hover") or "(pending)",
        "proposed_public_hover": proposed_hover,
        "impact_preview": {
            "required_before_apply": True,
            "preview_id": "repair-preview:entry-%s-sense-1" % entry_id.replace(":", "-"),
            "affected_token_count": int(entry.get("dependent_token_count") or len(sample_tokens)),
            "affected_hover_count": int(entry.get("dependent_hover_count") or len(entry.get("sample_hover_slots") or [])),
            "affected_parse_key_count": int(entry.get("parse_key_count") or len(parse_ids)),
            "sample_tokens": sample_tokens,
        },
        "propagation_policy": propagation_policy(False, False),
        "gate": gate,
        "live_mutation_allowed": False,
        "public_boundary": public_boundary(pack),
    }


def validate_rows(rows):
    import validate_hover_edit_intent
    with tempfile.TemporaryDirectory(prefix="shadow-hover-edit-intent-") as td:
        path = os.path.join(td, "intent.jsonl")
        write_jsonl(path, rows)
        count, errors = validate_hover_edit_intent.validate(path)
        if count != len(rows) or errors:
            raise SystemExit("planned intent failed validation: %s" % errors)


def self_test():
    pack = load_json(SAMPLE_PACK)
    safe_pack = copy.deepcopy(pack)
    safe_pack["hover_inspectors"][0]["edit_scopes"]["parse_key_family"]["family_propagation_allowed"] = True
    safe_pack["hover_inspectors"][0]["edit_scopes"]["parse_key_family"]["required_gate"] = "auto_safe_after_preview"
    safe_pack["parse_family_views"][0]["propagation_allowed"] = True
    safe_pack["parse_family_views"][0]["family_class"] = "propagation_safe"
    rows = [
        token_only_intent(pack, "33:63:1", "ask you"),
        parse_family_intent(safe_pack, "parse:aaaaaaaa", "ask you"),
        entry_sense_intent(pack, "qamus:5935ecfb1ec5", "ask; ask someone"),
    ]
    validate_rows(rows)
    try:
        parse_family_intent(pack, "parse:aaaaaaaa", "ask you", gate="two_vote_required")
        print("SELF-TEST FAIL: unsafe parse family emitted an edit intent")
        return 1
    except SystemExit as exc:
        if "not propagation-safe" not in str(exc):
            print("SELF-TEST FAIL: unsafe parse family failed for wrong reason: %s" % exc)
            return 1
    if rows[0]["target_address"] != "wbw:33:63:1":
        print("SELF-TEST FAIL: token target not exact wbw address")
        return 1
    if rows[0]["propagation_policy"]["family_propagation_allowed"]:
        print("SELF-TEST FAIL: token-only intent allowed family propagation")
        return 1
    if rows[1]["propagation_policy"]["parse_key_primary_identity"]:
        print("SELF-TEST FAIL: parse key used as primary identity")
        return 1
    if rows[2]["requested_scope"] != "entry_sense":
        print("SELF-TEST FAIL: entry scope mismatch")
        return 1
    print("PASS — shadow hover edit intent planner self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", default=SAMPLE_PACK)
    parser.add_argument("--scope", choices=["token_only", "parse_family", "entry_sense"], required=False)
    parser.add_argument("--token", help="quran:S:A:W, wbw:S:A:W, or S:A:W")
    parser.add_argument("--parse", dest="parse_id", help="parse:<id>")
    parser.add_argument("--entry", help="qamus:<id>")
    parser.add_argument("--proposed-hover")
    parser.add_argument("--gate")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.scope:
        parser.error("--scope is required unless --self-test is used")
    if not args.proposed_hover:
        parser.error("--proposed-hover is required")
    pack = load_json(args.pack)
    if pack.get("live_mutation_allowed") is not False:
        raise SystemExit("refusing pack with live_mutation_allowed != false")
    if args.scope == "token_only":
        if not args.token:
            parser.error("--token is required for token_only")
        rows = [token_only_intent(pack, args.token, args.proposed_hover)]
    elif args.scope == "parse_family":
        if not args.parse_id:
            parser.error("--parse is required for parse_family")
        rows = [parse_family_intent(pack, args.parse_id, args.proposed_hover, gate=args.gate)]
    else:
        if not args.entry:
            parser.error("--entry is required for entry_sense")
        rows = [entry_sense_intent(pack, args.entry, args.proposed_hover, gate=args.gate or "two_vote_required")]
    validate_rows(rows)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, rows)
    else:
        emit_jsonl(rows)


if __name__ == "__main__":
    main()
