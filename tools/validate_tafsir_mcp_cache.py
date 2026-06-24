#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the Tafsir MCP cache: schema, source-hash integrity, and the no-public-leak invariant. Fail-closed.

Checks every record under the cache dir (and the committed examples):
  - has schema fusha/tafsir-mcp-cache@1, kind, key, request, response, source_hash;
  - stored source_hash matches a re-hash of the response (integrity);
  - public_export_allowed is False (cache is internal-only).
Exit 0 = all valid.

Usage: python tools/validate_tafsir_mcp_cache.py [--dir <cache_or_examples_dir>]
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.environ.get("TAFSIR_MCP_CACHE", os.path.join(ROOT, "sources", "tafsir_mcp", "cache"))


def _hash(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def validate_dir(d):
    errors, n = [], 0
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        n += 1
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            errors.append("%s: bad JSON (%s)" % (os.path.basename(f), e)); continue
        for k in ("schema", "kind", "key", "request", "response", "source_hash"):
            if k not in r:
                errors.append("%s: missing %s" % (os.path.basename(f), k))
        if r.get("schema") != "fusha/tafsir-mcp-cache@1":
            errors.append("%s: wrong schema %s" % (os.path.basename(f), r.get("schema")))
        if "response" in r and r.get("source_hash") != _hash(r["response"]):
            errors.append("%s: source_hash mismatch (cache corrupted/edited)" % os.path.basename(f))
        if r.get("public_export_allowed") is not False:
            errors.append("%s: public_export_allowed must be False" % os.path.basename(f))
    return n, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT)
    a = ap.parse_args()
    total, errors = 0, []
    dirs = [a.dir, os.path.join(ROOT, "sources", "tafsir_mcp", "examples")]
    for d in dirs:
        if os.path.isdir(d):
            n, e = validate_dir(d)
            total += n
            errors += e
    print("checked %d cache record(s) across %d dir(s)" % (total, len([d for d in dirs if os.path.isdir(d)])))
    if errors:
        print("FAIL:")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    print("PASS — schema + source-hash integrity + no-public-leak invariant OK")


if __name__ == "__main__":
    main()
