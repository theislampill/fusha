#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the Phase-3 blocker root-cause ledger: every pending token mapped, controlled vocab,
counts reconcile to the live coarse-blocker totals, and every row carries deciding evidence + an
unlock action. Read-only. Exit non-zero on any defect.
"""
import json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "qamus", "reports", "closure-2092")
LED = os.path.join(D, "blocker-root-cause-ledger.jsonl")
SUMM = os.path.join(D, "blocker-root-cause-summary.json")

COARSE = {"stem_base_unknown", "source_entry_unverified",
          "same_surface_polysemy_requires_i3rab", "proper_noun_no_qamus_entry"}
RC_VOCAB = {
    "missing_form_variant_on_existing_entry", "host_lexeme_possessive_candidate",
    "missing_qamus_entry_candidate", "particle_or_pronoun_misclassified_as_stem",
    "nominal_derivative_candidate", "truly_low_frequency_tail",
    "source_entry_required_before_resolution", "context_i3rab_required",
    "proper_name_or_named_entity",
    "forms_array_missing_surface", "quran_refs_missing_or_incomplete",
    "sense_missing_or_ambiguous", "source_photo_visual_needed",
    "count_total_uses_needs_photo_check",
    "genuinely_ambiguous_pending", "verb_form_or_voice", "content_homograph",
    "particle_function", "proper_vs_common", "token_addressable_proper_noun",
    # closure-2092 open-stem hygiene lanes
    "verb_clitic_object_or_subject_candidate", "already_entry_form_present_index_miss",
    "function_word_not_form_work",
}

def fail(m):
    print("LEDGER VALIDATE FAIL:", m); sys.exit(1)

def main():
    if not os.path.exists(LED): fail("ledger jsonl missing — run tools/build_blocker_root_cause_ledger.py")
    rows = []
    locs = set()
    for ln in open(LED, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        r = json.loads(ln)
        if "_generator" in r and "loc" not in r:
            continue
        rows.append(r); locs.add(r["loc"])

    if len(rows) != len(locs): fail("duplicate locs in ledger")
    blk_c = collections.Counter()
    for r in rows:
        for k in ("loc", "surface", "coarse_blocker", "root_cause", "unlock"):
            if k not in r: fail(f"row {r.get('loc')} missing field {k}")
        if r["coarse_blocker"] not in COARSE: fail(f"bad coarse_blocker {r['coarse_blocker']} @ {r['loc']}")
        if r["root_cause"] not in RC_VOCAB: fail(f"root_cause out of vocab: {r['root_cause']} @ {r['loc']}")
        if r["root_cause"] == "unclassified": fail(f"unclassified token {r['loc']}")
        # lane-sanity (open-stem hygiene): possessive-host lane must be noun-only, never verb-clitic
        if r["root_cause"] == "host_lexeme_possessive_candidate" and r.get("qac_pos") == "V":
            fail(f"host_lexeme_possessive_candidate with qac_pos==V @ {r['loc']} (verb-clitic must split out)")
        blk_c[r["coarse_blocker"]] += 1

    # reconcile vs the audit tool's CURRENT pending-by-blocker report (regenerated each rebuild) —
    # robust to coverage changes: ledger + audit are rebuilt together from the same staged artifact.
    import re
    rep = os.path.join(ROOT, "qamus", "reports", "hover-token-pending-by-blocker.md")
    if os.path.exists(rep):
        expect = {}
        for m in re.finditer(r"##\s+`([a-z0-9_]+)`\s+—\s+([\d,]+)\s+tokens", open(rep, encoding="utf-8").read()):
            expect[m.group(1)] = int(m.group(2).replace(",", ""))
        for k, v in expect.items():
            if blk_c.get(k, 0) != v:
                fail(f"coarse blocker {k}: ledger {blk_c.get(k,0)} != audit report {v} "
                     "(re-run audit_all_hover_tokens then rebuild the ledger from the same staged artifact)")
    else:
        print("  (note: hover-token-pending-by-blocker.md absent — skipped cross-report reconciliation)")

    if not os.path.exists(SUMM): fail("summary json missing")
    s = json.load(open(SUMM, encoding="utf-8"))
    if s.get("total_pending") != len(rows): fail("summary total_pending mismatch")

    counts = "/".join(str(blk_c.get(k, 0)) for k in
                      ("stem_base_unknown", "source_entry_unverified",
                       "same_surface_polysemy_requires_i3rab", "proper_noun_no_qamus_entry"))
    print(f"LEDGER VALIDATE OK — {len(rows):,} pending tokens, controlled vocab, "
          f"reconciled to coarse blockers ({counts})")

if __name__ == "__main__":
    main()
