# Open-stem hygiene delta (closure-2092 Phase 2)

Fixes F2/F3/F4 + the F1 fine marker in `build_blocker_root_cause_ledger.py`, so the remaining-pending
queue is truthfully classified and locally gateable before authoring. Companion: `.json`.

## Lane changes (root-cause counts, before → after hygiene)

| root cause | before | after | what changed |
|---|---:|---:|---|
| `missing_form_variant_on_existing_entry` | 3,461 | **3,032** | genuine form authoring; index-misses + reroutes removed |
| `already_entry_form_present_index_miss` | — | **1,050** | **NEW** — form already stored in entry; reindex/resolver-recoverable, NOT authoring |
| `verb_clitic_object_or_subject_candidate` | — | **822** | **NEW** — split out of host_lexeme (qac_pos==V; object/subject pronoun, not possessive) |
| `function_word_not_form_work` | — | **550** | **NEW** — function-words split out of forms_array (token/particle lane) |
| `particle_or_pronoun_misclassified_as_stem` | 418 | 388 | |
| `missing_qamus_entry_candidate` | 473 | **326** | أتي/رأي (+others) rerouted to existing entries via flattened-root lookup |
| `host_lexeme_possessive_candidate` | 1,210 | **255** | now **noun-host only** |
| `forms_array_missing_surface` | 633 | **158** | content N/V only |
| iʿrāb/ambiguous (`verb_form_or_voice`+`content_homograph`+`genuinely_ambiguous`) | 378 | 378 | unchanged (genuinely per-loc) |

## The four defects fixed

1. **F1 — already-present forms.** 1,050 tokens whose inflected surface is already stored in the owning
   entry's `usage[].forms`/headword are now `already_entry_form_present_index_miss` (recoverable by the
   live index/resolver fix), removed from authoring queues.
2. **F2 — verb-clitic pollution.** 780+ `qac_pos==V` rows (a verb's object/subject pronoun, e.g.
   ٱهْدِنَا "guide us", يَأْمُرُكُمْ "He commands you") are split into `verb_clitic_object_or_subject_candidate`;
   `host_lexeme_possessive_candidate` is now noun-host only (255). Per the nahw skill: an attached pronoun
   on a verb is never possessive.
3. **F3 — root-flatten misroute.** QAC roots are flattened (hamza/weak) before the by-root lookup, exactly
   as entry roots are; أتي (55) + رأي (34) + others now resolve to the existing أَتَى/رَأَى entries instead
   of inflating `missing_qamus_entry_candidate`.
4. **F4 — function-word pollution.** 494 `qac_pos==P` / function-word rows are routed out of
   `forms_array_missing_surface` into `function_word_not_form_work` (a token/particle decision).

## Revised safe-realizable pool (PROVISIONAL — validated by the hygiene validators)

| metric | value |
|---|---:|
| expected safe-realizable | **~3,516** |
| coverage ceiling if realized | **92.92%** |
| tokens still needed for 90% | **2,061** |
| 90% reachable via root-known authoring | **YES** (bounded multi-batch) |

Gates green: `validate_blocker_root_cause_ledger.py` (host-lexeme noun-only enforced) +
`validate_open_stem_lane_sanity.py` (no verb-clitic / false-blocker / function-word-stem pollution;
summary reconciles). The yield number is now honest because the authoring lanes no longer contain
index-misses, verb-clitics, function-words, or root-flatten misroutes.
