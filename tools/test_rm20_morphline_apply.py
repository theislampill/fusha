#!/usr/bin/env python3
"""Regression tests for the owner-approved RM-20 morphline apply lane."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "tools" / "apply_rm20_morphline.py"
INPUTS = ROOT / ".inputs"


class Rm20RefusalGateTests(unittest.TestCase):
    def test_all_five_manifest_refusals_stop_before_positive_path(self) -> None:
        result = subprocess.run(
            [sys.executable, str(APPLY), "--self-test-refusals"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("REFUSAL GATE PASS: 5/5", result.stdout)
        self.assertIn("tie_unresolved=2", result.stdout)
        self.assertIn("blocked_insufficient_convention_exemplars=3", result.stdout)
        self.assertIn("positive_path_calls=0", result.stdout)


class Rm20PositivePathTests(unittest.TestCase):
    def test_tracked_apply_artifacts_match_the_approved_manifest(self) -> None:
        sys.path.insert(0, str(ROOT))
        from tools import apply_rm20_morphline as apply_mod
        from tools import fact_ledger
        from tools.largelexicon_common import previous_generation_path, verify_generation

        manifest = apply_mod.load_manifest()
        receipt = json.loads(
            apply_mod.RECEIPT_PATH.read_text(encoding="utf-8")
        )
        reports = json.loads(
            apply_mod.FINAL_REPORTS_PATH.read_text(encoding="utf-8")
        )

        self.assertEqual("qamus.rm20_morphline_apply_receipt.v1", receipt["schema"])
        self.assertEqual(manifest["input_sha256"], receipt["input_sha256"])
        self.assertEqual(receipt["entries_sha256_before"], receipt["entries_sha256_after"])
        self.assertEqual(receipt["public_whitelist_sha256_before"], receipt["public_whitelist_sha256_after"])
        self.assertEqual(
            {
                "payloads": 9,
                "dependent_bindings": 26,
                "replacement_bindings": 26,
                "payload_tombstones": 9,
                "binding_tombstone_conflicts": 26,
                "facts": 26,
                "fact_revisions": 104,
            },
            receipt["counts"],
        )

        approved = {row["final_canonical_payload_id"]: row for row in manifest["approved_payloads"]}
        self.assertEqual(set(approved), {row["new_payload"]["canonical_payload_id"] for row in reports})
        self.assertEqual(9, len(reports))
        expected_new_bindings = {
            binding["new_binding_id"]
            for row in manifest["approved_payloads"]
            for binding in row["binding_rebinds"]
        }
        actual_new_bindings = {
            binding["new_binding"]["binding_id"]
            for report in reports
            for binding in report["binding_rebinds"]
        }
        self.assertEqual(expected_new_bindings, actual_new_bindings)

        store = fact_ledger.FactLedgerStore(apply_mod.LEDGER_DIR)
        apply_mod.validate_ledger(store, "materialized", 4)
        current = store.query(fact_type="morphline_rendering", current_only=True)
        self.assertEqual(26, len(current))
        for row in current:
            history = store.history(row["fact_id"])
            self.assertEqual(
                ["candidate", "review_required", "certified", "materialized"],
                [revision["certification_state"] for revision in history],
            )
            self.assertEqual(
                ["Opus-author", "Codex-reviewer"],
                [vote["voter_id"] for vote in history[-1]["review_votes"]],
            )
            evidence_refs = {item["evidence_id"] for item in history[-1]["evidence"]}
            vote_refs = {item["evidence_ref"] for item in history[-1]["review_votes"]}
            self.assertEqual(evidence_refs, vote_refs)
            self.assertEqual(2, len(evidence_refs))

        expected_generation_ids = {
            "current": (set(approved), expected_new_bindings),
            "previous": (
                {row["old_canonical_payload_id"] for row in manifest["approved_payloads"]},
                {
                    binding["old_binding_id"]
                    for row in manifest["approved_payloads"]
                    for binding in row["binding_rebinds"]
                },
            ),
        }
        for label, generation in (
            ("current", apply_mod.SHADOW_DIR),
            ("previous", previous_generation_path(apply_mod.SHADOW_DIR)),
        ):
            self.assertTrue(verify_generation(generation, allow_legacy=False)["ok"])
            payloads = apply_mod.read_jsonl(generation / apply_mod.SHARD_PAYLOADS)
            bindings = apply_mod.read_jsonl(generation / apply_mod.SHARD_BINDINGS)
            expected_payloads, expected_bindings = expected_generation_ids[label]
            self.assertEqual(expected_payloads, {row["canonical_payload_id"] for row in payloads})
            self.assertEqual(expected_bindings, {row["binding_id"] for row in bindings})

        refusal_counts = apply_mod.run_refusal_gate(manifest)
        self.assertEqual(
            Counter({"tie_unresolved": 2, "blocked_insufficient_convention_exemplars": 3}),
            refusal_counts,
        )

    def test_committed_ledger_copy_omits_disposable_index_cache(self) -> None:
        sys.path.insert(0, str(ROOT))
        from tools import apply_rm20_morphline as apply_mod

        self.assertTrue(hasattr(apply_mod, "copy_ledger_for_commit"))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            target = base / "target"
            source.mkdir()
            (source / "ledger.jsonl").write_text("{}\n", encoding="utf-8")
            (source / "index.json").write_text("{}\n", encoding="utf-8")
            apply_mod.copy_ledger_for_commit(source, target)
            self.assertTrue((target / "ledger.jsonl").is_file())
            self.assertFalse((target / "index.json").exists())

    def test_real_frozen_inputs_pass_all_precommit_gates_in_tempdir(self) -> None:
        if not INPUTS.is_dir():
            self.skipTest("workspace-only frozen inputs are absent in a fresh checkout")
        result = subprocess.run(
            [sys.executable, str(APPLY), "--self-test-positive"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("POSITIVE PATH PASS: reports=9", result.stdout)
        self.assertIn("dependent=26 replacement=26 conflicts=26", result.stdout)
        self.assertIn("ledger_before=certified:26", result.stdout)
        self.assertIn("ledger_after=materialized:26 histories=26x4", result.stdout)
        self.assertIn("atomic=current+prev generation_ok", result.stdout)
        self.assertIn("double_compile=byte_identical", result.stdout)
        self.assertIn("modify=11 exact_set", result.stdout)
        self.assertIn("refusal_locations_in_delta=0", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
