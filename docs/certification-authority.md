# Fact-level certification authority (`source_certified`)

**Status:** proposed 2026-07-28 (owner decision #1 design). This doc **extends**
`docs/certification-policy.md` — it does not replace it. That policy governs the
*lemma-fanout* layer and names the *token-level two-vote* layer; this doc adds the
layer beneath both: **who and what may certify an individual typed fact**, and what
evidence bundle must exist before `certification.status: "certified"` is honest.

Machine anchors (extend, never fork):

- `qamus/schemas/typed-claim-contract.schema.json` — `$defs/evidence_mode`,
  `$defs/source_evidence`, `$defs/derivation_step`, `$defs/dependencies`,
  `governed_fact.certification`, `defeaters`, `dependent_fact_ids`,
  `dependent_projection_ids`. This doc's policy is expressed entirely in that
  contract's existing fields.
- `qamus/schemas/two-vote-artifact.schema.json` + `tools/validate_two_vote_artifacts.py` —
  the reconstructible review-artifact contract behind any `two_vote` /
  `bulk_two_vote_certified` claim (adopted with this doc).

## 0. The certification stack (three layers, bottom-up)

| Layer | Unit | Contract | Status |
|---|---|---|---|
| **Fact** (this doc) | one `governed_fact` (root, pattern, case ending, governor relation, …) | typed-claim contract | policy proposed here |
| **Token** | one occurrence's hover decision | two-vote artifact bundle | contract adopted; history reclassified, not backfilled |
| **Lemma fanout** | reuse of a solved fact across occurrences | `certified-lemma.schema.json` gates | adopted 2026-07-04 |

A token-level certification is only as strong as the facts under it; a fanout is
only as strong as the token certifications it generalizes. Nothing above may claim
more than the layer below supports.

## 1. Evidence modes — reuse of `$defs/evidence_mode`, verbatim

The typed-claim contract already carries the closed enum. This policy assigns each
mode its sufficiency conditions; **no new enum values are introduced**.

| `evidence_mode` | Meaning | Minimum bundle for `source_certified` |
|---|---|---|
| `direct_source_attestation` | The canonical source states the fact at an exact address | source address + verbatim quotation **or** structured source fact |
| `cross_source_corroboration` | Two or more independent sources state the same fact | ≥2 source addresses from independent source kinds + conflict record (empty allowed, must exist) |
| `deterministic_derivation_from_certified_facts` | The fact follows mechanically from already-certified facts | full `derivation_chain`; every `input_fact_ids` member already certified; derivation re-runnable |
| `paired_form_inference` | The fact is inferred from a certified paired form (e.g. singular↔plural letter accounting) | the paired fact's `fact_id` in `dependencies.fact_ids` + the pairing rule in `derivation_chain` |
| `normalized_lexical_body` | The fact is a normalization of a certified lexical body | the source fact + the normalization operation recorded as a derivation step |
| `owner_or_scholar_adjudication` | A human authority resolved what sources could not | reviewer artifact (see §4) recording adjudicator role (`owner` or `scholar`), the question, the ruling, and the grounds |
| `unresolved` | No sufficient evidence | **may never** carry `certification.status: "certified"` — it stays `pending`/`blocked` with `unresolved_blockers` |

The prompt-level distinction "owner adjudication" vs "scholar adjudication" is
recorded **inside the reviewer artifact** (`adjudicator_role`), not as a new enum
value — the contract enum stays closed and additive.

## 2. Sufficiency ladder — which evidence is enough, per fact class

Internal source names (analysis corpora, morphology databases, external Qur'an
tooling) are **private-side provenance**: they may appear in evidence bundles and
lane reports, never in public payload fields (`FORBIDDEN_LABELS` discipline, as in
`certification-policy.md` §2).

1. **Single canonical read-off suffices** (`direct_source_attestation`, one address):
   surface observation, visible diacritics/case sign, segment boundaries visible in
   the script, exact occurrence address. These are *observations of the source
   itself*; a second source adds nothing.
2. **Entry-store / corpus corroboration required** (`cross_source_corroboration`):
   lexical identity (occurrence → entry/lemma), root when not directly attested,
   crosswalk facts joining a reader occurrence to a qamus entry. One tool's
   morphology row is a candidate, not a certification — the sufaha `root` fact is
   the model: certified only under corroboration.
3. **External triangulation required**: any fact where internal sources disagree,
   or a function-word sense where the gloss flips by context
   (`certification-policy.md` §3: مِن/مَن, إِنْ/إِنَّ, عَلَىٰ). Triangulation results stay
   private-side; the public artifact carries only the authored conclusion.
4. **Two-vote required** (token layer): any iʿrāb-bearing conclusion that will
   surface to a learner — contextual function, governor, case/mood with sign
   status, attachment, referent. The two-vote artifact bundle (schema above) is the
   *only* acceptable proof; a declared gate string or matching gloss text is not.
5. **Owner/scholar adjudication required**: contested grammatical analysis with
   scholarly disagreement, theological sensitivity, or an `unresolved` nahw
   dependency that sources cannot settle (the PROOF-V governor/object relation is
   the standing example — routed to scholar packets, *not* certified by repetition
   of the same internal source).

**Rule of non-substitution:** repetition of the same engine, the same source read
twice, or an English gloss match can never move a fact up this ladder.

## 3. Who / what may assign `source_certified`

| Assigner | May certify | May never certify |
|---|---|---|
| **Deterministic producer** (versioned tool with self-test) | modes `deterministic_derivation_from_certified_facts`, `normalized_lexical_body`, `paired_form_inference` — mechanically, when all inputs are already certified | anything requiring judgment; anything with a non-empty conflict record |
| **Lane operator** (agent run, recorded `producer.id`/`version`) | modes `direct_source_attestation`, `cross_source_corroboration` when the bundle is complete and no conflict exists | iʿrāb-bearing token conclusions (two-vote layer required); contested facts |
| **Two independent reviewers** (two-vote artifact bundle) | token-layer conclusions, per the artifact contract | fanout (lemma layer gates apply on top) |
| **Owner** | adjudications (`owner_or_scholar_adjudication`, role `owner`); authorization of any *deploy/apply* of certified facts | overriding a source's verbatim content |
| **Scholar** | adjudications (role `scholar`) on contested Arabic grammar | deploy authorization (owner-gated) |

Assignment is invalid — regardless of assigner — unless the **reconstructible
evidence bundle** exists with every element:

1. source address(es) (`source_evidence.source_addresses`, exact, typed `source_kind`);
2. verbatim quotation **or** structured source fact (`source_evidence` oneOf — already enforced);
3. declared `evidence_mode` consistent with §2's ladder for that fact class;
4. `dependencies` (fact ids + source addresses actually relied upon);
5. `derivation_chain` (non-empty whenever the mode is derivational/inferential);
6. conflict record: `contradiction_records`/`tension_records` present (possibly empty) with any known disagreement attached — certifying *over* an unattached known conflict is a violation;
7. reviewer artifacts, when the ladder requires review: the two-vote artifact bundle id, or the adjudication artifact id, in `evidence.evidence_ids`;
8. invalidation conditions: `defeaters` naming what would falsify the fact, and `dependent_fact_ids`/`dependent_projection_ids` populated so revocation can propagate.

## 4. Reviewer / adjudication artifacts

- **Two-vote:** `qamus.two_vote_artifact.v1` — two independent votes (distinct
  engines and reviewer ids; provenance = engine/model/lane), each reconstructing
  occurrence + exact surface, segmentation, lexical identity, root/form where
  applicable, contextual function, governor, governed expression, case/mood with
  sign visibility, attachment, referent where applicable, grammatical reason, and
  unresolved points. Agreement is computed on **conclusion + reason key**, never on
  gloss text. Historical claims without artifacts are representable only as
  `two_vote_claimed_unverified`; fabricating votes is a validator FAIL.
- **Adjudication:** a committed artifact recording adjudicator role, exact
  question, the competing analyses considered, the ruling, grounds, and scope
  (this occurrence only vs. rule-level). Referenced from `evidence.evidence_ids`.

## 5. Revocation and invalidation

1. **Source fact changes** (a source row is corrected, a capture was wrong): the
   fact's certification drops to `review_required`; every id in
   `dependent_fact_ids` and `dependent_projection_ids` is flagged the same run.
   Flagging is mandatory and mechanical; re-certification is not.
2. **Cascade rule:** a fact certified by `deterministic_derivation_from_certified_facts`
   or `paired_form_inference` is *automatically* de-certified when any input fact
   loses certification (its derivation premise is gone).
3. **Defeater fires:** the fact moves to `blocked` with the defeater recorded;
   dependent projections are flagged, not silently kept.
4. **Two-vote revocation:** if a vote artifact is shown non-independent or
   non-reconstructible after the fact, the bundle reclassifies to
   `two_vote_claimed_unverified` and every dependent certification is flagged.
5. **No silent downgrade:** every revocation appends an audit row (below); history
   is reclassified, never rewritten.

## 6. Audit artifacts

- the typed-claim contract row itself (fact ledger) — certified state + full bundle;
- the two-vote artifact bundle jsonl (committed sample: `qamus/examples/two_vote_artifact.sample.jsonl`);
- adjudication artifacts (owner/scholar packets);
- a certification event trail (assign/revoke/reclassify with date, assigner, and
  reason) — append-only, fixture-first before any live store exists;
- validator gates in `tools/check_regressions.py` (self-tests + committed samples),
  so the contract cannot drift without a red gate.

## 7. Worked examples — the three canaries

### 7.1 سُفَهَاء 11-fact packet (`quran:2:13:12`, `qamus/examples/proof-noun-sufaha/`)

Fact-level modes as committed in `sufaha-contract.json`:

| Fact | Mode | Ladder rung (§2) |
|---|---|---|
| `singular_plural_relation`, `plural_formation`, `singular_pattern`, `plural_pattern`, `retained_radicals`, `plural_introduced_letters` | `direct_source_attestation` | 1 — read-off of the paired entry forms |
| `root` | `cross_source_corroboration` | 2 — one morphology row alone would be candidate-only |
| `paired_y_removal` | `paired_form_inference` | dependency on the certified pair + pairing rule in the chain |
| `plural_lexical_body` | `normalized_lexical_body` | normalization step recorded |
| `case_ending` (nominative, visible damma) | `direct_source_attestation` | 1 for the *sign*; rung 4 for surfacing the conclusion |
| `governor_relation` (fāʿil of آمَنَ) | `direct_source_attestation` | a new iʿrāb-bearing certification requires the token-layer two-vote artifact plus exact fact-value, reason-key, occurrence and written-surface binding; current certified state is re-audited from the referenced bundle, and the p007 location-only legacy events are append-only revoked in favor of exact successors |

This packet is the model of *heterogeneous* fact-level certification: one word,
eleven facts, four evidence modes — certification is per-fact, never per-word.

### 7.2 فَٱتَّبِعْنِي — PROOF-V (`quran:19:43:10`, `qamus/examples/proof-verb/`)

Committed as `candidate_with_source_gaps`, `pre_apply_not_authorized`: surface
observation, protective nūn, and object pronoun are `direct_source_attestation`;
lexeme crosswalk, letter ownership, and derived-verb evidence are
`cross_source_corroboration`; and the naḥw dependency (exact governor/object
relation) is honestly `unresolved` → `pending`. Under this policy that is the
**correct terminal state absent adjudication**: rung 5 applies, the gap routes to a
scholar packet, and nothing about the verb's iʿrāb may be certified by re-reading
the same sources. PROOF-V demonstrates that a packet can be end-to-end typed and
still refuse certification — refusal is a feature of the authority, not a defect
of the packet.

### 7.3 مَا particle proof — PROOF-P (`quran:2:284:10`, `qamus/examples/proof-particle/`)

Entry, sense, selected-word edge, canonical occurrence, contextual function, and
governed scope are `direct_source_attestation` (certified); contextual gloss and
entry↔occurrence reciprocity are `deterministic_derivation_from_certified_facts`
but remain **candidate** because an input hop (card→occurrence with two identical
مَا surfaces; empty crosswalk `occurrence_id`) is itself candidate — the cascade
rule of §5.2 in its positive form: a derivation cannot outrank its weakest input.
`alternative_function_routes` is `unresolved`/`pending`, which is what keeps this
a `function_context`-gated word under `certification-policy.md` §1 (a particle
never fans out on lemma/pattern/POS).

## 8. Open design questions for the owner

1. **Independence definition:** the two-vote artifact contract enforces distinct
   engines + distinct reviewer ids. Is distinct *engine family* required (two
   models of one vendor = same engine?), and should lane independence
   (sarf-primary vs nahw-primary) be mandatory rather than merely recorded?
2. **Adjudication artifact schema:** §4's owner/scholar artifact is described but
   not yet schema-enforced. Adopt a `qamus.adjudication_artifact.v1` next?
3. **Certification event trail placement:** fixture-first in-repo, or defer until
   the live store exists (mirroring the closure-2092 apply-receipt pattern)?
4. **Historical reclassification tranche:** when do we sweep the closure-2092
   `bulk_two_vote_certified` rows into explicit `two_vote_claimed_unverified`
   bundles (they currently carry the claim only in reports/receipts)?
5. **Scholar roster and quorum:** who counts as `scholar`, and does a contested
   ruling need one scholar or agreement of two?
