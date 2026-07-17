# FB1 clitic-pronoun composition calibration design

## Boundary

FB1 is a calibration packet for the 234 `clitic_pronoun_compositions` rows in
the supplied STRAT stream. It does not write the whitelist, Qamus entries,
learner payloads, or any live/public artifact. The producer accepts external
STRAT, verdict, and corpus paths only as explicit CLI arguments. The committed
harness uses a small in-repository fixture sample.

## Governing output

Each output line is a `qamus.typed_claim_contract.v1` record. Candidate facts
are typed component/composition facts; unresolved lines contain typed blocker
facts. Every fact repeats the canonical occurrence in `fact_value`, carries
exact code-point spans whose UTF-8 bytes reconstruct the written token, names
primary and secondary owners, source/source address, evidence mode, producer
and registered projector, guards, defeaters, dependencies, and reconstruction
proof. English glosses and morphline text are never inputs to a linguistic
claim.

The registered projector is
`sarf.fb1_clitic_pronoun_composition.v1`, backed by the F-A contract and the
existing data-driven lattice registry. It remains candidate-only and its
materialization and live-mutation flags are false.

## Abstention policy

- Closed-class function words may retain typed function/clitic components, but
  never inherit or project a root. A root-bearing closed-class claim routes to
  `nahw.function_word_review`.
- `لا`/`إلا` surface/function ambiguity routes to typed unresolved output; no
  English gloss or morphline resolves it.
- Written boundaries are built by ordered exact substring matching and a UTF-8
  reconstruction check. No normalization is used to manufacture a split.
- Idghām boundary classes are explicit: A/B may project only with a source
  boundary attestation and byte-clean spans; C (fused) and D (ambiguous or
  missing boundary evidence) are unresolved with a route.
- Protective nūn is emitted only from an explicit structured source segment as
  `fact_value.typed_kind = sarf.protective_nun`. It is never emitted as a
  particle and is unresolved when the source only permits an inference or a
  fused split.
- Missing, contradictory, or unverified morphology is a typed unresolved
  record rather than a guessed host, root, or clitic.

## Calibration evidence

The packet contains at least 40 real family rows selected across attached
object/possessive/subject pronouns, proclitic combinations, protective-nūn
contexts, and boundary-ambiguous/idghām contexts. It also contains at least six
positive and six adversarial fixture cases. The report records each row's
status, reason codes, routes, and exact nonclaims; it attests zero false
projections only over the fixture and selected calibration sample under these
guards, never over the 234-row family or the corpus.
