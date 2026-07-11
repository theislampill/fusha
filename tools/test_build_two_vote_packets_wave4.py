#!/usr/bin/env python3
"""Permanent fixture tests for Wave 4 two-vote packet selection."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import build_two_vote_packets as subject


LEXICAL = "competing_lexical_senses"
OCCURRENCE = "unresolved_occurrence_ambiguity"


def classification(loc: str, lane: str = LEXICAL, **extra: object) -> dict[str, object]:
    return {"canonical_location": loc, "laneb_classification": lane, **extra}


def queue_row(loc: str, **extra: object) -> dict[str, object]:
    return {
        "canonical_location": loc,
        "primary_resolution_family": "multiple_qword_candidates",
        "provenance_state": "unresolved_candidate",
        "review_state": "pending",
        **extra,
    }


def selected_locations(selected: list[tuple[str, dict[str, object]]]) -> list[str]:
    return [str(row["canonical_location"]) for _lane, row in selected]


class Wave4SelectionFixtureTests(unittest.TestCase):
    def test_current_index_tatweel_combining_hamza_matches_standalone_hamza(self) -> None:
        self.assertEqual(
            subject.norm_strict("ٱلْـَٔاخِرَةِ"),
            subject.norm_strict("ٱلْءَاخِرَةِ"),
        )

    def test_stale_loc_surface_index_sha_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue = root / "queue.jsonl"
            manifest = root / "queue.manifest.json"
            loc_index = root / "loc-index.jsonl"
            queue.write_text('{"canonical_location":"2:1:1"}\n', encoding="utf-8")
            manifest.write_text(
                json.dumps({"queue_sha256": subject.sha256_file(queue)}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            loc_index.write_text('{"loc":"2:1:1","surface":"x"}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"STOP: loc-surface index SHA-256"):
                subject.verify_wave_4_queue_pin(
                    queue,
                    manifest,
                    subject.sha256_file(manifest),
                    loc_index,
                    "0" * 64,
                )

    def test_stale_queue_sha_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue = root / "queue.jsonl"
            manifest = root / "queue.manifest.json"
            queue.write_text('{"canonical_location":"2:1:1"}\n', encoding="utf-8")
            manifest.write_text(
                json.dumps({"queue_sha256": subject.sha256_file(queue)}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            pinned_manifest_sha = subject.sha256_file(manifest)

            with self.assertRaisesRegex(ValueError, r"STOP: queue manifest SHA-256"):
                subject.verify_wave_4_queue_pin(queue, manifest, "0" * 64)

            queue.write_text('{"canonical_location":"2:1:2"}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"STOP: queue SHA-256"):
                subject.verify_wave_4_queue_pin(queue, manifest, pinned_manifest_sha)

    def test_review_required_or_quarantined_row_is_never_selected(self) -> None:
        rows = [classification("11:44:8"), classification("11:44:9")]
        queue = {
            "11:44:8": queue_row(
                "11:44:8",
                review_state="review_required",
                data_quality_quarantine=True,
            ),
            "11:44:9": queue_row("11:44:9"),
        }

        selected = subject.select_wave_4_rows(
            rows,
            queue_by_loc=queue,
            excluded_locations=set(),
            excluded_review_fact_ids=set(),
            strata={LEXICAL: 1, OCCURRENCE: 0},
        )

        self.assertEqual(selected_locations(selected), ["11:44:9"])

    def test_terminal_rm20_repair_is_not_selectable_as_live_only(self) -> None:
        rows = [classification("2:1:1"), classification("2:1:2")]
        queue = {
            "2:1:1": queue_row(
                "2:1:1",
                primary_resolution_family="in_crosswalk_morphline_repair",
                provenance_state="resolved",
                repair_provenance={"terminal": True, "wave": "RM-20"},
                shadow_effect="live_only",
            ),
            "2:1:2": queue_row("2:1:2"),
        }

        selected = subject.select_wave_4_rows(
            rows,
            queue_by_loc=queue,
            excluded_locations=set(),
            excluded_review_fact_ids=set(),
            strata={LEXICAL: 1, OCCURRENCE: 0},
        )

        self.assertEqual(selected_locations(selected), ["2:1:2"])

    def test_promoted_location_or_review_fact_id_is_not_selected_again(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reports = []
            for wave in (1, 2, 3):
                report = Path(temporary) / f"laneb-wave-0{wave}.report.json"
                report.write_text(
                    json.dumps(
                        {
                            "schema": "qamus.laneb_wave_promotion_report.v1",
                            "rows": [
                                {
                                    "canonical_location": f"2:1:{wave}",
                                    "review_fact_id": f"sha256:promoted-fact-{wave}",
                                }
                            ],
                        },
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                reports.append(report)
            exclusions = subject.load_wave_4_exclusions(reports)

        rows = [
            classification("2:1:1"),
            classification("2:1:4", review_fact_id="sha256:promoted-fact-2"),
            classification("2:1:5"),
        ]
        queue = {loc: queue_row(loc) for loc in ("2:1:1", "2:1:4", "2:1:5")}
        selected = subject.select_wave_4_rows(
            rows,
            queue_by_loc=queue,
            excluded_locations=exclusions.locations,
            excluded_review_fact_ids=exclusions.review_fact_ids,
            strata={LEXICAL: 1, OCCURRENCE: 0},
        )

        self.assertEqual(selected_locations(selected), ["2:1:5"])

    def test_double_run_selection_artifact_is_byte_identical(self) -> None:
        rows = [classification("10:1:2"), classification("2:1:1")]
        queue = {loc: queue_row(loc) for loc in ("2:1:1", "10:1:2")}
        kwargs = {
            "queue_by_loc": queue,
            "excluded_locations": set(),
            "excluded_review_fact_ids": set(),
            "strata": {LEXICAL: 2, OCCURRENCE: 0},
        }

        first = subject.render_wave_4_selection_artifact(
            subject.select_wave_4_rows(rows, **kwargs)
        )
        second = subject.render_wave_4_selection_artifact(
            subject.select_wave_4_rows(reversed(rows), **kwargs)
        )

        self.assertEqual(first, second)

    def test_d07_tie_break_artifact_is_ordering_only_and_has_no_conclusion(self) -> None:
        tied = [
            classification("2:1:2", semantic_conclusion="candidate-b"),
            classification("2:1:1", semantic_conclusion="candidate-a"),
        ]
        queue = {loc: queue_row(loc) for loc in ("2:1:1", "2:1:2")}
        selected = subject.select_wave_4_rows(
            tied,
            queue_by_loc=queue,
            excluded_locations=set(),
            excluded_review_fact_ids=set(),
            strata={LEXICAL: 1, OCCURRENCE: 0},
        )
        artifact = subject.render_wave_4_selection_artifact(selected)
        records = [json.loads(line) for line in artifact.decode("utf-8").splitlines()]

        self.assertEqual(records[0]["canonical_location"], "2:1:1")
        self.assertEqual(records[0]["selection_basis"], "ordering_only")
        self.assertEqual(
            set(records[0]),
            {"canonical_location", "schema", "selection_basis", "selection_rank", "stratum"},
        )

    def test_active_queue_rows_are_partitioned_once_with_requested_side_routes(self) -> None:
        selected_row = queue_row("2:1:1")
        lane_a_row = queue_row(
            "2:1:2",
            primary_resolution_family="unique_qword_candidate",
            candidate_entry_ids=["entry-a"],
            candidate_qword_row_ids=["qword-a"],
        )
        review_row = queue_row("2:1:3")
        blocked_row = queue_row("2:1:4", primary_resolution_family="no_qword_candidate")
        quarantined_row = queue_row(
            "2:1:5",
            review_state="review_required",
            data_quality_quarantine=True,
        )
        classifications = {
            "2:1:1": classification("2:1:1"),
            "2:1:3": classification(
                "2:1:3",
                lane="normalization_collision",
                evidence={"candidate_norm_strict_values": ["x", "y"]},
            ),
        }

        routed = subject.partition_wave_4_rows(
            [selected_row, lane_a_row, review_row, blocked_row, quarantined_row],
            classifications_by_loc=classifications,
            selected=[(LEXICAL, classification("2:1:1"))],
        )

        self.assertEqual(
            {route: [row["canonical_location"] for row in rows] for route, rows in routed.items()},
            {
                "selected": ["2:1:1"],
                "lane-a-eligible": ["2:1:2"],
                "review-routing": ["2:1:3"],
                "blocked": ["2:1:4"],
                "quarantined": ["2:1:5"],
            },
        )
        self.assertEqual(
            routed["lane-a-eligible"][0]["candidate_entry_ids"],
            ["entry-a"],
        )
        self.assertEqual(
            routed["review-routing"][0]["collision_evidence"],
            {"candidate_norm_strict_values": ["x", "y"]},
        )
        self.assertEqual(sum(map(len, routed.values())), 5)

    def test_wave_4_write_emits_named_side_artifacts_beside_packet_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet_out = root / "packets-wave-04.jsonl"
            manifest_out = root / "wave-04.manifest.json"
            side_artifacts = {
                "lane-a-eligible": b'{"canonical_location":"2:1:2"}\n',
                "review-routing": b'{"canonical_location":"2:1:3"}\n',
            }

            subject.write_outputs(
                {"schema": "fixture", "output": {}},
                [],
                packet_out,
                manifest_out,
                side_artifacts=side_artifacts,
            )

            self.assertEqual(
                (root / "lane-a-eligible.jsonl").read_bytes(),
                side_artifacts["lane-a-eligible"],
            )
            self.assertEqual(
                (root / "review-routing.jsonl").read_bytes(),
                side_artifacts["review-routing"],
            )

    def test_morphology_record_carries_target_self_from_live_payload(self) -> None:
        record = subject.build_morphology_record(
            target_loc="2:1:1",
            target_surface="وَشُرَكَاءُ",
            target_source_address="qamus/indexes/quran-loc-surface/index.jsonl#loc=2:1:1",
            target_live_payload={
                "morphline": "root ش ر ك · noun · broken plural",
                "segments": [
                    {"class": "qg-conjunction", "surface": "وَ"},
                    {"class": "qg-noun-stem", "surface": "شُرَكَاءُ"},
                ],
            },
            target_live_source_address="baseline.jsonl#loc=2:1:1",
            carriers=[],
            entries={},
            entries_path=Path("entries.jsonl"),
            homograph_index={},
            homograph_path=Path("homographs.json"),
        )

        self.assertEqual(record["target_self"]["surface"]["value"], "وَشُرَكَاءُ")
        self.assertEqual(record["target_self"]["root"]["value"], "ش ر ك")
        self.assertEqual(record["target_self"]["pos"]["value"], "noun")
        self.assertFalse(record["target_self"]["particle_flag"]["value"])
        self.assertIn("baseline.jsonl#loc=2:1:1", record["target_self"]["root"]["source_address"])

    def test_target_self_uses_live_roles_and_closed_function_classes(self) -> None:
        noun = subject._target_self_from_live_payload(
            target_surface="ٱلْحَيَوٰةُ",
            target_source_address="index#loc=13:26:11",
            live_payload={
                "morphline": "definite article + noun stem",
                "segments": [
                    {"class": "qg-article", "role": "definite_article"},
                    {"class": "qg-segment", "role": "noun_stem"},
                ],
            },
            live_source_address="live#loc=13:26:11",
        )
        conditional = subject._target_self_from_live_payload(
            target_surface="إِذَآ",
            target_source_address="index#loc=11:102:4",
            live_payload={
                "morphline": "temporal/conditional particle · no lexical root",
                "segments": [
                    {"class": "qg-conditional", "role": "temporal_conditional_particle"}
                ],
            },
            live_source_address="live#loc=11:102:4",
        )
        pronoun = subject._target_self_from_live_payload(
            target_surface="هُوَ",
            target_source_address="index#loc=2:1:1",
            live_payload={
                "morphline": "independent pronoun",
                "segments": [{"class": "qg-pronoun", "role": "pronoun"}],
            },
            live_source_address="live#loc=2:1:1",
        )

        self.assertEqual(noun["pos"]["value"], "noun")
        self.assertEqual(conditional["pos"]["value"], "particle")
        self.assertTrue(conditional["particle_flag"]["value"])
        self.assertEqual(pronoun["pos"]["value"], "pronoun")

    def test_candidate_role_is_derived_only_from_target_fingerprint_coverage(self) -> None:
        self.assertEqual(
            subject.candidate_role(["2:1:1"], "2:1:1"),
            "aligns_to_target_token",
        )
        self.assertEqual(
            subject.candidate_role(["2:1:2"], "2:1:1"),
            "host_lexeme_incidental",
        )
        self.assertEqual(
            subject.candidate_role(["2:1:1", "2:1:2"], "2:1:1"),
            "aligns_to_target_token",
        )

    def test_affirm_live_no_carrier_conclusion_requires_rationale(self) -> None:
        schema = subject.response_schema(
            {"tier": "two_vote_required"},
            {"packet": "sha256:fixture"},
        )

        conclusion = schema["properties"]["proposed_conclusion"]
        self.assertIn(
            {"const": "affirm_live_no_carrier_owns_token"},
            conclusion["anyOf"],
        )
        self.assertIn("conclusion_rationale", schema["required"])
        self.assertEqual(
            schema["properties"]["conclusion_rationale"],
            {"type": "string", "minLength": 1},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
