# Verb-clitic lane readiness (closure-2092 Phase 4A)

`tools/build_verb_clitic_candidates.py` + `tools/validate_verb_clitic_candidates.py` +
`qamus/schemas/verb-clitic-candidate.schema.json`.

- Input: `verb_clitic_object_or_subject_candidate` rows (822) from the root-cause ledger.
- Output: **638 review-only** candidates (gitignored `out/`); 183 tanwīn-alif false-enclitics + 1 particle
  bundle correctly skipped. **No public gloss authored** (`gloss_draft` blank until 2-vote certifies).
- Each row: loc, surface, verb_stem, root, qac_pos=V, enclitic, pronoun person/gender/number, clitic_role
  (object/subject), sarf procedure (verb-form), nahw procedure (preposition-pronoun), gate=two_vote.
- **Never** routes to the possessed-noun lane (a verb's enclitic is object/subject — nahw skill). Rejects
  tanwīn-alif / false suffix / particle bundles. Fixtures for ٱهْدِنَا / يَأْمُرُكُمْ / فَلَهُمْ / وَإِنَّهَا are in
  `qamus/examples/form_variant_rejections.jsonl`.
- Sample: `2:10:4 فَزَادَهُمُ` → verb زاد + هم (object "them"), gloss blank.
- Gate: wired into `check_regressions` (generator runnable + validator green). GO at 2-vote.
