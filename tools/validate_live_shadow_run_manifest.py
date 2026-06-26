#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the Phase 2 live-readonly shadow graph run manifest.

The manifest is the non-mutating receipt for a shadow build: exact input
artifacts, output isolation, no-write flags, graph counts, public/private
boundary, and detector-maturity warnings. It does not read live Qamus and does
not validate the graph rows themselves; pair it with validate_phase1_shadow_graph.
"""
import argparse
import io
import json
import os
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "live-shadow-run-manifest.schema.json")
DETECTOR_MATURITY = {
    "two_vote_required": "partial_shadow_gate",
    "source_disagreement": "reserved_detector_gap",
    "zero_count_policy": "zero_does_not_prove_absence",
}
EXPECTED_SECTIONS = {"noun": 1045, "verb": 947, "particle": 100}
FORBIDDEN_PUBLIC_LABELS = (
    "informed_by_public",
    "mcp_public",
    "qac_public",
    "quran.com_public",
    "ocr_public",
    "source-photo_public",
    "source_photo_public",
)


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def _err(errors, msg):
    errors.append(msg)


def input_by_role(row):
    return {item.get("role"): item for item in row.get("input_artifacts") or []}


def validate(row, expect_live_counts=False):
    errors = []
    warnings = []
    if not os.path.exists(SCHEMA):
        _err(errors, "schema missing: %s" % SCHEMA)
    if row.get("schema_version") != "qamus-live-shadow-run-manifest@1":
        _err(errors, "schema_version must be qamus-live-shadow-run-manifest@1")
    if row.get("builder") != "tools/build_live_shadow_graph.py":
        _err(errors, "builder must be tools/build_live_shadow_graph.py")

    run_mode = row.get("run_mode")
    if run_mode not in ("fixture", "live_readonly"):
        _err(errors, "run_mode must be fixture or live_readonly")
    if row.get("no_live_write") is not True:
        _err(errors, "no_live_write must be true")
    for field in ("live_mutation_allowed", "wbw_rebuild_allowed", "service_restart_allowed", "mirror_sync_allowed"):
        if row.get(field) is not False:
            _err(errors, "%s must be false" % field)
    if run_mode == "live_readonly" and row.get("fixture_mode") is not False:
        _err(errors, "live_readonly run must have fixture_mode=false")
    if run_mode == "fixture" and row.get("fixture_mode") is not True:
        _err(errors, "fixture run must have fixture_mode=true")
    if row.get("live_readonly") is not True:
        _err(errors, "live_readonly must be true")

    identity = row.get("identity_hierarchy") or {}
    expected_identity = {
        "quran_token": "quran:S:A:W",
        "hover_slot": "wbw:S:A:W",
        "entry": "qamus:*",
        "decision": "decision:*",
        "parse_family": "parse:<hash>",
        "parse_key_primary_identity": False,
        "raw_surface_identity_allowed": False,
        "norm_only_certification_allowed": False,
    }
    for key, expected in sorted(expected_identity.items()):
        if identity.get(key) != expected:
            _err(errors, "identity_hierarchy.%s must be %r" % (key, expected))

    inputs = input_by_role(row)
    for role in ("entries_dir", "wbw_json", "decision_ledger"):
        if role not in inputs:
            _err(errors, "missing input_artifacts role %s" % role)
            continue
        item = inputs[role]
        if item.get("required") is True and item.get("exists") is not True:
            _err(errors, "required input %s must exist" % role)
        if item.get("exists") is True:
            if not item.get("sha256"):
                _err(errors, "existing input %s must have sha256" % role)
            if item.get("bytes") is None:
                _err(errors, "existing input %s must have bytes" % role)

    guard = row.get("output_guard") or {}
    if guard.get("output_inside_forbidden_root") is not False:
        _err(errors, "output_guard.output_inside_forbidden_root must be false")
    if guard.get("overwrite_refused_for_existing_artifacts") is not True:
        _err(errors, "output_guard.overwrite_refused_for_existing_artifacts must be true")

    counts = row.get("counts") or {}
    required_counts = ("entries", "token_universe", "live_word_records", "token_decisions", "parse_keys",
                       "unresolved_tokens", "orphan_edges", "public_success_leak_count")
    for key in required_counts:
        if not isinstance(counts.get(key), int):
            _err(errors, "counts.%s must be an integer" % key)
    if counts.get("orphan_edges") != 0:
        _err(errors, "counts.orphan_edges must be 0")
    if counts.get("public_success_leak_count") != 0:
        _err(errors, "counts.public_success_leak_count must be 0")
    if isinstance(counts.get("token_universe"), int) and isinstance(counts.get("live_word_records"), int):
        expected_unresolved = counts["token_universe"] - counts["live_word_records"]
        if counts.get("unresolved_tokens") != expected_unresolved:
            _err(errors, "counts.unresolved_tokens must equal token_universe-live_word_records")
    if not counts.get("parse_family_classes"):
        _err(errors, "counts.parse_family_classes must be non-empty")
    if expect_live_counts:
        if counts.get("entries") != 2092:
            _err(errors, "live entries count must be 2092")
        if counts.get("sections") != EXPECTED_SECTIONS:
            _err(errors, "live section split must be %r" % EXPECTED_SECTIONS)
        if counts.get("token_universe") != 49900:
            _err(errors, "live token_universe must be 49900")

    boundary = row.get("public_boundary") or {}
    if boundary.get("src") != "qamus" or boundary.get("kind") != "authored" or boundary.get("lang") != "en":
        _err(errors, "public_boundary must be src=qamus kind=authored lang=en")
    if boundary.get("external_source_names_public") is not False:
        _err(errors, "external_source_names_public must be false")
    if boundary.get("internal_provenance_public") is not False:
        _err(errors, "internal_provenance_public must be false")
    public_blob = json.dumps(boundary, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in public_blob:
            _err(errors, "public boundary leaks forbidden public label %s" % label)

    scan = row.get("public_readback_scan") or {}
    if scan.get("status") == "public_readback_scanned":
        if scan.get("leak_count") != 0:
            _err(errors, "public_readback_scan leak_count must be 0")
    elif scan.get("status") == "not_run_by_builder":
        if scan.get("leak_count") is not None:
            _err(errors, "public_readback_scan leak_count must be null when not run by builder")
        warnings.append("public readback scan not run by builder; run scan_public_boundary.py for HTTP proof")
    else:
        _err(errors, "public_readback_scan.status must be not_run_by_builder or public_readback_scanned")

    if row.get("detector_maturity") != DETECTOR_MATURITY:
        _err(errors, "detector_maturity must preserve two-vote/source-disagreement detector-gap warnings")

    artifacts = row.get("artifacts_written") or []
    if not artifacts:
        _err(errors, "artifacts_written must be non-empty")
    for item in artifacts:
        if item.get("exists") is not True:
            _err(errors, "artifact %r must exist" % item.get("name"))
        if not item.get("sha256"):
            _err(errors, "artifact %r must have sha256" % item.get("name"))
        if not isinstance(item.get("bytes"), int) or item.get("bytes") <= 0:
            _err(errors, "artifact %r must have positive bytes" % item.get("name"))

    return errors, warnings


def sample_manifest():
    return read_json(os.path.join(ROOT, "qamus", "examples", "live_shadow_run_manifest.sample.json"))


def self_test():
    with tempfile.TemporaryDirectory(prefix="shadow-manifest-") as td:
        good = os.path.join(td, "good.json")
        bad = os.path.join(td, "bad.json")
        row = sample_manifest()
        write_json(good, row)
        bad_row = dict(row)
        bad_row["identity_hierarchy"] = dict(row["identity_hierarchy"])
        bad_row["identity_hierarchy"]["parse_key_primary_identity"] = True
        write_json(bad, bad_row)
        for path, should_pass in ((good, True), (bad, False)):
            errors, _warnings = validate(read_json(path))
            if should_pass and errors:
                print("SELF-TEST FAIL good:", errors)
                return 1
            if not should_pass and not any("parse_key_primary_identity" in err for err in errors):
                print("SELF-TEST FAIL bad:", errors)
                return 1
    print("PASS — live shadow run manifest validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--expect-live-counts", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        parser.error("path is required unless --self-test is used")
    row = read_json(args.path)
    errors, warnings = validate(row, expect_live_counts=args.expect_live_counts)
    for warning in warnings:
        print("WARN:", warning)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — live shadow run manifest is read-only, exact-addressed, and non-vacuous")


if __name__ == "__main__":
    main()
