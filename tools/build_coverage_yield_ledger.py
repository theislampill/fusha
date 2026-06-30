#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase B — coverage-yield ledger: rank the path to 90% by SAFE resolved-token yield.

The lever is the surface-family: one safe gloss for a collision-free surface unlocks ALL its pending
occurrences. This ledger groups every pending token by norm_strict surface, counts occurrences,
flags collision (distinct QAC roots / vocalized surfaces), checks dataset coverage, and ranks by
yield among the SAFE (collision-free) families. Outputs the ranked ledger + a candidate file for the
top safe surfaces. Read-only.

Env: QAMUS_WBW_SERVICES, QAMUS_WBW_ARTIFACT, QAMUS_DATASET.
"""
import argparse, json, os, re, sys, collections


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


FN = {"ما","وما","فما","ان","وان","فان","لم","لما","من","ومن","فمن","ام","او","لو","ولو","ال","بل","قد",
      "ها","ذا","اذ","اذا","لا","ولا","فلا","انا","انّ","لن","كل","كلا","الا","ألا","ثم","حتى","اذن"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--dataset", default=os.environ.get("QAMUS_DATASET", "/tmp/entries.jsonl"))
    ap.add_argument("--out", required=True); ap.add_argument("--cand", required=True)
    ap.add_argument("--target", type=int, default=3634)
    a = ap.parse_args()
    X, N = load_qamus_wbw()
    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words, pending = d["verses"], d["words"], d.get("pending", {})
    X._load_qac_roots(); qroot = X._QAC_CACHE.get("root", {}); qpos = X._QAC_CACHE.get("pos", {})

    # dataset key set + glosses (for has_entry + base gloss)
    ds = {}
    for line in open(a.dataset, encoding="utf-8"):
        e = json.loads(line)
        g = [s.get("gloss") for s in e.get("senses", []) if s.get("gloss")] or [e.get("definition")]
        for k in [N.norm_strict(e.get("headword",""))]:
            if k: ds.setdefault(k, (e["section"], g[:2], e["id"]))
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                for t in re.findall(r"[؀-ۿ]+", fstr):
                    k = N.norm_strict(t)
                    if k: ds.setdefault(k, (e["section"], g[:2], e["id"]))

    fam = collections.defaultdict(lambda: {"count":0,"roots":set(),"surfaces":set(),"locs":[],"pos":set()})
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i+1)
            if loc in words: continue
            k = N.norm_strict(tok)
            f = fam[k]
            f["count"] += 1; f["surfaces"].add(tok); f["locs"].append(loc)
            r = qroot.get((ref, k));  p = qpos.get((ref, k))
            if r: f["roots"].add(r)
            if p: f["pos"].add(p)

    rows = []
    for k, f in fam.items():
        collision_free = len(f["roots"]) <= 1 and len(f["surfaces"]) <= 1
        rows.append({"key": k, "count": f["count"], "distinct_roots": len(f["roots"]),
                     "distinct_surfaces": len(f["surfaces"]),
                     "sample_surface": sorted(f["surfaces"])[0] if f["surfaces"] else "",
                     "all_surfaces": sorted(f["surfaces"])[:4],
                     "collision_free": collision_free,
                     "is_function_word": k in FN,
                     "has_dataset_entry": k in ds,
                     "dataset_hint": ds.get(k, [None])[0] if k in ds else None,
                     "qac_root": (sorted(f["roots"])[0] if f["roots"] else None),
                     "qac_pos": (sorted(f["pos"])[0] if f["pos"] else None),
                     "locs": f["locs"]})
    rows.sort(key=lambda r: -r["count"])

    # cumulative safe yield among collision-free, single-surface, content (non-function) families
    safe = [r for r in rows if r["collision_free"] and not r["is_function_word"] and r["count"] >= 2]
    cum = 0; cutoff = 0
    for r in safe:
        cum += r["count"]; cutoff += 1
        if cum >= a.target * 1.20: break  # 20% buffer
    chosen = safe[:cutoff]
    # emit candidate file: one row per chosen surface (author one gloss for the whole family)
    with open(a.cand, "w", encoding="utf-8", newline="\n") as f:
        for r in chosen:
            f.write(json.dumps({"key": r["key"], "sample_surface": r["sample_surface"],
                                "all_surfaces": r["all_surfaces"], "count": r["count"],
                                "qac_root": r["qac_root"], "qac_pos": r["qac_pos"],
                                "has_dataset_entry": r["has_dataset_entry"],
                                "dataset_hint": r["dataset_hint"], "locs": r["locs"]}, ensure_ascii=False) + "\n")
    # ledger json (lite — no per-loc lists)
    lite = [{k: r[k] for k in r if k != "locs"} for r in rows[:400]]
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"total_pending": sum(r["count"] for r in rows), "target_resolves": a.target,
                   "distinct_pending_surfaces": len(rows),
                   "safe_collisionfree_content_surfaces": len(safe),
                   "cumulative_safe_yield_top": cum, "chosen_surfaces": cutoff,
                   "top_families": lite}, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    print(json.dumps({"total_pending": sum(r["count"] for r in rows),
                      "distinct_surfaces": len(rows),
                      "safe_families": len(safe),
                      "chosen_for_target": cutoff,
                      "chosen_cumulative_yield": cum,
                      "function_word_pending": sum(r["count"] for r in rows if r["is_function_word"]),
                      "collision_pending": sum(r["count"] for r in rows if not r["collision_free"])},
                     ensure_ascii=False))

if __name__ == "__main__":
    main()
