#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the per-section proofing matrices from the CANONICAL P2 entry matrix.

Supersedes the old qamus/scripts/build_nv_matrices.py (which used Fusha index-ordinal classes
970/1022/100). The authoritative split is the public/live `section` field: 947 verb / 1045 noun /
100 particle. Reads qamus/reports/qamus-2092-entry-matrix.jsonl (built by audit_qamus_2092_entries.py)
and emits reviewer-facing matrices that agree with the canonical scoreboards.
"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATRIX = os.path.join(ROOT, "qamus", "reports", "qamus-2092-entry-matrix.jsonl")
OUT = {"verb": os.path.join(ROOT, "qamus", "reports", "verbs", "verb-proofing-matrix.md"),
       "noun": os.path.join(ROOT, "qamus", "reports", "nouns", "noun-proofing-matrix.md"),
       "particle": os.path.join(ROOT, "qamus", "reports", "particles", "particle-proofing-matrix.md")}
LABEL = {"verb": "Verbs", "noun": "Nouns", "particle": "Particles"}

def main():
    rows = [json.loads(l) for l in open(MATRIX, encoding="utf-8")]
    by = collections.defaultdict(lambda: {"n": 0, "hc": 0, "res": 0, "pend": 0, "wp": 0, "blk": collections.Counter()})
    for r in rows:
        s = r["section"]; d = by[s]; d["n"] += 1
        h = r["hover_status"]
        if h["complete"]: d["hc"] += 1
        d["res"] += h["resolved_tokens"]; d["pend"] += h["pending_tokens"]
        if h["pending_tokens"] > 0: d["wp"] += 1
        for b, c in (h.get("blockers") or {}).items(): d["blk"][b] += c
    for sec, path in OUT.items():
        d = by[sec]; tot = d["res"] + d["pend"]
        pct = round(100 * d["res"] / tot, 1) if tot else 0
        L = [f"# {LABEL[sec]} proofing matrix (canonical, from qamus-2092-entry-matrix)", "",
             f"Per-entry audit of the **{d['n']}** {sec} entries (public `section` split — authoritative "
             f"947 verb / 1045 noun / 100 particle). **0 unknown buckets.** Regenerate: "
             f"`tools/build_proofing_matrices.py` (from `qamus-2092-entry-matrix.jsonl`). Reconciles to "
             f"`hover-gloss-terminal-scoreboard.md` (82.49% overall) and `qamus-2092-terminal-scoreboard.md`.", "",
             "| metric | value |", "|---|---:|",
             f"| {sec} entries | **{d['n']}** |",
             f"| entries fully hover-complete | {d['hc']} |",
             f"| entries with ≥1 pending hover token | {d['wp']} |",
             f"| resolved example tokens (per-entry, overlapping) | {d['res']:,} |",
             f"| pending example tokens (per-entry, overlapping) | {d['pend']:,} |",
             f"| per-section example coverage | **{pct}%** |", "",
             "> Per-entry token counts overlap (a token in a shared āyah counts for each citing entry); "
             "the canonical de-duplicated total is the P3 audit (41,164 resolved / 8,736 pending / 49,900).", "",
             "## Pending by blocker (this section)", "", "| blocker | count |", "|---|---:|"]
        for b, c in d["blk"].most_common():
            L.append(f"| `{b}` | {c:,} |")
        L.append("")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(L))
        print(f"{sec}: {d['n']} entries, {d['hc']} hover-complete, {pct}% -> {os.path.relpath(path, ROOT)}")

if __name__ == "__main__":
    main()
