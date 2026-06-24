# Procedure — doubled / geminate root (المضاعف)

**Invoke when:** the last two radicals are identical (C2 = C3) and idghām has merged them under a **shadda**, so a
triliteral root wears a two-letter skeleton (رَدَّ looks bi-consonantal).

**Input:** surface (with diacritics if available), optional QAC root/POS, optional Qamus entry candidates.

**Checks (in order — stop at the first that certifies):**
1. **Qamus entry** root for this surface/form — highest authority; the geminate is already expanded to C2 = C3.
2. **QAC** root for this token position (`(ref, norm_strict)`) — gives the un-merged triliteral root directly
   (internal evidence).
3. **Shadda expansion + conjugation probe:** expand the shadda to its two identical radicals **before** counting
   (رَدَّ → ر + دّ → **ر د د**), then confirm against a form where the gemination splits — the geminate breaks apart
   when a sukūn-bearing suffix follows (رَدَدْتُ "I returned", رَدَدْنَا "we returned"), exposing both د's. A
   surfacing split CdaCC form certifies C2 = C3.
4. external reference triangulation (internal only).
5. heuristic (`normalize_ar`) — **never sufficient alone.**

**Evidence-ladder rule:** `norm_strict` **drops the shadda** (it strips all harakāt, shadda included), so a doubled
root collapses to two letters and looks biliteral on the live key — `norm_strict` alone can mistake رَدَّ for a
two-radical stem. A doubled root therefore needs **QAC or the Qamus entry** to confirm the third radical; never
certify the count from a key. `norm()` likewise under-counts. The split forms (رَدَدْتُ) are the in-text proof.

**Output:** `candidate_root` (3 radicals, geminate expanded: ر د د), `geminate: true`, the rung used,
`confidence`, and `split_form_seen` (the CdaCC witness if any). If the third radical cannot be confirmed →
**pending** (`geminate_shadda`).

**Forbidden:** counting radicals off the shadda-bearing surface (reading رَدَّ as biliteral); certifying a doubled
root from `norm`/`norm_strict` alone (both drop the shadda); asserting gemination without QAC/entry/split-form
support. Gate per [`../rules/weak-root-gates.json`](../rules/weak-root-gates.json) — never below `two_vote` while the
third radical is shadda-hidden.

**Example — رَدَّ:** surface skeleton is ر + دّ → expand the shadda → **ر د د** "to return/repel". Confirm via the
split conjugation رَدَدْتُ / رَدَدْنَ, which spells both د's, and via QAC. Do not file it as a two-letter root.

**Example — مَدَّ / حَقَّ / ظَنَّ:** مَدَّ → ر… → **م د د** "to extend"; حَقَّ → **ح ق ق** "to be true/binding";
ظَنَّ → **ظ ن ن** "to think/suppose". Each wears one shadda hiding the duplicated last radical; expand before
counting, then certify the C2 = C3 reading from the entry or QAC, never from the merged surface.

**Test:** `tools/check_regressions.py` (shadda-expansion / geminate count invariants); fixtures
`examples/root-form-decisions.jsonl`, `examples/qamus-regressions.jsonl`.

**Feeds:**
- **/qamus/ entry authoring:** supplies the expanded triliteral root + `geminate` flag so a new entry files under
  the full headword (رَدَّ under ر د د) and the `usage[]` shows both merged and split forms (رَدَّ / رَدَدْتُ).
- **hover-gloss resolution:** tells `qamus-highlight` that a shadda-bearing surface is a real triliteral, so it
  certifies via QAC/entry instead of the `norm_strict` key that drops the shadda — or emits `pending` with
  `geminate_shadda` rather than guessing a two-letter root.
- **ʿajamī learners:** teaches that the shadda **is a doubled letter**, that رَدَّ and رَدَدْتُ are the same root,
  and that one always expands the gemination before reading the root — turning a confusing 2-letter look into a
  recognizable triliteral.
