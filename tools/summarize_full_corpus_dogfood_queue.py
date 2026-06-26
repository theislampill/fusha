#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize full-corpus hover dogfood rows into review queues.

This is a read-only reporting tool. It consumes the full-corpus dogfood audit
JSONL and, optionally, dogfood-derived production-bug lessons. It does not
author hovers, mutate live Qamus, rebuild WBW artifacts, or certify coverage.
"""

import argparse
import io
import json
import os
import tempfile
from collections import Counter, defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOGFOOD_SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_hover_dogfood_audit.sample.jsonl")
DEFAULT_LESSON_SAMPLE = os.path.join(ROOT, "qamus", "examples", "dogfood_production_bug_lesson.sample.jsonl")


QUEUE_DEFS = {
    "known_defects": {
        "selector": lambda row: row.get("dogfood_class") == "known_defect",
        "next_action": "review as graph-addressed repair candidates; no live apply without owner-gated apply plan",
    },
    "token_only_overrides": {
        "selector": lambda row: row.get("dogfood_class") == "token_only_override",
        "next_action": "prepare token-addressed override review; do not propagate by surface or parse family",
    },
    "pending_blockers": {
        "selector": lambda row: row.get("dogfood_class") == "pending/blocker",
        "next_action": "keep in blocker queue with exact blocker and sarf/nahw route",
    },
    "populated_uncertified": {
        "selector": lambda row: row.get("dogfood_class") == "populated_uncertified",
        "next_action": "audit populated string hovers; visible text alone is not dogfood certification",
    },
    "rich_certified": {
        "selector": lambda row: row.get("dogfood_class") == "rich_certified",
        "next_action": "treat as certified only for the recorded exact token and gate evidence",
    },
    "renderer_requirements": {
        "selector": lambda row: "renderer_rich_hover_requirement" in set(row.get("routes") or []),
        "next_action": "route to rich-hover segment/rendering requirement; do not treat as gloss closure",
    },
    "repair_candidates": {
        "selector": lambda row: "repair_candidate" in set(row.get("routes") or []),
        "next_action": "turn into owner-gated repair preview before any entry/sense or token decision",
    },
    "production_bug_lessons": {
        "selector": lambda row: "production_bug_lesson" in set(row.get("routes") or []),
        "next_action": "emit or review production-bug lessons that update sarf/nahw drills and regressions",
    },
    "sarf_nahw_procedure_improvements": {
        "selector": lambda row: "sarf_nahw_procedure_improvement" in set(row.get("routes") or []),
        "next_action": "feed procedure/eval/drill hardening; do not only patch the row",
    },
    "drill_regression_fixtures": {
        "selector": lambda row: "drill_regression_fixture" in set(row.get("routes") or []),
        "next_action": "convert to learner-facing drill plus regression fixture when bug class is stable",
    },
}


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise SystemExit("%s:%d invalid JSON: %s" % (path, line_no, exc))
    return rows


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def compact_example(row):
    linkage = row.get("entry_linkage") or {}
    certification = row.get("certification") or {}
    return {
        "quran_loc": row.get("quran_loc"),
        "wbw_loc": row.get("wbw_loc"),
        "surface": row.get("surface"),
        "current_visible_gloss": row.get("current_visible_gloss"),
        "dogfood_class": row.get("dogfood_class"),
        "detectors": row.get("detectors") or [],
        "routes": row.get("routes") or [],
        "parse_id": linkage.get("parse_id"),
        "parse_gate": linkage.get("parse_gate"),
        "parse_family_class": linkage.get("parse_family_class"),
        "entry": linkage.get("resolved_qamus_entry_id"),
        "sense": linkage.get("resolved_sense_id"),
        "decision_ids": linkage.get("decision_ids") or [],
        "blocker": row.get("learner_breakdown_blocker"),
        "requires_two_vote": certification.get("requires_two_vote"),
        "rich_rendered": row.get("rich_rendered"),
        "public_leak_detected": (row.get("public_boundary") or {}).get("public_leak_detected"),
    }


def lesson_summary(lesson_rows):
    counts = Counter()
    examples = defaultdict(list)
    for row in lesson_rows:
        bug_class = row.get("bug_class") or "unknown"
        counts[bug_class] += 1
        if len(examples[bug_class]) < 5:
            examples[bug_class].append({
                "target_address": row.get("target_address"),
                "source_addresses": row.get("source_addresses") or [],
                "visible_bad_hover": row.get("visible_bad_hover"),
                "gate": row.get("gate"),
                "entry_sense": row.get("entry_sense"),
            })
    return {
        "count": len(lesson_rows),
        "bug_class_counts": dict(sorted(counts.items())),
        "examples_by_bug_class": {k: v for k, v in sorted(examples.items())},
    }


def summarize(dogfood_rows, lesson_rows=None, sample_limit=5):
    if not dogfood_rows:
        raise SystemExit("dogfood audit has zero rows; refusing vacuous summary")
    lesson_rows = lesson_rows or []

    class_counts = Counter(row.get("dogfood_class") or "unknown" for row in dogfood_rows)
    presence_counts = Counter(row.get("hover_presence") or "unknown" for row in dogfood_rows)
    route_counts = Counter()
    detector_counts = Counter()
    gate_counts = Counter()
    family_class_counts = Counter()
    blocker_counts = Counter()
    public_leak_count = 0
    rich_rendered_count = 0

    for row in dogfood_rows:
        route_counts.update(row.get("routes") or [])
        detector_counts.update(row.get("detectors") or [])
        linkage = row.get("entry_linkage") or {}
        gate_counts[linkage.get("parse_gate") or "unknown"] += 1
        family_class_counts[linkage.get("parse_family_class") or "unknown"] += 1
        blocker = row.get("learner_breakdown_blocker")
        if blocker:
            blocker_counts[blocker] += 1
        if row.get("rich_rendered"):
            rich_rendered_count += 1
        if (row.get("public_boundary") or {}).get("public_leak_detected"):
            public_leak_count += 1

    queues = {}
    for queue_name, spec in sorted(QUEUE_DEFS.items()):
        rows = [row for row in dogfood_rows if spec["selector"](row)]
        queues[queue_name] = {
            "count": len(rows),
            "next_action": spec["next_action"],
            "examples": [compact_example(row) for row in rows[:sample_limit]],
        }

    unresolved = class_counts.get("pending/blocker", 0)
    populated_uncertified = class_counts.get("populated_uncertified", 0)
    string_only_risk = populated_uncertified + class_counts.get("string_correct_but_not_rich", 0)
    known_or_override = class_counts.get("known_defect", 0) + class_counts.get("token_only_override", 0)

    return {
        "audit_scope": "full_corpus_hover_dogfood_queue_summary",
        "identity_boundary": {
            "token_identity": "quran:S:A:W",
            "hover_identity": "wbw:S:A:W",
            "parse_key_role": "grammar-family key only; never primary identity",
            "live_mutation_allowed": False,
        },
        "row_count": len(dogfood_rows),
        "rich_rendered_count": rich_rendered_count,
        "public_leak_count": public_leak_count,
        "class_counts": dict(sorted(class_counts.items())),
        "hover_presence_counts": dict(sorted(presence_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "detector_counts": dict(sorted(detector_counts.items())),
        "parse_gate_counts": dict(sorted(gate_counts.items())),
        "parse_family_class_counts": dict(sorted(family_class_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "headline": {
            "pending_blockers": unresolved,
            "populated_uncertified_or_string_only": string_only_risk,
            "known_defect_or_token_only_override": known_or_override,
            "rich_certified": class_counts.get("rich_certified", 0),
            "no_public_leak": public_leak_count == 0,
        },
        "queues": queues,
        "production_bug_lessons": lesson_summary(lesson_rows),
        "not_claimed": [
            "hover coverage improvement",
            "grammatical correctness completion",
            "live Qamus mutation",
            "WBW rebuild",
            "parse-key propagation approval",
        ],
    }


def write_markdown(path, summary):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Full-Corpus Hover Dogfood Queue Summary\n\n")
        handle.write("This is a read-only dogfood queue report. It is not a hover coverage claim.\n\n")
        handle.write("## Headline\n\n")
        for key, value in sorted(summary["headline"].items()):
            handle.write("- `%s`: `%s`\n" % (key, value))
        handle.write("\n## Class Counts\n\n")
        for key, value in summary["class_counts"].items():
            handle.write("- `%s`: `%s`\n" % (key, value))
        handle.write("\n## Route Counts\n\n")
        for key, value in summary["route_counts"].items():
            handle.write("- `%s`: `%s`\n" % (key, value))
        handle.write("\n## Detector Counts\n\n")
        if summary["detector_counts"]:
            for key, value in summary["detector_counts"].items():
                handle.write("- `%s`: `%s`\n" % (key, value))
        else:
            handle.write("- none observed\n")
        handle.write("\n## Queues\n\n")
        for queue_name, queue in summary["queues"].items():
            handle.write("### %s\n\n" % queue_name)
            handle.write("- count: `%s`\n" % queue["count"])
            handle.write("- next action: %s\n" % queue["next_action"])
            for example in queue["examples"]:
                handle.write(
                    "- `%s` / `%s` surface `%s` class `%s` detectors `%s`\n"
                    % (
                        example.get("quran_loc"),
                        example.get("wbw_loc"),
                        example.get("surface"),
                        example.get("dogfood_class"),
                        example.get("detectors"),
                    )
                )
            handle.write("\n")
        handle.write("## Production Bug Lessons\n\n")
        handle.write("- rows: `%s`\n" % summary["production_bug_lessons"]["count"])
        for key, value in summary["production_bug_lessons"]["bug_class_counts"].items():
            handle.write("- `%s`: `%s`\n" % (key, value))
        handle.write("\n## Not Claimed\n\n")
        for item in summary["not_claimed"]:
            handle.write("- %s\n" % item)


def run_self_test():
    rows = read_jsonl(DEFAULT_DOGFOOD_SAMPLE)
    lessons = read_jsonl(DEFAULT_LESSON_SAMPLE)
    summary = summarize(rows, lessons, sample_limit=3)
    if summary["row_count"] != 3:
        print("SELF-TEST FAIL: expected 3 sample rows")
        return 1
    if summary["class_counts"].get("rich_certified") != 1:
        print("SELF-TEST FAIL: rich_certified count")
        return 1
    if summary["queues"]["known_defects"]["count"] != 1:
        print("SELF-TEST FAIL: known defect queue")
        return 1
    if summary["queues"]["pending_blockers"]["count"] != 1:
        print("SELF-TEST FAIL: pending blocker queue")
        return 1
    if summary["queues"]["production_bug_lessons"]["count"] != 1:
        print("SELF-TEST FAIL: production bug lesson route queue")
        return 1
    if summary["public_leak_count"] != 0:
        print("SELF-TEST FAIL: public leak count")
        return 1
    if summary["production_bug_lessons"]["bug_class_counts"].get("verb_object_suffix_omitted") != 1:
        print("SELF-TEST FAIL: joined production bug lesson count")
        return 1
    example = summary["queues"]["known_defects"]["examples"][0]
    if example["quran_loc"] != "quran:33:63:1" or example["wbw_loc"] != "wbw:33:63:1":
        print("SELF-TEST FAIL: exact addresses preserved")
        return 1
    if "live Qamus mutation" not in summary["not_claimed"]:
        print("SELF-TEST FAIL: non-claim boundary")
        return 1
    with tempfile.TemporaryDirectory(prefix="dogfood-queue-summary-") as td:
        out_json = os.path.join(td, "summary.json")
        out_md = os.path.join(td, "summary.md")
        write_json(out_json, summary)
        write_markdown(out_md, summary)
        if "Full-Corpus Hover Dogfood Queue Summary" not in io.open(out_md, encoding="utf-8").read():
            print("SELF-TEST FAIL: markdown output")
            return 1
        roundtrip = json.load(io.open(out_json, encoding="utf-8"))
        if roundtrip.get("row_count") != 3:
            print("SELF-TEST FAIL: json output")
            return 1
    print("PASS — full-corpus dogfood queue summarizer self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dogfood-jsonl", default=DEFAULT_DOGFOOD_SAMPLE)
    parser.add_argument("--bug-lessons-jsonl")
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    parser.add_argument("--sample-limit", type=int, default=5)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        raise SystemExit(run_self_test())

    dogfood_rows = read_jsonl(args.dogfood_jsonl)
    lesson_rows = read_jsonl(args.bug_lessons_jsonl) if args.bug_lessons_jsonl else []
    summary = summarize(dogfood_rows, lesson_rows, sample_limit=args.sample_limit)
    if args.out_json:
        write_json(args.out_json, summary)
    if args.out_md:
        write_markdown(args.out_md, summary)
    print(json.dumps({
        "row_count": summary["row_count"],
        "class_counts": summary["class_counts"],
        "route_counts": summary["route_counts"],
        "public_leak_count": summary["public_leak_count"],
        "lesson_rows": summary["production_bug_lessons"]["count"],
    }, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — full-corpus dogfood queue summarized")


if __name__ == "__main__":
    main()
