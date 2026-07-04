#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard the public Qamus entry count against accidental drift.

The public dataset is 2092 entries: 1045 nouns + 947 verbs + 100 particles.
Internal projection/index layers (e.g. the largelexicon qword crosswalk, which
projects 117,117 qword rows) count OTHER things and must never be mistaken for
the public entry count. An earlier ledger note of "2096 (+4 drift)" was such a
projection/transient artifact — NOT four missing public entries. Live == public
== 2092 (verified 2026-07-04). See docs/qamus-public-entry-count-policy.md.

This guard asserts, on the real dataset:
  * entries.jsonl line count == entry-manifest.json entry_count
  * sum(section_counts) == entry_count
  * section counts recomputed from entries.jsonl == manifest section_counts
  * no section outside {noun, verb, particle}
  * entry_count == EXPECTED_TOTAL and section split == EXPECTED_SECTIONS
    (the tripwire — bump these CONSCIOUSLY only on owner-approved authoring).

It complements the existing check_regressions line "entries.jsonl has 2092
entries" by adding the section-split + manifest-consistency dimensions (a swap
that keeps the total at 2092 would slip past a total-only check).
Read-only; deterministic.
"""
import argparse
import collections
import io
import json
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATASET = os.path.join(ROOT, "qamus", "data", "current")

# The authoritative public count. Bump CONSCIOUSLY (with owner approval) only when
# real new public entries are exported — never to chase an internal projection figure.
EXPECTED_TOTAL = 2092
EXPECTED_SECTIONS = {"noun": 1045, "particle": 100, "verb": 947}
ALLOWED_SECTIONS = {"noun", "verb", "particle"}


def consistency_errors(n_lines, manifest, recomputed, expected_total, expected_sections):
    """Pure logic (exercised by --self-test with synthetic values)."""
    errors = []
    m = manifest.get("entry_count")
    s = manifest.get("section_counts") or {}
    if m != n_lines:
        errors.append("manifest entry_count %r != entries.jsonl lines %d" % (m, n_lines))
    if sum(s.values()) != m:
        errors.append("sum(section_counts)=%d != entry_count %r" % (sum(s.values()), m))
    if recomputed != s:
        errors.append("recomputed section counts %s != manifest section_counts %s" % (dict(recomputed), s))
    stray = set(s) - ALLOWED_SECTIONS
    if stray:
        errors.append("section(s) outside {noun,verb,particle}: %s" % sorted(stray))
    if m != expected_total:
        errors.append("public entry count drifted: %r != expected %d "
                      "(if intentional, bump EXPECTED_TOTAL consciously; do NOT match an internal projection)"
                      % (m, expected_total))
    if s != expected_sections:
        errors.append("section split drifted: %s != expected %s" % (s, expected_sections))
    return errors


def validate_dataset(dataset_dir):
    entries_path = os.path.join(dataset_dir, "entries.jsonl")
    manifest_path = os.path.join(dataset_dir, "entry-manifest.json")
    if not os.path.exists(entries_path):
        return ["entries.jsonl missing at %s" % entries_path]
    if not os.path.exists(manifest_path):
        return ["entry-manifest.json missing at %s" % manifest_path]
    n_lines = 0
    recomputed = collections.Counter()
    with io.open(entries_path, encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line:
                continue
            n_lines += 1
            try:
                recomputed[json.loads(line).get("section", "?")] += 1
            except Exception as exc:
                return ["entries.jsonl line %d bad JSON (%s)" % (n_lines, exc)]
    with io.open(manifest_path, encoding="utf-8") as h:
        manifest = json.load(h)
    return consistency_errors(n_lines, manifest, dict(recomputed), EXPECTED_TOTAL, EXPECTED_SECTIONS)


def self_test():
    exp_total = 3
    exp_sections = {"noun": 2, "verb": 1}
    good = {"entry_count": 3, "section_counts": {"noun": 2, "verb": 1}}
    if consistency_errors(3, good, {"noun": 2, "verb": 1}, exp_total, exp_sections):
        print("SELF-TEST FAIL good dataset:", consistency_errors(3, good, {"noun": 2, "verb": 1}, exp_total, exp_sections))
        return 1
    # manifest count vs lines mismatch
    if not any("!= entries.jsonl lines" in e for e in
               consistency_errors(4, good, {"noun": 2, "verb": 1}, exp_total, exp_sections)):
        print("SELF-TEST FAIL lines-mismatch not caught"); return 1
    # section swap that keeps the total (2 nouns -> 1 noun + 1 particle): total stays 3
    swap = {"entry_count": 3, "section_counts": {"noun": 1, "verb": 1, "particle": 1}}
    if not any("section split drifted" in e for e in
               consistency_errors(3, swap, {"noun": 1, "verb": 1, "particle": 1}, exp_total, exp_sections)):
        print("SELF-TEST FAIL section-swap not caught"); return 1
    # recomputed vs manifest mismatch
    if not any("recomputed section counts" in e for e in
               consistency_errors(3, good, {"noun": 1, "verb": 2}, exp_total, exp_sections)):
        print("SELF-TEST FAIL recomputed-mismatch not caught"); return 1
    # stray section
    stray = {"entry_count": 3, "section_counts": {"noun": 2, "adverb": 1}}
    if not any("outside {noun,verb,particle}" in e for e in
               consistency_errors(3, stray, {"noun": 2, "adverb": 1}, exp_total, exp_sections)):
        print("SELF-TEST FAIL stray-section not caught"); return 1
    # total drift
    if not any("public entry count drifted" in e for e in
               consistency_errors(4, {"entry_count": 4, "section_counts": {"noun": 3, "verb": 1}},
                                   {"noun": 3, "verb": 1}, exp_total, exp_sections)):
        print("SELF-TEST FAIL total-drift not caught"); return 1
    print("PASS - public entry-count guard self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Guard the public Qamus entry count (2092) against drift.")
    parser.add_argument("dataset_dir", nargs="?", default=DEFAULT_DATASET,
                        help="dataset dir with entries.jsonl + entry-manifest.json (default: qamus/data/current)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    errors = validate_dataset(args.dataset_dir)
    if errors:
        print("FAIL:")
        for err in errors:
            print("  - " + err)
        raise SystemExit(1)
    print("PASS - public entry count is %d (%s), manifest-consistent" % (EXPECTED_TOTAL, EXPECTED_SECTIONS))


if __name__ == "__main__":
    main()
