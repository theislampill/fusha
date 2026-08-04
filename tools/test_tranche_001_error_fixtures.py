#!/usr/bin/env python3
"""Focused tests for tranche-001 Line 4 hostile error fixtures, batch A.

Pins: deterministic 101->50 selection off curriculum/l1l6/canonical/lesson-unit-map.jsonl +
curriculum/l1l6/reports/queues/q-error-fixtures.jsonl; full 50/50 trace coverage with no silent row; every
runner_loaded_fixture_only trace resolves to a fixture a real eval runner actually loads (tools/run_sarf_evals.py
/ tools/run_nahw_evals.py) AND is verified fixture_only / not behaviorally_decided through those real runners;
zero capability gaps in this repaired batch; no duplicate fixture id within or across banks; no answer-key/source
leakage; right-answer/wrong-reason naḥw cases stay genuine hostile traps; the candidate/certified boundary is
never crossed by a fixture_only bank. `executable` and any other behavioral-closure vocabulary are forbidden
outcome/disposition labels for a bank whose real runner reports zero decided rows.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

LESSON_UNIT_MAP = _REPO / "curriculum" / "l1l6" / "canonical" / "lesson-unit-map.jsonl"
QUEUE = _REPO / "curriculum" / "l1l6" / "reports" / "queues" / "q-error-fixtures.jsonl"
TRACE = _REPO / "curriculum" / "l1l6" / "reports" / "mistake-pattern-fixtures.jsonl"
TRACE_META = _REPO / "curriculum" / "l1l6" / "reports" / "mistake-pattern-fixtures.meta.json"
SARF_BANK = _REPO / "sarf" / "evals" / "tranche-001-error-fixtures-a.jsonl"
NAHW_BANK = _REPO / "nahw" / "evals" / "tranche-001-error-fixtures-a.jsonl"

SELECTED_UNIT_IDS = {
    "cu-grapheme-inventory-and-confusables",
    "cu-orthographic-connectivity-classes",
    "cu-short-vowel-diacritics-and-vocalization-state",
    "u-s06",
    "u-s01",
    "cu-nunation-support-orthography",
    "u-n01",
    "cu-definite-article-assimilation",
}

# The only honest outcome labels for THIS batch: no bank here has a real adapter that compares consumer output
# against a row's expected claim, so no row may ever be labelled 'executable' or otherwise implied
# behaviorally-decided. capability_gap stays in the closed vocabulary for a future batch that proves a genuine
# gap against current code; this batch's own count of it is pinned at zero below.
ALLOWED_OUTCOMES = {"runner_loaded_fixture_only", "capability_gap"}
FORBIDDEN_OUTCOME_SUBSTRINGS = ("executable", "behaviorally_closed", "certified", "decided_by_consumer")


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _candidate_rows():
    """Recompute the deterministic candidate universe independently of the committed trace."""
    lum = _jsonl(LESSON_UNIT_MAP)
    selected_lessons = {row["lesson_id"] for row in lum if SELECTED_UNIT_IDS & set(row.get("units") or [])}
    queue = _jsonl(QUEUE)
    candidates = [row for row in queue if row.get("source") in selected_lessons]
    candidates.sort(key=lambda r: r["row_id"])
    return candidates


def _batch_a_trace():
    """Return only batch A rows from the append-only shared trace."""
    return [
        row for row in _jsonl(TRACE)
        if row.get("row_id", "").startswith("trf-a-trace-")
    ]


class SelectionDeterminismTests(unittest.TestCase):
    def test_candidate_universe_is_exactly_101(self):
        candidates = _candidate_rows()
        self.assertEqual(len(candidates), 101, "candidate universe drifted from the pinned 101 rows")

    def test_selected_batch_is_the_first_50_by_row_id_no_hand_picking(self):
        candidates = _candidate_rows()
        want = [r["row_id"] for r in candidates[:50]]
        got = [r["source_queue_row_id"] for r in _batch_a_trace()]
        self.assertEqual(got, want, "trace does not carry the deterministic row_id-sorted first-50 prefix")

    def test_original_tail_is_partitioned_between_later_batches_and_remaining(self):
        candidates = _candidate_rows()
        want_remaining = [r["row_id"] for r in candidates[50:]]
        meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
        later_rows = [
            row["source_queue_row_id"] for row in _jsonl(TRACE)
            if not row.get("row_id", "").startswith("trf-a-trace-")
        ]
        self.assertEqual(set(later_rows) & set(meta["remaining_row_ids"]), set())
        self.assertEqual(
            set(later_rows) | set(meta["remaining_row_ids"]),
            set(want_remaining),
        )
        self.assertEqual(len(want_remaining), 51)


class TraceCoverageTests(unittest.TestCase):
    def test_batch_a_trace_has_exactly_50_rows(self):
        self.assertEqual(len(_batch_a_trace()), 50)

    def test_no_silent_row_every_row_declares_an_allowed_outcome(self):
        for row in _batch_a_trace():
            self.assertIn(row.get("outcome"), ALLOWED_OUTCOMES,
                         "row %r has no valid outcome" % row.get("row_id"))

    def test_no_behavioral_closure_vocabulary_anywhere_in_the_trace(self):
        """Red-first: this must fail if 'executable' or another behavioral-closure label reappears on a
        fixture_only bank. Scans every row's raw JSON text, not just the outcome field, so a relabelled field
        or a smuggled note cannot slip the forbidden vocabulary back in."""
        for row in _jsonl(TRACE):
            blob = json.dumps(row, ensure_ascii=False).lower()
            self.assertNotIn('"outcome": "executable"', blob, row.get("row_id"))
            for bad in FORBIDDEN_OUTCOME_SUBSTRINGS:
                if bad == "certified":
                    # 'not_certified' legitimately contains 'certified' as a substring; only a bare/positive
                    # certification claim is forbidden.
                    self.assertNotIn("qamus_certified", blob, row.get("row_id"))
                    self.assertNotIn('"certified": true', blob, row.get("row_id"))
                    continue
                self.assertNotIn(bad, blob, "%s: forbidden behavioral-closure vocabulary %r" % (row["row_id"], bad))
            self.assertIn("behaviorally_decided", row, "%s: missing behaviorally_decided" % row["row_id"])
            self.assertIs(row["behaviorally_decided"], False,
                          "%s: behaviorally_decided must be false for a fixture_only bank" % row["row_id"])
            self.assertTrue(row.get("owning_runner"), "%s: missing owning runner identity" % row["row_id"])

    def test_no_duplicate_trace_row_ids_or_source_queue_rows(self):
        trace = _jsonl(TRACE)
        row_ids = [r["row_id"] for r in trace]
        source_ids = [r["source_queue_row_id"] for r in trace]
        self.assertEqual(len(row_ids), len(set(row_ids)), "duplicate trace row_id")
        self.assertEqual(len(source_ids), len(set(source_ids)), "duplicate source_queue_row_id")

    def test_every_runner_loaded_trace_resolves_to_a_fixture_the_runner_actually_loads(self):
        sarf_ids = {r["id"] for r in _jsonl(SARF_BANK)}
        nahw_ids = {r["id"] for r in _jsonl(NAHW_BANK)}
        for row in _batch_a_trace():
            if row["outcome"] != "runner_loaded_fixture_only":
                continue
            fid = row.get("fixture_id")
            self.assertTrue(fid, "runner_loaded_fixture_only row %r names no fixture_id" % row["row_id"])
            bank = row.get("owning_skill_bank") or ""
            if bank.startswith("sarf/"):
                self.assertEqual(row.get("owning_runner"), "tools/run_sarf_evals.py")
                self.assertIn(fid, sarf_ids, "sarf fixture_id %r is not loaded by the sarf bank" % fid)
            elif bank.startswith("nahw/"):
                self.assertEqual(row.get("owning_runner"), "tools/run_nahw_evals.py")
                self.assertIn(fid, nahw_ids, "naḥw fixture_id %r is not loaded by the naḥw bank" % fid)
            else:
                self.fail("row %r names an unrecognised owning_skill_bank %r" % (row["row_id"], bank))

    def test_zero_capability_gaps_in_this_repaired_batch(self):
        gaps = [r for r in _batch_a_trace() if r["outcome"] == "capability_gap"]
        self.assertEqual(len(gaps), 0,
                         "this batch was repaired to have zero capability gaps against current code; a gap "
                         "reappearing here must carry fresh, non-stale evidence")
        for lesson in ("L1.M1.01", "L1.M1.03", "L1.M1.04"):
            rows = [r for r in _batch_a_trace() if r["source_lesson"] == lesson]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["outcome"], "runner_loaded_fixture_only")
            self.assertIsNone(rows[0].get("capability_gap_reason"))
            self.assertTrue(rows[0].get("fixture_id"))

    def test_sarf_nahw_and_behaviorally_decided_counts_match_meta(self):
        meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
        trace = _batch_a_trace()
        loaded = [r for r in trace if r["outcome"] == "runner_loaded_fixture_only"]
        gaps = [r for r in trace if r["outcome"] == "capability_gap"]
        decided = [r for r in trace if r.get("behaviorally_decided") is True]
        sarf = [r for r in loaded if r["owning_skill_bank"].startswith("sarf/")]
        nahw = [r for r in loaded if r["owning_skill_bank"].startswith("nahw/")]
        self.assertEqual(len(loaded) + len(gaps), 50)
        self.assertGreaterEqual(meta["outcomes"]["runner_loaded_fixture_only_count"], len(loaded))
        self.assertGreaterEqual(meta["outcomes"]["capability_gap_count"], len(gaps))
        self.assertEqual(len(decided), 0)
        self.assertEqual(meta["outcomes"]["behaviorally_decided_count"], 0)
        self.assertGreaterEqual(meta["domain_routing"]["sarf_runner_loaded_count"], len(sarf))
        self.assertGreaterEqual(meta["domain_routing"]["nahw_runner_loaded_count"], len(nahw))
        self.assertEqual(meta["domain_routing"]["sarf_behaviorally_decided_count"], 0)
        self.assertEqual(meta["domain_routing"]["nahw_behaviorally_decided_count"], 0)
        self.assertEqual(meta["candidate_universe_row_count"], 101)
        self.assertEqual(meta["selected_batch_row_count"], 50)
        self.assertEqual(
            len(_jsonl(TRACE)) - len(trace) + meta["remaining_row_count"],
            51,
        )
        self.assertNotIn("executable_fixture_count", meta["outcomes"])


class FixtureIntegrityTests(unittest.TestCase):
    def test_no_duplicate_fixture_id_within_or_across_banks(self):
        sarf_ids = [r["id"] for r in _jsonl(SARF_BANK)]
        nahw_ids = [r["id"] for r in _jsonl(NAHW_BANK)]
        self.assertEqual(len(sarf_ids), len(set(sarf_ids)), "duplicate id inside the sarf bank")
        self.assertEqual(len(nahw_ids), len(set(nahw_ids)), "duplicate id inside the naḥw bank")
        self.assertEqual(set(sarf_ids) & set(nahw_ids), set(), "an id collides across the sarf/naḥw banks")

    def test_sarf_bank_has_exactly_48_rows_nahw_has_2(self):
        self.assertEqual(len(_jsonl(SARF_BANK)), 48)
        self.assertEqual(len(_jsonl(NAHW_BANK)), 2)

    def test_the_three_repaired_orthography_rows_route_through_fusha_orthography(self):
        by_id = {r["id"]: r for r in _jsonl(SARF_BANK)}
        for fid, fn_name, lesson in (
            ("trf-a-sarf-0046", "confusable_family", "L1.M1.01"),
            ("trf-a-sarf-0047", "vocalization_state", "L1.M1.03"),
            ("trf-a-sarf-0048", "vocalization_state", "L1.M1.04"),
        ):
            row = by_id[fid]
            self.assertEqual(row["source_lesson"], lesson)
            probe = row.get("orthography_probe")
            self.assertIsInstance(probe, dict, "%s: missing orthography_probe" % fid)
            self.assertEqual(probe.get("function"), fn_name)
            self.assertTrue(probe.get("arg"))

    def test_no_answer_key_or_source_leakage(self):
        for row in _jsonl(SARF_BANK):
            self.assertNotIn("expected_decision", row)
            self.assertNotIn("qamus_source_card", row)
            self.assertTrue((row.get("clean_room_posture") or "").strip(), row.get("id"))
        for row in _jsonl(NAHW_BANK):
            self.assertNotIn("expected_decision", row)
            self.assertTrue((row.get("clean_room_posture") or "").strip(), row.get("id"))

    def test_correct_answer_wrong_reason_cases_remain_hostile_failures(self):
        rows = _jsonl(NAHW_BANK)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertTrue(row["expected_reasoning"].strip())
            self.assertTrue(row["wrong_reasoning_trap"].strip())
            self.assertNotEqual(row["expected_reasoning"], row["wrong_reasoning_trap"],
                               "%s: the honest path and the trap must not be the same text" % row["id"])
            self.assertTrue(row["why_trap_wrong"].strip())
            self.assertEqual(row.get("anti_llm_boundary"), "correct_conclusion_wrong_reason")
            self.assertIn(row.get("required_gate"), ("two_vote_required", "human_source_review_required",
                                                      "never_auto_resolve"))
            self.assertNotEqual(row.get("hover_safety"), "auto_safe")

    def test_candidate_never_certified_boundary(self):
        for path in (SARF_BANK, NAHW_BANK):
            for row in _jsonl(path):
                blob = json.dumps(row, ensure_ascii=False).lower()
                self.assertNotIn('"certified": true', blob,
                                 "%s: a fixture_only row must never claim certification" % path)
                self.assertNotIn("qamus_certified", blob)
                self.assertNotIn("public_release", blob)

    def test_every_sarf_row_names_a_recognised_anti_llm_boundary(self):
        boundaries = {"correct_conclusion_wrong_reason", "surface_shape_alone_cannot_promote",
                     "swallowed_boundary_fails", "missing_evidence_abstains", "candidate_never_certified",
                     "ambiguous_rivals_preserved"}
        seen = set()
        for row in _jsonl(SARF_BANK):
            b = row.get("anti_llm_boundary")
            self.assertIn(b, boundaries, "%s: unrecognised anti_llm_boundary %r" % (row["id"], b))
            seen.add(b)
            self.assertGreaterEqual(len(row.get("distractors") or []), 2,
                                    "%s: fewer than two rival distractors" % row["id"])
        self.assertGreaterEqual(len(seen), 3, "the batch should exercise more than one failure boundary")


class RunnerLoadTests(unittest.TestCase):
    """A row counts loaded only when a real eval runner loads its linked fixture, and this batch's fixture_only
    classification must be verified THROUGH those real runners, not merely asserted in committed JSON."""

    def test_sarf_bank_is_registered_fixture_only_and_reports_zero_decided_rows(self):
        import run_sarf_evals as rse
        contract = rse.load_contract(str(_REPO))
        spec = rse.bank_spec(contract, "sarf/evals/tranche-001-error-fixtures-a.jsonl")
        self.assertEqual(spec["adapter"], "tranche_001_error_fixtures_a")
        self.assertEqual(spec["disposition"], "fixture_only")
        self.assertIsNone(spec["behavioral_consumer"])
        rows = rse.load_bank(str(_REPO), spec)
        self.assertEqual(len(rows), 48)
        errors = rse.validate_contract(contract, str(_REPO))
        my_errors = [e for e in errors if "tranche-001-error-fixtures-a" in e]
        self.assertEqual(my_errors, [], my_errors)
        # Verify fixture_only through the REAL runner, not just the committed spec: run the adapter and require
        # decided_rows == 0 (the property finding 1 requires) while confirming it genuinely calls the real
        # consumers (byte-exactness on every row, orthography probes on the three repaired rows).
        ctx = rse.Consumers.real()
        fails, metrics = rse.adapter_tranche_001_error_fixtures_a(rows, spec, ctx, str(_REPO))
        self.assertEqual(fails, [], fails)
        self.assertEqual(metrics["decided_rows"], 0,
                         "a fixture_only bank must report zero rows decided by a production consumer")
        self.assertEqual(metrics["surfaces_byte_exact"], 48)
        self.assertEqual(metrics["orthography_probed_rows"], 3)

    def test_sarf_bank_resolves_by_the_corrected_basename_cli_form(self):
        """The orchestrator's corrected focused command: --bank tranche-001-error-fixtures-a.jsonl (repo path or
        basename; no extensionless-stem broadening)."""
        import run_sarf_evals as rse
        contract = rse.load_contract(str(_REPO))
        spec = rse.bank_spec(contract, "tranche-001-error-fixtures-a.jsonl")
        self.assertEqual(spec["path"], "sarf/evals/tranche-001-error-fixtures-a.jsonl")
        with self.assertRaises(KeyError):
            rse.bank_spec(contract, "tranche-001-error-fixtures-a")

    def test_nahw_bank_is_registered_fixture_only_and_reports_zero_decided_rows(self):
        import run_nahw_evals as rne
        self.assertIn("tranche-001-error-fixtures-a", rne.BANKS)
        errors, stats = [], {}
        rne.BANKS["tranche-001-error-fixtures-a"](errors, stats)
        self.assertEqual(errors, [])
        self.assertEqual(stats["tranche-001-error-fixtures-a"]["cases"], 2)
        self.assertEqual(stats["tranche-001-error-fixtures-a"]["routing_checked"], 2)
        self.assertEqual(stats["tranche-001-error-fixtures-a"]["classification"], "fixture_only")


if __name__ == "__main__":
    unittest.main()
