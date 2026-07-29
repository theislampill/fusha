#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the ratified VN readiness v2 ledger and matrix."""

from __future__ import annotations

from collections import Counter
import argparse
import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.build_vn_readiness_v2 import (
    ARCHITECTURE_PROOF_STATUS,
    CONTRACT_WINDOW_IDS,
    FROZEN_LABELS,
    PRIMARY_LABELS,
    PROOF_NAME_SET,
    PROPOSAL_LABELS,
    STAGING_NAMESPACE,
    TAIL_LABELS,
    USABLE_CROSSWALK_STATUSES,
    _canonical_source_key,
    _card_key,
    _label_for_key,
    PARTITION_RANGES,
    PLAN_RANGES,
    source_certified_ledger_count,
)
STATUS_VALUES = {"authoritative", "planning_only", "unassigned", "historical_conflict"}
VN_FIELDS = {
    "vn_tranche_authoritative",
    "vn_tranche_status",
    "vn_planning_assignment",
    "vn_staging_history_claims",
    "vn_deployment_receipts",
    "vn_assignment_provenance",
}
LEGACY_VN_FIELDS = {
    "vn_tranche",
    "vn_tranche_claims",
    "vn_tranche_evidence",
    "vn00_staging_member",
    "vn00_documented_window_member",
    "vn_authority_surface",
    "vn_tranche_partition_proposal",
    "vn_tranche_plan_table_proposal",
    "vn_matrix_view_authoritative_partition",
    "vn_matrix_view_plan_table",
    "partition_label",
    "plan_table_label",
    "proposal_vn_tranche",
}
PROVENANCE_FIELDS = tuple(VN_FIELDS - {"vn_assignment_provenance"})
SOURCE_KEY_RE = re.compile(r"^[vnp]\d+$", re.IGNORECASE)


class ValidationReport:
    def __init__(self, ok, errors):
        self.ok = bool(ok)
        self.errors = list(errors)


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            rows.append(value)
    return rows


def _int(value, label, errors):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"{label} must be a non-negative integer")
        return 0
    return value


def _signed_int(value, label, errors):
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{label} must be an integer")
        return 0
    return value


def _list_of_strings(value, label, errors, allow_empty=True):
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{label} must be a string list")
        return []
    if not allow_empty and not value:
        errors.append(f"{label} must not be empty")
    if value != sorted(set(value)):
        errors.append(f"{label} must be sorted and unique")
    return value


def _card_identity(row):
    address = row.get("display_local_address") or {}
    return _card_key(
        row.get("entry_id"),
        row.get("usage_index") or 1,
        address.get("entry_example_index") or 1,
    )


def _derived_view(row, view_kind):
    status = row.get("vn_tranche_status")
    if status == "historical_conflict":
        return "historical_conflict" if view_kind == "primary" else None
    authoritative = row.get("vn_tranche_authoritative")
    if authoritative:
        return authoritative if view_kind == "primary" else None
    planning = row.get("vn_planning_assignment")
    if view_kind == "primary":
        if planning in PRIMARY_LABELS:
            return planning
        if planning in TAIL_LABELS:
            return None
        return "unplanned_particles" if _clean_source_key(row.get("source_key")).startswith("p") else "unassigned"
    return planning if planning in TAIL_LABELS else None


def _clean_source_key(value):
    return _canonical_source_key(value) if value else ""


def _validate_provenance(row, prefix, errors):
    provenance = row.get("vn_assignment_provenance")
    if not isinstance(provenance, dict):
        errors.append(f"{prefix} vn_assignment_provenance must be an object")
        return
    for field in PROVENANCE_FIELDS:
        record = provenance.get(field)
        if not isinstance(record, dict):
            errors.append(f"{prefix} provenance missing {field}")
            continue
        if record.get("value") != row.get(field):
            errors.append(f"{prefix} provenance value does not match {field}")
        evidence = record.get("evidence")
        if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item for item in evidence):
            errors.append(f"{prefix} provenance for {field} must contain evidence citations")
    history = row.get("vn_staging_history_claims")
    history_record = provenance.get("vn_staging_history_claims")
    if history == [STAGING_NAMESPACE]:
        if not isinstance(history_record, dict) or history_record.get("namespace") != STAGING_NAMESPACE:
            errors.append(f"{prefix} staging provenance must name {STAGING_NAMESPACE}")
        if not isinstance(history_record.get("snapshots") if isinstance(history_record, dict) else None, list):
            errors.append(f"{prefix} staging provenance must list snapshot identifiers")
    elif history == [] and isinstance(history_record, dict) and history_record.get("value") != []:
        errors.append(f"{prefix} empty staging claims must have an empty provenance value")


def _validate_ledger(ledger, errors):
    if not isinstance(ledger, list):
        errors.append("ledger must be a list")
        return Counter(), set()
    selected_ids = set()
    status_counts = Counter()
    proof_rows = []
    for index, row in enumerate(ledger):
        prefix = f"ledger[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = sorted(VN_FIELDS - set(row))
        if missing:
            errors.append(f"{prefix} is missing ratified fields: {', '.join(missing)}")
        legacy = sorted(LEGACY_VN_FIELDS & set(row))
        if legacy:
            errors.append(f"{prefix} contains superseded VN fields: {', '.join(legacy)}")
        source_key = _clean_source_key(row.get("source_key"))
        if not SOURCE_KEY_RE.fullmatch(source_key):
            errors.append(f"{prefix} has invalid source_key")
        selected_id = row.get("selected_word_id")
        if not isinstance(selected_id, str) or not selected_id:
            errors.append(f"{prefix} selected_word_id must be a non-empty string")
        elif selected_id in selected_ids:
            errors.append(f"{prefix} selected_word_id is duplicated")
        selected_ids.add(selected_id)
        status = row.get("vn_tranche_status")
        status_counts[status] += 1
        if status not in STATUS_VALUES:
            errors.append(f"{prefix} has invalid vn_tranche_status {status!r}")
        auth = row.get("vn_tranche_authoritative")
        if auth is not None and auth not in FROZEN_LABELS:
            errors.append(f"{prefix} authoritative tranche must be VN-00, VN-01, or VN-02")
        planning = row.get("vn_planning_assignment")
        if planning is not None and planning not in PLAN_RANGES:
            errors.append(f"{prefix} planning assignment must be an exact VN-03→VN-23 identifier")
        history = row.get("vn_staging_history_claims")
        if history not in ([], [STAGING_NAMESPACE]):
            errors.append(f"{prefix} staging claims must be [] or [{STAGING_NAMESPACE!r}]")
        receipts = row.get("vn_deployment_receipts")
        if not isinstance(receipts, list) or not all(isinstance(item, str) and item for item in receipts):
            errors.append(f"{prefix} deployment receipts must be a string list")
        elif receipts != sorted(set(receipts)):
            errors.append(f"{prefix} deployment receipts must be sorted and unique")
        for receipt in receipts or []:
            if not receipt.startswith(("staging_snapshot:", "backup_listing:")):
                errors.append(f"{prefix} deployment receipt has an unknown namespace: {receipt}")
        if status == "authoritative" and (auth is None or planning is not None):
            errors.append(f"{prefix} authoritative status requires only documented membership")
        if status == "planning_only" and (auth is not None or planning not in PLAN_RANGES):
            errors.append(f"{prefix} planning_only status requires a plan-table assignment and no authority")
        if status == "unassigned" and (auth is not None or planning is not None):
            errors.append(f"{prefix} unassigned status cannot carry authority or planning")
        if status == "historical_conflict":
            provenance = row.get("vn_assignment_provenance") or {}
            unresolved = (provenance.get("vn_tranche_authoritative") or {}).get("unresolved_claims")
            if auth is not None or planning is not None or not isinstance(unresolved, list) or len(unresolved) < 2:
                errors.append(f"{prefix} historical_conflict must list each genuinely irreconcilable claim")
        if row.get("crosswalk_edge_usable") != (row.get("crosswalk_status") in USABLE_CROSSWALK_STATUSES):
            errors.append(f"{prefix} crosswalk_edge_usable disagrees with crosswalk_status")
        if row.get("architecture_proof_status") not in (None, ARCHITECTURE_PROOF_STATUS):
            errors.append(f"{prefix} has an invalid architecture proof status")
        if row.get("architecture_proof_status") == ARCHITECTURE_PROOF_STATUS:
            proof_rows.append(row)
        _validate_provenance(row, prefix, errors)
        if "blocker" in row:
            errors.append(f"{prefix} contains forbidden blocker field")
    return status_counts, selected_ids, proof_rows


def _metric_counts(rows):
    statuses = Counter(row.get("crosswalk_status") or "unavailable" for row in rows)
    return {
        "entries": len({row.get("entry_id") for row in rows}),
        "cards": len({_card_identity(row) for row in rows}),
        "displayed_selected_words": len(rows),
        "unique_canonical_occurrences": len({row.get("occurrence_id") for row in rows if row.get("occurrence_id")}),
        "crosswalk_status_counts": dict(sorted(statuses.items())),
        "graph_complete_rows": sum(statuses.get(status, 0) for status in USABLE_CROSSWALK_STATUSES),
        "graph_complete_deterministic_exact_rows": statuses.get("deterministic_exact", 0),
        "graph_complete_candidate_rows": statuses.get("candidate", 0),
        "source_certified_rows": source_certified_ledger_count(),
    }


def _validate_metric_row(row, expected_rows, label, errors):
    if not isinstance(row, dict):
        errors.append(f"matrix row {label} must be an object")
        return
    actual = _metric_counts(expected_rows)
    for field in (
        "entries",
        "cards",
        "displayed_selected_words",
        "unique_canonical_occurrences",
        "graph_complete_rows",
        "graph_complete_deterministic_exact_rows",
        "graph_complete_candidate_rows",
        "source_certified_rows",
    ):
        value = _int(row.get(field), f"matrix {label}.{field}", errors)
        if field == "entries":
            minimum = actual[field]
            if value < minimum:
                errors.append(f"matrix {label}.{field} is below ledger coverage ({value} < {minimum})")
        elif field == "cards":
            minimum = actual[field]
            if value < minimum:
                errors.append(f"matrix {label}.{field} is below ledger coverage ({value} < {minimum})")
        elif value != actual[field]:
            errors.append(f"matrix {label}.{field} does not match ledger ({value} != {actual[field]})")
    if row.get("crosswalk_status_counts") != actual["crosswalk_status_counts"]:
        errors.append(f"matrix {label}.crosswalk_status_counts does not match ledger")
    if row.get("graph_complete_rows") != row.get("graph_complete_deterministic_exact_rows", 0) + row.get("graph_complete_candidate_rows", 0):
        errors.append(f"matrix {label}.graph_complete_rows does not equal deterministic/candidate split")
    if row.get("source_certified_rows") != source_certified_ledger_count():
        errors.append(
            f"matrix {label}.source_certified_rows must equal the typed-fact "
            f"certification ledger count ({source_certified_ledger_count()})"
        )
    proof_names = row.get("fully_rich_generated_proof_names")
    if not isinstance(proof_names, list) or proof_names != sorted(set(proof_names)) or not set(proof_names).issubset(PROOF_NAME_SET):
        errors.append(f"matrix {label}.fully_rich_generated_proof_names is invalid")
    if row.get("fully_rich_generated_rows") != len(proof_names or []):
        errors.append(f"matrix {label}.fully_rich_generated_rows does not match proof names")
    if row.get("candidate_only") is not True:
        errors.append(f"matrix {label}.candidate_only must be true")
    for field in ("debt_rows", "owner_scholar_rows", "source_crosswalk_repair_rows"):
        _int(row.get(field), f"matrix {label}.{field}", errors)
    if label in FROZEN_LABELS:
        if row.get("scope_status") != "CLOSED-FROZEN (recorded evidence)":
            errors.append(f"matrix {label} must retain recorded CLOSED-FROZEN status")
        if "not live-reverified" not in row.get("already_live_noop_state", ""):
            errors.append(f"matrix {label} must state that live status was not reverified")


def _view_rows(ledger, view_kind, label):
    return [row for row in ledger if _derived_view(row, view_kind) == label]


def _validate_view(ledger, matrix, view_kind, labels, errors):
    matrix_view_key = "documented_tail" if view_kind == "tail" else view_kind
    view = matrix.get("views", {}).get(matrix_view_key)
    if not isinstance(view, dict):
        errors.append(f"matrix view {view_kind} must be an object")
        return
    tranches = view.get("tranches")
    if not isinstance(tranches, list) or [row.get("label") for row in tranches if isinstance(row, dict)] != labels:
        errors.append(f"matrix view {view_kind} has the wrong ordered tranche labels")
        tranches = []
    special = view.get("special_rows")
    if not isinstance(special, dict) or set(special) != {
        "vn00_staging_history",
        "historical_conflict",
        "unplanned_particles",
        "unassigned",
    }:
        errors.append(f"matrix view {view_kind} has the wrong special rows")
        special = {}
    for label, row in zip(labels, tranches):
        _validate_metric_row(row, _view_rows(ledger, view_kind, label), label, errors)
    for label in special:
        if label == "vn00_staging_history":
            rows = [row for row in ledger if row.get("vn_staging_history_claims")]
        elif label == "historical_conflict":
            rows = _view_rows(ledger, "primary", label)
        else:
            rows = _view_rows(ledger, view_kind, label)
        _validate_metric_row(special[label], rows, f"{view_kind}.{label}", errors)
        if label == "vn00_staging_history":
            if special[label].get("sidecar_only") is not True:
                errors.append(f"{view_kind}.vn00_staging_history must be sidecar_only")
            if special[label].get("namespace") != STAGING_NAMESPACE:
                errors.append(f"{view_kind}.vn00_staging_history has the wrong namespace")
            if special[label].get("source_key_count") != len({_clean_source_key(row.get("source_key")) for row in rows}):
                errors.append(f"{view_kind}.vn00_staging_history source_key_count is wrong")
    included = list(tranches)
    included.extend(special[label] for label in ("historical_conflict", "unplanned_particles", "unassigned"))
    totals = view.get("totals")
    if not isinstance(totals, dict):
        errors.append(f"matrix view {view_kind}.totals must be an object")
    else:
        for field in ("entries", "cards", "displayed_selected_words", "unique_canonical_occurrences"):
            expected = sum(_int(row.get(field), f"{view_kind}.{field}", errors) for row in included if isinstance(row, dict))
            if totals.get(field) != expected:
                errors.append(f"matrix view {view_kind}.totals.{field} does not equal included rows")
        expected_rows = [row for row in ledger if _derived_view(row, view_kind) in set(labels)]
        if view_kind == "primary":
            expected_rows.extend(_view_rows(ledger, "primary", label) for label in ("historical_conflict", "unplanned_particles", "unassigned"))
            expected_rows = [row for group in expected_rows for row in (group if isinstance(group, list) else [group])]
        expected = _metric_counts(expected_rows)
        if totals.get("displayed_selected_words") != expected["displayed_selected_words"]:
            errors.append(f"matrix view {view_kind} totals do not cover its ledger view")
    if view.get("candidate_only") is not True:
        errors.append(f"matrix view {view_kind}.candidate_only must be true")


def _validate_planning_and_comparison(matrix, errors):
    planning = matrix.get("planning_baseline")
    if not isinstance(planning, dict) or planning.get("artifact_id") != "vn-plan-table.v1" or planning.get("authoritative") is not True or planning.get("planning_role") is not True:
        errors.append("planning_baseline must be the authoritative vn-plan-table.v1 artifact")
    else:
        tranches = planning.get("tranches") or {}
        for label in (f"VN-{index:02d}" for index in range(3, 24)):
            record = tranches.get(label)
            if not isinstance(record, dict) or record.get("identifier") != label or record.get("authoritative") is not True:
                errors.append(f"planning baseline is missing exact identifier {label}")
    comparison = (matrix.get("comparison_artifacts") or {}).get("vn-partition-proposal.v1")
    if not isinstance(comparison, dict) or comparison.get("artifact_id") != "vn-partition-proposal.v1":
        errors.append("balanced partition comparison artifact is missing")
    else:
        if comparison.get("authoritative") is not False or comparison.get("planning_role") is not False:
            errors.append("balanced partition must be non-authoritative and have no planning role")
        comparison_labels = [
            row.get("label") for row in comparison.get("tranches") or [] if isinstance(row, dict)
        ]
        for label in comparison_labels:
            if label in CONTRACT_WINDOW_IDS:
                errors.append(
                    f"comparison artifact: proposal-namespace tranche label {label!r} collides "
                    "with a contract window id (VN-00..VN-23); proposal labels must use the "
                    "VNPROP-xx namespace"
                )
        if comparison_labels != list(PROPOSAL_LABELS):
            errors.append("comparison artifact must carry the ordered VNPROP-00..VNPROP-20 labels")


def _validate_delta(ledger, matrix, errors):
    delta = matrix.get("material_improvement_delta")
    if not isinstance(delta, dict):
        errors.append("material_improvement_delta must be an object")
        return
    rows = delta.get("rows")
    if not isinstance(rows, list) or [row.get("label") for row in rows if isinstance(row, dict)] != list(PROPOSAL_LABELS):
        errors.append("material improvement delta must contain VNPROP-00 through VNPROP-20 rows")
        rows = []
    for row in rows:
        if isinstance(row, dict) and row.get("label") in CONTRACT_WINDOW_IDS:
            errors.append(
                f"material delta: proposal-namespace label {row.get('label')!r} collides with a "
                "contract window id (VN-00..VN-23)"
            )
    for row in rows:
        label = row.get("label")
        for field in (
            "baseline_selected_word_rows",
            "baseline_usable_selected_word_rows",
            "after_deterministic_exact_rows",
            "after_candidate_rows",
            "after_usable_selected_word_rows",
            "delta_usable_selected_word_rows",
            "baseline_cards_completable",
            "after_cards_completable",
            "delta_cards_completable",
            "baseline_entries_with_usable_edge",
            "after_entries_with_usable_edge",
            "delta_entries_with_usable_edge",
        ):
            (_signed_int if field.startswith("delta_") else _int)(row.get(field), f"delta {label}.{field}", errors)
        partition_rows = [value for value in ledger if _label_for_key(value.get("source_key"), PARTITION_RANGES) == label]
        det = sum(value.get("crosswalk_status") == "deterministic_exact" for value in partition_rows)
        candidate = sum(value.get("crosswalk_status") == "candidate" for value in partition_rows)
        if row.get("after_deterministic_exact_rows") != det or row.get("after_candidate_rows") != candidate:
            errors.append(f"delta {label} after crosswalk split does not match ledger")
        if row.get("after_usable_selected_word_rows") != det + candidate:
            errors.append(f"delta {label} usable rows do not equal status split")
        if row.get("delta_usable_selected_word_rows") != row.get("after_usable_selected_word_rows") - row.get("baseline_usable_selected_word_rows"):
            errors.append(f"delta {label} usable-row arithmetic is wrong")
    totals = delta.get("totals") or {}
    for field in (
        "baseline_usable_selected_word_rows",
        "after_usable_selected_word_rows",
        "delta_usable_selected_word_rows",
        "baseline_cards_completable",
        "after_cards_completable",
        "delta_cards_completable",
        "baseline_entries_with_usable_edge",
        "after_entries_with_usable_edge",
        "delta_entries_with_usable_edge",
    ):
        if totals.get(field) != sum(row.get(field, 0) for row in rows):
            errors.append(f"delta totals.{field} does not sum tranche rows")
    if delta.get("proof_candidate_rows_added_separately") != 3:
        errors.append("material delta must keep three proof rows separate")


def validate_artifacts(ledger, matrix):
    errors = []
    if not isinstance(matrix, dict):
        return ValidationReport(False, ["matrix must be a JSON object"])
    if matrix.get("schema") != "vn-readiness-v2@1":
        errors.append("matrix schema is not vn-readiness-v2@1")
    if matrix.get("candidate_only") is not True:
        errors.append("matrix candidate_only must be true")
    if matrix.get("assignment_mode") != "vnrec_documented_authority_with_historical_plan_baseline":
        errors.append("matrix assignment mode does not preserve ratified authority")
    if matrix.get("proposal_ids") != ["vn-partition-proposal.v1", "vn-plan-table.v1"]:
        errors.append("matrix proposal_ids must retain both versioned artifacts")
    _status_counts, selected_ids, proof_rows = _validate_ledger(ledger, errors)
    if not ledger:
        errors.append("ledger must contain selected-word rows")
    summary = matrix.get("denominators")
    if not isinstance(summary, dict):
        errors.append("matrix denominators must be an object")
        summary = {}
    d3 = _int(summary.get("D3_displayed_selected_word_rows"), "D3", errors)
    if d3 != len(ledger):
        errors.append("D3 displayed selected-word rows must equal ledger length")
    d4_unique = _int(summary.get("D4_unique_canonical_occurrences"), "D4 unique", errors)
    d4_total = _int(summary.get("D4_total_appearances"), "D4 total", errors)
    d4_repeated = _int(summary.get("D4_repeated_appearances"), "D4 repeated", errors)
    if d4_unique + d4_repeated != d4_total:
        errors.append("D4 unique occurrences plus repeated appearances must equal total appearances")
    crosswalk_status_counts = Counter(row.get("crosswalk_status") or "unavailable" for row in ledger)
    if matrix.get("crosswalk_status_counts") != dict(sorted(crosswalk_status_counts.items())):
        errors.append("matrix.crosswalk_status_counts does not match ledger")
    expected_usable = {status: crosswalk_status_counts.get(status, 0) for status in USABLE_CROSSWALK_STATUSES}
    if matrix.get("usable_crosswalk_status_counts") != expected_usable:
        errors.append("matrix.usable_crosswalk_status_counts does not match ledger")
    edge_input = matrix.get("edge_summary_input")
    if not isinstance(edge_input, dict) or edge_input.get("candidate_only") is not True:
        errors.append("edge_summary_input must preserve candidate_only")
    else:
        metrics = edge_input.get("metrics") or {}
        if metrics.get("selected_word_rows_total") != len(ledger):
            errors.append("edge summary selected-word denominator does not equal ledger length")
        if metrics.get("selected_word_rows_with_usable_lexeme_or_form_edge") != sum(expected_usable.values()):
            errors.append("edge summary usable-row count does not equal ledger")
    proofs = matrix.get("proofs")
    if not isinstance(proofs, dict) or proofs.get("candidate_only") is not True or proofs.get("status") != ARCHITECTURE_PROOF_STATUS:
        errors.append("proofs must be candidate-only architecture proof candidates")
    else:
        if proofs.get("count") != 3 or proofs.get("names") != sorted(PROOF_NAME_SET):
            errors.append("proofs must name exactly the three architecture proof candidates")
        if proofs.get("source_certified_count") != source_certified_ledger_count():
            errors.append(
                "proofs source_certified_count must equal the typed-fact "
                f"certification ledger count ({source_certified_ledger_count()})"
            )
        if not isinstance(proofs.get("rows"), list) or len(proofs["rows"]) != 3 or any(row.get("status") != ARCHITECTURE_PROOF_STATUS for row in proofs["rows"]):
            errors.append("proof rows must each be architecture_proof_candidate")
    expected_proof_entry_ids = {
        row.get("entry_id")
        for row in (proofs.get("rows") if isinstance(proofs, dict) else [])
        if isinstance(row, dict)
    }
    actual_proof_entry_ids = {row.get("entry_id") for row in proof_rows}
    if actual_proof_entry_ids != expected_proof_entry_ids:
        errors.append("ledger architecture proof statuses must cover exactly the three proof entry identities")
    compounding = matrix.get("compounding_impact")
    if not isinstance(compounding, dict) or compounding.get("candidate_only") is not True or compounding.get("proof_candidate_rows") != 3:
        errors.append("compounding_impact must remain candidate-only and count three proof rows")
    _validate_view(ledger, matrix, "primary", list(PRIMARY_LABELS), errors)
    _validate_view(ledger, matrix, "tail", list(TAIL_LABELS), errors)
    _validate_planning_and_comparison(matrix, errors)
    _validate_delta(ledger, matrix, errors)
    staging = matrix.get("scope_summary", {}).get("staging_history_namespace")
    if not isinstance(staging, dict) or staging.get("namespace") != STAGING_NAMESPACE:
        errors.append("scope_summary must name the vn00_staging_history namespace")
    else:
        actual_staging = len({row.get("source_key") for row in ledger if row.get("vn_staging_history_claims")})
        if staging.get("source_key_count", 0) < actual_staging:
            errors.append("staging namespace source_key_count is below ledger coverage")
    if not isinstance(matrix.get("staging_investigation"), list):
        errors.append("four-key staging investigation must be present")
    return ValidationReport(ok=not errors, errors=errors)


def _render(report):
    if report.ok:
        return "VN READINESS V2 VALIDATION PASS"
    return "\n".join(["VN READINESS V2 VALIDATION FAIL", *[f"FAIL {error}" for error in report.errors]])


def self_test():
    fixture_root = os.path.join(ROOT, "qamus", "examples", "vnmap-v2")
    ledger = _read_jsonl(os.path.join(fixture_root, "vn-ledger-v2.fixture.jsonl"))
    matrix = _read_json(os.path.join(fixture_root, "vn-readiness-v2.fixture.json"))
    passing = validate_artifacts(ledger, matrix)
    if not passing.ok:
        print(_render(passing))
        return 1
    print("ok   ratified fixture validates")

    mutated = copy.deepcopy(ledger)
    dual_claim = next(row for row in mutated if row.get("source_key") == "v048")
    dual_claim["vn_tranche_authoritative"] = "VN-00"
    failed = validate_artifacts(mutated, matrix)
    if failed.ok or not any("provenance" in error or "documented" in error for error in failed.errors):
        print("FAIL staging override mutation was not rejected")
        return 1
    print("ok   staging override mutation rejected")

    mutated = copy.deepcopy(ledger)
    staged = next(row for row in mutated if row.get("source_key") == "v048")
    staged["vn_staging_history_claims"] = ["VN-00"]
    failed = validate_artifacts(mutated, matrix)
    if failed.ok or not any("staging claims" in error for error in failed.errors):
        print("FAIL staging namespace mutation was not rejected")
        return 1
    print("ok   staging namespace mutation rejected")

    mutated_matrix = copy.deepcopy(matrix)
    tranche = next(row for row in mutated_matrix["views"]["primary"]["tranches"] if row["label"] == "VN-03")
    tranche["graph_complete_rows"] += 1
    failed = validate_artifacts(ledger, mutated_matrix)
    if failed.ok or not any("graph_complete_rows" in error for error in failed.errors):
        print("FAIL v2 graph mutation was not rejected")
        return 1
    print("ok   graph mutation rejected")

    # Namespace-collision hazard (red-first): a comparison tranche relabelled
    # with a bare contract window id (pre-ruling "VN-03") must FAIL.
    mutated_matrix = copy.deepcopy(matrix)
    comparison = mutated_matrix["comparison_artifacts"]["vn-partition-proposal.v1"]
    comparison["tranches"][3]["label"] = "VN-03"
    failed = validate_artifacts(ledger, mutated_matrix)
    if failed.ok or not any("collides" in error for error in failed.errors):
        print("FAIL v2 proposal/contract namespace collision was not rejected")
        return 1
    print("ok   v2 proposal/contract namespace collision rejected")
    print("VN READINESS V2 SELF-TEST PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger")
    parser.add_argument("--matrix")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.ledger or not args.matrix:
        parser.error("provide --ledger and --matrix, or use --self-test")
    report = validate_artifacts(_read_jsonl(args.ledger), _read_json(args.matrix))
    print(_render(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
