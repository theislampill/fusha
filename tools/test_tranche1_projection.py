#!/usr/bin/env python3
"""Tests for the Q7 eight-canary fixture-only projection proof."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402
from tools import fact_projectors  # noqa: E402
from tools import lattice_projectors  # noqa: E402


SCHEMA_DIR = ROOT / "qamus" / "schemas"
CROSSWALK_SCHEMA = SCHEMA_DIR / "tranche1-projection-crosswalk.schema.json"
FIXTURE_DIR = ROOT / "qamus" / "examples" / "tranche1"
WHITELIST = ROOT.parent / "data" / "rh_live_01_beta_whitelist.jsonl"
SOURCE_COMMIT = "f706698a9f682de1731b1913221538c7a4289870"
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


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


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


class TrancheProjectorTests(unittest.TestCase):
    def test_tranche_projector_contracts_are_registered_with_lineage(self) -> None:
        contracts = {row["projector_id"]: row for row in fact_projectors.REGISTRY.list_contracts()}
        for projector_id, family in (
            ("sarf.tranche1_fixture_projection.v1", "sarf"),
            ("nahw.tranche1_fixture_projection.v1", "nahw"),
        ):
            with self.subTest(projector_id=projector_id):
                contract = contracts[projector_id]
                self.assertEqual(family, contract["fact_family"])
                self.assertEqual("tools.tranche1_projection", contract["producer"])
                self.assertEqual("1.0.0", contract["version"])
                self.assertEqual([], fact_projectors.validate_projector_record(contract))

    def test_source_gap_abstains_without_copying_linguistic_claims(self) -> None:
        projector = {
            row["projector_id"]: row for row in lattice_projectors.load_registry()["registered"]
        }["sarf.tranche1_fixture_projection.v1"]
        source_row = {
            "loc": "2:13:12",
            "surface": "السُّفَهَاءُ",
            "root": "must-not-copy",
            "morphline": "must-not-copy",
            "segments": [{"surface": "must-not-copy"}],
        }
        policy = {
            "loc": "2:13:12",
            "surface": "السُّفَهَاءُ",
            "fact_family": "sarf",
            "status": "source_gap",
            "blocker": "source lacks typed singular, template, root, and ending facts",
            "route": {"lane": "sarf", "procedure": "sarf/procedures/root-decision.md"},
        }
        result = lattice_projectors.run_tranche1_fixture_projector(
            projector,
            source_row,
            policy,
            fact_ids=["sha256:" + "a" * 64],
        )
        self.assertEqual("typed_queue_record", result["record_type"])
        self.assertEqual("source_gap", result["status"])
        self.assertEqual("tools.tranche1_projection", result["producer"])
        self.assertEqual("sarf.tranche1_fixture_projection.v1", result["projector_id"])
        self.assertEqual("1.0.0", result["version"])
        blob = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("must-not-copy", blob)
        self.assertNotIn("public_payload", result)

    def test_candidate_path_names_producer_projector_and_version(self) -> None:
        projector = {
            row["projector_id"]: row for row in lattice_projectors.load_registry()["registered"]
        }["nahw.tranche1_fixture_projection.v1"]
        result = lattice_projectors.run_tranche1_fixture_projector(
            projector,
            {"loc": "2:34:5", "surface": "لِءَادَمَ"},
            {
                "loc": "2:34:5",
                "surface": "لِءَادَمَ",
                "fact_family": "nahw",
                "status": "candidate",
                "blocker": None,
                "route": None,
            },
            fact_ids=["sha256:" + "b" * 64],
        )
        self.assertEqual(
            ("tools.tranche1_projection", "nahw.tranche1_fixture_projection.v1", "1.0.0"),
            (result["producer"], result["projector_id"], result["version"]),
        )
        self.assertEqual("candidate_projection", result["record_type"])


class TrancheCompilerTests(unittest.TestCase):
    def compile_fixture(self, out_dir: Path) -> dict:
        from tools import tranche1_projection

        return tranche1_projection.compile_tranche(
            WHITELIST,
            FIXTURE_DIR / "canary-policy.json",
            out_dir,
            SOURCE_COMMIT,
        )

    def test_compiler_emits_exact_four_plus_four(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            summary = self.compile_fixture(out_dir)
            self.assertEqual(4, summary["candidate_count"])
            self.assertEqual(4, summary["queue_count"])
            self.assertEqual(0, summary["live_mutations"])
            self.assertEqual(8, len(read_jsonl(out_dir / "normalized-public-payload.jsonl")))

    def test_source_gap_omits_guessed_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            self.compile_fixture(out_dir)
            queue = {row["loc"]: row for row in read_jsonl(out_dir / "unresolved-queue.jsonl")}
            row = queue["2:13:12"]
            def keys(value: object) -> set[str]:
                if isinstance(value, dict):
                    return set(value) | set().union(*(keys(item) for item in value.values()))
                if isinstance(value, list):
                    return set().union(*(keys(item) for item in value)) if value else set()
                return set()

            for forbidden in ("root", "candidate_root", "template", "singular", "morphline", "segments", "public_payload"):
                self.assertNotIn(forbidden, keys(row))
            self.assertEqual("source_gap", row["status"])
            self.assertIn("singular", row["blocker"].lower())
            self.assertIn("template", row["blocker"].lower())

    def test_positive_segments_reconstruct_exact_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            self.compile_fixture(out_dir)
            candidates = read_jsonl(out_dir / "public-hover-projections.jsonl")
            self.assertEqual(4, len(candidates))
            for row in candidates:
                with self.subTest(loc=row["canonical_quran_loc"]):
                    self.assertEqual(row["surface"], "".join(s["surface"] for s in row["segments"]))
                    self.assertEqual("tools.tranche1_projection", row["producer"])
                    self.assertFalse(row["live_mutation_allowed"])


class TrancheValidatorTests(unittest.TestCase):
    def compile_fixture(self, out_dir: Path) -> None:
        from tools import tranche1_projection

        tranche1_projection.compile_tranche(
            WHITELIST,
            FIXTURE_DIR / "canary-policy.json",
            out_dir,
            SOURCE_COMMIT,
        )

    def test_validator_accepts_clean_fixture(self) -> None:
        from tools import validate_tranche1_projection

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            self.compile_fixture(out_dir)
            self.assertEqual(
                [],
                validate_tranche1_projection.validate_tranche(out_dir, WHITELIST, SOURCE_COMMIT),
            )

    def test_validator_rejects_segment_parity_drift(self) -> None:
        from tools import validate_tranche1_projection

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            self.compile_fixture(out_dir)
            path = out_dir / "public-hover-projections.jsonl"
            rows = read_jsonl(path)
            rows[0]["segments"][0]["surface"] += "x"
            write_jsonl(path, rows)
            errors = validate_tranche1_projection.validate_tranche(out_dir, WHITELIST, SOURCE_COMMIT)
            self.assertTrue(any("segment parity" in error for error in errors), errors)

    def test_validator_rejects_round_trip_hash_drift(self) -> None:
        from tools import validate_tranche1_projection

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            self.compile_fixture(out_dir)
            path = out_dir / "projection-crosswalk.jsonl"
            rows = read_jsonl(path)
            rows[0]["output_row_hash"] = "sha256:" + "0" * 64
            write_jsonl(path, rows)
            errors = validate_tranche1_projection.validate_tranche(out_dir, WHITELIST, SOURCE_COMMIT)
            self.assertTrue(any("output hash" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
