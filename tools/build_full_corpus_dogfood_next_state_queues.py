#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build next-state review queues from controller-reconciled dogfood rows.

This is still read-only dogfood infrastructure. It turns one controller row per
exact `wbw:S:A:W` into bounded next-state queues for later reviewer lanes. It
does not author hovers, mutate live Qamus, rebuild WBW, or authorize apply.
Rows with conflicting next states are deliberately held in a
`controller_reconciliation` queue instead of entering repair/blocker/renderer
work queues.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

import reconcile_full_corpus_dogfood_review_outputs as reconciler
import validate_full_corpus_dogfood_subagent_lanes as boundary_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_next_state_queue.sample.jsonl")
RECONCILIATION_SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_reconciliation.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

ACTION_QUEUE_NAMES = set(reconciler.ALLOWED_ROUTES)
QUEUE_NAMES = ACTION_QUEUE_NAMES | {"controller_reconciliation"}

REQUIRED_KEYS = (
    "queue_id",
    "audit_scope",
    "source_reconciliation_packet_id",
    "quran_loc",
    "wbw_loc",
    "surface",
    "current_gloss",
    "classification",
    "queue_name",
    "primary_route",
    "routes",
    "controller_status",
    "route_requires_controller_reconciliation",
    "requires_two_vote",
    "may_apply_live",
    "owner_apply_authorized",
    "live_mutation_allowed",
    "public_boundary_status",
    "public_leak_detected",
    "next_state_counts",
    "review_lanes",
    "review_row_count",
    "evidence_count",
    "controller_reason",
    "recommended_next_action",
    "next_gate",
)

NEXT_GATES = {
    "blocker_queue_row": "keep exact-address blocker row until required sarf/nahw or owner gate is satisfied",
    "drill_regression_fixture": "convert to drill/regression fixture before future closure batches",
    "entry_linkage_review": "review exact Qamus entry/sense linkage or valid no-entry function-token rationale",
    "no_action": "no live action; retain as review evidence only",
    "production_bug_lesson": "emit or verify production-bug lesson before row repair is considered closed",
    "renderer_requirement": "route to rich-hover renderer/segment requirement; not a gloss closure lane",
    "repair_candidate": "prepare owner-gated repair preview; no live apply from this queue",
    "sarf_nahw_procedure_improvement": "feed sarf/nahw procedure, eval, or drill hardening",
    "controller_reconciliation": "controller must reconcile competing next states before any action queue may proceed",
}


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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


def queue_for_controller_row(row):
    if row["controller_status"] == "needs_controller_reconciliation":
        return "controller_reconciliation"
    return row["primary_route"]


def build_queue_row(row):
    queue_name = queue_for_controller_row(row)
    return {
        "queue_id": "dogfood-next-state-queue:%s:%s" % (queue_name, safe_id(row["wbw_loc"])),
        "audit_scope": "full_corpus_dogfood_next_state_queue",
        "source_reconciliation_packet_id": row["packet_id"],
        "quran_loc": row["quran_loc"],
        "wbw_loc": row["wbw_loc"],
        "surface": row["surface"],
        "current_gloss": row.get("current_gloss"),
        "classification": row["classification"],
        "queue_name": queue_name,
        "primary_route": row["primary_route"],
        "routes": row["routes"],
        "controller_status": row["controller_status"],
        "route_requires_controller_reconciliation": row["controller_status"] == "needs_controller_reconciliation",
        "requires_two_vote": row["requires_two_vote"],
        "may_apply_live": False,
        "owner_apply_authorized": False,
        "live_mutation_allowed": False,
        "public_boundary_status": row["public_boundary_status"],
        "public_leak_detected": False,
        "next_state_counts": row["next_state_counts"],
        "review_lanes": row["review_lanes"],
        "review_row_count": row["review_row_count"],
        "evidence_count": len(row.get("evidence") or []),
        "controller_reason": row["controller_reason"],
        "recommended_next_action": row["recommended_next_action"],
        "next_gate": NEXT_GATES[queue_name],
    }


def build_queues(rows):
    if not rows:
        raise SystemExit("reconciliation input has zero rows; refusing vacuous queue build")
    queue_rows = [build_queue_row(row) for row in rows]
    return sorted(queue_rows, key=lambda row: (row["queue_name"], row["quran_loc"], row["wbw_loc"]))


def summarize(queue_rows, source_files=None):
    if not queue_rows:
        raise SystemExit("queue output has zero rows; refusing vacuous summary")
    queue_counts = Counter(row["queue_name"] for row in queue_rows)
    class_counts = Counter(row["classification"] for row in queue_rows)
    status_counts = Counter(row["controller_status"] for row in queue_rows)
    route_counts = Counter()
    lane_counts = Counter()
    for row in queue_rows:
        route_counts.update(row["routes"])
        lane_counts.update(row["review_lanes"])
    conflict_count = queue_counts.get("controller_reconciliation", 0)
    return {
        "audit_scope": "full_corpus_dogfood_next_state_queues",
        "may_apply_live": False,
        "owner_apply_authorized": False,
        "live_mutation_allowed": False,
        "source_files": source_files or [],
        "queue_rows": len(queue_rows),
        "unique_wbw_locs": len({row["wbw_loc"] for row in queue_rows}),
        "rows_requiring_two_vote": sum(1 for row in queue_rows if row["requires_two_vote"]),
        "queue_counts": dict(sorted(queue_counts.items())),
        "classification_counts": dict(sorted(class_counts.items())),
        "controller_status_counts": dict(sorted(status_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "review_lane_counts": dict(sorted(lane_counts.items())),
        "controller_reconciliation_count": conflict_count,
        "public_leak_count": sum(1 for row in queue_rows if row["public_leak_detected"]),
        "not_claimed": [
            "live Qamus mutation",
            "WBW rebuild",
            "hover coverage improvement",
            "owner-gated apply authorization",
            "parse-key propagation approval",
        ],
    }


def validate_queue_row(row, errors, path, line_no):
    keys = set(row)
    missing = [key for key in REQUIRED_KEYS if key not in keys]
    extra = sorted(keys - set(REQUIRED_KEYS))
    if missing:
        errors.append("%s:%s: missing keys: %s" % (path, line_no, ", ".join(missing)))
    if extra:
        errors.append("%s:%s: unexpected keys: %s" % (path, line_no, ", ".join(extra)))
    if row.get("audit_scope") != "full_corpus_dogfood_next_state_queue":
        errors.append("%s:%s: bad audit_scope" % (path, line_no))
    if not str(row.get("queue_id", "")).startswith("dogfood-next-state-queue:"):
        errors.append("%s:%s: bad queue_id" % (path, line_no))
    if not str(row.get("source_reconciliation_packet_id", "")).startswith("dogfood-lane-packet:"):
        errors.append("%s:%s: bad source_reconciliation_packet_id" % (path, line_no))
    if not QURAN_RE.match(str(row.get("quran_loc", ""))):
        errors.append("%s:%s: bad quran_loc" % (path, line_no))
    if not WBW_RE.match(str(row.get("wbw_loc", ""))):
        errors.append("%s:%s: bad wbw_loc" % (path, line_no))
    if row.get("queue_name") not in QUEUE_NAMES:
        errors.append("%s:%s: bad queue_name %r" % (path, line_no, row.get("queue_name")))
    if row.get("primary_route") not in ACTION_QUEUE_NAMES:
        errors.append("%s:%s: bad primary_route %r" % (path, line_no, row.get("primary_route")))
    routes = row.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append("%s:%s: routes must be a non-empty list" % (path, line_no))
        routes = []
    for route in routes:
        if route not in ACTION_QUEUE_NAMES:
            errors.append("%s:%s: bad route %r" % (path, line_no, route))
    if row.get("primary_route") not in routes:
        errors.append("%s:%s: primary_route must be in routes" % (path, line_no))
    if row.get("controller_status") not in reconciler.ALLOWED_STATUS:
        errors.append("%s:%s: bad controller_status %r" % (path, line_no, row.get("controller_status")))
    conflict = row.get("controller_status") == "needs_controller_reconciliation"
    if row.get("route_requires_controller_reconciliation") is not conflict:
        errors.append("%s:%s: route_requires_controller_reconciliation mismatch" % (path, line_no))
    if conflict and row.get("queue_name") != "controller_reconciliation":
        errors.append("%s:%s: conflict rows must be held in controller_reconciliation queue" % (path, line_no))
    if not conflict and row.get("queue_name") != row.get("primary_route"):
        errors.append("%s:%s: routed rows must enter their primary_route queue" % (path, line_no))
    if row.get("may_apply_live") is not False:
        errors.append("%s:%s: may_apply_live must be false" % (path, line_no))
    if row.get("owner_apply_authorized") is not False:
        errors.append("%s:%s: owner_apply_authorized must be false" % (path, line_no))
    if row.get("live_mutation_allowed") is not False:
        errors.append("%s:%s: live_mutation_allowed must be false" % (path, line_no))
    if row.get("public_leak_detected") is not False:
        errors.append("%s:%s: public_leak_detected must be false" % (path, line_no))
    if not boundary_validator._is_source_clean_boundary(row.get("public_boundary_status")):
        errors.append("%s:%s: public_boundary_status must be source-clean" % (path, line_no))
    if not isinstance(row.get("requires_two_vote"), bool):
        errors.append("%s:%s: requires_two_vote must be boolean" % (path, line_no))
    if not isinstance(row.get("next_state_counts"), dict) or not row.get("next_state_counts"):
        errors.append("%s:%s: next_state_counts must be non-empty object" % (path, line_no))
    if not isinstance(row.get("review_lanes"), list) or not row.get("review_lanes"):
        errors.append("%s:%s: review_lanes must be non-empty list" % (path, line_no))
    if not isinstance(row.get("review_row_count"), int) or row.get("review_row_count") < 1:
        errors.append("%s:%s: review_row_count must be positive integer" % (path, line_no))
    if not isinstance(row.get("evidence_count"), int) or row.get("evidence_count") < 1:
        errors.append("%s:%s: evidence_count must be positive integer" % (path, line_no))
    for text_key in ("surface", "controller_reason", "recommended_next_action", "next_gate"):
        if not str(row.get(text_key, "")).strip():
            errors.append("%s:%s: %s must be non-empty" % (path, line_no, text_key))


def validate_queue_file(path, expect_min_rows=1):
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
            validate_queue_row(row, errors, path, line_no)
    if rows < expect_min_rows:
        errors.append("%s: expected at least %s rows, got %s" % (path, expect_min_rows, rows))
    return {"path": path, "rows": rows, "errors": errors}


def validate_reconciliation_inputs(paths, expect_min_rows=1):
    results = [reconciler.validate_reconciliation_file(path, expect_min_rows) for path in paths]
    errors = [err for result in results for err in result["errors"]]
    if errors:
        raise SystemExit(json.dumps({"ok": False, "errors": errors[:100], "files": results}, indent=2))
    return results


def build_from_paths(paths, expect_min_rows=1):
    validation = validate_reconciliation_inputs(paths, expect_min_rows)
    source_rows = []
    for path in paths:
        source_rows.extend(read_jsonl(path))
    queue_rows = build_queues(source_rows)
    return queue_rows, validation


def write_queue_outputs(out_dir, queue_rows):
    os.makedirs(out_dir, exist_ok=True)
    grouped = defaultdict(list)
    for row in queue_rows:
        grouped[row["queue_name"]].append(row)
    written = []
    for queue_name, rows in sorted(grouped.items()):
        path = os.path.join(out_dir, "queue_%s.jsonl" % safe_id(queue_name))
        write_jsonl(path, rows)
        written.append(path)
    summary_path = os.path.join(out_dir, "next-state-queue-summary.json")
    write_json(summary_path, summarize(queue_rows, written))
    return written, summary_path


def self_test():
    routed = {
        "packet_id": "dogfood-lane-packet:wbw_33_63_1",
        "quran_loc": "quran:33:63:1",
        "wbw_loc": "wbw:33:63:1",
        "surface": "يَسْأَلُكَ",
        "current_gloss": "to ask, question",
        "classification": "known_defect",
        "controller_status": "routed",
        "primary_route": "repair_candidate",
        "routes": ["repair_candidate"],
        "next_state_counts": {"repair_candidate": 1},
        "review_lanes": ["sarf-component-reviewer"],
        "review_row_count": 1,
        "requires_two_vote": True,
        "may_apply_live": False,
        "public_boundary_status": "source_clean:qamus/authored/en",
        "controller_reason": "all validated review rows agree on one next state",
        "recommended_next_action": "route to repair_candidate queue; no live apply is authorized",
        "evidence": [
            {
                "review_lane": "sarf-component-reviewer",
                "next_state": "repair_candidate",
                "classification": "known_defect",
                "detected_issue": "attached object pronoun omitted",
                "procedure_or_rule": "sarf/procedures/clitic-and-host-morphology.md",
                "confidence": "high",
                "requires_two_vote": True,
            }
        ],
    }
    conflict = dict(routed)
    conflict.update(
        {
            "packet_id": "dogfood-lane-packet:wbw_86_14_1",
            "quran_loc": "quran:86:14:1",
            "wbw_loc": "wbw:86:14:1",
            "surface": "وَمَا",
            "current_gloss": None,
            "classification": "needs_nahw_review",
            "controller_status": "needs_controller_reconciliation",
            "primary_route": "blocker_queue_row",
            "routes": ["blocker_queue_row", "drill_regression_fixture"],
            "next_state_counts": {"blocker_queue_row": 1, "drill_regression_fixture": 1},
            "review_lanes": ["nahw-function-reviewer", "learner-explanation-reviewer"],
            "review_row_count": 2,
            "controller_reason": "multiple validated review lanes propose different next states",
            "recommended_next_action": "controller must reconcile routes before owner-gated apply packet",
        }
    )
    with tempfile.TemporaryDirectory(prefix="dogfood-next-state-") as td:
        recon_path = os.path.join(td, "reconciled.jsonl")
        write_jsonl(recon_path, [routed, conflict])
        queue_rows, _ = build_from_paths([recon_path])
        queue_path = os.path.join(td, "queues.jsonl")
        write_jsonl(queue_path, queue_rows)
        result = validate_queue_file(queue_path, expect_min_rows=2)
        if result["errors"]:
            raise SystemExit("self-test validation failed: %s" % result["errors"])
        summary = summarize(queue_rows)
        if summary["queue_counts"].get("repair_candidate") != 1:
            raise SystemExit("self-test did not route repair candidate: %s" % summary)
        if summary["queue_counts"].get("controller_reconciliation") != 1:
            raise SystemExit("self-test did not quarantine conflict: %s" % summary)
        written, summary_path = write_queue_outputs(os.path.join(td, "out"), queue_rows)
        if len(written) != 2 or not os.path.exists(summary_path):
            raise SystemExit("self-test output files missing")
    print("PASS - full-corpus dogfood next-state queue builder self-test")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*")
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--out-dir", help="write queue_<name>.jsonl files plus summary")
    parser.add_argument("--out-jsonl", help="write all queue rows to one JSONL file")
    parser.add_argument("--out-summary", help="write pretty JSON summary")
    parser.add_argument("--validate-jsonl", help="validate an existing next-state queue JSONL file")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.validate_jsonl:
        result = validate_queue_file(args.validate_jsonl, args.expect_min_rows)
        output = {"ok": not result["errors"], "files": [result]}
        if result["errors"]:
            output["errors"] = result["errors"][:100]
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        if result["errors"]:
            raise SystemExit(1)
        return

    paths = args.jsonl or [RECONCILIATION_SAMPLE]
    queue_rows, validation = build_from_paths(paths, args.expect_min_rows)
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, queue_rows)
    written = []
    if args.out_dir:
        written, _ = write_queue_outputs(args.out_dir, queue_rows)
    summary = summarize(queue_rows, source_files=[item["path"] for item in validation] + written)
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out_summary:
        write_json(args.out_summary, summary)
    print(text, end="")


if __name__ == "__main__":
    main()
