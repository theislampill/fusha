#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the backfillfull sarf/nahw largelexicon transclusion surfaces.

This gate is intentionally stricter than the older broad marker checks. It
proves that Plan 15 route families, qword denominator/crosswalk/source-card
boundaries, packet-vs-hover visibility, qg class canonicalization, and
bidirectional transclusion are discoverable from the skill, procedure,
curriculum, executor, and closeout surfaces.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


REQUIRED_PATHS = {
    "sarf/SKILL.md": [
        "largelexicon / plan 15 routing",
        "qword denominator",
        "source-card repair",
        "source-crosswalk",
        "packet-only",
        "learner-visible",
        "lexicon_entry_needed",
        "stem_entry_needed",
        "pattern_rule_needed",
        "proper_name_no_root_needed",
    ],
    "nahw/SKILL.md": [
        "largelexicon / plan 15 routing",
        "qword denominator",
        "source-card repair",
        "source-crosswalk",
        "packet-only",
        "learner-visible",
        "governor_irab_fixture_needed",
        "particle_function_rule_needed",
        "أَمْ",
        "لَهُمْ",
        "وَمَا",
    ],
    "sarf/README.md": [
        "Plan 15",
        "qword denominator",
        "source-crosswalk",
        "source-card repair",
    ],
    "nahw/README.md": [
        "Plan 15",
        "qword denominator",
        "source-crosswalk",
        "source-card repair",
    ],
    "sarf/procedures/largelexicon-morphology-expansion.md": [
        "Pre-sarf source gates",
        "Plan 15 sarf route families",
        "packet-only",
        "source-crosswalk",
    ],
    "nahw/procedures/largelexicon-function-token-routing.md": [
        "Source identity before function certification",
        "Plan 15 nahw route families",
        "packet-only",
        "source-crosswalk",
    ],
    "sarf/procedures/plan15-sarf-route-families.md": [
        "lexicon_entry_needed",
        "stem_entry_needed",
        "pattern_rule_needed",
        "proper_name_no_root_needed",
    ],
    "sarf/procedures/qword-crosswalk-before-morphology.md": [
        "source_crosswalk_packet_ready",
        "accepted crosswalk",
        "morphology can be true but not deployable",
    ],
    "nahw/procedures/plan15-nahw-route-families.md": [
        "governor_irab_fixture_needed",
        "particle_function_rule_needed",
        "scholar_irab_packet",
    ],
    "curriculum/drills/plan15-route-families.md": [
        "parser_interface_ok",
        "lexicon_entry_needed",
        "stem_entry_needed",
        "pattern_rule_needed",
        "proper_name_no_root_needed",
        "governor_irab_fixture_needed",
        "particle_function_rule_needed",
    ],
    "curriculum/drills/qword-denominator-and-crosswalk.md": [
        "denominator_only",
        "source_crosswalk_packet",
        "accepted_crosswalk_hover_candidate",
    ],
    "curriculum/drills/source-card-repair-and-transclusion.md": [
        "source-card repair",
        "downstream artifacts",
        "transclusion",
    ],
    "curriculum/drills/packet-vs-hover-projection.md": [
        "packet-only",
        "learner_visible=false",
        "learner_visible=true",
    ],
    "curriculum/drills/transclusion-hover-capstone.md": [
        "forward trace",
        "reverse trace",
        "public/private projection",
    ],
    "curriculum/tutor-runtime-routing.md": [
        "teach_plan15_route_family",
        "teach_qword_denominator",
        "teach_source_crosswalk",
        "teach_packet_vs_hover",
        "teach_transclusion_trace",
    ],
    "qamus/procedures/largelexicon-rollout-consumption.md": [
        "largelexicon_table_reader.py",
        "source_crosswalk_packet_ready",
        "accepted crosswalk",
        "forward trace",
        "reverse trace",
    ],
    "qamus/procedures/source-card-repair-decision-application.md": [
        "accepted_exact",
        "accepted_with_crosswalk",
        "downstream_invalidates",
    ],
    "qamus/schemas/source-card-example-repair-decision.schema.json": [
        "decision_status",
        "downstream_invalidates",
        "public_boundary",
    ],
}

CANONICAL_QG_SURFACE = "docs/parser/qamus-grammar-v1-class-map.md"
QG_MARKERS = ["qg-negation", "qg-negative", "alias", "canonical"]


def validate(required_paths: dict[str, list[str]] | None = None) -> list[str]:
    errors: list[str] = []
    for rel, markers in (required_paths or REQUIRED_PATHS).items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing required backfill surface: {rel}")
            continue
        text = _read(rel)
        lowered = text.lower()
        for marker in markers:
            if marker.lower() not in lowered:
                errors.append(f"{rel}: missing marker {marker!r}")

    qg_path = ROOT / CANONICAL_QG_SURFACE
    if not qg_path.exists():
        errors.append(f"missing qg canonical class surface: {CANONICAL_QG_SURFACE}")
    else:
        qg_text = qg_path.read_text(encoding="utf-8").lower()
        for marker in QG_MARKERS:
            if marker.lower() not in qg_text:
                errors.append(f"{CANONICAL_QG_SURFACE}: missing marker {marker!r}")

    public_risk_text = "\n".join(_read(rel) for rel in (required_paths or REQUIRED_PATHS))
    for leak in ("qac says", "mcp says", "/srv/", "c:\\", "source photo path"):
        if leak in public_risk_text.lower():
            errors.append(f"public/private boundary risk marker present: {leak!r}")
    return errors


def self_test() -> int:
    failures: list[str] = []
    real_errors = validate()
    if real_errors:
        failures.append(f"real tree should pass after backfill, got {len(real_errors)} error(s): {real_errors[:5]}")

    broken = {
        "sarf/SKILL.md": ["largelexicon / plan 15 routing", "stem_entry_needed"],
    }
    # This deliberately references the real file but asks for an impossible marker.
    broken["sarf/SKILL.md"].append("__definitely_missing_marker__")
    broken_errors = validate(broken)
    if not any("__definitely_missing_marker__" in e for e in broken_errors):
        failures.append("self-test should catch a missing marker")

    for failure in failures:
        print("FAIL " + failure)
    if not failures:
        print("ok   backfillfull sarf/nahw largelexicon gate: skills, procedures, drills, qg map, source-card/crosswalk/transclusion surfaces are discoverable")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate backfillfull sarf/nahw largelexicon surfaces.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
