#!/usr/bin/env python3
"""Claim-binding regressions for two-vote typed-fact certification."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import certify_typed_fact as certifier
from tools import validate_two_vote_artifacts as two_vote


def _fact_value_for(row: dict, fact_type: str) -> dict:
    vote = row["votes"][0]
    conclusion = vote["conclusion"]
    common = {"reason_key": vote["reason_key"]}
    if row["schema"] == "qamus.two_vote_artifact.v1.1":
        compact = two_vote.compact
        governor = conclusion.get("governor")
        governor_identity = None
        if governor is not None:
            governor_identity = {
                "loc": compact(governor.get("loc")),
                "surface": compact(governor.get("normalized_surface") or governor.get("surface")),
            }
        common = {"reason_key": compact(vote["reason_key"])}
        case_or_mood = conclusion["case_or_mood"]
        canonical_case = {
            "mood_basis": compact(case_or_mood.get("mood_basis")) or None,
            "sign": compact(case_or_mood.get("sign")),
            "sign_visibility": compact(case_or_mood.get("sign_visibility")),
            "value": compact(case_or_mood.get("value")),
        }
        if fact_type == "governor_relation":
            return dict(common, governor=governor_identity,
                        attachment_key=compact(conclusion.get("attachment_key")) or None,
                        governed_expression=compact(conclusion.get("governed_expression")) or None)
        if fact_type == "case_mood_governor":
            return dict(common, case_or_mood=canonical_case,
                        governor=governor_identity,
                        governed_expression=compact(conclusion.get("governed_expression")) or None)
        if fact_type == "contextual_function":
            return dict(common, function=compact(conclusion["function"]))
        if fact_type == "irab_rendering":
            return dict(common, conclusion={
                "attachment_key": compact(conclusion.get("attachment_key")) or None,
                "case_or_mood": canonical_case,
                "function": compact(conclusion["function"]),
                "governed_expression": compact(conclusion.get("governed_expression")) or None,
                "governor": governor_identity,
            })
        raise AssertionError(f"unsupported fixture fact type: {fact_type}")
    if fact_type == "governor_relation":
        return dict(common, governor=copy.deepcopy(conclusion["governor"]),
                    attachment=conclusion["attachment"],
                    governed_expression=conclusion["governed_expression"])
    if fact_type == "case_mood_governor":
        return dict(common, case_or_mood=copy.deepcopy(conclusion["case_or_mood"]),
                    governor=copy.deepcopy(conclusion["governor"]),
                    governed_expression=conclusion["governed_expression"])
    if fact_type == "contextual_function":
        return dict(common, function=(conclusion.get("function")
                                     or conclusion["contextual_function"]))
    if fact_type == "irab_rendering":
        return dict(common, conclusion=copy.deepcopy(conclusion))
    raise AssertionError(f"unsupported fixture fact type: {fact_type}")


def _fact_for(row: dict, *, fact_type: str = "governor_relation") -> dict:
    occurrence = row["occurrence"]
    return {
        "fact_id": "sha256:" + hashlib.sha256(
            (fact_type + occurrence["quran_loc"]).encode("utf-8")
        ).hexdigest(),
        "fact_type": fact_type,
        "fact_value": _fact_value_for(row, fact_type),
        "surface_spans": [{
            "quran_loc": occurrence["quran_loc"],
            "surface": occurrence["surface"],
        }],
        "evidence_mode": "direct_source_attestation",
        "source_evidence": {
            "source_addresses": [{
                "address": occurrence["quran_loc"],
                "source_kind": "quran_token",
            }],
            "source_quotation": "fixture quotation",
        },
        "source_address": {
            "address": occurrence["quran_loc"],
            "source_kind": "quran_token",
        },
        "dependencies": {"fact_ids": [], "source_addresses": []},
        "derivation_chain": [],
        "contradiction_records": [],
        "defeaters": [],
        "dependent_fact_ids": [],
        "dependent_projection_ids": ["projection:test"],
        "evidence": {"evidence_ids": [row["artifact_id"]]},
    }


def _errors(fact: dict, row: dict) -> list[str]:
    return certifier.evidence_bundle_errors(fact, {}, two_vote_row=row)


class TwoVoteClaimBindingTests(unittest.TestCase):
    def test_exact_v1_and_v11_claims_pass_for_every_two_vote_fact_type(self) -> None:
        for row in (two_vote.sample_verified_row(), two_vote.sample_verified_row_v11()):
            for fact_type in certifier.TWO_VOTE_FACT_TYPES:
                with self.subTest(schema=row["schema"], fact_type=fact_type):
                    self.assertEqual([], _errors(_fact_for(row, fact_type=fact_type), row))

    def test_same_occurrence_different_fact_value_is_refused(self) -> None:
        for row in (two_vote.sample_verified_row(), two_vote.sample_verified_row_v11()):
            with self.subTest(schema=row["schema"]):
                fact = _fact_for(row)
                fact["fact_value"]["governor"]["surface"] = "قَالَ"
                self.assertTrue(
                    any("two-vote claim" in error for error in _errors(fact, row)),
                    _errors(fact, row),
                )

    def test_same_value_under_different_fact_type_is_refused(self) -> None:
        for row in (two_vote.sample_verified_row(), two_vote.sample_verified_row_v11()):
            with self.subTest(schema=row["schema"]):
                fact = _fact_for(row)
                fact["fact_type"] = "contextual_function"
                self.assertTrue(
                    any("two-vote claim" in error for error in _errors(fact, row)),
                    _errors(fact, row),
                )

    def test_wrong_reason_key_is_refused(self) -> None:
        rows = (
            (two_vote.sample_verified_row(), "inna-ism-nasb-fatha"),
            (two_vote.sample_verified_row_v11(), "fail-of-amana-nominative-visible-damma"),
        )
        for row, wrong_reason in rows:
            with self.subTest(schema=row["schema"]):
                fact = _fact_for(row)
                fact["fact_value"]["reason_key"] = wrong_reason
                self.assertTrue(
                    any("two-vote claim" in error for error in _errors(fact, row)),
                    _errors(fact, row),
                )

    def test_same_location_different_written_surface_is_refused(self) -> None:
        for row in (two_vote.sample_verified_row(), two_vote.sample_verified_row_v11()):
            with self.subTest(schema=row["schema"]):
                fact = _fact_for(row)
                fact["surface_spans"][0]["surface"] = "مَا"
                self.assertTrue(
                    any("two-vote claim" in error for error in _errors(fact, row)),
                    _errors(fact, row),
                )

    def test_v11_uncompared_prose_does_not_change_the_governed_claim(self) -> None:
        row = two_vote.sample_verified_row_v11()
        row["votes"][1]["conclusion"]["attachment"] = "different reviewer prose"
        artifact_errors: list[str] = []
        two_vote.validate_row(row, 1, artifact_errors)
        self.assertEqual([], artifact_errors)
        fact = _fact_for(row)
        self.assertEqual([], _errors(fact, row))

    def test_v11_contract_whitespace_normalization_is_mirrored(self) -> None:
        row = two_vote.sample_verified_row_v11()
        conclusion = row["votes"][1]["conclusion"]
        conclusion["function"] = f"  {conclusion['function']}  "
        conclusion["attachment_key"] = f"  {conclusion['attachment_key']}  "
        conclusion["governed_expression"] = "  "
        conclusion["governor"]["surface"] = f"  {conclusion['governor']['surface']}  "
        conclusion["governor"]["normalized_surface"] = "  "
        artifact_errors: list[str] = []
        two_vote.validate_row(row, 1, artifact_errors)
        self.assertEqual([], artifact_errors)
        self.assertEqual([], _errors(_fact_for(row), row))

    def test_trail_reopens_current_two_vote_bundle_and_revocation_closes_legacy_gap(self) -> None:
        row = two_vote.sample_verified_row_v11()
        fact = _fact_for(row)
        fact["fact_value"]["reason_key"] = "legacy-location-only-certification"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle_path = root / "votes.jsonl"
            bundle_path.write_text(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            store = certifier.TypedFactCertificationStore(root / "store")
            store.register(
                fact,
                contract_id="fixture:two-vote",
                actor="fixture",
                timestamp="2026-08-02T00:00:00Z",
            )
            store.transition(
                fact["fact_id"],
                "review_required",
                actor="fixture",
                timestamp="2026-08-02T00:00:01Z",
                reason="legacy fixture under review",
            )
            store._append_event({
                "event_type": "transition",
                "fact_id": fact["fact_id"],
                "contract_id": "fixture:two-vote",
                "fact_type": fact["fact_type"],
                "evidence_mode": fact["evidence_mode"],
                "from_status": "review_required",
                "to_status": "certified",
                "actor": "legacy-fixture",
                "timestamp": "2026-08-02T00:00:02Z",
                "reason": "historical location-only acceptance",
                "evidence_bundle_ref": {
                    "two_vote_artifact_id": row["artifact_id"],
                    "two_vote_bundle": str(bundle_path),
                },
                "triggered_by": None,
            })
            errors = store.validate_trail()
            self.assertTrue(
                any("current two-vote certification" in error for error in errors),
                errors,
            )
            store.revoke(
                fact["fact_id"],
                actor="migration",
                timestamp="2026-08-02T00:00:03Z",
                reason="legacy claim is not exactly vote-bound",
            )
            self.assertEqual([], store.validate_trail())

    def test_dependency_rebind_is_append_only_and_changes_effective_payload(self) -> None:
        source = certifier._synthetic_fact(
            "rebind-source", "sarf_form", "direct_source_attestation"
        )
        legacy = certifier._synthetic_fact(
            "rebind-legacy", "sarf_form", "direct_source_attestation"
        )
        successor = certifier._synthetic_fact(
            "rebind-successor", "sarf_form", "direct_source_attestation"
        )
        source["dependent_fact_ids"] = [legacy["fact_id"]]
        with tempfile.TemporaryDirectory() as td:
            store = certifier.TypedFactCertificationStore(td)
            for fact in (source, legacy, successor):
                store.register(
                    fact,
                    contract_id="fixture:dependency-rebind",
                    actor="fixture",
                    timestamp="2026-08-02T00:00:00Z",
                )
            store.rebind_dependents(
                source["fact_id"],
                [successor["fact_id"]],
                actor="migration",
                timestamp="2026-08-02T00:00:01Z",
                reason="legacy fact superseded",
            )
            effective = store.state()[source["fact_id"]]["fact"]
            self.assertEqual([successor["fact_id"]], effective["dependent_fact_ids"])
            events = store._events()
            self.assertEqual("dependency_rebind", events[-1]["event_type"])
            self.assertEqual([], store.validate_trail())


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TwoVoteClaimBindingTests)
    )
    if result.wasSuccessful():
        print("CERTIFY TYPED FACT CLAIM-BINDING TESTS PASS")
    raise SystemExit(0 if result.wasSuccessful() else 1)
