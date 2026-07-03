#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate VN-00 aggressive false-closure flywheel fixtures.

The VN-00 public crawl found repeated cases where a qword looked "handled"
because a hover or color existed, while root, prefix, suffix, article,
particle role, or token-vs-phrase contribution was still hidden. This validator
turns those families into a Fusha regression gate.

It is repo-local and public-safe: rows contain only qamus-authored expectations,
no external wording, no local paths, and no live-apply authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

SARF_FIXTURE = ROOT / "sarf" / "evals" / "vn00-aggressive-false-closure.jsonl"
NAHW_FIXTURE = ROOT / "nahw" / "evals" / "vn00-aggressive-false-closure.jsonl"
PUBLIC_SARF_FIXTURE = ROOT / "sarf" / "evals" / "vn00-public-visual-andon.jsonl"
PUBLIC_NAHW_FIXTURE = ROOT / "nahw" / "evals" / "vn00-public-visual-andon.jsonl"
DRILL = ROOT / "curriculum" / "drills" / "vn00-aggressive-hover-closure.md"
META_LATTICE_QUEUE = ROOT / "qamus" / "reports" / "vn00-public-andon-20260703" / "plan18-meta-lattice-projection-queue.jsonl"
TYPED_EDGE_QUEUE = ROOT / "qamus" / "reports" / "vn00-public-andon-20260703" / "plan18-typed-edge-transclusion-queue.jsonl"
PARSER_FIXTURE = ROOT / "fusha" / "parser" / "eval" / "vn00-aggressive-false-closure-parser-fixtures.jsonl"

SARF_CLASSES = {
    "missing_root_in_hover",
    "stem_only_hover_or_root_not_asserted",
    "hidden_suffix_or_plural",
    "hidden_suffix_or_pronoun",
    "hidden_prefix_or_derivative",
    "root_present_but_pattern_or_derivative_not_segmented",
    "root_present_but_nominal_pattern_not_segmented",
    "nominal_ta_morphology_hidden",
    "broken_plural_underexplained",
    "uncolored_or_flat_qword",
}

NAHW_CLASSES = {
    "article_or_proclitic_not_explained",
    "common_particle_role_underexplained",
    "common_particle_transclusion_miss",
    "token_gloss_wrong_or_phrase_only",
    "preposition_pronoun_undersegmented",
}

REQUIRED_REPRESENTATIVES = {
    "sarf": {
        ("4:92:3", "لِمُؤْمِنٍ", "root_present_but_pattern_or_derivative_not_segmented"),
        ("9:71:4", "أَوْلِيَآءُ", "broken_plural_underexplained"),
        ("4:91:101", "يُرِيدُونَ", "hidden_suffix_or_plural"),
        ("4:91:103", "يَأْمَنُوكُمْ", "hidden_suffix_or_pronoun"),
        ("4:91:104", "وَيَأْمَنُوا۟", "hidden_suffix_or_plural"),
        ("4:91:105", "قَوْمَهُمْ", "hidden_suffix_or_pronoun"),
        ("9:6:13", "مَأْمَنَهُۥ", "root_present_but_pattern_or_derivative_not_segmented"),
        ("2:283:17", "أَمَٰنَتَهُۥ", "nominal_ta_morphology_hidden"),
        ("2:283:17", "أَمَٰنَتَهُۥ", "root_present_but_nominal_pattern_not_segmented"),
    },
    "nahw": {
        ("4:92:3", "لِمُؤْمِنٍ", "common_particle_transclusion_miss"),
        ("4:92:3", "لِمُؤْمِنٍ", "article_or_proclitic_not_explained"),
        ("4:91:102", "أَن", "common_particle_role_underexplained"),
        ("4:91:104", "وَيَأْمَنُوا۟", "article_or_proclitic_not_explained"),
    },
}

REQUIRED_BATCH05A_PUBLIC_REPRESENTATIVES = {
    "sarf": {
        ("30:44:2", "كَفَرَ", "generic_placeholder_hover"),
        ("64:2:4", "مُؤْمِنٌ", "derivative_prefix_hidden"),
        ("65:5:11", "سَيِّـَٔاتِهِۦ", "content_root_hidden"),
        ("2:161:6", "كُفَّارٌ", "suffix_or_inflection_hidden"),
        ("25:70:2", "عَمَلًا", "tanwin_or_case_visible_but_unexplained"),
        ("114:2:1", "مَلِكِ", "source_clean_fact_available_but_not_projected"),
        ("12:4:10", "كَوْكَبًۭا", "tanwin_or_case_visible_but_unexplained"),
        ("7:146:13", "ءَايَةٍۢ", "tanwin_or_case_visible_but_unexplained"),
    },
    "nahw": {
        ("5:65:1", "لَكَفَّرْنَا", "article_or_proclitic_not_explained"),
        ("2:88:4", "بِكُفْرِهِمْ", "preposition_pronoun_undersegmented"),
    },
    "meta_lattice": {
        ("2:88:2", "لَعَنَهُمُ", "source_address_inconsistent"),
        ("2:88:2", "لَعَنَهُمُ", "source_clean_fact_available_but_not_projected"),
        ("30:44:2", "كَفَرَ", "peer_payload_richer_than_current"),
        ("30:44:2", "كَفَرَ", "transclusion_peer_richer_than_claimed_page"),
        ("64:2:4", "مُؤْمِنٌ", "derivative_prefix_hidden"),
        ("114:2:1", "مَلِكِ", "source_clean_fact_available_but_not_projected"),
        ("12:4:10", "كَوْكَبًۭا", "tanwin_or_case_visible_but_unexplained"),
        ("7:146:13", "ءَايَةٍۢ", "tanwin_or_case_visible_but_unexplained"),
    },
    "typed_edge": {
        ("2:88:2", "لَعَنَهُمُ", "source_address_inconsistent"),
        ("2:88:2", "لَعَنَهُمُ", "source_clean_fact_available_but_not_projected"),
        ("14:7:2", "شَكَرْتُمْ", "source_clean_fact_available_but_not_projected"),
        ("114:2:1", "مَلِكِ", "source_clean_fact_available_but_not_projected"),
    },
}

REQUIRED_BATCH05D_PUBLIC_REPRESENTATIVES = {
    "sarf": {
        ("2:102:1", "وَٱتَّبَعُوا۟", "suffix_or_inflection_hidden"),
        ("2:102:38", "يُفَرِّقُونَ", "derivative_prefix_hidden"),
        ("43:77:8", "مَّٰكِثُونَ", "derivative_prefix_hidden"),
        ("43:77:8", "مَّٰكِثُونَ", "suffix_or_inflection_hidden"),
    },
    "nahw": {
        ("80:33:1", "فَإِذَا", "function_token_or_particle_flat"),
        ("80:33:1", "فَإِذَا", "source_clean_fact_available_but_not_projected"),
    },
    "meta_lattice": {
        ("2:102:1", "وَٱتَّبَعُوا۟", "subject_suffix_hidden"),
        ("2:102:38", "يُفَرِّقُونَ", "finite_prefix_hidden"),
        ("43:77:8", "مَّٰكِثُونَ", "derivative_prefix_hidden"),
        ("43:77:8", "مَّٰكِثُونَ", "sound_plural_suffix_hidden"),
        ("80:33:1", "فَإِذَا", "source_clean_fact_available_but_not_projected"),
    },
    "typed_edge": {
        ("43:77:8", "مَّٰكِثُونَ", "derivative_prefix_hidden"),
        ("80:33:1", "فَإِذَا", "source_clean_fact_available_but_not_projected"),
    },
}

REQUIRED_PARSER_REPRESENTATIVES = {
    ("65:5:11", "سَيِّـَٔاتِهِۦ", "content_root_hidden"),
    ("64:2:4", "مُؤْمِنٌ", "derivative_prefix_hidden"),
    ("30:44:2", "كَفَرَ", "generic_placeholder_hover"),
    ("5:65:1", "لَكَفَّرْنَا", "preposition_pronoun_undersegmented"),
    ("2:88:2", "لَعَنَهُمُ", "source_address_inconsistent"),
    ("2:161:6", "كُفَّارٌ", "suffix_or_inflection_hidden"),
    ("30:44:2", "كَفَرَ", "transclusion_peer_richer_than_claimed_page"),
    ("2:102:1", "وَٱتَّبَعُوا۟", "suffix_or_inflection_hidden"),
    ("2:102:38", "يُفَرِّقُونَ", "derivative_prefix_hidden"),
    ("43:77:8", "مَّٰكِثُونَ", "derivative_prefix_hidden"),
    ("80:33:1", "فَإِذَا", "source_clean_fact_available_but_not_projected"),
}

PARSER_ROW_FIELDS = {
    "case_id",
    "loc",
    "surface",
    "failure_family",
    "expected_parser_guard",
    "parser_followup",
    "blocks_page_closure",
    "unlocks_vn01",
}

REQUIRED_ROW_FIELDS = {
    "case_id",
    "source_scope",
    "loc",
    "surface",
    "aggressive_class",
    "expected_segments",
    "reject_if",
    "flywheel_targets",
    "blocks_page_closure",
    "unlocks_vn01",
}

LEAK_TERMS = (
    "informed_by",
    "qac",
    "quran.com",
    "mcp",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
    "root.txt",
)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: row must be an object")
            row["_line"] = lineno
            rows.append(row)
    return rows


def leaks_public_boundary(value: object) -> list[str]:
    text = json.dumps(value, ensure_ascii=False).lower()
    return [term for term in LEAK_TERMS if term in text]


def validate_rows(path: Path, rows: list[dict], required_classes: set[str], side: str) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_loc_classes: set[tuple[str, str]] = set()
    classes: set[str] = set()
    for row in rows:
        lineno = row.pop("_line")
        missing = REQUIRED_ROW_FIELDS - set(row)
        if missing:
            errors.append(f"{path}:{lineno}: missing fields: {', '.join(sorted(missing))}")
            continue
        case_id = str(row["case_id"])
        if case_id in seen_ids:
            errors.append(f"{path}:{lineno}: duplicate case_id {case_id}")
        seen_ids.add(case_id)
        loc = str(row["loc"])
        cls = str(row["aggressive_class"])
        loc_class = (loc, cls)
        if loc_class in seen_loc_classes:
            errors.append(f"{path}:{lineno}: duplicate loc/class {loc} {cls}")
        seen_loc_classes.add(loc_class)
        classes.add(cls)
        if cls not in required_classes:
            errors.append(f"{path}:{lineno}: unexpected {side} aggressive_class {cls!r}")
        if not isinstance(row["expected_segments"], list) or len(row["expected_segments"]) < 2:
            errors.append(f"{path}:{lineno}: expected_segments must name at least two visible pieces")
        if not isinstance(row["reject_if"], list) or not row["reject_if"]:
            errors.append(f"{path}:{lineno}: reject_if must be a nonempty list")
        if not isinstance(row["flywheel_targets"], list) or not row["flywheel_targets"]:
            errors.append(f"{path}:{lineno}: flywheel_targets must be a nonempty list")
        if row["blocks_page_closure"] is not True:
            errors.append(f"{path}:{lineno}: blocks_page_closure must be true")
        if row["unlocks_vn01"] is not True:
            errors.append(f"{path}:{lineno}: unlocks_vn01 must be true")
        for target in row["flywheel_targets"]:
            if target not in {"sarf", "nahw", "validator", "parser", "drill", "curriculum", "meta_lattice"}:
                errors.append(f"{path}:{lineno}: unknown flywheel target {target!r}")
        leaks = leaks_public_boundary(row)
        if leaks:
            errors.append(f"{path}:{lineno}: public fixture leaks {', '.join(leaks)}")

    missing_classes = required_classes - classes
    if missing_classes:
        errors.append(f"{path}: missing aggressive classes: {', '.join(sorted(missing_classes))}")
    return errors


def validate_representatives(sarf_rows: list[dict], nahw_rows: list[dict]) -> list[str]:
    errors: list[str] = []
    actual = {
        "sarf": {(str(row.get("loc")), str(row.get("surface")), str(row.get("aggressive_class"))) for row in sarf_rows},
        "nahw": {(str(row.get("loc")), str(row.get("surface")), str(row.get("aggressive_class"))) for row in nahw_rows},
    }
    for side, required in REQUIRED_REPRESENTATIVES.items():
        missing = required - actual[side]
        if missing:
            pretty = ", ".join(f"{loc} {surface} {cls}" for loc, surface, cls in sorted(missing))
            errors.append(f"{side} fixture missing required v003 representatives: {pretty}")
    return errors


def _families(row: dict) -> set[str]:
    return {part.strip() for part in str(row.get("failure_family", "")).split(",") if part.strip()}


def _public_actual(rows: list[dict]) -> set[tuple[str, str, str]]:
    actual: set[tuple[str, str, str]] = set()
    for row in rows:
        loc = str(row.get("loc"))
        surface = str(row.get("surface"))
        family = str(row.get("failure_family"))
        actual.add((loc, surface, family))
    return actual


def _queue_actual(rows: list[dict]) -> set[tuple[str, str, str]]:
    actual: set[tuple[str, str, str]] = set()
    for row in rows:
        loc = str(row.get("loc"))
        surface = str(row.get("surface"))
        for family in _families(row):
            actual.add((loc, surface, family))
    return actual


def validate_batch05a_public_representatives(
    public_sarf_rows: list[dict],
    public_nahw_rows: list[dict],
    meta_rows: list[dict],
    typed_rows: list[dict],
) -> list[str]:
    errors: list[str] = []
    actual = {
        "sarf": _public_actual(public_sarf_rows),
        "nahw": _public_actual(public_nahw_rows),
        "meta_lattice": _queue_actual(meta_rows),
        "typed_edge": _queue_actual(typed_rows),
    }
    for side, required in REQUIRED_BATCH05A_PUBLIC_REPRESENTATIVES.items():
        missing = required - actual[side]
        if missing:
            pretty = ", ".join(f"{loc} {surface} {family}" for loc, surface, family in sorted(missing))
            errors.append(f"{side} fixture missing required batch05a representatives: {pretty}")
    for side, required in REQUIRED_BATCH05D_PUBLIC_REPRESENTATIVES.items():
        missing = required - actual[side]
        if missing:
            pretty = ", ".join(f"{loc} {surface} {family}" for loc, surface, family in sorted(missing))
            errors.append(f"{side} fixture missing required batch05d representatives: {pretty}")
    for path, rows in (
        (PUBLIC_SARF_FIXTURE, public_sarf_rows),
        (PUBLIC_NAHW_FIXTURE, public_nahw_rows),
        (META_LATTICE_QUEUE, meta_rows),
        (TYPED_EDGE_QUEUE, typed_rows),
    ):
        for row in rows:
            leaks = leaks_public_boundary(row)
            if leaks:
                errors.append(f"{path}: public fixture leaks {', '.join(leaks)}")
    return errors


def validate_parser_fixture(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    actual: set[tuple[str, str, str]] = set()
    for row in rows:
        lineno = row.pop("_line")
        missing = PARSER_ROW_FIELDS - set(row)
        if missing:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: missing fields: {', '.join(sorted(missing))}")
            continue
        case_id = str(row["case_id"])
        if case_id in seen_ids:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: duplicate case_id {case_id}")
        seen_ids.add(case_id)
        loc = str(row["loc"])
        surface = str(row["surface"])
        family = str(row["failure_family"])
        actual.add((loc, surface, family))
        if not isinstance(row["expected_parser_guard"], list) or len(row["expected_parser_guard"]) < 2:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: expected_parser_guard must name at least two parser obligations")
        if not isinstance(row["parser_followup"], list) or not row["parser_followup"]:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: parser_followup must be a nonempty list")
        if row["blocks_page_closure"] is not True:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: blocks_page_closure must be true")
        if row["unlocks_vn01"] is not True:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: unlocks_vn01 must be true")
        leaks = leaks_public_boundary(row)
        if leaks:
            errors.append(f"{PARSER_FIXTURE}:{lineno}: parser fixture leaks {', '.join(leaks)}")
    missing_representatives = REQUIRED_PARSER_REPRESENTATIVES - actual
    if missing_representatives:
        pretty = ", ".join(f"{loc} {surface} {family}" for loc, surface, family in sorted(missing_representatives))
        errors.append(f"parser fixture missing required batch05a representatives: {pretty}")
    return errors


def validate_tree() -> list[str]:
    errors: list[str] = []
    for path in (SARF_FIXTURE, NAHW_FIXTURE, PUBLIC_SARF_FIXTURE, PUBLIC_NAHW_FIXTURE, META_LATTICE_QUEUE, TYPED_EDGE_QUEUE, PARSER_FIXTURE, DRILL):
        if not path.exists():
            errors.append(f"missing VN-00 aggressive flywheel artifact: {path.relative_to(ROOT)}")
    if errors:
        return errors

    sarf_rows = load_jsonl(SARF_FIXTURE)
    nahw_rows = load_jsonl(NAHW_FIXTURE)
    public_sarf_rows = load_jsonl(PUBLIC_SARF_FIXTURE)
    public_nahw_rows = load_jsonl(PUBLIC_NAHW_FIXTURE)
    meta_rows = load_jsonl(META_LATTICE_QUEUE)
    typed_rows = load_jsonl(TYPED_EDGE_QUEUE)
    parser_rows = load_jsonl(PARSER_FIXTURE)
    if len(sarf_rows) < 8:
        errors.append("sarf aggressive fixture needs at least 8 rows")
    if len(nahw_rows) < 8:
        errors.append("nahw aggressive fixture needs at least 8 rows")
    errors.extend(validate_rows(SARF_FIXTURE, sarf_rows, SARF_CLASSES, "sarf"))
    errors.extend(validate_rows(NAHW_FIXTURE, nahw_rows, NAHW_CLASSES, "nahw"))
    errors.extend(validate_representatives(sarf_rows, nahw_rows))
    errors.extend(validate_batch05a_public_representatives(public_sarf_rows, public_nahw_rows, meta_rows, typed_rows))
    errors.extend(validate_parser_fixture(parser_rows))

    drill = DRILL.read_text(encoding="utf-8")
    for marker in (
        "missing_root_in_hover",
        "hidden_suffix_or_plural",
        "broken_plural_underexplained",
        "nominal_ta_morphology_hidden",
        "article_or_proclitic_not_explained",
        "common_particle_transclusion_miss",
        "token_gloss_wrong_or_phrase_only",
        "VN-01",
    ):
        if marker not in drill:
            errors.append(f"{DRILL.relative_to(ROOT)} missing drill marker {marker}")
    for term in LEAK_TERMS:
        if term in drill.lower():
            errors.append(f"{DRILL.relative_to(ROOT)} leaks {term}")
    return errors


def self_test() -> int:
    failures: list[str] = []
    good = {
        "case_id": "selftest",
        "source_scope": "VN-00",
        "loc": "1:1:1",
        "surface": "سَلَامٌ",
        "aggressive_class": "missing_root_in_hover",
        "expected_segments": ["root", "host"],
        "reject_if": ["root hidden"],
        "flywheel_targets": ["sarf", "validator", "drill"],
        "blocks_page_closure": True,
        "unlocks_vn01": True,
    }
    if validate_rows(Path("selftest.jsonl"), [dict(good, _line=1)], {"missing_root_in_hover"}, "sarf"):
        failures.append("good row should pass")
    bad = dict(good, _line=1)
    bad["expected_segments"] = ["host"]
    if not validate_rows(Path("selftest.jsonl"), [bad], {"missing_root_in_hover"}, "sarf"):
        failures.append("single-segment row should fail")
    bad = dict(good, _line=1)
    bad["blocks_page_closure"] = False
    if not validate_rows(Path("selftest.jsonl"), [bad], {"missing_root_in_hover"}, "sarf"):
        failures.append("non-blocking row should fail")
    bad = dict(good, _line=1)
    bad["surface"] = "mentions qac"
    if not validate_rows(Path("selftest.jsonl"), [bad], {"missing_root_in_hover"}, "sarf"):
        failures.append("source leak should fail")
    for failure in failures:
        print("FAIL " + failure)
    if not failures:
        print("ok   validate_vn00_aggressive_false_closure self-test: class coverage, closure gate, flywheel targets, and leak checks reject")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate VN-00 aggressive false-closure flywheel fixtures.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate_tree()
    for error in errors:
        print("FAIL " + error)
    print(f"checked VN-00 aggressive false-closure flywheel fixtures: {len(errors)} violation(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
