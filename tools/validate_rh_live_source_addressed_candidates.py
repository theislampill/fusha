#!/usr/bin/env python3
"""Gate source-addressed RH-LIVE candidate rows for Qamus executor merge.

This validator is deliberately narrower than the arbitrary-text largelexicon
parser CLI.  It may mark a row as executor-autopromotable only when the row is
already a Qamus-authored, source-addressed RH-LIVE payload candidate and passes
the public-boundary, trace, segment, qg-class, and context gates here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
QURAN_RE = re.compile(r"^quran:(\d{1,3}:\d{1,3}:\d{1,3})$")
WBW_RE = re.compile(r"^wbw:(\d{1,3}:\d{1,3}:\d{1,3})$")

SUPPORTED_QG_CLASSES = {
    "qg-adjective",
    "qg-alternative",
    "qg-article",
    "qg-comitative",
    "qg-conditional",
    "qg-conjunction",
    "qg-demonstrative",
    "qg-derivative-prefix",
    "qg-dual-suffix",
    "qg-emphasis",
    "qg-exception",
    "qg-future-particle",
    "qg-interrogative",
    "qg-lam",
    "qg-ma-particle",
    "qg-negation",
    "qg-noun",
    "qg-noun-stem",
    "qg-number",
    "qg-oath",
    "qg-object-pronoun",
    "qg-particle",
    "qg-plural-suffix",
    "qg-possessive-pronoun",
    "qg-preposition",
    "qg-pronoun",
    "qg-proper-noun",
    "qg-question",
    "qg-referential-pronoun",
    "qg-relative",
    "qg-result",
    "qg-result-fa",
    "qg-segment",
    "qg-subject-pronoun",
    "qg-verb",
    "qg-verb-prefix",
    "qg-verb-stem",
    "qg-vocative",
}

GENERIC_CLASSES_NOT_AUTOPROMOTE = {"qg-segment"}
LEXICAL_CLASSES_NEED_ROOT_OR_NO_ROOT = {
    "qg-adjective",
    "qg-derivative-prefix",
    "qg-noun-stem",
    "qg-verb-stem",
}

PUBLIC_TEXT_FIELDS = {
    "contextual_phrase_gloss",
    "learner_explanation",
    "morphline",
    "token_contribution_gloss",
}
PUBLIC_NESTED_FIELDS = {
    "parse_key",
    "public_preview",
    "segments",
}
FORBIDDEN_PUBLIC_SUBSTRINGS = (
    "informed_by",
    "mcp",
    "qac",
    "quran.com",
    "quran_com",
    "corpus.quran",
    "tanzil",
    "tafsir",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
    "c:\\",
    "ssh",
    "password",
    "secret",
    "api_key",
    "apikey",
    "bearer",
    "internal evidence",
    "public payload",
    "keeps internal",
    "hover is authored",
)


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield line_no, json.loads(stripped)
            except json.JSONDecodeError as exc:
                yield line_no, {"__json_error__": str(exc)}


def write_jsonl(path: Path | None, rows: list[dict[str, Any]]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_public_projection(row: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    for key in PUBLIC_TEXT_FIELDS:
        if key in row:
            projection[key] = row[key]
    for key in PUBLIC_NESTED_FIELDS:
        if key in row:
            projection[key] = row[key]
    return projection


def public_leaks(row: dict[str, Any]) -> list[str]:
    blob = json.dumps(row_public_projection(row), ensure_ascii=False, sort_keys=True).lower()
    return [item for item in FORBIDDEN_PUBLIC_SUBSTRINGS if item in blob]


def nested_value(row: dict[str, Any], *keys: str) -> Any:
    cur: Any = row
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def row_entry_id(row: dict[str, Any]) -> Any:
    return row.get("entry_id") or nested_value(row, "traceability", "entry_id")


def row_source_key(row: dict[str, Any]) -> Any:
    return row.get("source_key") or nested_value(row, "traceability", "source_key")


def row_card_ref(row: dict[str, Any]) -> Any:
    return row.get("card_ref") or nested_value(row, "traceability", "card_ref")


def row_qword_index(row: dict[str, Any]) -> Any:
    return row.get("qword_index") if row.get("qword_index") is not None else nested_value(row, "traceability", "qword_index")


def segment_class(segment: dict[str, Any]) -> str:
    return str(segment.get("class") or segment.get("qg_class") or "")


def segment_classes(row: dict[str, Any]) -> set[str]:
    classes = {str(item) for item in row.get("qg_classes") or [] if item}
    for segment in row.get("segments") or []:
        if isinstance(segment, dict) and segment_class(segment):
            classes.add(segment_class(segment))
    for segment in nested_value(row, "display", "segments") or []:
        if isinstance(segment, dict) and segment_class(segment):
            classes.add(segment_class(segment))
    return classes


def has_root_or_no_root_reason(row: dict[str, Any]) -> bool:
    keys = (
        "root",
        "root_ar",
        "candidate_root",
        "qac_root",
        "base",
        "lemma",
        "no_root_reason",
        "proper_name_no_root_reason",
        "function_only_no_root_reason",
    )
    return any(row.get(key) not in (None, "", []) for key in keys)


def validate_candidate(row: dict[str, Any], line_no: int, seen_locs: set[str]) -> tuple[bool, list[str], list[str]]:
    reasons: list[str] = []
    routes: list[str] = []

    if "__json_error__" in row:
        return False, ["invalid_json"], ["validator_packet"]

    loc = str(row.get("loc") or "")
    quran_loc = str(row.get("quran_loc") or "")
    wbw_loc = str(row.get("wbw_loc") or "")
    quran_match = QURAN_RE.match(quran_loc)
    wbw_match = WBW_RE.match(wbw_loc)
    if not LOC_RE.match(loc):
        reasons.append("missing_or_invalid_loc")
        routes.append("source_crosswalk_packet")
    if not quran_match or (loc and quran_match.group(1) != loc):
        reasons.append("quran_loc_not_source_addressed")
        routes.append("source_crosswalk_packet")
    if not wbw_match or (loc and wbw_match.group(1) != loc):
        reasons.append("wbw_loc_not_source_addressed")
        routes.append("source_crosswalk_packet")
    if loc and loc in seen_locs:
        reasons.append("duplicate_candidate_loc")
        routes.append("validator_packet")
    if loc:
        seen_locs.add(loc)

    if not row_entry_id(row):
        reasons.append("missing_entry_id")
        routes.append("source_crosswalk_packet")
    if not row_source_key(row):
        reasons.append("missing_source_key")
        routes.append("source_crosswalk_packet")
    if not row_card_ref(row):
        reasons.append("missing_card_ref")
        routes.append("source_crosswalk_packet")
    if row_qword_index(row) in (None, ""):
        reasons.append("missing_qword_index")
        routes.append("source_crosswalk_packet")

    public = row.get("public_preview") or {}
    if public.get("src") != "qamus" or public.get("kind") != "authored" or public.get("lang") != "en":
        reasons.append("public_boundary_not_qamus_authored_en")
        routes.append("validator_packet")
    leaked = public_leaks(row)
    if leaked:
        reasons.append("public_boundary_leak:" + ",".join(leaked))
        routes.append("validator_packet")

    if row.get("terminal_state") not in (None, "deploy_ready"):
        reasons.append("terminal_state_not_deploy_ready")
        routes.append("validator_packet")

    surface = row.get("surface")
    segments = row.get("segments") or []
    if not isinstance(surface, str) or not surface:
        reasons.append("missing_surface")
        routes.append("validator_packet")
    if not isinstance(segments, list) or not segments:
        reasons.append("missing_segments")
        routes.append("validator_packet")
    elif "".join(str(segment.get("surface") or "") for segment in segments if isinstance(segment, dict)) != surface:
        reasons.append("segment_concat_mismatch")
        routes.append("validator_packet")

    classes = segment_classes(row)
    unsupported = sorted(cls for cls in classes if cls not in SUPPORTED_QG_CLASSES)
    if unsupported:
        reasons.append("unsupported_qg_class:" + ",".join(unsupported))
        routes.append("renderer_template_patch")
    if classes & GENERIC_CLASSES_NOT_AUTOPROMOTE:
        reasons.append("generic_qg_segment_not_autopromote")
        routes.append("executor_template_patch_ready")
    if classes & LEXICAL_CLASSES_NEED_ROOT_OR_NO_ROOT and not has_root_or_no_root_reason(row):
        reasons.append("lexical_class_missing_root_or_no_root_reason")
        routes.append("lexicon_entry_needed")

    token_gloss = str(row.get("token_contribution_gloss") or "").strip()
    phrase_gloss = str(row.get("contextual_phrase_gloss") or "").strip()
    if not token_gloss:
        reasons.append("missing_token_contribution_gloss")
        routes.append("validator_packet")
    if not phrase_gloss:
        reasons.append("missing_contextual_phrase_gloss")
        routes.append("validator_packet")
    if token_gloss and phrase_gloss and token_gloss != phrase_gloss:
        if row.get("adjacent_context_required") is not True:
            reasons.append("contextual_gloss_diff_without_context_gate")
            routes.append("governor_irab_fixture_needed")
        if not row.get("adjacent_context_locs"):
            reasons.append("contextual_gloss_diff_missing_adjacent_locs")
            routes.append("governor_irab_fixture_needed")

    if row.get("source_crosswalk_required") is True:
        reasons.append("source_crosswalk_required")
        routes.append("source_crosswalk_packet")

    routes = sorted(set(routes or ["qamus_executor_validation"]))
    return not reasons, sorted(set(reasons)), routes


def annotate(row: dict[str, Any], accepted: bool, reasons: list[str], routes: list[str], line_no: int) -> dict[str, Any]:
    out = dict(row)
    out["_e87_source_addressed_gate"] = {
        "analysis_status": "source_addressed_executor_candidate" if accepted else "candidate_held",
        "input_line": line_no,
        "reasons": reasons,
        "routes": routes,
        "safety_gate": "source_addressed_executor_validation" if accepted else "source_addressed_hold",
        "safe_for_public_hover": accepted,
        "safe_for_qamus_executor_autopromote": accepted,
    }
    out["analysis_status"] = out["_e87_source_addressed_gate"]["analysis_status"]
    out["safety_gate"] = out["_e87_source_addressed_gate"]["safety_gate"]
    out["safe_for_public_hover"] = accepted
    out["safe_for_qamus_executor_autopromote"] = accepted
    out["routes"] = routes
    return out


def gate_file(path: Path, accepted_out: Path | None = None, held_out: Path | None = None, report_out: Path | None = None) -> dict[str, Any]:
    accepted_rows: list[dict[str, Any]] = []
    held_rows: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    seen_locs: set[str] = set()
    rows = 0

    for line_no, row in iter_jsonl(path):
        rows += 1
        accepted, reasons, routes = validate_candidate(row, line_no, seen_locs)
        route_counts.update(routes)
        if accepted:
            accepted_rows.append(annotate(row, True, [], routes, line_no))
        else:
            reason_counts.update(reasons)
            held_rows.append(annotate(row, False, reasons, routes, line_no))

    write_jsonl(accepted_out, accepted_rows)
    write_jsonl(held_out, held_rows)
    report = {
        "accepted": len(accepted_rows),
        "accepted_sha256": None,
        "claim": "source-addressed RH-LIVE candidate gate; not arbitrary-text parser certification and not live Qamus progress",
        "fusha_gate": "e87-source-addressed-rh-live",
        "held": len(held_rows),
        "held_sha256": None,
        "input": str(path),
        "ok": len(held_rows) == 0,
        "reason_counts": dict(sorted(reason_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "rows": rows,
        "schema": "fusha/rh-live-source-addressed-candidate-gate@1",
    }
    write_report(report_out, report)
    report["accepted_sha256"] = file_sha256(accepted_out)
    report["held_sha256"] = file_sha256(held_out)
    if report_out:
        write_report(report_out, report)
    return report


def good_source_addressed_row() -> dict[str, Any]:
    return {
        "adjacent_context_locs": [],
        "adjacent_context_required": False,
        "card_ref": "2:1",
        "contextual_phrase_gloss": "with mercy",
        "entry_id": "entry-demo",
        "learner_explanation": "The bā' gives the relation \"with,\" and رَحْمَةٍ contributes \"mercy.\"",
        "loc": "2:1:1",
        "morphline": "bā' preposition + noun host",
        "no_root_reason": None,
        "parse_key": {"key": "P+N", "summary": "preposition plus governed noun"},
        "public_preview": {"kind": "authored", "lang": "en", "src": "qamus"},
        "quran_loc": "quran:2:1:1",
        "qword_index": 1,
        "root": "ر ح م",
        "schema": "rh_live_01_beta.v1",
        "segments": [
            {"class": "qg-preposition", "label": "P", "role": "prefix_preposition", "segment_index": 0, "surface": "بِ"},
            {"class": "qg-noun-stem", "label": "N", "role": "noun_stem", "segment_index": 1, "surface": "رَحْمَةٍ"},
        ],
        "source_key": "v-test",
        "surface": "بِرَحْمَةٍ",
        "terminal_state": "deploy_ready",
        "token_contribution_gloss": "with mercy",
        "wbw_loc": "wbw:2:1:1",
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="rh-live-source-gate-") as raw_tmp:
        tmp = Path(raw_tmp)
        good = good_source_addressed_row()
        good_path = tmp / "good.jsonl"
        good_path.write_text(json.dumps(good, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        report = gate_file(good_path, tmp / "good-accepted.jsonl", tmp / "good-held.jsonl", tmp / "good-report.json")
        if report["accepted"] != 1 or report["held"] != 0:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 1

        generic = dict(good)
        generic["segments"] = [{"class": "qg-segment", "label": "TOKEN", "role": "token", "segment_index": 0, "surface": "بِرَحْمَةٍ"}]
        generic["root"] = None
        generic["no_root_reason"] = "not_certified"
        generic_path = tmp / "generic.jsonl"
        generic_path.write_text(json.dumps(generic, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        report = gate_file(generic_path, tmp / "generic-accepted.jsonl", tmp / "generic-held.jsonl", tmp / "generic-report.json")
        if report["accepted"] != 0 or report["reason_counts"].get("generic_qg_segment_not_autopromote") != 1:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 1

        leak = dict(good)
        leak["learner_explanation"] = "The hover is authored from Qamus data and keeps internal evidence out of the public payload."
        leak_path = tmp / "leak.jsonl"
        leak_path.write_text(json.dumps(leak, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        report = gate_file(leak_path, tmp / "leak-accepted.jsonl", tmp / "leak-held.jsonl", tmp / "leak-report.json")
        if report["accepted"] != 0 or not any(key.startswith("public_boundary_leak:") for key in report["reason_counts"]):
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 1

        source_gap = dict(good)
        source_gap["wbw_loc"] = "wbw:2:1:2"
        source_gap_path = tmp / "source-gap.jsonl"
        source_gap_path.write_text(json.dumps(source_gap, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        report = gate_file(source_gap_path, tmp / "source-gap-accepted.jsonl", tmp / "source-gap-held.jsonl", tmp / "source-gap-report.json")
        if report["accepted"] != 0 or report["reason_counts"].get("wbw_loc_not_source_addressed") != 1:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
    print("PASS - source-addressed RH-LIVE candidate gate self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?")
    parser.add_argument("--accepted-out")
    parser.add_argument("--held-out")
    parser.add_argument("--report-out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.input:
        parser.error("provide an input JSONL path or --self-test")
    report = gate_file(
        Path(args.input),
        Path(args.accepted_out) if args.accepted_out else None,
        Path(args.held_out) if args.held_out else None,
        Path(args.report_out) if args.report_out else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
