#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 — deep-research reattempt traceability matrix. One row per distinct finding across
dr01-dr05, with closure status verified against the current repo. Emits JSONL + MD under closure-2092/.
Reproducible: the authored finding list is data; statuses reflect the post-hygiene repo at HEAD a0f596b.
"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092")
C = "a0f596b"

# (dr_files, approach, fid, text, affected, severity, status, method, evidence, validator,
#  remaining, b_auth, b_90, b_skill, b_pack, b_corpus)
F = [
 (["dr01","dr03"],1,"DR-001","82.49→85.02→85.87 coverage trail verifiable","fusha-production-bridge-status.md","info","confirmed_fixed","report-only","post-hygiene-baseline-20260624.md","validate_report_reconciliation","none",0,0,0,0,0),
 (["dr01"],1,"DR-002","later tranche is a scope-correction, not a contradiction","root-cause-yield-ledger.md","info","confirmed_fixed","report-only","root-cause-yield-ledger.md","-","none",0,0,0,0,0),
 (["dr01","dr03"],1,"DR-003","coverage-90 report reads as current 'frontier ~86%'","coverage-90-tranche-report-20260624.md","high","confirmed_fixed","code inspection","coverage-90-tranche-report-20260624.md (HISTORICAL banner)","validate_canonical_paths","none",0,0,0,0,0),
 (["dr01","dr02","dr03"],1,"DR-004","stale existing_qamus_index.json / old scoreboard names in docs+curriculum","qamus/README.md;curriculum/*;corpora/*","high","confirmed_fixed","validator","validate_canonical_paths (321 files,0 stale)","validate_canonical_paths","none",0,0,0,0,0),
 (["dr01","dr02","dr04"],1,"DR-005","validators use git ls-files -> vacuous pass in no-git","check_artifact_ergonomics.py;validate_report_reconciliation.py","medium","confirmed_fixed","code inspection","filesystem fallback added","check_regressions","none",0,0,0,0,0),
 (["dr01","dr02","dr03"],1,"DR-006","'2,092 audited' overstated (only mechanically classified)","qamus-2092-audit-completion.md;final-closure-report","medium","confirmed_fixed","code inspection","status-vocabulary banners","validate_report_reconciliation","none",0,0,0,0,0),
 (["dr01","dr02","dr03"],1,"DR-007","claude.ai Project Knowledge pack missing","dist/claude-ai/","medium","confirmed_fixed","validator","verify_claude_ai_pack PASS (28 files,140KB)","verify_claude_ai_pack","none",0,0,0,1,0),
 (["dr01","dr02","dr03"],1,"DR-008","no canonical-path validator","tools/validate_canonical_paths.py","medium","confirmed_fixed","validator","validate_canonical_paths OK","validate_canonical_paths","none",0,0,0,0,0),
 (["dr01","dr02","dr03"],1,"DR-009","no bidirectional-link validator","tools/validate_bidirectional_links.py","medium","confirmed_fixed","validator","SOURCE GRAPH OK (0 orphans)","validate_bidirectional_links","none",0,0,0,0,0),
 (["dr01","dr03"],1,"DR-010","report ergonomics warnings on generated reports","qamus/reports/*","low","narrowed","report-only","check_report_ergonomics (soft warnings only)","check_report_ergonomics","optional: add generator notes",0,0,0,0,0),
 (["dr01","dr02","dr03","dr04","dr05"],1,"DR-011","live-deployment claims unverifiable from repo","final-closure-report","info","narrowed","live read-only","this tranche: live coverage read 85.87% == repo-local","-","label log-claimed where apply not run",0,0,0,0,0),
 (["dr05","dr02","dr04"],2,"DR-012","by-normalized-surface.json built from headwords only (usage.forms miscounted)","export_current_qamus_dataset.py;by-normalized-surface.json","high","confirmed_fixed","validator","validate_surface_index_covers_usage_forms OK (7125 keys,+5075)","validate_surface_index_covers_usage_forms","none",0,0,0,0,0),
 (["dr02","dr03"],2,"DR-013","build_proofing_matrices hardcoded 82.49% / 41,164","build_proofing_matrices.py","medium","confirmed_fixed","code inspection","dynamic _dedup_totals(); regenerated","validate_canonical_paths","none",0,0,0,0,0),
 (["dr02","dr03"],2,"DR-014","blocker-root-cause-ledger preamble says 85.02% while rows are 85.87-era","build_blocker_root_cause_ledger.py","medium","confirmed_fixed","code inspection","computes coverage dynamically","-","none",0,0,0,0,0),
 (["dr03"],2,"DR-015","root-cause-yield-ledger hardcodes 3,859/657 (rows sum 3,461/633)","build_root_cause_yield_ledger.py","medium","confirmed_fixed","code inspection","correction paragraph computed from rows","-","none",0,0,0,0,0),
 (["dr03"],2,"DR-016","final-closure-report <commit C> placeholder","final-closure-report-20260624.md","medium","confirmed_fixed","code inspection","-> 74607a9","validate_canonical_paths","none",0,0,0,0,0),
 (["dr02","dr04"],2,"DR-017","build_decision_backlinks reads missing legacy index -> entry_nodes:0 silent","build_decision_backlinks.py","medium","confirmed_fixed","code inspection","fail-closed + committed entry-matrix fallback","-","none",0,0,0,0,0),
 (["dr02","dr03"],2,"DR-018","public export usage.examples[].en vs source-boundary policy","provenance/source-boundaries.md;NOTICE.md","medium","narrowed","report-only","NOTICE.md states English renderings are qamus-authored","-","report-only boundary; no dataset rewrite (dr02-reattempt §examples-en)",0,0,0,1,0),
 (["dr02","dr03","dr04"],2,"DR-019","candidate batch validators not run as hard gates + no provenance parity","check_regressions.py;validate_form_variant_family_batches.py","high","confirmed_fixed","validator","7 batch gates + provenance parity green","check_regressions","none",0,0,0,0,0),
 (["dr04"],2,"DR-020","validate_suffix_pronoun_decisions too strict for leading prefixes","validate_suffix_pronoun_decisions.py","medium","confirmed_fixed","validator","host_lexeme_batch_001 PASS","check_regressions","none",0,0,0,0,0),
 (["dr02","dr03"],2,"DR-021","no corpus-to-Qamus read-only fixture validator","tools/validate_corpus_fixture.py","medium","confirmed_fixed","validator","CORPUS FIXTURE OK; Ṣaḥīḥayn plan-only","check_regressions","none",0,0,0,0,1),
 (["dr02","dr03"],2,"DR-022","tutor/learner-runtime routing missing (production drills mostly exist)","curriculum/tutor-runtime-routing.md","low","narrowed","report-only","routing appendix added","-","Phase 10 self-tests this tranche",0,0,0,0,0),
 (["dr01","dr02","dr03"],3,"DR-023","'repo still anchored at 82.49% current' — FALSE POSITIVE","-","info","false_positive","code inspection","bridge-status banner already 85.87%","validate_report_reconciliation","none",0,0,0,0,0),
 (["dr03"],3,"DR-024","check_regressions uses git ls-files — FALSE POSITIVE","check_regressions.py","info","false_positive","code inspection","check_regressions uses filesystem existence checks, no git ls-files","-","none",0,0,0,0,0),
 (["dr03"],3,"DR-025","historical-report hygiene broadly missing — NARROWED","qamus/reports/*","info","narrowed","code inspection","HISTORICAL markers present on superseded reports","validate_canonical_paths","none",0,0,0,0,0),
 (["dr03"],3,"DR-026","examples[].en is a policy DEFECT — NARROWED to under-validated","NOTICE.md","low","narrowed","report-only","authored per NOTICE; only leak-pattern-checkable","audit_hover_gloss_quality","optional examples-en leak validator (dr03-reattempt)",0,0,0,0,0),
 (["dr04","dr05"],4,"DR-027","host_lexeme_possessive 780 verb-clitic pollution","build_blocker_root_cause_ledger.py","high","confirmed_fixed","validator","qac_pos==V in host_lexeme = 0; verb_clitic lane 822","validate_open_stem_lane_sanity","none",0,0,0,0,0),
 (["dr04","dr05"],4,"DR-028","forms_array_missing_surface 494 function-word pollution","build_blocker_root_cause_ledger.py","high","confirmed_fixed","validator","function_word_not_form_work 550; forms_array 158 N/V","validate_open_stem_lane_sanity","none",0,0,0,0,0),
 (["dr04","dr05"],4,"DR-029","أتي/رأي 89 misrouted to missing-entry (unflattened root)","build_blocker_root_cause_ledger.py","high","confirmed_fixed","validator","missing_entry أتي/رأي residual = 0","validate_open_stem_lane_sanity","none",0,0,0,0,0),
 (["dr05","dr04"],4,"DR-030","~433-1100 pending tokens already in usage.forms (index miss)","audit_all_hover_tokens.py","high","confirmed_fixed","validator","already_entry_form_present_index_miss 1,050 (non-authoring)","validate_surface_index_covers_usage_forms","bucket 1 needs LIVE resolver rebuild (owner-gated)",0,1,0,0,0),
 (["dr04","dr05"],4,"DR-031","missing regression fixtures for scar families","qamus/examples/form_variant_rejections.jsonl","medium","confirmed_fixed","validator","20 fixtures wired","check_regressions","none",0,0,1,0,0),
 (["dr02","dr03","dr04"],4,"DR-032","verb-clitic object/subject lane has NO generator","tools/build_verb_clitic_candidates.py","high","confirmed_fixed","validator","built this tranche (Phase 4A) + validator + schema","check_regressions","none (was blocking bucket 3)",0,1,0,0,0),
 (["dr02","dr03","dr04","dr05"],4,"DR-033","missing-entry proposal lane has NO generator","tools/build_new_entry_proposals.py","high","confirmed_fixed","validator","built this tranche (Phase 4B) + validator + schema; owner-gated review-only","check_regressions","none",1,1,0,0,0),
 (["dr02","dr03","dr04"],4,"DR-034","source-entry repair lane (forms/refs/photo) has NO generator","tools/build_source_entry_repair_candidates.py","high","confirmed_fixed","validator","built this tranche (Phase 4C) + validator + schema","check_regressions","none",0,1,0,0,0),
 (["dr04"],4,"DR-035","yield/safe-realizable provisional until hygiene validators pass","root-cause-yield-ledger.json","medium","confirmed_fixed","validator","lane-sanity green; yield ~3,516 -> 92.92% ceiling","validate_open_stem_lane_sanity","none",0,0,0,0,0),
 (["dr05"],5,"DR-036","structural reroute families (أتي/رأي/ظمأ/already-present)","review-only-casebook.jsonl","high","confirmed_fixed","regenerated artifact","casebook bucket 1 (1,050) + buckets reroute","build_review_only_casebook","reindex (owner-gated)",0,1,0,0,0),
 (["dr05"],5,"DR-037","function-word bundles routed out of stem (وما/وإن/وأن/وأنا/فإنما/وله)","build_blocker_root_cause_ledger.py","high","confirmed_fixed","validator","function_word_not_form_work + particle lanes","validate_open_stem_lane_sanity","none",0,0,0,0,0),
 (["dr05"],5,"DR-038","true missing-entry families (سوء/رضو/جيأ/زكو/صلو/أخو/ربب) need verification","build_new_entry_proposals.py","medium","confirmed_unfixed","validator","Phase 4B generator emits owner-gated proposals; families re-verified vs current ledger","validate_new_entry_proposals","owner approval before any entry creation",1,1,0,0,0),
 (["dr05","dr04"],5,"DR-039","unsafe/reject families frozen as fixtures (كذبوا/يقتلون/الملك/صالحا/يدعون/تولوا/ينظرون/يكفر/...)","form_variant_rejections.jsonl","medium","confirmed_fixed","validator","20 frozen fixtures incl all named families","check_regressions","none",0,0,0,0,0),
 (["dr05","dr04"],5,"DR-040","regression envelope not strong enough to certify authoring","check_regressions.py","medium","confirmed_fixed","validator","lane-sanity + batch gates + fixtures + canonical-paths all wired","check_regressions","none",0,0,0,0,0),
]

def main():
    rows = []
    for (drf, ap, fid, text, aff, sev, st, meth, ev, val, rem, ba, b9, bs, bp, bc) in F:
        rows.append({"dr_file": "+".join(drf), "approach": ap, "finding_id": fid, "finding_text": text,
                     "affected_files": aff, "severity": sev, "current_status": st, "verification_method": meth,
                     "evidence_file": ev, "validator_or_report": val, "current_commit": C, "remaining_action": rem,
                     "blocks_authoring": bool(ba), "blocks_90": bool(b9), "blocks_skill_completion": bool(bs),
                     "blocks_claude_ai_pack": bool(bp), "blocks_corpus_to_qamus": bool(bc)})
    with open(os.path.join(OUT, "deep-research-reattempt-matrix.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"_generator": "tools/build_deep_research_reattempt_matrix.py", "_commit": C,
                            "_rows": len(rows)}, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    sc = collections.Counter(r["current_status"] for r in rows)
    sev = collections.Counter(r["severity"] for r in rows)
    blk = {k: sum(1 for r in rows if r[k]) for k in
           ("blocks_authoring", "blocks_90", "blocks_skill_completion", "blocks_claude_ai_pack", "blocks_corpus_to_qamus")}
    md = ["# Deep-research reattempt matrix (closure-2092)", "",
          f"One row per distinct finding across dr01–dr05, status verified at HEAD `{C}`. "
          f"Companion: `.jsonl` ({len(rows)} rows). Generated by `tools/build_deep_research_reattempt_matrix.py`.", "",
          "## Rollup", "", f"- status: {dict(sc)}", f"- severity: {dict(sev)}", f"- blocks: {blk}", "",
          "## Findings", "", "| id | dr | sev | status | finding | validator/report | remaining |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['finding_id']} | {r['dr_file']} | {r['severity']} | **{r['current_status']}** | "
                  f"{r['finding_text'][:64]} | {r['validator_or_report']} | {r['remaining_action'][:40]} |")
    high_unfixed = [r for r in rows if r["severity"] == "high" and r["current_status"] in ("confirmed_unfixed", "reopened") and r["blocks_authoring"]]
    md += ["", "## High-severity findings still blocking authoring", "",
           ("None — all high-severity findings are confirmed_fixed / false_positive / narrowed, or are owner-gated "
            "review-only lanes that do not block the GO authoring lanes." if not high_unfixed
            else "\n".join("- " + r["finding_id"] + " " + r["finding_text"] for r in high_unfixed)), ""]
    open(os.path.join(OUT, "deep-research-reattempt-matrix.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("MATRIX OK — %d findings; status %s" % (len(rows), dict(sc)))
    print("blocks:", blk)

if __name__ == "__main__":
    main()
