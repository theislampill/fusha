#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.rm38.alignment import align_monotonic_spans
from tools.rm38.crosswalks import coarse_pos
from tools.rm38.load_eqtb import load_eqtb
from tools.rm38.metrics import evaluate_layer
from tools.rm38.pins import PinError, verify_pinned_file
from tools.rm38.runner import attach_other_gold
from tools.rm38.runner import split_for_unit
from tools.rm38.validate import validate_no_collapsed_score, validate_split_non_overlap


def fixture_rows() -> list[dict]:
    path = HERE / "fixtures" / "synthetic-20.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class Rm38EvaluationTests(unittest.TestCase):
    def test_fixture_is_exactly_twenty_fabricated_tokens(self) -> None:
        rows = fixture_rows()
        self.assertEqual(20, len(rows))
        self.assertTrue(all(row["unit_id"].startswith("synthetic:") for row in rows))

    def test_abstention_is_not_a_root_mismatch(self) -> None:
        report = evaluate_layer(fixture_rows()[0:1], source="quranmorph", layer="root", split="dev")
        self.assertEqual(1, report["buckets"]["abstention"])
        self.assertEqual(0, report["buckets"]["root_mismatch"])
        self.assertEqual({"numerator": 0, "denominator": 1, "value": 0.0}, report["wrong_resolve_rate"])

    def test_candidate_recall_credits_rank_two_without_top_one_credit(self) -> None:
        report = evaluate_layer(
            fixture_rows()[7:8], source="quranmorph", layer="pos", split="dev",
            score_bin_edges=[0.55], score_edge_source="dev",
        )
        self.assertEqual(0.0, report["candidate_recall@1"]["value"])
        self.assertEqual(1.0, report["candidate_recall@k"]["value"])
        self.assertEqual(1, report["abstention_matrix"]["abstain_gold_disagrees_with_top"])
        self.assertEqual([0.55], report["calibration"]["score_bin_edges"])
        self.assertEqual("dev", report["calibration"]["score_edge_source"])

    def test_tokenization_boundary_artifact_is_quarantined_from_pos(self) -> None:
        report = evaluate_layer(fixture_rows()[2:3], source="eqtb", layer="pos", split="dev")
        self.assertEqual(1, report["buckets"]["tokenization_boundary_artifact"])
        self.assertEqual(0, report["n_alignable"])
        self.assertEqual(0, report["emit_accuracy"]["denominator"])

    def test_hamza_seat_distinction_prevents_join(self) -> None:
        aligned = align_monotonic_spans([{"surface": "إيمان"}], [{"surface": "أيمان"}])
        self.assertEqual([], aligned["pairs"])
        self.assertEqual(1, len(aligned["quarantined"]))

    def test_pausal_surface_difference_does_not_override_equal_case(self) -> None:
        report = evaluate_layer(fixture_rows()[3:4], source="quranmorph", layer="features", split="dev")
        self.assertEqual(0, report["buckets"]["feature_mismatch"])
        self.assertEqual(1.0, report["case_mood"]["case"]["voweled_subset_accuracy"]["value"])

    def test_unvoweled_case_mood_abstention_is_reported_separately(self) -> None:
        report = evaluate_layer(fixture_rows()[14:15], source="quranmorph", layer="features", split="dev")
        self.assertEqual(1.0, report["case_mood"]["mood"]["unvoweled_abstention_rate"]["value"])

    def test_eqtb_fine_noun_maps_to_fusha_coarse_noun(self) -> None:
        self.assertEqual("noun", coarse_pos("NOUN_PLACE", source="eqtb"))
        report = evaluate_layer(fixture_rows()[4:5], source="eqtb", layer="pos", split="dev")
        self.assertEqual(1.0, report["emit_accuracy"]["value"])

    def test_eqtb_governor_report_is_always_silver_flagged(self) -> None:
        report = evaluate_layer(fixture_rows()[6:7], source="eqtb", layer="governor", split="test")
        self.assertIs(True, report["eqtb_syntax_is_partly_dl_silver"])
        self.assertIn("dl_only", report["provenance_split"])

    def test_inter_gold_disagreement_is_not_wrong_resolve(self) -> None:
        report = evaluate_layer(fixture_rows()[8:9], source="quranmorph", layer="pos", split="test")
        self.assertEqual(1, report["buckets"]["gold_error_candidate"])
        self.assertIn("inter-gold-disagreement", report["flags"])
        self.assertEqual(0, report["wrong_resolve_rate"]["numerator"])
        self.assertEqual(["gold_error_candidate"], [item["bucket"] for item in report["disagreements"]])

    def test_real_source_join_is_norm_strict_and_quarantines_unalignable_spans(self) -> None:
        primary = [{"unit_id": "quran:1:1", "surface": "إيمان", "quranmorph": {"surface": "إيمان"}}]
        other = [{"unit_id": "quran:1:1", "surface": "أيمان", "pos": "N"}]
        attach_other_gold(primary, other, "eqtb")
        self.assertNotIn("eqtb", primary[0])
        self.assertIs(True, primary[0]["_inter_gold_unalignable"])

    def test_each_disagreement_gets_one_taxonomy_bucket(self) -> None:
        report = evaluate_layer(fixture_rows()[0:3], source="quranmorph", layer="root", split="dev")
        token_ids = [item["token_id"] for item in report["disagreements"]]
        self.assertEqual(len(token_ids), len(set(token_ids)))
        self.assertTrue(all(item["bucket"] in report["buckets"] for item in report["disagreements"]))

    def test_split_overlap_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "appears in both"):
            validate_split_non_overlap([{"unit_id": "synthetic:x"}], [{"unit_id": "synthetic:x"}])

    def test_report_rejects_collapsed_score_keys_recursively(self) -> None:
        validate_no_collapsed_score({"reports": [{"coverage": {"value": 1.0}}]})
        with self.assertRaisesRegex(ValueError, "overall_score"):
            validate_no_collapsed_score({"nested": {"overall_score": 0.9}})

    def test_hash_mismatch_and_placeholder_refuse_to_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.tsv"
            path.write_text("synthetic\n", encoding="utf-8")
            with self.assertRaises(PinError):
                verify_pinned_file(path, {"sha256": "TO_PIN"})
            with self.assertRaises(PinError):
                verify_pinned_file(path, {"sha256": "0" * 64})
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, verify_pinned_file(path, {"sha256": digest}))

    def test_eqtb_loader_projects_away_english_gloss_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "eqtb.csv"
            path.write_text("surface,pos,english_gloss,translation\nلفظ,N,forbidden prose,also prose\n", encoding="utf-8")
            pin = hashlib.sha256(path.read_bytes()).hexdigest()
            rows = load_eqtb(path, {"sha256": pin})
            self.assertEqual(["pos", "surface"], sorted(rows[0]))
            self.assertNotIn("forbidden prose", json.dumps(rows, ensure_ascii=False))

    def test_eqtb_loader_prefers_uthmani_surface_for_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "eqtb.csv"
            path.write_text("surface,uthmani,pos\nاملائي,عُثْمَانِي,N\n", encoding="utf-8")
            pin = hashlib.sha256(path.read_bytes()).hexdigest()
            rows = load_eqtb(path, {"sha256": pin})
            self.assertEqual("عُثْمَانِي", rows[0]["surface"])
            self.assertEqual("uthmani", rows[0]["orthography"])

    def test_cli_self_tests_are_offline_and_green(self) -> None:
        for script in ("runner.py", "validate.py"):
            result = subprocess.run(
                [sys.executable, str(HERE / script), "--self-test"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_synthetic_user_local_files_run_end_to_end_with_pins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            qm = base / "qm.jsonl"
            eqtb = base / "eqtb.csv"
            qm.write_text(
                json.dumps({"unit_id": "quran:99:1", "token_id": "q1", "surface": "لفظ", "pos": "NOUN"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            eqtb.write_text("unit_id,token_id,surface,pos,english_gloss\nquran:99:1,e1,لفظ,N,synthetic prose\n", encoding="utf-8")
            pins = {
                "schema": "fusha/rm38-data-pins@1",
                "split_seed": "rm38-eval-v1",
                "sources": {
                    "quranmorph": {
                        "sha256": hashlib.sha256(qm.read_bytes()).hexdigest(), "filename": qm.name,
                        "attribution": "synthetic QuranMorph fixture", "license": "CC BY 4.0",
                    },
                    "eqtb": {
                        "sha256": hashlib.sha256(eqtb.read_bytes()).hexdigest(), "filename": eqtb.name,
                        "attribution": "synthetic EQTB fixture", "license": "CC BY 4.0",
                    },
                },
            }
            pins_path = base / "pins.json"
            pins_path.write_text(json.dumps(pins), encoding="utf-8")
            out = base / "out"
            split = split_for_unit("quran:99:1", pins["split_seed"])
            result = subprocess.run(
                [sys.executable, str(HERE / "runner.py"), "--quranmorph", str(qm), "--eqtb", str(eqtb),
                 "--pins", str(pins_path), "--split", split, "--layer", "all", "--out", str(out)],
                cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            reports = sorted(out.glob("*-report.json"))
            self.assertEqual(12, len(reports))
            for path in reports:
                payload = json.loads(path.read_text(encoding="utf-8"))
                validate_no_collapsed_score(payload)
                self.assertNotIn("synthetic prose", json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
