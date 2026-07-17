import json
from pathlib import Path
import unittest

from tools.build_vn_readiness_v2 import (
    _assignment_for_key,
    _membership_claims,
    _selected_word_id,
    build_v2,
)


FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "qamus" / "examples" / "vnmap-v2"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class VnReadinessV2Tests(unittest.TestCase):
    def setUp(self):
        self.inputs = (
            read_jsonl(FIXTURE_ROOT / "entries.fixture.jsonl"),
            read_jsonl(FIXTURE_ROOT / "whitelist.fixture.jsonl"),
            read_jsonl(FIXTURE_ROOT / "occurrence-appearances.fixture.jsonl"),
            read_jsonl(FIXTURE_ROOT / "famwide-strat.fixture.jsonl"),
            read_json(FIXTURE_ROOT / "membership.fixture.json"),
            read_jsonl(FIXTURE_ROOT / "conflicts.fixture.jsonl"),
            read_json(FIXTURE_ROOT / "edge-summary.fixture.json"),
            read_jsonl(FIXTURE_ROOT / "crosswalk-forward.fixture.jsonl"),
            read_jsonl(FIXTURE_ROOT / "debt-classification.fixture.jsonl"),
            read_json(FIXTURE_ROOT / "baseline-matrix.fixture.json"),
            read_json(FIXTURE_ROOT / "proofs.fixture.json"),
        )

    def test_owner_schema_keeps_conflict_null_and_staging_separate(self):
        result = build_v2(*self.inputs)
        conflict = next(row for row in result.ledger if row["source_key"] == "v048")
        self.assertIsNone(conflict["vn_tranche"])
        self.assertEqual(conflict["vn_tranche_status"], "historical_conflict")
        self.assertEqual(conflict["vn_tranche_claims"], ["VN-00", "VN-01"])
        self.assertTrue(conflict["vn00_staging_member"])
        row = result.matrix["views"]["authoritative_partition"]["tranches"][1]
        self.assertEqual(row["historical_conflict_entries"], 1)

    def test_both_proposal_namespaces_and_graph_status_split_are_explicit(self):
        result = build_v2(*self.inputs)
        proposed = next(row for row in result.ledger if row["source_key"] == "v150")
        self.assertEqual(proposed["vn_tranche"], "proposed:vn-partition-proposal.v1:VN-02")
        self.assertEqual(proposed["vn_tranche_plan_table_proposal"], "proposed:vn-plan-table.v1:VN-03")
        self.assertNotIn("partition_label", proposed)
        self.assertNotIn("plan_table_label", proposed)
        self.assertNotIn("proposal_vn_tranche", proposed)
        row = result.matrix["views"]["authoritative_partition"]["tranches"][2]
        self.assertEqual(row["graph_complete_deterministic_exact_rows"], 1)
        self.assertEqual(row["graph_complete_candidate_rows"], 1)

    def test_particle_is_unplanned_in_plan_table_and_proofs_are_named(self):
        result = build_v2(*self.inputs)
        particle = next(row for row in result.ledger if row["source_key"] == "p099")
        self.assertEqual(particle["vn_matrix_view_plan_table"], "UNPLANNED_PARTICLES")
        self.assertEqual(result.matrix["proofs"]["count"], 3)
        self.assertEqual(
            result.matrix["proofs"]["names"],
            ["fattabini 19:43:10", "ma 2:284:10", "sufaha 2:13:12"],
        )

    def test_selected_word_identity_prefers_canonical_quran_address(self):
        selected_id = _selected_word_id(
            {
                "entry_id": "entry-repaired",
                "sense_index": 1,
                "usage_index": 1,
                "form_index": 1,
                "source_card_ref": "28:35",
                "occurrence_id": "28:35:2",
                "canonical_quran_loc": "quran:28:35:12",
                "display_local_address": {"entry_example_index": 1},
            }
        )
        self.assertTrue(selected_id.endswith(":o28:35:12"))

    def test_staging_only_surface_keeps_authority_and_separate_namespace(self):
        membership = read_json(FIXTURE_ROOT / "membership.fixture.json")
        membership["vn"]["VN-00"]["authoritative_sets"].append(
            {
                "set_id": "fixture-staging-only",
                "kind": "deployed_rollout_staging_cumulative_snapshot",
                "source_keys": ["v150"],
                "evidence": [{"artifact": "fixture/staging-sourcekeys.json", "locator": "v150"}],
            }
        )
        claims, evidence, doc_sets, staging = _membership_claims(
            membership,
            read_jsonl(FIXTURE_ROOT / "conflicts.fixture.jsonl"),
        )
        assignment = _assignment_for_key("v150", claims, evidence, doc_sets, staging)
        self.assertEqual(assignment["vn_tranche_status"], "authoritative")
        self.assertEqual(assignment["vn_tranche"], "VN-00")
        self.assertTrue(assignment["vn00_staging_member"])
        self.assertEqual(assignment["vn_matrix_view_authoritative_partition"], "VN-00-STAGING")


if __name__ == "__main__":
    unittest.main()
