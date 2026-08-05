#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused red-first tests for the deterministic FUSHA-BENCH v1 runner."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "tools", "fusha_bench.py")
assert os.path.exists(MODULE_PATH), "feature missing: tools/fusha_bench.py"
SPEC = importlib.util.spec_from_file_location("fusha_bench", MODULE_PATH)
bench = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bench)


class FushaBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = bench.read_json(bench.DEFAULT_MANIFEST)
        cls.quarantine = bench.read_json(bench.DEFAULT_QUARANTINE)
        cls.report = bench.build_report()

    def test_report_has_four_structured_axes_and_no_aggregate(self):
        self.assertEqual(
            set(self.report["axes"]),
            {"ownership_geometry", "structured_hover", "contextual_translation", "tutor"},
        )
        self.assertFalse(bench.contains_aggregate_score(self.report))
        self.assertNotIn("overall_score", self.report)
        for axis in self.report["axes"].values():
            self.assertIn("status", axis)

    def test_geometry_uses_effective_certification_and_exact_occurrences(self):
        axis = self.report["axes"]["ownership_geometry"]
        self.assertEqual(axis["status"], "scored_authority_integrity")
        self.assertEqual(axis["canonical_occurrences"], 454)
        self.assertEqual(axis["effectively_certified_facts"], 1362)
        self.assertEqual(axis["appearances_dispositioned"], 985)
        self.assertEqual(axis["metric"]["numerator"], 1362)
        self.assertEqual(axis["metric"]["denominator"], 1362)
        self.assertEqual(axis["identity_join"], "exact_quran_occurrence_id")
        self.assertEqual(axis["gold_scope"], "partial_attachment_geometry_only")
        self.assertFalse(axis["full_token_ownership_gold"])
        self.assertEqual(axis["metric"]["comparison"], "baseline_no_previous_report")
        self.assertIsNone(axis["metric"]["delta"])

    def test_hover_scores_only_current_certified_pilot_facts(self):
        axis = self.report["axes"]["structured_hover"]
        self.assertEqual(axis["status"], "scored_projection_fact_parity")
        self.assertEqual(axis["effectively_certified_facts"], 49)
        self.assertEqual(axis["occurrence_scoped_facts"], 48)
        self.assertEqual(axis["supporting_entry_facts"], 1)
        self.assertEqual(axis["canonical_occurrences"], 12)
        self.assertEqual(axis["appearances_dispositioned"], 78)
        self.assertEqual(axis["metric"]["name"], "projection_effective_fact_parity")
        self.assertEqual(axis["metric"]["numerator"], 49)
        self.assertEqual(axis["metric"]["denominator"], 49)
        self.assertEqual(axis["active_rivals"], 0)
        self.assertEqual(axis["gold_scope"], "p007_pilot_structured_facts_only")
        self.assertFalse(axis["full_rich_hover_gold"])

    def test_hover_appearance_count_and_fact_parity_are_derived(self):
        pilot = self.manifest["axes"]["structured_hover"]
        projections = bench.read_jsonl(
            os.path.join(ROOT, "qamus", "examples", "p007-li-pilot", "projections.jsonl")
        )
        reverse_trace = bench.read_json_array(
            os.path.join(ROOT, "qamus", "examples", "p007-li-pilot", "reverse-trace.json")
        )
        facts, _ = bench.load_effective_certified_facts(
            root=ROOT,
            store_dir=pilot["certification_store_dir"],
            claims_path=pilot["claims_path"],
            allowed_fact_types=set(pilot["allowed_fact_types"]),
        )
        parity = bench.analyze_hover_projection_parity(projections, reverse_trace, facts)
        self.assertEqual(parity["appearance_count"], 78)
        self.assertEqual(parity["rendered_fact_count"], 49)

        stale_appearance = copy.deepcopy(projections)
        stale_appearance[0]["appearances"][0]["projection_hash"] = "0" * 64
        with self.assertRaisesRegex(bench.BenchError, "appearance projection hash"):
            bench.analyze_hover_projection_parity(stale_appearance, reverse_trace, facts)

        stale_fact_binding = copy.deepcopy(reverse_trace)
        stale_fact_binding[0]["renders_from_facts"].pop()
        with self.assertRaisesRegex(bench.BenchError, "projection/fact parity"):
            bench.analyze_hover_projection_parity(projections, stale_fact_binding, facts)

        stale_axis = copy.deepcopy(self.report["axes"]["structured_hover"])
        stale_axis["appearances_dispositioned"] -= 1
        with self.assertRaisesRegex(bench.BenchError, "stale appearance count"):
            bench.ensure_hover_axis_matches_parity(stale_axis, parity)

    def test_translation_refuses_a_fabricated_denominator(self):
        axis = self.report["axes"]["contextual_translation"]
        self.assertEqual(axis["status"], "not_scored_no_certified_gold")
        self.assertEqual(axis["denominator"], 0)
        self.assertIsNone(axis["score"])
        mutated = copy.deepcopy(self.manifest)
        mutated["axes"]["contextual_translation"]["denominator"] = 1
        with self.assertRaisesRegex(bench.BenchError, "certified translation gold"):
            bench.validate_manifest(mutated, root=ROOT)

    def test_tutor_probes_are_quarantined_from_authoring_and_runtime_inputs(self):
        axis = self.report["axes"]["tutor"]
        self.assertEqual(axis["status"], "scored_runtime_replay")
        self.assertEqual(axis["probe_count"], 16)
        self.assertEqual(axis["quarantine_overlap_count"], 0)
        self.assertEqual(set(axis["probe_ids"]), set(self.quarantine["probe_ids"]))
        self.assertFalse(axis["learner_performance_scored"])
        self.assertEqual(axis["metric"]["name"], "ordinary_tutor_runtime_replay")
        self.assertEqual(axis["metric"]["numerator"], 16)
        self.assertEqual(axis["metric"]["denominator"], 16)
        self.assertEqual(axis["runtime_replay"]["expected_answers_accepted"], 16)
        self.assertGreater(axis["runtime_replay"]["accepted_forms_checked"], 16)
        self.assertGreater(axis["runtime_replay"]["forbidden_answers_rejected"], 16)
        self.assertEqual(axis["runtime_replay"]["required_reason_gates_enforced"], 16)
        self.assertGreater(axis["runtime_replay"]["two_vote_rows_held"], 0)
        with self.assertRaisesRegex(bench.BenchError, "quarantine overlap"):
            bench.ensure_no_quarantine_overlap(
                set(self.quarantine["probe_ids"]),
                {"synthetic-authoring-input": {self.quarantine["probe_ids"][0]}},
            )

    def test_quarantine_rejects_a_discovered_but_unlisted_runtime_key_bank(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = os.path.abspath(temp_dir)
            assessment_dir = os.path.join(temp_root, "curriculum", "assessment")
            keys_dir = os.path.join(temp_root, "curriculum", "drills", "keys")
            os.makedirs(assessment_dir)
            os.makedirs(keys_dir)
            probe_path = os.path.join(assessment_dir, "placement-test.sample.jsonl")
            listed_path = os.path.join(keys_dir, "listed.keys.jsonl")
            unlisted_path = os.path.join(keys_dir, "unlisted.keys.jsonl")
            shutil.copyfile(
                os.path.join(ROOT, "curriculum", "assessment", "placement-test.sample.jsonl"),
                probe_path,
            )
            with open(listed_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write('{"id":"listed-runtime-row","expected_answer":"listed"}\n')
            with open(unlisted_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write('{"id":"unlisted-runtime-row","expected_answer":"unlisted"}\n')
            manifest = {
                "axes": {"tutor": {
                    "probe_artifact_id": "probes",
                    "excluded_input_artifact_ids": ["listed"],
                }}
            }
            quarantine = copy.deepcopy(self.quarantine)
            quarantine["excluded_input_artifact_ids"] = ["listed"]
            artifacts = {
                "probes": {"path": os.path.relpath(probe_path, temp_root)},
                "listed": {
                    "path": os.path.relpath(listed_path, temp_root),
                    "role": "runtime_drill_input",
                },
            }
            with self.assertRaisesRegex(bench.BenchError, "discovered.*unlisted"):
                bench._validate_quarantine(temp_root, manifest, quarantine, artifacts)

    def test_quarantine_rejects_probe_answer_text_exposed_to_an_input(self):
        probe_rows = bench.read_jsonl(
            os.path.join(ROOT, "curriculum", "assessment", "placement-test.sample.jsonl")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            probe_path = os.path.join(temp_dir, "placement.jsonl")
            input_path = os.path.join(temp_dir, "runtime.keys.jsonl")
            shutil.copyfile(
                os.path.join(ROOT, "curriculum", "assessment", "placement-test.sample.jsonl"),
                probe_path,
            )
            with open(input_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps({
                    "id": "different-stable-id",
                    "prompt": "Unrelated prompt",
                    "expected_answer": probe_rows[0]["expected_answer"],
                }, ensure_ascii=False) + "\n")
            manifest = {"axes": {"tutor": {
                "probe_artifact_id": "probes",
                "excluded_input_artifact_ids": ["input"],
            }}}
            quarantine = copy.deepcopy(self.quarantine)
            quarantine["excluded_input_artifact_ids"] = ["input"]
            artifacts = {
                "probes": {"path": probe_path},
                "input": {"path": input_path, "role": "runtime_drill_input"},
            }
            with self.assertRaisesRegex(bench.BenchError, "answer exposure"):
                bench._validate_quarantine(temp_dir, manifest, quarantine, artifacts)

    def test_tutor_runtime_replay_fails_closed_on_bad_key_semantics(self):
        rows = bench.read_jsonl(
            os.path.join(ROOT, "curriculum", "assessment", "placement-test.sample.jsonl")
        )
        broken_forbidden = copy.deepcopy(rows)
        broken_forbidden[0]["forbidden_answers"] = []
        with self.assertRaisesRegex(bench.BenchError, "requires forbidden answers"):
            bench.replay_tutor_probes(broken_forbidden)

        broken_reason = copy.deepcopy(rows)
        broken_reason[0]["required_reasoning"] = []
        with self.assertRaisesRegex(bench.BenchError, "requires reasoning gates"):
            bench.replay_tutor_probes(broken_reason)

    def test_copied_claim_status_never_substitutes_for_effective_state(self):
        pilot = self.manifest["axes"]["structured_hover"]
        facts, statuses = bench.load_effective_certified_facts(
            root=ROOT,
            store_dir=pilot["certification_store_dir"],
            claims_path=pilot["claims_path"],
            allowed_fact_types=set(pilot["allowed_fact_types"]),
        )
        self.assertEqual(len(facts), 49)
        self.assertEqual(sum(status == "review_required" for status in statuses.values()), 36)
        self.assertNotEqual(len(statuses), len(facts))

    def test_broken_event_hash_chain_is_rejected_even_when_claims_look_certified(self):
        pilot = self.manifest["axes"]["structured_hover"]
        source_dir = os.path.join(ROOT, pilot["certification_store_dir"])
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_store = os.path.join(temp_dir, "certification")
            shutil.copytree(source_dir, copied_store)
            events_path = os.path.join(copied_store, "events.jsonl")
            with open(events_path, "r+", encoding="utf-8") as handle:
                events = handle.read()
                handle.seek(0)
                handle.write(events.replace('"actor":', '"actor_broken":', 1))
                handle.truncate()
            with self.assertRaisesRegex(bench.BenchError, "certification trail"):
                bench.load_effective_certified_facts(
                    root=ROOT,
                    store_dir=copied_store,
                    claims_path=pilot["claims_path"],
                    allowed_fact_types=set(pilot["allowed_fact_types"]),
                )

    def test_candidate_or_revoked_fact_cannot_be_added_to_gold_by_status_copy(self):
        pilot = self.manifest["axes"]["structured_hover"]
        source_claims = os.path.join(ROOT, pilot["claims_path"])
        with tempfile.TemporaryDirectory() as temp_dir:
            forged = os.path.join(temp_dir, "typed-facts.jsonl")
            shutil.copyfile(source_claims, forged)
            forged_row = {
                "fact_id": "fact:forged:candidate",
                "fact_type": "contextual_function",
                "certification": {"status": "certified"},
                "source_address": {"address": "quran:2:2:2"},
                "surface_spans": [{"quran_loc": "quran:2:2:2", "surface": "فِى"}],
            }
            with open(forged, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(forged_row, ensure_ascii=False, sort_keys=True) + "\n")
            with self.assertRaisesRegex(bench.BenchError, "exact effective certified fact set"):
                bench.load_effective_certified_facts(
                    root=ROOT,
                    store_dir=pilot["certification_store_dir"],
                    claims_path=forged,
                    allowed_fact_types=set(pilot["allowed_fact_types"]),
                )

    def test_norm_or_surface_join_is_forbidden(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["axes"]["ownership_geometry"]["identity_join"] = "normalized_surface"
        with self.assertRaisesRegex(bench.BenchError, "exact_quran_occurrence_id"):
            bench.validate_manifest(mutated, root=ROOT)

    def test_stale_span_wrong_reason_and_active_rival_are_rejected(self):
        geometry = {
            "fact_id": "fact:test:geom",
            "fact_type": "attachment_geometry",
            "fact_value": {
                "surface_nfc": "لِلَّهِ",
                "component_surface": "لِ",
                "char_span": {"start": 0, "end": 1},
                "base_letter_span": {"start": 0, "end": 1},
            },
            "surface_spans": [{"quran_loc": "quran:1:2:2", "surface": "لِلَّهِ"}],
            "unresolved_blockers": [],
            "contradiction_records": [],
        }
        with self.assertRaisesRegex(bench.BenchError, "char span"):
            bench.validate_certified_fact(geometry)

        function = {
            "fact_id": "fact:test:function",
            "fact_type": "contextual_function",
            "fact_value": {"function": "harf-jarr-lam-fused", "reason_key": ""},
            "surface_spans": [{"quran_loc": "quran:1:2:2", "surface": "لِلَّهِ"}],
            "unresolved_blockers": [],
            "contradiction_records": [],
        }
        with self.assertRaisesRegex(bench.BenchError, "reason_key"):
            bench.validate_certified_fact(function)
        function["fact_value"]["reason_key"] = "exact-governor-reason"
        function["contradiction_records"] = [{"status": "unresolved"}]
        with self.assertRaisesRegex(bench.BenchError, "unresolved rival"):
            bench.validate_certified_fact(function)

    def test_candidate_payload_prose_is_safety_canary_never_gold(self):
        canary_ids = set(self.manifest["safety_canary_artifact_ids"])
        self.assertTrue(canary_ids)
        axis_artifacts = bench.axis_gold_artifact_ids(self.manifest)
        self.assertTrue(canary_ids.isdisjoint(axis_artifacts))
        mutated = copy.deepcopy(self.manifest)
        mutated["axes"]["structured_hover"]["gold_artifact_ids"].append(
            next(iter(canary_ids))
        )
        with self.assertRaisesRegex(bench.BenchError, "safety canary"):
            bench.validate_manifest(mutated, root=ROOT)

    def test_every_authority_artifact_is_sha_pinned(self):
        bench.validate_manifest(self.manifest, root=ROOT)
        mutated = copy.deepcopy(self.manifest)
        mutated["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(bench.BenchError, "sha256 mismatch"):
            bench.validate_manifest(mutated, root=ROOT)

    def test_kc_catalog_gate_bearing_artifacts_are_pinned_with_the_kc_catalog_input_role(self):
        # R4: curriculum/kc-catalog.json, both declared shards, and the loader module itself must all be
        # sha-pinned with role kc_catalog_input -- not just discoverable on disk.
        expected_paths = {"curriculum/kc-catalog.json", "tools/kc_catalog.py"} | {
            "curriculum/kc-catalog.d/%s" % name for name in bench.kc_catalog.DECLARED_KC_SHARDS
        }
        pinned = {a["path"]: a for a in self.manifest["artifacts"] if a.get("role") == "kc_catalog_input"}
        self.assertEqual(set(pinned), expected_paths)
        for path, artifact in pinned.items():
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$", path)

    def test_removing_a_gate_bearing_kc_catalog_artifact_fails_the_completeness_guard(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["artifacts"] = [a for a in mutated["artifacts"] if a["artifact_id"] != "kc-catalog-legacy"]
        with self.assertRaisesRegex(bench.BenchError, "gate-bearing KC catalog artifact"):
            bench.validate_manifest(mutated, root=ROOT)

    def test_axis_paths_are_bound_to_the_exact_pinned_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_claims = os.path.join(temp_dir, "typed-facts.jsonl")
            shutil.copyfile(
                os.path.join(ROOT, self.manifest["axes"]["structured_hover"]["claims_path"]),
                copied_claims,
            )
            mutated = copy.deepcopy(self.manifest)
            mutated["axes"]["structured_hover"]["claims_path"] = copied_claims
            with self.assertRaisesRegex(bench.BenchError, "pinned artifact"):
                bench.validate_manifest(mutated, root=ROOT)

    def test_missing_certification_store_is_refused_without_creating_it(self):
        pilot = self.manifest["axes"]["structured_hover"]
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_store = os.path.join(temp_dir, "missing-certification-store")
            with self.assertRaisesRegex(bench.BenchError, "store directory missing"):
                bench.load_effective_certified_facts(
                    root=ROOT,
                    store_dir=missing_store,
                    claims_path=pilot["claims_path"],
                    allowed_fact_types=set(pilot["allowed_fact_types"]),
                )
            self.assertFalse(os.path.exists(missing_store))

    def test_leakage_and_aggregate_score_are_rejected(self):
        with self.assertRaisesRegex(bench.BenchError, "source-boundary leak"):
            bench.ensure_source_clean({"note": "/srv/private/source/lesson.txt"})
        mutated = copy.deepcopy(self.manifest)
        mutated["aggregate_score"] = 1.0
        with self.assertRaisesRegex(bench.BenchError, "aggregate"):
            bench.validate_manifest(mutated, root=ROOT)

    def test_committed_report_is_fresh_and_cli_refuses_implicit_write(self):
        with open(bench.DEFAULT_REPORT, encoding="utf-8") as handle:
            committed = json.load(handle)
        self.assertEqual(committed, self.report)
        with tempfile.TemporaryDirectory() as temp_dir:
            noncanonical = os.path.join(temp_dir, "report.json")
            with open(noncanonical, "w", encoding="utf-8") as handle:
                json.dump(self.report, handle, ensure_ascii=False)
            with self.assertRaisesRegex(bench.BenchError, "byte-for-byte"):
                bench.check_fresh(noncanonical)
        proc = subprocess.run(
            [sys.executable, MODULE_PATH, "--report-out", os.path.join(ROOT, "out", "should-not-write.json")],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--write", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
