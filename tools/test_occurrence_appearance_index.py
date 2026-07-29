#!/usr/bin/env python3
"""Focused red-first tests for the occurrence-to-appearance index contract."""

import unittest

from tools.build_occurrence_appearance_index import build_index, projection_hash
from tools.validate_appearance_parity import validate_records


def row(loc, surface, analysis, *, source_key=None, entry_url=None, entry_id=None):
    return {
        "loc": loc,
        "surface": surface,
        "segments": [{
            "class": "qg-noun-stem",
            "surface": surface,
            "gloss_contribution": analysis,
            "role": "noun_stem",
        }],
        "token_contribution_gloss": analysis,
        "contextual_phrase_gloss": analysis,
        "morphline": analysis,
        "root": None,
        "sarf_facts": None,
        "nahw_facts": None,
        "card_ref": loc.rsplit(":", 1)[0],
        "source_key": source_key,
        "entry_url": entry_url,
        "entry_id": entry_id,
    }


class OccurrenceAppearanceIndexTests(unittest.TestCase):
    def test_builder_records_reader_and_entry_example_relationship(self):
        source = row(
            "1:1:1",
            "كِتَابٌ",
            "book",
            source_key="n0002",
            entry_url="https://qamus.dawah.wiki/n0002",
        )
        entries = [{
            "id": "entry-book",
            "source_keys": ["n2"],
            "usage": [{"examples": [{"ref": "1:1"}]}],
        }]

        result = build_index([source], entries)

        self.assertEqual(len(result.records), 1)
        record = result.records[0]
        self.assertEqual(record["loc"], "1:1:1")
        self.assertTrue(record["unique"])
        self.assertEqual(record["appearance_count"], 2)
        self.assertEqual(
            [appearance["surface_kind"] for appearance in record["appearances"]],
            ["reader", "entry_example"],
        )
        self.assertEqual(record["entry_relationships"], ["entry-book"])
        self.assertEqual(record["projection_hash"], projection_hash(source))

    def test_direct_source_key_entry_id_resolves_to_typed_entry_id(self):
        source = row(
            "1:1:2",
            "كِتَابٌ",
            "book",
            source_key="n0002",
            entry_id="n0002",
        )
        entries = [{
            "id": "entry-book",
            "source_keys": ["n2"],
            "usage": [{"examples": [{"ref": "1:1"}]}],
        }]

        result = build_index([source], entries)

        self.assertEqual(result.records[0]["entry_relationships"], ["entry-book"])

    def test_e_url_source_key_alias_resolves_to_typed_entry_id(self):
        source = row(
            "1:1:3",
            "كِتَابٌ",
            "book",
            source_key="n0002",
            entry_url="https://qamus.dawah.wiki/e/n0002",
        )
        entries = [{
            "id": "entry-book",
            "source_keys": ["n2"],
            "usage": [],
        }]

        result = build_index([source], entries)

        self.assertEqual(result.records[0]["entry_relationships"], ["entry-book"])

    def test_six_e_url_source_key_aliases_reciprocate_to_canonical_entries(self):
        aliases = ["v516", "v521", "v526", "v526", "v528", "v539"]
        locations = ["1:1:1", "1:1:2", "1:1:3", "1:1:4", "1:1:5", "1:1:6"]
        rows = [
            row(
                loc,
                "كِتَابٌ",
                "fixture",
                entry_url=f"https://qamus.dawah.wiki/e/{alias}",
            )
            for loc, alias in zip(locations, aliases)
        ]
        entries = [
            {"id": f"entry-{alias}", "source_keys": [alias], "usage": []}
            for alias in sorted(set(aliases))
        ]

        result = build_index(rows, entries)

        self.assertEqual(
            [record["entry_relationships"] for record in result.records],
            [[f"entry-{alias}"] for alias in aliases],
        )

    def test_same_surface_different_locations_are_allowed(self):
        first = row("39:63:3", "السَّمَاوَاتِ", "segmented")
        second = row("22:18:9", "ٱلسَّمَٰوَٰتِ", "fused")

        built = build_index([first, second], [])
        report = validate_records(built.records, source_rows=[first, second])

        self.assertTrue(report.ok, report.errors)
        self.assertGreaterEqual(report.allowed_same_surface_groups, 1)
        self.assertNotEqual(
            built.records[0]["projection_hash"], built.records[1]["projection_hash"]
        )

    def test_same_loc_divergent_projection_is_rejected(self):
        first = row("1:1:1", "أ", "a")
        fork = row("1:1:1", "أ", "the")

        report = validate_records([], source_rows=[first, fork])

        self.assertFalse(report.ok)
        self.assertTrue(any("divergent" in error for error in report.errors))

    def test_appearance_copy_must_inherit_parent_projection_hash(self):
        source = row("1:1:1", "أ", "a")
        record = {
            "loc": source["loc"],
            "unique": True,
            "appearances": [{
                "surface_kind": "entry_example",
                "entry_id": "entry-a",
                "projection_hash": "0" * 64,
            }],
            "appearance_count": 1,
            "entry_relationships": ["entry-a"],
            "projection_hash": projection_hash(source),
        }

        report = validate_records([record], source_rows=[source])

        self.assertFalse(report.ok)
        self.assertTrue(any("appearance" in error for error in report.errors))


class TwoLexemeAyahReciprocityTests(unittest.TestCase):
    """GRAPH-BACKLINK-REPAIR §5: per-selected-token attribution on two-lexeme āyāt."""

    def _two_lexeme_fixture(self):
        # 7:40-shaped āyah: token 17 الْجَمَلُ, token 19 الْخِيَاطِ.  The whitelist
        # rows were authored under the خيط entry page, so BOTH rows carry the
        # khayt entry context; the jamal entry cites the same āyah ayah-only.
        camel = row("7:40:17", "ٱلْجَمَلُ", "camel", entry_id="entry-khayt")
        needle = row("7:40:19", "ٱلْخِيَاطِ", "needle", entry_id="entry-khayt")
        entries = [
            {
                "id": "entry-khayt",
                "source_keys": ["n819"],
                "usage": [{"forms": ["الْخِيَاطِ"], "examples": [{"ref": "7:40"}]}],
            },
            {
                "id": "entry-jamal",
                "source_keys": ["n704"],
                "usage": [{"forms": ["الْجَمَلُ"], "examples": [{"ref": "7:40"}]}],
            },
        ]
        return [camel, needle], entries

    def test_sibling_entry_attributes_at_its_own_selected_token(self):
        rows, entries = self._two_lexeme_fixture()
        result = build_index(rows, entries)
        by_loc = {record["loc"]: record for record in result.records}
        # The jamal entry must be credited at ITS token (7:40:17) even though the
        # row-carried page context credits only khayt there.
        self.assertIn("entry-jamal", by_loc["7:40:17"]["entry_relationships"])
        # Multi-entry entry_relationships per loc are allowed: the row-carried
        # khayt attribution is not removed.
        self.assertIn("entry-khayt", by_loc["7:40:17"]["entry_relationships"])
        self.assertEqual(
            result.stats.get("entry_store_selected_token_matched_refs"), 1
        )

    def test_ambiguous_multi_position_match_abstains(self):
        rows, entries = self._two_lexeme_fixture()
        # A second جمل token in the same āyah makes the selected-token match
        # ambiguous; the builder must abstain, never guess a position.
        rows.append(row("7:40:21", "ٱلْجَمَلُ", "camel", entry_id="entry-khayt"))
        result = build_index(rows, entries)
        by_loc = {record["loc"]: record for record in result.records}
        self.assertNotIn("entry-jamal", by_loc["7:40:17"]["entry_relationships"])
        self.assertNotIn("entry-jamal", by_loc["7:40:21"]["entry_relationships"])
        self.assertEqual(
            result.stats.get("entry_store_selected_token_ambiguous_refs"), 1
        )

    def test_offline_ledger_anchored_repair_closes_reciprocity(self):
        from tools.build_occurrence_appearance_index import repair_reciprocity

        record = {
            "loc": "7:40:17",
            "unique": True,
            "appearances": [
                {"surface_kind": "reader"},
                {"entry_id": "entry-khayt", "surface_kind": "entry_example"},
            ],
            "appearance_count": 2,
            "entry_relationships": ["entry-khayt"],
            "projection_hash": "0" * 64,
        }
        ledger_rows = [
            {
                "occurrence_id": "7:40:17",
                "entry_id": "entry-jamal",
                "join_method": "strict_unique",
                "selected_surface": "الْجَمَلُ",
            },
            {  # non-deterministic join methods must never repair
                "occurrence_id": "7:40:17",
                "entry_id": "entry-wrong",
                "join_method": "ayah_fallback",
                "selected_surface": "الْجَمَلُ",
            },
            {  # surface mismatch must never repair
                "occurrence_id": "7:40:17",
                "entry_id": "entry-mismatch",
                "join_method": "strict_unique",
                "selected_surface": "النَّخْلَةِ",
            },
        ]
        stats, repaired = repair_reciprocity(
            [record], ledger_rows, {"7:40:17": "ٱلْجَمَلُ"}
        )
        self.assertEqual(stats["repaired"], 1)
        self.assertEqual(stats["surface_mismatch_skipped"], 1)
        self.assertEqual(
            record["entry_relationships"], ["entry-jamal", "entry-khayt"]
        )
        self.assertEqual(record["appearance_count"], 3)
        self.assertEqual(
            repaired,
            [{"loc": "7:40:17", "entry_id": "entry-jamal", "selected_surface": "الْجَمَلُ"}],
        )


if __name__ == "__main__":
    unittest.main()
