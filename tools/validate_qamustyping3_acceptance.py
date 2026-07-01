"""Validate qamustyping3 repo-side acceptance gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fusha_mode_a import ALLOWED_QG_CLASSES, FORBIDDEN_PUBLIC_SUBSTRINGS, read_jsonl
from validate_qamus_mode_a_adoption import validate_bundle


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "qamus" / "reports" / "qamustyping3-implementation-ledger.json"
SOURCE_LEDGER_PATH = ROOT / "sources" / "source-artifact-ledger.json"
THIN_SLICE_BUNDLE = ROOT / "qamus" / "examples" / "mode_a_thin_slice" / "mode-a-bundle.json"
ALL_QWORD_WORKLIST = (
    ROOT / "qamus" / "examples" / "mode_a_all_qword" / "qamustyping3-all-qword-worklist.sample.jsonl"
)
VISUAL_READBACK = (
    ROOT / "qamus" / "examples" / "mode_a_all_qword" / "qamustyping3-visual-readback.fixture.jsonl"
)
EVAL_MATRIX = ROOT / "fusha" / "parser" / "eval" / "qamustyping3-eval-matrix.json"

REQUIRED_STAGES = {"P0", "P0.5", "P1", "P2", "P3", "P4"}
REQUIRED_EXTERNAL_SOURCES = {
    "camel_morph_msa",
    "camel_tools",
    "camelparser2",
    "madamira",
    "qac",
    "quran_foundation_api",
    "quran_wbw",
    "stanza",
    "tafsir_mcp",
    "tanzil",
    "ud_arabic_nyuad",
    "ud_arabic_padt",
}
REQUIRED_CAPABILITIES = {
    "source_artifact_ledger",
    "local_cli_contract",
    "mode_a_thin_slice",
    "morphology_database",
    "morphology_generator",
    "statistical_disambiguator",
    "dependency_parser",
    "qamus_all_qword_mode_a",
    "arbitrary_text_checker",
}
REQUIRED_ALL_QWORD_FAMILIES = {
    "n0005",
    "v100",
    "p011",
    "p018",
    "p050",
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


def _relative(path: str) -> Path:
    return ROOT / path


def _check_artifact_paths(paths: list[str], label: str, errors: list[str]) -> None:
    for raw_path in paths:
        path = _relative(raw_path)
        if not path.exists():
            errors.append(f"{label}: artifact path missing: {raw_path}")


def _public_text(obj: Any) -> str:
    if isinstance(obj, dict):
        return " ".join(_public_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_public_text(v) for v in obj)
    if isinstance(obj, str):
        return obj.lower()
    return ""


def _validate_source_ledger(errors: list[str]) -> tuple[dict[str, Any], set[str]]:
    ledger = _load_json(SOURCE_LEDGER_PATH, errors)
    if not ledger:
        return {}, set()
    if ledger.get("schema") != "fusha/source-artifact-ledger@1":
        errors.append("source ledger schema must be fusha/source-artifact-ledger@1")
    for field in ("generated_at", "generated_by", "source_head", "source_branch", "stale_after", "status"):
        if not ledger.get(field):
            errors.append(f"source ledger missing freshness field: {field}")
    external_sources = {
        row.get("source_id")
        for row in ledger.get("external_sources", [])
        if isinstance(row, dict) and row.get("source_id")
    }
    missing_sources = REQUIRED_EXTERNAL_SOURCES - external_sources
    if missing_sources:
        errors.append(f"source ledger missing external source ids: {sorted(missing_sources)}")
    for row in ledger.get("external_sources", []):
        if row.get("public_provenance_allowed") is not False:
            errors.append(f"external source must be internal-only: {row.get('source_id')}")
    for artifact in ledger.get("artifacts", []):
        path = artifact.get("path")
        if path and not _relative(path).exists():
            errors.append(f"source ledger artifact path missing: {path}")
    return ledger, external_sources


def _validate_all_qword_fixture(errors: list[str]) -> dict[str, Any]:
    rows = read_jsonl(ALL_QWORD_WORKLIST) if ALL_QWORD_WORKLIST.exists() else []
    visual_rows = read_jsonl(VISUAL_READBACK) if VISUAL_READBACK.exists() else []
    if not rows:
        errors.append("all-qword fixture worklist is missing or empty")
    if not visual_rows:
        errors.append("visual readback fixture is missing or empty")
    families = {str(row.get("entry_key", "")) for row in rows}
    missing_families = REQUIRED_ALL_QWORD_FAMILIES - families
    if missing_families:
        errors.append(f"all-qword fixture missing entry families: {sorted(missing_families)}")
    seen_ids: set[str] = set()
    for row in rows:
        row_id = row.get("row_id")
        if not row_id:
            errors.append("all-qword row missing row_id")
        elif row_id in seen_ids:
            errors.append(f"duplicate all-qword row_id: {row_id}")
        seen_ids.add(row_id)
        for field in (
            "entry_key",
            "card_id",
            "qword_index",
            "canonical_loc",
            "visible_surface",
            "status",
            "qg_segments",
            "public_projection",
            "private_trace",
        ):
            if field not in row:
                errors.append(f"{row_id}: missing {field}")
        if not row.get("forward_trace_complete") or not row.get("reverse_trace_complete"):
            errors.append(f"{row_id}: missing forward/reverse trace")
        segments = row.get("qg_segments", [])
        segment_surface = "".join(seg.get("surface", "") for seg in segments if isinstance(seg, dict))
        if segment_surface != row.get("visible_surface"):
            errors.append(f"{row_id}: qg segment surfaces do not concatenate to visible surface")
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
                errors.append(f"{row_id}: public projection {key} must be {value!r}")
        text = _public_text(projection)
        for forbidden in FORBIDDEN_PUBLIC_SUBSTRINGS:
            if forbidden in text:
                errors.append(f"{row_id}: public projection leaks {forbidden!r}")
    for visual in visual_rows:
        if visual.get("mode") != "fixture_only":
            errors.append(f"{visual.get('fixture_id')}: visual readback mode must be fixture_only")
        if visual.get("not_live_qamus") is not True:
            errors.append(f"{visual.get('fixture_id')}: visual fixture must mark not_live_qamus")
    return {
        "rows": len(rows),
        "visual_rows": len(visual_rows),
        "families": sorted(families),
    }


def validate_qamustyping3(root: Path = ROOT) -> dict[str, Any]:
    if root != ROOT:
        # The implementation is intentionally repo-relative; tests pass ROOT.
        pass
    errors: list[str] = []
    ledger = _load_json(LEDGER_PATH, errors)
    source_ledger, source_ids = _validate_source_ledger(errors)
    thin_slice_summary, thin_slice_errors = validate_bundle(THIN_SLICE_BUNDLE)
    errors.extend(f"thin slice: {error}" for error in thin_slice_errors)
    all_qword_summary = _validate_all_qword_fixture(errors)
    eval_matrix = _load_json(EVAL_MATRIX, errors)

    if ledger.get("schema") != "fusha/qamustyping3-implementation-ledger@1":
        errors.append("qamustyping3 ledger schema must be fusha/qamustyping3-implementation-ledger@1")
    for field in ("generated_at", "generated_by", "source_head", "source_branch", "stale_after", "status"):
        if not ledger.get(field):
            errors.append(f"qamustyping3 ledger missing freshness field: {field}")

    claim_boundary = ledger.get("claim_boundary", {})
    if claim_boundary.get("is_full_classical_arabic_nlp_stack") is not False:
        errors.append("claim boundary must not mark this as a full Classical Arabic NLP stack")
    if claim_boundary.get("not_live_qamus") is not True or claim_boundary.get("not_arbitrary_text") is not True:
        errors.append("claim boundary must explicitly mark not_live_qamus and not_arbitrary_text")

    stages = {
        row.get("stage"): row
        for row in ledger.get("stages", [])
        if isinstance(row, dict) and row.get("stage")
    }
    missing_stages = REQUIRED_STAGES - set(stages)
    if missing_stages:
        errors.append(f"missing qamustyping3 stages: {sorted(missing_stages)}")
    for stage, row in stages.items():
        if stage in REQUIRED_STAGES:
            status = str(row.get("status", ""))
            if not status.startswith("implemented"):
                errors.append(f"{stage}: status must be implemented*, found {status!r}")
            _check_artifact_paths(row.get("artifacts", []), stage, errors)
            if not row.get("validators"):
                errors.append(f"{stage}: validators required")

    capabilities = ledger.get("capabilities", {})
    missing_capabilities = REQUIRED_CAPABILITIES - set(capabilities)
    if missing_capabilities:
        errors.append(f"missing capabilities: {sorted(missing_capabilities)}")
    for name, capability in capabilities.items():
        _check_artifact_paths(capability.get("artifacts", []), f"capability {name}", errors)

    ledger_source_ids = set(ledger.get("external_sources", []))
    if REQUIRED_EXTERNAL_SOURCES - ledger_source_ids:
        errors.append(
            "qamustyping3 ledger missing external source ids: "
            f"{sorted(REQUIRED_EXTERNAL_SOURCES - ledger_source_ids)}"
        )
    if REQUIRED_EXTERNAL_SOURCES - source_ids:
        errors.append(
            "canonical source ledger missing external source ids: "
            f"{sorted(REQUIRED_EXTERNAL_SOURCES - source_ids)}"
        )
    if source_ledger.get("external_source_policy", {}).get("public_payload_rule") is None:
        errors.append("source ledger missing public_payload_rule")

    if eval_matrix.get("schema") != "fusha/qamustyping3-eval-matrix@1":
        errors.append("qamustyping3 eval matrix schema mismatch")
    if eval_matrix.get("claim_boundary", "").lower().find("not arbitrary-text") == -1:
        errors.append("eval matrix must carry not arbitrary-text claim boundary")

    result = {
        "ok": not errors,
        "errors": errors,
        "ledger": str(LEDGER_PATH.relative_to(ROOT)),
        "source_ledger": str(SOURCE_LEDGER_PATH.relative_to(ROOT)),
        "claim_boundary": claim_boundary,
        "stages": stages,
        "capabilities": capabilities,
        "external_sources": sorted(ledger_source_ids),
        "thin_slice": thin_slice_summary,
        "all_qword_fixture": all_qword_summary,
        "eval_matrix_status": eval_matrix.get("status"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate qamustyping3 acceptance gates.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = validate_qamustyping3(ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
