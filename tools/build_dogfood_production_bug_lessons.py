#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build production-bug lesson candidates from full-corpus dogfood audit rows.

This is a read-only bridge: it does not author hover fixes, mutate live Qamus,
rebuild WBW, or certify closure. It turns graph-addressed dogfood failures into
validated lesson skeletons so sarf/nahw drills and regressions can follow the
same exact token addresses that produced the production failure.
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(ROOT, "qamus", "examples", "full_corpus_hover_dogfood_audit.sample.jsonl")
DEFAULT_VALIDATOR = "tools/validate_production_bug_lessons.py"
PRODUCTION_VALIDATOR = os.path.join(ROOT, "tools", "validate_production_bug_lessons.py")

ALLOWED_GATES = {
    "token_review",
    "auto_safe_after_preview",
    "two_vote_required",
    "human_review_required",
    "owner_review_required",
    "never_auto",
}


TEMPLATES = {
    "suffix_omitted": {
        "bug_class": "verb_object_suffix_omitted",
        "level": "beginner",
        "what_failed": "A composed token hover omitted an attached suffix pronoun.",
        "sarf_lesson": "Segment the host and suffix pronoun before choosing an English hover.",
        "nahw_lesson": "A following explicit subject or surrounding phrase does not erase an attached object or possessive pronoun.",
        "learner_explanation": "The suffix is a real grammatical piece of the written token; the hover must either show it or stay pending.",
        "drill_prompt": "Mark the host and attached suffix pronoun, then write what each piece contributes.",
        "procedure_links": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/pronoun-attachment.md"],
    },
    "conjunction_article_omitted": {
        "bug_class": "conjunction_article_host_omitted",
        "level": "beginner",
        "what_failed": "The hover showed the host while dropping a visible conjunction or definite article.",
        "sarf_lesson": "For written tokens with وَ/فَ plus ال, segment conjunction, article, and host before glossing.",
        "nahw_lesson": "The conjunction or resumptive particle has its own function and cannot disappear into the noun host.",
        "learner_explanation": "A written token may contain 'and' plus 'the' plus a host noun; each visible piece should be teachable.",
        "drill_prompt": "Break the token into conjunction, article, and host, then write the contribution of each piece.",
        "procedure_links": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/particle-decision.md"],
    },
    "vocative_collapse": {
        "bug_class": "vocative_token_collapsed",
        "level": "intermediate",
        "what_failed": "Adjacent vocative pieces were collapsed into one phrase-level gloss.",
        "sarf_lesson": "Do not merge neighboring function tokens merely because English renders the phrase compactly.",
        "nahw_lesson": "Vocative particles, vocative bridges, and addressees have distinct roles in the address construction.",
        "learner_explanation": "The learner should see which token supplies the call and which token bridges to the addressee.",
        "drill_prompt": "Label the vocative particle, bridge, and addressee; explain what each token contributes.",
        "procedure_links": ["nahw/procedures/exception-and-vocative-review.md", "nahw/procedures/function-token-hover-review.md"],
    },
    "preposition_oath_host_only_hover": {
        "bug_class": "oath_or_preposition_role_omitted",
        "level": "intermediate",
        "what_failed": "The host noun was translated while an attached preposition or oath particle disappeared.",
        "sarf_lesson": "Attached particles are grammatical pieces of the written token and must be segmented before host glossing.",
        "nahw_lesson": "A bāʾ preposition or oath wāw changes the phrase function; preserve that relation or keep the row pending.",
        "learner_explanation": "The hover must teach both the relation marker and the host noun, not just the host.",
        "drill_prompt": "Identify the particle, article if present, and host; decide whether the particle is preposition, oath, or conjunction.",
        "procedure_links": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/pp-attachment-review.md"],
    },
    "article_duplication": {
        "bug_class": "article_duplicated_in_host_gloss",
        "level": "beginner",
        "what_failed": "The definite article was segmented and then repeated inside the host gloss.",
        "sarf_lesson": "When ال is its own segment, the host contribution should not repeat 'the'.",
        "nahw_lesson": "The noun remains definite through the article; English composition should show article plus clean host meaning.",
        "learner_explanation": "Teach 'the' once for the article, then the host meaning without duplicating it.",
        "drill_prompt": "Rewrite the segmented hover as article plus host without repeating 'the'.",
        "procedure_links": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/irab-case-mood.md"],
    },
    "finite_verb_dictionary_root_gloss_leakage": {
        "bug_class": "finite_verb_entry_gloss_leakage",
        "level": "beginner",
        "what_failed": "A lemma or dictionary gloss was shown for a finite contextual verb token.",
        "sarf_lesson": "Record aspect, voice, person, number, gender, and clitics before turning a verb entry into a hover.",
        "nahw_lesson": "Context decides subject/object wording; a root gloss is not enough for a finite verb hover.",
        "learner_explanation": "A verb token is not merely 'to do X'; the hover should preserve who acts, voice, and attached objects when known.",
        "drill_prompt": "Convert the lemma gloss into a finite token hover using the parse key and attached pronouns.",
        "procedure_links": ["sarf/procedures/verb-form-routing.md", "nahw/procedures/verb-subject-object-review.md"],
    },
    "nominal_pos_leakage": {
        "bug_class": "nominal_pos_leakage",
        "level": "intermediate",
        "what_failed": "The hover leaked a broad entry/POS family instead of the concrete nominal token role.",
        "sarf_lesson": "Distinguish noun, adjective, participle, masdar, and proper noun before reusing a root-family gloss.",
        "nahw_lesson": "Case and syntactic role decide how a nominal contributes in context.",
        "learner_explanation": "The same root can produce different noun-like words; the hover should teach the actual token.",
        "drill_prompt": "Name the nominal type, case, and role before proposing the hover.",
        "procedure_links": ["sarf/procedures/masdar-participle.md", "nahw/procedures/irab-case-mood.md"],
    },
    "function_preposition_flattening": {
        "bug_class": "particle_function_flattening",
        "level": "intermediate",
        "what_failed": "A function token was flattened into a phrase gloss without preserving its grammar role.",
        "sarf_lesson": "Function particles may have little morphology, but they still need token segmentation and exact address.",
        "nahw_lesson": "Classify particle function before authoring: vocative, relative, negation, preposition, oath, cause, result, or resumption.",
        "learner_explanation": "Function words teach sentence structure; a fluent phrase gloss can hide the very grammar the learner needs.",
        "drill_prompt": "Choose the particle function and explain why a phrase-level translation is not enough.",
        "procedure_links": ["nahw/procedures/function-token-hover-review.md", "nahw/procedures/particle-decision.md"],
    },
    "clitic_host_collapse": {
        "bug_class": "clitic_host_collapse",
        "level": "beginner",
        "what_failed": "A clitic and host were collapsed into a host-only hover.",
        "sarf_lesson": "Segment proclitics and enclitics before matching the host entry.",
        "nahw_lesson": "The clitic's role may determine relation, attachment, or object meaning.",
        "learner_explanation": "The visible clitic is part of the word the learner sees; the hover must account for it.",
        "drill_prompt": "Underline the clitic and host separately; write the contribution of each.",
        "procedure_links": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/function-token-hover-review.md"],
    },
    "surface_family_requires_token_only_override": {
        "bug_class": "surface_family_token_only_required",
        "level": "advanced",
        "what_failed": "A surface or parse family cannot safely propagate without token-addressed review.",
        "sarf_lesson": "A shared surface or parse family is recall evidence, not certification.",
        "nahw_lesson": "Referent, attachment, function, or i'rab may force token-only treatment even when forms look reusable.",
        "learner_explanation": "Some words look alike but do different work in context; the row must stay token-addressed until the gate passes.",
        "drill_prompt": "Compare two tokens in the same family and identify what blocks family-wide propagation.",
        "procedure_links": ["qamus/procedures/closure-lane-routing.md", "nahw/procedures/irab-case-mood.md"],
    },
}

DETECTOR_PRIORITY = [
    "suffix_omitted",
    "vocative_collapse",
    "preposition_oath_host_only_hover",
    "conjunction_article_omitted",
    "article_duplication",
    "finite_verb_dictionary_root_gloss_leakage",
    "nominal_pos_leakage",
    "function_preposition_flattening",
    "clitic_host_collapse",
    "surface_family_requires_token_only_override",
]


def load_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def emit_jsonl(rows):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def repo_path_exists(relpath):
    return os.path.exists(os.path.join(ROOT, relpath.replace("/", os.sep)))


def sanitize_blocker(text):
    slug = re.sub(r"[^a-z0-9_]+", "_", str(text or "dogfood_blocker").lower()).strip("_")
    return "blocker:%s" % (slug or "dogfood_blocker")


def first_existing(paths):
    seen = set()
    out = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        if repo_path_exists(path):
            out.append(path)
    return out


def choose_detector(row):
    detectors = set(row.get("detectors") or [])
    for detector in DETECTOR_PRIORITY:
        if detector in detectors:
            return detector
    if row.get("dogfood_class") == "token_only_override":
        return "surface_family_requires_token_only_override"
    return None


def normalize_gate(gate, dogfood_class):
    if gate == "auto_safe":
        return "auto_safe_after_preview"
    if gate in ALLOWED_GATES:
        return gate
    if dogfood_class == "token_only_override":
        return "token_review"
    return "human_review_required"


def entry_sense(row):
    linkage = row.get("entry_linkage") or {}
    entry = linkage.get("resolved_qamus_entry_id")
    sense = linkage.get("resolved_sense_id")
    if entry and sense is not None:
        return "%s#sense=%s" % (entry, sense)
    return None


def lesson_from_row(row):
    if "production_bug_lesson" not in (row.get("routes") or []):
        return None
    detector = choose_detector(row)
    if not detector:
        return None
    template = TEMPLATES[detector]
    quran_loc = row.get("quran_loc")
    wbw_loc = row.get("wbw_loc")
    if not quran_loc or not wbw_loc:
        raise ValueError("dogfood row lacks exact quran/wbw identity")
    procedures = first_existing(template["procedure_links"] + (row.get("procedures") or []))
    if not procedures:
        procedures = ["qamus/procedures/production-bug-lessons.md"]
    blocker_text = row.get("learner_breakdown_blocker") or template["what_failed"]
    corrected_or_pending = "pending: %s" % blocker_text
    decision_ids = (row.get("entry_linkage") or {}).get("decision_ids") or []
    row_out = {
        "bug_class": template["bug_class"],
        "token_addresses": [quran_loc],
        "visible_bad_hover": row.get("current_visible_gloss") or "(pending)",
        "corrected_hover_or_pending_reason": corrected_or_pending,
        "what_failed": "%s Source row says: %s" % (template["what_failed"], blocker_text),
        "sarf_lesson": template["sarf_lesson"],
        "nahw_lesson": template["nahw_lesson"],
        "learner_explanation": template["learner_explanation"],
        "drill_prompt": "%s Token: %s." % (template["drill_prompt"], row.get("surface") or quran_loc),
        "level": template["level"],
        "procedure_links": procedures,
        "regression_fixture_link": "qamus/examples/full_corpus_hover_dogfood_audit.sample.jsonl",
        "validator_link": "tools/validate_production_bug_lessons.py",
        "source_addresses": [quran_loc, wbw_loc],
        "edit_intent_id": None,
        "requested_scope": "token_only" if row.get("dogfood_class") != "pending/blocker" else "unsafe",
        "target_address": wbw_loc,
        "parse_id": (row.get("entry_linkage") or {}).get("parse_id"),
        "decision_id": decision_ids[0] if decision_ids else None,
        "entry_sense": entry_sense(row),
        "gate": normalize_gate((row.get("entry_linkage") or {}).get("parse_gate"), row.get("dogfood_class")),
        "blocker": sanitize_blocker(detector),
    }
    return row_out


def validate_lessons(rows):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import validate_production_bug_lessons
    with tempfile.TemporaryDirectory(prefix="dogfood-bug-lessons-") as td:
        path = os.path.join(td, "lessons.jsonl")
        write_jsonl(path, rows)
        count, errors = validate_production_bug_lessons.validate(path)
        if count != len(rows) or errors:
            raise SystemExit("built dogfood production bug lessons failed validation: %s" % errors[:20])


def build_lessons(input_jsonl, max_rows=None):
    lessons = []
    for row in load_jsonl(input_jsonl):
        lesson = lesson_from_row(row)
        if lesson:
            lessons.append(lesson)
            if max_rows is not None and len(lessons) >= max_rows:
                break
    if not lessons:
        raise SystemExit("no production-bug lesson candidates found")
    validate_lessons(lessons)
    return lessons


def self_test():
    lessons = build_lessons(DEFAULT_INPUT, max_rows=5)
    if len(lessons) != 1:
        print("SELF-TEST FAIL: expected one sample lesson, got %s" % len(lessons))
        return 1
    lesson = lessons[0]
    if lesson["bug_class"] != "verb_object_suffix_omitted":
        print("SELF-TEST FAIL: wrong bug class %r" % lesson["bug_class"])
        return 1
    if lesson["token_addresses"] != ["quran:33:63:1"]:
        print("SELF-TEST FAIL: token address not preserved")
        return 1
    if "wbw:33:63:1" not in lesson["source_addresses"]:
        print("SELF-TEST FAIL: wbw address not preserved")
        return 1
    if lesson["parse_id"] != "parse:222222222222222222222222":
        print("SELF-TEST FAIL: parse id not preserved")
        return 1
    print("PASS — dogfood production bug lesson builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dogfood-jsonl", default=DEFAULT_INPUT)
    parser.add_argument("--out-jsonl")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    lessons = build_lessons(args.dogfood_jsonl, max_rows=args.max_rows)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, lessons)
    else:
        emit_jsonl(lessons)


if __name__ == "__main__":
    main()
