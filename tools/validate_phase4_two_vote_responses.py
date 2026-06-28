#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate exact-addressed Phase 4 two-vote response rows."""
import argparse
import io
import json
import os
import re
import tempfile

import validate_phase4_two_vote_requests as request_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "phase4-two-vote-response.schema.json")
RESP = re.compile(r"^phase4-two-vote-response:queue_parse_[0-9a-f]+:(sarf-primary|nahw-primary)$")
REQUEST = re.compile(r"^phase4-two-vote:queue_parse_[0-9a-f]+$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
LENSES = {"sarf-primary", "nahw-primary"}
DECISIONS = {"approve", "reject", "pending"}
SAFE_SCOPES = {"token_only", "parse_family_after_impact_preview", "pending"}
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
CONTEXT_SOURCE_FIELDS = (
    "context_subject_source",
    "context_object_source",
    "context_governor_source",
    "context_attachment_source",
)
GLOSS_CONTEXT_FIELDS = (
    "token_contribution_gloss",
    "contextual_phrase_gloss",
    "context_subject_source",
    "context_object_source",
    "context_governor_source",
    "context_attachment_source",
    "adjacent_context_required",
    "adjacent_context_locs",
    "contextual_gloss_certification_state",
)
REQUIRED = [
    "id",
    "phase",
    "source_request_id",
    "parse_id",
    "lens",
    "decision",
    "identity",
    "concise_authored_gloss",
    "sarf_reasoning",
    "nahw_reasoning",
    "reason_agreement_key",
    "blocker_if_rejected",
    "safe_scope_after_vote",
    "public_boundary",
    "component_candidates_used_as_certification",
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


def read_requests(path):
    count, errors = request_validator.validate(path)
    if errors:
        raise ValueError("request packet failed validation before response validation: %s" % errors[:20])
    rows = {}
    for _line_no, row in iter_jsonl(path):
        rows[row["id"]] = row
    return rows


def compact(value):
    return " ".join(str(value or "").strip().split())


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


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


def public_text_leaks(value):
    text = compact(value).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def validate_gloss_context(row, line_no, errors):
    context = row.get("gloss_context")
    if context is None:
        return
    if not isinstance(context, dict):
        _err(errors, line_no, "gloss_context must be an object")
        return
    for field in GLOSS_CONTEXT_FIELDS:
        if field not in context:
            _err(errors, line_no, "gloss_context missing %s" % field)
    token_gloss = compact(context.get("token_contribution_gloss"))
    phrase_gloss = compact(context.get("contextual_phrase_gloss"))
    if not token_gloss:
        _err(errors, line_no, "gloss_context.token_contribution_gloss is required")
    if not phrase_gloss:
        _err(errors, line_no, "gloss_context.contextual_phrase_gloss is required")
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in token_gloss.lower() or label in phrase_gloss.lower():
            _err(errors, line_no, "gloss_context gloss leaks forbidden label %r" % label)
    differs = bool(token_gloss and phrase_gloss and token_gloss != phrase_gloss)
    locs = context.get("adjacent_context_locs")
    if locs is None:
        locs = []
    if not isinstance(locs, list):
        _err(errors, line_no, "gloss_context.adjacent_context_locs must be a list")
        locs = []
    for loc in locs:
        if not (QURAN.match(str(loc)) or WBW.match(str(loc))):
            _err(errors, line_no, "bad gloss_context adjacent loc %r" % loc)
    if differs:
        if context.get("adjacent_context_required") is not True:
            _err(errors, line_no, "contextual gloss that differs from token contribution requires adjacent_context_required=true")
        if not locs:
            _err(errors, line_no, "contextual gloss that differs from token contribution requires adjacent_context_locs")
        if not compact(context.get("contextual_gloss_certification_state")):
            _err(errors, line_no, "contextual gloss that differs from token contribution requires contextual_gloss_certification_state")
        if not any(compact(context.get(field)) for field in CONTEXT_SOURCE_FIELDS):
            _err(errors, line_no, "contextual gloss that differs from token contribution requires a context source field")
    elif context.get("adjacent_context_required") is not False:
        _err(errors, line_no, "matching token/context gloss must set adjacent_context_required=false")


def validate_row(row, line_no, errors, requests=None):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = str(row.get("id") or "")
    source_id = str(row.get("source_request_id") or "")
    lens = str(row.get("lens") or "")
    parse_id = str(row.get("parse_id") or "")
    if not RESP.match(row_id):
        _err(errors, line_no, "id must be phase4-two-vote-response:queue_parse_<hash>:<lens>")
    if not REQUEST.match(source_id):
        _err(errors, line_no, "source_request_id must be phase4-two-vote:queue_parse_<hash>")
    if lens not in LENSES:
        _err(errors, line_no, "lens must be sarf-primary or nahw-primary")
    if row_id and source_id and lens and row_id != "%s:%s" % (source_id.replace("phase4-two-vote:", "phase4-two-vote-response:"), lens):
        _err(errors, line_no, "id must derive from source_request_id and lens")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    if parse_id and source_id and source_id != "phase4-two-vote:queue_%s" % parse_id.replace(":", "_"):
        _err(errors, line_no, "source_request_id must derive from parse_id")

    if row.get("phase") != "phase4_two_vote_response":
        _err(errors, line_no, "phase must be phase4_two_vote_response")
    decision = row.get("decision")
    if decision not in DECISIONS:
        _err(errors, line_no, "decision must be approve, reject, or pending")
    if row.get("safe_scope_after_vote") not in SAFE_SCOPES:
        _err(errors, line_no, "safe_scope_after_vote is invalid")
    if row.get("component_candidates_used_as_certification") is not False:
        _err(errors, line_no, "component_candidates_used_as_certification must be false")

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

    if requests is not None:
        request = requests.get(source_id)
        if request is None:
            _err(errors, line_no, "source_request_id is not present in request packet")
        else:
            if lens not in request.get("vote_lenses", []):
                _err(errors, line_no, "lens was not requested")
            if parse_id != request.get("parse_id"):
                _err(errors, line_no, "parse_id does not match request")
            if identity != request.get("identity"):
                _err(errors, line_no, "identity does not match request")
            if row.get("public_boundary") != request.get("public_boundary"):
                _err(errors, line_no, "public_boundary does not match request")
            if request.get("gloss_context") is not None and row.get("gloss_context") != request.get("gloss_context"):
                _err(errors, line_no, "gloss_context does not match request")
            hint = compact(request.get("agreement_key_hint"))
            if row.get("decision") == "approve" and hint and compact(row.get("reason_agreement_key")) != hint:
                _err(errors, line_no, "reason_agreement_key must match request agreement_key_hint")
            style_hint = request.get("gloss_style_hint") or {}
            preferred_gloss = compact(style_hint.get("preferred_concise_authored_gloss"))
            if (
                row.get("decision") == "approve"
                and style_hint.get("required_when_approving") is True
                and preferred_gloss
                and compact(row.get("concise_authored_gloss")) != preferred_gloss
            ):
                _err(errors, line_no, "approved concise_authored_gloss must match request gloss_style_hint")
            request_context = request.get("gloss_context") or {}
            request_contextual = compact(request_context.get("contextual_phrase_gloss"))
            if row.get("decision") == "approve" and request_contextual and compact(row.get("concise_authored_gloss")) != request_contextual:
                _err(errors, line_no, "approved concise_authored_gloss must match request contextual_phrase_gloss")

    validate_gloss_context(row, line_no, errors)

    gloss = compact(row.get("concise_authored_gloss"))
    sarf_reasoning = compact(row.get("sarf_reasoning"))
    nahw_reasoning = compact(row.get("nahw_reasoning"))
    reason_key = compact(row.get("reason_agreement_key"))
    blocker = compact(row.get("blocker_if_rejected"))
    if decision == "approve":
        if not gloss:
            _err(errors, line_no, "approved response lacks concise_authored_gloss")
        leaks = public_text_leaks(gloss)
        if leaks:
            _err(errors, line_no, "public gloss leaks forbidden label %r" % leaks[0])
        if not sarf_reasoning:
            _err(errors, line_no, "approved response lacks sarf_reasoning")
        if not nahw_reasoning:
            _err(errors, line_no, "approved response lacks nahw_reasoning")
        if not reason_key:
            _err(errors, line_no, "approved response lacks reason_agreement_key")
        if row.get("safe_scope_after_vote") == "pending":
            _err(errors, line_no, "approved response cannot keep safe_scope_after_vote pending")
    else:
        if gloss:
            _err(errors, line_no, "%s response must not carry public gloss text" % decision)
        if reason_key:
            _err(errors, line_no, "%s response must not carry reason_agreement_key" % decision)
        if not blocker:
            _err(errors, line_no, "%s response lacks blocker_if_rejected" % decision)
    for msg in public_boundary_errors(row.get("public_boundary")):
        _err(errors, line_no, msg)


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
        errors.append("zero Phase 4 two-vote response rows")
    return count, errors


def sample_row():
    return {
        "id": "phase4-two-vote-response:queue_parse_c0ffee12:sarf-primary",
        "phase": "phase4_two_vote_response",
        "source_request_id": "phase4-two-vote:queue_parse_c0ffee12",
        "parse_id": "parse:c0ffee12",
        "lens": "sarf-primary",
        "decision": "approve",
        "identity": {
            "quran_locs": ["quran:22:18:17"],
            "wbw_locs": ["wbw:22:18:17"],
            "parse_id": "parse:c0ffee12",
            "surface_sample": "وَٱلشَّجَرُ",
        },
        "concise_authored_gloss": "and + the trees",
        "gloss_context": {
            "token_contribution_gloss": "and + the trees",
            "contextual_phrase_gloss": "and + the trees",
            "context_subject_source": None,
            "context_object_source": None,
            "context_governor_source": None,
            "context_attachment_source": None,
            "adjacent_context_required": False,
            "adjacent_context_locs": [],
            "contextual_gloss_certification_state": "word_level_or_token_internal",
        },
        "sarf_reasoning": "Visible conjunction/article/host composition is preserved.",
        "nahw_reasoning": "The prefixed waw is a grammar-bearing function piece in context.",
        "reason_agreement_key": "conj-definite-noun-coordinated-list",
        "blocker_if_rejected": "",
        "safe_scope_after_vote": "token_only",
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
        "component_candidates_used_as_certification": False,
    }


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def self_test():
    with tempfile.TemporaryDirectory(prefix="phase4-two-vote-response-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        row = sample_row()
        write_jsonl(good, [row])
        count, errors = validate(good)
        if count != 1 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        bad_row = dict(row)
        bad_row["concise_authored_gloss"] = "QAC says and + the trees"
        write_jsonl(bad, [bad_row])
        count, errors = validate(bad)
        if count != 1 or not any("public gloss leaks" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
        request_path = os.path.join(td, "request.jsonl")
        req = request_validator.sample_row()
        req["public_boundary"] = row["public_boundary"]
        req["gloss_context"] = row["gloss_context"]
        write_jsonl(request_path, [req])
        mismatch = dict(row)
        mismatch["reason_agreement_key"] = "wrong-key"
        write_jsonl(bad, [mismatch])
        count, errors = validate(bad, request_path=request_path)
        if count != 1:
            print("SELF-TEST FAIL agreement key mismatch count:", count)
            return 1
        if not any("reason_agreement_key must match request agreement_key_hint" in err for err in errors):
            print("SELF-TEST FAIL agreement key mismatch:", errors)
            return 1
        gloss_mismatch = dict(row)
        gloss_mismatch["concise_authored_gloss"] = "and the trees"
        write_jsonl(bad, [gloss_mismatch])
        count, errors = validate(bad, request_path=request_path)
        if count != 1:
            print("SELF-TEST FAIL gloss hint mismatch count:", count)
            return 1
        if not any("approved concise_authored_gloss must match request gloss_style_hint" in err for err in errors):
            print("SELF-TEST FAIL gloss hint mismatch:", errors)
            return 1
        context_mismatch = dict(row)
        context_mismatch["gloss_context"] = dict(row["gloss_context"])
        context_mismatch["gloss_context"]["token_contribution_gloss"] = "trees"
        write_jsonl(bad, [context_mismatch])
        count, errors = validate(bad, request_path=request_path)
        if count != 1:
            print("SELF-TEST FAIL context mismatch count:", count)
            return 1
        if not any("gloss_context does not match request" in err for err in errors):
            print("SELF-TEST FAIL context mismatch:", errors)
            return 1
    print("PASS — Phase 4 two-vote response validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="?")
    parser.add_argument("--requests")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.jsonl:
        parser.error("jsonl path is required unless --self-test is used")
    count, errors = validate(args.jsonl, request_path=args.requests)
    print("checked %d Phase 4 two-vote response rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — Phase 4 two-vote responses are exact-addressed and review-only")


if __name__ == "__main__":
    main()
