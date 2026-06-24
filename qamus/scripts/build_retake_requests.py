#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate qamus/reports/retake-source-photo-requests.md from the entry audit dump (read-only).

The source-photo queue is the authoring FLOOR: entries whose example ayat are hover-complete but whose ENTRY
FIELDS are not yet verified against the photographed source (owner-gated). This lists them so the owner can
retake/verify. No live writes.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUD = os.path.join(ROOT, "corpora", "sarfnahw", "out", "audit", "entry_audit.jsonl")
OUT = os.path.join(ROOT, "qamus", "reports", "retake-source-photo-requests.md")
TICK = chr(96)  # backtick, kept out of any shell


def code(s):
    return TICK + s + TICK


def main():
    rows = [json.loads(l) for l in open(AUD, encoding="utf-8") if l.strip()]
    photo = sorted([r for r in rows if r["terminal_state"] == "needs_source_photo_review"],
                   key=lambda r: -r["n_ayah_refs"])
    ref = [r for r in rows if r["terminal_state"] == "needs_quran_ref_verification"]
    defr = [r for r in rows if r["terminal_state"] == "deferred_missing_source"]
    L = ["# Source-photo retake / verification requests", "",
         "Entries whose example ayat are now hover-complete but whose ENTRY FIELDS (headword, forms, senses, "
         "sense-counts, total_uses) are not yet verified against the photographed source. This is the authoring "
         "FLOOR — these need the physical source corpus (owner-gated). Public hover for these entries is "
         "already live and correct; this queue certifies the ENTRY DATA, not the hover aid.", "",
         "| queue | n | what is needed |", "|---|---:|---|",
         "| %s | %d | photograph the source page; verify headword/forms/senses/counts |"
         % (code("needs_source_photo_review"), len(photo)),
         "| %s | %d | fix bad/range ayah refs before re-audit |" % (code("needs_quran_ref_verification"), len(ref)),
         "| %s | %d | no addressable ayat; locate source or mark out-of-scope |"
         % (code("deferred_missing_source"), len(defr)), "",
         "## Top entries to verify next (by ayah-ref count)", "",
         "| entry_id | source_address | root | headword | refs | hover_cov |", "|---|---|---|---|---:|---:|"]
    for r in photo[:40]:
        L.append("| %s | %s | %s | %s | %d | %.2f |" % (
            r["entry_id"], r.get("source_address", ""), r.get("root", ""), r.get("headword", ""),
            r["n_ayah_refs"], r.get("hover_coverage", 0)))
    L += ["", "## Ref-verification queue", "", "| entry_id | root | headword | refs |", "|---|---|---|---:|"]
    for r in ref:
        L.append("| %s | %s | %s | %d |" % (r["entry_id"], r.get("root", ""), r.get("headword", ""),
                                            r["n_ayah_refs"]))
    L += ["", "## Retake instructions (per entry)", "",
          "Photograph the dictionary page containing the entry's headword; crop to the entry block; record "
          "%s (internal address). The crop is a DERIVED VIEW — never the public authority. Verification then "
          "sets headword_verified / forms_verified / senses_verified / sense_counts_verified / "
          "total_count_verified true in the audit, advancing the entry toward %s."
          % (code("source-photo:<page>#entry=<source_key>"), code("fully_verified"))]
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("retake worklist: photo=%d ref=%d deferred=%d" % (len(photo), len(ref), len(defr)))


if __name__ == "__main__":
    main()
