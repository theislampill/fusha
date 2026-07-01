"""Validate qamustyping4 acceptance and claim gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fusha_mode_a import ALLOWED_QG_CLASSES, FORBIDDEN_PUBLIC_SUBSTRINGS, read_jsonl
from validate_qamustyping3_acceptance import validate_qamustyping3


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "qamus" / "reports" / "qamustyping4-implementation-ledger.json"
REGRESSION_WORKLIST = (
    ROOT / "qamus" / "examples" / "mode_a_all_qword" / "qamustyping4-regression-worklist.sample.jsonl"
)
VISUAL_FIXTURE = (
    ROOT / "qamus" / "examples" / "mode_a_all_qword" / "qamustyping4-visual-readback.fixture.jsonl"
)
EVAL_MATRIX = ROOT / "fusha" / "parser" / "eval" / "qamustyping4-eval-matrix.json"

REQUIRED_STAGES = {"P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"}
TERMINAL_STATES = {"done", "changed", "blocked", "deferred", "unverified"}
REQUIRED_FAMILIES = {"p011", "p014", "p016", "p018", "p050", "n0005", "n0100", "v033", "v100"}
REQUIRED_REGRESSION_CLASSES = {
    "verb_prefix_stem_subject_marker",
    "imperfect_prefix_governed_mood",
    "noun_not_verb_or_hidden_segment",
    "imperfect_prefix_plural_subject",
    "article_participle_prefix_plural_suffix",
    "vocalized_card_readback",
    "vocalized_function_token",
    "all_qword_not_selected_only",
    "proper_name_no_fake_root",
    "preposition_plus_host",
    "preposition_plus_pronoun",
    "particle_cluster_all_qword",
    "verb_attached_object_pronoun",
}


def _load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing JSON artifact: {path.relative_to(ROOT)}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return {}


def _public_text(obj: Any) -> str:
    if isinstance(obj, dict):
        return " ".join(_public_text(v) for k, v in obj.items() if k not in {"private_trace", "internal_evidence"})
    if isinstance(obj, list):
        return " ".join(_public_text(v) for v in obj)
    if isinstance(obj, str):
        return obj.lower()
    return ""


def _repo_path(path_value: str) -> Path:
    return ROOT / path_value


def _check_artifacts(label: str, paths: list[str], errors: list[str]) -> None:
    for raw_path in paths:
        if not _repo_path(raw_path).exists():
            errors.append(f"{label}: missing artifact path {raw_path}")


def _validate_regression_worklist(errors: list[str]) -> dict[str, Any]:
    rows = read_jsonl(REGRESSION_WORKLIST) if REGRESSION_WORKLIST.exists() else []
    if not rows:
        errors.append("qamustyping4 regression worklist is missing or empty")
        return {"rows": 0, "families": [], "regression_classes": []}

    row_ids: set[str] = set()
    families: set[str] = set()
    regression_classes: set[str] = set()
    statuses: set[str] = set()
    for row in rows:
        row_id = row.get("row_id")
        if not row_id:
            errors.append("regression row missing row_id")
            continue
        if row_id in row_ids:
            errors.append(f"duplicate regression row_id: {row_id}")
        row_ids.add(row_id)
        family = str(row.get("entry_key", ""))
        families.add(family)
        regression_classes.add(str(row.get("regression_family", "")))
        statuses.add(str(row.get("status", "")))
        for field in (
            "entry_key",
            "card_id",
            "qword_index",
            "canonical_loc",
            "visible_surface",
            "status",
            "regression_family",
            "qg_segments",
            "public_projection",
            "private_trace",
            "forward_trace_complete",
            "reverse_trace_complete",
            "expected_detector",
        ):
            if field not in row:
                errors.append(f"{row_id}: missing {field}")
        if not row.get("forward_trace_complete") or not row.get("reverse_trace_complete"):
            errors.append(f"{row_id}: forward/reverse trace must be complete in regression fixture")
        segments = row.get("qg_segments", [])
        segment_surface = "".join(seg.get("surface", "") for seg in segments if isinstance(seg, dict))
        if segment_surface != row.get("visible_surface"):
            errors.append(f"{row_id}: qg segment surfaces do not concatenate to visible_surface")
        bad_classes = {
            seg.get("qg_class")
            for seg in segments
            if isinstance(seg, dict) and seg.get("qg_class") not in ALLOWED_QG_CLASSES
        }
        if bad_classes:
            errors.append(f"{row_id}: unsupported qg classes {sorted(bad_classes)}")
        projection = row.get("public_projection", {})
        for key, value in {"src": "qamus", "kind": "authored", "lang": "en"}.items():
            if projection.get(key) != value:
                errors.append(f"{row_id}: public_projection.{key} must be {value!r}")
        text = _public_text(projection)
        for forbidden in FORBIDDEN_PUBLIC_SUBSTRINGS:
            if forbidden in text:
                errors.append(f"{row_id}: public projection leaks {forbidden!r}")

    missing_families = REQUIRED_FAMILIES - families
    if missing_families:
        errors.append(f"qamustyping4 regression worklist missing families: {sorted(missing_families)}")
    missing_classes = REQUIRED_REGRESSION_CLASSES - regression_classes
    if missing_classes:
        errors.append(f"qamustyping4 regression worklist missing classes: {sorted(missing_classes)}")
    if "review_packet" not in statuses:
        errors.append("qamustyping4 regression worklist must include at least one exact review_packet row")
    return {
        "rows": len(rows),
        "families": sorted(families),
        "regression_classes": sorted(regression_classes),
        "statuses": sorted(statuses),
    }


def _validate_visual_fixture(errors: list[str]) -> dict[str, Any]:
    rows = read_jsonl(VISUAL_FIXTURE) if VISUAL_FIXTURE.exists() else []
    if not rows:
        errors.append("qamustyping4 visual fixture is missing or empty")
        return {"rows": 0, "families": []}
    families = {str(row.get("entry_key", "")) for row in rows}
    for row in rows:
        fixture_id = row.get("fixture_id", "<missing>")
        if row.get("mode") != "fixture_only":
            errors.append(f"{fixture_id}: visual fixture mode must be fixture_only")
        if row.get("not_live_qamus") is not True:
            errors.append(f"{fixture_id}: visual fixture must mark not_live_qamus")
        if row.get("visible_qwords", 0) < row.get("rich_hover_qwords", 0):
            errors.append(f"{fixture_id}: rich_hover_qwords exceeds visible_qwords")
        if row.get("visible_qwords", 0) < row.get("colored_qwords", 0):
            errors.append(f"{fixture_id}: colored_qwords exceeds visible_qwords")
        if not row.get("regressions_caught"):
            errors.append(f"{fixture_id}: regressions_caught required")
    missing = REQUIRED_FAMILIES - families
    if missing:
        errors.append(f"visual fixture missing families: {sorted(missing)}")
    return {"rows": len(rows), "families": sorted(families)}


def validate_qamustyping4() -> dict[str, Any]:
    errors: list[str] = []
    q3 = validate_qamustyping3(ROOT)
    if q3.get("errors"):
        errors.extend(f"qamustyping3 baseline: {error}" for error in q3["errors"])

    ledger = _load_json(LEDGER_PATH, errors)
    if ledger.get("schema") != "fusha/qamustyping4-implementation-ledger@1":
        errors.append("qamustyping4 ledger schema mismatch")
    for field in ("generated_at", "generated_by", "source_head", "source_branch", "stale_after", "status"):
        if not ledger.get(field):
            errors.append(f"qamustyping4 ledger missing freshness field: {field}")
    claim = ledger.get("claim_boundary", {})
    if claim.get("is_full_classical_arabic_nlp_stack") is not False:
        errors.append("qamustyping4 must not claim full Classical Arabic NLP stack")
    if claim.get("not_live_qamus") is not True:
        errors.append("qamustyping4 must explicitly mark not_live_qamus")
    not_claimed = set(claim.get("not_claimed", []))
    for phrase in ("trained statistical disambiguator", "trained dependency parser", "general-purpose Classical Arabic Grammarly"):
        if phrase not in not_claimed:
            errors.append(f"claim boundary missing not_claimed phrase: {phrase}")

    stages = {row.get("stage"): row for row in ledger.get("stages", []) if isinstance(row, dict)}
    missing_stages = REQUIRED_STAGES - set(stages)
    if missing_stages:
        errors.append(f"qamustyping4 ledger missing stages: {sorted(missing_stages)}")
    for stage, row in stages.items():
        terminal = row.get("terminal_state")
        if terminal not in TERMINAL_STATES:
            errors.append(f"{stage}: terminal_state must be one of {sorted(TERMINAL_STATES)}, found {terminal!r}")
        if not row.get("status"):
            errors.append(f"{stage}: status required")
        if not row.get("validators"):
            errors.append(f"{stage}: validators required")
        _check_artifacts(stage, row.get("artifacts", []), errors)
        if terminal in {"blocked", "deferred"} and not row.get("blocked_by") and stage != "P5":
            errors.append(f"{stage}: blocked/deferred rows require blocked_by")

    for andon in ledger.get("andons", []):
        if andon.get("terminal_state") not in TERMINAL_STATES:
            errors.append(f"{andon.get('id')}: ANDON terminal_state invalid")
        if len(andon.get("five_whys", [])) < 5:
            errors.append(f"{andon.get('id')}: ANDON must include at least five whys")
        if not andon.get("next_concrete_action"):
            errors.append(f"{andon.get('id')}: ANDON missing next_concrete_action")

    worklist_summary = _validate_regression_worklist(errors)
    visual_summary = _validate_visual_fixture(errors)
    eval_matrix = _load_json(EVAL_MATRIX, errors)
    if eval_matrix.get("schema") != "fusha/qamustyping4-eval-matrix@1":
        errors.append("qamustyping4 eval matrix schema mismatch")
    if eval_matrix.get("live_qamus_progress_claimed") is not False:
        errors.append("qamustyping4 eval matrix must not claim live Qamus progress")
    if eval_matrix.get("aggregate_claim") != "no aggregate NLP-stack score":
        errors.append("qamustyping4 eval matrix must reject aggregate NLP-stack score")

    return {
        "ok": not errors,
        "errors": errors,
        "ledger": str(LEDGER_PATH.relative_to(ROOT)),
        "regression_worklist": worklist_summary,
        "visual_fixture": visual_summary,
        "eval_matrix_status": eval_matrix.get("status"),
        "claim_boundary": claim,
        "stage_terminal_states": {stage: row.get("terminal_state") for stage, row in sorted(stages.items())},
        "baseline_qamustyping3_ok": q3.get("ok"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate qamustyping4 acceptance gates.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = validate_qamustyping4()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
