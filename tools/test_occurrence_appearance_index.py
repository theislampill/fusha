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


if __name__ == "__main__":
    unittest.main()
