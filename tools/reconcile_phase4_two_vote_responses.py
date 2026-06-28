#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile Phase 4 exact-addressed two-vote responses.

This is a review gate only. Certified rows remain unapplied until a separate
owner-gated apply path with backup, rebuild, validation, health check, and
public readback exists.
"""
import argparse
import collections
import io
import json
import os
import sys

import validate_phase4_two_vote_requests as request_validator
import validate_phase4_two_vote_responses as response_validator


LENSES = ["sarf-primary", "nahw-primary"]


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


def read_requests(path):
    count, errors = request_validator.validate(path)
    if errors:
        raise ValueError("request packet failed validation: %s" % errors[:20])
    return {row["id"]: row for row in iter_jsonl(path)}


def read_responses(path, request_path):
    count, errors = response_validator.validate(path, request_path=request_path)
    if errors:
        raise ValueError("response packet failed validation: %s" % errors[:20])
    rows = list(iter_jsonl(path))
    grouped = collections.defaultdict(dict)
    for row in rows:
        source_id = row["source_request_id"]
        lens = row["lens"]
        if lens in grouped[source_id]:
            raise ValueError("duplicate response lens for %s/%s" % (source_id, lens))
        grouped[source_id][lens] = row
    return rows, grouped


def unresolved_row(request, responses, reason):
    return {
        "phase": "phase4_two_vote_unresolved",
        "source_request_id": request["id"],
        "parse_id": request["parse_id"],
        "identity": request["identity"],
        "unresolved_reason": reason,
        "responses_seen": sorted(responses),
        "vote_summaries": [
            {
                "lens": row.get("lens"),
                "decision": row.get("decision"),
                "gloss": compact(row.get("concise_authored_gloss")),
                "reason_agreement_key": compact(row.get("reason_agreement_key")),
                "blocker_if_rejected": compact(row.get("blocker_if_rejected")),
            }
            for row in responses.values()
        ],
        "apply_policy": request["apply_policy"],
    }


def certified_row(request, responses):
    sarf = responses["sarf-primary"]
    nahw = responses["nahw-primary"]
    gloss = compact(sarf.get("concise_authored_gloss"))
    row = {
        "phase": "phase4_two_vote_reconciled",
        "source_request_id": request["id"],
        "parse_id": request["parse_id"],
        "identity": request["identity"],
        "public_hover": {
            "gloss": gloss,
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "vote_response_ids": [sarf["id"], nahw["id"]],
        "reason_agreement_key": compact(sarf.get("reason_agreement_key")),
        "safe_scope_after_vote": sarf.get("safe_scope_after_vote"),
        "public_boundary": request["public_boundary"],
        "apply_policy": request["apply_policy"],
        "component_candidates_used_as_certification": False,
        "status": "certified_not_applied",
    }
    if request.get("gloss_context") is not None:
        row["gloss_context"] = request["gloss_context"]
    return row


def disagreement_reason(sarf, nahw):
    same_gloss = compact(sarf.get("concise_authored_gloss")) == compact(nahw.get("concise_authored_gloss"))
    same_reason = compact(sarf.get("reason_agreement_key")) == compact(nahw.get("reason_agreement_key"))
    same_scope = sarf.get("safe_scope_after_vote") == nahw.get("safe_scope_after_vote")
    if same_reason and same_scope and not same_gloss:
        return "gloss_wording_disagreement"
    if same_gloss and same_scope and not same_reason:
        return "reason_disagreement"
    if same_gloss and same_reason and not same_scope:
        return "scope_disagreement"
    return "vote_disagreement"


def reconcile_one(request, responses):
    missing = [lens for lens in LENSES if lens not in responses]
    if missing:
        return None, unresolved_row(request, responses, "missing_vote")
    decisions = {lens: responses[lens].get("decision") for lens in LENSES}
    if decisions["sarf-primary"] != "approve" or decisions["nahw-primary"] != "approve":
        if decisions["sarf-primary"] == "pending" and decisions["nahw-primary"] == "pending":
            return None, unresolved_row(request, responses, "both_votes_pending")
        if decisions["sarf-primary"] == "reject" and decisions["nahw-primary"] == "reject":
            return None, unresolved_row(request, responses, "both_votes_rejected")
        return None, unresolved_row(request, responses, "vote_disagreement")
    sarf = responses["sarf-primary"]
    nahw = responses["nahw-primary"]
    same_gloss = compact(sarf.get("concise_authored_gloss")) == compact(nahw.get("concise_authored_gloss"))
    same_reason = compact(sarf.get("reason_agreement_key")) == compact(nahw.get("reason_agreement_key"))
    same_scope = sarf.get("safe_scope_after_vote") == nahw.get("safe_scope_after_vote")
    if not (same_gloss and same_reason and same_scope):
        return None, unresolved_row(request, responses, disagreement_reason(sarf, nahw))
    return certified_row(request, responses), None


def reconcile_files(request_path, response_path, certified_path, unresolved_path):
    requests = read_requests(request_path)
    responses, grouped = read_responses(response_path, request_path)
    certified = []
    unresolved = []
    for request_id in sorted(requests):
        row, problem = reconcile_one(requests[request_id], grouped.get(request_id, {}))
        if row:
            certified.append(row)
        else:
            unresolved.append(problem)
    write_jsonl(certified_path, certified)
    write_jsonl(unresolved_path, unresolved)
    return {
        "requests": len(requests),
        "responses": len(responses),
        "certified_rows": len(certified),
        "unresolved_rows": len(unresolved),
        "apply_allowed": False,
        "live_mutation_allowed": False,
        "closure_claim_allowed": False,
        "status": "reconciled_not_applied",
    }


def self_test():
    import build_phase4_two_vote_requests as request_builder
    import validate_phase4_closure_tranche as tranche_validator
    import tempfile

    with tempfile.TemporaryDirectory(prefix="phase4-two-vote-reconcile-") as td:
        tranche = os.path.join(td, "tranche.jsonl")
        requests_path = os.path.join(td, "requests.jsonl")
        responses_path = os.path.join(td, "responses.jsonl")
        certified_path = os.path.join(td, "certified.jsonl")
        unresolved_path = os.path.join(td, "unresolved.jsonl")
        write_jsonl(tranche, tranche_validator.sample_rows())
        request_builder.build_requests(tranche, requests_path)
        request = next(iter_jsonl(requests_path))
        base = response_validator.sample_row()
        responses = []
        for lens in LENSES:
            row = dict(base)
            row["lens"] = lens
            row["id"] = "%s:%s" % (request["id"].replace("phase4-two-vote:", "phase4-two-vote-response:"), lens)
            row["source_request_id"] = request["id"]
            row["parse_id"] = request["parse_id"]
            row["identity"] = request["identity"]
            row["public_boundary"] = request["public_boundary"]
            responses.append(row)
        write_jsonl(responses_path, responses)
        summary = reconcile_files(requests_path, responses_path, certified_path, unresolved_path)
        if summary["certified_rows"] != 1 or summary["unresolved_rows"] != 0:
            print("SELF-TEST FAIL:", summary)
            return 1
    print("PASS — Phase 4 two-vote response reconciler self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests")
    parser.add_argument("--responses")
    parser.add_argument("--certified-out")
    parser.add_argument("--unresolved-out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    missing = [name for name in ("requests", "responses", "certified_out", "unresolved_out") if not getattr(args, name)]
    if missing:
        parser.error("missing required args: %s" % ", ".join("--%s" % m.replace("_", "-") for m in missing))
    try:
        summary = reconcile_files(args.requests, args.responses, args.certified_out, args.unresolved_out)
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(1)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 two-vote responses reconciled for internal review")


if __name__ == "__main__":
    main()
