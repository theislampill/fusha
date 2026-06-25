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
| read a proper noun as a common verb | `sarf/procedures/proper-noun.md` |
| collapsed a homograph (مَن/مِن، لَمْ/لِمَ، الملك) | `sarf/procedures/homograph-risk.md` + `nahw/procedures/particle-decision.md` |
| wrong particle function | `nahw/procedures/particle-decision.md` |
| mis-rendered preposition+pronoun (إِلَيْنَا as a root) | `nahw/procedures/preposition-pronoun.md` |
| missed negation/mood effect (لم + jussive → past) | `nahw/procedures/negation.md` / `irab-case-mood.md` |
| wrong iḍāfa / jar-majrūr wording | `nahw/procedures/idafa-jar-majrur.md` |
| carried a referent across (divine Name vs attribute, Prophet vs adjective) | `nahw/procedures/referent-context.md` |

## Situation → curriculum

| situation | route to |
|---|---|
| new learner, unknown level | `curriculum/placement-test.md` → `zero-to-fluency-roadmap.md` |
| wants the path end-to-end | `curriculum/zero-to-fluency-roadmap.md` (12-level ladder) |
| wants practice from real Qurʾān | `curriculum/qamus-driven-fluency-engine.md` (Qamus examples → drills) |
| checking mastery before advancing | `curriculum/mastery-checkpoints.md` |
| right answer but shaky reasoning | the GrammarProblems gate (`nahw/SKILL.md` §grammar-safety) — a correct answer with wrong iʿrāb is unsafe |

## Discipline

- Blank beats wrong: if the learner (or you) cannot certify the root + POS + sense, mark it **pending**
  with the exact blocker, then route to the procedure that resolves that blocker.
- Production/speaking practice and answer-keys live in the curriculum drills; this file only routes to them.
