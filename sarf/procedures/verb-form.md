# Procedure — verb form / voice

**Invoke when:** the surface is (or might be) a verb, before glossing.

**Input:** surface, root, optional QAC POS.

**Checks:**
1. Identify the measure (I–X) from the wazn — [`../rules/verb-measures.json`](../rules/verb-measures.json),
   [`../references/verb-measures-table.md`](../references/verb-measures-table.md). The shadda (II), hamza (IV),
   اِسْتَ‑ (X), اِن‑ (VII), infixed‑ت (VIII) each select a DIFFERENT verb — never the Form I sense.
2. Voice: ḍamma–kasra signature → passive ("was created" خُلِقَ ≠ خَلَقَ).
3. Person/number/gender of the conjugation → finite English (قَالُوا "they said", قَالَتْ "she said",
   ءَامَنُوا "they believed"), never a bare infinitive.
4. Governing negative flips tense: لَمْ + jussive → PAST; لَنْ + subjunctive → future ([`../../nahw/rules/negation-rules.json`](../../nahw/rules/negation-rules.json)).

**Output:** `form`, `voice`, `person_number_gender`, gloss with finite wording.

**Forbidden:** Form I gloss on a derived form; active gloss on a passive; bare infinitive on a conjugated verb;
gating below `two_vote` for an iʿrāb/voice-sensitive case ([`../rules/verb-measure-gates.json`](../rules/verb-measure-gates.json)).

**Test:** `examples/verb-measure-examples.jsonl`; regression checks for أَنزَلَ(IV)≠نَزَلَ(I), نَزَّلَ(II) shadda.
