# Largelexicon Implementation

Largelexicon implements the first measured bridge from the Qamus 2,092-entry
dataset into Fusha parser/checker tooling.

## Implemented Lanes

- P0: claim boundary, source ledger extension, freshness-bearing inventory, and
  no-live-mutation wording.
- P1: Qamus-authored lemma/form/stem sample generation plus morphology
  validators.
- P2: opt-in `--db largelexicon` parser/analyzer path while preserving `smoke`
  as the default.
- P3: all visible qword-style Mode A worklist sample for Qamus rollout support,
  plus sarf, nahw, curriculum, drill, and tutor-routing backfill surfaces.

## CLI Contract

```powershell
python tools/build_largelexicon_source_inventory.py --sample-size 100 --out-dir out/largelexicon
python tools/build_largelexicon_morph_db.py --sample-size 400 --out-dir out/largelexicon
python tools/fusha_standalone_parse.py --db largelexicon --text "خَاضُوا"
python tools/fusha_morph_analyze.py --db largelexicon --surface "خَاضُوا"
python tools/build_largelexicon_qamus_mode_a_worklist.py --limit 160
python tools/project_largelexicon_qamus_hover_candidates.py
python tools/build_largelexicon_flywheel_artifacts.py
python tools/validate_largelexicon_source_ledger.py --self-test
python tools/validate_largelexicon_morph_db.py --self-test
python tools/validate_largelexicon_parser.py --self-test
python tools/validate_largelexicon_qamus_mode_a.py --self-test
python tools/validate_largelexicon_qg_projection.py --self-test
```

## ANDON Rules

Stop the affected row or artifact, not the whole branch, when:

- source ledger freshness fails;
- a no-root row lacks a no-root reason;
- public fields leak external source labels or local/server paths;
- visible segments do not concatenate to the Arabic surface;
- the parser certifies arbitrary text rather than emitting a candidate;
- a Qamus Mode A worklist row lacks source-address/crosswalk routing;
- a sarf or nahw lesson remains only in chat instead of a file, fixture, or
  packet.

## Qamus Executor Boundary

Fusha produces candidate/support artifacts. The Qamus executor owns live
whitelist backup, append/replacement policy, restart/reload, DOM/mobile
readback, public health, DUV/static verification, commits, rollback, and final
tranche closure claims.
