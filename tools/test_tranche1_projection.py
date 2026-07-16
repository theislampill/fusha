#!/usr/bin/env python3
"""Tests for the Q7 eight-canary fixture-only projection proof."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402


SCHEMA_DIR = ROOT / "qamus" / "schemas"
CROSSWALK_SCHEMA = SCHEMA_DIR / "tranche1-projection-crosswalk.schema.json"
LINEAGE_FIELDS = {
    "fact_ids",
    "status",
    "source_address",
    "materialization_target",
    "producer",
    "projector_id",
    "version",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def top_properties(schema: dict) -> dict:
    if schema.get("$ref") == "#/$defs/lattice":
        return schema["$defs"]["lattice"]["properties"]
    return schema["properties"]


def validate_crosswalk(row: dict) -> list[str]:
    schema = read_json(CROSSWALK_SCHEMA)
    errors: list[str] = []
    fact_ledger._validate_node(row, schema, "$", errors, schema)
    return errors


class TrancheSchemaTests(unittest.TestCase):
    def test_crosswalk_schema_requires_lineage(self) -> None:
        self.assertTrue(CROSSWALK_SCHEMA.exists(), "crosswalk schema must exist")
        schema = read_json(CROSSWALK_SCHEMA)
        self.assertEqual("qamus.tranche1_projection_crosswalk.v1", schema["properties"]["schema"]["const"])
        self.assertTrue(LINEAGE_FIELDS.issubset(set(schema["required"])))
        errors = validate_crosswalk({"schema": "qamus.tranche1_projection_crosswalk.v1"})
        for field in LINEAGE_FIELDS:
            self.assertTrue(any(field in error for error in errors), (field, errors))

    def test_named_schemas_advertise_additive_lineage_carrier(self) -> None:
        names = [
            "fact-ledger-row.schema.json",
            "morphology-candidate-lattice.schema.json",
            "dependency-candidate-lattice.schema.json",
            "morphosyntax-token.schema.json",
            "canonical-hover-payload.schema.json",
            "public-hover-projection.schema.json",
        ]
        for name in names:
            with self.subTest(schema=name):
                schema = read_json(SCHEMA_DIR / name)
                props = top_properties(schema)
                self.assertTrue(LINEAGE_FIELDS.issubset(set(props)), (name, sorted(set(LINEAGE_FIELDS) - set(props))))
                required = set(schema.get("required", []))
                if schema.get("$ref") == "#/$defs/lattice":
                    required = set(schema["$defs"]["lattice"].get("required", []))
                newly_added = LINEAGE_FIELDS - {"source_address"}
                self.assertTrue(newly_added.isdisjoint(required), (name, "new lineage fields must remain additive"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
