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


if __name__ == "__main__":
    unittest.main(verbosity=2)
