# Host-lexeme authoring (B2)

The suffix/pronoun lane's `stem_base_unknown` blockers are possessed nouns whose host lexeme is **not
in the Qamus dataset**. This lane authors the host noun gloss (sarf/nahw + QAC root) and composes the
possessive — 2-vote certified, POS-gated, false-split-guarded.

## Result

- **150 host-lexeme decision-requests** generated (`tools/build_host_lexeme_candidates.py`): possessed
  noun + unambiguous multi-letter enclitic (هم/كم/نا/هما/ها…), host NOT in dataset, POS≠verb,
  tanwīn-alef excluded, particle-host stoplist applied.
- **2-vote authoring** (`host-lexeme-verify` workflow, 26 sarf/nahw authors): **101 applied / 49
  rejected**. Rejections = the exact guards: `false_split_root_radical` (ٱلْمُلْك root م-ل-ك),
  `preposition_or_particle_pronoun` (لَهُ "for him"), `verb_host_not_possessive`, `tanwin_alef`,
  `host_noun_unknown` (prefer pending over a guess).
- Applied → live **82.49%** (41,063 → 41,164, **−0 removed, −0 changed**, 0 wrong).

## Authored possessives (number-correct broken plurals)

their evil deeds (سيئات) · your/our gods (آلهة) · their dwellings (مساكن) · their faith (إيمان) ·
their recompense (جزاء) · their women (نساء) · their partners (شركاء) · their families (أهل) ·
their burdens (أوزار) · your sins (ذنوب) · your affair (أمر) · our heels (أعقاب) · your enemy (عدو) ·
your sons (أبناء) · their protectors/allies (أولياء) · their prayer direction (قبلة) · their fathers (آباء) ·
your sisters (أخوات) · Our revelation (وحي) · their transgression (طغيان) · their companion (صاحب) ·
their right hands (أيمان) · her offspring (ذرية) · their mark (سيما) · our father (أب) · their vows (نذور) ·
their adopted sons (أدعياء) · our messengers (رسل) · their waiting period (عدة) · your community (أمة) ·
your backs (ظهور) · your heads (رؤوس) · their wives (أزواج) · your souls (أنفس) · their rage (غيظ) …

## Safety (skills cited)

- **/fusha-sarf** `suffix-pronoun-state` + `noun-plural-gender`: broken plural shares the root (سيئة→سيئات
  "evil deeds" plural), not the surface; clitic stripping must not invent a false stem.
- **/fusha-sarf** principle 4 + the false-split guard: ٱلْمُلْك (root م-ل-ك) is "the dominion", the ك is a
  radical — rejected, not glossed as مُلك+"your".
- **/fusha-nahw** `pronoun-attachment`: a preposition+pronoun (لَهُ) is a phrase, not a possessed noun —
  rejected. A verb host's enclitic is subject/object, never possessive — rejected.
- Tests: `nahw/evals/suffix-pronoun-eval.jsonl` + `tools/test_suffix_pronoun.py` (verb-exclusion,
  tanwīn-alef, false-split, named classes) — green.

## Remaining

`stem_base_unknown` dropped 6,969 → **6,866**. The remaining are lower-frequency host nouns + the
false-split residue (correctly pending). Re-run `build_host_lexeme_candidates.py` for the next tier;
genuinely recurring missing nouns become owner-gated new-entry candidates (none minted this pass).
