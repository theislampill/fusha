# Translation as a downstream projection — governed direction and fixtures

Status: adopted 2026-07-29 (canonical architecture doc, precedence tier 4).
Records the owner's §29 translation ruling (2026-07-29, controlling) and
specifies the five required fixture TYPES as **future fixtures with exact
cases**. This doc does NOT authorize building a translation system; no
translation tooling exists in this repo yet, and none should be built without
an owner window.

## 1. Governed direction

Owner ruling (decision ledger, 2026-07-29, verbatim):

> **Translation (§29)**: downstream lattice projection only; never evidence
> for analysis; never English→presumed-Arabic; separate gloss strata;
> divergent-analysis translations both retained.

Unpacked:

- **Downstream consumer.** Translation is one more projection of the
  certified typed-fact lattice — it sits after stage 11 of
  `docs/architecture/meta-transclusive-projection.md`, exactly like the
  hover surfaces. A translation may only render facts the occurrence's
  canonical artifact carries.
- **Forbidden reverse inference.** A translation is never evidence for an
  analysis. An English rendering cannot certify a root, function, referent,
  case, or segmentation — not at any rung of the evidence ladder (it is
  weaker than "an English gloss match", which the rule of non-substitution
  already excludes). Equally forbidden: English→presumed-Arabic — inferring
  what the Arabic "must be" from a chosen translation.
- **Separate gloss strata fields.** Translation output never overwrites or
  shares fields with the existing gloss strata (segment `gloss`,
  `whole_word_gloss`, `contextual_gloss`, `learner_explanation`). A future
  translation stratum gets its own schema fields with its own provenance,
  so certification status of the teaching plane never silently launders
  into a fluent-translation register (additive-only, per the handoff
  contract's semver discipline).
- **Divergent-analysis retention.** Where two analyses are honestly retained
  (attributed unresolved, D-2), their divergent translations are BOTH
  retained and attributed. Translation never forces a false winner.
- **Later-corpus rules.** Expansion beyond the Qurʾānic anchor into later
  Fusha corpora is the charter's "controlled expansion" arc: later-corpus
  translation reuses the same pipeline (source-addressed occurrences, typed
  facts, certification, projection) and never imports Qurʾān-certified facts
  into a later corpus by surface similarity — the unsafe-surface-similarity
  prohibition crosses corpora too.

## 2. The five required translation fixture types (future fixtures)

Each fixture type below names its exact anchor case from committed artifacts.
They are specified now so the fixture files can be authored red-first when a
translation lane opens; none exist yet.

1. **Particle homograph.** مَا at `quran:2:284:2` vs مَا at `quran:2:284:10`
   (`qamus/examples/website-payloads/unresolved_ma_2_284_2.payload.json`,
   `qamus/examples/proof-particle/`). The fixture must show translation
   consuming the per-occurrence function lattice — "whatever" (mawṣūla
   reading) vs the rival readings — and rendering the honest-unresolved state
   without picking a winner; and that the two same-surface occurrences are
   distinct artifacts with independently chosen renderings.

2. **Root-family-not-lexeme.** لِقَوْمِهِ at `quran:61:5:4`
   (`qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json`):
   the segment قَوْمِ relates to verb entry v005 (قَامَ) by
   `root_family_of_entry` ONLY. The fixture must prove the translation
   renders the noun lexeme ("his people"), and that no rendering derived from
   the root-family verb ("stood") can be produced — root relation never
   licenses lexeme translation.

3. **Pronoun-referent ambiguity.** A `pronoun_referent_edge` case where the
   referent is genuinely contested across sources (e.g. the object pronouns
   of `quran:48:9` وَتُعَزِّرُوهُ وَتُوَقِّرُوهُ, a classical referent split) —
   contrast with the certified-unambiguous هِ of `quran:61:5:4` (referent:
   Mūsā). The fixture must show the translation carrying the attributed
   ambiguity (both referent readings retained) rather than silently choosing.

4. **Attachment ambiguity.** لَمَآ at `quran:3:81:6` — the 2026-07-29
   two-vote wave-1 substantive-arbitration case. The fixture must show that
   while attachment/function is in arbitration, translation renders from the
   unresolved state, and that when arbitration lands, the translation
   regenerates from the certified fact (revocation propagation reaching the
   translation stratum).

5. **Same-facts-different-context-translation.** The p007 pair
   `quran:2:34:5` لِءَادَمَ ("[prostrate] **to** Adam") vs `quran:12:31:24`
   لِلَّهِ ("**for/belongs to** God") —
   (`qamus/examples/website-payloads/p007_li_adam_clean.payload.json`,
   `p007_lillahi_fused.payload.json`). Same certified particle entry+sense
   facts; context legitimately selects different English. The fixture must
   show the divergence is recorded as contextual rendering choice with its
   reason, never as a fact fork (the underlying artifacts keep their own
   hashes; parity is per-occurrence, not per-particle).

## 3. Boundaries restated

- No translation system, schema, or tooling is authorized by this doc.
- Any future translation lane enters through the standard machinery: schema
  first, validator red-first, wired into `tools/check_regressions.py`,
  fixtures 1–5 above committed before any bulk rendering.
- Public-boundary rules apply unchanged: no external translation text copied,
  authored renderings only, `informed_by` never leaks
  (`AGENTS.md`, `provenance/source-boundaries.md`).

---
Verified against: commit 637d7da (origin/main, 2026-07-29). Artifacts:
`qamus/examples/website-payloads/{unresolved_ma_2_284_2,multi_entry_liqawmihi_61_5_4,p007_li_adam_clean,p007_lillahi_fused}.payload.json`,
`qamus/examples/proof-particle/`, `qamus/examples/p007-li-pilot/README.md`,
`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md`; §29 ruling transcribed from the owner
decision ledger tail (2026-07-29); `tools/check_regressions.py`
ALL REGRESSION CHECKS PASS.
