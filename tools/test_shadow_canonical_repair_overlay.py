#!/usr/bin/env python3
"""Regression tests for registry-driven canonical repair SHADOW overlays."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import compile_canonical_hover_whitelist_packet as compile_mod  # noqa: E402
from tools import run_shadow_compile as shadow  # noqa: E402


REGISTRY = ROOT / "qamus" / "indexes" / "largelexicon" / "canonical-repairs.json"
RM20 = ROOT / "qamus" / "indexes" / "largelexicon" / "canonical-hover-shadow-rm20"
RM20_PREV = RM20.with_name(RM20.name + ".prev")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def canonical_bytes(rows: list[dict]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


class CanonicalRepairOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payloads = shadow.read_jsonl(str(RM20 / "canonical_payloads.jsonl"))
        self.bindings = shadow.read_jsonl(str(RM20 / "occurrence_bindings.jsonl"))
        self.old_payloads = shadow.read_jsonl(str(RM20_PREV / "canonical_payloads.jsonl"))
        self.old_bindings = shadow.read_jsonl(str(RM20_PREV / "occurrence_bindings.jsonl"))
        self.binding_keys = {
            (row["canonical_wbw_loc"], row["qword_row_id"]) for row in self.bindings
        }

    def _crosswalk_fixture(self, directory: Path) -> str:
        rows = []
        for path in sorted(
            (ROOT / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk").glob("*.jsonl")
        ):
            for row in shadow.read_jsonl(str(path)):
                key = (row.get("canonical_wbw_loc"), row.get("qword_row_id"))
                unresolved_repair = (
                    row.get("qword_row_id")
                    in {binding["qword_row_id"] for binding in self.bindings}
                )
                if key in self.binding_keys or unresolved_repair:
                    rows.append(row)
        self.assertEqual(26, len(rows))
        path = directory / "crosswalk.jsonl"
        write_jsonl(path, rows)
        return str(path)

    def _baseline(self, directory: Path) -> tuple[Path, dict[str, dict]]:
        baseline, _noops, conflicts, _report = compile_mod.compile_packet(
            self.old_payloads, self.old_bindings, [], []
        )
        self.assertFalse(conflicts)
        self.assertEqual(11, len(baseline))
        path = directory / "baseline.jsonl"
        write_jsonl(path, baseline)
        by_loc = {
            compile_mod.canonical_public_loc(row): row for row in baseline
        }
        return path, by_loc

    def test_absent_registry_preserves_today_input_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-repair-none-") as temporary:
            root = Path(temporary)
            crosswalk = self._crosswalk_fixture(root)
            _baseline, live_by_loc = self._baseline(root)
            rows, _shared, _pending = shadow.construct_input_rows(
                str(ROOT), live_by_loc, compile_mod.public_content,
                compile_mod.canonical_public_loc, crosswalk_glob=crosswalk,
            )
            overlay = shadow.load_canonical_repair_overlay(
                str(ROOT), registry_path=str(root / "missing-registry.json")
            )
            actual, stats = shadow.apply_canonical_repair_overlay(
                rows, overlay, compile_mod.canonical_public_loc,
                crosswalk_glob=crosswalk,
            )
            self.assertEqual(canonical_bytes(rows), canonical_bytes(actual))
            self.assertEqual(0, stats["overlaid_bindings"])

    def test_rm20_registry_changes_exactly_11_locations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-repair-rm20-") as temporary:
            root = Path(temporary)
            crosswalk = self._crosswalk_fixture(root)
            baseline_path, live_by_loc = self._baseline(root)
            rows, _shared, _pending = shadow.construct_input_rows(
                str(ROOT), live_by_loc, compile_mod.public_content,
                compile_mod.canonical_public_loc, crosswalk_glob=crosswalk,
            )
            overlay = shadow.load_canonical_repair_overlay(
                str(ROOT), registry_path=str(REGISTRY)
            )
            actual, stats = shadow.apply_canonical_repair_overlay(
                rows, overlay, compile_mod.canonical_public_loc,
                crosswalk_glob=crosswalk,
            )
            self.assertNotEqual(
                hashlib.sha256(canonical_bytes(rows)).hexdigest(),
                hashlib.sha256(canonical_bytes(actual)).hexdigest(),
            )
            expected_locations = set(
                json.loads(
                    (ROOT / "prep" / "morphline-approved-manifest.json").read_text(
                        encoding="utf-8"
                    )
                )["predeclared_shadow_delta"]["expected_modify_locations"]
            )
            changed = {
                (row["canonical_wbw_loc"], row["qword_row_id"])
                for row in actual
                if row.get("public_payload", {}).get("morphline_repair_wave") == "RM-20"
            }
            self.assertEqual(self.binding_keys, changed)
            self.assertEqual(expected_locations, {loc for loc, _qid in changed})
            self.assertEqual(26, stats["overlaid_bindings"])
            self.assertEqual(1, stats["added_bindings"])
            workdir = root / "run"
            workdir.mkdir()
            _report, summary, sha_a, sha_b, paths = shadow.run_pipeline(
                str(ROOT), actual, str(baseline_path), str(workdir), 25
            )
            self.assertEqual(sha_a, sha_b)
            counts = summary["classifications"]
            self.assertEqual(11, counts["modify"]["count"])
            self.assertEqual(0, counts["no_op"]["count"])
            self.assertEqual(0, counts["append"]["count"])
            self.assertEqual(0, counts["remove_or_unrepresented"]["count"])
            self.assertEqual(0, paths["build_conflicts"])
            rowdiff = shadow.read_jsonl(str(workdir / "g8-rowdiff.jsonl"))
            self.assertEqual(
                expected_locations,
                {
                    row["canonical_wbw_loc"]
                    for row in rowdiff
                    if row["classification"] == "modify"
                },
            )

            records = root / "records"
            exit_code = shadow.shadow_run(
                {
                    "repo_root": str(ROOT),
                    "records_dir": str(records),
                    "live_whitelist": str(baseline_path),
                    "expected_source_head": None,
                    "leak_local_overlay": None,
                    "sample_size": 25,
                    "keep_rowdiff_runs": 8,
                    "snapshot_every": 0,
                    "crosswalk_glob": crosswalk,
                }
            )
            self.assertEqual(1, exit_code)  # the standing modify alert remains intentional
            record_path = next(records.glob("run-*/record.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(overlay["registry_sha256"], record["canonical_repair_registry_sha256"])
            self.assertEqual(overlay["generations"], record["canonical_repair_generations"])
            ledger = shadow.read_jsonl(str(records / "shadow-ledger.jsonl"))[-1]
            self.assertEqual(overlay["registry_sha256"], ledger["canonical_repair_registry_sha256"])
            self.assertEqual(overlay["generations"], ledger["canonical_repair_generations"])

    def test_missing_generation_is_a_hard_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-repair-invalid-") as temporary:
            registry = Path(temporary) / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "schema": "qamus.canonical_repair_registry.v1",
                        "active_repairs": [
                            {
                                "table": "qamus/indexes/largelexicon/does-not-exist",
                                "generation_id": "sha256:" + "0" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(shadow.CanonicalRepairError):
                shadow.load_canonical_repair_overlay(
                    str(ROOT), registry_path=str(registry)
                )

            registry.write_text(
                json.dumps(
                    {
                        "schema": "qamus.canonical_repair_registry.v1",
                        "active_repairs": [
                            {
                                "table": "qamus/indexes/largelexicon/canonical-hover-shadow-rm20",
                                "generation_id": "sha256:" + "0" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(shadow.CanonicalRepairError):
                shadow.load_canonical_repair_overlay(
                    str(ROOT), registry_path=str(registry)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
