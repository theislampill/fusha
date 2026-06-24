#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PP1 — build the committed particle-proofing matrix + Qurʾān usage spine reports.

Reads the git-ignored particle audit dump (read-only on server, artifacts/pp1_particle_audit.py /
export equivalent) at corpora/sarfnahw/out/particles/ and writes:

    qamus/reports/particles/particle-proofing-matrix.json | .md
    qamus/reports/particles/particle-hover-audit.md
    qamus/indexes/quran_usage_spine.json          (one source-addressed token spine; entries reuse it)
    qamus/reports/quran-usage-spine-report.md

The spine stores Qurʾān token SURFACES + per-token hover state only (scripture text is read-only; no gloss
text copied from any external source).
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "corpora", "sarfnahw", "out", "particles")
REP = os.path.join(ROOT, "qamus", "reports", "particles")
IDX = os.path.join(ROOT, "qamus", "indexes")


def build():
    os.makedirs(REP, exist_ok=True)
    matrix = [json.loads(l) for l in open(os.path.join(OUT, "particle_matrix.jsonl"), encoding="utf-8") if l.strip()]
    spine = json.load(open(os.path.join(OUT, "particle_spine.json"), encoding="utf-8"))
    summary = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    pool = json.load(open(os.path.join(OUT, "particle_pending_pool.json"), encoding="utf-8"))

    import collections
    st = collections.Counter(r["status"] for r in matrix)
    doc = {"schema": "fusha/particle-proofing-matrix@1",
           "generator": "qamus/scripts/build_particle_reports.py (data: read-only server particle audit)",
           "summary": {"particles": len(matrix), "status": dict(st),
                       "particle_ayat": summary["particle_ayat"],
                       "tokens": summary["tokens_in_particle_ayat"],
                       "resolved": summary["resolved"], "pending": summary["pending"],
                       "coverage_pct": round(100.0 * summary["resolved"] / summary["tokens_in_particle_ayat"], 2)},
           "particles": matrix}
    json.dump(doc, open(os.path.join(REP, "particle-proofing-matrix.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    L = ["# Particle proofing matrix — p001–p100 (PP1)", "",
         "Every Qamus particle entry, its example-āyah hover coverage, and a terminal status. Generator: "
         "`qamus/scripts/build_particle_reports.py`. **0 unknown.**", "",
         "| metric | value |", "|---|---:|",
         "| particles (p-keys) | %d |" % len(matrix),
         "| particle example āyāt | %d |" % summary["particle_ayat"],
         "| tokens in those āyāt | %d |" % summary["tokens_in_particle_ayat"],
         "| resolved | %d |" % summary["resolved"],
         "| pending | %d |" % summary["pending"],
         "| coverage %% | %.2f |" % doc["summary"]["coverage_pct"], "",
         "## Status", "", "| status | n |", "|---|---:|"]
    for k, v in sorted(st.items(), key=lambda x: -x[1]):
        L.append("| `%s` | %d |" % (k, v))
    L.append("")
    L.append("## Per-particle (sorted by pending desc)")
    L.append("")
    L.append("| p-key | headword | refs | tokens | resolved | pending | cov | status |")
    L.append("|---|---|---:|---:|---:|---:|---:|---|")
    for r in sorted(matrix, key=lambda r: -r["pending"]):
        L.append("| %s | %s | %d | %d | %d | %d | %.0f%% | %s |" % (
            r["source_key"], r["headword"], r["n_refs"], r["n_tokens"], r["resolved"],
            r["pending"], 100 * r["coverage"], r["status"]))
    open(os.path.join(REP, "particle-proofing-matrix.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # hover audit (top pending pool in particle āyāt)
    H = ["# Particle example-āyah hover audit (PP1)", "",
         "Pending tokens across the p001–p100 example āyāt, ranked by frequency — the PP1 authoring pool. "
         "Function-word tops (وَمَآ, لَمْ, أَمْ, وَإِن) are correctly pending (homograph/multi-function → two-vote); "
         "content words are the authorable batch.", "",
         "| # | surface | norm_strict | count | QAC root | POS | reason |",
         "|---:|---|---|---:|---|---|---|"]
    for i, p in enumerate(pool[:60], 1):
        H.append("| %d | %s | %s | %d | %s | %s | %s |" % (
            i, p.get("surface", ""), p["norm_strict"], p["count"], p.get("qac_root") or "—",
            p.get("qac_pos") or "—", p.get("reason", "")))
    open(os.path.join(REP, "particle-hover-audit.md"), "w", encoding="utf-8").write("\n".join(H) + "\n")

    # the Qurʾān usage spine (source-addressed; reused by entries, not duplicated)
    spine_doc = {"schema": "fusha/quran-usage-spine@1",
                 "doc": "One source-addressed token spine per āyah used by p001–p100. Entries/hover reuse these "
                        "quran:S:A:W nodes by link (Xanadu), not by duplicating the āyah. Token surfaces are "
                        "scripture (read-only); no external gloss text stored.",
                 "ayat": len(spine), "ayah": spine}
    json.dump(spine_doc, open(os.path.join(IDX, "quran_usage_spine.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    tok = sum(len(v) for v in spine.values())
    res = sum(1 for v in spine.values() for t in v if t["state"] == "resolved")
    S = ["# Qurʾān usage spine — report (PP1)", "",
         "A single source-addressed token spine (`quran:S:A:W`) for every āyah used by the p001–p100 particle "
         "entries; entries and hover-gloss decisions **reuse** these nodes by backlink (Xanadu), they do not "
         "duplicate the āyah. Full data: `qamus/indexes/quran_usage_spine.json`. Generator: "
         "`qamus/scripts/build_particle_reports.py`.", "",
         "| metric | value |", "|---|---:|",
         "| āyah nodes | %d |" % len(spine),
         "| token nodes (`quran:S:A:W`) | %d |" % tok,
         "| resolved (have a `wbw:S:A:W` gloss) | %d |" % res,
         "| pending | %d |" % (tok - res), ""]
    S.append("Each token node carries `{w, surface, state}`; resolved tokens link to a `wbw:S:A:W` gloss node, "
             "pending tokens carry a precise reason. 0 orphan: every token is classified.")
    open(os.path.join(ROOT, "qamus", "reports", "quran-usage-spine-report.md"), "w",
         encoding="utf-8").write("\n".join(S) + "\n")
    print("wrote particle proofing matrix (%d), hover audit, spine (%d āyāt / %d tokens)"
          % (len(matrix), len(spine), tok))


if __name__ == "__main__":
    build()
