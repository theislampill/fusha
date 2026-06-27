#!/usr/bin/env python3
"""Validate read-only full-corpus dogfood subagent lane JSONL outputs.

Subagent lanes are review evidence only. They must remain exact-addressed,
source-clean, and non-applying. This validator intentionally checks only the
lane contract, not whether a reviewer agreed with every classification.
"""

import argparse
import json
import os
import re
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_subagent_lane.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

REQUIRED_KEYS = (
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_gloss",
    "classification",
    "detected_issue",
    "evidence_summary",
    "procedure_or_rule",
    "recommended_next_action",
    "public_boundary_status",
    "confidence",
    "requires_two_vote",
    "may_apply_live",
)

ALLOWED_CLASSES = {
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

ALLOWED_CONFIDENCE = {"low", "medium", "high"}

FORBIDDEN_PUBLIC_BOUNDARY_TERMS = {
    "mcp public",
    "qac public",
    "quran.com public",
    "ocr public",
    "source-photo public",
    "source_photo public",
    "informed_by public",
    "adapter public",
    "local path public",
}


def _err(errors, path, line_no, message):
    errors.append("%s:%s: %s" % (path, line_no, message))


def _is_source_clean_boundary(boundary):
    text = str(boundary or "").strip().lower()
    if not text:
        return False
    if any(term in text for term in FORBIDDEN_PUBLIC_BOUNDARY_TERMS):
        return False
    no_public_hover = (
        "no_public_hover" in text
        or "pending/no_public_hover" in text
        or "pending_no_public_gloss" in text
    )
    qamus_authored = (
        "qamus/authored/en" in text
        or ("src=qamus" in text and "kind=authored" in text and "lang=en" in text)
    )
    public_clean_signal = (
        text.startswith("source_clean")
        or text.startswith("clean:")
        or text.startswith("public-clean")
        or text.startswith("clean public boundary")
        or "no public provenance leak" in text
        or "no provenance leak" in text
        or "no public leak" in text
        or "no_external_source_names_public" in text
        or "no_external_provenance_public" in text
        or "no_internal_provenance_public" in text
    )
    return no_public_hover or (qamus_authored and public_clean_signal)


def validate_file(path, expect_min_rows=1):
    errors = []
    rows = 0
    classifications = set()
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
            if not QURAN_RE.match(str(row.get("quran_loc", ""))):
                _err(errors, path, line_no, "bad quran_loc")
            if not WBW_RE.match(str(row.get("wbw_loc", ""))):
                _err(errors, path, line_no, "bad wbw_loc")
            cls = row.get("classification")
            classifications.add(cls)
            if cls not in ALLOWED_CLASSES:
                _err(errors, path, line_no, "bad classification %r" % cls)
            if row.get("may_apply_live") is not False:
                _err(errors, path, line_no, "may_apply_live must be false")
            if not isinstance(row.get("requires_two_vote"), bool):
                _err(errors, path, line_no, "requires_two_vote must be boolean")
            if row.get("confidence") not in ALLOWED_CONFIDENCE:
                _err(errors, path, line_no, "bad confidence %r" % row.get("confidence"))
            boundary = str(row.get("public_boundary_status", ""))
            if not _is_source_clean_boundary(boundary):
                _err(errors, path, line_no, "public_boundary_status must describe source-clean qamus/authored/en output or no public hover")
            for text_key in ("surface", "detected_issue", "evidence_summary", "procedure_or_rule", "recommended_next_action"):
                if not str(row.get(text_key, "")).strip():
                    _err(errors, path, line_no, "%s must be non-empty" % text_key)
    if rows < expect_min_rows:
        errors.append("%s: expected at least %s rows, got %s" % (path, expect_min_rows, rows))
    return {
        "path": path,
        "rows": rows,
        "classifications": sorted(str(item) for item in classifications),
        "errors": errors,
    }


def self_test():
    good = {
        "quran_loc": "quran:22:18:17",
        "wbw_loc": "wbw:22:18:17",
        "surface": "وَالشَّجَرُ",
        "current_gloss": "and + the trees",
        "classification": "needs_renderer_segments",
        "detected_issue": "rich display missing segment breakdown",
        "evidence_summary": "surface has conjunction, article, and host noun; row is not rich-certified",
        "procedure_or_rule": "qamus/procedures/source-triangulation-and-public-boundary.md",
        "recommended_next_action": "route to renderer/rich-hover requirement queue",
        "public_boundary_status": "source_clean:qamus/authored/en",
        "confidence": "high",
        "requires_two_vote": True,
        "may_apply_live": False,
    }
    bad = dict(good)
    bad["may_apply_live"] = True
    bad_boundary = dict(good)
    bad_boundary["public_boundary_status"] = "qamus/authored/en but QAC public"
    with tempfile.TemporaryDirectory(prefix="dogfood-subagent-lane-") as td:
        good_path = os.path.join(td, "good.jsonl")
        bad_path = os.path.join(td, "bad.jsonl")
        bad_boundary_path = os.path.join(td, "bad-boundary.jsonl")
        with open(good_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(good, ensure_ascii=False, sort_keys=True) + "\n")
        with open(bad_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(bad, ensure_ascii=False, sort_keys=True) + "\n")
        with open(bad_boundary_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(bad_boundary, ensure_ascii=False, sort_keys=True) + "\n")
        good_result = validate_file(good_path)
        bad_result = validate_file(bad_path)
        bad_boundary_result = validate_file(bad_boundary_path)
        if good_result["errors"]:
            raise SystemExit("good self-test row failed: %s" % good_result["errors"])
        if not bad_result["errors"]:
            raise SystemExit("bad self-test row unexpectedly passed")
        if not bad_boundary_result["errors"]:
            raise SystemExit("bad boundary self-test row unexpectedly passed")
    print("PASS - full-corpus dogfood subagent lane validator self-test")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*", help="Subagent lane JSONL files")
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    paths = args.jsonl or [SAMPLE]
    all_results = [validate_file(path, expect_min_rows=args.expect_min_rows) for path in paths]
    errors = []
    for result in all_results:
        errors.extend(result["errors"])
    if errors:
        print(json.dumps({"ok": False, "errors": errors[:100], "error_count": len(errors)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "files": all_results}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
