#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan public and internal artifacts for Qamus provenance leakage.

Public output must remain qamus-authored. Internal artifacts may carry evidence
labels, but this tool classifies them separately so a public leak is never
confused with internal-only provenance.
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile
import urllib.request


LEAK_RE = re.compile(
    r"\b(informed_by|mcp|qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
    r"tanzil|tafsir|ocr|source-photo|source_photo|/srv/|c:\\\\|root\.txt)\b",
    re.I,
)


def read_target(target, timeout=20, max_bytes=10_000_000):
    if re.match(r"^https?://", target):
        with urllib.request.urlopen(target, timeout=timeout) as resp:
            data = resp.read(max_bytes + 1)
            return {
                "target": target,
                "kind": "url",
                "status": getattr(resp, "status", None),
                "bytes": min(len(data), max_bytes),
                "truncated": len(data) > max_bytes,
                "text": data[:max_bytes].decode("utf-8", "replace"),
            }
    with io.open(target, "rb") as handle:
        data = handle.read(max_bytes + 1)
    return {
        "target": target,
        "kind": "file",
        "status": None,
        "bytes": min(len(data), max_bytes),
        "truncated": len(data) > max_bytes,
        "text": data[:max_bytes].decode("utf-8", "replace"),
    }


def scan_text(text):
    hits = []
    for match in LEAK_RE.finditer(text):
        token = match.group(0)
        if token.lower() not in [h.lower() for h in hits]:
            hits.append(token)
    return hits


def scan_targets(public_targets=None, internal_targets=None, shadow_dir=None):
    public_targets = public_targets or []
    internal_targets = internal_targets or []
    results = {
        "public": [],
        "internal": [],
        "shadow": [],
        "classification": {
            "public_leak_count": 0,
            "internal_only_provenance_count": 0,
            "private_path_leak_count": 0,
            "adapter_label_leak_count": 0,
        },
    }

    for bucket, targets in (("public", public_targets), ("internal", internal_targets)):
        for target in targets:
            item = read_target(target)
            leaks = scan_text(item.pop("text"))
            item["leaks"] = leaks
            item["leak_count"] = len(leaks)
            results[bucket].append(item)
            if bucket == "public":
                results["classification"]["public_leak_count"] += len(leaks)
            else:
                results["classification"]["internal_only_provenance_count"] += len(leaks)

    if shadow_dir:
        for name in ("nodes.jsonl", "edges.jsonl", "parse-keys.jsonl", "decision-index.jsonl", "public-boundary-scan.md"):
            path = os.path.join(shadow_dir, name)
            if not os.path.exists(path):
                continue
            item = read_target(path)
            leaks = scan_text(item.pop("text"))
            item["leaks"] = leaks
            item["leak_count"] = len(leaks)
            results["shadow"].append(item)

    for bucket in ("public", "internal", "shadow"):
        for item in results[bucket]:
            joined = " ".join(item.get("leaks") or []).lower()
            if "/srv/" in joined or "c:\\\\" in joined or "root.txt" in joined:
                results["classification"]["private_path_leak_count"] += 1
            if any(label in joined for label in ("mcp", "qac", "quran.com", "tafsir", "tanzil")):
                results["classification"]["adapter_label_leak_count"] += 1
    return results


def self_test():
    with tempfile.TemporaryDirectory(prefix="qamus-boundary-scan-") as td:
        public = os.path.join(td, "public.html")
        internal = os.path.join(td, "internal.json")
        with io.open(public, "w", encoding="utf-8") as handle:
            handle.write('<div data-src="qamus" data-kind="authored" data-lang="en">ask you</div>')
        with io.open(internal, "w", encoding="utf-8") as handle:
            json.dump({"informed_by": ["qac", "tafsir_mcp"]}, handle)
        result = scan_targets([public], [internal])
        if result["classification"]["public_leak_count"] != 0:
            print("SELF-TEST FAIL: clean public file flagged")
            return 1
        if result["classification"]["internal_only_provenance_count"] == 0:
            print("SELF-TEST FAIL: internal provenance not detected")
            return 1
        with io.open(public, "w", encoding="utf-8") as handle:
            handle.write("QAC public leak")
        bad = scan_targets([public], [])
        if bad["classification"]["public_leak_count"] == 0:
            print("SELF-TEST FAIL: public leak not detected")
            return 1
    print("PASS — public-boundary scanner self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="append", default=[], help="public URL/file to scan")
    parser.add_argument("--internal", action="append", default=[], help="internal file to classify")
    parser.add_argument("--shadow-dir", help="shadow graph directory to scan")
    parser.add_argument("--out", help="write JSON report")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    result = scan_targets(args.public, args.internal, args.shadow_dir)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
    print(text)
    if result["classification"]["public_leak_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
