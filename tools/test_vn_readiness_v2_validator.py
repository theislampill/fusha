import json
from pathlib import Path
import unittest

from tools.validate_vn_readiness_v2 import validate_artifacts


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "qamus" / "examples" / "vnmap-v2"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class VnReadinessV2ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = read_jsonl(FIXTURE_ROOT / "vn-ledger-v2.fixture.jsonl")
        cls.matrix = json.loads((FIXTURE_ROOT / "vn-readiness-v2.fixture.json").read_text(encoding="utf-8"))

    def test_fixture_passes(self):
        report = validate_artifacts(self.ledger, self.matrix)
        self.assertTrue(report.ok, report.errors)

    def test_conflict_scalar_mutation_is_rejected(self):
        ledger = [dict(row) for row in self.ledger]
        conflict = next(row for row in ledger if row["source_key"] == "v048")
        conflict["vn_tranche"] = "VN-01"
        report = validate_artifacts(ledger, self.matrix)
        self.assertFalse(report.ok)
        self.assertTrue(any("historical conflict" in error for error in report.errors))

    def test_graph_count_mutation_is_rejected(self):
        matrix = json.loads(json.dumps(self.matrix))
        tranche = next(row for row in matrix["views"]["authoritative_partition"]["tranches"] if row["label"] == "VN-02")
        tranche["graph_complete_rows"] += 1
        report = validate_artifacts(self.ledger, matrix)
        self.assertFalse(report.ok)
        self.assertTrue(any("graph_complete_rows" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
