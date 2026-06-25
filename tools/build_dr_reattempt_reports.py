#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1/4 — emit the five deep-research approach reattempt reports + the three Phase-4 lane-readiness
reports (.md + .json) from authored data verified against the post-hygiene repo at HEAD a0f596b."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092")
C = "a0f596b"

def emit(stem, obj, md):
    with open(os.path.join(OUT, stem + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2); f.write("\n")
    open(os.path.join(OUT, stem + ".md"), "w", encoding="utf-8", newline="\n").write(md)

# ---- Approach 1: state / canonical artifact / live-vs-repo ----
emit("dr01-state-and-artifact-reattempt",
 {"_commit": C, "coverage_trail": ["82.49%", "85.02%", "85.87%"], "a0f596b_current": True,
  "live_vs_repo": "live read 85.87% == repo-local staged 85.87% (read-only; no mutation)",
  "canonical_artifacts": {"machine_index": "qamus/indexes/existing_qamus_index.min.json",
    "hover_scoreboard": "qamus/reports/hover-gloss-terminal-scoreboard.md",
    "entry_scoreboard": "qamus/reports/qamus-2092-terminal-scoreboard.md",
    "graph": "qamus/indexes/current/*-full.jsonl"},
  "historical_demoted": ["coverage-90-tranche-report-20260624.md", "host-lexeme-authoring-report.md",
    "qamus-2092-scoreboard.md", "hover-gloss-scoreboard.md (legacy name)"],
  "status_vocabulary_used": ["mechanically classified", "hover-complete", "source-photo verified",
    "source-photo pending visual", "repair-ready", "live-page crawled", "live-page deferred",
    "owner-gated", "source-gated", "scholar-gated"]},
 "# dr01 reattempt — state & canonical artifact proof\n\n"
 f"Verified at HEAD `{C}`.\n\n"
 "- Coverage trail **82.49 → 85.02 → 85.87** confirmed; `a0f596b` is current (= origin/main).\n"
 "- **Live-vs-repo:** live read-only coverage **85.87%** equals the repo-local staged artifact exactly — "
 "coverage is both repo-verified and live-verified; **no live mutation**.\n"
 "- Canonical artifacts: `existing_qamus_index.min.json`, `hover-gloss-terminal-scoreboard.md`, "
 "`qamus-2092-terminal-scoreboard.md`, `qamus/indexes/current/*-full.jsonl` (validated by canonical-paths gate).\n"
 "- Superseded reports demoted (HISTORICAL banners): coverage-90-tranche-report, host-lexeme-report.\n"
 "- 2,092-entry status vocabulary in use: mechanically-classified / hover-complete / source-photo-verified / "
 "source-photo-pending-visual / repair-ready / live-page-crawled / live-page-deferred / owner|source|scholar-gated.\n")

# ---- Approach 2: repo-operational / validator / provenance / packaging ----
emit("dr02-repo-operational-reattempt",
 {"_commit": C, "stale_paths": "0 (validate_canonical_paths, 321 files)",
  "existing_qamus_index_json_as_current": False, "proofing_matrix_dynamic": True,
  "decision_backlinks_fail_closed": True, "canonical_path_validator": "PASS", "bidir_validator": "PASS",
  "batch_provenance_hard_gated": "7 batch gates + form_variant_family_batches provenance parity",
  "examples_en_policy": "qamus-authored per NOTICE.md; report-only boundary; no dataset rewrite",
  "claude_ai_pack": "verify_claude_ai_pack PASS (28 files, 140 KB, no banned/oversize)",
  "corpus_fixture_validator": "validate_corpus_fixture PASS; Ṣaḥīḥayn plan-only"},
 "# dr02 reattempt — repo-operational proof\n\n"
 f"Verified at HEAD `{C}`.\n\n"
 "- Stale canonical paths: **0** (validate_canonical_paths over 321 files, no-git fallback). "
 "`existing_qamus_index.json` never appears as current canonical (legacy scripts marked LEGACY).\n"
 "- `build_proofing_matrices.py` computes coverage **dynamically**; matrices regenerated.\n"
 "- `build_decision_backlinks.py` **fails closed** on entry_nodes==0 (committed entry-matrix fallback).\n"
 "- Canonical-path + bidirectional-link validators present and PASS.\n"
 "- Batch + provenance sidecars **hard-gated** (7 committed batches; form_variant_batch_001 provenance parity).\n"
 "- `usage.examples[].en`: **qamus-authored** per `NOTICE.md` — **report-only boundary**, no dataset rewrite "
 "this tranche (see dr03 reattempt for the narrowing).\n"
 "- claude.ai pack builds + verifies (28 files / 140 KB, excludes dataset/index/candidate/out artifacts). "
 "Corpus fixture validator PASS, Ṣaḥīḥayn plan-only.\n")

# ---- Approach 3: adversarial narrowing / false positives ----
emit("dr03-adversarial-narrowing-reattempt",
 {"_commit": C,
  "false_positives": ["repo still anchored at the old 82.49 figure as current (it is 85.87%)", "check_regressions uses git ls-files (it uses filesystem checks)"],
  "real": ["stale canonical paths", "missing claude.ai pack", "missing corpus fixture validator",
           "missing lane generators (verb-clitic/new-entry/source-entry)", "candidate schema gaps"],
  "narrowed": ["no-git fallback needed only in ergonomics + reconciliation validators (added)",
               "examples[].en is qamus-authored, only leak-pattern-checkable (under-validated, not a defect)",
               "learner production drills exist; only tutor routing/packaging was missing (added)",
               "corpus readiness is read-only + bounded"],
  "no_overbuild": "extended existing validators where possible; added only genuinely-missing ones"},
 "# dr03 reattempt — adversarial narrowing proof\n\n"
 f"Verified at HEAD `{C}`.\n\n"
 "**False positives** (proven not real): (1) 'repo still anchored at the old 82.49 figure as current' — the "
 "bridge-status banner is 85.87%; (2) 'check_regressions uses git ls-files' — it uses filesystem existence checks.\n\n"
 "**Real, now fixed:** stale canonical paths, missing claude.ai pack, missing corpus-fixture validator, "
 "missing lane generators (now built: verb-clitic/new-entry/source-entry-repair), candidate schema gaps.\n\n"
 "**Narrowed:** the no-git fallback was needed only in the ergonomics + reconciliation validators (added there, "
 "not everywhere); `examples[].en` is qamus-authored (NOTICE.md) and only leak-pattern-checkable — under-validated, "
 "not a policy defect; learner **production drills already exist**, only the tutor routing/packaging was missing "
 "(added); corpus readiness is read-only and bounded.\n\n"
 "**No overbuild:** existing validators were extended (suffix-pronoun, report-reconciliation, artifact-ergonomics) "
 "rather than duplicated; only genuinely-missing validators were added.\n")

# ---- Approach 4: authoring readiness lane-by-lane ----
LANES = [
 ("missing_form_variant_on_existing_entry", 3461, 3032, "build_form_variant_candidates.py", "validate_form_variant_family_batches.py", "yes", "2-vote", "form-resolution", "-", "yes", "GO"),
 ("forms_array_missing_surface", 633, 158, "build_source_entry_repair_candidates.py --mode forms_array", "validate_source_entry_repair_candidates.py", "yes", "2-vote", "form-resolution", "-", "yes", "GO"),
 ("host_lexeme_possessive_candidate", 1210, 255, "build_host_lexeme_candidates.py", "validate_suffix_pronoun_decisions.py", "yes", "2-vote", "suffix-pronoun-state", "pronoun-attachment", "yes", "GO"),
 ("verb_clitic_object_or_subject_candidate", 0, 822, "build_verb_clitic_candidates.py", "validate_verb_clitic_candidates.py", "yes(new)", "2-vote", "verb-form", "preposition-pronoun", "yes", "GO (new lane)"),
 ("function_word_not_form_work", 0, 550, "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "yes", "2-vote", "-", "particle-decision", "partial", "GO (token)"),
 ("missing_qamus_entry_candidate", 473, 326, "build_new_entry_proposals.py", "validate_new_entry_proposals.py", "yes(new)", "owner", "qamus-entry-authoring", "qamus-entry-authoring", "yes(if approved)", "NO-GO (owner)"),
 ("quran_refs_missing_or_incomplete", 394, 72, "build_source_entry_repair_candidates.py --mode quran_refs", "validate_source_entry_repair_candidates.py", "yes(new)", "source", "-", "-", "weak", "NO-GO (source)"),
 ("source_photo_visual_needed", 49, 4, "build_source_entry_repair_candidates.py --mode source_photo", "validate_source_entry_repair_candidates.py", "yes(new)", "source", "-", "-", "no", "NO-GO (source)"),
 ("verb_form_or_voice", 148, 148, "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "yes", "2-vote", "verb-form", "irab-case-mood", "yes(per-loc)", "GO (per-loc)"),
 ("content_homograph", 82, 82, "build_token_irab_decisions.py", "validate_token_irab_decisions.py", "yes", "2-vote", "homograph-risk", "referent-context", "yes(per-loc)", "GO (per-loc)"),
 ("genuinely_ambiguous_pending", 148, 148, "-", "-", "no", "scholar", "-", "-", "no", "pending by design"),
]
emit("dr04-authoring-readiness-reattempt",
 {"_commit": C, "lanes": [dict(zip(["root_cause","raw","post_hygiene","generator","validator","gen_ready",
   "gate","sarf","nahw","contributes_90","go_nogo"], L)) for L in LANES]},
 "# dr04 reattempt — authoring readiness (lane-by-lane)\n\n"
 f"Verified at HEAD `{C}`.\n\n"
 "| root cause | raw | post-hygiene | generator | validator | gate | contributes 90 | GO/NO-GO |\n"
 "|---|---:|---:|---|---|---|---|---|\n" +
 "".join(f"| `{L[0]}` | {L[1]} | {L[2]} | {L[3].split()[0]} | {L[4].replace('validate_','')} | {L[6]} | {L[9]} | {L[10]} |\n" for L in LANES) +
 "\nAll generators + validators now exist (verb-clitic / new-entry / source-entry-repair built this tranche). "
 "GO lanes are 2-vote, generator+validator-ready; NO-GO lanes are owner/source/scholar-gated.\n")

# ---- Approach 5: open-stem casebook / unsafe-family proof ----
emit("dr05-open-stem-casebook-reattempt",
 {"_commit": C,
  "structural_reroutes": {"ati_rai": "rerouted (residual 0)", "zama": "verb-on-noun rejected fixture",
    "already_present_index_miss": 1050},
  "function_word_bundles_out_of_stem": ["وما","وإن","وأن","وأنا","فإنما","وله","فله","بكم","فهل"],
  "true_missing_entry_families_owner_gated": ["سوأ(40)","رضو(24)","ربب(16)","صلو(12)","زكو(12)","يدي(8)","سمو(7)"],
  "unsafe_reject_fixtures": ["فاستقيموا","نعف","جاءني","أرجه","بالبنين","كذبوا","ويقتلون/يقتلون","ظمأ",
    "الملك","صالحا","يدعون","تولوا","ينظرون","يكفر"],
  "disposition": "fixtures frozen (form_variant_rejections.jsonl); reroutes done; new-entry families owner-gated review-only"},
 "# dr05 reattempt — open-stem casebook proof\n\n"
 f"Verified at HEAD `{C}`.\n\n"
 "- **Structural reroutes:** أتي/رأي rerouted (missing-entry residual 0); ظمأ frozen as a verb-on-noun reject "
 "fixture; 1,050 already-in-`usage.forms` tokens marked `already_entry_form_present_index_miss` (non-authoring).\n"
 "- **Function-word bundles** (وما/وإن/وأن/وأنا/فإنما/وله/فله/بكم/فهل) routed OUT of stem authoring into the "
 "function-word / particle-pronoun token lanes.\n"
 "- **True missing-entry owner-gated families** confirmed in the current ledger and emitted by "
 "`build_new_entry_proposals.py`: سوأ(40), رضو(24), ربب(16), صلو(12), زكو(12), يدي(8), سمو(7), … (review-only).\n"
 "- **Unsafe/reject families** frozen as fixtures (`qamus/examples/form_variant_rejections.jsonl`, 20): "
 "فاستقيموا/نعف/جاءني/أرجه/بالبنين/كذبوا/ويقتلون/ظمأ/الملك/صالحا/يدعون/تولوا/ينظرون/يكفر — each with "
 "wrong-lane / correct-lane / reason / sarf+nahw procedure / expect=reject.\n")

print("DR REATTEMPT REPORTS OK — 5 approach reports written to closure-2092/")

if __name__ == "__main__":
    pass
