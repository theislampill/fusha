# Dogfood Error Remediation Index

Use this index when a learner or agent makes a mistake already seen in Qamus dogfood. The goal is not to memorize
the history; it is to route a miss to the procedure and drill that prevents the same hover defect from returning.

**Precedence when the same symptom appears in both tables below:** the runtime field
`progress.missed[].error_reason` (see `tools/fusha_tutor_runtime.py`) carries a bound `kc_id` or null. It does not
emit legacy error-class strings. The first table is a manual-log and historical dogfood vocabulary; the second
table records the current KC routing posture. The two vocabularies were authored independently and are NOT
interchangeable spellings of each other. Where the same real-world symptom
may appear under both vocabularies, treat the ids as equivalent only when the authoritative crosswalk explicitly
pairs them. The legacy `hidden_derivative_plural_piece` row is broader than either
`kc-number-suffix-hidden` or `kc-derivative-shape-hidden`; it is not an equivalence assertion for either KC. The
table whose id vocabulary matches the actual `error_reason` value is authoritative for that lookup. The full
crosswalk, including which `kc_id`s have no legacy equivalent, is maintained in
[`../progress/missed-error-log.template.md`](../progress/missed-error-log.template.md#train-c-kc_id-crosswalk).

| error class | learner symptom | drill | procedure |
|---|---|---|---|
| `finite_verb_dictionary_gloss` | finite verb glossed as "to ..." | `../assessment/level-checkpoints.sample.jsonl` L8 item, `../../sarf/drills/dogfood-sarf-remediation.md` | `../../sarf/procedures/verb-form-and-mood-review.md` |
| `suffix_omitted` | `كَ`, `ه`, `هم`, `نا` disappears from answer | `../../sarf/drills/clitic-and-host-morphology.md`, `../../sarf/drills/dogfood-sarf-remediation.md` | `../../nahw/procedures/pronoun-attachment.md` |
| `preposition_host_omitted` | `بـ`/`لـ`/`كـ` ignored and host gloss shown alone | `hover-composition-and-routing.md` | `../../nahw/procedures/preposition-pronoun.md` |
| `particle_function_flattened` | `ما`, `و`, `ف`, `لا`, `لم`, `لن`, `إلا` treated as one fixed gloss | `quranic-function-words.md`, `../../nahw/drills/dogfood-nahw-remediation.md` | `../../nahw/procedures/particle-decision.md` |
| `wrong_irab_reasoning` | English answer looks plausible but case/mood/governor is wrong | `../../nahw/drills/grammar-reasoning-safety.md` | `../../nahw/procedures/grammar-risk-gate.md` |
| `root_family_vibes` | same-root surface chosen without POS/form/context | `root-pattern-practice.md`, `../../sarf/drills/root-detection.md` | `../../sarf/procedures/root-decision.md` |
| `component_only_overclaim` | segment evidence used as whole-token certification | `parse-key-and-color-layer.md` | `../../qamus/reports/morphosyntax-token-contract.md` |
| `renderer_only_gap` | grammar is safe but not teachable as rich hover | `parse-key-and-color-layer.md` | `../qamus-hover-parse-key-and-color.md` |
| `token_only_override` | surface-family propagation would change another location incorrectly | `hover-composition-and-routing.md` | `../../qamus/reports/source-address-model.md` |
| `rich_cert_preview_overclaim` | preview metadata treated as certified/live hover support | `parse-key-and-color-layer.md` | `../../qamus/reports/rich-cert-flywheel-synthesis-20260627.md` |
| `rich_cert_pending_gate` | pending/two-vote row cleared from readable English alone | `hover-composition-and-routing.md`, `parse-key-and-color-layer.md` | `../../qamus/reports/rich-cert-flywheel-synthesis-20260627.md` |
| `rh_live_preview_only` | renderer/admin preview candidate mistaken for public rollout approval | `parse-key-and-color-layer.md` | `../../qamus/reports/rich-cert-flywheel-synthesis-20260627.md` |
| `all_visible_qword_not_accounted` | selected word or draft counter looks complete while other qwords on the same card stay flat | `mode-a-thin-slice-regressions.md` | `../../docs/parser/qamustyping4-implementation.md` |
| `vocalized_card_readback_drift` | cited Qur'an usage text loses required harakat, hamza, maddah, or selected surface | `mode-a-thin-slice-regressions.md` | `../../provenance/source-boundaries.md` |
| `hidden_finite_verb_piece` | finite verb hover hides prefix, stem, subject marker, or object pronoun | `../../sarf/drills/clitic-and-host-morphology.md` | `../../sarf/procedures/verb-form.md` |
| `hidden_derivative_plural_piece` | participle/noun hover hides article, derivative prefix, or plural suffix | `../../sarf/drills/nominal-derivatives.md` | `../../sarf/procedures/noun-plural-gender.md` |
| `proper_name_fake_root` | a proper name is forced into a root just to fill morphology fields | `mode-a-thin-slice-regressions.md` | `../../sarf/procedures/proper-noun.md` |
| `function_cluster_phrase_only` | particle cluster is translated as a phrase while individual functions stay uncolored | `../../nahw/drills/particle-disambiguation.md` | `../../nahw/procedures/function-token-hover-review.md` |
| `vn00_aggressive_false_closure` | public qword has hover/color or packet status but hides root, prefix, suffix, article, particle role, or token-vs-phrase contribution | `vn00-aggressive-hover-closure.md` | `../../tools/validate_vn00_aggressive_false_closure.py` |
| `vn00_v003_false_closure_addendum` | v003-style rows hide suffix/pronoun/plural, derivative/place prefix, nominal tāʾ, broken plural, common-particle role, or token pieces behind phrase-only hovers | `vn00-aggressive-hover-closure.md` | `../../tools/validate_vn00_aggressive_false_closure.py` |
| `cognitive_load_density_overload` | one hover or explanation stacks so many facts (root, form, every clitic, case, referent) at once that the learner is overwhelmed and cannot act; density is treated as thoroughness | `parse-key-and-color-layer.md` | `../cefr-fusha-instruction.md` (hint depth, metalanguage exposure, and correction aggressiveness gated by band — teach one piece at a time, not the whole lattice) |
| `learner_outcome_not_improving` | the same miss recurs across sessions, or a level is marked cleared while the learner cannot reproduce the reasoning cold; mastery asserted from confidence, not evidence | `../assessment/level-checkpoints.sample.jsonl` (cumulative-review rows) | `../tutor-session-protocol.md` (schema-graded loop: answer-key grading, two-vote, missed-error log, pending over guessing) |

## Train C — KC-bound learner symptoms

These rows document the Knowledge Component in `curriculum/kc-catalog.json` that owns each symptom. Only rows
marked `emittable` are currently bound to a drill-key row and can appear in `progress.missed[].error_reason`.
Rows marked `documented_only` provide an honest remediation route for manual review but cannot be emitted by the
current tutor runtime. See `tools/fusha_tutor_runtime.py` and the authoritative reachability crosswalk linked
above.

| kc_id | runtime posture | learner symptom | drill | procedure |
|---|---|---|---|---|
| `kc-clitic-segmentation` | `emittable` | the whole token read as one stem instead of prefixed particle + host | `hover-composition-and-routing.md` | `../../sarf/procedures/clitic-and-host-morphology.md` |
| `kc-hidden-proclitic` | `documented_only` | a hover shows only the host and drops a prefixed particle (wāw/fāʾ/bāʾ/lām/kāf/al-) | `hover-composition-and-routing.md` | `../../sarf/procedures/clitic-and-host-morphology.md` |
| `kc-attached-pronoun` | `documented_only` | the ending folded into the stem instead of surfaced as an attached pronoun | `hover-composition-and-routing.md` | `../../sarf/procedures/suffix-pronoun-state.md` |
| `kc-suffix-pronoun-missing` | `emittable` | an attached object/possessive pronoun dropped from the gloss | `hover-composition-and-routing.md` | `../../sarf/procedures/suffix-pronoun-state.md` |
| `kc-number-suffix-hidden` | `emittable` | a dual/plural ending hidden behind a plain singular host or an English-only number | `parse-key-and-color-layer.md` | `../../sarf/procedures/noun-plural-gender.md` |
| `kc-derivative-shape-hidden` | `emittable` | a participle/derived noun glossed as the verb, or its derivative shape hidden | `parse-key-and-color-layer.md` | `../../sarf/procedures/nominal-derivative-decision.md` |
| `kc-masdar-template-not-uniform` | `emittable` | a Form-I verb's maṣdar (verbal noun) shape is assumed from one uniform template instead of checked per verb | `root-pattern-practice.md` | `../../sarf/procedures/masdar-participle.md` |
| `kc-root-template-slot-classification` | `emittable` | a weak letter or template-added letter is called a root radical (or the reverse) by shape or position alone, or a root is named by counting the first three consonants before the word is matched to its template | `root-pattern-practice.md` | `../../sarf/procedures/homograph-risk.md` |
| `kc-particle-function` | `emittable` | a multi-function particle (mā, wāw, ...) given one fixed gloss regardless of context | `quranic-function-words.md` | `../../nahw/procedures/particle-decision.md` |
| `kc-case-mood-context` | `documented_only` | a case/mood ending asserted with no visible ending and no governor named | `sentence-foundations.md` | `../../nahw/procedures/irab-case-mood.md` |
| `kc-governor-justification` | `documented_only` | a correct case ending given with an absent or unjustified governor (right answer, wrong reason) | `sentence-foundations.md` | `../../nahw/procedures/irab-case-mood.md` |
| `kc-nawasikh-kana-laysa-government` | `emittable` | kāna/laysa's khabar (or, for laysa, its paradigm/tense) mishandled — predicate left nominative, the rival (inna) family's pattern imported, or laysa forced into an imperfective/past-time/verb-negating reading it cannot carry | `nawasikh-governor-families.md` | `../../nahw/procedures/nawasikh-government.md` |
| `kc-nawasikh-continuative-licensing` | `emittable` | a polarity-licensed kāna-sister (`مَا زَالَ`/`مَا دَامَ` type) read without checking its required licensing negator, or a mā-composite treated as ordinary sentence negation | `nawasikh-governor-families.md` | `../../nahw/procedures/nawasikh-government.md` |
| `kc-nawasikh-inna-family-government` | `emittable` | inna-family's ism left nominative, its khabar wrongly marked accusative (importing kāna's pattern), or a light/heavy or inna/anna selection error | `nawasikh-governor-families.md` | `../../nahw/procedures/nawasikh-government.md` |
| `kc-nawasikh-qalb-verb-transitivity` | `emittable` | a two-accusative expectation forced onto a qalb-verb's literal-perception/location sense, only one of two complements marked accusative in a genuine judgemental use, or the verb's own agent miscounted as a complement | `nawasikh-governor-families.md` | `../../nahw/procedures/nawasikh-government.md` |
| `kc-nawasikh-stacked-governor-scope` | `emittable` | one family's case signature applied across a span that actually contains more than one governor, corrupting the elements belonging to the other governor | `nawasikh-governor-families.md` | `../../nahw/procedures/nawasikh-government.md` |

Checkpoint rule: a remediated item is not cleared until the learner can name what the visible Arabic piece
contributes and why the old hover failure was unsafe.
