#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""closure-2092 Phase 5/6 — candidate generator for the `missing_form_variant_on_existing_entry` +
`forms_array_missing_surface` levers (the top root-cause queue).

Every pending token here has a QAC root that already resolves to a Qamus entry — but the inflected
form isn't glossed. This is NOT a free add_form: the surface may be a noun/participle while the entry
gloss is verbal, the entry may be multi-sense, or it may be a same-root/different-lexeme collision.
So each candidate is a SURFACE FAMILY (collision-free only) carrying the deciding evidence; a 2-vote
sarf+nahw verifier authors ONE POS-correct, sense-selected gloss valid across all its occurrences, or
rejects. Approved families apply surface-wide via per-loc token decisions.

Read-only. Outputs out/hover_stage/form_variant_cand.jsonl (one row per surface family).
"""
import argparse, json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_all_hover_tokens as A
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT, "out", "hover_stage"))
LED = os.path.join(ROOT, "qamus", "reports", "closure-2092", "blocker-root-cause-ledger.jsonl")
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(STAGE, "form_variant_cand.jsonl"))
    ap.add_argument("--max-a", type=int, default=999999)
    ap.add_argument("--max-b", type=int, default=160)
    ap.add_argument("--max-c", type=int, default=160)
    a = ap.parse_args()

    wbw = json.load(open(os.path.join(STAGE, "wbw-lookup.json"), encoding="utf-8"))
    verses = wbw["verses"]
    ent = {}
    for ln in open(DATA, encoding="utf-8"):
        e = json.loads(ln); ent[e["id"]] = e
    FN = {"ما","وما","فما","ان","وان","فان","لم","لما","ولما","فلما","من","ومن","فمن","لمن","ام","او",
          "لو","ولو","ال","بل","قد","ها","ذا","اذ","واذ","اذا","واذا","لا","ولا","فلا","الا","ألا","ثم",
          "حتى","اذن","لن","كل","كلا","انّ","ليت","لعل","لكن","كي","لكي","اي","نعم","بلى","قط","لمّا","ان"}

    def rootcc(r):
        return (r or "").replace(" ", "")

    # group collision-free form-variant rows by surface (nk)
    fams = collections.defaultdict(lambda: {"locs": [], "surfaces": set(), "tier": None,
                                            "qac_root": None, "qpos": None, "entry": None})
    for ln in open(LED, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        r = json.loads(ln)
        if r.get("root_cause") not in ("missing_form_variant_on_existing_entry", "forms_array_missing_surface"):
            continue
        if r.get("homograph"):       # collisions -> per-loc iʿrāb lane, not surface-family
            continue
        # SAFETY: this lane is "QAC confirms a content root (N/V) that an entry hosts". Exclude
        # function words / particles / null-root surface matches (e.g. لَمَن = لـ+مَن mis-linked to منّ).
        nk = r["nk"]
        if nk in FN: continue
        if r.get("qac_pos") not in ("N", "V"): continue
        if not r.get("qac_root"): continue
        f = fams[nk]
        f["locs"].append(r["loc"]); f["surfaces"].add(r["surface"])
        f["qac_root"] = r.get("qac_root"); f["qpos"] = r.get("qac_pos")
        f["entry"] = r.get("root_entry") or r.get("host_entry")
        # family tier = best (A>B>C) seen
        order = {"A_safe": 0, "B_sense_select": 1, "C_pos_or_collision": 2}
        t = r.get("safe_tier")
        if t and (f["tier"] is None or order.get(t, 9) < order.get(f["tier"], 9)):
            f["tier"] = t

    # ayah text lookup
    def ayah_text(loc):
        sa = ":".join(loc.split(":")[:2])
        return " ".join(verses.get(sa, []))

    by_tier = collections.defaultdict(list)
    for nk, f in fams.items():
        by_tier[f["tier"]].append((nk, f))
    # rank within tier by yield (loc count) desc
    for t in by_tier:
        by_tier[t].sort(key=lambda x: -len(x[1]["locs"]))

    caps = {"A_safe": a.max_a, "B_sense_select": a.max_b, "C_pos_or_collision": a.max_c}
    chosen = []
    for t in ("A_safe", "B_sense_select", "C_pos_or_collision"):
        chosen += by_tier.get(t, [])[:caps[t]]

    out_rows = []
    skipped_root_mismatch = 0
    for nk, f in chosen:
        e = ent.get(f["entry"], {})
        # confirm the entry is for the SAME root QAC assigns (guards surface-collision mis-links)
        if f["qac_root"] and rootcc(e.get("root", "")) and rootcc(e.get("root", "")) != f["qac_root"]:
            skipped_root_mismatch += 1
            continue
        senses = [{"gloss": s.get("gloss"), "ar": s.get("ar"), "translit": s.get("translit")}
                  for s in e.get("senses", [])][:6]
        examples = []
        for loc in f["locs"][:3]:
            examples.append({"loc": loc, "ayah": ayah_text(loc)[:400]})
        out_rows.append({
            "nk": nk, "surface": sorted(f["surfaces"])[0], "all_surfaces": sorted(f["surfaces"])[:4],
            "tier": f["tier"], "qac_root": f["qac_root"], "qac_pos": f["qpos"],
            "occurrences": len(f["locs"]), "locs": f["locs"],
            "entry_id": f["entry"], "entry_headword": e.get("headword"),
            "entry_root": e.get("root"), "entry_senses": senses,
            "examples": examples,
        })
    out_rows.sort(key=lambda r: -r["occurrences"])
    with open(a.out, "w", encoding="utf-8", newline="\n") as fo:
        for r in out_rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")

    tier_c = collections.Counter(r["tier"] for r in out_rows)
    tok = sum(r["occurrences"] for r in out_rows)
    print("FORM-VARIANT CANDIDATES: %d families, %d tokens covered" % (len(out_rows), tok))
    print("by tier:", dict(tier_c))
    print("skipped (entry root != QAC root):", skipped_root_mismatch)
    print("out ->", a.out)

if __name__ == "__main__":
    main()
