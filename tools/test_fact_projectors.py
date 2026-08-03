#!/usr/bin/env python3
"""End-to-end tests for registered fact-family projectors."""

from __future__ import annotations

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
from tools import largelexicon_common  # noqa: E402
from tools import fact_projectors  # noqa: E402


ENTRIES_PATH = ROOT / "qamus" / "data" / "current" / "entries.jsonl"
PROJECTOR_SCHEMA = ROOT / "qamus" / "schemas" / "projector-record.schema.json"
NOW = "2026-07-11T12:00:00Z"
LATER = "2026-07-11T12:30:00Z"


def identity(loc: str, entry_id: str = "entry-v001") -> dict:
    return {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": entry_id,
        "card_id": "card-" + loc.replace(":", "-"),
        "qword_row_id": "qword-" + loc.replace(":", "-"),
    }


def source_row(
    *,
    family: str,
    value: object,
    surface: str,
    entry_id: str = "entry-v001",
    created_from: str | None = None,
) -> dict:
    fact_type = "sarf_form" if family == "sarf" else "particle_function"
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "lexeme" if family == "sarf" else "construction",
        "subject_identity": {
            "ref_type": "lexeme" if family == "sarf" else "construction",
            "id": ("lexeme:" if family == "sarf" else "particle:") + entry_id,
        },
        "fact_type": fact_type,
        "candidate_or_value": {
            "value": value,
            "competing_alternatives": [],
            "semantic_tie": False,
        },
        "scope": "lexeme_global" if family == "sarf" else "rule_global",
        "source_address": {
            "address": "qamus-entry:%s:%s" % (entry_id, surface),
            "source_kind": "qamus_entry_field",
        },
        "evidence": [
            {
                "evidence_id": "ev-source-" + family,
                "type": "source_quote",
                "detail": "fixture-certified source fact for projector testing",
            }
        ],
        "provenance": {
            "actor": "test-suite",
            "method": "fixture",
            "created_at": NOW,
            "input_hashes": {"fixture": "sha256:" + "1" * 64},
        },
        "review_votes": [],
        "certification_state": "candidate",
        "confidence_or_calibration": None,
        "defeaters": [],
        "exceptions": [],
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": created_from,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def votes(evidence_ref: str, prefix: str = "reviewer") -> list[dict]:
    return [
        {
            "voter_id": prefix + "-a",
            "vote": "approve",
            "evidence_ref": evidence_ref,
            "independent": True,
        },
        {
            "voter_id": prefix + "-b",
            "vote": "approve",
            "evidence_ref": evidence_ref,
            "independent": True,
        },
    ]


def certify_source(store: fact_ledger.FactLedgerStore, row: dict) -> dict:
    stored = store.append(row)
    store.transition(stored["fact_id"], "review_required")
    return store.transition(
        stored["fact_id"],
        "certified",
        review_votes=votes(stored["evidence"][0]["evidence_id"], "source-reviewer"),
    )


def sarf_occurrences(entry_id: str = "entry-v001") -> list[dict]:
    return [
        {"identity": identity("9:69:1", entry_id), "surface": "خُضْتُمْ"},
        {"identity": identity("9:69:2", entry_id), "surface": "نَزَلَ"},
        {"identity": identity("9:69:3", entry_id), "surface": "يخوضون"},
        {
            "identity": identity("9:69:4", entry_id),
            "surface": "خُضْتُمْ",
            "clitics": ["و"],
        },
    ]


def sarf_forms(entry_id: str = "entry-v001", form: str = "I") -> list[dict]:
    return [
        {
            "form_id": "form-khudtum",
            "entry_id": entry_id,
            "surface": "خُضْتُمْ",
            "sarf_form": form,
            "clitics": [],
            "liaison": False,
        },
        {
            "form_id": "form-yakhudun",
            "entry_id": entry_id,
            "surface": "يَخُوضُون",
            "sarf_form": form,
            "clitics": [],
            "liaison": False,
        },
        {
            "form_id": "form-nazzala",
            "entry_id": entry_id,
            "surface": "نَزَّلَ",
            "sarf_form": "II",
            "clitics": [],
            "liaison": False,
        },
    ]


def nahw_occurrences(entry_id: str = "particle-min") -> list[dict]:
    return [
        {
            "identity": identity("2:1:1", entry_id),
            "surface": "مِنْ",
            "context": {"next_pos": "noun"},
        },
        {
            "identity": identity("2:1:2", entry_id),
            "surface": "مَنْ",
            "context": {"next_pos": "noun"},
        },
    ]


def min_pattern(function: str = "preposition_from") -> list[dict]:
    return [
        {
            "pattern_id": "pattern-min-before-noun",
            "particle_surface": "مِنْ",
            "function": function,
            "context_equals": {"next_pos": "noun"},
        }
    ]


class RegistryTests(unittest.TestCase):
    def test_default_registry_contracts_are_data_inspectable_and_schema_valid(self):
        contracts = fact_projectors.REGISTRY.list_contracts()
        self.assertEqual(
            {
                fact_projectors.SARF_PROJECTOR_ID,
                fact_projectors.NAHW_PROJECTOR_ID,
                fact_projectors.SARF_GENERATED_PROJECTOR_ID,
                fact_projectors.TRANCHE1_SARF_PROJECTOR_ID,
                fact_projectors.TRANCHE1_NAHW_PROJECTOR_ID,
                fact_projectors.FAM2_LEXICAL_PROJECTOR_ID,
                fact_projectors.FAM3_NUMBER_PROJECTOR_ID,
                fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID,
                fact_projectors.LARGELEXICON_ABSTENTION_PROJECTOR_ID,
                fact_projectors.FAM4_FINITE_VERB_PROJECTOR_ID,
                fact_projectors.FAM5_DERIVED_VERB_PROJECTOR_ID,
                fact_projectors.PROOFV_VERB_PROJECTOR_ID,
                fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
                fact_projectors.NOUN_LEXICAL_GENDER_PROJECTOR_ID,
            },
            {item["projector_id"] for item in contracts},
        )
        for contract in contracts:
            self.assertEqual([], fact_projectors.validate_projector_record(contract))
            self.assertTrue(contract["defeater_checks"])
            self.assertIn(contract["gate_tier"], fact_projectors.load_gate_tiers())

    def test_fam3_number_projector_reuses_registered_pattern_and_abstains(self):
        from tools import fam3_number_producer

        registry = fam3_number_producer.load_pattern_registry(
            ROOT / "qamus" / "examples" / "fam3-numbers" / "pattern-registry.jsonl"
        )
        candidate = fact_projectors.REGISTRY.run(
            fact_projectors.FAM3_NUMBER_PROJECTOR_ID,
            base_surface="أَلْف",
            observed_surface="أُلُوف",
            pattern_id="cardinal.base_to_number_form",
            context={"entry_direct": True},
            pattern_registry=registry,
        )
        self.assertEqual("candidate", candidate["status"])
        self.assertEqual("formation_evidence", candidate["candidate"]["fact_type"])
        abstained = fact_projectors.REGISTRY.run(
            fact_projectors.FAM3_NUMBER_PROJECTOR_ID,
            base_surface="أَلْف",
            observed_surface="أُلُوف",
            pattern_id="cardinal.base_to_number_form",
            context={"entry_direct": False},
            pattern_registry=registry,
        )
        self.assertEqual("abstained", abstained["status"])
        self.assertFalse(abstained["materialization_allowed"])

    def test_missing_defeater_list_and_unregistered_projector_fail_closed(self):
        contract = copy.deepcopy(fact_projectors.REGISTRY.list_contracts()[0])
        contract["defeater_checks"] = []
        with self.assertRaisesRegex(fact_projectors.ProjectorValidationError, "defeater"):
            fact_projectors.ProjectorRegistry().register(contract, lambda **_: {})
        contract["defeater_checks"] = ["not_a_real_defeater_function"]
        with self.assertRaisesRegex(fact_projectors.ProjectorValidationError, "callable"):
            fact_projectors.ProjectorRegistry().register(contract, lambda **_: {})
        with self.assertRaisesRegex(fact_projectors.ProjectorValidationError, "unregistered"):
            fact_projectors.REGISTRY.run("projector:not-registered")

    def test_cli_lists_projector_contracts(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fact_projectors.py"), "list", "--json"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        listed = json.loads(result.stdout)
        self.assertEqual(len(fact_projectors.REGISTRY.list_contracts()), len(listed))
        self.assertIn("compatibility_class", listed[0])

    def test_projector_record_schema_is_pretty_and_accepts_both_record_kinds(self):
        raw = PROJECTOR_SCHEMA.read_text(encoding="utf-8")
        self.assertTrue(raw.endswith("\n"))
        self.assertGreater(len(raw.splitlines()), 20)
        self.assertEqual("object", json.loads(raw)["type"])
        self.assertEqual(
            [], fact_projectors.validate_projector_record(
                fact_projectors.REGISTRY.list_contracts()[0]
            )
        )

    def test_detached_certified_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            source = certify_source(
                fact_ledger.FactLedgerStore(first),
                source_row(family="sarf", value={"form": "I"}, surface="خَاضُوا"),
            )
            with self.assertRaisesRegex(fact_projectors.ProjectorValidationError, "current ledger"):
                fact_projectors.REGISTRY.run(
                    fact_projectors.SARF_PROJECTOR_ID,
                    store=fact_ledger.FactLedgerStore(second),
                    source_fact=source,
                    occurrences=sarf_occurrences()[:1],
                    documented_forms=sarf_forms(),
                    created_at=NOW,
                    started_at=NOW,
                    finished_at=LATER,
                    prior_candidates=[],
                )


class SarfProjectorTests(unittest.TestCase):
    def run_sarf(self, store, source, occurrences=None, forms=None, prior=None):
        return fact_projectors.REGISTRY.run(
            fact_projectors.SARF_PROJECTOR_ID,
            store=store,
            source_fact=source,
            occurrences=occurrences or sarf_occurrences(),
            documented_forms=forms or sarf_forms(),
            created_at=NOW,
            started_at=NOW,
            finished_at=LATER,
            prior_candidates=prior or [],
        )

    def test_candidate_never_enters_ledger_as_certified_without_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(Path(tmp) / "source")
            source = certify_source(
                store,
                source_row(family="sarf", value={"form": "I"}, surface="خَاضُوا"),
            )
            run = self.run_sarf(store, source)
            candidate = store.query(fact_id=run["candidates_generated"][0])[0]
            self.assertEqual("candidate", candidate["certification_state"])
            self.assertEqual("I", candidate["candidate_or_value"]["value"]["sarf_form"])

            illicit = copy.deepcopy(candidate)
            illicit["certification_state"] = "certified"
            illicit["review_votes"] = []
            with tempfile.TemporaryDirectory() as other:
                with self.assertRaisesRegex(fact_ledger.ValidationError, "new fact must begin as candidate"):
                    fact_ledger.FactLedgerStore(other).append(illicit)

    def test_each_sarf_defeater_fires_and_only_documented_exact_form_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            source = certify_source(
                store,
                source_row(family="sarf", value={"form": "I"}, surface="خَاضُوا"),
            )
            run = self.run_sarf(store, source)
            self.assertEqual(1, len(run["candidates_generated"]))
            by_loc = {item["subject_identity"]["loc"]: item for item in run["abstentions"]}
            self.assertEqual("homograph_norm_key_collision", by_loc["9:69:2"]["defeater_name"])
            self.assertEqual("harakah_blind_sole_candidate", by_loc["9:69:3"]["defeater_name"])
            self.assertEqual("liaison_clitic_mismatch", by_loc["9:69:4"]["defeater_name"])

    def test_sarf_full_cycle_and_correction_propagates_to_every_dependent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            old_source = certify_source(
                store,
                source_row(family="sarf", value={"form": "I"}, surface="خَاضُوا"),
            )
            dependents = [
                sarf_occurrences()[0],
                {"identity": identity("9:70:1"), "surface": "خُضْتُمْ"},
            ]
            first = self.run_sarf(store, old_source, occurrences=dependents, forms=sarf_forms())
            materialized = []
            for dependent_id in first["candidates_generated"]:
                materialized.append(
                    fact_projectors.review_and_materialize(
                        store,
                        dependent_id,
                        votes("ev-form-form-khudtum"),
                        "review-artifact:sarf-demo",
                        first,
                    )
                )
            self.assertEqual(2, len(materialized))
            self.assertTrue(
                all(row["certification_state"] == "materialized" for row in materialized)
            )
            self.assertEqual(2, len(first["certifications"]))
            self.assertEqual(2, len(first["materializations"]))

            store.transition(old_source["fact_id"], "superseded")
            new_source = certify_source(
                store,
                source_row(
                    family="sarf",
                    value={"form": "III"},
                    surface="خَاضُوا",
                    created_from=old_source["fact_id"],
                ),
            )
            second = self.run_sarf(
                store,
                new_source,
                occurrences=dependents,
                forms=sarf_forms(form="III"),
                prior=materialized,
            )
            replacements = [
                store.query(fact_id=fact_id)[0]
                for fact_id in second["candidates_generated"]
            ]
            old_ids = {row["fact_id"] for row in materialized}
            self.assertEqual(old_ids, {row["created_from"] for row in replacements})
            self.assertTrue(
                all(
                    row["dependency_hashes"]["source_fact"] == new_source["fact_id"]
                    for row in replacements
                )
            )
            self.assertEqual(old_ids, set(second["superseded_dependents"]))
            self.assertTrue(old_ids.isdisjoint(second["candidates_generated"]))
            self.assertEqual([], store.validate_all())

    def test_real_entries_read_only_smoke_projects_a_documented_verb_form(self):
        before = ENTRIES_PATH.stat().st_mtime_ns
        entry = None
        with ENTRIES_PATH.open(encoding="utf-8") as handle:
            for line in handle:
                candidate = json.loads(line)
                forms = largelexicon_common.forms_for_entry(candidate)
                if candidate.get("section") == "verb" and candidate.get("root") and forms:
                    entry = candidate
                    break
        self.assertIsNotNone(entry)
        form_rows = largelexicon_common.form_rows_for_lemmas(
            [largelexicon_common.entry_to_lemma(entry)]
        )
        documented = [
            {
                "form_id": row["form_id"],
                "entry_id": row["entry_id"],
                "surface": row["surface"],
                "sarf_form": "documented",
                "clitics": [],
                "liaison": False,
            }
            for row in form_rows
        ]
        occurrence = {
            "identity": identity("1:1:1", entry["id"]),
            "surface": documented[0]["surface"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            source = certify_source(
                store,
                source_row(
                    family="sarf",
                    value={"form": "documented", "root": entry["root"]},
                    surface=documented[0]["surface"],
                    entry_id=entry["id"],
                ),
            )
            run = self.run_sarf(
                store, source, occurrences=[occurrence], forms=documented
            )
            self.assertGreaterEqual(len(run["candidates_generated"]), 1)
        self.assertEqual(before, ENTRIES_PATH.stat().st_mtime_ns)


class NahwProjectorTests(unittest.TestCase):
    def run_nahw(self, store, source, occurrences=None, patterns=None, prior=None):
        return fact_projectors.REGISTRY.run(
            fact_projectors.NAHW_PROJECTOR_ID,
            store=store,
            source_fact=source,
            occurrences=occurrences or nahw_occurrences(),
            construction_patterns=patterns or min_pattern(),
            created_at=NOW,
            started_at=NOW,
            finished_at=LATER,
            prior_candidates=prior or [],
        )

    def test_man_min_vowel_defeater_and_two_vote_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            source = certify_source(
                store,
                source_row(
                    family="nahw",
                    value="preposition_from",
                    surface="مِنْ",
                    entry_id="particle-min",
                ),
            )
            run = self.run_nahw(store, source)
            self.assertEqual(1, len(run["candidates_generated"]))
            self.assertEqual("particle_vowel_distinction", run["abstentions"][0]["defeater_name"])
            with self.assertRaisesRegex(fact_projectors.ProjectorValidationError, "two independent"):
                fact_projectors.review_and_materialize(
                    store,
                    run["candidates_generated"][0],
                    [],
                    "review-artifact:nahw-demo",
                    run,
                )

    def test_ambiguous_la_stays_tie_unresolved(self):
        occurrence = {
            "identity": identity("2:2:1", "particle-la"),
            "surface": "لَا",
            "context": {},
        }
        patterns = [
            {
                "pattern_id": "pattern-la",
                "particle_surface": "لَا",
                "function": "simple_negation",
                "context_equals": {},
                "competing_functions": ["prohibition"],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            source = certify_source(
                store,
                source_row(
                    family="nahw",
                    value="simple_negation",
                    surface="لَا",
                    entry_id="particle-la",
                ),
            )
            run = self.run_nahw(store, source, [occurrence], patterns)
            self.assertEqual([], run["candidates_generated"])
            self.assertEqual("la_family_ambiguity", run["abstentions"][0]["defeater_name"])
            self.assertEqual("tie_unresolved", run["abstentions"][0]["resolution"])

    def test_nahw_full_cycle_and_correction_propagates_to_every_dependent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            old_source = certify_source(
                store,
                source_row(
                    family="nahw",
                    value="preposition_from",
                    surface="مِنْ",
                    entry_id="particle-min",
                ),
            )
            dependents = [
                nahw_occurrences()[0],
                {
                    "identity": identity("2:1:3", "particle-min"),
                    "surface": "مِنْ",
                    "context": {"next_pos": "noun"},
                },
            ]
            first = self.run_nahw(store, old_source, dependents, min_pattern())
            materialized = []
            for dependent_id in first["candidates_generated"]:
                materialized.append(
                    fact_projectors.review_and_materialize(
                        store,
                        dependent_id,
                        votes("ev-pattern-pattern-min-before-noun"),
                        "review-artifact:nahw-demo",
                        first,
                    )
                )
            self.assertEqual(2, len(materialized))

            store.transition(old_source["fact_id"], "superseded")
            new_source = certify_source(
                store,
                source_row(
                    family="nahw",
                    value="partitive_from",
                    surface="مِنْ",
                    entry_id="particle-min",
                    created_from=old_source["fact_id"],
                ),
            )
            second = self.run_nahw(
                store,
                new_source,
                dependents,
                min_pattern("partitive_from"),
                prior=materialized,
            )
            replacements = [
                store.query(fact_id=fact_id)[0]
                for fact_id in second["candidates_generated"]
            ]
            old_ids = {row["fact_id"] for row in materialized}
            self.assertEqual(old_ids, {row["created_from"] for row in replacements})
            self.assertTrue(
                all(
                    row["dependency_hashes"]["source_fact"] == new_source["fact_id"]
                    for row in replacements
                )
            )
            self.assertEqual(old_ids, set(second["superseded_dependents"]))
            self.assertEqual([], store.validate_all())


class FlywheelTests(unittest.TestCase):
    def test_run_record_has_required_instrumentation_and_aggregate_is_caller_timed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fact_ledger.FactLedgerStore(tmp)
            source = certify_source(
                store,
                source_row(family="sarf", value={"form": "I"}, surface="خَاضُوا"),
            )
            run = fact_projectors.REGISTRY.run(
                fact_projectors.SARF_PROJECTOR_ID,
                store=store,
                source_fact=source,
                occurrences=sarf_occurrences()[:1],
                documented_forms=sarf_forms(),
                created_at=NOW,
                started_at=NOW,
                finished_at=LATER,
                prior_candidates=[],
            )
            self.assertEqual([], fact_projectors.validate_projector_record(run))
            for key in (
                "projector_id",
                "version",
                "inputs",
                "candidates_generated",
                "abstentions",
                "certifications",
                "review_votes",
                "runtime_ms",
                "resolution_method",
            ):
                self.assertIn(key, run)
            metrics = fact_projectors.aggregate_projection_runs([run])
            self.assertEqual(2.0, metrics["facts_per_hour"])
            self.assertEqual(1, metrics["candidate_count"])


class LargelexiconBridgeRegistrationTest(unittest.TestCase):
    """The A3 bridge must be registered fail-closed and have no certification path."""

    def setUp(self) -> None:
        from tools import largelexicon_fact_bridge

        self.bridge = largelexicon_fact_bridge
        self.contract = fact_projectors.REGISTRY.contract(
            fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID
        )

    def test_registered_with_never_auto_resolve(self):
        self.assertEqual("never_auto_resolve", self.contract["gate_tier"])
        self.assertEqual([], fact_projectors.validate_projector_record(self.contract))
        self.assertIn("never_auto_resolve", fact_projectors.load_gate_tiers())
        self.assertEqual(
            "largelexicon_lexeme_candidate", self.contract["output_fact_type"]
        )

    def test_not_registered_behind_a_placeholder_lattice_predicate(self):
        """The lattice registry keys @2.1 skill-rule projectors; the bridge is not one.

        Registering it there would require a placeholder class_predicate, which
        would misrepresent the bridge's real class. The enforcing registration is
        this module's REGISTRY, where never_auto_resolve blocks certification.
        """

        registry = json.loads(
            (ROOT / "qamus" / "lattice" / "registered-projectors.json").read_text(encoding="utf-8")
        )
        entries = {item["projector_id"] for item in registry["registered"]}
        self.assertNotIn(fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID, entries)
        self.assertIn(
            fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID,
            {item["projector_id"] for item in fact_projectors.REGISTRY.list_contracts()},
        )

    def test_never_auto_resolve_blocks_certification(self):
        class _Store:
            def __init__(self, row):
                self.row = row

            def query(self, fact_id=None):
                return [self.row] if fact_id == self.row["fact_id"] else []

        row = {"fact_id": "sha256:" + "0" * 64, "fact_type": self.contract["output_fact_type"]}
        votes = [
            {"voter_id": "a", "independent": True, "vote": "approve"},
            {"voter_id": "b", "independent": True, "vote": "approve"},
        ]
        with self.assertRaises(fact_projectors.ProjectorValidationError) as caught:
            fact_projectors.review_and_materialize(_Store(row), row["fact_id"], votes, "target", {})
        self.assertIn("never_auto_resolve", str(caught.exception))

    def test_registry_run_is_candidate_or_abstention_only(self):
        result = fact_projectors.REGISTRY.run(
            fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID,
            crosswalk_row=self.bridge.fixture_crosswalk_row(),
            inputs=self.bridge.fixture_inputs(),
        )
        self.assertEqual("candidate", result["status"])
        self.assertFalse(result["materialization_allowed"])
        self.assertFalse(result["certification_allowed"])
        record = result["typed_claim_record"]
        self.assertFalse(record["projection"]["learner_visible"])
        self.assertTrue(
            all(fact["certification"]["status"] != "certified" for fact in record["facts"])
        )

    def test_committed_fixtures_are_fresh(self):
        self.assertEqual([], self.bridge.check_fixtures())

    def test_bridge_behavioural_suite_runs(self):
        """Gate the FULL A3 mutation suite from the harness-run projector tests.

        Collection happens at call time: a frozen module-import snapshot silently
        drops every test appended after it, which is exactly how the harness came
        to run 20 of 41. The count is also asserted against the module's own
        dynamic discovery so the two can never diverge again.
        """

        from tools import test_largelexicon_fact_bridge as suite

        collected = suite.all_tests()
        self.assertEqual(len(collected), len(suite.all_tests()))
        self.assertGreaterEqual(
            len(collected), suite.EXPECTED_MINIMUM_TESTS,
            "the bridge suite shrank below its declared minimum",
        )
        names = {test.__name__ for test in collected}
        for critical in suite.CRITICAL_PROBES:
            self.assertIn(critical, names, "critical bridge probe is missing: " + critical)
        for test in collected:
            with self.subTest(test=test.__name__):
                test()


QURAN_LOC_SURFACE_INDEX_PATH = ROOT / "qamus" / "indexes" / "quran-loc-surface" / "index.jsonl"


def loc_surface(loc: str) -> str:
    with QURAN_LOC_SURFACE_INDEX_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["loc"] == loc:
                return row["surface"]
    raise KeyError(loc)


def noun_occurrence(loc: str) -> dict:
    return {"identity": {"loc": loc}, "surface": loc_surface(loc)}


class NounPluralGenderProjectorTests(unittest.TestCase):
    """u-s08 Train A: broken-plural lexeme-link + lexical-gender-registry projectors."""

    def test_broken_plural_without_attested_pair_abstains(self):
        occurrence = noun_occurrence("2:25:12")
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ن ه ر", template_id="taksir-afal",
            attested_plurals=[],
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("no_attested_lexeme_pair", result["abstention"]["reason"])
        self.assertIsNone(result["candidate"])

    def test_multiple_attested_plurals_remain_unranked(self):
        occurrence = noun_occurrence("7:194:7")
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ع ب د", template_id="taksir-fiaal",
            attested_plurals=[occurrence["surface"], "عَبِيد"],
        )
        self.assertEqual("candidate", result["status"])
        self.assertTrue(result["candidate"]["semantic_tie"])
        self.assertEqual(["عَبِيد"], result["candidate"]["competing_alternatives"])
        self.assertNotIn("rank", result["candidate"])

    def test_lexical_feminine_requires_registry_evidence(self):
        no_marker = noun_occurrence("18:17:2")  # الشمس -- feminine, no ta marbuta
        with_marker = noun_occurrence("31:27:6")  # شجرة -- feminine, has ta marbuta
        for occurrence in (no_marker, with_marker):
            abstained = fact_projectors.REGISTRY.run(
                fact_projectors.NOUN_LEXICAL_GENDER_PROJECTOR_ID,
                occurrence=occurrence, gender_registry_entry=None,
            )
            self.assertEqual("abstained", abstained["status"])
            self.assertEqual("lexical_gender_registry_missing", abstained["abstention"]["reason"])

            certified = fact_projectors.REGISTRY.run(
                fact_projectors.NOUN_LEXICAL_GENDER_PROJECTOR_ID,
                occurrence=occurrence, gender_registry_entry="feminine",
            )
            self.assertEqual("candidate", certified["status"])
            self.assertEqual("feminine", certified["candidate"]["gender"])

    def test_noun_projector_records_lexeme_link_abstention(self):
        occurrence = noun_occurrence("33:35:2")
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="س ل م", template_id="msl-genitive-accusative",
            attested_plurals=[],
        )
        self.assertEqual("abstained", result["status"])
        self.assertIsNone(result["candidate"])
        abstention = result["abstention"]
        self.assertEqual({"subject_identity", "reason", "detail", "dependencies"}, set(abstention))
        self.assertEqual(occurrence["identity"], abstention["subject_identity"])
        self.assertEqual("sound_plural_suffix_not_broken_template", abstention["reason"])
        self.assertTrue(abstention["detail"])
        self.assertTrue(abstention["dependencies"])

    def test_noun_projector_never_certifies_generated_plural(self):
        # A paradigm-GENERATED surface (never sourced/attested) must not be
        # admitted as an attested pair merely because a generator produced it.
        from tools import fusha_paradigm_generate as generator

        generated_rows = generator.generate_noun_plural(
            {"pos": "noun", "lemma": "قَلَم", "root": "ق ل م", "plural_template_id": "taksir-afal"}
        )
        self.assertTrue(generated_rows)
        generated_surface = generated_rows[0]["value"]["generated_surface"]

        occurrence = noun_occurrence("2:25:12")
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ق ل م", template_id="taksir-afal",
            attested_plurals=[generated_surface],
        )
        self.assertEqual("abstained", result["status"])
        self.assertNotEqual("certified", result["status"])
        self.assertFalse(result["certification_allowed"])
        self.assertFalse(result["materialization_allowed"])

        # structural: across every scenario this projector can reach, status is
        # only ever candidate or abstained -- never certified.
        for scenario in (
            dict(occurrence=noun_occurrence("2:25:12"), root="ن ه ر", template_id="taksir-afal",
                 attested_plurals=[loc_surface("2:25:12")]),
            dict(occurrence=noun_occurrence("33:35:2"), root="س ل م",
                 template_id="msl-genitive-accusative", attested_plurals=[]),
        ):
            outcome = fact_projectors.REGISTRY.run(
                fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID, **scenario
            )
            self.assertIn(outcome["status"], ("candidate", "abstained"))
            self.assertFalse(outcome["certification_allowed"])
            self.assertFalse(outcome["materialization_allowed"])

    def test_loc_surface_mismatch_abstains_before_any_other_evidence(self):
        occurrence = {"identity": {"loc": "2:25:12"}, "surface": loc_surface("2:25:18")}
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ن ه ر", template_id="taksir-afal",
            attested_plurals=[occurrence["surface"]],
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("loc_surface_mismatch", result["abstention"]["reason"])

    # -- Train A review-repair (finding #1): rare/second-order licences are the exact (lexeme_id, root) pair --

    def test_rare_lexeme_licensed_by_exact_pair_only(self):
        occurrence = noun_occurrence("4:11:11")  # نِسَآءً
        licensed = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="م ر أ", template_id="taksir-nisa-suppletive-rare",
            attested_plurals=[occurrence["surface"]], lexeme_id="امرأة",
        )
        self.assertEqual("candidate", licensed["status"])

    def test_rare_lexeme_hostile_no_kwarg_wrong_root_wrong_lexeme_all_abstain(self):
        occurrence = noun_occurrence("4:11:11")
        base = dict(occurrence=occurrence, root="م ر أ", template_id="taksir-nisa-suppletive-rare",
                   attested_plurals=[occurrence["surface"]])
        no_kwarg = fact_projectors.REGISTRY.run(fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID, **base)
        self.assertEqual("abstained", no_kwarg["status"])
        self.assertEqual("rare_plural_unlicensed", no_kwarg["abstention"]["reason"])

        wrong_root = dict(base)
        wrong_root["root"] = "ك ل ب"
        wrong_root_result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID, lexeme_id="امرأة", **wrong_root
        )
        self.assertEqual("abstained", wrong_root_result["status"])
        self.assertEqual("rare_plural_unlicensed", wrong_root_result["abstention"]["reason"])

        wrong_lexeme = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID, lexeme_id="كلب", **base
        )
        self.assertEqual("abstained", wrong_lexeme["status"])
        self.assertEqual("rare_plural_unlicensed", wrong_lexeme["abstention"]["reason"])

    def test_plural_of_plural_base_attested_defaults_false(self):
        # a caller who forgets plural_of_plural_base_attested entirely must NOT get a free candidate: this
        # auxiliary evidence fails closed (finding #1), never defaults permissively.
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=noun_occurrence("2:25:12"), root="ب ي ت", template_id="taksir-jam-al-jam-fuulaat",
            attested_plurals=[loc_surface("2:25:12")], lexeme_id="بيت",
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("plural_of_plural_base_unattested", result["abstention"]["reason"])

    # -- finding #3: harakah-blind / wrong-vocalization attested-pair matches never certify --

    def test_wrong_vocalization_attested_entry_abstains_not_certifies(self):
        occurrence = noun_occurrence("12:110:4")  # ٱلرُّسُلُ
        # flip the damma on the second radical (س) to a sukun -- a plausible wrong-vocalization typo, produced
        # by exact character surgery (never hand-typed Arabic, which risks an invisible combining-mark-order
        # mismatch against the canonical surface).
        chars = list(occurrence["surface"])
        seen_index = occurrence["surface"].index("س")
        self.assertEqual(chars[seen_index + 1], "ُ")  # damma
        chars[seen_index + 1] = "ْ"  # sukun
        wrong_vocalization = "".join(chars)
        self.assertNotEqual(wrong_vocalization, occurrence["surface"])
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ر س ل", template_id="taksir-fual",
            attested_plurals=[wrong_vocalization],
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("attested_pair_vocalization_mismatch", result["abstention"]["reason"])

    def test_bare_attested_entry_is_recall_only_never_a_false_candidate(self):
        occurrence = noun_occurrence("9:18:3")  # مَسَٰجِدَ
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="س ج د", template_id="taksir-mafail",
            attested_plurals=["مساجد"],  # bare skeleton, not the byte-exact documented surface
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("no_attested_lexeme_pair", result["abstention"]["reason"])

    # -- finding #7: semantic_tie and competing_alternatives share one canonical key --

    def test_semantic_tie_and_competing_alternatives_share_one_key(self):
        occurrence = noun_occurrence("7:194:7")
        single = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ع ب د", template_id="taksir-fiaal",
            attested_plurals=[occurrence["surface"]],
        )
        self.assertEqual("candidate", single["status"])
        self.assertEqual([], single["candidate"]["competing_alternatives"])
        self.assertFalse(single["candidate"]["semantic_tie"])  # zero rivals -> never a tie

        multi = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ع ب د", template_id="taksir-fiaal",
            attested_plurals=[occurrence["surface"], "عَبِيد"],
        )
        self.assertTrue(multi["candidate"]["semantic_tie"])
        self.assertEqual(["عَبِيد"], multi["candidate"]["competing_alternatives"])

    # -- finding #8: an unknown plural_template_id abstains typed, never raises --

    def test_unknown_template_id_abstains_typed_never_raises(self):
        occurrence = noun_occurrence("2:25:12")
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ق ل م", template_id="taksir-does-not-exist",
            attested_plurals=[occurrence["surface"]],
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("unknown_plural_template_id", result["abstention"]["reason"])

    # -- finding #10: malformed root evidence is validated, not merely "non-empty" --

    def test_malformed_root_evidence_abstains_no_root_evidence(self):
        from tools import rm40_gate_stack as gates
        self.assertFalse(gates.is_valid_root_evidence("ق"))
        self.assertFalse(gates.is_valid_root_evidence("ق 5 م"))
        self.assertFalse(gates.is_valid_root_evidence(None))
        self.assertTrue(gates.is_valid_root_evidence("ق ل م"))
        occurrence = noun_occurrence("2:25:12")
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=occurrence, root="ن", template_id="taksir-afal",
            attested_plurals=[occurrence["surface"]],
        )
        self.assertEqual("abstained", result["status"])
        self.assertEqual("no_root_evidence", result["abstention"]["reason"])

    # -- finding #6: rules_payload is no longer a public gate parameter --

    def test_rules_payload_removed_from_public_gate_signatures(self):
        import inspect
        from tools import rm40_gate_stack as gates
        gate_params = set(inspect.signature(gates.broken_plural_lexeme_link_gate).parameters)
        gender_params = set(inspect.signature(gates.lexical_gender_gate).parameters)
        self.assertNotIn("rules_payload", gate_params)
        self.assertNotIn("rules_payload", gender_params)
        # a private, test-only seam still exists for mutation proofs (module-level, never a public kwarg)
        self.assertTrue(callable(gates._load_plural_gender_rules))

    # -- finding #5: gate_tier is never_auto_resolve for both output fact types --

    def test_gate_tier_never_auto_resolve_for_both_fact_types(self):
        self.assertEqual("never_auto_resolve", fact_projectors.NOUN_PLURAL_LEXEME_LINK_CONTRACT["gate_tier"])
        self.assertEqual("never_auto_resolve", fact_projectors.NOUN_LEXICAL_GENDER_CONTRACT["gate_tier"])

    def test_review_and_materialize_refuses_plural_lexeme_link_evidence(self):
        class _Store:
            def __init__(self, row):
                self.row = row

            def query(self, fact_id=None):
                return [self.row] if fact_id == self.row["fact_id"] else []

        row = {"fact_id": "sha256:" + "1" * 64,
              "fact_type": fact_projectors.NOUN_PLURAL_LEXEME_LINK_CONTRACT["output_fact_type"]}
        approvals = [
            {"voter_id": "a", "independent": True, "vote": "approve"},
            {"voter_id": "b", "independent": True, "vote": "approve"},
        ]
        with self.assertRaises(fact_projectors.ProjectorValidationError) as caught:
            fact_projectors.review_and_materialize(_Store(row), row["fact_id"], approvals, "target", {})
        self.assertIn("never_auto_resolve", str(caught.exception))

    def test_review_and_materialize_refuses_lexical_gender_evidence(self):
        class _Store:
            def __init__(self, row):
                self.row = row

            def query(self, fact_id=None):
                return [self.row] if fact_id == self.row["fact_id"] else []

        row = {"fact_id": "sha256:" + "2" * 64,
              "fact_type": fact_projectors.NOUN_LEXICAL_GENDER_CONTRACT["output_fact_type"]}
        approvals = [
            {"voter_id": "a", "independent": True, "vote": "approve"},
            {"voter_id": "b", "independent": True, "vote": "approve"},
        ]
        with self.assertRaises(fact_projectors.ProjectorValidationError) as caught:
            fact_projectors.review_and_materialize(_Store(row), row["fact_id"], approvals, "target", {})
        self.assertIn("never_auto_resolve", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
