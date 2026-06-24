#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export token-addressed hover decisions (quran:S:A:W → gloss) for surface-distinct homographs. READ-ONLY.

The live hover aid keys by norm_strict, which collapses لَمْ/لِمَ، مَن/مِن، إِنْ/إِنَّ، أَمْ/أُمّ. The VOCALIZED
surface (already in the artifact) preserves the harakat that distinguishes them, so a per-token decision keyed by
loc resolves the collision. This emits one JSONL decision per currently-pending loc whose surface unambiguously
selects a reading; SAME-surface polysemy (وَمَا، لَمَّا، bare إِنْ) is left pending (needs iʿrāb).

Output (JSONL) is the runtime artifact consumed by qamus_wbw/expand.py at
qamus-service/ref/fusha-hover-token-decisions.jsonl (gitignored). Public record stays {src:'qamus',kind:'authored'}.

Config via ENV: QAMUS_WBW_SERVICES (for norm_strict), QAMUS_WBW_ARTIFACT (verses+words). No path hardcoded.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.environ.get("QAMUS_WBW_SERVICES", "services"))
from qamus_wbw import expand as X  # noqa: E402

F, K, U, SUK, SH = "َ", "ِ", "ُ", "ْ", "ّ"  # fatha kasra damma sukun shadda


def disambig(tok):
    """Authored gloss for a surface-distinct homograph, or None to leave pending (same-surface polysemy)."""
    t, pre = tok, ""
    for p, gp in (("وَ", "and "), ("فَ", "so "), ("وَّ", "and ")):
        if t.startswith(p):
            pre = gp; t = t[len(p):]; break
    base = X.N.norm_strict(t)
    if base == "لم":                                  # لم
        if t[:2] == "ل" + K:
            return pre + "why"                                  # لِمَ
        if F in t[:2] or t.startswith("لَّ") or SUK in t:
            return (pre + "did not").strip()                    # لَمْ / لَّمْ
        return None
    if base == "من":                                  # من
        mi = t.find("م")
        if mi >= 0 and t[mi + 1:mi + 2] == K:
            return (pre + "from").strip()                       # مِن
        if mi >= 0 and t[mi + 1:mi + 2] == F:
            return (pre + "who / whoever").strip()              # مَن (relative or interrogative)
        return None
    if base in ("ان", "إن"):                # ان / إن
        if SH in t:
            return (pre + "indeed").strip()                     # إِنَّ (shadda) — emphatic
        return None                                             # bare إِنْ ambiguous -> pending
    if base in ("ام", "أم"):                # ام / أم
        if U in t or SH in t:
            return "mother"                                     # أُمّ
        if F in t and SUK in t:
            return "or"                                         # أَمْ
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--all-locs", action="store_true", help="emit for every matching loc (default: only pending)")
    a = ap.parse_args()
    if not a.artifact:
        ap.error("--artifact/QAMUS_WBW_ARTIFACT required")
    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words = d["verses"], d["words"]
    out = []
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            if not a.all_locs and loc in words:
                continue
            g = disambig(tok)
            if not g:
                continue
            out.append({"loc": loc, "gloss": g, "surface": tok, "state_id": "state:tok:%s" % loc,
                        "key": X.N.norm_strict(tok), "src": "qamus", "kind": "authored", "lang": "en",
                        "internal_provenance": {"informed_by": ["qac", "quran-text", "tafsir-mcp"],
                                                "method": "harakat-disambiguated surface-distinct homograph"}})
    with open(a.out, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    import collections
    print(json.dumps({"token_decisions": len(out),
                      "by_gloss": dict(collections.Counter(o["gloss"] for o in out).most_common(12))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
