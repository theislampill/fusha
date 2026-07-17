import json
from pathlib import Path
import unittest

from tools.build_entry_card_word_ledger import build_ledger
from tools.validate_vn_ledger import validate_artifacts


FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "qamus" / "examples" / "vnmap"


def read_fixture(name):
    return [
        json.loads(line)
        for line in (FIXTURE_ROOT / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class EntryCardWordLedgerTests(unittest.TestCase):
    def setUp(self):
        self.entries = read_fixture("entries.fixture.jsonl")
        self.whitelist = read_fixture("whitelist.fixture.jsonl")
        self.appearances = read_fixture("occurrence-appearances.fixture.jsonl")
        self.family = read_fixture("famwide-strat.fixture.jsonl")

    def test_build_ledger_preserves_four_denominators_and_exact_missing_edges(self):
        result = build_ledger(self.entries, self.whitelist, self.appearances, self.family)

        self.assertEqual(result.metrics["denominators"]["D1_entries"], 2)
        self.assertEqual(result.metrics["denominators"]["D2_listed_quran_example_cards"], 2)
        self.assertEqual(result.metrics["denominators"]["D3_displayed_selected_word_rows"], 4)
        self.assertEqual(result.metrics["denominators"]["D4_unique_canonical_occurrences"], 2)
        self.assertTrue(any("missing_selected_word_edge" in row["missing_edges"] for row in result.ledger))
        self.assertTrue(any(row["join_method"] == "strict_unique" for row in result.ledger))
        self.assertTrue(all("blocker" not in row for row in result.ledger))
        noun_row = next(row for row in result.ledger if row["source_key"] == "n001")
        self.assertEqual(noun_row["occurrence_id"], "2:3:2")
        self.assertTrue(noun_row["crosswalk_flag"])

    def test_build_ledger_reciprocity_and_fixture_validator_contract(self):
        result = build_ledger(self.entries, self.whitelist, self.appearances, self.family)

        self.assertEqual(result.metrics["edge_join_rows_total"], 4)
        self.assertEqual(result.metrics["entry_occurrence_reciprocity_failures"], 0)
        report = validate_artifacts(result.ledger, result.metrics, result.matrix)
        self.assertTrue(report.ok, report.errors)

    def test_absent_authoritative_mapping_stays_null_and_proposal_is_labelled(self):
        result = build_ledger(self.entries, self.whitelist, self.appearances, self.family)

        self.assertTrue(all(row["vn_tranche"] is None for row in result.ledger))
        self.assertEqual(result.matrix["assignment_mode"], "derived_proposal_requires_owner_confirmation")
        self.assertEqual(len(result.matrix["tranches"]), 21)

    def test_clitic_family_maps_to_occurrence_and_repeated_appearance_denominators(self):
        result = build_ledger(self.entries, self.whitelist, self.appearances, self.family)
        mapping = result.matrix["clitic_family_northstar"]

        self.assertEqual(mapping["family_rows"], 1)
        self.assertEqual(mapping["affected_entries"], 1)
        self.assertEqual(mapping["affected_unique_occurrences"], 1)
        self.assertEqual(mapping["affected_repeated_appearances"], 1)


if __name__ == "__main__":
    unittest.main()
