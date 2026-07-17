"""Validate the committed FD2 455-row rerun artifacts.

This validator is intentionally fixture-only.  It proves that the checked-in
report and row matrix agree with one another, that generated learner text is
fact-derived and N-LANG-clean, and that no live mutation or external path has
leaked into the artifacts.  It does not rerun the external corpus.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools import fact_ledger
from tools import fd_compiler


REPORT_PATH = _ROOT / "fd2-455-report.json"
VERDICTS_PATH = _ROOT / "fd2-455-verdicts.jsonl"
META_PATH = _ROOT / "fd2-455-verdicts.meta.json"
REPORT_SCHEMA_PATH = _ROOT / "qamus" / "schemas" / "fd2-455-report.schema.json"
_ABSOLUTE_PATH_RE = re.compile(r"(?:^[A-Za-z]:[\\/]|^\\\\|file://)")
_FORBIDDEN_LEARNER_TERMS = (
    "source-addressed",
    "calibration",
    "producer",
    "evidence",
    "candidate",
    "live mutation",
    "informed_by",
    "quran:",
    "wbw:",
)
_SARF_LABEL = "Ṣarf — how this piece forms the word"
_NAHW_LABEL = "Naḥw — what this piece does here"


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {path}:{line_no}")
        rows.append(value)
    return rows


def _schema_errors(value: Any, path: Path) -> list[str]:
    errors: list[str] = []
    schema = _load(path)
    fact_ledger._validate_node(value, schema, "$", errors, schema)
    return errors


def _recursive_live_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        if "live_mutation_allowed" in value and value["live_mutation_allowed"] is not False:
            errors.append(f"{path}.live_mutation_allowed must be false")
        for key, child in value.items():
            errors.extend(_recursive_live_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_recursive_live_errors(child, f"{path}[{index}]"))
    return errors


def _absolute_path_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(_absolute_path_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_absolute_path_errors(child, f"{path}[{index}]"))
    elif isinstance(value, str) and _ABSOLUTE_PATH_RE.search(value):
        errors.append(f"{path} embeds an absolute/external file path")
    return errors


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _expected_metrics(verdicts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    blockers = Counter(
        blocker
        for row in verdicts
        for blocker in row.get("blockers", [])
        if isinstance(blocker, str)
    )
    source = sum(bool(row.get("source_queue")) for row in verdicts)
    scholar = sum(bool(row.get("scholar_queue")) for row in verdicts)
    routes = Counter(str(row.get("review_route", "")) for row in verdicts)
    defects = [
        item
        for row in verdicts
        for item in row.get("producer_defects", [])
        if isinstance(item, dict)
    ]
    return {
        fd_compiler.FD2_METRIC_KEYS[0]: sum(bool(row.get("fact_completeness", {}).get("morphology")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[1]: sum(bool(row.get("fact_completeness", {}).get("nahw")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[2]: sum(bool(row.get("fact_completeness", {}).get("both")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[3]: sum(bool(row.get("at_rest_projection", {}).get("generated")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[4]: sum(bool(row.get("views", {}).get("rich_sarf")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[5]: sum(bool(row.get("views", {}).get("rich_nahw")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[6]: sum(bool(row.get("views", {}).get("both_compact_and_expanded")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[7]: sum(bool(row.get("repeated_appearance_parity", {}).get("covered")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[8]: dict(sorted(blockers.items())),
        fd_compiler.FD2_METRIC_KEYS[9]: {
            "source": source,
            "scholar": scholar,
            "both": sum(bool(row.get("source_queue")) and bool(row.get("scholar_queue")) for row in verdicts),
            "routes": dict(sorted(routes.items())),
        },
        fd_compiler.FD2_METRIC_KEYS[10]: sum(bool(row.get("reconstruction_failed")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[11]: sum(bool(row.get("projection_conflicts")) for row in verdicts),
        fd_compiler.FD2_METRIC_KEYS[12]: {
            "count": len(defects),
            "items": sorted(defects, key=_canonical),
        },
    }


def _validate_learner_row(row: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    learner = row.get("learner_language") or {}
    views = row.get("views") or {}
    generated = learner.get("generated_from_facts") is True
    if generated:
        if learner.get("n_lang_clean") is not True:
            errors.append(f"verdict {index} generated learner language is not N-LANG-clean")
        if views.get("both_compact_and_expanded") is True:
            compact = views.get("compact") or {}
            expanded = views.get("expanded") or {}
            if compact.get("payload_id") != expanded.get("payload_id"):
                errors.append(f"verdict {index} compact/expanded payload identity diverges")
            if compact.get("payload_id") != views.get("payload_id"):
                errors.append(f"verdict {index} view payload identity diverges from row payload")
        if views.get("rich_sarf") and _SARF_LABEL not in str(learner.get("sarf", "")):
            errors.append(f"verdict {index} rich Ṣarf view lacks the exact learner label")
        if views.get("rich_nahw") and _NAHW_LABEL not in str(learner.get("nahw", "")):
            errors.append(f"verdict {index} rich Naḥw view lacks the exact learner label")
        learner_text = " ".join(
            str(learner.get(key, ""))
            for key in ("component_gloss", "sarf", "nahw", "composition", "learner_explanation")
        ).lower()
        for term in _FORBIDDEN_LEARNER_TERMS:
            if term in learner_text:
                errors.append(f"verdict {index} learner text contains forbidden process term {term!r}")
        if any("\u0600" <= char <= "\u08ff" for char in learner_text):
            errors.append(f"verdict {index} generated learner text contains Arabic source prose")
    elif any(views.get(key) for key in ("rich_sarf", "rich_nahw", "both_compact_and_expanded")):
        errors.append(f"verdict {index} claims a rich/generated view without fact generation")
    if learner.get("generated_from_facts") and learner.get("complete") is not True:
        errors.append(f"verdict {index} fact generation did not yield a complete learner payload")
    return errors


def _validate_scope_row(row: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    family = row.get("morphology_family")
    fb_status = (row.get("producer_status") or {}).get("F-B")
    if fb_status not in {"not_applicable", None} and family != "clitic_pronoun_compositions":
        errors.append(f"verdict {index} applies F-B outside its calibrated family")
    if fb_status == "candidate" and row.get("fact_completeness", {}).get("morphology") is not True:
        errors.append(f"verdict {index} positive F-B row lacks complete morphology")
    fc_status = (row.get("producer_status") or {}).get("F-C")
    if fc_status == "candidate" and row.get("fact_completeness", {}).get("nahw") is not True:
        errors.append(f"verdict {index} positive F-C row lacks complete naḥw")
    if row.get("compile_mode") != "candidate" or row.get("live_mutation_allowed") is not False:
        errors.append(f"verdict {index} is outside candidate/no-live scope")
    return errors


def validate_fd2_artifacts(
    report: dict[str, Any],
    verdicts: Sequence[dict[str, Any]],
    meta: dict[str, Any],
) -> list[str]:
    """Return deterministic validation errors for one FD2 artifact set."""

    errors: list[str] = []
    if REPORT_SCHEMA_PATH.is_file():
        errors.extend(_schema_errors(report, REPORT_SCHEMA_PATH))
    errors.extend(_recursive_live_errors(report))
    errors.extend(_recursive_live_errors(list(verdicts)))
    errors.extend(_recursive_live_errors(meta))
    errors.extend(_absolute_path_errors(report))
    errors.extend(_absolute_path_errors(list(verdicts)))
    errors.extend(_absolute_path_errors(meta))
    if report.get("schema") != fd_compiler.FD2_REPORT_SCHEMA:
        errors.append("report schema identifier drifted")
    if report.get("candidate_only") is not True or report.get("live_mutation_allowed") is not False:
        errors.append("report is not candidate-only with live mutation disabled")
    if report.get("input_verdict_count") != 575:
        errors.append("FD2 report must bind to the 575-row v575 verdict input")
    if report.get("verified_row_count") != 455 or len(verdicts) != 455:
        errors.append(f"FD2 row count is report={report.get('verified_row_count')} verdicts={len(verdicts)}, expected 455")
    locations = [row.get("loc") for row in verdicts]
    if len(set(locations)) != len(locations):
        errors.append("FD2 verdict locations are not unique")
    for index, row in enumerate(verdicts):
        if row.get("schema") != fd_compiler.FD2_VERDICT_SCHEMA:
            errors.append(f"verdict {index} schema identifier drifted")
        if row.get("source_verdict") != "verified":
            errors.append(f"verdict {index} is not sourced from a verified row")
        if row.get("compile_mode") != "candidate":
            errors.append(f"verdict {index} is not candidate mode")
        errors.extend(_validate_scope_row(row, index))
        errors.extend(_validate_learner_row(row, index))
        if row.get("repeated_appearance_parity", {}).get("covered") and not row.get("repeated_appearance_parity", {}).get("same_payload_id"):
            errors.append(f"verdict {index} parity lacks same-payload identity")
    if len(verdicts) == 455:
        expected_metrics = _expected_metrics(verdicts)
        if report.get("metrics") != expected_metrics:
            errors.append("FD2 report metrics do not recompute from the per-row matrix")
        expected_after = {
            "rows needing F-B": len(verdicts) - expected_metrics[fd_compiler.FD2_METRIC_KEYS[0]],
            "rows needing F-C": len(verdicts) - expected_metrics[fd_compiler.FD2_METRIC_KEYS[1]],
            "rows lacking learner-language": len(verdicts) - sum(bool(row.get("learner_language", {}).get("complete")) for row in verdicts),
            "rows with repeated-appearance coverage": expected_metrics[fd_compiler.FD2_METRIC_KEYS[7]],
        }
        movement = report.get("movement") or {}
        if movement.get("before") != fd_compiler.FD2_BASELINE:
            errors.append("FD2 movement baseline drifted")
        if movement.get("after") != expected_after:
            errors.append("FD2 movement after-values do not recompute")
        if movement.get("delta") != {key: expected_after[key] - fd_compiler.FD2_BASELINE[key] for key in fd_compiler.FD2_BASELINE}:
            errors.append("FD2 movement deltas do not recompute")
        primary = Counter(str(row.get("primary_blocker", "")) for row in verdicts)
        if report.get("primary_blocker_counts") != dict(sorted(primary.items())):
            errors.append("FD2 primary blocker counts do not recompute")
    if meta.get("artifact") != "fd2-455-verdicts.jsonl" or meta.get("count") != len(verdicts):
        errors.append("FD2 verdict metadata does not bind to the emitted row artifact")
    if meta.get("candidate_only") is not True or meta.get("live_mutation_allowed") is not False:
        errors.append("FD2 verdict metadata is not candidate-only with live mutation disabled")
    return errors


def validate_files(
    report_path: Path = REPORT_PATH,
    verdicts_path: Path = VERDICTS_PATH,
    meta_path: Path = META_PATH,
) -> list[str]:
    return validate_fd2_artifacts(
        _load(report_path),
        _load_jsonl(verdicts_path),
        _load(meta_path),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--verdicts", type=Path, default=VERDICTS_PATH)
    parser.add_argument("--meta", type=Path, default=META_PATH)
    args = parser.parse_args(argv)
    try:
        errors = validate_files(args.report, args.verdicts, args.meta)
    except Exception as exc:  # pragma: no cover - operational fixture failures
        print("FD2 RERUN SELF-TEST FAIL")
        print(f"- validator exception: {exc}")
        return 1
    if errors:
        print("FD2 RERUN SELF-TEST FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("FD2 RERUN SELF-TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
