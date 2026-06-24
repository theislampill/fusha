# Procedure — conditional particles (and the إِنْ / إِنَّ collision)

**Invoke when:** the token is a conditional particle — إِنْ, إِذَا, لَوْ — or مَنْ / مَا used conditionally.

**Input:** surface (with diacritics, hamza seat preserved by `norm_strict`), the verb(s) it governs, the clause shape
(protasis شرط + apodosis جواب).

**Checks** (ordered evidence ladder — **stop at the first rung that certifies**), per
[`../rules/particle-context-rules.json`](../rules/particle-context-rules.json):
1. **إِنْ vs إِنَّ first** — read the hamza seat and the shadda on the nūn (kept by `norm_strict`, dropped by `norm`):
   - kasra-seat إِ + **shadda** → **إِنَّ** "indeed / verily" — the emphatic, **NOT** a conditional; leave this procedure.
   - kasra-seat إِ + **light** (no shadda) + a following verb (jussive) → **إِنْ** "if". Continue at rung 4.
   Stop here only to *route*: إِنَّ exits, إِنْ proceeds.
2. **إِذَا** — "when / whenever": a *realized* or expected condition; followed by a past-form verb read as
   present/future, apodosis often introduced by فَـ. → resolved "when".
3. **لَوْ** — counterfactual "if (had) …, (would have) …": signals an unreal past condition; the جواب often opens with
   لَـ (لَوْ … لَـ …). → resolved "if (only) / had it been".
4. **مَنْ / مَا as conditional** — مَنْ + two jussive verbs ("whoever does X, Y") or مَا + two jussives ("whatever …")
   is the **conditional** reading, distinct from the relative/interrogative ones in
   [`relative-interrogative.md`](relative-interrogative.md). The twin-jussive (شرط + جواب) frame is the signal.
   → resolved "whoever / whatever".
5. **No rung certifies** (seat collapsed, or the governed verbs are out of range) → `pending`.

**Evidence-ladder rule:** rung 1 is a gate, not a gloss — never glossed-past it without settling إِنْ vs إِنَّ on the
seat+shadda. Below it, take the gloss from the **first** rung that fires and stop. If the hamza seat was lost to `norm`,
re-read with `norm_strict` before deciding; if still ambiguous, `pending` — never default إِنْ to "if" or إِنَّ to
"indeed" on the bare key.

**Why the وَإِن key is unsafe:** norm() renders both **وَإِنْ** ("and if", conditional) and **وَإِنَّ** ("and indeed",
emphatic) to the same key `وان` — the و proclitic does nothing to separate them, and the only distinguishers (the kasra
seat is shared; the **shadda on the nūn**) are exactly what undiacritized input drops. So a `وَإِن` surface key can carry
either sense and **cannot certify** a gloss; it must be decided on the shadda (and the governed clause) or held
`pending(seat_collapsed)`. Keying وَإِن → "and if" is the failure this rule blocks. PENDING beats a wrong gloss.

**Output object fields:**
- `surface` — the diacritized token.
- `function` — `conditional` | `emphatic` (إِنَّ exit) | `temporal` (إِذَا) | `counterfactual` (لَوْ).
- `gloss` — "if" | "indeed / verily" | "when / whenever" | "if (had) …".
- `decision` — `resolved` | `pending`.
- `reason` — the seat/shadda read plus the governed-clause shape (twin jussive, فَـ-apodosis, لَـ-apodosis).
- `reason_code` — `homograph_haraka` | `seat_collapsed` (for إِنْ/إِنَّ) | `context_sensitive_needs_nahw`.
- `gate` — `two_vote` whenever the إِنْ/إِنَّ seat is collapsed or مَنْ/مَا conditional vs relative is in play
  (`grammar-risk-gate.md`).

**Forbidden shortcuts:** glossing وَإِن (or إن) on the key without reading the shadda; defaulting إِنْ → "if" /
إِنَّ → "indeed"; confusing conditional مَنْ/مَا with their relative readings without the twin-jussive frame; reading
إِذَا (when) as لَوْ (counterfactual). A particle never takes a content-verb/noun gloss.

**Worked examples (vowelized):**
- `وَإِنْ تَعُدُّوا نِعْمَةَ اللَّهِ لَا تُحْصُوهَا` — light nūn (no shadda) + twin jussive (شرط تَعُدُّوا، جواب
  تُحْصُوهَا) → **إِنْ conditional**, gloss "**and if** you count Allah's favour, you cannot enumerate it".
- `وَإِنَّ اللَّهَ لَهُوَ الْغَنِيُّ الْحَمِيدُ` — **shadda** on the nūn + a noun in naṣb (اللَّهَ) → **إِنَّ emphatic**,
  gloss "**and indeed** Allah is the Free of need, the Praiseworthy". Same `وان` key, opposite function — decided only by
  the shadda.
- `إِذَا جَاءَ نَصْرُ اللَّهِ` — إِذَا + past-form verb read as future, expected event → **temporal**, "**when** the help
  of Allah comes".
- `لَوْ كَانَ فِيهِمَا آلِهَةٌ ... لَفَسَدَتَا` — لَوْ + لَـ-apodosis → **counterfactual**, "**had** there been gods in
  them … they would have been ruined".
- `مَنْ يَعْمَلْ سُوءًا يُجْزَ بِهِ` — مَنْ + twin jussive (يَعْمَلْ … يُجْزَ) → **conditional مَنْ**, "**whoever** does
  evil will be recompensed for it" (not the bare relative of [`relative-interrogative.md`](relative-interrogative.md)).

**Test:** `examples/function-word-decisions.jsonl` (إِنْ/إِنَّ seat rows, وَإِن key) and
`examples/ayah-context-decisions.jsonl` (مَنْ conditional twin-jussive rows); `tools/check_regressions.py` asserts the
`وان` key never resolves without a shadda read (else `pending(seat_collapsed)`).

**Feeds:**
- **/qamus/ entry authoring** — إِنْ "if" and إِنَّ "indeed" are authored as **separate function entries** (never one
  blended note), each citing the āyah where its seat+shadda were read; conditional مَنْ/مَا are cross-linked to their
  relative/interrogative siblings so the entry shows all jobs of the word; src:"qamus", kind:"authored".
- **hover-gloss resolution** — the hover plaque shows the shadda-certified sense ("if" vs "indeed"); on an
  undiacritized وإن with no shadda evidence it shows the plain word, never a guessed "and if", so the emphatic is never
  silently turned conditional.
- **ajami learners** — drills the two highest-frequency traps at once: that one tiny shadda flips "if" into "indeed",
  and that مَنْ/مَا are read by the *clause shape* (twin jussive = condition) rather than by a memorized English word.
