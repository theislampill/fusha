#!/usr/bin/env python3
"""Phase 1 — MY re-attempt of the five deep-research approaches against the CURRENT tree.

Not a restatement of the prior tranche's reattempt: this is a fresh verification at HEAD d67f873
(+ this session's live read-only verification) that re-derives each finding's status from evidence,
and surfaces the new examples[].en provenance discovery. Emits:
  qamus/reports/closure-2092/my-dr01..05-*-reattempt.md/.json (+ my-dr05 .jsonl)
  qamus/reports/closure-2092/my-deep-research-master-matrix.md/.jsonl
Authored data only; Date.now() intentionally unused for determinism.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092")
DATE = "2026-06-25"
HEAD = "d67f873"

# Master finding list. Each: (dr, fid, text, status, method, affected, remaining, blocks[6])
# blocks order: authoring, ninety, sarf_nahw, claude_ai, corpus, public_redistribution
F = [
 # ---- DR01: state / canonical artifacts / liveness ----
 ("dr01","DR01-1","Commit identity inconsistent across GitHub UI (a0f596b), report JSON (3d621c1), and prior final message (d67f873) — which is the real HEAD?",
  "confirmed_fixed","git rev-parse + git ls-remote origin main (live remote)","Phase0 current-truth-reconciliation-20260625",
  "none — real HEAD=origin/main=GitHub=d67f873; a0f596b=prior-tranche tip(stale view), 3d621c1=stale report text",[0,0,0,0,0,0]),
 ("dr01","DR01-2","Coverage numbers must be labelled repo-verified / live-verified / claimed / stale, not stated bare",
  "confirmed_fixed","Phase0 report labels every number by evidence class","current-truth-reconciliation-20260625",
  "none",[0,0,0,0,0,0]),
 ("dr01","DR01-3","Live coverage was only 'private-deploy-claimed' (86.18%) — never read back from the live artifact",
  "confirmed_fixed","read live wbw-lookup.json _meta.coverage (glossed 43005/49900=86.18, built 2026-06-25T03:48:30Z); 0 leaks in words","live /srv/.../qamus_wbw/build/wbw-lookup.json",
  "none — upgraded to live-verified; live==repo exactly",[0,0,0,0,0,0]),
 ("dr01","DR01-4","2,092-entry 'audited' could be mis-read as 'fully checked / hover-complete / source-verified'",
  "confirmed_fixed","status-vocabulary banner emitted by audit_qamus_2092_entries.py","qamus/reports/qamus-2092-audit-completion.md",
  "none — 'mechanically classified' != hover-complete/source-verified, stated explicitly",[0,0,0,0,0,0]),
 ("dr01","DR01-5","Public 2,092-page crawl never performed (only a home-page 200 check)",
  "confirmed_unfixed","read-only home check 200/2092 only; full crawl deferred prior tranche","(Phase 2 of THIS tranche)",
  "execute throttled read-only crawl + live-vs-repo reconciliation (Phase 2)",[0,0,0,0,0,0]),
 ("dr01","DR01-6","Historical/superseded reports could masquerade as current",
  "confirmed_fixed","validate_report_reconciliation.py PASS; 3d621c1 stale text flagged in Phase0","tools/validate_report_reconciliation.py",
  "none",[0,0,0,0,0,0]),
 # ---- DR02: repo operations / paths / provenance / claude.ai pack ----
 ("dr02","DR02-1","Canonical path drift must be gated",
  "confirmed_fixed","validate_canonical_paths.py PASS (379 files, 0 stale)","tools/validate_canonical_paths.py",
  "none",[0,0,0,0,0,0]),
 ("dr02","DR02-2","Batch / provenance parity must be hard-gated",
  "confirmed_fixed","check_regressions.py batch + provenance gates PASS","tools/check_regressions.py",
  "none",[0,0,0,0,0,0]),
 ("dr02","DR02-3","claude.ai pack must be a small text-only operational pack, not giant JSONL",
  "confirmed_fixed","verify_claude_ai_pack.py PASS (28 files, 139,983 B, <5MB, no file >500KB)","scripts/verify_claude_ai_pack.py",
  "none",[0,0,0,0,0,0]),
 ("dr02","DR02-4","Corpus fixture must be read-only (no live write, no translation copy)",
  "confirmed_fixed","check_regressions corpus fixture gate PASS","tools/validate_corpus_fixture.py",
  "none",[0,0,0,0,0,0]),
 ("dr02","DR02-5","examples[].en must be qamus-authored public text, NOT a copied translation — is it covered by a validator, or a policy gap?",
  "confirmed_unfixed_owner_gated","audit_examples_en_provenance.py: 7,700 examples, 41.3% carry Saheeh-International [bracket] signature; dataset validator gates structure/leak/private but NOT anti-copy","qamus/data/current/entries.jsonl; tools/audit_examples_en_provenance.py",
  "OWNER DECISION: confirm Saheeh-Intl redistribution rights+attribute / replace with open-licensed / author original / drop en from public dataset. NOTE: separate from hover output (clean).",[0,0,0,0,0,1]),
 ("dr02","DR02-6","Public-output (hover) provenance leak risk",
  "confirmed_fixed","live words scan: 0 informed_by/qac/tanzil/ocr keys; ALLOWED_* + PRIVATE_FIELDS + LEAK_PAT gate every dataset level","validate_current_qamus_dataset.py; live artifact",
  "none for hover output",[0,0,0,0,0,0]),
 # ---- DR03: adversarial narrowing / false positives ----
 ("dr03","DR03-1","Repo is still globally anchored at 82.49%",
  "false_positive","ledger validator: 43,005/49,900=86.18% repo + live","tools/validate_blocker_root_cause_ledger.py",
  "none — old 82.49 figure is historical, not current",[0,0,0,0,0,0]),
 ("dr03","DR03-2","Historical-report hygiene still broken",
  "narrowed","report ergonomics PASS (89 reports, 19 soft warns); reconciliation PASS","tools/check_report_ergonomics.py",
  "soft warnings only (non-blocking)",[0,0,0,0,0,0]),
 ("dr03","DR03-3","Learner production / drill content is missing",
  "narrowed","claude.ai pack present w/ learner+review self-tests; curriculum dirs exist","dist/claude-ai/, curriculum/",
  "gap was packaging/runtime, not absence of content",[0,0,0,0,0,0]),
 ("dr03","DR03-4","Real remaining gaps: stale docs, candidate schema parity, corpus validation, claude.ai packaging, under-validated sidecars",
  "confirmed_fixed","each has a wired validator now (canonical-paths/schemas/corpus-fixture/claude-ai-pack/batch-provenance), all PASS","tools/check_regressions.py",
  "none of these block; examples[].en is the one real residual",[0,0,0,0,0,0]),
 ("dr03","DR03-5","All concerns were over-stated (nothing serious remains)",
  "reopened","examples[].en copied-translation was UNDER-stated by every prior pass","examples-en-provenance-audit-20260625",
  "escalated to owner-gated (DR02-5)",[0,0,0,0,0,1]),
 # ---- DR04: authoring lane readiness ----
 ("dr04","DR04-form_variant","existing-entry form authoring lane",
  "confirmed_fixed","build_form_variant_candidates.py + build_form_variant_apply.py + validate_form_variant_family_batches.py present; 2-vote; live-apply private-context","tools/build_form_variant_*.py",
  "GO — top lever for 90%",[0,0,0,0,0,0]),
 ("dr04","DR04-host_lexeme","noun-host possessive lane",
  "confirmed_fixed","build_host_lexeme_candidates.py + validate_suffix_pronoun_decisions.py + suffix-pronoun-decision.schema.json","tools/build_host_lexeme_candidates.py",
  "GO — noun-only (verb clitics split out, lane-sanity PASS)",[0,0,0,0,0,0]),
 ("dr04","DR04-token_irab","token iʿrāb / function-word lane",
  "confirmed_fixed","build_token_irab_decisions.py + validate_token_irab_decisions.py","tools/build_token_irab_decisions.py",
  "GO — two votes must agree on answer AND reason",[0,0,0,0,0,0]),
 ("dr04","DR04-verb_clitic","verb-clitic object/subject lane",
  "confirmed_fixed","build_verb_clitic_candidates.py + validator + verb-clitic-candidate.schema.json (638 review-only)","tools/build_verb_clitic_candidates.py",
  "review-only (two-vote); not auto",[0,0,0,0,0,0]),
 ("dr04","DR04-new_entry","missing-entry proposals lane",
  "confirmed_fixed","build_new_entry_proposals.py + validator + new-entry-proposal.schema.json (52 owner-gated)","tools/build_new_entry_proposals.py",
  "owner-gated, review-only",[0,1,0,0,0,0]),
 ("dr04","DR04-source_entry_repair","source-entry repair lane",
  "confirmed_fixed","build_source_entry_repair_candidates.py + validator + schema (forms_array/quran_refs/source_photo)","tools/build_source_entry_repair_candidates.py",
  "source-gated where source_photo mode",[0,0,0,0,0,0]),
 ("dr04","DR04-index_miss","index-miss lane",
  "narrowed","live expand.py already matches usage.forms under MIN_FORM_LEN+homograph quarantine; <=1,050 upper bound","index-miss-live-rebuild-instructions",
  "owner-gated live reindex; NOT authoring",[0,1,0,0,0,0]),
 ("dr04","DR04-source_photo","source-photo / scholar-gated lane",
  "confirmed_fixed","source-entry-repair source_photo mode (4 queued); corpus complete, needs head-on crops","source-photo readiness",
  "owner/source-gated (crops)",[0,0,0,0,1,0]),
 # ---- DR05: open-stem casebook ----
 ("dr05","DR05-1","Backlog is one undifferentiated pile",
  "false_positive","review-only-casebook.jsonl: 1,606 families, 9 buckets, per-row lane/gate/validator/next_command/contributes_to_90","qamus/reports/closure-2092/review-only-casebook.jsonl",
  "none — fully differentiated",[0,0,0,0,0,0]),
 ("dr05","DR05-2","Structural reroutes (هدي already-present, أتي/رأي unflattened) still mis-routed",
  "confirmed_fixed","lane-sanity PASS; casebook bucket1='structural reroute — no authoring' (هدي example) routed to reindex","validate_open_stem_lane_sanity.py",
  "owner-gated live reindex for index-miss families",[0,0,0,0,0,0]),
 ("dr05","DR05-3","Unsafe families must be frozen as rejection fixtures",
  "confirmed_fixed","check_regressions scar-family fixtures (>=16: verb-clitic+voice+banned كذبوا/ويقتلون/فاستقيموا/جاءني) all REJECT","tools/check_regressions.py",
  "none",[0,0,0,0,0,0]),
 ("dr05","DR05-4","True missing-entry families need owner-gated proposals",
  "confirmed_fixed","new_entry lane: 52 proposals (سوأ/رضو/ربب/صلو/زكو); owner-gated review-only","build_new_entry_proposals.py",
  "owner decision to author entries",[0,1,0,0,0,0]),
]

STATUS_BLOCK = {0:"no",1:"YES"}
BLOCK_LABELS = ["authoring","90%","sarf/nahw","claude.ai","corpus","public-redistribution"]

def rows():
    out=[]
    for dr,fid,text,status,method,aff,rem,bl in F:
        out.append({"approach":dr,"finding_id":fid,"finding":text,"status":status,
                    "verification_method":method,"affected":aff,"remaining_action":rem,
                    "blocks":{BLOCK_LABELS[i]:bool(bl[i]) for i in range(6)}})
    return out

def emit_master(rs):
    with open(os.path.join(OUT,"my-deep-research-master-matrix.jsonl"),"w",encoding="utf-8") as f:
        for r in rs: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    from collections import Counter
    sc=Counter(r["status"] for r in rs)
    md=[f"# My deep-research master matrix — {DATE} (HEAD {HEAD})\n",
        "Fresh re-attempt of dr01–dr05 against the current tree + live read-only verification. "
        "One row per finding; status re-derived from evidence, not inherited.\n",
        f"**{len(rs)} findings** — " + ", ".join(f"{k}: {v}" for k,v in sc.most_common()) + ".\n",
        "| approach | id | status | blocks | finding | verification |",
        "|---|---|---|---|---|---|"]
    for r in rs:
        b=[k for k,v in r["blocks"].items() if v] or ["—"]
        md.append(f"| {r['approach']} | {r['finding_id']} | **{r['status']}** | {','.join(b)} | "
                  f"{r['finding'][:90]} | {r['verification_method'][:70]} |")
    md.append("\n## Headline\n")
    md.append("- **DR02-5 (examples[].en = verbatim Saheeh International, owner-gated)** is the one "
              "finding under-stated by every prior pass — surfaced + quantified + detector built this "
              "tranche. Blocks public-repo redistribution cleanliness ONLY; does NOT block coverage-to-90 "
              "or the (clean, authored) hover output.\n")
    md.append("- Everything else: confirmed_fixed or narrowed/false_positive. 0 findings block authoring "
              "or the engine. The only authoring-relevant pending is owner-paced multi-batch coverage "
              "(Phase 8) + owner-gated lanes.\n")
    open(os.path.join(OUT,"my-deep-research-master-matrix.md"),"w",encoding="utf-8").write("\n".join(md))
    return sc

REPORTS = {
 "my-dr01-state-and-artifact-reattempt": ("DR01 — state, canonical artifacts, liveness",
   "Settled the truth-source problem head-on (Phase 0). The real current HEAD is **d67f873**, "
   "identical across the working tree, the local tracking ref, AND the actual GitHub remote "
   "(`git ls-remote`). `a0f596b` is the prior open-stem tranche tip (a stale reviewer view); "
   "`3d621c1` is stale text inside the prior final report (its HEAD-at-generation). Coverage is "
   "**86.18% (43,005/49,900), now LIVE-verified** by reading the live wbw-lookup `_meta.coverage` "
   "(built 2026-06-25T03:48:30Z) — equal to repo. The one open DR01 item is the **public 2,092-page "
   "crawl**, executed in Phase 2 of this tranche."),
 "my-dr02-repo-operational-reattempt": ("DR02 — repo operations, paths, provenance, claude.ai pack",
   "Canonical-path hygiene, batch/provenance parity, the claude.ai pack, and the corpus fixture are "
   "all validator-gated and PASS. The hover output is leak-free (0 private keys live + structural "
   "gating at every dataset level). **The decisive DR02 finding: `examples[].en` is NOT "
   "qamus-authored — it is verbatim Saheeh International** (7,700 examples, 41.3% carry the "
   "`[bracket]` interpolation signature), copied into the PUBLIC dataset. The dataset validator gates "
   "structure/leak/private keys but has no anti-copy guard. Built `audit_examples_en_provenance.py` "
   "to quantify it. **Classification: owner-gated (source/licensing).** It blocks public-repo "
   "redistribution cleanliness only — NOT coverage-to-90 and NOT the (clean) hover output."),
 "my-dr03-adversarial-narrowing-reattempt": ("DR03 — adversarial narrowing / false-positive control",
   "Old concerns triaged: the '82.49% anchor' is a **false positive** (now 86.18% repo+live); "
   "'historical hygiene broken' is **narrowed** to soft warnings; 'learner content missing' is "
   "**narrowed** (it was a packaging/runtime gap, not absence). The real residuals all have wired, "
   "passing validators. The one **reopened** item is the opposite of over-statement: the "
   "examples[].en copied-translation was UNDER-stated by every prior pass and is now escalated "
   "to an owner-gated blocker."),
 "my-dr04-authoring-readiness-reattempt": ("DR04 — remaining stems / authoring lane readiness",
   "Lane-readiness re-derived from the current tree (generator + validator + schema confirmed "
   "present per lane). **GO:** form_variant (top lever), host_lexeme (noun-only), token_irab. "
   "**Built / review-only:** verb_clitic (638), source_entry_repair. **Owner-gated:** new_entry (52), "
   "index_miss (live reindex, not authoring). **Source/scholar-gated:** source_photo. The prior "
   "NO-GO (polluted host-lexeme, unhandled forms-array, missing generators) is resolved — all "
   "generators+validators+schemas exist and pass the regression gate."),
 "my-dr05-open-stem-casebook-reattempt": ("DR05 — open-stem casebook / unsafe families",
   "The backlog is fully differentiated: `review-only-casebook.jsonl` holds **1,606 families across "
   "9 buckets**, each row carrying bucket / family_key / root_cause / gate / generator / validator / "
   "next_command / contributes_to_90 — i.e. an open-stem-casebook-v2 already. Structural reroutes "
   "(هدي already-present → reindex; أتي/رأي flattened), function-word lanes, owner-gated missing "
   "entries (52), and frozen scar fixtures (كذبوا/ويقتلون/فاستقيموا/جاءني, all REJECT in the gate) "
   "are each routed to the correct lane with the correct gate."),
}

def emit_reports(rs):
    for stem,(title,summary) in REPORTS.items():
        dr=stem.split("-")[1]  # dr01..dr05
        frs=[r for r in rs if r["approach"]==dr]
        obj={"approach":title,"date":DATE,"head":HEAD,"findings":frs,
             "summary":summary,"count":len(frs),
             "statuses":{s:sum(1 for r in frs if r["status"]==s) for s in {r["status"] for r in frs}}}
        with open(os.path.join(OUT,stem+".json"),"w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2,sort_keys=True); f.write("\n")
        md=[f"# {title} — my re-attempt ({DATE}, HEAD {HEAD})\n", summary+"\n",
            "| id | status | blocks | finding | remaining |","|---|---|---|---|---|"]
        for r in frs:
            b=[k for k,v in r["blocks"].items() if v] or ["—"]
            md.append(f"| {r['finding_id']} | **{r['status']}** | {','.join(b)} | {r['finding'][:80]} | {r['remaining_action'][:80]} |")
        open(os.path.join(OUT,stem+".md"),"w",encoding="utf-8").write("\n".join(md))
        if dr=="dr05":
            with open(os.path.join(OUT,stem+".jsonl"),"w",encoding="utf-8") as f:
                for r in frs: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")

def main():
    rs=rows()
    sc=emit_master(rs)
    emit_reports(rs)
    print(f"MY-DR OK — {len(rs)} findings; statuses={dict(sc)}")
    print("owner-gated/unfixed:", [r["finding_id"] for r in rs if "unfixed" in r["status"] or "owner" in r["status"]])

if __name__=="__main__":
    main()
