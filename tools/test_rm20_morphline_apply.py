#!/usr/bin/env python3
"""Regression tests for the owner-approved RM-20 morphline apply lane."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "tools" / "apply_rm20_morphline.py"


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
