#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P11+P12 data export — run READ-ONLY on the server, pull the output into Fusha.

Produces the audit dump that `build_audit_completion.py` turns into the committed reports:
    <out>/entry_audit.jsonl   — per Qamus entry: refs valid, QAC-root agreement, hover coverage, terminal state
    <out>/pending_top.json    — top-500 pending hover surfaces (the P13 candidate pool)
    <out>/summary.json        — reconciliation totals

Config via ENV (no private path committed):
    QAMUS_WBW_SERVICES  — dir containing the qamus_wbw package (default "services")
    QAMUS_ENTRIES       — the entries dir (or --entries)
    QAMUS_WBW_ARTIFACT  — the built wbw-lookup.json (or --artifact)

Honest: *_verified flags reflect only independently-measurable evidence (refs valid, QAC root agreement,
hover coverage). Source-photo / sense-count verification is NOT performed here -> recorded false; no entry
is fully_verified.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.environ.get("QAMUS_WBW_SERVICES", "services"))
from qamus_wbw import expand as X  # noqa: E402

REF_RE = re.compile(r"^(\d{1,3}:\d{1,3})(?::\d{1,3})?$")  # S:A or S:A:W -> S:A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", default=os.environ.get("QAMUS_ENTRIES"))
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.entries or not a.artifact:
        ap.error("--entries/QAMUS_ENTRIES and --artifact/QAMUS_WBW_ARTIFACT are required (no path hardcoded)")
    os.makedirs(a.out, exist_ok=True)

    d = json.load(open(a.artifact, encoding="utf-8"))
    words, verses = d["words"], d["verses"]
    pend_reason = d.get("pending") if isinstance(d.get("pending"), dict) else {}
    qac = X._load_qac_roots()
    qpos = X._QAC_CACHE.get("pos", {})

    state_c = collections.Counter()
    pend_surf = collections.Counter()
    pend_meta = {}
    tok_state = {}
    total = 0
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            total += 1
            nst = X.N.norm_strict(tok)
            if loc in words:
                st = "resolved_qamus_authored"
            else:
                qr = qac.get((ref, nst)); pos = qpos.get((ref, nst)) or ""
                r = str(pend_reason.get(loc, ""))
                if "proper" in r or pos == "PN":
                    st = "pending_proper_noun"
                elif qr is None and not pos:
                    st = "pending_source_data_issue"
                elif not qr and pos:
                    st = "pending_no_qamus_entry"
                else:
                    st = "pending_needs_sarf"
                pend_surf[nst] += 1
                pend_meta.setdefault(nst, {"surface": tok, "qac_root": qr or None,
                                          "qac_pos": pos or None, "example_loc": loc})
            tok_state[loc] = st
            state_c[st] += 1

    ent_states = collections.Counter()
    rows = []
    for f in sorted(glob.glob(os.path.join(a.entries, "*.json"))):
        e = json.load(open(f, encoding="utf-8"))
        eid = e.get("entry_id") or os.path.basename(f).replace(".json", "")
        root = (e.get("root") or "").strip()
        refs, bad = [], False
        for blk in e.get("usage") or []:
            for ex in blk.get("examples") or []:
                ref = (ex.get("ref") or "").strip()
                if not ref:
                    continue
                m = REF_RE.match(ref)
                if m:
                    refs.append(m.group(1))
                else:
                    bad = True
        refs = sorted(set(refs))
        n_tok = res = pen = 0
        qac_roots = collections.Counter()
        for r in refs:
            for i, tok in enumerate(verses.get(r, [])):
                loc = "%s:%d" % (r, i + 1)
                n_tok += 1
                if tok_state.get(loc, "").startswith("resolved"):
                    res += 1
                else:
                    pen += 1
                qr = qac.get((r, X.N.norm_strict(tok)))
                if qr:
                    qac_roots[qr] += 1
        cov = (res / n_tok) if n_tok else 0.0
        if not refs:
            ts = "deferred_missing_source"
        elif bad:
            ts = "needs_quran_ref_verification"
        elif pen > 0:
            ts = "needs_hover_authoring"
        elif n_tok:
            ts = "needs_source_photo_review"
        else:
            ts = "deferred_missing_source"
        ent_states[ts] += 1
        rows.append({
            "entry_id": eid, "source_keys": e.get("source_keys") or [], "root": root,
            "headword": e.get("headword", ""), "category": e.get("category", ""),
            "source_address": "qamus:%s#root=%s" % ((e.get("source_keys") or ["?"])[0], root),
            "n_ayah_refs": len(refs), "refs_valid": (not bad and bool(refs)),
            "n_tokens": n_tok, "hover_resolved": res, "hover_pending": pen, "hover_coverage": round(cov, 3),
            "root_verified_vs_qac": bool(root and root in qac_roots),
            "headword_verified": False, "forms_verified": False, "senses_verified": False,
            "sense_counts_verified": False, "total_count_verified": False,
            "usage_refs_verified": (not bad and bool(refs)), "examples_verified": False,
            "source_photo_verified": False, "external_reference_authoring": "none",
            "source_corpus_certification": "none", "terminal_state": ts,
        })

    with open(os.path.join(a.out, "entry_audit.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    top = [{"norm_strict": k, "count": c, **pend_meta[k]} for k, c in pend_surf.most_common(500)]
    json.dump(top, open(os.path.join(a.out, "pending_top.json"), "w", encoding="utf-8"), ensure_ascii=False)
    summary = {
        "entries": len(rows), "entry_terminal_states": dict(ent_states),
        "hover_total_tokens": total, "hover_states": dict(state_c),
        "hover_resolved": state_c.get("resolved_qamus_authored", 0),
        "distinct_pending_surfaces": len(pend_surf),
        "coverage_pct": round(100.0 * state_c.get("resolved_qamus_authored", 0) / total, 2) if total else 0,
        "unknown_entries": ent_states.get("unknown", 0),
    }
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
