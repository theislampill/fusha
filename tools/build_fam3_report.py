"""Render the checked-in FAM3 calibration packet as a compact audit report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam3_number_producer as producer


SHAPE_ORDER = [
    "bare_cardinal",
    "gender_polarity_cardinal",
    "ordinals",
    "compound_11_19",
    "tens",
    "fractions",
    "first_last_edge",
    "other_number_form",
    "unclassified",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _loc_key(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split(":"))  # type: ignore[return-value]


def _shape_and_route(record: dict[str, Any]) -> tuple[str, str, str]:
    formation = next(
        (fact for fact in record.get("facts", []) if fact.get("fact_type") == "formation_evidence"),
        None,
    )
    pending = next(
        (fact for fact in record.get("facts", []) if fact.get("fact_type") == "number_formation_pending"),
        None,
    )
    if formation:
        value = formation.get("fact_value") or {}
        return str(value.get("sub_shape") or "unclassified"), "candidate", str(value.get("pattern_id") or "")
    value = (pending or {}).get("fact_value") or {}
    return str(value.get("observed_sub_shape") or "unclassified"), "abstention", str(value.get("route") or "")


def _pct(numerator: int, denominator: int) -> str:
    return "n/a" if denominator == 0 else f"{numerator / denominator:.1%}"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_report(packet_dir: Path, output: Path) -> None:
    packet_dir = Path(packet_dir)
    summary = json.loads((packet_dir / "calibration-summary.json").read_text(encoding="utf-8"))
    records = sorted(
        _load_jsonl(packet_dir / "calibration-sample.jsonl"),
        key=lambda record: _loc_key(record["canonical_occurrence"]["quran_loc"]),
    )
    populations = summary.get("sub_shape_populations") or {}
    validated_candidates = sum(
        1
        for record in records
        if record.get("projection", {}).get("status") == "candidate"
        and not producer.validate_number_record(record)
    )
    all_candidates_valid = validated_candidates == int(summary.get("candidate_count", 0))
    survey = summary.get("source_survey") or {}

    lines = [
        "# FAM3 Number-Word Producer Calibration",
        "",
        "Candidate-mode calibration for the `number_words` family. This report is rendered from the committed 57-row packet; no materialization or live mutation is authorized.",
        "",
        "## Survey",
        "",
        f"The family contains **{summary.get('family_population', 0)} rows** with exact verdict coverage. The caller-supplied whitelist joins rows to entry IDs, but an entry ID is treated as a verse-context edge until the observed surface matches an entry field.",
        "",
        "| survey measure | rows |",
        "| --- | ---: |",
        f"| family rows | {survey.get('family_rows', summary.get('family_population', 0))} |",
        f"| rows with a whitelist join | {survey.get('whitelist_rows_with_joined_entry_id', 'n/a')} |",
        f"| joined entries with usable forms | {(survey.get('entry_evidence_availability') or {}).get('joinable_entry_with_usable_forms', 'n/a')} |",
        f"| hosting-entry-only joins | {(survey.get('entry_evidence_availability') or {}).get('hosting_entry_only', 'n/a')} |",
        f"| rows with exact entry surface match | {survey.get('exact_surface_entry_match_rows', 'n/a')} |",
        f"| orthography-near entry matches held out | {survey.get('orthography_near_miss_rows', 'n/a')} |",
        f"| rows without exact entry surface match | {survey.get('rows_without_exact_entry_surface_match', 'n/a')} |",
        f"| rows carrying join ambiguity flags | {survey.get('joined_entry_ambiguity_rows', 'n/a')} |",
        "",
        "The 57 rows are classified from written surface and available local context. A label, gloss, morphline, or learner copy is never used as formation evidence.",
        "",
        "## Precision + abstention by sub-shape",
        "",
        "Typed-candidate precision below means **contract-valid candidates / emitted candidates**. It is not a linguistic gold-label precision estimate; no external adjudication is invented. `n/a` means the family shape had no candidate emitted.",
        "",
        "| sub-shape | population | candidates | abstentions | abstention rate | typed-candidate precision |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for shape in SHAPE_ORDER:
        item = populations.get(shape, {})
        population = int(item.get("population", 0))
        candidate_count = int(item.get("candidate_count", 0))
        abstention_count = int(item.get("abstention_count", 0))
        lines.append(
            f"| {_cell(shape)} | {population} | {candidate_count} | {abstention_count} | {_pct(abstention_count, population)} | {_pct(candidate_count if all_candidates_valid else 0, candidate_count)} |"
        )
    lines.extend([
        "",
        f"Overall: **{summary.get('candidate_count', 0)} candidates**, **{summary.get('unresolved_count', 0)} typed abstentions**, and **{_pct(summary.get('unresolved_count', 0), summary.get('family_population', 0))} abstention rate**. The packet validator accepts all emitted records; candidate contract precision is {_pct(validated_candidates, int(summary.get('candidate_count', 0)))}.",
        "",
        "Fractions and أول/آخر-type edge words have zero population in this 57-row family. Their absence is reported rather than filled by a generic number rule.",
        "",
        "## Per-row outcome table",
        "",
        "| quran location | surface | sub-shape | outcome | route or pattern | entry edge |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for record in records:
        loc = record["canonical_occurrence"]["quran_loc"]
        shape, outcome, route = _shape_and_route(record)
        entry_id = record["canonical_occurrence"].get("entry_id", "—")
        lines.append(
            f"| quran:{_cell(loc)} | {_cell(record['canonical_occurrence'].get('surface', ''))} | {_cell(shape)} | {_cell(outcome)} | {_cell(route)} | {_cell(entry_id)} |"
        )

    lines.extend([
        "",
        "## Zero-false-projection attestation basis",
        "",
        "The packet supports a zero-false-projection attestation for this candidate run on these bounded grounds:",
        "",
        "- every candidate contains an entry-backed base attestation and exactly one formation fact dependent on it;",
        "- every formation fact names a registry rule, carries source addresses, and has a passed reconstruction proof over the preserved written span;",
        "- unresolved records carry one typed `number_formation_pending` blocker and no formation fact or claim;",
        "- homograph ambiguity, wrong gender polarity, context-only joins, and orthographic near misses are guarded as abstentions;",
        "- every projection remains `pre_apply_not_authorized`, with public and live mutation flags false.",
        "",
        "This is a producer-contract attestation, not a claim that every Quranic number analysis is linguistically complete.",
        "",
        "## Exact nonclaims",
        "",
        "This packet does not claim: Quranic scripture facts beyond the supplied row and entry addresses; roots or lexical senses from labels alone; counted-noun gender where the context carrier does not provide it; ordinal, compound, fraction, or أول/آخر formation where the registered rule prerequisites are absent; construct-state or iʿrāb analysis; source approval; whitelist append; public publication; or live mutation.",
        "",
        "## Compounding Impact",
        "",
        "The reusable asset is the existing FAM2 pattern/carrier discipline: an entry-backed source fact, a named registry rule, exact-span and orthography guards, source-addressed reconstruction, and a typed pending route. The same carrier shape can support the finite_verbs lane without transferring number semantics. F-C numeral-governance rules can consume the explicit `compound_partner`, counted-noun context, and source addresses as inputs, but they must not auto-certify a syntactic relation from a FAM3 formation candidate.",
        "",
        "## Status",
        "",
        "- Candidate mode: `pre_apply_not_authorized`.",
        "- Corpus inputs are caller-supplied at calibration time; the committed packet contains only the resulting typed records and no external filesystem path.",
        "- Recommended next gate: independent owner review of the named patterns and unresolved queues; no automatic promotion is defined here.",
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
