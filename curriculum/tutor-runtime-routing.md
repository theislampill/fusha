# Tutor-runtime routing

A thin routing layer (NOT a separate skill): map a learner's situation to the exact existing procedure,
roadmap section, or drill. The engine is already `sarf` + `nahw` + `curriculum`; this is the dispatcher.

For an actual tutoring session, start with
[`tutor-session-protocol.md`](tutor-session-protocol.md). It requires a progress file, missed-error log,
roadmap, assessment rubric, and explicit sarf/nahw procedure loading before a level is marked cleared.

## Learner mistake → sarf/nahw procedure

| learner error | route to |
|---|---|
| wrong/guessed root from the bare consonants | `sarf/procedures/root-decision.md` (evidence ladder; never from `norm()` alone) |
| confused verb form / tense / voice (I vs II vs IV; active vs passive) | `sarf/procedures/verb-form.md` |
| missed a weak/hamza/doubled radical | `sarf/procedures/weak-root.md` / `sarf/procedures/hamza-root.md` / `sarf/procedures/doubled-root.md` |
| put a verb gloss on a noun / participle / maṣdar | `sarf/procedures/masdar-participle.md` + sarf principle 3 (POS mismatch is a blocker) |
| hidden dual/plural ending in a rich hover or answer | `sarf/drills/dogfood-sarf-remediation.md` §Visible Number And Derivative Shape + `curriculum/drills/parse-key-and-color-layer.md` |
| passive participle/adjective read as an infinitive | `sarf/procedures/masdar-participle.md` + `sarf/drills/nominal-derivatives.md` §RH-LIVE visible number and derivative color |
| finite imperfect prefix hidden inside one verb-colored span | `sarf/procedures/verb-form.md` + `curriculum/drills/parse-key-and-color-layer.md` |
| accepted a host-only gloss when a written token has `بِـ`/`لِـ`/`كَـ`/`وَ`/`فَـ`/suffix pronoun | `curriculum/drills/hover-composition-and-routing.md` + `sarf/procedures/clitic-and-host-morphology.md` |
| split tanwīn fatḥ alif as pronoun `نا` | `curriculum/drills/alphabet-and-sounds.md` + `sarf/procedures/clitic-and-host-morphology.md` |
| read a proper noun as a common verb | `sarf/procedures/proper-noun.md` |
| collapsed a homograph (مَن/مِن، لَمْ/لِمَ، الملك) | `sarf/procedures/homograph-risk.md` + `nahw/procedures/particle-decision.md` |
| wrong particle function | `nahw/procedures/particle-decision.md` |
| treated `مَا` as one fixed English gloss | `nahw/procedures/ma-function-decision.md` + `curriculum/drills/quranic-function-words.md` |
| treated `وَمَا` as a single opaque word | `curriculum/drills/hover-composition-and-routing.md` + `nahw/procedures/function-token-hover-review.md` |
| flattened `وَ` as always "and" or `فَـ` as always "then" | `nahw/drills/grammar-routing-hard-cases.md` + `nahw/procedures/function-token-hover-review.md` |
| mis-rendered preposition+pronoun (إِلَيْنَا as a root) | `nahw/procedures/preposition-pronoun.md` |
| missed PP attachment or hidden attachment | `nahw/procedures/pp-attachment-review.md` |
| missed negation/mood effect (لم + jussive → past) | `nahw/procedures/negation.md` / `nahw/procedures/irab-case-mood.md` |
| missed governing-particle mood (lan/lam/lām/causal fā'/prohibition lā) | `nahw/procedures/governing-particle-mood-review.md` |
| wrong iḍāfa / jar-majrūr wording | `nahw/procedures/idafa-jar-majrur.md` |
| carried a referent across (divine Name vs attribute, Prophet vs adjective) | `nahw/procedures/referent-context.md` |
| tooltip explanation contains source-boundary/deployment/process prose instead of Arabic reasoning | `nahw/drills/dogfood-nahw-remediation.md` §Learner Explanation Versus Process Prose + `curriculum/drills/hover-composition-and-routing.md` |
| Qurʾān usage text lacks canonical hamza/maddah/diacritics or the selected target word | `provenance/source-boundaries.md` + `curriculum/drills/hover-composition-and-routing.md` source-text blocker rule |
| report says row coverage is complete while a visible example card remains flat/blocked | `curriculum/drills/hover-composition-and-routing.md` card-level coverage rule + `curriculum/progress/missed-error-log.template.md` |
| rollout or assessment manually rediscovers pages despite existing entry/card/word edges | build the graph edge join first; route missing pieces as `missing_entry_url_edge`, `missing_source_card_edge`, `missing_selected_word_edge`, or `missing_quran_wbw_edge` |
| public color/tooltip fix is claimed but stale assets may still render | require cachebuster/DUV readback and affected CSS/JS URL proof before marking the learner-visible fix complete |
| qamus restart causes immediate public readback noise | run health-wait plus source/runtime parity before judging the Arabic/content payload |
| used QAC concept membership as a translation | `qamus/procedures/grammar-resource-usage.md` + `curriculum/drills/hover-composition-and-routing.md` |
| confused named entity with common lexical meaning | concept-map flag internally, then `sarf/procedures/proper-noun.md` and verse-specific nahw/i'rab |
| qamustyping4 all-qword regression: a cited card has uncolored or hoverless visible words | `curriculum/drills/mode-a-thin-slice-regressions.md` + `curriculum/drills/dogfood-error-remediation-index.md` |
| qamustyping4 visual regression: cited Arabic loses harakat/hamza/maddah | source-text/readback blocker in `curriculum/drills/mode-a-thin-slice-regressions.md`; do not teach from the corrupted display |
| qamustyping4 function cluster: `أَمْ لَهُمْ`, `أَيَّانَ`, or similar rows are phrase-only | `nahw/drills/particle-disambiguation.md` + `nahw/procedures/function-token-hover-review.md` |
| Plan 15 route family is unknown or collapsed to "blocked" | `teach_plan15_route_family` → `curriculum/drills/plan15-route-families.md` |
| all visible qword denominator is confused with hover completion | `teach_qword_denominator` → `curriculum/drills/qword-denominator-and-crosswalk.md` |
| source-crosswalk packet is treated as deployable | `teach_source_crosswalk` → `curriculum/drills/qword-denominator-and-crosswalk.md` |
| packet row is taught as a public hover answer | `teach_packet_vs_hover` → `curriculum/drills/packet-vs-hover-projection.md` |
| rendered hover cannot trace back to source/card/qword | `teach_transclusion_trace` → `curriculum/drills/transclusion-hover-capstone.md` |

## Situation → curriculum

| situation | route to |
|---|---|
| new learner, unknown level | `curriculum/placement-test.md` → `curriculum/zero-to-fluency-roadmap.md` |
| wants the path end-to-end | `curriculum/zero-to-fluency-roadmap.md` (12-level ladder) |
| wants practice from real Qurʾān | `curriculum/qamus-driven-fluency-engine.md` (Qamus examples → drills) |
| keeps losing attached pieces inside one written token | `curriculum/drills/hover-composition-and-routing.md` |
| auditing whether a Qamus card is actually rich-hover/color complete | `curriculum/drills/mode-a-thin-slice-regressions.md` |
| checking mastery before advancing | `curriculum/mastery-checkpoints.md` |
| running a live tutoring session | `curriculum/tutor-session-protocol.md` + `curriculum/assessment/grading-rubric.md` |
| tracking learner state | `curriculum/progress/learner-progress.template.md` |
| tracking repeated misses | `curriculum/progress/missed-error-log.template.md` |
| right answer but shaky reasoning | the GrammarProblems gate (`nahw/SKILL.md` §grammar-safety) — a correct answer with wrong iʿrāb is unsafe |

## Discipline

- Blank beats wrong: if the learner (or you) cannot certify the root + POS + sense, mark it **pending**
  with the exact blocker, then route to the procedure that resolves that blocker.
- Production/speaking practice is outside this reading-first curriculum scope. Answer keys, grading rubrics,
  and state templates live under `curriculum/assessment/` and `curriculum/progress/`; this file only routes to them.

## Parser/checker diagnostic → route

The Fusha parser/checker (`tools/fusha_check.py`, contract `qamus/reports/parser-checker-substrate.md`) emits a
source-addressed **grammar Issue** for each thing wrong with a proposed analysis. Every issue already carries its
own `route_to {lane, procedure}`; this table is the human-readable mirror so a tutor knows where a diagnostic
lands. The checker is the deterministic verifier — a `pending`/`out_of_scope` diagnostic is a PASS, a wrong gloss
is not (blank beats wrong).

| parser issue class | route to |
|---|---|
| `hidden_clitic_or_proclitic` | `sarf/procedures/clitic-and-host-morphology.md` |
| `host_only_preposition_hover` | `sarf/procedures/clitic-and-host-morphology.md` (+ `nahw/procedures/preposition-pronoun.md`) |
| `suffix_pronoun_missing` | `sarf/procedures/clitic-and-host-morphology.md` (+ `nahw/procedures/pronoun-attachment.md`) |
| `passive_voice_hidden` | `sarf/procedures/verb-form.md` |
| `dual_or_plural_suffix_hidden` | `sarf/procedures/masdar-participle.md` |
| `derivative_or_participle_prefix_hidden` | `sarf/procedures/masdar-participle.md` |
| `ma_function_unresolved_or_wrong` | `nahw/procedures/ma-function-decision.md` |
| `phrase_translation_used_as_token_hover` | `curriculum/drills/hover-composition-and-routing.md` |
| `weak_irab_reasoning` (right answer, wrong/no governor) | `nahw/procedures/irab-case-mood.md` — **scholar/iʿrāb (two-vote) review** |
| `graph_edge_missing` / token out of source-addressed scope | `qamus/reports/source-address-model.md` (validator lane) |
| `display_local_canonical_crosswalk_missing` | `curriculum/drills/hover-composition-and-routing.md` source-text blocker rule |
| `source_clean_boundary_violation` | `provenance/source-boundaries.md` (validator lane) — never ships |

`weak_irab_reasoning` is the executable form of the GrammarProblems gate (`nahw/SKILL.md` §grammar-safety): a
correct ending without a justified governor is unsafe and routes to two-vote/scholar review, never to an
auto-resolved hover. Deepening: the curriculum/learner-feedback lane is `parserplans/010` (KC Violation Records +
Point→Teach→Bottom-out hints).

## General (arbitrary-text) diagnostic → route

The general Fusha text checker (`tools/fusha_text_check.py`) runs on arbitrary typed/unvoweled Arabic where there is
**no** source address. It emits the 12 NEW general classes below; every one carries `severity` + `gate` + `route` and
is **never** `auto_safe` (arbitrary text cannot reach source-addressed certainty). These are the arbitrary-text
generalization of the 12 source-addressed classes above — a tutor uses the same procedures, but the diagnostic is a
*candidate/ambiguity* notice, not a verified error. Blank/PENDING beats a guess.

| general issue class | severity | route to |
|---|---|---|
| `possible_clitic_segmentation` | warn | `sarf/procedures/clitic-and-host-morphology.md` |
| `possible_preposition_host` | warn | `nahw/procedures/preposition-pronoun.md` |
| `possible_definite_article` | info | `sarf/procedures/clitic-and-host-morphology.md` |
| `possible_attached_pronoun` | warn | `sarf/procedures/suffix-pronoun-state.md` (single-letter ه/ك/ي → two-vote or PENDING `context_sensitive_needs_nahw`) |
| `ambiguous_unvoweled_token` | warn | `sarf/procedures/homograph-risk.md` (keep the candidate lattice; never force one parse) |
| `possible_particle_function` | warn | `nahw/procedures/particle-decision.md` |
| `possible_case_or_mood_requires_context` | warn | `nahw/procedures/irab-case-mood.md` |
| `possible_governor_unresolved` | warn | `nahw/procedures/irab-case-mood.md` — arbitrary-mode equivalent of `weak_irab_reasoning` |
| `orthography_normalization_warning` | info | `sarf/procedures/hamza-root.md` (original spelling preserved; key is match-only) |
| `dialect_or_non_fusha_possible` | info | `nahw/procedures/grammar-risk-gate.md` |
| `source_address_required_for_certainty` | info | `provenance/source-boundaries.md` (validator lane) — cite an address to raise confidence |
| `rich_hover_candidate_available_when_source_addressed` | info | `qamus/reports/general-checker-rich-hover-flywheel.md` — bridge to the rich-hover candidate flywheel |

Full design: `parserplans/general-fusha-grammar-checker/{004,011,014}`; flywheel bridge:
`qamus/reports/general-checker-rich-hover-flywheel.md`.

## P2: governor / dependency-lattice diagnostic → route

The governor/iʿrāb dependency lattice (`tools/fusha_governor.py`) emits dependency-edge candidates. A tutor routes by
the edge's `route_to`; the lattice is **conservative** — only a standalone preposition→genitive resolves (and only when
the ending is confirmed), PP-attachment stays unresolved, iḍāfa keeps ṣifa/badal alternatives, a coordinating wāw is
headless. "Prefer phrase-aware pending over a wrong one-word gloss."

| dependency edge / governor class | route to |
|---|---|
| `jar_majrur` (preposition governs the genitive) | `nahw/procedures/idafa-jar-majrur.md` |
| `idafa_dependent` (muḍāf ilayh candidate — kept ambiguous) | `nahw/procedures/idafa-jar-majrur.md` |
| `pp_attachment` (which head the PP attaches to — **unresolved**) | `nahw/procedures/pp-attachment-review.md` |
| `coordination` (headless wāw) | `nahw/procedures/particle-decision.md` |
| `governor_not_justified` (case asserted, governor absent/wrong — **right answer, wrong reason**) | `nahw/procedures/irab-case-mood.md` — **scholar/iʿrāb (two-vote+) review** |

`governor_not_justified` is in `fusha_check.IRAB_SENSITIVE_ISSUE_CLASSES`; a correct ending without a justified governor
is unsafe and never `auto_safe`. Learner feedback: show the segment, name the governing element (ʿāmil), explain the
case it assigns, and — when the governor is not determinable — explain why the row stays pending.

## P2: cross-builder conflict → route

When two builders disagree (`tools/fusha_conflicts.py`), the conflict record carries its own `route_to`. P2 **surfaces**
the conflict and routes it; it never silently picks a side. Precedence: source-addressed certainty > heuristic ;
cert-validator gate > candidate gate ; deterministic verdict > suggestion ; qg-palette enum > segment-role ; source-clean
public_boundary > internal evidence. `gate_required = max(both readings)`; a conflict is never `auto_safe`. Full design:
`parserplans/general-fusha-grammar-checker-p2/{002,006}`; bridge: `qamus/reports/p2-deepening.md`.

## P2b: morphology candidate lattice → route

The morphology candidate lattice (`tools/fusha_morphology_lattice.py`) populates `morphology_candidates[]` with the competing
out-of-context readings of a token, RANKED (`score` + `rank`), never collapsed to one parse for unvoweled Arabic. A tutor uses
the candidate's `evidence_class` to route; `>1` candidate keeps the token `pending`.

| morphology evidence_class | route to |
|---|---|
| `unvoweled_competing` / `homograph_split` (≥2 readings kept) | `sarf/procedures/homograph-risk.md` + `curriculum/drills/root-pattern-practice.md` (keep all readings; never force one) |
| `voweled_confirmable` / `source_addressed_confirmable` | the chosen reading may be taught; confirm against the source before asserting case/mood |
| `weak_root_gated` | `sarf/procedures/weak-root.md` / `hamza-root.md` |
| `component_only` (a lone clitic, not a whole-token reading) | `sarf/procedures/clitic-and-host-morphology.md` — a repair candidate, never a certification |

## P2b: suggestion / correction → route

The suggestion engine (`tools/fusha_suggest.py`) is **abstain-first** and never overcorrects. Edit ops: INSERT/DELETE/REPLACE/
MERGE/SPLIT (applicable) and RETAIN/REJECT/ABSTAIN (no replacement; reject/abstain carry a closed `reject_reason`). Structural and
iʿrāb-sensitive edits are never `auto_safe`; overlapping edits are NMS-resolved and surfaced as a C10 conflict.

| suggestion outcome | route to |
|---|---|
| `abstain` (`ambiguous_unvoweled` / `needs_context`) | keep the input unchanged; route to the diagnostic's own procedure |
| `reject` (`governor_not_justified`) | `nahw/procedures/irab-case-mood.md` — **scholar/iʿrāb review** (right answer, wrong reason) |
| `reject` (`nms_suppressed_conflict`) | the C10 conflict record (`tools/fusha_conflicts.py`); the winner is shown, the loser surfaced |
| `split` / `merge` (clitic spacing) | `sarf/procedures/clitic-and-host-morphology.md` — shown as a review hint, not applied |
| `retain` | no change; the token reads acceptably |

## P2b: learner-feedback hint ladder (by Knowledge Component)

The hint ladder (`tools/fusha_learner_feedback.py` + `curriculum/kc-catalog.json`) maps a diagnostic to a Knowledge Component and
a **Point → Teach → Bottom-out** ladder. **Bottom-out is WITHHELD** unless `gate==auto_safe ∧ decision_status==resolved ∧
right_answer_wrong_reason_marker==false` — so in arbitrary mode it is always withheld and the event routes to review. Teach for an
iʿrāb-sensitive class must reference the **cause** (the governor), not the symptom.

| KC (`kc_id`) | covers diagnostic class(es) | sarf/nahw route | cefr_band |
|---|---|---|---|
| `kc-clitic-segmentation` | `possible_clitic_segmentation`, `possible_definite_article` | `sarf/procedures/clitic-and-host-morphology.md` | A2 |
| `kc-attached-pronoun` | `possible_attached_pronoun` | `sarf/procedures/suffix-pronoun-state.md` | A2 |
| `kc-unvoweled-homograph` | `ambiguous_unvoweled_token` | `sarf/procedures/homograph-risk.md` | B1 |
| `kc-particle-function` | `possible_particle_function`, `ma_function_unresolved_or_wrong` | `nahw/procedures/particle-decision.md` | B1 |
| `kc-preposition-host` | `possible_preposition_host`, `host_only_preposition_hover` | `nahw/procedures/preposition-pronoun.md` | B1 |
| `kc-case-mood-context` | `possible_case_or_mood_requires_context` | `nahw/procedures/irab-case-mood.md` | C1 |
| `kc-governor-justification` | `possible_governor_unresolved`, `governor_not_justified`, `weak_irab_reasoning` | `nahw/procedures/irab-case-mood.md` — **scholar/two-vote** | C1 |
| `kc-orthography` | `orthography_normalization_warning` | `sarf/procedures/hamza-root.md` | A1 |

## P2b: CEFR-aligned instruction level → display gating

The CEFR layer (`curriculum/cefr-fusha-instruction.md` + `cefr-fusha-levels.json` + `tools/fusha_cefr_gate.py`) is **scaffolding,
not certification.** For a **caller-supplied** level it gates *display* — diagnostic visibility, metalanguage exposure, correction
aggressiveness, hint depth, example difficulty. It NEVER lowers a gate, forces a parse, reveals a withheld Bottom-out, or asserts a
learner's level. Beginner bands (`pre_A1/A1/A2`) carry no iʿrāb-sensitive diagnostic and no heavy metalanguage. Full design:
`parserplans/general-fusha-grammar-checker-p2b-learning-cefr/{004,005,009}`.
