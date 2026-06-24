# Procedure — nahw evidence → Qamus entry (particles & constructions)

**Invoke when:** authoring or repairing a Qamus entry whose headword is a function word (particle, preposition,
pronoun) or a construction (iḍāfa, jar-majrūr, ẓarf phrase) — i.e. an entry where the *sense lives in the syntax*,
not in a triliteral root.

**Input:** the proposed headword (vowelized) + POS class · the nahw output object for each cited token
([`../SKILL.md`](../SKILL.md) §3: `quran_ref`, `syntactic_role`, `governing_particle`, `case_or_mood_signal`,
`contextual_choice`, `decision`) · the candidate example āyāt (source addresses only, internal) · any existing
Qamus entry to repair.

**Checks (ordered evidence ladder — stop at the first rung that certifies the function):**
1. **Closed-set certainty.** Is the headword a member of a closed particle/preposition/pronoun inventory
   ([`../references/particles.md`](../references/particles.md))? If yes, the *function* is fixed by membership +
   content-letter harakah ([`particle-decision.md`](particle-decision.md)) — author the function gloss, not a
   lexical one. Stop.
2. **Construction rule.** Is the headword a construct head (iḍāfa) or a jar-majrūr phrase? Apply
   [`idafa-jar-majrur.md`](idafa-jar-majrur.md): the sense is the *relationship + definiteness from the second
   term*, not the bare head. Stop once the construct rule certifies.
3. **Governing-context fix.** Does a governing particle / case-mood signal pick one of several functions
   (مَا negation vs relative; لَا verbal vs لا النافية للجنس)? Use [`negation.md`](negation.md) +
   [`referent-context.md`](referent-context.md). Stop only if the governor uniquely fixes it.
4. **Two-vote.** Anything iʿrāb-dependent, multi-function, or referent-sensitive — two independent checks must
   agree on *conclusion AND reasoning* ([`grammar-risk-gate.md`](grammar-risk-gate.md)). No agreement → pending.

**Evidence-ladder rule:** stop at the first rung that certifies the function; never skip a rung to reach a
gloss. A particle whose content-letter harakah is unread, or a construct whose second term is out of range, has
**not** been certified — it is pending, never a guess.

**Output object fields (candidate entry — JSONL, never live):**
`headword_ar` (vowelized) · `translit` · `pos` (`particle | preposition | pronoun | construction`) ·
`function_en` (the original English rendering of the function in context) · `senses[]` (each: `gloss_en`,
`trigger` — the harakah / governor / construct that selects it) · `usage[]` (each: `surface_ar` vowelized,
`quran_ref` as `surah:ayah`, `role`, `gloss_en`) · `notes` (teacher note for the ʿajamī learner) ·
`gate` (`auto_safe | two_vote_required | human_source_review_required`) · `grammar_triggers[]` · `reasoning` ·
`src:"qamus"` · `kind:"authored"` · `lang:"en"` · `decision:"candidate"`.

**Forbidden shortcuts:**
- Authoring a **lexical** gloss for a function word (مِنْ is "from / among", never the root م-ن-ن).
- Glossing a construct head as bare/indefinite when the second term makes it definite
  (بَيْتُ ٱللَّهِ = "the House of Allah", not "a house").
- Letting an attached pronoun invent a stem (إِلَيْنَا = إِلَى + نا, **not** root ل-ي-ن).
- Marking a two-vote/iʿrāb entry exportable without `reasoning`, or gating below the trigger tier.
- Exposing any external corpus/source name in the record — internal evidence only.

**Example 1 — preposition entry (closed-set, rung 1).**
Headword عِنْدَ. Cited token عِنْدَ ٱللَّهِ at `3:19`. Rung 1: closed ẓarf/preposition → function is fixed. But
rung 2 also fires (it heads an iḍāfa of place): the construct sense is "in the sight of / with", definiteness
from ٱللَّهِ. Candidate entry: `function_en:"with / in the sight of"`,
`senses:[{gloss_en:"in the sight of", trigger:"iḍāfa head + divine second term"},{gloss_en:"in the possession of", trigger:"iḍāfa with a possessor"}]`,
`usage:[{surface_ar:"عِنْدَ ٱللَّهِ", quran_ref:"3:19", role:"jar-majrūr/iḍāfa", gloss_en:"in the sight of Allah"}]`,
`gate:"two_vote_required"` (referent-sensitive construct), `reasoning:"ẓarf heading iḍāfa; sense + definiteness from the divine مضاف إليه, not the bare adverb"`.

**Example 2 — multi-function particle entry (stops at rung 4 → pending sense).**
Headword مَا. Rung 1 says closed-set, but مَا is *multi-function* (negation / relative / interrogative /
maṣdariyyah). No single content-letter harakah resolves it; rung 3 (governor) varies per āyah. So the entry is
authored with **one sense per function, each carrying its own trigger**, and any āyah whose function is
unresolved stays pending: `senses:[{gloss_en:"not", trigger:"مَا + perfect verb (negation)"},{gloss_en:"that which / what", trigger:"relative, with a ṣilah clause"},{gloss_en:"what?", trigger:"interrogative head"}]`,
`gate:"two_vote_required"`, `grammar_triggers:["multi_function_particle"]`. A bare default "not" is forbidden.

**Test:** [`../examples/function-word-decisions.jsonl`](../examples/function-word-decisions.jsonl) (particle &
jar-majrūr cases) and [`../examples/ayah-context-decisions.jsonl`](../examples/ayah-context-decisions.jsonl)
(construct + لا النافية للجنس); enforced by `tools/validate_linguistic_decisions.py` (gate ≥ triggers, reasoning
present, public record exactly `{src:"qamus",kind:"authored",lang:"en"}`) and `tools/check_regressions.py`
(مَن/مِن، إِلَيْنَا≠لين، عِنْدَ construct).

**Feeds:**
- *Qamus entry authoring* — yields a ready candidate object (headword + function senses + construct-aware usage)
  the curator can promote into a `/qamus/` entry; see the sarf half [`../../sarf/procedures/corpus-to-qamus.md`](../../sarf/procedures/corpus-to-qamus.md).
- *Hover-gloss resolution* — each certified `senses[].trigger` + `usage[]` exports a surface-keyed candidate for
  the live key path ([`../../sarf/procedures/hover-application.md`](../../sarf/procedures/hover-application.md)),
  so عِنْدَ/بِهِ/وَمِنَ resolve in context instead of pending.
- *Teaching the ʿajamī learner* — the `function_en` + `notes` + worked construct examples give a non-native a
  plain-English "what this word *does* in the sentence", the gap a root-only dictionary leaves open.
