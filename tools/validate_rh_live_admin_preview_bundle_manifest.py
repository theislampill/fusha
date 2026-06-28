#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the RH-LIVE-00 admin-preview bundle manifest.

This is a repo-only guard. It proves the RH-LIVE preview candidates, source
readiness, two-vote review artifacts, route contract, and reports describe one
exact-address packet. It does not inspect or mutate the live Qamus app.
"""
import argparse
import collections
import hashlib
import io
import json
import os
import tempfile

import validate_phase4_two_vote_requests as two_vote_requests
import validate_phase4_two_vote_responses as two_vote_responses
import validate_rh_live_preview_candidates as preview_candidates
import validate_rh_live_source_triangulation_readiness as source_readiness
import validate_shadow_admin_route_contract as route_contract


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "rh_live_00_admin_preview_bundle_manifest.sample.json")
FALSE_POLICY_FIELDS = (
    "component_candidates_can_certify",
    "hover_ledger_mutation_allowed",
    "live_mutation_allowed",
    "may_apply_live",
    "mirror_sync_allowed",
    "parse_key_primary_identity",
    "public_rollout_allowed",
    "service_restart_allowed",
    "wbw_rebuild_allowed",
)
FORBIDDEN_LABELS = (
    "informed_by",
    "qac",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
    "c:\\",
)


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                yield lineno, json.loads(line)


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(relpath):
    rel = str(relpath or "").replace("\\", "/")
    if os.path.isabs(rel) or rel.startswith("../") or "/../" in rel:
        raise ValueError("unsafe manifest path: %r" % relpath)
    return os.path.join(ROOT, rel)


def add(errors, message):
    errors.append(message)


def read_rows(relpath):
    path = repo_path(relpath)
    return [row for _lineno, row in iter_jsonl(path)]


def identity_pairs_from_preview(rows):
    return sorted((row.get("quran_loc"), row.get("wbw_loc")) for row in rows)


def identity_pairs_from_readiness(rows):
    return sorted((row.get("quran_loc"), row.get("wbw_loc")) for row in rows)


def identity_pairs_from_request(rows):
    pairs = []
    for row in rows:
        identity = row.get("identity") or {}
        quran = identity.get("quran_locs") or []
        wbw = identity.get("wbw_locs") or []
        pairs.extend(zip(quran, wbw))
    return sorted(pairs)


def identity_pairs_from_certified(rows):
    return identity_pairs_from_request(rows)


def request_id_for(row):
    return row.get("id")


def validate_hashes_and_counts(manifest, errors):
    artifacts = manifest.get("artifacts") or {}
    for name, artifact in sorted(artifacts.items()):
        relpath = artifact.get("path")
        if not relpath:
            add(errors, "artifacts.%s.path is required" % name)
            continue
        try:
            path = repo_path(relpath)
        except ValueError as exc:
            add(errors, str(exc))
            continue
        if not os.path.exists(path):
            add(errors, "artifacts.%s.path does not exist: %s" % (name, relpath))
            continue
        expected_sha = artifact.get("sha256")
        if expected_sha and sha256_file(path) != expected_sha:
            add(errors, "artifacts.%s.sha256 does not match current file" % name)
        if relpath.endswith(".jsonl") and "rows" in artifact:
            actual = sum(1 for _lineno, _row in iter_jsonl(path))
            if actual != artifact.get("rows"):
                add(errors, "artifacts.%s.rows expected %s got %s" % (name, artifact.get("rows"), actual))


def validate_policy(manifest, errors):
    if manifest.get("version") != "rh-live-admin-preview-bundle@1":
        add(errors, "version must be rh-live-admin-preview-bundle@1")
    if manifest.get("stage") != "RH-LIVE-00":
        add(errors, "stage must be RH-LIVE-00")
    if manifest.get("status") != "repo_only_admin_preview_bundle_not_live":
        add(errors, "status must be repo_only_admin_preview_bundle_not_live")
    policy = manifest.get("policy") or {}
    for field in FALSE_POLICY_FIELDS:
        if policy.get(field) is not False:
            add(errors, "policy.%s must be false" % field)
    if policy.get("owner_authorization_required") is not True:
        add(errors, "policy.owner_authorization_required must be true")
    boundary = manifest.get("public_boundary") or {}
    expected_boundary = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
    }
    for key, expected in expected_boundary.items():
        if boundary.get(key) != expected:
            add(errors, "public_boundary.%s must be %r" % (key, expected))
    public_blob = json.dumps({"policy": policy, "public_boundary": boundary}, ensure_ascii=False).lower()
    for label in FORBIDDEN_LABELS:
        if label in public_blob:
            add(errors, "manifest public/policy section leaks forbidden label: %s" % label)


def validate_route(manifest, errors):
    admin = manifest.get("admin_preview") or {}
    if admin.get("admin_only") is not True:
        add(errors, "admin_preview.admin_only must be true")
    if admin.get("route_view") != "rich_hover_preview":
        add(errors, "admin_preview.route_view must be rich_hover_preview")
    route_path = admin.get("route_contract_path")
    if not route_path:
        add(errors, "admin_preview.route_contract_path is required")
        return
    try:
        route_full = repo_path(route_path)
    except ValueError as exc:
        add(errors, str(exc))
        return
    contract = load_json(route_full)
    route_errors = route_contract.validate_contract(contract)
    for error in route_errors:
        add(errors, "route_contract: " + error)
    rich_routes = [row for row in contract.get("routes", []) if row.get("view") == "rich_hover_preview"]
    if len(rich_routes) != 1:
        add(errors, "route contract must contain exactly one rich_hover_preview route")
    elif rich_routes[0].get("read_only") is not True or rich_routes[0].get("public_payload_allowed") is not False:
        add(errors, "rich_hover_preview route must be read_only and non-public")


def validate_artifact_files(manifest, errors):
    artifacts = manifest.get("artifacts") or {}
    required = (
        "preview_candidates",
        "source_readiness",
        "two_vote_requests",
        "two_vote_responses",
        "certified_not_applied",
        "two_vote_unresolved",
    )
    missing = [name for name in required if name not in artifacts]
    if missing:
        add(errors, "missing artifacts: " + ", ".join(missing))
        return None

    preview_path = repo_path(artifacts["preview_candidates"]["path"])
    count, preview_errors = preview_candidates.validate_file(preview_path)
    for error in preview_errors:
        add(errors, "preview_candidates: " + error)
    if count != 9:
        add(errors, "preview_candidates must have 9 rows")

    readiness_path = repo_path(artifacts["source_readiness"]["path"])
    readiness_count, ready, retry, readiness_errors = source_readiness.validate_file(readiness_path)
    for error in readiness_errors:
        add(errors, "source_readiness: " + error)
    if readiness_count != 9 or ready != 9 or retry != 0:
        add(errors, "source_readiness must have 9 ready rows and 0 retry rows")

    request_path = repo_path(artifacts["two_vote_requests"]["path"])
    request_count, request_errors = two_vote_requests.validate(request_path)
    for error in request_errors:
        add(errors, "two_vote_requests: " + error)
    if request_count != 9:
        add(errors, "two_vote_requests must have 9 rows")

    response_path = repo_path(artifacts["two_vote_responses"]["path"])
    response_count, response_errors = two_vote_responses.validate(response_path, request_path=request_path)
    for error in response_errors:
        add(errors, "two_vote_responses: " + error)
    if response_count != 18:
        add(errors, "two_vote_responses must have 18 rows")

    certified_rows = read_rows(artifacts["certified_not_applied"]["path"])
    unresolved_rows = read_rows(artifacts["two_vote_unresolved"]["path"])
    if len(certified_rows) != 9:
        add(errors, "certified_not_applied must have 9 rows")
    if len(unresolved_rows) != 0:
        add(errors, "two_vote_unresolved must have 0 rows")
    for row in certified_rows:
        if row.get("status") != "certified_not_applied":
            add(errors, "certified row status must be certified_not_applied")
        if row.get("apply_policy", {}).get("apply_allowed") is not False:
            add(errors, "certified row must not be applyable")

    return {
        "preview": read_rows(artifacts["preview_candidates"]["path"]),
        "readiness": read_rows(artifacts["source_readiness"]["path"]),
        "requests": read_rows(artifacts["two_vote_requests"]["path"]),
        "responses": read_rows(artifacts["two_vote_responses"]["path"]),
        "certified": certified_rows,
        "unresolved": unresolved_rows,
    }


def validate_cross_artifact_identity(rows, errors):
    if rows is None:
        return
    preview_pairs = identity_pairs_from_preview(rows["preview"])
    readiness_pairs = identity_pairs_from_readiness(rows["readiness"])
    request_pairs = identity_pairs_from_request(rows["requests"])
    certified_pairs = identity_pairs_from_certified(rows["certified"])
    if preview_pairs != readiness_pairs:
        add(errors, "preview and source-readiness quran/wbw identities differ")
    if preview_pairs != request_pairs:
        add(errors, "preview and two-vote request quran/wbw identities differ")
    if preview_pairs != certified_pairs:
        add(errors, "preview and certified-not-applied quran/wbw identities differ")

    request_ids = {row.get("id") for row in rows["requests"]}
    readiness_locs = {row.get("wbw_loc") for row in rows["readiness"]}
    preview_locs = {row.get("wbw_loc") for row in rows["preview"]}
    if readiness_locs != preview_locs:
        add(errors, "preview and readiness wbw sets differ")

    grouped = collections.defaultdict(list)
    for row in rows["responses"]:
        grouped[row.get("source_request_id")].append(row)
    if set(grouped) != request_ids:
        add(errors, "response request ids do not match request packet ids")
    for request_id, response_rows in sorted(grouped.items()):
        lenses = sorted(row.get("lens") for row in response_rows)
        if lenses != ["nahw-primary", "sarf-primary"]:
            add(errors, "%s must have exactly sarf-primary and nahw-primary responses" % request_id)
        keys = {row.get("reason_agreement_key") for row in response_rows}
        decisions = {row.get("decision") for row in response_rows}
        if len(keys) != 1 or decisions != {"approve"}:
            add(errors, "%s responses must agree on reason and approve" % request_id)

    certified_request_ids = {row.get("source_request_id") for row in rows["certified"]}
    if certified_request_ids != request_ids:
        add(errors, "certified rows do not cover every request id")
    for row in rows["certified"]:
        if row.get("component_candidates_used_as_certification") is not False:
            add(errors, "certified rows must not use component candidates as certification")
        if row.get("safe_scope_after_vote") != "token_only":
            add(errors, "certified rows must remain token_only in this preview bundle")


def validate_reports(manifest, errors):
    artifacts = manifest.get("artifacts") or {}
    needles = {
        "preview_readiness_report": ("RH-LIVE-00 Preview Readiness", "Forbidden Without Separate Owner Gate"),
        "source_readiness_report": ("RH-LIVE-00 Source-Triangulation Readiness", "exact-address two-vote"),
        "two_vote_reconciliation_report": ("certified-not-applied rows | 9", "live mutation rows | 0"),
        "renderer_admin_plan": ("admin-only or feature-flagged preview", "normal public hover remains unchanged"),
    }
    for name, expected_needles in needles.items():
        artifact = artifacts.get(name)
        if not artifact:
            add(errors, "missing report artifact %s" % name)
            continue
        text = io.open(repo_path(artifact["path"]), encoding="utf-8").read()
        for needle in expected_needles:
            if needle not in text:
                add(errors, "%s missing report text: %s" % (name, needle))


def validate_manifest(path):
    manifest = load_json(path)
    errors = []
    validate_policy(manifest, errors)
    validate_hashes_and_counts(manifest, errors)
    validate_route(manifest, errors)
    rows = validate_artifact_files(manifest, errors)
    validate_cross_artifact_identity(rows, errors)
    validate_reports(manifest, errors)
    return errors


def self_test():
    errors = validate_manifest(SAMPLE)
    if errors:
        raise SystemExit("self-test failed: " + "; ".join(errors[:20]))
    manifest = load_json(SAMPLE)
    bad = json.loads(json.dumps(manifest))
    bad["policy"]["live_mutation_allowed"] = True
    with tempfile.TemporaryDirectory(prefix="rh-live-admin-preview-manifest-") as tmp:
        bad_path = os.path.join(tmp, "bad.json")
        write_json(bad_path, bad)
        bad_errors = validate_manifest(bad_path)
        if not any("policy.live_mutation_allowed must be false" in error for error in bad_errors):
            raise SystemExit("self-test failed: live mutation policy regression was not caught")
    print("RH-LIVE admin-preview bundle manifest self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.manifest:
        parser.error("provide at least one manifest JSON or --self-test")
    all_errors = []
    for path in args.manifest:
        all_errors.extend("%s: %s" % (path, error) for error in validate_manifest(path))
    if all_errors:
        for error in all_errors:
            print(error)
        return 1
    print("RH-LIVE admin-preview bundle manifest OK - files=%d" % len(args.manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
