# -*- coding: utf-8 -*-
"""HAZARD fixtures (owner close-and-scale steer §7, red-first).

Each hazard proven live by VN-UNLOCK-PROOF-2026-07-29 gets an executable
fixture here so no future lane can re-introduce it silently:

(a) wbw loc-aliasing (17:15:5, 20:14:11, 33:18:7): a loc-keyed apply lane
    would patch the WRONG token. Guard: tools/apply_surface_guard.
(b) proposal/contract namespace collision (former proposal "VN-03" =
    v196–v296 vs contract VN-03 = v142–v188 + n0136–n0180): the readiness
    and universe validators must FAIL on a bare contract spelling in a
    proposal-namespace position.
(c) لَـ allomorph family (لَهُمْ / لَكُمْ / لَنَا): a strict لِ+kasra filter misses it;
    the discovery classifier must carry an explicit allomorph expansion note.
(d) live carve forks (2:187:63, 4:11:5): certified carve vs live carve,
    NOT-DEPLOYED; regression-pinned against production-difference.json.
(e) diptote-fatḥah (2:34:5 لِءَادَمَ): jarr sign is fatḥah; NOT covered by the
    increment-24 fixtures (verified), so covered here.

Cited-existing coverage (do NOT duplicate):
- lexical-lām, lām-taʿlīl, fused-لِلَّهِ: PR #123
  tools/skill_fixtures/skill_fixtures_increment24.jsonl (26 fixtures).
- multi-entry token: PR #121 invariant test 7,
  tools/test_entry_transclusion_invariants.py::
  test_07_multi_entry_token_separate_morphemes.
"""

import io
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SCRIPTS = os.path.join(ROOT, "qamus", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

HAZARDS = os.path.join(ROOT, "qamus", "examples", "hazards")

from tools.apply_surface_guard import (  # noqa: E402
    require_surface_loc_double_match,
    surface_keys,
)
from find_li_noun_host_rows import classify  # noqa: E402


def read_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


class WbwLocAliasingGuardTests(unittest.TestCase):
    """(a) surface+loc double-match guard against the 3 aliased locs."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = read_jsonl(os.path.join(HAZARDS, "wbw-loc-aliasing.fixture.jsonl"))
        cls.by_loc = {row["loc"]: row for row in cls.fixture}
        cls.index = {}
        index_path = os.path.join(ROOT, "qamus", "indexes", "quran-loc-surface", "index.jsonl")
        wanted = set(cls.by_loc)
        with io.open(index_path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("loc") in wanted:
                    cls.index[row["loc"]] = row.get("surface")
                    if len(cls.index) == len(wanted):
                        break

    def test_fixture_covers_the_three_aliased_locs(self):
        self.assertEqual(set(self.by_loc), {"17:15:5", "20:14:11", "33:18:7"})
        for row in self.fixture:
            self.assertEqual(row["hazard"], "wbw_loc_aliasing")
            self.assertEqual(row["not_deployed_marker"], "NOT-DEPLOYED")
            self.assertTrue(row["provenance"])

    def test_claimed_surfaces_match_the_committed_canonical_index(self):
        for loc, row in self.by_loc.items():
            self.assertEqual(self.index.get(loc), row["claimed_surface_index"], loc)

    def test_loc_keyed_apply_would_mispatch_but_guard_blocks(self):
        # Baseline (the hazard): a loc-only matcher "finds" the aliased live
        # row for 17:15:5 and would patch نَبْعَثَ with a لِنَفْسِهِ gloss.
        row = self.by_loc["17:15:5"]
        aliased_live = {"loc": "17:15:5", "surface": row["live_surface_observed"]}
        loc_only_match = aliased_live["loc"] == row["loc"]
        self.assertTrue(loc_only_match, "loc-only matching finds the aliased row — that IS the hazard")
        self.assertFalse(
            surface_keys(row["claimed_surface_matrix"]) & surface_keys(aliased_live["surface"]),
            "the aliased live token must not share any surface key with the claim",
        )
        verdict = require_surface_loc_double_match(row["loc"], row["claimed_surface_matrix"], aliased_live)
        self.assertFalse(verdict.ok)
        self.assertIn("surface_mismatch", verdict.reason)

    def test_guard_refuses_when_live_surface_is_unverified(self):
        for loc in ("20:14:11", "33:18:7"):
            row = self.by_loc[loc]
            self.assertIsNone(row["live_surface_observed"])
            verdict = require_surface_loc_double_match(
                loc, row["claimed_surface_matrix"], {"loc": loc, "surface": None}
            )
            self.assertFalse(verdict.ok, loc)
            self.assertIn("live_surface_unverified", verdict.reason)
            missing = require_surface_loc_double_match(loc, row["claimed_surface_matrix"], None)
            self.assertFalse(missing.ok)
            self.assertIn("no_live_row", missing.reason)

    def test_guard_accepts_a_genuine_surface_loc_double_match(self):
        live_rows = read_jsonl(
            os.path.join(ROOT, "qamus", "examples", "p007-li-pilot", "live-rows.jsonl")
        )
        live = next(row for row in live_rows if row["loc"] == "2:187:63")
        verdict = require_surface_loc_double_match("2:187:63", "لِلنَّاسِ", live)
        self.assertTrue(verdict.ok, verdict.reason)
        cross = require_surface_loc_double_match("2:187:64", "لِلنَّاسِ", live)
        self.assertFalse(cross.ok)
        self.assertIn("loc_mismatch", cross.reason)

    def test_guard_normalizes_nfc_and_quranic_annotation_marks(self):
        # Index surface carries U+06E6 (small yeh); the matrix surface does not.
        row = self.by_loc["17:15:5"]
        self.assertTrue(
            surface_keys(row["claimed_surface_index"]) & surface_keys(row["claimed_surface_matrix"])
        )


class NamespaceCollisionTests(unittest.TestCase):
    """(b) proposal-namespace label colliding with a contract window id must FAIL."""

    def test_vn_ledger_validator_rejects_contract_spelling_in_proposal_row(self):
        from tools.validate_vn_ledger import _read_json, _read_jsonl, validate_artifacts

        fixture_root = os.path.join(ROOT, "qamus", "examples", "vnmap")
        ledger = _read_jsonl(os.path.join(fixture_root, "vn-ledger.fixture.jsonl"))
        metrics = _read_json(os.path.join(fixture_root, "vn-graph-metrics.fixture.json"))
        matrix = _read_json(os.path.join(fixture_root, "vn-readiness-matrix.fixture.json"))
        self.assertTrue(validate_artifacts(ledger, metrics, matrix).ok)
        collided = json.loads(json.dumps(matrix))
        collided["tranches"][3]["proposal_vn_tranche"] = "VN-03"
        report = validate_artifacts(ledger, metrics, collided)
        self.assertFalse(report.ok)
        self.assertTrue(any("collides with a" in error for error in report.errors), report.errors)

    def test_universe_validator_rejects_contract_spelling_on_vn_kind_rows(self):
        from tools.validate_example_universe import validate_universe

        rows = [
            {
                "appearance_id": "x:u0:x0:w0",
                "selected": True,
                "canonical_loc": "1:1:1",
                "crosswalk": "resolved",
                "tranche_kind": "VN",
                "tranche": "VN-03",
            }
        ]
        errors = []
        validate_universe(rows, [], {}, errors, appearance_locs=None)
        self.assertTrue(
            any("collides with a contract window id" in error for error in errors), errors
        )
        rows[0]["tranche"] = "VNPROP-03"
        errors = []
        validate_universe(rows, [], {}, errors, appearance_locs=None)
        self.assertFalse(
            any("collides" in error or "unknown VN proposal" in error for error in errors), errors
        )


class AllomorphLaFamilyTests(unittest.TestCase):
    """(c) لَـ allomorph rows the strict لِ+kasra filter misses must carry an expansion note."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = read_jsonl(os.path.join(HAZARDS, "allomorph-la-family.fixture.jsonl"))

    def test_fixture_covers_the_pronoun_host_allomorph_family(self):
        self.assertEqual([row["surface"] for row in self.fixture], ["لَهُمْ", "لَكُمْ", "لَنَا"])

    def test_classifier_carries_the_allomorph_expansion_note(self):
        for row in self.fixture:
            route, flags = classify(
                {
                    "particle_source_key": "p007",
                    "surface": row["surface"],
                    "host_visible": row["host_visible"],
                    "function_candidates": [],
                }
            )
            self.assertEqual(route, row["expected_route"], row["surface"])
            for flag in row["expected_flags_include"]:
                self.assertIn(flag, flags, f"{row['surface']} missing {flag}")

    def test_strict_kasra_row_does_not_get_the_allomorph_flag(self):
        _route, flags = classify(
            {
                "particle_source_key": "p007",
                "surface": "لِقَوْمِهِ",
                "host_visible": "قومه",
                "function_candidates": [],
            }
        )
        self.assertNotIn("allomorph_la_family_requires_expansion", flags)
        self.assertNotIn("non_kasra_lam_needs_diacritic_check", flags)


class LiveCarveForkTests(unittest.TestCase):
    """(d) the two live carve forks stay pinned against production-difference.json."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = read_jsonl(os.path.join(HAZARDS, "live-carve-forks.fixture.jsonl"))
        production = read_json(
            os.path.join(ROOT, "qamus", "examples", "p007-li-pilot", "production-difference.json")
        )
        cls.not_deployed = production.get("not_deployed")
        cls.production_by_occurrence = {
            row.get("occurrence_id"): row for row in production.get("rows") or []
        }

    def test_fixture_covers_both_forks_and_is_not_deployed(self):
        self.assertEqual(
            [row["occurrence_id"] for row in self.fixture],
            ["quran:2:187:63", "quran:4:11:5"],
        )
        self.assertTrue(self.not_deployed)
        for row in self.fixture:
            self.assertEqual(row["not_deployed_marker"], "NOT-DEPLOYED")
            self.assertEqual(row["verdict"], "wrong")

    def test_fixture_matches_the_committed_production_difference(self):
        for row in self.fixture:
            source = self.production_by_occurrence[row["occurrence_id"]]
            self.assertEqual(row["certified_carve"], source["candidate_carve"], row["occurrence_id"])
            self.assertEqual(row["live_carve"], source["current_public_carve"], row["occurrence_id"])
            self.assertEqual(
                row["certified_colour_classes"], source["candidate_colour_classes"]
            )
            self.assertEqual(row["live_colour_classes"], source["current_colour_classes"])
            self.assertEqual(row["surface"], source["surface"])
            self.assertFalse(source["deployed"])
            self.assertNotEqual(row["certified_carve"], row["live_carve"], "fork must remain a fork")


class DiptoteFathaTests(unittest.TestCase):
    """(e) diptote-fatḥah fixture — gap verified against increment-24, no duplication."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = read_jsonl(os.path.join(HAZARDS, "diptote-fatha-jarr.fixture.jsonl"))

    def test_fixture_matches_the_pilot_exception_and_reason_key(self):
        row = self.fixture[0]
        self.assertEqual(row["loc"], "quran:2:34:5")
        self.assertEqual(row["correct_label"], "jarr_majrur_sign_fatha_diptote")
        locations = read_json(
            os.path.join(ROOT, "qamus", "examples", "p007-li-pilot", "locations.json")
        )
        exception = next(
            item for item in locations["exceptions"] if item["id"] == "diptote-jarr-sign-fatha"
        )
        self.assertIn("quran:2:34:5", exception["locs"])
        registry = read_jsonl(os.path.join(ROOT, "qamus", "skills", "reason-key-registry.jsonl"))
        self.assertTrue(any(item.get("id") == row["reason_key"] for item in registry))

    def test_diptote_is_genuinely_absent_from_increment24(self):
        fixtures = read_jsonl(
            os.path.join(ROOT, "tools", "skill_fixtures", "skill_fixtures_increment24.jsonl")
        )
        self.assertEqual(len(fixtures), 26)
        self.assertFalse(any("diptote" in json.dumps(row) for row in fixtures))


class CitedExistingCoverageTests(unittest.TestCase):
    """(e)/(f) classes already covered elsewhere are cited, not duplicated."""

    def test_increment24_covers_lexical_lam_talil_and_fused_lillah(self):
        fixtures = read_jsonl(
            os.path.join(ROOT, "tools", "skill_fixtures", "skill_fixtures_increment24.jsonl")
        )
        labels = {row.get("correct_label") for row in fixtures}
        rule_ids = {row.get("rule_id") for row in fixtures}
        self.assertIn("reject_carve_lexical_initial_lam", labels)  # lexical-lām (2:187:9 لِبَاسٌ)
        self.assertIn("lam_talil_an_mudmara_subjunctive", labels)  # lām-taʿlīl (48:29:42)
        self.assertIn("sarf-fused-lil-exact-letter-ownership", rule_ids)  # fused-لِلَّهِ (12:31:24)

    def test_pr121_invariant_seven_covers_multi_entry_tokens(self):
        path = os.path.join(ROOT, "tools", "test_entry_transclusion_invariants.py")
        with io.open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("def test_07_multi_entry_token_separate_morphemes", source)


if __name__ == "__main__":
    unittest.main()
