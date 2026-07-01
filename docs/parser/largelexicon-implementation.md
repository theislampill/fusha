# Largelexicon Implementation

Largelexicon implements the first measured bridge from the Qamus 2,092-entry
dataset into Fusha parser/checker tooling.

## Implemented Lanes

- P0: claim boundary, source ledger extension, freshness-bearing inventory, and
  no-live-mutation wording.
- P0.5: the existing Mode A thin slice remains the vertical proof that a
  visible qword can carry source/private trace, public projection, rendered
  readback fixture, and flywheel artifact before broad expansion.
- P4/P5: explicit full-table allowlist plus committed Qamus-authored
  source-clean lemma/form/stem tables and a manifest-backed sharded qword
  denominator table. Raw QAC/MCP/API/source evidence remains private
  adapter/cache data.
- P1/P8: Qamus-authored lemma/form/stem sample and full-table generation plus
  morphology validators and generation keys.
- P2/P9/P10: opt-in `--db largelexicon` parser/analyzer path while preserving
  `smoke` as the default; the large table is a candidate/ranking substrate, not
  a trained statistical/dependency claim.
- P0/P1 collision safety: match-basis tagging, high-risk function/proper-name
  routing, and validator fixtures prevent `morphology_candidates[0]` from being
  projected as a hover when larger tables create short-token collisions. See
  `docs/parser/largelexicon-collision-safety.md`.
- P11: compact all-visible-qword denominator rows for Qamus rollout support,
  preserving entry/card/qword handles without live mutation.
- P6/P12: sarf, nahw, curriculum, drill, claim-card, and tutor-routing backfill
  surfaces.
- P3: all visible qword-style Mode A worklist sample for Qamus rollout support,
  plus sarf, nahw, curriculum, drill, and tutor-routing backfill surfaces.

## CLI Contract

```powershell
python tools/build_largelexicon_source_inventory.py --sample-size 120 --commit-full --out-dir out/largelexicon
python tools/build_largelexicon_morph_db.py --sample-size 480 --commit-full --out-dir out/largelexicon
python tools/fusha_standalone_parse.py --db largelexicon --text "خَاضُوا"
python tools/fusha_morph_analyze.py --db largelexicon --surface "خَاضُوا"
python tools/fusha_morph_generate.py --db largelexicon --generation-key "qamus:00107b99a50e:000"
python tools/fusha_largelexicon_cli.py analyze-token --surface "خَاضُوا"
python tools/fusha_largelexicon_cli.py analyze-card --text "إنما الأعمال بالنيات"
python tools/build_largelexicon_qamus_mode_a_worklist.py --limit 160
python tools/project_largelexicon_qamus_hover_candidates.py
python tools/build_largelexicon_flywheel_artifacts.py
python tools/validate_largelexicon_source_ledger.py --self-test
python tools/validate_largelexicon_table_manifest.py --self-test
python tools/validate_largelexicon_table_reader.py --self-test
python tools/validate_largelexicon_morph_db.py --self-test
python tools/validate_largelexicon_parser.py --self-test
python tools/validate_largelexicon_qamus_mode_a.py --self-test
python tools/validate_largelexicon_qg_projection.py --self-test
python tools/validate_largelexicon_cli_contract.py --self-test
```

## ANDON Rules

Stop the affected row or artifact, not the whole branch, when:

- source ledger freshness fails;
- a full table is absent from the explicit source-clean allowlist;
- a no-root row lacks a no-root reason;
- public fields leak external source labels or local/server paths;
- visible segments do not concatenate to the Arabic surface;
- the parser certifies arbitrary text rather than emitting a candidate;
- a collision-gated token emits a public hover from a forbidden selected
  candidate;
- a Qamus Mode A worklist row lacks source-address/crosswalk routing;
- a sarf or nahw lesson remains only in chat instead of a file, fixture, or
  packet.

## Qamus Executor Boundary

Fusha produces candidate/support artifacts. The Qamus executor owns live
whitelist backup, append/replacement policy, restart/reload, DOM/mobile
readback, public health, DUV/static verification, commits, rollback, and final
tranche closure claims.

## Current Measured Denominators

- Qamus lemma rows: 2,092.
- Qamus form/stem rows: 8,483.
- Qamus all-visible-qword denominator rows: 117,117, stored as one logical
  manifest-backed table under `qamus/indexes/largelexicon/qword-denominator/`.
- Qamus entries acknowledged by the qword manifest: 2,092; entries with qword
  rows in the current export: 2,091; current source-card repair packet: `n993`
  / `مَلْجَأ` (`pg443.jpeg`, candidate ref `42:47`).
- Current largelexicon parser scope: dependency-free candidate analysis over
  committed Qamus-derived tables, plus smoke arbitrary input. It is not yet a
  CAMeL/MADAMIRA/Stanza-equivalent analyzer, trained statistical disambiguator,
  or certified dependency/i'rab parser.
