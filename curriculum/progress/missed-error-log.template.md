# Missed Error Log Template

Copy this file outside the repo for a real learner. The repo keeps the template only.

| date/session | level | token/example | learner answer | correct answer | error class | sarf issue | nahw issue | correction source | remediation drill | recurred? | two-vote/teacher review? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | answer key / rubric / procedure | | | |

## Error Classes

- `script_harakat`: missed sukūn, shadda, tanwīn, hamza seat, or vowel.
- `root_family_vibes`: guessed from root resemblance without POS/form/context.
- `finite_verb_dictionary_gloss`: used an infinitive/dictionary phrase for a finite verb.
- `suffix_omitted`: attached object/possessive/preposition pronoun vanished from the answer.
- `preposition_host_omitted`: bāʾ/lām/kāf/preposition contribution vanished.
- `particle_function_flattened`: `و`, `ف`, `ما`, `لا`, `لم`, `لن`, `إلا`, or similar treated as one fixed gloss.
- `wrong_irab_reasoning`: English answer may look right but case/mood/governor reasoning is wrong or missing.
- `pp_attachment_unclear`: jar-majrūr / PP attachment not certified.
- `idafa_reversed`: construct relationship or definiteness reversed.
- `component_only_overclaim`: component evidence used to certify a whole-token hover.
- `renderer_only_gap`: answer is linguistically safe but needs rich segment/display support.
- `hidden_number_morphology`: dual/plural ending exists but the answer or hover hides it.
- `hidden_derivative_shape`: participle/adjective/maṣdar shape exists but the answer collapses it to a root or infinitive.
- `hidden_imperfect_prefix`: finite imperfect prefix exists but the answer or color layer treats it as part of one opaque verb span.
- `coarse_white_host_span`: rich hover uses a plain/uncolored host where the learner needs role-aware color or a segment row.
- `quran_display_text_mismatch`: cited Qurʾān text lost a hamza seat, maddah, diacritic, word boundary, or selected target word.
- `process_prose_in_hover`: learner-facing explanation contains authoring/deployment/source-boundary prose instead of Arabic reasoning.
- `card_level_coverage_hidden`: report counts live rows while a visible listed example card remains flat, blocked, or unreported.
- `edge_join_missing_or_ignored`: rollout/tutoring claim skips the entry -> card -> selected word -> quran/wbw edge chain or manually rediscovers data that the graph already supplies.
- `orphan_loc_append`: an authored hover was keyed to a loc that does not render as a qword on its own live page (card-local/example-scoped index mistaken for a canonical `S:A:W` address); append was not gated on a `data-loc` readback.
- `mirror_row_infinitive_substitution`: a mirrored-surface authoring row replaced the certified inflected gloss with the dictionary infinitive, dropping voice/person/number (e.g. passive "is said" flattened to "to say").
- `cachebuster_parity_unverified`: learner-visible color/tooltip fix is claimed without asset-version/cachebuster readback and source/runtime payload parity.
- `health_wait_skipped`: service restart/readback result is judged before bounded health and parity checks finish.
- `token_only_override`: exact address differs from surface-family siblings.
- `rich_cert_preview_overclaim`: preview-only rich metadata treated as certified hover output.
- `rich_cert_pending_gate`: a pending/two-vote rich-cert row cleared from readable English alone.
- `rh_live_preview_only`: admin/renderer preview candidate treated as public rollout approval.
- `nafiya_false_govern`: named a non-governing particle (لا النافية, coordinating wāw, vocative) as the case/mood governor; right ending, wrong reason.
- `matuf_subjunctive_missed`: a verb conjoined onto a منصوب/مجزوم verb was read as indicative; the ʿaṭf-propagated mood was dropped.
- `estimated_ending_missed`: a defective/maqṣūr token's mood/case is muqaddar (estimated), not written; "no visible mark" was misread as "no mood/case".
- `loc_surface_mislabel`: an authored hover was keyed to a loc whose live span renders a different surface than the row's target token (data-loc existed but the word did not match).

## Train C `kc_id` Crosswalk

`tools/fusha_tutor_runtime.py` writes `progress.missed[].error_reason` as a `kc_id` from
`curriculum/kc-catalog.json` when the drill-key row carries one, and null otherwise. Legacy error classes from
the list above remain a manual-log vocabulary; the runtime does not emit them. The two vocabularies were authored
at different times, for different populations of items, and do not lexically match even where they describe the
same real-world symptom; a downstream consumer of `progress.missed` must not assume a `kc-*` code and a legacy
code are distinct errors just because their spelling differs. Known semantic overlaps are listed below; treat a
pairing as equivalent ONLY if it appears on this list.

| legacy `error_reason` | `kc_id` | same symptom? |
|---|---|---|
| `hidden_number_morphology` | `kc-number-suffix-hidden` | yes — a dual/plural ending hidden behind a plain singular gloss |
| `hidden_derivative_shape` | `kc-derivative-shape-hidden` | yes — a participle/derived noun collapsed to the verb, or its derivative shape hidden |
| `finite_verb_dictionary_gloss` | `kc-dictionary-infinitive-leakage` | describes the same defect (the dictionary "to ..." infinitive pasted onto a finite or derived form), but `kc-dictionary-infinitive-leakage` is not bound to any drill-key row yet and cannot currently be emitted as an `error_reason`; only `finite_verb_dictionary_gloss` is reachable today |
| `suffix_omitted` | `kc-suffix-pronoun-missing` | yes — an attached object/possessive pronoun dropped from the answer |
| `particle_function_flattened` | `kc-particle-function` | yes — a multi-function particle given one fixed gloss regardless of context |
| `wrong_irab_reasoning` | `kc-governor-justification` | describes the same defect (a correct case ending given with an absent or unjustified governor, right answer, wrong reason), but `kc-governor-justification` is not bound to any drill-key row yet and cannot currently be emitted as an `error_reason`; only `wrong_irab_reasoning` is reachable today |

Every other `kc_id` currently reachable as an `error_reason` (`kc-clitic-segmentation`,
`kc-root-template-slot-classification`, `kc-masdar-template-not-uniform`, `kc-nawasikh-kana-laysa-government`,
`kc-nawasikh-continuative-licensing`, `kc-nawasikh-inna-family-government`, `kc-nawasikh-qalb-verb-transitivity`,
`kc-nawasikh-stacked-governor-scope`, `kc-grapheme-confusables`, `kc-orthographic-connectivity`,
`kc-short-vowels-and-vocalization-state`, `kc-sukun-shadda-stack`, `kc-long-vowel-carrier-role`,
`kc-nunation-written-realization`, `kc-definite-article-assimilation`, `kc-attributive-follower-licensing`,
`kc-coordination-particle-case-following`, `kc-badal-apposition-typology`, `kc-waw-function-accompaniment`,
`kc-assimilated-verb-radical-scope`, `kc-defective-verb-suffix-and-jussive-shift`,
`kc-geminate-verb-merger-licensing`, `kc-hamzated-verb-carrier-and-imperfect`,
`kc-doubly-weak-verb-subtype-composition`, `kc-passive-voice-melody-and-argument-promotion`,
`kc-deputy-agent-function-discrimination`, `kc-t1-derivation-noun-final-class-declension`,
`kc-t1-derivation-passive-voice-construction`, `kc-t1-derivation-root-template-letter-discipline`,
`kc-t1-derivation-idafa-masdar-argument-case`, `kc-t1-derivation-participle-usage-licensing`,
`kc-t1-derivation-terminology-category-discipline`, `kc-t1-ma-context-masdariyya-verbal-noun-substitution`,
`kc-t1-ma-context-hijaziyya-tamimiyya-nullifiers`, `kc-t1-ma-context-amma-kaffa-jawab-fa`,
`kc-t1-ma-context-exclamatory-interrogative-case`, `kc-t1-ma-context-negated-possession-lam-subjunctive`,
`kc-t1-ma-context-lamma-jazm-vs-temporal-rival`, `kc-t1-ma-context-ma-zala-kana-sister-government`,
`kc-t1-ma-context-ma-dama-temporal-not-negation`, `kc-t1-ma-context-ma-nafiya-no-mood-government`,
`kc-t1-ma-context-istifham-alif-elision-preposition`, `kc-t1-ma-context-relative-preposition-majrur-government`,
`kc-t1-ma-context-ma-vs-man-rational-referent`, `kc-t1-ma-context-innama-kaffa-restriction-scope`,
`kc-t1-ma-context-lamma-jazm-requires-mudari`) has NO legacy equivalent above; treat it as
its own distinct error class,
not a re-spelling of anything in the "Error Classes" list. Conversely, every legacy code not listed in the
crosswalk table (`script_harakat`, `root_family_vibes`, `pp_attachment_unclear`, etc.) has no `kc_id` equivalent
yet and stays a legacy-only code until a drill row binds it. The remaining KCs in `curriculum/kc-catalog.json`
(e.g. `kc-attached-pronoun`, `kc-unvoweled-homograph`, `kc-preposition-host`, `kc-case-mood-context`,
`kc-governor-justification`, `kc-dictionary-infinitive-leakage`, `kc-orthography`, `kc-hidden-proclitic`,
`kc-passive-voice-hidden`, `kc-token-vs-phrase-hover`, `kc-source-address-scope`, `kc-canonical-address-crosswalk`,
`kc-public-boundary-source-clean`) are not yet bound to any drill-key row and so cannot appear as an
`error_reason` at all, even where they are listed as a "same symptom" pairing above. The five `kc-nawasikh-*` KCs
are bound to `curriculum/drills/keys/nawasikh-governor-families.keys.jsonl` (Train B/C L2.M2 batch); the sixth
candidate family from the same batch, inna-family MODAL FORCE, has NO `kc_id` — it stays `documented_only` at
the canonical-unit level (`cu-inna-modal-force`, `capability_family: instructional_only`) and its two practice
rows in that key file carry no `kc_id` at all, never a substitute one.

## Review Standard

Levels 0-3 usually need the answer key or one competent check. Levels 4-6 need procedure-linked reasoning for
morphology and syntax. Levels 7+ and every iʿrāb, case, mood, particle-function, PP-attachment, pronoun-referent,
exception, vocative, oath, or token-only item need two independent checks or an answer-key-backed rubric. If the
checks agree on English but disagree on grammar, log the item as not cleared.
