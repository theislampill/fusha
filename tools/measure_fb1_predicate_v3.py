#!/usr/bin/env python3
"""Measure the FB1 v1/v2/v3 predicate populations from explicit inputs.

The corpus, STRAT packet, and PREDV2 drop set are operational inputs supplied
through the CLI. This tool writes only requested candidate-mode artifacts and
never mutates any input.
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

from tools.lattice_projectors import (  # noqa: E402
    FB1_ATTACHED_ROLE_REGISTRY,
    FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY,
    FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY,
    FB1_GENERIC_GOVERNOR_HOST_REGISTRY,
    FB1_GENERIC_NON_ATTACHED_ROLE_MARKERS,
    pred_fb1_clitic_pronoun,
    pred_fb1_clitic_pronoun_v2,
    pred_fb1_clitic_pronoun_v3,
)

FIXTURE_V2_PATH = ROOT / "qamus" / "examples" / "fb1-predicate-v2" / "predicate-fixtures.jsonl"
FIXTURE_V3_PATH = ROOT / "qamus" / "examples" / "fb1-predicate-v3" / "predicate-fixtures.jsonl"
_V1_ROLE_TOKENS = ("pronoun", "subject_marker", "possessive")
_GENERIC_CLASSES = ("pronoun", "possessive", "subject_marker")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def loc_key(loc: str) -> Tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(loc).split(":"))
    except (TypeError, ValueError):
        return (10**9, 10**9, 10**9)


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


def compact_segment(segment: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "segment_index",
        "surface",
        "class",
        "role",
        "label",
        "gloss_contribution",
        "sarf_note",
        "nahw_note",
    )
    return {key: segment[key] for key in keys if key in segment}


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def is_named_non_attached_role(role: str) -> bool:
    lowered = role.lower()
    return any(marker in lowered for marker in FB1_GENERIC_NON_ATTACHED_ROLE_MARKERS)


def is_generic_role(role: str) -> bool:
    lowered = role.lower()
    return (
        any(token in lowered for token in _GENERIC_CLASSES)
        and not is_named_non_attached_role(role)
        and role not in FB1_ATTACHED_ROLE_REGISTRY
    )


def previous_shape(segments: Sequence[Mapping[str, Any]], position: int) -> Optional[Dict[str, Any]]:
    if position <= 0 or position > len(segments) - 1:
        return None
    previous = segments[position - 1]
    return {
        "role": previous.get("role"),
        "class": previous.get("class"),
        "surface": previous.get("surface"),
        "segment_index": previous.get("segment_index", position - 1),
    }


def shape_key(shape: Optional[Mapping[str, Any]]) -> Optional[Tuple[str, str]]:
    if shape is None:
        return None
    return (str(shape.get("role", "")), str(shape.get("class", "")))


def v3_role_hits(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    segments = ordered_segments(row)
    hits: List[Dict[str, Any]] = []
    for position, segment in enumerate(segments):
        if position == 0:
            continue
        role = str(segment.get("role", ""))
        reason: Optional[str] = None
        previous = previous_shape(segments, position)
        if role in FB1_ATTACHED_ROLE_REGISTRY:
            reason = "exact_attached_role"
        elif (
            role == "subject_pronoun"
            and segment.get("class") == "qg-subject-pronoun"
            and segments[position - 1].get("class") == "qg-verb-stem"
        ):
            reason = "typed_subject_after_verb_stem"
        elif is_generic_role(role) and shape_key(previous) in FB1_GENERIC_GOVERNOR_HOST_REGISTRY:
            reason = "generic_role_after_governor_host"
        if reason is not None:
            hit = {
                "position": position,
                "segment_index": int(segment.get("segment_index", position)),
                "role": role,
                "class": segment.get("class"),
                "match_reason": reason,
            }
            if reason == "generic_role_after_governor_host":
                hit["previous_role"] = previous.get("role")
                hit["previous_class"] = previous.get("class")
            hits.append(hit)
    return hits


def generic_events(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    segments = ordered_segments(row)
    events: List[Dict[str, Any]] = []
    for position, segment in enumerate(segments):
        role = str(segment.get("role", ""))
        if position == 0 or not is_generic_role(role):
            continue
        shape = previous_shape(segments, position)
        events.append({
            "position": position,
            "segment_index": int(segment.get("segment_index", position)),
            "role": role,
            "class": segment.get("class"),
            "previous": shape,
        })
    return events


def classify_shape(pair: Tuple[str, str]) -> Tuple[str, str]:
    memberships = [
        ("governor_host", pair in FB1_GENERIC_GOVERNOR_HOST_REGISTRY),
        ("conjunction_only", pair in FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY),
        ("ambiguous_prev", pair in FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY),
    ]
    active = [name for name, present in memberships if present]
    if len(active) > 1:
        raise ValueError(f"registry overlap for previous shape {pair!r}: {active}")
    if active:
        reasons = {
            "governor_host": "exact empirical governor/host pair admitted by v3",
            "conjunction_only": "pure conjunction/resumption/result-fā predecessor remains excluded",
            "ambiguous_prev": "residual predecessor shape is fail-closed and excluded",
        }
        return active[0], reasons[active[0]]
    return "ambiguous_prev", "unregistered predecessor shape is fail-closed and excluded"


def collect_predecessor_inventory(
    row_by_loc: Mapping[str, Mapping[str, Any]],
    v2_drop_locs: Iterable[str],
) -> OrderedDict[Tuple[str, str], Dict[str, Any]]:
    inventory: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for loc in sorted(v2_drop_locs, key=loc_key):
        row = row_by_loc[loc]
        for event in generic_events(row):
            pair = shape_key(event["previous"])
            if pair is None:
                continue
            stats = inventory.setdefault(pair, {
                "count": 0,
                "generic_roles": Counter(),
                "examples": [],
            })
            stats["count"] += 1
            stats["generic_roles"][event["role"]] += 1
            if len(stats["examples"]) < 3:
                stats["examples"].append({
                    "loc": loc,
                    "surface": row.get("surface"),
                    "generic_role": event["role"],
                    "generic_class": event["class"],
                    "previous_role": event["previous"].get("role"),
                    "previous_class": event["previous"].get("class"),
                    "previous_surface": event["previous"].get("surface"),
                })
    return OrderedDict((pair, inventory[pair]) for pair in sorted(inventory))


def evidence_for_hit(row: Mapping[str, Any], hit: Mapping[str, Any]) -> Dict[str, Any]:
    segments = ordered_segments(row)
    position = int(hit["position"])
    previous = previous_shape(segments, position)
    return {
        "position": position,
        "segment_index": hit.get("segment_index"),
        "role": hit.get("role"),
        "class": hit.get("class"),
        "previous": previous,
    }


def classify_remaining_drop(row: Mapping[str, Any]) -> Tuple[str, Dict[str, Any]]:
    hits = v1_role_hits(row)
    nonleading = [hit for hit in hits if hit["position"] > 0]
    if not nonleading:
        hit = hits[0] if hits else {"position": 0, "segment_index": 0, "role": "", "class": None}
        return "leading", evidence_for_hit(row, hit)

    named = [hit for hit in nonleading if is_named_non_attached_role(str(hit.get("role", "")))]
    if named:
        return "named_non_attached", evidence_for_hit(row, named[0])

    generic = [hit for hit in nonleading if is_generic_role(str(hit.get("role", "")))]
    classifications: List[Tuple[str, Dict[str, Any]]] = []
    for hit in generic:
        evidence = evidence_for_hit(row, hit)
        pair = shape_key(evidence["previous"])
        if pair is not None:
            classification, _ = classify_shape(pair)
            classifications.append((classification, evidence))
    conjunction = next((item for item in classifications if item[0] == "conjunction_only"), None)
    if conjunction is not None:
        return "conjunction_prev", conjunction[1]
    ambiguous = next((item for item in classifications if item[0] == "ambiguous_prev"), None)
    if ambiguous is not None:
        return "ambiguous_prev", ambiguous[1]
    hit = generic[0] if generic else nonleading[0]
    return "ambiguous_prev", evidence_for_hit(row, hit)


def read_hand_checks(
    path: Optional[Path],
    selected: Sequence[str],
    label: str,
) -> Dict[str, Dict[str, Any]]:
    if path is None:
        return {}
    checks: Dict[str, Dict[str, Any]] = {}
    for row in load_jsonl(path):
        loc = str(row.get("loc", ""))
        if not loc or loc in checks:
            raise ValueError(f"{label} hand-check has missing or duplicate loc: {loc!r}")
        if not isinstance(row.get("manual_family_match"), bool):
            raise ValueError(f"{label} hand-check {loc} must set boolean manual_family_match")
        if not str(row.get("manual_reason", "")).strip():
            raise ValueError(f"{label} hand-check {loc} must set manual_reason")
        checks[loc] = row
    expected = set(selected)
    if set(checks) != expected:
        missing = sorted(expected - set(checks), key=loc_key)
        extra = sorted(set(checks) - expected, key=loc_key)
        raise ValueError(f"{label} hand-check loc mismatch; missing={missing}, extra={extra}")
    return checks


def attach_hand_check(
    record: Dict[str, Any],
    check: Optional[Mapping[str, Any]],
    seed: int,
    sample_size: int,
) -> None:
    record["seed"] = seed
    record["sample_size"] = sample_size
    record["manual_family_match"] = check.get("manual_family_match") if check else None
    record["manual_reason"] = check.get("manual_reason", "PENDING_HAND_CHECK") if check else "PENDING_HAND_CHECK"


def annotate_readmitted_records(
    records: List[Dict[str, Any]],
    selected: Sequence[str],
    checks: Mapping[str, Mapping[str, Any]],
    *,
    seed: int,
    sample_size: int,
) -> List[Dict[str, Any]]:
    """Persist selected re-admission verdicts and return those same records."""
    selected_set = set(selected)
    sample: List[Dict[str, Any]] = []
    for record in records:
        loc = str(record["loc"])
        if loc in selected_set:
            attach_hand_check(record, checks.get(loc), seed, sample_size)
            record["hand_checked_re_admission"] = True
            sample.append(record)
        else:
            record["hand_checked_re_admission"] = False
    return sorted(sample, key=lambda row: loc_key(str(row["loc"])))


def fixture_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in (FIXTURE_V2_PATH, FIXTURE_V3_PATH):
        rows.extend(load_jsonl(path))
    return rows


def fixture_markdown() -> List[str]:
    lines = [
        "| fixture | expected v1 | expected v2 | actual v3 | purpose |",
        "|---|---:|---:|---:|---|",
    ]
    for fixture in fixture_rows():
        lines.append(
            "| " + " | ".join([
                str(fixture.get("fixture_id", "")).replace("|", "\\|"),
                str(fixture.get("expected_v1")),
                str(fixture.get("expected_v2")),
                str(pred_fb1_clitic_pronoun_v3(fixture)),
                str(fixture.get("category", "")).replace("|", "\\|"),
            ]) + " |"
        )
    return lines


def md_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def inventory_markdown(
    inventory: Mapping[Tuple[str, str], Mapping[str, Any]],
) -> List[str]:
    lines = [
        "| previous role | previous class | generic rows | generic roles | classification | evidence examples | rationale |",
        "|---|---|---:|---|---|---|---|",
    ]
    for (role, cls), stats in inventory.items():
        classification, rationale = classify_shape((role, cls))
        examples = "; ".join(
            f"{example['loc']} {example['surface']} ({example['generic_role']}; prev={example['previous_surface']})"
            for example in stats["examples"]
        )
        generic_roles = ", ".join(
            f"{name} ({count})" for name, count in sorted(stats["generic_roles"].items())
        )
        lines.append(
            "| " + " | ".join([
                md_cell(role),
                md_cell(cls),
                str(stats["count"]),
                md_cell(generic_roles),
                md_cell(classification),
                md_cell(examples),
                md_cell(rationale),
            ]) + " |"
        )
    return lines


def report_hand_table(
    rows: Sequence[Mapping[str, Any]],
    evidence_key: str,
) -> List[str]:
    lines = [
        "| loc | surface | manual family match | manual reason | evidence |",
        "|---|---|---:|---|---|",
    ]
    for row in rows:
        evidence = row.get(evidence_key) or row.get("v3_role_hits") or []
        evidence_text = ", ".join(
            f"{hit.get('position')}:{hit.get('role')} ({hit.get('match_reason')})"
            for hit in evidence
        )
        lines.append(
            "| " + " | ".join([
                md_cell(row.get("loc")),
                md_cell(row.get("surface")),
                str(row.get("manual_family_match")),
                md_cell(row.get("manual_reason")),
                md_cell(evidence_text),
            ]) + " |"
        )
    return lines


def render_report(
    *,
    corpus_path: Path,
    strat_path: Path,
    v2_report_path: Path,
    v2_dropped_path: Path,
    rows: Sequence[Mapping[str, Any]],
    strat_all_locs: Set[str],
    strat_family_locs: Set[str],
    v1_locs: Set[str],
    v2_locs: Set[str],
    v3_locs: Set[str],
    dropped: Sequence[Mapping[str, Any]],
    readmitted: Sequence[Mapping[str, Any]],
    inventory: Mapping[Tuple[str, str], Mapping[str, Any]],
    fp_sample: Sequence[Mapping[str, Any]],
    readmitted_sample: Sequence[Mapping[str, Any]],
    seed: int,
    sample_size: int,
    readmitted_sample_size: int,
    fp_checks_present: bool,
    readmitted_checks_present: bool,
) -> str:
    drop_counts = Counter(str(row["dropped_reason"]) for row in dropped)
    fp_false = sum(row.get("manual_family_match") is False for row in fp_sample)
    fp_true = sum(row.get("manual_family_match") is True for row in fp_sample)
    read_false = sum(row.get("manual_family_match") is False for row in readmitted_sample)
    read_true = sum(row.get("manual_family_match") is True for row in readmitted_sample)
    fp_status = (
        f"{fp_false}/{len(fp_sample)} false positives ({fp_false / len(fp_sample):.1%})"
        if fp_checks_present and fp_sample else "PENDING HAND CHECK"
    )
    read_status = (
        f"{read_true}/{len(readmitted_sample)} genuine attached compositions; failures={read_false}"
        if readmitted_checks_present and readmitted_sample else "PENDING HAND CHECK"
    )
    lines: List[str] = [
        "# PREDV3 Report",
        "",
        "## Scope and source of truth",
        "",
        "This is a candidate-only three-way comparison of `pred_fb1_clitic_pronoun` (v1), `pred_fb1_clitic_pronoun_v2` (v2), and `pred_fb1_clitic_pronoun_v3` (v3). All three owners remain runnable; the owner chooses any deploy boundary. The corpus, STRAT packet, and PREDV2 drop set were explicit read-only CLI inputs.",
        "",
        f"Generator: `tools/measure_fb1_predicate_v3.py`. Corpus: `{corpus_path.name}` ({len(rows):,} rows, SHA-256 `{sha256(corpus_path)}`). STRAT input: `{strat_path.name}` ({len(strat_all_locs):,} distinct locations; {len(strat_family_locs):,} primary `clitic_pronoun_compositions` rows; SHA-256 `{sha256(strat_path)}`). PREDV2 report input: `{v2_report_path.name}` (SHA-256 `{sha256(v2_report_path)}`). PREDV2 drop input: `{v2_dropped_path.name}` ({len(dropped) + len(v3_locs - v2_locs):,} source rows; SHA-256 `{sha256(v2_dropped_path)}`).",
        "",
        "## Predicate change",
        "",
        "V3 preserves the v2 explicit morphology-family override, exact attached-role registry, and typed subject-after-verb-stem admission. Its new fallback is non-leading only and admits a generic pronoun-family role only when the role is not in the explicit non-attached marker registry and its immediately previous exact `(role, class)` shape is in `FB1_GENERIC_GOVERNOR_HOST_REGISTRY`. Pure conjunction/resumption/result-fā and ambiguous predecessor shapes remain fail-closed.",
        "",
        f"The empirical v2 drop inventory contains {sum(stats['count'] for stats in inventory.values()):,} generic-role events across {len(inventory):,} distinct previous role+class shapes. The committed v3 registries classify {len(FB1_GENERIC_GOVERNOR_HOST_REGISTRY)} governor/host shapes, {len(FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY)} conjunction-only/result-fā shapes, and {len(FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY)} ambiguous shapes.",
        "",
        "## Governor / host registry evidence",
        "",
        *inventory_markdown(inventory),
        "",
        "The table enumerates every distinct previous role+class shape observed under a generic v1-v2 drop, with corpus evidence for each. The governor/host pairs are reusable by F-C dependency producers; the conjunction-only and ambiguous pair sets are explicit negative boundaries.",
        "",
        "Empirical boundary note: no distinct previous role+class shape named as a suffix or resumption predecessor occurred among the 440 generic drop events. V3 does not invent an unobserved allowlist entry; a future such shape remains fail-closed until separately evidenced and fixture-covered.",
        "",
        "## Three-way population comparison",
        "",
        "| population | rows |",
        "|---|---:|",
        f"| corpus rows | {len(rows):,} |",
        f"| v1 selected | {len(v1_locs):,} |",
        f"| v2 selected | {len(v2_locs):,} |",
        f"| v3 selected | {len(v3_locs):,} |",
        f"| v1 minus v2 | {len(v1_locs - v2_locs):,} |",
        f"| v2 minus v3 | {len(v2_locs - v3_locs):,} |",
        f"| v3 minus v2 | {len(v3_locs - v2_locs):,} |",
        f"| v1 minus v3 | {len(v1_locs - v3_locs):,} |",
        f"| v3 minus v1 | {len(v3_locs - v1_locs):,} |",
        "",
        f"Subset proof: `v2 - v3 = {len(v2_locs - v3_locs)}` and `v3 - v1 = {len(v3_locs - v1_locs)}`. V3 therefore retains every v2 row and selects no row outside v1.",
        "",
        "## Exact v1-v3 remaining-drop decomposition",
        "",
        "| reason | rows |",
        "|---|---:|",
        f"| named_non_attached | {drop_counts['named_non_attached']:,} |",
        f"| conjunction_prev | {drop_counts['conjunction_prev']:,} |",
        f"| ambiguous_prev | {drop_counts['ambiguous_prev']:,} |",
        f"| leading | {drop_counts['leading']:,} |",
        f"| total remaining drops | {len(dropped):,} |",
        "",
        "The complete machine-readable exact list is `predv3-dropped.jsonl`; each row records its decisive reason and predecessor evidence.",
        "",
        "| loc | surface | reason | decisive role | previous role+class |",
        "|---|---|---|---|---|",
    ]
    for row in dropped:
        evidence = row.get("reason_evidence", {})
        previous = evidence.get("previous") or {}
        lines.append(
            "| " + " | ".join([
                md_cell(row.get("loc")),
                md_cell(row.get("surface")),
                md_cell(row.get("dropped_reason")),
                md_cell(f"{evidence.get('position')}:{evidence.get('role')}"),
                md_cell(f"{previous.get('role', '-')} | {previous.get('class', '-')}"),
            ]) + " |"
        )
    lines.extend([
        "",
        "## Re-admitted v3-v2 rows",
        "",
        f"V3 re-admits `{len(readmitted):,}` rows from v2's excluded-role population. The exact list is `predv3-readmitted.jsonl`; all re-admissions are generic-role hits after an admitted governor/host pair, while v2's attached-role population is preserved unchanged.",
        "",
        "| v3 match reason | rows |",
        "|---|---:|",
        f"| generic_role_after_governor_host | {sum(1 for row in readmitted if any(hit.get('match_reason') == 'generic_role_after_governor_host' for hit in row.get('v3_role_hits', []))):,} |",
        "",
        "## STRAT overlap",
        "",
        "| owner | primary 234 family overlap | all 455 STRAT overlap |",
        "|---|---:|---:|",
        f"| v1 | {len(v1_locs & strat_family_locs):,} | {len(v1_locs & strat_all_locs):,} |",
        f"| v2 | {len(v2_locs & strat_family_locs):,} | {len(v2_locs & strat_all_locs):,} |",
        f"| v3 | {len(v3_locs & strat_family_locs):,} | {len(v3_locs & strat_all_locs):,} |",
        "",
        "The STRAT-side divergence set is not claimed as fixed by this predicate refinement.",
        "",
        "## Fixture matrix",
        "",
        *fixture_markdown(),
        "",
        "## Fresh v3 population hand-check",
        "",
        f"Using `random.Random({seed})`, this is a deterministic selection of `{sample_size}` rows from v3's population outside all `{len(strat_all_locs)}` STRAT locations (outside-pool size `{len(v3_locs - strat_all_locs):,}`). Artifact: `predv3-fp-sample.jsonl`.",
        "",
        f"Hand-check status: {fp_status}. Attached-family positives = `{fp_true}`, false positives = `{fp_false}`.",
        "",
        *report_hand_table(fp_sample, "v3_role_hits"),
        "",
        "## Newly re-admitted 12-row hand-check",
        "",
        f"Using `random.Random({seed})`, this is a deterministic selection of `{readmitted_sample_size}` rows from v3-v2 re-admissions (sorted by location after sampling). Requirement status: {read_status}. Artifact: `predv3-readmitted.jsonl` carries these verdicts on the selected rows.",
        "",
        *report_hand_table(readmitted_sample, "v3_role_hits"),
        "",
        "## EXACT NONCLAIMS",
        "",
        "- V3 does not remove, modify, replace, or silently re-register v1 or v2; all three owners remain available for comparison.",
        "- V3 does not certify, merge, publish, deploy, restart, mutate the whitelist, or choose a production/deploy boundary; every output is candidate-mode and remains gated by the registered two-vote contract.",
        "- The exact governor/host registry is an empirical allowlist for the supplied corpus and segment schema, not a claim that unseen role names or predecessor shapes are safe.",
        "- Explicit non-attached roles, pure conjunction/resumption/result-fā predecessors, and ambiguous residual shapes remain excluded by design.",
        "- The 40-row hand-check is a deterministic estimate, not exhaustive adjudication of the outside population; the 12-row re-admission check is a targeted sample, not proof of every re-admission.",
        "- The STRAT overlap comparison does not repair STRAT taxonomy or its divergence set.",
        "",
        "## Compounding Impact",
        "",
        "F-C dependency producers that need the same attached-pronoun family boundary can reuse `FB1_GENERIC_GOVERNOR_HOST_REGISTRY`, `FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY`, `FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY`, and `FB1_GENERIC_NON_ATTACHED_ROLE_MARKERS` rather than reintroducing broad substring predicates. A future extension must add corpus evidence for every new exact role+class shape, classify it as host/conjunction/ambiguous, add positive and negative fixtures, and rerun the three-way population and hand-check gates.",
        "",
        "## Reproduction",
        "",
        "Run `python tools/measure_fb1_predicate_v3.py --corpus <corpus.jsonl> --strat <strat-455.jsonl> --v2-report <PREDV2-REPORT.md> --v2-dropped <predv2-dropped.jsonl> --out-dropped <predv3-dropped.jsonl> --out-readmitted <predv3-readmitted.jsonl> --out-fp-sample <predv3-fp-sample.jsonl> --report <PREDV3-REPORT.md> --seed 20260718 --expected-v1 4865 --fp-hand-check <fp-hand-check.jsonl> --readmitted-hand-check <readmitted-hand-check.jsonl>` from the repository. The corpus and STRAT packet are operational CLI inputs only.",
        "",
    ])
    return "\n".join(lines)


def run_measurement(args: argparse.Namespace) -> int:
    rows = load_jsonl(args.corpus)
    if args.expected_corpus is not None and len(rows) != args.expected_corpus:
        raise ValueError(f"expected corpus population {args.expected_corpus}, got {len(rows)}")
    row_by_loc = {str(row.get("loc")): row for row in rows}
    if len(row_by_loc) != len(rows) or "None" in row_by_loc:
        raise ValueError("corpus contains duplicate or missing loc values")

    strat_rows = load_jsonl(args.strat)
    if not args.v2_report.read_text(encoding="utf-8").strip():
        raise ValueError("PREDV2 report input is empty")
    v2_dropped_rows = load_jsonl(args.v2_dropped)
    v1_locs = {loc for loc, row in row_by_loc.items() if pred_fb1_clitic_pronoun(row)}
    v2_locs = {loc for loc, row in row_by_loc.items() if pred_fb1_clitic_pronoun_v2(row)}
    v3_locs = {loc for loc, row in row_by_loc.items() if pred_fb1_clitic_pronoun_v3(row)}
    if len(v1_locs) != args.expected_v1:
        raise ValueError(f"expected v1 population {args.expected_v1}, got {len(v1_locs)}")
    if v2_locs - v1_locs:
        additions = sorted(v2_locs - v1_locs, key=loc_key)
        raise ValueError(f"STOP: v2-only additions found ({len(additions)}): {additions[:10]}")
    if v2_locs - v3_locs:
        missing = sorted(v2_locs - v3_locs, key=loc_key)
        raise ValueError(f"STOP: v2 rows lost by v3 ({len(missing)}): {missing[:10]}")
    if v3_locs - v1_locs:
        additions = sorted(v3_locs - v1_locs, key=loc_key)
        raise ValueError(f"STOP: v3-only additions found ({len(additions)}): {additions[:10]}")

    v2_drop_locs = {str(row.get("loc")) for row in v2_dropped_rows if row.get("loc")}
    expected_v2_drop_locs = v1_locs - v2_locs
    if v2_drop_locs != expected_v2_drop_locs:
        missing = sorted(expected_v2_drop_locs - v2_drop_locs, key=loc_key)
        extra = sorted(v2_drop_locs - expected_v2_drop_locs, key=loc_key)
        raise ValueError(f"PREDV2 drop set mismatch; missing={missing[:10]}, extra={extra[:10]}")

    dropped: List[Dict[str, Any]] = []
    for loc in sorted(v1_locs - v3_locs, key=loc_key):
        row = row_by_loc[loc]
        reason, evidence = classify_remaining_drop(row)
        dropped.append({
            "loc": loc,
            "surface": row.get("surface"),
            "v1": True,
            "v2": loc in v2_locs,
            "v3": False,
            "dropped_reason": reason,
            "reason_evidence": evidence,
            "v1_role_hits": v1_role_hits(row),
            "v2_role_hits": v2_role_hits(row),
            "v3_role_hits": v3_role_hits(row),
            "segments": [compact_segment(segment) for segment in ordered_segments(row)],
        })
    write_jsonl(args.out_dropped, dropped)

    readmitted: List[Dict[str, Any]] = []
    for loc in sorted(v3_locs - v2_locs, key=loc_key):
        row = row_by_loc[loc]
        hits = v3_role_hits(row)
        generic_hits = [hit for hit in hits if hit.get("match_reason") == "generic_role_after_governor_host"]
        if not generic_hits:
            raise ValueError(f"v3 re-admission at {loc} lacks a generic governor/host hit")
        hit = generic_hits[0]
        readmitted.append({
            "loc": loc,
            "surface": row.get("surface"),
            "v1": True,
            "v2": False,
            "v3": True,
            "v3_role_hits": hits,
            "generic_role": hit.get("role"),
            "previous_role": hit.get("previous_role"),
            "previous_class": hit.get("previous_class"),
            "morphline": row.get("morphline"),
            "segments": [compact_segment(segment) for segment in ordered_segments(row)],
        })

    strat_all_locs = {str(row.get("loc")) for row in strat_rows if row.get("loc")}
    strat_family_locs = {
        str(row.get("loc")) for row in strat_rows
        if row.get("loc") and row.get("morphology_family") == "clitic_pronoun_compositions"
    }
    fp_pool = sorted(v3_locs - strat_all_locs, key=loc_key)
    if len(fp_pool) < args.sample_size:
        raise ValueError(f"outside-STRAT v3 sample pool has only {len(fp_pool)} rows")
    fp_selected = sorted(
        random.Random(args.seed).sample(fp_pool, args.sample_size), key=loc_key
    )
    read_selected = sorted(
        random.Random(args.seed).sample(sorted(v3_locs - v2_locs, key=loc_key), args.readmitted_sample_size),
        key=loc_key,
    )
    fp_checks = read_hand_checks(args.fp_hand_check, fp_selected, "outside-STRAT")
    read_checks = read_hand_checks(args.readmitted_hand_check, read_selected, "re-admitted")

    fp_sample: List[Dict[str, Any]] = []
    for loc in fp_selected:
        row = row_by_loc[loc]
        record = {
            "loc": loc,
            "surface": row.get("surface"),
            "v1": True,
            "v2": loc in v2_locs,
            "v3": True,
            "v3_role_hits": v3_role_hits(row),
            "morphline": row.get("morphline"),
            "segments": [compact_segment(segment) for segment in ordered_segments(row)],
        }
        attach_hand_check(record, fp_checks.get(loc), args.seed, args.sample_size)
        fp_sample.append(record)

    readmitted_sample = annotate_readmitted_records(
        readmitted,
        read_selected,
        read_checks,
        seed=args.seed,
        sample_size=args.readmitted_sample_size,
    )
    write_jsonl(args.out_readmitted, readmitted)
    write_jsonl(args.out_fp_sample, fp_sample)

    inventory = collect_predecessor_inventory(row_by_loc, v2_drop_locs)
    observed_pairs = set(inventory)
    registry_pairs = (
        set(FB1_GENERIC_GOVERNOR_HOST_REGISTRY)
        | set(FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY)
        | set(FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY)
    )
    if observed_pairs != registry_pairs:
        missing = sorted(observed_pairs - registry_pairs)
        unused = sorted(registry_pairs - observed_pairs)
        raise ValueError(f"generic predecessor registry mismatch; missing={missing}, unused={unused}")

    report = render_report(
        corpus_path=args.corpus,
        strat_path=args.strat,
        v2_report_path=args.v2_report,
        v2_dropped_path=args.v2_dropped,
        rows=rows,
        strat_all_locs=strat_all_locs,
        strat_family_locs=strat_family_locs,
        v1_locs=v1_locs,
        v2_locs=v2_locs,
        v3_locs=v3_locs,
        dropped=dropped,
        readmitted=readmitted,
        inventory=inventory,
        fp_sample=fp_sample,
        readmitted_sample=readmitted_sample,
        seed=args.seed,
        sample_size=args.sample_size,
        readmitted_sample_size=args.readmitted_sample_size,
        fp_checks_present=args.fp_hand_check is not None,
        readmitted_checks_present=args.readmitted_hand_check is not None,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8", newline="\n")

    fp_false = sum(row.get("manual_family_match") is False for row in fp_sample)
    read_false = sum(row.get("manual_family_match") is False for row in readmitted_sample)
    print(json.dumps({
        "corpus_rows": len(rows),
        "v1": len(v1_locs),
        "v2": len(v2_locs),
        "v3": len(v3_locs),
        "v1_minus_v2": len(v1_locs - v2_locs),
        "v3_minus_v2": len(v3_locs - v2_locs),
        "v1_minus_v3": len(v1_locs - v3_locs),
        "v3_minus_v1": len(v3_locs - v1_locs),
        "remaining_drop_reasons": dict(Counter(row["dropped_reason"] for row in dropped)),
        "strat_primary_family_rows": len(strat_family_locs),
        "strat_primary_overlap_v1": len(v1_locs & strat_family_locs),
        "strat_primary_overlap_v2": len(v2_locs & strat_family_locs),
        "strat_primary_overlap_v3": len(v3_locs & strat_family_locs),
        "strat_all_rows": len(strat_all_locs),
        "strat_all_overlap_v1": len(v1_locs & strat_all_locs),
        "strat_all_overlap_v2": len(v2_locs & strat_all_locs),
        "strat_all_overlap_v3": len(v3_locs & strat_all_locs),
        "outside_strat_pool_v3": len(fp_pool),
        "fp_sample": len(fp_sample),
        "fp_sample_manual_false": fp_false if args.fp_hand_check is not None else None,
        "fp_sample_rate": fp_false / len(fp_sample) if args.fp_hand_check is not None else None,
        "readmitted_sample": len(readmitted_sample),
        "readmitted_sample_manual_false": read_false if args.readmitted_hand_check is not None else None,
        "readmitted_sample_all_true": read_false == 0 if args.readmitted_hand_check is not None else None,
    }, ensure_ascii=False, indent=2))
    return 0


def self_test() -> int:
    v2 = load_jsonl(FIXTURE_V2_PATH)
    v3 = load_jsonl(FIXTURE_V3_PATH)
    fixture_ok = (
        len(v2) == 12
        and len(v3) == 4
        and all(
            pred_fb1_clitic_pronoun(row) == row["expected_v1"]
            and pred_fb1_clitic_pronoun_v2(row) == row["expected_v2"]
            for row in v2
        )
        and all(
            pred_fb1_clitic_pronoun(row) == row["expected_v1"]
            and pred_fb1_clitic_pronoun_v2(row) == row["expected_v2"]
            and pred_fb1_clitic_pronoun_v3(row) == row["expected_v3"]
            for row in v3
        )
    )
    registry_ok = (
        len(FB1_GENERIC_GOVERNOR_HOST_REGISTRY) == 32
        and len(FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY) == 3
        and len(FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY) == 4
        and not (set(FB1_GENERIC_GOVERNOR_HOST_REGISTRY) & set(FB1_GENERIC_CONJUNCTION_ONLY_REGISTRY))
        and not (set(FB1_GENERIC_GOVERNOR_HOST_REGISTRY) & set(FB1_GENERIC_AMBIGUOUS_PREVIOUS_REGISTRY))
    )
    ok = fixture_ok and registry_ok
    print("FB1 PREDICATE V3 MEASUREMENT SELF-TEST PASS" if ok else "FB1 PREDICATE V3 MEASUREMENT SELF-TEST FAIL")
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--strat", type=Path)
    parser.add_argument("--v2-report", type=Path)
    parser.add_argument("--v2-dropped", type=Path)
    parser.add_argument("--out-dropped", type=Path)
    parser.add_argument("--out-readmitted", type=Path)
    parser.add_argument("--out-fp-sample", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fp-hand-check", type=Path)
    parser.add_argument("--readmitted-hand-check", type=Path)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--readmitted-sample-size", type=int, default=12)
    parser.add_argument("--expected-v1", type=int, default=4865)
    parser.add_argument("--expected-corpus", type=int, default=34323)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    required = (
        "corpus",
        "strat",
        "v2_report",
        "v2_dropped",
        "out_dropped",
        "out_readmitted",
        "out_fp_sample",
        "report",
    )
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        parser.error("missing required options: " + ", ".join("--" + name.replace("_", "-") for name in missing))
    try:
        return run_measurement(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
