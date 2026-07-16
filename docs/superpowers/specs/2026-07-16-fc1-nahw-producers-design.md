# FC1 Naḥw Dependency Producer Design

## Goal

Build a bounded calibration producer for syntax/dependency facts over the supplied 455-row stratification. The producer emits F-A governed typed-claim envelopes for evidence-backed naḥw dependencies and typed `syntax_pending` envelopes when the dependency evidence is incomplete.

## Scope and boundaries

- This lane owns naḥw dependency facts only; morphology/root/POS facts remain input evidence and are never re-authored here.
- External inputs are read-only and enter through explicit command-line arguments. No lane workspace path is embedded in code, fixtures, reports, or generated output.
- The calibration packet is a deterministic sample of at least 30 evidence-backed rows from the 455 plus committed no-evidence fixtures and unresolved records.
- The producer never rewrites Qurʾānic or lexical letters. Surface bytes are preserved; learner projection can expose brackets, relations, explanations, and ending classes only.
- A role is invalid unless its record contains an exact governor occurrence, exact governed occurrence, relationship evidence, case/mood applicability and value where relevant, an ending status (`visible`, `estimated` with a reason, or `not_applicable`), source addresses, and certification status.
- The producer is candidate infrastructure only. It does not certify linguistic truth, publish a hover, mutate a whitelist, or authorize live behavior.

## Contract shape

Each output row is `qamus.typed_claim_contract.v1`. The canonical occurrence is the input token with exact `quran_loc`, `wbw_loc`, and Unicode surface length. Each governed fact uses `fact_type: nahw_dependency` and carries the required F-A envelope plus a `fact_value` with:

```json
{
  "role": "subject",
  "governor": {"occurrence_id": "quran:2:13:11", "surface": "آمَنَ", "span_id": null},
  "governed_occurrence": {"occurrence_id": "quran:2:13:12", "surface": "السُّفَهَاءُ", "span_ids": ["lexical-body"]},
  "relationship": "subject_of",
  "relationship_evidence": {"source_field": "nahw_facts", "summary": "..."},
  "case_or_mood": {"applicability": "case", "value": "nominative", "status": "observed"},
  "ending": {"value": "ُ", "status": "visible", "reason": "terminal mark on the source surface"},
  "source_certification_status": "candidate"
}
```

The actual record also binds the claim to typed fact fields, names the producer/projector versions, preserves source addresses, and sets `public_materialization_allowed` and `live_mutation_allowed` to false. Estimated endings require `status: estimated` and a nonempty reason; they never become certified facts.

## Selection and data flow

1. Read `strat-455.jsonl`, `v575-verdicts.jsonl`, and an explicitly supplied read-only whitelist.
2. Join on exact `loc`; verify the verdict row and source row agree on location and surface.
3. Extract only structured `nahw_facts`, meaningful segment naḥw notes, and explicit context-source fields. A morphology-only note such as “function prefix preserved” cannot certify a naḥw dependency.
4. Resolve a governor occurrence from an explicit governor location, an exact context-source location, a same-token governor component, or a unique same-ayah source surface. Resolve a governed occurrence from the current span, an attached component, or the exact following/preceding source row required by the relation.
5. Select a deterministic priority-balanced sample across subject/governor, object/governor, preposition→governed, case, mood, pronoun attachment/referent, and agreement. If a row fails any required dependency field, emit `syntax_pending` rather than guessing.
6. Validate every generated envelope with the F-A validator and the producer’s semantic checks, including surface preservation and no morphology-owned fields.

## Fixtures and verification

The committed fixture set contains at least five positive cases and at least five adversarial cases. Adversarial cases include bare-role rejection, missing-governor abstention, estimated-ending visibility, case-without-governor rejection, and lexical-letter repaint rejection. The focused tests run red-first, then green after the producer is implemented. The full harness invokes the producer self-test and committed fixture/sample validation.

## Exact nonclaims

This design does not certify any Arabic role, governor, case, mood, attachment, referent, agreement, morphology, lexical root, public hover, renderer behavior, live whitelist, deployment, or corpus-wide coverage rate. It does not claim that the historical 631-row detector cohort is fully represented by the supplied 455-row calibration packet. It does not authorize publication or live mutation.
