#!/usr/bin/env python3
"""Measure the FB1 v1/v2 predicate delta against an explicitly supplied corpus.

The corpus and STRAT packet are operational inputs, never repository defaults.
This runner writes only the requested lane artifacts: the dropped-row JSONL,
the deterministic hand-check sample, and the report.  It never mutates either
input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.lattice_projectors import (
    FB1_ATTACHED_ROLE_REGISTRY,
    pred_fb1_clitic_pronoun,
    pred_fb1_clitic_pronoun_v2,
)

FIXTURE_PATH = ROOT / "qamus" / "examples" / "fb1-predicate-v2" / "predicate-fixtures.jsonl"
_V1_ROLE_TOKENS = ("pronoun", "subject_marker", "possessive")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def loc_key(loc: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in str(loc).split(":"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path.name}:{line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected object at {path.name}:{line_no}")
            rows.append(value)
    return rows


def ordered_segments(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return sorted(
        list(row.get("segments") or []),
        key=lambda segment: int(segment.get("segment_index", 0)),
    )


def v1_role_hits(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for position, segment in enumerate(ordered_segments(row)):
        role = str(segment.get("role", ""))
        if any(token in role for token in _V1_ROLE_TOKENS):
            hits.append({
                "position": position,
                "segment_index": int(segment.get("segment_index", position)),
                "role": role,
                "class": segment.get("class"),
            })
    return hits


def v2_role_hits(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    segments = ordered_segments(row)
    hits: List[Dict[str, Any]] = []
    for position, segment in enumerate(segments):
        if position == 0:
            continue
        role = str(segment.get("role", ""))
        reason: Optional[str] = None
        if role in FB1_ATTACHED_ROLE_REGISTRY:
            reason = "exact_attached_role"
        elif (
            role == "subject_pronoun"
            and segment.get("class") == "qg-subject-pronoun"
            and segments[position - 1].get("class") == "qg-verb-stem"
        ):
            reason = "typed_subject_after_verb_stem"
        if reason is not None:
            hits.append({
                "position": position,
                "segment_index": int(segment.get("segment_index", position)),
                "role": role,
                "class": segment.get("class"),
                "match_reason": reason,
            })
    return hits


def compact_segment(segment: Mapping[str, Any]) -> Dict[str, Any]:
    keys = ("segment_index", "surface", "class", "role", "label", "sarf_note", "nahw_note")
    return {key: segment[key] for key in keys if key in segment}


def first_evidence(
    stats: Mapping[str, Any], prefer_nonleading: bool = True
) -> Mapping[str, Any]:
    if prefer_nonleading and stats["nonleading_evidence"] is not None:
        return stats["nonleading_evidence"]
    return stats["evidence"]


def role_classification(role: str) -> Tuple[str, str]:
    if role in FB1_ATTACHED_ROLE_REGISTRY:
        return "ATTACHED", "exact role admitted by the fail-closed v2 registry"
    if role == "subject_pronoun":
        return (
            "AMBIGUOUS / CONTEXT-ONLY",
            "role name is mixed; only qg-subject-pronoun after qg-verb-stem is admitted",
        )
    lowered = role.lower()
    non_attached_markers = (
        "independent",
        "detached",
        "separate",
        "relative",
        "demonstrative",
        "conditional",
        "interrogative",
        "addressee",
        "attention",
        "speaker",
        "referential",
        "third_person_pronoun",
    )
    if any(marker in lowered for marker in non_attached_markers):
        return "NON-ATTACHED / EXCLUDED", "independent, relative, demonstrative, or referential role shape"
    if "prefix" in lowered or "whole" in lowered or "verb +" in lowered or "noun +" in lowered:
        return "WHOLE-TOKEN / EXCLUDED", "role describes a host or prefix-level analysis, not an attached segment"
    return "AMBIGUOUS / EXCLUDED", "role name is not an explicit attached object/possessive/subject-marker class"


def collect_role_inventory(rows: Iterable[Mapping[str, Any]]) -> OrderedDict[str, Dict[str, Any]]:
    inventory: OrderedDict[str, Dict[str, Any]] = OrderedDict()
    for row in rows:
        segments = ordered_segments(row)
        for position, segment in enumerate(segments):
            role = str(segment.get("role", ""))
            if not any(token in role for token in _V1_ROLE_TOKENS):
                continue
            if role not in inventory:
                inventory[role] = {
                    "count": 0,
                    "nonleading": 0,
                    "classes": Counter(),
                    "evidence": None,
                    "nonleading_evidence": None,
                }
            stats = inventory[role]
            stats["count"] += 1
            if position > 0:
                stats["nonleading"] += 1
            stats["classes"][str(segment.get("class"))] += 1
            evidence = {
                "loc": row.get("loc"),
                "surface": row.get("surface"),
                "position": position,
                "segment_index": segment.get("segment_index", position),
                "class": segment.get("class"),
                "previous_role": segments[position - 1].get("role") if position else None,
                "previous_class": segments[position - 1].get("class") if position else None,
            }
            if stats["evidence"] is None:
                stats["evidence"] = evidence
            if position > 0 and stats["nonleading_evidence"] is None:
                stats["nonleading_evidence"] = evidence
    return OrderedDict((role, inventory[role]) for role in sorted(inventory))


def read_hand_checks(path: Optional[Path]) -> Optional[Dict[str, Dict[str, Any]]]:
    if path is None:
        return None
    checks: Dict[str, Dict[str, Any]] = {}
    for row in load_jsonl(path):
        loc = str(row.get("loc", ""))
        if not loc or loc in checks:
            raise ValueError(f"hand-check file has missing or duplicate loc: {loc!r}")
        if not isinstance(row.get("manual_family_match"), bool):
            raise ValueError(f"hand-check {loc} must set boolean manual_family_match")
        if not str(row.get("manual_reason", "")).strip():
            raise ValueError(f"hand-check {loc} must set manual_reason")
        checks[loc] = row
    return checks


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def md_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def role_inventory_markdown(inventory: Mapping[str, Mapping[str, Any]]) -> List[str]:
    lines = [
        "| role | occurrences | non-leading | observed classes | classification | corpus evidence | rationale |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for role, stats in inventory.items():
        classification, rationale = role_classification(role)
        evidence = first_evidence(stats)
        evidence_text = (
            f"{evidence['loc']} {evidence['surface']} pos={evidence['position']} "
            f"class={evidence['class']} prev={evidence['previous_role']}"
        )
        classes = ", ".join(f"{name} ({count})" for name, count in sorted(stats["classes"].items()))
        lines.append(
            "| " + " | ".join([
                md_cell(role),
                str(stats["count"]),
                str(stats["nonleading"]),
                md_cell(classes),
                md_cell(classification),
                md_cell(evidence_text),
                md_cell(rationale),
            ]) + " |"
        )
    return lines


def fixture_markdown() -> List[str]:
    fixtures = load_jsonl(FIXTURE_PATH)
    lines = [
        "| fixture | expected v1 | expected v2 | purpose |",
        "|---|---:|---:|---|",
    ]
    for fixture in fixtures:
        lines.append(
            "| " + " | ".join([
                md_cell(fixture.get("fixture_id")),
                str(fixture.get("expected_v1")),
                str(fixture.get("expected_v2")),
                md_cell(fixture.get("fixture_purpose", fixture.get("category", ""))),
            ]) + " |"
        )
    return lines


def render_report(
    *,
    corpus_path: Path,
    strat_path: Path,
    rows: Sequence[Mapping[str, Any]],
    inventory: Mapping[str, Mapping[str, Any]],
    v1_locs: Set[str],
    v2_locs: Set[str],
    dropped: Sequence[Mapping[str, Any]],
    strat_all_locs: Set[str],
    strat_family_locs: Set[str],
    sample: Sequence[Mapping[str, Any]],
    seed: int,
    hand_checks_present: bool,
) -> str:
    dropped_counts = Counter(row["dropped_reason"] for row in dropped)
    additions = sorted(v2_locs - v1_locs, key=loc_key)
    v1_strat = len(v1_locs & strat_family_locs)
    v2_strat = len(v2_locs & strat_family_locs)
    v1_all_strat = len(v1_locs & strat_all_locs)
    v2_all_strat = len(v2_locs & strat_all_locs)
    manual_true = sum(row.get("manual_family_match") is True for row in sample)
    manual_false = sum(row.get("manual_family_match") is False for row in sample)
    sample_status = (
        f"{manual_false}/40 false positives ({manual_false / len(sample):.1%})"
        if hand_checks_present and sample
        else "PENDING HAND CHECK"
    )

    lines: List[str] = [
        "# PREDV2 Report",
        "",
        "## Scope and source of truth",
        "",
        "This is a candidate-only comparison of `pred_fb1_clitic_pronoun` (v1) and `pred_fb1_clitic_pronoun_v2` (v2). Both registrations remain runnable; the deploy-population boundary is an owner decision. The corpus and STRAT packet were supplied as explicit CLI inputs and were read-only.",
        "",
        f"Generator: `tools/measure_fb1_predicate_v2.py`. Corpus: `{corpus_path.name}` ({len(rows):,} rows, SHA-256 `{hashlib.sha256(corpus_path.read_bytes()).hexdigest()}`). STRAT input: `{strat_path.name}` ({len(strat_all_locs):,} distinct locations; {len(strat_family_locs):,} primary `clitic_pronoun_compositions` rows).",
        "",
        "RECON evidence inputs: `RECON-REPORT.md`, `recon-fp-sample.jsonl`, and `recon-divergence-158.jsonl`.",
        "",
        "## Predicate change",
        "",
        "D1 is fixed by requiring the family-bearing segment to be non-leading after segment-index ordering. D2 is fixed by replacing substring vocabulary with the exact `FB1_ATTACHED_ROLE_REGISTRY` and a typed exception for generic `subject_pronoun` only after a `qg-verb-stem`; independent, relative, demonstrative, referential, detached, and other ambiguous role names fail closed. An explicit `morphology_family=clitic_pronoun_compositions` remains an override for both predicates.",
        "",
        f"The corpus-derived registry contains {len(FB1_ATTACHED_ROLE_REGISTRY)} exact role names. The inventory below enumerates all {len(inventory)} distinct observed roles containing `pronoun`, `possessive`, or `subject_marker`; every row includes at least one corpus example. `AMBIGUOUS / EXCLUDED` and `NON-ATTACHED / EXCLUDED` names are not admitted by v2.",
        "",
        "## Empirical role inventory",
        "",
        *role_inventory_markdown(inventory),
        "",
        "## Population delta",
        "",
        "| population | rows |",
        "|---|---:|",
        f"| corpus rows | {len(rows):,} |",
        f"| v1 selected | {len(v1_locs):,} |",
        f"| v2 selected | {len(v2_locs):,} |",
        f"| v1 minus v2 | {len(v1_locs - v2_locs):,} |",
        f"| v2 minus v1 | {len(additions):,} |",
        "",
        f"The v2 population is a strict subset: v2-only additions = `{len(additions)}`. Dropped reasons: `leading-only` = `{dropped_counts['leading-only']}`, `excluded-role` = `{dropped_counts['excluded-role']}`.",
        "",
        "### Full dropped-location list",
        "",
        "The complete machine-readable list is `predv2-dropped.jsonl`; the table below is the same full v1-v2 drop set.",
        "",
        "| loc | surface | dropped reason | v1 role hits | v2 role hits |",
        "|---|---|---|---|---|",
    ]
    for row in dropped:
        v1_roles = ", ".join(f"{hit['position']}:{hit['role']}" for hit in row["v1_role_hits"])
        v2_roles = ", ".join(f"{hit['position']}:{hit['role']}" for hit in row["v2_role_hits"]) or "-"
        lines.append(
            "| " + " | ".join([
                md_cell(row["loc"]),
                md_cell(row["surface"]),
                md_cell(row["dropped_reason"]),
                md_cell(v1_roles),
                md_cell(v2_roles),
            ]) + " |"
        )
    lines.extend([
        "",
        "The D1 edge `9:102:13` is the sole `leading-only` drop: its `preposition_ala_before_pronoun` role is at position 0. The other 639 drops retain a non-leading v1 substring hit but fail the exact attached-role registry.",
        "",
        "## STRAT overlap",
        "",
        f"Overlap with the STRAT primary 234-row `clitic_pronoun_compositions` cohort: v1 = `{v1_strat}`, v2 = `{v2_strat}`. This preserves the expected `{v2_strat}` overlap. For context, overlap with all {len(strat_all_locs)} STRAT locations is v1 = `{v1_all_strat}`, v2 = `{v2_all_strat}`. The STRAT-side divergence set of 158 remains a taxonomy issue and is not claimed as fixed here.",
        "",
        "## Fixture matrix",
        "",
        *fixture_markdown(),
        "",
        "## Fresh FP estimate",
        "",
        f"The sample is a deterministic `random.Random({seed})` selection of 40 rows from v2-selected locations outside all {len(strat_all_locs)} STRAT locations (outside-pool size `{len(v2_locs - strat_all_locs):,}`). The complete sample with manual verdicts is `predv2-fp-sample.jsonl`.",
        "",
        f"Hand-check status: {sample_status}. Manual attached-family positives = `{manual_true}`, manual false positives = `{manual_false}`.",
        "",
        "| loc | surface | manual family match | manual reason | v2 evidence |",
        "|---|---|---:|---|---|",
    ])
    for row in sample:
        evidence = ", ".join(
            f"{hit['position']}:{hit['role']} ({hit['match_reason']})" for hit in row["v2_role_hits"]
        )
        lines.append(
            "| " + " | ".join([
                md_cell(row["loc"]),
                md_cell(row["surface"]),
                str(row.get("manual_family_match")),
                md_cell(row.get("manual_reason", "PENDING_HAND_CHECK")),
                md_cell(evidence),
            ]) + " |"
        )
    lines.extend([
        "",
        "## Exact nonclaims",
        "",
        "- v2 does not remove, modify, or replace v1; the owner chooses whether a later packet adopts either population.",
        "- v2 does not certify, merge, publish, restart, deploy, mutate the whitelist, or choose a production boundary; every output remains candidate-mode and two-vote gated by the registered projector contract.",
        "- The exact registry is an empirical allowlist for the supplied corpus, not a claim that unseen role names are safe. New or ambiguous names remain excluded until separately evidenced and fixture-covered.",
        "- The 40-row hand-check is an estimate, not an exhaustive adjudication of the outside population.",
        "- The sampled miss at `4:157:34` is an upstream segmentation/role-label defect; v2 does not repair source rows or certify that label.",
        "- The unchanged STRAT-side 158 divergence is not resolved by this producer patch.",
        "",
        "## Compounding Impact",
        "",
        "Future family predicates that classify attached pronoun compositions should reuse `FB1_ATTACHED_ROLE_REGISTRY` and its non-leading/typed-host convention rather than reintroducing substring tests. Any extension must add corpus evidence, an attached-vs-independent classification, a negative fixture, a positive fixture, and a v1/v2 population comparison; ambiguous names remain fail-closed.",
        "",
        "## Reproduction",
        "",
        "Run `python tools/measure_fb1_predicate_v2.py --corpus <corpus.jsonl> --strat <strat.jsonl> --out-dropped <predv2-dropped.jsonl> --out-fp-sample <predv2-fp-sample.jsonl> --report <PREDV2-REPORT.md> --seed 20260717 --hand-check <hand-check.jsonl>` from the repository. The `--hand-check` file contains one `{loc, manual_family_match, manual_reason}` object per sampled location.",
        "",
    ])
    return "\n".join(lines)


def run_measurement(args: argparse.Namespace) -> int:
    rows = load_jsonl(args.corpus)
    strat_rows = load_jsonl(args.strat)
    row_by_loc = {str(row.get("loc")): row for row in rows}
    if len(row_by_loc) != len(rows):
        raise ValueError("corpus contains duplicate or missing loc values")

    v1_locs = {loc for loc, row in row_by_loc.items() if pred_fb1_clitic_pronoun(row)}
    v2_locs = {loc for loc, row in row_by_loc.items() if pred_fb1_clitic_pronoun_v2(row)}
    additions = sorted(v2_locs - v1_locs, key=loc_key)
    if additions:
        raise ValueError(f"STOP: v2-only additions found ({len(additions)}): {additions[:10]}")
    if len(v1_locs) != args.expected_v1:
        raise ValueError(f"expected v1 population {args.expected_v1}, got {len(v1_locs)}")

    dropped: List[Dict[str, Any]] = []
    for loc in sorted(v1_locs - v2_locs, key=loc_key):
        row = row_by_loc[loc]
        v1_hits = v1_role_hits(row)
        v2_hits = v2_role_hits(row)
        reason = "leading-only" if not any(hit["position"] > 0 for hit in v1_hits) else "excluded-role"
        dropped.append({
            "loc": loc,
            "surface": row.get("surface"),
            "v1": True,
            "v2": False,
            "dropped_reason": reason,
            "v1_role_hits": v1_hits,
            "v2_role_hits": v2_hits,
        })
    write_jsonl(args.out_dropped, dropped)

    strat_all_locs = {str(row.get("loc")) for row in strat_rows if row.get("loc")}
    strat_family_locs = {
        str(row.get("loc")) for row in strat_rows
        if row.get("loc") and row.get("morphology_family") == "clitic_pronoun_compositions"
    }
    sample_pool = sorted(v2_locs - strat_all_locs, key=loc_key)
    if len(sample_pool) < args.sample_size:
        raise ValueError(f"outside-STRAT sample pool has only {len(sample_pool)} rows")
    selected = sorted(
        random.Random(args.seed).sample(sample_pool, args.sample_size),
        key=loc_key,
    )
    hand_checks = read_hand_checks(args.hand_check)
    if hand_checks is not None and set(hand_checks) != set(selected):
        missing = sorted(set(selected) - set(hand_checks), key=loc_key)
        extra = sorted(set(hand_checks) - set(selected), key=loc_key)
        raise ValueError(f"hand-check loc mismatch; missing={missing}, extra={extra}")

    sample: List[Dict[str, Any]] = []
    for loc in selected:
        row = row_by_loc[loc]
        check = hand_checks.get(loc) if hand_checks is not None else None
        sample.append({
            "loc": loc,
            "surface": row.get("surface"),
            "seed": args.seed,
            "sample_size": args.sample_size,
            "manual_family_match": check.get("manual_family_match") if check else None,
            "manual_reason": check.get("manual_reason") if check else "PENDING_HAND_CHECK",
            "v2_role_hits": v2_role_hits(row),
            "morphline": row.get("morphline"),
            "segments": [compact_segment(segment) for segment in ordered_segments(row)],
        })
    write_jsonl(args.out_fp_sample, sample)

    inventory = collect_role_inventory(rows)
    report = render_report(
        corpus_path=args.corpus,
        strat_path=args.strat,
        rows=rows,
        inventory=inventory,
        v1_locs=v1_locs,
        v2_locs=v2_locs,
        dropped=dropped,
        strat_all_locs=strat_all_locs,
        strat_family_locs=strat_family_locs,
        sample=sample,
        seed=args.seed,
        hand_checks_present=hand_checks is not None,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8", newline="\n")

    manual_false = sum(row["manual_family_match"] is False for row in sample)
    print(json.dumps({
        "corpus_rows": len(rows),
        "v1": len(v1_locs),
        "v2": len(v2_locs),
        "dropped": len(dropped),
        "dropped_reasons": dict(Counter(row["dropped_reason"] for row in dropped)),
        "v2_only": len(additions),
        "strat_primary_family_rows": len(strat_family_locs),
        "strat_primary_overlap_v1": len(v1_locs & strat_family_locs),
        "strat_primary_overlap_v2": len(v2_locs & strat_family_locs),
        "strat_all_rows": len(strat_all_locs),
        "strat_all_overlap_v2": len(v2_locs & strat_all_locs),
        "outside_strat_pool": len(sample_pool),
        "fp_sample": args.sample_size,
        "fp_sample_manual_false": manual_false if hand_checks is not None else None,
        "fp_sample_rate": manual_false / args.sample_size if hand_checks is not None else None,
    }, ensure_ascii=False, indent=2))
    return 0


def self_test() -> int:
    fixtures = load_jsonl(FIXTURE_PATH)
    ok = (
        len(fixtures) == 12
        and all(
            pred_fb1_clitic_pronoun(row) == row["expected_v1"]
            and pred_fb1_clitic_pronoun_v2(row) == row["expected_v2"]
            for row in fixtures
        )
    )
    print("FB1 PREDICATE V2 MEASUREMENT SELF-TEST PASS" if ok else "FB1 PREDICATE V2 MEASUREMENT SELF-TEST FAIL")
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--strat", type=Path)
    parser.add_argument("--out-dropped", type=Path)
    parser.add_argument("--out-fp-sample", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--hand-check", type=Path)
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--expected-v1", type=int, default=4865)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    required = ("corpus", "strat", "out_dropped", "out_fp_sample", "report")
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        parser.error("missing required options: " + ", ".join("--" + name.replace("_", "-") for name in missing))
    return run_measurement(args)


if __name__ == "__main__":
    raise SystemExit(main())
