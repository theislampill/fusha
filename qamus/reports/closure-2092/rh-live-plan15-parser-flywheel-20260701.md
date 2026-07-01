# RH-LIVE Plan 15 parser flywheel handoff (2026-07-01)

Status: public-safe Fusha flywheel handoff. This is not live Qamus coverage
progress and it does not mutate any live Qamus state.

Controlling plan: `15-fusha-parser-coverage-boundary-and-lexicon-flywheel.md`.
Current Fusha commit used by this handoff:
`ed6b33a1f1d2c7600bebba6de728dfd566286f8c`.

## Boundary

The Fusha parser is used here as a structured gate and factory interface, not
as an oracle. Parser-known rows may accelerate clitic, sarf, nahw, qg-class,
and public/private projection checks. Parser-partial rows, root-null rows, and
lemma-null rows are not generic blockers; they become exact flywheel routes.

The raw executor route packets are external local executor artifacts and are
not vendored into this public repo because they include local rollout
provenance. This handoff records only public-safe counts, route classes, and
checksums needed to queue reusable Fusha work.

## Parser coverage boundary

| metric | count |
|---|---:|
| rows audited | 5,075 |
| rows parser-known | 911 |
| rows parser-partial | 4,164 |
| rows parser-unknown | 0 |
| root-null rows | 5,043 |
| lemma-null rows | 4,089 |
| fixture-level governor rows | 754 |
| rows converted to lexicon_entry_needed | 3,403 |
| rows converted to stem_entry_needed | 0 |
| rows converted to pattern_rule_needed | 3 |
| rows converted to governor_irab_fixture_needed | 754 |
| rows converted to owner/scholar/source packets | 0 |
| candidate rows safely accelerated by parser | 911 |
| candidate rows rejected because parser evidence was incomplete | 0 |

## Per-scope coverage

| scope | rows | parser-known | parser-partial | root-null | lemma-null | fixture-level governor | parser-accelerated |
|---|---:|---:|---:|---:|---:|---:|---:|
| VN-00 append | 231 | 2 | 229 | 229 | 228 | 59 | 2 |
| VN-00 replacement | 855 | 41 | 814 | 841 | 792 | 208 | 41 |
| VN-01 append | 2,047 | 473 | 1,574 | 2,039 | 1,552 | 244 | 473 |
| VN-01 replacement | 168 | 3 | 165 | 166 | 164 | 21 | 3 |
| VN-02 append | 1,677 | 391 | 1,286 | 1,671 | 1,257 | 214 | 391 |
| VN-02 replacement | 97 | 1 | 96 | 97 | 96 | 8 | 1 |

## Flywheel routes

| route | rows | packet sha256 |
|---|---:|---|
| lexicon_entry_needed | 3,403 | `8685c22b8dc2d2ece9ada4419bf7d692dca4e4127820d90eb8a2834baa5f8c10` |
| governor_irab_fixture_needed | 754 | `3add2fa1d0188ef2b2d0902b3b11c26e1ded77f06e87a367b1a8926cd8136013` |
| parser_interface_ok | 910 | `f7ec445f8a0b46dd643a2512cef4335edd4bddefddd7c2db2a7aa4cd2d26ed2d` |
| particle_function_rule_needed | 2 | `3adb80d58e261f1d94fd89d4f94c57294d0fdc489dd44cad00bc214c6f61e84a` |
| pattern_rule_needed | 3 | `1a39d5ae9c2ca0b462b03da4c748c574af7d71f17598178f316abbb225875a3a` |
| proper_name_no_root_needed | 3 | `682ff9601c0828f2267ca3b667f4f4f67b8a383b9bf8d09b22589d76421bd8df` |

Parent manifest sha256:
`f30721e16a756a692af6c28f55844105f9dde8284320d7a25af456215eaf2cb2`.

## Public-safe sample import

Generator added:
`tools/import_rh_live_plan15_flywheel.py`

Validator added:
`tools/validate_rh_live_plan15_flywheel.py`

Generated sample artifacts:

- `qamus/examples/rh_live_plan15_parser_flywheel.sample.jsonl`
- `qamus/examples/rh_live_plan15_parser_flywheel.sample.meta.json`

The sample imports 17 representative rows across the six route families. It
keeps source key, loc, surface, parser status, null-root/null-lemma flags,
segments found/needed, qg classes, and route class, but drops executor-local
paths and live deployment provenance. It is a Fusha flywheel queue sample, not a
live Qamus payload.

Full sanitized local queue proof:

- `out/rh-live-plan15-parser-flywheel/rh_live_plan15_parser_flywheel.full.jsonl`
- `out/rh-live-plan15-parser-flywheel/rh_live_plan15_parser_flywheel.full.meta.json`

The full queue contains all 5,075 rows and is intentionally ignored output, not
a committed artifact.

Validation:

- `python tools/validate_rh_live_plan15_flywheel.py --self-test`: pass.
- `python tools/validate_rh_live_plan15_flywheel.py qamus/examples/rh_live_plan15_parser_flywheel.sample.jsonl`: pass, 17 rows.
- `python tools/validate_rh_live_plan15_flywheel.py out/rh-live-plan15-parser-flywheel/rh_live_plan15_parser_flywheel.full.jsonl`: pass, 5,075 rows.
- `python tools/check_regressions.py`: pass with the RH-LIVE Plan 15 flywheel
  sample and regenerated full queue checks wired into the regression spine.

The validator enforces the Plan 15 boundary: each row must be a
`qamus/flywheel-artifact@1` item, route through an exact parser/sarf/nahw/qamus
Mode A lane, keep claim-boundary flags false, use accepted `qg-*` classes, and
avoid public leakage of local paths, source labels, process labels, or secret
markers.

## Route semantics

- `parser_interface_ok`: parser structure is useful enough as a gate/factory
  interface for the rollout candidate. It still does not certify live coverage
  by itself.
- `lexicon_entry_needed`: populate or queue Qamus-derived lemma/root/stem facts
  where the entry data and source-address graph support them. Do not infer
  roots from resemblance.
- `governor_irab_fixture_needed`: create source-addressed governor/irab
  fixtures or scholar packets. Correct gloss with weak reason is unsafe.
- `particle_function_rule_needed`: add focused function-token rule/eval cases
  before bulk reuse.
- `pattern_rule_needed`: add a reusable morphology pattern or compatibility
  fixture, then rerun affected rows.
- `proper_name_no_root_needed`: add explicit no-root/proper-name fixture
  handling, not a guessed root.

## Claim boundary

This handoff is not arbitrary-text parser completeness. It is not live Qamus
coverage progress. It records that VN-00,
VN-01, and VN-02 local candidate queues were audited through the Plan 15
boundary and that parser gaps became exact Fusha flywheel routes instead of
generic blockers.

## Next Fusha work

1. Promote selected rows from the sanitized full queue into lexicon/stem,
   governor/i'rab, particle, pattern, and no-root fixture patches.
2. Add lexicon/stem entries only where Qamus entry data and source-addressed
   evidence support them.
3. Add governor/irab fixtures for the 754 fixture-level governor rows or route
   them to scholar packets when the grammatical reason is not certifiable.
4. Add regression cases for the particle, pattern, and proper-name no-root
   route families.
5. Rerun the VN factory parser-boundary audit after those reusable Fusha
   updates land.
