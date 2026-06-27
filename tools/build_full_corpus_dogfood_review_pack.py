#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build exact-addressed review packets from full-corpus hover dogfood audit rows.

This is a read-only bridge from corpus-wide dogfooding to future review/apply
lanes. It does not author hovers, mutate live Qamus, rebuild WBW, or claim
coverage. Every output row starts from exact quran/wbw addresses rather than
surface text.
"""

import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOGFOOD_SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_hover_dogfood_audit.sample.jsonl")
DEFAULT_LESSON_SAMPLE = os.path.join(ROOT, "qamus", "examples", "dogfood_production_bug_lesson.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

CLASS_PRIORITY = {
    "known_defect": 10,
    "token_only_override": 20,
    "pending/blocker": 30,
    "needs_sarf_review": 40,
    "needs_nahw_review": 45,
    "needs_renderer_segments": 50,
    "string_correct_but_not_rich": 60,
    "populated_uncertified": 70,
    "rich_certified": 999,
}

DETECTOR_PRIORITY = {
    "suffix_omitted": 1,
    "vocative_collapse": 2,
    "preposition_oath_host_only_hover": 3,
    "conjunction_article_omitted": 4,
    "function_preposition_flattening": 5,
    "clitic_host_collapse": 6,
    "finite_verb_dictionary_root_gloss_leakage": 7,
    "nominal_pos_leakage": 8,
    "article_duplication": 9,
    "surface_family_requires_token_only_override": 10,
}

APPLY_POLICY = {
    "apply_allowed": False,
    "live_mutation_allowed": False,
    "coverage_claim_allowed": False,
    "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
    "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
    "raw_surface_identity_allowed": False,
    "parse_key_primary_identity": False,
}


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise SystemExit("%s:%d invalid JSON: %s" % (path, line_no, exc))
    return rows


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def emit_jsonl(rows):
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))


def loc_sort_key(loc):
    text = str(loc or "").split(":", 1)[-1]
    parts = []
    for part in text.split(":"):
        try:
            parts.append(int(part))
        except Exception:
            parts.append(9999)
    return tuple(parts)


def lesson_index(lesson_rows):
    index = {}
    for row in lesson_rows or []:
        target = row.get("target_address")
        if target:
            index[target] = row
    return index


def first_detector(detectors):
    detectors = list(detectors or [])
    if not detectors:
        return None
    return sorted(detectors, key=lambda item: DETECTOR_PRIORITY.get(item, 999))[0]


def review_scope(row):
    dogfood_class = row.get("dogfood_class")
    routes = set(row.get("routes") or [])
    detectors = set(row.get("detectors") or [])
    if dogfood_class == "known_defect":
        return "defect_repair_review"
    if dogfood_class == "token_only_override":
        return "token_only_override_review"
    if dogfood_class == "pending/blocker":
        return "blocker_queue_review"
    if "renderer_rich_hover_requirement" in routes:
        return "renderer_segment_review"
    if {"suffix_omitted", "finite_verb_dictionary_root_gloss_leakage", "clitic_host_collapse"}.intersection(detectors):
        return "sarf_review"
    if {"vocative_collapse", "function_preposition_flattening", "preposition_oath_host_only_hover"}.intersection(detectors):
        return "nahw_review"
    if dogfood_class == "populated_uncertified":
        return "populated_hover_certification_review"
    return "manual_review"


def required_evidence(row):
    dogfood_class = row.get("dogfood_class")
    detectors = set(row.get("detectors") or [])
    evidence = [
        "exact quran:S:A:W and wbw:S:A:W trace",
        "public hover remains qamus/authored/en",
    ]
    if dogfood_class == "token_only_override":
        evidence.append("proof no parse-family propagation is intended")
    if dogfood_class == "pending/blocker":
        evidence.append("exact blocker must be resolved or preserved")
    if "suffix_omitted" in detectors:
        evidence.append("sarf segmentation proves attached suffix/pronoun contribution")
    if "finite_verb_dictionary_root_gloss_leakage" in detectors:
        evidence.append("finite verb form/aspect/voice/person is reflected before any hover repair")
    if "vocative_collapse" in detectors:
        evidence.append("nahw vocative pieces remain separately accounted for")
    if "preposition_oath_host_only_hover" in detectors or "function_preposition_flattening" in detectors:
        evidence.append("particle/preposition/oath function is preserved by nahw review")
    if dogfood_class == "populated_uncertified":
        evidence.append("rich morphosyntax certification is required; string presence is insufficient")
    return evidence


def priority(row):
    dogfood_class = row.get("dogfood_class")
    detectors = row.get("detectors") or []
    return (
        CLASS_PRIORITY.get(dogfood_class, 500),
        DETECTOR_PRIORITY.get(first_detector(detectors), 500),
        loc_sort_key(row.get("quran_loc")),
    )


def row_id(row):
    loc = str(row.get("wbw_loc") or "").replace(":", "_").replace("/", "_")
    cls = re.sub(r"[^a-z0-9_]+", "_", str(row.get("dogfood_class") or "unknown").lower()).strip("_")
    return "dogfood-review:%s:%s" % (cls, loc)


def validate_source_row(row):
    quran_loc = row.get("quran_loc")
    wbw_loc = row.get("wbw_loc")
    if not QURAN_RE.match(str(quran_loc)):
        raise ValueError("bad quran_loc %r" % quran_loc)
    if not WBW_RE.match(str(wbw_loc)):
        raise ValueError("bad wbw_loc %r" % wbw_loc)


def build_review_row(row, lesson=None, rank=1):
    validate_source_row(row)
    linkage = row.get("entry_linkage") or {}
    certification = row.get("certification") or {}
    public = row.get("public_boundary") or {}
    if public.get("public_leak_detected"):
        required_gate = "never_auto"
    else:
        required_gate = linkage.get("parse_gate") or certification.get("mode") or "human_review_required"
    lesson_ref = None
    if lesson:
        lesson_ref = {
            "bug_class": lesson.get("bug_class"),
            "target_address": lesson.get("target_address"),
            "validator_link": lesson.get("validator_link"),
            "regression_fixture_link": lesson.get("regression_fixture_link"),
        }
    return {
        "id": row_id(row),
        "audit_scope": "full_corpus_dogfood_review_pack",
        "priority": rank,
        "allowed_next_step": "review_only",
        "review_scope": review_scope(row),
        "dogfood_class": row.get("dogfood_class"),
        "detectors": row.get("detectors") or [],
        "routes": row.get("routes") or [],
        "target": {
            "quran_loc": row.get("quran_loc"),
            "wbw_loc": row.get("wbw_loc"),
            "surface": row.get("surface"),
            "current_visible_gloss": row.get("current_visible_gloss"),
            "hover_presence": row.get("hover_presence"),
            "rich_rendered": row.get("rich_rendered"),
        },
        "parse": {
            "parse_id": linkage.get("parse_id"),
            "parse_gate": linkage.get("parse_gate"),
            "parse_family_class": linkage.get("parse_family_class"),
            "parse_family_size": linkage.get("parse_family_size"),
            "parse_confidence": linkage.get("parse_confidence"),
        },
        "entry_linkage": {
            "resolved_qamus_entry_id": linkage.get("resolved_qamus_entry_id"),
            "resolved_sense_id": linkage.get("resolved_sense_id"),
            "decision_ids": linkage.get("decision_ids") or [],
            "whole_token_candidates": linkage.get("whole_token_candidates") or [],
            "component_candidate_entries": linkage.get("component_candidate_entries") or [],
            "no_entry_function_token_rationale": linkage.get("no_entry_function_token_rationale"),
        },
        "grammar": {
            "sarf": row.get("sarf") or {},
            "nahw": row.get("nahw") or {},
            "token_internal_segments": row.get("token_internal_segments") or [],
            "procedures": row.get("procedures") or [],
        },
        "blocker": row.get("learner_breakdown_blocker"),
        "required_gate": required_gate,
        "required_evidence": required_evidence(row),
        "production_bug_lesson": lesson_ref,
        "public_boundary": {
            "src": public.get("src"),
            "kind": public.get("kind"),
            "lang": public.get("lang"),
            "public_leak_detected": public.get("public_leak_detected"),
        },
        "apply_policy": APPLY_POLICY,
    }


def build_pack(dogfood_rows, lesson_rows=None, include_classes=None, max_rows=None):
    wanted = set(include_classes or [])
    lessons = lesson_index(lesson_rows or [])
    candidates = []
    for row in dogfood_rows:
        cls = row.get("dogfood_class")
        if cls == "rich_certified":
            continue
        if wanted and cls not in wanted:
            continue
        candidates.append(row)
    candidates.sort(key=priority)
    if max_rows is not None:
        candidates = candidates[:max_rows]
    out = []
    for idx, row in enumerate(candidates, 1):
        out.append(build_review_row(row, lesson=lessons.get(row.get("wbw_loc")), rank=idx))
    return out


def validate_pack(rows):
    errors = []
    if not rows:
        errors.append("review pack has zero rows")
        return errors
    seen = set()
    for idx, row in enumerate(rows, 1):
        if row.get("id") in seen:
            errors.append("row %d duplicate id %s" % (idx, row.get("id")))
        seen.add(row.get("id"))
        target = row.get("target") or {}
        if not QURAN_RE.match(str(target.get("quran_loc"))):
            errors.append("row %d bad quran_loc" % idx)
        if not WBW_RE.match(str(target.get("wbw_loc"))):
            errors.append("row %d bad wbw_loc" % idx)
        policy = row.get("apply_policy") or {}
        if policy.get("live_mutation_allowed") is not False or policy.get("apply_allowed") is not False:
            errors.append("row %d allows live mutation/apply" % idx)
        if policy.get("parse_key_primary_identity") is not False:
            errors.append("row %d treats parse key as primary identity" % idx)
        public = row.get("public_boundary") or {}
        if public.get("src") != "qamus" or public.get("kind") != "authored" or public.get("lang") != "en":
            errors.append("row %d public boundary is not qamus/authored/en" % idx)
        if public.get("public_leak_detected"):
            errors.append("row %d public leak detected" % idx)
        if not row.get("required_evidence"):
            errors.append("row %d lacks required evidence" % idx)
        if row.get("dogfood_class") == "token_only_override" and "proof no parse-family propagation is intended" not in row.get("required_evidence", []):
            errors.append("row %d token_only_override lacks propagation guard" % idx)
    return errors


def run_self_test():
    dogfood = read_jsonl(DEFAULT_DOGFOOD_SAMPLE)
    lessons = read_jsonl(DEFAULT_LESSON_SAMPLE)
    rows = build_pack(dogfood, lessons)
    errors = validate_pack(rows)
    if errors:
        print("SELF-TEST FAIL: %s" % "; ".join(errors))
        return 1
    if len(rows) != 2:
        print("SELF-TEST FAIL: expected 2 non-certified sample rows")
        return 1
    if rows[0]["dogfood_class"] != "known_defect":
        print("SELF-TEST FAIL: known defect should be first")
        return 1
    if rows[0]["target"]["wbw_loc"] != "wbw:33:63:1":
        print("SELF-TEST FAIL: exact target not preserved")
        return 1
    if rows[0]["production_bug_lesson"]["bug_class"] != "verb_object_suffix_omitted":
        print("SELF-TEST FAIL: dogfood lesson was not linked by exact hover address")
        return 1
    if "sarf segmentation proves attached suffix/pronoun contribution" not in rows[0]["required_evidence"]:
        print("SELF-TEST FAIL: suffix evidence requirement missing")
        return 1
    pending = [row for row in rows if row["dogfood_class"] == "pending/blocker"]
    if not pending or pending[0]["review_scope"] != "blocker_queue_review":
        print("SELF-TEST FAIL: pending row did not route to blocker queue")
        return 1
    with tempfile.TemporaryDirectory(prefix="dogfood-review-pack-") as td:
        out = os.path.join(td, "review.jsonl")
        write_jsonl(out, rows)
        loaded = read_jsonl(out)
        if len(loaded) != 2 or validate_pack(loaded):
            print("SELF-TEST FAIL: output roundtrip")
            return 1
    print("PASS — full-corpus dogfood review-pack builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dogfood-jsonl", default=DEFAULT_DOGFOOD_SAMPLE)
    parser.add_argument("--bug-lessons-jsonl")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--include-class", action="append")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(run_self_test())
    dogfood = read_jsonl(args.dogfood_jsonl)
    lessons = read_jsonl(args.bug_lessons_jsonl) if args.bug_lessons_jsonl else []
    rows = build_pack(dogfood, lessons, include_classes=args.include_class, max_rows=args.max_rows)
    errors = validate_pack(rows)
    if errors:
        raise SystemExit("review pack validation failed:\n- %s" % "\n- ".join(errors[:20]))
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, rows)
    else:
        emit_jsonl(rows)
    print(json.dumps({
        "rows": len(rows),
        "class_counts": dict(sorted(Counter(row["dogfood_class"] for row in rows).items())) if rows else {},
        "apply_allowed": False,
    }, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — full-corpus dogfood review pack built")


if __name__ == "__main__":
    from collections import Counter
    main()
