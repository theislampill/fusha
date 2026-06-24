# Procedure — proper noun (ʿalam) detection

**Invoke when:** the surface might be a proper noun (ʿalam) — a name of a person, prophet, place, or people —
before any root-verb gloss is attached. A name is **not** its etymon: إِبْرَٰهِيم is not "to be a father", and
فِرْعَوْن is not glossed from any Arabic root at all.

**Input:** surface (with diacritics if available), root candidate, optional QAC POS, optional Qamus entry, and the
āyah referent/context.

**Checks (ordered evidence ladder — stop at the first rung that certifies):**
1. **QAC POS == `PN`** for this `(ref, norm_strict)` token — internal evidence; the strongest single rung. `PN` →
   route to `pending_proper_noun`, never to a root-verb gloss.
2. **Qamus entry recorded as a name** (a name-as-name record, not a verbal-root sense) → use the name; stop.
3. **Non-Arabic / non-derivable form** — foreign theophorics and place-names that fit **no** Arabic wazn:
   إِبْرَٰهِيم, إِسْرَٰٓءِيل, فِرْعَوْن, جَالُوت, إِلْيَاس. A form that no measure or pattern explains is a name by
   default, not a root surface.
4. **Referent guard / context** — the verse is *about* a named individual or place (نُوح addressed as a prophet;
   مَكَّة as a city) ([`../../nahw/procedures/referent-context.md`](../../nahw/procedures/referent-context.md),
   [`../../nahw/rules/referent-guard-rules.json`](../../nahw/rules/referent-guard-rules.json)).
5. **Heuristic alone** — never sufficient; many names are homographs of common words and must NOT auto-resolve
   either way.

**Evidence-ladder rule:** `norm()` strips the very harakāt and seats that separate a name from its homograph
(صَٰلِحًا "righteous" vs the Prophet Ṣāliḥ; ٱلْعَزِيز "the Mighty / ʿAzīz of Egypt"; أَحْمَد the name vs the
elative). The bare consonant skeleton **never** certifies "name vs common noun" — certify with `norm_strict` +
QAC `PN` + context, or send to pending.

**Output object fields:**
- `is_proper_noun` — boolean.
- `name` — the romanised/Arabic name when authored as a name-as-name record (e.g. "Ibrāhīm").
- `route` — `pending_proper_noun` (default for an un-authored ʿalam) or `name_record`.
- `rung`, `confidence`, and `pending(reason)` when the referent is unresolved or the surface is a name↔common
  homograph.

**Forbidden shortcuts:**
- **Deriving a verb sense from a name** — مُحَمَّد is never "to praise", إِبْرَٰهِيم never "to be a father",
  فِرْعَوْن has no root gloss. This is the `proper-noun-never-verb` blocker
  ([`../rules/pos-mismatch-rules.json`](../rules/pos-mismatch-rules.json)).
- Auto-resolving a name↔common homograph in **either** direction without context (صَٰلِح, ٱلْعَزِيز, أَحْمَد).
- Treating a name's apparent wazn as a participle/elative and glossing the trait instead of routing to the name.

**Example 1 — foreign name, no root.** فِرْعَوْنُ (e.g. 79:17), QAC `PN`. No Arabic measure explains it; rung 1
fires → `route: pending_proper_noun`, `name: "Firʿawn"`. No ف‑ر‑ع gloss is ever attached.

**Example 2 — name↔common homograph.** صَٰلِحًا appears both as the adjective "righteous (deed)" (2:62) and as the
Prophet Ṣāliḥ (7:73). The `norm_strict` key صالحا cannot separate them, so neither the adjective nor the name may
auto-key; rung 4 (context) decides per āyah, else `pending(referent_sensitive)`. Likewise أَحْمَد (61:6) is the
name, **not** the elative or the verb ح م د.

**Test:** `examples/qamus-regressions.jsonl` (مُحَمَّد, أَحْمَد, صَٰلِحًا rows — proper-name-vs-verb / vs-adjective
risk); `tools/check_regressions.py`; the live `pending_proper_noun` bucket in
`../../qamus/reports/hover-token-completion.md`.

**Feeds:**
- **/qamus/ entry authoring** — distinguishes a name-as-name record from a verbal-root entry, so an ʿalam never
  acquires a spurious root, senses[], or usage[] derived from its etymon.
- **hover-gloss resolution** — routes ʿalam tokens to `pending_proper_noun` (they stay plain, never key-glossed),
  keeping name↔common homographs out of the auto-safe lane ([`hover-application.md`](hover-application.md)).
- **ajami learners** — teaches that a Qurʾanic name carries no lesson in its consonants: نُوح is "the Prophet
  Nūḥ", not a word to parse, so the learner stops hunting a root where there is only a name.
