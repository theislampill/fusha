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
- `cachebuster_parity_unverified`: learner-visible color/tooltip fix is claimed without asset-version/cachebuster readback and source/runtime payload parity.
- `health_wait_skipped`: service restart/readback result is judged before bounded health and parity checks finish.
- `token_only_override`: exact address differs from surface-family siblings.
- `rich_cert_preview_overclaim`: preview-only rich metadata treated as certified hover output.
- `rich_cert_pending_gate`: a pending/two-vote rich-cert row cleared from readable English alone.
- `rh_live_preview_only`: admin/renderer preview candidate treated as public rollout approval.

## Review Standard

Levels 0-3 usually need the answer key or one competent check. Levels 4-6 need procedure-linked reasoning for
morphology and syntax. Levels 7+ and every iʿrāb, case, mood, particle-function, PP-attachment, pronoun-referent,
exception, vocative, oath, or token-only item need two independent checks or an answer-key-backed rubric. If the
checks agree on English but disagree on grammar, log the item as not cleared.
