# Next-batch resume plan — exact, no vague "standing by"

## Where we are (live-verified, 2026-06-25, FINALIZATION/coverage-to-90 tranche)

- **Live coverage 87.35%** · 43,589 / 49,900 · 6,311 pending (cycle 003 form-variant +510 + host-lexeme
  +74 = **+584 this tranche, 0 wrong**). Need **+1,321 for 90%**. Non-owner authoring lanes top out
  ~88.5–89.4%; **90% is owner-gated** — safest lever = LIVE index-miss reindex (~1,055, 0 authoring
  risk), then new-entry authoring (52 ready) + examples[].en licensing (DR02-5). See
  `closure-2092/final-completion-and-90-report-20260625.md`.
- **HEAD reconciled** (Phase 0): real HEAD=origin/main=GitHub; `a0f596b`/`3d621c1` were stale captures.
- **Public crawl DONE**: 2,092/2,092 × HTTP 200, 0 mismatch (`live-vs-repo-entry-reconciliation`).
- **🔴 examples[].en = verbatim Saheeh International** in public dataset (owner-gated licensing; separate
  from clean hover output) — `examples-en-provenance-audit`.

### (prior) post-hygiene closure tranche — HISTORICAL
- **Deep-research reattempt PROVEN**: 40 findings closed (31 fixed/6 narrowed/2 false-positive/1 owner-gated), 5 approach reports, 0 high-sev blocking authoring (`closure-2092/deep-research-reattempt-matrix.*`). Missing generators built (verb-clitic/new-entry/source-entry-repair). Engine operational (sarf 11/11, nahw 16/16).
- **Open-stem queue-hygiene DONE** (5 deep-research audits actioned): surface index now covers `usage[].forms`
  (F1); host-lexeme is noun-only with verb-clitics split out (F2); roots flattened so أتي/رأي reroute (F3);
  function-words split out of forms_array (F4); batch + provenance gates wired (F12/F13); scar fixtures (F20);
  stale paths/status fixed (F6/F7/F10/F11); graph fail-closed (F5). All hygiene validators GREEN.
- **The raw pre-hygiene lane counts were polluted** — do NOT resume authoring from them. Use the de-polluted
  casebook: `closure-2092/review-only-casebook.md` + `next-authoring-go-nogo.md`.

### Next authoring — GO lanes only (generator+validator-ready, 2-vote; hygiene validators pass)
1. **bucket 6 — existing-entry form authoring (3,262)** [top lever]: `build_form_variant_candidates.py --max-b 200
   --max-c 200` → `form-variant-2vote` workflow → `validate_form_variant_family_batches.py` → (LIVE apply is
   **private-context only**: append+`rebuild.sh` happen on the server, owner-gated; this repo never writes live).
2. **bucket 2 — noun-host possessive (255)** `build_host_lexeme_candidates.py` → 2-vote → `validate_suffix_pronoun_decisions.py`.
3. **bucket 7/4 — token iʿrāb + function-word (239 + 939)** `build_token_irab_decisions.py` → token-irab 2-vote.

### NO-GO until built (do NOT author from these raw counts)
- **bucket 3 verb-clitic (822)** — needs `build_verb_clitic_candidates.py` (object/subject pronoun lane).
- **bucket 5 missing-entry (326)** — needs `build_new_entry_proposals.py` + schema/validator; owner-gated, review-only.
- **bucket 1 index-miss (1,050)** — resolves on a LIVE resolver/index rebuild (owner-gated, out of repo scope), not authoring.
- **bucket 8/9 (158)** — source-photo / scholar-gated; stay pending by design.

> LIVE-APPLY commands (`append → rebuild.sh → restart`) are **private-context only** and never run from this
> public repo. This tranche produced NO apply payloads and authored NO glosses.

### (prior) Where we are (corrective tranche) — HISTORICAL, superseded by the banner above

- Live coverage **82.49%** · **41,164 / 49,900** resolved · **8,736 pending** · health 200 ·
  `source_sha=65797d7d5599fadd` · 2,092 entries (947 v / 1,045 n / 100 p) · **904 token decisions**.
- This tranche (corrective): **A1 artifact ergonomics** (repo dogfoodable — pretty/JSONL/.min, gated)
  + **+289 tokens** applied (B3 token-iʿrāb +188, B2 host-lexeme +101), **−0 removed, −0 changed**,
  **0 wrong glosses**. Blockers now: `stem_base_unknown` 6,866 · `source_entry_unverified` 1,349 ·
  `same_surface_polysemy_requires_i3rab` 520 · `proper_noun` 1.
- Coverage trail: 81.91 → 82.29 (B3) → **82.49% (B2)**.

### exact next (this tranche's resume)
1. Re-run `build_token_irab_decisions.py` for the next polysemy tier (remaining وما/لمّا + lower-freq
   content homographs) → `token-irab-verify` workflow → apply.
2. Re-run `build_host_lexeme_candidates.py` next tier → `host-lexeme-verify` → apply; mint owner-gated
   new-entry candidates for genuinely recurring missing nouns.
3. Source-photo: head-on crop pass over `source_photo_entry_locator.json` candidate pages (method
   proven; bulk digit-reads need head-on crops, not retakes — corpus complete).

### prior state (completion-tranche P0–P12, 81.91%)
- **Every one of the 49,900 hover tokens is terminal** (P3): resolved, or pending with an EXACT
  blocker — `stem_base_unknown` 6,969 · `source_entry_unverified` 1,505 ·
  `same_surface_polysemy_requires_i3rab` 550 · `proper_noun_no_qamus_entry` 1. **No generic pending.**
- **Complete public dataset committed** (P0): `qamus/data/current/` (2,092 entries, 7 indexes,
  schema, validator, query tool). **Source-address graph** (P1, 28,393 addresses, 0 orphans, 10
  queries). **Entry audit matrix** (P2, 2,092 rows, 0 unknown). All offline-queryable.

## What is DONE (this tranche)

P0 dataset · P1 graph · P2 matrix · P3 49,900-token audit · P4 suffix/pronoun expansion (+40) ·
P5/P6 content batch (+30) · P7 source-photo (2 visually verified, 0 retakes) · P8 skill install
verified · P9 GrammarProblems gate (88 cases + 8 wrong-reasoning traps) · P10 corpus→Qamus bound to
committed dataset · P11 live screenshots (b10 particle, عمل verb) · P12 scoreboards.

## Exact next (in priority order)

1. **Author the 785 host lexemes** with no Qamus noun entry (suffix/pronoun `stem_base_unknown`:
   خَلَاق, رِضْوَان, سِيمَا, مَثَل, …) → re-run `build_suffix_pronoun_candidates.py` → 2-vote → apply.
   Command chain:
   ```bash
   cat tools/build_suffix_pronoun_candidates.py | /tmp/sshx 'cat > /tmp/bspc.py'
   /tmp/sshx 'cd .../services && QAMUS_WBW_SERVICES=.../services \
     QAMUS_WBW_ARTIFACT=.../qamus_wbw/build/wbw-lookup.json QAMUS_DATASET=/tmp/entries.jsonl \
     python3 /tmp/bspc.py --out /tmp/sp_cands.jsonl'
   # pull -> Workflow(suffix-pronoun-verify) -> build_sp_batch -> append (backup) -> rebuild.sh
   ```
2. **Per-loc iʿrāb token decisions** for the 550 `same_surface_polysemy_requires_i3rab` (verb/noun
   homographs the content probe correctly rejected: يَدْعُونَ call/shove, يَحِلُّونَ lawful/adorn,
   وَمَا not/what, bare إِنْ if/emphatic). Generate per-loc candidates with āyah context → 2-vote
   (`/fusha-nahw` relative/negation + `/fusha-sarf` form-split) → apply. These need context, not a
   surface key — the token layer is the mechanism.
3. **Next content tier:** re-run `build_content_hover_candidates.py --max-per-section 60` for the
   next frequency tier (collision-free + single-sense) → 2-vote → apply. Each tier is smaller/harder.
4. **Build the `source_key → page` index** (the P7 bottleneck) from `pages.md` + the draft JSONs to
   scale source-photo visual verification beyond the 2 done this pass (corpus is complete; 0 retakes).

## Reusable harness (proven this tranche)

- candidate gen: `tools/build_suffix_pronoun_candidates.py`, `tools/build_content_hover_candidates.py`
- verify: Workflow `suffix-pronoun-verify` / `content-hover-verify` (2-vote, sarf+nahw lenses)
- apply: `out/hover_stage/build_*_batch.py` + byte-safe append (backup) to
  `qamus-service/ref/fusha-hover-token-decisions.jsonl` → `qamus_wbw/rebuild.sh`
- reconcile: `audit_all_hover_tokens.py` → `build_full_source_address_graph.py` →
  `audit_qamus_2092_entries.py` → scoreboards. Gate: `check_regressions.py` + `run_grammar_evals.py`.

## Continuation rule

Do not stop after one green batch. Continue tiers (per-loc iʿrāb → content tiers → new lexemes)
until every token is resolved or pending-with-exact-blocker (already true) AND every *safe* decision
is applied, or a real evidence/safety gate blocks. Each applied batch re-reconciles all scoreboards.
