# FC1 — naḥw dependency producer calibration

Status: complete for the bounded calibration packet. The producer is on branch
`andon-fc-nahw-producers`; no push or live mutation was performed.

## Outcome table

| Area | Outcome | Evidence |
| --- | --- | --- |
| F-A producer contract | PASS | Strict `nahw_dependency` fact builder and F-A envelope validation |
| Positive fixtures | PASS | 5 positive fixtures, including the `sufaha` subject-of-آمن reference-positive |
| Adversarial fixtures | PASS | 6 red-first adversarial fixtures; bare role, missing governor, estimated-ending reason, surface repaint, and morphology leak are covered |
| Typed abstentions | PASS | Missing-governor and no-evidence rows emit `syntax_pending` records with `claim: null` |
| Calibrated positive packet | PASS | 30 selected rows from the 455-row stratified input |
| Calibrated unresolved packet | PASS | 3 typed unresolved rows |
| Packet abstention rate | 9.09% | `3 / (30 + 3)`; packet metric only |
| Priority-role coverage | PASS | subject 4, object 1, preposition-to-governed 14, mood 1, pronoun attachment 8, agreement 1; one additional relation is classified as `other` |
| Estimated-ending fixture | PASS | Estimated ending carries an explicit reason and is not certified |
| Surface boundary | PASS | Source and projected surfaces are compared exactly; naḥw facts do not carry morphology-owned fields |
| Harness | PASS | `python tools/check_regressions.py` → `ALL REGRESSION CHECKS PASS` |

The packet was generated from explicit external arguments for the 455-row
stratification, 575-row verdict input, and read-only corpus whitelist. The
committed JSONL contains only F-A records; source file paths are not embedded.

## Evidence modes and certification

All 30 positive calibration records use `direct_source_attestation` as their
F-A evidence mode. They remain `candidate` or `review_required`, never newly
certified. Estimated case/ending states are reasoned and review-gated. Pronoun
records carry a typed unresolved referent field where the source does not name
an exact antecedent occurrence.

The producer projects syntax through typed relations, exact occurrences,
relationship evidence, case/mood objects, ending states, and public relation
payloads. It preserves the canonical surface and keeps root, lemma, POS, form,
voice, sarf, and related morphology-owned fields out of naḥw facts.

## Validation commands

```text
python tools/fc_nahw_producer.py --self-test
python -m unittest tools.test_fc_nahw_producer -q
python tools/validate_fc1_nahw_producer.py --self-test
python tools/validate_fc1_nahw_producer.py --fixtures qamus/examples/fc1-nahw
python tools/check_artifact_ergonomics.py
python tools/check_regressions.py
```

The external calibration command is intentionally represented with explicit
arguments rather than a repository-default corpus path:

```text
python tools/fc_nahw_producer.py --strat-455 <STRAT_455_JSONL> --v575-verdicts <V575_VERDICTS_JSONL> --whitelist <READ_ONLY_CORPUS_JSONL> --output-dir qamus/examples/fc1-nahw --positive-limit 30 --unresolved-limit 3
```

## EXACT NONCLAIMS

- This packet does not claim that all 455 stratified rows have usable typed
  naḥw evidence, nor that the packet abstention rate is a corpus-wide accuracy,
  coverage, or error rate.
- This packet does not claim to reproduce or certify a 631-row typed-naḥw
  cohort. It reports only the supplied 455-row stratified input, 575-row
  verdict input, and the read-only corpus rows actually joined during
  calibration.
- Candidate or review-required facts are not scholarly certification and do
  not authorize publication, whitelist append, deployment, restart, or live
  mutation.
- The `sufaha` governor fact is a reference-positive fixture only; FC1 performs
  no new certification of that packet and does not promote it into a live
  surface.
- A visible or estimated ending is not a claim that the lexical letters should
  be repainted. Estimated states remain explicitly estimated with reasons.
- A preposition-to-following-occurrence relation does not claim a wider
  prepositional-phrase head or attachment where the source leaves that head
  unasserted.
- Pronoun attachment records do not claim an antecedent when the source lacks
  an exact referent occurrence; that gap remains typed and unresolved.
- FC1 is separate from morphology. No root, lemma, POS, derived form, voice,
  sarf field, or morphology certification is emitted by this producer.
- No push, release, publication, production mutation, or external message was
  performed.
