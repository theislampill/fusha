#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan a read-only Phase 4 closure tranche from a shadow review pack.

This script does not author hovers, mutate live Qamus, rebuild WBW, or claim
coverage. It only turns already-validated review-pack rows into a bounded,
exact-addressed review tranche for the next executor.
"""
import argparse
import io
import json
import os
import tempfile

import validate_phase4_closure_tranche as tranche_validator
import validate_shadow_review_pack as review_validator


DEFAULT_LANES = [
    "two_vote_required",
    "token_only_required",
    "propagation_safe_candidate",
    "missing_entry",
]
LANE_PRIORITY = {
    "two_vote_required": 10,
    "token_only_required": 20,
    "propagation_safe_candidate": 30,
    "missing_entry": 40,
    "human_review_required": 50,
    "unknown_parse": 60,
    "quarantine_collision": 70,
    "source_disagreement": 80,
    "never_auto": 90,
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


def required_evidence(row):
    lane = row.get("lane")
    if lane == "two_vote_required":
        return [
            "two independent sarf/nahw checks agreeing on conclusion and reason",
            "exact quran:S:A:W and wbw:S:A:W trace",
            "public hover remains qamus/authored/en",
        ]
    if lane == "token_only_required":
        return [
            "exact token-only override target",
            "proof no parse-family propagation is intended",
            "last-wins append-only decision plan before apply",
        ]
    if lane == "propagation_safe_candidate":
        return [
            "exact whole-token candidate join",
            "family impact preview before any apply",
            "targeted public no-leak readback plan",
        ]
    if lane == "missing_entry":
        return [
            "owner-approved entry or mapping target",
            "no hover decision until entry/sense identity exists",
            "affected token list preserved",
        ]
    if lane == "unknown_parse":
        return [
            "sarf/nahw parse enrichment",
            "no norm-only certification",
            "rerun parse-key validator after enrichment",
        ]
    if lane in {"quarantine_collision", "source_disagreement", "never_auto", "human_review_required"}:
        return [
            "human review resolves blocker before any edit",
            "no family propagation while blocker remains",
            "exact affected token list preserved",
        ]
    return [
        "lane-specific review before any edit",
        "exact affected token list preserved",
        "public boundary remains source-clean",
    ]


def candidate_address(candidate):
    if isinstance(candidate, dict):
        return candidate.get("entry_address") or candidate.get("entry")
    return candidate


def candidate_addresses(candidates):
    result = []
    seen = set()
    for candidate in candidates or []:
        entry = candidate_address(candidate)
        if entry and entry not in seen:
            result.append(entry)
            seen.add(entry)
    return result


def tranche_row(review_row, priority):
    parse_id = review_row["parse_id"]
    row_id = review_row["id"]
    return {
        "id": "phase4-tranche:%s" % row_id.replace(":", "_"),
        "phase": "phase4_dry_run",
        "source_review_pack_id": row_id,
        "parse_id": parse_id,
        "lane": review_row.get("lane"),
        "priority": priority,
        "allowed_next_step": "review_only",
        "scope": review_row.get("scope"),
        "recommended_action": review_row.get("recommended_action"),
        "required_gate": review_row.get("required_gate"),
        "required_evidence": required_evidence(review_row),
        "impact_preview_required": True,
        "identity": {
            "quran_locs": review_row.get("quran_locs") or [],
            "wbw_locs": review_row.get("wbw_locs") or [],
            "parse_id": parse_id,
            "surface_sample": review_row.get("surface_sample") or "",
        },
        "candidate_evidence": {
            "whole_token_candidates": candidate_addresses(review_row.get("candidate_entries") or []),
            "whole_token_candidate_joins": review_row.get("candidate_join_statuses") or [],
            "component_candidates": candidate_addresses(review_row.get("component_candidate_entries") or []),
            "component_candidate_joins": review_row.get("component_candidate_join_statuses") or [],
        },
        "gate_reasons": review_row.get("gate_reasons") or [],
        "apply_policy": APPLY_POLICY,
    }


def plan(review_pack_path, lanes=None, max_rows=None):
    count, errors = review_validator.validate(review_pack_path)
    if errors:
        raise SystemExit("review pack failed validation before tranche planning:\n- %s" % "\n- ".join(errors[:20]))
    wanted = set(lanes or DEFAULT_LANES)
    selected = []
    for row in iter_jsonl(review_pack_path):
        lane = row.get("lane")
        if lane in wanted:
            selected.append(row)
    selected.sort(key=lambda r: (LANE_PRIORITY.get(r.get("lane"), 999), -int(r.get("family_size") or 0), r.get("parse_id") or ""))
    if max_rows is not None:
        selected = selected[:max_rows]
    return [tranche_row(row, idx + 1) for idx, row in enumerate(selected)]


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-tranche-plan-") as td:
        review_pack = os.path.join(td, "review-pack.jsonl")
        rows = [
            review_validator.component_enriched_two_vote_row(),
            review_validator.propagation_preview_row(),
            review_validator.never_auto_row(),
        ]
        rows[1]["candidate_entries"] = [
            {
                "entry_address": "qamus:n:earth",
                "entry_id": "earth",
                "sense_id": 1,
                "source": "usage_form",
            }
        ]
        if candidate_addresses([{"entry_address": "qamus:p:waw"}, {"entry": "qamus:n:tree"}]) != ["qamus:p:waw", "qamus:n:tree"]:
            print("SELF-TEST FAIL: rich candidate object normalization failed")
            return 1
        write_jsonl(review_pack, rows)
        out_rows = plan(review_pack, lanes=["two_vote_required", "propagation_safe_candidate"])
        if len(out_rows) != 2:
            print("SELF-TEST FAIL: expected 2 tranche rows, got %d" % len(out_rows))
            return 1
        if out_rows[0]["lane"] != "two_vote_required":
            print("SELF-TEST FAIL: two-vote lane should be prioritized")
            return 1
        if out_rows[0]["candidate_evidence"]["component_candidates"] and out_rows[0]["required_gate"] != "two_vote_required":
            print("SELF-TEST FAIL: component candidates weakened gate")
            return 1
        for row in out_rows:
            evidence = row["candidate_evidence"]
            for field in ("whole_token_candidates", "component_candidates"):
                if any(isinstance(candidate, dict) for candidate in evidence[field]):
                    print("SELF-TEST FAIL: %s leaked rich candidate objects" % field)
                    return 1
        if any(row["apply_policy"]["apply_allowed"] for row in out_rows):
            print("SELF-TEST FAIL: dry-run tranche allowed apply")
            return 1
        out_path = os.path.join(td, "tranche.jsonl")
        write_jsonl(out_path, out_rows)
        count, errors = tranche_validator.validate(out_path)
        if count != 2 or errors:
            print("SELF-TEST FAIL: validator rejected planner output", errors)
            return 1
    print("PASS — Phase 4 dry-run closure tranche planner self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("review_pack_jsonl", nargs="?")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--lane", action="append", help="review-pack lane to include; may be repeated")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.review_pack_jsonl:
        parser.error("review_pack_jsonl is required unless --self-test is used")
    rows = plan(args.review_pack_jsonl, lanes=args.lane, max_rows=args.max_rows)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, rows)
    print(json.dumps({
        "rows": len(rows),
        "lanes": sorted({row["lane"] for row in rows}),
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
    }, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 dry-run closure tranche planned")


if __name__ == "__main__":
    main()
