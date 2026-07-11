#!/usr/bin/env python3
"""Stdlib-only regression tests for RM-19 atomic shard promotion.

Red-first evidence captured at baseline dfdf36b24a473b7b530d790ab18b46adafe7b3c8:

* ``test_concurrent_writer_fails_closed`` failed with
  ``AssertionError: False is not true : baseline has no exclusive writer lock helper``.
* An exception injected after the first denominator shard write failed with
  ``prior generation changed after injected write failure``.  The two old
  shards ``{p001-p040, p041-p080}`` became only a partially written
  ``p001-p040`` shard, proving both overwrite and prior-state loss.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import largelexicon_common as common


class SimulatedProcessCrash(BaseException):
    """Bypass ordinary exception recovery to model termination between renames."""


def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def sample_generations() -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    old = {
        "p001-p040.jsonl": [{"row_id": "old-1", "value": 1}],
        "p041-p080.jsonl": [{"row_id": "old-2", "value": 2}],
    }
    new = {
        "p001-p040.jsonl": [
            {"row_id": "new-1", "value": 10},
            {"row_id": "new-2", "value": 20},
        ],
        "p081-p100.jsonl": [{"row_id": "new-3", "value": 30}],
    }
    return old, new


class AtomicPromotionTests(unittest.TestCase):
    def seed_legacy(self, target: Path, shards: dict[str, list[dict[str, object]]]) -> None:
        target.mkdir(parents=True)
        for name, rows in shards.items():
            common.write_jsonl(target / name, rows)

    def promote(self, target: Path, shards: dict[str, list[dict[str, object]]], **kwargs: object) -> dict[str, object]:
        return common.atomic_promote_shards(
            target,
            shards,
            writer_id="rm19-test-writer",
            promoted_at="2026-07-11T00:00:00Z",
            **kwargs,
        )

    def test_kill_mid_write_preserves_current_and_releases_lock(self) -> None:
        old, new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "qword-denominator"
            self.seed_legacy(target, old)
            before = snapshot(target)
            written = 0

            def fail_after_two_rows(_path: Path, _row: dict[str, object]) -> None:
                nonlocal written
                written += 1
                if written == 2:
                    raise RuntimeError("simulated mid-write failure")

            with self.assertRaisesRegex(RuntimeError, "simulated mid-write"):
                self.promote(target, new, after_row=fail_after_two_rows)

            self.assertEqual(before, snapshot(target))
            self.assertFalse(common.writer_lock_path(target).exists())
            self.assertFalse(list(target.parent.glob(f"{target.name}.staging-*")))

    def test_denominator_writer_uses_atomic_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "qword-denominator"
            self.seed_legacy(target, {"p001-p040.jsonl": [{"old": 1}], "p041-p080.jsonl": [{"old": 2}]})
            before = snapshot(target)
            seen = 0

            def fail_after_one(_path: Path, _row: dict[str, object]) -> None:
                nonlocal seen
                seen += 1
                if seen == 2:
                    raise RuntimeError("denominator injection")

            patched = {
                "ROOT": root,
                "QWORD_DENOMINATOR_FULL": root / "denominator.full.jsonl",
                "QWORD_DENOMINATOR_SHARD_DIR": target,
                "QWORD_DENOMINATOR_MANIFEST": root / "denominator.manifest.json",
                "QWORD_DENOMINATOR_ENTRY_INDEX": root / "denominator.entry-index.json",
                "QWORD_DENOMINATOR_SOURCE_REPAIR": root / "denominator.repairs.json",
            }
            rows = [
                {"row_id": "new-1", "entry_id": "a", "source_keys": ["p001"]},
                {"row_id": "new-2", "entry_id": "b", "source_keys": ["p041"]},
            ]
            with mock.patch.multiple(common, **patched):
                with self.assertRaisesRegex(RuntimeError, "denominator injection"):
                    common.write_qword_denominator_shards(rows, _after_row=fail_after_one)
            self.assertEqual(before, snapshot(target))

    def test_concurrent_writer_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "qword-crosswalk"
            with common.exclusive_writer_lock(target, writer_id="first"):
                with self.assertRaises(common.WriterLockError) as caught:
                    with common.exclusive_writer_lock(target, writer_id="second"):
                        self.fail("second writer acquired the lock")
            message = str(caught.exception)
            self.assertIn("writer lock exists", message)
            self.assertIn("fails closed", message)

    def test_successful_promotion_manifest_and_prior_bytes(self) -> None:
        old, new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "qword-crosswalk"
            self.seed_legacy(target, old)
            old_bytes = snapshot(target)
            generation = self.promote(target, new)

            self.assertEqual(old_bytes, snapshot(common.previous_generation_path(target)))
            verified = common.verify_generation(target, allow_legacy=False)
            self.assertTrue(verified["ok"], verified)
            self.assertEqual(3, generation["row_count"])
            for shard in generation["shards"]:
                path = target / shard["path"]
                self.assertEqual(common.sha256_file(path), shard["sha256"])

    def test_mixed_generation_is_rejected(self) -> None:
        _old, new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "qword-crosswalk"
            self.promote(target, new)
            with (target / "p001-p040.jsonl").open("ab") as handle:
                handle.write(b'{"corrupt":true}\n')
            verified = common.verify_generation(target, allow_legacy=False)
            self.assertFalse(verified["ok"])
            self.assertTrue(any("sha256 mismatch" in error for error in verified["errors"]))

    def test_rollback_restores_prior_bytes_exactly(self) -> None:
        old, new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "qword-crosswalk"
            self.seed_legacy(target, old)
            old_bytes = snapshot(target)
            self.promote(target, new)
            common.rollback_generation(target, writer_id="rm19-test-rollback")
            self.assertEqual(old_bytes, snapshot(target))

    def test_crash_between_renames_has_deterministic_recovery(self) -> None:
        old, new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "qword-crosswalk"
            self.seed_legacy(target, old)
            old_bytes = snapshot(target)

            def crash() -> None:
                raise SimulatedProcessCrash("between directory renames")

            with self.assertRaises(SimulatedProcessCrash):
                self.promote(target, new, after_current_to_previous=crash)
            self.assertFalse(target.exists())
            self.assertTrue(common.previous_generation_path(target).exists())

            outcome = common.recover_generation(target, writer_id="rm19-test-recovery")
            self.assertEqual("restored_previous", outcome["action"])
            self.assertEqual(old_bytes, snapshot(target))
            self.assertFalse(list(target.parent.glob(f"{target.name}.staging-*")))

    def test_deterministic_generation_bytes(self) -> None:
        _old, new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "first"
            second = Path(td) / "second"
            first_manifest = self.promote(first, new)
            second_manifest = common.atomic_promote_shards(
                second,
                new,
                writer_id="different-writer",
                promoted_at="2030-01-01T00:00:00Z",
            )
            for name in new:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            for manifest in (first_manifest, second_manifest):
                manifest.pop("writer_id")
                manifest.pop("promoted_at")
            self.assertEqual(first_manifest, second_manifest)

    def test_legacy_generation_without_sidecar_is_tolerated(self) -> None:
        old, _new = sample_generations()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "legacy"
            self.seed_legacy(target, old)
            result = common.verify_generation(target)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["legacy"])


def main() -> int:
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AtomicPromotionTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if result.wasSuccessful():
        return 0
    print(stream.getvalue(), end="")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
