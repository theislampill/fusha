#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A1 — artifact ergonomics gate: committed artifacts must be reviewable & diffable.

Every committed JSON/JSONL is classified, then validated against its class rules. Fails closed.

Classes (by path/name):
  compact-checksum  *.min.json, checksums.json            compact single line ALLOWED
  sample            *.sample.json / *.sample.jsonl        small illustrative
  source-boundary   provenance/** , sources/**            provenance/boundary docs
  generated-cache   **/out/** , **/cache/**               should be gitignored (warn if committed)
  canonical-machine *.jsonl                               row-records, 1 JSON object/line
  reviewer-facing   every other *.json (incl *.meta.json) pretty: indent=2, sort_keys, ensure_ascii=False, \n

Rules enforced on reviewer-facing JSON:
  - if >2000 bytes it MUST be multi-line (no one-line mega-index)
  - MUST end with a trailing newline
  - MUST NOT escape Arabic (no \\u05/06/08xx — ensure_ascii=True leak)
  - MUST NOT be a top-level JSON array with >50 elements (use JSONL instead)
On JSONL: every non-empty line is one valid JSON object; file does not begin with '['.
"""
import io, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIG = 2000
AR_ESCAPE = re.compile(r"\\u0[5-8][0-9a-fA-F][0-9a-fA-F]")

def tracked_files():
    out = subprocess.run(["git", "ls-files", "*.json", "*.jsonl"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    files = [l for l in out.splitlines() if l.strip()]
    if files:
        return files
    # F14 no-git fallback: deterministic filesystem walk (a ZIP/non-git checkout must not scan vacuously)
    for dp, _, fs in os.walk(ROOT):
        if (os.sep + ".git") in dp or (os.sep + "out") in (dp + os.sep) or "__pycache__" in dp:
            continue
        for f in fs:
            if f.endswith((".json", ".jsonl")):
                files.append(os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/"))
    return files

def classify(rel):
    name = os.path.basename(rel)
    if name.endswith(".min.json") or name == "checksums.json":
        return "compact-checksum"
    if ".sample." in name:
        return "sample"
    if rel.startswith("provenance/") or rel.startswith("sources/"):
        return "source-boundary"
    if "/out/" in rel or rel.startswith("out/") or "/cache/" in rel:
        return "generated-cache"
    if name.endswith(".jsonl"):
        return "canonical-machine"
    return "reviewer-facing"

def check():
    fails, warns = [], []
    counts = {}
    for rel in tracked_files():
        cls = classify(rel)
        counts[cls] = counts.get(cls, 0) + 1
        p = os.path.join(ROOT, rel)
        try:
            raw = io.open(p, "rb").read()
        except FileNotFoundError:
            continue
        text = raw.decode("utf-8", "replace")
        nbytes = len(raw)
        if cls == "generated-cache":
            warns.append(f"{rel}: committed generated-cache (should be gitignored)")
            continue
        if cls in ("compact-checksum",):
            try: json.loads(text)
            except Exception as e: fails.append(f"{rel}: {cls} unparseable ({e})")
            continue
        if cls == "canonical-machine" or rel.endswith(".jsonl"):
            if text.lstrip()[:1] == "[":
                fails.append(f"{rel}: JSONL file starts with '[' (is a JSON array, not JSONL)")
            for i, ln in enumerate(text.splitlines(), 1):
                if not ln.strip(): continue
                try: json.loads(ln)
                except Exception as e:
                    fails.append(f"{rel}:{i}: invalid JSONL line ({e})"); break
            if raw and not raw.endswith(b"\n"):
                fails.append(f"{rel}: missing trailing newline")
            continue
        # reviewer-facing / sample / source-boundary JSON
        if AR_ESCAPE.search(text):
            fails.append(f"{rel}: escapes Arabic (ensure_ascii=True leak)")
        if not raw.endswith(b"\n"):
            fails.append(f"{rel}: missing trailing newline")
        newlines = text.count("\n")
        if nbytes > BIG and newlines <= 1:
            fails.append(f"{rel}: one-line mega-JSON ({nbytes} bytes) — pretty-print or rename .min.json / use JSONL")
        try:
            obj = json.loads(text)
            if isinstance(obj, list) and len(obj) > 50:
                fails.append(f"{rel}: top-level JSON array with {len(obj)} elements — use JSONL")
        except Exception as e:
            fails.append(f"{rel}: unparseable ({e})")
    print("artifact classes:", counts)
    for w in warns: print("warn:", w)
    if fails:
        print(f"FAIL — {len(fails)} ergonomics violation(s):")
        for f in fails[:60]: print("  -", f)
        return 1
    print("ARTIFACT ERGONOMICS OK — all committed artifacts reviewable/diffable")
    return 0

if __name__ == "__main__":
    sys.exit(check())
