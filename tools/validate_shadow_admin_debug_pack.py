#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Qamus Phase 3 shadow admin/debug pack JSON.

This validator checks the static read-only inspector pack emitted by
build_shadow_admin_debug_pack.py. It is intentionally repo/fixture friendly:
it does not inspect or write live Qamus state.
"""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "shadow-admin-debug-pack.schema.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:")
REQUIRED_VIEWS = {
    "hover_inspector",
    "entry_backlinks",
    "parse_family_view",
    "blocker_queue",
    "repair_preview",
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


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _err(errors, msg):
    errors.append(msg)


def public_boundary_errors(boundary, prefix="public_boundary"):
    errors = []
    if not isinstance(boundary, dict):
        return ["%s must be an object" % prefix]
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            errors.append("%s.%s must be %r" % (prefix, key, value))
    blob = json.dumps(boundary, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in blob:
            errors.append("%s leaks forbidden public label %r" % (prefix, label))
    return errors


def visit_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from visit_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from visit_dicts(value)


def validate_hover_inspector(row, index, errors):
    prefix = "hover_inspectors[%d]" % index
    if row.get("view") != "hover_inspector":
        _err(errors, "%s.view must be hover_inspector" % prefix)
    if row.get("public_exposable") is not False:
        _err(errors, "%s.public_exposable must be false" % prefix)
    quran_loc = row.get("quran_loc")
    wbw_loc = row.get("wbw_loc")
    if not QURAN.match(str(quran_loc or "")):
        _err(errors, "%s.quran_loc must be quran:S:A:W" % prefix)
    if not WBW.match(str(wbw_loc or "")):
        _err(errors, "%s.wbw_loc must be wbw:S:A:W" % prefix)
    if quran_loc and wbw_loc and wbw_loc != "wbw:" + str(quran_loc).split(":", 1)[1]:
        _err(errors, "%s.wbw_loc must match quran_loc" % prefix)
    parse_id = row.get("parse_id")
    if parse_id is not None and not PARSE.match(str(parse_id)):
        _err(errors, "%s.parse_id must be parse:<id> or null" % prefix)
    if not isinstance(row.get("parse_key_family_size"), int) or row.get("parse_key_family_size") < 0:
        _err(errors, "%s.parse_key_family_size must be nonnegative integer" % prefix)
    if not isinstance(row.get("propagation_allowed"), bool):
        _err(errors, "%s.propagation_allowed must be boolean" % prefix)
    if not isinstance(row.get("decision_ids") or [], list):
        _err(errors, "%s.decision_ids must be an array" % prefix)
    scopes = row.get("edit_scopes") or {}
    if not isinstance(scopes, dict):
        _err(errors, "%s.edit_scopes must be an object" % prefix)
        scopes = {}
    token_scope = scopes.get("token_only") or {}
    family_scope = scopes.get("parse_key_family") or {}
    if token_scope.get("allowed_for_preview") is not True:
        _err(errors, "%s.edit_scopes.token_only.allowed_for_preview must be true" % prefix)
    if token_scope.get("affected_token_count") != 1:
        _err(errors, "%s.edit_scopes.token_only.affected_token_count must be 1" % prefix)
    if family_scope.get("allowed_for_preview") is not True:
        _err(errors, "%s.edit_scopes.parse_key_family.allowed_for_preview must be true" % prefix)
    if family_scope.get("family_propagation_allowed") != row.get("propagation_allowed"):
        _err(errors, "%s parse-family propagation flag must match inspector propagation_allowed" % prefix)
    candidates = row.get("entry_candidates") or {}
    if not isinstance(candidates, dict):
        _err(errors, "%s.entry_candidates must be an object" % prefix)
    for key in ("whole_token_candidates", "component_candidates"):
        if key in candidates and not isinstance(candidates.get(key), list):
            _err(errors, "%s.entry_candidates.%s must be an array" % (prefix, key))
    if candidates.get("component_candidates") and row.get("propagation_allowed") is True:
        _err(errors, "%s component candidates must not make propagation_allowed true" % prefix)
    for msg in public_boundary_errors(row.get("public_boundary"), "%s.public_boundary" % prefix):
        _err(errors, msg)


def validate_entry_backlink(row, index, errors):
    prefix = "entry_backlinks[%d]" % index
    if row.get("view") != "entry_backlinks":
        _err(errors, "%s.view must be entry_backlinks" % prefix)
    if row.get("public_exposable") is not False:
        _err(errors, "%s.public_exposable must be false" % prefix)
    if not str(row.get("entry_id") or "").startswith("qamus:"):
        _err(errors, "%s.entry_id must start with qamus:" % prefix)
    if row.get("candidate_scope") != "whole_token_or_resolved_entry":
        _err(errors, "%s.candidate_scope must be whole_token_or_resolved_entry" % prefix)
    for key in ("dependent_token_count", "dependent_hover_count", "parse_key_count"):
        if not isinstance(row.get(key), int) or row.get(key) < 0:
            _err(errors, "%s.%s must be nonnegative integer" % (prefix, key))
    stub = row.get("repair_preview_stub") or {}
    if not isinstance(stub, dict):
        _err(errors, "%s.repair_preview_stub must be an object" % prefix)
        stub = {}
    if stub.get("live_mutation_allowed") is not False:
        _err(errors, "%s.repair_preview_stub.live_mutation_allowed must be false" % prefix)
    if stub.get("required_before_apply") is not True:
        _err(errors, "%s.repair_preview_stub.required_before_apply must be true" % prefix)
    for key in ("affected_token_count", "affected_hover_count"):
        if not isinstance(stub.get(key), int) or stub.get(key) < 0:
            _err(errors, "%s.repair_preview_stub.%s must be nonnegative integer" % (prefix, key))
    for msg in public_boundary_errors(row.get("public_boundary"), "%s.public_boundary" % prefix):
        _err(errors, msg)


def validate_parse_family(row, index, errors):
    prefix = "parse_family_views[%d]" % index
    if row.get("view") != "parse_family_view":
        _err(errors, "%s.view must be parse_family_view" % prefix)
    if row.get("public_exposable") is not False:
        _err(errors, "%s.public_exposable must be false" % prefix)
    if not PARSE.match(str(row.get("parse_id") or "")):
        _err(errors, "%s.parse_id must be parse:<id>" % prefix)
    if not isinstance(row.get("family_size"), int) or row.get("family_size") < 0:
        _err(errors, "%s.family_size must be nonnegative integer" % prefix)
    if not isinstance(row.get("propagation_allowed"), bool):
        _err(errors, "%s.propagation_allowed must be boolean" % prefix)
    if row.get("component_candidate_entries") and row.get("propagation_allowed") is True:
        _err(errors, "%s component candidates must not make propagation_allowed true" % prefix)
    for loc in row.get("seen_locs_sample") or []:
        if not QURAN.match(str(loc)):
            _err(errors, "%s.seen_locs_sample has bad loc %r" % (prefix, loc))
    for loc in row.get("hover_slots_sample") or []:
        if not WBW.match(str(loc)):
            _err(errors, "%s.hover_slots_sample has bad loc %r" % (prefix, loc))
    for qloc, wloc in zip(row.get("seen_locs_sample") or [], row.get("hover_slots_sample") or []):
        if wloc != "wbw:" + str(qloc).split(":", 1)[1]:
            _err(errors, "%s hover sample must match quran sample" % prefix)
    for msg in public_boundary_errors(row.get("public_boundary"), "%s.public_boundary" % prefix):
        _err(errors, msg)


def validate_blocker_queue(row, errors):
    if not isinstance(row, dict):
        _err(errors, "blocker_queue must be an object")
        return
    if row.get("view") != "blocker_queue":
        _err(errors, "blocker_queue.view must be blocker_queue")
    if row.get("public_exposable") is not False:
        _err(errors, "blocker_queue.public_exposable must be false")
    if not isinstance(row.get("blocker_classes") or [], list):
        _err(errors, "blocker_queue.blocker_classes must be an array")
    for index, blocker in enumerate(row.get("blocker_classes") or []):
        prefix = "blocker_queue.blocker_classes[%d]" % index
        if blocker.get("public_exposable") is not False:
            _err(errors, "%s.public_exposable must be false" % prefix)
        if not str(blocker.get("blocker") or "").startswith("blocker:"):
            _err(errors, "%s.blocker must start with blocker:" % prefix)
        if not isinstance(blocker.get("count"), int) or blocker.get("count") < 0:
            _err(errors, "%s.count must be nonnegative integer" % prefix)
        for loc in blocker.get("sample_tokens") or []:
            if not QURAN.match(str(loc)):
                _err(errors, "%s.sample_tokens has bad loc %r" % (prefix, loc))
    for msg in public_boundary_errors(row.get("public_boundary"), "blocker_queue.public_boundary"):
        _err(errors, msg)


def validate_pack(pack):
    errors = []
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    if not isinstance(pack, dict):
        return ["pack must be an object"]
    if pack.get("version") != "qamus-shadow-admin-debug-pack@1":
        _err(errors, "version must be qamus-shadow-admin-debug-pack@1")
    if pack.get("public_exposable") is not False:
        _err(errors, "public_exposable must be false")
    if pack.get("live_mutation_allowed") is not False:
        _err(errors, "live_mutation_allowed must be false")
    views = set(pack.get("views") or [])
    if not REQUIRED_VIEWS.issubset(views):
        _err(errors, "views must include %s" % sorted(REQUIRED_VIEWS))
    summary = pack.get("summary") or {}
    if not isinstance(summary, dict):
        _err(errors, "summary must be an object")
        summary = {}
    for key in ("token_rows", "hover_rows", "entry_rows", "parse_rows"):
        if not isinstance(summary.get(key), int) or summary.get(key) <= 0:
            _err(errors, "summary.%s must be positive integer" % key)
    for key in ("decision_rows", "blocker_classes"):
        if not isinstance(summary.get(key), int) or summary.get(key) < 0:
            _err(errors, "summary.%s must be nonnegative integer" % key)

    inspectors = pack.get("hover_inspectors") or []
    entries = pack.get("entry_backlinks") or []
    families = pack.get("parse_family_views") or []
    if not inspectors:
        _err(errors, "hover_inspectors must be non-empty")
    if not families:
        _err(errors, "parse_family_views must be non-empty")
    for index, row in enumerate(inspectors):
        validate_hover_inspector(row, index, errors)
    for index, row in enumerate(entries):
        validate_entry_backlink(row, index, errors)
    for index, row in enumerate(families):
        validate_parse_family(row, index, errors)
    validate_blocker_queue(pack.get("blocker_queue"), errors)
    for msg in public_boundary_errors(pack.get("public_boundary"), "public_boundary"):
        _err(errors, msg)

    for obj in visit_dicts(pack):
        if obj.get("live_mutation_allowed") is True:
            _err(errors, "live_mutation_allowed true found in pack")
        if obj.get("public_exposable") is True:
            _err(errors, "public_exposable true found in pack")
    return errors


def validate(path):
    if not os.path.exists(path):
        return 0, ["missing pack: %s" % path]
    try:
        pack = load_json(path)
    except Exception as exc:
        return 0, ["bad JSON: %s" % exc]
    return 1, validate_pack(pack)


def good_pack():
    boundary = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
        "public_fields": ["gloss", "src", "kind", "lang"],
        "private_fields": ["internal_evidence", "adapter_labels"],
    }
    inspector = {
        "view": "hover_inspector",
        "public_exposable": False,
        "quran_loc": "quran:33:63:1",
        "wbw_loc": "wbw:33:63:1",
        "surface": "يَسْأَلُكَ",
        "status": "resolved",
        "current_visible_hover": "ask you",
        "parse_id": "parse:aaaaaaaa",
        "parse_key_family_size": 1,
        "family_class": "two_vote_required",
        "gate": "two_vote_required",
        "gates": ["two_vote_required"],
        "propagation_allowed": False,
        "blocker": None,
        "grammar_triggers": ["suffix_pronoun"],
        "token_internal_segments": [{"role": "object_pronoun", "surface": "كَ"}],
        "entry_candidates": {
            "whole_token_candidates": ["qamus:5935ecfb1ec5"],
            "component_candidates": ["qamus:p:kaf"],
        },
        "decision_ids": ["decision:token-33-63-1"],
        "public_boundary": boundary,
        "edit_scopes": {
            "token_only": {"allowed_for_preview": True, "affected_token_count": 1, "required_gate": "token_review"},
            "parse_key_family": {
                "allowed_for_preview": True,
                "affected_token_count": 1,
                "required_gate": "two_vote_required",
                "family_propagation_allowed": False,
            },
        },
    }
    entry = {
        "view": "entry_backlinks",
        "public_exposable": False,
        "entry_id": "qamus:5935ecfb1ec5",
        "candidate_scope": "whole_token_or_resolved_entry",
        "dependent_token_count": 1,
        "dependent_hover_count": 1,
        "parse_key_count": 1,
        "repair_preview_stub": {
            "scope": "entry_sense",
            "live_mutation_allowed": False,
            "required_before_apply": True,
            "affected_token_count": 1,
            "affected_hover_count": 1,
            "rollback_strategy": "no_apply_preview_only",
        },
        "public_boundary": boundary,
    }
    family = {
        "view": "parse_family_view",
        "public_exposable": False,
        "parse_id": "parse:aaaaaaaa",
        "family_size": 1,
        "propagation_allowed": False,
        "component_candidate_entries": ["qamus:p:kaf"],
        "seen_locs_sample": ["quran:33:63:1"],
        "hover_slots_sample": ["wbw:33:63:1"],
        "public_boundary": boundary,
    }
    return {
        "version": "qamus-shadow-admin-debug-pack@1",
        "public_exposable": False,
        "live_mutation_allowed": False,
        "source_shadow_dir": "out/sample-shadow",
        "views": sorted(REQUIRED_VIEWS),
        "summary": {
            "token_rows": 1,
            "hover_rows": 1,
            "entry_rows": 1,
            "decision_rows": 1,
            "parse_rows": 1,
            "blocker_classes": 1,
            "sample_token_count": 1,
            "sample_entry_count": 1,
        },
        "hover_inspectors": [inspector],
        "entry_backlinks": [entry],
        "parse_family_views": [family],
        "blocker_queue": {
            "view": "blocker_queue",
            "public_exposable": False,
            "blocker_classes": [
                {
                    "blocker": "blocker:suffix_pronoun",
                    "count": 1,
                    "sample_tokens": ["quran:33:63:1"],
                    "public_exposable": False,
                }
            ],
            "public_boundary": boundary,
        },
        "public_boundary": boundary,
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="shadow-admin-pack-validator-") as td:
        good = os.path.join(td, "good.json")
        bad = os.path.join(td, "bad.json")
        pack = good_pack()
        dump_json(good, pack)
        bad_pack = good_pack()
        bad_pack["hover_inspectors"][0]["wbw_loc"] = "wbw:33:63:2"
        bad_pack["hover_inspectors"][0]["propagation_allowed"] = True
        bad_pack["parse_family_views"][0]["propagation_allowed"] = True
        bad_pack["entry_backlinks"][0]["candidate_scope"] = "component_candidate"
        bad_pack["live_mutation_allowed"] = True
        dump_json(bad, bad_pack)
        count, errors = validate(good)
        if count != 1 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        count, errors = validate(bad)
        if count != 1:
            print("SELF-TEST FAIL bad count:", count)
            return 1
        if not any("wbw_loc must match quran_loc" in err for err in errors):
            print("SELF-TEST FAIL bad missing wbw mismatch:", errors)
            return 1
        if not any("live_mutation_allowed must be false" in err for err in errors):
            print("SELF-TEST FAIL bad missing live mutation:", errors)
            return 1
        if not any("component candidates must not make propagation_allowed true" in err for err in errors):
            print("SELF-TEST FAIL bad missing component propagation:", errors)
            return 1
        if not any("candidate_scope must be whole_token_or_resolved_entry" in err for err in errors):
            print("SELF-TEST FAIL bad missing entry scope:", errors)
            return 1
    print("PASS — shadow admin debug pack validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.json:
        parser.error("json path is required unless --self-test is used")
    count, errors = validate(args.json)
    print("checked %d shadow admin debug pack files" % count)
    if errors:
        for err in errors:
            print("ERROR:", err)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
