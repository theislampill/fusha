#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate full-corpus Qamus hover dogfood audit rows.

This is a read-only correctness/completeness gate. It intentionally treats
visible hover text as insufficient evidence: populated rows may still be
defective, uncertified, or missing learner-ready sarf/nahw breakdowns.
"""

import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_hover_dogfood_audit.sample.jsonl")

QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
DOGFOOD_ID = re.compile(r"^dogfood:wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")

DOGFOOD_CLASSES = {
    "rich_certified",
    "populated_uncertified",
    "string_correct_but_not_rich",
    "known_defect",
    "needs_sarf_review",
    "needs_nahw_review",
    "needs_renderer_segments",
    "token_only_override",
    "pending/blocker",
}

HOVER_PRESENCE = {"missing", "pending", "populated"}
ROUTES = {
    "repair_candidate",
    "blocker_queue_row",
    "production_bug_lesson",
    "sarf_nahw_procedure_improvement",
    "drill_regression_fixture",
    "renderer_rich_hover_requirement",
}
FAILURE_CLASSES = DOGFOOD_CLASSES - {"rich_certified", "string_correct_but_not_rich"}
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
KNOWN_DETECTORS = {
    "suffix_omitted",
    "conjunction_article_omitted",
    "vocative_collapse",
    "preposition_oath_host_only_hover",
    "article_duplication",
    "finite_verb_dictionary_root_gloss_leakage",
    "nominal_pos_leakage",
    "function_preposition_flattening",
    "clitic_host_collapse",
    "surface_family_requires_token_only_override",
}

REQUIRED = [
    "id",
    "audit_scope",
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_visible_gloss",
    "hover_presence",
    "rich_rendered",
    "dogfood_class",
    "status",
    "token_internal_segments",
    "sarf",
    "nahw",
    "entry_linkage",
    "procedures",
    "public_boundary",
    "certification",
    "learner_breakdown",
    "learner_breakdown_blocker",
    "detectors",
    "routes",
    "source",
]

SARF_FIELDS = [
    "root",
    "pos",
    "verb_form",
    "voice",
    "aspect",
    "mood",
    "person",
    "number",
    "gender",
    "case",
    "state",
    "derivative_type",
    "proclitics",
    "enclitics",
    "suffix_pronouns",
]

NAHW_FIELDS = [
    "particle_function",
    "governor",
    "attachment",
    "dependency_roles",
    "referent_class",
    "blocker",
]

ENTRY_FIELDS = [
    "parse_id",
    "parse_family_class",
    "parse_family_size",
    "parse_gate",
    "parse_confidence",
    "whole_token_candidates",
    "component_candidate_entries",
    "resolved_qamus_entry_id",
    "resolved_sense_id",
    "no_entry_function_token_rationale",
    "decision_ids",
]

CERT_FIELDS = [
    "mode",
    "string_populated_only",
    "rich_certified",
    "propagation_allowed",
    "requires_two_vote",
    "validated_code_head",
    "report_head",
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


def _err(errors, line_no, message):
    errors.append("line %d: %s" % (line_no, message))


def loc_tail(value):
    return str(value).split(":", 1)[1] if ":" in str(value) else str(value)


def has_value(value):
    return value is not None and str(value).strip() != ""


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    if not isinstance(row, dict):
        _err(errors, line_no, "row must be an object")
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    quran = row.get("quran_loc")
    wbw = row.get("wbw_loc")
    row_id = row.get("id")
    if not QURAN.match(str(quran)):
        _err(errors, line_no, "quran_loc must be quran:S:A:W")
    if not WBW.match(str(wbw)):
        _err(errors, line_no, "wbw_loc must be wbw:S:A:W")
    if QURAN.match(str(quran)) and WBW.match(str(wbw)) and loc_tail(quran) != loc_tail(wbw):
        _err(errors, line_no, "quran_loc and wbw_loc must point to same S:A:W")
    if not DOGFOOD_ID.match(str(row_id)):
        _err(errors, line_no, "id must be dogfood:wbw:S:A:W")
    elif WBW.match(str(wbw)) and str(row_id) != "dogfood:%s" % wbw:
        _err(errors, line_no, "id must derive from wbw_loc")

    dogfood_class = row.get("dogfood_class")
    if dogfood_class not in DOGFOOD_CLASSES:
        _err(errors, line_no, "bad dogfood_class %r" % dogfood_class)
    presence = row.get("hover_presence")
    if presence not in HOVER_PRESENCE:
        _err(errors, line_no, "bad hover_presence %r" % presence)
    if row.get("source") != "read_only_shadow_graph":
        _err(errors, line_no, "source must be read_only_shadow_graph")
    if row.get("audit_scope") != "full_corpus_hover_dogfood":
        _err(errors, line_no, "audit_scope must be full_corpus_hover_dogfood")

    segments = row.get("token_internal_segments")
    if not isinstance(segments, list):
        _err(errors, line_no, "token_internal_segments must be an array")
        segments = []
    for idx, segment in enumerate(segments):
        if not isinstance(segment, dict):
            _err(errors, line_no, "token_internal_segments[%d] must be object" % idx)
            continue
        if not has_value(segment.get("role")):
            _err(errors, line_no, "token_internal_segments[%d] missing role" % idx)
        if "surface" not in segment:
            _err(errors, line_no, "token_internal_segments[%d] missing surface" % idx)

    for section, fields in (("sarf", SARF_FIELDS), ("nahw", NAHW_FIELDS), ("entry_linkage", ENTRY_FIELDS), ("certification", CERT_FIELDS)):
        value = row.get(section)
        if not isinstance(value, dict):
            _err(errors, line_no, "%s must be an object" % section)
            value = {}
        for field in fields:
            if field not in value:
                _err(errors, line_no, "%s missing %s" % (section, field))

    sarf = row.get("sarf") if isinstance(row.get("sarf"), dict) else {}
    nahw = row.get("nahw") if isinstance(row.get("nahw"), dict) else {}
    entry = row.get("entry_linkage") if isinstance(row.get("entry_linkage"), dict) else {}
    cert = row.get("certification") if isinstance(row.get("certification"), dict) else {}

    parse_id = entry.get("parse_id")
    if parse_id is not None and not PARSE.match(str(parse_id)):
        _err(errors, line_no, "entry_linkage.parse_id must be parse:<hex> or null")
    if not isinstance(entry.get("parse_family_size"), int) or entry.get("parse_family_size") < 0:
        _err(errors, line_no, "entry_linkage.parse_family_size must be >=0")
    for list_field in ("whole_token_candidates", "component_candidate_entries", "decision_ids"):
        if not isinstance(entry.get(list_field), list):
            _err(errors, line_no, "entry_linkage.%s must be array" % list_field)

    boundary = row.get("public_boundary") if isinstance(row.get("public_boundary"), dict) else {}
    if boundary.get("src") != "qamus" or boundary.get("kind") != "authored" or boundary.get("lang") != "en":
        _err(errors, line_no, "public boundary must be src=qamus kind=authored lang=en")
    for bool_field in ("internal_provenance_public", "external_source_names_public", "public_leak_detected"):
        if boundary.get(bool_field) is not False:
            _err(errors, line_no, "public_boundary.%s must be false" % bool_field)
    public_blob = json.dumps({"public_boundary": boundary, "certification": cert}, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in public_blob:
            _err(errors, line_no, "public fields leak forbidden label %r" % label)

    procedures = row.get("procedures")
    if not isinstance(procedures, list):
        _err(errors, line_no, "procedures must be array")
        procedures = []
    detectors = row.get("detectors")
    if not isinstance(detectors, list):
        _err(errors, line_no, "detectors must be array")
        detectors = []
    routes = row.get("routes")
    if not isinstance(routes, list):
        _err(errors, line_no, "routes must be array")
        routes = []
    for route in routes:
        if route not in ROUTES:
            _err(errors, line_no, "bad route %r" % route)
    for detector in detectors:
        if detector not in KNOWN_DETECTORS:
            _err(errors, line_no, "unknown detector %r" % detector)

    if dogfood_class == "rich_certified":
        if presence != "populated":
            _err(errors, line_no, "rich_certified requires populated hover")
        if row.get("rich_rendered") is not True:
            _err(errors, line_no, "rich_certified requires rich_rendered=true")
        if cert.get("rich_certified") is not True or cert.get("string_populated_only") is not False:
            _err(errors, line_no, "rich_certified certification flags inconsistent")
        if detectors or routes:
            _err(errors, line_no, "rich_certified rows must not carry detectors/routes")
        if not has_value(row.get("learner_breakdown")):
            _err(errors, line_no, "rich_certified requires learner_breakdown")
        if entry.get("parse_gate") not in ("auto_safe", "two_vote_required"):
            _err(errors, line_no, "rich_certified requires certified parse gate")
        if entry.get("parse_confidence") in ("surface_only", "unknown", None):
            _err(errors, line_no, "rich_certified cannot use surface_only/unknown parse confidence")

    if dogfood_class == "string_correct_but_not_rich":
        if presence != "populated" or not has_value(row.get("current_visible_gloss")):
            _err(errors, line_no, "string_correct_but_not_rich requires visible populated gloss")
        if row.get("rich_rendered") is True:
            _err(errors, line_no, "string_correct_but_not_rich must not claim rich_rendered")
        if cert.get("string_populated_only") is not True:
            _err(errors, line_no, "string_correct_but_not_rich requires string_populated_only=true")
        if not routes or "renderer_rich_hover_requirement" not in routes:
            _err(errors, line_no, "string_correct_but_not_rich routes to renderer_rich_hover_requirement")

    if dogfood_class in FAILURE_CLASSES:
        if not routes:
            _err(errors, line_no, "%s rows must route to a queue/action" % dogfood_class)
        if cert.get("rich_certified") is True:
            _err(errors, line_no, "%s cannot be rich_certified" % dogfood_class)
        if not row.get("learner_breakdown_blocker"):
            _err(errors, line_no, "%s requires learner_breakdown_blocker" % dogfood_class)

    if dogfood_class == "known_defect" and not detectors:
        _err(errors, line_no, "known_defect requires detectors")
    if dogfood_class == "needs_sarf_review" and "sarf_nahw_procedure_improvement" not in routes:
        _err(errors, line_no, "needs_sarf_review must route to sarf/nahw procedure improvement")
    if dogfood_class == "needs_nahw_review" and "sarf_nahw_procedure_improvement" not in routes:
        _err(errors, line_no, "needs_nahw_review must route to sarf/nahw procedure improvement")
    if dogfood_class == "needs_renderer_segments" and "renderer_rich_hover_requirement" not in routes:
        _err(errors, line_no, "needs_renderer_segments must route to renderer_rich_hover_requirement")
    if dogfood_class == "token_only_override" and entry.get("parse_family_class") != "token_only_required":
        _err(errors, line_no, "token_only_override requires parse_family_class=token_only_required")
    if dogfood_class == "pending/blocker":
        if presence == "populated" and not (nahw.get("blocker") or entry.get("parse_gate") in ("never_auto", "human_review_required")):
            _err(errors, line_no, "pending/blocker requires missing/pending hover or explicit blocker gate")

    if detectors and not routes:
        _err(errors, line_no, "detectors must route to at least one action")
    if "suffix_omitted" in detectors and not (sarf.get("suffix_pronouns") or sarf.get("enclitics")):
        _err(errors, line_no, "suffix_omitted detector requires suffix/enclitic evidence")
    if "finite_verb_dictionary_root_gloss_leakage" in detectors and sarf.get("pos") != "verb":
        _err(errors, line_no, "finite_verb_dictionary_root_gloss_leakage requires verb POS")
    if "nominal_pos_leakage" in detectors and sarf.get("pos") not in ("noun", "adjective", "proper_noun"):
        _err(errors, line_no, "nominal_pos_leakage requires nominal POS")
    if "article_duplication" in detectors and "the + the" not in str(row.get("current_visible_gloss") or "").lower():
        _err(errors, line_no, "article_duplication detector requires visible duplicated article text")
    if "function_preposition_flattening" in detectors and not (nahw.get("particle_function") or sarf.get("proclitics")):
        _err(errors, line_no, "function_preposition_flattening requires particle/preposition evidence")


def validate_file(path, expect_min_rows=1):
    errors = []
    rows = []
    classes = set()
    for line_no, row in iter_jsonl(path):
        rows.append(row)
        if isinstance(row, dict):
            classes.add(row.get("dogfood_class"))
        validate_row(row, line_no, errors)
    if len(rows) < expect_min_rows:
        errors.append("file has %d rows, expected at least %d" % (len(rows), expect_min_rows))
    if not rows:
        errors.append("vacuous audit: no rows")
    if "rich_certified" not in classes and os.path.abspath(path) == os.path.abspath(SAMPLE):
        errors.append("sample must include at least one rich_certified row")
    if "known_defect" not in classes and os.path.abspath(path) == os.path.abspath(SAMPLE):
        errors.append("sample must include at least one known_defect row")
    if "pending/blocker" not in classes and os.path.abspath(path) == os.path.abspath(SAMPLE):
        errors.append("sample must include at least one pending/blocker row")
    return errors


def self_test():
    errors = validate_file(SAMPLE)
    if errors:
        raise SystemExit("sample failed validation:\n%s" % "\n".join(errors))
    bad = {
        "id": "dogfood:wbw:1:1:1",
        "audit_scope": "full_corpus_hover_dogfood",
        "quran_loc": "quran:1:1:1",
        "wbw_loc": "wbw:1:1:1",
        "surface": "x",
        "current_visible_gloss": "text",
        "hover_presence": "populated",
        "rich_rendered": False,
        "dogfood_class": "rich_certified",
        "status": "resolved",
        "token_internal_segments": [],
        "sarf": {field: [] if field in ("proclitics", "enclitics", "suffix_pronouns") else None for field in SARF_FIELDS},
        "nahw": {field: [] if field == "dependency_roles" else None for field in NAHW_FIELDS},
        "entry_linkage": {
            "parse_id": "parse:abc123",
            "parse_family_class": "propagation_safe",
            "parse_family_size": 1,
            "parse_gate": "auto_safe",
            "parse_confidence": "certified",
            "whole_token_candidates": [],
            "component_candidate_entries": [],
            "resolved_qamus_entry_id": None,
            "resolved_sense_id": None,
            "no_entry_function_token_rationale": None,
            "decision_ids": [],
        },
        "procedures": [],
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "internal_provenance_public": False,
            "external_source_names_public": False,
            "public_leak_detected": False,
        },
        "certification": {
            "mode": "rich_certified",
            "string_populated_only": False,
            "rich_certified": True,
            "propagation_allowed": True,
            "requires_two_vote": False,
            "validated_code_head": None,
            "report_head": None,
        },
        "learner_breakdown": None,
        "learner_breakdown_blocker": None,
        "detectors": [],
        "routes": [],
        "source": "read_only_shadow_graph",
    }
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = os.path.join(tmp, "bad.jsonl")
        write_jsonl(bad_path, [bad])
        bad_errors = validate_file(bad_path)
        if not bad_errors:
            raise SystemExit("bad rich_certified row unexpectedly validated")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="?", default=SAMPLE)
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate_file(args.jsonl, expect_min_rows=args.expect_min_rows)
    if errors:
        raise SystemExit("\n".join(errors))
    print("full-corpus hover dogfood audit validates: %s" % args.jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
