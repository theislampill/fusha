#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate VNMAP ledger, denominator, and reverse-edge invariants offline."""

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

from tools.build_entry_card_word_ledger import (  # noqa: E402
    CONTRACT_WINDOW_IDS,
    OWNER_EDGE_ORDER,
    OWNER_MISSING_EDGE_CLASSES,
    TRANCHE_LABELS,
)


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str]


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _int_metric(metrics, key, errors):
    value = metrics.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"metric {key} must be a non-negative integer")
        return 0
    return value


def _check_proposal_label(value, where, errors):
    """Namespace-collision guard (owner ruling 2026-07-29, VN-UNLOCK-PROOF Finding 0).

    A proposal-namespace tranche label must never collide with a contract
    window identifier (VN-00..VN-23): the proposal population behind e.g.
    the former proposal "VN-03" (v196-v296) is NOT the contract VN-03
    window (v142-v188 + n0136-n0180).
    """

    if value in CONTRACT_WINDOW_IDS:
        errors.append(
            f"{where}: proposal-namespace tranche label {value!r} collides with a "
            "contract window id (VN-00..VN-23); proposal labels must use the "
            "VNPROP-xx namespace"
        )
    elif value is not None and value not in TRANCHE_LABELS:
        errors.append(f"{where}: unknown proposal tranche label {value!r}")


def validate_artifacts(ledger, metrics, matrix):
    """Validate complete artifact values and return a structured report."""

    errors = []
    if not isinstance(ledger, list):
        return ValidationReport(False, ["ledger is not a list"])
    if not isinstance(metrics, dict):
        return ValidationReport(False, ["metrics is not an object"])
    if not isinstance(matrix, dict):
        return ValidationReport(False, ["matrix is not an object"])

    if metrics.get("candidate_only") is not True or matrix.get("candidate_only") is not True:
        errors.append("candidate_only must be true in metrics and matrix")
    if matrix.get("assignment_mode") != "derived_proposal_requires_owner_confirmation":
        errors.append("matrix assignment_mode is not the owner-confirmation proposal mode")

    seen_rows = set()
    missing_counts = Counter()
    occurrence_reverse_failures = 0
    for index, row in enumerate(ledger, 1):
        if not isinstance(row, dict):
            errors.append(f"ledger row {index} is not an object")
            continue
        if "blocker" in row:
            errors.append(f"ledger row {index} uses forbidden generic blocker field")
        row_key = (
            row.get("entry_id"),
            row.get("sense_index"),
            row.get("usage_index"),
            row.get("form_index"),
        )
        if row_key in seen_rows:
            errors.append(f"duplicate ledger row identity at row {index}")
        seen_rows.add(row_key)
        if row.get("vn_tranche") is not None:
            errors.append(f"ledger row {index} has a non-null candidate vn_tranche")
        _check_proposal_label(row.get("proposal_vn_tranche"), f"ledger row {index}", errors)
        missing_edges = row.get("missing_edges")
        if not isinstance(missing_edges, list):
            errors.append(f"ledger row {index} missing_edges is not a list")
            missing_edges = []
        expected_order = sorted(
            set(missing_edges), key=lambda value: OWNER_EDGE_ORDER.get(value, len(OWNER_EDGE_ORDER))
        )
        if missing_edges != expected_order:
            errors.append(f"ledger row {index} missing_edges is not owner-enum ordered")
        for edge in missing_edges:
            if edge not in OWNER_EDGE_ORDER:
                errors.append(f"ledger row {index} has non-owner missing edge {edge!r}")
            else:
                missing_counts[edge] += 1
        if row.get("occurrence_id") and not row.get("reverse_entry_relationship_present"):
            occurrence_reverse_failures += 1

    denominators = metrics.get("denominators")
    if not isinstance(denominators, dict):
        errors.append("metrics denominators is not an object")
        denominators = {}
    d1 = _int_metric(denominators, "D1_entries", errors)
    d1_spaces = denominators.get("D1_entries_by_space")
    if not isinstance(d1_spaces, dict) or sum(d1_spaces.values()) != d1:
        errors.append("D1 entries do not sum across source spaces")
    d2 = _int_metric(denominators, "D2_listed_quran_example_cards", errors)
    d3 = _int_metric(denominators, "D3_displayed_selected_word_rows", errors)
    d4_unique = _int_metric(denominators, "D4_unique_canonical_occurrences", errors)
    d4_total = _int_metric(denominators, "D4_total_appearances", errors)
    d4_repeated = _int_metric(denominators, "D4_repeated_appearances", errors)
    if d4_unique + d4_repeated != d4_total:
        errors.append("D4 unique occurrences plus repeated appearances does not equal total appearances")
    if d3 != len(ledger):
        errors.append("D3 selected-word denominator does not equal ledger row count")

    for key, expected in (
        ("D2_cards_by_proposal_tranche", d2),
        ("D3_selected_words_by_proposal_tranche", d3),
    ):
        values = denominators.get(key)
        if not isinstance(values, dict) or set(values) != set(TRANCHE_LABELS) or sum(values.values()) != expected:
            errors.append(f"{key} does not contain all 21 tranches or does not sum to its denominator")
        for label in values if isinstance(values, dict) else ():
            _check_proposal_label(label, f"metrics {key}", errors)

    for key in (
        "edge_join_rows_total",
        "forward_trace_complete_rows",
        "reverse_trace_complete_rows",
        "quran_wbw_trace_complete_rows",
        "canonical_occurrence_trace_complete_rows",
        "appearance_index_complete_rows",
        "rows_needing_source_address_crosswalk",
        "orphan_typed_fact_rows",
        "orphan_payload_rows",
        "entry_occurrence_reciprocity_failures",
        "appearance_projection_parity_failures",
        "manual_probe_count",
    ):
        _int_metric(metrics, key, errors)
    if metrics.get("edge_join_rows_total") != len(ledger):
        errors.append("edge_join_rows_total does not equal ledger row count")
    if metrics.get("entry_occurrence_reciprocity_failures") != occurrence_reverse_failures:
        errors.append("entry_occurrence_reciprocity_failures does not equal measured reverse failures")
    if metrics.get("manual_probe_count") != 0:
        errors.append("manual_probe_count must remain zero for this offline lane")
    if metrics.get("missing_edge_counts") != dict(sorted(missing_counts.items())):
        errors.append("missing_edge_counts does not equal ledger owner-edge counts")

    tranches = matrix.get("tranches")
    if not isinstance(tranches, list):
        tranches = []
    for row_index, row in enumerate(tranches):
        if isinstance(row, dict):
            _check_proposal_label(row.get("proposal_vn_tranche"), f"matrix tranche {row_index}", errors)
    if not tranches or [row.get("proposal_vn_tranche") for row in tranches] != list(TRANCHE_LABELS):
        errors.append("matrix does not contain the ordered VNPROP-00 through VNPROP-20 proposal rows")
        tranches = []
    matrix_totals = matrix.get("totals") if isinstance(matrix.get("totals"), dict) else {}
    for key in ("entries", "cards", "displayed_selected_words", "unique_occurrences", "appearances_affected"):
        if not isinstance(matrix_totals.get(key), int) or matrix_totals[key] < 0:
            errors.append(f"matrix total {key} is not a non-negative integer")
    for key, denominator_key in (
        ("cards", "D2_listed_quran_example_cards"),
        ("displayed_selected_words", "D3_displayed_selected_word_rows"),
    ):
        if isinstance(matrix_totals.get(key), int) and matrix_totals[key] != denominators.get(denominator_key):
            errors.append(f"matrix total {key} does not equal {denominator_key}")
    if isinstance(matrix_totals.get("entries"), int) and matrix_totals["entries"] != d1:
        errors.append("matrix total entries does not equal D1")
    if isinstance(matrix_totals.get("unique_occurrences"), int) and matrix_totals["unique_occurrences"] > d4_unique:
        errors.append("matrix unique occurrences exceeds D4")
    if isinstance(matrix_totals.get("appearances_affected"), int) and matrix_totals["appearances_affected"] < 0:
        errors.append("matrix appearances_affected is negative")

    return ValidationReport(ok=not errors, errors=errors)


def _render(report):
    if report.ok:
        return "VNMAP LEDGER VALIDATION PASS"
    return "\n".join(["VNMAP LEDGER VALIDATION FAIL", *[f"FAIL {error}" for error in report.errors]])


def self_test():
    fixture_root = os.path.join(ROOT, "qamus", "examples", "vnmap")
    try:
        ledger = _read_jsonl(os.path.join(fixture_root, "vn-ledger.fixture.jsonl"))
        metrics = _read_json(os.path.join(fixture_root, "vn-graph-metrics.fixture.json"))
        matrix = _read_json(os.path.join(fixture_root, "vn-readiness-matrix.fixture.json"))
    except FileNotFoundError:
        # Before fixture generation, exercise the builder directly so the self-test
        # remains useful during the red-green cycle.
        from tools.build_entry_card_word_ledger import build_ledger

        entries = _read_jsonl(os.path.join(fixture_root, "entries.fixture.jsonl"))
        whitelist = _read_jsonl(os.path.join(fixture_root, "whitelist.fixture.jsonl"))
        appearances = _read_jsonl(os.path.join(fixture_root, "occurrence-appearances.fixture.jsonl"))
        family = _read_jsonl(os.path.join(fixture_root, "famwide-strat.fixture.jsonl"))
        result = build_ledger(entries, whitelist, appearances, family)
        ledger, metrics, matrix = result.ledger, result.metrics, result.matrix

    passing = validate_artifacts(ledger, metrics, matrix)
    if not passing.ok:
        print(_render(passing))
        return 1
    print("ok   vnmap fixture validates")

    mutated = [dict(row) for row in ledger]
    for row in mutated:
        if row.get("occurrence_id"):
            row["reverse_entry_relationship_present"] = False
            break
    failed = validate_artifacts(mutated, metrics, matrix)
    if failed.ok or not any("reciprocity" in error for error in failed.errors):
        print("FAIL vnmap reciprocity mutation was not rejected")
        return 1
    print("ok   vnmap reciprocity mutation rejected")

    mutated_edge = [dict(row) for row in ledger]
    mutated_edge[0] = dict(mutated_edge[0])
    mutated_edge[0]["missing_edges"] = list(mutated_edge[0].get("missing_edges", [])) + ["not_an_owner_edge"]
    failed_edge = validate_artifacts(mutated_edge, metrics, matrix)
    if failed_edge.ok or not any("non-owner" in error for error in failed_edge.errors):
        print("FAIL vnmap missing-edge enum mutation was not rejected")
        return 1
    print("ok   vnmap missing-edge enum mutation rejected")

    # Namespace-collision hazard (red-first): a proposal row relabelled with a
    # bare contract window id (the pre-ruling "VN-03" spelling) must FAIL.
    mutated_matrix = json.loads(json.dumps(matrix))
    collided = mutated_matrix.get("tranches") or [{}]
    collided[3 if len(collided) > 3 else 0]["proposal_vn_tranche"] = "VN-03"
    failed_collision = validate_artifacts(ledger, metrics, mutated_matrix)
    if failed_collision.ok or not any("collides with a" in error for error in failed_collision.errors):
        print("FAIL vnmap proposal/contract namespace collision was not rejected")
        return 1
    print("ok   vnmap proposal/contract namespace collision rejected")
    print("VNMAP LEDGER SELF-TEST PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger")
    parser.add_argument("--metrics")
    parser.add_argument("--matrix")
    parser.add_argument("--structure-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not all((args.ledger, args.metrics, args.matrix)):
        parser.error("provide --ledger, --metrics, and --matrix, or use --self-test")
    report = validate_artifacts(
        _read_jsonl(args.ledger),
        _read_json(args.metrics),
        _read_json(args.matrix),
    )
    print(_render(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
