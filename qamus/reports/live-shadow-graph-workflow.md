# Live Shadow Graph Workflow

Status: Phase 2 read-only tooling contract. This report describes durable gates for rebuilding and validating a
Qamus shadow graph before future hover editing or admin UI work. It is not a coverage report and does not claim
hover closure progress.

## Truth Owners

- Live WBW artifact: read-only runtime input supplied to `tools/build_live_shadow_graph.py --wbw-json`.
- Live entries: read-only runtime input supplied to `--entries-dir`.
- Live token decisions: read-only runtime input supplied to `--decision-ledger`.
- Fusha indexes: graph model/reference truth, not live behavior truth. Optional joins through `--fusha-index-dir`
  enrich candidate/sibling explanations only; exact token identity and live behavior still come from live inputs.
- Phase 1 shadow outputs: baseline evidence, not a live source of truth.

The tools intentionally do not embed private server paths. Server acceptance passes those paths at runtime.

## Durable Tools

- `tools/build_live_shadow_graph.py`: builds a shadow graph from explicit local input paths and refuses unsafe output
  roots. It requires `--live-readonly` and `--no-live-write` outside fixture mode. Optional Fusha graph exports are
  recorded as `exact`, `candidate`, or `inferred` join statuses; candidate/inferred joins cannot make a parse family
  propagation-safe. New runs also emit `phase2-run-manifest.json`, a compact receipt tying the generated graph to
  input hashes, no-write flags, forbidden-root guards, counts, detector-maturity warnings, and the public/private
  boundary. `parse-keys.jsonl` is one row per parse family with `canonical_parse_object`, `seen_locs`, and
  `family_size`; exact token rows in `token-index.jsonl` carry `parse_key`/`parse_id` backlinks and remain the token
  identity boundary.
- `tools/validate_phase1_shadow_graph.py`: validates required Phase 1/2 shadow artifacts, nonzero rows, exact
  counts, token/hover/parse linkage, no orphan count, public-boundary markers, and the reusable parse-key family
  contract from `tools/validate_parse_key_contract.py`.
- `tools/scan_public_boundary.py`: classifies public readback leaks separately from internal-only provenance.
- `tools/compare_wbw_artifacts.py`: compares WBW artifacts without reconciling or copying either side.
- `tools/summarize_shadow_closure_queue.py`: consumes an already-built shadow graph and emits closure-lane,
  blocker, family-size, sample-token summaries, and optional source-addressed review-pack JSONL rows. It is
  read-only and does not inspect or mutate live inputs. Review-pack rows include `gate_reasons` so two-vote,
  collision, source-disagreement, pending, and preview-only lanes are explainable instead of mere labels.
- `tools/summarize_rich_wbw_roles.py`: consumes `parse-keys.jsonl` from an already-built shadow graph and emits a
  strict rich-WBW segment-role taxonomy. It reports every observed role, occurrence counts, lanes/gates, samples, and
  whether the role is explicitly gated, explicitly allowlisted, or unknown. Strict mode fails if an unknown role is
  observed, or if a grammar-sensitive role such as `preposition`, `conjunction`, `vocative_particle`,
  `object_pronoun`, `result_particle`, `resumption_particle`, or `adjectival_state` appears in an `auto_safe` gate or
  `propagation_safe` lane.
- `tools/validate_rich_wbw_gate_cases.py`: Phase 2.9 closeout guard for the named rich-WBW rows that motivated the
  current parser/renderer contract. It checks that `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`, `وَٱلْجِبَالُ`,
  `وَٱلشَّجَرُ`, `بِٱلْمَعْرُوفِ`, and `يَٰٓأَيُّهَا` are present in both parse-key and review-pack artifacts, remain
  `two_vote_required`, carry rich component evidence in component-only fields, and are not weakened into auto-safe
  propagation. It also rejects any rich component evidence that is placed into whole-token `qamus_entry_candidates`.
- `tools/build_shadow_admin_debug_pack.py`: Phase 3 read-only admin/debug scaffolding. It consumes an already-built
  shadow graph and emits a static local `index.html` plus `admin-debug-pack.json` with hover inspectors, entry
  backlinks, parse-family views, blocker queues, and repair-preview stubs. It is not a live route, does not discover
  server paths, refuses likely live/runtime output paths, and always marks the pack `live_mutation_allowed=false`.
- `tools/validate_shadow_admin_debug_pack.py`: validates the Phase 3 static admin/debug pack contract. It rejects
  empty packs, missing Phase 3 views, broken `quran:S:A:W -> wbw:S:A:W` identity chains, public-exposable inspector
  records, `live_mutation_allowed=true`, malformed repair-preview stubs, and public-boundary leaks.
- `tools/query_shadow_admin_debug_pack.py`: read-only CLI for the validated Phase 3 pack. It answers reverse traces
  (`wbw:S:A:W -> quran:S:A:W -> parse:<hash> -> entry candidates -> affected siblings`), forward traces
  (`qamus:<id> -> dependent tokens -> parse families -> decisions/hover slots`), and parse-family traces without
  re-reading live artifacts or using raw Arabic surfaces as identity.
- `tools/validate_shadow_admin_route_contract.py`: validates the future app/admin route contract for this static
  pack before any live route exists. It requires admin-only authenticated `GET` routes, exact graph identities,
  `live_mutation_allowed=false`, no apply/write/mutate route wording, no raw-surface identity, no parse-key-primary
  identity, a validated static `shadow_admin_debug_pack` source-pack contract, and a source-clean public/private
  boundary. The source-pack contract rejects live paths, public webroot paths, and dirty mirror repos as route inputs,
  so a future UI scaffold cannot quietly become an edit/apply endpoint or rediscover live data outside the sealed pack.
- `tools/plan_phase4_closure_tranche.py`: consumes a validated shadow review-pack JSONL and emits a bounded Phase 4
  dry-run tranche. It prioritizes source-addressed review work, carries whole-token and rich component candidate
  evidence separately, and keeps every row `allowed_next_step=review_only`, `apply_allowed=false`,
  `live_mutation_allowed=false`, and `closure_claim_allowed=false`. Component candidates from rich WBW segments remain
  review evidence only; they cannot weaken a row to an auto-safe gate.
- `tools/validate_phase4_closure_tranche.py`: validates the Phase 4 dry-run tranche contract. It rejects malformed
  `quran:S:A:W`/`wbw:S:A:W` identities, parse-key-primary identity, source-boundary leaks, live/apply/coverage claims,
  component candidates inside propagation-safe rows, and any component-enriched row that has been weakened to an
  auto-safe gate.
- `tools/build_phase4_two_vote_requests.py`: consumes a validated Phase 4 dry-run tranche and emits exact-addressed
  two-vote request packets only for rows still in `lane=two_vote_required` with `required_gate=two_vote_required`.
  These packets are the review bridge between Phase 4 tranche planning and future sarf/nahw votes. They preserve
  component candidates in `candidate_evidence.component_candidates` / `component_candidate_joins`, keep whole-token
  candidates separate, and state that component candidates, raw surface, norm-only recall, and parse keys alone cannot
  certify a hover. Each packet also carries a deterministic `agreement_key_hint`; this is a review coordination key
  only, not propagation evidence and not a weakening of the `two_vote_required` gate.
- `tools/validate_phase4_two_vote_requests.py`: validates Phase 4 two-vote request packets. It rejects non-exact
  identities, public-boundary leakage, weakened gates, non-two-vote lanes, missing component provenance, component
  candidates marked certifying, missing `agreement_key_hint`, live/apply/coverage claims, and vacuous zero-row request
  files.
- `tools/validate_phase4_two_vote_responses.py`: validates exact-addressed Phase 4 sarf/nahw response rows before
  reconciliation. It requires the response to derive from a known two-vote request, preserves the exact
  `quran:S:A:W` / `wbw:S:A:W` identity, rejects public gloss provenance leaks, requires approved responses to use
  the request's exact `agreement_key_hint`, and keeps component candidates explicitly non-certifying.
- `tools/reconcile_phase4_two_vote_responses.py`: reconciles validated sarf and nahw response rows into internal
  review output. It certifies only same-gloss, same-reason, same-scope agreement and emits `certified_not_applied`
  rows with `apply_allowed=false`; missing, pending, rejected, or disagreeing votes stay unresolved. It does not
  mutate live Qamus data, rebuild WBW, or claim closure progress.
- `tools/build_phase4_draft_token_decision_ledger.py`: converts a validated Phase 4 hover decision plan into a
  source-only draft token-decision ledger for owner review. The emitted rows copy only the source-clean
  `token_decision_preview` (`loc`, `gloss`, `src=qamus`, `kind=authored`, `lang=en`) plus plan lineage. They remain
  `status=draft_not_applied` and cannot mutate live Qamus data, rebuild WBW, or substitute for the owner-gated
  append-only live ledger.
- `tools/validate_phase4_draft_token_decision_ledger.py`: validates that draft ledger rows derive from the exact hover
  decision plan, preserve `quran:S:A:W` / `wbw:S:A:W` identity, reject public provenance leakage, keep all live/apply
  policy fields false, and require the future backup/rebuild/validation/health/readback gates.
- `tools/build_phase4_owner_authorization_request.py`: bundles a validated apply-readiness manifest and source-only
  draft token-decision ledger into one owner review request. It hashes both artifacts, records exact row counts and
  sample source-clean token decisions, and keeps `owner_authorization.status=not_provided`, `apply_allowed=false`,
  `live_mutation_allowed=false`, `wbw_rebuild_allowed=false`, `service_restart_allowed=false`,
  `mirror_sync_allowed=false`, and `closure_claim_allowed=false`.
- `tools/validate_phase4_owner_authorization_request.py`: validates that the owner request is still only a request. It
  rejects provided/approved authorization, mismatched manifest or draft-ledger hashes/counts, public provenance leaks,
  non-source-clean sample decisions, and any live/apply/closure policy flag set true.
- `tools/plan_shadow_hover_edit_intent.py`: read-only CLI for planning future hover-edit intents from a validated
  Phase 3 admin/debug pack. It emits validator-clean JSONL rows for token-only, parse-family, or entry/sense edit
  intent review, preserves exact `wbw:S:A:W -> quran:S:A:W -> parse:<hash> -> qamus:<id>#sense=<n>` identity, and
  refuses parse-family intents when the pack marks that family non-propagation-safe. It does not write live Qamus
  data, rebuild WBW, mutate entries, or create repair ledgers.
- `tools/plan_shadow_repair_impact_preview.py`: read-only CLI that turns validated hover-edit intent rows into
  validated repair-impact-preview rows. It makes the future apply target explicit as a `qamus:<id>#field=<path>`
  address, carries explicit affected token/hover/parse counts separately from sampled address lists, adds
  `sample_tokens_are_complete`, adds a rollback strategy, and keeps `live_mutation_allowed=false`. It is still a
  preview artifact only; no decision ledger, entry JSON, WBW artifact, or app route is changed. Token-only previews
  that have no resolved entry/sense use the deterministic overlay target
  `qamus:hover-overrides#field=token_overrides[wbw:S:A:W].gloss` rather than inventing an entry.
- `tools/build_production_bug_lesson.py`: Phase 3.5 bridge from graph-addressed hover edit intents to production
  bug lesson rows. It copies exact token, hover slot, parse, decision, entry/sense, gate, scope, and target-address
  provenance from a validated edit intent, while the reviewer supplies the sarf/nahw lesson text. The emitted JSONL
  validates with `tools/validate_production_bug_lessons.py` and remains read-only: no live Qamus data, WBW artifact,
  entry JSON, decision ledger, or app route is changed.
- `tools/validate_detector_maturity.py`: validates standalone or embedded detector-maturity records so Phase 2
  reports cannot treat `two_vote_required=0` or `source_disagreement=0` as proof that no such cases exist.
- `tools/validate_live_shadow_run_manifest.py`: validates `phase2-run-manifest.json` so future live-readonly graph
  builds cannot be treated as evidence unless they prove input artifact identity, output isolation, no live mutation,
  no WBW rebuild, no service restart, no mirror sync, nonzero counts, zero orphan edges, detector-gap warnings, and a
  source-clean public boundary.
- `tools/validate_public_private_boundary.py`: validates the reusable public/private boundary object used by
  decision, edit-intent, repair-preview, and manifest artifacts. It keeps `src=qamus`, `kind=authored`, `lang=en`,
  public source-name flags false, and forbids public field names that smuggle adapter labels or private paths.
- `tools/validate_parse_key_contract.py`: validates parse-key family rows as grammar-reuse nodes, not identities. It
  checks exact token backlinks, canonical hash stability, family-size reconciliation, no surface-only auto-safe rows,
  no multi-candidate propagation, and no grammar-sensitive trigger marked propagation-safe.
- Rich WBW segment roles such as `conjunction`, `resumption_particle`, `preposition`, `vocative_particle`, and
  `addressee_bridge` are grammar-sensitive for propagation. Even when a visible token is resolved, these rows must not
  become `auto_safe` merely because the family has one token; they require the same gate discipline as the corresponding
  `function_particle` / `preposition` / `vocative` parse triggers.
- Rich WBW component evidence is deliberately separate from whole-token Qamus candidates. The builder may emit
  `qamus_component_candidates`, `component_candidate_entries`, and `component_candidate_join_statuses` with
  `source=rich_wbw_segment`, role, segment text, and token loc provenance. These fields are review/impact-preview
  evidence only: they must not contribute to `auto_safe`, source agreement, propagation safety, closure coverage, or
  hover coverage, and they must not infer a missing host entry merely from an article, preposition, conjunction, or
  vocative component.
- `tools/validate_shadow_review_pack.py`: validates that review-pack rows are non-vacuous, exact-addressed with
  `quran:S:A:W` and `wbw:S:A:W`, source-clean at the public boundary, and explicitly non-mutating.
- `tools/validate_decision_linkage.py`: validates that authored decision rows link exact `quran:S:A:W` tokens,
  exact `wbw:S:A:W` hover slots, parse keys, entry/sense or blocker state, and source-clean public boundaries.
- `tools/validate_hover_edit_intent.py`: validates the pre-preview editor contract so future UI/apply paths must
  start from exact `wbw:S:A:W -> quran:S:A:W -> parse:<hash> -> decision/qamus` identity rather than raw surface
  text, parse-key-primary identity, or norm-only certification.
- `tools/validate_repair_impact_preview.py`: validates graph-addressed token-only, parse-family, and entry/sense
  repair previews before any future apply path can use them.
- `tools/validate_production_bug_lessons.py`: keeps production hover failures connected to sarf/nahw procedure,
  regression, learner explanation, drill, and validator work.
- `qamus/examples/detector_maturity.sample.json`: tiny fixture slice for the reusable detector-gap warning:
  zero-count detector output is not absence proof.
- `qamus/examples/live_shadow_run_manifest.sample.json`: tiny fixture receipt showing the no-mutation run contract
  without committing live server paths or full live graph blobs.
- `qamus/examples/parse_key.sample.jsonl`: tiny fixture slice covering a propagation-safe noun family, a
  two-vote-required verb suffix family, and a quarantined `ما` collision family.
- `qamus/examples/decision_linkage.sample.jsonl`: tiny fixture slice covering resolved, pending, and superseded
  decision rows with exact token/hover addresses.
- `qamus/examples/hover_edit_intent.sample.jsonl`: tiny fixture slice covering token-only, parse-family, and
  entry/sense edit intents before repair-impact preview generation.
- `qamus/examples/repair_impact_preview.sample.jsonl`: tiny fixture slice covering the three edit scopes without
  touching live Qamus data.
- `qamus/examples/shadow_review_pack.sample.jsonl`: tiny fixture slice covering propagation-preview, collision
  quarantine, missing-entry, never-auto, and component-enriched two-vote lanes without committing live graph dumps.
- `qamus/examples/shadow_admin_route_contract.sample.json`: tiny future-route contract fixture for read-only,
  admin-only token inspector, entry backlinks, parse family, blocker queue, repair preview, and edit-intent preview
  surfaces. It deliberately contains no app implementation and no live path, and now states that future routes consume
  only a validated static `shadow_admin_debug_pack` from `out/` or committed sample fixtures.

## Acceptance Gates

Read-only live acceptance should run:

```bash
python tools/build_live_shadow_graph.py --live-readonly --no-live-write \
  --entries-dir <live entries dir> \
  --wbw-json <live wbw lookup> \
  --decision-ledger <live token decision ledger> \
  --fusha-index-dir <fusha qamus/indexes/current> \
  --out-dir <isolated shadow output> \
  --forbid-output-root <live app path> \
  --forbid-output-root <live entries dir> \
  --forbid-output-root <live wbw build dir> \
  --forbid-output-root <public webroot>

python tools/validate_phase1_shadow_graph.py <isolated shadow output>
python tools/summarize_shadow_closure_queue.py <isolated shadow output> \
  --out-md <review report> \
  --review-pack-jsonl <review pack jsonl>
python tools/validate_shadow_review_pack.py <review pack jsonl>
python tools/summarize_rich_wbw_roles.py --shadow-dir <isolated shadow output> \
  --out-md <rich-role-taxonomy report> \
  --strict
python tools/validate_rich_wbw_gate_cases.py --shadow-dir <isolated shadow output> \
  --review-pack-jsonl <review pack jsonl>
python tools/scan_public_boundary.py --public <public entry URL> --shadow-dir <isolated shadow output>
python tools/compare_wbw_artifacts.py <live wbw lookup> <mirror wbw lookup>
python tools/validate_detector_maturity.py <review pack jsonl or detector maturity json>
python tools/build_shadow_admin_debug_pack.py --shadow-dir <isolated shadow output> \
  --out-dir <isolated static admin-debug output> \
  --sample-token quran:33:63:1 \
  --sample-token quran:22:18:17 \
  --sample-token quran:2:21:1
python tools/validate_shadow_admin_debug_pack.py <isolated static admin-debug output>/admin-debug-pack.json
python tools/validate_shadow_admin_route_contract.py qamus/examples/shadow_admin_route_contract.sample.json \
  --pack <isolated static admin-debug output>/admin-debug-pack.json
python tools/plan_phase4_closure_tranche.py <review pack jsonl> \
  --out-jsonl <isolated static admin-debug output>/phase4-dry-run-tranche.jsonl \
  --max-rows 25
python tools/validate_phase4_closure_tranche.py \
  <isolated static admin-debug output>/phase4-dry-run-tranche.jsonl
python tools/build_phase4_two_vote_requests.py \
  <isolated static admin-debug output>/phase4-dry-run-tranche.jsonl \
  --out-jsonl <isolated static admin-debug output>/phase4-two-vote-requests.jsonl
python tools/validate_phase4_two_vote_requests.py \
  <isolated static admin-debug output>/phase4-two-vote-requests.jsonl
python tools/validate_phase4_two_vote_responses.py \
  <isolated static admin-debug output>/phase4-two-vote-responses.jsonl \
  --requests <isolated static admin-debug output>/phase4-two-vote-requests.jsonl
python tools/reconcile_phase4_two_vote_responses.py \
  --requests <isolated static admin-debug output>/phase4-two-vote-requests.jsonl \
  --responses <isolated static admin-debug output>/phase4-two-vote-responses.jsonl \
  --certified-out <isolated static admin-debug output>/phase4-two-vote-certified.jsonl \
  --unresolved-out <isolated static admin-debug output>/phase4-two-vote-unresolved.jsonl
python tools/query_shadow_admin_debug_pack.py --pack <isolated static admin-debug output>/admin-debug-pack.json \
  --token quran:33:63:1
python tools/query_shadow_admin_debug_pack.py --pack <isolated static admin-debug output>/admin-debug-pack.json \
  --entry qamus:<id>
python tools/plan_shadow_hover_edit_intent.py --pack <isolated static admin-debug output>/admin-debug-pack.json \
  --scope token_only \
  --token quran:33:63:1 \
  --proposed-hover "ask you" \
  --out-jsonl <isolated static admin-debug output>/token-edit-intent.jsonl
python tools/validate_hover_edit_intent.py <isolated static admin-debug output>/token-edit-intent.jsonl
python tools/plan_shadow_repair_impact_preview.py \
  --intent-jsonl <isolated static admin-debug output>/token-edit-intent.jsonl \
  --out-jsonl <isolated static admin-debug output>/token-repair-preview.jsonl
python tools/validate_repair_impact_preview.py <isolated static admin-debug output>/token-repair-preview.jsonl
python tools/build_production_bug_lesson.py \
  --intent-jsonl <isolated static admin-debug output>/token-edit-intent.jsonl \
  --edit-intent-id edit-intent:token-33-63-1 \
  --bug-class verb_object_suffix_omitted \
  --what-failed "The entry/lemma gloss omitted the attached object pronoun." \
  --sarf-lesson "Segment the host and suffix pronoun before choosing a hover." \
  --nahw-lesson "The explicit following subject does not erase the attached object." \
  --learner-explanation "The final kaaf contributes 'you'." \
  --drill-prompt "Mark the prefix, stem, and object pronoun in يَسْأَلُكَ." \
  --level beginner \
  --procedure-link sarf/procedures/clitic-and-host-morphology.md \
  --procedure-link nahw/procedures/pronoun-attachment.md \
  --regression-fixture-link qamus/examples/production_bug_lesson.sample.jsonl \
  --out-jsonl <isolated static admin-debug output>/token-production-bug-lesson.jsonl
python tools/validate_production_bug_lessons.py <isolated static admin-debug output>/token-production-bug-lesson.jsonl
```

CI should use fixture/self-test mode only:

```bash
python tools/build_live_shadow_graph.py --self-test
python tools/validate_live_shadow_run_manifest.py --self-test
python tools/validate_live_shadow_run_manifest.py qamus/examples/live_shadow_run_manifest.sample.json
python tools/validate_public_private_boundary.py --self-test
python tools/validate_public_private_boundary.py qamus/examples/public_private_boundary.sample.json
python tools/validate_parse_key_contract.py --self-test
python tools/validate_parse_key_contract.py qamus/examples/parse_key.sample.jsonl
python tools/validate_phase1_shadow_graph.py --self-test
python tools/summarize_shadow_closure_queue.py --self-test
python tools/summarize_rich_wbw_roles.py --self-test
python tools/validate_rich_wbw_gate_cases.py --self-test
python tools/build_shadow_admin_debug_pack.py --self-test
python tools/validate_shadow_admin_debug_pack.py --self-test
python tools/validate_shadow_admin_debug_pack.py qamus/examples/shadow_admin_debug_pack.sample.json
python tools/validate_shadow_admin_route_contract.py --self-test
python tools/validate_shadow_admin_route_contract.py qamus/examples/shadow_admin_route_contract.sample.json
python tools/validate_shadow_admin_route_contract.py qamus/examples/shadow_admin_route_contract.sample.json \
  --pack qamus/examples/shadow_admin_debug_pack.sample.json
python tools/plan_phase4_closure_tranche.py --self-test
python tools/validate_phase4_closure_tranche.py --self-test
python tools/validate_phase4_closure_tranche.py qamus/examples/phase4_closure_tranche.sample.jsonl
python tools/build_phase4_two_vote_requests.py --self-test
python tools/validate_phase4_two_vote_requests.py --self-test
python tools/validate_phase4_two_vote_requests.py qamus/examples/phase4_two_vote_request.sample.jsonl
python tools/validate_phase4_two_vote_responses.py --self-test
python tools/validate_phase4_two_vote_responses.py qamus/examples/phase4_two_vote_response.sample.jsonl
python tools/reconcile_phase4_two_vote_responses.py --self-test
python tools/test_phase4_two_vote_reconciliation.py
python tools/query_shadow_admin_debug_pack.py --self-test
python tools/plan_shadow_hover_edit_intent.py --self-test
python tools/plan_shadow_repair_impact_preview.py --self-test
python tools/build_production_bug_lesson.py --self-test
python tools/validate_shadow_review_pack.py --self-test
python tools/validate_shadow_review_pack.py qamus/examples/shadow_review_pack.sample.jsonl
python tools/validate_decision_linkage.py --self-test
python tools/validate_decision_linkage.py qamus/examples/decision_linkage.sample.jsonl
python tools/validate_hover_edit_intent.py --self-test
python tools/validate_hover_edit_intent.py qamus/examples/hover_edit_intent.sample.jsonl
python tools/validate_repair_impact_preview.py --self-test
python tools/validate_repair_impact_preview.py qamus/examples/repair_impact_preview.sample.jsonl
python tools/scan_public_boundary.py --self-test
python tools/compare_wbw_artifacts.py --self-test
python tools/validate_detector_maturity.py --self-test
python tools/validate_detector_maturity.py qamus/examples/detector_maturity.sample.json
python tools/validate_detector_maturity.py qamus/examples/shadow_review_pack.sample.jsonl
python tools/validate_production_bug_lessons.py qamus/examples/production_bug_lesson.sample.jsonl
python tools/validate_production_bug_lessons.py qamus/examples/production_bug_lesson_from_intent.sample.jsonl
```

## Guardrails

- `parse:<hash>` is a grammar-family key, never primary identity.
- `quran:S:A:W` and `wbw:S:A:W` remain the exact token/hover identities.
- `parse-keys.jsonl` is a family index, not a per-token ledger. Use `seen_locs`/`token-index.jsonl` for exact
  locations and never edit or propagate from a parse key without the preview/gate lane.
- Surface-only and norm-only rows must never certify or propagate.
- Component candidates from rich WBW segments are not whole-token candidates. They may help a reviewer understand
  which pieces are visible in a composite token, but they cannot make a family propagation-safe or count as closure.
- Two-vote and source-disagreement counts are detector maturity signals; zero does not prove absence. Review-pack
  rows carry this as required `apply_policy.detector_maturity`, and the validator rejects overconfident claims.
- `propagation_safe_candidate` means "read-only impact preview is allowed next", not "auto-apply"; review-pack rows
  must preserve `scope=parse_key_family_readonly_preview` and `required_gate=auto_safe_after_preview`.
- Public hover output remains `src=qamus`, `kind=authored`, `lang=en`.
- Internal provenance may exist, but public scans must remain zero-leak.
- Mirror mismatch is report-only until a separate guarded sync is authorized.

## Phase 2.9 Closeout Snapshot

Status: Phase 2 sealed as a read-only graph/build/validation substrate. This closeout does not claim hover coverage
improvement and did not mutate live Qamus, rebuild WBW, sync the mirror, restart services, or start admin UI work.

Run source:

- source HEAD: `31a7654dde3e8a1e16ff9cb7926ec273f824f916`
- remote main/codex phase2-shadow-graph readback: `31a7654dde3e8a1e16ff9cb7926ec273f824f916`
- isolated server shadow output label: `phase2p9-20260626-180157`
- latest-HEAD tools ran from an isolated extracted archive, not from the stale server checkout.
- live inputs were consumed read-only with `--live-readonly`, `--no-live-write`, and forbidden output roots for the
  live app, live service data, mirror repo, and public webroot.

Sealed graph counts:

- entries: `2,092`
- section split: `noun 1045`, `particle 100`, `verb 947`
- token universe: `49,900`
- live word records: `49,260`
- token decisions: `9,111`
- nodes: `153,033`
- edges: `254,526`
- parse keys: `17,065`
- orphan edges: `0`
- public success leak count: `0`
- unresolved tokens: `640`

Sealed parse-family classes:

- `propagation_safe`: `1,870`
- `token_only_required`: `4,530`
- `human_review_required`: `517`
- `quarantine_collision`: `585`
- `two_vote_required`: `11`
- `unknown_parse`: `9,552`

Phase 2.8's component-candidate guardrail is active in this sealed run: rich WBW segment evidence is stored
separately from whole-token entry candidates, carries `source:rich_wbw_segment`, role, segment text, and token
location provenance, and does not weaken any lane into `auto_safe` / `propagation_safe_candidate`.

Rich WBW role taxonomy from the sealed run:

- rich parse rows: `12`
- observed roles: `13`
- strict taxonomy risks: `0`
- rich parse rows with component candidate evidence: `10`
- rich review-pack rows with component candidate evidence: `10`
- rich component candidate auto-safe/propagation violations: `0`
- named rich gate cases checked by `tools/validate_rich_wbw_gate_cases.py`: `7`
- explicitly gated roles observed: `addressee_bridge`, `adjectival_state`, `conjunction`, `object_pronoun`,
  `preposition`, `result_particle`, `resumption_particle`, `vocative_particle`
- explicitly allowlisted roles observed: `definite_article`, `imperfect_prefix`, `noun`, `verb`, `verb_stem`

Required rich gate cases were confirmed as `two_vote_required` and non-propagating in the sealed run:

- `quran:22:18:13` `وَٱلشَّمْسُ`
- `quran:22:18:14` `وَٱلْقَمَرُ`
- `quran:22:18:15` `وَٱلنُّجُومُ`
- `quran:22:18:16` `وَٱلْجِبَالُ`
- `quran:22:18:17` `وَٱلشَّجَرُ`
- `quran:2:178:22` `بِٱلْمَعْرُوفِ`
- `quran:2:21:1` `يَٰٓأَيُّهَا`

Validator evidence:

- `python tools/build_live_shadow_graph.py --self-test` -> `PASS`
- `python tools/build_live_shadow_graph.py --live-readonly --no-live-write ...` -> `PASS`
- `python tools/validate_phase1_shadow_graph.py <shadow-output>` -> `PASS`
- `python tools/validate_live_shadow_run_manifest.py --expect-live-counts <manifest>` -> `PASS`
- `python tools/summarize_shadow_closure_queue.py <shadow-output> ...` -> `PASS`
- `python tools/summarize_rich_wbw_roles.py --shadow-dir <shadow-output> --strict` -> `PASS`
- `python tools/validate_rich_wbw_gate_cases.py --shadow-dir <shadow-output> --review-pack-jsonl <review-pack>` ->
  `PASS`
- `python tools/validate_shadow_review_pack.py <review-pack>` -> `PASS`
- `python tools/compare_wbw_artifacts.py <live-wbw> <mirror-wbw>` -> report-only comparison completed

Public boundary scan:

- public sampled pages: `https://qamus.dawah.wiki/e/5935ecfb1ec5`,
  `https://qamus.dawah.wiki/e/a23a0c853dd8`, `https://qamus.dawah.wiki/e/c59a0161fac8`
- HTTP statuses: all `200`
- public leak count: `0`
- internal-only provenance count: `5` in the live WBW artifact copy
- shadow graph adapter labels: present internally, not public-exposed

Mirror mismatch classification remains unchanged and report-only:

`content-equivalent-or-near-equivalent; metadata/source-hash divergent; not safe for mutation until separately reconciled`.

## Full-Corpus Hover Dogfood Audit Lane

Status: added as a read-only audit lane after the Phase 2.9 graph/readiness seal. This lane does not reopen Phase 2.9
unless graph/tool/schema/live-input/public-boundary/mirror-affecting code or data changes. Report-only refreshes must
record both:

- `validated_code_head`: the latest code head whose graph/build/validator behavior was verified
- `report_head`: the later report/documentation head, if any

Purpose:

- audit all `49,900` Qur'an token slots and every live populated WBW hover row
- distinguish visible hover population from grammar-certified, learner-explainable rich hover readiness
- route already-populated but defective hovers into repair/blocker/lesson/skill/drill/renderer queues
- keep the audit read-only: no live Qamus mutation, no WBW rebuild, no service restart, no mirror sync, and no hover
  coverage claim

Durable tooling:

- `tools/build_full_corpus_hover_dogfood_audit.py`
- `tools/validate_full_corpus_hover_dogfood_audit.py`
- `tools/summarize_full_corpus_dogfood_queue.py`
- `tools/build_full_corpus_dogfood_review_pack.py`
- `tools/build_dogfood_production_bug_lessons.py`
- `qamus/schemas/full-corpus-hover-dogfood-audit.schema.json`
- `qamus/examples/full_corpus_hover_dogfood_audit.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_queue_summary.sample.json`
- `qamus/examples/full_corpus_dogfood_review_pack.sample.jsonl`
- `qamus/examples/dogfood_production_bug_lesson.sample.jsonl`

Row classes:

- `rich_certified`
- `populated_uncertified`
- `string_correct_but_not_rich`
- `known_defect`
- `needs_sarf_review`
- `needs_nahw_review`
- `needs_renderer_segments`
- `token_only_override`
- `pending/blocker`

Seed production-defect detectors:

- `suffix_omitted`
- `conjunction_article_omitted`
- `vocative_collapse`
- `preposition_oath_host_only_hover`
- `article_duplication`
- `finite_verb_dictionary_root_gloss_leakage`
- `nominal_pos_leakage`
- `function_preposition_flattening`
- `clitic_host_collapse`
- `surface_family_requires_token_only_override`

Every non-certified row must route to at least one of:

- repair candidate
- blocker queue row
- production-bug lesson
- sarf/nahw procedure improvement
- drill/regression fixture
- renderer/rich-hover requirement

Rows routed to `production_bug_lesson` must be convertible into
`qamus/schemas/production-bug-lesson.schema.json` by
`tools/build_dogfood_production_bug_lessons.py`. The builder preserves the exact
`quran:S:A:W`, `wbw:S:A:W`, `parse:<hash>`, decision, entry/sense, gate, and
blocker evidence from the dogfood row. It emits pending reasons rather than
inventing corrected hover prose when the audit has not certified a repair.

`tools/summarize_full_corpus_dogfood_queue.py` is the read-only triage layer
over the 49,900-row dogfood audit. It groups exact-addressed rows into review
queues (`known_defects`, `token_only_overrides`, `pending_blockers`,
`populated_uncertified`, `repair_candidates`, `production_bug_lessons`,
`sarf_nahw_procedure_improvements`, `drill_regression_fixtures`, and
`renderer_requirements`) while preserving sample `quran:S:A:W` / `wbw:S:A:W`
addresses, parse ids, gates, detectors, and blocker text. It is a
prioritization artifact only: no live apply, no WBW rebuild, no coverage claim,
and no parse-key propagation approval.

`tools/build_full_corpus_dogfood_review_pack.py` turns prioritized dogfood rows
into exact-addressed reviewer/subagent packets. Each row begins from
`quran:S:A:W` and `wbw:S:A:W`, carries the current visible hover, detectors,
routes, parse gate/family class, entry/sense linkage, sarf/nahw evidence,
blocker text, required evidence, and a read-only apply policy. It links an
available dogfood-derived production-bug lesson by exact `wbw:S:A:W` address,
but does not invent corrected hover wording and does not weaken gates.

This lane is the real dogfooding pass for populated hovers. A live row being present, repo/live parity, zero public
crawl mismatch, or a Phase 4 narrow apply packet is not sufficient evidence of sarf/nahw correctness or learner-ready
breakdown.

## Phase 4 Current-HEAD Dry-Run Blocker Refinement

Status: review-only dry run refreshed from latest pushed current HEAD
`a9ff84b1e4bd7469f71b57683a3b20bd4224d9c2`. This did not mutate live
Qamus, rebuild WBW, restart services, sync the mirror, apply hover decisions,
or claim closure progress.

Dry-run inputs and outputs:

- sealed shadow graph:
  `out/live-shadow-runs/20260626-110034/shadow-output-phase2p9-sealed`
- dry-run output:
  `out/phase4-dryrun-20260626-180341-a9ff84b1e4bd`
- two-vote request rows: `11`
- validated source-only response rows replayed against the fresh request packet:
  `22`
- reconciled certified rows: `10`
- reconciled unresolved rows: `1`
- post-adjudication certified rows: `11`
- post-adjudication unresolved rows: `0`
- post-adjudication hover decision plan rows: `11`
- post-adjudication draft token-decision ledger rows: `11`
- post-adjudication owner authorization request rows: `1`
- post-adjudication owner authorization request id:
  `phase4-owner-authorization-request:a322533d81c96154`
- source-only review/apply artifact leak-pattern matches: `0`
- `apply_allowed=false`, `live_mutation_allowed=false`,
  `closure_claim_allowed=false`

The current-HEAD queue still preserves the Phase 2.8 component-candidate
boundary:

- all dry-run request rows are `lane=two_vote_required`
- `auto_safe_rows=0`
- `component_candidate_rows=11`
- component candidates remain non-certifying and cannot weaken the gate

Validation evidence:

- `python tools/summarize_shadow_closure_queue.py <sealed-shadow> --review-lane two_vote_required` -> `PASS`
- `python tools/validate_shadow_review_pack.py <two-vote-review-pack.jsonl>` -> `PASS`
- `python tools/plan_phase4_closure_tranche.py <two-vote-review-pack.jsonl> --lane two_vote_required` -> `PASS`
- `python tools/validate_phase4_closure_tranche.py <phase4-two-vote-dryrun-tranche.jsonl>` -> `PASS`
- `python tools/build_phase4_two_vote_requests.py <phase4-two-vote-dryrun-tranche.jsonl>` -> `PASS`
- `python tools/validate_phase4_two_vote_requests.py <phase4-two-vote-requests.jsonl>` -> `PASS`
- `python tools/validate_phase4_two_vote_responses.py <combined-responses.jsonl> --requests <phase4-two-vote-requests.jsonl>` -> `PASS`
- `python tools/reconcile_phase4_two_vote_responses.py --requests <phase4-two-vote-requests.jsonl> --responses <combined-responses.jsonl> ...` -> `PASS`
- `python tools/build_phase4_gloss_adjudication_requests.py <unresolved.jsonl>` -> `PASS`
- `python tools/validate_phase4_gloss_adjudication_requests.py <gloss-adjudication-requests.jsonl>` -> `PASS`
- `python tools/build_phase4_hover_decision_plan.py <certified.jsonl>` -> `PASS`
- `python tools/validate_phase4_hover_decision_plan.py <hover-decision-plan.jsonl>` -> `PASS`
- `python tools/build_phase4_apply_readiness_manifest.py <hover-decision-plan.jsonl>` -> `PASS`
- `python tools/validate_phase4_apply_readiness_manifest.py <apply-readiness-manifest.json> --plan-jsonl <hover-decision-plan.jsonl>` -> `PASS`
- `python tools/build_phase4_draft_token_decision_ledger.py <hover-decision-plan.jsonl>` -> `PASS`
- `python tools/validate_phase4_draft_token_decision_ledger.py <draft-token-decision-ledger.jsonl> --plan-jsonl <hover-decision-plan.jsonl>` -> `PASS`
- `python tools/validate_phase4_gloss_adjudication_responses.py <gloss-adjudication-responses.jsonl> --requests <gloss-adjudication-requests.jsonl>` -> `PASS`
- `python tools/reconcile_phase4_gloss_adjudication_responses.py --requests <gloss-adjudication-requests.jsonl> --responses <gloss-adjudication-responses.jsonl> ...` -> `PASS`
- `python tools/build_phase4_hover_decision_plan.py <certified-plus-adjudicated.jsonl>` -> `PASS`
- `python tools/validate_phase4_hover_decision_plan.py <post-adjudication-hover-decision-plan.jsonl>` -> `PASS`
- `python tools/build_phase4_apply_readiness_manifest.py <post-adjudication-hover-decision-plan.jsonl>` -> `PASS`
- `python tools/validate_phase4_apply_readiness_manifest.py <post-adjudication-apply-readiness-manifest.json> --plan-jsonl <post-adjudication-hover-decision-plan.jsonl>` -> `PASS`
- `python tools/build_phase4_draft_token_decision_ledger.py <post-adjudication-hover-decision-plan.jsonl>` -> `PASS`
- `python tools/validate_phase4_draft_token_decision_ledger.py <post-adjudication-draft-token-decision-ledger.jsonl> --plan-jsonl <post-adjudication-hover-decision-plan.jsonl>` -> `PASS`
- `python tools/build_phase4_owner_authorization_request.py --manifest-json <post-adjudication-apply-readiness-manifest.json> --draft-ledger-jsonl <post-adjudication-draft-token-decision-ledger.jsonl>` -> `PASS`
- `python tools/validate_phase4_owner_authorization_request.py <owner-authorization-request.json> --manifest-json <post-adjudication-apply-readiness-manifest.json> --draft-ledger-jsonl <post-adjudication-draft-token-decision-ledger.jsonl>` -> `PASS`

Residual blocker precision was hardened in the reconciler. When both sarf and
nahw approve the same token with the same reason key and same scope, but differ
only on public gloss wording, the unresolved row is now
`gloss_wording_disagreement` instead of generic `vote_disagreement`.

Current residual example:

- token: `quran:2:178:22` / `wbw:2:178:22`
- surface: `بِٱلْمَعْرُوفِ`
- parse: `parse:e5e4e1aeb56a7fdd636257b0`
- internal grammar evidence: `بـ` governs the genitive host; the host is a
  derived/genitive nominal from `ع ر ف`
- shared reason key: `preposition-governed-nominal-manner`
- sarf vote gloss: `in a recognized manner`
- nahw vote gloss: `with recognized fairness`
- unresolved reason: `gloss_wording_disagreement`

This is the intended fail-closed outcome: the token is promising and
source-addressed, but the public hover wording still needs resolution before any
append-only decision or live apply path can be considered.

A review-only gloss adjudication bridge now converts that exact unresolved row
into an owner/scholar wording request without weakening any gate:

- schema: `qamus/schemas/phase4-gloss-adjudication-request.schema.json`
- builder: `tools/build_phase4_gloss_adjudication_requests.py`
- validator: `tools/validate_phase4_gloss_adjudication_requests.py`
- sample: `qamus/examples/phase4_gloss_adjudication_request.sample.jsonl`
- generated ignored dry-run packet:
  `out/phase4-dryrun-20260626-180341-a9ff84b1e4bd/gloss-adjudication-requests.jsonl`
- generated rows: `1`
- candidate glosses: `in a recognized manner`; `with recognized fairness`
- allowed next step: `owner_or_scholar_gloss_adjudication_only`
- `apply_allowed=false`, `live_mutation_allowed=false`,
  `closure_claim_allowed=false`

The adjudication packet is still not an apply artifact. It is the next
source-addressed review object needed to choose or author one public Qamus
wording while preserving the sarf/nahw evidence boundary.

The latest review-only adjudication replay selected the conservative candidate
`in a recognized manner` for `بِٱلْمَعْرُوفِ`, preserving the visible bāʾ
relation and the governed nominal without over-specifying context. Internal
iʿrāb evidence confirmed the preposition plus genitive-host structure; no
external evidence label or source text is present in the public-hover-shaped
rows.

Generated ignored adjudication replay packet:

- output:
  `out/phase4-dryrun-20260626-181705-0c2a4ba22e94-adjudicated`
- response rows: `1`
- gloss-adjudication certified rows: `1`
- gloss-adjudication unresolved rows: `0`
- combined certified rows: `11`
- hover decision plan rows: `11`
- draft token-decision ledger rows: `11`
- owner authorization request rows: `1`
- owner authorization request id:
  `phase4-owner-authorization-request:a322533d81c96154`
- source-only review/apply artifact leak-pattern matches: `0`
- `apply_allowed=false`, `live_mutation_allowed=false`,
  `closure_claim_allowed=false`

A matching review-only response/reconciliation bridge now validates an
authorized wording selection and converts it to a `certified_not_applied`
artifact, still without live mutation or closure claims:

- schema: `qamus/schemas/phase4-gloss-adjudication-response.schema.json`
- validator: `tools/validate_phase4_gloss_adjudication_responses.py`
- reconciler: `tools/reconcile_phase4_gloss_adjudication_responses.py`
- sample: `qamus/examples/phase4_gloss_adjudication_response.sample.jsonl`
- test: `tools/test_phase4_gloss_adjudication_response_reconciliation.py`
- accepted source: the exact `phase4-gloss-adjudication:*` request id and the
  same `quran:S:A:W` / `wbw:S:A:W` / `parse:<hash>` identity
- output status: `certified_not_applied`
- `apply_allowed=false`, `live_mutation_allowed=false`,
  `closure_claim_allowed=false`

The reconciled response chooses or authors one source-clean public Qamus
wording for the exact blocker. It does not append a live token decision, rebuild
WBW, sync the mirror, or claim hover coverage.

A follow-up review-only hover decision plan now converts certified-not-applied
rows into exact token-addressed previews for a future apply lane:

- schema: `qamus/schemas/phase4-hover-decision-plan.schema.json`
- builder: `tools/build_phase4_hover_decision_plan.py`
- validator: `tools/validate_phase4_hover_decision_plan.py`
- sample: `qamus/examples/phase4_hover_decision_plan.sample.jsonl`
- test: `tools/test_phase4_hover_decision_plan.py`
- accepted sources: `phase4_two_vote_reconciled` and
  `phase4_gloss_adjudication_reconciled` rows with `status=certified_not_applied`
- output status: `planned_not_applied`

Each plan row is expanded to one exact `quran:S:A:W` / `wbw:S:A:W` pair and
includes a `token_decision_preview` shaped like a future Qamus token decision
(`loc`, `gloss`, `src=qamus`, `kind=authored`, `lang=en`). It remains a
preview, not a token-decision ledger row. The apply policy still requires a
separate append-only ledger, backup, rebuild, validation, health check, and
targeted public readback before any live apply can exist.

A second source-only apply-readiness manifest now hashes that hover decision
plan and records the future apply gates without authorizing them:

- schema: `qamus/schemas/phase4-apply-readiness-manifest.schema.json`
- builder: `tools/build_phase4_apply_readiness_manifest.py`
- validator: `tools/validate_phase4_apply_readiness_manifest.py`
- sample: `qamus/examples/phase4_apply_readiness_manifest.sample.json`
- test: `tools/test_phase4_apply_readiness_manifest.py`
- output status: `pre_apply_not_authorized`

The manifest is a review artifact only. It records symbolic truth owners,
required future gates, rollback requirements, source-clean sample decisions,
and the source plan hash. It does not permit live mutation, WBW rebuild,
service restart, mirror sync, parse-key identity, raw-surface identity, or
component-candidate certification.

A companion source-only draft token-decision ledger can now be generated from
the same hover decision plan for owner review:

- schema: `qamus/schemas/phase4-draft-token-decision-ledger.schema.json`
- builder: `tools/build_phase4_draft_token_decision_ledger.py`
- validator: `tools/validate_phase4_draft_token_decision_ledger.py`
- sample: `qamus/examples/phase4_draft_token_decision_ledger.sample.jsonl`
- test: `tools/test_phase4_draft_token_decision_ledger.py`
- output status: `draft_not_applied`

This draft ledger is not the live append-only token decision ledger. It copies
only the source-clean public token decision shape and plan lineage into a
review artifact, keeping `apply_allowed=false`, `live_mutation_allowed=false`,
and all future backup/rebuild/validation/health/readback gates required.

A final source-only owner authorization request can now bind the exact
apply-readiness manifest hash to the exact draft token-decision ledger hash for
review, without itself granting permission:

- schema: `qamus/schemas/phase4-owner-authorization-request.schema.json`
- builder: `tools/build_phase4_owner_authorization_request.py`
- validator: `tools/validate_phase4_owner_authorization_request.py`
- sample: `qamus/examples/phase4_owner_authorization_request.sample.json`
- test: `tools/test_phase4_owner_authorization_request.py`
- output status: `owner_review_required_not_authorized`

The request is intentionally inert. It requires an owner to authorize the exact
request id and artifact hashes before any future live apply. It rejects public
provenance leakage and keeps live mutation, WBW rebuild, service restart,
mirror sync, and closure claims disabled.

## Phase 3 Latest Read-Only Admin/Debug Refresh

Status: latest read-only admin/debug scaffold smoke completed from pushed `main`
HEAD `40a98fa32b2d3036a1ababe1157771c487bd1fda`. This remains scaffolding only:
no live Qamus mutation, no WBW rebuild, no service restart, no mirror sync, and
no hover coverage claim.

Server-side latest checkout and input/output paths:

- tools clone: `/srv/dawah-ops/hermes-workspace/qamus-shadow-graph/phase3-tools-40a98fa-20260626-195928`
- input shadow graph: `/srv/dawah-ops/hermes-workspace/qamus-shadow-graph/phase2p9-fcffc79-20260626-194628`
- static admin/debug pack: `/tmp/qamus-phase3-admin-debug-40a98fa-20260626-195928/admin-debug-pack.json`

Output-root guard evidence:

- first attempted output under `/srv/dawah-ops/hermes-workspace/qamus-shadow-graph/...` was rejected:
  `refusing likely live/runtime output path`
- final output used `/tmp/qamus-phase3-admin-debug-40a98fa-20260626-195928`, leaving live/app/service paths untouched

Admin/debug pack counts:

- token rows: `49,900`
- hover rows: `49,900`
- parse rows: `17,065`
- decision rows: `9,106`
- entry rows: `2,092`
- blocker classes: `9`
- sample tokens: `6`
- sample entries: `2`

Validated sampled traces:

- `quran:33:63:1` suffix-pronoun/token-only exemplar
- `quran:22:18:17` conjunction/article/noun rich-WBW exemplar
- `quran:2:21:1` vocative/addressee bridge exemplar
- `quran:4:28:8` adjectival-state exemplar
- `quran:2:178:22` preposition/governed nominal exemplar
- `parse:1bbe8fa09823c3c0d064dc83` safe parse-family preview exemplar
- `qamus:v:430015446b77` entry backlink / entry-sense preview exemplar

Read-only edit-intent and repair-impact smoke:

- token-only intent target: `wbw:33:63:1`, repair preview affected tokens/hovers/parse keys: `1 / 1 / 1`
- parse-family intent target:
  `qamus:v:430015446b77#field=parse_family[parse:1bbe8fa09823c3c0d064dc83].hover_pattern`,
  repair preview affected tokens/hovers/parse keys: `236 / 236 / 1`
- entry/sense intent target: `qamus:v:430015446b77#sense=1`,
  repair preview affected tokens/hovers/parse keys: `736 / 736 / 57`
- every preview row has `live_mutation_allowed=false`

Production bug lesson bridge smoke:

- bug class: `verb_object_suffix_omitted`
- target: `wbw:33:63:1`
- visible bad hover: `to ask, question`
- corrected hover / lesson target: `ask you`
- learner level: `beginner`

Latest Phase 3 validator evidence:

- `python3 tools/build_shadow_admin_debug_pack.py --shadow-dir <phase2p9-shadow> --out-dir /tmp/...` -> `PASS`
- `python3 tools/validate_shadow_admin_debug_pack.py <pack>` -> `PASS`
- `python3 tools/validate_shadow_admin_route_contract.py qamus/examples/shadow_admin_route_contract.sample.json --pack <pack>` -> `PASS`
- `python3 tools/query_shadow_admin_debug_pack.py --pack <pack> --token quran:33:63:1` -> `PASS`
- `python3 tools/query_shadow_admin_debug_pack.py --pack <pack> --token quran:22:18:17` -> `PASS`
- `python3 tools/query_shadow_admin_debug_pack.py --pack <pack> --token quran:2:21:1` -> `PASS`
- `python3 tools/query_shadow_admin_debug_pack.py --pack <pack> --parse parse:1bbe8fa09823c3c0d064dc83` -> `PASS`
- `python3 tools/query_shadow_admin_debug_pack.py --pack <pack> --entry qamus:v:430015446b77` -> `PASS`
- `python3 tools/validate_hover_edit_intent.py <all-edit-intents.jsonl>` -> `PASS`
- `python3 tools/validate_repair_impact_preview.py <repair-impact-previews.jsonl>` -> `PASS`
- `python3 tools/validate_production_bug_lessons.py <production-bug-lesson.jsonl>` -> `PASS`

## Phase 3.25 / 3.5 Latest Grammar Gate Refresh

Status: latest repo-side GrammarProblems regression-mining and grouped nahw
issue validation rerun completed from pushed HEAD
`af60907bc6e7dfebf2725b6ca518a54c2825c19f`. This remains a pre-authoring
gate only; it does not perform corpus-facing grammar authoring or live Qamus
mutation.

Latest Phase 3.25 mining evidence:

- command: `python tools\build_grammar_regression_mining.py`
- regenerated rows: `88`
- classification counts:
  - `already_covered_issue_1`: `45`
  - `already_covered_issue_2`: `12`
  - `already_covered_issue_3`: `18`
  - `correct_positive_regression`: `13`
- no `new_root_cause_cluster` rows were present in this rerun

Latest Phase 3.5 grouped issue validation:

- command:
  `python tools\validate_grammar_issue_clusters.py nahw\rules\grammar-problems-issue-clusters.json --mining nahw\evals\grammar-problems-phase3p25-mining.jsonl`
- mapped clusters:
  - `issue_1_wrong_reasoning`: `45`
  - `issue_2_function_attachment`: `12`
  - `issue_3_morphosyntax_preservation`: `18`
  - `positive_regression_control`: `13`
- validation result: `PASS`

Latest GrammarProblems executable eval:

- command: `python tools\run_grammar_evals.py`
- cases: `88`
- errors: `0`
- levels: `ajurrumiyyah=16`, `qatr_al_nada=39`, `awdah_al_masalik=33`
- gates: `two_vote_required=75`, `auto_safe=13`
- wrong-reasoning traps exercised: `8`
- result: `PASS`

## Phase 3 Read-Only Admin/Debug Scaffold

Status: started as repo-only tooling. Phase 3 scaffolding is deliberately static and local before any app route exists.
The scaffold consumes durable Phase 2 shadow outputs and produces an inspector pack that a future app/admin route can
mirror after separate app-repo review.

Fresh Phase 3 smoke on the Phase 2.9 sealed graph:

- source HEAD for refresh: `922af2ec334fa6037a32deca9e231ac8a1c65633`
- input shadow graph: sealed Phase 2.9 shadow outputs copied into a local ignored `out/` review directory
- static admin/debug pack: local ignored `out/phase3-admin-debug-20260626-142444-922af2ec334f/admin-debug-pack.json`
- pack counts: `49,900` token rows, `49,900` hover rows, `17,065` parse rows, `9,106` decision rows,
  `2,092` entry rows, `9` blocker classes, `6` requested token samples, `2` entry backlink samples
- validated pack: `python tools/validate_shadow_admin_debug_pack.py <pack>` -> `PASS`
- exercised gated reverse traces: `quran:33:63:1` suffix pronoun (`two_vote_required`),
  `quran:22:18:17` conjunction/article/noun (`two_vote_required`), `quran:2:21:1` vocative bridge
  (`two_vote_required`), `quran:4:28:8` adjectival-state row (`two_vote_required`), and
  `quran:2:178:22` preposition row (`two_vote_required`)
- exercised safe parse-family trace: `quran:2:30:2` / `parse:1bbe8fa09823c3c0d064dc83`, surface `قَالَ`,
  family size `236`, gate `auto_safe`, propagation allowed for preview only
- exercised future edit scopes without mutation:
  - token-only: `wbw:33:63:1`, affected tokens `1`
  - parse-family: `parse:1bbe8fa09823c3c0d064dc83`, affected tokens `236`, gate
    `auto_safe_after_preview`, sample list `12`, `sample_tokens_are_complete=false`
  - entry/sense: `qamus:n:6751c0e4d0fd#sense=1`, affected tokens `6`, gate `two_vote_required`
- validated edit intents and repair previews:
  `python tools/validate_hover_edit_intent.py <all-edit-intents.jsonl>` -> `PASS`;
  `python tools/validate_repair_impact_preview.py <repair-impact-previews.jsonl>` -> `PASS`
- repair preview rows now carry explicit `affected_token_count`, `affected_hover_count`,
  `affected_parse_key_count`, and `sample_tokens_are_complete` fields so a compact sample list cannot be mistaken for
  full blast-radius coverage.
- entry/sense previews now require a complete sample-token inspector chain. `tools/build_shadow_admin_debug_pack.py`
  adds hover inspectors for entry backlink sample tokens, and `tools/validate_shadow_admin_debug_pack.py` rejects any
  entry sample token or hover slot that lacks a matching inspector. This prevents future admin/edit scaffolding from
  showing an entry blast-radius sample that cannot be followed back through
  `wbw:S:A:W -> quran:S:A:W -> parse:<hash>`.
- production bug lesson smoke:
  `python tools/validate_production_bug_lessons.py <production-bug-lesson.jsonl>` -> `PASS`
  for `verb_object_suffix_omitted` on `quran:33:63:1` / `wbw:33:63:1`.

Fresh Phase 3.25 / 3.5 grammar-regression gate:

- regenerated `nahw/evals/grammar-problems-phase3p25-mining.jsonl` and `.md` from
  `nahw/evals/grammar-problems-derived-eval.jsonl`
- rows: `88`
- classifications: `already_covered_issue_1=45`, `already_covered_issue_2=12`,
  `already_covered_issue_3=18`, `correct_positive_regression=13`
- validator: `python tools/validate_grammar_regression_mining.py nahw/evals/grammar-problems-phase3p25-mining.jsonl`
  -> `PASS`
- grouped issue coverage:
  `python tools/validate_grammar_issue_clusters.py nahw/rules/grammar-problems-issue-clusters.json --mining nahw/evals/grammar-problems-phase3p25-mining.jsonl`
  -> `PASS`

Phase 4 dry-run readiness smoke:

- status: review-only dry run completed from the complete sealed Phase 2.9 shadow graph; no live Qamus mutation, no
  WBW rebuild, no service restart, no mirror sync, and no hover coverage claim.
- source HEAD for dry run: `84505746635e150739e446f2cab9914369c2873d`
- complete shadow input: ignored local copy under
  `out/live-shadow-runs/20260626-110034/shadow-output-phase2p9-sealed`
- dry-run output: ignored local directory `out/phase4-dryrun-20260626-143455-84505746635e`
- initial dry-run attempt against the compact Phase 3 admin input copy was rejected because that copy lacks
  `phase1-current-truth.json`; Phase 4 queue tooling must consume a complete sealed shadow graph, not an admin-pack
  slice.
- closure queue summary: `two_vote_required=11`, `human_review_required=517`, `propagation_safe_candidate=1870`,
  `quarantine_collision=585`, `token_only_required=4530`, `unknown_parse=9552`
- lane token counts: `two_vote_required=11`, `human_review_required=640`, `propagation_safe_candidate=18038`,
  `quarantine_collision=5580`, `token_only_required=4530`, `unknown_parse=21101`
- detector maturity remains explicit: `two_vote_required=partial_shadow_gate`,
  `source_disagreement=reserved_detector_gap`, `zero_count_policy=zero_does_not_prove_absence`
- review pack: `11` rows, all `lane=two_vote_required`, all `required_gate=two_vote_required`
- dry-run tranche: `11` rows, all `lane=two_vote_required`, all `required_gate=two_vote_required`, all `11` rows
  preserve rich component evidence separately from whole-token candidates
- two-vote requests: `11` rows, all `lane=two_vote_required`, all `required_gate=two_vote_required`, all `11` rows
  preserve component candidate evidence as non-certifying review evidence; regenerated agreement-key smoke kept
  `auto_safe_rows=0` and produced these request coordination keys:
  `conj-definite-noun-coordinated-list=5`, `accusative-adjectival-state=1`,
  `preposition-governed-nominal-manner=1`, `result-particle-active-verb-object-suffix=1`,
  `resumption-passive-verb-clause=1`, `verb-object-suffix-explicit-subject=1`,
  `vocative-particle-addressee-bridge=1`
- sample request identity:
  `parse:15651e48a4731deea206356a` / `quran:22:18:14` / `wbw:22:18:14` / `وَٱلْقَمَرُ`
- validators:
  - `python tools/validate_shadow_review_pack.py <two-vote-review-pack.jsonl>` -> `PASS`
  - `python tools/validate_phase4_closure_tranche.py <phase4-two-vote-dryrun-tranche.jsonl>` -> `PASS`
  - `python tools/validate_phase4_two_vote_requests.py <phase4-two-vote-requests.jsonl>` -> `PASS`

The current scaffold covers:

- hover inspector: `wbw:S:A:W -> quran:S:A:W -> parse:<hash> -> decision/gloss/gate/blocker`
- entry backlinks: entry candidates/components -> dependent token locations, hover slots, parse keys, blockers
- parse-family view: family size, lanes, gates, propagation status, candidate/component evidence, sibling samples
- blocker queue: blocker classes grouped with sample tokens, parse counts, and POS counts
- repair preview stub: read-only affected counts and `live_mutation_allowed=false`

The scaffold intentionally does not:

- mutate live Qamus
- rebuild WBW
- start or restart services
- expose internal provenance as public payload
- perform hover authoring or closure
- use raw Arabic surface text as identity

## Phase 2.8 / 2.9 Latest Closeout Refresh

Status: latest live-readonly closeout rerun completed from pushed `main` and
`codex/phase2-shadow-graph` HEAD `4a66210c315878f59a6cb372814729ccc184c1ab`.
This was a graph/readiness run only: no live Qamus mutation, no WBW rebuild, no
service restart, no mirror sync, and no hover coverage claim.

Server-side latest checkout and shadow paths:

- tools clone label: `phase2p9-tools-4a66210-20260626-225033`
- shadow output label: `phase2p9-4a66210-20260626-225033`
- local repo status before closeout refresh: clean detached HEAD at `4a66210c315878f59a6cb372814729ccc184c1ab`
- remote readback before closeout refresh: both `main` and `codex/phase2-shadow-graph` pointed at
  `4a66210c315878f59a6cb372814729ccc184c1ab`

Single-run counts from the latest live-readonly shadow build:

- entries: `2,092` (`noun=1045`, `verb=947`, `particle=100`)
- token universe: `49,900`
- live word records: `49,260`
- unresolved tokens: `640`
- token decisions: `9,111`
- parse keys: `17,065`
- nodes: `153,033`
- edges: `254,526`
- decision index rows: `9,106`
- backlink top-level keys: `143,734`
- orphan edges: `0`
- public success leak count: `0`

Latest parse-family classes:

- `propagation_safe`: `1,870`
- `token_only_required`: `4,530`
- `human_review_required`: `517`
- `quarantine_collision`: `585`
- `unknown_parse`: `9,552`
- `two_vote_required`: `11`

Latest lane token counts:

- `propagation_safe_candidate`: `18,038`
- `token_only_required`: `4,530`
- `human_review_required`: `640`
- `quarantine_collision`: `5,580`
- `unknown_parse`: `21,101`
- `two_vote_required`: `11`

Detector maturity remains explicit:

- `two_vote_required`: `partial_shadow_gate`
- `source_disagreement`: `reserved_detector_gap`
- `zero_count_policy`: `zero_does_not_prove_absence`

Rich WBW role taxonomy from the latest run:

- rich parse rows: `12`
- observed roles: `13`
- strict taxonomy risks: `0`
- explicitly gated roles: `addressee_bridge=1`, `adjectival_state=1`, `conjunction=5`,
  `object_pronoun=2`, `preposition=1`, `result_particle=1`, `resumption_particle=1`,
  `vocative_particle=1`
- explicitly allowlisted roles: `definite_article=7`, `imperfect_prefix=1`, `noun=7`,
  `verb=2`, `verb_stem=1`
- no unknown rich role was observed
- no explicitly gated role appeared in an `auto_safe` gate or `propagation_safe` lane
- rich WBW segment evidence remains component-only: component candidates are stored
  separately from whole-token `candidate_entries`, preserve `source=rich_wbw_segment`
  plus role/segment/token provenance, and do not contribute to `auto_safe`, source
  agreement, propagation safety, closure coverage, or hover coverage

Required rich gate cases were re-confirmed as `two_vote_required` and non-propagating:

- `quran:22:18:13` `وَٱلشَّمْسُ`
- `quran:22:18:14` `وَٱلْقَمَرُ`
- `quran:22:18:15` `وَٱلنُّجُومُ`
- `quran:22:18:16` `وَٱلْجِبَالُ`
- `quran:22:18:17` `وَٱلشَّجَرُ`
- `quran:2:178:22` `بِٱلْمَعْرُوفِ`
- `quran:2:21:1` `يَٰٓأَيُّهَا`

Latest validator evidence:

- `python3 tools/build_live_shadow_graph.py --live-readonly --no-live-write ...` -> `PASS`
- `python3 tools/validate_phase1_shadow_graph.py <shadow-output>` -> `PASS`
- `python3 tools/validate_live_shadow_run_manifest.py --expect-live-counts <shadow-output>/phase2-run-manifest.json` -> `PASS`
- `python3 tools/summarize_shadow_closure_queue.py <shadow-output> ...` -> `PASS`
- `python3 tools/validate_shadow_review_pack.py <review-pack>` -> `PASS`
- `python3 tools/summarize_rich_wbw_roles.py --shadow-dir <shadow-output> --strict` -> `PASS`
- `python3 tools/validate_rich_wbw_gate_cases.py --shadow-dir <shadow-output> --review-pack-jsonl <review-pack>` -> `PASS`
- `python3 tools/scan_public_boundary.py --public https://qamus.dawah.wiki/e/5935ecfb1ec5 --internal <live-wbw> --shadow-dir <shadow-output>` -> `PASS`, public leak count `0`
- `python3 tools/compare_wbw_artifacts.py <live-wbw> <mirror-wbw>` -> report-only comparison completed

Public/private boundary from the latest scan:

- public sampled page: `https://qamus.dawah.wiki/e/5935ecfb1ec5`
- HTTP status: `200`
- public leak count: `0`
- live WBW internal-only provenance labels remain present internally:
  `Tanzil`, `informed_by`, `qac`, `tafsir`, `mcp`
- shadow graph contains internal adapter labels in shadow artifacts only; no public exposure was detected

Mirror mismatch classification remains unchanged and report-only:

`content-equivalent-or-near-equivalent; metadata/source-hash divergent; not safe for mutation until separately reconciled`.
