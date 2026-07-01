# RH-LIVE Plan 15 VN-01/VN-02 subword graph supplement (2026-07-01)

Status: public-safe Fusha flywheel supplement. This is not live Qamus
coverage progress and it does not mutate any live Qamus state.

Controlling plan: `15-fusha-parser-coverage-boundary-and-lexicon-flywheel.md`.
Current Fusha commit used by this supplement:
`6a475e62addb17172b05054e6e08713974b14848`.

## Boundary

This supplement records the VN-01/VN-02 subword-upgrade rows that passed the
source-address graph gate after the Plan 15 parser-boundary pass. The parser is
used as a structured gate/factory interface, not as an oracle. Parser-known
rows may accelerate checks; parser-partial, parser-unknown, root-null, and
lemma-null rows become exact Fusha flywheel routes.

The raw executor route packets are not vendored into this public repo. This
handoff records only public-safe counts, route classes, and checksums needed to
queue reusable Fusha work.

## Parser coverage boundary

| metric | count |
|---|---:|
| rows audited | 177 |
| rows parser-known | 2 |
| rows parser-partial | 52 |
| rows parser-unknown | 123 |
| root-null rows | 172 |
| lemma-null rows | 171 |
| fixture-level governor rows | 9 |
| rows converted to lexicon_entry_needed | 161 |
| rows converted to stem_entry_needed | 161 |
| rows converted to pattern_rule_needed | 24 |
| rows converted to governor_irab_fixture_needed | 9 |
| rows converted to owner/scholar/source packets | 0 |
| candidate rows safely accelerated by parser | 2 |
| candidate rows rejected because parser evidence was incomplete | 0 |

## Per-scope coverage

| scope | rows | parser-known | parser-partial | parser-unknown | root-null | lemma-null | fixture-level governor |
|---|---:|---:|---:|---:|---:|---:|---:|
| VN-01 subword-upgrade graph-accepted | 104 | 2 | 35 | 67 | 99 | 98 | 4 |
| VN-02 subword-upgrade graph-accepted | 73 | 0 | 17 | 56 | 73 | 73 | 5 |

## Flywheel routes

| route | rows | packet sha256 |
|---|---:|---|
| lexicon_entry_needed | 161 | `107d4a6d6be3718d2cefd6e025698cec74f297ac5dc9b0e637c19651e65838de` |
| stem_entry_needed | 161 | `a03deb2fa0d084ee0c94eb9d9cdd983f86b8816517f997d810df9a62e4a118e0` |
| pattern_rule_needed | 24 | `9299c378d7435b240cb9d62845c2772d27d3048812fcbeed237250b7c0ebf438` |
| particle_function_rule_needed | 12 | `b9dd1f99412b7c79ede2c976005333aae31dbe2a28f1fa42efc581256fbec7b9` |
| governor_irab_fixture_needed | 9 | `4ef17bb55b4ef94930346dd107884a010395d3524a4c9877087cd27081cf3830` |
| parser_interface_ok | 2 | `8f233344612a82df5c349a7802f2c72edded52f23c3f1aa4d8b25942cde33381` |

Parent route summary sha256:
`dcc91f90476f93ca785160008669ffc31f8837b2f4566f034a2de8c61d579bd9`.

## Public-safe sample import

Generator:
`tools/import_rh_live_plan15_flywheel.py`

Validator:
`tools/validate_rh_live_plan15_flywheel.py`

Generated sample artifacts:

- `qamus/examples/rh_live_plan15_vn01_vn02_subword_graph.sample.jsonl`
- `qamus/examples/rh_live_plan15_vn01_vn02_subword_graph.sample.meta.json`

The sample imports 17 representative rows across the six route families,
including the new `stem_entry_needed` route. It keeps source key where
available, loc, surface, parser status, null-root/null-lemma flags, segments
found/needed, qg classes, and route class. It drops executor-local paths and
live deployment provenance. It is a Fusha flywheel queue sample, not a live
Qamus payload.

Sample sha256:
`fe0176a388941a31b9f781c3b4f30f701102b3546a5dc8679ca5268b46196bb6`.

Sample meta sha256:
`25f26bc371d86cf09af9b49236bb22b54e0a1ed922e233f5aee34b9d8971d085`.

## Route semantics

- `parser_interface_ok`: parser structure is useful enough as a gate/factory
  interface for the rollout candidate. It still does not certify live coverage
  by itself.
- `lexicon_entry_needed`: populate or queue Qamus-derived lemma/root facts
  where the entry data and source-address graph support them. Do not infer
  roots from resemblance.
- `stem_entry_needed`: populate the exact visible stem and inflection pieces
  needed for reusable subword-complete RH-LIVE hovers. Do not collapse
  prefix/stem/suffix rows into broad whole-token glosses.
- `governor_irab_fixture_needed`: create source-addressed governor/i'rab
  fixtures or scholar packets. Correct gloss with weak reason is unsafe.
- `particle_function_rule_needed`: add focused function-token rule/eval cases
  before bulk reuse.
- `pattern_rule_needed`: add a reusable morphology pattern or compatibility
  fixture, then rerun affected rows.

## Claim boundary

This supplement is not arbitrary-text parser completeness. It is not live Qamus
coverage progress. It records that VN-01 and VN-02 graph-accepted subword rows
were audited through the Plan 15 boundary and that parser gaps became exact
Fusha flywheel routes instead of generic blockers.

## Next Fusha work

1. Promote selected `stem_entry_needed` rows into reusable stem/inflection
   fixtures where Qamus entry data and source-addressed evidence support them.
2. Add pattern-rule fixtures for derivative prefixes, verb prefix/stem/subject
   suffixes, and plural suffix rows exposed by this supplement.
3. Add function-token cases for lam/preposition/pronoun clusters before bulk
   reuse.
4. Add governor/i'rab fixtures for the nine fixture-level governor rows or
   route them to scholar packets when the grammatical reason is not certifiable.
5. Rerun the VN factory parser-boundary audit after those reusable Fusha
   updates land.
