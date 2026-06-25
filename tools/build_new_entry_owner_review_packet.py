#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build owner-review packet reports for new-entry proposals."""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROPOSALS = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                                 "new_entry_proposals_batch_002.jsonl")
DEFAULT_JSON = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                            "new-entry-owner-review-packet-002.json")
DEFAULT_MD = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                          "new-entry-owner-review-packet-002.md")


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def dump_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def build_packet(proposals_path=DEFAULT_PROPOSALS, out_json=DEFAULT_JSON, out_md=DEFAULT_MD):
    proposals = read_jsonl(proposals_path)
    proposals.sort(key=lambda row: (-(row.get("expected_coverage_unlock") or row.get("occurrences") or 0),
                                    row.get("root") or ""))
    total_unlock = sum(row.get("expected_coverage_unlock") or row.get("occurrences") or 0
                       for row in proposals)
    payload = {
        "_generator": "tools/build_new_entry_owner_review_packet.py",
        "source_proposals": os.path.relpath(proposals_path, ROOT),
        "proposal_count": len(proposals),
        "coverage_unlock": total_unlock,
        "status": "owner_gated_review_only",
        "proposals": proposals,
    }
    dump_json(out_json, payload)

    lines = [
        "# New Entry Owner Review Packet 002",
        "",
        "Owner-gated review only. No live entry IDs are allocated, no live Qamus data is changed, and definition drafts remain blank for owner authoring.",
        "",
        "| metric | value |",
        "|---|---:|",
        "| proposals | %d |" % len(proposals),
        "| potential token unlock | %d |" % total_unlock,
        "",
        "## High-Yield Proposals",
        "",
        "| rank | root | unlock | headword candidate | sample locs | blocker |",
        "|---:|---|---:|---|---|---|",
    ]
    for index, row in enumerate(proposals[:50], 1):
        sample_locs = ", ".join(row.get("example_locs") or [])
        lines.append("| %d | `%s` | %d | `%s` | %s | %s |" % (
            index,
            row.get("root") or "",
            row.get("expected_coverage_unlock") or row.get("occurrences") or 0,
            row.get("headword_candidate") or "",
            sample_locs,
            row.get("why_existing_insufficient") or "",
        ))
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposals", default=DEFAULT_PROPOSALS)
    parser.add_argument("--out-json", default=DEFAULT_JSON)
    parser.add_argument("--out-md", default=DEFAULT_MD)
    args = parser.parse_args()
    summary = build_packet(args.proposals, args.out_json, args.out_md)
    print(json.dumps({
        "proposal_count": summary["proposal_count"],
        "coverage_unlock": summary["coverage_unlock"],
        "out_json": os.path.relpath(args.out_json, ROOT),
        "out_md": os.path.relpath(args.out_md, ROOT),
    }, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
