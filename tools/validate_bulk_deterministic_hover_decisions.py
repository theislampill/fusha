#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a bulk deterministic hover decision batch and provenance sidecar."""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                             "pending-source-triangulation-table.jsonl")

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK_RE = re.compile(r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
                     r"tanzil|saheeh|sahih|tafsir|ocr|informed_by)\b", re.I)
PUBLIC_FIELDS = ("loc", "gloss", "surface", "key", "state_id", "src", "kind", "lang", "decision_state")


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def deterministic_by_loc(table_path):
    rows = {}
    for row in read_jsonl(table_path):
        if row.get("deterministic_resolvable") is True:
            rows[row.get("loc")] = row
    return rows


def validate_files(batch_path, provenance_path=None, table_path=DEFAULT_TABLE):
    errors = []
    public_rows = read_jsonl(batch_path)
    provenance_rows = read_jsonl(provenance_path) if provenance_path else []
    expected = deterministic_by_loc(table_path) if table_path else {}
    locs = []

    for i, row in enumerate(public_rows, 1):
        loc = row.get("loc")
        locs.append(loc)
        if not loc or not LOC_RE.match(str(loc)):
            errors.append("line %d: bad loc %r" % (i, loc))
        if not (row.get("gloss") or "").strip():
            errors.append("%s: empty gloss" % loc)
        if row.get("src") != "qamus" or row.get("kind") != "authored":
            errors.append("%s: public record not {src:qamus,kind:authored}" % loc)
        public_blob = json.dumps({k: row.get(k) for k in PUBLIC_FIELDS if k in row}, ensure_ascii=False)
        if LEAK_RE.search(public_blob):
            errors.append("%s: external source name/provenance leak in public fields" % loc)
        if row.get("decision_state") != "bulk_deterministic_auto_rule":
            errors.append("%s: decision_state must be bulk_deterministic_auto_rule" % loc)
        if expected:
            src = expected.get(loc)
            if not src:
                errors.append("%s: public row not present as deterministic source-table row" % loc)
            elif row.get("gloss") != src.get("proposed_gloss"):
                errors.append("%s: gloss does not match source-table proposed_gloss" % loc)

    if len(locs) != len(set(locs)):
        errors.append("duplicate locs in public batch")
    if expected and set(locs) != set(expected):
        errors.append("public loc set != deterministic source-table loc set (%d vs %d)" %
                      (len(set(locs)), len(expected)))

    if provenance_path:
        prov_locs = [row.get("loc") for row in provenance_rows]
        if set(prov_locs) != set(locs):
            errors.append("provenance loc set != public loc set")
        if len(provenance_rows) != len(public_rows):
            errors.append("provenance row count %d != public %d" %
                          (len(provenance_rows), len(public_rows)))
        for row in provenance_rows:
            loc = row.get("loc")
            if row.get("review_status") != "auto_rule_certified":
                errors.append("%s: review_status != auto_rule_certified" % loc)
            if row.get("gate") != "auto_rule":
                errors.append("%s: provenance gate != auto_rule" % loc)
            if row.get("votes") != 0:
                errors.append("%s: deterministic provenance votes must be 0" % loc)
            if row.get("public_provenance_clean") is not True:
                errors.append("%s: provenance public_provenance_clean must be true" % loc)
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    parser.add_argument("--provenance")
    parser.add_argument("--table", default=DEFAULT_TABLE)
    args = parser.parse_args()
    errors = validate_files(args.batch, args.provenance, args.table)
    print("checked %d deterministic hover decision(s)" % len(read_jsonl(args.batch)))
    if errors:
        print("FAIL:")
        for error in errors[:60]:
            print("  -", error)
        if len(errors) > 60:
            print("  ... %d more" % (len(errors) - 60))
        sys.exit(1)
    print("PASS — deterministic hover batch public-clean + provenance/table parity OK")


if __name__ == "__main__":
    main()
