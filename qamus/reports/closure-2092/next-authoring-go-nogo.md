# Next-authoring GO / NO-GO (closure-2092 Phase 10)

After the open-stem hygiene pass, the remaining 7,051 pending tokens are truthfully classified and
locally gateable. Companion: `next-authoring-go-nogo.json`, `review-only-casebook.{md,jsonl}`.

## Verdict

**GO** for the next authoring tranche on the **repo-authorable, generator+validator-ready, 2-vote** lanes
— but ONLY because the hygiene tranche removed the queue pollution (verb-clitics, function-words, index
misses, root-flatten misroutes). **NO-GO** on the raw pre-hygiene lane counts (they were inflated).

## Lane readiness (from the casebook buckets)

| bucket | lane | tokens | generator | validator | gate | GO/NO-GO |
|---:|---|---:|---|---|---|---|
| 6 | existing-entry form authoring | 3,262 | `build_form_variant_candidates.py` ✓ | `validate_form_variant_family_batches.py` ✓ | 2-vote | **GO** (top lever) |
| 2 | noun-host possessive | 255 | `build_host_lexeme_candidates.py` ✓ | `validate_suffix_pronoun_decisions.py` ✓ | 2-vote | **GO** |
| 7 | token-level iʿrāb / homograph | 239 | `build_token_irab_decisions.py` ✓ | `validate_token_irab_decisions.py` ✓ | 2-vote (per-loc) | **GO** (per-loc only) |
| 4 | function-word / particle-pronoun | 939 | `build_token_irab_decisions.py` ✓ | ✓ | 2-vote (token) | GO (token lane, not stem) |
| 3 | verb-clitic object/subject | 822 | **missing** `build_verb_clitic_candidates.py` | `validate_token_hover_decisions.py` | 2-vote (token) | **NO-GO** until generator exists |
| 5 | missing-entry proposal | 326 | **missing** `build_new_entry_proposals.py` | missing | owner | **NO-GO** (owner-gated, review-only) |
| 1 | structural reroute — index miss | 1,050 | `rebuild_surface_index_from_dataset.py` ✓ | `validate_surface_index_covers_usage_forms.py` ✓ | repo/reindex | **NO-GO for authoring** — resolves on a LIVE index/resolver rebuild (owner-gated, out of repo scope) |
| 8 | source-photo / source-gated | 10 | `source_photo_verify_entry.py` | manual | source | **NO-GO** (human source review) |
| 9 | scholar-gated / genuinely ambiguous | 148 | — | — | scholar | stays pending by design |

## What this changes for the path to 90%

- Real repo-authorable, generator-ready pool (buckets 6+2+7+4) = **~4,695 tokens** behind 2-vote.
- Index-recoverable (bucket 1, 1,050) needs a **live resolver rebuild**, not authoring — owner-gated.
- Yield-v2 safe-realizable ≈ **3,516** → ceiling **92.92%**; **+2,061** needed for 90% → **reachable**,
  but it is bounded multi-batch authoring on the GO lanes, NOT a single lever and NOT the raw queue.

## Required before resuming authoring (all DONE this tranche)

- ✅ surface index covers `usage[].forms` (F1); lane sanity green (no verb-clitic / false-blocker /
  function-word-stem pollution, F2/F3/F4); batch + provenance gates wired (F12/F13); scar-family
  fixtures frozen (F20); stale paths/status fixed (F6/F7/F10/F11); graph fail-closed (F5).

## Still missing before buckets 3 & 5 are GO

- `tools/build_verb_clitic_candidates.py` (verb + object/subject pronoun → token decisions).
- `tools/build_new_entry_proposals.py` + schema/validator (review-only, owner-gated).
- `tools/build_source_entry_repair_candidates.py --mode quran_refs` (entry-completeness).
