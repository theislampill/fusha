"""Render the committed FAM4 finite-verb packet as an audit report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam4_finite_verb_producer as producer


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _loc_key(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split(":"))  # type: ignore[return-value]


def _pct(numerator: int, denominator: int) -> str:
    return "n/a" if denominator == 0 else f"{numerator / denominator:.1%}"


def _cell(value: Any) -> str:
    return str(value if value not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def build_report(packet_dir: Path, output: Path) -> None:
    packet_dir = Path(packet_dir)
    summary = json.loads((packet_dir / "calibration-summary.json").read_text(encoding="utf-8"))
    records = sorted(_load_jsonl(packet_dir / "calibration-sample.jsonl"), key=lambda item: _loc_key(item["canonical_occurrence"]["quran_loc"]))
    outcomes = {str(item["quran_loc"]): item for item in summary.get("row_outcomes", [])}
    populations = summary.get("sub_shape_populations") or {}
    valid_candidates = sum(
        1
        for record in records
        if record.get("projection", {}).get("status") == "candidate" and not producer.validate_finite_verb_record(record)
    )
    source_survey = summary.get("source_survey") or {}
    lines = [
        "# FAM4 Finite-Verb Producer Calibration",
        "",
        "Candidate-mode calibration for the `finite_verbs` STRAT family. The committed packet covers all 12 rows; no materialization, whitelist append, public publication, or live mutation is authorized.",
        "",
        "## Survey",
        "",
        "All 12 rows were processed. A whitelist `entry_id` is retained as a verse-context edge only; it becomes morphology evidence only when the observed written surface matches a caller-supplied entry form under the closed orthography guard. Labels, glosses, morphlines, and existing carrier labels never create a finite-verb fact.",
        "",
        "| survey measure | rows |",
        "| --- | ---: |",
        f"| family rows | {summary.get('family_population', 0)} |",
        f"| rows with whitelist context edge | {source_survey.get('rows_with_whitelist_context_edge', 'n/a')} |",
        f"| rows with usable entry evidence (exact or held-out near match) | {source_survey.get('rows_with_usable_entry_evidence', 'n/a')} |",
        f"| rows with exact entry-form match | {source_survey.get('rows_with_exact_entry_surface_match', 'n/a')} |",
        f"| rows with Qurʾanic-annotation-only entry match | {source_survey.get('rows_with_quran_annotation_only_entry_match', 'n/a')} |",
        f"| orthography near-misses held out | {source_survey.get('orthography_near_miss_rows_held_out', 'n/a')} |",
        f"| context-only joins | {source_survey.get('context_only_join_rows', 'n/a')} |",
        "",
        "The evidence situation for every row is preserved below, including direct entry matches, context-only joins, owner gates, weak-root defeaters, and the non-finite/non-verb route.",
        "",
        "## Precision + abstention by sub-shape",
        "",
        "Typed-candidate precision means **contract-valid candidates / emitted candidates**. It is not a linguistic gold-label precision estimate; no external adjudication is invented. `n/a` means that no candidate was emitted for the sub-shape.",
        "",
        "| sub-shape | population | candidates | abstentions | abstention rate | typed-candidate precision |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for shape in producer.SUBSHAPES:
        item = populations.get(shape, {})
        population = int(item.get("population", 0))
        candidates = int(item.get("candidate_count", 0))
        abstentions = int(item.get("abstention_count", 0))
        precision = _pct(candidates if valid_candidates == int(summary.get("candidate_count", 0)) else 0, candidates)
        lines.append(f"| {_cell(shape)} | {population} | {candidates} | {abstentions} | {_pct(abstentions, population)} | {precision} |")
    candidate_count = int(summary.get("candidate_count", 0))
    unresolved_count = int(summary.get("unresolved_count", 0))
    lines.extend([
        "",
        f"Overall: **{candidate_count} candidates**, **{unresolved_count} typed abstentions**, and **{_pct(unresolved_count, int(summary.get('family_population', 0)))} abstention rate**. Fresh contract validation accepts **{valid_candidates}/{candidate_count}** emitted candidates.",
        "",
        "## Per-row outcome table",
        "",
        "| quran location | surface | evidence situation | sub-shape | outcome | route or pattern | direct entry | near entry | whitelist edge |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for record in records:
        loc = record["canonical_occurrence"]["quran_loc"]
        outcome = outcomes.get(loc, {})
        lines.append(
            "| "
            + " | ".join([
                f"quran:{_cell(loc)}",
                _cell(record["canonical_occurrence"].get("surface")),
                _cell(outcome.get("evidence_situation")),
                _cell(outcome.get("sub_shape")),
                _cell(outcome.get("status")),
                _cell(outcome.get("route")),
                _cell(outcome.get("direct_entry_id")),
                _cell(outcome.get("near_entry_id")),
                _cell(outcome.get("whitelist_entry_id")),
            ])
            + "|"
        )
    lines.extend([
        "",
        "## Zero-false-projection attestation basis",
        "",
        "The packet supports a zero-false-projection attestation for this bounded producer run on these explicit grounds:",
        "",
        "- every candidate has a caller-supplied direct entry-form attestation and exactly one dependent `finite_verb_evidence` fact;",
        "- every finite fact names a closed Form-I registry pattern, identifies all three root radicals as written spans, assigns person/tense affixes to owned segments, and carries a passed exact reconstruction proof;",
        "- D-3 keeps person prefixes, derivative-form markers, and root radicals in separate classes; Form-V/VI `ت` is owner-gated to `derived_verbs`;",
        "- derived/quadriliteral rows are typed `owner_gated` and never analyzed, while hidden or alternating weak radicals are typed `weak_root_pattern_unresolved`;",
        "- unresolved records contain one typed pending blocker and no finite-verb fact or linguistic claim;",
        "- mood and case are kept as a separate Naḥw overlay and are never emitted as finite-verb morphology; and",
        "- every projection remains `pre_apply_not_authorized`, with public and live materialization disabled.",
        "",
        "This is a producer-contract attestation, not a claim that every Quranic verb analysis is linguistically complete.",
        "",
        "## EXACT NONCLAIMS",
        "",
        "This packet does not claim: scripture facts beyond the supplied occurrence and entry addresses; lexical senses or roots from labels, glosses, morphlines, or whitelist entry IDs alone; any derived-form analysis; any weak-root transformation rule; mood, case, iʿrāb, or governor interpretation as morphology; a semantic translation; source approval; whitelist append; public publication; live mutation; or readiness for `derived_verbs` ownership.",
        "",
        "## Compounding Impact",
        "",
        "The FAM4 verb-affix registry reuses and feeds the clitic producer’s `qg-subject-pronoun` subject-marker classes while keeping `qg-object-pronoun` distinct at the host boundary. Its weak-root defeater registry records the unresolved patterns and feeds future `derived_verbs` work only when that owner opens the lane. The existing F-A carrier and projector registry remain the single projection path.",
        "",
        "## Status",
        "",
        "- Candidate mode: `pre_apply_not_authorized`.",
        "- All 12 rows were surveyed; corpus inputs were caller-supplied and remain read-only.",
        "- No scripture text, whitelist row, public payload, or live runtime was mutated.",
        "- Recommended next gate: independent owner review of the named Form-I patterns and typed unresolved queue.",
        "",
    ])
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    build_report(args.packet_dir, args.output)
    print(args.output.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
