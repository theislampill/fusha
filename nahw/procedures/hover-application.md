# Procedure — apply a hover decision (syntax-sensitive tokens)

**Invoke when:** a token's correct gloss depends on its syntactic role/context (case, mood, negation scope,
construct boundary, referent) — i.e. the surface alone underdetermines the English. The naḥw mirror of
[`../../sarf/procedures/hover-application.md`](../../sarf/procedures/hover-application.md), which handles
form/voice/person.

**Input:** the `norm_strict` key (the live hover key — keeps ال + skeleton + hamza seat, drops harakāt), the
vocalized surface, the governing element, and the candidate glosses with their proposed reason.

**Checks** (ordered evidence ladder — **stop at the first that certifies**):
1. **Does the syntax actually move the gloss?** If case only fixes the *role* and the lexeme's English is
   unchanged (rafʿ vs naṣb of عَلِيمٌ), the hover gloss is stable → author the lexeme gloss.
   ([`irab-case-mood.md`](irab-case-mood.md).)
2. **Is the governor present and decisive?** A certified mood→tense flip (لَمْ يَلِدْ → "did not beget"), a
   resolved negation scope, or a resolved construct relationship is applied as the *precise* gloss
   ([`negation.md`](negation.md), [`idafa-jar-majrur.md`](idafa-jar-majrur.md)).
3. **Is the live key safe?** The gloss fires on every token sharing the `norm_strict` key — safe only if every
   same-key surface is the same word/POS/person. A key that mixes meanings → pending, never a surface gloss.
4. **Does it survive the two-vote gate?** iʿrāb / case-mood / istithnāʾ / لا النافية للجنس / ambiguous
   iḍāfa-jar-majrūr / referent-sensitive decisions are `never_auto`; two independent checks must agree on
   conclusion AND reason ([`../rules/irab-safety-gates.json`](../rules/irab-safety-gates.json),
   [`grammar-risk-gate.md`](grammar-risk-gate.md)).

**Evidence-ladder rule:** when role/context is undetermined, **mark pending with a precise reason — never a
one-word gloss.** A confident single word on a syntax-dependent token is the failure mode the gate exists to
catch; "pending(case_or_mood)" is a correct, shippable state, "ordains" on a contronym is not.

**Output object fields:** `loc`, `surface`, `norm_strict`, `candidate_glosses`, `contextual_choice` (or null),
`decision` (resolved|pending), `pending_reason` (precise: `case_or_mood` | `negation_scope` |
`idafa_ambiguous` | `jar_majrur_ambiguous` | `nafy_lil_jins` | `istithna` | `referent_sensitive` |
`norm_strict_collision`), `gate`, `reasoning`, `confidence`. Public record is exactly
`{src:"qamus",kind:"authored",lang:"en"}`.

**Forbidden shortcuts:** emitting a one-word gloss on a token whose role is unresolved; applying a surface gloss
on a `norm_strict` key that mixes meanings; gating a case/mood/referent decision below `two_vote_required`;
hand-editing the runtime lookup (the live apply path is `rebuild.sh`, not an artifact edit — see the sarf mirror).

**Regression guard:** for function-word entries, never let the governed content word erase the function word. A
بِـ entry example like بِسَلَـٰمٍ needs the bāʾ sense plus the host ("with peace"), and a locative bāʾ example like
بِبَدْرٍ needs the place reading ("at Badr"). Likewise `وَمَا` must be read as wāw + mā in context, even though it
remains one word token in the Qur'anic word count.

**Source-triangulation guard:** source agreement is necessary but not sufficient. Bind external word evidence by a
unique Arabic surface match inside the ayah, not by the Qamus token loc alone. If the source morphology has a
preposition segment but the agreed English omits it (for example بِكُم glossed only as "you"), mark the token
pending until the jar-majrūr role is authored.

**Example 1 (apply a resolved flip):** لَمْ يَلِدْ — governor لَمْ + jazm certified (two votes agree). Apply the
precise gloss "did not beget" to that slot; **do not** ship the surface "begets". Resolved, hover updated.

**Example 2 (mark pending, not a word):** أَن لَّا مَلْجَأَ — لَّا could be verbal "did not" or لا النافية للجنس
"(there is) no", and the reading depends on the governed noun's state. The token is syntax-sensitive and the
gate is `never_auto` → emit `decision:"pending", pending_reason:"nafy_lil_jins"` with the reason recorded —
**not** the one-word guess "no". The token renders plain until two votes certify the construction.

**Test:** `tools/validate_linguistic_decisions.py --self-test` (rejects a one-word gloss on a below-gate
syntax-sensitive token; rejects provenance leak); `tools/check_regressions.py` (pending propagation on
case_or_mood / nafy_lil_jins); fixture
[`../examples/ayah-context-decisions.jsonl`](../examples/ayah-context-decisions.jsonl) (the لَّا pending row).

**Feeds:**
- **→ /qamus/ entry authoring:** a resolved syntactic role files the citation under the right sense/usage; a
  pending token tells the editor a sense still needs context before it can anchor an example āya.
- **→ hover-gloss resolution:** resolved tokens apply the precise context gloss live; pending tokens render plain
  (no half-right one-word gloss leaks), exactly as the sarf
  [`hover-application.md`](../../sarf/procedures/hover-application.md) apply gates govern form/voice/person.
- **→ ajami learners:** models the discipline of *withholding* a gloss until the syntax is certified — teaching
  that "I cannot yet say" is a real, honest answer for a context-dependent word, not a gap to paper over.
