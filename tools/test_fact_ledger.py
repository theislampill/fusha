#!/usr/bin/env python3
"""Regression tests for the typed, append-only fact ledger."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402


SCHEMA_PATH = ROOT / "qamus" / "schemas" / "fact-ledger-row.schema.json"


def make_row(*, value="restricts", state="candidate", fact_type="sense", loc="28:82:7"):
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": {
            "ref_type": "surface_occurrence",
            "loc": loc,
            "entry_id": "entry-v001",
            "card_id": "card-28-82",
            "qword_row_id": "qword-28-82-7",
        },
        "fact_type": fact_type,
        "candidate_or_value": {
            "value": value,
            "competing_alternatives": [],
            "semantic_tie": False,
        },
        "scope": "occurrence",
        "source_address": {
            "address": "quran:28:82:7",
            "source_kind": "quran_token",
        },
        "evidence": [
            {
                "evidence_id": "ev-derivation-1",
                "type": "deterministic_derivation",
                "detail": "fixture derivation",
            }
        ],
        "provenance": {
            "actor": "test-suite",
            "method": "fixture",
            "created_at": "2026-07-11T12:00:00Z",
            "input_hashes": {"fixture": "sha256:" + "1" * 64},
        },
        "review_votes": [],
        "certification_state": state,
        "confidence_or_calibration": None,
        "defeaters": [],
        "exceptions": [],
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": None,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def approving_votes():
    return [
        {
            "voter_id": "reviewer-a",
            "vote": "approve",
            "evidence_ref": "ev-derivation-1",
            "independent": True,
        },
        {
            "voter_id": "reviewer-b",
            "vote": "approve",
            "evidence_ref": "ev-derivation-1",
            "independent": True,
        },
    ]


class FactLedgerTests(unittest.TestCase):
    def test_schema_validates_every_fixture_row(self):
        schema = fact_ledger.load_schema(SCHEMA_PATH)
        fixtures = [
            make_row(),
            make_row(state="invalid"),
            make_row(state="tie_unresolved"),
            make_row(state="materialized"),
        ]
        for row in fixtures:
            with self.subTest(state=row["certification_state"]):
                self.assertEqual([], fact_ledger.validate_schema(row, schema))

    def test_illegal_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            row = store.append(make_row())
            with self.assertRaisesRegex(fact_ledger.ValidationError, "illegal transition"):
                store.transition(row["fact_id"], "certified", review_votes=approving_votes())

    def test_two_vote_fact_cannot_certify_without_independent_votes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            row = store.append(make_row(fact_type="irab_rendering"))
            store.transition(row["fact_id"], "review_required")
            with self.assertRaisesRegex(fact_ledger.ValidationError, "independent approving votes"):
                store.transition(row["fact_id"], "certified")

    def test_statistical_evidence_only_cannot_certify(self):
        statistical = [
            {
                "evidence_id": "ev-stat-1",
                "type": "statistical_signal",
                "detail": "model score only",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            row = store.append(make_row(fact_type="irab_rendering"))
            store.transition(row["fact_id"], "review_required")
            with self.assertRaisesRegex(fact_ledger.ValidationError, "statistical_signal"):
                store.transition(
                    row["fact_id"],
                    "certified",
                    evidence=statistical,
                    review_votes=approving_votes(),
                )

    def test_statistical_signal_can_support_candidate_only(self):
        row = make_row()
        row["evidence"] = [
            {
                "evidence_id": "ev-stat-1",
                "type": "statistical_signal",
                "detail": "model score only",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            row = store.append(row)
            with self.assertRaisesRegex(fact_ledger.ValidationError, "candidate"):
                store.transition(row["fact_id"], "review_required")

    def test_bare_loc_occurrence_subject_is_rejected(self):
        row = make_row()
        row["subject_identity"] = {"ref_type": "surface_occurrence", "loc": "28:82:7"}
        row["fact_id"] = fact_ledger.compute_fact_id(row)
        with self.assertRaisesRegex(fact_ledger.ValidationError, "full D-13 carrier"):
            fact_ledger.validate_row(row)

    def test_semantic_tie_cannot_be_adjudicated_by_deterministic_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_row(value="reading-a")
            row["candidate_or_value"] = {
                "value": "reading-a",
                "competing_alternatives": [
                    {"value": "reading-b", "semantic_tie": True}
                ],
                "semantic_tie": True,
            }
            row["fact_id"] = fact_ledger.compute_fact_id(row)
            store = fact_ledger.FactLedgerStore(tmp)
            row = store.append(row)
            store.transition(row["fact_id"], "review_required")
            with self.assertRaisesRegex(fact_ledger.ValidationError, "tie_unresolved"):
                store.transition(row["fact_id"], "certified", review_votes=approving_votes())
            tied = store.transition(
                row["fact_id"], "tie_unresolved", review_votes=approving_votes()
            )
            self.assertEqual("tie_unresolved", tied["certification_state"])

    def test_certified_collision_assigns_conflicted_to_both_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            first = store.append(make_row(value="restricts"))
            second = store.append(make_row(value="constrains"))
            for row in (first, second):
                store.transition(row["fact_id"], "review_required")
            store.transition(first["fact_id"], "certified", review_votes=approving_votes())
            result = store.transition(
                second["fact_id"], "certified", review_votes=approving_votes()
            )
            self.assertEqual("conflicted", result["certification_state"])
            current = {row["fact_id"]: row for row in store.query(current_only=True)}
            self.assertEqual("conflicted", current[first["fact_id"]]["certification_state"])
            self.assertEqual("conflicted", current[second["fact_id"]]["certification_state"])

    def test_round_trip_and_traversable_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            candidate = store.append(make_row())
            store.transition(candidate["fact_id"], "review_required")
            store.transition(candidate["fact_id"], "certified", review_votes=approving_votes())
            store.transition(candidate["fact_id"], "superseded")

            reopened = fact_ledger.FactLedgerStore(tmp)
            history = reopened.history(candidate["fact_id"])
            self.assertEqual(
                ["candidate", "review_required", "certified", "superseded"],
                [row["certification_state"] for row in history],
            )
            self.assertEqual(candidate["fact_id"], history[-1]["supersedes"])
            self.assertEqual([], reopened.validate_all())
            self.assertTrue((Path(tmp) / "index.json").is_file())

    def test_fact_id_excludes_review_churn_but_includes_value_core(self):
        row = make_row()
        changed_review = copy.deepcopy(row)
        changed_review["review_votes"] = approving_votes()
        changed_review["certification_state"] = "review_required"
        changed_review["provenance"]["created_at"] = "2026-07-11T13:00:00Z"
        changed_review["candidate_or_value"]["competing_alternatives"] = [
            {"value": "constrains", "reason": "review-added alternative"}
        ]
        self.assertEqual(row["fact_id"], fact_ledger.compute_fact_id(changed_review))

        changed_value = copy.deepcopy(row)
        changed_value["candidate_or_value"]["value"] = "expands"
        self.assertNotEqual(row["fact_id"], fact_ledger.compute_fact_id(changed_value))

    def test_open_fact_type_is_forward_compatible(self):
        row = make_row(fact_type="future_fact_family")
        fact_ledger.validate_row(row)

    def test_global_case_governor_requires_certified_compatibility_relation(self):
        row = make_row(fact_type="case_mood_governor")
        row["subject_type"] = "lexeme"
        row["subject_identity"] = {"ref_type": "lexeme", "id": "lexeme:قدر"}
        row["scope"] = "lexeme_global"
        row["fact_id"] = fact_ledger.compute_fact_id(row)
        with self.assertRaisesRegex(fact_ledger.ValidationError, "syntactic compatibility"):
            fact_ledger.validate_row(row)

        row["dependency_hashes"]["syntactic_compatibility_relation"] = "sha256:" + "2" * 64
        fact_ledger.validate_row(row)

    def test_deployed_row_cannot_be_used_as_source(self):
        row = make_row()
        row["source_address"]["address"] = "deployed:fact-row-123"
        with self.assertRaisesRegex(fact_ledger.ValidationError, "deployed row"):
            fact_ledger.validate_row(row)

    def test_two_vote_evidence_refs_must_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            row = store.append(make_row(fact_type="irab_rendering"))
            store.transition(row["fact_id"], "review_required")
            votes = approving_votes()
            votes[1]["evidence_ref"] = "ev-missing"
            with self.assertRaisesRegex(fact_ledger.ValidationError, "evidence_ref"):
                store.transition(row["fact_id"], "certified", review_votes=votes)

    def test_gate_trigger_mapping_is_checked_against_ssot(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate_path = Path(tmp) / "gates.json"
            gate_path.write_text(
                json.dumps({"gates": {"two_vote_required": {"trigger_when_ANY": []}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(fact_ledger.ValidationError, "missing gate SSOT trigger"):
                fact_ledger.FactLedgerStore(Path(tmp) / "store", gate_path=gate_path)

    def test_calibration_value_requires_evidence_basis(self):
        row = make_row()
        row["confidence_or_calibration"] = 0.91
        self.assertTrue(fact_ledger.validate_schema(row))

        row["confidence_or_calibration"] = {
            "kind": "calibration",
            "value": 0.91,
            "basis_evidence_refs": ["ev-derivation-1"],
        }
        fact_ledger.validate_row(row)

    def test_provenance_requires_at_least_one_input_hash(self):
        row = make_row()
        row["provenance"]["input_hashes"] = {}
        self.assertTrue(fact_ledger.validate_schema(row))

    def test_cli_self_test(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fact_ledger.py"), "--self-test"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("fact_ledger self-test OK", result.stdout)

    def test_cli_append_validate_query_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            row_path = Path(tmp) / "row.json"
            row_path.write_text(json.dumps(make_row(), ensure_ascii=False), encoding="utf-8")
            commands = [
                ["append", "--directory", tmp, "--row", str(row_path)],
                ["validate", "--directory", tmp],
                ["query", "--directory", tmp, "--fact-type", "sense"],
            ]
            outputs = []
            for args in commands:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "fact_ledger.py"), *args],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr + result.stdout)
                outputs.append(result.stdout)
            fact_id = json.loads(outputs[0])["fact_id"]
            self.assertEqual(1, len(json.loads(outputs[2])))
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "fact_ledger.py"),
                    "history",
                    "--directory",
                    tmp,
                    "--fact-id",
                    fact_id,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertEqual(1, len(json.loads(result.stdout)))

    def test_validate_reports_structurally_invalid_existing_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "ledger.jsonl"
            ledger_path.write_text('{"schema":"qamus.fact_ledger_row.v1"}\n', encoding="utf-8")
            store = fact_ledger.FactLedgerStore(tmp)
            errors = store.validate_all()
            self.assertEqual(1, len(errors))
            self.assertIn("schema validation failed", errors[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
