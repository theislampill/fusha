#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize closure lanes from a built Qamus shadow graph.

This is read-only. It consumes shadow graph artifacts and produces a review
queue summary; it does not inspect, rebuild, or mutate live Qamus data.
"""
import argparse
import io
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict


REQUIRED = [
    "phase1-current-truth.json",
    "token-index.jsonl",
    "parse-keys.jsonl",
    "decision-index.jsonl",
    "blocker-index.jsonl",
]


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception as exc:
                raise SystemExit("%s:%d: bad JSON: %s" % (path, line_no, exc))


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_candidate_statuses(parse_obj):
    joins = parse_obj.get("qamus_entry_candidate_joins") or []
    result = {}
    for join in joins:
        entry = join.get("entry")
        if entry:
            result[entry] = set(join.get("join_status") or [])
    if not result:
        for entry in parse_obj.get("qamus_entry_candidates") or []:
            result[entry] = {"candidate:unspecified"}
    return result


def classify_parse_family(parse_id, parse_obj, tokens):
    candidate_statuses = parse_candidate_statuses(parse_obj)
    candidates = set(candidate_statuses)
    exact = {
        entry
        for entry, statuses in candidate_statuses.items()
        if any(str(status).startswith("exact:") for status in statuses)
    }
    candidate_or_exact = {
        entry
        for entry, statuses in candidate_statuses.items()
        if any(str(status).startswith(("exact:", "candidate:")) for status in statuses)
    }
    blocker = parse_obj.get("blocker")
    gate = parse_obj.get("gate")
    confidence = parse_obj.get("parse_confidence")
    unresolved = [t for t in tokens if t.get("status") != "resolved"]

    if blocker and unresolved:
        return "blocked:%s" % blocker
    if not candidates:
        return "missing_entry"
    if len(candidates) > 1:
        return "quarantine_collision"
    if confidence == "surface_only":
        return "unknown_parse"
    if gate in ("two_vote_required", "human_review_required", "never_auto"):
        return gate
    if len(exact) == 1 and len(tokens) > 1 and not unresolved:
        return "propagation_safe_candidate"
    if len(candidate_or_exact) == 1 and len(tokens) == 1:
        return "token_only_required"
    return "human_review_required"


def lane_action(lane):
    if lane.startswith("blocked:stem_base_unknown"):
        return {
            "scope": "source_entry_or_parser_repair",
            "recommended_action": "repair stem/base mapping before authoring hover",
            "gate": "source_or_owner_review",
        }
    if lane.startswith("blocked:source_entry_unverified"):
        return {
            "scope": "source_entry_repair",
            "recommended_action": "verify Qamus source entry before token decision",
            "gate": "source_review",
        }
    if lane.startswith("blocked:same_surface_polysemy_requires_i3rab"):
        return {
            "scope": "token_only_or_small_family",
            "recommended_action": "classify same-surface polysemy with i'rab/context evidence",
            "gate": "scholar_or_two_vote",
        }
    if lane == "two_vote_required":
        return {
            "scope": "token_or_family_after_votes",
            "recommended_action": "build two-vote review packet with source-addressed reasoning",
            "gate": "two_vote_required",
        }
    if lane == "human_review_required":
        return {
            "scope": "human_review",
            "recommended_action": "review candidate entry/sense/function before propagation",
            "gate": "human_review_required",
        }
    if lane == "quarantine_collision":
        return {
            "scope": "quarantine",
            "recommended_action": "resolve entry/sense/function collision; do not fan out",
            "gate": "human_review_required",
        }
    if lane == "missing_entry":
        return {
            "scope": "entry_creation_or_mapping",
            "recommended_action": "route to owner for missing Qamus entry or mapping repair",
            "gate": "owner_review",
        }
    if lane == "unknown_parse":
        return {
            "scope": "parser_enrichment",
            "recommended_action": "add sarf/nahw evidence before certification",
            "gate": "human_review_required",
        }
    if lane == "propagation_safe_candidate":
        return {
            "scope": "parse_family",
            "recommended_action": "eligible for guarded propagation preview; still require impact list",
            "gate": "auto_safe_with_preview",
        }
    if lane == "token_only_required":
        return {
            "scope": "token_only",
            "recommended_action": "append token-addressed decision only",
            "gate": "token_review",
        }
    return {
        "scope": "review",
        "recommended_action": "review lane before any apply",
        "gate": "human_review_required",
    }


def review_pack_row(parse_id, lane, parse_obj, tokens):
    unresolved = [t for t in tokens if t.get("status") != "resolved"]
    action = lane_action(lane)
    candidate_joins = parse_obj.get("qamus_entry_candidate_joins") or []
    token_locs = [t.get("loc") for t in tokens if t.get("loc")]
    quran_locs = ["quran:%s" % loc for loc in token_locs]
    wbw_locs = ["wbw:%s" % loc for loc in token_locs]
    row = {
        "id": "queue:%s" % parse_id.replace(":", "_"),
        "parse_id": parse_id,
        "lane": lane,
        "scope": action["scope"],
        "recommended_action": action["recommended_action"],
        "required_gate": action["gate"],
        "family_size": len(tokens),
        "resolved_token_count": len(tokens) - len(unresolved),
        "unresolved_token_count": len(unresolved),
        "surface_sample": next((t.get("surface") for t in tokens if t.get("surface")), ""),
        "quran_locs": quran_locs,
        "wbw_locs": wbw_locs,
        "token_sample": [t.get("id") for t in tokens[:10]],
        "candidate_entries": parse_obj.get("qamus_entry_candidates") or [],
        "candidate_join_statuses": [
            {
                "entry": join.get("entry"),
                "join_status": join.get("join_status") or [],
            }
            for join in candidate_joins
        ],
        "parse": {
            "gate": parse_obj.get("gate"),
            "blocker": parse_obj.get("blocker"),
            "decision_status": parse_obj.get("decision_status"),
            "parse_confidence": parse_obj.get("parse_confidence"),
            "pos": parse_obj.get("pos"),
            "root": parse_obj.get("root"),
            "lemma": parse_obj.get("lemma"),
            "particle_function": parse_obj.get("particle_function"),
            "grammar_triggers": parse_obj.get("grammar_triggers") or [],
        },
        "apply_policy": {
            "live_mutation_allowed": False,
            "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
        },
    }
    return row


def summarize(shadow_dir, sample_limit=8):
    missing = [name for name in REQUIRED if not os.path.exists(os.path.join(shadow_dir, name))]
    if missing:
        raise SystemExit("missing required shadow artifacts: %s" % ", ".join(missing))

    truth = read_json(os.path.join(shadow_dir, "phase1-current-truth.json"))
    token_rows = list(read_jsonl(os.path.join(shadow_dir, "token-index.jsonl")))
    decision_rows = list(read_jsonl(os.path.join(shadow_dir, "decision-index.jsonl")))

    parse_by_id = {}
    parse_row_count = 0
    for row in read_jsonl(os.path.join(shadow_dir, "parse-keys.jsonl")):
        parse_row_count += 1
        pid = row.get("id")
        if pid and pid not in parse_by_id:
            parse_by_id[pid] = row.get("parse") or row

    tokens_by_parse = defaultdict(list)
    for token in token_rows:
        tokens_by_parse[token.get("parse_id")].append(token)

    lane_counts = Counter()
    lane_token_counts = Counter()
    blocker_counts = Counter()
    unresolved_samples = defaultdict(list)
    lane_samples = defaultdict(list)
    surface_missing = 0
    surface_present = 0

    for token in token_rows:
        if token.get("surface"):
            surface_present += 1
        else:
            surface_missing += 1
        if token.get("status") != "resolved":
            blocker_counts[token.get("blocker") or "unknown"] += 1

    family_rows = []
    review_rows = []
    for parse_id, tokens in sorted(tokens_by_parse.items()):
        parse_obj = parse_by_id.get(parse_id, {})
        lane = classify_parse_family(parse_id, parse_obj, tokens)
        lane_counts[lane] += 1
        lane_token_counts[lane] += len(tokens)
        unresolved = [t for t in tokens if t.get("status") != "resolved"]
        if unresolved and len(unresolved_samples[lane]) < sample_limit:
            unresolved_samples[lane].extend(unresolved[: sample_limit - len(unresolved_samples[lane])])
        if len(lane_samples[lane]) < sample_limit:
            lane_samples[lane].append({
                "parse_id": parse_id,
                "family_size": len(tokens),
                "surface_sample": next((t.get("surface") for t in tokens if t.get("surface")), ""),
                "token_sample": [t.get("id") for t in tokens[:5]],
                "candidate_entries": parse_obj.get("qamus_entry_candidates") or [],
                "gate": parse_obj.get("gate"),
                "blocker": parse_obj.get("blocker"),
                "parse_confidence": parse_obj.get("parse_confidence"),
            })
        family_rows.append({
            "parse_id": parse_id,
            "lane": lane,
            "family_size": len(tokens),
            "unresolved": len(unresolved),
            "surface_sample": next((t.get("surface") for t in tokens if t.get("surface")), ""),
            "token_sample": [t.get("id") for t in tokens[:5]],
            "candidate_entries": parse_obj.get("qamus_entry_candidates") or [],
            "gate": parse_obj.get("gate"),
            "blocker": parse_obj.get("blocker"),
            "parse_confidence": parse_obj.get("parse_confidence"),
        })
        review_rows.append(review_pack_row(parse_id, lane, parse_obj, tokens))

    result = {
        "shadow_dir": shadow_dir,
        "truth_counts": truth.get("counts") or {},
        "computed": {
            "token_rows": len(token_rows),
            "decision_rows": len(decision_rows),
            "parse_rows": parse_row_count,
            "unique_parse_ids": len(parse_by_id),
            "surface_present": surface_present,
            "surface_missing": surface_missing,
        },
        "lane_counts": dict(sorted(lane_counts.items())),
        "lane_token_counts": dict(sorted(lane_token_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "lane_samples": {k: v for k, v in sorted(lane_samples.items())},
        "unresolved_samples": {
            k: [
                {
                    "id": t.get("id"),
                    "loc": t.get("loc"),
                    "surface": t.get("surface"),
                    "parse_id": t.get("parse_id"),
                    "blocker": t.get("blocker"),
                    "has_wbw_record": t.get("has_wbw_record"),
                }
                for t in v[:sample_limit]
            ]
            for k, v in sorted(unresolved_samples.items())
        },
        "families": family_rows,
        "review_pack": review_rows,
    }
    return result


def write_markdown(path, summary, sample_limit=8):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Shadow Closure Queue Summary\n\n")
        handle.write("Source shadow graph: `%s`\n\n" % summary["shadow_dir"])
        handle.write("## Counts\n\n")
        for key, value in sorted(summary["computed"].items()):
            handle.write("- %s: `%s`\n" % (key, value))
        handle.write("\n## Lane Counts\n\n")
        for lane, count in summary["lane_counts"].items():
            tokens = summary["lane_token_counts"].get(lane, 0)
            handle.write("- `%s`: `%s` parse families / `%s` tokens\n" % (lane, count, tokens))
        handle.write("\n## Pending Blockers\n\n")
        for blocker, count in summary["blocker_counts"].items():
            handle.write("- `%s`: `%s` tokens\n" % (blocker, count))
        handle.write("\n## Lane Samples\n\n")
        for lane, samples in summary["lane_samples"].items():
            handle.write("### %s\n\n" % lane)
            for sample in samples[:sample_limit]:
                handle.write(
                    "- `%s` size `%s` surface `%s` candidates `%s` tokens `%s`\n"
                    % (
                        sample["parse_id"],
                        sample["family_size"],
                        sample["surface_sample"],
                        sample["candidate_entries"][:5],
                        sample["token_sample"],
                    )
                )
            handle.write("\n")


def run_self_test():
    with tempfile.TemporaryDirectory(prefix="shadow-queue-summary-") as td:
        shadow = os.path.join(td, "shadow")
        os.makedirs(shadow)
        write_json(os.path.join(shadow, "phase1-current-truth.json"), {"counts": {"token_universe": 3}})
        write_jsonl(os.path.join(shadow, "token-index.jsonl"), [
            {"id": "quran:1:1:1", "loc": "1:1:1", "surface": "بِسْمِ", "parse_id": "parse:a", "status": "resolved", "blocker": None, "has_wbw_record": True},
            {"id": "quran:1:1:2", "loc": "1:1:2", "surface": "اللَّهِ", "parse_id": "parse:b", "status": "pending", "blocker": "unknown_parse", "has_wbw_record": False},
            {"id": "quran:1:1:3", "loc": "1:1:3", "surface": "الرَّحْمَٰنِ", "parse_id": "parse:c", "status": "resolved", "blocker": None, "has_wbw_record": True},
        ])
        write_jsonl(os.path.join(shadow, "parse-keys.jsonl"), [
            {"id": "parse:a", "parse": {"qamus_entry_candidates": ["qamus:p:one"], "qamus_entry_candidate_joins": [{"entry": "qamus:p:one", "join_status": ["exact:decision_entry"]}], "gate": "auto_safe", "parse_confidence": "candidate", "blocker": None}},
            {"id": "parse:b", "parse": {"qamus_entry_candidates": [], "gate": "human_review_required", "parse_confidence": "surface_only", "blocker": "unknown_parse"}},
            {"id": "parse:c", "parse": {"qamus_entry_candidates": ["qamus:n:one", "qamus:v:two"], "gate": "human_review_required", "parse_confidence": "candidate", "blocker": None}},
        ])
        write_jsonl(os.path.join(shadow, "decision-index.jsonl"), [{"id": "decision:1"}])
        write_jsonl(os.path.join(shadow, "blocker-index.jsonl"), [{"id": "blocker:unknown_parse", "count": 1}])
        summary = summarize(shadow)
        if summary["computed"]["token_rows"] != 3:
            print("SELF-TEST FAIL: token count")
            return 1
        if summary["lane_counts"].get("blocked:unknown_parse") != 1:
            print("SELF-TEST FAIL: blocker lane")
            return 1
        if summary["lane_counts"].get("quarantine_collision") != 1:
            print("SELF-TEST FAIL: collision lane")
            return 1
        pack = summary["review_pack"]
        if not any(row["recommended_action"].startswith("resolve entry") for row in pack):
            print("SELF-TEST FAIL: review pack collision action")
            return 1
        if not all(loc.startswith("quran:") for row in pack for loc in row["quran_locs"]):
            print("SELF-TEST FAIL: review pack quran addresses")
            return 1
        out_md = os.path.join(td, "summary.md")
        write_markdown(out_md, summary)
        if "Shadow Closure Queue Summary" not in io.open(out_md, encoding="utf-8").read():
            print("SELF-TEST FAIL: markdown")
            return 1
        out_pack = os.path.join(td, "review-pack.jsonl")
        write_jsonl(out_pack, pack)
        if sum(1 for _ in read_jsonl(out_pack)) != 3:
            print("SELF-TEST FAIL: review pack jsonl")
            return 1
    print("PASS — shadow closure queue summarizer self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("shadow_dir", nargs="?")
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    parser.add_argument("--families-jsonl")
    parser.add_argument("--review-pack-jsonl")
    parser.add_argument("--review-lane", action="append",
                        help="only emit review-pack rows for this lane; may be repeated")
    parser.add_argument("--review-max-families", type=int,
                        help="cap emitted review-pack families after lane filtering")
    parser.add_argument("--sample-limit", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(run_self_test())
    if not args.shadow_dir:
        parser.error("shadow_dir is required unless --self-test is used")
    summary = summarize(args.shadow_dir, sample_limit=args.sample_limit)
    if args.out_json:
        compact = dict(summary)
        compact.pop("families", None)
        compact.pop("review_pack", None)
        write_json(args.out_json, compact)
    if args.out_md:
        write_markdown(args.out_md, summary, sample_limit=args.sample_limit)
    if args.families_jsonl:
        write_jsonl(args.families_jsonl, summary["families"])
    if args.review_pack_jsonl:
        review_rows = summary["review_pack"]
        if args.review_lane:
            wanted = set(args.review_lane)
            review_rows = [row for row in review_rows if row.get("lane") in wanted]
        if args.review_max_families is not None:
            review_rows = review_rows[:args.review_max_families]
        write_jsonl(args.review_pack_jsonl, review_rows)
    print(json.dumps({
        "computed": summary["computed"],
        "lane_counts": summary["lane_counts"],
        "lane_token_counts": summary["lane_token_counts"],
        "blocker_counts": summary["blocker_counts"],
    }, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — shadow closure queue summarized")


if __name__ == "__main__":
    main()
