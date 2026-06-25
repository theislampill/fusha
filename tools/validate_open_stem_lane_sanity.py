#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open-stem lane-sanity gate — fail closed on the exact queue-shaping defects the deep-research
audits found, so a polluted queue can never be handed to an authoring tranche.

Fails if:
  - host_lexeme_possessive_candidate has qac_pos == "V"            (verb-clitic in possessive-noun lane)
  - missing_qamus_entry_candidate flatten-matches an existing entry (unflattened-root misroute)
  - missing_form_variant_on_existing_entry / forms_array_missing_surface target an entry that already
    contains the surface in usage[].forms or headword               (false authoring blocker)
  - forms_array_missing_surface counts qac_pos==P / function-word material as form work
  - a function-word bundle (raw ما/من/هل/clitic) is routed as open-stem authoring
  - the root-cause summary totals disagree with the JSONL ledger
Read-only. Exit non-zero on any defect.
"""
import json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "qamus", "reports", "closure-2092")
LED = os.path.join(D, "blocker-root-cause-ledger.jsonl")
SUMM = os.path.join(D, "blocker-root-cause-summary.json")
IDX = os.path.join(ROOT, "qamus", "indexes", "current")
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")

AUTHORING_LANES = {"missing_form_variant_on_existing_entry", "forms_array_missing_surface",
                   "host_lexeme_possessive_candidate", "missing_qamus_entry_candidate"}
# use the SAME function-word set the ledger guards on, so the validator can never flag a surface the
# ledger's guard would miss (no FN-set drift between generator and validator)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_led", os.path.join(ROOT, "tools", "build_blocker_root_cause_ledger.py"))
_led = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_led)
FN = _led.FN

def flat(s):
    return (s or "").replace(" ", "").replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ء","").replace("ؤ","و").replace("ئ","ي").replace("ى","ي")

def main():
    fails = []
    rows = [json.loads(l) for l in open(LED, encoding="utf-8") if l.strip() and '"loc"' in l]

    # build entry form/headword keysets + flattened-root index
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("_aud", os.path.join(ROOT, "tools", "audit_all_hover_tokens.py"))
    A = ilu.module_from_spec(spec); spec.loader.exec_module(A)
    ent_forms = {}
    by_root_flat = collections.defaultdict(set)
    for l in open(DATA, encoding="utf-8"):
        e = json.loads(l)
        forms = {A.norm_strict(e.get("headword",""))}
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                for t in str(fstr).split():
                    forms.add(A.norm_strict(t))
        ent_forms[e["id"]] = forms
        if e.get("root"):
            by_root_flat[flat(e["root"])].add(e["id"])

    hl_v = mqe_re = fa_p = fv_present = fn_stem = 0
    for r in rows:
        rc = r["root_cause"]; qp = r.get("qac_pos"); nk = r.get("nk"); qr = r.get("qac_root")
        if rc == "host_lexeme_possessive_candidate" and qp == "V":
            hl_v += 1
        if rc == "missing_qamus_entry_candidate" and qr and flat(qr) in by_root_flat:
            mqe_re += 1
        if rc == "forms_array_missing_surface" and (qp == "P" or nk in FN):
            fa_p += 1
        if rc in ("missing_form_variant_on_existing_entry", "forms_array_missing_surface"):
            tgts = [t for t in (r.get("root_entry"), r.get("host_entry")) if t]
            if any(nk in ent_forms.get(t, set()) for t in tgts):
                fv_present += 1
        if rc in AUTHORING_LANES and (nk in FN or qp == "P"):
            fn_stem += 1
    if hl_v: fails.append(f"{hl_v} host_lexeme_possessive_candidate rows have qac_pos==V (verb-clitic contamination)")
    if mqe_re: fails.append(f"{mqe_re} missing_qamus_entry_candidate rows flatten-match an existing entry (root-flatten misroute)")
    if fa_p: fails.append(f"{fa_p} forms_array_missing_surface rows are function-word/particle (not form work)")
    if fv_present: fails.append(f"{fv_present} form-authoring rows target an entry that already contains the form (false blocker)")
    if fn_stem: fails.append(f"{fn_stem} function-word/particle rows routed into an open-stem authoring lane")

    # summary/ledger reconciliation
    if os.path.exists(SUMM):
        s = json.load(open(SUMM, encoding="utf-8"))
        led_counts = collections.Counter(r["root_cause"] for r in rows)
        summ_counts = {}
        for blk, sub in s.get("by_coarse_blocker", {}).items():
            for rc, c in sub.items():
                summ_counts[rc] = summ_counts.get(rc, 0) + c
        for rc, c in led_counts.items():
            if summ_counts.get(rc, 0) != c:
                fails.append(f"summary/ledger disagree for {rc}: ledger {c} != summary {summ_counts.get(rc,0)}")
                break

    if fails:
        print("OPEN-STEM LANE SANITY FAIL:")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("OPEN-STEM LANE SANITY OK — host-lexeme noun-only, roots flattened, no false form blockers, "
          "no function-word stem routing, summary reconciles")

if __name__ == "__main__":
    main()
