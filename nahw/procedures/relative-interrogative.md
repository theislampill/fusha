# Procedure — relative vs interrogative (vs negation)

**Invoke when:** the token is مَا, مَن, or أَيّ and could be a relative, an interrogative, or (for مَا) a negation.

**Input:** surface (with diacritics), the immediately governing/following token, the clause it sits in.

**Why this is a particle-sense collision:** norm() folds مَا and مَن each into ONE undiacritized key, but each key carries
≥2 unrelated function-senses that no harakah separates — مَا is "what / which (relative)", "what? (interrogative)",
"not (negation)", and "[verbal-noun] that (maṣdariyyah)"; مَن is "who / whoever (relative)" and "who? (interrogative)".
A single key therefore cannot certify a gloss the way مَن/مِن can (which the **content-letter harakah** decides —
see [`particle-decision.md`](particle-decision.md)). Here the diacritics are identical across senses, so **only the
syntactic context decides**. A keyed default ("مَا" → "what", "مَن" → "who") is the failure this procedure exists to
block. PENDING beats a wrong gloss.

**Checks** (ordered evidence ladder — **stop at the first rung that certifies**), per
[`../rules/context-sense-rules.json`](../rules/context-sense-rules.json):
1. **Interrogative test** — does the clause ask a question (head of the sentence, often with a verb of saying, or a
   bare nominal question)? مَاذَا / مَا هَٰذَا / مَن ذَا → interrogative ("what / who"). Stop → resolved.
2. **Negation test (مَا only)** — does مَا directly precede a **past verb** or a **nominal predicate** that it negates
   (مَا كَانَ، مَا أَنتَ)? Then مَا = "not / is not", not relative. Stop → resolved(negation), then hand the polarity to
   [`negation.md`](negation.md).
3. **Relative test** — is the token a **substantive head** (subject/object, often after a preposition: لِمَن، بِمَا،
   فِيمَا) followed by a clause that describes it ("that which / whoever")? Stop → resolved(relative).
4. **أَيّ test** — أَيّ in iḍāfa + a question frame = "which (of) …?"; أَيّ as a relative/conditional head = "whichever";
   vocative أَيُّهَا = the call particle "O …", not a question. Pick by the construct it heads.
5. **No rung certifies** → `pending`.

**Evidence-ladder rule:** take the gloss from the **first** rung that fires and stop; do not average senses or let a
lower rung override a higher one. If two rungs seem to fire (e.g. an embedded question that is also relative), that is
not certification → drop to `pending`. The diacritics never break the tie here — never "resolve" on the harakah.

**Output object fields:**
- `surface` — the diacritized token.
- `function` — one of `relative` | `interrogative` | `negation` | `vocative` (أَيّ).
- `gloss` — "that which / whoever" | "what? / who? / which?" | "not / is not" | "O …".
- `decision` — `resolved` | `pending`.
- `reason` — which ladder rung fired and the context token that fired it.
- `reason_code` — `particle_sense_collision` (when pending on مَا/مَن) | `context_sensitive_needs_nahw`.
- `gate` — `two_vote` whenever مَا's negation reading is in play or the rungs conflict (`grammar-risk-gate.md`).

**Forbidden shortcuts:** keying مَا → "what" or مَن → "who" with no rung fired; resolving on the harakah (it does not
separate these senses); collapsing a relative مَا into the negation مَا (or vice-versa) without rung 2/3; treating
أَيُّهَا as a question. A particle never takes a content-verb/noun gloss.

**Worked examples (vowelized):**
- `مَنْ آمَنَ بِاللَّهِ` — مَنْ heads a substantive followed by a describing clause → rung 3 **relative**, gloss
  "whoever / he who believes". (Compare وَمِنَ in `مِنَ النَّاسِ` — that is the preposition مِنْ, decided by the kasra on
  the mīm, a *different* procedure: [`particle-decision.md`](particle-decision.md).)
- `مَا هَٰذَا بَشَرًا` — مَا precedes a nominal predicate it negates → rung 2 **negation**, gloss "this is **not** a
  human"; do **not** gloss "what". Polarity goes to [`negation.md`](negation.md).
- `مَا تِلْكَ بِيَمِينِكَ` — مَا heads a bare nominal question → rung 1 **interrogative**, gloss "**what** is that in your
  right hand?".
- `بِمَا كَانُوا يَكْذِبُونَ` — مَا after the preposition بـ, heading a clause → rung 3 **relative/maṣdariyyah**, gloss
  "for **that which** / because they used to lie". The بـ proclitic is the relative signal, not a key default.

**Test:** `examples/ayah-context-decisions.jsonl` (مَنْ relative vs مِنْ preposition rows) and
`examples/function-word-decisions.jsonl` (مَن / مِن); `tools/check_regressions.py` asserts مَا/مَن never resolve on the
key alone (must carry a fired rung or stay `pending`).

**Feeds:**
- **/qamus/ entry authoring** — a مَا/مَن occurrence is tagged with its certified `function` so the entry lists the
  relative, interrogative, and negation uses as *distinct senses*, each cited to the āyah where its rung fired —
  never one blended "what/who" gloss; src:"qamus", kind:"authored".
- **hover-gloss resolution** — the hover plaque shows the rung-certified sense ("whoever" / "what?" / "not"); when no
  rung fires it shows the plain word with no gloss rather than a guessed default, so a relative مَا is never mislabelled
  "not".
- **ajami learners** — teaches the reader to *look right* of مَا/مَن (what governs and what follows) instead of reaching
  for one English word, building the habit that closed-set words are read by their job in the sentence, not by sight.
