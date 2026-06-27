#!/usr/bin/env python3
"""Validate bounded dogfood review subagent outputs.

These rows are review routing evidence only. They must stay exact-addressed,
source-clean, non-applying, and limited to the approved next-state vocabulary.
"""

import argparse
import json
import os
import re
import tempfile

import validate_full_corpus_dogfood_subagent_lanes as boundary_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_review_output.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

REQUIRED_KEYS = (
    "packet_id",
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_gloss",
    "review_lane",
    "classification",
    "next_state",
    "detected_issue",
    "evidence_summary",
    "procedure_or_rule",
    "recommended_next_action",
    "public_boundary_status",
    "confidence",
    "requires_two_vote",
    "may_apply_live",
)

ALLOWED_CLASSES = boundary_validator.ALLOWED_CLASSES
ALLOWED_CONFIDENCE = boundary_validator.ALLOWED_CONFIDENCE
ALLOWED_NEXT_STATES = {
    "repair_candidate",
    "blocker_queue_row",
    "production_bug_lesson",
    "sarf_nahw_procedure_improvement",
    "drill_regression_fixture",
    "renderer_requirement",
    "entry_linkage_review",
    "no_action",
}
ALLOWED_LANES = {
    "sarf-component-reviewer",
    "nahw-function-reviewer",
    "rich-renderer-reviewer",
    "production-bug-lesson-writer",
    "qamus-entry-linkage-reviewer",
    "learner-explanation-reviewer",
}


def _err(errors, path, line_no, message):
    errors.append("%s:%s: %s" % (path, line_no, message))


def validate_file(path, expect_min_rows=1):
    errors = []
    rows = 0
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                _err(errors, path, line_no, "invalid JSON: %s" % exc)
                continue
            rows += 1
            keys = set(row)
            missing = [key for key in REQUIRED_KEYS if key not in keys]
            extra = sorted(keys - set(REQUIRED_KEYS))
            if missing:
                _err(errors, path, line_no, "missing keys: %s" % ", ".join(missing))
            if extra:
                _err(errors, path, line_no, "unexpected keys: %s" % ", ".join(extra))
            packet_id = str(row.get("packet_id", ""))
            if not packet_id.startswith("dogfood-lane-packet:"):
                _err(errors, path, line_no, "packet_id must start dogfood-lane-packet:")
            if not QURAN_RE.match(str(row.get("quran_loc", ""))):
                _err(errors, path, line_no, "bad quran_loc")
            if not WBW_RE.match(str(row.get("wbw_loc", ""))):
                _err(errors, path, line_no, "bad wbw_loc")
            if row.get("review_lane") not in ALLOWED_LANES:
                _err(errors, path, line_no, "bad review_lane %r" % row.get("review_lane"))
            if row.get("classification") not in ALLOWED_CLASSES:
                _err(errors, path, line_no, "bad classification %r" % row.get("classification"))
            if row.get("next_state") not in ALLOWED_NEXT_STATES:
                _err(errors, path, line_no, "bad next_state %r" % row.get("next_state"))
            if row.get("confidence") not in ALLOWED_CONFIDENCE:
                _err(errors, path, line_no, "bad confidence %r" % row.get("confidence"))
            if not isinstance(row.get("requires_two_vote"), bool):
                _err(errors, path, line_no, "requires_two_vote must be boolean")
            if row.get("may_apply_live") is not False:
                _err(errors, path, line_no, "may_apply_live must be false")
            if not boundary_validator._is_source_clean_boundary(row.get("public_boundary_status")):
                _err(errors, path, line_no, "public_boundary_status must be source-clean or no-public-hover")
            for text_key in ("surface", "detected_issue", "evidence_summary", "procedure_or_rule", "recommended_next_action"):
                if not str(row.get(text_key, "")).strip():
                    _err(errors, path, line_no, "%s must be non-empty" % text_key)
    if rows < expect_min_rows:
        errors.append("%s: expected at least %s rows, got %s" % (path, expect_min_rows, rows))
    return {"path": path, "rows": rows, "errors": errors}


def self_test():
    good = {
        "packet_id": "dogfood-lane-packet:wbw_33_63_1",
        "quran_loc": "quran:33:63:1",
        "wbw_loc": "wbw:33:63:1",
        "surface": "يَسْأَلُكَ",
        "current_gloss": "to ask, question",
        "review_lane": "sarf-component-reviewer",
        "classification": "known_defect",
        "next_state": "repair_candidate",
        "detected_issue": "attached object pronoun omitted",
        "evidence_summary": "exact-addressed row preserves the suffix-pronoun defect for review",
        "procedure_or_rule": "sarf/procedures/clitic-and-host-morphology.md",
        "recommended_next_action": "build token-only repair candidate; do not apply live",
        "public_boundary_status": "source_clean:qamus/authored/en",
        "confidence": "high",
        "requires_two_vote": True,
        "may_apply_live": False,
    }
    bad = dict(good)
    bad["may_apply_live"] = True
    with tempfile.TemporaryDirectory(prefix="dogfood-review-output-") as td:
        good_path = os.path.join(td, "good.jsonl")
        bad_path = os.path.join(td, "bad.jsonl")
        with open(good_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(good, ensure_ascii=False, sort_keys=True) + "\n")
        with open(bad_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(bad, ensure_ascii=False, sort_keys=True) + "\n")
        good_result = validate_file(good_path)
        bad_result = validate_file(bad_path)
        if good_result["errors"]:
            raise SystemExit("good self-test row failed: %s" % good_result["errors"])
        if not bad_result["errors"]:
            raise SystemExit("bad self-test row unexpectedly passed")
    print("PASS - full-corpus dogfood review output validator self-test")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*")
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    paths = args.jsonl or [SAMPLE]
    results = [validate_file(path, args.expect_min_rows) for path in paths]
    errors = [err for result in results for err in result["errors"]]
    if errors:
        print(json.dumps({"ok": False, "error_count": len(errors), "errors": errors[:100]}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "files": results}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
