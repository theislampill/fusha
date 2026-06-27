# Dogfood Error Remediation Index

Use this index when a learner or agent makes a mistake already seen in Qamus dogfood. The goal is not to memorize
the history; it is to route a miss to the procedure and drill that prevents the same hover defect from returning.

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

Checkpoint rule: a remediated item is not cleared until the learner can name what the visible Arabic piece
contributes and why the old hover failure was unsafe.
