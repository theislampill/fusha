"""Validate the P0.5 Qamus Mode A thin end-to-end slice."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fusha_mode_a import (
    ALLOWED_QG_CLASSES,
    FORBIDDEN_PUBLIC_SUBSTRINGS,
    PUBLIC_BOUNDARY,
    bundle_artifact_path,
    has_arabic_diacritic,
    load_bundle,
    read_jsonl,
    write_json,
)
from validate_artifact_freshness import validate_freshness


def _public_text(obj: Any) -> str:
    if isinstance(obj, dict):
        return " ".join(_public_text(v) for k, v in obj.items() if k != "private_trace")
    if isinstance(obj, list):
        return " ".join(_public_text(v) for v in obj)
    if isinstance(obj, str):
        return obj.lower()
    return ""


def _check_public_boundary(row: dict[str, Any], label: str, errors: list[str]) -> None:
    for key, value in PUBLIC_BOUNDARY.items():
        if row.get(key, row.get("public_boundary", {}).get(key)) != value:
            errors.append(f"{label}: public boundary {key} is not {value!r}")
    text = _public_text(row)
    for forbidden in FORBIDDEN_PUBLIC_SUBSTRINGS:
        if forbidden in text:
            errors.append(f"{label}: public field leaks {forbidden!r}")


def validate_bundle(bundle_path: Path) -> tuple[dict[str, Any], list[str]]:
    bundle = load_bundle(bundle_path)
    errors = validate_freshness(bundle, str(bundle_path))
    if bundle.get("schema") != "qamus/mode-a-thin-slice-bundle@1":
        errors.append("bundle schema must be qamus/mode-a-thin-slice-bundle@1")
    source_rows = read_jsonl(bundle_artifact_path(bundle, "source_rows"))
    analyses = read_jsonl(bundle_artifact_path(bundle, "analysis"))
    projections = read_jsonl(bundle_artifact_path(bundle, "public_hover_projection"))
    traces = read_jsonl(bundle_artifact_path(bundle, "private_trace"))
    edges = read_jsonl(bundle_artifact_path(bundle, "source_edge_manifest"))
    rendered = read_jsonl(bundle_artifact_path(bundle, "rendered_readback_fixture"))
    flywheel = read_jsonl(bundle_artifact_path(bundle, "flywheel_artifacts"))

    expected = len(source_rows)
    artifacts = {
        "analysis": analyses,
        "public_hover_projection": projections,
        "private_trace": traces,
        "source_edge_manifest": edges,
        "rendered_readback_fixture": rendered,
        "flywheel_artifacts": flywheel,
    }
    for name, rows in artifacts.items():
        if len(rows) != expected:
            errors.append(f"{name}: expected {expected} rows, found {len(rows)}")

    source_by_id = {row["row_id"]: row for row in source_rows}
    if len(source_by_id) != expected:
        errors.append("source rows have duplicate row_id values")

    card_counts: Counter[str] = Counter()
    card_expected: dict[str, int] = {}
    for row in source_rows:
        card_counts[row["card_id"]] += 1
        if row.get("card_expected_qword_count") is not None:
            card_expected[row["card_id"]] = row["card_expected_qword_count"]
        if row.get("vocalization_required") and not has_arabic_diacritic(row["displayed_surface"]):
            errors.append(f"{row['row_id']}: vocalization_required but displayed_surface lacks diacritics")
        if row.get("card_vocalization_required") and not has_arabic_diacritic(row["card_text"]):
            errors.append(f"{row['row_id']}: card_vocalization_required but card_text lacks diacritics")
    for card_id, count in card_counts.items():
        if card_expected.get(card_id) and card_expected[card_id] != count:
            errors.append(f"{card_id}: expected all-qword count {card_expected[card_id]}, found {count}")

    projections_by_id = {row["row_id"]: row for row in projections}
    analyses_by_id = {row["row_id"]: row for row in analyses}
    traces_by_id = {row["row_id"]: row for row in traces}
    edges_by_id = {row["row_id"]: row for row in edges}
    rendered_by_id = {row["row_id"]: row for row in rendered}
    flywheel_by_id = {row["row_id"]: row for row in flywheel}

    for row_id, source in source_by_id.items():
        missing = [
            name
            for name, rows in {
                "analysis": analyses_by_id,
                "public_hover_projection": projections_by_id,
                "private_trace": traces_by_id,
                "source_edge_manifest": edges_by_id,
                "rendered_readback_fixture": rendered_by_id,
                "flywheel_artifacts": flywheel_by_id,
            }.items()
            if row_id not in rows
        ]
        if missing:
            errors.append(f"{row_id}: missing artifacts {', '.join(missing)}")
            continue

        analysis = analyses_by_id[row_id]
        projection = projections_by_id[row_id]
        edge = edges_by_id[row_id]
        readback = rendered_by_id[row_id]
        fly = flywheel_by_id[row_id]

        if analysis.get("segment_surface") != source["displayed_surface"]:
            errors.append(f"{row_id}: analysis segments do not concatenate to surface")
        projected_surface = "".join(seg["surface"] for seg in projection.get("segments", []))
        if projected_surface != source["displayed_surface"]:
            errors.append(f"{row_id}: public projection segments do not concatenate to surface")
        bad_classes = set(projection.get("qg_classes", [])) - ALLOWED_QG_CLASSES
        if bad_classes:
            errors.append(f"{row_id}: unsupported qg classes {sorted(bad_classes)}")
        _check_public_boundary(projection, row_id, errors)
        if readback.get("text_content") != source["displayed_surface"]:
            errors.append(f"{row_id}: rendered fixture text mismatch")
        if not readback.get("hover_present"):
            errors.append(f"{row_id}: rendered fixture lacks hover")
        if not edge.get("forward_trace") or not edge.get("reverse_trace"):
            errors.append(f"{row_id}: missing forward/reverse trace")
        if edge.get("orphan_payload") or edge.get("orphan_rendered_span"):
            errors.append(f"{row_id}: orphan payload/rendered span")
        if not traces_by_id[row_id].get("decision_backlink"):
            errors.append(f"{row_id}: private trace missing decision backlink")
        if not fly.get("routes"):
            errors.append(f"{row_id}: flywheel artifact missing routes")

    case_families = defaultdict(int)
    for row in source_rows:
        case_families[row["smoke_case"]] += 1
    required_cases = bundle.get("required_smoke_cases", [])
    for case in required_cases:
        if case not in case_families:
            errors.append(f"required smoke case missing: {case}")

    summary = {
        "ok": not errors,
        "bundle": str(bundle_path),
        "source_rows": expected,
        "smoke_cases": dict(sorted(case_families.items())),
        "claim": "fixture-proven Mode A thin slice only; not live coverage and not arbitrary-text parser certification",
        "errors": errors,
    }
    return summary, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Qamus Mode A P0.5 adoption fixture.")
    parser.add_argument("--bundle", default="qamus/examples/mode_a_thin_slice/mode-a-bundle.json")
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    summary, errors = validate_bundle(Path(args.bundle))
    if args.out:
        write_json(Path(args.out), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
