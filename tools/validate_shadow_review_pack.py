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
QAMUS = re.compile(r"^qamus:")
QURAN_LOC_STATUS = re.compile(r"^token_loc:quran:\d{1,3}:\d{1,3}:\d{1,3}$")
LANES = {
    "human_review_required",
    "never_auto",
    "quarantine_collision",
    "two_vote_required",
    "source_disagreement",
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
DETECTOR_MATURITY = {
    "two_vote_required": "partial_shadow_gate",
    "source_disagreement": "reserved_detector_gap",
    "zero_count_policy": "zero_does_not_prove_absence",
}
REQUIRED = [
    "id",
    "parse_id",
    "lane",
    "scope",
    "recommended_action",
    "required_gate",
    "gate_reasons",
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
    maturity = policy.get("detector_maturity")
    if maturity != DETECTOR_MATURITY:
        _err(errors, line_no, "detector_maturity must preserve Phase 2 detector-gap warning")
    if isinstance(maturity, dict):
        bad_claims = [
            "%s=%s" % (key, value)
            for key, value in maturity.items()
            if str(value).lower() in ("complete", "trusted_complete", "absence_proven")
        ]
        if bad_claims:
            _err(errors, line_no, "detector_maturity overclaims completion: %s" % ", ".join(bad_claims))
    public_blob = json.dumps(policy, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in public_blob:
            _err(errors, line_no, "public apply_policy leaks forbidden label %r" % label)

    if lane == "quarantine_collision" and len(row.get("candidate_entries") or []) < 2:
        _err(errors, line_no, "quarantine_collision must expose multiple candidate entries")
    gate_reasons = row.get("gate_reasons")
    if not isinstance(gate_reasons, list) or not gate_reasons:
        _err(errors, line_no, "gate_reasons must be a non-empty array")
    if lane in {"two_vote_required", "source_disagreement", "quarantine_collision", "human_review_required", "never_auto"}:
        if not any(str(reason).startswith(("grammar_trigger:", "blocker:", "source_disagreement", "candidate_collision", "parse_gate:")) for reason in gate_reasons or []):
            _err(errors, line_no, "%s lane must explain its gate_reasons" % lane)
    if lane == "source_disagreement" and "source_disagreement" not in (gate_reasons or []):
        _err(errors, line_no, "source_disagreement lane must include source_disagreement gate reason")
    if lane == "missing_entry" and row.get("candidate_entries"):
        _err(errors, line_no, "missing_entry lane must not carry candidate_entries")
    if lane == "propagation_safe_candidate":
        if row.get("component_candidate_entries"):
            _err(errors, line_no, "component candidates cannot support propagation_safe_candidate")
        statuses = [
            status
            for join in row.get("candidate_join_statuses") or []
            for status in join.get("join_status") or []
        ]
        if not any(str(status).startswith("exact:") for status in statuses):
            _err(errors, line_no, "propagation_safe_candidate requires exact join evidence")
        if row.get("required_gate") != "auto_safe_after_preview":
            _err(errors, line_no, "propagation_safe_candidate must use required_gate=auto_safe_after_preview")
        if row.get("scope") != "parse_key_family_readonly_preview":
            _err(errors, line_no, "propagation_safe_candidate must use parse_key_family_readonly_preview scope")
    if lane == "never_auto" and row.get("required_gate") != "never_auto":
        _err(errors, line_no, "never_auto lane must preserve required_gate=never_auto")

    component_entries = set(row.get("component_candidate_entries") or [])
    for entry in component_entries:
        if not isinstance(entry, str) or not QAMUS.match(entry):
            _err(errors, line_no, "component_candidate_entries values must be qamus:*")
    component_joins = row.get("component_candidate_join_statuses") or []
    joined_entries = set()
    if component_entries and not isinstance(component_joins, list):
        _err(errors, line_no, "component_candidate_join_statuses must be an array")
        component_joins = []
    for join in component_joins:
        if not isinstance(join, dict):
            _err(errors, line_no, "component_candidate_join_statuses rows must be objects")
            continue
        entry = join.get("entry")
        if isinstance(entry, str) and QAMUS.match(entry):
            joined_entries.add(entry)
        else:
            _err(errors, line_no, "component candidate join entry must be qamus:*")
        statuses = set(join.get("join_status") or [])
        if not any(str(status).startswith("source:") for status in statuses):
            _err(errors, line_no, "component candidate join must preserve source:* provenance")
        if not any(str(status).startswith("role:") for status in statuses):
            _err(errors, line_no, "component candidate join must preserve role:* provenance")
        if not any(str(status).startswith("segment_text:") for status in statuses):
            _err(errors, line_no, "component candidate join must preserve segment_text:* provenance")
        if not any(QURAN_LOC_STATUS.match(str(status)) for status in statuses):
            _err(errors, line_no, "component candidate join must preserve token_loc:quran:S:A:W provenance")
    if component_entries and not component_entries.issubset(joined_entries):
        _err(errors, line_no, "component_candidate_entries must have matching join rows")


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
        "gate_reasons": ["parse_gate:two_vote_required", "requires_independent_reason_agreement"],
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
            "detector_maturity": DETECTOR_MATURITY,
        },
    }


def never_auto_row():
    row = good_row()
    row.update({
        "id": "queue:parse_deadbeef",
        "parse_id": "parse:deadbeef",
        "lane": "never_auto",
        "scope": "quarantine",
        "recommended_action": "do not propagate; resolve blocker or route to owner/scholar review before any token decision",
        "required_gate": "never_auto",
        "gate_reasons": ["grammar_trigger:ma_function", "parse_gate:never_auto"],
        "surface_sample": "مَا",
        "quran_locs": ["quran:2:21:1"],
        "wbw_locs": ["wbw:2:21:1"],
        "token_sample": ["quran:2:21:1"],
        "candidate_entries": ["qamus:p:ma"],
        "candidate_join_statuses": [
            {"entry": "qamus:p:ma", "join_status": ["exact:decision_entry"]}
        ],
    })
    row["parse"] = dict(row["parse"])
    row["parse"].update({
        "gate": "never_auto",
        "decision_status": "resolved",
        "parse_confidence": "candidate",
        "particle_function": "function_sensitive",
        "grammar_triggers": ["ma_function"],
    })
    return row


def propagation_preview_row():
    row = good_row()
    row.update({
        "id": "queue:parse_abcdef12",
        "parse_id": "parse:abcdef12",
        "lane": "propagation_safe_candidate",
        "scope": "parse_key_family_readonly_preview",
        "recommended_action": "preview exact token family before any append-only propagation",
        "required_gate": "auto_safe_after_preview",
        "family_size": 2,
        "resolved_token_count": 2,
        "unresolved_token_count": 0,
        "surface_sample": "ٱلْأَرْضِ",
        "quran_locs": ["quran:22:18:12", "quran:29:22:5"],
        "wbw_locs": ["wbw:22:18:12", "wbw:29:22:5"],
        "token_sample": ["quran:22:18:12", "quran:29:22:5"],
        "candidate_entries": ["qamus:n:earth"],
        "candidate_join_statuses": [
            {"entry": "qamus:n:earth", "join_status": ["exact:entry_surface", "exact:strict_surface"]}
        ],
    })
    row["gate_reasons"] = ["parse_gate:auto_safe", "requires_pre_apply_family_preview"]
    row["parse"] = dict(row["parse"])
    row["parse"].update({
        "gate": "auto_safe",
        "parse_confidence": "strict_and_entry_joined",
        "pos": "noun",
        "grammar_triggers": [],
    })
    return row


def component_enriched_two_vote_row():
    row = good_row()
    row.update({
        "id": "queue:parse_c0ffee12",
        "parse_id": "parse:c0ffee12",
        "lane": "two_vote_required",
        "scope": "token_or_family_after_votes",
        "recommended_action": "build two-vote review packet with source-addressed reasoning",
        "required_gate": "two_vote_required",
        "gate_reasons": [
            "grammar_trigger:function_particle",
            "parse_gate:two_vote_required",
            "requires_independent_reason_agreement",
        ],
        "surface_sample": "وَٱلشَّجَرُ",
        "quran_locs": ["quran:22:18:17"],
        "wbw_locs": ["wbw:22:18:17"],
        "token_sample": ["quran:22:18:17"],
        "candidate_entries": [],
        "candidate_join_statuses": [],
        "component_candidate_entries": ["qamus:p:waw", "qamus:p:al", "qamus:n:tree"],
        "component_candidate_join_statuses": [
            {
                "entry": "qamus:p:waw",
                "join_status": [
                    "source:rich_wbw_segment",
                    "role:conjunction",
                    "segment_text:وَ",
                    "token_loc:quran:22:18:17",
                ],
            },
            {
                "entry": "qamus:p:al",
                "join_status": [
                    "source:rich_wbw_segment",
                    "role:definite_article",
                    "segment_text:ٱل",
                    "token_loc:quran:22:18:17",
                ],
            },
            {
                "entry": "qamus:n:tree",
                "join_status": [
                    "source:rich_wbw_segment",
                    "role:stem",
                    "segment_text:شَّجَرُ",
                    "token_loc:quran:22:18:17",
                ],
            },
        ],
    })
    row["parse"] = dict(row["parse"])
    row["parse"].update({
        "gate": "two_vote_required",
        "decision_status": "resolved",
        "parse_confidence": "rich_metadata",
        "pos": "noun",
        "grammar_triggers": ["function_particle"],
    })
    return row


def source_disagreement_row():
    row = good_row()
    row.update({
        "id": "queue:parse_feedface",
        "parse_id": "parse:feedface",
        "lane": "source_disagreement",
        "scope": "quarantine",
        "recommended_action": "resolve source/join disagreement before any token or family edit",
        "required_gate": "human_review_required",
        "gate_reasons": ["source_disagreement", "parse_gate:human_review_required"],
        "candidate_entries": ["qamus:n:one"],
        "candidate_join_statuses": [
            {"entry": "qamus:n:one", "join_status": ["conflict:source_surface_mismatch"]}
        ],
    })
    row["parse"] = dict(row["parse"])
    row["parse"].update({"gate": "human_review_required"})
    return row


def self_test():
    with tempfile.TemporaryDirectory(prefix="review-pack-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        with io.open(good, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(good_row(), ensure_ascii=False, sort_keys=True) + "\n")
            handle.write(json.dumps(never_auto_row(), ensure_ascii=False, sort_keys=True) + "\n")
            handle.write(json.dumps(propagation_preview_row(), ensure_ascii=False, sort_keys=True) + "\n")
            handle.write(json.dumps(component_enriched_two_vote_row(), ensure_ascii=False, sort_keys=True) + "\n")
            handle.write(json.dumps(source_disagreement_row(), ensure_ascii=False, sort_keys=True) + "\n")
        row = good_row()
        row["quran_locs"] = ["33:63:1"]
        weak_propagation = propagation_preview_row()
        weak_propagation["required_gate"] = "auto_safe"
        component_propagation = component_enriched_two_vote_row()
        component_propagation.update({
            "lane": "propagation_safe_candidate",
            "scope": "parse_key_family_readonly_preview",
            "required_gate": "auto_safe_after_preview",
            "gate_reasons": ["parse_gate:auto_safe", "requires_pre_apply_family_preview"],
        })
        component_propagation["parse"] = dict(component_propagation["parse"])
        component_propagation["parse"].update({
            "gate": "auto_safe",
            "grammar_triggers": [],
        })
        with io.open(bad, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.write(json.dumps(weak_propagation, ensure_ascii=False, sort_keys=True) + "\n")
            handle.write(json.dumps(component_propagation, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(good)
        if count != 5 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        component_rows = [
            row for _line, row in iter_jsonl(good)
            if row.get("component_candidate_entries")
        ]
        if len(component_rows) != 1 or component_rows[0].get("lane") != "two_vote_required":
            print("SELF-TEST FAIL component lane:", component_rows)
            return 1
        count, errors = validate(bad)
        if count != 3 or not any("bad quran loc" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
        if not any("propagation_safe_candidate must use required_gate=auto_safe_after_preview" in err for err in errors):
            print("SELF-TEST FAIL weak propagation:", errors)
            return 1
        if not any("component candidates cannot support propagation_safe_candidate" in err for err in errors):
            print("SELF-TEST FAIL component propagation:", errors)
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
