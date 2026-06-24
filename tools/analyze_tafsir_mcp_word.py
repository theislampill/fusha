#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze one Qur'anic word via Tafsir MCP (meaning/irab/sarf/statistics/qeraat), cache it, print it. INTERNAL.

Returns morphology (sarf: POS, wazn, form, voice, number, weak/hamza) + syntax (irab: case/mood, role) + root.
Nothing here ships publicly; it is evidence for the sarf/nahw gates.

Usage: python tools/analyze_tafsir_mcp_word.py 2 3 2 --aspects meaning irab sarf
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
    ap.add_argument("word_no", type=int)
    ap.add_argument("--aspects", nargs="*", default=["meaning", "irab", "sarf"])
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    with TafsirMCP() as m:
        resp = m.call("analyze_word", {"surah": a.surah, "ayah": a.ayah, "word_no": a.word_no, "aspects": a.aspects})
    if not a.no_cache and "error" not in resp:
        write_cache("analyze_word", "%d_%d_%d" % (a.surah, a.ayah, a.word_no),
                    {"surah": a.surah, "ayah": a.ayah, "word_no": a.word_no, "aspects": a.aspects}, resp)
    print(json.dumps(resp, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
