#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch a Qur'an ayah (Uthmani) + optional grammar layers from Tafsir MCP, cache it, print it. INTERNAL evidence.

include types: tajweed, irab (إعراب القرآن الكريم — الآيات), gharib, qiraat_ayah, tadabbur.
Nothing fetched here ships to the public hover artifact.

Usage: python tools/fetch_tafsir_mcp_ayah.py 1 1 --include irab gharib
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from tafsir_mcp_client import TafsirMCP  # noqa: E402
from build_tafsir_mcp_cache import write_cache  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surah", type=int)
    ap.add_argument("ayah", type=int)
    ap.add_argument("--include", nargs="*", default=["irab"])
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    with TafsirMCP() as m:
        resp = m.call("fetch_ayah", {"surah": a.surah, "ayah": a.ayah, "include": a.include})
    if not a.no_cache:
        write_cache("fetch_ayah", "%d_%d" % (a.surah, a.ayah),
                    {"surah": a.surah, "ayah": a.ayah, "include": a.include}, resp)
    print(json.dumps(resp, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
