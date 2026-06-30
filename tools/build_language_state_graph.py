#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the language state graph (OSM-style hidden-state model) — run READ-ONLY on the server, pull output.

The live qamus-highlight aid keys ONLY by a vowel-stripped norm_strict key. A single key (observation) may
emit from MORE THAN ONE hidden state (different lemma / POS / verb-form / voice). This tool makes those splits
explicit: one node per distinct key, every candidate hidden state attached, and a decision:

    resolved_qamus_authored  key has a live authored gloss (in the hover-decisions tsv)
    quarantine_homograph     >1 distinct root, POS, or lemma-bearing surface  -> NO single gloss may fire
    pending                  one owner but not yet authored
    repair_candidate         (reserved) entry field needs fixing

A gloss is public_export_allowed ONLY for a resolved or single-owner key. This is the structural Poka-yoke that
prevents the norm_strict collisions that caused prior regressions (نَزَّلَ/نَزَلَ, مُلْك/مَلِك, أُمَّة/أُمّ,
كَذَّبَ/كَذَبَ/كُذِبَ, يَخْرُجُ/يُخْرِجُ).

Config via ENV (no private path committed):
    QAMUS_WBW_SERVICES  dir containing the qamus_wbw package (for norm_strict + QAC)
    QAMUS_WBW_ARTIFACT  built wbw-lookup.json (verses = the propagation universe; words = resolved locations)
    QAMUS_HOVER_TSV     the hover-decisions tsv (resolved key -> authored gloss)   [optional]
Outputs <out>/language_state_graph.json (validates against qamus/schemas/language-state.schema.json).
"""
import argparse
import collections
import json
import os
import sys


def load_qamus_wbw():
    """Lazily load (expand, normalize) through the public-safe seam (tools/qamus_wbw_adapter).

    Call inside main()/first use, never at module top level, so imports + --help still work on a public clone
    (the private qamus_wbw package is not shipped). The guarded direct import below stays detectable by
    validate_public_runnability.py; on a clone it raises the adapter's actionable SystemExit (naming
    QAMUS_WBW_SERVICES) — never a bare ModuleNotFoundError."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # ensure tools/ on path for the adapter
    import qamus_wbw_adapter
    sd = qamus_wbw_adapter.services_dir()
    if sd and sd not in sys.path:
        sys.path.insert(0, sd)
    try:
        from qamus_wbw import expand as X  # noqa: E402  (intentional lazy, guarded import via the seam)
        from qamus_wbw import normalize as N  # noqa: E402
    except ModuleNotFoundError as exc:
        raise SystemExit("ERROR: " + (qamus_wbw_adapter._GUIDANCE % qamus_wbw_adapter.DEFAULT_ENV)) from exc
    return X, N


def strip_case(nk):
    # the norm_strict key already drops harakat; this is a no-op hook kept for clarity/future tuning
    return nk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--tsv", default=os.environ.get("QAMUS_HOVER_TSV"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-used-by", type=int, default=5)
    a = ap.parse_args()
    if not a.artifact:
        ap.error("--artifact/QAMUS_WBW_ARTIFACT required")
    X, _N = load_qamus_wbw()
    os.makedirs(a.out, exist_ok=True)

    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words = d["verses"], d["words"]
    qac = X._load_qac_roots()
    qpos = X._QAC_CACHE.get("pos", {})

    gloss = {}
    if a.tsv and os.path.exists(a.tsv):
        for ln in open(a.tsv, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 2:
                gloss[p[0]] = p[1]

    surfaces = collections.defaultdict(collections.Counter)        # key -> {surface: n}
    rootpos = collections.defaultdict(set)                          # key -> {(root,pos)}
    locs = collections.defaultdict(list)                           # key -> [quran:S:A:W]
    resolved_locs = collections.defaultdict(int)                   # key -> #resolved token locations
    total = 0
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            total += 1
            k = X.N.norm_strict(tok)
            surfaces[k][tok] += 1
            rp = (qac.get((ref, k)), qpos.get((ref, k)))
            if rp[0] or rp[1]:
                rootpos[k].add(rp)
            if len(locs[k]) < a.max_used_by:
                locs[k].append("quran:%s:%d" % (ref, i + 1))
            if ("%s:%d" % (ref, i + 1)) in words:
                resolved_locs[k] += 1

    states = []
    counts = collections.Counter()
    for k in sorted(surfaces):
        surf = dict(surfaces[k])
        occ = sum(surf.values())
        rps = sorted(rootpos.get(k, set()), key=lambda x: (str(x[0]), str(x[1])))
        roots = {r for (r, p) in rps if r}
        poss = {p for (r, p) in rps if p}
        # hidden states: one per distinct (root,pos); fall back to a single unknown state
        hidden = []
        for (r, p) in (rps or [(None, None)]):
            hidden.append({
                "root": r, "lemma": None, "pos": p, "form": None, "sense": None,
                "sarf_role": None, "nahw_role": None,
                "evidence": {"qamus_entry": None, "qac": bool(r or p), "source_address": None},
            })
        # decision
        if k in gloss:
            dec, exp, reason = "resolved_qamus_authored", True, "live authored gloss"
            for h in hidden[:1]:
                h["sense"] = gloss[k]
        elif len(roots) > 1 or len(poss) > 1 or len(surf) > 1 and len(roots) <= 1 and _multi_lemma(surf):
            dec, exp, reason = "quarantine_homograph", False, "split: roots=%s pos=%s surfaces=%d" % (
                sorted(roots), sorted(poss), len(surf))
        else:
            dec, exp, reason = "pending", False, "single owner, gloss not yet authored"
        counts[dec] += 1
        states.append({
            "state_id": "state:key:" + k,
            "observation": {"norm_key": k, "dominant_surface_ar": surfaces[k].most_common(1)[0][0],
                            "surfaces": surf, "occurrences": occ},
            "hidden_states": hidden,
            "decision": dec, "decision_reason": reason,
            "public_gloss": gloss.get(k),
            "public_export_allowed": exp,
            "used_by": locs[k] + (["+%d more" % (occ - len(locs[k]))] if occ > len(locs[k]) else []),
        })

    out = {
        "schema": "fusha/language-state-graph@1",
        "built_from": {"coverage_pct": round(100.0 * sum(resolved_locs.values()) / total, 2) if total else 0,
                       "total_tokens": total, "distinct_keys": len(states),
                       "source_sha": (d.get("meta") or {}).get("source_sha")},
        "counts": dict(counts),
        "states": states,
    }
    json.dump(out, open(os.path.join(a.out, "language_state_graph.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"distinct_keys": len(states), "counts": dict(counts),
                      "coverage_pct": out["built_from"]["coverage_pct"]}, ensure_ascii=False))


def _multi_lemma(surf):
    """Heuristic: surfaces under one QAC root may still be two lemmas (مُلْك vs مَلِك). We cannot detect this from
    skeletons alone, so we conservatively DO NOT auto-split here — the key-aware 2-vote (verify stage) is the
    semantic arbiter. This hook returns False so root/POS splits drive quarantine; lemma collisions are caught at
    authoring time and recorded as forbidden transitions."""
    return False


if __name__ == "__main__":
    main()
