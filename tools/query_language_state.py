#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query the language state graph (qamus/indexes/language_state_graph.json).

Answers the state-machine questions:
    --key <norm_key>      why this gloss? why pending? which evidence? which surfaces/locations?
    --split               list quarantined homograph keys (the explicit splits)
    --pending [N]         list the top-N pending keys by occurrence (the next authoring pool)
    --stats               decision-class reconciliation
    --share <root>        keys whose hidden states include this root (shared-state query)

Read-only. Default graph path: qamus/indexes/language_state_graph.json (override with --graph).
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "qamus", "indexes", "language_state_graph.json")


def load(p):
    return json.load(open(p, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default=DEFAULT)
    ap.add_argument("--key")
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--pending", nargs="?", type=int, const=30)
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--share")
    a = ap.parse_args()
    g = load(a.graph)
    by = {s["observation"]["norm_key"]: s for s in g["states"]}

    if a.stats:
        print(json.dumps({"built_from": g["built_from"], "counts": g["counts"]}, ensure_ascii=False, indent=1))
        return
    if a.key:
        s = by.get(a.key)
        if not s:
            print("no state for key:", a.key); return
        print(json.dumps(s, ensure_ascii=False, indent=1))
        if s["decision"] == "quarantine_homograph":
            print("\n=> WHY PENDING: this key SPLITS across", len(s["hidden_states"]),
                  "hidden states (%s). No single gloss is safe; the key-aware 2-vote must own each surface."
                  % s["decision_reason"])
        elif s["decision"] == "resolved_qamus_authored":
            print("\n=> WHY THIS GLOSS:", json.dumps(s["public_gloss"], ensure_ascii=False),
                  "— one owner, authored, fires on", s["observation"]["occurrences"], "occurrences.")
        else:
            print("\n=> PENDING:", s["decision_reason"])
        return
    if a.split:
        q = [s for s in g["states"] if s["decision"] == "quarantine_homograph"]
        q.sort(key=lambda s: -s["observation"]["occurrences"])
        print("quarantined (split) keys:", len(q))
        for s in q[:50]:
            print("  %-12s occ=%-4d %s" % (s["observation"]["norm_key"], s["observation"]["occurrences"],
                                           s["decision_reason"]))
        return
    if a.pending is not None:
        q = [s for s in g["states"] if s["decision"] == "pending"]
        q.sort(key=lambda s: -s["observation"]["occurrences"])
        print("pending keys:", len(q), "(top %d):" % a.pending)
        for s in q[:a.pending]:
            print("  %-12s occ=%-4d surfaces=%d" % (s["observation"]["norm_key"],
                  s["observation"]["occurrences"], len(s["observation"]["surfaces"])))
        return
    if a.share:
        hits = [s["observation"]["norm_key"] for s in g["states"]
                if any(h.get("root") == a.share for h in s["hidden_states"])]
        print("keys sharing root %s:" % a.share, len(hits))
        print("  " + ", ".join(hits[:60]))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
