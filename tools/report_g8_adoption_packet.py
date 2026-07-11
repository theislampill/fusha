#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report public and lineage adoption differences for a dry-run compile packet.

The deployed baseline may be legacy-shaped: canonical location plus renderer fields,
without row_id, binding_id, or canonical_payload_id. Public meaning and internal
lineage are therefore compared independently. This tool writes only to an explicit
output directory; it never adopts or deploys rows.
"""
import argparse
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.compile_canonical_hover_whitelist_packet import (  # noqa: E402
    canonical_public_loc, public_content, public_content_bytes,
)
from tools.largelexicon_common import match_forbidden_labels  # noqa: E402
from tools.validate_public_private_boundary import FORBIDDEN_LABELS  # noqa: E402

CLASSIFICATIONS = (
    "no_op", "append", "modify", "remove_or_unrepresented", "conflict", "blocked")
LINEAGE_FIELDS = ("row_id", "canonical_payload_id", "binding_id", "entry_id", "card_id",
                  "qword_row_id")
SAMPLE_DIMENSIONS = (
    "vn_tranche_or_surah_band", "payload_type", "segmentation_count", "grammar_class",
    "source_entry_card_multiplicity", "conflict_status")


def read_jsonl(path):
    if not path or not os.path.exists(path):
        return []
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path, value):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _loc_index(rows, failures, label):
    result = {}
    for row in rows:
        loc = canonical_public_loc(row)
        if not loc:
            failures.append("%s_missing_canonical_loc" % label)
            continue
        if loc in result:
            failures.append("%s_duplicate_canonical_loc:%s" % (label, loc))
            continue
        result[loc] = row
    return result


def _lineage_signature(row, binding_rows):
    direct = {field: row.get(field) for field in LINEAGE_FIELDS if row.get(field) is not None}
    bindings = []
    for binding in binding_rows:
        values = {field: binding.get(field) for field in LINEAGE_FIELDS
                  if binding.get(field) is not None}
        if values:
            bindings.append(values)
    bindings.sort(key=lambda value: json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return {"row": direct, "bindings": bindings}


def _is_blocked(conflict):
    explicit = conflict.get("classification") or conflict.get("status")
    if explicit in ("blocked", "conflict"):
        return explicit == "blocked"
    reason = str(conflict.get("reason") or "").lower()
    return any(token in reason for token in (
        "blocked", "validation", "missing", "incomplete", "drift", "unapproved",
        "without-replacement"))


def _rate(count, denominator):
    return {"numerator": count, "denominator": denominator,
            "value": (count / denominator if denominator else 0.0)}


def _stratum_values(row, bindings_by_loc, mapping_method):
    loc = row["canonical_wbw_loc"]
    after = row.get("public_after") or row.get("public_before") or {}
    segments = after.get("segments") or []
    packet_meta = row.get("packet_metadata") or {}
    if mapping_method == "vn_mapping":
        loc_stratum = packet_meta.get("vn_tranche")
    else:
        try:
            surah = int(loc.split(":", 1)[0])
            lower = ((surah - 1) // 10) * 10 + 1
            loc_stratum = "surah-%03d-%03d" % (lower, lower + 9)
        except (TypeError, ValueError):
            loc_stratum = "surah-unknown"
    grammar = sorted({str(segment.get("qg_class") or "unknown") for segment in segments})
    loc_bindings = bindings_by_loc.get(loc, [])
    entries = {binding.get("entry_id") for binding in loc_bindings if binding.get("entry_id")}
    cards = {binding.get("card_id") for binding in loc_bindings if binding.get("card_id")}
    return {
        "vn_tranche_or_surah_band": loc_stratum,
        "payload_type": packet_meta.get("payload_type") or (
            "segmented" if len(segments) > 1 else "single_segment"),
        "segmentation_count": str(len(segments)),
        "grammar_class": "+".join(grammar) if grammar else "none",
        "source_entry_card_multiplicity": "entries:%d/cards:%d" % (len(entries), len(cards)),
        "conflict_status": "conflict" if row.get("conflict_or_block_reasons") else "clear",
    }


def _samples(rowdiff, bindings_by_loc, sample_size):
    eligible = [row for row in rowdiff if row["classification"] in ("append", "modify")]
    mapping_method = ("vn_mapping" if eligible and all(
        (row.get("packet_metadata") or {}).get("vn_tranche") for row in eligible)
                      else "surah_band_fallback")
    strata = {}
    for row in eligible:
        values = _stratum_values(row, bindings_by_loc, mapping_method)
        for dimension in SAMPLE_DIMENSIONS:
            key = (dimension, values[dimension])
            strata.setdefault(key, []).append(row["canonical_wbw_loc"])
    output = []
    for (dimension, stratum), locs in sorted(strata.items()):
        locs = sorted(locs)
        output.append({
            "dimension": dimension, "stratum": stratum, "available": len(locs),
            "selected": min(len(locs), sample_size), "canonical_wbw_locs": locs[:sample_size],
        })
    return {"sample_size_per_stratum": sample_size, "stratification_method": mapping_method,
            "strata": output}


def build_adoption_report(packet, bindings, conflicts, repair_candidates, baseline,
                          compile_report=None, sample_size=25):
    failures = []
    packet_by_loc = _loc_index(packet, failures, "packet")
    baseline_by_loc = _loc_index(baseline, failures, "baseline")
    bindings_by_loc = {}
    for binding in bindings:
        loc = canonical_public_loc(binding)
        if not loc:
            failures.append("binding_missing_canonical_loc")
            continue
        bindings_by_loc.setdefault(loc, []).append(binding)
    conflicts_by_loc = {}
    for conflict in conflicts:
        loc = canonical_public_loc(conflict)
        if not loc:
            failures.append("conflict_missing_canonical_loc")
            continue
        conflicts_by_loc.setdefault(loc, []).append(conflict)

    required_report = {"source_head", "input_artifacts", "schemas_consumed", "schemas_produced",
                       "compiler_version", "packet_sha256"}
    if compile_report is not None:
        for field in sorted(required_report - set(compile_report)):
            failures.append("compile_report_missing_%s" % field)

    all_locs = sorted(set(packet_by_loc) | set(baseline_by_loc) | set(conflicts_by_loc))
    rowdiff = []
    leak_false_blocks = 0
    exception_counts = {}
    for loc in all_locs:
        before = baseline_by_loc.get(loc)
        after = packet_by_loc.get(loc)
        loc_conflicts = conflicts_by_loc.get(loc, [])
        reasons = sorted({str(item.get("reason") or "unknown") for item in loc_conflicts})
        if loc_conflicts:
            classification = "blocked" if any(_is_blocked(item) for item in loc_conflicts) else "conflict"
            for reason in reasons:
                exception_counts[reason] = exception_counts.get(reason, 0) + 1
        elif before is None:
            classification = "append"
        elif after is None:
            classification = "remove_or_unrepresented"
        elif public_content_bytes(before) == public_content_bytes(after):
            classification = "no_op"
        else:
            classification = "modify"

        before_lineage = _lineage_signature(before or {}, [])
        after_lineage = _lineage_signature(after or {}, bindings_by_loc.get(loc, []))
        lineage_change = before_lineage != after_lineage and bool(
            after_lineage["row"] or after_lineage["bindings"])
        public_before = public_content(before) if before is not None else None
        public_after = public_content(after) if after is not None else None
        public_for_scan = public_after if public_after is not None else public_before
        if (any("leak" in reason.lower() or "forbidden" in reason.lower() for reason in reasons)
                and not match_forbidden_labels(
                    json.dumps(public_for_scan, ensure_ascii=False).lower(), FORBIDDEN_LABELS)):
            leak_false_blocks += 1
        rowdiff.append({
            "canonical_wbw_loc": loc,
            "classification": classification,
            "public_before": public_before,
            "public_after": public_after,
            "lineage_change": lineage_change,
            "conflict_or_block_reasons": reasons,
            "packet_metadata": {
                key: after.get(key) for key in ("payload_type", "vn_tranche")
                if after is not None and after.get(key) is not None},
        })

    denominator = len(rowdiff)
    class_counts = {name: sum(row["classification"] == name for row in rowdiff)
                    for name in CLASSIFICATIONS}
    lineage_only = sum(row["classification"] == "no_op" and row["lineage_change"]
                       for row in rowdiff)
    summary = {
        "total_locations": denominator,
        "classifications": {name: {"count": count, "rate": _rate(count, denominator)}
                            for name, count in class_counts.items()},
        "lineage_only_improvement": {
            "count": lineage_only, "rate": _rate(lineage_only, denominator)},
        "exception_classes": {
            name: {"count": count, "rate": _rate(count, denominator)}
            for name, count in sorted(exception_counts.items())},
        "leak_false_block": {
            "count": leak_false_blocks, "rate": _rate(leak_false_blocks, denominator)},
        "schema_join_failures": {
            "count": len(failures), "rate": _rate(len(failures), denominator),
            "reasons": sorted(failures)},
        "repair_candidate_count": len(repair_candidates),
        "public_change": {
            "count": class_counts["append"] + class_counts["modify"]
                     + class_counts["remove_or_unrepresented"],
            "rate": _rate(class_counts["append"] + class_counts["modify"]
                          + class_counts["remove_or_unrepresented"], denominator),
        },
    }
    samples = _samples(rowdiff, bindings_by_loc, sample_size)
    summary["stratification_method"] = samples["stratification_method"]
    return rowdiff, summary, samples


def self_test():
    def public_row(loc, gloss, legacy=False, **extra):
        row = {
            "surface": "كتاب", "src": "qamus", "kind": "authored", "lang": "en",
            "public_gloss": gloss, "contextual_phrase_gloss": None, "morphline": "STEM",
            "segments": [{"role": "STEM", "surface": "كتاب", "qg_class": "noun",
                          "gloss": gloss}],
            "learner_explanation": "noun",
        }
        # gloss text must stay comparable across shapes for the NF-T6-3 case
        if extra.get("segments"):
            for seg in extra["segments"]:
                seg.setdefault("gloss_contribution", gloss)
        row["loc" if legacy else "canonical_wbw_loc"] = loc
        row.update(extra)
        return row

    packet = [
        public_row("1:1:1", "book", row_id="chw:one", canonical_payload_id="chp:one"),
        public_row("1:1:2", "volume", row_id="chw:two", canonical_payload_id="chp:two"),
        public_row("1:1:3", "new book", row_id="chw:three", canonical_payload_id="chp:three"),
        public_row("1:1:7", "same", row_id="chw:seven", canonical_payload_id="chp:seven"),
    ]
    baseline = [
        public_row("1:1:1", "book", legacy=True),
        public_row("1:1:3", "old book", legacy=True),
        public_row("1:1:4", "removed", legacy=True),
        public_row("1:1:5", "clean", legacy=True),
        public_row("1:1:6", "blocked", legacy=True),
        # NF-T6-1 mixed-shape case: deployed rows carry the wbw: prefix; identical public
        # content must still join and classify no_op (red-first vs the unfixed loc key).
        # NF-T6-3: the deployed segment shape (class: "qg-noun", gloss_contribution) must
        # project semantically equal to the contract shape (qg_class: "noun", gloss).
        public_row("wbw:1:1:7", "same", legacy=True,
                   segments=[{"role": "STEM", "surface": "كتاب",
                              "class": "qg-noun", "gloss_contribution": "same",
                              "label": "N", "segment_index": 0}]),
    ]
    bindings = [{"canonical_wbw_loc": "1:1:1", "binding_id": "chb:one",
                 "entry_id": "entry-one", "card_id": "card-one", "qword_row_id": "qword-one"}]
    conflicts = [
        {"canonical_wbw_loc": "1:1:5", "reason": "public-leak", "classification": "conflict"},
        {"canonical_wbw_loc": "1:1:6", "reason": "owner-blocked", "classification": "blocked"},
    ]
    rowdiff, summary, samples = build_adoption_report(
        packet, bindings, conflicts, [], baseline, sample_size=1)
    counts = {name: summary["classifications"][name]["count"] for name in CLASSIFICATIONS}
    expected = {name: 1 for name in CLASSIFICATIONS}
    expected["no_op"] = 2  # incl. the NF-T6-1 wbw:-prefixed mixed-shape no_op
    if counts != expected:
        print("SELF-TEST FAIL classifications", counts); return 1
    noop = next(row for row in rowdiff if row["classification"] == "no_op")
    if not noop["lineage_change"] or summary["lineage_only_improvement"]["count"] != 2:
        # both no_ops (bare and wbw:-prefixed legacy rows) gain internal lineage records
        print("SELF-TEST FAIL legacy lineage-only", noop); return 1
    if summary["leak_false_block"]["count"] != 1:
        print("SELF-TEST FAIL leak false-block", summary); return 1
    if samples["stratification_method"] != "surah_band_fallback" or not samples["strata"]:
        print("SELF-TEST FAIL stratification", samples); return 1
    print("PASS - G8 adoption reporter self-test (six classes, legacy no-op, lineage-only)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Report dry-run canonical hover adoption differences.")
    parser.add_argument("--compile-dir")
    parser.add_argument("--baseline")
    parser.add_argument("--outdir")
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not (args.compile_dir and args.baseline and args.outdir):
        parser.error("--compile-dir, --baseline, and --outdir are required unless --self-test")
    if args.sample_size < 1:
        parser.error("--sample-size must be at least 1")
    compile_dir = args.compile_dir
    report_path = os.path.join(compile_dir, "compile_report.json")
    with io.open(report_path, encoding="utf-8") as handle:
        compile_report = json.load(handle)
    full_packet_path = os.path.join(compile_dir, "whitelist_packet.jsonl")
    packet_path = (full_packet_path if os.path.exists(full_packet_path)
                   else os.path.join(compile_dir, "whitelist_append_replace.jsonl"))
    rowdiff, summary, samples = build_adoption_report(
        read_jsonl(packet_path),
        read_jsonl(os.path.join(compile_dir, "occurrence_bindings.jsonl")),
        read_jsonl(os.path.join(compile_dir, "whitelist_conflicts.jsonl")),
        read_jsonl(os.path.join(compile_dir, "repair_candidates.jsonl")),
        read_jsonl(args.baseline), compile_report=compile_report, sample_size=args.sample_size)
    os.makedirs(args.outdir, exist_ok=True)
    write_jsonl(os.path.join(args.outdir, "g8-rowdiff.jsonl"), rowdiff)
    write_json(os.path.join(args.outdir, "g8-summary.json"), summary)
    write_json(os.path.join(args.outdir, "g8-samples.json"), samples)
    print(json.dumps({"locations": len(rowdiff), "outdir": args.outdir}, sort_keys=True))


if __name__ == "__main__":
    main()
