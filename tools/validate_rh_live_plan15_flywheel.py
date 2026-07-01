"""Validate RH-LIVE Plan 15 parser flywheel artifacts.

These artifacts are Fusha flywheel queues, not live Qamus payloads and not
claims that the parser can certify arbitrary Classical Arabic text. The
validator checks the public-safe projection emitted by
``tools/import_rh_live_plan15_flywheel.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "qamus/flywheel-artifact@1"
DEFAULT_PATH = ROOT / "qamus" / "examples" / "rh_live_plan15_parser_flywheel.sample.jsonl"

ALLOWED_ROUTES = {
    "governor_irab_fixture_needed": {"parser", "nahw", "qamus_mode_a_validator"},
    "lexicon_entry_needed": {"parser", "sarf", "qamus_mode_a_validator"},
    "parser_interface_ok": {"parser", "qamus_mode_a_validator"},
    "particle_function_rule_needed": {"parser", "nahw", "qamus_mode_a_validator"},
    "pattern_rule_needed": {"parser", "sarf", "qamus_mode_a_validator"},
    "proper_name_no_root_needed": {"parser", "sarf", "qamus_mode_a_validator"},
}

ALLOWED_QG_CLASSES = {
    "qg-adjective",
    "qg-article",
    "qg-conditional",
    "qg-conjunction",
    "qg-demonstrative",
    "qg-derivative-prefix",
    "qg-dual-suffix",
    "qg-emphasis",
    "qg-exception",
    "qg-lam",
    "qg-ma-particle",
    "qg-negation",
    "qg-noun",
    "qg-noun-stem",
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
    "qg-verb-prefix",
    "qg-verb-stem",
}

CLAIM_BOUNDARY_FLAGS = {
    "arbitrary_text_parser_claim",
    "live_qamus_payload",
    "parser_oracle_claim",
}

FORBIDDEN_KEYS = {
    "entry_url",
    "public_url",
    "source_parser_ledger",
    "source_photo_path",
    "source_photo",
    "source_card_path",
}

PRIVATE_RE = re.compile(
    r"(?:[A-Za-z]:\\|/srv/|qamus\.dawah\.wiki|ssh|password|secret|api[_-]?key|bearer|BEGIN .*PRIVATE|"
    r"\binformed_by\b|\bmcp\b|\bqac\b|quran\.com|corpus\.quran|tanzil|tafsir|ocr|source[-_]photo)",
    re.IGNORECASE,
)

REQUIRED_FIELDS = {
    "schema",
    "row_id",
    "entry_id",
    "card_id",
    "routes",
    "reusable_lesson",
    "future_unlock",
    "flywheel_route",
    "loc",
    "surface",
    "parser_status",
    "claim_boundary",
}


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return ROOT / path


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


def validate_segment(row_id: str, index: int, segment: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(segment, dict):
        return [f"{row_id}: segments_found[{index}] must be an object"]
    cls = segment.get("class")
    if cls is not None:
        if not isinstance(cls, str) or not cls.startswith("qg-"):
            errors.append(f"{row_id}: segment class must be qg-*")
        elif cls not in ALLOWED_QG_CLASSES:
            errors.append(f"{row_id}: unsupported segment class {cls!r}")
    for key in ("surface", "role", "label"):
        if key in segment and segment[key] is not None and not isinstance(segment[key], str):
            errors.append(f"{row_id}: segments_found[{index}].{key} must be a string or null")
    return errors


def validate_row(row: dict[str, Any], path: Path, line_no: int) -> list[str]:
    row_id = str(row.get("row_id") or f"{path}:{line_no}")
    errors: list[str] = []
    if "__json_error__" in row:
        return [f"{path}:{line_no}: invalid JSONL: {row['__json_error__']}"]

    missing = sorted(field for field in REQUIRED_FIELDS if field not in row or row[field] in (None, "", []))
    for field in missing:
        errors.append(f"{row_id}: missing {field}")

    if row.get("schema") != SCHEMA:
        errors.append(f"{row_id}: schema must be {SCHEMA!r}")

    route = row.get("flywheel_route")
    if route not in ALLOWED_ROUTES:
        errors.append(f"{row_id}: unsupported flywheel_route {route!r}")
    else:
        routes = row.get("routes")
        if not isinstance(routes, list) or not all(isinstance(item, str) for item in routes):
            errors.append(f"{row_id}: routes must be an array of strings")
        elif not ALLOWED_ROUTES[route].issubset(set(routes)):
            expected = sorted(ALLOWED_ROUTES[route])
            errors.append(f"{row_id}: {route} routes must include {expected}")

    parser_status = row.get("parser_status")
    if parser_status not in {"known", "partial", "unknown"}:
        errors.append(f"{row_id}: parser_status must be known, partial, or unknown")

    claim_boundary = row.get("claim_boundary")
    if not isinstance(claim_boundary, dict):
        errors.append(f"{row_id}: claim_boundary must be an object")
    else:
        for flag in CLAIM_BOUNDARY_FLAGS:
            if claim_boundary.get(flag) is not False:
                errors.append(f"{row_id}: claim_boundary.{flag} must be false")

    for key in FORBIDDEN_KEYS:
        if key in row:
            errors.append(f"{row_id}: public flywheel artifact must not include {key}")

    qg_classes = row.get("qg_classes") or []
    if not isinstance(qg_classes, list) or not all(isinstance(item, str) for item in qg_classes):
        errors.append(f"{row_id}: qg_classes must be an array of strings")
    else:
        for cls in qg_classes:
            if not cls.startswith("qg-"):
                errors.append(f"{row_id}: qg class must start with qg-: {cls!r}")
            elif cls not in ALLOWED_QG_CLASSES:
                errors.append(f"{row_id}: unsupported qg class {cls!r}")

    segments_found = row.get("segments_found") or []
    if not isinstance(segments_found, list):
        errors.append(f"{row_id}: segments_found must be an array")
    else:
        for index, segment in enumerate(segments_found):
            errors.extend(validate_segment(row_id, index, segment))

    segments_needed = row.get("segments_needed") or []
    if not isinstance(segments_needed, list) or not all(isinstance(item, str) for item in segments_needed):
        errors.append(f"{row_id}: segments_needed must be an array of strings")

    text = json.dumps(row, ensure_ascii=False, sort_keys=True)
    if PRIVATE_RE.search(text):
        errors.append(f"{row_id}: public artifact leaks private path, source label, process label, or secret marker")

    return errors


def validate_jsonl(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    route_counts: Counter[str] = Counter()
    parser_status_counts: Counter[str] = Counter()
    rows = 0
    seen_row_ids: set[str] = set()

    if not path.exists():
        return {
            "path": str(path),
            "rows": 0,
            "ok": False,
            "errors": [f"missing file: {path}"],
        }

    for line_no, row in iter_jsonl(path):
        rows += 1
        if isinstance(row, dict):
            route_counts.update([str(row.get("flywheel_route"))])
            parser_status_counts.update([str(row.get("parser_status"))])
            row_id = row.get("row_id")
            if row_id in seen_row_ids:
                errors.append(f"{row_id}: duplicate row_id")
            if isinstance(row_id, str):
                seen_row_ids.add(row_id)
        else:
            row = {"__json_error__": "row must be an object"}
        errors.extend(validate_row(row, path, line_no))

    return {
        "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "rows": rows,
        "ok": not errors,
        "route_counts": dict(sorted(route_counts.items())),
        "parser_status_counts": dict(sorted(parser_status_counts.items())),
        "errors": errors,
    }


def self_test() -> int:
    good = {
        "schema": SCHEMA,
        "row_id": "plan15-self-test",
        "entry_id": "v001",
        "card_id": "v001-card-1-1:1",
        "routes": ["parser", "sarf", "qamus_mode_a_validator"],
        "reusable_lesson": "Parser partial output queues a lexicon entry.",
        "future_unlock": "populate reusable lexicon facts",
        "flywheel_route": "lexicon_entry_needed",
        "loc": "1:1:1",
        "surface": "الحمد",
        "parser_status": "partial",
        "root_null": True,
        "lemma_null": True,
        "segments_found": [{"surface": "ال", "role": "article", "class": "qg-article", "label": "ART"}],
        "segments_needed": ["root_or_no_root_reason"],
        "qg_classes": ["qg-article"],
        "claim_boundary": {
            "live_qamus_payload": False,
            "arbitrary_text_parser_claim": False,
            "parser_oracle_claim": False,
        },
    }
    with tempfile.TemporaryDirectory(prefix="plan15-flywheel-") as td:
        path = Path(td) / "good.jsonl"
        path.write_text(json.dumps(good, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        good_result = validate_jsonl(path)
        if not good_result["ok"]:
            print(json.dumps(good_result, ensure_ascii=False, indent=2, sort_keys=True))
            return 1

        bad = dict(good)
        bad["row_id"] = "plan15-bad"
        bad["claim_boundary"] = dict(good["claim_boundary"])
        bad["claim_boundary"]["parser_oracle_claim"] = True
        bad["reusable_lesson"] = "Generated from C:\\private\\source_photo.jpg"
        bad_path = Path(td) / "bad.jsonl"
        bad_path.write_text(json.dumps(bad, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        bad_result = validate_jsonl(bad_path)
        if bad_result["ok"] or len(bad_result["errors"]) < 2:
            print(json.dumps(bad_result, ensure_ascii=False, indent=2, sort_keys=True))
            return 1

    print("PASS - RH-LIVE Plan 15 flywheel validator self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=[str(DEFAULT_PATH)])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    results = [validate_jsonl(resolve_path(raw)) for raw in args.paths]
    errors = [error for result in results for error in result.get("errors", [])]
    print(
        json.dumps(
            {
                "ok": not errors,
                "checked": len(results),
                "rows": sum(result.get("rows", 0) for result in results),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
