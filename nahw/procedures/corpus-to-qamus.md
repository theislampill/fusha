# Procedure — corpus → Qamus (the nahw half)

**Invoke when:** walking a corpus token (or a Nawawī40 / catalogue surface) to assign its nahw role/state,
detect a construction, classify it for the catalogue, and emit a particle/construction **candidate** — the
syntactic counterpart to the sarf half [`../../sarf/procedures/corpus-to-qamus.md`](../../sarf/procedures/corpus-to-qamus.md).

**Input:** a token with its source address (`surah:ayah:word` or hadith ref) · the surrounding tokens · the sarf
output object if available ([`../../sarf/SKILL.md`](../../sarf/SKILL.md) §3: root, POS, form, clitics) · existing
Qamus entry candidates.

**Checks (ordered evidence ladder — stop at the first rung that certifies the role/sense):**
1. **POS gate.** Is the token a content word or a function word? If the sarf object already certified a root+POS
   for a content word, nahw only refines sense — hand back. If it is a closed-set particle/preposition/pronoun
   ([`../references/particles.md`](../references/particles.md)), continue here.
2. **Role/state assignment.** Read the content-letter harakah and the iʿrāb signal: subject/object, jar-majrūr,
   ẓarf, mubtadaʾ/khabar, governing particle ([`../references/irab-case-mood.md`](../references/irab-case-mood.md)).
   مَن(fatḥa)≠مِن(kasra); لَمْ+jussive negates the *past* ([`negation.md`](negation.md)).
3. **Construction detection.** Is the token the head of an iḍāfa, or part of a jar-majrūr phrase
   ([`idafa-jar-majrur.md`](idafa-jar-majrur.md))? If so the unit — not the bare token — is the candidate, and
   the sense is the relationship + definiteness from the second term.
4. **Referent/context guard.** Does the sense depend on who/what the āyah is about
   ([`referent-context.md`](referent-context.md))? Never carry a divine-Name / Prophet / proper-noun sense onto a
   common word, or vice-versa.
5. **Gate & classify.** Apply [`grammar-risk-gate.md`](grammar-risk-gate.md). Anything iʿrāb-dependent,
   multi-function, or referent-sensitive is `two_vote_required`; unresolved → catalogue class
   `particle_or_construction` / `uncertain_needs_review`, not a gloss.

**Evidence-ladder rule:** stop at the first rung that certifies the role; never reach a gloss by skipping a rung.
A token whose harakah is unread or whose construct second-term is out of range is **pending**, never guessed.

**Output object fields (per token — JSONL candidate, never live):**
`token_loc` (`surah:ayah:word`) · `surface_ar` (vowelized) · `pos_class` · `syntactic_role` ·
`case_or_mood` · `governing_particle` · `construction` (`none | idafa | jar_majrur | zarf_phrase`) ·
`construction_head` / `construction_tail` (when a construct) · `function_en` · `contextual_choice` ·
`catalogue_class` (`already_in_qamus | particle_or_construction | new_construction | uncertain_needs_review`) ·
`gate` · `grammar_triggers[]` · `reasoning` · `decision` (`candidate | pending`) ·
`src:"qamus"` · `kind:"authored"` · `lang:"en"`.

**Forbidden shortcuts:**
- Deciding a particle on its first letter or on `norm()` instead of the content-letter harakah.
- Glossing a construct's bare head while ignoring the second term's definiteness/relationship.
- Promoting a `two_vote_required` row to a candidate on a single check, or without `reasoning`.
- Defaulting multi-function مَا to "not", or any catalogue class to `already_in_qamus` without a matched lemma.
- Writing a live entry from this procedure — it emits candidates only; promotion is the curator's gate.
- Naming any external corpus/source in the record.

**Example 1 — jar-majrūr construction candidate.**
Token بِإِذْنِهِ at `2:255:...`. Rung 1: function word (preposition بِ + إِذْن + ـه). Rung 3: jar-majrūr phrase,
construct بِ + إِذْنِ + pronoun. Candidate:
`{surface_ar:"بِإِذْنِهِ", construction:"jar_majrur", function_en:"by His permission", contextual_choice:"by His permission", catalogue_class:"particle_or_construction", gate:"two_vote_required", grammar_triggers:["jar_majrur","referent_pronoun"], reasoning:"بِ governs majrūr إِذْن; the ـه pronoun refers to Allah → 'His', not 'its'", decision:"candidate"}`.

**Example 2 — homograph particle → pending.**
Token وَمَا at the head of a clause. Rung 2: content-letter harakah is مَا, but مَا is multi-function (negation /
relative / interrogative / maṣdariyyah) and the governor does not uniquely fix it. Rung 5: stays pending —
`{surface_ar:"وَمَا", pos_class:"particle", construction:"none", catalogue_class:"uncertain_needs_review", gate:"two_vote_required", grammar_triggers:["multi_function_particle"], reasoning:"مَا reading not fixed by governor in range; negation vs relative vs interrogative all open", decision:"pending"}`.
A surface-keyed "not" would be wrong.

**Test:** [`../examples/ayah-context-decisions.jsonl`](../examples/ayah-context-decisions.jsonl) (role/construct +
لا النافية للجنس) and [`../examples/function-word-decisions.jsonl`](../examples/function-word-decisions.jsonl)
(content-letter homographs); the pipeline tool `tools/corpus_to_hover_decisions.py` walks corpus tokens into
these candidate objects, and `tools/validate_linguistic_decisions.py` + `tools/check_regressions.py` enforce
gate ≥ triggers, present `reasoning`, and the مَن/مِن، إِلَيْنَا≠لين، عِنْدَ-construct regressions.

**Feeds:**
- *Qamus entry authoring* — `particle_or_construction` / `new_construction` candidates flow to
  [`qamus-entry-authoring.md`](qamus-entry-authoring.md) as headword+function+usage objects for curator promotion.
- *Hover-gloss resolution* — every certified `contextual_choice` exports a surface candidate for the live key
  via [`../../sarf/procedures/hover-application.md`](../../sarf/procedures/hover-application.md); pendings keep an
  honest pending reason instead of firing a wrong gloss.
- *Teaching the ʿajamī learner* — `syntactic_role` + `function_en` + the worked construct examples show a
  non-native *how the sentence holds together* (jar-majrūr, iḍāfa, negation scope), not just isolated word lists.
