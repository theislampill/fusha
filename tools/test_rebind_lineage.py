#!/usr/bin/env python3
"""Regression tests for the RM-20 canonical-hover dry-run rebind tool."""
from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import rebind_canonical_hover as rebind
from tools.validate_canonical_hover_payload_table import binding_id, payload_id


def payload(gloss: str = "the book") -> dict:
    row = {
        "schema": "qamus.canonical_hover_payload.v2",
        "payload_family": "source_address_exact",
        "surface_norm": "الكتاب",
        "root": "كتب",
        "lemma_id": None,
        "lemma_status": "missing",
        "pos": "noun",
        "pattern": "فِعال",
        "sarf_certification": "candidate",
        "nahw_certification": "missing",
        "public_payload": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "token_contribution_gloss": gloss,
            "contextual_phrase_gloss": None,
            "morphline": "ART+STEM",
            "segments": [
                {"role": "ART", "surface": "ال", "qg_class": "definite_article", "gloss": "the"},
                {"role": "STEM", "surface": "كتاب", "qg_class": "noun", "gloss": "book"},
            ],
            "learner_explanation": "definite article + noun",
        },
    }
    row["canonical_payload_id"] = payload_id(row)
    return row


def binding(pid: str, suffix: str) -> dict:
    row = {
        "schema": "qamus.canonical_hover_occurrence_binding.v2",
        "canonical_payload_id": pid,
        "entry_id": "n0030",
        "entry_url": None,
        "source_key": "qamus",
        "sense_index": 1,
        "card_index": 0,
        "card_id": "n0030:u1:e" + suffix,
        "qword_row_id": "q" + suffix,
        "source_dependency_sha256": suffix * 64,
        "visible_surface": "الكتاب",
        "canonical_quran_loc": "2:2:" + suffix,
        "canonical_wbw_loc": "2:2:" + suffix,
        "exact_transclusion_group_key": "quran:2:2:" + suffix + "|الكتاب",
        "binding_status": "accepted",
        "binding_gate": "source_address_exact",
        "reason": "source_address_exact_ok",
        "exception_id": None,
    }
    row["binding_id"] = binding_id(row)
    return row


def read_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


class RebindLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = payload()
        self.new = payload("the written book")
        self.bindings = [
            binding(self.old["canonical_payload_id"], "1"),
            binding(self.old["canonical_payload_id"], "2"),
        ]

    def report(self) -> dict:
        return rebind.build_rebind_report(
            [self.old], self.bindings, self.old["canonical_payload_id"], self.new
        )

    def test_build_report_enumerates_all_dependents_deterministically(self) -> None:
        report = self.report()
        self.assertEqual(report["schema"], "qamus.canonical_hover_rebind_report.v1")
        self.assertEqual(report["mode"], "dry_run")
        self.assertEqual(report["summary"]["dependent_bindings"], 2)
        self.assertEqual(
            [item["old_binding"]["binding_id"] for item in report["binding_rebinds"]],
            sorted(row["binding_id"] for row in self.bindings),
        )
        self.assertEqual(report, self.report())

    def test_replacement_ids_and_edges_use_existing_content_address_apis(self) -> None:
        report = self.report()
        self.assertEqual(report["new_payload"]["canonical_payload_id"], payload_id(self.new))
        self.assertEqual(
            report["payload_edge"],
            {
                "canonical_payload_id": self.new["canonical_payload_id"],
                "supersedes": self.old["canonical_payload_id"],
            },
        )
        for item in report["binding_rebinds"]:
            self.assertEqual(item["new_binding"]["binding_id"], binding_id(item["new_binding"]))
            self.assertEqual(item["new_binding"]["supersedes"], item["old_binding"]["binding_id"])

    def test_verify_fails_when_report_omits_a_dependent(self) -> None:
        report = self.report()
        report["binding_rebinds"].pop()
        errors = rebind.verify_dataset([self.old], self.bindings, report)
        self.assertTrue(any("missing dependent" in error for error in errors), errors)

    def test_verify_flags_superseded_payload_without_tombstone_conflict(self) -> None:
        report = self.report()
        report["conflicts"].pop()
        errors = rebind.verify_dataset([self.old], self.bindings, report)
        self.assertTrue(any("live payload or explicit tombstone conflict" in error for error in errors), errors)

    def test_verify_detects_broken_binding_supersedes_chain(self) -> None:
        report = self.report()
        report["binding_rebinds"][0]["new_binding"].pop("supersedes")
        errors = rebind.verify_dataset([self.old], self.bindings, report)
        self.assertTrue(any("supersedes edge" in error for error in errors), errors)

    def test_lineage_is_traversable_in_both_directions(self) -> None:
        forward, reverse = rebind.lineage_maps(self.report())
        old_pid = self.old["canonical_payload_id"]
        new_pid = self.new["canonical_payload_id"]
        self.assertEqual(forward[old_pid], new_pid)
        self.assertEqual(reverse[new_pid], old_pid)
        for old_binding in self.bindings:
            new_binding = forward[old_binding["binding_id"]]
            self.assertEqual(reverse[new_binding], old_binding["binding_id"])

    def test_verify_accepts_live_payload_or_matching_tombstone_conflict(self) -> None:
        self.assertEqual(rebind.verify_dataset([self.old], self.bindings, self.report()), [])
        self.assertEqual(rebind.verify_dataset([self.old], self.bindings), [])

    def test_build_rejects_wrong_new_payload_id(self) -> None:
        bad = copy.deepcopy(self.new)
        bad["canonical_payload_id"] = "chp:0000000000000000"
        with self.assertRaisesRegex(ValueError, "content-addressed"):
            rebind.build_rebind_report(
                [self.old], self.bindings, self.old["canonical_payload_id"], bad
            )

    def test_cli_writes_pretty_report_and_verify_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payloads_path = os.path.join(directory, "payloads.jsonl")
            bindings_path = os.path.join(directory, "bindings.jsonl")
            new_path = os.path.join(directory, "new.json")
            report_path = os.path.join(directory, "report.json")
            for path, rows in ((payloads_path, [self.old]), (bindings_path, self.bindings)):
                with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            with io.open(new_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(self.new, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")

            create = subprocess.run(
                [sys.executable, os.path.join(ROOT, "tools", "rebind_canonical_hover.py"),
                 "--payloads", payloads_path, "--bindings", bindings_path,
                 "--old-payload-id", self.old["canonical_payload_id"],
                 "--new-payload", new_path, "--out", report_path],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(create.returncode, 0, create.stdout + create.stderr)
            before = {path: read_bytes(path) for path in (payloads_path, bindings_path, report_path)}
            verify = subprocess.run(
                [sys.executable, os.path.join(ROOT, "tools", "rebind_canonical_hover.py"),
                 "--verify", "--payloads", payloads_path, "--bindings", bindings_path,
                 "--report", report_path],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )
            after = {path: read_bytes(path) for path in before}
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(before, after)
            self.assertIn("\n  \"", before[report_path].decode("utf-8"))
            self.assertTrue(before[report_path].endswith(b"\n"))

    def test_cli_refuses_to_overwrite_any_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payloads_path = os.path.join(directory, "payloads.jsonl")
            bindings_path = os.path.join(directory, "bindings.jsonl")
            new_path = os.path.join(directory, "new.json")
            with io.open(payloads_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self.old, ensure_ascii=False, sort_keys=True) + "\n")
            with io.open(bindings_path, "w", encoding="utf-8", newline="\n") as handle:
                for row in self.bindings:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            with io.open(new_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(self.new, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
            before = read_bytes(payloads_path)

            run = subprocess.run(
                [sys.executable, os.path.join(ROOT, "tools", "rebind_canonical_hover.py"),
                 "--payloads", payloads_path, "--bindings", bindings_path,
                 "--old-payload-id", self.old["canonical_payload_id"],
                 "--new-payload", new_path, "--out", payloads_path],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )

            self.assertNotEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(read_bytes(payloads_path), before)


if __name__ == "__main__":
    unittest.main()
