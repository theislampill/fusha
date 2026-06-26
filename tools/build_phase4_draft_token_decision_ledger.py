#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a source-only Phase 4 draft token-decision ledger.

This converts validated hover decision plan rows into draft append-only token
decision rows for owner review. It does not write live Qamus data, rebuild WBW,
restart services, sync mirrors, or claim hover coverage.
"""
import argparse
import io
import json
import os
import tempfile


APPLY_POLICY = {
    "draft_only": True,
    "apply_allowed": False,
    "live_mutation_allowed": False,
    "closure_claim_allowed": False,
    "append_only_ledger_required": True,
    "backup_required": True,
    "rebuild_required": True,
    "validation_required": True,
    "health_check_required": True,
    "targeted_public_readback_required": True,
    "public_boundary_scan_required": True,
    "rollback_required": True,
    "component_candidates_can_certify": False,
    "raw_surface_identity_allowed": False,
    "parse_key_primary_identity": False,
}

PUBLIC_BOUNDARY = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "internal_provenance_public": False,
    "external_source_names_public": False,
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


def bare_loc(wbw_loc):
    if not str(wbw_loc).startswith("wbw:"):
        raise ValueError("bad wbw loc: %r" % wbw_loc)
    return str(wbw_loc).replace("wbw:", "", 1)


def parse_hash(parse_id):
    if not str(parse_id).startswith("parse:"):
        raise ValueError("bad parse id: %r" % parse_id)
    return str(parse_id).replace("parse:", "", 1)


def draft_id(plan_row):
    wbw_loc = ((plan_row.get("identity") or {}).get("wbw_loc"))
    parse_id = plan_row.get("parse_id")
    return "phase4-draft-token-decision:%s:%s" % (
        bare_loc(wbw_loc).replace(":", "_"),
        parse_hash(parse_id),
    )


def draft_row_from_plan(row):
    if row.get("phase") != "phase4_hover_decision_plan":
        return None
    if row.get("status") != "planned_not_applied":
        return None

    identity = row.get("identity") or {}
    preview = row.get("token_decision_preview") or {}
    public_hover = row.get("public_hover") or {}
    quran_loc = identity.get("quran_loc")
    wbw_loc = identity.get("wbw_loc")
    parse_id = row.get("parse_id")
    if preview.get("loc") != bare_loc(wbw_loc):
        raise ValueError("token_decision_preview.loc does not match wbw_loc for %s" % row.get("id"))
    for key in ("gloss", "src", "kind", "lang"):
        if preview.get(key) != public_hover.get(key):
            raise ValueError("preview %s does not match public_hover for %s" % (key, row.get("id")))
    if preview.get("src") != "qamus" or preview.get("kind") != "authored" or preview.get("lang") != "en":
        raise ValueError("token decision preview is not source-clean for %s" % row.get("id"))

    return {
        "id": draft_id(row),
        "phase": "phase4_draft_token_decision_ledger",
        "status": "draft_not_applied",
        "identity": {
            "quran_loc": quran_loc,
            "wbw_loc": wbw_loc,
            "parse_id": parse_id,
            "surface_sample": identity.get("surface_sample", ""),
        },
        "token_decision": {
            "loc": preview.get("loc"),
            "gloss": compact(preview.get("gloss")),
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "plan_lineage": {
            "source_plan_id": row.get("id"),
            "source_phase": row.get("source_phase"),
            "source_certified_id": row.get("source_certified_id"),
            "source_certified_ids": row.get("source_certified_ids") or [],
            "reason_agreement_key": compact(row.get("reason_agreement_key")),
        },
        "safe_scope": row.get("safe_scope"),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "apply_policy": dict(APPLY_POLICY),
    }


def build_draft_ledger(plan_jsonl, out_jsonl):
    rows = []
    source_rows = 0
    for row in iter_jsonl(plan_jsonl):
        source_rows += 1
        draft = draft_row_from_plan(row)
        if draft:
            rows.append(draft)
    write_jsonl(out_jsonl, rows)
    return {
        "source_plan_rows": source_rows,
        "draft_rows": len(rows),
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
        "status": "draft_not_applied",
    }


def self_test():
    import validate_phase4_draft_token_decision_ledger as validator

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plan = os.path.join(root, "qamus", "examples", "phase4_hover_decision_plan.sample.jsonl")
    with tempfile.TemporaryDirectory(prefix="phase4-draft-token-decision-build-") as td:
        out = os.path.join(td, "draft.jsonl")
        summary = build_draft_ledger(plan, out)
        if summary["draft_rows"] != 2:
            raise AssertionError(summary)
        count, errors = validator.validate(out, plan_jsonl=plan)
        if count != 2 or errors:
            raise AssertionError(errors)
    print("PASS — Phase 4 draft token-decision ledger builder self-test")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_jsonl", nargs="?")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.plan_jsonl or not args.out_jsonl:
        parser.error("plan_jsonl and --out-jsonl are required unless --self-test is used")
    summary = build_draft_ledger(args.plan_jsonl, args.out_jsonl)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 draft token-decision ledger built for owner-gated review only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
