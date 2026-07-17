# FAM2 Lexical Formation-Evidence Producer Design

## Status

Pre-approved by the FAM2 execution brief. This document records the bounded implementation contract; it does not authorize whitelist, renderer, live, publication, or corpus mutation.

## Goal

Build a candidate-only, source-addressed formation-evidence producer for the `lexical_nouns_adjectives` family, run it on a deterministic representative sample of at least 40 of the 121 stratified rows, and prove that every projected label is backed by typed facts that a learner can reconstruct.

## Boundary and nonclaims

- The external stratification, verdict, whitelist, and entry files are read-only and are accepted only through explicit CLI arguments.
- The repository commits a small fixture subset and generated calibration/proof artifacts only; it never embeds a lane-workspace path or uses an external-input default.
- The producer owns formation facts for broken plural, sound masculine plural, sound feminine plural, dual, nisba adjective, and elative only when the exact input carries the required evidence. Generic English glosses and unverified morphlines are never evidence.
- A label-only broken-plural input, including the real `سُفَهَاء` 2:13 canary row without a singular link, emits a typed unresolved record (`entry_lookup_missing`, `pattern_unresolved`, or `source_gap`) and never a candidate projection.
- The first positive worked proof is an exact fixture for the same `سُفَهَاء` occurrence with an entry-backed singular form and the named `فَعِيل→فُعَلَاء` pair. It remains a candidate, not certification.
- No generated record authorizes a whitelist append, renderer output, public materialization, restart, deployment, commit, push, release, or live mutation.

## Architecture and data flow

The producer is `tools/fam2_lexical_producer.py`. It uses `tools.typed_claim_contract` for the closed F-A envelope, `tools.fact_projectors` for a registered projector contract, and the existing `tools.fd_compiler` for fact-derived learner views, matrix accounting, exact span reconstruction, compact/expanded payload identity, and candidate-only routing. There is no second projection or renderer pipeline.

The operational path is:

1. Load the family rows and verdicts, join by exact location, and select a stable priority-balanced sample from the 121 rows.
2. Load the caller-supplied corpus and entries into memory. Entry lookup is exact over headword/usage-form addresses; it may produce a singular/plural pair only when a named registry rule matches both written forms without orthographic repair.
3. Run the registered FAM2 projector. Positive records are F-A `projection_input` envelopes. Missing or conflicting evidence produces an F-A `unresolved_projection` envelope with a typed route and no claim.
4. Pass the records into the shared compiler. The compiler derives only plain-English learner fields from typed fact values and exact written spans, using the literal labels `Ṣarf — how this piece forms the word` and `Naḥw — what this piece does here`.
5. Write deterministic JSONL/JSON/Markdown artifacts without serializing external paths. The calibration packet is bounded; it is not a corpus-wide rerun.

## Formation fact contract

Each positive formation fact carries:

- canonical occurrence, exact Unicode span and written surface;
- `primary` and `secondary` ownership;
- `evidence_mode`, source address, source evidence, producer/version, rule ID, and projector ID;
- guards, defeaters, unresolved blockers, dependencies, and a nonempty reconstruction proof;
- fact values naming `sub_shape`, `singular_surface` when applicable, `plural_surface` when applicable, `pattern_id`, and the exact paired pattern names.

The allowed positive modes are direct source attestation, deterministic derivation from certified entry facts, and paired-form inference. The latter is emitted only after the entry-backed forms and the registered pattern match pass. Orthography variants are hard defeaters: hamza-seat differences, `ة`/`ه` differences, defective spellings, and any diacritic mismatch outside an explicitly supported inflectional ending route to a typed abstention.

The pattern registry contains only rules exercised by the fixture/calibration inputs. It includes the `فَعِيل→فُعَلَاء` broken-plural rule plus the sound masculine, sound feminine, dual, nisba, and elative rule families. Registry rows are named, versioned, and bound to the registered projector; adding a rule does not weaken the matcher.

## Learner projection

The shared compiler produces a projection only when the typed fact is positive and exact reconstruction passes. The generated copy exposes the sub-shape, the entry-backed pair, the named pattern pair, and the exact occurrence span. Ṣarf explains how the piece forms the word; Naḥw explains its local role from the row’s supplied dependency evidence when available. No English gloss is used to create a formation fact, and no source prose, internal route code, path, or process term is placed in learner text. Unresolved rows carry the mapped plain-English unresolved statement and no linguistic claim.

## Fixtures and calibration

The committed fixture set contains at least six positives and six adversarial negatives. Required negatives are the label-only `سُفَهَاء` canary, a sound plural that resembles a broken pattern, a missing singular lookup, and a noun/adjective homograph ambiguity. Additional negatives cover hamza-seat mismatch, `ة`/`ه` mismatch, defective spelling, and unverified-morphline-only input. The calibration artifact contains at least 40 exact family rows, includes all supported sub-shape routes where the input exposes them, and records one typed outcome per row.

## Validation and rollback

`tools/validate_fam2_lexical.py` validates the committed fixtures, calibration packet, proof chain, report recomputation, N-LANG cleanliness, no-live flags, no absolute paths, and zero false projections. `tools/check_regressions.py` invokes its fixture-only self-test and focused tests. Rollback is limited to removing FAM2-specific code, registry rows, fixtures, reports, and the harness hook; external corpus and public/runtime surfaces remain untouched.

## Exact nonclaims

- Candidate formation facts are not scholarly certification.
- A matched entry form is not a claim about every occurrence of that lexeme.
- The 40-plus-row packet is not corpus-wide accuracy, coverage, or production readiness.
- The real label-only canary remains unresolved unless an explicit entry-backed singular and pattern pair are supplied.
- Generated Ṣarf/Naḥw copy is not permission to publish or materialize a hover.
- Pattern registry reach is not evidence that any unobserved row has that formation.
