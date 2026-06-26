#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile Phase 4 gloss adjudication responses into certified-not-applied rows."""
import argparse
import collections
import io
import json
import os
import tempfile

import validate_phase4_gloss_adjudication_requests as request_validator
import validate_phase4_gloss_adjudication_responses as response_validator


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
        raise ValueError("adjudication request packet failed validation: %s" % errors[:20])
    return {row["id"]: row for row in iter_jsonl(path)}


def read_responses(path, request_path):
    count, errors = response_validator.validate(path, request_path=request_path)
    if errors:
        raise ValueError("adjudication response packet failed validation: %s" % errors[:20])
    rows = list(iter_jsonl(path))
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row["source_adjudication_request_id"]].append(row)
    return rows, grouped


def unresolved_row(request, reason, responses=None):
    return {
        "phase": "phase4_gloss_adjudication_unresolved",
        "source_adjudication_request_id": request["id"],
        "source_two_vote_request_id": request["source_two_vote_request_id"],
        "parse_id": request["parse_id"],
        "identity": request["identity"],
        "unresolved_reason": reason,
        "responses_seen": [row["id"] for row in (responses or [])],
        "candidate_glosses": request["candidate_glosses"],
        "apply_policy": request["apply_policy"],
    }


def certified_row(request, response):
    gloss = compact(response.get("selected_concise_authored_gloss"))
    return {
        "phase": "phase4_gloss_adjudication_reconciled",
        "source_adjudication_request_id": request["id"],
        "source_two_vote_request_id": request["source_two_vote_request_id"],
        "parse_id": request["parse_id"],
        "identity": request["identity"],
        "public_hover": {
            "gloss": gloss,
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        },
        "adjudication_response_id": response["id"],
        "selection_source": response["selection_source"],
        "adjudication_reason": compact(response.get("adjudication_reason")),
        "reason_agreement_key": request["shared_reason_agreement_key"],
        "safe_scope_after_adjudication": response["safe_scope_after_adjudication"],
        "public_boundary": request["public_boundary"],
        "apply_policy": request["apply_policy"],
        "status": "certified_not_applied",
    }


def reconcile_one(request, responses):
    if not responses:
        return None, unresolved_row(request, "missing_adjudication_response")
    if len(responses) > 1:
        return None, unresolved_row(request, "multiple_adjudication_responses", responses)
    response = responses[0]
    return certified_row(request, response), None


def reconcile_files(request_path, response_path, certified_path, unresolved_path):
    requests = read_requests(request_path)
    responses, grouped = read_responses(response_path, request_path)
    certified = []
    unresolved = []
    for request_id in sorted(requests):
        row, problem = reconcile_one(requests[request_id], grouped.get(request_id, []))
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
    request = request_validator.sample_row()
    response = response_validator.sample_row()
    with tempfile.TemporaryDirectory(prefix="phase4-gloss-adjudication-reconcile-") as td:
        request_path = os.path.join(td, "requests.jsonl")
        response_path = os.path.join(td, "responses.jsonl")
        certified_path = os.path.join(td, "certified.jsonl")
        unresolved_path = os.path.join(td, "unresolved.jsonl")
        write_jsonl(request_path, [request])
        write_jsonl(response_path, [response])
        summary = reconcile_files(request_path, response_path, certified_path, unresolved_path)
        if summary["certified_rows"] != 1 or summary["unresolved_rows"] != 0:
            print("SELF-TEST FAIL:", summary)
            return 1
        row = list(iter_jsonl(certified_path))[0]
        if row["status"] != "certified_not_applied":
            print("SELF-TEST FAIL: certified row must remain not applied")
            return 1
        if row["apply_policy"]["apply_allowed"] is not False:
            print("SELF-TEST FAIL: apply must remain false")
            return 1
    print("PASS — Phase 4 gloss adjudication response reconciler self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", required=False)
    parser.add_argument("--responses", required=False)
    parser.add_argument("--certified-out")
    parser.add_argument("--unresolved-out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.requests or not args.responses:
        parser.error("--requests and --responses are required unless --self-test is used")
    certified = args.certified_out or os.path.splitext(args.responses)[0] + ".certified.jsonl"
    unresolved = args.unresolved_out or os.path.splitext(args.responses)[0] + ".unresolved.jsonl"
    summary = reconcile_files(args.requests, args.responses, certified, unresolved)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 gloss adjudication responses reconciled for internal review")


if __name__ == "__main__":
    main()
