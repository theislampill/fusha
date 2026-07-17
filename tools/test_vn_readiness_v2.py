import json
from pathlib import Path
import unittest

from tools.build_vn_readiness_v2 import build_v2


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


if __name__ == "__main__":
    unittest.main()
