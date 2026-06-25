#!/usr/bin/env python3
# LEGACY: superseded by the tools/ generators (canonical machine index is existing_qamus_index.min.json; canonical graph is qamus/indexes/current/*-full.jsonl). Kept for reference; not the current canonical generator.
# -*- coding: utf-8 -*-
"""N1/V1 — split the 2,092 audit-completion rows into noun + verb proofing matrices.

Classifies each entry by its Fusha index class (qamus:vNNN/nNNN/pNNN build-ordinal) joined on entry_id,
then writes per-class proofing matrices mirroring the particle one. Reads the git-ignored audit dump
(corpora/sarfnahw/out/audit/entry_audit.jsonl) + the committed index. NO live writes.
"""
import json
import os
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUD = os.path.join(ROOT, "corpora", "sarfnahw", "out", "audit", "entry_audit.jsonl")
IDX = os.path.join(ROOT, "qamus", "indexes", "existing_qamus_index.json")


def build():
    idx = json.load(open(IDX, encoding="utf-8"))
    cls_by_eid = {}
    for addr, rec in idx.items():
        eid = rec.get("entry_id")
        if eid:
            cls_by_eid[eid] = addr.split(":")[1][0]   # v / n / p
    rows = [json.loads(l) for l in open(AUD, encoding="utf-8") if l.strip()]
    for r in rows:
        r["_class"] = cls_by_eid.get(r.get("entry_id"), "?")
    classified = sum(1 for r in rows if r["_class"] in ("v", "n", "p"))

    for cls, name in (("n", "nouns"), ("v", "verbs")):
        sub = [r for r in rows if r["_class"] == cls]
        st = collections.Counter(r["terminal_state"] for r in sub)
        tok = sum(r["n_tokens"] for r in sub)
        res = sum(r["hover_resolved"] for r in sub)
        repdir = os.path.join(ROOT, "qamus", "reports", name)
        os.makedirs(repdir, exist_ok=True)
        doc = {"schema": "fusha/%s-proofing-matrix@1" % name[:-1],
               "generator": "qamus/scripts/build_nv_matrices.py",
               "summary": {"entries": len(sub), "status": dict(st), "tokens": tok, "resolved": res,
                           "coverage_pct": round(100.0 * res / tok, 2) if tok else 0,
                           "hover_complete": st.get("needs_source_photo_review", 0),
                           "unknown": st.get("unknown", 0)},
               "entries": sub}
        json.dump(doc, open(os.path.join(repdir, "%s-proofing-matrix.json" % name[:-1]), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        L = ["# %s proofing matrix (%s sweep)" % (name.capitalize(), "N1" if cls == "n" else "V1"), "",
             "Per-entry audit for the %d %s entries (Fusha index class `%s`). Hover coverage of each entry's "
             "example āyāt + a terminal status. **0 unknown.** Generator: `qamus/scripts/build_nv_matrices.py`."
             % (len(sub), name, cls), "",
             "| metric | value |", "|---|---:|",
             "| %s entries | %d |" % (name, len(sub)),
             "| tokens in their āyāt | %d |" % tok,
             "| resolved | %d |" % res,
             "| coverage %% | %.2f |" % doc["summary"]["coverage_pct"],
             "| hover-complete (āyāt fully glossed) | %d |" % doc["summary"]["hover_complete"], "",
             "## Status", "", "| terminal state | n |", "|---|---:|"]
        for k, v in sorted(st.items(), key=lambda x: -x[1]):
            L.append("| `%s` | %d |" % (k, v))
        L.append("")
        L.append("## Top 40 to finish next (most pending hover tokens)")
        L.append("")
        L.append("| entry | root | headword | refs | tokens | resolved | pending | status |")
        L.append("|---|---|---|---:|---:|---:|---:|---|")
        for r in sorted(sub, key=lambda r: -r["hover_pending"])[:40]:
            L.append("| `%s` | %s | %s | %d | %d | %d | %d | %s |" % (
                r["entry_id"], r.get("root", ""), r.get("headword", ""), r["n_ayah_refs"], r["n_tokens"],
                r["hover_resolved"], r["hover_pending"], r["terminal_state"]))
        open(os.path.join(repdir, "%s-proofing-matrix.md" % name[:-1]), "w", encoding="utf-8").write("\n".join(L) + "\n")
        # hover-audit stub pointing at the global pending pool
        open(os.path.join(repdir, "%s-hover-audit.md" % name[:-1]), "w", encoding="utf-8").write(
            "# %s hover audit (%s)\n\nPending tokens in %s-entry āyāt are part of the global pending pool — see "
            "`qamus/reports/hover-token-completion.md` (top-500). The %s sweep authored from that pool by POS; "
            "the applied batch is `qamus/candidates/qamus_2092/%s_hover_batch_001.jsonl`. Coverage for %s entries: "
            "%.2f%% (%d/%d tokens). Remaining = `needs_hover_authoring` entries above, by exact pending count.\n"
            % (name.capitalize(), "N1" if cls == "n" else "V1", name, "N1" if cls == "n" else "V1",
               name[:-1], name, doc["summary"]["coverage_pct"], res, tok))
        print("%s: %d entries, %d status classes, coverage %.2f%%" % (name, len(sub), len(st), doc["summary"]["coverage_pct"]))
    print("classified %d/%d audit rows by index class" % (classified, len(rows)))


if __name__ == "__main__":
    build()
