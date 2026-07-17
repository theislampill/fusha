# FAM3 Number-Word Formation-Evidence Producer Design

## Status

Pre-approved by the FAM3 execution brief. This document records the bounded
candidate-only implementation contract; it does not authorize source, public,
whitelist, renderer, or runtime mutation.

## Goal

Build a self-contained number-word producer for all 57 `number_words` rows. A
candidate is emitted only when the row's whitelist-linked entry supplies an
orthography-guarded base and a registered number-paradigm rule reconstructs the
observed written form. Every other row becomes a typed unresolved record.

## Survey boundary

The producer surveys these requested shapes before projection:

- bare cardinals;
- gender-polarity cardinals with an evidenced counted noun;
- ordinals;
- compound numbers 11–19;
- tens;
- fractions;
- أول/آخر-type edge words;
- other number forms and non-number surfaces that were assigned to the family
  by the stratification fallback.

Only shapes recognized in the 57-row input or in the required red-first
fixtures receive a registered rule. A shape with no supporting evidence is
reported as zero-population and remains unresolved if encountered.

## Architecture and data flow

`tools/fam3_number_producer.py` is the one family producer. It reuses the FAM2
exact-written-surface helpers, F-A fact carrier shape, typed-claim validator,
and shared fact-derived learner view. It uses `WhitelistIndex` from the VNMAP
entry-card builder for the location-to-entry join; the whitelist `entry_id` is
retained as a verse-context edge and never treated as a lexeme assertion by
itself.

The CLI requires caller-supplied stratification, verdict, whitelist, and entry
files. It selects all 57 family rows, verifies verdict-location coverage, joins
each row to its whitelist entry, and emits one candidate or typed unresolved
record per row. The committed fixture validator uses only repository files; it
never needs the external corpus.

## Formation contract

Positive records contain:

- an `entry_base_attestation` fact naming the exact entry field and base
  surface;
- one dependent `formation_evidence` fact with `sub_shape`, `pattern_id`,
  `evidence_mode`, source addresses, guards, defeaters, and reconstruction
  proof;
- an exact Unicode occurrence span and a fact-bound claim envelope;
- generated learner copy with the literal public labels
  `Ṣarf — how this piece forms the word` and
  `Naḥw — what this piece does here`;
- `candidate` status with `pre_apply_not_authorized`,
  `public_materialization_allowed=false`, and `live_mutation_allowed=false`.

The registered patterns cover the evidenced cardinal/base and visible
case-form routes, visible tāʾ-marbūṭa gender-polarity form, ordinal
cardinal-to-fāʿil pattern, compound 11–19 component pairing, tens suffix
forms, and the observed pairwise/other-number route. The pattern matcher uses
the FAM2 orthography guard: hamza seats, tāʾ/هāʾ, defective spellings, and
unsupported near-misses abstain.

Typed unresolved records carry a closed route such as
`entry_lookup_missing`, `source_gap`, `orthography_mismatch`,
`homograph_ambiguity`, `gender_polarity_mismatch`, or `pattern_unresolved`.
They contain no formation claim. Labels, English glosses, morphlines, and
context-only joins never create a formation fact.

## Homograph and context gates

Explicit ambiguity flags or multiple candidate readings fail closed before
pattern matching. The fixtures include the number/noun homograph `سبع` and a
context-only whitelist join. Gender-polarity projection requires visible
formation evidence for the counted noun and rejects the wrong-gender form.
Compound projection requires adjacent, source-addressed number components;
missing components remain pending.

## Validation and artifacts

The fixture set contains at least six positives and six adversarial negatives,
including the required label-only ordinal, wrong-gender, homograph, and
context-only cases. The explicit calibration writes all 57 records, split
positive/unresolved JSONL, a summary, and fixture proof artifacts under the
FAM3 example directory. `FAM3-REPORT.md` records the survey populations,
precision and abstention by sub-shape, per-row outcomes, zero-false-projection
attestation basis, exact nonclaims, and compounding impact.

The full regression harness runs the FAM3 fixture self-test, unit tests,
packet validator, central projector registration, RM-09/no-image hygiene, and
the existing FAM2/VNMAP gates. No external input file is copied or tracked.

## Exact nonclaims

The packet is not scholarly certification, independent linguistic gold, or a
corpus-wide precision measurement. An entry-linked context edge is not proof
that the entry is the lexeme for every occurrence. A candidate learner view is
not a public hover, whitelist append, release, or runtime authorization. An
unobserved or unsupported number shape is not inferred from the registry.
