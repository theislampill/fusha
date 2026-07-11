#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused RM-26 nahw replay tests (NHP-07..12/14/15/17/19/20)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from tools import fusha_governor as G  # noqa: E402
from tools.validate_dependency_lattice import validate_lattice  # noqa: E402


def lattice(tokens, *, mode="arbitrary_typing", claims=None):
    unit = {
        "input_mode": mode,
        "source_unit": {
            "address": "quran:2:2" if mode == "source_addressed" else "",
            "scope": "in_scope_source_addressed" if mode == "source_addressed" else "arbitrary",
        },
        "tokens": tokens,
    }
    if claims is not None:
        unit["claims"] = claims
    return G.build_dependency_lattice(unit)


def abstention_for(result, trigger_ref):
    return next(
        (
            edge
            for edge in result["edges"]
            if edge["rel_label"] == "abstained_unmodeled_construction"
            and edge.get("trigger_particle") == trigger_ref
        ),
        None,
    )


class RM26NahwReplay(unittest.TestCase):
    def assert_trigger_abstains(self, surface, family, following_pos="verb"):
        result = lattice(
            [
                {"ref": "tok:0", "surface": surface, "pos": "particle"},
                {"ref": "tok:1", "surface": "X", "pos": following_pos},
            ]
        )
        edge = abstention_for(result, "tok:0")
        self.assertIsNotNone(edge, result)
        self.assertEqual(edge["trigger_family"], family)
        self.assertEqual(edge["decision_status"], "pending")

    def test_nhp_07_jussive_trigger_emits_explicit_abstention(self):
        self.assert_trigger_abstains("لم", "jussive")

    def test_nhp_08_inna_family_trigger_emits_explicit_abstention(self):
        self.assert_trigger_abstains("إن", "inna_family", "noun")

    def test_nhp_09_la_jins_trigger_emits_explicit_abstention(self):
        self.assert_trigger_abstains("لا", "la_jins", "noun")

    def test_nhp_10_istithna_trigger_emits_explicit_abstention(self):
        self.assert_trigger_abstains("إلا", "istithna", "noun")

    def test_nhp_11_hal_trigger_emits_explicit_abstention(self):
        self.assert_trigger_abstains("هل", "hal")

    def test_nhp_12_vocative_trigger_emits_explicit_abstention(self):
        self.assert_trigger_abstains("يا", "vocative", "noun")

    def test_nhp_14_mabni_and_fi_mahall_fields_round_trip(self):
        result = lattice(
            [
                {"ref": "2:2:2", "surface": "لا", "pos": "particle"},
                {"ref": "2:2:3", "surface": "رَيْبَ", "pos": "noun"},
            ],
            mode="source_addressed",
        )
        edge = abstention_for(result, "2:2:2")
        self.assertIsNotNone(edge, result)
        edge.update({"mabni": True, "mabni_on": "fatha", "fi_mahall_case_mood": "accusative"})
        self.assertEqual(validate_lattice(json.loads(json.dumps(result))), [])

    def test_nhp_15_idafa_refuses_case_conflict_and_keeps_number_tamyiz(self):
        conflict = lattice(
            [
                {"ref": "q:1", "surface": "كتاب", "pos": "noun", "case_visible": "nominative"},
                {"ref": "q:2", "surface": "طالبًا", "pos": "noun", "case_visible": "accusative"},
            ],
            mode="source_addressed",
        )
        idafa = next(edge for edge in conflict["edges"] if edge["rel_label"] == "idafa_dependent")
        self.assertTrue(idafa["contradiction_marker"])
        self.assertNotEqual(idafa["decision_status"], "resolved")

        numbered = lattice(
            [
                {"ref": "tok:0", "surface": "عشرون", "pos": "number"},
                {"ref": "tok:1", "surface": "كتابًا", "pos": "noun"},
            ]
        )
        edge = next(edge for edge in numbered["edges"] if edge["rel_label"] == "idafa_dependent")
        self.assertTrue(any(alt.get("rel_label") == "tamyiz" for alt in edge["unresolved_alternatives"]))

    def test_nhp_17_kana_family_suppresses_false_idafa_and_is_annotated(self):
        result = lattice(
            [
                {"ref": "tok:0", "surface": "كان", "pos": "verb"},
                {"ref": "tok:1", "surface": "الله", "pos": "proper_noun"},
                {"ref": "tok:2", "surface": "غفورًا", "pos": "adjective"},
            ]
        )
        edge = abstention_for(result, "tok:0")
        self.assertIsNotNone(edge, result)
        self.assertEqual(edge["trigger_family"], "kana_family")
        self.assertEqual(edge["suppressed_rule"], "idafa")
        self.assertFalse(any(e["rel_label"] == "idafa_dependent" for e in result["edges"]))

    def test_nhp_19_governor_license_table_and_negation_aware_matching(self):
        claims = [
            {
                "claim_id": "ok",
                "target": "q:1",
                "claim_type": "case_mood",
                "claimed_value": "genitive",
                "claimed_governor_type": "preposition",
                "claimed_governor": "min",
                "claimed_reasoning": "the preposition governs this noun",
            },
            {
                "claim_id": "wrong-case",
                "target": "q:2",
                "claim_type": "case_mood",
                "claimed_value": "accusative",
                "claimed_governor_type": "preposition",
                "claimed_governor": "min",
                "claimed_reasoning": "the preposition governs this noun",
            },
            {
                "claim_id": "negated-keyword",
                "target": "q:3",
                "claim_type": "case_mood",
                "claimed_value": "nominative",
                "claimed_governor": "",
                "claimed_reasoning": "not governed by the preposition; no governor is identified",
            },
        ]
        result = lattice([], mode="source_addressed", claims=claims)
        flagged = {edge.get("claim_id") for edge in result["edges"] if edge["right_answer_wrong_reason_marker"]}
        self.assertNotIn("ok", flagged)
        self.assertIn("wrong-case", flagged)
        self.assertIn("negated-keyword", flagged)

    def test_nhp_20_case_claim_requires_reasoning_and_two_vote_gate(self):
        base = {
            "loc": "2:2:3",
            "surface": "رَيْبَ",
            "gloss": "doubt",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "internal_provenance": {},
            "case": "accusative",
        }

        def run(row):
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                path = fh.name
            try:
                env = dict(os.environ)
                env["PYTHONUTF8"] = "1"
                return subprocess.run(
                    [sys.executable, os.path.join(REPO, "tools", "validate_token_irab_decisions.py"), path],
                    cwd=REPO,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                    env=env,
                )
            finally:
                os.unlink(path)

        no_reason = run(dict(base, gate="two_vote_required"))
        self.assertNotEqual(no_reason.returncode, 0, no_reason.stdout)
        self.assertIn("case/mood claim missing reasoning", no_reason.stdout)

        low_gate = run(dict(base, reasoning="lā of genus licenses the naṣb slot", gate="auto_safe"))
        self.assertNotEqual(low_gate.returncode, 0, low_gate.stdout)
        self.assertIn("case/mood claim gate below two_vote_required", low_gate.stdout)

        valid = run(dict(base, reasoning="lā of genus licenses the naṣb slot", gate="two_vote_required"))
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
