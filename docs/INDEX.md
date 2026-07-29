# Documentation index — Fusha repo (authoritative)

Status: adopted 2026-07-29 (institutionalization lane A).
Purpose: a cold reader (human or lower-cost model) starts here. Every document
in this repo is classified below as **authoritative**, **historical**,
**generated**, **example**, or **superseded**, with a one-line role. When two
documents disagree, the authority-precedence order in §1 decides.

## 1. Authority precedence (§26, owner-ruled 2026-07-29 — controlling)

1. **Verified repo artifacts + tests** (schemas, validators, committed data,
   `tools/check_regressions.py` green output)
2. **Owner decision ledger** (private-side; rulings mirrored into this repo's
   docs where public-safe)
3. **Rate-limit handoff steer + addendum** (private-side, 2026-07-29)
4. **Canonical architecture docs** (this index, `docs/architecture/*`, the
   contract docs marked authoritative below)
5. **Historical charters / dashboards**
6. **Chat transcripts**

Lower tiers never override higher tiers. A generated report never overrides a
policy doc; a policy doc never overrides a failing validator.

## 2. Programme status block (owner-ruled, 2026-07-29 — record verbatim)

```
FUSHA_SHADOW_SCHEDULING: RETIRED_BY_OWNER
FUSHA_30RUN_14DAY_QUALIFICATION: RETIRED_BY_OWNER
FUSHA_WBW_TIMER: PRESERVED
FUSHA_SHADOW_HISTORICAL_EVIDENCE: PRESERVED_AS_HISTORY_ONLY
LIVE_QAMUS_MUTATION: NOT_AUTHORIZED
WEBSITE_FRONTEND: OWNED_BY_THE_SEPARATE_WEBSITE_AGENT
```

## 3. SUPERSEDED concepts (explicit markers — do not build on these)

| Concept | Status | What replaces it |
|---|---|---|
| Recurring shadow scheduling (daily `dawah-fusha-shadow` timer runs) | **SUPERSEDED — RETIRED_BY_OWNER 2026-07-29.** Timer disabled and stopped; local scheduled task deleted. The WBW timer is PRESERVED and unaffected. | Future shadow runs require explicit bounded owner authorization per run. `docs/SHADOW-RUNNER.md` (the manual-invocation contract) already reflects the post-retirement posture. |
| 30-run / 14-day shadow qualification window | **SUPERSEDED — RETIRED_BY_OWNER.** Qualification-ledger evidence is PRESERVED_AS_HISTORY_ONLY. | Owner adoption decisions (ADR-003 G8) made explicitly, never by accumulated run count. |
| "Autonomous live deploy" phrasings in old directives | **SUPERSEDED.** No autonomous deployment path exists or is authorized. | `LIVE_QAMUS_MUTATION: NOT_AUTHORIZED`; every apply is a separate owner-gated step (`docs/CI.md`: "CI results are evidence, not adoption"). |
| Coarse `PFX/STEM/SUF` segmentation as target quality | **SUPERSEDED.** Legacy-valid only; never target quality (owner decision D-1: rich letter-level projection is the target). | `docs/qamus/particle-projection-contract.md` + `docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md` (N-SEG-03 tiered standard). Note: `docs/parser/index.html` is a stale demo still rendering a `PFX` label — example class, not a target. |
| Simplified linkage-board hovers as final standard | **SUPERSEDED.** The W5/entry-linkage board's simplified hovers were an interim sketch. | The rich-at-rest + rich-hover two-surface contract (`docs/architecture/two-surface-contract.md` and its sources). |
| Proposal population labelled "VN-03" (v196–v296) | **SUPERSEDED — VN-03 namespace ruling 2026-07-29.** Authoritative VN-03 = v142–v188 + n0136–n0180 + its 3,280-row worklist. The proposal population is renamed to the `VNPROP-xx` namespace with provenance preserved. | `qamus/examples/p007-li-pilot/vn-unlock.json` uses `VNPROP-xx` keys and records the ruling. Never quote VN-03 counts except against the contract namespace. |

Additionally superseded by their own banners: the 13 HISTORICAL-bannered
reports listed in §4.6, plus the un-bannered stale coverage reports flagged
there. Coverage truth lives only in `docs/STATUS.md`.

## 4. Document inventory

### 4.1 Entry points and repo-wide rules (authoritative)

| Path | Role |
|---|---|
| `README.md` | Repo front door: Fusha is the portable language-intelligence layer; not the app; never writes to the live site. |
| `AGENTS.md` | Hard rules for agents (no live mutation, no external gloss text, `norm()` never certifies, pending-over-wrong, grammar-safety gate). |
| `INSTALL.md` | Skill install instructions. |
| `provenance/README.md` | Where published facts come from; what may be committed. |
| `provenance/source-boundaries.md` | The enforceable numbered source-boundary rules (read first). |
| `provenance/public-runnability.md` | Which tools run on a fresh public clone (gated by `tools/validate_public_runnability.py`). |
| `docs/INDEX.md` | This index. |

### 4.2 Canonical architecture docs (authoritative — precedence tier 4)

| Path | Role |
|---|---|
| `docs/architecture/transclusion-graph.md` | Canonical node types, typed edge families, identity rules, worked examples from committed artifacts. |
| `docs/architecture/meta-transclusive-projection.md` | The 15-stage engineering explanation of the projection pipeline, grounded in real tools; reuse-safety vocabulary. |
| `docs/architecture/two-surface-contract.md` | Rich-at-rest + rich-hover relationship; the one-artifact rule; pointers to the binding contracts. |
| `docs/architecture/evidence-and-certification.md` | Evidence-mode ladder, MCP operational discipline + index hazards, two-vote v1.1, adjudication, revocation; 2026-07-29 §20 rulings recorded. |
| `docs/architecture/dogfood-flywheel.md` | The dogfood loop and per-family compounding-impact accounting requirements. |
| `docs/architecture/translation-projection.md` | Translation as a downstream lattice consumer; forbidden inferences; the 5 required future fixture types. |

### 4.3 Policy and contract docs (authoritative)

| Path | Role |
|---|---|
| `docs/STATUS.md` | SSOT for live glossed coverage (98.72%, as-of 2026-07-07/checked 2026-07-10 — time-decaying; not recomputable from this repo). |
| `docs/GLOSSARY.md` | Canonical vocabulary; defers to schemas and STATUS.md. |
| `docs/CLAIMS-AND-RELEASES.md` | Claim → validator table: what Fusha may claim and which executable artifact backs it. |
| `docs/CI.md` | The pr-gate / full-gate public CI contract; green is evidence, never adoption. |
| `docs/SHADOW-RUNNER.md` | Manual, owner-invoked shadow-compile contract (T9B); no scheduling — already post-retirement posture. |
| `docs/certification-policy.md` | Adopted certified-lemma gated-fanout policy (three fanout gates; particles never fan out via `lemma_pattern_pos`). |
| `docs/certification-authority.md` | Fact-level certification layer: evidence modes, sufficiency ladder, two-vote, revocation, canaries. |
| `docs/certification-store-reconciliation.md` | Typed-claim plane is canonical for fact identity; token-layer ledger frozen as historical evidence. |
| `docs/qamus-public-entry-count-policy.md` | Public dataset is exactly 2,092 entries (machine-enforced). |
| `docs/source-selection-policy.md` | Which authored candidate becomes the transclusion source. |
| `docs/VN-OPERATIONS.md` | The reusable VN tranche completion method (authoritative copy). |
| `docs/vn-tranche-completion-playbook.md` | **Superseded near-duplicate** of `VN-OPERATIONS.md` (older VN-00→VN-20 scoping); consult VN-OPERATIONS.md. |
| `docs/qamus/particle-projection-contract.md` | Two-surface particle projection contract; executable twin `tools/validate_particle_projection_parity.py`. |
| `docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md` | `norm@1` — what a correct rich-hover row looks like (DRAFT, authored, not yet enforced). |
| `docs/qamus/particle-rich-hover-templates.md` | Learner-language hover templates T1–T5 (candidate spec for `fd_compiler.py` adoption). |
| `docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md` | `qamus.website_projection_payload.v1` payload contract; validator `tools/validate_website_payload.py` wins on disagreement. |
| `docs/qamus/website-handoff/HANDOFF-RECORD.md` | Living delivery/coordination record with the separate website agent. |
| `qamus/reports/grammar-risk-policy.md` | Binding GP0 governance for grammar-affecting decisions. |
| `qamus/reports/artifact-ergonomics-report.md` | The A1 artifact-ergonomics contract (prose companion to the taxonomy). |
| `qamus/reports/corpus-to-qamus-pipeline.md` | The corpus → catalogue + worklist pipeline (read-only, never a live write). |
| `qamus/reports/morphosyntax-token-contract.md` | Parse-layer contract: concise public hover + separate grammar metadata. |
| `qamus/reports/parser-checker-substrate.md` | Source-addressed parser/checker verifier contract. |
| `qamus/reports/live-shadow-graph-workflow.md` | Read-only shadow-graph rebuild/validation gates. |
| `qamus/reports/PROJECTION-ACCELERATION.md` | T12 deterministic same-surface projection lattice (candidate-only). |
| `qamus/reports/ROOT-INHERITANCE-JOIN.md` | T13 certified-root projection (candidate-only; pattern never certifies a root). |
| `qamus/reports/dataset-integrity-blocker.md` | Open blocker: `entries.jsonl` checksum mismatch; owner decision required. |

### 4.4 Parser-layer docs (`docs/parser/`)

Authoritative: `claim-boundary.md`, `largelexicon-claim-boundary.md`,
`fusha-cli-contract.md`, `canonical-hover-payload-table.md`,
`TRANSCLUSION.md` (leads with its defect box), 
`meta-transclusive-lattice-projection.md` (two-layer model; superseded on
counts by TRANSCLUSION.md's live `#status_counts` redirect),
`largelexicon-collision-safety.md`, `largelexicon-source-ledger.md`,
`source-ledger-and-split-policy.md`.

Generated: `qamus-grammar-v1-class-map.md` (emitted by
`tools/validate_schema_coherence.py --emit-class-map`; do not hand-edit).

Historical (implementation records): `largelexicon-implementation.md`,
`largelexicon-largerollout3-implementation.md`,
`qamustyping3-implementation.md`, `qamustyping4-implementation.md`.

Example: `index.html` — static demo page, not gated, still shows a coarse
`PFX` label (see §3 supersession of coarse segmentation as target).

### 4.5 Skills, schemas, registries (authoritative machine SSOT)

| Path | Role |
|---|---|
| `sarf/SKILL.md`, `nahw/SKILL.md` | The operational morphology/syntax gates (the engine). |
| `skills/sarf/SKILL.md`, `skills/nahw/SKILL.md` | Installable wrappers deferring to the above. |
| `qamus/schemas/*.schema.json` (87) | The main machine contract plane (entry, certified-lemma, typed-claim contract, two-vote artifact, fact ledger row, morphosyntax token, particle-edge ontology, projector record, acceleration/dogfood/compounding-impact ledgers, …). |
| `fusha/morphology/schemas/`, `fusha/parser/schemas/` | Morphology-generation and parser result schemas. |
| `sources/source-adapter.schema.json`, `sources/tafsir_mcp/schema.json`, `provenance/informed-by.schema.json` | Source-boundary schemas. |
| `qamus/skills/rule-registry.jsonl` + `rule-registry-increment-2{1,2,3,4}.jsonl` | Canonical versioned sarf/nahw rule registry + accepted increments. |
| `qamus/skills/rule-registry-richseg.jsonl` + `.README.md` | Draft rich-seg rules — candidate, owner adjudication pending; never mark accepted. |
| `qamus/skills/particle-function-registry.jsonl` | Particle function vocabulary. |
| `qamus/skills/reason-key-registry.jsonl` | Controlled reason-key vocabulary (two-vote v1.1 comparison keys). |
| `skills/registry/skill-rule-registry.json` | Installable skill-rule registry. |
| `qamus/registry/qg-class-reconciliation.{json,md}`, `palette-collision-matrix.{json,md}`, `palette-source-snapshot.css` | Generated display-class/palette reconciliation outputs. |
| `qamus/lattice/registered-projectors.json` | The projector registry (gate tiers, guards, compatibility classes). |
| `qamus/task-packets/TP-*.json` | **Public executable task packets** — one per `qamus/work-queues/next-actions.jsonl` queue head (`repo_packet` field) plus the doc-linkcheck packet; schema `qamus/schemas/task-packet.schema.json`, gated by `tools/validate_task_packets.py`. Start here to execute a queue head cold. |
| `qamus/task-packets/tp-p007-ds-w1-covered-locs.json` | Wave-1 coverage manifest (260 covered canonical locs + per-loc evidence sha256; evidence-custody §2 rows) — the deterministic exclusion set for TP-P007-DS-W2. |

### 4.6 Generated / batch-run reports (`qamus/reports/`, grouped by glob)

Generated evidence of past runs — cite as history, never as current policy:

- `full-corpus-dogfood-vn??-20260627.md` (21) + the 7 category-sliced
  `full-corpus-dogfood-*-20260627.md` — the 2026-06-27 dogfood sweep.
- `vn-rich-*-standard-rich-hover-*.md` (20) and `vn-rich-cert-*-standard-*.md`
  (20) + 2 calibration variants — per-tranche rich-hover shape + cert queues.
- `p-rich-{cert-,}0?-*.md` (8) — particle-family pilot equivalents.
- `rh-live-*.md` (~12) — RH-LIVE operational run artifacts.
- `source-photo-verification-batch-*.md` (2).
- `qamus/reports/closure-2092/` — bulk apply/two-vote/repair run records.
- `qamus/reports/artifact-taxonomy.md` — generated canonical index of **data**
  artifacts (5 ergonomics classes); complementary to this doc index.

**Superseded (HISTORICAL banner present, 13):**
`baseline-reconciliation-20260624.md`, `coverage-90-tranche-report-20260624.md`,
`fusha-production-bridge-status.md`, `host-lexeme-authoring-report.md`,
`hover-gloss-terminal-scoreboard.md`, `hover-token-completion.md`,
`language-state-machine-report.md`, `next-batch-resume-plan.md`,
`qamus-2092-scoreboard.md`, `source-address-completion.md`,
`suffix-pronoun-expansion-report.md`, `suffix-pronoun-hover-report.md`,
`token-addressed-hover-layer.md`.

**Superseded (stale figures, banner MISSING — treat as superseded anyway):**
`coverage-yield-ledger-90.md`, `qamus-2092-terminal-scoreboard.md`,
`hover-token-terminal-matrix.md`. Coverage truth is `docs/STATUS.md` only.

### 4.7 Historical plans, specs and lane reports

- `docs/superpowers/plans/*.md` (22) — executed implementation plans
  (2026-07-01 → 2026-07-17), historical.
- `docs/superpowers/specs/*-design.md` (16) — design specs superseded by the
  shipped code and schemas they describe, historical.
- Root `{FA,FAM3,FAM4,FAM5,FB1,FC1,FD,FD2,IDX,ONTO,PROOFN,PROOFV,TRANCHE1,VNMAP}-REPORT.md`
  (14) — per-lane completion reports pairing with the plans, historical.
- `docs/QURANIC-ANCHOR-AND-FLYWHEEL.md` — owner-adopted charter (authoritative
  for self-description; carries its own four epistemic labels).

### 4.8 Example / evidence artifacts (`qamus/examples/`)

Committed worked evidence, never policy: the p007 pilot
(`qamus/examples/p007-li-pilot/`), website payload samples
(`qamus/examples/website-payloads/`), proof packets
(`proof-noun-sufaha/`, `proof-verb/`, `proof-particle/`), hazard fixtures
(`qamus/examples/hazards/`), per-family FAM/FB/FC/FD lanes, and the
`*.sample.*` files named by `qamus/reports/artifact-taxonomy.md`.

## 5. Reading order for a cold model

1. `README.md` → `AGENTS.md` → `provenance/source-boundaries.md`
2. `docs/INDEX.md` (this file) — precedence, status block, supersessions
3. `docs/architecture/transclusion-graph.md` →
   `docs/architecture/meta-transclusive-projection.md` →
   `docs/architecture/two-surface-contract.md` →
   `docs/architecture/evidence-and-certification.md` →
   `docs/architecture/dogfood-flywheel.md`
4. `sarf/SKILL.md` + `nahw/SKILL.md` before touching any Arabic decision
5. Run `python tools/check_regressions.py` before and after any change

---
Verified against: commit 637d7da (origin/main, 2026-07-29); inventory audited
over `docs/`, `docs/parser/`, `docs/qamus/`, `docs/superpowers/`,
`qamus/reports/` (159 .md), `qamus/schemas/` (87 schemas), `qamus/skills/`,
`qamus/examples/`, `provenance/`; harness `tools/check_regressions.py`
ALL REGRESSION CHECKS PASS at this commit.
