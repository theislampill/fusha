#!/usr/bin/env python3
"""Red-first contract for the append-safe KC catalog shard loader."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import kc_catalog


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class KcCatalogShardTests(unittest.TestCase):
    def test_legacy_catalog_then_sorted_shards_are_one_deterministic_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "curriculum" / "kc-catalog.json", [
                {"kc_id": "kc-legacy-a"},
                {"kc_id": "kc-legacy-b"},
            ])
            _write_jsonl(root / "curriculum" / "kc-catalog.d" / "z.jsonl", [
                {"kc_id": "kc-shard-z"},
            ])
            _write_jsonl(root / "curriculum" / "kc-catalog.d" / "a.jsonl", [
                {"kc_id": "kc-shard-a"},
            ])
            rows = kc_catalog.load_kc_catalog(root)
            self.assertEqual(
                [row["kc_id"] for row in rows],
                ["kc-legacy-a", "kc-legacy-b", "kc-shard-a", "kc-shard-z"],
            )

    def test_duplicate_id_across_legacy_and_shard_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "curriculum" / "kc-catalog.json", [{"kc_id": "kc-a"}])
            _write_jsonl(
                root / "curriculum" / "kc-catalog.d" / "batch.jsonl",
                [{"kc_id": "kc-a"}],
            )
            with self.assertRaisesRegex(kc_catalog.KcCatalogError, "duplicate kc_id"):
                kc_catalog.load_kc_catalog(root)

    def test_missing_id_and_non_object_rows_fail_closed(self):
        for bad_row, expected in (({"plain_rule": "missing"}, "missing kc_id"), ([], "must be an object")):
            with self.subTest(bad_row=bad_row), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write_json(root / "curriculum" / "kc-catalog.json", [])
                _write_jsonl(root / "curriculum" / "kc-catalog.d" / "bad.jsonl", [bad_row])
                with self.assertRaisesRegex(kc_catalog.KcCatalogError, expected):
                    kc_catalog.load_kc_catalog(root)

    def test_absent_shard_directory_preserves_legacy_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = [{"kc_id": "kc-only"}]
            _write_json(root / "curriculum" / "kc-catalog.json", expected)
            self.assertEqual(kc_catalog.load_kc_catalog(root), expected)


class DeclaredShardGateTests(unittest.TestCase):
    """F3: every gate-bearing curriculum/kc-catalog.d/*.jsonl shard must be pinned by name; an undeclared
    shard must fail closed rather than silently join the catalog _check_kc_gate_row reads."""

    def test_undeclared_shard_fails_closed(self):
        import sys as _sys
        _repo = TOOLS.parent
        _sys.path.insert(0, str(_repo))
        from tools import fusha_tutor_runtime as RT

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_jsonl(root / "curriculum" / "kc-catalog.d" / "rogue-undeclared-shard.jsonl",
                        [{"kc_id": "kc-rogue"}])
            # RT imports kc_catalog as "tools.kc_catalog" (a distinct module object from this file's bare
            # "kc_catalog" import), so the raised exception's class must be looked up through RT itself.
            with self.assertRaises(RT.kc_catalog.KcCatalogError):
                RT._assert_declared_kc_shards(repo_root=str(root))

    def test_declared_shards_match_the_real_kc_catalog_d_directory_exactly(self):
        import sys as _sys
        _repo = TOOLS.parent
        _sys.path.insert(0, str(_repo))
        from tools import fusha_tutor_runtime as RT

        real_shard_dir = _repo / "curriculum" / "kc-catalog.d"
        on_disk = {p.name for p in real_shard_dir.glob("*.jsonl")}
        self.assertEqual(on_disk, RT._DECLARED_KC_SHARDS,
                         "curriculum/kc-catalog.d drifted from tools.fusha_tutor_runtime._DECLARED_KC_SHARDS")

    def test_real_repo_kc_catalog_d_passes_the_declared_shard_gate(self):
        import sys as _sys
        _repo = TOOLS.parent
        _sys.path.insert(0, str(_repo))
        from tools import fusha_tutor_runtime as RT

        RT._assert_declared_kc_shards()  # must not raise


if __name__ == "__main__":
    unittest.main()
