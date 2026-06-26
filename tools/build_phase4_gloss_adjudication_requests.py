#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build owner/scholar adjudication packets for Phase 4 gloss wording blockers."""
import argparse
import io
import json
import os
import tempfile

import validate_phase4_gloss_adjudication_requests as validator


PUBLIC_BOUNDARY = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "external_text_allowed": False,
    "external_source_names_public_allowed": False,
}
REQUESTED_OUTPUT = {
    "selected_concise_authored_gloss": "",
    "adjudication_reason": "",
    "safe_scope_after_adjudication": "token_only | parse_family_after_impact_preview | pending",
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


def request_id(source_two_vote_request_id):
    return source_two_vote_request_id.replace("phase4-two-vote:", "phase4-gloss-adjudication:")


def unique_compact(values):
    out = []
    seen = set()
    for value in values:
        text = compact(value)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def adjudication_row(unresolved):
    summaries = unresolved.get("vote_summaries") or []
    approved = [row for row in summaries if row.get("decision") == "approve"]
    glosses = unique_compact(row.get("gloss") for row in approved)
    reason_keys = unique_compact(row.get("reason_agreement_key") for row in approved)
    source_id = unresolved["source_request_id"]
    policy = dict(unresolved.get("apply_policy") or {})
    policy["apply_allowed"] = False
    policy["live_mutation_allowed"] = False
    policy["closure_claim_allowed"] = False
    policy["component_candidates_can_certify"] = False
    policy["raw_surface_identity_allowed"] = False
    policy["parse_key_primary_identity"] = False
    policy.setdefault("identity", "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity")
    policy.setdefault("public_boundary", "src=qamus, kind=authored, lang=en; no external provenance")
    return {
        "id": request_id(source_id),
        "phase": "phase4_gloss_adjudication_request",
        "source_two_vote_request_id": source_id,
        "source_unresolved_reason": unresolved.get("unresolved_reason"),
        "parse_id": unresolved["parse_id"],
        "identity": unresolved["identity"],
        "candidate_glosses": glosses,
        "shared_reason_agreement_key": reason_keys[0] if len(reason_keys) == 1 else "",
        "vote_summaries": summaries,
        "allowed_next_step": "owner_or_scholar_gloss_adjudication_only",
        "requested_output": dict(REQUESTED_OUTPUT),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "apply_policy": policy,
    }


def build_rows(unresolved_path):
    rows = []
    for row in iter_jsonl(unresolved_path):
        if row.get("unresolved_reason") == "gloss_wording_disagreement":
            rows.append(adjudication_row(row))
    return rows


def build_requests(unresolved_path, out_jsonl):
    rows = build_rows(unresolved_path)
    write_jsonl(out_jsonl, rows)
    count, errors = validator.validate(out_jsonl)
    if errors:
        raise SystemExit("built Phase 4 gloss adjudication requests failed validation:\n- %s" %
                         "\n- ".join(errors[:20]))
    return {
        "rows": count,
        "source_unresolved_rows": sum(1 for _ in iter_jsonl(unresolved_path)),
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
    }


def self_test():
    unresolved = {
        "phase": "phase4_two_vote_unresolved",
        "source_request_id": "phase4-two-vote:queue_parse_e5e4e1aeb56a7fdd636257b0",
        "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
        "identity": {
            "quran_locs": ["quran:2:178:22"],
            "wbw_locs": ["wbw:2:178:22"],
            "parse_id": "parse:e5e4e1aeb56a7fdd636257b0",
            "surface_sample": "بِٱلْمَعْرُوفِ",
        },
        "unresolved_reason": "gloss_wording_disagreement",
        "vote_summaries": [
            {"lens": "sarf-primary", "decision": "approve", "gloss": "in a recognized manner",
             "reason_agreement_key": "preposition-governed-nominal-manner", "blocker_if_rejected": ""},
            {"lens": "nahw-primary", "decision": "approve", "gloss": "with recognized fairness",
             "reason_agreement_key": "preposition-governed-nominal-manner", "blocker_if_rejected": ""},
        ],
        "apply_policy": {
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "closure_claim_allowed": False,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
            "component_candidates_can_certify": False,
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
        },
    }
    with tempfile.TemporaryDirectory(prefix="phase4-gloss-adjudication-build-") as td:
        source = os.path.join(td, "unresolved.jsonl")
        out = os.path.join(td, "adjudication.jsonl")
        write_jsonl(source, [unresolved])
        summary = build_requests(source, out)
        if summary["rows"] != 1:
            print("SELF-TEST FAIL: expected 1 adjudication row")
            return 1
        row = list(iter_jsonl(out))[0]
        if row["candidate_glosses"] != ["in a recognized manner", "with recognized fairness"]:
            print("SELF-TEST FAIL: candidate glosses were not preserved")
            return 1
        if row["apply_policy"]["apply_allowed"] is not False:
            print("SELF-TEST FAIL: adjudication request must remain non-applying")
            return 1
    print("PASS — Phase 4 gloss adjudication request builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("unresolved_jsonl", nargs="?")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.unresolved_jsonl:
        parser.error("unresolved_jsonl is required unless --self-test is used")
    out = args.out_jsonl
    if not out:
        base = os.path.splitext(args.unresolved_jsonl)[0]
        out = base + ".gloss-adjudication-requests.jsonl"
    summary = build_requests(args.unresolved_jsonl, out)
    summary["out_jsonl"] = out
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 gloss adjudication requests built for internal review")


if __name__ == "__main__":
    main()
