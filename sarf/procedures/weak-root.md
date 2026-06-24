# Procedure — weak-root recovery (مثال / أجوف / ناقص / لفيف)

**Invoke when:** the surface has a hidden weak radical (و/ي) that shows as ا, or drops, or alternates — i.e. the
skeleton has too few letters or an unstable last letter to read the root directly.

**Input:** surface (with diacritics if available), the muḍāriʿ if known, optional QAC root/POS, optional Qamus
entry candidates.

**Checks (in order — stop at the first that certifies):**
1. **Qamus entry** root for this surface/form — highest authority for our gloss; the weak radical is already
   resolved in the entry.
2. **QAC** root for this token position (`(ref, norm_strict)`) — recovers the و/ي directly (internal evidence).
3. **Muḍāriʿ recovery** from the family ([`../references/weak-verbs.md`](../references/weak-verbs.md)):
   - **أجوف (hollow, C2 weak):** CāC past → read C2 off the present. يَقُولُ→و, يَبِيعُ→ي, يَنَامُ→و/ا.
   - **ناقص (defective, C3 weak):** final ا/ى/و/ي alternates → read C3 off the present. يَدْعُو→و, يَرْمِي→ي.
   - **مثال (assimilated, C1 weak):** C1 و **drops** in the present (وَعَدَ→يَعِدُ) — a yaCiC with no و can still be
     a و-initial root; recover C1 from the past/maṣdar.
   - **لفيف (doubly weak):** two weak radicals (وَفَىٰ ← و ف ي مفروق; طَوَىٰ ← ط و ي مقرون) — recover both, never
     read one as a long vowel.
4. external reference triangulation (internal only).
5. heuristic (`normalize_ar`) — **never sufficient alone.**

**Evidence-ladder rule:** `norm()` over-recalls weak roots (it maps ؤ→و, ئ→ي, drops ء, folds ى→ي) so a weak
skeleton matches far too many roots — recall only, never certifies. Certify with `norm_strict` + QAC. The
canonical false tie: `إِلَيْنَا` (إِلَىٰ + نا) is **not** root ل ي ن.

**Output:** `candidate_root` (3 radicals with the weak letter restored), `weak_class`
(`assimilated`/`hollow`/`defective`/`lafif`), the rung used, `confidence`, and `recovered_from`
(`entry`/`qac`/`mudari3`). If the radical cannot be certified → **pending** with the precise reason
(`hollow_root_c2_hidden`, `defective_c3_alternation`, `assimilated_c1_dropped`).

**Forbidden:** reading a hollow CāC as a sound biliteral; treating a defective ا/ى/ي as a stable last radical;
inferring a weak root from `norm()`; asserting a weak root by subsequence match (the Nawawī40 ~50% false-tie
lesson). Gate per [`../rules/weak-root-gates.json`](../rules/weak-root-gates.json) — never below `two_vote` for a
hidden/alternating radical.

**Example — hollow:** قَالَ shows no و; the past is a bare CāC. Recover from يَقُولُ → C2 = **و** → root **ق و ل**.
Likewise دَعَا (no visible final radical) → يَدْعُو → C3 = **و** → **د ع و**; رَمَىٰ → يَرْمِي → C3 = **ي** → **ر م ي**.

**Example — assimilated:** وَعَدَ "he promised". The C1 و survives in the past, so read it directly → **و ع د**; do
not be misled by the present يَعِدُ where the و drops. Confirm against the entry/QAC before glossing.

**Test:** `tools/check_regressions.py` (norm-vs-norm_strict invariants, the `إِلَيْنَا ≠ ل ي ن` guard); fixtures
`examples/root-form-decisions.jsonl`.

**Feeds:**
- **/qamus/ entry authoring:** supplies the restored triliteral root + `weak_class` so a new entry files under the
  correct headword (قَالَ under ق و ل, not a two-letter stub) and the `usage[]` forms read coherently.
- **hover-gloss resolution:** lets `qamus-highlight` certify a weak surface via QAC/entry instead of a `norm()`
  match, or emit `pending` with the exact hidden-radical reason rather than a guess.
- **ʿajamī learners:** teaches the "recover the weak letter from the muḍāriʿ" reflex — that قَالَ/يَقُولُ and
  دَعَا/يَدْعُو share a real third radical hidden by the surface — so the root, not the spelling, is what is learned.
