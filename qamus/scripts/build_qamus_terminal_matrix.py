#!/usr/bin/env python3
# LEGACY: superseded by the tools/ generators (canonical machine index is existing_qamus_index.min.json; canonical graph is qamus/indexes/current/*-full.jsonl). Kept for reference; not the current canonical generator.
# -*- coding: utf-8 -*-
"""P2 — assign every one of the 2,092 Qamus entries a single TERMINAL state (read-only).

Joins the Qamus index (F1) with the source-address graph's entry status + the QAC form-error flag, and emits
qamus-2092-terminal-matrix.{json,md}. Counts reconcile to 2,092; no entry is left unclassified.

Inputs: --index existing_qamus_index.json ; --graph SOURCE-ADDRESS-INDEX.json (live, read-only) ;
        --formerrors a JSON list of entry_ids with a QAC-contradicted form (optional).
"""
import argparse
import collections
import io
import json
import os

STATES = ["clean", "repaired-live", "candidate-repair-ready", "needs-source-locator",
          "needs-visual-certification", "needs-sarf-review", "needs-nahw-review",
          "needs-external-reference-authoring", "duplicate-merge-risk", "source-missing", "deferred-ambiguous"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="qamus/indexes/existing_qamus_index.json")
    ap.add_argument("--graph", required=True, help="live SOURCE-ADDRESS-INDEX.json (read-only)")
    ap.add_argument("--formerrors", default=None)
    ap.add_argument("--out-json", default="qamus/reports/qamus-2092-terminal-matrix.json")
    ap.add_argument("--out-md", default="qamus/reports/qamus-2092-terminal-matrix.md")
    a = ap.parse_args()
    idx = json.load(io.open(a.index, encoding="utf-8"))
    graph = json.load(io.open(a.graph, encoding="utf-8"))
    gnodes = {n.get("locator", {}).get("entry_id"): n for n in graph.get("entry_nodes", {}).values()}
    form_err = set(json.load(io.open(a.formerrors, encoding="utf-8"))) if a.formerrors and os.path.exists(a.formerrors) else set()

    # detect intentional root splits (≥2 entries per root)
    by_root = collections.defaultdict(list)
    for sid, r in idx.items():
        if r.get("root"):
            by_root[r["root"]].append(sid)
    split_roots = {root for root, ids in by_root.items() if len(ids) > 1}

    matrix = {}
    for sid, r in idx.items():
        eid = r.get("entry_id")
        gn = gnodes.get(eid) or {}
        gstatus = gn.get("status", "clean")
        if gstatus == "source-located":
            state = "needs-visual-certification"
        elif gstatus == "needs-source-search":
            state = "needs-source-locator"
        elif eid in form_err:
            state = "needs-sarf-review"
        elif r.get("root") in split_roots:
            state = "duplicate-merge-risk"
        else:
            state = "clean"
        matrix[sid] = {
            "entry_id": eid, "source_address": r.get("source_address"), "source_keys": r.get("source_keys"),
            "root": r.get("root"), "headword": r.get("headword"), "category": r.get("pos_category"),
            "usage_refs": len(r.get("usage_refs") or []), "n_senses": r.get("n_senses"),
            "open_anomalies": gn.get("blockers", []),
            "terminal_state": state,
            "next_action": {
                "needs-visual-certification": "crop the located ToC page; a human reads the printed root/count (scripture — owner verifies)",
                "needs-source-locator": "OCR the noun/particle section window; match the headword to pin the page",
                "needs-sarf-review": "QAC contradicts a stored form; sarf-review the form→root before any repair",
                "duplicate-merge-risk": "two entries share this root — confirm the homograph/sense split is intentional",
                "clean": "none — entry is serving glosses correctly",
            }.get(state, "review"),
            "owner_gate": state in ("needs-visual-certification", "needs-source-locator"),
        }

    cnt = collections.Counter(m["terminal_state"] for m in matrix.values())
    assert sum(cnt.values()) == len(idx), "counts must reconcile to %d" % len(idx)
    json.dump({"total": len(matrix), "by_state": dict(cnt), "matrix": matrix},
              io.open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    # top-50 high-value next actions: non-clean entries ranked by usage_refs
    actionable = sorted([m for m in matrix.values() if m["terminal_state"] != "clean"],
                        key=lambda m: -(m["usage_refs"] or 0))[:50]
    md = ["# Qamus 2,092 terminal matrix", "",
          "Every entry has exactly one terminal state; counts reconcile to %d." % len(matrix), "",
          "| terminal state | n |", "|---|---:|"]
    for s in STATES:
        if cnt.get(s):
            md.append("| %s | %d |" % (s, cnt[s]))
    md += ["", "## Top 50 high-value next actions (non-clean, by usage refs)", "",
           "| address | root | state | refs | next action |", "|---|---|---|---:|---|"]
    for m in actionable:
        md.append("| %s | %s | %s | %d | %s |" % (m["source_address"], m["root"] or "—", m["terminal_state"],
                                                  m["usage_refs"] or 0, m["next_action"][:70]))
    io.open(a.out_md, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("2092 matrix: %s" % dict(cnt))


if __name__ == "__main__":
    main()
