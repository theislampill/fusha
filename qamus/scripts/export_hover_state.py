#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export the live qamus-highlight per-token hover state for the P3 terminal matrix + P4 batch selection.

Read-only over the deployed artifact + the QAC reference. Run ON THE SERVER (it needs the live artifact +
qac-tokroots.tsv); the JSON it writes is pulled into Fusha (no private paths inside the JSON).

Configuration is via ENV VARS so no private/server path lives in this public repo:
  QAMUS_WBW_SERVICES  — dir containing the `qamus_wbw` package (added to sys.path). Default: "services".
  QAMUS_WBW_ARTIFACT  — path to the built wbw-lookup.json (or pass --artifact). Required if neither is set.

Outputs (to --out):
  hover_state.jsonl       — one row per token: {loc, surface, norm_strict, qac_root, qac_pos, state, conf, gloss}
  hover_pending_top.json  — top pending surfaces ranked by frequency, with QAC root/POS (P4 candidates)
  hover_state_summary.json
"""
import argparse
import collections
import io
import json
import os
import sys


def load_qamus_wbw():
    """Lazily load (expand, normalize) through the public-safe seam (tools/qamus_wbw_adapter).

    Call inside main()/first use, never at module top level, so imports + --help still work on a public clone
    (the private qamus_wbw package is not shipped). The guarded direct import below stays detectable by
    validate_public_runnability.py; on a clone it raises the adapter's actionable SystemExit (naming
    QAMUS_WBW_SERVICES) — never a bare ModuleNotFoundError."""
    _here = os.path.dirname(os.path.abspath(__file__))
    _tools = os.path.join(os.path.dirname(os.path.dirname(_here)), "tools")  # qamus/scripts -> repo/tools
    if _tools not in sys.path:
        sys.path.insert(0, _tools)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"),
                    help="built wbw-lookup.json (or set QAMUS_WBW_ARTIFACT)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.artifact:
        ap.error("--artifact or QAMUS_WBW_ARTIFACT is required (no path is hardcoded in this public repo)")
    X, N = load_qamus_wbw()
    os.makedirs(a.out, exist_ok=True)
    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words = d.get("verses", {}), d["words"]
    qac = X._load_qac_roots()
    qpos = X._QAC_CACHE.get("pos", {})

    rows = []
    state_c = collections.Counter()
    pend_surf = collections.Counter()
    pend_meta = {}
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            nst = N.norm_strict(tok)
            qr = qac.get((ref, nst))
            pos = qpos.get((ref, nst)) or ""
            rec = words.get(loc)
            if rec:
                state = "resolved:%s" % rec.get("conf", "?")
                gloss = rec["glosses"][0]["text"]
            else:
                # classify the pending reason from available evidence
                if qr is None and not pos:
                    state = "pending:source_data_issue"
                elif not qr and pos:
                    state = "pending:proper_noun" if pos == "PN" else "pending:no_qamus_entry"
                else:
                    state = "pending:root_exists_form_unresolved"
                gloss = None
                pend_surf[nst] += 1
                if nst not in pend_meta:
                    pend_meta[nst] = {"surface": tok, "qac_root": qr or None, "qac_pos": pos or None, "example_loc": loc}
            state_c[state.split(":")[0]] += 1
            rows.append({"loc": loc, "surface": tok, "norm_strict": nst, "qac_root": qr or None,
                         "qac_pos": pos or None, "state": state, "gloss": (gloss or "")[:60]})

    with io.open(os.path.join(a.out, "hover_state.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    top = []
    for nst, c in pend_surf.most_common(400):
        m = pend_meta[nst]
        top.append({"norm_strict": nst, "count": c, **m})
    json.dump(top, io.open(os.path.join(a.out, "hover_pending_top.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"tokens": len(rows), "states": dict(state_c), "distinct_pending_surfaces": len(pend_surf),
               "pending_by_reason": d.get("_meta", {}).get("coverage", {}).get("pending_by_reason", {}),
               "coverage_pct": d.get("_meta", {}).get("coverage", {}).get("pct")},
              io.open(os.path.join(a.out, "hover_state_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("tokens=%d states=%s distinct_pending=%d" % (len(rows), dict(state_c), len(pend_surf)))


if __name__ == "__main__":
    main()
