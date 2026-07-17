# FB1 Predicate v3 Design

**Status:** pre-approved for implementation by the PREDV3 lane instruction.

## Goal

Add `pred_fb1_clitic_pronoun_v3` beside the unchanged v1 and v2 predicates. V3 keeps the v2 exact attached-role admission and adds a narrowly empirical fallback for generic pronoun-family role names when the immediately preceding segment is a known governor/host.

## Predicate contract

The decision order is:

1. If `morphology_family` or `family` is present, return whether it equals `clitic_pronoun_compositions`.
2. Otherwise retain every v2 admission: a non-leading role in `FB1_ATTACHED_ROLE_REGISTRY`, or a typed `subject_pronoun` after a `qg-verb-stem`.
3. Otherwise inspect non-leading segments whose role contains `pronoun`, `possessive`, or `subject_marker`. Exclude any role containing one of the explicit non-attached markers: `independent`, `detached`, `demonstrative`, `relative`, `interrogative`, `conditional`, `attention`, `addressee`, `speaker`, `concealed`, or `hidden`.
4. Admit the generic role only when the previous segment's exact `(role, class)` pair is in the empirical governor/host registry. Pure conjunction, resumption, and result-fā pairs are outside that registry. Ambiguous residual pairs are explicitly recorded and remain fail-closed.

Segment ordering is by numeric `segment_index`; leading segments never satisfy a fallback admission.

## Empirical registry

The PREDV2 drop set contains 440 generic-role rows across 39 distinct previous `(role, class)` shapes. The v3 implementation records all shapes in three reusable registries: 32 governor/host pairs (396 rows), 3 conjunction-only/result-fā pairs (34 rows), and 4 ambiguous pairs (10 rows). The measurement CLI derives the counts and evidence table from the supplied corpus and PREDV2 drop set; the committed predicate registry is the reviewed exact-shape contract used by downstream F-C dependency producers.

The ambiguous registry includes the proper-noun-labeled host shape, emphatic lām, the interrogative noun, and the question hamza. They remain excluded even where a local row may look host-like, because the previous segment shape is not sufficiently specific for this family predicate.

## Files and data flow

- `tools/lattice_projectors.py` exports the v3 predicate and reusable predecessor registries while retaining v1/v2 unchanged.
- `qamus/examples/fb1-predicate-v3/predicate-fixtures.jsonl` contains the four new red-first shapes. The existing v2 fixture file remains untouched and is still exercised.
- `qamus/lattice/registered-projectors.json` registers the candidate-only v3 owner beside v1 and v2.
- `tools/measure_fb1_predicate_v3.py` accepts the corpus and STRAT packet only through required CLI arguments, compares all three populations, writes the three requested JSONL artifacts, and renders `PREDV3-REPORT.md`.
- `tools/check_regressions.py`, `tools/lattice_projectors.py`, and `tools/test_lattice_projectors.py` run the v3 fixture/self-test gates.

The corpus is never copied into the repository or changed. All generated lane artifacts remain candidate-mode; the owner chooses any deploy boundary.

## Measurement and hand-checks

The CLI will stop if v3 is not a subset of v1. It will report exact v1−v3 drop reasons: `named_non_attached`, `conjunction_prev`, `ambiguous_prev`, and `leading`. It will report v1/v2/v3 overlap with both the 234-row STRAT primary family cohort and all STRAT locations.

With seed `20260718`, it will write a deterministic 40-row hand-check from v3 outside the 455-row STRAT cohort and a deterministic 12-row sample from the newly re-admitted v3−v2 rows. The report records manual verdicts and reasons; the 12-row set must contain no false verdicts for completion.

## Safety and nonclaims

V3 is a population comparison and candidate producer only. It does not modify v1/v2, certify Arabic analyses, mutate the whitelist or live app, publish, deploy, restart services, or select an owner/deploy boundary. The exact predecessor registry is empirical for the supplied corpus and does not certify unseen role names or future segment shapes.
