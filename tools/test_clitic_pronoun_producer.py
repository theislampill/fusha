#!/usr/bin/env python3
"""Red-first contract tests for the FB1 clitic-pronoun producer."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import typed_claim_contract as tcc  # noqa: E402
from tools import build_clitic_pronoun_producer as producer  # noqa: E402


def row(
    surface: str,
    segments: list[dict],
    *,
    loc: str = "1:1:1",
    **extra: object,
) -> dict:
    value = {
        "loc": loc,
        "quran_loc": "quran:" + loc,
        "wbw_loc": "wbw:" + loc,
        "surface": surface,
        "morphology_family": "clitic_pronoun_compositions",
        "segments": segments,
    }
    value.update(extra)
    return value


def segment(index: int, surface: str, role: str, klass: str) -> dict:
    return {
        "segment_index": index,
        "surface": surface,
        "role": role,
        "class": klass,
    }


class FB1ProducerTests(unittest.TestCase):
    def assert_valid(self, record: dict) -> None:
        self.assertEqual([], tcc.validate_contract_record(record))

    def test_basic_host_and_attached_pronoun_is_a_typed_candidate(self):
        record = producer.produce_record(
            row(
                "وَكِتَابُهُ",
                [
                    segment(0, "وَ", "prefix_conjunction", "qg-conjunction"),
                    segment(1, "كِتَابُ", "host", "qg-noun-stem"),
                    segment(2, "هُ", "attached_pronoun", "qg-possessive-pronoun"),
                ],
            )
        )
        self.assertEqual("candidate", record["projection"]["status"])
        self.assertIn("clitic_composition", {fact["fact_type"] for fact in record["facts"]})
        self.assertTrue(all(fact["surface_spans"] for fact in record["facts"]))
        self.assert_valid(record)

    def test_protective_nun_is_explicit_sarf_fact_and_never_particle(self):
        record = producer.produce_record(
            row(
                "فَٱرْهَبُونِ",
                [
                    segment(0, "فَ", "prefix_result_fa", "qg-result-fa"),
                    segment(1, "ٱرْهَبُ", "verb_stem", "qg-verb-stem"),
                    segment(2, "و", "subject_suffix_2mp", "qg-subject-pronoun"),
                    {
                        **segment(3, "نِ", "protective_nun", "qg-protective-nun"),
                        "typed_kind": "sarf.protective_nun",
                    },
                ],
            )
        )
        protective = [fact for fact in record["facts"] if fact["fact_type"] == "protective_nun"]
        self.assertEqual(1, len(protective))
        self.assertEqual("sarf.protective_nun", protective[0]["fact_value"]["typed_kind"])
        self.assertNotIn("particle", protective[0]["fact_value"].get("class", ""))
        self.assertEqual("candidate", record["projection"]["status"])
        self.assert_valid(record)

    def test_idgham_A_and_B_require_explicit_byte_clean_boundary(self):
        for boundary_class in ("A_clean_split", "B_shared_letter_clean_split"):
            record = producer.produce_record(
                row(
                    "ٱلشَّمْسِ",
                    [
                        segment(0, "ٱل", "definite_article", "qg-article"),
                        segment(1, "شَّمْسِ", "noun_stem", "qg-noun-stem"),
                    ],
                    idgham_boundary={
                        "boundary_class": boundary_class,
                        "byte_clean": True,
                        "source_fact_id": "fixture:idgham:" + boundary_class,
                    },
                )
            )
            self.assertEqual("candidate", record["projection"]["status"])
            self.assertIn("idgham_boundary", {fact["fact_type"] for fact in record["facts"]})
            self.assert_valid(record)

    def test_idgham_C_fused_boundary_abstains_with_route(self):
        record = producer.produce_record(
            row(
                "مِّمَّنْ",
                [
                    segment(0, "مِّ", "preposition", "qg-preposition"),
                    segment(1, "مَّنْ", "relative_pronoun", "qg-pronoun"),
                ],
                idgham_boundary={
                    "boundary_class": "C_fused_boundary",
                    "byte_clean": False,
                    "route": "sarf.idgham_boundary_review",
                },
            )
        )
        self.assertNotEqual("candidate", record["projection"]["status"])
        self.assertEqual("C_fused_boundary", record["facts"][0]["fact_value"]["boundary_class"])
        self.assertEqual("sarf.idgham_boundary_review", record["facts"][0]["fact_value"]["route"])
        self.assert_valid(record)

    def test_idgham_D_or_unattested_shadda_boundary_abstains(self):
        record = producer.produce_record(
            row(
                "ٱلشَّمْسِ",
                [
                    segment(0, "ٱل", "definite_article", "qg-article"),
                    segment(1, "شَّمْسِ", "noun_stem", "qg-noun-stem"),
                ],
            )
        )
        self.assertNotEqual("candidate", record["projection"]["status"])
        self.assertIn("D_ambiguous_boundary", record["facts"][0]["fact_value"]["boundary_class"])
        self.assert_valid(record)

    def test_closed_class_function_word_does_not_project_spurious_root(self):
        record = producer.produce_record(
            row(
                "مِنْهُ",
                [
                    segment(0, "مِنْ", "preposition", "qg-preposition"),
                    segment(1, "هُ", "attached_pronoun", "qg-pronoun"),
                ],
                morphline="root م ن · preposition plus pronoun",
            )
        )
        self.assertNotEqual("candidate", record["projection"]["status"])
        self.assertTrue(any("closed_class" in item["blocker_id"] for item in record["facts"][0]["unresolved_blockers"]))
        self.assertNotIn("root", record["facts"][0]["fact_value"])
        self.assert_valid(record)

    def test_la_illa_function_ambiguity_abstains(self):
        for surface, function_surface in (("وَلَا", "لَا"), ("إِلَّا", "إِلَّا")):
            record = producer.produce_record(
                row(
                    surface,
                    [
                        segment(0, "وَ", "prefix_conjunction", "qg-conjunction")
                        if surface.startswith("وَ")
                        else segment(0, "إِلَّا", "exception_particle", "qg-particle"),
                        *([] if surface == "إِلَّا" else [segment(1, function_surface, "negation_particle", "qg-negation")]),
                    ],
                )
            )
            self.assertNotEqual("candidate", record["projection"]["status"])
            self.assertTrue(any("function_ambiguity" in item["blocker_id"] for item in record["facts"][0]["unresolved_blockers"]))
            self.assert_valid(record)

    def test_surface_reconstruction_mismatch_abstains(self):
        record = producer.produce_record(
            row(
                "كِتَابُهُ",
                [
                    segment(0, "كِتَابُ", "host", "qg-noun-stem"),
                    segment(1, "ه", "attached_pronoun", "qg-pronoun"),
                ],
            )
        )
        self.assertNotEqual("candidate", record["projection"]["status"])
        self.assertTrue(any("reconstruction" in item["blocker_id"] for item in record["facts"][0]["unresolved_blockers"]))
        self.assert_valid(record)

    def test_morphline_is_not_a_root_source(self):
        candidate = row(
            "كَتَبَهُ",
            [
                segment(0, "كَتَبَ", "verb_stem", "qg-verb-stem"),
                segment(1, "هُ", "object_pronoun", "qg-object-pronoun"),
            ],
            morphline="root ك ت ب · Form I perfect + object pronoun",
        )
        record = producer.produce_record(candidate)
        self.assertEqual("candidate", record["projection"]["status"])
        self.assertFalse(any("root" in fact["fact_value"] for fact in record["facts"]))
        self.assert_valid(record)

    def test_unverified_v575_verdict_abstains(self):
        record = producer.produce_record(
            row(
                "كُلَّهَا",
                [
                    segment(0, "كُلَّ", "host", "qg-noun-stem"),
                    segment(1, "هَا", "possessive_pronoun", "qg-possessive-pronoun"),
                ],
                _fb1_verdict="span_fail",
            )
        )
        self.assertEqual("input_verdict_not_verified", record["facts"][0]["fact_value"]["reason_codes"][0])
        self.assertNotEqual("candidate", record["projection"]["status"])
        self.assert_valid(record)

    def test_input_mutation_does_not_change_source_row(self):
        source = row(
            "كُلَّهَا",
            [
                segment(0, "كُلَّ", "host", "qg-noun-stem"),
                segment(1, "هَا", "possessive_pronoun", "qg-possessive-pronoun"),
            ],
        )
        before = copy.deepcopy(source)
        producer.produce_record(source)
        self.assertEqual(before, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
