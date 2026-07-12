#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first tests for tools/enrich_rebind_queue.py.

Covers the enrichment contracts the C4 brief pins:
  * root-skeleton lookup derives the correct root for inflected surfaces,
  * ambiguity is preserved (a homograph surface emits ALL competing roots, no pick),
  * the no-host lane routes to requires_authoring after the norm_strict fallback,
  * neighbor carriers are flagged via root/fingerprint disagreement,
  * the artifact is deterministic (double build is byte-identical),
  * the O1 calibration agreement clears the >=55/59 bar and the three homograph
    traps (2:264:7, 3:36:16, 3:14:7) each list every competing root.

The synthetic fixtures are red-first: a force-pick or single-root implementation, or
one that skips the skeleton/fallback tiers, fails HomographTrap / NoHostLane / Skeleton.
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tools.enrich_rebind_queue as E  # noqa: E402


def make_morph(entries):
    return E.Morphology(entries, _by_root(entries), _by_norm(entries))


def _by_root(entries):
    out = {}
    for e in entries:
        if e.get("root"):
            out.setdefault(e["root"], []).append(e["id"])
    return out


def _by_norm(entries):
    return {}


def entry(eid, root, headword, section="verb", senses=None, usage=None):
    return {
        "id": eid, "root": root, "headword": headword, "section": section,
        "senses": senses or [], "usage": usage or [],
    }


class SkeletonDerivation(unittest.TestCase):
    def test_strict_skeleton_recovers_root_of_inflected_surface(self):
        # فَرَشْنَاهَا-style: entry documents root ف ر ش; target surface فِرَاشًا is an
        # inflection whose consonant skeleton contains the radicals in order.
        m = make_morph([entry("host", "ف ر ش", "فَرَشَ")])
        derived, _ = m.derive("فِرَٰشًۭا")
        self.assertIn("ف ر ش", derived)
        self.assertTrue(set(derived["ف ر ش"]) & {"root_skeleton_strict", "root_skeleton_weak_folded"})

    def test_documented_form_exact_beats_skeleton(self):
        m = make_morph([entry("h", "ر ج ع", "يَرْجِعُونَ")])
        derived, _ = m.derive("يَرْجِعُونَ")
        self.assertIn("documented_form_exact", derived["ر ج ع"])

    def test_weak_root_needs_fold(self):
        # اتَّقُوا (root و ق ي): the و is assimilated, so only the weak-folded tier recovers it.
        m = make_morph([entry("h", "و ق ي", "اِتَّقَىٰ")])
        derived, _ = m.derive("فَٱتَّقُوا")
        self.assertIn("و ق ي", derived)


class HomographTrap(unittest.TestCase):
    """A homograph surface MUST emit every competing root with no forced pick."""

    def _rows(self, morph, loc, surface):
        row = {
            "schema": "qamus.class2_rebind_candidate.v1",
            "target": {"canonical_location": loc, "surface": surface},
            "misbound_carriers": {"competing_analyses": []},
            "proposed_host_entries": [],
        }
        fp = E.Fingerprinter([], [], {})
        return E.enrich_row(row, morph, fp, {}, {loc: surface})

    def test_two_roots_both_surface_no_pick(self):
        # سَمَّيْتُهَا collides: root س م ي (to name) vs م و ت (death). Both have entries.
        m = make_morph([
            entry("name", "س م ي", "سَمَّىٰ"),
            entry("death", "م و ت", "مَاتَ"),
        ])
        out = self._rows(m, "3:36:16", "سَمَّيْتُهَا")
        host_roots = out["enrichment"]["host_roots"]
        # ALL competing roots emitted, no forced pick.
        self.assertIn("س م ي", host_roots)
        self.assertIn("م و ت", host_roots)
        self.assertGreater(len(host_roots), 1)
        eids = {p["entry_id"] for p in out["enrichment"]["proposed_host_entries"]}
        self.assertEqual({"name", "death"}, eids)

    def test_anchored_homograph_flag(self):
        # Two entries whose documented headword is exactly the target surface both
        # surface-anchor -> a genuine homograph flag fires.
        m = make_morph([
            entry("a", "ق د ر", "قَدَرٌ"),
            entry("b", "ق د ر", "قِدْرٌ", section="noun"),
            entry("c", "ك ت ب", "قَدَرٌ", section="noun"),  # same surface, different root
        ])
        out = self._rows(m, "5:5:5", "قَدَرٌ")
        self.assertTrue(out["enrichment"]["homograph_multiple_roots"])
        self.assertIn("ق د ر", out["enrichment"]["surface_anchored_host_roots"])
        self.assertIn("ك ت ب", out["enrichment"]["surface_anchored_host_roots"])


class NoHostLane(unittest.TestCase):
    def test_absent_root_routes_to_authoring(self):
        # A surface whose only plausible root has NO entry, and no fallback surface hit,
        # must route to requires_authoring (never fabricate a host).
        m = make_morph([entry("unrelated", "ك ت ب", "كَتَبَ")])
        row = {
            "schema": "qamus.class2_rebind_candidate.v1",
            "target": {"canonical_location": "9:9:9", "surface": "بُقْرَةٌ"},
            "misbound_carriers": {"competing_analyses": []},
            "proposed_host_entries": [],
        }
        fp = E.Fingerprinter([], [], {})
        out = E.enrich_row(row, m, fp, {}, {"9:9:9": "بُقْرَةٌ"})
        # ك ت ب radicals are not an ordered subsequence of ب ق ر ه, so no host.
        if out["enrichment"]["proposed_host_entries"]:
            self.fail("expected no host for an absent-root surface")
        self.assertEqual("requires_authoring", out["enrichment"]["routing_class"])
        self.assertTrue(out["enrichment"]["no_host_after_surface_fallback"])


class NeighborDistractor(unittest.TestCase):
    def test_bound_carrier_wrong_root_flagged(self):
        # target root ف ر ش; a bound carrier with root ب ن ي glosses a neighbour token.
        m = make_morph([
            entry("host", "ف ر ش", "فَرَشَ"),
            entry("neighbor", "ب ن ي", "بَنَىٰ"),
        ])
        row = {
            "schema": "qamus.class2_rebind_candidate.v1",
            "target": {"canonical_location": "2:22:5", "surface": "فِرَٰشًۭا"},
            "misbound_carriers": {
                "competing_analyses": [],
                "bound_carriers": [{"entry_id": "neighbor", "qword_row_id": "llx-qword-neighbor-01-01-002"}],
            },
            "proposed_host_entries": [],
        }
        fp = E.Fingerprinter(list(m.entry.values()), [], {})
        out = E.enrich_row(row, m, fp, {}, {"2:22:5": "فِرَٰشًۭا"})
        props = {p["entry_id"]: p for p in out["enrichment"]["proposed_host_entries"]}
        self.assertIn("host", props)
        self.assertFalse(props["host"]["neighbor_distractor"])
        self.assertIn("neighbor", props)
        self.assertTrue(props["neighbor"]["neighbor_distractor"])


class Determinism(unittest.TestCase):
    def test_double_build_byte_identical(self):
        _v1a, rows_a, _ra = E.build()
        _v1b, rows_b, _rb = E.build()
        self.assertEqual(E.write_jsonl_bytes(rows_a), E.write_jsonl_bytes(rows_b))


class CalibrationAgreement(unittest.TestCase):
    def setUp(self):
        self.cal = os.path.join(ROOT, ".lane-inputs", "rebind-review-cal.jsonl")
        if not os.path.exists(self.cal):
            self.skipTest("calibration input not present")
        _v1, self.rows, _r = E.build()

    def test_absent_host_agreement_meets_threshold(self):
        agree = E.calibration_agreement(self.rows, self.cal)
        self.assertGreaterEqual(agree["surfaced_correct_host"], 55, agree["shortfalls"])

    def test_all_2330_rows_present(self):
        self.assertEqual(len(self.rows), 2330)

    def test_homograph_traps_emit_competing_roots(self):
        # The brief requires every COMPETING root to be listed with no forced pick.
        ev = E.homograph_evidence(self.rows, ["2:264:7", "3:36:16", "3:14:7"])
        self.assertIn("م ن ن", ev["2:264:7"]["host_roots"])          # manna / reproach (sense homograph)
        self.assertIn("س م ي", ev["3:36:16"]["host_roots"])          # to name
        self.assertIn("م و ت", ev["3:36:16"]["host_roots"])          # death
        self.assertIn("ب ن ي", ev["3:14:7"]["host_roots"])           # build (vs sons ب ن و, an authoring gap)
        # No forced pick: each trap keeps more than one candidate root on the row.
        for loc in ev:
            self.assertGreater(len(ev[loc]["host_roots"]), 1, loc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
