# Procedure — hamza as a radical & hamza seat (المهموز)

**Invoke when:** a radical is ء (initial أ/آ, medial ؤ/ئ/ء, final أ/ئ/ء), or you must choose/validate the hamza
**seat** (ء أ إ ؤ ئ ا) on an authored surface.

**Input:** surface (with diacritics if available), optional QAC root/POS, optional Qamus entry candidates.

**Checks (in order — stop at the first that certifies):**
1. **Qamus entry** root for this surface/form — highest authority; the hamza radical + seat are fixed in the entry.
2. **QAC** root for this token position (`(ref, norm_strict)`) — `norm_strict` KEEPS the seat, so it carries the
   hamza radical as real evidence (internal).
3. **Seat by position rule** (orthography, for authoring an example):
   - initial hamza rides ا → أَ / إِ / آ (madd when أَ + ʾalif: أَأْ → آ).
   - medial/final seat follows the stronger of the adjacent vowels (kasra→ئ, ḍamma→ؤ, fatḥa/sukūn→أ, after ا/long
     vowel→ء).
4. external reference triangulation (internal only).
5. heuristic (`normalize_ar`) — **never sufficient alone.**

**Evidence-ladder rule:** `norm()` **collapses hamza** — it deletes أ/إ/ء and maps ؤ→و, ئ→ي. So under `norm()`
the hamza radical vanishes: **إيمان and أيمان share the same `norm()` key** though they are different words. `norm()`
is therefore recall-only for any hamza surface. Certify with `norm_strict` (which keeps the seat) + QAC, never the
lenient key.

**Output:** `candidate_root` (with the hamza radical placed: أ ك ل, س أ ل, ق ر أ), `hamza_position`
(`C1`/`C2`/`C3`), `seat` (the orthographic form on the authored surface), the rung used, `confidence`. If the seat
or the hamza-radical reading cannot be certified → **pending** (`hamza_sensitive_homograph`).

**Forbidden:** inferring a hamza root from `norm()` (the إيمان≠أيمان regression); altering a seat on Qurʾān text;
asserting a hamza radical by subsequence match. Gate per [`../rules/hamza-gates.json`](../rules/hamza-gates.json) —
two-vote when the seat is meaning-bearing, never-auto when only `norm()` ties.

**Example — initial-hamza radical:** أَكَلَ "he ate" → C1 is the hamza → root **أ ك ل**. Under `norm()` the أ is
dropped (key "كل"), which would wrongly tie it to كُلّ / كَلَّا; only `norm_strict` (key keeps أ) + QAC certifies it.

**Example — madd contraction:** آمَنَ "he believed" is Form IV of **أ م ن**, where the underlying أَأْمَنَ contracts
أَ + hamza into the madd آ. The headword root is **أ م ن**, not a hollow ا — recover the hamza radical, do not read
آ as a long vowel. (Its maṣdar إِيمان keeps the same C1 hamza, written under a kasra seat إ.)

**Example — medial / final hamza:** سَأَلَ "he asked" → C2 hamza, seat أ → root **س أ ل**. قَرَأَ "he read/recited"
→ C3 hamza, seat أ (after fatḥa) → root **ق ر أ**; its maṣdar قُرْآن places the same C3 hamza on a madd.

**Test:** `tools/check_regressions.py` (the `إيمان ≠ أيمان` invariant, hamza-seat homographs); fixtures
`examples/root-form-decisions.jsonl`.

**Feeds:**
- **/qamus/ entry authoring:** supplies the hamza radical + seat so the entry files under the correct headword
  (أَكَلَ under أ ك ل, سَأَلَ under س أ ل) and the vocalized `usage[]` forms carry the right seat.
- **hover-gloss resolution:** forces `qamus-highlight` to key hamza surfaces on `norm_strict`/QAC, never `norm()`,
  so إيمان and أيمان never collide on one gloss; an uncertain seat emits `pending` instead of guessing.
- **ʿajamī learners:** teaches that the hamza is a full consonant radical (not decoration) and that its seat
  ء/أ/إ/ؤ/ئ is rule-governed by the surrounding vowels — making أَكَلَ، سَأَلَ، قَرَأَ recognizable as a single class.
