# FAM4 finite-verb producer design

## Scope

FAM4 owns only the `finite_verbs` STRAT family. It processes the complete
12-row calibration population, in candidate mode, using caller-supplied
stratified rows, v575 verdicts, whitelist context rows, and entry records.
`derived_verbs` remains outside this owner boundary. Any derived or
quadriliteral verb observed in the FAM4 population receives a typed
`owner_gated` route and no finite-verb analysis.

## Contract

The producer emits an F-A `qamus.typed_claim_contract.v1` record per row.
Candidates require:

- an exact written-form match to a caller-supplied verb entry, with a
  quran-token address and entry-form address;
- a registered Form-I pattern;
- all three root radicals located as letter-level spans in the written
  surface;
- explicitly owned person/tense affix spans, when the pattern requires them;
- a passed reconstruction proof whose concatenated spans equal the canonical
  surface; and
- a separate `Naḥw — what this piece does here` overlay only for independently
  sourced syntactic context. Mood/case is never stored as a finite-verb
  morphology claim.

The producer never derives a fact from a label, gloss, morphline, or existing
carrier label. The whitelist entry ID is recorded as a context edge and is not
used as the base source until the observed surface matches an entry field.

## Closed registry and guards

`verb-affix-registry.jsonl` contains only the supported Form-I patterns and
the shared `qg-subject-pronoun` / `qg-object-pronoun` component classes. The
Form-V/VI prefix `ت` is registered as
`derivative_prefix_form_v` only as a non-supported owner-gated marker; it is
never treated as a person prefix by this producer.

`weak-root-defeater-registry.jsonl` records hidden/alternating weak-root
patterns and their future `derived_verbs` owner. None is currently a
registered transformation rule, so FAM4 routes those surfaces to
`weak_root_pattern_unresolved`.

## Routes

The typed route set is:

`candidate`, `owner_gated`, `weak_root_pattern_unresolved`,
`surface_not_finite_verb`, `label_only_affix_evidence_missing`,
`subject_object_suffix_ambiguity`, `orthography_mismatch`,
`entry_lookup_missing`, `entry_join_ambiguity`, and
`input_verdict_not_verified`.

Only `candidate` carries a claim and `finite_verb_evidence`. Every other
route carries exactly one pending fact with a blocker and no claim.

## Reuse and boundaries

The implementation reuses the F-A contract validator and the established
FAM2 carrier shape. It does not create a second projection pipeline. It
references the clitic producer’s subject-marker classes through the shared
verb-affix registry. All outputs remain `pre_apply_not_authorized`, with
public and live materialization disabled.

## Verification

RED fixtures cover at least six positive Form-I cases and six adversarial
cases, including label-only tense, hidden weak radical, derived-form owner
gating, subject/object suffix boundaries, and a non-verb family mislabel.
The fixture validator, focused unit tests, committed packet validator, report
renderer, and full regression harness are required to pass. No corpus file is
copied into the repository and no image artifact is tracked.
