#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Qamus shadow-graph review-pack JSONL rows.

This validator is intentionally stricter than a shape check. Review packs are
allowed to guide future closure work only if every row is exact-addressed,
read-only, source-clean at the public boundary, and non-vacuous.
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "shadow-review-pack.schema.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
QUEUE = re.compile(r"^queue:parse_[0-9a-f]+$")
LANES = {
    "human_review_required",
    "quarantine_collision",
    "two_vote_required",
    "missing_entry",
    "unknown_parse",
    "propagation_safe_candidate",
    "token_only_required",
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
)
REQUIRED = [
    "id",
    "parse_id",
    "lane",
    "scope",
    "recommended_action",
    "required_gate",
    "family_size",
    "resolved_token_count",
    "unresolved_token_count",
    "quran_locs",
    "wbw_locs",
    "token_sample",
    "candidate_entries",
    "candidate_join_statuses",
    "parse",
    "apply_policy",
]
PARSE_REQUIRED = [
    "gate",
    "blocker",
    "decision_status",
    "parse_confidence",
    "pos",
    "root",
    "lemma",
    "particle_function",
    "grammar_triggers",
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


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return

    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    row_id = row.get("id")
    parse_id = row.get("parse_id")
    if not QUEUE.match(str(row_id)):
        _err(errors, line_no, "id must be queue:parse_<hash>")
    if not PARSE.match(str(parse_id)):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    elif str(row_id) != "queue:%s" % str(parse_id).replace(":", "_"):
        _err(errors, line_no, "id must derive from parse_id")

    lane = row.get("lane")
    if not (str(lane).startswith("blocked:") or lane in LANES):
        _err(errors, line_no, "bad lane %r" % lane)

    family_size = row.get("family_size")
    quran_locs = row.get("quran_locs") or []
    wbw_locs = row.get("wbw_locs") or []
    if not isinstance(family_size, int) or family_size < 1:
        _err(errors, line_no, "family_size must be positive")
    else:
        if len(quran_locs) != family_size:
            _err(errors, line_no, "quran_locs count must equal family_size")
        if len(wbw_locs) != family_size:
            _err(errors, line_no, "wbw_locs count must equal family_size")

    for loc in quran_locs:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad quran loc %r" % loc)
    for loc in wbw_locs:
        if not WBW.match(str(loc)):
            _err(errors, line_no, "bad wbw loc %r" % loc)
    for loc in row.get("token_sample") or []:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad token_sample loc %r" % loc)

    resolved = row.get("resolved_token_count")
    unresolved = row.get("unresolved_token_count")
    if isinstance(resolved, int) and isinstance(unresolved, int) and isinstance(family_size, int):
        if resolved + unresolved != family_size:
            _err(errors, line_no, "resolved + unresolved must equal family_size")

    parse = row.get("parse") or {}
    if not isinstance(parse, dict):
        _err(errors, line_no, "parse must be an object")
        parse = {}
    for field in PARSE_REQUIRED:
        if field not in parse:
            _err(errors, line_no, "parse missing %s" % field)
    if parse.get("parse_confidence") == "surface_only" and lane == "propagation_safe_candidate":
        _err(errors, line_no, "surface_only parse cannot be propagation_safe_candidate")

    policy = row.get("apply_policy") or {}
    if policy.get("live_mutation_allowed") is not False:
        _err(errors, line_no, "apply_policy.live_mutation_allowed must be false")
    identity = str(policy.get("identity") or "")
    if "quran:S:A:W" not in identity or "wbw:S:A:W" not in identity:
        _err(errors, line_no, "apply_policy.identity must name exact quran/wbw identities")
    if "parse key is not primary identity" not in identity:
        _err(errors, line_no, "apply_policy.identity must reject parse_key as primary identity")
    public_boundary = str(policy.get("public_boundary") or "")
    if public_boundary != "src=qamus, kind=authored, lang=en; no external provenance":
        _err(errors, line_no, "public boundary must be source-clean qamus/authored/en")
    public_blob = json.dumps(policy, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in public_blob:
            _err(errors, line_no, "public apply_policy leaks forbidden label %r" % label)

    if lane == "quarantine_collision" and len(row.get("candidate_entries") or []) < 2:
        _err(errors, line_no, "quarantine_collision must expose multiple candidate entries")
    if lane == "missing_entry" and row.get("candidate_entries"):
        _err(errors, line_no, "missing_entry lane must not carry candidate_entries")
    if lane == "propagation_safe_candidate":
        statuses = [
            status
            for join in row.get("candidate_join_statuses") or []
            for status in join.get("join_status") or []
        ]
        if not any(str(status).startswith("exact:") for status in statuses):
            _err(errors, line_no, "propagation_safe_candidate requires exact join evidence")


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero review-pack rows")
    return count, errors


def good_row():
    return {
        "id": "queue:parse_0123abcd",
        "parse_id": "parse:0123abcd",
        "lane": "two_vote_required",
        "scope": "token_or_family_after_votes",
        "recommended_action": "build two-vote review packet with source-addressed reasoning",
        "required_gate": "two_vote_required",
        "family_size": 1,
        "resolved_token_count": 1,
        "unresolved_token_count": 0,
        "surface_sample": "يَسْأَلُكَ",
        "quran_locs": ["quran:33:63:1"],
        "wbw_locs": ["wbw:33:63:1"],
        "token_sample": ["quran:33:63:1"],
        "candidate_entries": ["qamus:v:5935ecfb1ec5"],
        "candidate_join_statuses": [
            {"entry": "qamus:v:5935ecfb1ec5", "join_status": ["candidate:live_surface"]}
        ],
        "parse": {
            "gate": "two_vote_required",
            "blocker": None,
            "decision_status": "resolved",
            "parse_confidence": "candidate",
            "pos": "unknown",
            "root": None,
            "lemma": None,
            "particle_function": None,
            "grammar_triggers": [],
        },
        "apply_policy": {
            "live_mutation_allowed": False,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
        },
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="review-pack-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        with io.open(good, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(good_row(), ensure_ascii=False, sort_keys=True) + "\n")
        row = good_row()
        row["quran_locs"] = ["33:63:1"]
        with io.open(bad, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(good)
        if count != 1 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        count, errors = validate(bad)
        if count != 1 or not any("bad quran loc" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
    print("PASS — shadow review-pack validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.jsonl:
        parser.error("jsonl path is required unless --self-test is used")
    count, errors = validate(args.jsonl)
    print("checked %d shadow review-pack rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — shadow review pack is exact-addressed and source-clean")


if __name__ == "__main__":
    main()
