#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the owner-rules VN readiness v2 matrix and selected-word ledger.

The builder is offline and candidate-only.  Every input is supplied through an
explicit CLI argument; the repo contains only the builder and a small fixture
subset, while the full corpus run can consume lane-owned read-only artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import os
import re
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.build_entry_card_word_ledger import build_ledger  # noqa: E402
from tools.build_typed_edge_crosswalk import selected_word_node  # noqa: E402


PRIMARY_LABELS = tuple(f"VN-{index:02d}" for index in range(21))
PLAN_EXTRA_LABELS = ("VN-21", "VN-22", "VN-23")
FROZEN_LABELS = ("VN-00", "VN-01", "VN-02")
SPECIAL_LABELS = ("VN-00-STAGING", "HISTORICAL_CONFLICT", "UNPLANNED_PARTICLES", "UNASSIGNED")
USABLE_CROSSWALK_STATUSES = frozenset({"deterministic_exact", "candidate"})
PROOF_NAMES = (
    "sufaha 2:13:12",
    "fattabini 19:43:10",
    "ma 2:284:10",
)
PROOF_NAME_SET = frozenset(PROOF_NAMES)

OWNER_SCHOLAR_FAMILY = "source/scholar required"
OWNER_POLICY_FAMILIES = frozenset({"divine-name policy", "proper noun"})
FUNCTION_WORD_FAMILY = "function word"
DUPLICATE_FAMILY = "duplicate-surface ambiguity"
SOURCE_REPAIR_FAMILIES = frozenset(
    {
        "deterministic entry/form match",
        "display-local crosswalk missing",
        "source card/photo missing",
        "sense edge missing",
    }
)

FROZEN_SCOPE_TEXT = {
    "VN-00": "v001–v047 + n0001–n0045",
    "VN-01": "v048–v094 + n0046–n0090",
    "VN-02": "v095–v141 + n0091–n0135",
}
FROZEN_SCOPE_CITATIONS = {
    "VN-00": "VNREC/VNREC-REPORT.md §Recovered authoritative scope; recorded CLOSED-FROZEN",
    "VN-01": "VNREC/VNREC-REPORT.md §Recovered authoritative scope; recorded CLOSED-FROZEN",
    "VN-02": "VNREC/VNREC-REPORT.md §Recovered authoritative scope; recorded CLOSED-FROZEN",
}

SOURCE_KEY_RE = re.compile(r"^(?P<prefix>[vnp])0*(?P<number>\d+)$", re.IGNORECASE)


@dataclass
class BuildResultV2:
    ledger: list[dict]
    matrix: dict
    report: str


def _clean(value):
    return "" if value is None else str(value).strip()


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            rows.append(value)
    return rows


def _write_json(value, path):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def _write_jsonl(rows, path):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _canonical_source_key(value):
    match = SOURCE_KEY_RE.fullmatch(_clean(value))
    if not match:
        return _clean(value)
    prefix = match.group("prefix").lower()
    number = int(match.group("number"))
    return f"{prefix}{number:04d}" if prefix == "n" else f"{prefix}{number:03d}"


def _source_key(entry):
    values = entry.get("source_keys") or []
    if not values:
        raise ValueError(f"entry {entry.get('id')!r} has no source_key")
    return _canonical_source_key(values[0])


def _range_keys(prefix, start, end, width=3):
    return {
        f"{prefix}{number:0{width}d}"
        for number in range(start, end + 1)
    }


def _partition_ranges():
    ranges = {
        "VN-00": _range_keys("v", 1, 47) | _range_keys("n", 1, 45, 4),
        "VN-01": _range_keys("v", 48, 94) | _range_keys("n", 46, 90, 4),
        "VN-02": _range_keys("v", 95, 195),
        "VN-10": _range_keys("v", 903, 947) | _range_keys("n", 91, 145, 4),
        "VN-20": _range_keys("p", 1, 100),
    }
    for label in range(3, 10):
        verb_start = 196 + (label - 3) * 101
        ranges[f"VN-{label:02d}"] = _range_keys("v", verb_start, verb_start + 100)
    for label in range(11, 20):
        noun_start = 146 + (label - 11) * 100
        ranges[f"VN-{label:02d}"] = _range_keys("n", noun_start, noun_start + 99, 4)
    return ranges


def _plan_ranges():
    ranges = {
        "VN-00": _range_keys("v", 1, 47) | _range_keys("n", 1, 45, 4),
        "VN-01": _range_keys("v", 48, 94) | _range_keys("n", 46, 90, 4),
        "VN-02": _range_keys("v", 95, 141) | _range_keys("n", 91, 135, 4),
        "VN-20": _range_keys("v", 941, 947) | _range_keys("n", 901, 945, 4),
        "VN-21": _range_keys("n", 946, 990, 4),
        "VN-22": _range_keys("n", 991, 1035, 4),
        "VN-23": _range_keys("n", 1036, 1045, 4),
    }
    for label in range(3, 20):
        verb_start = 142 + (label - 3) * 47
        noun_start = 136 + (label - 3) * 45
        ranges[f"VN-{label:02d}"] = _range_keys("v", verb_start, verb_start + 46) | _range_keys(
            "n", noun_start, noun_start + 44, 4
        )
    return ranges


PARTITION_RANGES = _partition_ranges()
PLAN_RANGES = _plan_ranges()


def _label_for_key(source_key, ranges):
    source_key = _canonical_source_key(source_key)
    for label in sorted(ranges):
        if source_key in ranges[label]:
            return label
    return None


def _proposal_string(proposal_id, label):
    return f"proposed:{proposal_id}:{label}" if label else None


def _evidence_string(item):
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return ""
    artifact = _clean(item.get("artifact"))
    locator = _clean(item.get("locator"))
    claim = _clean(item.get("claim"))
    if artifact and locator:
        return f"{artifact}:{locator}"
    if artifact:
        return artifact
    if locator:
        return locator
    return claim


def _append_evidence(target, values):
    for value in values or []:
        rendered = _evidence_string(value)
        if rendered and rendered not in target:
            target.append(rendered)


def _membership_claims(membership, conflicts):
    claims = defaultdict(set)
    evidence = defaultdict(list)
    doc_sets = {label: set() for label in FROZEN_LABELS}
    staging = set()

    for label, details in (membership.get("vn") or {}).items():
        for record in details.get("authoritative_sets") or []:
            keys = {_canonical_source_key(value) for value in record.get("source_keys") or []}
            kind = record.get("kind")
            if kind == "documented_window_contract" and label in FROZEN_LABELS:
                doc_sets[label].update(keys)
                for key in keys:
                    claims[key].add(label)
                    _append_evidence(evidence[key], record.get("evidence"))
            elif kind == "deployed_rollout_staging_cumulative_snapshot":
                staging.update(keys)
                for key in keys:
                    claims[key].add("VN-00")
                    _append_evidence(evidence[key], record.get("evidence"))

    for record in conflicts:
        if record.get("record_type") != "source_key_conflict":
            continue
        key = _canonical_source_key(record.get("source_key"))
        labels = {_clean(value) for value in record.get("historical_authoritative_labels") or []}
        if labels:
            claims[key] = labels
        _append_evidence(evidence[key], record.get("evidence"))
        evidence[key].append(f"VNREC/vnrec-conflicts.jsonl:source_key={key}")

    for key in list(evidence):
        evidence[key] = sorted(set(value for value in evidence[key] if value))
    return claims, evidence, doc_sets, staging


def _assignment_for_key(source_key, claims, evidence, doc_sets, staging):
    source_key = _canonical_source_key(source_key)
    historical_claims = sorted(claims.get(source_key, set()))
    partition_label = _label_for_key(source_key, PARTITION_RANGES)
    plan_label = _label_for_key(source_key, PLAN_RANGES)
    row_evidence = list(evidence.get(source_key, []))

    if len(historical_claims) > 1:
        scalar = None
        status = "historical_conflict"
        partition_proposal = None
        plan_proposal = None
    elif len(historical_claims) == 1:
        scalar = historical_claims[0]
        status = "authoritative"
        partition_proposal = None
        plan_proposal = None
    elif partition_label:
        scalar = _proposal_string("vn-partition-proposal.v1", partition_label)
        status = "proposed"
        partition_proposal = scalar
        plan_proposal = _proposal_string("vn-plan-table.v1", plan_label)
        if not row_evidence:
            row_evidence.append(f"VNREC/vnrec-authoritative-membership.json:source_key={source_key}:no_historical_claim")
    else:
        scalar = None
        status = "unassigned"
        partition_proposal = None
        plan_proposal = None

    if source_key in doc_sets["VN-00"]:
        authority_surface = "documented_window"
    elif source_key in doc_sets["VN-01"]:
        authority_surface = "documented_window"
    elif source_key in doc_sets["VN-02"]:
        authority_surface = "documented_window"
    elif source_key in staging:
        authority_surface = "deployed_staging"
    elif len(historical_claims) > 1:
        authority_surface = "historical_multi_claim"
    else:
        authority_surface = "none"

    if not historical_claims and plan_label:
        row_evidence.append(f"VNREC/VNREC-REPORT.md:future-plan-table:{plan_label}")
    if not historical_claims and partition_label:
        row_evidence.append(f"VNREC/vnrec-conflicts.jsonl:source_key={source_key}:proposal-only")
    row_evidence = sorted(set(row_evidence))

    def matrix_view(kind):
        if source_key in doc_sets["VN-00"]:
            return "VN-00"
        if source_key in doc_sets["VN-01"]:
            return "VN-01"
        if source_key in doc_sets["VN-02"]:
            return "VN-02"
        if source_key in staging:
            return "VN-00-STAGING"
        if kind == "authoritative_partition":
            return partition_label or "UNASSIGNED"
        if plan_label:
            return plan_label
        if source_key.startswith("p"):
            return "UNPLANNED_PARTICLES"
        return "UNASSIGNED"

    return {
        "vn_tranche": scalar,
        "vn_tranche_status": status,
        "vn_tranche_claims": historical_claims,
        "vn_tranche_evidence": row_evidence,
        "evidence": row_evidence,
        "vn00_staging_member": source_key in staging,
        "vn00_documented_window_member": source_key in doc_sets["VN-00"],
        "vn_authority_surface": authority_surface,
        "vn_tranche_partition_proposal": partition_proposal,
        "vn_tranche_plan_table_proposal": plan_proposal,
        "vn_matrix_view_authoritative_partition": matrix_view("authoritative_partition"),
        "vn_matrix_view_plan_table": matrix_view("plan_table"),
        "partition_label": partition_label,
        "plan_table_label": plan_label,
    }


def _selected_word_id(row):
    address = row.get("display_local_address") or {}
    try:
        example_index = int(
            address.get("entry_example_index")
            or address.get("whitelist_example_card_index")
            or address.get("example_index")
            or 1
        )
    except (TypeError, ValueError):
        example_index = 1
    return selected_word_node(
        _clean(row.get("entry_id")),
        int(row.get("sense_index") or 1),
        int(row.get("usage_index") or 1),
        int(row.get("form_index") or 1),
        _clean(row.get("source_card_ref")),
        max(1, example_index),
        _clean(row.get("occurrence_id")),
    )


def _card_key(entry_id, usage_index, example_index):
    return f"{entry_id}|{int(usage_index)}|{int(example_index)}"


def _make_cards(entries):
    cards = []
    for entry in entries:
        entry_id = _clean(entry.get("id"))
        for usage_index, usage in enumerate(entry.get("usage") or [], 1):
            for example_index, _example in enumerate((usage.get("examples") or []) if isinstance(usage, dict) else [], 1):
                cards.append(
                    {
                        "card_key": _card_key(entry_id, usage_index, example_index),
                        "entry_id": entry_id,
                        "usage_index": usage_index,
                        "example_index": example_index,
                    }
                )
    return cards


def _counter_dict(counter):
    return dict(sorted(counter.items()))


def _proofs_by_view(proof_rows, entry_by_id, assignment_by_key, view_kind):
    result = defaultdict(list)
    for proof in proof_rows:
        name = _clean(proof.get("name"))
        entry_id = _clean(proof.get("entry_id"))
        if name not in PROOF_NAME_SET:
            raise ValueError(f"unexpected proof name: {name!r}")
        if entry_id not in entry_by_id:
            raise ValueError(f"proof {name!r} entry_id is absent from entries: {entry_id!r}")
        key = entry_by_id[entry_id]
        result[assignment_by_key[key][f"vn_matrix_view_{view_kind}"]].append(name)
    return result


def _family_view_counts(family_rows, entry_by_id, whitelist_by_loc, assignment_by_key, view_kind):
    counts = Counter()
    for family in family_rows:
        entry_id = _clean(family.get("entry_id"))
        if entry_id not in entry_by_id:
            entry_id = _clean(whitelist_by_loc.get(_clean(family.get("loc")), ""))
        if entry_id not in entry_by_id:
            continue
        key = entry_by_id[entry_id]
        label = assignment_by_key[key][f"vn_matrix_view_{view_kind}"]
        counts[label] += 1
    return counts


def _debt_bucket_counts(debt_counter):
    return {
        "owner_scholar_rows": debt_counter.get(OWNER_SCHOLAR_FAMILY, 0),
        "owner_policy_rows": sum(debt_counter.get(value, 0) for value in OWNER_POLICY_FAMILIES),
        "function_word_rows": debt_counter.get(FUNCTION_WORD_FAMILY, 0),
        "duplicate_surface_rows": debt_counter.get(DUPLICATE_FAMILY, 0),
        "source_crosswalk_repair_rows": sum(debt_counter.get(value, 0) for value in SOURCE_REPAIR_FAMILIES),
    }


def _next_action(label, stats):
    debt = stats["debt_rows"]
    owner = stats["owner_scholar_rows"]
    repair = stats["source_crosswalk_repair_rows"]
    if label in FROZEN_LABELS:
        if stats["historical_conflict_entries"]:
            return (
                f"Preserve the recorded CLOSED-FROZEN {label} scope; owner-ratify "
                f"{stats['historical_conflict_entries']} historical conflict entries while keeping scalar null; "
                "do not re-verify live."
            )
        return f"No live action: preserve recorded CLOSED-FROZEN {label}; route only candidate source/crosswalk repairs."
    if label == "VN-00-STAGING":
        return "Keep the 1,302-key staging namespace separate; owner-ratify its relationship to documented windows before any planning or live action."
    if label == "HISTORICAL_CONFLICT":
        return "Preserve every historical claim and keep vn_tranche null until the owner ratifies the conflicting surfaces."
    if label == "UNPLANNED_PARTICLES":
        return "Define and owner-ratify a particle plan; p-pages remain outside the documented future table and candidate-only."
    if label == "UNASSIGNED":
        return "Provide a source-owned assignment or stop; no provisional label is available."
    if label in PLAN_EXTRA_LABELS:
        plan_action = f"Owner-ratify the future plan row {label}; do not convert it into historical closure."
    else:
        plan_action = f"Owner-ratify the selected planning namespace for {label}; keep both proposals visible."
    if owner and repair:
        return f"{plan_action} Route {owner} source/scholar rows, then apply {repair} source/crosswalk repairs in candidate mode."
    if owner:
        return f"{plan_action} Route {owner} source/scholar rows for owner evidence; remain candidate-only."
    if repair:
        return f"{plan_action} Apply {repair} source/crosswalk repairs after evidence review; remain candidate-only."
    if debt:
        return f"{plan_action} Resolve the remaining {debt} classified debt rows before promotion."
    return f"{plan_action} Start with the graph-complete rows and retain the candidate boundary."


def _stats_for_label(
    label,
    view_kind,
    entries,
    cards,
    ledger,
    assignment_by_key,
    entry_by_id,
    debt_by_id,
    proof_by_view,
    family_counts,
    doc_sets,
    claims,
):
    entry_ids = {
        entry["id"]
        for entry in entries
        if assignment_by_key[entry_by_id[entry["id"]]][f"vn_matrix_view_{view_kind}"] == label
    }
    card_rows = [card for card in cards if card["entry_id"] in entry_ids]
    rows = [
        row
        for row in ledger
        if row[f"vn_matrix_view_{view_kind}"] == label
    ]
    occurrences = {row.get("occurrence_id") for row in rows if row.get("occurrence_id")}
    status_counts = Counter(row.get("crosswalk_status") or "unavailable" for row in rows)
    usable_det = sum(row.get("crosswalk_status") == "deterministic_exact" for row in rows)
    usable_candidate = sum(row.get("crosswalk_status") == "candidate" for row in rows)
    debt_counter = Counter(row["debt_repair_family"] for row in rows if row.get("debt_repair_family"))
    debt_buckets = _debt_bucket_counts(debt_counter)

    historical_conflict_entries = 0
    historical_conflict_rows = 0
    already_live_entries = 0
    already_live_cards = 0
    already_live_rows = 0
    assigned_entries = 0
    if label in FROZEN_LABELS:
        scope_keys = doc_sets[label]
        scope_entry_ids = {
            entry_id for entry_id, key in entry_by_id.items() if key in scope_keys
        }
        scope_cards = [card for card in cards if card["entry_id"] in scope_entry_ids]
        scope_rows = [row for row in ledger if row.get("source_key") in scope_keys]
        historical_conflict_entries = sum(len(claims.get(key, set())) > 1 for key in scope_keys)
        historical_conflict_rows = sum(len(claims.get(row.get("source_key"), set())) > 1 for row in scope_rows)
        already_live_entries = len(scope_entry_ids)
        already_live_cards = len(scope_cards)
        already_live_rows = len(scope_rows)
        assigned_entries = sum(len(claims.get(key, set())) == 1 for key in scope_keys)

    stats = {
        "label": label,
        "view": view_kind,
        "entries": len(entry_ids),
        "cards": len(card_rows),
        "displayed_selected_words": len(rows),
        "unique_canonical_occurrences": len(occurrences),
        "crosswalk_status_counts": _counter_dict(status_counts),
        "graph_complete_rows": usable_det + usable_candidate,
        "graph_complete_deterministic_exact_rows": usable_det,
        "graph_complete_candidate_rows": usable_candidate,
        "source_certified_rows": 0,
        "source_certification_state": "0; candidate-only lane has no source certification",
        "fully_rich_generated_rows": len(proof_by_view.get(label, [])),
        "fully_rich_generated_proof_names": sorted(proof_by_view.get(label, [])),
        "already_live_noop_entries": already_live_entries,
        "already_live_noop_cards": already_live_cards,
        "already_live_noop_selected_word_rows": already_live_rows,
        "already_live_noop_state": "recorded CLOSED-FROZEN scope; not live-reverified" if label in FROZEN_LABELS else "not applicable",
        "historical_conflict_entries": historical_conflict_entries,
        "historical_conflict_selected_word_rows": historical_conflict_rows,
        "authoritative_assigned_entries": assigned_entries,
        "debt_rows": sum(debt_counter.values()),
        "debt_family_counts": _counter_dict(debt_counter),
        **debt_buckets,
        "calibrated_family_candidate_rows": family_counts.get(label, 0),
        "candidate_only": True,
    }
    if label in FROZEN_LABELS:
        stats["scope_source_key_range"] = FROZEN_SCOPE_TEXT[label]
        stats["scope_status"] = "CLOSED-FROZEN (recorded evidence)"
        stats["scope_evidence"] = [FROZEN_SCOPE_CITATIONS[label]]
    elif label == "VN-00-STAGING":
        stats["scope_source_key_range"] = "1,302 sparse cumulative staging source keys"
        stats["scope_status"] = "separate preserved staging namespace"
        stats["scope_evidence"] = ["VNREC/vnrec-authoritative-membership.json:staging_metadata.final_source_key_count=1302"]
    elif label == "HISTORICAL_CONFLICT":
        stats["scope_status"] = "scalar null; claims preserved"
        stats["scope_evidence"] = ["VNREC/vnrec-conflicts.jsonl:164 historical-conflict source keys"]
    elif label == "UNPLANNED_PARTICLES":
        stats["scope_status"] = "outside future plan"
        stats["scope_evidence"] = ["VNREC/VNREC-REPORT.md:future plan leaves p001–p100 unplanned"]
    else:
        range_keys = (PLAN_RANGES if view_kind == "plan_table" else PARTITION_RANGES).get(label, set())
        stats["scope_source_key_count"] = len(range_keys)
        stats["scope_status"] = "planning-only; no historical closure assignment"
        stats["scope_evidence"] = [
            "VNREC/VNREC-REPORT.md:future-plan table",
            "VNREC/vnrec-authoritative-membership.json:proposal-only boundary",
        ]
    stats["next_action"] = _next_action(label, stats)
    return stats


def _special_stats(label, view_kind, entries, cards, ledger, entry_by_id, proof_by_view, claims):
    if label == "HISTORICAL_CONFLICT":
        rows = [row for row in ledger if row.get("vn_tranche_status") == "historical_conflict"]
        entry_ids = {row["entry_id"] for row in rows}
        card_keys = {_card_key(row["entry_id"], row["usage_index"], (row.get("display_local_address") or {}).get("entry_example_index") or 1) for row in rows}
    else:
        rows = [row for row in ledger if row[f"vn_matrix_view_{view_kind}"] == label]
        entry_ids = {row["entry_id"] for row in rows}
        card_keys = {_card_key(row["entry_id"], row["usage_index"], (row.get("display_local_address") or {}).get("entry_example_index") or 1) for row in rows}
    status_counts = Counter(row.get("crosswalk_status") or "unavailable" for row in rows)
    debt_counter = Counter(row["debt_repair_family"] for row in rows if row.get("debt_repair_family"))
    result = {
        "label": label,
        "view": view_kind,
        "entries": len(entry_ids),
        "cards": len(card_keys),
        "displayed_selected_words": len(rows),
        "unique_canonical_occurrences": len({row.get("occurrence_id") for row in rows if row.get("occurrence_id")}),
        "crosswalk_status_counts": _counter_dict(status_counts),
        "graph_complete_rows": sum(row.get("crosswalk_status") in USABLE_CROSSWALK_STATUSES for row in rows),
        "graph_complete_deterministic_exact_rows": sum(row.get("crosswalk_status") == "deterministic_exact" for row in rows),
        "graph_complete_candidate_rows": sum(row.get("crosswalk_status") == "candidate" for row in rows),
        "source_certified_rows": 0,
        "fully_rich_generated_rows": len(proof_by_view.get(label, [])),
        "fully_rich_generated_proof_names": sorted(proof_by_view.get(label, [])),
        "already_live_noop_entries": 0,
        "already_live_noop_cards": 0,
        "already_live_noop_selected_word_rows": 0,
        "historical_conflict_entries": len(entry_ids) if label == "HISTORICAL_CONFLICT" else 0,
        "historical_conflict_selected_word_rows": len(rows) if label == "HISTORICAL_CONFLICT" else 0,
        "authoritative_assigned_entries": 0,
        "debt_rows": sum(debt_counter.values()),
        "debt_family_counts": _counter_dict(debt_counter),
        **_debt_bucket_counts(debt_counter),
        "candidate_only": True,
        "scope_status": "scalar null; claims preserved" if label == "HISTORICAL_CONFLICT" else "separate namespace",
    }
    result["next_action"] = _next_action(label, result)
    return result


def _matrix_totals(tranches, special_rows):
    included = list(tranches)
    for label, row in special_rows.items():
        if label in {"VN-00-STAGING", "UNPLANNED_PARTICLES"}:
            included.append(row)
    return {
        "entries": sum(row["entries"] for row in included),
        "cards": sum(row["cards"] for row in included),
        "displayed_selected_words": sum(row["displayed_selected_words"] for row in included),
        "unique_canonical_occurrences": sum(row["unique_canonical_occurrences"] for row in included),
    }


def _card_completeness(ledger, cards, partition_label_for_entry, field):
    rows_by_card = defaultdict(list)
    for row in ledger:
        key = _card_key(
            row["entry_id"],
            row["usage_index"],
            (row.get("display_local_address") or {}).get("entry_example_index") or 1,
        )
        rows_by_card[key].append(row)
    grouped = Counter()
    for card in cards:
        if partition_label_for_entry.get(card["entry_id"]) is None:
            continue
        rows = rows_by_card.get(card["card_key"], [])
        if rows and all(bool(row.get(field)) for row in rows):
            grouped[partition_label_for_entry[card["entry_id"]]] += 1
    return grouped


def _material_delta(ledger, cards, baseline_matrix, entry_by_id):
    baseline_rows = {}
    for row in baseline_matrix.get("tranches") or []:
        label = _clean(row.get("proposal_vn_tranche"))
        if label:
            baseline_rows[label] = {
                "selected": int(row.get("displayed_selected_words") or 0),
                "complete": int(row.get("displayed_selected_words") or 0) - int(row.get("graph_crosswalk_gap_rows") or 0),
            }
    partition_by_entry = {entry_id: _label_for_key(key, PARTITION_RANGES) for entry_id, key in entry_by_id.items()}
    before_cards = _card_completeness(ledger, cards, partition_by_entry, "crosswalk_flag")
    after_cards = Counter()
    rows_by_entry = defaultdict(list)
    after_by_label = defaultdict(Counter)
    before_by_label = defaultdict(Counter)
    for row in ledger:
        label = partition_by_entry.get(row["entry_id"])
        if not label:
            continue
        status = row.get("crosswalk_status")
        if status == "deterministic_exact":
            after_by_label[label]["deterministic_exact"] += 1
        elif status == "candidate":
            after_by_label[label]["candidate"] += 1
        if row.get("crosswalk_flag"):
            before_by_label[label]["usable"] += 1
        if status in USABLE_CROSSWALK_STATUSES:
            rows_by_entry[row["entry_id"]].append(row)
    for card in cards:
        label = partition_by_entry.get(card["entry_id"])
        if not label:
            continue
        card_rows = [
            row
            for row in ledger
            if _card_key(
                row["entry_id"],
                row["usage_index"],
                (row.get("display_local_address") or {}).get("entry_example_index") or 1,
            )
            == card["card_key"]
        ]
        if card_rows and all(row.get("crosswalk_status") in USABLE_CROSSWALK_STATUSES for row in card_rows):
            after_cards[label] += 1
    before_entries = Counter()
    after_entries = Counter()
    for row in ledger:
        label = partition_by_entry.get(row["entry_id"])
        if not label:
            continue
        if row.get("crosswalk_flag"):
            before_entries[label] += 1
    before_entries = Counter({label: len({row["entry_id"] for row in ledger if partition_by_entry.get(row["entry_id"]) == label and row.get("crosswalk_flag")}) for label in PRIMARY_LABELS})
    after_entries = Counter({label: len({entry_id for entry_id, rows in rows_by_entry.items() if partition_by_entry.get(entry_id) == label and rows}) for label in PRIMARY_LABELS})

    rows = []
    for label in PRIMARY_LABELS:
        before = baseline_rows.get(label, {"selected": 0, "complete": 0})
        after_det = after_by_label[label].get("deterministic_exact", 0)
        after_candidate = after_by_label[label].get("candidate", 0)
        after_usable = after_det + after_candidate
        rows.append(
            {
                "label": label,
                "baseline_selected_word_rows": before["selected"],
                "baseline_usable_selected_word_rows": before["complete"],
                "after_deterministic_exact_rows": after_det,
                "after_candidate_rows": after_candidate,
                "after_usable_selected_word_rows": after_usable,
                "delta_usable_selected_word_rows": after_usable - before["complete"],
                "baseline_cards_completable": before_cards.get(label, 0),
                "after_cards_completable": after_cards.get(label, 0),
                "delta_cards_completable": after_cards.get(label, 0) - before_cards.get(label, 0),
                "baseline_entries_with_usable_edge": before_entries.get(label, 0),
                "after_entries_with_usable_edge": after_entries.get(label, 0),
                "delta_entries_with_usable_edge": after_entries.get(label, 0) - before_entries.get(label, 0),
            }
        )
    return {
        "basis": "stable VN-00..VN-20 partition identity; historical scope remapping is not mixed into this delta",
        "before_source": "pre-crosswalk vn-readiness-matrix.json",
        "after_source": "EDGES/full-artifacts/lexeme-entry-crosswalk.forward.jsonl",
        "rows": rows,
        "totals": {
            "baseline_usable_selected_word_rows": sum(row["baseline_usable_selected_word_rows"] for row in rows),
            "after_usable_selected_word_rows": sum(row["after_usable_selected_word_rows"] for row in rows),
            "delta_usable_selected_word_rows": sum(row["delta_usable_selected_word_rows"] for row in rows),
            "baseline_cards_completable": sum(row["baseline_cards_completable"] for row in rows),
            "after_cards_completable": sum(row["after_cards_completable"] for row in rows),
            "delta_cards_completable": sum(row["delta_cards_completable"] for row in rows),
            "baseline_entries_with_usable_edge": sum(row["baseline_entries_with_usable_edge"] for row in rows),
            "after_entries_with_usable_edge": sum(row["after_entries_with_usable_edge"] for row in rows),
            "delta_entries_with_usable_edge": sum(row["delta_entries_with_usable_edge"] for row in rows),
        },
        "proof_candidate_rows_added_separately": 3,
    }


def _input_evidence():
    return {
        "vnrec_report": "VNREC/VNREC-REPORT.md",
        "vnrec_membership": "VNREC/vnrec-authoritative-membership.json",
        "vnrec_conflicts": "VNREC/vnrec-conflicts.jsonl",
        "edge_summary": "EDGES/edge-closure-summary.json",
        "crosswalk": "EDGES/full-artifacts/lexeme-entry-crosswalk.forward.jsonl",
        "debt": "EDGES/full-artifacts/debt-classification.jsonl",
        "famwide": "FAMWIDE/famwide-strat.jsonl",
        "baseline": "vn-readiness-matrix.json",
    }


def _render_report(matrix):
    lines = [
        "# VNREGEN v2 Report",
        "",
        "Generated by `tools/build_vn_readiness_v2.py` from explicit input files.",
        "All rows are candidate-mode. No live mutation, deployment, source certification, public readback, or push is claimed.",
        "",
        "## Outcome",
        "",
        "The readiness ledger now carries recovered VNREC authority and conflict claims, a separate staging namespace, both provisional planning namespaces, and EDGES usable-crosswalk yield. The historical CLOSED-FROZEN state is recorded evidence only; this lane did not re-verify it live.",
        "",
        "## Denominators",
        "",
        "| unit | count |",
        "|---|---:|",
    ]
    denom = matrix["denominators"]
    for key, label in (
        ("D1_entries", "D1 entries"),
        ("D2_listed_quran_example_cards", "D2 cards"),
        ("D3_displayed_selected_word_rows", "D3 displayed selected-word rows"),
        ("D4_unique_canonical_occurrences", "D4 unique canonical occurrences"),
        ("D4_total_appearances", "D4 total appearances"),
        ("D4_repeated_appearances", "D4 repeated appearances"),
    ):
        lines.append(f"| {label} | {denom[key]:,} |")
    lines.extend(
        [
            "",
            "## Authority and namespace rules",
            "",
            "- `vn_tranche` follows the VNREC scalar contract: authoritative single claims remain scalar, 164 multi-claim historical conflicts remain null, and only no-claim rows receive a `proposed:` partition value.",
            "- `vn_tranche_partition_proposal` and `vn_tranche_plan_table_proposal` are emitted side-by-side only on no-claim rows. The two proposal IDs are never silently collapsed.",
            "- `VN-00-STAGING` is a separate matrix namespace. `vn00_staging_member=true` is retained on ledger rows and does not change the documented VN-00 window label.",
            "- Source certification is exactly zero. The three fully-rich rows are candidate deploy-shaped proof rows only: `sufaha 2:13:12`, `fattabini 19:43:10`, and `ma 2:284:10`.",
            "",
            "## EDGES yield",
            "",
            f"Usable full-corpus forward crosswalk rows: **{matrix['crosswalk_status_counts'].get('deterministic_exact', 0) + matrix['crosswalk_status_counts'].get('candidate', 0):,}**; deterministic_exact={matrix['crosswalk_status_counts'].get('deterministic_exact', 0):,}, candidate={matrix['crosswalk_status_counts'].get('candidate', 0):,}; ambiguous={matrix['crosswalk_status_counts'].get('ambiguous', 0):,} remains incomplete.",
            "",
        ]
    )
    for view_name, view in (("authoritative + partition", matrix["views"]["authoritative_partition"]), ("plan table", matrix["views"]["plan_table"])):
        lines.extend(
            [
                f"## Matrix — {view_name}",
                "",
                "| label | entries | cards | selected words | unique occurrences | graph complete (det/cand) | source-certified | fully-rich proofs | live/no-op rows | owner/scholar | source/crosswalk repair | next action |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in view["tranches"]:
            action = row["next_action"].replace("|", "/")
            lines.append(
                f"| `{row['label']}` | {row['entries']:,} | {row['cards']:,} | {row['displayed_selected_words']:,} | {row['unique_canonical_occurrences']:,} | {row['graph_complete_deterministic_exact_rows']:,}/{row['graph_complete_candidate_rows']:,} | {row['source_certified_rows']:,} | {row['fully_rich_generated_rows']:,} | {row['already_live_noop_selected_word_rows']:,} | {row['owner_scholar_rows']:,} | {row['source_crosswalk_repair_rows']:,} | {action} |"
            )
        lines.append("")
        lines.append(
            f"View totals: entries={view['totals']['entries']:,}, cards={view['totals']['cards']:,}, selected words={view['totals']['displayed_selected_words']:,}, summed unique occurrences={view['totals']['unique_canonical_occurrences']:,}."
        )
        lines.append("")
        for special_label in ("VN-00-STAGING", "HISTORICAL_CONFLICT", "UNPLANNED_PARTICLES"):
            special = view["special_rows"].get(special_label)
            if not special:
                continue
            lines.append(
                f"- `{special_label}`: entries={special['entries']:,}, cards={special['cards']:,}, selected words={special['displayed_selected_words']:,}, graph complete={special['graph_complete_rows']:,}; {special['next_action']}"
            )
        lines.append("")

    delta = matrix["material_improvement_delta"]
    lines.extend(
        [
            "## Material-improvement delta vs the pre-crosswalk matrix",
            "",
            "The delta uses the stable old partition identity so scope recovery does not masquerade as graph improvement. Before counts are the v1 matrix's selected-word rows minus its graph-crosswalk gaps; after counts are the EDGES forward artifact's usable statuses.",
            "",
            "| yield unit | before | after | delta |",
            "|---|---:|---:|---:|",
            f"| selected-word rows with usable edges | {delta['totals']['baseline_usable_selected_word_rows']:,} | {delta['totals']['after_usable_selected_word_rows']:,} | {delta['totals']['delta_usable_selected_word_rows']:+,} |",
            f"| cards completable by usable selected-word edges | {delta['totals']['baseline_cards_completable']:,} | {delta['totals']['after_cards_completable']:,} | {delta['totals']['delta_cards_completable']:+,} |",
            f"| entries with a usable edge | {delta['totals']['baseline_entries_with_usable_edge']:,} | {delta['totals']['after_entries_with_usable_edge']:,} | {delta['totals']['delta_entries_with_usable_edge']:+,} |",
            "",
            "The three proof rows are additive candidate deploy-shaped evidence, not extra corpus selected-word denominator rows and not source-certified rows.",
            "",
            "## Debt classification",
            "",
            "| family | rows |",
            "|---|---:|",
        ]
    )
    for family, count in matrix["debt_family_counts"].items():
        lines.append(f"| {family} | {count:,} |")
    lines.extend(
        [
            "",
            "The owner/scholar headline is `source/scholar required`; divine-name policy and proper-noun rows remain separately visible, as do function-word and duplicate-surface routes.",
            "",
            "## Compounding Impact",
            "",
            f"The EDGES crosswalk changes {matrix['material_improvement_delta']['totals']['delta_usable_selected_word_rows']:+,} stable-partition selected-word rows into usable graph routes, with {matrix['material_improvement_delta']['totals']['after_cards_completable']:,} cards and {matrix['material_improvement_delta']['totals']['after_entries_with_usable_edge']:,} entries now represented by usable edges. Each usable selected-word route can reuse its canonical occurrence and its {denom['D4_total_appearances']:,} indexed appearance surface without copying or rewriting occurrence history.",
            f"FAMWIDE contributes {matrix['family_rows']:,} verified family rows as candidate routing evidence, not source certification. The proof packets add exactly {matrix['proofs']['count']} named candidate deploy-shaped rows and preserve their repeated-appearance/readback limits.",
            "",
            "## Evidence and honest limits",
            "",
            "- Scope and claims: `VNREC/VNREC-REPORT.md`, `VNREC/vnrec-authoritative-membership.json`, and `VNREC/vnrec-conflicts.jsonl`.",
            "- Graph yield: `EDGES/edge-closure-summary.json`, `EDGES/full-artifacts/lexeme-entry-crosswalk.forward.jsonl`, and `EDGES/full-artifacts/debt-classification.jsonl`.",
            "- Calibrated family input: `FAMWIDE/famwide-strat.jsonl`.",
            "- Baseline: the pre-crosswalk `vn-readiness-matrix.json`.",
            "- Proof evidence: `qamus/examples/proof-noun-sufaha/`, `qamus/examples/proof-verb/`, and `qamus/examples/proof-particle/`.",
            "- No source-certified row, live deployment, live readback, browser probe, whitelist append, restart, push, or release is claimed.",
            "",
            "## Reproduction",
            "",
            "Run `python tools/build_vn_readiness_v2.py` with explicit `--entries`, `--whitelist`, `--appearance-index`, `--family`, `--membership`, `--conflicts`, `--edge-summary`, `--crosswalk-forward`, `--debt-classification`, `--baseline-matrix`, `--proofs`, and output arguments. The committed `qamus/examples/vnmap-v2/` subset is the repo-self-contained harness gate.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_v2(
    entries,
    whitelist,
    appearances,
    family_rows,
    membership,
    conflicts,
    edge_summary,
    crosswalk_rows,
    debt_rows,
    baseline_matrix,
    proof_rows,
):
    if not isinstance(entries, list) or not isinstance(whitelist, list) or not isinstance(appearances, list):
        raise ValueError("entries, whitelist, and appearances must be lists")
    entry_by_id = {}
    for entry in entries:
        entry_id = _clean(entry.get("id"))
        if not entry_id or entry_id in entry_by_id:
            raise ValueError(f"duplicate or missing entry id: {entry_id!r}")
        entry_by_id[entry_id] = _source_key(entry)
    claims, evidence, doc_sets, staging = _membership_claims(membership, conflicts)
    assignment_by_key = {
        key: _assignment_for_key(key, claims, evidence, doc_sets, staging)
        for key in set(entry_by_id.values())
    }

    base = build_ledger(entries, whitelist, appearances, family_rows)
    ledger = []
    forward_by_id = {}
    for record in crosswalk_rows:
        selected_id = _clean(record.get("selected_word_id"))
        if selected_id:
            if selected_id in forward_by_id:
                raise ValueError(f"duplicate EDGES forward selected_word_id: {selected_id}")
            forward_by_id[selected_id] = record
    debt_by_id = {}
    for record in debt_rows:
        selected_id = _clean(record.get("selected_word_id"))
        if selected_id:
            debt_by_id[selected_id] = record

    for base_row in base.ledger:
        row = dict(base_row)
        raw_source_key = _clean(row.get("source_key"))
        source_key = _canonical_source_key(raw_source_key)
        assignment = assignment_by_key.get(source_key)
        if assignment is None:
            raise ValueError(f"ledger source key is absent from assignment map: {source_key}")
        selected_id = _selected_word_id(row)
        forward = forward_by_id.get(selected_id, {})
        row["record_type"] = "selected_word_readiness_row"
        row["source_key_raw"] = raw_source_key
        row["source_key"] = source_key
        row["selected_word_id"] = selected_id
        row["crosswalk_status"] = _clean(forward.get("crosswalk_status")) or None
        row["crosswalk_edge_ids"] = sorted(forward.get("edge_ids") or [])
        row["crosswalk_edge_usable"] = row["crosswalk_status"] in USABLE_CROSSWALK_STATUSES
        row["debt_repair_family"] = _clean(debt_by_id.get(selected_id, {}).get("repair_family")) or None
        row.update(assignment)
        # The v1 ledger carried derived labels whose names could be mistaken
        # for recovered authority. v2 exposes only the explicit scalar,
        # status, claims, and proposal fields below.
        for legacy_label_field in ("partition_label", "plan_table_label", "proposal_vn_tranche"):
            row.pop(legacy_label_field, None)
        ledger.append(row)
    ledger.sort(
        key=lambda row: (
            row.get("source_key") or "",
            row.get("usage_index") or 0,
            row.get("form_index") or 0,
            row.get("entry_id") or "",
        )
    )

    assignment_by_key = {key: assignment_by_key[key] for key in assignment_by_key}
    cards = _make_cards(entries)
    whitelist_by_loc = {
        _clean(row.get("loc")): _clean(row.get("entry_id"))
        for row in whitelist
        if _clean(row.get("loc")) and _clean(row.get("entry_id"))
    }
    proof_by_view = {}
    family_counts_by_view = {}
    for view_kind in ("authoritative_partition", "plan_table"):
        proof_by_view[view_kind] = _proofs_by_view(proof_rows, entry_by_id, assignment_by_key, view_kind)
        family_counts_by_view[view_kind] = _family_view_counts(
            family_rows, entry_by_id, whitelist_by_loc, assignment_by_key, view_kind
        )

    views = {}
    for view_kind in ("authoritative_partition", "plan_table"):
        labels = list(PRIMARY_LABELS)
        if view_kind == "plan_table":
            labels.extend(PLAN_EXTRA_LABELS)
        tranches = [
            _stats_for_label(
                label,
                view_kind,
                entries,
                cards,
                ledger,
                assignment_by_key,
                entry_by_id,
                debt_by_id,
                proof_by_view[view_kind],
                family_counts_by_view[view_kind],
                doc_sets,
                claims,
            )
            for label in labels
        ]
        special_rows = {
            label: _special_stats(label, view_kind, entries, cards, ledger, entry_by_id, proof_by_view[view_kind], claims)
            for label in SPECIAL_LABELS
        }
        views[view_kind] = {
            "schema": "vn-readiness-v2/view@1",
            "view_kind": view_kind,
            "tranches": tranches,
            "special_rows": special_rows,
            "totals": _matrix_totals(tranches, special_rows),
            "candidate_only": True,
        }

    status_counts = Counter(row.get("crosswalk_status") or "unavailable" for row in ledger)
    debt_counts = Counter(row["debt_repair_family"] for row in ledger if row.get("debt_repair_family"))
    entry_by_id_for_delta = entry_by_id
    delta = _material_delta(ledger, cards, baseline_matrix, entry_by_id_for_delta)
    all_usable = status_counts.get("deterministic_exact", 0) + status_counts.get("candidate", 0)
    proof_names = sorted(_clean(row.get("name")) for row in proof_rows)
    if proof_names != sorted(PROOF_NAME_SET):
        raise ValueError(f"proof fixture must contain exactly {sorted(PROOF_NAME_SET)}")
    family_mapping = base.matrix.get("clitic_family_northstar") or {
        "family_rows": len(family_rows),
        "calibrated_verified_rows": sum(_clean(row.get("_fb1_verdict")) == "verified" for row in family_rows),
        "candidate_only": True,
        "source_certified_count": 0,
    }
    matrix = {
        "schema": "vn-readiness-v2@1",
        "candidate_only": True,
        "assignment_mode": "vnrec_authority_with_two_explicit_proposals",
        "proposal_ids": ["vn-partition-proposal.v1", "vn-plan-table.v1"],
        "denominators": {
            "D1_entries": base.metrics["denominators"]["D1_entries"],
            "D2_listed_quran_example_cards": base.metrics["denominators"]["D2_listed_quran_example_cards"],
            "D3_displayed_selected_word_rows": base.metrics["denominators"]["D3_displayed_selected_word_rows"],
            "D4_unique_canonical_occurrences": base.metrics["denominators"]["D4_unique_canonical_occurrences"],
            "D4_total_appearances": base.metrics["denominators"]["D4_total_appearances"],
            "D4_repeated_appearances": base.metrics["denominators"]["D4_repeated_appearances"],
        },
        "views": views,
        "scope_summary": {
            "documented_windows": {
                label: {
                    "source_key_range": FROZEN_SCOPE_TEXT[label],
                    "entries": len(doc_sets[label]),
                    "status": "CLOSED-FROZEN (recorded evidence)",
                    "evidence": [FROZEN_SCOPE_CITATIONS[label]],
                }
                for label in FROZEN_LABELS
            },
            "staging_namespace": {
                "source_key_count": len(staging),
                "entries_resolved": sum(_canonical_source_key(value) in entry_by_id.values() for value in staging),
                "field": "vn00_staging_member",
                "matrix_label": "VN-00-STAGING",
                "evidence": ["VNREC/vnrec-authoritative-membership.json:staging_metadata.final_source_key_count=1302"],
            },
            "historical_conflict_source_keys": sum(len(value) > 1 for value in claims.values()),
        },
        "crosswalk_status_counts": _counter_dict(status_counts),
        "usable_crosswalk_status_counts": {
            "deterministic_exact": status_counts.get("deterministic_exact", 0),
            "candidate": status_counts.get("candidate", 0),
        },
        "edge_summary_input": edge_summary,
        "debt_family_counts": _counter_dict(debt_counts),
        "family_rows": len(family_rows),
        "family_mapping": family_mapping,
        "proofs": {
            "count": len(proof_rows),
            "names": proof_names,
            "candidate_only": True,
            "source_certified_count": 0,
            "by_view": {
                view_kind: {label: sorted(names) for label, names in proof_by_view[view_kind].items()}
                for view_kind in proof_by_view
            },
        },
        "material_improvement_delta": delta,
        "compounding_impact": {
            "usable_selected_word_rows": all_usable,
            "usable_cards_after": delta["totals"]["after_cards_completable"],
            "usable_entries_after": delta["totals"]["after_entries_with_usable_edge"],
            "canonical_unique_occurrences_in_ledger": len({row.get("occurrence_id") for row in ledger if row.get("occurrence_id")}),
            "indexed_total_appearances": base.metrics["denominators"]["D4_total_appearances"],
            "family_candidate_rows": len(family_rows),
            "proof_candidate_rows": len(proof_rows),
            "candidate_only": True,
        },
        "input_evidence": _input_evidence(),
    }
    report = _render_report(matrix)
    return BuildResultV2(ledger=ledger, matrix=matrix, report=report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "entries",
        "whitelist",
        "appearance-index",
        "family",
        "membership",
        "conflicts",
        "edge-summary",
        "crosswalk-forward",
        "debt-classification",
        "baseline-matrix",
        "proofs",
        "matrix-output",
        "ledger-output",
        "report-output",
    ):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    result = build_v2(
        _read_jsonl(args.entries),
        _read_jsonl(args.whitelist),
        _read_jsonl(args.appearance_index),
        _read_jsonl(args.family),
        _read_json(args.membership),
        _read_jsonl(args.conflicts),
        _read_json(args.edge_summary),
        _read_jsonl(args.crosswalk_forward),
        _read_jsonl(args.debt_classification),
        _read_json(args.baseline_matrix),
        _read_json(args.proofs),
    )
    _write_json(result.matrix, args.matrix_output)
    _write_jsonl(result.ledger, args.ledger_output)
    directory = os.path.dirname(os.path.abspath(args.report_output))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(args.report_output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(result.report)
    print(
        "VN READINESS V2 BUILD PASS "
        f"entries={result.matrix['denominators']['D1_entries']} "
        f"selected_words={result.matrix['denominators']['D3_displayed_selected_word_rows']} "
        f"usable_crosswalk={sum(result.matrix['usable_crosswalk_status_counts'].values())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
