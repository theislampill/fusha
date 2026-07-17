#!/usr/bin/env python3
"""Validate the candidate-only VN readiness v2 matrix and ledger offline."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import os
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.build_vn_readiness_v2 import (  # noqa: E402
    FROZEN_LABELS,
    PARTITION_RANGES,
    PLAN_EXTRA_LABELS,
    PRIMARY_LABELS,
    PROOF_NAME_SET,
    SPECIAL_LABELS,
    USABLE_CROSSWALK_STATUSES,
    _card_key,
    _label_for_key,
)


STATUSES = {"authoritative", "historical_conflict", "proposed", "unassigned"}
VIEW_KINDS = ("authoritative_partition", "plan_table")
PROPOSAL_PREFIXES = {
    "vn_tranche_partition_proposal": "proposed:vn-partition-proposal.v1:",
    "vn_tranche_plan_table_proposal": "proposed:vn-plan-table.v1:",
}
MATRIX_METRIC_FIELDS = (
    "entries",
    "cards",
    "displayed_selected_words",
    "unique_canonical_occurrences",
    "graph_complete_rows",
    "graph_complete_deterministic_exact_rows",
    "graph_complete_candidate_rows",
    "source_certified_rows",
    "fully_rich_generated_rows",
    "already_live_noop_entries",
    "already_live_noop_cards",
    "already_live_noop_selected_word_rows",
    "historical_conflict_entries",
    "historical_conflict_selected_word_rows",
    "authoritative_assigned_entries",
    "debt_rows",
    "owner_scholar_rows",
    "owner_policy_rows",
    "function_word_rows",
    "duplicate_surface_rows",
    "source_crosswalk_repair_rows",
    "calibrated_family_candidate_rows",
)


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str]


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _int(value, label, errors):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"{label} must be a non-negative integer")
        return 0
    return value


def _signed_int(value, label, errors):
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{label} must be an integer")
        return 0
    return value


def _counter(value, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return Counter()
    result = Counter()
    for key, count in value.items():
        if not isinstance(key, str):
            errors.append(f"{label} has a non-string key")
            continue
        result[key] = _int(count, f"{label}.{key}", errors)
    return result


def _proposal_is_valid(value, prefix):
    return isinstance(value, str) and value.startswith(prefix) and bool(value[len(prefix) :])


def _card_identity(row):
    address = row.get("display_local_address") or {}
    return _card_key(
        row.get("entry_id"),
        row.get("usage_index") or 1,
        address.get("entry_example_index") or 1,
    )


def _validate_ledger(ledger, errors):
    if not isinstance(ledger, list):
        errors.append("ledger must be a JSON array")
        return Counter(), set()
    seen_ids = set()
    status_counts = Counter()
    for index, row in enumerate(ledger, 1):
        prefix = f"ledger row {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if row.get("record_type") != "selected_word_readiness_row":
            errors.append(f"{prefix} record_type is not selected_word_readiness_row")
        for field in (
            "entry_id",
            "source_key",
            "selected_word_id",
            "vn_tranche",
            "vn_tranche_status",
            "vn_tranche_claims",
            "vn_tranche_evidence",
            "vn_tranche_partition_proposal",
            "vn_tranche_plan_table_proposal",
            "vn_matrix_view_authoritative_partition",
            "vn_matrix_view_plan_table",
            "vn00_staging_member",
            "vn00_documented_window_member",
        ):
            if field not in row:
                errors.append(f"{prefix} missing {field}")
        selected_id = row.get("selected_word_id")
        if not isinstance(selected_id, str) or not selected_id:
            errors.append(f"{prefix} selected_word_id is empty")
        elif selected_id in seen_ids:
            errors.append(f"{prefix} duplicates selected_word_id {selected_id}")
        else:
            seen_ids.add(selected_id)

        status = row.get("vn_tranche_status")
        if status not in STATUSES:
            errors.append(f"{prefix} has invalid vn_tranche_status {status!r}")
            continue
        status_counts[status] += 1

        claims = row.get("vn_tranche_claims")
        if not isinstance(claims, list) or any(not isinstance(value, str) for value in claims):
            errors.append(f"{prefix} vn_tranche_claims must be a string list")
            claims = []
        if claims != sorted(set(claims)):
            errors.append(f"{prefix} vn_tranche_claims must be sorted and unique")
        evidence = row.get("vn_tranche_evidence")
        if not isinstance(evidence, list) or any(not isinstance(value, str) for value in evidence):
            errors.append(f"{prefix} vn_tranche_evidence must be a string list")

        scalar = row.get("vn_tranche")
        partition_proposal = row.get("vn_tranche_partition_proposal")
        plan_proposal = row.get("vn_tranche_plan_table_proposal")
        if status == "historical_conflict":
            if scalar is not None:
                errors.append(f"{prefix} historical conflict must keep vn_tranche null")
            if len(claims) < 2:
                errors.append(f"{prefix} historical conflict must preserve multiple claims")
            if partition_proposal is not None or plan_proposal is not None:
                errors.append(f"{prefix} historical conflict cannot emit a proposal scalar")
        elif status == "authoritative":
            if scalar not in FROZEN_LABELS:
                errors.append(f"{prefix} authoritative scalar is not VN-00/VN-01/VN-02")
            if claims != [scalar]:
                errors.append(f"{prefix} authoritative claims do not match scalar")
            if partition_proposal is not None or plan_proposal is not None:
                errors.append(f"{prefix} authoritative row cannot emit a proposal")
        elif status == "proposed":
            if not _proposal_is_valid(scalar, "proposed:"):
                errors.append(f"{prefix} proposed row does not use a proposed: scalar")
            if claims:
                errors.append(f"{prefix} proposed row must have no historical claims")
            if partition_proposal != scalar:
                errors.append(f"{prefix} partition proposal does not equal proposed scalar")
            if plan_proposal is not None and not _proposal_is_valid(plan_proposal, PROPOSAL_PREFIXES["vn_tranche_plan_table_proposal"]):
                errors.append(f"{prefix} plan-table proposal has the wrong namespace")
        else:
            if scalar is not None or claims or partition_proposal is not None or plan_proposal is not None:
                errors.append(f"{prefix} unassigned row must have null scalar/proposals and no claims")

        for field, proposal_prefix in PROPOSAL_PREFIXES.items():
            value = row.get(field)
            if value is not None and not _proposal_is_valid(value, proposal_prefix):
                errors.append(f"{prefix} {field} has the wrong proposal namespace")
        if not isinstance(row.get("vn00_staging_member"), bool):
            errors.append(f"{prefix} vn00_staging_member must be boolean")
        if not isinstance(row.get("vn00_documented_window_member"), bool):
            errors.append(f"{prefix} vn00_documented_window_member must be boolean")
        if row.get("vn_authority_surface") not in {
            "documented_window",
            "deployed_staging",
            "historical_multi_claim",
            "none",
        }:
            errors.append(f"{prefix} has an invalid vn_authority_surface")
        if row.get("vn_matrix_view_authoritative_partition") not in set(PRIMARY_LABELS) | set(SPECIAL_LABELS):
            errors.append(f"{prefix} has an invalid authoritative/partition view label")
        if row.get("vn_matrix_view_plan_table") not in set(PRIMARY_LABELS) | set(PLAN_EXTRA_LABELS) | set(SPECIAL_LABELS):
            errors.append(f"{prefix} has an invalid plan-table view label")

        crosswalk_status = row.get("crosswalk_status")
        if crosswalk_status is not None and not isinstance(crosswalk_status, str):
            errors.append(f"{prefix} crosswalk_status must be string or null")
        if row.get("crosswalk_edge_usable") != (crosswalk_status in USABLE_CROSSWALK_STATUSES):
            errors.append(f"{prefix} crosswalk_edge_usable disagrees with crosswalk_status")
        if not isinstance(row.get("crosswalk_edge_ids"), list):
            errors.append(f"{prefix} crosswalk_edge_ids must be a list")
        if row.get("debt_repair_family") is not None and not isinstance(row.get("debt_repair_family"), str):
            errors.append(f"{prefix} debt_repair_family must be string or null")
    return status_counts, seen_ids


def _validate_metric_row(row, label, rows, errors, special=False):
    prefix = f"matrix {label}"
    if not isinstance(row, dict):
        errors.append(f"{prefix} must be an object")
        return
    if row.get("label") != label:
        errors.append(f"{prefix} label mismatch")
    metric_fields = MATRIX_METRIC_FIELDS if not special else tuple(
        field for field in MATRIX_METRIC_FIELDS if field != "calibrated_family_candidate_rows"
    )
    for field in metric_fields:
        _int(row.get(field), f"{prefix}.{field}", errors)
    if row.get("candidate_only") is not True:
        errors.append(f"{prefix}.candidate_only must be true")
    if row.get("source_certified_rows") != 0:
        errors.append(f"{prefix}.source_certified_rows must remain zero")
    expected_statuses = Counter(value.get("crosswalk_status") or "unavailable" for value in rows)
    actual_statuses = _counter(row.get("crosswalk_status_counts"), f"{prefix}.crosswalk_status_counts", errors)
    if actual_statuses != expected_statuses:
        errors.append(f"{prefix}.crosswalk_status_counts does not match ledger rows")
    expected_graph = sum(expected_statuses.get(status, 0) for status in USABLE_CROSSWALK_STATUSES)
    if row.get("graph_complete_rows") != expected_graph:
        errors.append(f"{prefix}.graph_complete_rows does not match usable ledger rows")
    if row.get("graph_complete_deterministic_exact_rows") != expected_statuses.get("deterministic_exact", 0):
        errors.append(f"{prefix}.graph_complete_deterministic_exact_rows does not match ledger rows")
    if row.get("graph_complete_candidate_rows") != expected_statuses.get("candidate", 0):
        errors.append(f"{prefix}.graph_complete_candidate_rows does not match ledger rows")
    if row.get("displayed_selected_words") != len(rows):
        errors.append(f"{prefix}.displayed_selected_words does not match ledger rows")
    entry_ids = {value.get("entry_id") for value in rows}
    card_ids = {_card_identity(value) for value in rows}
    occurrences = {value.get("occurrence_id") for value in rows if value.get("occurrence_id")}
    debt_counts = Counter(value.get("debt_repair_family") for value in rows if value.get("debt_repair_family"))
    actual_debt_counts = _counter(row.get("debt_family_counts"), f"{prefix}.debt_family_counts", errors)
    if actual_debt_counts != debt_counts:
        errors.append(f"{prefix}.debt_family_counts does not match ledger rows")
    if row.get("debt_rows") != sum(debt_counts.values()):
        errors.append(f"{prefix}.debt_rows does not match debt family counts")
    if row.get("entries", 0) < len(entry_ids):
        errors.append(f"{prefix}.entries is below the ledger entry lower bound")
    if row.get("cards", 0) < len(card_ids):
        errors.append(f"{prefix}.cards is below the ledger card lower bound")
    if row.get("unique_canonical_occurrences") != len(occurrences):
        errors.append(f"{prefix}.unique_canonical_occurrences does not match ledger rows")
    proof_names = row.get("fully_rich_generated_proof_names")
    if not isinstance(proof_names, list) or proof_names != sorted(set(proof_names)):
        errors.append(f"{prefix}.fully_rich_generated_proof_names must be sorted and unique")
        proof_names = []
    if not set(proof_names).issubset(PROOF_NAME_SET):
        errors.append(f"{prefix} contains an unknown fully-rich proof name")
    if row.get("fully_rich_generated_rows") != len(proof_names):
        errors.append(f"{prefix}.fully_rich_generated_rows does not match proof names")
    if special and label == "HISTORICAL_CONFLICT":
        if row.get("historical_conflict_entries") != len(entry_ids):
            errors.append(f"{prefix}.historical_conflict_entries does not match conflict rows")
        if row.get("historical_conflict_selected_word_rows") != len(rows):
            errors.append(f"{prefix}.historical_conflict_selected_word_rows does not match conflict rows")


def _view_rows(ledger, view_kind, label):
    if label == "HISTORICAL_CONFLICT":
        return [row for row in ledger if row.get("vn_tranche_status") == "historical_conflict"]
    return [row for row in ledger if row.get(f"vn_matrix_view_{view_kind}") == label]


def _validate_views(ledger, matrix, errors):
    views = matrix.get("views")
    if not isinstance(views, dict) or set(views) != set(VIEW_KINDS):
        errors.append("matrix views must contain authoritative_partition and plan_table")
        return
    for view_kind in VIEW_KINDS:
        view = views.get(view_kind)
        if not isinstance(view, dict):
            errors.append(f"matrix view {view_kind} must be an object")
            continue
        labels = list(PRIMARY_LABELS) + (list(PLAN_EXTRA_LABELS) if view_kind == "plan_table" else [])
        tranches = view.get("tranches")
        if not isinstance(tranches, list) or [row.get("label") for row in tranches if isinstance(row, dict)] != labels:
            errors.append(f"matrix view {view_kind} has the wrong ordered tranche labels")
            tranches = []
        special_rows = view.get("special_rows")
        if not isinstance(special_rows, dict) or set(special_rows) != set(SPECIAL_LABELS):
            errors.append(f"matrix view {view_kind} has the wrong special rows")
            special_rows = {}
        for label, row in zip(labels, tranches):
            _validate_metric_row(row, label, _view_rows(ledger, view_kind, label), errors)
            if label in FROZEN_LABELS:
                if row.get("scope_status") != "CLOSED-FROZEN (recorded evidence)":
                    errors.append(f"matrix {label} must retain recorded CLOSED-FROZEN status")
                if not any("CLOSED-FROZEN" in value for value in row.get("scope_evidence") or []):
                    errors.append(f"matrix {label} is missing CLOSED-FROZEN evidence")
                if "not live-reverified" not in row.get("already_live_noop_state", ""):
                    errors.append(f"matrix {label} must state that live status was not reverified")
        for label in SPECIAL_LABELS:
            row = special_rows.get(label)
            _validate_metric_row(row, label, _view_rows(ledger, view_kind, label), errors, special=True)

        included = [row for row in tranches]
        included.extend(special_rows[label] for label in ("VN-00-STAGING", "UNPLANNED_PARTICLES") if label in special_rows)
        totals = view.get("totals")
        if not isinstance(totals, dict):
            errors.append(f"matrix view {view_kind}.totals must be an object")
            continue
        for field in ("entries", "cards", "displayed_selected_words", "unique_canonical_occurrences"):
            expected = sum(_int(row.get(field), f"{view_kind}.{field}", errors) for row in included if isinstance(row, dict))
            if totals.get(field) != expected:
                errors.append(f"matrix view {view_kind}.totals.{field} does not equal included rows")
        if totals.get("displayed_selected_words") != len(ledger):
            errors.append(f"matrix view {view_kind}.totals.displayed_selected_words does not cover the ledger")
        if view.get("candidate_only") is not True:
            errors.append(f"matrix view {view_kind}.candidate_only must be true")


def _validate_delta(ledger, matrix, errors):
    delta = matrix.get("material_improvement_delta")
    if not isinstance(delta, dict):
        errors.append("material_improvement_delta must be an object")
        return
    rows = delta.get("rows")
    if not isinstance(rows, list) or [row.get("label") for row in rows if isinstance(row, dict)] != list(PRIMARY_LABELS):
        errors.append("material improvement delta must contain ordered VN-00 through VN-20 rows")
        rows = []
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
            if field.startswith("delta_"):
                _signed_int(row.get(field), f"material delta {label}.{field}", errors)
            else:
                _int(row.get(field), f"material delta {label}.{field}", errors)
        partition_rows = [value for value in ledger if _label_for_key(value.get("source_key"), PARTITION_RANGES) == label]
        det = sum(value.get("crosswalk_status") == "deterministic_exact" for value in partition_rows)
        candidate = sum(value.get("crosswalk_status") == "candidate" for value in partition_rows)
        if row.get("after_deterministic_exact_rows") != det or row.get("after_candidate_rows") != candidate:
            errors.append(f"material delta {label} after crosswalk split does not match ledger")
        if row.get("after_usable_selected_word_rows") != det + candidate:
            errors.append(f"material delta {label} usable rows do not equal status split")
        if row.get("delta_usable_selected_word_rows") != row.get("after_usable_selected_word_rows") - row.get("baseline_usable_selected_word_rows"):
            errors.append(f"material delta {label} usable-row delta arithmetic is wrong")
        if row.get("delta_cards_completable") != row.get("after_cards_completable") - row.get("baseline_cards_completable"):
            errors.append(f"material delta {label} card delta arithmetic is wrong")
        if row.get("delta_entries_with_usable_edge") != row.get("after_entries_with_usable_edge") - row.get("baseline_entries_with_usable_edge"):
            errors.append(f"material delta {label} entry delta arithmetic is wrong")
    totals = delta.get("totals")
    if not isinstance(totals, dict):
        errors.append("material improvement delta totals must be an object")
    else:
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
            expected = sum(row.get(field, 0) for row in rows)
            if totals.get(field) != expected:
                errors.append(f"material delta totals.{field} does not sum tranche rows")
    if delta.get("proof_candidate_rows_added_separately") != 3:
        errors.append("material delta must keep the three proof rows separate")


def validate_artifacts(ledger, matrix):
    """Validate v2 schema, authority boundaries, matrix arithmetic, and delta."""

    errors = []
    if not isinstance(matrix, dict):
        return ValidationReport(False, ["matrix must be a JSON object"])
    if matrix.get("schema") != "vn-readiness-v2@1":
        errors.append("matrix schema is not vn-readiness-v2@1")
    if matrix.get("candidate_only") is not True:
        errors.append("matrix candidate_only must be true")
    if matrix.get("assignment_mode") != "vnrec_authority_with_two_explicit_proposals":
        errors.append("matrix assignment mode does not preserve both proposal namespaces")
    if matrix.get("proposal_ids") != ["vn-partition-proposal.v1", "vn-plan-table.v1"]:
        errors.append("matrix proposal_ids must list both owner-ratification namespaces")

    status_counts, selected_ids = _validate_ledger(ledger, errors)
    if not ledger:
        errors.append("ledger must contain selected-word rows")
    summary = matrix.get("denominators")
    if not isinstance(summary, dict):
        errors.append("matrix denominators must be an object")
        summary = {}
    d3 = _int(summary.get("D3_displayed_selected_word_rows"), "denominators.D3_displayed_selected_word_rows", errors)
    if d3 != len(ledger):
        errors.append("D3 displayed selected-word rows must equal ledger length")
    d4_unique = _int(summary.get("D4_unique_canonical_occurrences"), "denominators.D4_unique_canonical_occurrences", errors)
    d4_total = _int(summary.get("D4_total_appearances"), "denominators.D4_total_appearances", errors)
    d4_repeated = _int(summary.get("D4_repeated_appearances"), "denominators.D4_repeated_appearances", errors)
    if d4_unique + d4_repeated != d4_total:
        errors.append("D4 unique occurrences plus repeated appearances must equal total appearances")

    actual_status_counts = _counter(matrix.get("crosswalk_status_counts"), "matrix.crosswalk_status_counts", errors)
    if actual_status_counts != Counter(row.get("crosswalk_status") or "unavailable" for row in ledger):
        errors.append("matrix.crosswalk_status_counts does not match the ledger")
    usable = {status: actual_status_counts.get(status, 0) for status in USABLE_CROSSWALK_STATUSES}
    if matrix.get("usable_crosswalk_status_counts") != usable:
        errors.append("matrix.usable_crosswalk_status_counts does not match deterministic/candidate rows")
    if len(selected_ids) != len(ledger):
        errors.append("ledger selected-word IDs are not unique")

    edge_input = matrix.get("edge_summary_input")
    if not isinstance(edge_input, dict) or edge_input.get("candidate_only") is not True:
        errors.append("edge_summary_input must preserve candidate_only")
    else:
        metrics = edge_input.get("metrics") or {}
        if metrics.get("selected_word_rows_total") != len(ledger):
            errors.append("edge summary selected-word denominator does not equal ledger length")
        if metrics.get("selected_word_rows_with_usable_lexeme_or_form_edge") != sum(usable.values()):
            errors.append("edge summary usable-row count does not equal deterministic/candidate rows")

    proofs = matrix.get("proofs")
    if not isinstance(proofs, dict) or proofs.get("candidate_only") is not True:
        errors.append("proofs must be candidate-only")
    else:
        if proofs.get("count") != 3 or proofs.get("names") != sorted(PROOF_NAME_SET):
            errors.append("proofs must name exactly the three candidate deploy-shaped rows")
        if proofs.get("source_certified_count") != 0:
            errors.append("proofs source_certified_count must remain zero")

    compounding = matrix.get("compounding_impact")
    if not isinstance(compounding, dict) or compounding.get("candidate_only") is not True:
        errors.append("compounding_impact must be candidate-only")
    elif compounding.get("proof_candidate_rows") != 3:
        errors.append("compounding_impact must count three proof candidate rows")
    _validate_views(ledger, matrix, errors)
    _validate_delta(ledger, matrix, errors)
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
    print("ok   v2 fixture validates")

    mutated = [dict(row) for row in ledger]
    conflict = next(row for row in mutated if row.get("vn_tranche_status") == "historical_conflict")
    conflict["vn_tranche"] = "VN-01"
    failed = validate_artifacts(mutated, matrix)
    if failed.ok or not any("historical conflict" in error for error in failed.errors):
        print("FAIL v2 conflict mutation was not rejected")
        return 1
    print("ok   v2 conflict mutation rejected")

    mutated_matrix = json.loads(json.dumps(matrix))
    tranche = next(row for row in mutated_matrix["views"]["authoritative_partition"]["tranches"] if row["label"] == "VN-02")
    tranche["graph_complete_rows"] += 1
    failed = validate_artifacts(ledger, mutated_matrix)
    if failed.ok or not any("graph_complete_rows" in error for error in failed.errors):
        print("FAIL v2 graph mutation was not rejected")
        return 1
    print("ok   v2 graph mutation rejected")
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
