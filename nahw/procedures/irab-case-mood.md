# Procedure — read iʿrāb (case & mood)

**Invoke when:** a gloss or tense depends on the token's case (رفع/نصب/جر) or mood (رفع/نصب/جزم).

**Input:** surface (with diacritics), the governing word/particle before it, and the role slot the token fills.

**Checks** (ordered evidence ladder — **stop at the first that certifies**; consult
[`../references/irab-case-mood.md`](../references/irab-case-mood.md)):
1. **Is it mabnī?** Particles, most pronouns, demonstratives, relatives carry a *fixed* ending — not iʿrāb. The
   ـنا of إِلَيْنَا and the ـكُمْ of عَلَيْكُمْ are pronouns, never case markers or root letters. If mabnī, the
   ending decides nothing → resolve by function, not by vowel.
2. **Mood on a present verb (tense-flipping):** read the governing particle, not the surface form.
   لَمْ + jazm → PAST negation (لَمْ يَلِدْ = "did not beget"); لَنْ + naṣb → categorical FUTURE ("will never");
   أَنْ/كَيْ/حَتَّى + naṣb → "(that) he do". The mood overrides the present surface
   ([`../rules/negation-rules.json`](../rules/negation-rules.json), [`negation.md`](negation.md)).
3. **Case on a noun:** the ending fixes the role but **not** the lexeme's gloss — رفع → subject/predicate ("the
   doer / the topic"), نصب → object/ḥāl/tamyīz ("the done-to / as a …"), جر → after a preposition or as مضاف
   إليه ("of …"). Quarantine the whole inflection family together (عَلِيمٌ and عَلِيمًا are one word).
4. **Is the decisive vowel actually present?** If the ending that would settle role/tense is unwritten and the
   reading turns on it → do not pick the commoner reading → **pending**.

**Evidence-ladder rule:** a case/mood claim certifies only when the governing element *and* the ending agree; a
bare final vowel with no licensing governor is not proof. Surface confidence is never evidence.

**Output object fields:** `loc`, `surface`, `irab` (`case` ∈ rafʿ|naṣb|jarr or `mood` ∈ rafʿ|naṣb|jazm or
`mabni`), `governor` (the word/particle that assigns it), `role`, `gloss_effect` (tense/polarity/role wording),
`decision` (resolved|pending), `gate`, `reasoning`, `pending_reason` (if pending).
Public record stays exactly `{src:"qamus",kind:"authored",lang:"en"}` — the matrix/study is internal evidence only.

**Forbidden shortcuts:** asserting a case/mood from the surface vowel without naming the governor; letting an
ambiguous ending pick the commoner reading; reading a fixed pronoun/particle vowel as a case marker; shipping a
case/mood decision on the answer alone — a correct gloss with wrong iʿrāb reasoning is unsafe and must be rejected.

**Why two votes:** iʿrāb assignment and mood→tense flips are the GrammarProblems study's worst area (signs of
iʿrāb; building of the present verb — جزم/نصب of the muḍāriʿ). LLM self-assurance collapses exactly here, so any
case/mood-affecting decision is **`two_vote_required`, hover `never_auto`** (mood-tense flips may be
`pending_if_reason_uncertain`) — two independent checks must agree on **conclusion AND reason**
([`../rules/irab-safety-gates.json`](../rules/irab-safety-gates.json) `irab_assignment` / `mood_tense_flip`;
[`grammar-risk-gate.md`](grammar-risk-gate.md)).

**Example 1 (mood flips tense):** لَمْ يَلِدْ وَلَمْ يُولَدْ — يَلِدْ is a present *form* in the jazm under لَمْ;
the governor forces past negation, so the gloss is "He did **not** beget" (not "does not beget"). Vote-A: لَمْ
governs jazm → past negation. Vote-B: sukūn on the lām confirms jazm, voice of يُولَدْ is passive ("was begotten").
Both agree on conclusion and reason → certified.

**Example 2 (case fixes role, not lexeme):** إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ — غَفُورٌ in rafʿ is the khabar
("All-Forgiving" as predicate); the same word in naṣb (غَفُورًا) elsewhere is the same lexeme in object/ḥāl
position. Gloss the lexeme once, quarantine both endings together; the case never rewrites the English meaning,
only the syntactic slot.

**Test:** `tools/check_regressions.py` (لَمْ/jussive past-flip, لَنْ future, عَلِيمٌ↔عَلِيمًا family quarantine);
`tools/validate_linguistic_decisions.py --self-test` (rejects a case/mood decision gated below `two_vote_required`
or lacking reasoning); fixtures in [`../examples/ayah-context-decisions.jsonl`](../examples/ayah-context-decisions.jsonl).

**Feeds:**
- **→ /qamus/ entry authoring:** the case/mood read tells the entry which form is being cited and in what role, so
  the `usage[]` form + example āya are filed under the right sense (subject vs object, past vs future) instead of a
  bare surface.
- **→ hover-gloss resolution:** a certified mood→tense flip rewrites the live gloss ("did not beget"), and an
  uncertain ending returns pending instead of the commoner reading — see [`hover-application.md`](hover-application.md).
- **→ ajami learners:** shows the beginner that the *ending and its governor*, not the verb's surface tense, set
  the English — the single highest-leverage naḥw habit the study found general models lack.
