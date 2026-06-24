#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 9 (closure-2092) — hover-gloss QUALITY + grammar-metadata audit over every RESOLVED token.

For each resolved token this audits: provenance cleanliness (public record must be src=qamus,
kind=authored, lang=en — nothing else), too-generic gloss (the "what/from/it" class the owner
flagged as insufficient), derivable grammar metadata (root + coarse POS from QAC), particle-function
presence, homograph-reason presence (a resolved homograph must carry a per-loc token decision), and
source-leak risk (no external source name / informed_by leaking into the PUBLIC gloss text).

Read-only. Emits a quality summary + a repair queue (worst offenders), not a rewrite.
Outputs under qamus/reports/closure-2092/.
"""
import json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT, "out", "hover_stage"))
OUTDIR = os.path.join(ROOT, "qamus", "reports", "closure-2092")

# glosses too generic to teach meaning (owner: "what/from/thing/he/it" are insufficient)
GENERIC = {"what", "who", "from", "thing", "he", "it", "she", "they", "this", "that", "the", "a",
           "and", "of", "to", "in", "on", "with", "for", "is", "was", "not", "no", "yes", "them",
           "him", "her", "its", "their", "his", "you", "we", "i", "but", "or", "so", "then"}
# source-leak detection: URL/symbol patterns match as substrings; short alpha tokens match only on
# WORD BOUNDARIES (else "ocr" matches "hypocrite", "mcp" etc. — false positives).
import re as _re
LEAK_SUBSTR = ("quran.com", "corpus.quran", "informed_by", "qac:", "http://", "https://", ".com/")
LEAK_WORD = _re.compile(r"\b(tafsir|mcp|ocr|qac|qul|tanzil|quranwbw)\b", _re.I)
def _leaks(low):
    return any(t in low for t in LEAK_SUBSTR) or bool(LEAK_WORD.search(low))

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    wbw = json.load(open(os.path.join(STAGE, "wbw-lookup.json"), encoding="utf-8"))
    words, verses = wbw["words"], wbw["verses"]
    dec = {}
    dp = os.path.join(STAGE, "fusha-hover-token-decisions.jsonl")
    for ln in open(dp, encoding="utf-8"):
        ln = ln.strip()
        if ln:
            d = json.loads(ln); dec[d["loc"]] = d
    # QAC root/POS
    roots_by_loc = {}
    for ln in open(os.path.join(STAGE, "qac-roots.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 2: roots_by_loc[p[0]] = p[1]
    pos_by_as = {}
    for ln in open(os.path.join(STAGE, "qac-tokroots.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 4: pos_by_as[(p[0], A.norm_strict(p[1]))] = p[3].strip()
    # homograph surfaces (norm_strict -> distinct roots over all tokens)
    sr = collections.defaultdict(set)
    for sa, wl in verses.items():
        for i, surf in enumerate(wl, 1):
            r = roots_by_loc.get(f"{sa}:{i}")
            if r: sr[A.norm_strict(surf)].add(r.replace(" ", ""))

    flags = collections.Counter()
    repair = []
    total = 0
    for loc, tok in words.items():
        total += 1
        sa = ":".join(loc.split(":")[:2])
        surf = tok.get("ar", "")
        nk = A.norm_strict(surf)
        g = (tok.get("glosses") or [{}])[0]
        text = (g.get("text") or "").strip()
        row_flags = []
        # provenance cleanliness (public record)
        if not (g.get("src") == "qamus" and g.get("kind") == "authored" and g.get("lang") == "en"):
            row_flags.append("public_provenance_unclean")
        # source leak in public text
        low = text.lower()
        if _leaks(low):
            row_flags.append("source_leak_risk")
        # too-generic gloss
        words_in = [w for w in low.replace("-", " ").split() if w]
        if text and all(w in GENERIC for w in words_in):
            row_flags.append("too_generic_gloss")
        if not text:
            row_flags.append("empty_gloss")
        # metadata derivability
        if not roots_by_loc.get(loc) and pos_by_as.get((sa, nk)) != "P":
            row_flags.append("root_not_derivable")
        # particle function presence: a particle (POS=P) resolved gloss should carry a token decision
        if pos_by_as.get((sa, nk)) == "P" and loc not in dec:
            row_flags.append("particle_function_missing")
        # homograph resolved without a per-loc token decision (surface-key gloss on a collision)
        if len(sr.get(nk, set())) > 1 and loc not in dec:
            row_flags.append("homograph_reason_missing")
        for f in row_flags:
            flags[f] += 1
        # repair queue: the actionable quality defects (exclude metadata-only notes)
        actionable = [f for f in row_flags if f in
                      ("too_generic_gloss", "empty_gloss", "source_leak_risk", "public_provenance_unclean")]
        if actionable:
            repair.append({"loc": loc, "surface": surf, "gloss": text, "flags": actionable})

    clean = total - len(repair)
    summary = {
        "_generator": "tools/audit_hover_gloss_quality.py",
        "resolved_tokens": total,
        "quality_clean": clean,
        "quality_clean_pct": round(100.0 * clean / total, 2) if total else 0,
        "flag_counts": dict(flags.most_common()),
        "repair_queue_size": len(repair),
    }
    with open(os.path.join(OUTDIR, "hover-gloss-quality-audit.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, sort_keys=True, indent=2); f.write("\n")
    with open(os.path.join(OUTDIR, "hover-gloss-quality-audit.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"_generator": "tools/audit_hover_gloss_quality.py",
                            "_summary": summary}, ensure_ascii=False) + "\n")
        for r in repair:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    md = ["# Hover-gloss quality + grammar-metadata audit (closure-2092)", "",
          "Generated by `tools/audit_hover_gloss_quality.py` from the live staged artifact + decisions.", "",
          f"- resolved tokens audited: **{total:,}**",
          f"- quality-clean (no actionable defect): **{clean:,}** ({summary['quality_clean_pct']}%)",
          f"- repair queue (actionable defects): **{len(repair):,}**", "",
          "## Flag counts", "", "| flag | count |", "|---|---:|"]
    for k, v in flags.most_common():
        md.append(f"| `{k}` | {v:,} |")
    md += ["", "## Notes", "",
           "- `public_provenance_unclean` / `source_leak_risk` / `empty_gloss` / `too_generic_gloss` are "
           "actionable (repair queue). `root_not_derivable`, `particle_function_missing`, "
           "`homograph_reason_missing` are metadata-completeness notes (internal records may be enriched "
           "without changing the concise public display).", ""]
    open(os.path.join(OUTDIR, "hover-gloss-quality-audit.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("QUALITY AUDIT OK resolved=%d clean=%d (%.2f%%) repair_queue=%d" %
          (total, clean, summary["quality_clean_pct"], len(repair)))
    print("flags:", dict(flags.most_common()))

if __name__ == "__main__":
    main()
