#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the ratified, candidate-only VN readiness v2 artifacts.

The builder keeps three different facts in three different lanes:

* documented VN-00/01/02 contracts are authoritative membership;
* cumulative rollout snapshots are deployment-history evidence in the
  ``vn00_staging_history`` namespace; and
* the historical VN-03..VN-23 table is the planning baseline.

The balanced partition proposal remains available as comparison data only.
All inputs are explicit CLI arguments and all outputs are candidate-mode.
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
from tools.certify_typed_fact import count_certified as _count_certified_typed_facts  # noqa: E402


_SOURCE_CERTIFIED_CACHE = None


def source_certified_ledger_count():
    """Ledger-derived count of certified typed facts.

    Read from the typed-fact certification event trail
    (tools/certify_typed_fact.py DEFAULT_STORE_DIR); an absent store means
    zero. This replaces the former hardcoded zero so the readiness matrix
    reports the certification layer instead of asserting its absence.
    """

    global _SOURCE_CERTIFIED_CACHE
    if _SOURCE_CERTIFIED_CACHE is None:
        _SOURCE_CERTIFIED_CACHE = _count_certified_typed_facts()
    return _SOURCE_CERTIFIED_CACHE


def source_certification_state_text():
    count = source_certified_ledger_count()
    if count == 0:
        return "0; candidate-only lane has no source certification"
    return "%d; counted from the typed-fact certification event trail" % count


PRIMARY_LABELS = tuple(f"VN-{index:02d}" for index in range(21))
TAIL_LABELS = ("VN-21", "VN-22", "VN-23")
FROZEN_LABELS = ("VN-00", "VN-01", "VN-02")
PLANNING_LABELS = tuple(f"VN-{index:02d}" for index in range(3, 24))
SPECIAL_LABELS = (
    "vn00_staging_history",
    "historical_conflict",
    "unplanned_particles",
    "unassigned",
)
USABLE_CROSSWALK_STATUSES = frozenset({"deterministic_exact", "candidate"})
PROOF_NAMES = (
    "sufaha 2:13:12",
    "fattabini 19:43:10",
    "ma 2:284:10",
)
PROOF_NAME_SET = frozenset(PROOF_NAMES)
ARCHITECTURE_PROOF_STATUS = "architecture_proof_candidate"
STAGING_NAMESPACE = "vn00_staging_history"

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
    label: f"VNREC/VNREC-REPORT.md §Recovered authoritative scope; recorded CLOSED-FROZEN ({label})"
    for label in FROZEN_LABELS
}

# This is the historical plan table, copied as an explicit identifier table so
# the planner never silently regenerates it from the balanced comparison.
PLAN_WINDOWS = {
    "VN-03": {"v": (142, 188), "n": (136, 180), "status_note": "measured 69.38%, worklist 3,280 (OBSERVED)"},
    "VN-04": {"v": (189, 235), "n": (181, 225), "status_note": "pattern-only"},
    "VN-05": {"v": (236, 282), "n": (226, 270), "status_note": "pattern-only"},
    "VN-06": {"v": (283, 329), "n": (271, 315), "status_note": "pattern-only"},
    "VN-07": {"v": (330, 376), "n": (316, 360), "status_note": "pattern-only"},
    "VN-08": {"v": (377, 423), "n": (361, 405), "status_note": "pattern-only"},
    "VN-09": {"v": (424, 470), "n": (406, 450), "status_note": "pattern-only"},
    "VN-10": {"v": (471, 517), "n": (451, 495), "status_note": "pattern-only"},
    "VN-11": {"v": (518, 564), "n": (496, 540), "status_note": "pattern-only"},
    "VN-12": {"v": (565, 611), "n": (541, 585), "status_note": "pattern-only"},
    "VN-13": {"v": (612, 658), "n": (586, 630), "status_note": "pattern-only"},
    "VN-14": {"v": (659, 705), "n": (631, 675), "status_note": "pattern-only"},
    "VN-15": {"v": (706, 752), "n": (676, 720), "status_note": "pattern-only"},
    "VN-16": {"v": (753, 799), "n": (721, 765), "status_note": "pattern-only"},
    "VN-17": {"v": (800, 846), "n": (766, 810), "status_note": "pattern-only"},
    "VN-18": {"v": (847, 893), "n": (811, 855), "status_note": "pattern-only"},
    "VN-19": {"v": (894, 940), "n": (856, 900), "status_note": "last full-shape window"},
    "VN-20": {"v": (941, 947), "n": (901, 945), "status_note": "stub v-side"},
    "VN-21": {"v": None, "n": (946, 990), "status_note": "beyond the titled program"},
    "VN-22": {"v": None, "n": (991, 1035), "status_note": "beyond the titled program"},
    "VN-23": {"v": None, "n": (1036, 1045), "status_note": "stub"},
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


def _read_receipts(path):
    """Read either a JSON receipt list or the line-oriented backup listing."""

    if not path:
        return []
    if str(path).lower().endswith((".json", ".jsonl")):
        payload = _read_json(path) if str(path).lower().endswith(".json") else _read_jsonl(path)
        if isinstance(payload, dict):
            payload = payload.get("receipts") or payload.get("items") or []
        result = []
        for item in payload or []:
            if isinstance(item, str):
                result.append(item.strip())
            elif isinstance(item, dict):
                result.append(_clean(item.get("receipt_id") or item.get("name") or item.get("identifier")))
        return [value for value in result if value]
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


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
    return {f"{prefix}{number:0{width}d}" for number in range(start, end + 1)}


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
    ranges = {}
    for label, window in PLAN_WINDOWS.items():
        keys = set()
        if window["v"]:
            keys |= _range_keys("v", window["v"][0], window["v"][1])
        if window["n"]:
            keys |= _range_keys("n", window["n"][0], window["n"][1], 4)
        ranges[label] = keys
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
    """Retained for comparison metadata; never emitted as a ledger assignment."""

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


def _snapshot_map(payload):
    if not payload:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("snapshots"), dict):
        payload = payload["snapshots"]
    if not isinstance(payload, dict):
        return {}
    result = {}
    for name, values in payload.items():
        if isinstance(values, list):
            result[_clean(name)] = {_canonical_source_key(value) for value in values if _clean(value)}
    return {name: values for name, values in result.items() if name}


def _backup_key(receipt):
    match = re.search(r"(?<![a-z])([vnp]\d{1,4})(?!\d)", _clean(receipt), re.IGNORECASE)
    return _canonical_source_key(match.group(1)) if match else None


def _membership_context(membership, conflicts, staging_snapshots=None, deployment_receipts=None):
    """Return documented authority and separate deployment-history evidence."""

    doc_sets = {label: set() for label in FROZEN_LABELS}
    documented_by_key = defaultdict(set)
    evidence = defaultdict(list)
    staging_from_membership = set()
    staging_metadata = membership.get("staging_metadata") or {}

    for label, details in (membership.get("vn") or {}).items():
        for record in details.get("authoritative_sets") or []:
            keys = {_canonical_source_key(value) for value in record.get("source_keys") or []}
            kind = record.get("kind")
            if kind == "documented_window_contract" and label in FROZEN_LABELS:
                doc_sets[label].update(keys)
                for key in keys:
                    documented_by_key[key].add(label)
                    _append_evidence(evidence[key], record.get("evidence"))
            elif kind == "deployed_rollout_staging_cumulative_snapshot":
                staging_from_membership.update(keys)
                for key in keys:
                    _append_evidence(evidence[key], record.get("evidence"))

    snapshots = _snapshot_map(staging_snapshots)
    if not snapshots and staging_from_membership:
        snapshot_name = _clean(staging_metadata.get("final_snapshot")) or "staging-final-cumulative"
        snapshots[snapshot_name] = set(staging_from_membership)
    elif staging_from_membership:
        final_name = _clean(staging_metadata.get("final_snapshot"))
        if final_name and final_name not in snapshots:
            snapshots[final_name] = set(staging_from_membership)

    staging = set(staging_from_membership)
    for values in snapshots.values():
        staging.update(values)

    backup_receipts = [value for value in (deployment_receipts or []) if _clean(value)]
    backup_by_key = defaultdict(list)
    for receipt in backup_receipts:
        key = _backup_key(receipt)
        if key:
            backup_by_key[key].append(receipt)

    unresolved = {}
    for record in conflicts:
        if record.get("record_type") != "source_key_conflict":
            continue
        key = _canonical_source_key(record.get("source_key"))
        labels = {_clean(value) for value in record.get("historical_authoritative_labels") or [] if _clean(value)}
        if not labels:
            continue
        _append_evidence(evidence[key], record.get("evidence"))
        evidence[key].append(f"VNREC/vnrec-conflicts.jsonl:source_key={key}")
        documented = documented_by_key.get(key, set())
        # The old conflict file encoded a documented label plus a synthetic
        # VN-00 staging label. Once staging is separated, a single documented
        # label controls. Any other shape remains genuinely irreconcilable.
        # A lone VN-00 claim is also a synthetic staging-membership claim, not
        # a second membership authority; the cumulative snapshots are the
        # only surface that can preserve it as deployment history.
        if labels == {"VN-00"}:
            continue
        if len(documented) == 1 and documented.issubset(labels) and labels - documented <= {"VN-00"} and key in staging:
            continue
        if labels == documented and len(documented) == 1:
            continue
        if len(documented) > 1 or not documented or labels - documented:
            unresolved[key] = sorted(labels)

    for key in list(evidence):
        evidence[key] = sorted(set(value for value in evidence[key] if value))

    return {
        "doc_sets": doc_sets,
        "documented_by_key": documented_by_key,
        "evidence": evidence,
        "staging": staging,
        "snapshots": snapshots,
        "backup_receipts": backup_receipts,
        "backup_by_key": {key: sorted(values) for key, values in backup_by_key.items()},
        "unresolved": unresolved,
    }


def _membership_claims(membership, conflicts):
    """Compatibility helper returning only documented claims and staging keys."""

    context = _membership_context(membership, conflicts)
    return (
        context["documented_by_key"],
        context["evidence"],
        context["doc_sets"],
        context["staging"],
    )


def _provenance(value, evidence, **extra):
    result = {"value": value, "evidence": sorted(set(evidence or []))}
    if not result["evidence"]:
        result["evidence"] = ["no recoverable value-specific evidence; value remains empty"]
    result.update(extra)
    return result


def _assignment_for_key(
    source_key,
    claims,
    evidence,
    doc_sets,
    staging,
    staging_snapshots=None,
    backup_receipts=None,
    unresolved=None,
):
    source_key = _canonical_source_key(source_key)
    documented_claims = sorted(claims.get(source_key, set()))
    unresolved = unresolved or {}
    unresolved_claims = sorted(unresolved.get(source_key, []))
    plan_label = _label_for_key(source_key, PLAN_RANGES)
    comparison_label = _label_for_key(source_key, PARTITION_RANGES)
    row_evidence = sorted(set(evidence.get(source_key, [])))
    snapshots = staging_snapshots or {}
    snapshot_hits = sorted(name for name, values in snapshots.items() if source_key in values)
    if source_key in staging and not snapshot_hits:
        snapshot_hits = ["staging-final-cumulative"]
    history_claims = [STAGING_NAMESPACE] if source_key in staging else []

    if unresolved_claims:
        authoritative = None
        status = "historical_conflict"
    elif len(documented_claims) == 1:
        authoritative = documented_claims[0]
        status = "authoritative"
    elif plan_label:
        authoritative = None
        status = "planning_only"
    else:
        authoritative = None
        status = "unassigned"

    if authoritative:
        primary_view = authoritative
        authority_evidence = row_evidence
        if history_claims:
            authority_evidence = authority_evidence + [
                "owner ratification: documented CLOSED-FROZEN contract controls staging history"
            ]
    elif status == "historical_conflict":
        primary_view = "historical_conflict"
        authority_evidence = row_evidence + [
            f"irreconcilable historical claims: {','.join(unresolved_claims)}"
        ]
    elif plan_label in PRIMARY_LABELS:
        primary_view = plan_label
        authority_evidence = []
    elif plan_label in TAIL_LABELS:
        primary_view = None
        authority_evidence = []
    elif source_key.startswith("p"):
        primary_view = "unplanned_particles"
        authority_evidence = []
    else:
        primary_view = "unassigned"
        authority_evidence = []
    tail_view = plan_label if plan_label in TAIL_LABELS else None

    planning_assignment = plan_label if plan_label else None
    planning_evidence = []
    if planning_assignment:
        planning_evidence = [
            f"VNREC/inputs/14-VN-FLYWHEEL-AND-TRANCHE-PLAN.md:§4.1 window table:{planning_assignment}",
            f"historical plan identifier={planning_assignment}; source-key window={_plan_window_text(planning_assignment)}",
        ]

    history_evidence = [
        f"VNREC/inputs/staging-sourcekeys-full.json:{snapshot}:source_key={source_key}"
        for snapshot in snapshot_hits
    ]
    if source_key in staging and not history_evidence:
        history_evidence = [
            f"VNREC/vnrec-authoritative-membership.json:staging_metadata.final_source_key_count=1302:source_key={source_key}"
        ]
    receipt_ids = [f"staging_snapshot:{snapshot}" for snapshot in snapshot_hits]
    source_backups = sorted((backup_receipts or {}).get(source_key, []))
    receipt_ids.extend(f"backup_listing:{receipt}" for receipt in source_backups)
    receipt_ids = sorted(set(receipt_ids))
    receipt_evidence = list(history_evidence)
    receipt_evidence.extend(
        f"VNREC/inputs/backups-vn-listing.txt:source_key-specific receipt={receipt}"
        for receipt in source_backups
    )
    if not receipt_ids:
        receipt_evidence = [
            "VNREC/inputs/backups-vn-listing.txt:global listing is not key-addressable for this source_key",
            "no key-specific staging snapshot receipt was recovered",
        ]

    provenance = {
        "vn_tranche_authoritative": _provenance(
            authoritative,
            authority_evidence or [
                f"no documented CLOSED-FROZEN membership for source_key={source_key}"
            ],
            unresolved_claims=unresolved_claims,
        ),
        "vn_tranche_status": _provenance(
            status,
            authority_evidence
            or planning_evidence
            or [f"no documented or historical plan assignment for source_key={source_key}"],
        ),
        "vn_planning_assignment": _provenance(
            planning_assignment,
            planning_evidence or ["not in the historical VN-03→VN-23 plan-table windows"],
        ),
        "vn_staging_history_claims": _provenance(
            history_claims,
            history_evidence or ["source_key absent from supplied cumulative staging snapshots"],
            namespace=STAGING_NAMESPACE,
            snapshots=snapshot_hits,
        ),
        "vn_deployment_receipts": _provenance(receipt_ids, receipt_evidence, receipts=receipt_ids),
    }
    return {
        "vn_tranche_authoritative": authoritative,
        "vn_tranche_status": status,
        "vn_planning_assignment": planning_assignment,
        "vn_staging_history_claims": history_claims,
        "vn_deployment_receipts": receipt_ids,
        "vn_assignment_provenance": provenance,
        # Internal routing metadata is removed before a row is serialized.
        "_primary_view": primary_view,
        "_tail_view": tail_view,
        "_comparison_label": comparison_label,
        "_snapshot_hits": snapshot_hits,
    }


def _plan_window_text(label):
    window = PLAN_WINDOWS[label]
    v = f"v{window['v'][0]:03d}–v{window['v'][1]:03d}" if window["v"] else "—"
    n = f"n{window['n'][0]:04d}–n{window['n'][1]:04d}" if window["n"] else "—"
    return f"{v}+{n}" if v != "—" else n


def _plan_window_record(label):
    window = PLAN_WINDOWS[label]
    v_window = f"v{window['v'][0]:03d}–v{window['v'][1]:03d}" if window["v"] else "—"
    n_window = f"n{window['n'][0]:04d}–n{window['n'][1]:04d}" if window["n"] else "—"
    return {
        "identifier": label,
        "v_window": v_window,
        "n_window": n_window,
        "source_key_range": _plan_window_text(label),
        "status_note": window["status_note"],
        "authoritative": True,
        "planning_role": True,
        "evidence": ["VNREC/inputs/14-VN-FLYWHEEL-AND-TRANCHE-PLAN.md:§4.1 window table"],
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
    occurrence_id = ""
    for key in ("canonical_quran_loc", "quran_loc", "occurrence_id"):
        value = _clean(row.get(key))
        if value:
            occurrence_id = value.split(":", 1)[1] if value.startswith("quran:") else value
            break
    return selected_word_node(
        _clean(row.get("entry_id")),
        int(row.get("sense_index") or 1),
        int(row.get("usage_index") or 1),
        int(row.get("form_index") or 1),
        _clean(row.get("source_card_ref")),
        max(1, example_index),
        occurrence_id,
    )


def _card_key(entry_id, usage_index, example_index):
    return f"{entry_id}|{int(usage_index)}|{int(example_index)}"


def _make_cards(entries):
    cards = []
    for entry in entries:
        entry_id = _clean(entry.get("id"))
        for usage_index, usage in enumerate(entry.get("usage") or [], 1):
            examples = (usage.get("examples") or []) if isinstance(usage, dict) else []
            for example_index, _example in enumerate(examples, 1):
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
        label = assignment_by_key[key].get(f"_{view_kind}_view")
        if label:
            result[label].append(name)
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
        label = assignment_by_key[key].get(f"_{view_kind}_view")
        if label:
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
    if label in FROZEN_LABELS:
        return f"Preserve recorded CLOSED-FROZEN {label}; candidate graph/source work remains non-live."
    if label == STAGING_NAMESPACE:
        return "Retain deployment-history evidence separately; never use it as membership."
    if label == "historical_conflict":
        return "Route each irreconcilable historical claim for explicit owner adjudication."
    if label == "unplanned_particles":
        return "Keep p-pages unplanned and candidate-only until a documented plan exists."
    if label == "unassigned":
        return "No documented membership or historical plan is available; retain unassigned."
    if label in TAIL_LABELS:
        return f"Keep documented tail {label} explicit; do not merge it into VN-00→VN-20."
    if label in PLANNING_LABELS:
        return f"Use the historical plan-table {label} baseline; candidate evidence only."
    return "Retain candidate boundary and provenance."


def _rows_for_assignment(ledger, assignment_by_key, view_kind, label):
    private_key = f"_{view_kind}_view"
    return [row for row in ledger if assignment_by_key.get(row.get("source_key"), {}).get(private_key) == label]


def _entry_ids_for_assignment(entries, entry_by_id, assignment_by_key, view_kind, label):
    private_key = f"_{view_kind}_view"
    return {
        entry["id"]
        for entry in entries
        if assignment_by_key.get(entry_by_id[entry["id"]], {}).get(private_key) == label
    }


def _metric_row(label, view_kind, rows, entry_ids, cards, proof_by_view, family_count, debt_counter, scope_evidence=None):
    card_rows = [card for card in cards if card["entry_id"] in entry_ids]
    status_counts = Counter(row.get("crosswalk_status") or "unavailable" for row in rows)
    det = status_counts.get("deterministic_exact", 0)
    candidate = status_counts.get("candidate", 0)
    occurrences = {row.get("occurrence_id") for row in rows if row.get("occurrence_id")}
    proof_names = sorted(proof_by_view.get(label, []))
    if label in FROZEN_LABELS:
        live_state = "recorded CLOSED-FROZEN scope; not live-reverified"
        live_entries, live_cards, live_rows = len(entry_ids), len(card_rows), len(rows)
        assigned = len(entry_ids)
        scope_status = "CLOSED-FROZEN (recorded evidence)"
        scope_range = FROZEN_SCOPE_TEXT[label]
    elif label in PLANNING_LABELS:
        live_state = "not applicable; planning baseline only"
        live_entries = live_cards = live_rows = 0
        assigned = 0
        scope_status = "authoritative historical planning baseline; not historical closure"
        scope_range = _plan_window_text(label)
    else:
        live_state = "not applicable"
        live_entries = live_cards = live_rows = 0
        assigned = 0
        scope_status = "candidate-only sidecar"
        scope_range = None
    return {
        "label": label,
        "view": view_kind,
        "entries": len(entry_ids),
        "cards": len(card_rows),
        "displayed_selected_words": len(rows),
        "unique_canonical_occurrences": len(occurrences),
        "crosswalk_status_counts": _counter_dict(status_counts),
        "graph_complete_rows": det + candidate,
        "graph_complete_deterministic_exact_rows": det,
        "graph_complete_candidate_rows": candidate,
        "source_certified_rows": source_certified_ledger_count(),
        "source_certification_state": source_certification_state_text(),
        "fully_rich_generated_rows": len(proof_names),
        "fully_rich_generated_proof_names": proof_names,
        "already_live_noop_entries": live_entries,
        "already_live_noop_cards": live_cards,
        "already_live_noop_selected_word_rows": live_rows,
        "already_live_noop_state": live_state,
        "historical_conflict_entries": len({row["entry_id"] for row in rows if row.get("vn_tranche_status") == "historical_conflict"}),
        "historical_conflict_selected_word_rows": sum(row.get("vn_tranche_status") == "historical_conflict" for row in rows),
        "authoritative_assigned_entries": assigned,
        "debt_rows": sum(debt_counter.values()),
        "debt_family_counts": _counter_dict(debt_counter),
        **_debt_bucket_counts(debt_counter),
        "calibrated_family_candidate_rows": family_count,
        "scope_source_key_range": scope_range,
        "scope_status": scope_status,
        "scope_evidence": sorted(set(scope_evidence or [])),
        "next_action": _next_action(label, {"debt_rows": sum(debt_counter.values())}),
        "candidate_only": True,
    }


def _special_metric(label, view_kind, entries, cards, ledger, assignment_by_key, entry_by_id, proof_by_view):
    if label == STAGING_NAMESPACE:
        rows = [row for row in ledger if row.get("vn_staging_history_claims")]
        entry_ids = {
            entry["id"]
            for entry in entries
            if assignment_by_key[entry_by_id[entry["id"]]].get("vn_staging_history_claims")
        }
        sidecar = True
        scope_evidence = [
            "VNREC/vnrec-authoritative-membership.json:staging_metadata.final_source_key_count=1302",
            "VNREC/inputs/staging-sourcekeys-full.json:complete cumulative per-snapshot source_key sets",
        ]
    elif label == "historical_conflict":
        rows = [row for row in ledger if row.get("vn_tranche_status") == "historical_conflict"]
        entry_ids = {row["entry_id"] for row in rows}
        sidecar = False
        scope_evidence = ["VNREC/vnrec-conflicts.jsonl:irreconcilable historical claims only"]
    else:
        rows = [row for row in ledger if assignment_by_key.get(row.get("source_key"), {}).get(f"_{view_kind}_view") == label]
        entry_ids = _entry_ids_for_assignment(entries, entry_by_id, assignment_by_key, view_kind, label)
        sidecar = False
        scope_evidence = []
    debt_counter = Counter(row["debt_repair_family"] for row in rows if row.get("debt_repair_family"))
    result = _metric_row(
        label,
        view_kind,
        rows,
        entry_ids,
        cards,
        proof_by_view,
        0,
        debt_counter,
        scope_evidence,
    )
    result["sidecar_only"] = sidecar
    result["namespace"] = STAGING_NAMESPACE if label == STAGING_NAMESPACE else None
    if label == STAGING_NAMESPACE:
        result["source_key_count"] = len({row["source_key"] for row in rows})
        result["matrix_accounting"] = "sidecar_only; overlaps are not added to primary or tail totals"
    return result


def _matrix_totals(tranches, special_rows):
    included = list(tranches)
    for label in ("historical_conflict", "unplanned_particles", "unassigned"):
        if label in special_rows:
            included.append(special_rows[label])
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
        label = partition_label_for_entry.get(card["entry_id"])
        if label is None:
            continue
        rows = rows_by_card.get(card["card_key"], [])
        if rows and all(bool(row.get(field)) for row in rows):
            grouped[label] += 1
    return grouped


def _material_delta(ledger, cards, baseline_matrix, entry_by_id):
    baseline_rows = {}
    for row in baseline_matrix.get("tranches") or []:
        label = _clean(row.get("proposal_vn_tranche"))
        if label:
            baseline_rows[label] = {
                "selected": int(row.get("displayed_selected_words") or 0),
                "complete": int(row.get("displayed_selected_words") or 0)
                - int(row.get("graph_crosswalk_gap_rows") or 0),
            }
    partition_by_entry = {
        entry_id: _label_for_key(key, PARTITION_RANGES) for entry_id, key in entry_by_id.items()
    }
    before_cards = _card_completeness(ledger, cards, partition_by_entry, "crosswalk_flag")
    after_cards = Counter()
    rows_by_entry = defaultdict(list)
    after_by_label = defaultdict(Counter)
    for row in ledger:
        label = partition_by_entry.get(row["entry_id"])
        if not label:
            continue
        status = row.get("crosswalk_status")
        if status in USABLE_CROSSWALK_STATUSES:
            after_by_label[label][status] += 1
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
    before_entries = Counter(
        {
            label: len(
                {
                    row["entry_id"]
                    for row in ledger
                    if partition_by_entry.get(row["entry_id"]) == label and row.get("crosswalk_flag")
                }
            )
            for label in PRIMARY_LABELS
        }
    )
    after_entries = Counter(
        {
            label: len(
                {
                    entry_id
                    for entry_id, rows in rows_by_entry.items()
                    if partition_by_entry.get(entry_id) == label and rows
                }
            )
            for label in PRIMARY_LABELS
        }
    )
    rows = []
    for label in PRIMARY_LABELS:
        before = baseline_rows.get(label, {"selected": 0, "complete": 0})
        det = after_by_label[label].get("deterministic_exact", 0)
        candidate = after_by_label[label].get("candidate", 0)
        usable = det + candidate
        rows.append(
            {
                "label": label,
                "baseline_selected_word_rows": before["selected"],
                "baseline_usable_selected_word_rows": before["complete"],
                "after_deterministic_exact_rows": det,
                "after_candidate_rows": candidate,
                "after_usable_selected_word_rows": usable,
                "delta_usable_selected_word_rows": usable - before["complete"],
                "baseline_cards_completable": before_cards.get(label, 0),
                "after_cards_completable": after_cards.get(label, 0),
                "delta_cards_completable": after_cards.get(label, 0) - before_cards.get(label, 0),
                "baseline_entries_with_usable_edge": before_entries.get(label, 0),
                "after_entries_with_usable_edge": after_entries.get(label, 0),
                "delta_entries_with_usable_edge": after_entries.get(label, 0) - before_entries.get(label, 0),
            }
        )
    return {
        "basis": "stable VN-00..VN-20 balanced comparison identity; authority remapping is not mixed into this delta",
        "before_source": "pre-ratification vn-readiness-matrix.json",
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
        "staging_snapshots": "VNREC/inputs/staging-sourcekeys-full.json",
        "staging_listing": "VNREC/inputs/staging-listing.txt",
        "backup_listing": "VNREC/inputs/backups-vn-listing.txt",
        "plan_table": "VNREC/inputs/14-VN-FLYWHEEL-AND-TRANCHE-PLAN.md §4.1",
        "edge_summary": "EDGES/edge-closure-summary.json",
        "crosswalk": "EDGES/full-artifacts/lexeme-entry-crosswalk.forward.jsonl",
        "debt": "EDGES/full-artifacts/debt-classification.jsonl",
        "famwide": "FAMWIDE/famwide-strat.jsonl",
        "baseline": "vn-readiness-matrix.json",
    }


def _staging_investigation(doc_sets, snapshots, backup_by_key):
    missing = sorted(doc_sets["VN-00"] - set().union(*snapshots.values()) if snapshots else doc_sets["VN-00"])
    rows = []
    for key in missing:
        hits = sorted(name for name, values in snapshots.items() if key in values)
        backups = sorted(backup_by_key.get(key, []))
        if hits:
            classification = "possible missing deployment-readback record; final snapshot does not retain an earlier observed key"
        else:
            classification = "staging-history coverage gap / snapshot incompleteness; possible missing deployment-readback record is not distinguishable"
        rows.append(
            {
                "source_key": key,
                "documented_membership": "VN-00",
                "final_staging_present": False,
                "cumulative_snapshot_hits": hits,
                "key_specific_backup_receipts": backups,
                "classification": classification,
                "evidence": [
                    "VNREC/vnrec-authoritative-membership.json:VN-00 documented_window_contract",
                    "VNREC/inputs/staging-sourcekeys-full.json:vn00-pages-061-070-c through vn00-pages-161-170-c",
                    "VNREC/inputs/backups-vn-listing.txt:lines 1-5",
                ],
            }
        )
    return rows


def _comparison_artifact(ledger, entries, entry_by_id, assignment_by_key, cards):
    tranches = []
    for label in PRIMARY_LABELS:
        entry_ids = {
            entry["id"]
            for entry in entries
            if assignment_by_key[entry_by_id[entry["id"]]]["_comparison_label"] == label
        }
        rows = [row for row in ledger if assignment_by_key[row["source_key"]]["_comparison_label"] == label]
        status = Counter(row.get("crosswalk_status") or "unavailable" for row in rows)
        tranches.append(
            {
                "label": label,
                "source_key_count": len(PARTITION_RANGES.get(label, set())),
                "entries": len(entry_ids),
                "cards": len({card["card_key"] for card in cards if card["entry_id"] in entry_ids}),
                "displayed_selected_words": len(rows),
                "graph_complete_rows": sum(status.get(value, 0) for value in USABLE_CROSSWALK_STATUSES),
                "crosswalk_status_counts": _counter_dict(status),
                "authoritative": False,
                "planning_role": False,
            }
        )
    return {
        "artifact_id": "vn-partition-proposal.v1",
        "authoritative": False,
        "planning_role": False,
        "role": "versioned_non_authoritative_comparison_artifact",
        "source_key_rule": "existing balanced partition proposal; retained for comparison only",
        "tranches": tranches,
    }


def _render_matrix_table(view):
    lines = [
        "| label | entries | cards | selected words | unique occurrences | graph complete (det/cand) | source-certified | architecture proofs | live/no-op rows | owner/scholar | source/crosswalk repair |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in view["tranches"]:
        lines.append(
            f"| `{row['label']}` | {row['entries']:,} | {row['cards']:,} | {row['displayed_selected_words']:,} | {row['unique_canonical_occurrences']:,} | {row['graph_complete_deterministic_exact_rows']:,}/{row['graph_complete_candidate_rows']:,} | {row['source_certified_rows']} | {', '.join(row['fully_rich_generated_proof_names']) or '0'} | {row['already_live_noop_selected_word_rows']:,} | {row['owner_scholar_rows']:,} | {row['source_crosswalk_repair_rows']:,} |"
        )
    return lines


def _render_report(matrix):
    delta = matrix["material_improvement_delta"]["totals"]
    lines = [
        "# VNREGEN v2 Ratified Report",
        "",
        "Generated by `tools/build_vn_readiness_v2.py` from explicit input files.",
        "All rows are candidate-mode. No live mutation, deployment, source certification, public readback, or push is claimed.",
        "",
        "## Outcome",
        "",
        "Documented CLOSED-FROZEN VN-00/01/02 contracts are the only historical membership authority. Cumulative rollout snapshots are preserved as the separate `vn00_staging_history` deployment-history namespace. The historical plan table is the planning baseline for VN-03→VN-23; the balanced partition remains comparison-only.",
        "",
        "## Denominators",
        "",
        "| unit | count |",
        "|---|---:|",
        f"| D1 entries | {matrix['denominators']['D1_entries']:,} |",
        f"| D2 cards | {matrix['denominators']['D2_listed_quran_example_cards']:,} |",
        f"| D3 displayed selected-word rows | {matrix['denominators']['D3_displayed_selected_word_rows']:,} |",
        f"| D4 unique canonical occurrences | {matrix['denominators']['D4_unique_canonical_occurrences']:,} |",
        f"| D4 total appearances | {matrix['denominators']['D4_total_appearances']:,} |",
        f"| D4 repeated appearances | {matrix['denominators']['D4_repeated_appearances']:,} |",
        "",
        "## Ratified schema and authority boundary",
        "",
        "- Ledger VN authority fields are `vn_tranche_authoritative`, `vn_tranche_status`, `vn_planning_assignment`, `vn_staging_history_claims`, `vn_deployment_receipts`, and `vn_assignment_provenance`; no legacy scalar or staging-membership field is emitted.",
        "- A staging-history claim never overrides documented membership. The same row may carry `vn_tranche_authoritative=VN-01` (or another documented tranche) and `vn_staging_history_claims=[\"vn00_staging_history\"]`.",
        "- `vn_tranche_status` is `authoritative`, `planning_only`, or `unassigned` for this full run. `historical_conflict` is reserved for genuinely irreconcilable claims and would list every unresolved claim in provenance.",
        f"- The three architecture proofs are marked `{ARCHITECTURE_PROOF_STATUS}`; they prove canonical path + compiler shape in candidate mode, not public tranche closure.",
        "",
        "## Matrix — primary VN-00→VN-20",
        "",
    ]
    lines.extend(_render_matrix_table(matrix["views"]["primary"]))
    lines.extend(
        [
            "",
            f"Primary totals: entries={matrix['views']['primary']['totals']['entries']:,}, cards={matrix['views']['primary']['totals']['cards']:,}, selected words={matrix['views']['primary']['totals']['displayed_selected_words']:,}.",
            "",
            "## Matrix — explicit documented tail VN-21→VN-23",
            "",
        ]
    )
    lines.extend(_render_matrix_table(matrix["views"]["documented_tail"]))
    lines.extend(
        [
            "",
            f"Tail totals: entries={matrix['views']['documented_tail']['totals']['entries']:,}, cards={matrix['views']['documented_tail']['totals']['cards']:,}, selected words={matrix['views']['documented_tail']['totals']['displayed_selected_words']:,}.",
            "The tail is not merged into VN-00→VN-20. Unplanned particles remain an explicit primary sidecar.",
            "",
            "### Separate history and unplanned sidecars",
            "",
            f"- `vn00_staging_history`: {matrix['scope_summary']['staging_history_namespace']['source_key_count']:,} source keys; {matrix['scope_summary']['staging_history_namespace']['history_only_source_key_count']:,} history-only keys; {matrix['scope_summary']['staging_history_namespace']['overlap_authoritative_source_key_count']:,} overlap documented authority. This sidecar is not added to primary/tail denominators.",
            f"- `unplanned_particles`: {matrix['views']['primary']['special_rows']['unplanned_particles']['entries']:,} entries / {matrix['views']['primary']['special_rows']['unplanned_particles']['displayed_selected_words']:,} selected-word rows; no planning assignment.",
            "",
            "## Four-key VN-00 staging-history investigation",
            "",
            "The four documented VN-00 keys below remain authoritative members. They are absent from the final staging snapshot and from every supplied cumulative snapshot. That is a staging-history coverage discrepancy, not a membership deletion; the supplied evidence cannot distinguish snapshot incompleteness from a missing deployment-readback record.",
            "",
            "| source key | documented membership | final staging | cumulative snapshot hits | key-specific backup receipt | classification |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in matrix["staging_investigation"]:
        lines.append(
            f"| `{item['source_key']}` | `{item['documented_membership']}` | absent | {', '.join(item['cumulative_snapshot_hits']) or 'none'} | {', '.join(item['key_specific_backup_receipts']) or 'none'} | {item['classification']} |"
        )
    lines.extend(
        [
            "",
            "Evidence for each row: `VNREC/vnrec-authoritative-membership.json` documented window, `VNREC/inputs/staging-sourcekeys-full.json` cumulative snapshots, and `VNREC/inputs/backups-vn-listing.txt` backup listing. No four-key row is removed or downgraded.",
            "",
            "## Material-improvement delta vs pre-ratification output",
            "",
            "The delta remains on the stable balanced-partition identity so authority remapping is not misreported as graph improvement:",
            "",
            "| yield unit | before | after | delta |",
            "|---|---:|---:|---:|",
            f"| selected-word rows with usable edges | {delta['baseline_usable_selected_word_rows']:,} | {delta['after_usable_selected_word_rows']:,} | {delta['delta_usable_selected_word_rows']:+,} |",
            f"| cards completable by usable selected-word edges | {delta['baseline_cards_completable']:,} | {delta['after_cards_completable']:,} | {delta['delta_cards_completable']:+,} |",
            f"| entries with a usable edge | {delta['baseline_entries_with_usable_edge']:,} | {delta['after_entries_with_usable_edge']:,} | {delta['delta_entries_with_usable_edge']:+,} |",
            "",
            "This restates the material improvement from the pre-ratification output: the graph-yield delta is unchanged by the authority repair, while the final matrix no longer treats staging history as membership and no longer calls dual documented/staging rows historical conflicts.",
            "",
            "## Comparison artifact",
            "",
            "`vn-partition-proposal.v1` is retained under `comparison_artifacts` as versioned non-authoritative comparison data. It has `authoritative=false` and `planning_role=false`; it does not populate `vn_planning_assignment` and does not determine the primary or tail matrix.",
            "",
            "## Compounding Impact",
            "",
            f"EDGES contributes {matrix['compounding_impact']['usable_selected_word_rows']:,} usable selected-word routes, representing {matrix['compounding_impact']['usable_cards_after']:,} cards and {matrix['compounding_impact']['usable_entries_after']:,} entries after the crosswalk. The ledger preserves {matrix['compounding_impact']['indexed_total_appearances']:,} indexed appearances and exactly {matrix['compounding_impact']['proof_candidate_rows']} architecture-proof candidates. These are candidate routing facts, not source certification or public closure.",
            "",
            "## Honest limits and reproduction",
            "",
            "- CLOSED-FROZEN status is recorded evidence and was not live-reverified.",
            "- No live mutation, whitelist append, restart, deployment, public readback, source certification, push, or release is claimed.",
            "- Reproduce with `python tools/build_vn_readiness_v2.py` and explicit corpus, VNREC, staging-snapshot, receipt, EDGES, FAMWIDE, baseline, proof, and output paths. The committed `qamus/examples/vnmap-v2/` subset is the repo-self-contained harness gate.",
            "",
        ]
    )
    return "\n".join(lines)


def _build_view(view_kind, labels, entries, cards, ledger, assignment_by_key, entry_by_id, proof_by_view, family_counts_by_view):
    tranches = []
    for label in labels:
        rows = _rows_for_assignment(ledger, assignment_by_key, view_kind, label)
        entry_ids = _entry_ids_for_assignment(entries, entry_by_id, assignment_by_key, view_kind, label)
        debt_counter = Counter(row["debt_repair_family"] for row in rows if row.get("debt_repair_family"))
        evidence = []
        if label in FROZEN_LABELS:
            evidence = [FROZEN_SCOPE_CITATIONS[label]]
        elif label in PLANNING_LABELS:
            evidence = [
                "VNREC/inputs/14-VN-FLYWHEEL-AND-TRANCHE-PLAN.md:§4.1 window table",
                f"historical plan identifier={label}; source-key window={_plan_window_text(label)}",
            ]
        tranches.append(
            _metric_row(
                label,
                view_kind,
                rows,
                entry_ids,
                cards,
                proof_by_view[view_kind],
                family_counts_by_view[view_kind].get(label, 0),
                debt_counter,
                evidence,
            )
        )
    special = {
        label: _special_metric(label, view_kind, entries, cards, ledger, assignment_by_key, entry_by_id, proof_by_view[view_kind])
        for label in SPECIAL_LABELS
    }
    return {
        "schema": "vn-readiness-v2/view@2",
        "view_kind": view_kind,
        "tranches": tranches,
        "special_rows": special,
        "sidecar_only_special_rows": [STAGING_NAMESPACE],
        "totals": _matrix_totals(tranches, special),
        "candidate_only": True,
    }


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
    staging_snapshots=None,
    deployment_receipts=None,
):
    if not isinstance(entries, list) or not isinstance(whitelist, list) or not isinstance(appearances, list):
        raise ValueError("entries, whitelist, and appearances must be lists")
    entry_by_id = {}
    for entry in entries:
        entry_id = _clean(entry.get("id"))
        if not entry_id or entry_id in entry_by_id:
            raise ValueError(f"duplicate or missing entry id: {entry_id!r}")
        entry_by_id[entry_id] = _source_key(entry)

    context = _membership_context(membership, conflicts, staging_snapshots, deployment_receipts)
    assignment_by_key = {}
    for key in set(entry_by_id.values()):
        assignment_by_key[key] = _assignment_for_key(
            key,
            context["documented_by_key"],
            context["evidence"],
            context["doc_sets"],
            context["staging"],
            context["snapshots"],
            context["backup_by_key"],
            context["unresolved"],
        )
        assignment_by_key[key]["_primary_view"] = assignment_by_key[key].pop("_primary_view")
        assignment_by_key[key]["_tail_view"] = assignment_by_key[key].pop("_tail_view")
        assignment_by_key[key]["_comparison_label"] = assignment_by_key[key].pop("_comparison_label")

    base = build_ledger(entries, whitelist, appearances, family_rows)
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

    proof_by_entry_id = {}
    proof_names = sorted(_clean(row.get("name")) for row in proof_rows)
    if proof_names != sorted(PROOF_NAME_SET):
        raise ValueError(f"proof fixture must contain exactly {sorted(PROOF_NAME_SET)}")
    for proof in proof_rows:
        proof_by_entry_id[_clean(proof.get("entry_id"))] = _clean(proof.get("name"))

    ledger = []
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
        row.update(
            {
                key: value
                for key, value in assignment.items()
                if not key.startswith("_")
            }
        )
        row["architecture_proof_status"] = ARCHITECTURE_PROOF_STATUS if row.get("entry_id") in proof_by_entry_id else None
        for legacy_label_field in (
            "partition_label",
            "plan_table_label",
            "proposal_vn_tranche",
            "vn_tranche",
            "vn_tranche_claims",
            "vn_tranche_evidence",
            "evidence",
            "vn00_staging_member",
            "vn00_documented_window_member",
            "vn_authority_surface",
            "vn_tranche_partition_proposal",
            "vn_tranche_plan_table_proposal",
            "vn_matrix_view_authoritative_partition",
            "vn_matrix_view_plan_table",
        ):
            if legacy_label_field not in {
                "evidence",
            }:
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

    cards = _make_cards(entries)
    whitelist_by_loc = {
        _clean(row.get("loc")): _clean(row.get("entry_id"))
        for row in whitelist
        if _clean(row.get("loc")) and _clean(row.get("entry_id"))
    }
    proof_by_view = {
        "primary": _proofs_by_view(proof_rows, entry_by_id, assignment_by_key, "primary"),
        "tail": _proofs_by_view(proof_rows, entry_by_id, assignment_by_key, "tail"),
    }
    family_counts_by_view = {
        "primary": _family_view_counts(family_rows, entry_by_id, whitelist_by_loc, assignment_by_key, "primary"),
        "tail": _family_view_counts(family_rows, entry_by_id, whitelist_by_loc, assignment_by_key, "tail"),
    }

    primary_view = _build_view(
        "primary", PRIMARY_LABELS, entries, cards, ledger, assignment_by_key, entry_by_id, proof_by_view, family_counts_by_view
    )
    tail_view = _build_view(
        "tail", TAIL_LABELS, entries, cards, ledger, assignment_by_key, entry_by_id, proof_by_view, family_counts_by_view
    )
    status_counts = Counter(row.get("crosswalk_status") or "unavailable" for row in ledger)
    debt_counts = Counter(row["debt_repair_family"] for row in ledger if row.get("debt_repair_family"))
    delta = _material_delta(ledger, cards, baseline_matrix, entry_by_id)
    comparison = _comparison_artifact(ledger, entries, entry_by_id, assignment_by_key, cards)
    staging_set = context["staging"]
    documented_overlap = set().union(*(context["doc_sets"][label] for label in FROZEN_LABELS)) & staging_set
    staging_history_namespace = {
        "namespace": STAGING_NAMESPACE,
        "source_key_count": len(staging_set),
        "history_only_source_key_count": len(staging_set - documented_overlap),
        "overlap_authoritative_source_key_count": len(documented_overlap),
        "final_snapshot": _clean((membership.get("staging_metadata") or {}).get("final_snapshot")) or None,
        "matrix_accounting": "sidecar_only; deployment history is never membership",
        "evidence": [
            "VNREC/vnrec-authoritative-membership.json:staging_metadata.final_source_key_count=1302",
            "VNREC/inputs/staging-sourcekeys-full.json:complete cumulative per-snapshot source_key sets",
        ],
    }
    plan_baseline = {label: _plan_window_record(label) for label in PLANNING_LABELS}
    investigation = _staging_investigation(context["doc_sets"], context["snapshots"], context["backup_by_key"])
    all_usable = status_counts.get("deterministic_exact", 0) + status_counts.get("candidate", 0)
    proof_records = []
    for proof in sorted(proof_rows, key=lambda row: _clean(row.get("name"))):
        proof_records.append(
            {
                "name": _clean(proof.get("name")),
                "entry_id": _clean(proof.get("entry_id")),
                "source_key": _canonical_source_key(proof.get("source_key")),
                "target_occurrence": _clean(proof.get("target_occurrence") or proof.get("target_loc")),
                "status": ARCHITECTURE_PROOF_STATUS,
                "candidate_only": True,
                "evidence": [
                    _clean(proof.get("artifact")) or value
                    for value in (proof.get("evidence") or [])
                    if _clean(proof.get("artifact")) or _clean(value)
                ],
            }
        )
    matrix = {
        "schema": "vn-readiness-v2@1",
        "candidate_only": True,
        "assignment_mode": "vnrec_documented_authority_with_historical_plan_baseline",
        "proposal_ids": ["vn-partition-proposal.v1", "vn-plan-table.v1"],
        "planning_assignment_id": "vn-plan-table.v1",
        "denominators": {
            "D1_entries": base.metrics["denominators"]["D1_entries"],
            "D2_listed_quran_example_cards": base.metrics["denominators"]["D2_listed_quran_example_cards"],
            "D3_displayed_selected_word_rows": base.metrics["denominators"]["D3_displayed_selected_word_rows"],
            "D4_unique_canonical_occurrences": base.metrics["denominators"]["D4_unique_canonical_occurrences"],
            "D4_total_appearances": base.metrics["denominators"]["D4_total_appearances"],
            "D4_repeated_appearances": base.metrics["denominators"]["D4_repeated_appearances"],
        },
        "views": {"primary": primary_view, "documented_tail": tail_view},
        "scope_summary": {
            "documented_windows": {
                label: {
                    "source_key_range": FROZEN_SCOPE_TEXT[label],
                    "entries": len(context["doc_sets"][label]),
                    "status": "CLOSED-FROZEN (recorded evidence)",
                    "evidence": [FROZEN_SCOPE_CITATIONS[label]],
                }
                for label in FROZEN_LABELS
            },
            "staging_history_namespace": staging_history_namespace,
            "historical_conflict_source_keys": len(context["unresolved"]),
            "historical_conflict_keys": sorted(context["unresolved"]),
        },
        "planning_baseline": {
            "artifact_id": "vn-plan-table.v1",
            "authoritative": True,
            "planning_role": True,
            "identifier_policy": "preserve historical VN-03→VN-23 identifiers exactly",
            "tranches": plan_baseline,
            "evidence": ["VNREC/inputs/14-VN-FLYWHEEL-AND-TRANCHE-PLAN.md:§4.1 window table"],
        },
        "comparison_artifacts": {"vn-partition-proposal.v1": comparison},
        "staging_investigation": investigation,
        "crosswalk_status_counts": _counter_dict(status_counts),
        "usable_crosswalk_status_counts": {
            "deterministic_exact": status_counts.get("deterministic_exact", 0),
            "candidate": status_counts.get("candidate", 0),
        },
        "edge_summary_input": edge_summary,
        "debt_family_counts": _counter_dict(debt_counts),
        "family_rows": len(family_rows),
        "family_mapping": base.matrix.get("clitic_family_northstar")
        or {
            "family_rows": len(family_rows),
            "calibrated_verified_rows": sum(_clean(row.get("_fb1_verdict")) == "verified" for row in family_rows),
            "candidate_only": True,
            "source_certified_count": source_certified_ledger_count(),
        },
        "proofs": {
            "count": len(proof_rows),
            "names": proof_names,
            "status": ARCHITECTURE_PROOF_STATUS,
            "candidate_only": True,
            "source_certified_count": source_certified_ledger_count(),
            "rows": proof_records,
            "by_view": {
                "primary": {label: sorted(names) for label, names in proof_by_view["primary"].items()},
                "tail": {label: sorted(names) for label, names in proof_by_view["tail"].items()},
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
        "deployment_receipt_summary": {
            "receipt_count": len(context["backup_receipts"]),
            "key_specific_receipt_count": sum(len(value) for value in context["backup_by_key"].values()),
            "unscoped_receipts": [
                receipt for receipt in context["backup_receipts"] if not _backup_key(receipt)
            ],
            "evidence": ["VNREC/inputs/backups-vn-listing.txt:lines 1-5"],
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
    parser.add_argument("--staging-snapshots")
    parser.add_argument("--deployment-receipts")
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
        _read_json(args.staging_snapshots) if args.staging_snapshots else None,
        _read_receipts(args.deployment_receipts) if args.deployment_receipts else None,
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
