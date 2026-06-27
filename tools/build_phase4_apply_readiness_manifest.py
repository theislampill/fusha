#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a review-only Phase 4 apply-readiness manifest.

The manifest is a source-side preflight contract for a future owner-gated
apply lane. It does not write live Qamus data, rebuild WBW artifacts, restart
services, or claim hover coverage.
"""
import argparse
import hashlib
import io
import json
import os
import tempfile


REQUIRED_GATES = {
    "append_only_ledger": "A future apply must append last-wins token decisions; it must not rewrite unrelated rows.",
    "backup": "A future apply must identify a rollback artifact before any live write.",
    "rebuild": "A future apply must rebuild the derived hover artifact from the append-only ledger.",
    "validation": "A future apply must run token-decision, public-boundary, and exact-address validators.",
    "health_check": "A future apply must prove the service/app health check after rebuild.",
    "targeted_public_readback": "A future apply must read back affected public pages and exact hover payloads.",
    "public_boundary_scan": "A future apply must prove zero public provenance leakage.",
    "rollback_rehearsal": "A future apply must have an explicit rollback command or append-only revert path.",
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
    "\\srv\\",
)


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, row):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(row, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def compact(value):
    return " ".join(str(value or "").strip().split())


def plan_summary(plan_jsonl):
    rows = list(iter_jsonl(plan_jsonl))
    quran_locs = []
    wbw_locs = []
    parse_ids = []
    plan_ids = []
    sample_tokens = []
    for row in rows:
        identity = row.get("identity") or {}
        quran_loc = identity.get("quran_loc")
        wbw_loc = identity.get("wbw_loc")
        parse_id = row.get("parse_id") or identity.get("parse_id")
        plan_ids.append(row.get("id"))
        quran_locs.append(quran_loc)
        wbw_locs.append(wbw_loc)
        parse_ids.append(parse_id)
        if len(sample_tokens) < 8:
            sample_tokens.append({
                "plan_id": row.get("id"),
                "quran_loc": quran_loc,
                "wbw_loc": wbw_loc,
                "parse_id": parse_id,
                "surface_sample": identity.get("surface_sample", ""),
                "public_hover": row.get("public_hover") or {},
            })
    return {
        "row_count": len(rows),
        "plan_ids": [item for item in plan_ids if item],
        "quran_locs": [item for item in quran_locs if item],
        "wbw_locs": [item for item in wbw_locs if item],
        "parse_ids": [item for item in parse_ids if item],
        "sample_tokens": sample_tokens,
    }


def gate_rows():
    return {
        name: {
            "required": True,
            "status": "not_run",
            "evidence_required": evidence,
        }
        for name, evidence in sorted(REQUIRED_GATES.items())
    }


def excluded_tranche_summary(source_tranche_jsonl, plan_jsonl):
    if not source_tranche_jsonl:
        return None
    tranche_rows = list(iter_jsonl(source_tranche_jsonl))
    plan_parse_ids = set()
    plan_quran_locs = set()
    plan_wbw_locs = set()
    for row in iter_jsonl(plan_jsonl):
        identity = row.get("identity") or {}
        plan_parse_ids.add(row.get("parse_id") or identity.get("parse_id"))
        plan_quran_locs.add(identity.get("quran_loc"))
        plan_wbw_locs.add(identity.get("wbw_loc"))

    sample_excluded = []
    excluded_count = 0
    excluded_by_lane = {}
    excluded_by_gate = {}
    for row in tranche_rows:
        identity = row.get("identity") or {}
        parse_id = row.get("parse_id") or identity.get("parse_id")
        quran_locs = identity.get("quran_locs") or []
        wbw_locs = identity.get("wbw_locs") or []
        is_in_plan = (
            parse_id in plan_parse_ids
            or any(loc in plan_quran_locs for loc in quran_locs)
            or any(loc in plan_wbw_locs for loc in wbw_locs)
        )
        if is_in_plan:
            continue
        excluded_count += 1
        lane = row.get("lane") or "unknown"
        gate = row.get("required_gate") or "unknown"
        excluded_by_lane[lane] = excluded_by_lane.get(lane, 0) + 1
        excluded_by_gate[gate] = excluded_by_gate.get(gate, 0) + 1
        if len(sample_excluded) < 8:
            sample_excluded.append({
                "parse_id": parse_id,
                "surface_sample": identity.get("surface_sample", ""),
                "quran_locs": quran_locs,
                "wbw_locs": wbw_locs,
                "lane": lane,
                "required_gate": gate,
                "recommended_action": row.get("recommended_action", ""),
            })

    return {
        "source_tranche": {
            "artifact": os.path.basename(source_tranche_jsonl),
            "sha256": sha256_file(source_tranche_jsonl),
            "row_count": len(tranche_rows),
        },
        "excluded_count": excluded_count,
        "excluded_by_lane": dict(sorted(excluded_by_lane.items())),
        "excluded_by_gate": dict(sorted(excluded_by_gate.items())),
        "sample_excluded": sample_excluded,
    }


def build_manifest(plan_jsonl, out_json, source_tranche_jsonl=None):
    plan_sha = sha256_file(plan_jsonl)
    summary = plan_summary(plan_jsonl)
    manifest = {
        "id": "phase4-apply-readiness:%s" % plan_sha[:16],
        "phase": "phase4_apply_readiness_manifest",
        "status": "pre_apply_not_authorized",
        "generated_by": "tools/build_phase4_apply_readiness_manifest.py",
        "source_plan": {
            "artifact": os.path.basename(plan_jsonl),
            "sha256": plan_sha,
            "row_count": summary["row_count"],
            "plan_id_count": len(summary["plan_ids"]),
            "quran_loc_count": len(set(summary["quran_locs"])),
            "wbw_loc_count": len(set(summary["wbw_locs"])),
            "parse_id_count": len(set(summary["parse_ids"])),
        },
        "truth_owners": {
            "hover_decision_plan": "phase4_hover_decision_plan_jsonl",
            "live_wbw_lookup": "live_wbw_lookup_truth_owner_symbolic",
            "live_entries": "live_entries_truth_owner_symbolic",
            "token_decision_ledger": "live_token_decision_ledger_truth_owner_symbolic",
            "public_render": "public_http_readback_truth_owner_symbolic",
        },
        "apply_policy": {
            "apply_authorized": False,
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "wbw_rebuild_allowed": False,
            "service_restart_allowed": False,
            "mirror_sync_allowed": False,
            "closure_claim_allowed": False,
            "parse_key_primary_identity": False,
            "raw_surface_identity_allowed": False,
            "component_candidates_can_certify": False,
            "decision_plan_only": True,
        },
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_source_names_public": False,
            "internal_provenance_public": False,
        },
        "required_gates": gate_rows(),
        "abort_conditions": [
            "source plan validator fails",
            "source plan sha or row count changes unexpectedly",
            "append-only ledger target is missing",
            "backup or rollback artifact is missing",
            "derived WBW rebuild fails",
            "token-decision validation fails",
            "public-boundary scan reports a public leak",
            "health check fails",
            "targeted public readback mismatches intended hover",
            "repo or live HEAD moves during a gated apply",
        ],
        "rollback": {
            "required": True,
            "strategy": "append_only_revert_or_restore_backup",
            "status": "not_run",
        },
        "sample_tokens": summary["sample_tokens"],
    }
    excluded_summary = excluded_tranche_summary(source_tranche_jsonl, plan_jsonl)
    if excluded_summary:
        manifest["excluded_tranche_rows"] = excluded_summary
    write_json(out_json, manifest)
    return manifest


def sample_plan_row():
    return {
        "id": "phase4-hover-decision-plan:22_18_17:c0ffee12",
        "phase": "phase4_hover_decision_plan",
        "source_phase": "phase4_two_vote_reconciled",
        "source_certified_id": "phase4-two-vote:queue_parse_c0ffee12",
        "source_certified_ids": [
            "phase4-two-vote:queue_parse_c0ffee12",
            "phase4-two-vote-response:queue_parse_c0ffee12:sarf-primary",
            "phase4-two-vote-response:queue_parse_c0ffee12:nahw-primary",
        ],
        "status": "planned_not_applied",
        "parse_id": "parse:c0ffee12",
        "identity": {
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "parse_id": "parse:c0ffee12",
            "surface_sample": "وَٱلشَّجَرُ",
        },
        "public_hover": {
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "token_decision_preview": {
            "loc": "22:18:17",
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "safe_scope": "token_only",
        "reason_agreement_key": "conj-definite-noun-coordinated-list",
        "apply_policy": {
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "closure_claim_allowed": False,
            "append_only_ledger_required": True,
            "requires_backup_rebuild_health_readback_before_apply": True,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
            "component_candidates_can_certify": False,
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
        },
    }


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def self_test():
    import validate_phase4_apply_readiness_manifest as validator

    with tempfile.TemporaryDirectory(prefix="phase4-apply-readiness-build-") as td:
        plan = os.path.join(td, "plan.jsonl")
        manifest_path = os.path.join(td, "manifest.json")
        tranche = os.path.join(td, "tranche.jsonl")
        blocked = {
            "id": "phase4-tranche:queue_parse_333333333333333333333333",
            "parse_id": "parse:333333333333333333333333",
            "identity": {
                "quran_locs": ["quran:86:14:1"],
                "wbw_locs": ["wbw:86:14:1"],
                "parse_id": "parse:333333333333333333333333",
                "surface_sample": "وَمَا",
            },
            "lane": "quarantine_collision",
            "required_gate": "human_review_required",
            "recommended_action": "quarantine until candidate collision is resolved by exact-token nahw/sarf review",
        }
        write_jsonl(plan, [sample_plan_row()])
        write_jsonl(tranche, [blocked])
        manifest = build_manifest(plan, manifest_path, source_tranche_jsonl=tranche)
        if manifest["source_plan"]["row_count"] != 1:
            print("SELF-TEST FAIL: wrong row_count")
            return 1
        if manifest["excluded_tranche_rows"]["excluded_count"] != 1:
            print("SELF-TEST FAIL: wrong excluded_count")
            return 1
        count, errors = validator.validate(manifest_path, plan)
        if count != 1 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
    print("PASS — Phase 4 apply-readiness manifest builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan_jsonl", nargs="?")
    parser.add_argument("--out-json")
    parser.add_argument("--source-tranche-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.plan_jsonl:
        parser.error("plan_jsonl is required unless --self-test is used")
    out_path = args.out_json or os.path.splitext(args.plan_jsonl)[0] + ".apply-readiness.json"
    manifest = build_manifest(args.plan_jsonl, out_path, source_tranche_jsonl=args.source_tranche_jsonl)
    print(json.dumps({
        "manifest": out_path,
        "row_count": manifest["source_plan"]["row_count"],
        "excluded_tranche_rows": (manifest.get("excluded_tranche_rows") or {}).get("excluded_count", 0),
        "apply_authorized": manifest["apply_policy"]["apply_authorized"],
        "live_mutation_allowed": manifest["apply_policy"]["live_mutation_allowed"],
        "status": manifest["status"],
    }, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 apply-readiness manifest built for internal review only")


if __name__ == "__main__":
    main()
