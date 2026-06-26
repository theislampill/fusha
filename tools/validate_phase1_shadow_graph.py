#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a read-only Phase 1 Qamus shadow graph export.

This checks an already-built shadow directory. It does not SSH, read live Qamus
paths, rebuild WBW artifacts, or mutate anything. The real token identity remains
quran:S:A:W / wbw:S:A:W; parse keys are checked only as grammar-family nodes.

Usage:
  python tools/validate_phase1_shadow_graph.py /path/to/phase1-YYYYMMDD-HHMMSS
  python tools/validate_phase1_shadow_graph.py --self-test
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile


REQUIRED_FILES = [
    "phase1-current-truth.json",
    "phase1-current-truth.md",
    "nodes.jsonl",
    "edges.jsonl",
    "backlinks.json",
    "parse-keys.jsonl",
    "entry-index.jsonl",
    "token-index.jsonl",
    "hover-index.jsonl",
    "decision-index.jsonl",
    "blocker-index.jsonl",
    "collision-report.md",
    "public-boundary-scan.md",
    "mirror-diff-summary.md",
    "sample-traces.md",
    "validator-report.md",
]

EXPECTED_SECTIONS = {"noun": 1045, "verb": 947, "particle": 100}
EXPECTED_ENTRIES = 2092
EXPECTED_TOKEN_UNIVERSE = 49900
LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
QURAN_ID_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_ID_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
NODE_ID_PREFIXES = ("qamus:", "quran:", "wbw:", "parse:", "decision:", "blocker:", "external:", "repair:")
EDGE_TYPES = {
    "has_field",
    "has_sense",
    "has_hover_slot",
    "has_parse",
    "seen_at",
    "candidate_entry",
    "candidate_for_token",
    "resolved_entry",
    "blocked_by",
    "resolves_token",
    "renders_hover",
    "based_on_parse",
    "resolves_entry",
    "informed_by_internal",
    "blocks_token",
}


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
                yield line_no, json.loads(line)
            except Exception as exc:
                yield line_no, {"__json_error__": str(exc)}


def count_jsonl(path, sample_limit=2000):
    count = 0
    errors = []
    samples = []
    for line_no, row in read_jsonl(path):
        count += 1
        if "__json_error__" in row:
            errors.append("line %d: bad JSON (%s)" % (line_no, row["__json_error__"]))
        elif len(samples) < sample_limit:
            samples.append((line_no, row))
    return count, errors, samples


def edge_endpoints(edge):
    src = edge.get("from") or edge.get("source") or edge.get("src")
    dst = edge.get("to") or edge.get("target") or edge.get("dst")
    typ = edge.get("type") or edge.get("edge") or edge.get("rel")
    return src, typ, dst


def validate_shadow_dir(shadow_dir, sample_limit=2000, allow_legacy_missing_parse_version=False):
    errors = []
    warnings = []
    counts = {}

    if not os.path.isdir(shadow_dir):
        return {"ok": False, "errors": ["not a directory: %s" % shadow_dir], "warnings": [], "counts": {}}

    abs_shadow = os.path.abspath(shadow_dir)
    for rel in REQUIRED_FILES:
        path = os.path.join(shadow_dir, rel)
        if not os.path.exists(path):
            errors.append("missing artifact: %s" % rel)
        elif os.path.getsize(path) == 0:
            errors.append("empty artifact: %s" % rel)
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings, "counts": counts}

    truth = read_json(os.path.join(shadow_dir, "phase1-current-truth.json"))
    c = truth.get("counts") or {}
    counts.update({
        "entries": c.get("entries"),
        "token_universe": c.get("token_universe"),
        "live_word_records": c.get("live_word_records"),
        "token_decisions": c.get("token_decisions"),
        "parse_keys": c.get("parse_keys"),
        "orphan_edges": c.get("orphan_edges"),
        "public_success_leak_count": c.get("public_success_leak_count"),
    })

    if c.get("entries") != EXPECTED_ENTRIES:
        errors.append("live entries count is %r, expected %d" % (c.get("entries"), EXPECTED_ENTRIES))
    if c.get("sections") != EXPECTED_SECTIONS:
        errors.append("section split is %r, expected %r" % (c.get("sections"), EXPECTED_SECTIONS))
    if c.get("token_universe") != EXPECTED_TOKEN_UNIVERSE:
        errors.append("token universe is %r, expected %d" % (c.get("token_universe"), EXPECTED_TOKEN_UNIVERSE))
    if c.get("orphan_edges") != 0:
        errors.append("orphan_edges is %r, expected 0" % c.get("orphan_edges"))
    if truth.get("failures"):
        errors.append("phase1-current-truth failures not empty: %r" % truth.get("failures"))

    resolved = c.get("live_word_records")
    unresolved = None
    if isinstance(c.get("token_universe"), int) and isinstance(resolved, int):
        unresolved = c.get("token_universe") - resolved
    reconciliation = truth.get("reconciliation") or {}
    if unresolved is not None and reconciliation:
        if reconciliation.get("resolved_plus_unresolved") != c.get("token_universe"):
            errors.append("resolved_plus_unresolved does not reconcile to token universe")
        if reconciliation.get("unresolved_total") != unresolved:
            errors.append(
                "unresolved_total %r != token_universe-live_word_records %r"
                % (reconciliation.get("unresolved_total"), unresolved)
            )

    for name in ("nodes.jsonl", "edges.jsonl", "parse-keys.jsonl", "token-index.jsonl", "hover-index.jsonl", "decision-index.jsonl"):
        row_count, row_errors, _samples = count_jsonl(os.path.join(shadow_dir, name), sample_limit=0)
        counts[name] = row_count
        if row_errors:
            errors.extend("%s: %s" % (name, e) for e in row_errors[:5])
        if row_count == 0:
            errors.append("%s has zero rows" % name)

    node_count, node_errors, node_samples = count_jsonl(os.path.join(shadow_dir, "nodes.jsonl"), sample_limit=sample_limit)
    if node_errors:
        errors.extend("nodes.jsonl: %s" % e for e in node_errors[:20])
    for _line_no, node in node_samples:
        nid = node.get("id")
        if not nid:
            errors.append("nodes.jsonl sample missing id")
            continue
        if not str(nid).startswith(NODE_ID_PREFIXES):
            errors.append("unexpected node id prefix: %s" % nid)
        if not node.get("type"):
            errors.append("%s: missing node type" % nid)
        if "public_exposable" not in node:
            errors.append("%s: missing public_exposable" % nid)
        if os.path.abspath(str(node.get("locator", ""))).startswith(abs_shadow):
            warnings.append("%s: locator points inside shadow dir" % nid)

    parse_count, parse_errors, parse_samples = count_jsonl(os.path.join(shadow_dir, "parse-keys.jsonl"), sample_limit=sample_limit)
    if parse_errors:
        errors.extend("parse-keys.jsonl: %s" % e for e in parse_errors[:20])
    for _line_no, row in parse_samples:
        pid = row.get("id") or row.get("parse_id") or row.get("node_id")
        if pid and not str(pid).startswith("parse:"):
            errors.append("parse key row has non-parse id: %s" % pid)
        obj = row.get("parse") or row.get("parse_object") or row.get("canonical_parse_object") or row
        if not obj.get("parse_key_version"):
            message = "%s: missing parse_key_version" % (pid or "<parse row>")
            if allow_legacy_missing_parse_version:
                warnings.append("legacy Phase 1 baseline: " + message)
            else:
                errors.append(message)
        loc = obj.get("quran_loc")
        if loc not in (None, "unknown") and not LOC_RE.match(str(loc)):
            errors.append("%s: bad quran_loc %r" % (pid or "<parse row>", loc))
        if obj.get("gate") == "auto_safe" and obj.get("parse_confidence") == "surface_only":
            errors.append("%s: surface-only parse marked auto_safe" % (pid or "<parse row>"))

    _token_count, token_errors, token_samples = count_jsonl(
        os.path.join(shadow_dir, "token-index.jsonl"),
        sample_limit=sample_limit,
    )
    if token_errors:
        errors.extend("token-index.jsonl: %s" % e for e in token_errors[:20])
    for line_no, row in token_samples:
        tid = row.get("id") or row.get("quran")
        if not QURAN_ID_RE.match(str(tid or "")):
            errors.append("token-index.jsonl line %d: token id must be quran:S:A:W" % line_no)
        parse_ref = row.get("parse_id") or row.get("parse_key")
        if not str(parse_ref or "").startswith("parse:"):
            errors.append("token-index.jsonl line %d: missing parse_id/parse_key" % line_no)

    edge_count, edge_errors, edge_samples = count_jsonl(os.path.join(shadow_dir, "edges.jsonl"), sample_limit=sample_limit)
    if edge_errors:
        errors.extend("edges.jsonl: %s" % e for e in edge_errors[:20])
    for _line_no, edge in edge_samples:
        src, typ, dst = edge_endpoints(edge)
        if not src or not dst or not typ:
            errors.append("edge sample missing endpoint/type: %r" % edge)
            continue
        if typ not in EDGE_TYPES:
            warnings.append("unknown edge type in sample: %s" % typ)
        if not str(src).startswith(NODE_ID_PREFIXES):
            errors.append("bad edge source prefix: %s" % src)
        if not str(dst).startswith(NODE_ID_PREFIXES):
            errors.append("bad edge target prefix: %s" % dst)

    _decision_count, decision_errors, decision_samples = count_jsonl(
        os.path.join(shadow_dir, "decision-index.jsonl"),
        sample_limit=100000,
    )
    if decision_errors:
        errors.extend("decision-index.jsonl: %s" % e for e in decision_errors[:20])
    for line_no, row in decision_samples:
        did = row.get("id") or row.get("decision_id")
        if not did or not str(did).startswith("decision:"):
            errors.append("decision-index.jsonl line %d: missing decision id" % line_no)
        if not QURAN_ID_RE.match(str(row.get("quran_loc") or "")):
            errors.append("decision-index.jsonl line %d: quran_loc must be quran:S:A:W" % line_no)
        if not WBW_ID_RE.match(str(row.get("wbw_loc") or "")):
            errors.append("decision-index.jsonl line %d: wbw_loc must be wbw:S:A:W" % line_no)
        if not str(row.get("parse_id") or "").startswith("parse:"):
            errors.append("decision-index.jsonl line %d: parse_id must be parse:<hash>" % line_no)

    backlinks = read_json(os.path.join(shadow_dir, "backlinks.json"))
    if not backlinks:
        errors.append("backlinks.json is empty")
    else:
        counts["backlinks_top_keys"] = len(backlinks)

    reports = {
        "validator-report.md": "All Phase 1 shadow validators passed",
        "public-boundary-scan.md": "Successful public endpoint leak count: `0`",
        "mirror-diff-summary.md": "Classification:",
        "sample-traces.md": "Reverse trace",
        "collision-report.md": "quarantine_collision",
    }
    for rel, needle in reports.items():
        text = io.open(os.path.join(shadow_dir, rel), encoding="utf-8").read()
        if needle not in text:
            errors.append("%s missing expected marker %r" % (rel, needle))

    counts["nodes_sampled"] = min(node_count, sample_limit)
    counts["edges_sampled"] = min(edge_count, sample_limit)
    counts["parse_keys_sampled"] = min(parse_count, sample_limit)
    return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": counts}


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_self_test():
    with tempfile.TemporaryDirectory(prefix="phase1-shadow-selftest-") as td:
        truth = {
            "counts": {
                "entries": EXPECTED_ENTRIES,
                "sections": EXPECTED_SECTIONS,
                "token_universe": EXPECTED_TOKEN_UNIVERSE,
                "live_word_records": 49260,
                "token_decisions": 1,
                "parse_keys": 1,
                "orphan_edges": 0,
                "public_success_leak_count": 0,
            },
            "failures": [],
            "reconciliation": {
                "resolved_plus_unresolved": EXPECTED_TOKEN_UNIVERSE,
                "unresolved_total": 640,
            },
        }
        write_json(os.path.join(td, "phase1-current-truth.json"), truth)
        for rel, text in {
            "phase1-current-truth.md": "Entries: `2092`\n",
            "collision-report.md": "## quarantine_collision\n",
            "public-boundary-scan.md": "Successful public endpoint leak count: `0`\n",
            "mirror-diff-summary.md": "Classification: token rows match\n",
            "sample-traces.md": "## Reverse trace\n",
            "validator-report.md": "All Phase 1 shadow validators passed\n",
        }.items():
            with io.open(os.path.join(td, rel), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        write_json(os.path.join(td, "backlinks.json"), {"quran:1:1:1": {"has_parse": ["parse:abc"]}})
        write_jsonl(os.path.join(td, "nodes.jsonl"), [
            {"id": "quran:1:1:1", "type": "quran_token", "source": "self-test", "status": "clean", "public_exposable": True, "locator": "1:1:1"},
            {"id": "wbw:1:1:1", "type": "wbw_hover_slot", "source": "self-test", "status": "clean", "public_exposable": True, "locator": "1:1:1"},
            {"id": "parse:abc", "type": "parse_key", "source": "self-test", "status": "clean", "public_exposable": False, "locator": "parse:abc"},
            {"id": "decision:one", "type": "decision", "source": "self-test", "status": "resolved", "public_exposable": False, "locator": "decision:one"},
        ])
        write_jsonl(os.path.join(td, "edges.jsonl"), [
            {"from": "quran:1:1:1", "type": "has_hover_slot", "to": "wbw:1:1:1"},
            {"from": "quran:1:1:1", "type": "has_parse", "to": "parse:abc"},
            {"from": "decision:one", "type": "resolves_token", "to": "quran:1:1:1"},
        ])
        write_jsonl(os.path.join(td, "parse-keys.jsonl"), [
            {
                "id": "parse:abc",
                "canonical_parse_object": {
                    "parse_key_version": "phase1.shadow.v1",
                    "quran_loc": "1:1:1",
                    "gate": "human_review_required",
                    "parse_confidence": "partial",
                },
                "seen_locs": ["quran:1:1:1"],
                "family_size": 1,
            }
        ])
        write_jsonl(os.path.join(td, "token-index.jsonl"), [
            {"id": "quran:1:1:1", "loc": "1:1:1", "parse_key": "parse:abc", "status": "resolved"}
        ])
        for rel in ("entry-index.jsonl", "hover-index.jsonl", "blocker-index.jsonl"):
            write_jsonl(os.path.join(td, rel), [{"id": rel, "type": "self_test"}])
        write_jsonl(os.path.join(td, "decision-index.jsonl"), [
            {
                "id": "decision:one",
                "quran_loc": "quran:1:1:1",
                "wbw_loc": "wbw:1:1:1",
                "parse_id": "parse:abc",
                "gloss": "self-test",
            }
        ])
        result = validate_shadow_dir(td)
        if not result["ok"]:
            print("SELF-TEST FAIL")
            for err in result["errors"]:
                print("  -", err)
            return 1
        write_jsonl(os.path.join(td, "token-index.jsonl"), [
            {"id": "quran:1:1:1", "loc": "1:1:1", "status": "resolved"}
        ])
        missing_parse = validate_shadow_dir(td)
        if missing_parse["ok"]:
            print("SELF-TEST FAIL: token missing parse linkage did not fail")
            return 1
        write_jsonl(os.path.join(td, "token-index.jsonl"), [
            {"id": "quran:1:1:1", "loc": "1:1:1", "parse_key": "parse:abc", "status": "resolved"}
        ])
        os.remove(os.path.join(td, "edges.jsonl"))
        bad = validate_shadow_dir(td)
        if bad["ok"]:
            print("SELF-TEST FAIL: missing edges.jsonl did not fail")
            return 1
    print("PASS — phase1 shadow graph validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("shadow_dir", nargs="?", help="Phase 1 shadow graph output directory")
    parser.add_argument("--self-test", action="store_true", help="run synthetic validator self-test")
    parser.add_argument("--sample-limit", type=int, default=2000, help="row sample size for deep shape checks")
    parser.add_argument(
        "--allow-legacy-missing-parse-version",
        action="store_true",
        help="accept the current Phase 1 baseline artifact while warning about pre-Phase-2 unversioned parse rows",
    )
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(run_self_test())
    if not args.shadow_dir:
        parser.error("shadow_dir is required unless --self-test is used")
    result = validate_shadow_dir(
        args.shadow_dir,
        sample_limit=args.sample_limit,
        allow_legacy_missing_parse_version=args.allow_legacy_missing_parse_version,
    )
    print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True, indent=2))
    if result["warnings"]:
        print("WARN:")
        for warning in result["warnings"][:40]:
            print("  -", warning)
    if not result["ok"]:
        print("FAIL:")
        for error in result["errors"][:80]:
            print("  -", error)
        raise SystemExit(1)
    print("PASS — Phase 1 shadow graph artifacts are addressed, nonzero, reconciled, and public-boundary clean")


if __name__ == "__main__":
    main()
