# Next-batch resume plan — exact, no vague "standing by"

## Where we are (live, reconciled 2026-06-24, completion-tranche P0–P12)

- Live coverage **81.91%** · **40,875 / 49,900** resolved · **9,025 pending** · health 200 ·
  `source_sha=65797d7d5599fadd` · 2,092 entries (947 v / 1,045 n / 100 p) · **615 token decisions**.
- This tranche: **+70 tokens** applied, **−0 removed, −0 changed**, **0 wrong glosses shipped**
  (81.77 → 81.85 suffix/pronoun batch_002 +40 → 81.91 content batch_001 +30), all 2-vote certified.
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
