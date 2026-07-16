#!/usr/bin/env python3
"""Validate the qg reconciliation/collision artifacts and prove the gate red-first."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from qg_registry import (
    DEFAULT_CSS_PATH,
    LEGACY_ALIASES,
    MATRIX_PATH,
    OWNER_NAMED_PAIRS,
    REGISTRY_PATH,
    SCHEMA_PATH,
    build_collision_matrix,
    build_registry,
    delta_e_76,
    read_schema,
)


REQUIRED_ENTRY_FIELDS = {
    "class_id", "semantic_class_id", "canonical_class_id", "legacy_aliases", "schema_membership",
    "public_internal_status", "renderer_token", "typed_applicability", "exclusions", "colour",
    "non_colour_fallback",
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "registry_version", "generated_by", "source_inputs", "inventory", "theme_inputs", "classes", "accessibility_floor",
}
REQUIRED_COLOUR_FIELDS = {"css_value", "resolved_rgb", "rgb", "opacity"}
VALID_CLASS_STATUSES = {
    "public-canonical", "internal-canonical", "status-only", "legacy-alias", "live-generic-fallback", "canonical-uninstantiated",
}
VALID_PAIR_CLASSIFICATIONS = {"exact-RGB", "near", "acceptable-distinct"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_registry() -> dict:
    return build_registry(DEFAULT_CSS_PATH.read_text(encoding="utf-8"), read_schema())


def validate_registry(registry: dict, css_text: str | None = None, schema: dict | None = None) -> list[str]:
    errors = []
    if not isinstance(registry, dict):
        return ["registry must be an object"]
    source_registry = _source_registry() if css_text is None or schema is None else build_registry(css_text, schema)
    expected_live = set(source_registry["inventory"]["live_css_class_ids"])
    expected_schema = set(source_registry["inventory"]["schema_enum_ids"])
    rows = registry.get("classes")
    missing_top = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(registry))
    errors.extend(f"registry missing top-level field: {field}" for field in missing_top)
    if not isinstance(rows, list):
        return errors + ["registry classes must be a list"]
    ids = [row.get("class_id") for row in rows if isinstance(row, dict)]
    duplicates = sorted({class_id for class_id in ids if ids.count(class_id) > 1})
    errors.extend(f"duplicate registry class id: {class_id}" for class_id in duplicates)
    row_by_id = {row.get("class_id"): row for row in rows if isinstance(row, dict)}
    expected_ids = expected_live | expected_schema
    errors.extend(f"live/schema class missing from reconciliation table: {class_id}" for class_id in sorted(expected_ids - set(row_by_id)))
    errors.extend(f"reconciliation row is not sourced by live CSS or schema enum: {class_id}" for class_id in sorted(set(row_by_id) - expected_ids))
    for class_id, row in sorted(row_by_id.items()):
        missing = sorted(REQUIRED_ENTRY_FIELDS - set(row))
        errors.extend(f"{class_id}: missing required entry field: {field}" for field in missing)
        if missing:
            continue
        status = row["public_internal_status"]
        if status not in VALID_CLASS_STATUSES:
            errors.append(f"{class_id}: invalid public_internal_status {status!r}")
        if not isinstance(row["legacy_aliases"], list):
            errors.append(f"{class_id}: legacy_aliases must be a list")
        if not isinstance(row["typed_applicability"], dict) or not row["typed_applicability"].get("typed_fields"):
            errors.append(f"{class_id}: typed_applicability must carry typed_fields")
        if not isinstance(row["exclusions"], list) or not row["exclusions"]:
            errors.append(f"{class_id}: exclusions must be a nonempty list")
        if not isinstance(row["non_colour_fallback"], dict) or not row["non_colour_fallback"].get("status"):
            errors.append(f"{class_id}: non_colour_fallback must carry status")
        for theme in ("dark", "light"):
            colour = row["colour"].get(theme) if isinstance(row["colour"], dict) else None
            if not isinstance(colour, dict):
                errors.append(f"{class_id}: colour.{theme} must be an object")
                continue
            if expected_live.intersection({class_id, row.get("canonical_class_id")}):
                errors.extend(f"{class_id}: colour.{theme} missing field: {field}" for field in sorted(REQUIRED_COLOUR_FIELDS - set(colour)))
                if not colour.get("resolved_rgb") or not colour.get("rgb"):
                    errors.append(f"{class_id}: live colour.{theme} must have resolved RGB")
        if class_id == "qg-case" or class_id == "qg-relation":
            if status != "internal-canonical":
                errors.append(f"{class_id}: Q6-2 requires internal-canonical status")
        if class_id == "qg-unknown":
            if status != "status-only":
                errors.append("qg-unknown: Q6-2 requires status-only, not a public class")
            if row.get("status_entry", {}).get("points_to") != "projection-status":
                errors.append("qg-unknown: status_entry must point to projection-status")
        if class_id == "qg-negative":
            if status != "legacy-alias" or row.get("canonical_class_id") != "qg-negation":
                errors.append("qg-negative: must be a legacy alias normalizing to qg-negation")
        if class_id == "qg-negation" and "qg-negative" not in row.get("legacy_aliases", []):
            errors.append("qg-negation: legacy_aliases must include qg-negative")
        if class_id == "qg-verb-prefix":
            change = row.get("required_ontology_change", {})
            for field in ("status", "action", "migration_note"):
                if not change.get(field):
                    errors.append(f"qg-verb-prefix: required_ontology_change missing {field}")
            if "decision_made" not in change:
                errors.append("qg-verb-prefix: required_ontology_change missing decision_made")
            if change.get("action") != "SPLIT" or change.get("decision_made") is not False:
                errors.append("qg-verb-prefix: split must be required and not marked decided")
    inv = registry.get("inventory", {})
    if inv.get("live_css_class_count") != len(expected_live):
        errors.append("inventory live_css_class_count does not match live CSS")
    valid_ids = [row["class_id"] for row in rows if row.get("public_internal_status") in {"public-canonical", "internal-canonical"}]
    if inv.get("valid_final_count") != len(valid_ids):
        errors.append("inventory valid_final_count does not emerge from row statuses")
    if set(inv.get("live_css_class_ids", [])) != expected_live:
        errors.append("inventory live_css_class_ids drifted from CSS")
    if set(inv.get("schema_enum_ids", [])) != expected_schema:
        errors.append("inventory schema_enum_ids drifted from schema")
    return errors


def validate_collision_matrix(matrix: dict, registry_class_ids: set[str] | None = None) -> list[str]:
    errors = []
    if registry_class_ids is None:
        registry = _load_json(REGISTRY_PATH)
        registry_class_ids = set(registry.get("inventory", {}).get("live_css_class_ids", []))
    if set(matrix.get("registry_classes", [])) != registry_class_ids:
        errors.append("collision matrix registry_classes does not match live registry classes")
    expected_pair_count = len(registry_class_ids) * (len(registry_class_ids) - 1) // 2
    for theme in ("dark", "light"):
        payload = matrix.get("themes", {}).get(theme)
        if not isinstance(payload, dict):
            errors.append(f"collision matrix missing theme: {theme}")
            continue
        pairs = payload.get("pairs")
        if not isinstance(pairs, list) or len(pairs) != expected_pair_count:
            errors.append(f"{theme}: expected {expected_pair_count} pair rows")
            continue
        seen = set()
        for pair in pairs:
            class_a, class_b = pair.get("class_a"), pair.get("class_b")
            if class_a not in registry_class_ids or class_b not in registry_class_ids:
                unknown = sorted({class_id for class_id in (class_a, class_b) if class_id not in registry_class_ids})
                errors.append(f"{theme}: pair references unknown class: {', '.join(str(class_id) for class_id in unknown)}")
                continue
            if class_a == class_b:
                errors.append(f"{theme}: pair compares a class with itself: {class_a}")
            key = tuple(sorted((class_a, class_b)))
            if key in seen:
                errors.append(f"{theme}: duplicate pair: {class_a}/{class_b}")
            seen.add(key)
            if pair.get("classification") not in VALID_PAIR_CLASSIFICATIONS:
                errors.append(f"{theme}: invalid pair classification for {class_a}/{class_b}")
            if pair.get("flagged") != (tuple(sorted((class_a, class_b))) in OWNER_NAMED_PAIRS or pair.get("classification") != "acceptable-distinct"):
                errors.append(f"{theme}: flagged state is inconsistent for {class_a}/{class_b}")
            if pair.get("classification") == "exact-RGB" and pair.get("hex_a") != pair.get("hex_b"):
                errors.append(f"{theme}: exact-RGB pair has unequal hex values: {class_a}/{class_b}")
            try:
                computed = round(delta_e_76(tuple(pair["rgb_a"]), tuple(pair["rgb_b"])), 2)
                if abs(computed - float(pair["delta_e_76"])) > 0.02:
                    errors.append(f"{theme}: delta-E mismatch for {class_a}/{class_b}")
            except (KeyError, TypeError, ValueError):
                errors.append(f"{theme}: malformed RGB/delta-E fields for {class_a}/{class_b}")
        if len(seen) != expected_pair_count:
            errors.append(f"{theme}: pair set is incomplete")
        named = {tuple(sorted((pair.get("class_a"), pair.get("class_b")))) for pair in pairs if "owner-named-pair" in pair.get("flag_reasons", [])}
        if named != OWNER_NAMED_PAIRS:
            errors.append(f"{theme}: owner-named pair set is incomplete")
    if matrix.get("accessibility_floor", {}).get("normal_text_threshold") != 4.5:
        errors.append("collision matrix accessibility floor must be 4.5")
    return errors


def validate_files(registry_path: Path = REGISTRY_PATH, matrix_path: Path = MATRIX_PATH) -> list[str]:
    registry = _load_json(registry_path)
    errors = validate_registry(registry)
    matrix = _load_json(matrix_path)
    errors.extend(validate_collision_matrix(matrix, registry_class_ids=set(registry.get("inventory", {}).get("live_css_class_ids", []))))
    return errors


def self_test() -> int:
    registry = _load_json(REGISTRY_PATH)
    matrix = _load_json(MATRIX_PATH)
    real_errors = validate_registry(registry)
    real_errors.extend(validate_collision_matrix(matrix, registry_class_ids=set(registry["inventory"]["live_css_class_ids"])))
    if real_errors:
        for error in real_errors:
            print("FAIL", error)
        print(f"qg registry self-test FAIL: {len(real_errors)} real artifact error(s)")
        return 1
    mutations = []
    broken = copy.deepcopy(registry)
    broken["classes"][0].pop("typed_applicability")
    mutations.append(("missing entry field", validate_registry(broken)))
    broken = copy.deepcopy(registry)
    broken["classes"] = [row for row in broken["classes"] if row["class_id"] != "qg-segment"]
    mutations.append(("missing live class", validate_registry(broken)))
    broken_matrix = copy.deepcopy(matrix)
    broken_matrix["themes"]["dark"]["pairs"][0]["class_b"] = "qg-not-in-registry"
    mutations.append(("unknown collision class", validate_collision_matrix(broken_matrix, set(registry["inventory"]["live_css_class_ids"]))))
    for name, errors in mutations:
        if not errors:
            print(f"FAIL red-proof did not turn red: {name}")
            return 1
        print(f"ok   red-proof: {name}")
    print("qg registry self-test OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    errors = validate_files()
    if errors:
        for error in errors:
            print("FAIL", error)
        return 1
    print("QG REGISTRY CONSISTENCY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
