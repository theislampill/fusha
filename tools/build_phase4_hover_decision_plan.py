#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build review-only Phase 4 hover decision plan rows from certified rows.

This emits exact-addressed previews for a future append-only token-decision
apply lane. It does not write live Qamus data, rebuild artifacts, claim
coverage, or certify any row beyond the upstream review status.
"""
import argparse
import io
import json
import os
import tempfile


APPLY_POLICY = {
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
}


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path, rows):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(value):
    return " ".join(str(value or "").strip().split())


def bare_wbw_loc(wbw_loc):
    if not str(wbw_loc).startswith("wbw:"):
        raise ValueError("bad wbw loc: %r" % wbw_loc)
    return str(wbw_loc).replace("wbw:", "", 1)


def parse_hash(parse_id):
    if not str(parse_id).startswith("parse:"):
        raise ValueError("bad parse id: %r" % parse_id)
    return str(parse_id).replace("parse:", "", 1)


def source_ids(row):
    phase = row.get("phase")
    if phase == "phase4_two_vote_reconciled":
        ids = [row.get("source_request_id")]
        ids.extend(row.get("vote_response_ids") or [])
        return [item for item in ids if item]
    if phase == "phase4_gloss_adjudication_reconciled":
        ids = [
            row.get("source_adjudication_request_id"),
            row.get("source_two_vote_request_id"),
            row.get("adjudication_response_id"),
        ]
        return [item for item in ids if item]
    return []


def source_certified_id(row):
    if row.get("phase") == "phase4_two_vote_reconciled":
        return row.get("source_request_id")
    if row.get("phase") == "phase4_gloss_adjudication_reconciled":
        return row.get("source_adjudication_request_id")
    return None


def safe_scope(row):
    if row.get("phase") == "phase4_two_vote_reconciled":
        return row.get("safe_scope_after_vote")
    if row.get("phase") == "phase4_gloss_adjudication_reconciled":
        return row.get("safe_scope_after_adjudication")
    return None


def plan_rows_from_certified(row):
    if row.get("status") != "certified_not_applied":
        return []
    if row.get("phase") not in ("phase4_two_vote_reconciled", "phase4_gloss_adjudication_reconciled"):
        return []
    parse_id = row.get("parse_id")
    identity = row.get("identity") or {}
    quran_locs = identity.get("quran_locs") or []
    wbw_locs = identity.get("wbw_locs") or []
    if len(quran_locs) != len(wbw_locs) or not quran_locs:
        raise ValueError("certified row has mismatched or empty quran/wbw locs: %s" % row.get("source_request_id", row.get("source_adjudication_request_id")))
    hover = row.get("public_hover") or {}
    gloss = compact(hover.get("gloss"))
    if not gloss:
        raise ValueError("certified row has empty public_hover.gloss")
    ids = source_ids(row)
    primary_id = source_certified_id(row)
    if not primary_id or primary_id not in ids:
        raise ValueError("certified row lacks stable source id")
    scope = safe_scope(row)
    plans = []
    for quran_loc, wbw_loc in zip(quran_locs, wbw_locs):
        bare_loc = bare_wbw_loc(wbw_loc)
        plans.append({
            "id": "phase4-hover-decision-plan:%s:%s" % (bare_loc.replace(":", "_"), parse_hash(parse_id)),
            "phase": "phase4_hover_decision_plan",
            "source_phase": row["phase"],
            "source_certified_id": primary_id,
            "source_certified_ids": ids,
            "status": "planned_not_applied",
            "parse_id": parse_id,
            "identity": {
                "quran_loc": quran_loc,
                "wbw_loc": wbw_loc,
                "parse_id": parse_id,
                "surface_sample": identity.get("surface_sample", ""),
            },
            "public_hover": {
                "gloss": gloss,
                "src": "qamus",
                "kind": "authored",
                "lang": "en",
            },
            "token_decision_preview": {
                "loc": bare_loc,
                "gloss": gloss,
                "src": "qamus",
                "kind": "authored",
                "lang": "en",
            },
            "safe_scope": scope,
            "reason_agreement_key": compact(row.get("reason_agreement_key")),
            "apply_policy": dict(APPLY_POLICY),
        })
    return plans


def build_plan(certified_jsonl, out_jsonl):
    rows = []
    source_rows = 0
    for row in iter_jsonl(certified_jsonl):
        source_rows += 1
        rows.extend(plan_rows_from_certified(row))
    write_jsonl(out_jsonl, rows)
    return {
        "source_rows": source_rows,
        "planned_rows": len(rows),
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
        "status": "planned_not_applied",
    }


def sample_certified_rows():
    return [
        {
            "phase": "phase4_two_vote_reconciled",
            "source_request_id": "phase4-two-vote:queue_parse_c0ffee12",
            "parse_id": "parse:c0ffee12",
            "identity": {
                "quran_locs": ["quran:22:18:17"],
                "wbw_locs": ["wbw:22:18:17"],
                "parse_id": "parse:c0ffee12",
                "surface_sample": "وَٱلشَّجَرُ",
            },
            "public_hover": {"gloss": "and + the trees", "src": "qamus", "kind": "authored", "lang": "en"},
            "vote_response_ids": [
                "phase4-two-vote-response:queue_parse_c0ffee12:sarf-primary",
                "phase4-two-vote-response:queue_parse_c0ffee12:nahw-primary",
            ],
            "reason_agreement_key": "conj-definite-noun-coordinated-list",
            "safe_scope_after_vote": "token_only",
            "public_boundary": {"src": "qamus", "kind": "authored", "lang": "en", "external_text_allowed": False, "external_source_names_public_allowed": False},
            "apply_policy": {"apply_allowed": False, "live_mutation_allowed": False, "closure_claim_allowed": False},
            "component_candidates_used_as_certification": False,
            "status": "certified_not_applied",
        },
        {
            "phase": "phase4_gloss_adjudication_reconciled",
            "source_adjudication_request_id": "phase4-gloss-adjudication:queue_parse_e5e4e1aeb56a7fdd636257b0",
            "source_two_vote_request_id": "phase4-two-vote:queue_parse_e5e4e1aeb56a7fdd636257b0",
            "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
            "identity": {
                "quran_locs": ["quran:2:178:22"],
                "wbw_locs": ["wbw:2:178:22"],
                "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
                "surface_sample": "بِٱلْمَعْرُوفِ",
            },
            "public_hover": {"gloss": "in a recognized manner", "src": "qamus", "kind": "authored", "lang": "en"},
            "adjudication_response_id": "phase4-gloss-adjudication-response:queue_parse_e5e4e1aeb56a7fdd636257b0",
            "selection_source": "candidate",
            "adjudication_reason": "Preserves the bāʾ manner relation without over-specifying context.",
            "reason_agreement_key": "preposition-governed-nominal-manner",
            "safe_scope_after_adjudication": "token_only",
            "public_boundary": {"src": "qamus", "kind": "authored", "lang": "en", "external_text_allowed": False, "external_source_names_public_allowed": False},
            "apply_policy": {"apply_allowed": False, "live_mutation_allowed": False, "closure_claim_allowed": False},
            "status": "certified_not_applied",
        },
    ]


def self_test():
    import validate_phase4_hover_decision_plan as validator

    with tempfile.TemporaryDirectory(prefix="phase4-hover-decision-plan-build-") as td:
        certified_path = os.path.join(td, "certified.jsonl")
        plan_path = os.path.join(td, "plan.jsonl")
        write_jsonl(certified_path, sample_certified_rows())
        summary = build_plan(certified_path, plan_path)
        if summary["planned_rows"] != 2:
            print("SELF-TEST FAIL:", summary)
            return 1
        count, errors = validator.validate(plan_path)
        if count != 2 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
    print("PASS — Phase 4 hover decision plan builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("certified_jsonl", nargs="?")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.certified_jsonl:
        parser.error("certified_jsonl is required unless --self-test is used")
    out_path = args.out_jsonl or os.path.splitext(args.certified_jsonl)[0] + ".hover-decision-plan.jsonl"
    summary = build_plan(args.certified_jsonl, out_path)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 hover decision plan built for internal review only")


if __name__ == "__main__":
    main()
