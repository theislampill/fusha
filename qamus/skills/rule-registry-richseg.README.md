# rule-registry-richseg.jsonl — header / merge note

**Status: DRAFT (candidate @2). The owner adjudicates; do not mark accepted.**

`rule-registry-richseg.jsonl` holds the 9 versioned skill rules (5 ṣarf, 4 naḥw) drafted from the
**QAMUS-RICH-SEG-001** rich-segmentation audit's confirmed defect classes. It is kept as a **separate
file** so it does not collide with the in-flight `skill-registry` integration
(`qamus/skills/rule-registry.jsonl`, origin branch `skill-registry` @ `144d18c`).

**At release, these rows merge into `qamus/skills/rule-registry.jsonl`.** Every row is schema-conformant
against `qamus/schemas/skill-rule-registry-row.schema.json` and validates clean under
`tools/validate_skill_registry.py` (both standalone via `--registry` and when concatenated with the live
registry — no duplicate ids, no dangling relationships: all relationships target `external` SKILL.md
sections and are dangling-exempt). Each row also carries `provenance.merge_target`.

- **skill_version:** `sarf@2` / `nahw@2` — additive to the ṣarf@2 / naḥw@2 release.
- **status:** `candidate` (the validator forbids `@2` + `accepted`; release stays owner-gated).
- **evidence:** source-addressed `quran:S:A:W` anchors, MCP-verified via `fetch_ayah`. Where the audit's
  cited word index used a different word-numbering convention than the Uthmani split (2:91:3→word 23
  تقتلون; 40:72:4→word 6 يسجرون), `provenance.loc_reconciliation` records the verified index — the surface
  is verified present in the cited āyah (verify-before-trust; scripture refs are never self-edited).
- **fixtures:** each rule has a red-first fixture in `tools/skill_fixtures/skill_fixtures_richseg.jsonl`,
  proven green-on-corrected / red-on-superseded by `tools/skill_fixtures/test_skill_fixtures_richseg.py`
  (discriminators in `tools/skill_fixtures/skill_rules_richseg.py`). The two over-segmentation boundary
  negatives (4:144:17 مُّبِينًا, 102:3:3 تَعْلَمُونَ) are included so the rules do not over-generalize.

These are **observed morphosyntactic rules** with source-addressed Qurʾānic evidence, not theological
claims. Stdlib-only, deterministic, no production identifiers.
