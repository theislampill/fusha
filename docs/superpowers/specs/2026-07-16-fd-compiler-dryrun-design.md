# F-D Compiler Dry-Run Design

Status: pre-approved by the F-D execution brief. This document records the implementation boundary; it does not authorize live mutation, publication, commit of corpus data, or scholarly re-certification.

## Goal

Build one stdlib-only, contract-first compiler that can consume certified or candidate typed facts, emit a source-safe normalized public projection, and generate a proof HTML surface without hand-authored row payloads. The lane must also run the 455 structurally verified v575 rows in candidate mode and report the exact twelve requested metrics without treating structural verification as semantic certification.

## Alternatives considered

1. Generalize `tools/tranche1_projection.py` in place. This keeps one file but couples a tranche-specific fixture compiler to the new evidence and rich-card concerns, making the existing tranche gate harder to reason about.
2. Add a separate report-only validator. This would be safe but would not establish the shared compiler or prove that the two HTML views consume one generated payload.
3. Add an adjacent shared F-D compiler adapter with explicit registrations. This is the selected design. It preserves tranche-1 behavior, gives the new contract a single emission boundary, and makes every generated field traceable to a fact, a projector, or an explicitly marked candidate/review gap.

## Contract extension

The existing `qamus.typed_claim_contract.v1` envelope remains the source contract. Each governed fact gains:

- `evidence_mode`, restricted to `direct_source_attestation`, `cross_source_corroboration`, `deterministic_derivation_from_certified_facts`, `paired_form_inference`, `normalized_lexical_body`, `owner_or_scholar_adjudication`, or `unresolved`;
- `source_evidence`, with exactly one source quotation or structured source fact and one or more exact source addresses;
- `derivation_chain`, which is empty for direct attestations and explicit for derived facts;
- `dependencies`, carrying fact IDs and source addresses used by the fact;
- `contradiction_records`, pointing to tension records without changing the certification status of an independently certified fact.

The envelope gains optional `tension_records`. A tension record has an ID, status, statement, involved fact IDs, and resolution requirement. The Ṣufahāʾ `jām id/mushtaq` issue is attached here as unresolved. It is visible in the proof card and excluded from the certified claim bindings.

The existing `rule_projector` object remains the required rule/projector identity carrier. The F-D compiler registers `fd.shared_candidate_projection.v1` and emits its producer/version on every generated row.

## Ṣufahāʾ proof fixture

The fixture is for `quran:2:13:12`, surface `السُّفَهَاءُ`, and uses the lexical entry `1ffcc554ec44` for `سَفِهَ`. It converts the eleven supplied evidence records into independently hashed typed facts. The owner-mandated modes are preserved exactly:

- singular/plural relation and both patterns: direct source attestation;
- root: cross-source corroboration;
- removed yāʾ: paired-form inference with an explicit augment-inventory derivation chain;
- vowel-less plural body: normalized lexical body;
- nominative ending and governor relation: direct source attestation;
- jām id/mushtaq: unresolved tension record only.

The public projection uses Unicode code-point spans over the at-rest token: article `[0,2]`, lexical body `[2,11]`, and final nominative mark `[11,12]`. It keeps the lexical body and case ending as separate components and reconstructs the exact surface by concatenating the generated spans.

## Compiler boundary

`tools/fd_compiler.py` owns the forward path:

1. load evidence, corpus rows, and entries;
2. build or load a contract-conformant typed-fact envelope;
3. validate schema and semantic dependencies;
4. run a registered projector;
5. emit normalized public payload JSON and a generated HTML proof;
6. calculate reverse/parity witnesses and the 455-row candidate matrix.

The HTML contains one JSON payload script. Compact and expanded views are rendered by the same browser-side renderer from that script. Visual distinctions always have text equivalents (labels, badges, brackets, and status text); color is decorative only.

The payload is source-safe: learner text is plain English, source quotations stay in the contract/evidence fixture, and the HTML evidence footer exposes only source-addressed provenance, evidence modes, producer/projector IDs, and the immutable dry-run boundary. `live_mutation_allowed` is false in every contract, payload, report, and render witness.

## Repeated appearances and entry reciprocity

The compiler searches the read-only whitelist for the family represented by `سَفِيه`/`سُفَهَاء`. The fixture expectation records the observed family members and whether exact page-render traces are available. It does not infer page appearances from row or segment counts. The lexical occurrence-to-entry edge and the reverse entry-to-occurrence edge are both emitted for `1ffcc554ec44`; the stale source-row entry ID is retained only in a private diagnostic trace so the proof can expose the linkage correction without copying the wrong join into the public card.

## 455-row metrics

Candidate compilation is structural and non-authorizing. A row can contribute to multiple metric columns. The report keeps a per-row `flags` array and a deterministic `primary_blocker` chosen in this order: missing learner-language fields, source/scholar review, linguistic inconsistency, span ownership, entry linkage, projector, producer gaps, parity, and reconstruction.

The twelve report keys are exactly the brief’s keys and use these meanings:

| Metric | Meaning |
| --- | --- |
| rows compiling successfully | The compiler emitted a candidate/review record after structural checks. |
| rows failing linguistic consistency | Source row surface/segment invariants failed. |
| rows missing span ownership | No deterministic owned at-rest span could be assigned. |
| rows missing learner-language fields | At least one generated component lacks supplied learner text; no prose is invented. |
| rows missing entry linkage | The source entry ID cannot join the read-only entry corpus. |
| rows missing a projector | The input row has no registered projector identity before F-D assignment. |
| rows requiring F-B morphology producers | No direct structured morphology producer carrier is present in the source row. |
| rows requiring F-C naḥw producers | No direct structured syntax producer carrier is present in the source row. |
| rows routed to source/scholar review | v575 structural verification is not semantic certification, so the row remains review-routed. |
| repeated page appearances covered | Confirmed repeated page/render appearances with an available trace, never inferred counts. |
| parity failures | Generated payload differs from its source component/parity fixture. |
| exact reconstruction failures | Generated at-rest spans do not concatenate to the source surface. |

## Validation and rollback

Red-first tests cover evidence-mode rejection, derived-fact dependencies, unresolved tension isolation, Ṣufahāʾ span/reconstruction/reciprocity, same-payload HTML views, and the metric matrix. `tools/validate_fd_compiler.py` validates the checked-in fixtures; `tools/check_regressions.py` invokes the bounded F-D self-test and fixture gate. The final verification runs the focused tests, fixture validators, regression harness, `git diff --check`, and (when locally available) Playwright render checks.

Rollback is deleting the F-D-only files and reverting the F-D registry/harness hook. No corpus, live renderer, live whitelist, or deployment surface is changed by this lane.

