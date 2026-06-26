#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build exact-addressed Phase 4 two-vote request packets.

Input is a validated Phase 4 dry-run closure tranche. Output is internal review
material only: no live mutation, no WBW rebuild, no coverage claim.
"""
import argparse
import io
import json
import os
import tempfile

import validate_phase4_closure_tranche as tranche_validator
import validate_phase4_two_vote_requests as request_validator


PUBLIC_BOUNDARY = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "external_text_allowed": False,
    "external_source_names_public_allowed": False,
}
APPLY_POLICY = {
    "apply_allowed": False,
    "live_mutation_allowed": False,
    "closure_claim_allowed": False,
    "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
    "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
    "component_candidates_can_certify": False,
    "raw_surface_identity_allowed": False,
    "parse_key_primary_identity": False,
}
REQUESTED_OUTPUT = {
    "decision": "approve | reject | pending",
    "concise_authored_gloss": "",
    "sarf_reasoning": "",
    "nahw_reasoning": "",
    "reason_agreement_key": "",
    "blocker_if_rejected": "",
    "safe_scope_after_vote": "token_only | parse_family_after_impact_preview | pending",
}
NO_CERTIFY = [
    "component_candidates",
    "rich_wbw_segment_candidates",
    "raw_surface",
    "norm_only",
    "parse_key_alone",
]


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


def request_id(source_tranche_id):
    return source_tranche_id.replace("phase4-tranche:", "phase4-two-vote:")


def _component_roles(candidate_evidence):
    roles = []
    for join in (candidate_evidence.get("component_candidate_joins") or []):
        for item in (join.get("join_status") or []):
            if isinstance(item, str) and item.startswith("role:"):
                roles.append(item.split(":", 1)[1])
    return set(roles)


def agreement_key_hint(tranche_row):
    """Return the review-only reason key both votes must use if approving."""
    evidence = tranche_row.get("candidate_evidence") or {}
    roles = _component_roles(evidence)
    gate_reasons = set(tranche_row.get("gate_reasons") or [])
    surface = ((tranche_row.get("identity") or {}).get("surface_sample") or "")

    if "grammar_trigger:vocative" in gate_reasons or {"vocative_particle", "addressee_bridge"} <= roles:
        return "vocative-particle-addressee-bridge"
    if "grammar_trigger:preposition" in gate_reasons or "preposition" in roles:
        return "preposition-governed-nominal-manner"
    if "grammar_trigger:adjectival_state" in gate_reasons:
        return "accusative-adjectival-state"
    if "result_particle" in roles or surface.startswith("ف"):
        return "result-particle-active-verb-object-suffix"
    if "resumption_particle" in roles:
        return "resumption-passive-verb-clause"
    if "grammar_trigger:suffix_pronoun" in gate_reasons or "object_pronoun" in roles:
        return "verb-object-suffix-explicit-subject"
    if "conjunction" in roles and ("definite_article" in roles or surface.startswith("وَٱل")):
        return "conj-definite-noun-coordinated-list"
    role_slug = "-".join(sorted(roles)) or "unknown"
    return "two-vote-required-%s" % role_slug.replace("_", "-")


def request_row(tranche_row):
    evidence = tranche_row.get("candidate_evidence") or {}
    return {
        "id": request_id(tranche_row["id"]),
        "phase": "phase4_two_vote_request",
        "source_tranche_id": tranche_row["id"],
        "parse_id": tranche_row["parse_id"],
        "lane": "two_vote_required",
        "required_gate": "two_vote_required",
        "allowed_next_step": "two_vote_review_only",
        "identity": tranche_row["identity"],
        "candidate_evidence": {
            "whole_token_candidates": evidence.get("whole_token_candidates") or [],
            "whole_token_candidate_joins": evidence.get("whole_token_candidate_joins") or [],
            "component_candidates": evidence.get("component_candidates") or [],
            "component_candidate_joins": evidence.get("component_candidate_joins") or [],
            "component_candidates_can_certify": False,
        },
        "gate_reasons": tranche_row.get("gate_reasons") or [],
        "required_evidence": tranche_row.get("required_evidence") or [],
        "vote_lenses": ["sarf-primary", "nahw-primary"],
        "agreement_key_hint": agreement_key_hint(tranche_row),
        "requested_output": dict(REQUESTED_OUTPUT),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "apply_policy": dict(APPLY_POLICY),
        "cannot_certify_from": list(NO_CERTIFY),
    }


def build_rows(tranche_path):
    count, errors = tranche_validator.validate(tranche_path)
    if errors:
        raise SystemExit("Phase 4 tranche failed validation before two-vote request build:\n- %s" % "\n- ".join(errors[:20]))
    rows = []
    for row in iter_jsonl(tranche_path):
        if row.get("lane") == "two_vote_required" and row.get("required_gate") == "two_vote_required":
            rows.append(request_row(row))
    return count, rows


def build_requests(tranche_path, out_jsonl):
    source_count, rows = build_rows(tranche_path)
    write_jsonl(out_jsonl, rows)
    count, errors = request_validator.validate(out_jsonl)
    if errors:
        raise SystemExit("built Phase 4 two-vote requests failed validation:\n- %s" % "\n- ".join(errors[:20]))
    return {
        "source_tranche_rows": source_count,
        "rows": count,
        "component_candidate_rows": sum(1 for row in rows if row["candidate_evidence"]["component_candidates"]),
        "auto_safe_rows": sum(1 for row in rows if row.get("required_gate") != "two_vote_required" or row.get("lane") != "two_vote_required"),
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
    }


def self_test():
    rows = tranche_validator.sample_rows()
    with tempfile.TemporaryDirectory(prefix="phase4-two-vote-build-") as td:
        tranche = os.path.join(td, "tranche.jsonl")
        out = os.path.join(td, "requests.jsonl")
        write_jsonl(tranche, rows)
        summary = build_requests(tranche, out)
        if summary["rows"] != 1:
            print("SELF-TEST FAIL: expected 1 two-vote request, got %d" % summary["rows"])
            return 1
        built = list(iter_jsonl(out))
        if built[0]["candidate_evidence"]["component_candidates_can_certify"] is not False:
            print("SELF-TEST FAIL: component candidates can certify")
            return 1
        if built[0]["required_gate"] != "two_vote_required":
            print("SELF-TEST FAIL: two-vote request gate weakened")
            return 1
        if built[0].get("agreement_key_hint") != "conj-definite-noun-coordinated-list":
            print("SELF-TEST FAIL: missing stable agreement key hint")
            return 1
    print("PASS — Phase 4 two-vote request builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tranche_jsonl", nargs="?")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.tranche_jsonl:
        parser.error("tranche_jsonl is required unless --self-test is used")
    out = args.out_jsonl
    if not out:
        base = os.path.splitext(args.tranche_jsonl)[0]
        out = base + ".two-vote-requests.jsonl"
    summary = build_requests(args.tranche_jsonl, out)
    summary["out_jsonl"] = out
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 two-vote requests built for internal review")


if __name__ == "__main__":
    main()
