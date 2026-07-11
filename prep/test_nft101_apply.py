#!/usr/bin/env python3
"""Untracked red-first fixture for prep/nft101-apply.py baseline guards."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("nft101-apply.py")


def load_apply_module():
    spec = importlib.util.spec_from_file_location("nft101_apply", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_entry(ref: str = "4:46") -> dict:
    return {
        "id": "1c5f7c9c8e05",
        "usage": [
            {"examples": []},
            {"examples": []},
            {
                "examples": [
                    *({"ref": f"1:{index}"} for index in range(1, 12)),
                    {"ar": "ظَلَمُوا أَنْفُسَهُمْ", "ref": ref},
                ]
            },
        ],
    }


class BaselineGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "entries.jsonl"
        self.path.write_text(
            json.dumps(fixture_entry(), ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.baseline_sha = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_refuses_second_application(self) -> None:
        module = load_apply_module()
        module.apply_entry_edit(self.path, self.baseline_sha)
        with self.assertRaisesRegex(module.BaselineError, "already applied|baseline"):
            module.apply_entry_edit(self.path, self.baseline_sha)

    def test_refuses_wrong_baseline(self) -> None:
        module = load_apply_module()
        with self.assertRaisesRegex(module.BaselineError, "baseline"):
            module.apply_entry_edit(self.path, "0" * 64)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["usage"][2]["examples"][11]["ref"], "4:46")

    def test_rollback_snapshot_path_works_in_linked_worktree(self) -> None:
        module = load_apply_module()
        repo = Path(self.tempdir.name) / "repo"
        worktree = Path(self.tempdir.name) / "worktree"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "core.autocrlf", "false"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "nft101@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "NF-T10-1 Test"], check=True)
        (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "fixture"], check=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(worktree)], check=True)

        snapshot_path = module.rollback_snapshot_path(worktree)

        self.assertTrue((worktree / ".git").is_file())
        self.assertEqual(snapshot_path.name, "nft101-rollback")
        self.assertEqual(snapshot_path, snapshot_path.resolve())
        self.assertNotEqual(snapshot_path, worktree / ".git" / "nft101-rollback")


if __name__ == "__main__":
    unittest.main()
