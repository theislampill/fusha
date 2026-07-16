# Tranche 1 implementation report

## Result

The Q7 eight-canary architecture proof is implemented on branch `andon-tranche1` as a fixture-only pipeline:

`typed fact model -> registered projectors -> compiler -> normalized learner projection -> parity/hash validation -> typed unresolved queue -> non-authorizing Phase 4 gate`

Fresh verification produced exactly 8 normalized rows: 4 candidate projections and 4 typed queue records. Deterministic regeneration produced no tracked diff. The apply manifest is `pre_apply_not_authorized`; all future apply gates remain `not_run`, and authorized live mutations are zero.

## Verified source snapshot

- Read-only corpus: `../data/rh_live_01_beta_whitelist.jsonl`
- Row count: `34323`
- SHA-256: `5805cc9f3b3c98f5e2b6209871f106d708dc42848b135e780531cc8b2e38ac6e`
- Source commit: `f706698a9f682de1731b1913221538c7a4289870`
- Source commit scope: `fusha_checkout`
- Pristine source checkout: branch `main`, clean, HEAD exactly `f706698a9f682de1731b1913221538c7a4289870`
- Tranche worktree: branch `andon-tranche1`, linked Git worktree, clean before this report was added
- Renderer reference hashes (read-only evidence):
  - `wbw.js`: `5283a07d365ff27f598c08d9f0a0fe1e02175ff5f6c10ef727d2294b551a33d5`
  - `wbw.css`: `5e34864bb2db285985e6f0af34ac831b50d094e2ef90b069393f23a0c4a3fadc`

## What was built

1. Additive typed lineage carriers were added to the six named schemas without adding new required fields to legacy rows. The tranche-local `tranche1-projection-crosswalk.schema.json` requires fact IDs, status, source address/hash/commit, materialization target, producer/projector/version, exact field mappings, output hash, blocker/route, and a false live-mutation flag.
2. `sarf.tranche1_fixture_projection.v1` and `nahw.tranche1_fixture_projection.v1` are registered in both projector layers. Their producer is `tools.tranche1_projection`, version `1.0.0`; exact-surface and typed-status guards fail closed.
3. `tools/tranche1_projection.py` selects only the eight policy locations from exact raw source rows and emits deterministic UTF-8/LF fixtures:
   - exact source canaries and observation fact ledger;
   - morphology and dependency candidate lattices;
   - morphosyntax records;
   - canonical and normalized public payloads;
   - 4 public candidate projections;
   - 4 typed unresolved/blocked queue records;
   - projection crosswalk and DOM-consumption expectations;
   - renderer-completeness and rich-hover normalization fixtures;
   - 4-row `planned_not_applied` plan, 4-row human review packet, and Phase 4 manifest.
4. `tools/validate_tranche1_projection.py` validates schemas, exact raw source parity, exact segment reconstruction, exact `gloss_contribution -> gloss` and `class -> qg_class` mappings, fact/source/output hashes, forward/reverse crosswalks, lineage, 4+4 routing, DOM expectations, and zero live authorization.
5. The Phase 4 manifest schema, builder, and validator were extended additively with a read-only source-corpus block. The validator recomputes corpus row count and SHA-256 and compares the source commit.

Raw `source-canaries.jsonl` rows remain byte-exact source observations and therefore are not rewritten to add projection lineage. Every projected, compiled, validation-sidecar, apply-plan, or queue record carries its applicable producer/projector/version lineage; the manifest instead uses its existing closed `generated_by` contract.

## Exact 4 + 4 outcome

All eight normalized records use producer `tools.tranche1_projection`, projector version `1.0.0`, and `live_mutation_allowed=false`.

| Location | Exact surface | Outcome | Projector | Blocker and route |
|---|---|---|---|---|
| `3:141:4` | `آمَنُوا` | `candidate` / `candidate_projection` | `sarf.tranche1_fixture_projection.v1` | None; review-gated typed-input candidate |
| `24:31:76` | `ٱلْمُؤْمِنُونَ` | `candidate` / `candidate_projection` | `sarf.tranche1_fixture_projection.v1` | None; exact source labels remain `ART + DER + STEM + PL` |
| `2:34:5` | `لِءَادَمَ` | `candidate` / `candidate_projection` | `nahw.tranche1_fixture_projection.v1` | None; explicit `proper_name_no_public_root` status |
| `39:63:3` | `السَّمَاوَاتِ` | `candidate` / `candidate_projection` | `sarf.tranche1_fixture_projection.v1` | None; segmented side of same-surface parity fixture |
| `22:18:9` | `ٱلسَّمَٰوَٰتِ` | `unresolved` / `typed_queue_record` | `sarf.tranche1_fixture_projection.v1` | Fused/segmented difference lacks typed compatibility or legacy rationale; route `sarf/procedures/morphology-candidate-lattice.md` |
| `2:13:12` | `السُّفَهَاءُ` | `source_gap` / `typed_queue_record` | `sarf.tranche1_fixture_projection.v1` | Missing typed singular, template, root, and ending facts; route `sarf/procedures/root-decision.md` |
| `7:54:23` | `مُسَخَّرَٰتٍۭ` | `producer_pending` / `typed_queue_record` | `sarf.tranche1_fixture_projection.v1` | Generic whole-token segment cannot be split automatically; route `sarf/procedures/clitic-and-host-morphology.md` |
| `5:2:12` | `ٱلْهَدْىَ` | `syntax_pending` / `typed_queue_record` | `nahw.tranche1_fixture_projection.v1` | Governor and ending evidence absent; route `nahw/procedures/governor-dependency-lattice.md` |

This 4+4 partition is a fixture expectation, not a linguistic verdict or deployability count.

## Verbatim validator results

### Tranche schema, parity, field mapping, and row/hash validator

Command:

```powershell
python tools/validate_tranche1_projection.py qamus/examples/tranche1 --whitelist ..\data\rh_live_01_beta_whitelist.jsonl --source-commit f706698a9f682de1731b1913221538c7a4289870
```

Output:

```text
TRANCHE1 VALIDATION PASS
PASS - schema validation: all typed fixture rows conform
PASS - exact source surface and segment parity: 8/8
PASS - exact gloss_contribution/class to gloss/qg_class mapping: 4/4 candidates
PASS - row/hash round trip: 8/8 source and output hashes recompute
PASS - routing: 4 candidate projections + 4 typed queue records
PASS - DOM consumption expectations: 4 consume + 4 abstain; live assertions 0
PASS - same-surface adversary: segmented candidate + fused unresolved
PASS - live mutation authorization: 0
SUMMARY canonical=8 candidates=4 queued=4 errors=0
```

### Named validator 1: morphosyntax token metadata

Command:

```powershell
python tools/validate_morphosyntax_token_metadata.py qamus/examples/tranche1/morphosyntax-token.jsonl
```

Output:

```text
checked 4 morphosyntax token record(s)
PASS — schema + public boundary + composition invariants OK
```

### Named validator 2: dependency lattice

Command:

```powershell
python tools/validate_dependency_lattice.py qamus/examples/tranche1/dependency-lattice.jsonl
```

Output:

```text
checked 2 lattice(s), 0 violation(s)
```

### Named validator 3: renderer completeness

Command:

```powershell
python tools/validate_renderer_completeness_gate.py qamus/examples/tranche1/renderer-completeness.jsonl
```

Output:

```text
PASS - hover rows are renderer-complete and source-clean
```

### Named validator 4: rich-hover normalization

Command:

```powershell
python tools/check_rich_hover_norm.py --whitelist qamus/examples/tranche1/rich-hover-norm.jsonl
```

Output:

```text
========================================================================
RICH-HOVER NORMALIZATION CONTRACT  norm@1  conformance scan
========================================================================
total rows                 : 4
fully norm@1-conformant    : 4  (100.00%)  [zero MUST violations]
nonconformant (>=1 MUST)   : 0
  of which KNOWN debt      : 0  (already in rich-seg-known-debt.jsonl)
  of which NEW debt        : 0  (only norm@1 sees these)
------------------------------------------------------------------------
per-clause violation counts (MUST = headline; SHOULD = advisory):
  [MUST ] N-ROOT-01          0
  [MUST ] N-LANG-01          0
  [MUST ] N-LANG-02          0
  [MUST ] N-SEG-01           0
  [MUST ] N-SEG-02           0
  [MUST ] N-PED-01           0
  [MUST ] N-PED-02           0
  [MUST ] N-CONS-01          0
  [SHOULD] N-ROOT-02          0
  [SHOULD] N-COLOUR-02        0
------------------------------------------------------------------------
========================================================================
```

### Named validator 5: schema coherence

Command:

```powershell
python tools/validate_schema_coherence.py --self-test
```

Output:

```text
== real-repo lints ==
  ok   all 5 lints pass on the real repo
== red-first mutation proofs ==
  red-proof ok   (a) mutate a gate enum value -> gate lint red
      -> (a) fanout_gate spelling drift: ['function_context', 'lemma_pattern', 'source_address_exact'] != ['function_context', 'lemma_pattern_pos', 'source_address_exact']
  red-proof ok   (b) add a CSS class -> qg drift lint red
      -> (b) CSS/DOM fixture uses qg class 'qg-rogue-injected' not in the schema enum
  red-proof ok   (b) add a schema qg class w/o doc regen -> qg drift lint red
      -> (b) class-map doc drifted from the schema-generated table (regenerate via --emit-class-map)
  red-proof ok   (c) drop source_key disambiguation -> source_key lint red
      -> (c) binding schema source_key missing disambiguation vs the page-ordinal `source_keys` (carrier identity note)
  red-proof ok   (d) drop normalizer name -> surface_norm lint red
      -> (d) payload surface_norm description does not name the normalizer (_join_surface_key)
  red-proof ok   (d) non-fixed-point surface_norm -> round-trip lint red
      -> (d) surface_norm 'كِتَابـ ' is not a fixed point of _join_surface_key (round-trip fail)
  red-proof ok   (e) new disjoint same-name field -> cross-schema lint red
      -> (e) NEW disjoint same-name enum field 'pos' shared by >=2 schemas with no overlap (reconcile the enums or register it with rationale)

schema coherence self-test OK
```

### Phase 4 source snapshot and non-authorization gate

Command:

```powershell
python tools/validate_phase4_apply_readiness_manifest.py qamus/examples/tranche1/apply-readiness-manifest.json --plan-jsonl qamus/examples/tranche1/apply-plan.jsonl --source-corpus ..\data\rh_live_01_beta_whitelist.jsonl --source-commit f706698a9f682de1731b1913221538c7a4289870
```

Output:

```text
checked 1 Phase 4 apply-readiness manifest
verified source corpus rh_live_01_beta_whitelist.jsonl rows=34323 sha256=5805cc9f3b3c98f5e2b6209871f106d708dc42848b135e780531cc8b2e38ac6e status=verified_read_only_snapshot
verified source commit f706698a9f682de1731b1913221538c7a4289870 scope=fusha_checkout
status=pre_apply_not_authorized apply_authorized=false live_mutation_allowed=false
PASS — Phase 4 apply-readiness manifest is source-only and non-mutating
```

### Human-review packet gate

Command:

```powershell
python tools/validate_human_review_packet.py qamus/examples/tranche1/human-review-packet.json
```

Output:

```text
{"ok": true, "rows": 4}
```

### Full JSON Schema validation of new and legacy Phase 4 manifests

Output:

```text
PASS - qamus\examples\tranche1\apply-readiness-manifest.json conforms to phase4-apply-readiness-manifest.schema.json
PASS - qamus\examples\phase4_apply_readiness_manifest.sample.json conforms to phase4-apply-readiness-manifest.schema.json
```

## Regeneration and regression evidence

Fresh compiler result:

```text
canonical_count=8
candidate_count=4
queue_count=4
live_mutations=0
PASS - deterministic regeneration produced no tracked diff
```

Combined unit/regression command:

```powershell
python -m unittest tools.test_tranche1_projection tools.test_fact_projectors tools.test_lattice_projectors -v
```

Verbatim summary:

```text
----------------------------------------------------------------------
Ran 40 tests in 7.016s

OK
```

The suite includes observed RED -> GREEN coverage for missing schemas, missing projector registrations, absent compiler, segment-parity corruption, output-hash corruption, absent corpus-bound manifests, source-commit drift, and missing DOM lineage.

Additional self-test and hygiene output:

```text
fact_ledger self-test OK
PASS — Phase 4 apply-readiness manifest validator self-test
PASS — Phase 4 apply-readiness manifest builder self-test
artifact classes: {'canonical-machine': 513, 'reviewer-facing': 395, 'sample': 303, 'source-boundary': 14, 'compact-checksum': 2}
ARTIFACT ERGONOMICS OK — all committed artifacts reviewable/diffable
PASS - git diff --check
```

`tools/lattice_projectors.py self-test` also returned `"ok": true` with all `t1` through `t23` checks true, including `t7_whitelist_read_only`, `t20_wbw_norm_parity`, and registration of both tranche projector IDs.

The combined unit run emitted non-failing Python `ResourceWarning` messages from pre-existing file-handle patterns in `validate_dependency_lattice.py` and `validate_morphosyntax_token_metadata.py`. The dedicated validator CLIs emitted no warnings and exited zero.

## Exact implementation diff summary

Captured with `git log --stat --oneline f706698..HEAD` before adding this report:

```text
91a3b27 tranche1: trace DOM fixture expectations
 .../examples/tranche1/dom-consumption.expectations.jsonl | 16 ++++++++--------
 tools/test_tranche1_projection.py                        | 13 +++++++++++++
 tools/tranche1_projection.py                             |  4 ++++
 3 files changed, 25 insertions(+), 8 deletions(-)
cfa95a8 tranche1: add non-authorizing apply gate
 qamus/examples/tranche1/README.md                  |   7 +
 qamus/examples/tranche1/apply-plan.jsonl           |   4 +
 .../tranche1/apply-readiness-manifest.json         | 164 +++++++++++++++++++++
 qamus/examples/tranche1/human-review-packet.json   | 141 ++++++++++++++++++
 .../phase4-apply-readiness-manifest.schema.json    |  43 ++++++
 tools/build_phase4_apply_readiness_manifest.py     |  48 +++++-
 tools/test_tranche1_projection.py                  |  61 ++++++++
 tools/tranche1_projection.py                       | 128 +++++++++++++++-
 tools/validate_phase4_apply_readiness_manifest.py  |  81 +++++++++-
 9 files changed, 672 insertions(+), 5 deletions(-)
fa0e01f tranche1: validate projection parity and lineage
 qamus/examples/tranche1/README.md                  |  17 +
 .../tranche1/canonical-hover-payload.jsonl         |   8 +-
 qamus/examples/tranche1/projection-crosswalk.jsonl |   8 +-
 .../tranche1/public-hover-projections.jsonl        |   8 +-
 tools/test_tranche1_projection.py                  |  57 +++
 tools/tranche1_projection.py                       |   3 +-
 tools/validate_tranche1_projection.py              | 382 +++++++++++++++++++++
 7 files changed, 470 insertions(+), 13 deletions(-)
fc5146f tranche1: compile eight canary fixtures
 qamus/examples/tranche1/canary-policy.json         | 129 ++++
 .../tranche1/canonical-hover-payload.jsonl         |   4 +
 qamus/examples/tranche1/dependency-lattice.jsonl   |   2 +
 .../tranche1/dom-consumption.expectations.jsonl    |   8 +
 qamus/examples/tranche1/fact-ledger.jsonl          |   8 +
 qamus/examples/tranche1/morphology-lattice.jsonl   |   4 +
 qamus/examples/tranche1/morphosyntax-token.jsonl   |   4 +
 .../tranche1/normalized-public-payload.jsonl       |   8 +
 qamus/examples/tranche1/projection-crosswalk.jsonl |   8 +
 .../tranche1/public-hover-projections.jsonl        |   4 +
 .../examples/tranche1/renderer-completeness.jsonl  |   4 +
 qamus/examples/tranche1/rich-hover-norm.jsonl      |   4 +
 qamus/examples/tranche1/source-canaries.jsonl      |   8 +
 qamus/examples/tranche1/unresolved-queue.jsonl     |   4 +
 tools/test_tranche1_projection.py                  |  60 ++
 tools/tranche1_projection.py                       | 818 +++++++++++++++++++++
 16 files changed, 1077 insertions(+)
ad28489 tranche1: register fixture projectors
 qamus/lattice/registered-projectors.json   | 67 ++++++++++++++++++++++++
 qamus/schemas/projector-record.schema.json |  8 +++
 tools/fact_projectors.py                   | 73 ++++++++++++++++++++++++++
 tools/lattice_projectors.py                | 83 ++++++++++++++++++++++++++++++
 tools/test_fact_projectors.py              |  4 +-
 tools/test_lattice_projectors.py           |  2 +
 tools/test_tranche1_projection.py          | 74 ++++++++++++++++++++++++++
 7 files changed, 310 insertions(+), 1 deletion(-)
029bddc tranche1: add projection lineage schemas
 qamus/schemas/canonical-hover-payload.schema.json  |  24 +++++
 .../dependency-candidate-lattice.schema.json       |  24 +++++
 qamus/schemas/fact-ledger-row.schema.json          |  27 +++++
 .../morphology-candidate-lattice.schema.json       |  26 ++++-
 qamus/schemas/morphosyntax-token.schema.json       |  24 +++++
 qamus/schemas/public-hover-projection.schema.json  |  24 +++++
 .../tranche1-projection-crosswalk.schema.json      | 111 +++++++++++++++++++++
 tools/test_tranche1_projection.py                  |  80 +++++++++++++++
 8 files changed, 339 insertions(+), 1 deletion(-)
ae49020 tranche1: plan eight canary implementation
 .../2026-07-16-tranche1-pedagogical-projection.md  | 400 +++++++++++++++++++++
 1 file changed, 400 insertions(+)
7f15187 tranche1: document fixture projection design
 ...07-16-tranche1-pedagogical-projection-design.md | 91 ++++++++++++++++++++++
 1 file changed, 91 insertions(+)
```

Aggregate implementation diff before this report:

```text
39 files changed, 3362 insertions(+), 6 deletions(-)
```

Every implementation commit message begins with `tranche1:`. No push was performed.

## Risks and remaining gates

1. `qamus/reports/rich-seg-known-debt.meta.json` is stale against the active corpus: it records `34322` rows and SHA-256 `1c06d85a28cb4c2733c1aeb394b15e200e2b483d62b0a740f5cd20d466c0903c`, while the verified active snapshot is `34323` rows and `5805cc9f...ac6e`. This tranche does not rewrite that metadata; any future apply must reconcile it and fail closed on mismatch.
2. The corpus file is outside a Git repository. The manifest therefore records corpus count/hash separately and scopes `source_commit` to the pristine Fusha checkout; it does not imply a Git commit for the data checkout.
3. Candidate morphology and syntax remain review-gated. Existing source prose or typed-looking arrays were not upgraded to scholar/source certification.
4. The DOM artifact is an expectation fixture only. No browser, page, public DOM, CSS, legend, accessibility, or runtime consumption was tested.
5. All Phase 4 execution gates are `not_run`. The documented missing applier remains missing and was not recreated. A future owner-authorized apply would still require backup, append-only ledger, rebuild, validation, health check, public readback, boundary scan, and rollback rehearsal.
6. Non-failing `ResourceWarning` messages remain in two pre-existing validator modules during the combined unit process; dedicated validator commands are clean.

## EXACT NONCLAIMS

- This is fixture-only architecture proof. It is not a live or deployed change.
- It does not linguistically certify any root, lemma, singular, plural/dual, Form, pattern, participle, maṣdar, weak/hamzated/geminate operation, particle sense, case, mood, governor, attachment, agreement, referent, or reading. Existing source claims remain candidates unless separately source/scholar certified.
- It does not guess or certify a singular, template, root, case, ending, or syntactic role for a source-gap or evidence-gap canary. In particular, `2:13:12` remains `source_gap`, `7:54:23` remains `producer_pending`, and `5:2:12` remains `syntax_pending`.
- It does not establish that any of the four candidate projections is deployable. The 4+4 result is a fixture expectation, not a linguistic verdict.
- It does not perform browser, live-site, public HTML/CSS, computed-style, accessibility, SSH, production, deployment, publication, release, or post-deploy readback.
- It does not claim a live DOM assertion. `dom-consumption.expectations.jsonl` records expected fixture consumption only.
- It does not mutate the whitelist, `entries.jsonl`, `wbw.js`, `wbw.css`, any live source, or any production artifact.
- It does not recreate or substitute for the missing applier.
- It does not authorize or perform apply, merge, push, restart, deploy, publication, or release. The manifest remains `pre_apply_not_authorized`, all future execution gates remain `not_run`, and authorized live mutations remain zero.
- It does not prove corpus-wide linguistic correctness, coverage, deterministic-regeneration percentage, page/card appearance counts, or learner interaction counts. The proof is limited to the eight exact source-addressed fixtures.
- It does not treat a fact ID, typed-looking source field, projector output, passing schema, or passing renderer fixture as scholar certification.
- It does not treat the stale known-debt metadata as current source truth; the active corpus count/hash are recorded separately and the mismatch remains an explicit future gate.
