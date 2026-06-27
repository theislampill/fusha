#!/usr/bin/env python3
"""Reconcile bounded full-corpus dogfood review outputs.

This is a controller tool, not an apply tool. It groups validated review rows
by exact hover slot, preserves every proposed route, and emits one
non-applying controller row per `wbw:S:A:W`. Conflicting next states become
explicit reconciliation work before any owner-gated apply packet can exist.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

import validate_full_corpus_dogfood_review_outputs as review_validator
import validate_full_corpus_dogfood_subagent_lanes as boundary_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_reconciliation.sample.jsonl")
REVIEW_SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_review_output.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

REQUIRED_KEYS = (
    "packet_id",
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_gloss",
    "classification",
    "controller_status",
    "primary_route",
    "routes",
    "next_state_counts",
    "review_lanes",
    "review_row_count",
    "requires_two_vote",
    "may_apply_live",
    "public_boundary_status",
    "controller_reason",
    "recommended_next_action",
    "evidence",
)

ALLOWED_STATUS = {
    "routed",
    "needs_controller_reconciliation",
}
ALLOWED_ROUTES = review_validator.ALLOWED_NEXT_STATES
ALLOWED_CLASSES = review_validator.ALLOWED_CLASSES

CLASS_PRIORITY = {
    "known_defect": 1,
    "token_only_override": 2,
    "needs_sarf_review": 3,
    "needs_nahw_review": 4,
    "needs_renderer_segments": 5,
    "pending/blocker": 6,
    "string_correct_but_not_rich": 7,
    "populated_uncertified": 8,
    "rich_certified": 99,
}

ROUTE_PRIORITY_BY_CLASS = {
    "known_defect": (
        "repair_candidate",
        "blocker_queue_row",
        "renderer_requirement",
        "entry_linkage_review",
        "production_bug_lesson",
        "sarf_nahw_procedure_improvement",
        "drill_regression_fixture",
        "no_action",
    ),
    "token_only_override": (
        "repair_candidate",
        "blocker_queue_row",
        "entry_linkage_review",
        "renderer_requirement",
        "sarf_nahw_procedure_improvement",
        "drill_regression_fixture",
        "production_bug_lesson",
        "no_action",
    ),
    "needs_renderer_segments": (
        "renderer_requirement",
        "entry_linkage_review",
        "blocker_queue_row",
        "drill_regression_fixture",
        "repair_candidate",
        "sarf_nahw_procedure_improvement",
        "production_bug_lesson",
        "no_action",
    ),
    "needs_sarf_review": (
        "blocker_queue_row",
        "sarf_nahw_procedure_improvement",
        "drill_regression_fixture",
        "repair_candidate",
        "entry_linkage_review",
        "renderer_requirement",
        "production_bug_lesson",
        "no_action",
    ),
    "needs_nahw_review": (
        "blocker_queue_row",
        "sarf_nahw_procedure_improvement",
        "drill_regression_fixture",
        "repair_candidate",
        "entry_linkage_review",
        "renderer_requirement",
        "production_bug_lesson",
        "no_action",
    ),
}
DEFAULT_ROUTE_PRIORITY = (
    "blocker_queue_row",
    "repair_candidate",
    "renderer_requirement",
    "entry_linkage_review",
    "sarf_nahw_procedure_improvement",
    "drill_regression_fixture",
    "production_bug_lesson",
    "no_action",
)


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def validate_review_inputs(paths, expect_min_rows=1):
    validation = [review_validator.validate_file(path, expect_min_rows) for path in paths]
    errors = [err for result in validation for err in result["errors"]]
    if errors:
        raise SystemExit(json.dumps({"ok": False, "errors": errors[:100], "files": validation}, indent=2))
    return validation


def choose_class(rows):
    return sorted(
        {row["classification"] for row in rows},
        key=lambda cls: (CLASS_PRIORITY.get(cls, 100), cls),
    )[0]


def route_order(classification):
    priority = ROUTE_PRIORITY_BY_CLASS.get(classification, DEFAULT_ROUTE_PRIORITY)
    return {route: idx for idx, route in enumerate(priority)}


def sorted_routes(classification, routes):
    order = route_order(classification)
    return sorted(routes, key=lambda route: (order.get(route, 100), route))


def reconcile_rows(review_rows):
    by_wbw = defaultdict(list)
    for row in review_rows:
        by_wbw[row["wbw_loc"]].append(row)

    reconciled = []
    for wbw_loc, rows in sorted(by_wbw.items()):
        first = rows[0]
        classification = choose_class(rows)
        routes = sorted_routes(classification, {row["next_state"] for row in rows})
        lanes = sorted({row["review_lane"] for row in rows})
        next_state_counts = Counter(row["next_state"] for row in rows)
        conflict = len(routes) > 1
        primary_route = routes[0]
        reason = (
            "multiple validated review lanes propose different next states"
            if conflict
            else "all validated review rows agree on one next state"
        )
        action = (
            "controller must reconcile routes before owner-gated apply packet"
            if conflict
            else "route to %s queue; no live apply is authorized" % primary_route
        )
        evidence = []
        for row in sorted(rows, key=lambda item: item["review_lane"]):
            evidence.append(
                {
                    "review_lane": row["review_lane"],
                    "next_state": row["next_state"],
                    "classification": row["classification"],
                    "detected_issue": row["detected_issue"],
                    "procedure_or_rule": row["procedure_or_rule"],
                    "confidence": row["confidence"],
                    "requires_two_vote": row["requires_two_vote"],
                }
            )
        reconciled.append(
            {
                "packet_id": first["packet_id"],
                "quran_loc": first["quran_loc"],
                "wbw_loc": wbw_loc,
                "surface": first["surface"],
                "current_gloss": first["current_gloss"],
                "classification": classification,
                "controller_status": "needs_controller_reconciliation" if conflict else "routed",
                "primary_route": primary_route,
                "routes": routes,
                "next_state_counts": dict(sorted(next_state_counts.items())),
                "review_lanes": lanes,
                "review_row_count": len(rows),
                "requires_two_vote": any(row["requires_two_vote"] for row in rows),
                "may_apply_live": False,
                "public_boundary_status": "source_clean:qamus/authored/en",
                "controller_reason": reason,
                "recommended_next_action": action,
                "evidence": evidence,
            }
        )
    return reconciled


def summarize(rows, validation=None):
    class_counts = Counter(row["classification"] for row in rows)
    status_counts = Counter(row["controller_status"] for row in rows)
    primary_counts = Counter(row["primary_route"] for row in rows)
    route_counts = Counter(route for row in rows for route in row["routes"])
    lane_counts = Counter(lane for row in rows for lane in row["review_lanes"])
    return {
        "ok": True,
        "audit_scope": "full_corpus_dogfood_controller_reconciliation",
        "may_apply_live": False,
        "files": validation or [],
        "reconciled_rows": len(rows),
        "unique_wbw_locs": len({row["wbw_loc"] for row in rows}),
        "rows_requiring_two_vote": sum(1 for row in rows if row["requires_two_vote"]),
        "controller_status_counts": dict(sorted(status_counts.items())),
        "classification_counts": dict(sorted(class_counts.items())),
        "primary_route_counts": dict(sorted(primary_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "review_lane_counts": dict(sorted(lane_counts.items())),
        "conflict_count": status_counts.get("needs_controller_reconciliation", 0),
        "controller_note": (
            "Reconciliation rows are exact-addressed routing evidence only. "
            "They do not authorize live apply or hover coverage claims."
        ),
    }


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _err(errors, path, line_no, message):
    errors.append("%s:%s: %s" % (path, line_no, message))


def validate_reconciliation_file(path, expect_min_rows=1):
    errors = []
    rows = 0
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                _err(errors, path, line_no, "invalid JSON: %s" % exc)
                continue
            rows += 1
            keys = set(row)
            missing = [key for key in REQUIRED_KEYS if key not in keys]
            extra = sorted(keys - set(REQUIRED_KEYS))
            if missing:
                _err(errors, path, line_no, "missing keys: %s" % ", ".join(missing))
            if extra:
                _err(errors, path, line_no, "unexpected keys: %s" % ", ".join(extra))
            if not str(row.get("packet_id", "")).startswith("dogfood-lane-packet:"):
                _err(errors, path, line_no, "bad packet_id")
            if not QURAN_RE.match(str(row.get("quran_loc", ""))):
                _err(errors, path, line_no, "bad quran_loc")
            if not WBW_RE.match(str(row.get("wbw_loc", ""))):
                _err(errors, path, line_no, "bad wbw_loc")
            if row.get("classification") not in ALLOWED_CLASSES:
                _err(errors, path, line_no, "bad classification %r" % row.get("classification"))
            if row.get("controller_status") not in ALLOWED_STATUS:
                _err(errors, path, line_no, "bad controller_status %r" % row.get("controller_status"))
            routes = row.get("routes")
            if not isinstance(routes, list) or not routes:
                _err(errors, path, line_no, "routes must be a non-empty list")
                routes = []
            for route in routes:
                if route not in ALLOWED_ROUTES:
                    _err(errors, path, line_no, "bad route %r" % route)
            if row.get("primary_route") not in routes:
                _err(errors, path, line_no, "primary_route must be in routes")
            if row.get("controller_status") == "routed" and len(routes) != 1:
                _err(errors, path, line_no, "routed rows must have exactly one route")
            if row.get("controller_status") == "needs_controller_reconciliation" and len(routes) < 2:
                _err(errors, path, line_no, "reconciliation rows must have multiple routes")
            if not isinstance(row.get("next_state_counts"), dict) or not row.get("next_state_counts"):
                _err(errors, path, line_no, "next_state_counts must be non-empty object")
            if not isinstance(row.get("review_lanes"), list) or not row.get("review_lanes"):
                _err(errors, path, line_no, "review_lanes must be non-empty list")
            if not isinstance(row.get("review_row_count"), int) or row.get("review_row_count") < 1:
                _err(errors, path, line_no, "review_row_count must be positive integer")
            if not isinstance(row.get("requires_two_vote"), bool):
                _err(errors, path, line_no, "requires_two_vote must be boolean")
            if row.get("may_apply_live") is not False:
                _err(errors, path, line_no, "may_apply_live must be false")
            if not boundary_validator._is_source_clean_boundary(row.get("public_boundary_status")):
                _err(errors, path, line_no, "public_boundary_status must be source-clean")
            if not isinstance(row.get("evidence"), list) or not row.get("evidence"):
                _err(errors, path, line_no, "evidence must be non-empty list")
            for text_key in ("surface", "controller_reason", "recommended_next_action"):
                if not str(row.get(text_key, "")).strip():
                    _err(errors, path, line_no, "%s must be non-empty" % text_key)
    if rows < expect_min_rows:
        errors.append("%s: expected at least %s rows, got %s" % (path, expect_min_rows, rows))
    return {"path": path, "rows": rows, "errors": errors}


def self_test():
    row_a = {
        "packet_id": "dogfood-lane-packet:wbw_33_63_1",
        "quran_loc": "quran:33:63:1",
        "wbw_loc": "wbw:33:63:1",
        "surface": "يَسْأَلُكَ",
        "current_gloss": "to ask, question",
        "review_lane": "sarf-component-reviewer",
        "classification": "known_defect",
        "next_state": "repair_candidate",
        "detected_issue": "attached object pronoun omitted",
        "evidence_summary": "exact-addressed suffix-pronoun defect",
        "procedure_or_rule": "sarf/procedures/clitic-and-host-morphology.md",
        "recommended_next_action": "route to token-only repair candidate",
        "public_boundary_status": "source_clean:qamus/authored/en",
        "confidence": "high",
        "requires_two_vote": True,
        "may_apply_live": False,
    }
    row_b = dict(row_a)
    row_b["review_lane"] = "production-bug-lesson-writer"
    row_b["next_state"] = "production_bug_lesson"
    with tempfile.TemporaryDirectory(prefix="dogfood-reconcile-") as td:
        review_path = os.path.join(td, "review.jsonl")
        output_path = os.path.join(td, "reconciled.jsonl")
        with open(review_path, "w", encoding="utf-8") as handle:
            for row in (row_a, row_b):
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        validation = validate_review_inputs([review_path])
        rows = []
        rows.extend(read_jsonl(review_path))
        reconciled = reconcile_rows(rows)
        write_jsonl(output_path, reconciled)
        result = validate_reconciliation_file(output_path)
        if result["errors"]:
            raise SystemExit("self-test validation failed: %s" % result["errors"])
        summary = summarize(reconciled, validation)
        if summary["reconciled_rows"] != 1 or summary["conflict_count"] != 1:
            raise SystemExit("self-test summary mismatch: %s" % summary)
        if reconciled[0]["may_apply_live"] is not False:
            raise SystemExit("self-test may_apply_live must be false")
    print("PASS - full-corpus dogfood controller reconciliation self-test")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*")
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--out-jsonl", help="write reconciled JSONL rows")
    parser.add_argument("--out-summary", help="write pretty JSON summary")
    parser.add_argument("--validate-jsonl", help="validate an existing reconciliation JSONL file")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.validate_jsonl:
        result = validate_reconciliation_file(args.validate_jsonl, args.expect_min_rows)
        output = {"ok": not result["errors"], "files": [result]}
        if result["errors"]:
            output["errors"] = result["errors"][:100]
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        if result["errors"]:
            raise SystemExit(1)
        return

    paths = args.jsonl or [REVIEW_SAMPLE]
    validation = validate_review_inputs(paths, args.expect_min_rows)
    review_rows = []
    for path in paths:
        review_rows.extend(read_jsonl(path))
    reconciled = reconcile_rows(review_rows)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, reconciled)
    summary = summarize(reconciled, validation)
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out_summary:
        with open(args.out_summary, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
