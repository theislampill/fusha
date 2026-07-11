# Largelexicon data card

## Scope

This release describes five committed, source-clean, Qamus-authored largelexicon
row families:

1. `lemma-source`
2. `form-source`
3. `stem-source`
4. `qword-denominator`
5. `qword-crosswalk`

The first three are full JSONL tables. The qword families are logical JSONL
tables whose ordered shards are named by committed manifests. This repository
does not mutate the live Qamus site, and none of these tables is evidence of live
hover coverage or production deployment.

## Source and provenance

The input is `qamus/data/current/entries.jsonl`, containing 2,092 authored Qamus
entries. `RELEASE.json` records its byte-level SHA-256, the exact logical output
SHA-256 and row count for every family, the release-generator identity, and the
caller-supplied `built_at` value. External corpora and gloss text are not inputs
to this public release. The public boundary remains authored English from Qamus.

## Row contracts and validation state

The five `qamus/schemas/largelexicon-*.schema.json` files define the migration
target at row version `@2`. They require an RM-23-shaped root or a non-empty
`no_root_reason`, single-token surfaces unless an explicit multiword escape is
present, empty `risk_flags`, and an all-non-empty-or-all-absent
`pattern`/`form`/`features` stem annotation trio. Repeated table constants belong
in the release or table manifest rather than each row.

The committed tables remain at row version `@1` by design in RM-22: this lane is
not authorized to regenerate or edit data. Consequently the validator reports
current migration violations instead of dropping, repairing, or relabeling rows.
A non-zero normal validation exit is expected until an owner-authorized data
regeneration migrates the tables to `@2`.

The RM-23 source audit measured 133 raw root-shape failures (118 verbatim-word
copies, seven slash composites, seven tatweel-heh notations, and one
parenthesized root) and 263 non-single-token source surfaces, including 35
gloss-bearing surfaces. At the current committed table head, those defects map
to:

- `lemma-source`: 133 root-shape rows and 219 multiword lemma rows;
- `form-source`: 239 propagated root-shape rows and 261 multiword surface rows;
- `stem-source`: 239 propagated root-shape rows and 261 multiword surface rows.

The difference between 263 audited source surfaces and 261 generated form/stem
rows is expected: RM-23 quarantined two source surfaces before these generated
families. The validator retains the full denominators and separately counts all
non-empty `risk_flags`; it performs no silent filtering.

## POS mapping disclosure

At this release head, the generated lemma table classifies 970 rows as `verb`,
966 as `noun`, 56 as `proper_noun`, and 100 as `particle`. The authoritative
source-section/manifests split is 947 `verb`, 1,045 `noun`, and 100 `particle`.
Both views total 2,092. This is disclosed classification drift, not entry-count
drift; consumers must choose the view appropriate to their task.

## Intended use

These tables support offline candidate lookup, morphology experiments, source
address routing, and review-packet generation. They are appropriate for recall
and review assistance. They do not certify a root, sense, gloss, iʿrāb decision,
or arbitrary-text parse, and they must not be used to bypass owner review.

## Known limitations

- Current rows are `@1` inputs audited against stricter `@2` schemas.
- Empty or non-Arabic qword normalization keys may be legitimate punctuation or
  Qurʾānic marks; their existing route/status fields remain authoritative.
- `risk_flags` indicate review or quarantine requirements, not permission to
  discard records.
- Stem annotations are currently emitted as an empty trio and therefore fail the
  `@2` all-non-empty-or-all-absent rule.
- Sharded logical SHA-256 values depend on manifest shard order and exact bytes.

## Reproduction

Run from the repository root:

```text
python tools/validate_largelexicon_rows.py --self-test
python tools/validate_largelexicon_rows.py
python tools/validate_largelexicon_rows.py --check-release --built-at 2026-07-11T14:05:10Z
```

To regenerate only the deterministic release manifest, explicitly supply the
timestamp (the tool never reads the wall clock):

```text
python tools/validate_largelexicon_rows.py --write-release --built-at 2026-07-11T14:05:10Z
```

Rollback is `git revert` of the RM-22 commit. Table regeneration, live mutation,
integration-gate wiring, publication, and deployment are outside this brief.
