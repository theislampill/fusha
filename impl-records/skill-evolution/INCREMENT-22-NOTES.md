# INCREMENT-22 — ṣarf@2.2 / naḥw@2.2 + norm CANDIDATE increment notes

**Lane:** SKILL-INCREMENT @2.2 (QAMUS-RICH-NORM-001 consolidation). **Date:** 2026-07-12.
**Repo:** PUBLIC github.com/theIslampill/fusha. **Base:** origin/main `7d1265a` (norm@1 `59876fb` +
lattice-root-inherit `b12036c` already merged).
**Status:** CANDIDATE, drafted forward off `origin/main`. Does NOT amend released @2 text (appended as
clearly-marked @2.2-candidate sections). Fable adjudicates; nothing merged, nothing promoted to `accepted`.

Consolidates the QAMUS-RICH-NORM-001 cycle into **18 candidate rules (15 ṣarf, 3 naḥw; 12 norm-domain)**,
each with a source-addressed `projector` block, a positive (red-first) + a boundary/control example, defeaters,
and an abstention condition. Where @2.1 asked *"what is broken?"* one detector at a time, @2.2 encodes
*"what does a CORRECT row look like?"* (the `norm@1` clauses) and closes the C1–C5 detector blind spots the
ANDON traced.

- Registry rows: `qamus/skills/rule-registry-increment-22.jsonl` (18 rows, schema-conformant, `sarf@2.2`/`nahw@2.2`, status `candidate`).
- Fixtures: `tools/skill_fixtures/skill_fixtures_increment22.jsonl` (37) + discriminators `skill_rules_increment22.py` + harness `test_skill_fixtures_increment22.py`.
- Deterministic builder: `tools/skill_fixtures/_build_increment22.py` (`--check` proves regeneration-clean).
- SKILL amendments: `sarf/SKILL.md` §19 + `nahw/SKILL.md` "naḥw@2.2" section (append-only; mirrors regenerated, drift --real 0).
- Harness gate: `tools/check_regressions.py` **gate 13** (fixtures + merged released+@2.1+@2.2 registry validation).

## Evidence → rule map (which source produced which rule)

### norm@1 normalization contract (`docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md`) — the NEW-gate clauses
- `sarf-norm-root-hedge-ban` ← **N-ROOT-01**: a content segment must not decline its root with hedge prose;
  catches the multi-segment (فَحَقَّ) + clean-stem (خَلَقَ) hedge C2's single-segment gate skips.
- `sarf-norm-typed-rootless-rationale` (review) ← **N-ROOT-02**: typed rootless rationale from a closed
  vocabulary {function-word, proper-name, jamid-contested, pending}; never silent, never hedge prose.
- `sarf-norm-field-language-meta-ban` ← **N-LANG-01**: rendered-field meta-language blocklist (superset of C4's
  three phrases) + the `\b[A-Z]{1,6}:\S` segment-label-notation leak (`FA:فَ`, `TOK:حَقَّ`).
- `sarf-norm-english-led-rendered-fields` ← **N-LANG-02**: learner fields English-led; the Arabic-prose dump
  (كَلِمَةُ) is flagged; short quoted forms exempt.
- `nahw-norm-note-leads-english` ← **N-LANG-03**: sarf_note/nahw_note may cite Arabic terms but must lead English.
- `sarf-norm-gloss-contribution-present` ← **N-PED-01**: every segment carries a non-empty gloss_contribution.
- `nahw-mood-note-commits-or-named-ambiguity` ← **N-PED-02**: a knowable mood note commits (or names ambiguity),
  never "as context requires".
- `sarf-norm-same-surface-root-coherence` ← **N-CONS-01**: same-surface rows cohere on root or record a homograph
  rationale (حَقَّتْ asserts ح ق ق; sibling فَحَقَّ served rootless).
- `sarf-entry-root-inheritance-tier0` ← **N-CONS-02**: a rootless content row inherits its owning entry's root as a
  CANDIDATE (attested-source only; خَلَقَ is a headword, مُسَخَّرَٰتٍ matches v198 usage.forms).
- `nahw-irab-note-not-verbatim-source` ← **N-LANG-01/02** for the iʿrāb note: the raw analyzer Arabic iʿrāb is
  analysis input, not rendered copy.

### Rich-hover ANDON trace (`impl-records/andon-rich-norm/QAMUS-RICH-NORM-001-TRACE.md`) — detector gaps G1–G7
- G1 proclitic→rootless remainder + G2 clean-stem null root → folded into `sarf-norm-root-hedge-ban` (both hedge; C2's
  single-segment / verb-stem sets never see them).
- G3 adjective/participle exemption → covered by N-ROOT-01 (the participle guard applies to segmentation, not root presence).
- **G4** root in `مادة`/prose unparsed → `sarf-root-in-madda-prose-recognized`: recognize the مادة (كلم) idiom as an asserted root.
- G5 no field-language gate → `sarf-norm-field-language-meta-ban` + `-english-led-rendered-fields` (+ naḥw note rules).
- **G6 / O-2** C5 pronoun-only vocabulary → `sarf-sound-plural-suffix-swallow-detect`: sound plural ـات/ـين (+tanwīn)
  swallow, split STEM+PL-F/PL, with the radical-ت 2-vote guard.
- G7 headword/entry incoherence → `sarf-entry-root-inheritance-tier0` + `-rooted-vs-entry-conflict` + `-entry-id-context-only`.

### Global lexeme join (`qamus/reports/ROOT-INHERITANCE-JOIN.md`)
- `sarf-entry-root-inheritance-tier0` ← entry headword/usage.form self-join as a certification-evidence tier (candidate-only).
- `sarf-entry-id-context-only-not-root` ← the bare-`entry_id`-is-context-only correction (فَوْقَكُمُ carries the أخذ id).
- `sarf-rooted-vs-entry-conflict-never-auto-resolve` ← the 464-row rooted-vs-entry conflict rule (`root_conflict` edges; never auto-resolve).

### C4 / C5 / W1-A / W13 waves
- `sarf-honest-sentence-template` ← C4 honest-sentence template rule + the 100%-agreement telemetry (ONH-B5 et al.).
- `sarf-mu-pattern-taught-not-coloured` ← C5/W1-A: مُ-pattern (مُفَعَّل/تَفَعَّل) taught (named in morphline) not coloured (stem-internal per DR-1) when the entry attests the form.
- `sarf-sound-plural-suffix-swallow-detect` ← C5/W1-A ـات feminine-plural segmentation (with G6/O-2).
- `sarf-loc-range-external-authority-prevalidation` ← C5/W1-A: local indexes are circular — validated by the 17:1:22 catch.
- `sarf-demonstrative-dagger-alef-normalize` ← W13: the demonstrative dagger-alef (U+0670) engine-miss fixed twice; now a rule + fixture.

## Projector-readiness assessment (per rule)

**Projector-ready (17)** — machine-checkable condition, deterministic projection (a detector / inheritance /
consistency / negative-guard). Safe to key a transclusion/projection lattice on:
`sarf-norm-root-hedge-ban`, `sarf-norm-field-language-meta-ban`, `sarf-norm-english-led-rendered-fields`,
`sarf-norm-gloss-contribution-present`, `sarf-norm-same-surface-root-coherence`, `sarf-entry-root-inheritance-tier0`,
`sarf-entry-id-context-only-not-root`, `sarf-rooted-vs-entry-conflict-never-auto-resolve`,
`sarf-root-in-madda-prose-recognized`, `sarf-sound-plural-suffix-swallow-detect`, `sarf-mu-pattern-taught-not-coloured`,
`sarf-honest-sentence-template`, `sarf-loc-range-external-authority-prevalidation`, `sarf-demonstrative-dagger-alef-normalize`,
`nahw-norm-note-leads-english`, `nahw-irab-note-not-verbatim-mcp`, `nahw-mood-note-commits-or-named-ambiguity`.
(The entry-root-inheritance projection is projector-ready as a CANDIDATE-generator only — attested-source, stays
`certification_state=candidate` to the 2-vote; pattern never certifies.)

**Review-gated (1)** — the linguistic/authoring step is contextual; only the consequence is deterministic:
`sarf-norm-typed-rootless-rationale` (needs the NEW typed-rationale field + a per-row typing pass).

## Negative results / boundaries recorded (no rule authored)
- **No new pure-derivational rules** (the @2.1 measured-effect finding is honored: derivational-morphology rules
  added no disposition lift; this increment adds NORMALIZATION + detector-gap + ownership rules, the measured
  high-value classes).
- **N-SEG-01 concat / N-SEG-02·N-COLOUR-01 canonical class** are NOT re-authored as @2.2 rules — the contract maps them
  to the EXISTING completeness + schema-coherence gates; duplicating them would be justification-only.
- The @2.2 rules are candidate-generation / detector rules; **no whitelist/manifest mutation** is implied. The ANDON
  snapshot sha `1c06d85a…903c` is the analysis basis; nothing was deployed.

## Validation results (all green at author time)
- `python tools/skill_fixtures/_build_increment22.py --check` → regeneration-clean (18 rules, 37 fixtures).
- `python tools/skill_fixtures/test_skill_fixtures_increment22.py` → **37 fixtures, 19 red-first, 18 rules, 18 registry
  ids covered**; every corrected discriminator branches (non-constant / anti-send-back); norm@1 contract clauses present;
  registry↔fixture domain tags agree; builder regeneration-clean.
- `python tools/validate_skill_registry.py --self-test` → **17/17** (adds the @2.2 candidate/blocked transitions;
  @2.2-accepted correctly rejected).
- Merged registry (`rule-registry.jsonl` + @2.1 + @2.2) → **216 rows, 0 errors** (0 dup / 0 dangling; every `extends`
  target resolves in the merge).
- `jsonschema` Draft7 against `skill-rule-registry-row.schema.json` (pattern now `@(1|2|2.1|2.2)`) → **18/18 rows, 0 errors**.
- `python tools/generate_skill_mirrors.py --self-test` green; map regenerated; `python tools/check_skill_drift.py --real`
  → **0 findings** (recorded local-install observations updated to the new canonical SKILL.md SHAs).
- `python tools/check_regressions.py` → **ALL REGRESSION CHECKS PASS** (gate 13 added; released @2 + @2.1 untouched and still green).
