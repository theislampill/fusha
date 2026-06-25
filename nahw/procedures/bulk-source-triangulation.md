# Procedure — bulk source-triangulation context gate

**Invoke when:** many qamus-highlight pending rows are being classified from a source-triangulation table.

**Input:** the token row plus nearby-token/context evidence when available: particle/function flags, case or mood
signals, governing particle/preposition, referent risk, multi-sense candidates, and the proposed lane.

**Route rows before authoring:**
1. **Stable lexical rows** may pass through the sarf `auto_safe` lane only when syntax does not change the
   English and the live key is collision-free.
2. **Context-sensitive rows** require two independent checks that agree on conclusion and reason: particles,
   negation/mood, iʿrāb, iḍāfa, jar-majrūr, conditionals, relatives, contronyms, and referent-sensitive names or
   attributes. Emit a two-vote request row until the second check exists.
3. **Function-word/new-entry rows** are owner-gated if the Qamus entry itself needs a new function, usage note,
   or source-backed wording. Do not fill definition text from outside sources.
4. **Ambiguous rows** stay pending with the most specific reason (`particle_function`, `case_or_mood`,
   `idafa_ambiguous`, `jar_majrur_ambiguous`, `referent_sensitive`, `norm_strict_collision`, or
   `multi_sense_root`).

**Forbidden shortcuts:** resolving a particle by surface frequency alone; shipping a one-word gloss for an
iʿrāb-dependent token; letting an LLM's confidence stand in for two-vote reasoning; applying a gloss to a shared
`norm_strict` key that mixes meanings.

**Output fields:** `loc`, `surface`, `nearby_context` (or null), `context_trigger`, `candidate_glosses`,
`decision`, `pending_reason`, `gate`, `reasoning`, and `allowed_for_hover`.

**Test:** a bulk request is valid only if each syntax-sensitive row is either `two_vote_required` with reasoning
prompts or `pending` with a precise reason. No public hover artifact may expose `informed_by` or external source
names.
