#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build chunked high-throughput two-vote request packets from the triangulation table.

This does not certify or apply decisions. It prepares bounded sarf-primary and
nahw-primary review inputs for rows that already passed the table validator and
still require independent agreement.
"""
import argparse
import json
import os
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                             "pending-source-triangulation-table.jsonl")
DEFAULT_OUT = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                           "bulk_twovote_requests_batch_001.jsonl")
DEFAULT_MANIFEST = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                                "bulk-two-vote-requests-batch-001.json")
DEFAULT_MD = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                          "bulk-two-vote-requests-batch-001.md")

LANE_PRIORITY = {
    "form_variant": 0,
    "token_irab": 1,
    "verb_clitic": 2,
    "host_lexeme": 3,
}
RISK_PRIORITY = {"low": 0, "medium": 1, "high": 2, "scholar": 3}
VOTE_LENSES = ["sarf-primary", "nahw-primary"]
REQUESTED_OUTPUT_FIELDS = [
    "decision",
    "concise_authored_gloss",
    "sarf_reasoning",
    "nahw_reasoning",
    "reason_agreement_key",
    "blocker_if_rejected",
]


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def request_from_row(row):
    return {
        "loc": row["loc"],
        "surface_ar": row.get("surface_ar") or "",
        "key": row.get("strict_nk") or row.get("nk") or "",
        "ayah_context": row.get("ayah_context") or "",
        "qac": {"root": row.get("qac_root"), "pos": row.get("qac_pos")},
        "qamus_entry_candidate": {
            "id": row.get("qamus_entry_candidate"),
            "headword": row.get("qamus_entry_headword"),
            "match_type": row.get("qamus_entry_match_type"),
            "pos_agreement": row.get("pos_agreement"),
        },
        "suggested_lane": row.get("suggested_lane"),
        "gate": row.get("gate"),
        "risk": row.get("risk"),
        "sarf_procedure": row.get("sarf_procedure"),
        "nahw_procedure": row.get("nahw_procedure"),
        "known_blocker": row.get("blocker_if_not_resolved"),
        "vote_lenses": VOTE_LENSES,
        "requested_output": {
            "decision": "approve | reject | pending",
            "concise_authored_gloss": "",
            "sarf_reasoning": "",
            "nahw_reasoning": "",
            "reason_agreement_key": "",
            "blocker_if_rejected": "",
        },
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
    }


def read_excluded_locs(paths):
    locs = set()
    for path in paths or []:
        if not path:
            continue
        for row in read_jsonl(path):
            loc = row.get("loc")
            if loc:
                locs.add(str(loc))
    return locs


def _lane_set(values):
    return set(v for v in (values or []) if v)


def build_requests(table_path=DEFAULT_TABLE, out_path=DEFAULT_OUT, manifest_path=DEFAULT_MANIFEST,
                   limit=1000, chunk_size=40, report_md_path=None, exclude_loc_paths=None,
                   only_lanes=None, exclude_lanes=None):
    excluded_locs = read_excluded_locs(exclude_loc_paths)
    only_lanes = _lane_set(only_lanes)
    exclude_lanes = _lane_set(exclude_lanes)
    rows = []
    for row in read_jsonl(table_path):
        if row.get("gate") != "two_vote":
            continue
        if row.get("public_payload_allowed") != "yes":
            continue
        if row.get("risk") not in ("low", "medium"):
            continue
        if str(row.get("loc") or "") in excluded_locs:
            continue
        lane = row.get("suggested_lane")
        if only_lanes and lane not in only_lanes:
            continue
        if exclude_lanes and lane in exclude_lanes:
            continue
        rows.append(row)
    rows.sort(key=lambda r: (
        LANE_PRIORITY.get(r.get("suggested_lane"), 99),
        RISK_PRIORITY.get(r.get("risk"), 99),
        r.get("loc") or "",
    ))
    selected = rows[:limit]
    requests = [request_from_row(row) for row in selected]
    write_jsonl(out_path, requests)

    chunk_dir = Path(out_path).with_suffix("")
    chunk_dir = chunk_dir.parent / (chunk_dir.name + "_chunks")
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunks = []
    for index in range(0, len(requests), chunk_size):
        chunk_no = index // chunk_size + 1
        chunk_path = chunk_dir / ("chunk_%03d.jsonl" % chunk_no)
        write_jsonl(str(chunk_path), requests[index:index + chunk_size])
        chunks.append(os.path.relpath(chunk_path, ROOT))

    lane_counts = {}
    for row in selected:
        lane_counts[row.get("suggested_lane")] = lane_counts.get(row.get("suggested_lane"), 0) + 1
    summary = {
        "_generator": "tools/build_bulk_two_vote_requests.py",
        "source_table": os.path.relpath(table_path, ROOT),
        "request_file": os.path.relpath(out_path, ROOT),
        "rows": len(requests),
        "eligible_rows": len(rows),
        "limit": limit,
        "chunk_size": chunk_size,
        "exclude_loc_files": [os.path.relpath(path, ROOT) for path in (exclude_loc_paths or [])],
        "excluded_locs": len(excluded_locs),
        "only_lanes": sorted(only_lanes),
        "exclude_lanes": sorted(exclude_lanes),
        "chunks": chunks,
        "by_lane": lane_counts,
        "validator": "tools/validate_bulk_two_vote_requests.py",
        "reconciliation_tool": "tools/reconcile_bulk_two_vote_results.py",
        "vote_lenses": VOTE_LENSES,
        "requested_output_fields": REQUESTED_OUTPUT_FIELDS,
        "status": "requests_only_not_certified",
    }
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    if report_md_path:
        request_rel = summary["request_file"]
        table_rel = summary["source_table"]
        manifest_rel = os.path.relpath(manifest_path, ROOT)
        out_stem = Path(out_path).stem
        batch_label = "batch %s" % out_stem.rsplit("batch_", 1)[1] if "batch_" in out_stem else out_stem
        lines = [
            "# Bulk two-vote request %s" % batch_label,
            "",
            "Request packet only. No votes have been cast, no decisions are approved, and no live apply occurred.",
            "",
            "| metric | value |",
            "|---|---:|",
            "| selected request rows | %d |" % len(requests),
            "| eligible low/medium two-vote rows | %d |" % len(rows),
            "| chunk size | %d |" % chunk_size,
            "| chunks | %d |" % len(chunks),
            "",
            "## Review Contract",
            "",
            "- Required lenses: `%s`." % "`, `".join(VOTE_LENSES),
            "- Required vote fields: `%s`." % "`, `".join(REQUESTED_OUTPUT_FIELDS),
            "- Reconcile only when both votes agree on `decision`, `concise_authored_gloss`, and `reason_agreement_key`.",
            "- Validator: `python3 tools/validate_bulk_two_vote_requests.py %s --table %s --manifest %s`." %
            (request_rel, table_rel, manifest_rel),
            "- Reconciler: `python3 tools/reconcile_bulk_two_vote_results.py --requests %s --votes <votes.jsonl>`." %
            request_rel,
            "",
            "## By Lane",
            "",
        ]
        for lane, count in sorted(lane_counts.items()):
            lines.append("- `%s`: **%d**" % (lane, count))
        with open(report_md_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-table", default=DEFAULT_TABLE)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--report-md", default=DEFAULT_MD)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--chunk-size", type=int, default=40)
    parser.add_argument("--exclude-locs", action="append", default=[],
                        help="JSONL file containing loc fields to skip. May be passed multiple times.")
    parser.add_argument("--only-lane", action="append", default=[],
                        help="Restrict output to this suggested_lane. May be passed multiple times.")
    parser.add_argument("--exclude-lane", action="append", default=[],
                        help="Skip this suggested_lane. May be passed multiple times.")
    args = parser.parse_args()
    summary = build_requests(args.from_table, args.out, args.manifest, args.limit, args.chunk_size, args.report_md,
                             exclude_loc_paths=args.exclude_locs, only_lanes=args.only_lane,
                             exclude_lanes=args.exclude_lane)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
