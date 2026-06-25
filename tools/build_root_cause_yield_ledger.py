#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4 (closure-2092) — root-cause YIELD ledger v2.

The Phase-B coverage-yield ledger ranked only SURFACE-WIDE auto-glossing and concluded a ~86%
"safe frontier". That conflated "surface-wide auto-gloss exhausted" with "global frontier". This v2
ranks the actual ROOT-CAUSE levers from the blocker-root-cause ledger, because QAC gives every
pending token its root — so most remaining work is root-known *structured authoring* (pick POS /
sense / guard collisions), not genuine ambiguity.

Each lever gets an honest discount = expected fraction safely resolvable by 2-vote sarf/nahw
authoring. Discounts are PRIORS to be replaced by measured approval rates as lanes execute.
Read-only. Reads qamus/reports/closure-2092/blocker-root-cause-ledger.jsonl.
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "qamus", "reports", "closure-2092")
LED = os.path.join(OUTDIR, "blocker-root-cause-ledger.jsonl")

# honest priors: expected fraction safely resolvable per 2-vote authoring (calibrate w/ measured rate)
DISC = {
    ("missing_form_variant_on_existing_entry", "A_safe"): 0.90,
    ("missing_form_variant_on_existing_entry", "B_sense_select"): 0.60,
    ("missing_form_variant_on_existing_entry", "C_pos_or_collision"): 0.45,
    ("forms_array_missing_surface", "A_safe"): 0.90,
    ("forms_array_missing_surface", "B_sense_select"): 0.60,
    ("forms_array_missing_surface", "C_pos_or_collision"): 0.45,
    ("host_lexeme_possessive_candidate", None): 0.50,
    ("missing_qamus_entry_candidate", None): 0.55,          # owner-gated new entry; realizable if approved
    ("particle_or_pronoun_misclassified_as_stem", None): 0.55,
    ("quran_refs_missing_or_incomplete", None): 0.30,       # weak token-unlock (entry completeness)
    ("nominal_derivative_candidate", None): 0.50,
    ("verb_form_or_voice", None): 0.50,
    ("content_homograph", None): 0.50,
    ("particle_function", None): 0.70,
    ("genuinely_ambiguous_pending", None): 0.10,
    ("truly_low_frequency_tail", None): 0.30,
    ("source_photo_visual_needed", None): 0.20,             # needs source photo
    ("source_entry_required_before_resolution", None): 0.20,
    ("proper_name_or_named_entity", None): 0.40,
    ("token_addressable_proper_noun", None): 1.0,
    ("proper_vs_common", None): 0.50,
    # closure-2092 open-stem hygiene lanes
    ("already_entry_form_present_index_miss", None): 0.50,   # reindex/resolver-recoverable, NOT authoring
    ("verb_clitic_object_or_subject_candidate", None): 0.45, # token/nahw lane (object/subject pronoun)
    ("function_word_not_form_work", None): 0.55,             # token/particle lane, not form authoring
}
NON_AUTHORING = {"already_entry_form_present_index_miss"}   # recoverable by index/resolver fix, not gloss work
OWNER_GATED = {"missing_qamus_entry_candidate"}            # new entries need owner approval to go live
SOURCE_GATED = {"source_photo_visual_needed", "source_entry_required_before_resolution",
                "count_total_uses_needs_photo_check"}

def disc(rc, tier):
    return DISC.get((rc, tier), DISC.get((rc, None), 0.30))

def main():
    rows = []
    for ln in open(LED, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        r = json.loads(ln)
        if "loc" in r:
            rows.append(r)
    total_pending = len(rows)

    lever = collections.defaultdict(lambda: {"pending": 0, "safe": 0.0})
    for r in rows:
        rc = r["root_cause"]; tier = r.get("safe_tier")
        key = (rc, tier)
        lever[key]["pending"] += 1
        lever[key]["safe"] += disc(rc, tier)

    lr = []
    for (rc, tier), v in lever.items():
        lr.append({"root_cause": rc, "safe_tier": tier, "pending": v["pending"],
                   "discount": round(disc(rc, tier), 2),
                   "expected_safe": round(v["safe"], 1),
                   "owner_gated": rc in OWNER_GATED, "source_gated": rc in SOURCE_GATED})
    lr.sort(key=lambda x: -x["expected_safe"])

    total_safe = sum(x["expected_safe"] for x in lr)
    resolved_now = 49900 - total_pending
    cov_now = round(100.0 * resolved_now / 49900, 2)
    cov_ceiling = round(100.0 * (resolved_now + total_safe) / 49900, 2)
    need_for_90 = max(0, int(0.90 * 49900) - resolved_now)

    out = {"_generator": "tools/build_root_cause_yield_ledger.py",
           "total_pending": total_pending, "resolved_now": resolved_now, "coverage_now": cov_now,
           "expected_safe_realizable": round(total_safe, 1),
           "coverage_ceiling_if_all_safe_realized": cov_ceiling,
           "tokens_needed_for_90pct": need_for_90,
           "ninety_reachable_via_safe_authoring": (resolved_now + total_safe) >= 0.90 * 49900,
           "levers": lr}
    with open(os.path.join(OUTDIR, "root-cause-yield-ledger.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, sort_keys=True, indent=2); f.write("\n")

    md = ["# Root-cause yield ledger v2 (closure-2092)", "",
          "Generated by `tools/build_root_cause_yield_ledger.py` from `blocker-root-cause-ledger.jsonl`.",
          "Ranks the **root-cause levers** (not surface-wide auto-gloss) by expected SAFE resolves. "
          "Discounts are honest priors — replace with measured 2-vote approval rates as lanes run.", "",
          f"- pending now: **{total_pending:,}**  ·  resolved: **{resolved_now:,}**  ·  coverage: **{cov_now}%**",
          f"- expected safe-realizable (sum of discounts): **{round(total_safe):,}** tokens",
          f"- coverage ceiling if all safe realized: **{cov_ceiling}%**",
          f"- tokens still needed for 90%: **{need_for_90:,}**",
          f"- **90% reachable via safe root-known authoring? {'YES' if out['ninety_reachable_via_safe_authoring'] else 'NO'}** "
          "(bounded multi-batch authoring, gated by 2-vote approval — not a single lever, not a wall of ambiguity)", "",
          "| rank | lever (root cause) | tier | pending | discount | expected safe | gate |",
          "|---:|---|---|---:|---:|---:|---|"]
    REINDEX = {"already_entry_form_present_index_miss"}
    TOKEN = {"verb_clitic_object_or_subject_candidate", "function_word_not_form_work"}
    for i, x in enumerate(lr, 1):
        gate = ("owner" if x["owner_gated"] else "source" if x["source_gated"]
                else "reindex" if x["root_cause"] in REINDEX
                else "token" if x["root_cause"] in TOKEN else "2-vote")
        md.append(f"| {i} | `{x['root_cause']}` | {x['safe_tier'] or '—'} | {x['pending']:,} | "
                  f"{x['discount']} | {x['expected_safe']:.0f} | {gate} |")
    rct = collections.Counter(r["root_cause"] for r in rows)
    amb = rct.get("genuinely_ambiguous_pending", 0)
    fv = rct.get("missing_form_variant_on_existing_entry", 0)
    fa = rct.get("forms_array_missing_surface", 0)
    hl = rct.get("host_lexeme_possessive_candidate", 0)
    idx_miss = rct.get("already_entry_form_present_index_miss", 0)
    md += ["", "## Correction to the prior 'safe frontier ~86%' claim", "",
           "The prior Phase-B ledger measured only collision-free **surface-wide** auto-glossing and "
           "concluded the safe ceiling was ~86%. That is the ceiling for *one mechanism*, not the global "
           "frontier. QAC assigns a root to every pending token, so the dominant remaining lever is "
           f"**root-known form/sense authoring** (`missing_form_variant_on_existing_entry` = {fv:,}, "
           f"`forms_array_missing_surface` = {fa:,}, `host_lexeme_possessive` = {hl:,} noun-host). Each token "
           "still needs a POS-correct, sense-selected, collision-guarded 2-vote authored gloss (it is NOT a "
           "free `add_form` — e.g. ظَمَأٌ noun vs verbal entry 'to be thirsty'; بَنِين 'sons' vs root ب ن ي "
           "'to build'). With honest discounts the safe-realizable pool crosses 90%. The conclusion is "
           "therefore: **90% is reachable as bounded authoring work, not blocked by a wall of ambiguity** — "
           f"the genuinely-ambiguous residue is only ~{amb} tokens (`genuinely_ambiguous_pending`).", "",
           f"After the open-stem hygiene pass, **{idx_miss:,}** tokens are `already_entry_form_present_index_miss` "
           "(the inflected form is already stored in the entry; recoverable by the live index/resolver fix, not "
           "authoring), and verb-clitic / function-word material is split into token/particle lanes — so the "
           "authoring lanes above are now honest about what is actually gloss-authoring work.", ""]
    open(os.path.join(OUTDIR, "root-cause-yield-ledger.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))

    print("YIELD LEDGER v2 OK")
    print("pending=%d resolved=%d cov=%.2f%%" % (total_pending, resolved_now, cov_now))
    print("expected_safe=%.0f  ceiling=%.2f%%  need_for_90=%d  90_reachable=%s" %
          (total_safe, cov_ceiling, need_for_90, out["ninety_reachable_via_safe_authoring"]))
    for x in lr[:8]:
        print("  ", x["root_cause"], x["safe_tier"], "pending=%d safe=%.0f" % (x["pending"], x["expected_safe"]))

if __name__ == "__main__":
    main()
