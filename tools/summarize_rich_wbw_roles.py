#!/usr/bin/env python3
"""Summarize rich WBW segment roles from a live shadow graph run."""

import argparse
import collections
import json
import os
import sys
import tempfile


EXPLICITLY_GATED = {
    "addressee_bridge",
    "adjectival_state",
    "circumstantial_state",
    "conjunction",
    "object_pronoun",
    "particle",
    "prefix_cause_fa",
    "prefix_comitative_waw",
    "prefix_oath",
    "prefix_preposition",
    "preposition",
    "possessive_pronoun",
    "relative_particle",
    "resumption_particle",
    "result_particle",
    "subordinating_particle",
    "subject_pronoun",
    "vocative_particle",
}

EXPLICITLY_ALLOWLISTED = {
    "adjective",
    "case_marker",
    "definite_article",
    "imperfect_prefix",
    "mood_marker",
    "noun",
    "proper_noun",
    "stem",
    "verb",
    "verb_stem",
}

STRICT_UNSAFE_LANES = {"propagation_safe"}
STRICT_UNSAFE_GATES = {"auto_safe"}


def load_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                try:
                    yield line_no, json.loads(line)
                except Exception as exc:
                    raise SystemExit("%s:%d: invalid JSON: %s" % (path, line_no, exc))


def role_policy(role):
    if role in EXPLICITLY_GATED:
        return "explicitly_gated"
    if role in EXPLICITLY_ALLOWLISTED:
        return "explicitly_allowlisted"
    return "unknown"


def add_sample(bucket, row, segment, lane, gates):
    if len(bucket["samples"]) >= 5:
        return
    parse_obj = row.get("canonical_parse_object") or {}
    locs = row.get("seen_locs") or []
    bucket["samples"].append({
        "loc": parse_obj.get("quran_loc") or (locs[0] if locs else None),
        "surface": parse_obj.get("surface_raw"),
        "segment": segment.get("text") or segment.get("surface"),
        "lane": lane,
        "gates": gates,
        "parse": row.get("id"),
    })


def summarize(parse_keys_path):
    roles = {}
    total_parse_rows = 0
    rich_parse_rows = 0
    for _line_no, row in load_jsonl(parse_keys_path):
        total_parse_rows += 1
        parse_obj = row.get("canonical_parse_object") or {}
        segments = parse_obj.get("token_internal_segments") or []
        if not segments:
            continue
        rich_parse_rows += 1
        family_size = int(row.get("family_size") or max(1, len(row.get("seen_locs") or [])))
        lane = row.get("family_class") or parse_obj.get("gate") or "unknown"
        gates = row.get("gates") or []
        for segment in segments:
            if not isinstance(segment, dict):
                role = "unknown"
            else:
                role = segment.get("role") or "unknown"
            bucket = roles.setdefault(role, {
                "role": role,
                "policy": role_policy(role),
                "segment_occurrences": 0,
                "parse_key_rows": 0,
                "token_locations": 0,
                "lanes": collections.Counter(),
                "gates": collections.Counter(),
                "auto_safe_occurrences": 0,
                "propagation_safe_occurrences": 0,
                "samples": [],
            })
            bucket["segment_occurrences"] += family_size
            bucket["parse_key_rows"] += 1
            bucket["token_locations"] += family_size
            bucket["lanes"][lane] += family_size
            for gate in gates:
                bucket["gates"][gate] += family_size
            if lane in STRICT_UNSAFE_LANES:
                bucket["propagation_safe_occurrences"] += family_size
            if STRICT_UNSAFE_GATES.intersection(set(gates)):
                bucket["auto_safe_occurrences"] += family_size
            add_sample(bucket, row, segment if isinstance(segment, dict) else {}, lane, gates)
    rows = []
    for bucket in roles.values():
        bucket["lanes"] = dict(sorted(bucket["lanes"].items()))
        bucket["gates"] = dict(sorted(bucket["gates"].items()))
        rows.append(bucket)
    rows.sort(key=lambda item: item["role"])
    risks = []
    for row in rows:
        if row["policy"] == "unknown":
            risks.append("unknown role: %s" % row["role"])
        if row["policy"] == "explicitly_gated" and row["auto_safe_occurrences"]:
            risks.append("gated role has auto_safe gate: %s (%d)" % (row["role"], row["auto_safe_occurrences"]))
        if row["policy"] == "explicitly_gated" and row["propagation_safe_occurrences"]:
            risks.append("gated role has propagation_safe lane: %s (%d)" % (row["role"], row["propagation_safe_occurrences"]))
    return {
        "parse_keys_path": os.path.abspath(parse_keys_path),
        "total_parse_rows": total_parse_rows,
        "rich_parse_rows": rich_parse_rows,
        "role_count": len(rows),
        "roles": rows,
        "risks": risks,
        "strict_pass": not risks,
    }


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_markdown(path, summary):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Rich WBW Segment Role Taxonomy\n\n")
        handle.write("- parse keys: `%s`\n" % summary["total_parse_rows"])
        handle.write("- rich parse rows: `%s`\n" % summary["rich_parse_rows"])
        handle.write("- observed roles: `%s`\n" % summary["role_count"])
        handle.write("- strict pass: `%s`\n\n" % ("yes" if summary["strict_pass"] else "no"))
        if summary["risks"]:
            handle.write("## Risks\n\n")
            for risk in summary["risks"]:
                handle.write("- %s\n" % risk)
            handle.write("\n")
        handle.write("## Roles\n\n")
        handle.write("| Role | Occurrences | Parse rows | Policy | Lanes | Gates |\n")
        handle.write("|---|---:|---:|---|---|---|\n")
        for row in summary["roles"]:
            lanes = ", ".join("%s=%s" % (k, v) for k, v in row["lanes"].items()) or "-"
            gates = ", ".join("%s=%s" % (k, v) for k, v in row["gates"].items()) or "-"
            handle.write("| `%s` | %d | %d | `%s` | %s | %s |\n" % (
                row["role"],
                row["segment_occurrences"],
                row["parse_key_rows"],
                row["policy"],
                lanes,
                gates,
            ))
        handle.write("\n## Samples\n\n")
        for row in summary["roles"]:
            handle.write("### `%s`\n\n" % row["role"])
            for sample in row["samples"]:
                handle.write("- `%s` `%s` segment `%s` lane `%s` gates `%s`\n" % (
                    sample.get("loc"),
                    sample.get("surface"),
                    sample.get("segment"),
                    sample.get("lane"),
                    ",".join(sample.get("gates") or []),
                ))
            handle.write("\n")


def self_test():
    good_rows = [
        {
            "id": "parse:gated",
            "family_size": 1,
            "family_class": "two_vote_required",
            "gates": ["two_vote_required"],
            "seen_locs": ["quran:22:18:17"],
            "canonical_parse_object": {
                "surface_raw": "وَٱلشَّجَرُ",
                "token_internal_segments": [
                    {"role": "conjunction", "text": "وَ"},
                    {"role": "definite_article", "text": "ٱل"},
                    {"role": "noun", "text": "شَّجَرُ"},
                ],
            },
        },
        {
            "id": "parse:allow",
            "family_size": 1,
            "family_class": "token_only_required",
            "gates": ["auto_safe"],
            "seen_locs": ["quran:4:28:7"],
            "canonical_parse_object": {
                "surface_raw": "ٱلْإِنسَانُ",
                "token_internal_segments": [
                    {"role": "definite_article", "text": "ٱل"},
                    {"role": "noun", "text": "إِنسَانُ"},
                ],
            },
        },
    ]
    bad_rows = [
        {
            "id": "parse:bad",
            "family_size": 1,
            "family_class": "missing_entry",
            "gates": ["auto_safe"],
            "seen_locs": ["quran:4:28:8"],
            "canonical_parse_object": {
                "surface_raw": "ضَعِيفًا",
                "token_internal_segments": [{"role": "adjectival_state", "text": "ضَعِيفًا"}],
            },
        }
    ]
    unknown_rows = [
        {
            "id": "parse:unknown",
            "family_size": 1,
            "family_class": "two_vote_required",
            "gates": ["two_vote_required"],
            "seen_locs": ["quran:1:1:1"],
            "canonical_parse_object": {
                "surface_raw": "x",
                "token_internal_segments": [{"role": "surprise_role", "text": "x"}],
            },
        }
    ]
    with tempfile.TemporaryDirectory(prefix="rich-role-taxonomy-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        unknown = os.path.join(td, "unknown.jsonl")
        for path, rows in ((good, good_rows), (bad, bad_rows), (unknown, unknown_rows)):
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        good_summary = summarize(good)
        if not good_summary["strict_pass"]:
            print("SELF-TEST FAIL: good taxonomy should pass: %r" % good_summary["risks"])
            return 1
        bad_summary = summarize(bad)
        if bad_summary["strict_pass"] or not any("adjectival_state" in risk for risk in bad_summary["risks"]):
            print("SELF-TEST FAIL: gated auto-safe role was not caught: %r" % bad_summary["risks"])
            return 1
        unknown_summary = summarize(unknown)
        if unknown_summary["strict_pass"] or not any("surprise_role" in risk for risk in unknown_summary["risks"]):
            print("SELF-TEST FAIL: unknown role was not caught: %r" % unknown_summary["risks"])
            return 1
    print("PASS — rich WBW segment role taxonomy self-test")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-dir")
    parser.add_argument("--parse-keys")
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    parse_keys = args.parse_keys
    if not parse_keys and args.shadow_dir:
        parse_keys = os.path.join(args.shadow_dir, "parse-keys.jsonl")
    if not parse_keys:
        raise SystemExit("provide --shadow-dir or --parse-keys")
    if not os.path.exists(parse_keys):
        raise SystemExit("missing parse keys: %s" % parse_keys)
    summary = summarize(parse_keys)
    if args.out_json:
        write_json(args.out_json, summary)
    if args.out_md:
        write_markdown(args.out_md, summary)
    print(json.dumps({
        "rich_parse_rows": summary["rich_parse_rows"],
        "role_count": summary["role_count"],
        "strict_pass": summary["strict_pass"],
        "risks": summary["risks"],
    }, ensure_ascii=False, sort_keys=True))
    if args.strict and not summary["strict_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
