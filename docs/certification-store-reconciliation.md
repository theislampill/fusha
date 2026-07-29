# Certification store reconciliation (token-layer ledger ↔ typed-claim plane)

**Status:** proposed 2026-07-29 (owner order §11). This doc **extends**
`docs/certification-authority.md` and `docs/certification-policy.md` — it does not
replace either. Those docs define *what* certification means per layer; this doc
resolves the fact that two independent stores currently record certification
truth, and defines the one-way contract that ends that split.

Machine anchors (extend, never fork):

- `tools/fact_ledger.py` + `qamus/schemas/fact-ledger-row.schema.json` — the
  **token-layer ledger** (`certification_state`). Live stores under
  `qamus/indexes/largelexicon/fact-ledger/`:
  `c2-decidable` (491 certified), `funcword-cert` (894 certified),
  `rebind-cert` (1,234 certified) — **2,619** genuinely certified current rows —
  plus `rm20-morphline` (26 rows, all `materialized`, 0 currently `certified`).
- `tools/certify_typed_fact.py` + `qamus/schemas/typed-claim-contract.schema.json`
  — the **typed-claim plane** (`certification.status`), with its append-only,
  hash-chained certification event trail (PR #117).
- `tools/reconcile_certification_stores.py` — the executable reconciliation pass
  emitting `qamus/reports/certification-store-reconciliation.jsonl` (+ meta).

## 1. Canonical store

**The typed-claim plane is canonical for fact identity and certification status
going forward.** The token-layer ledger is a **historical evidence store**: its
rows are IMPORTABLE as evidence-bundle references, never auto-promoted.

| Store | Role after migration start | Writer |
|---|---|---|
| typed-claim plane (`certification.status` + event trail) | canonical; the only place a *new* certification may be asserted | `tools/certify_typed_fact.py` — **only** this tool writes typed-claim `certified` |
| token-layer ledger (`certification_state`) | historical evidence store; append-only for *reclassification and revocation of its own legacy rows only*; **frozen for new certifications** | `tools/fact_ledger.py` (retains authority over its own store) |

A token-layer `certified` row is a *claim about historical review work*, backed by
the evidence recorded inside that row. It becomes typed-claim `certified` only by
passing through `certify_typed_fact.py`'s full bundle validation — the same gate a
brand-new fact faces. History is evidence, not certification.

### Is anything still actively writing the token layer?

Verified 2026-07-29 on `main` (ecab943):

- The wave writers exist and remain runnable: `tools/certify_funcword_wave.py`,
  `tools/certify_rebind_wave.py`, `tools/certify_class2_decidable_wave.py`,
  `tools/apply_rm20_morphline.py`.
- **Nothing automated invokes them.** Neither `tools/check_regressions.py` nor
  the CI workflows (`.github/workflows/pr-gate.yml`, `full-gate.yml`) run any
  token-layer writer; they only self-test `fact_ledger.py` on temp fixtures.
- Last data writes to the live stores: 2026-07-11 (`4b14cd8`, c2-decidable) and
  2026-07-12 (`ccd1a66`, funcword-cert / rebind-cert).

So the freeze is a policy declaration over an already-quiescent store, not a
behavior change. From migration start, running a wave writer to mint a **new**
token-layer `certified` row is a contract violation; running `fact_ledger.py`
transitions (`superseded`, `conflicted`, tier annotations) on **existing** rows
remains legitimate and is the token layer's retained authority.

## 2. Fact-identity mapping (token-layer key → typed-claim fact_id)

The token-layer `fact_id` is `sha256(canonical(identity_core))` over
`{subject_type, subject_identity, fact_type, scope, value}`
(`tools/fact_ledger.py:identity_core`). The typed-claim plane requires a
`^sha256:[0-9a-f]{64}$` fact id. The migration derivation is deterministic and
injective over the token identity core:

```
typed_fact_id = "sha256:" + sha256(canonical({
  "plane": "typed_claim",
  "migration": "token_layer_v1",
  "subject_identity": <token row subject_identity, verbatim>,
  "fact_type": <mapped typed fact_type, table below>,
  "scope": <token row scope>,
  "value": <token row candidate_or_value.value, verbatim>
}))
```

`canonical` = `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`
— the same canonicalization both stores already use. The `"migration"` marker
keeps imported ids from ever colliding with natively-authored typed-claim ids for
the same subject: an import is a distinct assertion ("legacy review concluded X")
until verified.

### Fact-type mapping

| Token-layer `fact_type` | Typed-claim `fact_type` | Ladder rung (`certification-authority.md` §2) |
|---|---|---|
| `function_word_analysis` (funcword-cert) | `contextual_function` | 4 — two-vote required (iʿrāb-bearing, learner-surfacing) |
| `governing_entry_analysis` (c2-decidable, rebind-cert) | `governor_relation` | 4 — two-vote required |
| `morphline_rendering` (rm20-morphline) | `irab_rendering` | 4 — two-vote required; store is `materialized`-only and out of the 2,619 |

All three map onto the two-vote rung: no evidence mode below
`two-vote` can certify their typed-claim counterparts, whatever the legacy row
recorded.

## 3. Evidence-bundle mapping

A token-layer certified row's recorded provenance becomes an **evidence bundle
REFERENCE** on the typed-claim side, never a certification by itself:

- `evidence[].source_address` entries (packet row, vote-A row, vote-B row) →
  `source_evidence.source_addresses` (kind `review_artifact`), which
  `certify_typed_fact.py` already requires to resolve to committed in-repo files;
- the row's `provenance.input_hashes` → `dependencies.source_addresses` +
  derivation inputs, so the bundle is reconstructible;
- the token-layer `fact_id` itself → recorded in the register event's `reason`
  and in the mapping report, so the audit trail joins both stores.

**A reference satisfies a rung only where its recorded evidence actually meets
that rung.** For the rung-4 fact types above, that means the legacy row's vote
evidence must be re-expressible as a `qamus.two_vote_artifact.v1` bundle that
passes `tools/validate_two_vote_artifacts.py`. The legacy vote rows
(`funcword-votes-a/b.jsonl` etc.) are *not* in that schema; until a conversion
bundle exists and validates, the strongest honest status for any legacy row —
even one whose recorded evidence fully checks out — is `mapped_verified`,
not `imported_certified`.

## 4. Migration status vocabulary

Every mapping row carries exactly one `migration_status`:

| Status | Meaning |
|---|---|
| `unmapped` | token-layer row for which no typed-claim id has been derived (should be empty after any reconciliation run) |
| `mapped_unverified` | typed-claim id derived; the recorded evidence has **not** been re-verified against the rung the fact class demands |
| `mapped_verified` | typed-claim id derived **and** the recorded evidence was mechanically re-verified against committed files and found to meet its rung's recorded-evidence requirements (see §7); import-eligible pending bundle conversion |
| `imported_certified` | the fact was registered and certified on the typed-claim plane by `certify_typed_fact.py` consuming a validated bundle; the certification event trail carries the import events |
| `conflict` | the stores (or two token stores) disagree about this subject+predicate; routed to `review_required`, never auto-resolved |

Expected first-pass distribution: ~all `mapped_unverified` — that is the honest
state, and the report says so rather than inflating.

## 5. Duplicate detection and conflict handling

- **Duplicate key:** `(subject_identity.loc, mapped typed fact_type)` across all
  token stores *and* against currently-certified typed-claim facts (absent event
  trail store = zero certified, per `certify_typed_fact.count_certified`).
- **Duplicate, values agree:** the mapping keeps one canonical row and records
  the sibling store/fact ids in `duplicate_group`. Counting both would be
  double-counting (§8).
- **Duplicate, values disagree (conflict):** `migration_status: "conflict"`; the
  typed-claim side of the mapping is `review_required`. **No store auto-wins** —
  not the newer row, not the typed-claim plane, not the larger store. Resolution
  is a human/lane decision recorded as a normal typed-claim transition with a
  reason naming both source rows. Any tool code path that resolves a conflict by
  picking a winner must fail closed (red-tested in the reconciler self-test).
- Measured on the live stores (first pass, 2026-07-29): **0 duplicates and 0
  conflicts** — no `loc` appears in more than one token store, and the
  typed-claim plane has no certified facts beyond temp fixtures.

## 6. State-transition authority and revocation propagation

- **Only `tools/certify_typed_fact.py` writes typed-claim `certified`.** The
  reconciler derives mappings and verdicts; it never writes the event trail.
- `tools/fact_ledger.py` keeps authority over its own legacy stores (frozen for
  new certifications, §1).
- **Token → typed:** if a legacy row is later superseded/conflicted/revoked in
  its ledger, any typed-claim fact imported from it must be flagged the same
  run: `certify_typed_fact.revoke()` on the imported fact id (drops it and its
  dependents to `review_required`, cascade per `certification-authority.md` §5).
  The mapping report is the join table that makes this walk mechanical.
- **Typed → token:** revoking an imported typed-claim fact does not rewrite the
  legacy ledger (history is reclassified, never rewritten); if the *evidence
  itself* is discredited, the token layer appends its own reclassification row
  via `fact_ledger.py` under its retained authority.
- Either direction, the mapping row's `migration_status` is recomputed on the
  next reconciliation run; a status may only move backward (e.g.
  `imported_certified` → `mapped_unverified`) through a recorded revocation
  event, never silently.

## 7. Bounded-family verification (the worked example)

The reconciler verifies ONE bounded family per run rather than bulk-trusting:
the funcword-cert certified rows of entry `014e23727379` (8 rows ≤ 25). For each
row it mechanically re-checks the recorded evidence against rung 4's
recorded-evidence requirements:

1. evidence carries the packet row + vote-A + vote-B addresses, and every
   addressed file is committed in-repo;
2. the packet row resolves by `packet_id` in the committed packet file, and its
   embedded `packet_sha256` equals the ledger row's
   `provenance.input_hashes.packet_row`;
3. both vote rows resolve by the same `packet_id` and carry the **same**
   `packet_sha256` (votes bind to the exact packet reviewed);
4. two `review_votes`, both `independent: true`, both `approve`, from distinct
   voter ids on distinct engines (engine-diverse, per the non-substitution rule).

Rows passing all checks are `mapped_verified` with
`import_eligible_pending_bundle_conversion: true` — demonstrating the migration
path without importing: `imported_certified` additionally requires the
`qamus.two_vote_artifact.v1` conversion bundle (§3) plus the
`certify_typed_fact.py` transition, neither of which this pass performs.

## 8. No double-counting

**A certified count must name its store and mapping status.** Legal counts:

- "2,619 token-layer certified (`certification_state`, stores c2-decidable +
  funcword-cert + rebind-cert, migration_status mapped_unverified/mapped_verified)";
- "0 typed-claim certified (`certification.status`, event trail store absent)".

Illegal: any single number that sums across the two planes, or that counts a
`mapped_*` row as if it were typed-claim certified. The reconciler's meta emits
counts only in the labeled form and its self-test red-cases an unlabeled merged
tally. After an import, the same fact appears in both stores by design; the
mapping row (`token_fact_id` ↔ `typed_fact_id`) is what keeps it one fact.

## 9. Audit trail

Migration events land in the PR #117 event trail
(`qamus.certification_event.v1`, hash-chained, append-only):

- import = `register` (reason names the source `token_fact_id`, store, and the
  reconciliation report row) → `review_required` → `certified` consuming the
  converted bundle;
- revocation propagation (§6) = `revoke` / `revoke_cascade` events with
  `triggered_by`;
- the reconciliation report + meta (`qamus/reports/certification-store-reconciliation.jsonl`)
  is regenerated deterministically from the ledgers (no timestamps in rows), so
  `check_regressions.py` can diff a fresh run against the committed artifact and
  fail closed on drift.
