#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build bounded readiness packets for known-defect dogfood rows.

This is a read-only controller bridge. It consumes the next-state queue output
and emits only exact-addressed `known_defect` rows with their current readiness
gate. It does not author hovers, mutate live Qamus, rebuild WBW artifacts,
authorize repair, or turn controller-conflicted rows into repair packets.
"""

import argparse
import glob
import json
import os
import re
import tempfile
from collections import Counter

import build_full_corpus_dogfood_next_state_queues as queue_builder
import validate_full_corpus_dogfood_subagent_lanes as boundary_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_known_defect_readiness.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

REQUIRED_KEYS = (
    "readiness_id",
    "audit_scope",
    "source_queue_id",
    "source_queue_file",
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_gloss",
    "classification",
    "queue_name",
    "primary_route",
    "routes",
    "controller_status",
    "readiness_class",
    "readiness_reason",
    "next_required_gate",
    "blocked_by_controller_reconciliation",
    "repair_preview_required",
    "repair_preview_allowed",
    "production_bug_lesson_required",
    "production_bug_lesson_allowed",
    "drill_regression_fixture_required",
    "procedure_improvement_required",
    "renderer_requirement_required",
    "blocker_queue_required",
    "entry_linkage_review_required",
    "requires_two_vote",
    "exact_address_only",
    "raw_surface_propagation_allowed",
    "parse_family_propagation_allowed",
    "may_apply_live",
    "owner_apply_authorized",
    "live_mutation_allowed",
    "public_boundary_status",
    "public_leak_detected",
    "review_lanes",
    "review_row_count",
    "evidence_count",
    "controller_reason",
    "recommended_next_action",
)


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def safe_id(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text)).strip("_")


def expand_inputs(paths):
    expanded = []
    for path in paths:
        if os.path.isdir(path):
            expanded.extend(sorted(glob.glob(os.path.join(path, "queue_*.jsonl"))))
        else:
            expanded.append(path)
    return expanded


def readiness_for_queue_row(row, source_queue_file):
    if row.get("classification") != "known_defect":
        return None

    routes = row.get("routes") or []
    blocked = (
        row.get("controller_status") == "needs_controller_reconciliation"
        or row.get("queue_name") == "controller_reconciliation"
        or row.get("route_requires_controller_reconciliation") is True
    )
    repair_required = "repair_candidate" in routes
    lesson_required = "production_bug_lesson" in routes or row.get("classification") == "known_defect"

    if blocked:
        readiness_class = "controller_reconciliation_required"
        readiness_reason = "validated reviewers disagree on next state; main-thread reconciliation must happen before any repair preview"
        next_required_gate = "controller_reconciliation"
    elif repair_required and row.get("queue_name") == "repair_candidate":
        readiness_class = "owner_gated_repair_preview_candidate"
        readiness_reason = "all validated review rows routed to repair_candidate; still read-only until owner-gated impact preview"
        next_required_gate = "owner_gated_repair_impact_preview"
    elif lesson_required:
        readiness_class = "production_bug_lesson_candidate"
        readiness_reason = "known defect needs dogfood lesson/regression before closure can be considered"
        next_required_gate = "production_bug_lesson_review"
    else:
        readiness_class = "known_defect_review_required"
        readiness_reason = "known defect needs controller-owned route assignment"
        next_required_gate = "controller_route_assignment"

    return {
        "readiness_id": "dogfood-known-defect-readiness:%s" % safe_id(row["wbw_loc"]),
        "audit_scope": "full_corpus_dogfood_known_defect_readiness",
        "source_queue_id": row["queue_id"],
        "source_queue_file": os.path.normpath(source_queue_file),
        "quran_loc": row["quran_loc"],
        "wbw_loc": row["wbw_loc"],
        "surface": row["surface"],
        "current_gloss": row.get("current_gloss"),
        "classification": row["classification"],
        "queue_name": row["queue_name"],
        "primary_route": row["primary_route"],
        "routes": routes,
        "controller_status": row["controller_status"],
        "readiness_class": readiness_class,
        "readiness_reason": readiness_reason,
        "next_required_gate": next_required_gate,
        "blocked_by_controller_reconciliation": blocked,
        "repair_preview_required": repair_required,
        "repair_preview_allowed": (not blocked) and repair_required and row.get("queue_name") == "repair_candidate",
        "production_bug_lesson_required": lesson_required,
        "production_bug_lesson_allowed": lesson_required,
        "drill_regression_fixture_required": "drill_regression_fixture" in routes,
        "procedure_improvement_required": "sarf_nahw_procedure_improvement" in routes,
        "renderer_requirement_required": "renderer_requirement" in routes,
        "blocker_queue_required": "blocker_queue_row" in routes,
        "entry_linkage_review_required": "entry_linkage_review" in routes,
        "requires_two_vote": row["requires_two_vote"],
        "exact_address_only": True,
        "raw_surface_propagation_allowed": False,
        "parse_family_propagation_allowed": False,
        "may_apply_live": False,
        "owner_apply_authorized": False,
        "live_mutation_allowed": False,
        "public_boundary_status": row["public_boundary_status"],
        "public_leak_detected": False,
        "review_lanes": row["review_lanes"],
        "review_row_count": row["review_row_count"],
        "evidence_count": row["evidence_count"],
        "controller_reason": row["controller_reason"],
        "recommended_next_action": row["recommended_next_action"],
    }


def build_from_queue_paths(paths, expect_min_source_rows=1):
    paths = expand_inputs(paths)
    if not paths:
        raise SystemExit("no queue JSONL inputs found")

    readiness_rows = []
    validation = []
    for path in paths:
        result = queue_builder.validate_queue_file(path, expect_min_rows=expect_min_source_rows)
        validation.append(result)
        if result["errors"]:
            raise SystemExit(json.dumps({"ok": False, "errors": result["errors"][:100]}, indent=2))
        for row in read_jsonl(path):
            readiness = readiness_for_queue_row(row, path)
            if readiness:
                readiness_rows.append(readiness)

    readiness_rows.sort(key=lambda row: (row["readiness_class"], row["quran_loc"], row["wbw_loc"]))
    if not readiness_rows:
        raise SystemExit("no known_defect rows found; refusing vacuous readiness output")
    return readiness_rows, validation


def summarize(rows, source_files=None):
    if not rows:
        raise SystemExit("readiness output has zero rows; refusing vacuous summary")
    readiness_counts = Counter(row["readiness_class"] for row in rows)
    route_counts = Counter()
    lane_counts = Counter()
    for row in rows:
        route_counts.update(row["routes"])
        lane_counts.update(row["review_lanes"])
    return {
        "audit_scope": "full_corpus_dogfood_known_defect_readiness",
        "source_files": source_files or [],
        "readiness_rows": len(rows),
        "unique_wbw_locs": len({row["wbw_loc"] for row in rows}),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "review_lane_counts": dict(sorted(lane_counts.items())),
        "blocked_by_controller_reconciliation": sum(1 for row in rows if row["blocked_by_controller_reconciliation"]),
        "repair_preview_allowed_count": sum(1 for row in rows if row["repair_preview_allowed"]),
        "production_bug_lesson_required_count": sum(1 for row in rows if row["production_bug_lesson_required"]),
        "rows_requiring_two_vote": sum(1 for row in rows if row["requires_two_vote"]),
        "public_leak_count": sum(1 for row in rows if row["public_leak_detected"]),
        "may_apply_live": False,
        "owner_apply_authorized": False,
        "live_mutation_allowed": False,
        "not_claimed": [
            "live Qamus mutation",
            "WBW rebuild",
            "hover coverage improvement",
            "owner-gated apply authorization",
            "parse-key propagation approval",
            "controller-conflicted repair readiness",
        ],
    }


def validate_row(row, errors, path, line_no):
    keys = set(row)
    missing = [key for key in REQUIRED_KEYS if key not in keys]
    extra = sorted(keys - set(REQUIRED_KEYS))
    if missing:
        errors.append("%s:%s: missing keys: %s" % (path, line_no, ", ".join(missing)))
    if extra:
        errors.append("%s:%s: unexpected keys: %s" % (path, line_no, ", ".join(extra)))
    if row.get("audit_scope") != "full_corpus_dogfood_known_defect_readiness":
        errors.append("%s:%s: bad audit_scope" % (path, line_no))
    if not str(row.get("readiness_id", "")).startswith("dogfood-known-defect-readiness:"):
        errors.append("%s:%s: bad readiness_id" % (path, line_no))
    if not str(row.get("source_queue_id", "")).startswith("dogfood-next-state-queue:"):
        errors.append("%s:%s: bad source_queue_id" % (path, line_no))
    if not QURAN_RE.match(str(row.get("quran_loc", ""))):
        errors.append("%s:%s: bad quran_loc" % (path, line_no))
    if not WBW_RE.match(str(row.get("wbw_loc", ""))):
        errors.append("%s:%s: bad wbw_loc" % (path, line_no))
    if row.get("classification") != "known_defect":
        errors.append("%s:%s: readiness rows must remain known_defect" % (path, line_no))
    if not row.get("exact_address_only"):
        errors.append("%s:%s: exact_address_only must be true" % (path, line_no))
    for key in (
        "raw_surface_propagation_allowed",
        "parse_family_propagation_allowed",
        "may_apply_live",
        "owner_apply_authorized",
        "live_mutation_allowed",
        "public_leak_detected",
    ):
        if row.get(key) is not False:
            errors.append("%s:%s: %s must be false" % (path, line_no, key))
    if not boundary_validator._is_source_clean_boundary(row.get("public_boundary_status")):
        errors.append("%s:%s: public_boundary_status must be source-clean" % (path, line_no))
    if row.get("readiness_class") not in {
        "controller_reconciliation_required",
        "owner_gated_repair_preview_candidate",
        "production_bug_lesson_candidate",
        "known_defect_review_required",
    }:
        errors.append("%s:%s: bad readiness_class %r" % (path, line_no, row.get("readiness_class")))
    blocked = row.get("blocked_by_controller_reconciliation") is True
    if blocked and row.get("readiness_class") != "controller_reconciliation_required":
        errors.append("%s:%s: controller-blocked row must use controller_reconciliation_required" % (path, line_no))
    if blocked and row.get("repair_preview_allowed") is not False:
        errors.append("%s:%s: controller-blocked row cannot allow repair preview" % (path, line_no))
    if row.get("repair_preview_allowed") and row.get("blocked_by_controller_reconciliation"):
        errors.append("%s:%s: repair_preview_allowed conflicts with controller block" % (path, line_no))
    if row.get("repair_preview_allowed") and row.get("next_required_gate") != "owner_gated_repair_impact_preview":
        errors.append("%s:%s: repair-preview rows must require owner_gated_repair_impact_preview" % (path, line_no))
    if row.get("production_bug_lesson_required") is not True:
        errors.append("%s:%s: known_defect must require a production-bug lesson" % (path, line_no))
    if not isinstance(row.get("requires_two_vote"), bool):
        errors.append("%s:%s: requires_two_vote must be boolean" % (path, line_no))
    for list_key in ("routes", "review_lanes"):
        if not isinstance(row.get(list_key), list) or not row.get(list_key):
            errors.append("%s:%s: %s must be a non-empty list" % (path, line_no, list_key))
    for text_key in (
        "source_queue_file",
        "surface",
        "readiness_reason",
        "next_required_gate",
        "controller_reason",
        "recommended_next_action",
    ):
        if not str(row.get(text_key, "")).strip():
            errors.append("%s:%s: %s must be non-empty" % (path, line_no, text_key))


def validate_readiness_file(path, expect_min_rows=1):
    errors = []
    rows = 0
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append("%s:%s: invalid JSON: %s" % (path, line_no, exc))
                continue
            rows += 1
            validate_row(row, errors, path, line_no)
    if rows < expect_min_rows:
        errors.append("%s: expected at least %s rows, got %s" % (path, expect_min_rows, rows))
    return {"path": path, "rows": rows, "errors": errors}


def make_queue_row(loc, surface, status="routed", routes=None):
    routes = routes or ["repair_candidate"]
    queue_name = "controller_reconciliation" if status == "needs_controller_reconciliation" else routes[0]
    return {
        "queue_id": "dogfood-next-state-queue:%s:%s" % (queue_name, safe_id(loc.replace("wbw:", "wbw_"))),
        "audit_scope": "full_corpus_dogfood_next_state_queue",
        "source_reconciliation_packet_id": "dogfood-lane-packet:%s" % safe_id(loc.replace("wbw:", "wbw_")),
        "quran_loc": loc.replace("wbw:", "quran:"),
        "wbw_loc": loc,
        "surface": surface,
        "current_gloss": "to ask, question" if loc == "wbw:33:63:1" else "and + the trees",
        "classification": "known_defect",
        "queue_name": queue_name,
        "primary_route": routes[0],
        "routes": routes,
        "controller_status": status,
        "route_requires_controller_reconciliation": status == "needs_controller_reconciliation",
        "requires_two_vote": True,
        "may_apply_live": False,
        "owner_apply_authorized": False,
        "live_mutation_allowed": False,
        "public_boundary_status": "source_clean:qamus/authored/en",
        "public_leak_detected": False,
        "next_state_counts": {route: 1 for route in routes},
        "review_lanes": ["sarf-component-reviewer", "production-bug-lesson-writer"],
        "review_row_count": len(routes),
        "evidence_count": len(routes),
        "controller_reason": (
            "multiple validated review lanes propose different next states"
            if status == "needs_controller_reconciliation"
            else "all validated review rows agree on one next state"
        ),
        "recommended_next_action": "route known defect; no live apply is authorized",
        "next_gate": "controller must reconcile competing next states before any action queue may proceed",
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="known-defect-readiness-") as td:
        queue_path = os.path.join(td, "queue.jsonl")
        source_rows = [
            make_queue_row("wbw:33:63:1", "يَسْأَلُكَ", "routed", ["repair_candidate", "production_bug_lesson"]),
            make_queue_row(
                "wbw:22:18:17",
                "وَٱلشَّجَرُ",
                "needs_controller_reconciliation",
                ["repair_candidate", "renderer_requirement", "production_bug_lesson"],
            ),
        ]
        queue_builder.write_jsonl(queue_path, source_rows)
        rows, _ = build_from_queue_paths([queue_path])
        out_path = os.path.join(td, "readiness.jsonl")
        write_jsonl(out_path, rows)
        result = validate_readiness_file(out_path, expect_min_rows=2)
        if result["errors"]:
            raise SystemExit("self-test validation failed: %s" % result["errors"])
        summary = summarize(rows, [queue_path])
        if summary["readiness_counts"].get("owner_gated_repair_preview_candidate") != 1:
            raise SystemExit("self-test did not produce one repair-preview candidate: %s" % summary)
        if summary["readiness_counts"].get("controller_reconciliation_required") != 1:
            raise SystemExit("self-test did not keep one controller row blocked: %s" % summary)
        if summary["repair_preview_allowed_count"] != 1:
            raise SystemExit("self-test repair preview allowed count mismatch: %s" % summary)
    print("PASS - full-corpus dogfood known-defect readiness builder self-test")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="next-state queue JSONL files or directories containing queue_*.jsonl")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--out-summary-json")
    parser.add_argument("--validate-jsonl")
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if args.validate_jsonl:
        result = validate_readiness_file(args.validate_jsonl, args.expect_min_rows)
        if result["errors"]:
            raise SystemExit(json.dumps({"ok": False, **result}, ensure_ascii=False, indent=2))
        print("PASS - known-defect readiness JSONL validates (%s rows)" % result["rows"])
        return

    if not args.paths:
        parser.error("provide queue JSONL paths/directories, --validate-jsonl, or --self-test")

    rows, validation = build_from_queue_paths(args.paths)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))

    summary = summarize(rows, source_files=[item["path"] for item in validation])
    if args.out_summary_json:
        write_json(args.out_summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
