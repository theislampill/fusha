#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Qamus parse-key grammar-family JSONL rows.

Parse keys are reusable grammar-family keys, never primary identity. This
validator is the reusable Phase 2 gate for parse-keys.jsonl-style rows: exact
token locations remain quran:S:A:W, hover slots remain wbw:S:A:W, and unsafe
family fan-out must fail closed.
"""
import argparse
import copy
import hashlib
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_PATH = os.path.join(ROOT, "qamus", "examples", "parse_key.sample.jsonl")

PARSE = re.compile(r"^parse:[0-9a-f]{8,}$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
QURAN_BARE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
QAMUS = re.compile(r"^qamus:")

REQUIRED_ROW = (
    "id",
    "canonical_parse_object",
    "seen_locs",
    "family_size",
    "candidate_entries",
    "blockers",
    "gates",
    "confidences",
    "family_class",
    "propagation_allowed",
)
REQUIRED_PARSE = (
    "parse_key_version",
    "quran_loc",
    "surface_raw",
    "norm_strict",
    "bare",
    "pos",
    "qamus_entry_candidates",
    "proclitics",
    "enclitics",
    "suffix_pronouns",
    "token_internal_segments",
    "grammar_triggers",
    "gate",
    "decision_status",
    "blocker",
    "evidence_version",
    "parse_confidence",
)
GATES = {"auto_safe", "two_vote_required", "human_review_required", "never_auto", "unknown"}
CONFIDENCES = {"certified", "two_vote", "candidate", "partial", "rich_metadata", "lexical_candidate", "surface_only", "unknown"}
FAMILY_CLASSES = {
    "propagation_safe",
    "propagation_safe_candidate",
    "token_only_required",
    "two_vote_required",
    "human_review_required",
    "never_auto",
    "quarantine_collision",
    "source_disagreement",
    "missing_entry",
    "unknown_parse",
}
UNSAFE_AUTO_CONFIDENCES = {"surface_only", "unknown"}
COLLISION_TRIGGERS = {"candidate_collision", "parse_key_collision", "source_disagreement"}
GRAMMAR_SENSITIVE_TRIGGERS = {
    "ma_function",
    "pp_attachment",
    "jar_majrur_ambiguous",
    "oath_particle",
    "comitative_particle",
    "causal_particle",
    "suffix_pronoun",
    "preposition",
    "function_particle",
    "case_or_mood",
    "irab",
    "referent_sensitive_gloss",
}


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


def parse_id_for(canonical_parse_object):
    raw = json.dumps(
        canonical_parse_object,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "parse:%s" % hashlib.sha256(raw).hexdigest()[:24]


def quran_address(loc):
    if loc is None:
        return None
    text = str(loc)
    return text if text.startswith("quran:") else "quran:%s" % text


def candidate_addresses(parse_obj):
    out = []
    for candidate in parse_obj.get("qamus_entry_candidates") or []:
        if isinstance(candidate, str):
            out.append(candidate)
        elif isinstance(candidate, dict):
            out.append(candidate.get("entry_address"))
    return [item for item in out if item]


def _err(errors, line_no, message):
    errors.append("line %d: %s" % (line_no, message))


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    if not isinstance(row, dict):
        _err(errors, line_no, "row must be an object")
        return
    for field in REQUIRED_ROW:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    parse_id = str(row.get("id") or "")
    if not PARSE.match(parse_id):
        _err(errors, line_no, "id must be parse:<hex>")

    parse_obj = row.get("canonical_parse_object")
    if not isinstance(parse_obj, dict):
        _err(errors, line_no, "canonical_parse_object must be an object")
        return
    for field in REQUIRED_PARSE:
        if field not in parse_obj:
            _err(errors, line_no, "canonical_parse_object missing %s" % field)

    expected_id = parse_id_for(parse_obj)
    if PARSE.match(parse_id) and parse_id != expected_id:
        _err(errors, line_no, "id does not match canonical parse object hash (expected %s)" % expected_id)

    seen_locs = row.get("seen_locs") or []
    if not isinstance(seen_locs, list) or not seen_locs:
        _err(errors, line_no, "seen_locs must be a non-empty array")
        seen_locs = []
    for loc in seen_locs:
        if not QURAN.match(str(loc)):
            _err(errors, line_no, "bad seen_locs item %r" % loc)
    if len(set(seen_locs)) != len(seen_locs):
        _err(errors, line_no, "seen_locs must not contain duplicates")
    if row.get("family_size") != len(seen_locs):
        _err(errors, line_no, "family_size must equal len(seen_locs)")

    quran_loc = parse_obj.get("quran_loc")
    if quran_loc is not None:
        if not QURAN_BARE.match(str(quran_loc)) and not QURAN.match(str(quran_loc)):
            _err(errors, line_no, "canonical_parse_object.quran_loc must be null or an exact token address")
        elif quran_address(quran_loc) not in set(seen_locs):
            _err(errors, line_no, "canonical_parse_object.quran_loc must appear in seen_locs when present")

    for value in row.get("candidate_entries") or []:
        if not isinstance(value, str) or not QAMUS.match(value):
            _err(errors, line_no, "candidate_entries values must be qamus:* addresses")
    parse_candidates = set(candidate_addresses(parse_obj))
    row_candidates = set(row.get("candidate_entries") or [])
    if parse_candidates and parse_candidates != row_candidates:
        _err(errors, line_no, "candidate_entries must match canonical qamus_entry_candidates")

    gate = parse_obj.get("gate")
    if gate not in GATES:
        _err(errors, line_no, "bad canonical gate %r" % gate)
    for gate_value in row.get("gates") or []:
        if gate_value not in GATES:
            _err(errors, line_no, "bad gates value %r" % gate_value)
    if gate and gate not in set(row.get("gates") or []):
        _err(errors, line_no, "canonical gate must be present in row.gates")

    confidence = parse_obj.get("parse_confidence")
    if confidence not in CONFIDENCES:
        _err(errors, line_no, "bad parse_confidence %r" % confidence)
    for confidence_value in row.get("confidences") or []:
        if confidence_value not in CONFIDENCES:
            _err(errors, line_no, "bad confidences value %r" % confidence_value)
    if confidence and confidence not in set(row.get("confidences") or []):
        _err(errors, line_no, "canonical parse_confidence must be present in row.confidences")

    family_class = row.get("family_class")
    if family_class not in FAMILY_CLASSES:
        _err(errors, line_no, "bad family_class %r" % family_class)
    propagation_allowed = row.get("propagation_allowed")
    if not isinstance(propagation_allowed, bool):
        _err(errors, line_no, "propagation_allowed must be boolean")

    blockers = set(row.get("blockers") or [])
    blocker = parse_obj.get("blocker")
    if blocker and blocker not in blockers:
        _err(errors, line_no, "canonical blocker must be present in row.blockers")
    if blockers and not blocker:
        _err(errors, line_no, "row.blockers present but canonical blocker is empty")
    if blocker and parse_obj.get("decision_status") == "resolved":
        _err(errors, line_no, "resolved parse object cannot retain a blocker")

    triggers = set(parse_obj.get("grammar_triggers") or [])
    if propagation_allowed:
        if family_class != "propagation_safe":
            _err(errors, line_no, "propagation_allowed requires family_class=propagation_safe")
        if gate != "auto_safe" or "auto_safe" not in set(row.get("gates") or []):
            _err(errors, line_no, "propagation_allowed requires auto_safe gate")
        if blockers or blocker:
            _err(errors, line_no, "propagation_allowed rows cannot carry blockers")
        if len(row_candidates) != 1:
            _err(errors, line_no, "propagation_allowed requires exactly one candidate entry")
        if confidence in UNSAFE_AUTO_CONFIDENCES or set(row.get("confidences") or []) & UNSAFE_AUTO_CONFIDENCES:
            _err(errors, line_no, "surface/unknown parse confidence cannot propagate")
        if triggers & (COLLISION_TRIGGERS | GRAMMAR_SENSITIVE_TRIGGERS):
            _err(errors, line_no, "grammar-sensitive or collision trigger cannot propagate without a stronger gate")
    else:
        if family_class == "propagation_safe":
            _err(errors, line_no, "family_class=propagation_safe must set propagation_allowed=true")

    if confidence == "surface_only" and gate == "auto_safe":
        _err(errors, line_no, "surface_only parse cannot be auto_safe")
    if len(row_candidates) > 1 and (propagation_allowed or family_class == "propagation_safe"):
        _err(errors, line_no, "multi-candidate parse family cannot be propagation_safe")
    if triggers & COLLISION_TRIGGERS and (propagation_allowed or gate == "auto_safe"):
        _err(errors, line_no, "collision/source-disagreement trigger cannot be auto_safe")
    if triggers & GRAMMAR_SENSITIVE_TRIGGERS and gate == "auto_safe":
        _err(errors, line_no, "grammar-sensitive trigger requires two_vote/human/never_auto gate")


def validate(path):
    count = 0
    errors = []
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero parse-key rows")
    return count, errors


def self_test():
    with tempfile.TemporaryDirectory(prefix="parse-key-contract-") as td:
        good = os.path.join(td, "good.jsonl")
        rows = [row for _line, row in iter_jsonl(SAMPLE_PATH)]
        write_jsonl(good, rows)
        count, errors = validate(good)
        if count != 3 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1

        bad_surface = copy.deepcopy(rows[0])
        bad_surface["canonical_parse_object"]["parse_confidence"] = "surface_only"
        bad_surface["confidences"] = ["surface_only"]
        bad_surface["id"] = parse_id_for(bad_surface["canonical_parse_object"])
        count, errors = validate_obj_rows([bad_surface])
        if not any("surface/unknown parse confidence cannot propagate" in err for err in errors):
            print("SELF-TEST FAIL surface-only propagation:", errors)
            return 1

        bad_collision = copy.deepcopy(rows[2])
        bad_collision["canonical_parse_object"]["gate"] = "auto_safe"
        bad_collision["gates"] = ["auto_safe"]
        bad_collision["propagation_allowed"] = True
        bad_collision["family_class"] = "propagation_safe"
        bad_collision["id"] = parse_id_for(bad_collision["canonical_parse_object"])
        count, errors = validate_obj_rows([bad_collision])
        if not any("multi-candidate parse family cannot be propagation_safe" in err for err in errors):
            print("SELF-TEST FAIL collision propagation:", errors)
            return 1

        bad_hash = copy.deepcopy(rows[0])
        bad_hash["id"] = "parse:aaaaaaaa"
        count, errors = validate_obj_rows([bad_hash])
        if not any("id does not match canonical parse object hash" in err for err in errors):
            print("SELF-TEST FAIL hash:", errors)
            return 1
    print("PASS — parse-key contract validator self-test")
    return 0


def validate_obj_rows(rows):
    errors = []
    for line_no, row in enumerate(rows, 1):
        validate_row(row, line_no, errors)
    return len(rows), errors


def main():
    parser = argparse.ArgumentParser(description="Validate Qamus parse-key grammar-family JSONL rows.")
    parser.add_argument("jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.jsonl:
        parser.error("jsonl path is required unless --self-test is used")
    count, errors = validate(args.jsonl)
    print("checked %d parse-key rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  - " + err)
        raise SystemExit(1)
    print("PASS — parse-key rows are exact-addressed and fail closed")


if __name__ == "__main__":
    main()
