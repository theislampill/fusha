#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the future Qamus shadow admin/debug route contract.

This is a repo-side Phase 3 guard. It validates only a read-only route contract
for a future app/admin integration. It does not discover live paths, start
services, mutate Qamus data, rebuild WBW, or implement routes.
"""
import argparse
import copy
import io
import json
import os
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "shadow-admin-route-contract.schema.json")
SAMPLE = os.path.join(ROOT, "qamus", "examples", "shadow_admin_route_contract.sample.json")

REQUIRED_VIEWS = {
    "hover_inspector",
    "entry_backlinks",
    "parse_family_view",
    "blocker_queue",
    "repair_preview",
}
FORBIDDEN_ROUTE_WORDS = (
    "/apply",
    "/write",
    "/mutate",
    "/delete",
    "/commit",
    "/push",
    "source-photo",
    "source_photo",
    "qac",
    "mcp",
    "quran.com",
    "quran_com",
    "informed_by",
    "/srv/",
    "c:\\",
)
EXPECTED_BOUNDARY = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "external_source_names_public": False,
    "internal_provenance_public": False,
}
ADDRESS_TYPES = {
    "quran_loc",
    "wbw_loc",
    "parse_id",
    "qamus_entry",
    "qamus_field",
    "entry_sense",
    "decision_id",
    "blocker_id",
    "repair_preview_id",
    "edit_intent_id",
}


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _err(errors, msg):
    errors.append(msg)


def validate_public_boundary(boundary, errors, prefix):
    if not isinstance(boundary, dict):
        _err(errors, "%s must be an object" % prefix)
        return
    for key, value in EXPECTED_BOUNDARY.items():
        if boundary.get(key) != value:
            _err(errors, "%s.%s must be %r" % (prefix, key, value))
    public_blob = json.dumps({
        "src": boundary.get("src"),
        "kind": boundary.get("kind"),
        "lang": boundary.get("lang"),
        "public_fields": boundary.get("public_fields") or [],
        "external_source_names_public": boundary.get("external_source_names_public"),
        "internal_provenance_public": boundary.get("internal_provenance_public"),
    }, ensure_ascii=False).lower()
    for word in FORBIDDEN_ROUTE_WORDS:
        if word in public_blob:
            _err(errors, "%s leaks forbidden public label %r" % (prefix, word))


def validate_identity_policy(policy, errors):
    if not isinstance(policy, dict):
        _err(errors, "identity_policy must be an object")
        return
    expected = {
        "exact_token_identity_required": True,
        "raw_surface_identity_allowed": False,
        "parse_key_primary_identity": False,
        "norm_only_certification_allowed": False,
    }
    for key, value in expected.items():
        if policy.get(key) is not value:
            _err(errors, "identity_policy.%s must be %r" % (key, value))


def validate_route_defaults(defaults, errors):
    if not isinstance(defaults, dict):
        _err(errors, "route_defaults must be an object")
        return
    if defaults.get("allowed_methods") != ["GET"]:
        _err(errors, "route_defaults.allowed_methods must be ['GET']")
    if defaults.get("mutating_methods_allowed") is not False:
        _err(errors, "route_defaults.mutating_methods_allowed must be false")
    if defaults.get("apply_routes_allowed") is not False:
        _err(errors, "route_defaults.apply_routes_allowed must be false")
    if defaults.get("source_pack_required") is not True:
        _err(errors, "route_defaults.source_pack_required must be true")


def validate_route(route, index, errors):
    prefix = "routes[%d]" % index
    if not isinstance(route, dict):
        _err(errors, "%s must be an object" % prefix)
        return
    if not str(route.get("route_id") or "").startswith("route:"):
        _err(errors, "%s.route_id must start with route:" % prefix)
    if route.get("method") != "GET":
        _err(errors, "%s.method must be GET" % prefix)
    if route.get("admin_only") is not True:
        _err(errors, "%s.admin_only must be true" % prefix)
    if route.get("auth_required") is not True:
        _err(errors, "%s.auth_required must be true" % prefix)
    if route.get("read_only") is not True:
        _err(errors, "%s.read_only must be true" % prefix)
    if route.get("public_exposable") is not False:
        _err(errors, "%s.public_exposable must be false" % prefix)
    if route.get("live_mutation_allowed") is not False:
        _err(errors, "%s.live_mutation_allowed must be false" % prefix)
    if route.get("private_debug_allowed") is not True:
        _err(errors, "%s.private_debug_allowed must be true" % prefix)
    if route.get("public_payload_allowed") is not False:
        _err(errors, "%s.public_payload_allowed must be false" % prefix)
    path = str(route.get("path_template") or "")
    if not path.startswith("/admin/qamus/shadow/"):
        _err(errors, "%s.path_template must start with /admin/qamus/shadow/" % prefix)
    lowered = json.dumps(route, ensure_ascii=False).lower()
    for word in FORBIDDEN_ROUTE_WORDS:
        if word in lowered:
            _err(errors, "%s contains forbidden route/public token %r" % (prefix, word))
    address_types = route.get("input_address_types") or []
    if not isinstance(address_types, list) or not address_types:
        _err(errors, "%s.input_address_types must be a non-empty array" % prefix)
    for address_type in address_types:
        if address_type not in ADDRESS_TYPES:
            _err(errors, "%s has unknown address type %r" % (prefix, address_type))
    fields = route.get("output_pack_fields") or []
    if not isinstance(fields, list) or not fields:
        _err(errors, "%s.output_pack_fields must be a non-empty array" % prefix)


def validate_contract(contract):
    errors = []
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    if not isinstance(contract, dict):
        return ["contract must be an object"]
    expected = {
        "version": "qamus-shadow-admin-route-contract@1",
        "source_pack_version": "qamus-shadow-admin-debug-pack@1",
        "route_surface": "read_only_admin_debug",
        "public_exposable": False,
        "live_mutation_allowed": False,
        "requires_auth": True,
        "admin_only": True,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            _err(errors, "%s must be %r" % (key, value))
    validate_identity_policy(contract.get("identity_policy"), errors)
    validate_route_defaults(contract.get("route_defaults"), errors)
    validate_public_boundary(contract.get("public_boundary"), errors, "public_boundary")

    routes = contract.get("routes") or []
    if not isinstance(routes, list):
        _err(errors, "routes must be an array")
        routes = []
    if not routes:
        _err(errors, "routes must be non-empty")
    seen_views = set()
    seen_ids = set()
    for index, route in enumerate(routes):
        validate_route(route, index, errors)
        route_id = route.get("route_id")
        if route_id in seen_ids:
            _err(errors, "duplicate route_id %r" % route_id)
        seen_ids.add(route_id)
        if route.get("view"):
            seen_views.add(route.get("view"))
    missing = sorted(REQUIRED_VIEWS - seen_views)
    if missing:
        _err(errors, "routes missing required views %s" % missing)
    return errors


def validate(path):
    if not os.path.exists(path):
        return 0, ["missing route contract: %s" % path]
    try:
        contract = load_json(path)
    except Exception as exc:
        return 0, ["bad JSON: %s" % exc]
    return 1, validate_contract(contract)


def self_test():
    with tempfile.TemporaryDirectory(prefix="shadow-admin-route-contract-") as td:
        good = load_json(SAMPLE)
        good_path = os.path.join(td, "good.json")
        dump_json(good_path, good)
        count, errors = validate(good_path)
        if count != 1 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1

        bad = copy.deepcopy(good)
        bad["routes"][0]["method"] = "POST"
        bad["routes"][0]["path_template"] = "/admin/qamus/shadow/hover/:wbw_loc/apply"
        bad["routes"][0]["read_only"] = False
        bad["identity_policy"]["raw_surface_identity_allowed"] = True
        bad["live_mutation_allowed"] = True
        bad_path = os.path.join(td, "bad.json")
        dump_json(bad_path, bad)
        count, errors = validate(bad_path)
        if count != 1:
            print("SELF-TEST FAIL bad count:", count)
            return 1
        required_fragments = (
            "method must be GET",
            "read_only must be true",
            "raw_surface_identity_allowed",
            "live_mutation_allowed must be False",
            "forbidden route/public token",
        )
        joined = "\n".join(errors)
        missing = [fragment for fragment in required_fragments if fragment not in joined]
        if missing:
            print("SELF-TEST FAIL bad missing %r: %s" % (missing, errors))
            return 1
    print("PASS — shadow admin route contract validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate read-only Qamus shadow admin route contract JSON.")
    parser.add_argument("json", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.json:
        parser.error("json path is required unless --self-test is used")
    count, errors = validate(args.json)
    print("checked %d shadow admin route contract files" % count)
    if errors:
        for err in errors:
            print("ERROR:", err)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
