# Tutor-runtime routing (closure-2092 Phase 7/12)

A thin routing layer (NOT a separate skill): map a learner's situation to the exact existing procedure,
roadmap section, or drill. The engine is already `sarf` + `nahw` + `curriculum`; this is the dispatcher.

## Learner mistake → sarf/nahw procedure

| learner error | route to |
|---|---|
| wrong/guessed root from the bare consonants | `sarf/procedures/root-decision.md` (evidence ladder; never from `norm()` alone) |
| confused verb form / tense / voice (I vs II vs IV; active vs passive) | `sarf/procedures/verb-form.md` |
| missed a weak/hamza/doubled radical | `sarf/procedures/weak-root.md` / `hamza-root.md` / `doubled-root.md` |
| put a verb gloss on a noun / participle / maṣdar | `sarf/procedures/masdar-participle.md` + sarf principle 3 (POS mismatch is a blocker) |
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
| missed negation/mood effect (لم + jussive → past) | `nahw/procedures/negation.md` / `irab-case-mood.md` |
| missed governing-particle mood (lan/lam/lām/causal fā'/prohibition lā) | `nahw/procedures/governing-particle-mood-review.md` |
| wrong iḍāfa / jar-majrūr wording | `nahw/procedures/idafa-jar-majrur.md` |
| carried a referent across (divine Name vs attribute, Prophet vs adjective) | `nahw/procedures/referent-context.md` |
| used QAC concept membership as a translation | `qamus/procedures/grammar-resource-usage.md` + `curriculum/drills/hover-composition-and-routing.md` |
| confused named entity with common lexical meaning | concept-map flag internally, then `sarf/procedures/proper-noun.md` and verse-specific nahw/i'rab |

## Situation → curriculum

| situation | route to |
|---|---|
| new learner, unknown level | `curriculum/placement-test.md` → `zero-to-fluency-roadmap.md` |
| wants the path end-to-end | `curriculum/zero-to-fluency-roadmap.md` (12-level ladder) |
| wants practice from real Qurʾān | `curriculum/qamus-driven-fluency-engine.md` (Qamus examples → drills) |
| keeps losing attached pieces inside one written token | `curriculum/drills/hover-composition-and-routing.md` |
| checking mastery before advancing | `curriculum/mastery-checkpoints.md` |
| right answer but shaky reasoning | the GrammarProblems gate (`nahw/SKILL.md` §grammar-safety) — a correct answer with wrong iʿrāb is unsafe |

## Discipline

- Blank beats wrong: if the learner (or you) cannot certify the root + POS + sense, mark it **pending**
  with the exact blocker, then route to the procedure that resolves that blocker.
- Production/speaking practice and answer-keys live in the curriculum drills; this file only routes to them.
