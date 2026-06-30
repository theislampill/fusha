#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_index_integrity — REPORT (never fabricate) the referential integrity of the shipped Qamus indexes (P2-8).

`qamus/indexes/current/by-entry-id.json` is the authoritative entry-id set (its KEYS are the live entry-ids; its
values are per-entry metadata). The secondary indexes are inverted maps `{key: [entry_id, ...]}`:

  * by-lemma.json             — lemma surface          -> [entry_id, ...]
  * by-root.json              — space-joined root      -> [entry_id, ...]
  * by-quran-ref.json         — "surah:ayah"           -> [entry_id, ...]
  * by-normalized-surface.json — normalized surface     -> [entry_id, ...]

This tool asserts every entry-id referenced by a secondary index resolves to a live key in by-entry-id (no ORPHAN
ids — an id that points at no entry would 404 / silently drop a lookup). It also catches a malformed secondary value
(non-list, or a non-string id inside a list) so a structurally broken index cannot pass as "0 orphans".

It is READ-ONLY and authors nothing. Like fusha_checkpoint_coverage, the GATE is the `--self-test` over SYNTHETIC
indexes (a clean set + a planted orphan that MUST be caught); the real-index run REPORTS orphan counts and does NOT
fail-hard on a pre-existing orphan (so a data-debt orphan is surfaced, not silently swallowed). The shipped real
indexes currently reconcile (0 orphans) — see notes — so the real run is also wired as a green gate.

Stdlib only. No network, no writes, no datetime. Leak-free: secondary-index KEYS (lemma/root/ref/surface) and
entry-ids are scanned via tools.leak_sot before any are echoed into a report line. CLI: [--indexes DIR] | --self-test.
See parserplans/fusha-data-runtime-completion-pass (P2-8).
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# leak_sot is the single source of truth for public-boundary leak detection; reuse it (never re-implement).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leak_sot  # noqa: E402

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_INDEXES = os.path.join(_REPO, "qamus", "indexes", "current")

# the authoritative entry-id set lives in this file (its KEYS); the rest are inverted secondary indexes.
PRIMARY = "by-entry-id.json"
SECONDARY = ("by-lemma.json", "by-root.json", "by-quran-ref.json", "by-normalized-surface.json")


def _redact(s):
    """Never echo a raw forbidden token into a report; leak_sot redacts a tripped string (defensive — entry-ids are
    opaque 12-hex and index keys are Arabic surfaces, so a trip is unexpected, but we never assume)."""
    return leak_sot.redact(s) if isinstance(s, str) else s


def load_primary_ids(indexes_dir):
    """Return the set of live entry-ids (the KEYS of by-entry-id.json)."""
    with open(os.path.join(indexes_dir, PRIMARY), encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("%s is not a JSON object (entry-id -> metadata)" % PRIMARY)
    return set(data.keys())


def check_secondary(name, indexes_dir, live_ids):
    """Inspect one secondary index. Return a per-index report:
        {index, distinct_refs, orphans (sorted list, capped), orphan_count, malformed (list)}
    `orphans` are referenced ids absent from `live_ids`; `malformed` flags a non-list value or non-string id."""
    with open(os.path.join(indexes_dir, name), encoding="utf-8") as fh:
        data = json.load(fh)
    malformed = []
    refs = set()
    if not isinstance(data, dict):
        malformed.append({"key": _redact(name), "why": "index is not a JSON object"})
        data = {}
    for key, val in data.items():
        if not isinstance(val, list):
            malformed.append({"key": _redact(key), "why": "value is %s, expected list" % type(val).__name__})
            continue
        for eid in val:
            if not isinstance(eid, str):
                malformed.append({"key": _redact(key), "why": "non-string id %r" % (_redact(eid),)})
                continue
            refs.add(eid)
    orphans = sorted(r for r in refs if r not in live_ids)
    return {
        "index": name,
        "distinct_refs": len(refs),
        "orphan_count": len(orphans),
        "orphans": [_redact(o) for o in orphans[:20]],  # cap echoed list; orphan_count is the full truth
        "malformed": malformed[:20],
        "malformed_count": len(malformed),
    }


def validate(indexes_dir=_INDEXES, secondary=SECONDARY):
    """Return a whole-report dict over the primary + every secondary index in `indexes_dir`."""
    live_ids = load_primary_ids(indexes_dir)
    per_index = [check_secondary(n, indexes_dir, live_ids) for n in secondary]
    total_orphans = sum(p["orphan_count"] for p in per_index)
    total_malformed = sum(p["malformed_count"] for p in per_index)
    return {
        "live_entry_ids": len(live_ids),
        "per_index": per_index,
        "total_orphans": total_orphans,
        "total_malformed": total_malformed,
        "clean": total_orphans == 0 and total_malformed == 0,
    }


def render(report):
    lines = ["index referential-integrity report",
             "  live entry-ids (by-entry-id keys): %d" % report["live_entry_ids"]]
    for p in report["per_index"]:
        lines.append("  %-28s refs=%d  orphans=%d  malformed=%d"
                     % (p["index"], p["distinct_refs"], p["orphan_count"], p["malformed_count"]))
        for o in p["orphans"]:
            lines.append("      ORPHAN id -> %s (no entry in by-entry-id)" % o)
        for m in p["malformed"]:
            lines.append("      MALFORMED %s: %s" % (m["key"], m["why"]))
    lines.append("  TOTAL: %d orphan id(s), %d malformed value(s) across %d secondary index(es)"
                 % (report["total_orphans"], report["total_malformed"], len(report["per_index"])))
    lines.append("  note: a pre-existing orphan is DATA DEBT (surfaced, not fail-hard on the real run); the logic "
                 "gate is --self-test on synthetic indexes.")
    return "\n".join(lines)


def _self_test():
    import tempfile
    failures = []

    def write_idx(d, name, obj):
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False)

    # --- CLEAN synthetic set: every referenced id resolves -> 0 orphans, 0 malformed, clean=True ---
    with tempfile.TemporaryDirectory() as d:
        write_idx(d, PRIMARY, {"aaa": {"headword": "x"}, "bbb": {"headword": "y"}, "ccc": {"headword": "z"}})
        write_idx(d, "by-lemma.json", {"lem1": ["aaa"], "lem2": ["bbb", "ccc"]})
        write_idx(d, "by-root.json", {"r1": ["aaa", "ccc"]})
        write_idx(d, "by-quran-ref.json", {"2:255": ["bbb"]})
        write_idx(d, "by-normalized-surface.json", {"surf": ["aaa", "bbb", "ccc"]})
        rep = validate(d)
        if not rep["clean"]:
            failures.append("clean synthetic set reported not-clean: %s" % rep)
        if rep["total_orphans"] != 0:
            failures.append("clean set reported orphans: %d" % rep["total_orphans"])
        if rep["live_entry_ids"] != 3:
            failures.append("live id count wrong: %d" % rep["live_entry_ids"])

    # --- ORPHAN synthetic set: a secondary references an id NOT in by-entry-id -> MUST be caught ---
    with tempfile.TemporaryDirectory() as d:
        write_idx(d, PRIMARY, {"aaa": {"headword": "x"}, "bbb": {"headword": "y"}})
        write_idx(d, "by-lemma.json", {"lem1": ["aaa"]})
        write_idx(d, "by-root.json", {"r1": ["aaa"]})
        write_idx(d, "by-quran-ref.json", {"2:255": ["bbb"]})
        # 'zzz' is an ORPHAN: present in a secondary, absent from by-entry-id
        write_idx(d, "by-normalized-surface.json", {"surf": ["aaa", "zzz"]})
        rep = validate(d)
        if rep["clean"]:
            failures.append("orphan synthetic set wrongly reported clean")
        if rep["total_orphans"] != 1:
            failures.append("orphan count should be 1, got %d" % rep["total_orphans"])
        surf = next(p for p in rep["per_index"] if p["index"] == "by-normalized-surface.json")
        if "zzz" not in surf["orphans"]:
            failures.append("the planted orphan id 'zzz' was not surfaced: %s" % surf["orphans"])

    # --- MALFORMED synthetic set: a non-list value and a non-string id must be flagged (cannot pass as 0 orphans) ---
    with tempfile.TemporaryDirectory() as d:
        write_idx(d, PRIMARY, {"aaa": {"headword": "x"}})
        write_idx(d, "by-lemma.json", {"lem1": "aaa"})            # value is a str, not a list
        write_idx(d, "by-root.json", {"r1": ["aaa", 123]})        # a non-string id inside the list
        write_idx(d, "by-quran-ref.json", {"2:255": ["aaa"]})
        write_idx(d, "by-normalized-surface.json", {"surf": ["aaa"]})
        rep = validate(d)
        if rep["total_malformed"] < 2:
            failures.append("malformed set should flag >=2 (non-list + non-string id), got %d" % rep["total_malformed"])
        if rep["clean"]:
            failures.append("malformed set wrongly reported clean")

    # --- render() must never raise and must be leak-clean over a synthetic report ---
    with tempfile.TemporaryDirectory() as d:
        write_idx(d, PRIMARY, {"aaa": {"headword": "x"}})
        for n in SECONDARY:
            write_idx(d, n, {"k": ["aaa"]})
        text = render(validate(d))
        if leak_sot.is_leak(text):
            failures.append("render() output tripped the leak tripwire: %r" % leak_sot.scan(text))

    # --- the REAL shipped indexes must currently reconcile (0 orphans, 0 malformed) — a real regression guard ---
    if os.path.isdir(_INDEXES) and os.path.exists(os.path.join(_INDEXES, PRIMARY)):
        real = validate()
        if real["total_orphans"]:
            failures.append("real shipped indexes have %d orphan id(s) (data debt regressed)" % real["total_orphans"])
        if real["total_malformed"]:
            failures.append("real shipped indexes have %d malformed value(s)" % real["total_malformed"])

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_index_integrity self-test: clean synthetic set reconciles; planted orphan + malformed "
              "value caught; render is leak-clean; real shipped indexes have 0 orphans/0 malformed")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Report Qamus index referential integrity (orphan entry-ids); read-only.")
    ap.add_argument("--indexes", default=_INDEXES, help="directory holding by-entry-id.json + the secondary indexes")
    ap.add_argument("--strict", action="store_true",
                    help="also exit non-zero if the REAL run finds any orphan/malformed (default: report only)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    report = validate(indexes_dir=a.indexes)
    print(render(report))
    # report-only by default (a pre-existing orphan is data debt, not a logic failure) — like fusha_checkpoint_coverage.
    return 1 if (a.strict and not report["clean"]) else 0


if __name__ == "__main__":
    sys.exit(main())
