#!/usr/bin/env python3
"""Focused tests for tranche-001 Line 4 hostile error fixtures, batch B1 (Sarf: derivation/inflection/paradigms).

Pins the 17 source queue rows named by this worker's private pointer manifest
(batch-b1-pointer-manifest.json, schema private.t1_error_fixture_batch_b1_pointer_manifest.v1) against the
COMMITTED public evidence those rows must reverse-trace to: curriculum/l1l6/reports/queues/q-error-fixtures.jsonl
(lesson/domain), curriculum/l1l6/qualification/*.jsonl (per-lesson qualification), and
curriculum/l1l6/misconceptions/misconception-registry.jsonl (per-misconception manifestation/unit linkage).

This batch continues batch A (tools/test_tranche_001_error_fixtures.py) without touching its truth: batch A's
sarf bank (sarf/evals/tranche-001-error-fixtures-a.jsonl) and the first 50 rows of the shared trace
(curriculum/l1l6/reports/mistake-pattern-fixtures.jsonl) must stay exactly as committed; only 17 new trace rows
may be appended (67 unique covered queue rows total) and only the shared meta file's counts may move to record
that append. Every new row must be honestly runner_loaded_fixture_only / behaviorally_decided=false / not
certified — the same disposition batch A already carries, verified through the SAME real
tools/run_sarf_evals.py interfaces (load_contract/bank_spec/load_bank/validate_contract/Consumers.real/ADAPTERS),
never a reimplementation of them.

Red-first: this must fail until sarf/evals/tranche-001-error-fixtures-b1.jsonl exists with exactly 17 rows, the
17 matching trace rows are appended, the shared meta counts are updated, and tools/run_sarf_evals.py registers a
fixture_only contract row for the new bank.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

QUEUE = _REPO / "curriculum" / "l1l6" / "reports" / "queues" / "q-error-fixtures.jsonl"
MISCONCEPTIONS = _REPO / "curriculum" / "l1l6" / "misconceptions" / "misconception-registry.jsonl"
TRACE = _REPO / "curriculum" / "l1l6" / "reports" / "mistake-pattern-fixtures.jsonl"
TRACE_META = _REPO / "curriculum" / "l1l6" / "reports" / "mistake-pattern-fixtures.meta.json"
SARF_BANK_A = _REPO / "sarf" / "evals" / "tranche-001-error-fixtures-a.jsonl"
NAHW_BANK_A = _REPO / "nahw" / "evals" / "tranche-001-error-fixtures-a.jsonl"
SARF_BANK_B1 = _REPO / "sarf" / "evals" / "tranche-001-error-fixtures-b1.jsonl"
SARF_BANK_B1_REL = "sarf/evals/tranche-001-error-fixtures-b1.jsonl"

# ---------------------------------------------------------------------------
# the 17 source rows this worker's private pointer manifest names — structural IDs/links only (row ids, lesson
# ids, domain names, unit links, misconception ids), never private prose. Every field below is independently
# re-verified against COMMITTED public evidence by ManifestSourceTruthTests.
# ---------------------------------------------------------------------------
MANIFEST_ROWS = [
    {"source_queue_row_id": "q-error-fixtures-0091", "lesson_id": "L4.M1.01",
     "qualification_path": "curriculum/l1l6/qualification/L4M1.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s01", "u-s06"],
     "misconception_ids": ["mc-0119", "mc-0129", "mc-0242", "mc-0592"]},
    {"source_queue_row_id": "q-error-fixtures-0092", "lesson_id": "L4.M1.02",
     "qualification_path": "curriculum/l1l6/qualification/L4M1.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-n01", "u-s06"],
     "misconception_ids": ["mc-0234", "mc-0278", "mc-0353", "mc-0891"]},
    {"source_queue_row_id": "q-error-fixtures-0095", "lesson_id": "L4.M1.05",
     "qualification_path": "curriculum/l1l6/qualification/L4M1.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s06"],
     "misconception_ids": ["mc-0173", "mc-0278", "mc-0354", "mc-0654", "mc-0898"]},
    {"source_queue_row_id": "q-error-fixtures-0096", "lesson_id": "L4.M1.06",
     "qualification_path": "curriculum/l1l6/qualification/L4M1.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0031", "mc-0251", "mc-0348", "mc-0398", "mc-0422"]},
    {"source_queue_row_id": "q-error-fixtures-0098", "lesson_id": "L4.M2.01",
     "qualification_path": "curriculum/l1l6/qualification/L4M2.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0056", "mc-0322", "mc-0378", "mc-0512", "mc-0563"]},
    {"source_queue_row_id": "q-error-fixtures-0111", "lesson_id": "L4.M3.07",
     "qualification_path": "curriculum/l1l6/qualification/L4M3.jsonl", "target_domain": "inflection",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0193", "mc-0257", "mc-0435", "mc-0436", "mc-0904"]},
    {"source_queue_row_id": "q-error-fixtures-0151", "lesson_id": "L5.M4.02",
     "qualification_path": "curriculum/l1l6/qualification/L5M4.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s06"],
     "misconception_ids": ["mc-0039", "mc-0245", "mc-0612", "mc-0712"]},
    {"source_queue_row_id": "q-error-fixtures-0153", "lesson_id": "L5.M4.04",
     "qualification_path": "curriculum/l1l6/qualification/L5M4.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s01"],
     "misconception_ids": ["mc-0061", "mc-0182", "mc-0208", "mc-0666"]},
    {"source_queue_row_id": "q-error-fixtures-0154", "lesson_id": "L5.M4.05",
     "qualification_path": "curriculum/l1l6/qualification/L5M4.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s01", "u-s06"],
     "misconception_ids": ["mc-0117", "mc-0364", "mc-0773", "mc-0782"]},
    {"source_queue_row_id": "q-error-fixtures-0155", "lesson_id": "L5.M4.06",
     "qualification_path": "curriculum/l1l6/qualification/L5M4.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s01"],
     "misconception_ids": ["mc-0013", "mc-0212", "mc-0300", "mc-0492"]},
    {"source_queue_row_id": "q-error-fixtures-0158", "lesson_id": "L5.M5.02",
     "qualification_path": "curriculum/l1l6/qualification/L5M5.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0171", "mc-0433", "mc-0473", "mc-0630"]},
    {"source_queue_row_id": "q-error-fixtures-0181", "lesson_id": "L6.M3.03",
     "qualification_path": "curriculum/l1l6/qualification/L6M3.jsonl", "target_domain": "inflection",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0022", "mc-0337", "mc-0389", "mc-0801"]},
    {"source_queue_row_id": "q-error-fixtures-0185", "lesson_id": "L6.M3.07",
     "qualification_path": "curriculum/l1l6/qualification/L6M3.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s06"],
     "misconception_ids": ["mc-0452", "mc-0506", "mc-0574", "mc-0794", "mc-0887"]},
    {"source_queue_row_id": "q-error-fixtures-0192", "lesson_id": "L6.M4.06",
     "qualification_path": "curriculum/l1l6/qualification/L6M4.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0006", "mc-0052", "mc-0591", "mc-0763"]},
    {"source_queue_row_id": "q-error-fixtures-0194", "lesson_id": "L6.M5.02",
     "qualification_path": "curriculum/l1l6/qualification/L6M5.jsonl", "target_domain": "paradigms",
     "selected_unit_links": ["u-s06"],
     "misconception_ids": ["mc-0188", "mc-0244", "mc-0500", "mc-0743", "mc-0888"]},
    {"source_queue_row_id": "q-error-fixtures-0197", "lesson_id": "L6.M5.05",
     "qualification_path": "curriculum/l1l6/qualification/L6M5.jsonl", "target_domain": "derivation",
     "selected_unit_links": ["u-s01"],
     "misconception_ids": ["mc-0030", "mc-0073", "mc-0175", "mc-0699"]},
    {"source_queue_row_id": "q-error-fixtures-0203", "lesson_id": "L6.M6.03",
     "qualification_path": "curriculum/l1l6/qualification/L6M6.jsonl", "target_domain": "paradigms",
     "selected_unit_links": ["u-n01"],
     "misconception_ids": ["mc-0064", "mc-0179", "mc-0615", "mc-0756", "mc-0832"]},
]
MANIFEST_BY_ROW = {r["source_queue_row_id"]: r for r in MANIFEST_ROWS}
MANIFEST_ROW_IDS = [r["source_queue_row_id"] for r in MANIFEST_ROWS]

# ---------------------------------------------------------------------------
# batch A's committed 50-row trace prefix, compactly pinned (row_id, source_queue_row_id, source_lesson,
# runner_flag, fixture_id, misconception_ids_checked) — "s"=sarf runner/bank, "n"=naḥw runner/bank. Used to prove
# batch A is never mutated when the B1 rows are appended, and cross-checked directly against the live
# sarf/naḥw bank files (never a duplicated content snapshot of those banks).
# ---------------------------------------------------------------------------
_RUNNER = {
    "s": ("tools/run_sarf_evals.py", "sarf/evals/tranche-001-error-fixtures-a.jsonl"),
    "n": ("tools/run_nahw_evals.py", "nahw/evals/tranche-001-error-fixtures-a.jsonl"),
}
EXPECTED_BATCH_A_TRACE_PREFIX = [
    ("trf-a-trace-0001", "q-error-fixtures-0000", "L1.M1.01", "s", "trf-a-sarf-0046", ("mc-0587",)),
    ("trf-a-trace-0002", "q-error-fixtures-0001", "L1.M1.02", "s", "trf-a-sarf-0001", ("mc-0099",)),
    ("trf-a-trace-0003", "q-error-fixtures-0002", "L1.M1.03", "s", "trf-a-sarf-0047", ("mc-0328",)),
    ("trf-a-trace-0004", "q-error-fixtures-0003", "L1.M1.04", "s", "trf-a-sarf-0048", ("mc-0329",)),
    ("trf-a-trace-0005", "q-error-fixtures-0004", "L1.M1.05", "s", "trf-a-sarf-0002", ("mc-0559",)),
    ("trf-a-trace-0006", "q-error-fixtures-0005", "L1.M1.06", "s", "trf-a-sarf-0003", ("mc-0169",)),
    ("trf-a-trace-0007", "q-error-fixtures-0006", "L1.M1.07", "s", "trf-a-sarf-0004", ("mc-0003",)),
    ("trf-a-trace-0008", "q-error-fixtures-0007", "L1.M1.08", "s", "trf-a-sarf-0005", ("mc-0012",)),
    ("trf-a-trace-0009", "q-error-fixtures-0011", "L1.M2.03", "s", "trf-a-sarf-0006", ("mc-0016",)),
    ("trf-a-trace-0010", "q-error-fixtures-0014", "L1.M2.08", "s", "trf-a-sarf-0007", ("mc-0074",)),
    ("trf-a-trace-0011", "q-error-fixtures-0015", "L1.M3.05", "s", "trf-a-sarf-0008", ("mc-0045",)),
    ("trf-a-trace-0012", "q-error-fixtures-0017", "L1.M5.01", "s", "trf-a-sarf-0009", ("mc-0315",)),
    ("trf-a-trace-0013", "q-error-fixtures-0019", "L1.M5.03", "s", "trf-a-sarf-0010", ("mc-0489",)),
    ("trf-a-trace-0014", "q-error-fixtures-0020", "L1.M5.04", "s", "trf-a-sarf-0011", ("mc-0401",)),
    ("trf-a-trace-0015", "q-error-fixtures-0021", "L1.M5.05", "s", "trf-a-sarf-0012", ("mc-0527",)),
    ("trf-a-trace-0016", "q-error-fixtures-0022", "L1.M5.06", "s", "trf-a-sarf-0013", ("mc-0164",)),
    ("trf-a-trace-0017", "q-error-fixtures-0023", "L1.M5.07", "s", "trf-a-sarf-0014", ("mc-0198",)),
    ("trf-a-trace-0018", "q-error-fixtures-0024", "L2.M1.01", "s", "trf-a-sarf-0015", ("mc-0060",)),
    ("trf-a-trace-0019", "q-error-fixtures-0025", "L2.M1.02", "s", "trf-a-sarf-0016", ("mc-0363",)),
    ("trf-a-trace-0020", "q-error-fixtures-0026", "L2.M1.03", "s", "trf-a-sarf-0017", ("mc-0038",)),
    ("trf-a-trace-0021", "q-error-fixtures-0027", "L2.M1.04", "s", "trf-a-sarf-0018", ("mc-0367",)),
    ("trf-a-trace-0022", "q-error-fixtures-0028", "L2.M1.05", "s", "trf-a-sarf-0019", ("mc-0366",)),
    ("trf-a-trace-0023", "q-error-fixtures-0029", "L2.M1.06", "s", "trf-a-sarf-0020", ("mc-0274",)),
    ("trf-a-trace-0024", "q-error-fixtures-0030", "L2.M1.07", "s", "trf-a-sarf-0021", ("mc-0055",)),
    ("trf-a-trace-0025", "q-error-fixtures-0031", "L2.M1.08", "s", "trf-a-sarf-0022", ("mc-0259",)),
    ("trf-a-trace-0026", "q-error-fixtures-0032", "L2.M2.01", "s", "trf-a-sarf-0023", ("mc-0114",)),
    ("trf-a-trace-0027", "q-error-fixtures-0033", "L2.M2.02", "s", "trf-a-sarf-0024", ("mc-0191",)),
    ("trf-a-trace-0028", "q-error-fixtures-0037", "L2.M2.06", "s", "trf-a-sarf-0025", ("mc-0018",)),
    ("trf-a-trace-0029", "q-error-fixtures-0038", "L2.M3.01", "s", "trf-a-sarf-0026", ("mc-0207",)),
    ("trf-a-trace-0030", "q-error-fixtures-0040", "L2.M3.03", "s", "trf-a-sarf-0027", ("mc-0430",)),
    ("trf-a-trace-0031", "q-error-fixtures-0041", "L2.M3.04", "s", "trf-a-sarf-0028", ("mc-0036",)),
    ("trf-a-trace-0032", "q-error-fixtures-0042", "L2.M3.05", "s", "trf-a-sarf-0029", ("mc-0269",)),
    ("trf-a-trace-0033", "q-error-fixtures-0043", "L2.M3.06", "s", "trf-a-sarf-0030", ("mc-0023",)),
    ("trf-a-trace-0034", "q-error-fixtures-0045", "L2.M4.01", "s", "trf-a-sarf-0031", ("mc-0034",)),
    ("trf-a-trace-0035", "q-error-fixtures-0047", "L2.M4.04", "s", "trf-a-sarf-0032", ("mc-0539",)),
    ("trf-a-trace-0036", "q-error-fixtures-0048", "L2.M4.05", "n", "trf-a-nahw-0001", ("mc-0109",)),
    ("trf-a-trace-0037", "q-error-fixtures-0049", "L2.M5.01", "s", "trf-a-sarf-0033", ("mc-0001",)),
    ("trf-a-trace-0038", "q-error-fixtures-0050", "L2.M5.02", "s", "trf-a-sarf-0034", ("mc-0264",)),
    ("trf-a-trace-0039", "q-error-fixtures-0051", "L2.M5.03", "s", "trf-a-sarf-0035", ("mc-0215",)),
    ("trf-a-trace-0040", "q-error-fixtures-0054", "L3.M1.01", "s", "trf-a-sarf-0036", ("mc-0220",)),
    ("trf-a-trace-0041", "q-error-fixtures-0057", "L3.M1.04", "s", "trf-a-sarf-0037", ("mc-0204",)),
    ("trf-a-trace-0042", "q-error-fixtures-0060", "L3.M1.07", "s", "trf-a-sarf-0038", ("mc-0122",)),
    ("trf-a-trace-0043", "q-error-fixtures-0061", "L3.M1.08", "s", "trf-a-sarf-0039", ("mc-0205",)),
    ("trf-a-trace-0044", "q-error-fixtures-0062", "L3.M1.09", "s", "trf-a-sarf-0040", ("mc-0158",)),
    ("trf-a-trace-0045", "q-error-fixtures-0071", "L3.M3.03", "s", "trf-a-sarf-0041", ("mc-0010",)),
    ("trf-a-trace-0046", "q-error-fixtures-0074", "L3.M3.06", "s", "trf-a-sarf-0042", ("mc-0200",)),
    ("trf-a-trace-0047", "q-error-fixtures-0080", "L3.M4.04", "s", "trf-a-sarf-0043", ("mc-0258",)),
    ("trf-a-trace-0048", "q-error-fixtures-0084", "L3.M4.08", "s", "trf-a-sarf-0044", ("mc-0142",)),
    ("trf-a-trace-0049", "q-error-fixtures-0085", "L3.M5.01", "n", "trf-a-nahw-0002", ("mc-0449",)),
    ("trf-a-trace-0050", "q-error-fixtures-0086", "L3.M5.02", "s", "trf-a-sarf-0045", ("mc-0471",)),
]

ANTI_LLM_BOUNDARIES = {"correct_conclusion_wrong_reason", "surface_shape_alone_cannot_promote",
                       "swallowed_boundary_fails", "missing_evidence_abstains", "candidate_never_certified",
                       "ambiguous_rivals_preserved"}
FORBIDDEN_OUTCOME_SUBSTRINGS = ("executable", "behaviorally_closed", "certified", "decided_by_consumer")
FORBIDDEN_PROMOTION_KEYS = {"root", "pattern", "sense", "meaning", "translation", "lexeme", "gloss", "function"}
FORBIDDEN_LEAKAGE_SUBSTRINGS = ("_private", "pointer-manifest", "source_manifest", "batch-b1-pointer-manifest",
                                "qualification_path", "expected_decision", "qamus_source_card", ":\\\\", "C:\\\\")
B1_TRACE_ROW_ID_RE = re.compile(r"^trf-b1-trace-\d{4}$")
B1_FIXTURE_ID_RE = re.compile(r"^trf-b1-sarf-\d{4}$")


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _queue_by_row_id():
    return {r["row_id"]: r for r in _jsonl(QUEUE)}


def _misconceptions_by_id():
    return {r["misconception_id"]: r for r in _jsonl(MISCONCEPTIONS)}


def _blob(row):
    return json.dumps(row, ensure_ascii=False)


class ManifestSourceTruthTests(unittest.TestCase):
    """The 17 pinned rows are independently re-verified against COMMITTED public evidence, never trusted from
    the private manifest alone."""

    def test_manifest_pins_exactly_17_unique_rows(self):
        self.assertEqual(len(MANIFEST_ROWS), 17)
        self.assertEqual(len(set(MANIFEST_ROW_IDS)), 17)

    def test_every_row_resolves_in_the_committed_queue_with_matching_lesson_and_domain(self):
        queue = _queue_by_row_id()
        for row in MANIFEST_ROWS:
            q = queue.get(row["source_queue_row_id"])
            self.assertIsNotNone(q, "%s missing from q-error-fixtures.jsonl" % row["source_queue_row_id"])
            self.assertEqual(q["source"], row["lesson_id"])
            self.assertIn(row["target_domain"], q.get("target_consumer") or "")

    def test_qualification_paths_exist_and_contain_the_named_lesson(self):
        for row in MANIFEST_ROWS:
            path = _REPO / row["qualification_path"].replace("/", "\\")
            self.assertTrue(path.exists(), "%s does not exist" % row["qualification_path"])
            lessons = {r["lesson_id"] for r in _jsonl(path)}
            self.assertIn(row["lesson_id"], lessons)

    def test_every_misconception_id_exists_with_matching_lesson_manifestation_and_unit_link(self):
        registry = _misconceptions_by_id()
        for row in MANIFEST_ROWS:
            self.assertGreaterEqual(len(row["misconception_ids"]), 4)
            self.assertEqual(len(row["misconception_ids"]), len(set(row["misconception_ids"])))
            for mc_id in row["misconception_ids"]:
                mc = registry.get(mc_id)
                self.assertIsNotNone(mc, "%s missing from misconception-registry.jsonl" % mc_id)
                self.assertEqual(mc["disposition"], "candidate_fixture")
                manifestation_lessons = {m["lesson_id"] for m in mc.get("manifestations") or []}
                self.assertIn(row["lesson_id"], manifestation_lessons,
                             "%s has no manifestation for %s" % (mc_id, row["lesson_id"]))
                self.assertTrue(set(mc.get("related_units") or []) & set(row["selected_unit_links"]),
                               "%s related_units do not intersect %s's selected_unit_links"
                               % (mc_id, row["source_queue_row_id"]))

    def test_no_overlap_with_batch_a_selected_rows(self):
        batch_a_ids = {t[1] for t in EXPECTED_BATCH_A_TRACE_PREFIX}
        self.assertEqual(batch_a_ids & set(MANIFEST_ROW_IDS), set())


class BatchAImmutabilityTests(unittest.TestCase):
    """Batch A's own trace prefix and bank files must never move when B1 is appended."""

    def test_trace_prefix_50_rows_are_byte_identical_to_the_pinned_batch_a_snapshot(self):
        trace = _jsonl(TRACE)
        self.assertGreaterEqual(len(trace), 50)
        prefix = trace[:50]
        for got, expected in zip(prefix, EXPECTED_BATCH_A_TRACE_PREFIX):
            runner, bank = _RUNNER[expected[3]]
            self.assertEqual(got["row_id"], expected[0])
            self.assertEqual(got["source_queue_row_id"], expected[1])
            self.assertEqual(got["source_lesson"], expected[2])
            self.assertEqual(got["owning_runner"], runner)
            self.assertEqual(got["owning_skill_bank"], bank)
            self.assertEqual(got["fixture_id"], expected[4])
            self.assertEqual(tuple(got["misconception_ids_checked"]), expected[5])
            self.assertEqual(got["outcome"], "runner_loaded_fixture_only")
            self.assertIs(got["behaviorally_decided"], False)

    def test_sarf_bank_a_still_has_48_rows_matching_the_pinned_trace_cross_links(self):
        by_id = {r["id"]: r for r in _jsonl(SARF_BANK_A)}
        self.assertEqual(len(by_id), 48)
        for row_id, source_row_id, source_lesson, flag, fixture_id, mc_ids in EXPECTED_BATCH_A_TRACE_PREFIX:
            if flag != "s":
                continue
            bank_row = by_id.get(fixture_id)
            self.assertIsNotNone(bank_row, "%s missing from batch A sarf bank" % fixture_id)
            self.assertEqual(bank_row["source_row_id"], source_row_id)
            self.assertEqual(bank_row["source_lesson"], source_lesson)
            self.assertIn(bank_row["misconception_id"], mc_ids)

    def test_nahw_bank_a_still_has_2_rows(self):
        self.assertEqual(len(_jsonl(NAHW_BANK_A)), 2)


class TraceAppendTests(unittest.TestCase):
    """17 new rows appended after batch A's 50, for 67 unique covered queue rows total."""

    def test_trace_has_exactly_67_rows(self):
        self.assertEqual(len(_jsonl(TRACE)), 67)

    def test_appended_rows_are_a_bijection_with_the_manifest(self):
        trace = _jsonl(TRACE)
        appended = trace[50:67]
        self.assertEqual(len(appended), 17)
        got_ids = {r["source_queue_row_id"] for r in appended}
        self.assertEqual(got_ids, set(MANIFEST_ROW_IDS))
        row_ids = [r["row_id"] for r in appended]
        self.assertEqual(len(row_ids), len(set(row_ids)))
        for rid in row_ids:
            self.assertRegex(rid, B1_TRACE_ROW_ID_RE)

    def test_appended_rows_carry_exact_reverse_links_to_the_manifest(self):
        trace = _jsonl(TRACE)
        appended = {r["source_queue_row_id"]: r for r in trace[50:67]}
        for row in MANIFEST_ROWS:
            got = appended[row["source_queue_row_id"]]
            self.assertEqual(got["source_lesson"], row["lesson_id"])
            self.assertEqual(sorted(got["selected_unit_links"]), sorted(row["selected_unit_links"]))
            self.assertEqual(got["target_domain"], row["target_domain"])
            self.assertEqual(got["outcome"], "runner_loaded_fixture_only")
            self.assertIs(got["behaviorally_decided"], False)
            self.assertEqual(got["owning_runner"], "tools/run_sarf_evals.py")
            self.assertEqual(got["owning_skill_bank"], SARF_BANK_B1_REL)
            self.assertRegex(got["fixture_id"], B1_FIXTURE_ID_RE)
            self.assertIsNone(got.get("capability_gap_reason"))
            self.assertEqual(sorted(got["misconception_ids_checked"]), sorted(row["misconception_ids"]))
            self.assertTrue((got.get("clean_room_posture") or "").strip())
            self.assertEqual(got.get("certification_status"),
                             "not_certified; no public claim; fixture_only classification, no behavioral-closure "
                             "claim")

    def test_no_duplicate_row_id_or_source_queue_row_across_the_full_trace(self):
        trace = _jsonl(TRACE)
        row_ids = [r["row_id"] for r in trace]
        source_ids = [r["source_queue_row_id"] for r in trace]
        self.assertEqual(len(row_ids), len(set(row_ids)))
        self.assertEqual(len(source_ids), len(set(source_ids)))
        self.assertEqual(len(set(source_ids)), 67)

    def test_no_behavioral_closure_vocabulary_anywhere_in_the_trace(self):
        for row in _jsonl(TRACE):
            blob = _blob(row).lower()
            for bad in FORBIDDEN_OUTCOME_SUBSTRINGS:
                if bad == "certified":
                    self.assertNotIn("qamus_certified", blob, row.get("row_id"))
                    self.assertNotIn('"certified": true', blob, row.get("row_id"))
                    continue
                self.assertNotIn(bad, blob, "%s: forbidden behavioral-closure vocabulary %r" % (row["row_id"], bad))

    def test_appended_rows_leak_no_private_source_or_answer_key(self):
        for row in _jsonl(TRACE)[50:67]:
            blob = _blob(row)
            for bad in FORBIDDEN_LEAKAGE_SUBSTRINGS:
                self.assertNotIn(bad, blob, "%s: leaked %r" % (row.get("row_id"), bad))


class MetaUpdateTests(unittest.TestCase):
    """The shared meta file honestly records the append; behaviorally_decided stays zero throughout."""

    def test_meta_counts_reflect_67_loaded_rows_zero_decided(self):
        meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
        self.assertEqual(meta["outcomes"]["runner_loaded_fixture_only_count"], 67)
        self.assertEqual(meta["outcomes"]["behaviorally_decided_count"], 0)
        self.assertEqual(meta["outcomes"]["capability_gap_count"], 0)
        self.assertNotIn("executable_fixture_count", meta["outcomes"])
        self.assertEqual(meta["domain_routing"]["sarf_runner_loaded_count"], 65)
        self.assertEqual(meta["domain_routing"]["sarf_behaviorally_decided_count"], 0)
        self.assertEqual(meta["domain_routing"]["nahw_runner_loaded_count"], 2)
        self.assertEqual(meta["domain_routing"]["nahw_behaviorally_decided_count"], 0)

    def test_meta_batch_a_provenance_numbers_are_unchanged(self):
        meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
        self.assertEqual(meta["candidate_universe_row_count"], 101)
        self.assertEqual(meta["selected_batch_row_count"], 50)

    def test_meta_remaining_count_drops_the_17_b1_rows(self):
        meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
        self.assertEqual(meta["remaining_row_count"], 34)
        remaining = meta.get("remaining_row_ids") or []
        self.assertEqual(len(remaining), 34)
        self.assertEqual(len(remaining), len(set(remaining)))
        self.assertEqual(set(remaining) & set(MANIFEST_ROW_IDS), set())

    def test_meta_has_no_behavioral_closure_vocabulary_in_active_fields(self):
        """Reject behavioral-closure labels in active outcome keys, trace outcome values, counts and current
        claims — but not inside a historical note that explicitly documents the OLD label's removal (e.g.
        outcomes.vocabulary_note truthfully says this batch 'previously mislabelled these rows executable' and
        that vocabulary 'has been removed'). Narrowly whitelisting that one historical field is not a weaker
        check: every other string in the meta file, including every other note field, is still scanned."""
        meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
        historical_narrative_fields = {("outcomes", "vocabulary_note")}

        def walk(node, path):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, path + (k,))
            elif isinstance(node, list):
                for v in node:
                    walk(v, path)
            elif isinstance(node, str):
                low = node.lower()
                self.assertNotIn("qamus_certified", low, "%s: leaked qamus_certified" % (path,))
                self.assertNotIn("public_release", low, "%s: leaked public_release" % (path,))
                if path in historical_narrative_fields:
                    return
                for bad in ("executable", "behaviorally_closed", "decided_by_consumer"):
                    self.assertNotIn(bad, low, "%s: forbidden vocabulary %r in %r" % (path, bad, node[:120]))

        walk(meta, ())


class BankFixtureTests(unittest.TestCase):
    """17 original hostile fixtures, one per manifest row, structurally hostile and never a promotion surface."""

    def test_bank_has_exactly_17_rows_one_per_manifest_row(self):
        rows = _jsonl(SARF_BANK_B1)
        self.assertEqual(len(rows), 17)
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for rid in ids:
            self.assertRegex(rid, B1_FIXTURE_ID_RE)
        batch_a_ids = {r["id"] for r in _jsonl(SARF_BANK_A)}
        self.assertEqual(set(ids) & batch_a_ids, set())
        self.assertEqual({r["source_row_id"] for r in rows}, set(MANIFEST_ROW_IDS))

    def test_every_row_carries_exact_lesson_domain_and_misconception_reverse_links(self):
        rows = {r["source_row_id"]: r for r in _jsonl(SARF_BANK_B1)}
        for row in MANIFEST_ROWS:
            got = rows[row["source_queue_row_id"]]
            for field in ("id", "source_row_id", "source_lesson", "misconception_ids", "domain",
                         "anti_llm_boundary", "surface", "correct_surface", "wrong_reasoning", "why_wrong",
                         "clean_room_posture", "distractors"):
                self.assertIn(field, got, "%s missing field %r" % (got.get("id"), field))
            self.assertEqual(got["source_lesson"], row["lesson_id"])
            self.assertEqual(got["domain"], row["target_domain"])
            self.assertEqual(sorted(got["misconception_ids"]), sorted(row["misconception_ids"]))
            self.assertIn(got["anti_llm_boundary"], ANTI_LLM_BOUNDARIES)

    def test_hostile_positive_negative_discrimination_is_meaningful(self):
        seen_boundaries = set()
        for row in _jsonl(SARF_BANK_B1):
            self.assertTrue((row["surface"] or "").strip())
            self.assertTrue((row["correct_surface"] or "").strip())
            self.assertTrue((row["wrong_reasoning"] or "").strip())
            self.assertTrue((row["why_wrong"] or "").strip())
            self.assertNotEqual(row["wrong_reasoning"], row["why_wrong"])
            distractors = row.get("distractors") or []
            self.assertGreaterEqual(len(distractors), 2)
            self.assertEqual(len(distractors), len(set(distractors)))
            for d in distractors:
                self.assertNotEqual(d, row["why_wrong"])
            seen_boundaries.add(row["anti_llm_boundary"])
        self.assertGreaterEqual(len(seen_boundaries), 2,
                                "the batch should exercise more than one hostile failure boundary")

    def test_no_root_pattern_sense_meaning_translation_or_certification_promotion(self):
        for row in _jsonl(SARF_BANK_B1):
            for key in FORBIDDEN_PROMOTION_KEYS:
                self.assertNotIn(key, row, "%s: forbidden promotion key %r" % (row.get("id"), key))
            blob = _blob(row).lower()
            self.assertNotIn('"certified": true', blob)
            self.assertNotIn("qamus_certified", blob)
            self.assertNotIn("public_release", blob)

    def test_no_answer_key_or_private_leakage(self):
        for row in _jsonl(SARF_BANK_B1):
            self.assertNotIn("expected_decision", row)
            self.assertNotIn("qamus_source_card", row)
            blob = _blob(row)
            for bad in FORBIDDEN_LEAKAGE_SUBSTRINGS:
                self.assertNotIn(bad, blob, "%s: leaked %r" % (row.get("id"), bad))


class RunnerLoadTests(unittest.TestCase):
    """The real tools/run_sarf_evals.py interfaces, never a reimplementation, decide this bank's classification."""

    def test_b1_bank_is_registered_fixture_only_and_reports_zero_decided_rows(self):
        import run_sarf_evals as rse
        contract = rse.load_contract(str(_REPO))
        spec = rse.bank_spec(contract, SARF_BANK_B1_REL)
        self.assertEqual(spec["disposition"], "fixture_only")
        self.assertIsNone(spec["behavioral_consumer"])
        rows = rse.load_bank(str(_REPO), spec)
        self.assertEqual(len(rows), 17)
        errors = rse.validate_contract(contract, str(_REPO))
        my_errors = [e for e in errors if "tranche-001-error-fixtures-b1" in e]
        self.assertEqual(my_errors, [], my_errors)
        ctx = rse.Consumers.real()
        adapter = rse.ADAPTERS[spec["adapter"]]
        fails, metrics = adapter(rows, spec, ctx, str(_REPO))
        self.assertEqual(fails, [], fails)
        self.assertEqual(metrics["decided_rows"], 0,
                         "a fixture_only bank must report zero rows decided by a production consumer")
        for row in rows:
            cands = ctx.segment_candidates(row["surface"])
            self.assertTrue(rse._concat_exact(cands, row["surface"]),
                           "%s: surface is not byte-exact through the real segmenter" % row.get("id"))

    def test_b1_bank_resolves_by_the_basename_cli_form(self):
        import run_sarf_evals as rse
        contract = rse.load_contract(str(_REPO))
        spec = rse.bank_spec(contract, "tranche-001-error-fixtures-b1.jsonl")
        self.assertEqual(spec["path"], SARF_BANK_B1_REL)
        with self.assertRaises(KeyError):
            rse.bank_spec(contract, "tranche-001-error-fixtures-b1")


if __name__ == "__main__":
    unittest.main()
