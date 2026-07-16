#!/usr/bin/env python3
"""Red-first tests for the qg ontology registry consistency gate."""

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_qg_registry import validate_registry, validate_collision_matrix  # noqa: E402


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_reconciliation_rejects_missing_required_entry_field():
    registry = _load(ROOT / "qamus" / "registry" / "qg-class-reconciliation.json")
    broken = copy.deepcopy(registry)
    broken["classes"][0].pop("typed_applicability")
    errors = validate_registry(broken, css_text=None, schema=None)
    assert any("typed_applicability" in error for error in errors), errors


def test_reconciliation_rejects_missing_live_css_class():
    registry = _load(ROOT / "qamus" / "registry" / "qg-class-reconciliation.json")
    broken = copy.deepcopy(registry)
    broken["classes"] = [row for row in broken["classes"] if row["class_id"] != "qg-segment"]
    errors = validate_registry(broken, css_text=None, schema=None)
    assert any("qg-segment" in error for error in errors), errors


def test_collision_matrix_rejects_pair_with_unknown_class():
    matrix = _load(ROOT / "qamus" / "registry" / "palette-collision-matrix.json")
    broken = copy.deepcopy(matrix)
    broken["themes"]["dark"]["pairs"][0]["class_b"] = "qg-not-in-registry"
    errors = validate_collision_matrix(broken, registry_class_ids=set(matrix["registry_classes"]))
    assert any("qg-not-in-registry" in error for error in errors), errors


if __name__ == "__main__":
    tests = [
        test_reconciliation_rejects_missing_required_entry_field,
        test_reconciliation_rejects_missing_live_css_class,
        test_collision_matrix_rejects_pair_with_unknown_class,
    ]
    for test in tests:
        test()
        print("ok  ", test.__name__)
    print(f"qg registry tests OK ({len(tests)} tests)")
