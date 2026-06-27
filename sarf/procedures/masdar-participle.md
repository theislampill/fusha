# Procedure — maṣdar vs. participle vs. ṣifa mushabbaha (gloss shape)

**Invoke when:** the surface is a derived nominal of a verbal root — a maṣdar, ism fāʿil, ism mafʿūl, or ṣifa
mushabbaha — and you must fix the **shape** of the gloss before authoring/repairing/resolving it.

**Input:** surface (with diacritics if available), root, optional QAC POS, optional Qamus entry (`category`,
wazn, senses). The decision is over **morphological shape**, not lexical meaning: a wrong shape (a finite verb on
a noun) is a POS-mismatch blocker even when the meaning is "right".

**Checks (ordered evidence ladder — stop at the first rung that certifies the shape):**
1. **Qamus entry `category`/wazn for this lemma** — highest authority. If it records `masdar` /
   `ism_fa3il` / `ism_maf3ul` / `sifa_mushabbaha`, take that shape and stop.
2. **QAC POS for this token position** (`(ref, norm_strict)` — internal evidence): `N`/`ADJ` excludes a finite
   verb; pair it with the wazn to split the four shapes.
3. **Wazn read off the diacritized surface** — the four signatures:
   - **maṣdar** → names the act: ذِكْر "remembrance", إِنفَاق "spending", اِسْتِغْفَار "seeking forgiveness".
   - **ism fāʿil** (فَاعِل / مُـ…kasra) → the doer: كَاتِب "writer", مُؤْمِن "believer".
   - **ism mafʿūl** (مَفْعُول / مُـ…fatḥa) → the done-to: مَخْلُوق "created thing", مُنزَل "sent down".
   - **ṣifa mushabbaha** (فَعِيل، فَعِل، أَفْعَل…) → a **settled quality** of the subject, not an act in progress:
     كَظِيم "filled with restrained grief", حَلِيم "forbearing", عَظِيم "immense".
4. **Penult/last-radical vowel** for مُـ participles only (rung 3 ambiguous): kasra → fāʿil (مُعَلِّم "teacher"),
   fatḥa → mafʿūl (مُعَلَّم "taught one"). Read the vowel before choosing the gloss.
5. **Heuristic (`normalize_ar`) alone** — never sufficient; recall only.

**Evidence-ladder rule:** `norm()` drops harakāt → it cannot tell ṣifa mushabbaha فَعِيل from a maṣdar or a
verb on the same skeleton (ك‑ظ‑م certifies nothing). Certify the shape with `norm_strict` + QAC POS + the
diacritized wazn; the bare root never certifies a shape.

**Output object fields:**
- `pos` — one of `masdar` / `ism_fa3il` / `ism_maf3ul` / `sifa_mushabbaha` (not bare `noun`/`verb`).
- `gloss_shape` — `nominal_act` / `agent` / `patient` / `quality`.
- `gloss` — wording matching the shape (a noun or adjective; **never** an English "to …" infinitive).
- `rung`, `confidence`, and on failure `pending(reason)`.

**Forbidden shortcuts:**
- A finite-verb / "to …" gloss on any of the four shapes — the §3 POS-mismatch blocker
  ([`../rules/pos-mismatch-rules.json`](../rules/pos-mismatch-rules.json)).
- Collapsing a ṣifa mushabbaha فَعِيل into its Form-I verb ("to suppress" for كَظِيم) — a ṣifa names a state, not
  the act of entering it.
- Reading a maṣdar's harakāt off a bare root (the ذِكْر / ذَكَر / ذَكَرَ pull;
  [`../references/masdar-participle-notes.md`](../references/masdar-participle-notes.md)).

## Dogfood finding: populated hover is not shape certification

The full-corpus dogfood pass found populated hovers where a live token was a nominal derivative or nominal result
but inherited the Qamus entry's infinitive/root gloss. Examples:

- `ٱلْمُفْلِحُونَ` (2:5:8) carried "to succeed", but the token is a plural active-participle/nominal group:
  "the successful ones".
- `بِنَآءً` (2:22:7) carried "to build", but the token is a noun/result, not a finite verb.
- `مُّطَهَّرَةٌ` (2:25:31) carried "to purify", but the token is a passive participle/adjectival form:
  "purified".
- `جَاعِلٌ` (2:30:6) carried "to make", but the token is an active participle: "one who makes/places".

Treat this as `populated_hover_pos_leakage`: visible text exists, but it is not dogfood-complete until the
hover's English shape matches the token's sarf shape. A nominal token with a "to ..." hover routes to token-only
review plus production-bug lesson/regression fixture; it is never repair-ready merely because the root meaning is
recognizable.

**Example 1 — the كَظِيم repair lesson.** Surface كَظِيمٌ (12:84, 16:58, 43:17), root ك ظ م. The wazn is **فَعِيل
= ṣifa mushabbaha**, so the shape is `quality`, not an act. The shipped gloss read *"to suppress (or choke with)
anger or distress"* — a finite verb on a quality-adjective. Reshaped to **"(one) suppressing his grief; filled
with restrained grief/anger."** Yaʿqūb is وَهُوَ كَظِيمٌ — *characterised by* swallowed grief, not *performing*
the verb كَظَمَ. (Applied live as `repair_batch_004`; entry versioned + backed up.)

**Example 2 — three shapes, one root.** From ع ل م: عِلْم "knowledge" (maṣdar, `nominal_act`); عَالِم "a scholar"
(ism fāʿil, `agent`); مَعْلُوم "a known thing" (ism mafʿūl, `patient`); عَلِيم "All-Knowing" (ṣifa mushabbaha,
`quality`). None of the four may be glossed "to know".

**Test:** `examples/qamus-regressions.jsonl` (ذِكْر maṣdar, مُؤْمِنُونَ participle, the كَظِيم quality-shape row);
`tools/check_regressions.py` POS-mismatch checks. Gate tier in
[`../rules/masdar-participle-gates.json`](../rules/masdar-participle-gates.json) (`verb_on_nominal` =
`never_auto_resolve`).

**Feeds:**
- **/qamus/ entry authoring** — sets the entry's `category` and the gloss *shape* of `definition` +
  `senses[].gloss`, so a new entry never ships a verb gloss on a maṣdar/participle/ṣifa (the كَظִيم class).
- **hover-gloss resolution** — supplies `pos` + `gloss_shape` to `norm_strict` authoring so a "to …" candidate is
  dropped before it keys a derived nominal ([`hover-application.md`](hover-application.md)).
- **ajami learners** — teaches that Arabic packs "the act / the doer / the done-to / the quality" into four
  patterns on one root, so the learner reads عَلِيم as a *trait* ("All-Knowing"), not a verb ("knows").
