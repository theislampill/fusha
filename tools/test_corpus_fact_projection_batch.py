#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused contract tests for the P007 geometry-to-corpus projection batch."""

from __future__ import annotations

import collections
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MODULE_PATH = os.path.join(ROOT, "tools", "build_corpus_fact_projection_batch.py")
assert os.path.exists(MODULE_PATH), "feature missing: build_corpus_fact_projection_batch.py"
SPEC = importlib.util.spec_from_file_location("build_corpus_fact_projection_batch", MODULE_PATH)
batch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(batch)


class CorpusFactProjectionBatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.baseline, cls.context = batch.build_batch()
        cls.by_loc = collections.defaultdict(list)
        for row in cls.rows:
            cls.by_loc[row["canonical_loc"]].append(row)

    def test_event_trail_effective_state_is_exactly_certified_geometry(self):
        certification = self.baseline["certification_store"]
        self.assertTrue(certification["hash_chain_valid"])
        self.assertEqual(certification["event_count"], 4086)
        self.assertEqual(certification["registered_fact_count"], 1362)
        self.assertEqual(certification["effective_status_counts"], {"certified": 1362})
        self.assertEqual(
            certification["fact_type_counts"],
            {
                "attachment_geometry": 454,
                "surface_reconstruction_nfc": 454,
                "token_host_boundary": 454,
            },
        )

    def test_exact_cohort_counts_and_hashes(self):
        population = self.baseline["population"]
        self.assertEqual(population["source_corpus_manifest_rows"], 117117)
        self.assertEqual(population["occurrences"], 454)
        self.assertEqual(population["appearances"], 985)
        self.assertEqual(
            population["occurrence_id_sha256"],
            "49ef4431360d87a22a8e7def89076cfcfb2df129fa381e05dbee96c764f3529b",
        )
        self.assertEqual(
            population["location_hash"],
            "49ef4431360d87a22a8e7def89076cfcfb2df129fa381e05dbee96c764f3529b",
        )
        self.assertEqual(
            population["appearance_id_sha256"],
            "b3ee61976dcb711c5bb03babc3cf23412e7c1b574fb5b72125ba3b496ce45dc6",
        )
        self.assertEqual(
            population["appearance_hash"],
            "b3ee61976dcb711c5bb03babc3cf23412e7c1b574fb5b72125ba3b496ce45dc6",
        )
        self.assertEqual(
            population["occurrence_surface_posture_counts"],
            {"exact_all_appearances": 385, "mixed_surface": 15, "variant_only": 54},
        )
        self.assertEqual(
            population["appearance_surface_posture_counts"],
            {"exact_all_appearances": 820, "mixed_surface": 50, "variant_only": 115},
        )

    def test_every_occurrence_has_exactly_the_three_permitted_fact_types(self):
        expected = {
            "attachment_geometry",
            "surface_reconstruction_nfc",
            "token_host_boundary",
        }
        self.assertEqual(len(self.by_loc), 454)
        for loc, rows in self.by_loc.items():
            projection = rows[0]["geometry_projection"]
            self.assertEqual(set(projection["certified_facts"]), expected, loc)
            self.assertEqual(len(projection["fact_ids"]), 3, loc)
            self.assertEqual(projection["certification"], "partial_certified_geometry_only")

    def test_geometry_never_promotes_identity_function_or_semantics(self):
        forbidden_projection_keys = {
            "entry_id",
            "sense_id",
            "lexeme_id",
            "function",
            "meaning",
            "root",
            "nahw_fact_id",
            "semantic_colour",
            "hover_payload",
            "website_payload",
        }
        for row in self.rows:
            projection = row["geometry_projection"]
            self.assertTrue(forbidden_projection_keys.isdisjoint(projection), row["appearance_id"])
            boundaries = row["semantic_boundaries"]
            self.assertEqual(boundaries["token_lexeme"], "not_projected_geometry_only")
            self.assertEqual(boundaries["particle_function"], "not_projected_geometry_only")
            self.assertEqual(boundaries["nahw"], "not_available_candidate_refs_are_not_nahw")
            self.assertEqual(boundaries["colour"], "boundary_available_no_semantic_colour")
            self.assertEqual(boundaries["hover"], "not_available_missing_full_token_facts")

        with self.assertRaises(batch.ProjectionBuildError):
            batch.validate_geometry_fact_scope({
                "fact_id": "fact:forged",
                "fact_type": "attachment_geometry",
                "fact_value": {"function": "jarr"},
            })

    def test_component_span_is_subtoken_and_reconstructs_the_token(self):
        for loc, rows in self.by_loc.items():
            geometry = rows[0]["geometry_projection"]["span_geometry"]
            token_span = geometry["token_char_span"]
            component_span = geometry["component_char_span"]
            host_span = geometry["host_char_span"]
            self.assertEqual(token_span["start"], 0, loc)
            self.assertEqual(component_span["start"], 0, loc)
            self.assertEqual(component_span["end"], host_span["start"], loc)
            self.assertEqual(host_span["end"], token_span["end"], loc)
            self.assertLess(component_span["end"], token_span["end"], loc)
            self.assertTrue(geometry["component_is_subtoken"], loc)
            self.assertEqual(
                geometry["component_surface"] + geometry["host_surface"],
                geometry["token_surface_nfc"],
                loc,
            )

    def test_occurrence_wide_surface_gate_never_partially_projects_mixed_occurrence(self):
        occurrence_counts = collections.Counter()
        appearance_counts = collections.Counter()
        for loc, rows in self.by_loc.items():
            dispositions = {row["downstream_disposition"] for row in rows}
            hashes = {row["geometry_projection_hash"] for row in rows}
            self.assertEqual(len(dispositions), 1, loc)
            self.assertEqual(len(hashes), 1, loc)
            disposition = next(iter(dispositions))
            occurrence_counts[disposition] += 1
            appearance_counts[disposition] += len(rows)
            if rows[0]["occurrence_surface_posture"] == "mixed_surface":
                self.assertEqual(disposition, "appearance_surface_variant_mapping_required", loc)
                self.assertIn("exact_nfc", {row["appearance_surface_posture"] for row in rows})
                self.assertIn("surface_variant", {row["appearance_surface_posture"] for row in rows})
        self.assertEqual(
            occurrence_counts,
            {
                "geometry_projection_ready": 385,
                "appearance_surface_variant_mapping_required": 69,
            },
        )
        self.assertEqual(
            appearance_counts,
            {
                "geometry_projection_ready": 820,
                "appearance_surface_variant_mapping_required": 165,
            },
        )

    def test_candidate_refs_and_card_owner_remain_non_authorities(self):
        candidate_rows = 0
        context_rows = 0
        for row in self.rows:
            if row["corpus_context"]["particle_function_candidate_ref_count"]:
                candidate_rows += 1
                self.assertEqual(
                    row["semantic_boundaries"]["nahw"],
                    "not_available_candidate_refs_are_not_nahw",
                )
            if not row["corpus_context"]["selected"]:
                context_rows += 1
                self.assertEqual(
                    row["semantic_boundaries"]["token_lexeme"],
                    "not_projected_geometry_only",
                )
                self.assertTrue(row["corpus_context"]["card_owner_is_not_token_lexeme"])
        self.assertGreater(candidate_rows, 0)
        self.assertGreater(context_rows, 0)

    def test_zero_website_payload_and_live_output(self):
        delivery = self.baseline["delivery_boundary"]
        self.assertEqual(delivery["website_payloads_generated"], 0)
        self.assertEqual(delivery["live_outputs_generated"], 0)
        for row in self.rows:
            self.assertEqual(row["delivery"]["website_payload"], "not_generated")
            self.assertEqual(row["delivery"]["live_output"], "not_generated")
            self.assertFalse(row["delivery"]["public_materialization_allowed"])
            self.assertFalse(row["delivery"]["live_mutation_allowed"])

    def test_schema_closes_geometry_semantic_and_delivery_boundaries(self):
        schema_path = os.path.join(
            ROOT, "qamus", "schemas", "corpus-fact-projection-disposition.schema.json")
        self.assertTrue(os.path.exists(schema_path), "projection disposition schema is missing")
        with open(schema_path, encoding="utf-8") as handle:
            schema = json.load(handle)
        self.assertFalse(schema["additionalProperties"])
        projection = schema["properties"]["geometry_projection"]
        self.assertFalse(projection["additionalProperties"])
        self.assertEqual(
            projection["properties"]["certification"]["const"],
            "partial_certified_geometry_only",
        )
        boundaries = schema["properties"]["semantic_boundaries"]["properties"]
        self.assertEqual(boundaries["colour"]["const"], "boundary_available_no_semantic_colour")
        self.assertEqual(boundaries["hover"]["const"], "not_available_missing_full_token_facts")
        delivery = schema["properties"]["delivery"]["properties"]
        self.assertEqual(delivery["website_payload"]["const"], "not_generated")
        self.assertEqual(delivery["live_output"]["const"], "not_generated")

    def test_cli_writes_deterministic_output_and_check_mode_verifies_freshness(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = os.path.join(temp_dir, "batch.jsonl")
            baseline = os.path.join(temp_dir, "baseline.json")
            sample = os.path.join(temp_dir, "sample.jsonl")
            sample_meta = os.path.join(temp_dir, "sample.meta.json")
            command = [
                sys.executable,
                os.path.join(ROOT, "tools", "build_corpus_fact_projection_batch.py"),
                "--output", output,
                "--baseline-output", baseline,
                "--sample-output", sample,
                "--sample-meta-output", sample_meta,
            ]
            generated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            checked = subprocess.run(command + ["--check"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("CHECK PASS", checked.stdout)
            with open(baseline, encoding="utf-8") as handle:
                written_baseline = json.load(handle)
            self.assertEqual(written_baseline["population"]["appearances"], 985)


if __name__ == "__main__":
    unittest.main()
