# FINALIZATION / COVERAGE-TO-90 / FULL-AUDIT tranche — final report (2026-06-25)

## 0. State

- **HEAD / origin/main / GitHub remote**: all agree (verified `git ls-remote`). Real current HEAD =
  the commit carrying this report. The prior-session ambiguity (`a0f596b` / `3d621c1` / `d67f873`)
  was settled in Phase 0: `d67f873` was the real start; `a0f596b` = prior-tranche tip (stale view),
  `3d621c1` = stale report text. **No fork, no unpushed divergence.**
- **live deployment touched: YES** — qamus hover layer only (+584), via the scoped
  backup→append→`rebuild.sh`→health→diff loop; NOT webroot/phpBB/wiki/DB. Rollbacks in place
  (`.bak-fv3-*`, `.bak-hl2-*`, `wbw-lookup.prev.json`).

## 1. Coverage — live-verified

| metric | start | end | Δ |
|---|---:|---:|---:|
| **live coverage** | **86.18%** | **87.35%** | **+1.17 pts** |
| resolved (glossed) | 43,005 | **43,589** | **+584** |
| pending | 6,895 | 6,311 | −584 |
| wrong glosses shipped | 0 | **0** | 0 |

Both increments **live-verified** by reading the live `wbw-lookup.json` `_meta.coverage`
(`{glossed:43589, pct:87.35}`); repo reconciles to live exactly. Coarse blockers now
**4156 / 1775 / 380 / 0** (stem_base_unknown / source_entry_unverified / same_surface_polysemy /
proper_noun).

### Authoring cycles (this tranche)
| cycle | lane | candidates | approved | applied live | diff | wrong |
|---|---|---:|---:|---:|---|---:|
| 003 | form-variant (sarf+nahw 2-vote, 38 agents) | 559 fam | 366 | **+510** | +510/−0/~0 | 0 |
| 003b | host-lexeme possessive (2-vote, 12 agents) | 139 loc | 108 | **+74** | +74/−0/~0 | 0 |

Scar fixtures (كذبوا، ويقتلون، فاستقيموا، جاءني) were **rejected** by the gate in both cycles.

## 2. The five deep-research re-attempts (my deliverables)

`my-deep-research-master-matrix` + `my-dr01..05` — **29 findings**: 21 confirmed_fixed, 2
false_positive, 3 narrowed, 1 reopened, 2 open (DR01-5 crawl → done this tranche; DR02-5 below).

**🔴 DR02-5 (headline, owner-gated):** `examples[].en` in the **public dataset** is **verbatim
Saheeh International** — 7,700 examples, **41.3% carry the `[bracket]` interpolation signature** — a
copied published translation, NOT Qamus-authored. The dataset validator gates structure/leak/private
keys but has **no anti-copy guard** on `examples[].en`. Quantified by `audit_examples_en_provenance.py`.
**This is separate from the hover output** (live-verified `src:qamus`, 0 leaks). It blocks **public-repo
redistribution cleanliness only** — not coverage and not the hover layer. **OWNER DECISION required:**
(A) confirm Saheeh-Intl redistribution rights for daʿwah + add attribution/license notice; (B) replace
with an openly-licensed translation; (C) author original example renderings; (D) drop `en` from the
public dataset (Arabic is Tanzil CC BY 3.0, already attributed). Recommended: (A) or (D).

## 3. Full public crawl (Phase 2 — was deferred, now done)

**2,092 / 2,092 (100%) crawled** read-only; **2,092 × HTTP 200**, 0 render errors, **0 headword
mismatches** (1 transient 503 re-fetched → 200). Every repo entry renders publicly with a matching
headword. Tools: `crawl_qamus_public_entries.py` (throttled, resumable) + `validate_qamus_public_crawl.py`.

## 4. Audits

- **engine completeness:** sarf **11/11**, nahw **16/16** named failure modes (procedure+reference+eval);
  the prompt's enumerated checklist (16 sarf / 18 nahw) is subsumed (weak+hamzated+doubled combined;
  vowel+tanwīn combined; proper-vs-common in nahw + sarf/proper-noun). 0 gaps. Grammar evals: 88
  cases, 0 errors, 8 wrong-reasoning traps.
- **hover grammar metadata:** POS 99% / root 62% derivable; honest scope (gender/case/mood flagged
  missing, never fabricated). **quality 91.24% clean** (39,236/43,005), repair queue 3,769
  (`too_generic_gloss`).
- **source-photo + counts:** 0 internal count contradictions (cited āyāt ≤ claimed total_uses
  everywhere); 4 source-gated crops queued (owner-provided).
- **claude.ai pack:** 28 files / 139,896 B, verify PASS; learner + Qamus-review self-tests + tutor
  routing.
- **corpus-to-Qamus:** Nawawī40 read-only OK (0 live writes, no translation leak); Ṣaḥīḥayn plan-only.

## 5. 90% — NOT reached; precise blocker (owner-gated)

- Need for 90% = 44,910 resolved. Current **43,589**. **Delta = +1,321.**
- **Non-owner authoring lanes realistically top out near ~88.5–89.4%** — proven from the live ledger
  composition: the safe form-variant lane is now a long tail (1,243 tokens total; 510 banked),
  host-lexeme ~181 left, token-iʿrāb/function-word lanes are low-approval homographs, verb-clitic
  (822) is review-only. Their approval-discounted yield does not reach +1,321.
- **The single largest, safest lever to 90% is OWNER-GATED, not authoring:**
  `already_entry_form_present_index_miss` ≈ 1,055 tokens — a **LIVE surface-index / resolver rebuild**
  (0 wrong-gloss risk; the form already maps to an existing entry). It is out of public-repo scope.
- The dominant blocker `stem_base_unknown` (4,156) largely needs **new Qamus entries** = owner content
  decisions (52 owner-gated proposals already certified-ready in `build_new_entry_proposals`).

**Conclusion:** reaching exactly **90% live is owner-gated** (index-miss reindex + new-entry
authoring). This is a precise audited blocker, not a stall. The mechanism for the authoring lanes is
proven (this tranche, +584, 0 wrong) and every generator/validator/gate is wired.

## 6. Exact continuation

```
# more safe authoring (each ~+100–350, owner-paced; repeat):
python3 tools/build_form_variant_candidates.py --max-a 999999 --max-b 400 --max-c 400 --out out/hover_stage/fv_next.jsonl
  -> chunk -> form-variant-2vote -> build_form_variant_apply.py --name form_variant_batch_NNN
  -> validate -> append_decisions.py + rebuild.sh -> regenerate + gates + commit
# host-lexeme (server-side gen; ~181 left + 34 deferred partitives):
ssh: PYTHONPATH=.../services QAMUS_WBW_ARTIFACT=.../wbw-lookup.json QAMUS_DATASET=/tmp/entries.jsonl python3 build_host_lexeme_candidates.py --out /tmp/hl.jsonl --max 300
  -> host-lexeme-2vote -> build_host_lexeme_apply.py -> validate_suffix_pronoun_decisions -> append + rebuild
# verb-clitic (822, review-only) + token-iʿrāb (380): 2-vote, lower approval
# OWNER-GATED for the final push to 90%:
#   1) LIVE index-miss reindex (~1,055, 0 authoring risk) — fastest, safest lever
#   2) new-entry authoring for stem_base_unknown families (52 proposals ready)
#   3) examples[].en licensing decision (DR02-5)
```

## 7. Boundaries honored

Hover output stays Qamus-authored (`src:qamus, kind:authored`, 0 live leaks — verified). No external
glosses/translations/tafsir/OCR in public hover. Qurʾān read-only. `norm()` lookup-only. 2-vote
required answer AND reason; pending beats wrong (34 valid-but-non-conforming host glosses dropped,
not forced). Live apply only through the verified backup/rebuild/health/rollback gate.
