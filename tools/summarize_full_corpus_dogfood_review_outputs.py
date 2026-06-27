#!/usr/bin/env python3
"""Summarize bounded full-corpus dogfood review outputs.

The subagent review files are read-only routing evidence. This summarizer
validates them, deduplicates by exact packet/token address, and reports next
state disagreements for controller reconciliation. It does not author hovers,
mutate live Qamus, rebuild WBW, or claim coverage/correctness.
"""

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict

import validate_full_corpus_dogfood_review_outputs as review_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_review_output.sample.jsonl")


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                row["_source_file"] = path
                rows.append(row)
    return rows


def summarize(paths, expect_min_rows=1):
    validation = [review_validator.validate_file(path, expect_min_rows) for path in paths]
    errors = [err for result in validation for err in result["errors"]]
    if errors:
        return {
            "ok": False,
            "error_count": len(errors),
            "errors": errors[:100],
            "files": validation,
        }

    rows = []
    for path in paths:
        rows.extend(read_jsonl(path))

    by_packet = defaultdict(list)
    by_wbw = defaultdict(list)
    for row in rows:
        by_packet[row["packet_id"]].append(row)
        by_wbw[row["wbw_loc"]].append(row)

    def conflicts(grouped, key_name):
        out = []
        for key, group in grouped.items():
            next_states = sorted({row["next_state"] for row in group})
            lanes = sorted({row["review_lane"] for row in group})
            classes = sorted({row["classification"] for row in group})
            if len(next_states) > 1:
                out.append(
                    {
                        key_name: key,
                        "row_count": len(group),
                        "next_states": next_states,
                        "review_lanes": lanes,
                        "classifications": classes,
                        "surfaces": sorted({row["surface"] for row in group}),
                    }
                )
        return sorted(out, key=lambda item: (-item["row_count"], item[key_name]))

    next_state_counts = Counter(row["next_state"] for row in rows)
    lane_counts = Counter(row["review_lane"] for row in rows)
    class_counts = Counter(row["classification"] for row in rows)
    issue_counts = Counter(row["detected_issue"] for row in rows)
    action_counts = Counter(row["recommended_next_action"] for row in rows)

    return {
        "ok": True,
        "may_apply_live": False,
        "audit_scope": "bounded_full_corpus_dogfood_review_outputs",
        "files": validation,
        "total_rows": len(rows),
        "unique_packets": len(by_packet),
        "unique_wbw_locs": len(by_wbw),
        "rows_requiring_two_vote": sum(1 for row in rows if row["requires_two_vote"]),
        "review_lane_counts": dict(sorted(lane_counts.items())),
        "classification_counts": dict(sorted(class_counts.items())),
        "next_state_counts": dict(sorted(next_state_counts.items())),
        "top_detected_issues": issue_counts.most_common(25),
        "top_recommended_actions": action_counts.most_common(25),
        "packet_next_state_conflict_count": len(conflicts(by_packet, "packet_id")),
        "wbw_next_state_conflict_count": len(conflicts(by_wbw, "wbw_loc")),
        "packet_next_state_conflicts": conflicts(by_packet, "packet_id")[:50],
        "wbw_next_state_conflicts": conflicts(by_wbw, "wbw_loc")[:50],
        "controller_note": (
            "A next-state conflict is not a failure by itself; it marks rows "
            "where the controller must reconcile cross-lane review findings "
            "before any owner-gated apply packet can exist."
        ),
    }


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
        "evidence_summary": "exact-addressed row preserves the suffix-pronoun defect for review",
        "procedure_or_rule": "sarf/procedures/clitic-and-host-morphology.md",
        "recommended_next_action": "build token-only repair candidate; do not apply live",
        "public_boundary_status": "source_clean:qamus/authored/en",
        "confidence": "high",
        "requires_two_vote": True,
        "may_apply_live": False,
    }
    row_b = dict(row_a)
    row_b["review_lane"] = "production-bug-lesson-writer"
    row_b["next_state"] = "production_bug_lesson"
    row_b["recommended_next_action"] = "write production bug lesson; do not apply live"
    with tempfile.TemporaryDirectory(prefix="dogfood-review-summary-") as td:
        path = os.path.join(td, "reviews.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            for row in (row_a, row_b):
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        result = summarize([path])
        if not result["ok"]:
            raise SystemExit("self-test validation failed: %s" % result.get("errors"))
        if result["total_rows"] != 2 or result["unique_wbw_locs"] != 1:
            raise SystemExit("self-test count mismatch: %s" % result)
        if result["wbw_next_state_conflict_count"] != 1:
            raise SystemExit("self-test expected one next-state conflict: %s" % result)
    print("PASS - full-corpus dogfood review-output summarizer self-test")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*")
    parser.add_argument("--expect-min-rows", type=int, default=1)
    parser.add_argument("--out-json", help="write pretty JSON summary to this path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    paths = args.jsonl or [SAMPLE]
    result = summarize(paths, args.expect_min_rows)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
