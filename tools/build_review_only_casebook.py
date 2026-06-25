#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 10 — review-only casebook: bucket the de-polluted pending queue into the lanes the NEXT
authoring tranche may act on, with the gate each requires. Produces NO apply payloads, NO glosses.
Read-only over the blocker-root-cause ledger. Emits casebook.md + casebook.jsonl under closure-2092/.
"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092")
LED = os.path.join(OUT, "blocker-root-cause-ledger.jsonl")

# root_cause -> (bucket #, bucket name, gate, generator, validator, contributes_to_90, next_command)
BUCKET = {
  "already_entry_form_present_index_miss": (1, "structural reroute — no authoring", "repo/reindex",
     "rebuild_surface_index_from_dataset.py", "validate_surface_index_covers_usage_forms.py", "yes (live index/resolver rebuild)",
     "owner-gated: rebuild the LIVE surface index/resolver (out of repo scope); no authoring"),
  "host_lexeme_possessive_candidate": (2, "true noun-host possessive", "2-vote",
     "build_host_lexeme_candidates.py", "validate_suffix_pronoun_decisions.py", "yes",
     "build_host_lexeme_candidates.py --max 400 -> host-lexeme 2-vote -> validate_suffix_pronoun_decisions"),
  "verb_clitic_object_or_subject_candidate": (3, "verb-clitic object/subject", "2-vote (token)",
     "(needs build_verb_clitic_candidates.py)", "validate_token_hover_decisions.py", "yes",
     "MISSING generator build_verb_clitic_candidates.py (verb + object/subject pronoun) -> token 2-vote"),
  "function_word_not_form_work": (4, "function-word / particle-pronoun", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "partial (token)",
     "build_token_irab_decisions.py (function-word subset) -> token-irab 2-vote"),
  "particle_or_pronoun_misclassified_as_stem": (4, "function-word / particle-pronoun", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "partial (token)",
     "build_token_irab_decisions.py (particle/pronoun subset) -> token-irab 2-vote"),
  "particle_function": (4, "function-word / particle-pronoun", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "partial", "token-irab 2-vote"),
  "missing_qamus_entry_candidate": (5, "true missing-entry proposal", "owner",
     "(needs build_new_entry_proposals.py)", "(needs validator)", "yes (if approved)",
     "MISSING generator build_new_entry_proposals.py -> review-only owner-gated entry proposals; NO apply"),
  "nominal_derivative_candidate": (5, "true missing-entry proposal", "owner/2-vote",
     "(needs generator)", "(needs validator)", "small", "review-only; small, correctness-sensitive"),
  "missing_form_variant_on_existing_entry": (6, "existing-entry form authoring", "2-vote",
     "build_form_variant_candidates.py", "validate_form_variant_family_batches.py", "yes (largest lane)",
     "build_form_variant_candidates.py --max-b 200 --max-c 200 -> form-variant 2-vote -> apply (owner-gated live)"),
  "forms_array_missing_surface": (6, "existing-entry form authoring", "2-vote",
     "build_form_variant_candidates.py", "validate_form_variant_family_batches.py", "yes",
     "form-variant lane (forms_array subset, content N/V only)"),
  "quran_refs_missing_or_incomplete": (6, "source-entry repair (refs)", "source/owner",
     "(needs build_source_entry_repair_candidates.py)", "(needs validator)", "weak",
     "MISSING generator build_source_entry_repair_candidates.py --mode quran_refs; entry-completeness"),
  "content_homograph": (7, "token-level iʿrāb / homograph", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "yes (per-loc)",
     "build_token_irab_decisions.py -> token-irab 2-vote (per-loc only)"),
  "verb_form_or_voice": (7, "token-level iʿrāb / homograph", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "yes (per-loc)",
     "build_token_irab_decisions.py -> token-irab 2-vote (per-loc only)"),
  "proper_vs_common": (7, "token-level iʿrāb / homograph", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "small", "token-irab 2-vote, referent-guarded"),
  "proper_name_or_named_entity": (7, "token-level iʿrāb / homograph", "scholar/owner",
     "(needs proper-noun lane)", "(needs validator)", "small", "proper-noun token-address or owner-gated entry"),
  "token_addressable_proper_noun": (7, "token-level iʿrāb / homograph", "2-vote (token)",
     "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "yes", "token-address as proper noun"),
  "source_photo_visual_needed": (8, "source-photo / source-gated", "source",
     "source_photo_verify_entry.py", "(manual review)", "no (honesty, not bulk)",
     "source-photo head-on crop visual verification; source-gated human review"),
  "source_entry_required_before_resolution": (8, "source-photo / source-gated", "source", "(manual)", "(manual)", "no",
     "source verification required first"),
  "truly_low_frequency_tail": (7, "token-level iʿrāb / homograph", "2-vote (token)", "build_token_irab_decisions.py",
     "validate_token_irab_decisions.py", "small", "per-loc token decision; low frequency"),
  "genuinely_ambiguous_pending": (9, "scholar-gated / genuinely ambiguous", "scholar", "(none)", "(none)", "no",
     "stays pending by design — phrase-level / iʿrāb-undecidable / scholar review"),
}

def main():
    rows = [json.loads(l) for l in open(LED, encoding="utf-8") if l.strip() and '"loc"' in l]
    fam = collections.defaultdict(lambda: {"toks": 0, "surfaces": set(), "locs": []})
    for r in rows:
        rc = r["root_cause"]
        key = r.get("qac_root") or r.get("root_entry") or r.get("host_entry") or r.get("nk")
        fk = (rc, key)
        f = fam[fk]
        f["toks"] += 1
        if r.get("surface"): f["surfaces"].add(r["surface"])
        if len(f["locs"]) < 4: f["locs"].append(r["loc"])

    out_rows = []
    for (rc, key), f in fam.items():
        b = BUCKET.get(rc, (9, "unbucketed", "scholar", "?", "?", "no", "review"))
        out_rows.append({"bucket": b[0], "bucket_name": b[1], "root_cause": rc, "family_key": key,
                         "tokens": f["toks"], "surfaces": sorted(f["surfaces"])[:4], "sample_locs": f["locs"],
                         "gate": b[2], "generator": b[3], "validator": b[4],
                         "contributes_to_90": b[5], "next_command": b[6]})
    out_rows.sort(key=lambda r: (r["bucket"], -r["tokens"]))
    with open(os.path.join(OUT, "review-only-casebook.jsonl"), "w", encoding="utf-8", newline="\n") as fo:
        fo.write(json.dumps({"_generator": "tools/build_review_only_casebook.py", "_families": len(out_rows),
                             "_note": "review-only; NO apply payloads, NO glosses"}, ensure_ascii=False) + "\n")
        for r in out_rows:
            fo.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    # bucket rollup
    bk = collections.defaultdict(lambda: {"toks": 0, "fams": 0, "name": "", "gate": ""})
    for r in out_rows:
        d = bk[r["bucket"]]; d["toks"] += r["tokens"]; d["fams"] += 1; d["name"] = r["bucket_name"]; d["gate"] = r["gate"]
    md = ["# Review-only casebook (closure-2092 Phase 10)", "",
          "Buckets the de-polluted pending queue for the NEXT authoring tranche. **No apply payloads, no "
          "glosses authored here.** Generated by `tools/build_review_only_casebook.py` from the root-cause ledger.",
          "", "| bucket | lane | families | tokens | gate |", "|---:|---|---:|---:|---|"]
    for b in sorted(bk):
        d = bk[b]
        md.append(f"| {b} | {d['name']} | {d['fams']} | {d['toks']:,} | {d['gate']} |")
    md += ["", "## Top families per bucket (review-only)", ""]
    cur = None
    for r in out_rows:
        if r["bucket"] != cur:
            cur = r["bucket"]
            md += ["", f"### Bucket {r['bucket']} — {r['bucket_name']} (gate: {r['gate']})", "",
                   "| family | surfaces | tokens | root cause | generator | contributes 90% | next |",
                   "|---|---|---:|---|---|---|---|"]
        if r["tokens"] >= 3 or r["bucket"] in (5, 8, 9):
            md.append(f"| `{r['family_key']}` | {' '.join(r['surfaces'][:2])} | {r['tokens']} | "
                      f"`{r['root_cause']}` | {r['generator']} | {r['contributes_to_90']} | {r['next_command'][:60]} |")
    open(os.path.join(OUT, "review-only-casebook.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("CASEBOOK OK — %d families across %d buckets" % (len(out_rows), len(bk)))
    for b in sorted(bk):
        print("  bucket %d %s: %d families, %d tokens" % (b, bk[b]["name"], bk[b]["fams"], bk[b]["toks"]))

if __name__ == "__main__":
    main()
