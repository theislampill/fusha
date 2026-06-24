#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build / extend the source-hashed Tafsir MCP cache (read-from-MCP, write-to-disk). Cache is INTERNAL evidence.

Each cache record is one MCP response, source-hashed for integrity. Raw cache is gitignored (see .gitignore);
only tiny redacted examples live under sources/tafsir_mcp/examples/. Nothing here ships to the public hover
artifact — public records stay {src:"qamus",kind:"authored"}.

Usage:
  # batch a list of ayah/word targets from a JSONL/loc file:
  python tools/build_tafsir_mcp_cache.py --locs 2:3:2 2:6:1 1:1:1
  python tools/build_tafsir_mcp_cache.py --ayat 1:1 2:6 --include irab gharib
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from tafsir_mcp_client import TafsirMCP  # noqa: E402

CACHE = os.environ.get("TAFSIR_MCP_CACHE", os.path.join(ROOT, "sources", "tafsir_mcp", "cache"))
SERVER = {"name": "Tafsir MCP", "endpoint": "https://mcp.tafsir.net/mcp"}


def _hash(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def write_cache(kind, key, request, response, mcp_version=None):
    """Write a source-hashed cache record. kind in {analyze_word, fetch_ayah, ...}. Returns the path."""
    os.makedirs(CACHE, exist_ok=True)
    rec = {
        "schema": "fusha/tafsir-mcp-cache@1",
        "kind": kind, "key": key, "request": request,
        "source": {**SERVER, "version": mcp_version},
        "source_hash": _hash(response),
        "response": response,
        "public_export_allowed": False,
        "note": "INTERNAL evidence only — never shipped; public hover stays src:qamus,kind:authored",
    }
    path = os.path.join(CACHE, "%s__%s.json" % (kind, key))
    json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locs", nargs="*", default=[], help="S:A:W tokens to analyze_word")
    ap.add_argument("--ayat", nargs="*", default=[], help="S:A ayat to fetch_ayah")
    ap.add_argument("--include", nargs="*", default=["irab"], help="fetch_ayah include types")
    ap.add_argument("--aspects", nargs="*", default=["meaning", "irab", "sarf"], help="analyze_word aspects")
    a = ap.parse_args()
    written = []
    with TafsirMCP() as m:
        ver = None
        for loc in a.locs:
            s, ay, w = (int(x) for x in loc.split(":"))
            resp = m.call("analyze_word", {"surah": s, "ayah": ay, "word_no": w, "aspects": a.aspects})
            written.append(write_cache("analyze_word", "%d_%d_%d" % (s, ay, w),
                                       {"surah": s, "ayah": ay, "word_no": w, "aspects": a.aspects}, resp, ver))
        for ref in a.ayat:
            s, ay = (int(x) for x in ref.split(":"))
            resp = m.call("fetch_ayah", {"surah": s, "ayah": ay, "include": a.include})
            written.append(write_cache("fetch_ayah", "%d_%d" % (s, ay),
                                       {"surah": s, "ayah": ay, "include": a.include}, resp, ver))
    print(json.dumps({"cached": len(written), "dir": os.path.relpath(CACHE, ROOT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
