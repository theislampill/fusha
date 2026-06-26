#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Phase 4 exact-addressed gloss adjudication responses."""
import argparse
import io
import json
import os
import re
import tempfile

import validate_phase4_gloss_adjudication_requests as request_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-gloss-adjudication-response.schema.json")
RESP = re.compile(r"^phase4-gloss-adjudication-response:queue_parse_[0-9a-f]+$")
REQ = re.compile(r"^phase4-gloss-adjudication:queue_parse_[0-9a-f]+$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
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
)
REQUIRED = [
    "id",
    "phase",
    "source_adjudication_request_id",
    "parse_id",
    "identity",
    "decision",
    "selected_concise_authored_gloss",
    "selection_source",
    "adjudication_reason",
    "safe_scope_after_adjudication",
    "public_boundary",
    "apply_policy",
]


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except Exception as exc:
                yield line_no, {"__json_error__": str(exc)}


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(value):
    return " ".join(str(value or "").strip().split())


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def public_text_leaks(value):
    text = compact(value).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def public_boundary_errors(boundary):
    errors = []
    if not isinstance(boundary, dict):
        return ["public_boundary must be an object"]
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_text_allowed": False,
        "external_source_names_public_allowed": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            errors.append("public_boundary.%s must be %r" % (key, value))
    blob = json.dumps(boundary, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in blob:
            errors.append("public_boundary leaks forbidden label %r" % label)
    return errors


def read_requests(path):
    count, errors = request_validator.validate(path)
    if errors:
        raise ValueError("adjudication request packet failed validation before response validation: %s" % errors[:20])
    rows = {}
    for _line_no, row in iter_jsonl(path):
        rows[row["id"]] = row
    return rows


def validate_row(row, line_no, errors, requests=None):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    source_id = str(row.get("source_adjudication_request_id") or "")
    parse_id = str(row.get("parse_id") or "")
    if not RESP.match(row_id):
        _err(errors, line_no, "id must be phase4-gloss-adjudication-response:queue_parse_<hash>")
    if not REQ.match(source_id):
        _err(errors, line_no, "source_adjudication_request_id must be phase4-gloss-adjudication:queue_parse_<hash>")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    if row_id and source_id and row_id != source_id.replace("phase4-gloss-adjudication:", "phase4-gloss-adjudication-response:"):
        _err(errors, line_no, "id must derive from source_adjudication_request_id")
    if parse_id and source_id and source_id != "phase4-gloss-adjudication:queue_%s" % parse_id.replace(":", "_"):
        _err(errors, line_no, "source_adjudication_request_id must derive from parse_id")

    if row.get("phase") != "phase4_gloss_adjudication_response":
        _err(errors, line_no, "phase must be phase4_gloss_adjudication_response")
    if row.get("decision") != "select":
        _err(errors, line_no, "decision must be select")
    if row.get("selection_source") not in ("candidate", "new_authored"):
        _err(errors, line_no, "selection_source must be candidate or new_authored")
    if row.get("safe_scope_after_adjudication") not in ("token_only", "parse_family_after_impact_preview", "pending"):
        _err(errors, line_no, "safe_scope_after_adjudication is invalid")

    identity = row.get("identity") or {}
    if not isinstance(identity, dict):
        _err(errors, line_no, "identity must be an object")
        identity = {}
    quran_locs = identity.get("quran_locs") or []
    wbw_locs = identity.get("wbw_locs") or []
    if not quran_locs:
        _err(errors, line_no, "identity.quran_locs must be non-empty")
    if not wbw_locs:
        _err(errors, line_no, "identity.wbw_locs must be non-empty")
    if len(quran_locs) != len(wbw_locs):
        _err(errors, line_no, "quran_locs and wbw_locs must have matching counts")
    for loc in quran_locs:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad quran loc %r" % loc)
    for loc in wbw_locs:
        if not WBW.match(str(loc)):
            _err(errors, line_no, "bad wbw loc %r" % loc)
    if identity.get("parse_id") != parse_id:
        _err(errors, line_no, "identity.parse_id must match parse_id")

    gloss = compact(row.get("selected_concise_authored_gloss"))
    if not gloss:
        _err(errors, line_no, "selected_concise_authored_gloss must be non-empty")
    leaks = public_text_leaks(gloss)
    if leaks:
        _err(errors, line_no, "selected_concise_authored_gloss leaks forbidden label %r" % leaks[0])
    if not compact(row.get("adjudication_reason")):
        _err(errors, line_no, "adjudication_reason must be non-empty")
    reason_leaks = public_text_leaks(row.get("adjudication_reason"))
    if reason_leaks:
        _err(errors, line_no, "adjudication_reason leaks forbidden label %r" % reason_leaks[0])

    if requests is not None:
        request = requests.get(source_id)
        if request is None:
            _err(errors, line_no, "source_adjudication_request_id is not present in request packet")
        else:
            if parse_id != request.get("parse_id"):
                _err(errors, line_no, "parse_id does not match request")
            if identity != request.get("identity"):
                _err(errors, line_no, "identity does not match request")
            if row.get("public_boundary") != request.get("public_boundary"):
                _err(errors, line_no, "public_boundary does not match request")
            if row.get("apply_policy") != request.get("apply_policy"):
                _err(errors, line_no, "apply_policy does not match request")
            if row.get("selection_source") == "candidate":
                choices = {compact(item) for item in (request.get("candidate_glosses") or [])}
                if gloss not in choices:
                    _err(errors, line_no, "candidate selection must match one request candidate_gloss")

    for msg in public_boundary_errors(row.get("public_boundary")):
        _err(errors, line_no, msg)
    policy = row.get("apply_policy") or {}
    if not isinstance(policy, dict):
        _err(errors, line_no, "apply_policy must be an object")
        policy = {}
    for key in ("apply_allowed", "live_mutation_allowed", "closure_claim_allowed",
                "component_candidates_can_certify", "raw_surface_identity_allowed",
                "parse_key_primary_identity"):
        if policy.get(key) is not False:
            _err(errors, line_no, "apply_policy.%s must be false" % key)
    if "quran:S:A:W" not in str(policy.get("identity") or ""):
        _err(errors, line_no, "apply_policy.identity must preserve exact token identity")


def validate(path, request_path=None):
    errors = []
    count = 0
    requests = None
    if request_path:
        try:
            requests = read_requests(request_path)
        except ValueError as exc:
            errors.append(str(exc))
            requests = {}
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors, requests=requests)
    if count == 0:
        errors.append("zero Phase 4 gloss adjudication response rows")
    return count, errors


def sample_row():
    request = request_validator.sample_row()
    return {
        "id": request["id"].replace("phase4-gloss-adjudication:", "phase4-gloss-adjudication-response:"),
        "phase": "phase4_gloss_adjudication_response",
        "source_adjudication_request_id": request["id"],
        "parse_id": request["parse_id"],
        "identity": request["identity"],
        "decision": "select",
        "selected_concise_authored_gloss": request["candidate_glosses"][0],
        "selection_source": "candidate",
        "adjudication_reason": "Preserves the visible preposition relation without over-specifying context.",
        "safe_scope_after_adjudication": "token_only",
        "public_boundary": request["public_boundary"],
        "apply_policy": request["apply_policy"],
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-gloss-adjudication-response-validate-") as td:
        req_path = os.path.join(td, "requests.jsonl")
        resp_path = os.path.join(td, "responses.jsonl")
        request_validator.write_jsonl(req_path, [request_validator.sample_row()])
        write_jsonl(resp_path, [sample_row()])
        count, errors = validate(resp_path, request_path=req_path)
        if count != 1 or errors:
            print("SELF-TEST FAIL:", errors)
            return 1
        bad = sample_row()
        bad["selected_concise_authored_gloss"] = "QAC says with fairness"
        write_jsonl(resp_path, [bad])
        _count, errors = validate(resp_path, request_path=req_path)
        if not any("selected_concise_authored_gloss leaks forbidden label" in err for err in errors):
            print("SELF-TEST FAIL: expected public leak rejection")
            return 1
    print("PASS — Phase 4 gloss adjudication response validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("responses_jsonl", nargs="?")
    parser.add_argument("--requests")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.responses_jsonl:
        parser.error("responses_jsonl is required unless --self-test is used")
    count, errors = validate(args.responses_jsonl, request_path=args.requests)
    print("checked %d Phase 4 gloss adjudication response rows" % count)
    if errors:
        print("FAIL")
        for err in errors:
            print("- %s" % err)
        raise SystemExit(1)
    print("PASS — Phase 4 gloss adjudication responses are exact-addressed and review-only")


if __name__ == "__main__":
    main()
