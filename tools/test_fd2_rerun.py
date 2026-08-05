"""Red-first tests for the producer-aware FD2 rerun path."""

from __future__ import annotations

import unittest
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from tools import fd_compiler
from tools import fd2_rerun
from tools import validate_fd2_rerun


def _fb_record(surface: str = "وَكِتَابُهُ") -> dict:
    return {
        "record_type": "projection_input",
        "canonical_occurrence": {
            "quran_loc": "1:1:1",
            "surface": surface,
        },
        "facts": [
            {
                "fact_type": "function_component",
                "fact_value": {
                    "typed_kind": "nahw.function_component",
                    "segment_index": 0,
                    "role": "prefix_conjunction",
                    "class": "qg-conjunction",
                    "surface": "وَ",
                    "label": "WA",
                },
            },
            {
                "fact_type": "host_component",
                "fact_value": {
                    "typed_kind": "sarf.host",
                    "segment_index": 1,
                    "role": "host",
                    "class": "qg-noun-stem",
                    "surface": "كِتَابُ",
                    "label": "HOST",
                },
            },
            {
                "fact_type": "clitic_component",
                "fact_value": {
                    "typed_kind": "sarf.clitic_component",
                    "segment_index": 2,
                    "role": "attached_pronoun",
                    "class": "qg-possessive-pronoun",
                    "surface": "هُ",
                    "label": "PRON",
                },
            },
            {
                "fact_type": "clitic_composition",
                "fact_value": {
                    "typed_kind": "sarf.clitic_pronoun_composition",
                    "component_fact_ids": ["function", "host", "clitic"],
                    "surface": surface,
                },
            },
        ],
    }


def _fc_record(surface: str = "وَكِتَابُهُ") -> dict:
    return {
        "record_type": "projection_input",
        "canonical_occurrence": {
            "quran_loc": "1:1:1",
            "surface": surface,
        },
        "facts": [
            {
                "fact_type": "nahw_dependency",
                "fact_value": {
                    "role": "subject",
                    "relationship": "subject_of",
                    "governor": {"occurrence_id": "quran:1:1:0", "surface": "كَتَبَ"},
                    "governed_occurrence": {"occurrence_id": "quran:1:1:1", "surface": surface},
                    "case_or_mood": {"applicability": "case", "value": "nominative", "status": "observed"},
                    "ending": {"value": "ُ", "status": "visible", "reason": "fixture"},
                },
            }
        ],
    }


class FactDerivedViewTests(unittest.TestCase):
    def test_fact_derived_views_use_exact_labels_and_plain_english(self) -> None:
        views = fd_compiler.build_fact_derived_views("وَكِتَابُهُ", _fb_record(), _fc_record())

        self.assertIn("Ṣarf — how this piece forms the word", views["sarf_text"])
        self.assertIn("Naḥw — what this piece does here", views["nahw_text"])
        self.assertIn("Composition", views["composition_text"])
        self.assertTrue(views["n_lang_clean"])
        self.assertTrue(views["compact_view"])
        self.assertTrue(views["expanded_view"])
        self.assertEqual(views["compact_view"]["payload_id"], views["expanded_view"]["payload_id"])
        self.assertNotIn("source-addressed", views["learner_explanation"])
        self.assertNotIn("candidate", views["learner_explanation"].lower())

    def test_surface_conflict_is_not_silently_projected(self) -> None:
        views = fd_compiler.build_fact_derived_views("وَكِتَابُهُ", _fb_record("وَغَيْرُهُ"), None)
        self.assertTrue(views["projection_conflicts"])


class ProducerScopeTests(unittest.TestCase):
    def test_collection_never_applies_fb_outside_calibrated_family(self) -> None:
        clitic = {
            "loc": "12:59:5",
            "quran_loc": "quran:12:59:5",
            "wbw_loc": "wbw:12:59:5",
            "surface": "ٱئْتُونِى",
            "morphology_family": "clitic_pronoun_compositions",
            "segments": [
                {"segment_index": 0, "surface": "ٱئْتُو", "role": "verb_stem", "class": "qg-verb-stem"},
                {"segment_index": 1, "surface": "نِى", "role": "object_pronoun", "class": "qg-object-pronoun"},
            ],
        }
        lexical = dict(clitic)
        lexical.update({"loc": "1:1:2", "quran_loc": "quran:1:1:2", "wbw_loc": "wbw:1:1:2", "surface": "كِتَابٌ", "morphology_family": "lexical_nouns_adjectives", "segments": [{"segment_index": 0, "surface": "كِتَابٌ", "role": "host", "class": "qg-noun-stem"}]})
        result = fd_compiler.collect_calibrated_producer_records(
            [
                {"loc": "12:59:5", "morphology_family": "clitic_pronoun_compositions", "surface": clitic["surface"]},
                {"loc": "1:1:2", "morphology_family": "lexical_nouns_adjectives", "surface": lexical["surface"]},
            ],
            [{"loc": "12:59:5", "verdict": "verified"}, {"loc": "1:1:2", "verdict": "verified"}],
            [clitic, lexical],
            corpus_source_name="fixture.jsonl",
        )
        self.assertIn("12:59:5", result["fb_records"])
        self.assertNotIn("1:1:2", result["fb_records"])


class MatrixTests(unittest.TestCase):
    def test_matrix_reports_fact_completion_movement_and_occurrence_parity(self) -> None:
        source = {
            "loc": "1:1:1",
            "surface": "وَكِتَابُهُ",
            "entry_id": "entry-1",
            "projector_id": "source.projector",
            "segments": [
                {"segment_index": 0, "surface": "وَ", "role": "prefix_conjunction", "class": "qg-conjunction"},
                {"segment_index": 1, "surface": "كِتَابُ", "role": "host", "class": "qg-noun-stem"},
                {"segment_index": 2, "surface": "هُ", "role": "attached_pronoun", "class": "qg-possessive-pronoun"},
            ],
        }
        verdicts, report = fd_compiler.compile_fd2_rows(
            [{"loc": "1:1:1", "morphology_family": "clitic_pronoun_compositions", "surface": source["surface"]}],
            [{"loc": "1:1:1", "verdict": "verified"}],
            [source],
            [{"id": "entry-1"}],
            {"1:1:1": {"loc": "1:1:1", "unique": True, "appearance_count": 2, "appearances": [{"surface_kind": "reader"}, {"surface_kind": "entry_example"}], "projection_hash": "a" * 64}},
            fb_records_by_loc={"1:1:1": _fb_record()},
            fc_records_by_loc={"1:1:1": _fc_record()},
        )

        self.assertEqual(len(verdicts), 1)
        self.assertEqual(report["metrics"]["rows with complete morphology facts"], 1)
        self.assertEqual(report["metrics"]["rows with complete naḥw facts"], 1)
        self.assertEqual(report["metrics"]["rows with both"], 1)
        self.assertEqual(report["metrics"]["rows with repeated-appearance parity"], 1)
        self.assertEqual(report["movement"]["before"]["rows needing F-B"], 437)
        self.assertEqual(report["movement"]["before"]["rows needing F-C"], 437)
        self.assertEqual(report["movement"]["before"]["rows lacking learner-language"], 383)
        self.assertEqual(report["movement"]["before"]["rows with repeated-appearance coverage"], 0)
        self.assertFalse(verdicts[0]["live_mutation_allowed"])

    def test_unresolved_fb_blockers_have_one_exact_prefixed_code(self) -> None:
        unresolved = _fb_record()
        unresolved["record_type"] = "unresolved_projection"
        unresolved["facts"] = [{
            "fact_type": "unresolved_projection",
            "fact_value": {"reason_codes": ["function_ambiguity"]},
        }]
        source = {
            "loc": "1:1:1",
            "surface": "وَكِتَابُهُ",
            "entry_id": "entry-1",
            "segments": [
                {"segment_index": 0, "surface": "وَ", "role": "prefix_conjunction", "class": "qg-conjunction"},
                {"segment_index": 1, "surface": "كِتَابُ", "role": "host", "class": "qg-noun-stem"},
                {"segment_index": 2, "surface": "هُ", "role": "attached_pronoun", "class": "qg-possessive-pronoun"},
            ],
        }
        _, report = fd_compiler.compile_fd2_rows(
            [{"loc": "1:1:1", "morphology_family": "clitic_pronoun_compositions", "surface": source["surface"]}],
            [{"loc": "1:1:1", "verdict": "verified"}],
            [source],
            [{"id": "entry-1"}],
            {"1:1:1": {"loc": "1:1:1", "unique": True, "appearance_count": 2, "appearances": [{}, {}], "projection_hash": "a" * 64}},
            fb_records_by_loc={"1:1:1": unresolved},
            producer_diagnostics={"fb_blockers_by_loc": {"1:1:1": ["function_ambiguity"]}},
        )
        blockers = report["metrics"]["unresolved rows by exact blocker"]
        self.assertEqual(blockers.get("fb1.function_ambiguity"), 1)
        self.assertNotIn("function_ambiguity", blockers)


class RerunWriterTests(unittest.TestCase):
    def test_runner_script_bootstraps_repo_imports(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(fd2_rerun.__file__)), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_path_runner_writes_report_verdicts_meta_and_markdown(self) -> None:
        source = {
            "loc": "1:1:1",
            "surface": "وَكِتَابُهُ",
            "entry_id": "entry-1",
            "segments": [
                {"segment_index": 0, "surface": "وَ", "role": "prefix_conjunction", "class": "qg-conjunction"},
                {"segment_index": 1, "surface": "كِتَابُ", "role": "host", "class": "qg-noun-stem"},
                {"segment_index": 2, "surface": "هُ", "role": "attached_pronoun", "class": "qg-possessive-pronoun"},
            ],
        }
        with TemporaryDirectory() as temp:
            root = Path(temp)
            strat = root / "strat.jsonl"
            verdicts = root / "v575.jsonl"
            corpus = root / "corpus.jsonl"
            entries = root / "entries.jsonl"
            index = root / "index.jsonl"
            report = root / "fd2-455-report.json"
            output_verdicts = root / "fd2-455-verdicts.jsonl"
            meta = root / "fd2-455-verdicts.meta.json"
            markdown = root / "report.md"
            fd2_rerun._write_jsonl(strat, [{"loc": "1:1:1", "surface": source["surface"], "morphology_family": "clitic_pronoun_compositions"}])
            fd2_rerun._write_jsonl(verdicts, [{"loc": "1:1:1", "verdict": "verified"}])
            fd2_rerun._write_jsonl(corpus, [source])
            fd2_rerun._write_jsonl(entries, [{"id": "entry-1"}])
            fd2_rerun._write_jsonl(index, [{"loc": "1:1:1", "unique": True, "appearance_count": 2, "appearances": [{"surface_kind": "reader"}, {"surface_kind": "entry_example"}], "projection_hash": "a" * 64}])
            fd2_rerun.run_rerun(
                strat,
                verdicts,
                corpus,
                entries,
                report,
                output_verdicts,
                meta,
                markdown,
                occurrence_index_path=index,
            )
            self.assertTrue(report.is_file())
            self.assertEqual(1, len(output_verdicts.read_text(encoding="utf-8").splitlines()))
            self.assertTrue(meta.is_file())
            self.assertIn("EXACT NONCLAIMS", markdown.read_text(encoding="utf-8"))
            self.assertNotIn(str(root), report.read_text(encoding="utf-8"))


class ValidatorTests(unittest.TestCase):
    def test_validator_rejects_live_mutation(self) -> None:
        errors = validate_fd2_rerun.validate_fd2_artifacts(
            {"live_mutation_allowed": True},
            [],
            {},
        )
        self.assertTrue(any("live_mutation_allowed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
