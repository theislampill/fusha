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
  identity, and a source-clean public/private boundary. This prevents a future UI scaffold from quietly becoming an
  edit/apply endpoint.
- `tools/plan_shadow_hover_edit_intent.py`: read-only CLI for planning future hover-edit intents from a validated
  Phase 3 admin/debug pack. It emits validator-clean JSONL rows for token-only, parse-family, or entry/sense edit
  intent review, preserves exact `wbw:S:A:W -> quran:S:A:W -> parse:<hash> -> qamus:<id>#sense=<n>` identity, and
  refuses parse-family intents when the pack marks that family non-propagation-safe. It does not write live Qamus
  data, rebuild WBW, mutate entries, or create repair ledgers.
- `tools/plan_shadow_repair_impact_preview.py`: read-only CLI that turns validated hover-edit intent rows into
  validated repair-impact-preview rows. It makes the future apply target explicit as a `qamus:<id>#field=<path>`
  address, carries affected token/hover/parse samples forward, adds a rollback strategy, and keeps
  `live_mutation_allowed=false`. It is still a preview artifact only; no decision ledger, entry JSON, WBW artifact, or
  app route is changed. Token-only previews that have no resolved entry/sense use the deterministic overlay target
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
  surfaces. It deliberately contains no app implementation and no live path.

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
python tools/scan_public_boundary.py --public <public entry URL> --shadow-dir <isolated shadow output>
python tools/compare_wbw_artifacts.py <live wbw lookup> <mirror wbw lookup>
python tools/validate_detector_maturity.py <review pack jsonl or detector maturity json>
python tools/build_shadow_admin_debug_pack.py --shadow-dir <isolated shadow output> \
  --out-dir <isolated static admin-debug output> \
  --sample-token quran:33:63:1 \
  --sample-token quran:22:18:17 \
  --sample-token quran:2:21:1
python tools/validate_shadow_admin_debug_pack.py <isolated static admin-debug output>/admin-debug-pack.json
python tools/validate_shadow_admin_route_contract.py qamus/examples/shadow_admin_route_contract.sample.json
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
python tools/build_shadow_admin_debug_pack.py --self-test
python tools/validate_shadow_admin_debug_pack.py --self-test
python tools/validate_shadow_admin_debug_pack.py qamus/examples/shadow_admin_debug_pack.sample.json
python tools/validate_shadow_admin_route_contract.py --self-test
python tools/validate_shadow_admin_route_contract.py qamus/examples/shadow_admin_route_contract.sample.json
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

- Fresh checkout HEAD before closeout: `5ed6ffeb50758c71ee3b419e6be743e65bf8d9d5`.
- Local read-only snapshot path: `out/live-shadow-runs/20260626-110034`.
- Sealed shadow graph output: `out/live-shadow-runs/20260626-110034/shadow-output-phase2p9-sealed`.
- Live inputs were copied/streamed to the local snapshot first; the builder consumed local read-only copies.

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

The previous `missing_entry=1` rich-row gap was an Andon: `4:28:8` carried role `adjectival_state` with an
`auto_safe` gate. Phase 2.9 patches the builder so `adjectival_state` / `circumstantial_state` are grammar-sensitive
triggers and cannot remain auto-safe. The sealed run therefore moves that row into `two_vote_required`.

Rich WBW role taxonomy from the sealed run:

- rich parse rows: `12`
- observed roles: `13`
- strict taxonomy risks: `0`
- rich parse rows with component candidate evidence: `10`
- rich review-pack rows with component candidate evidence: `10`
- rich component candidate auto-safe/propagation violations: `0`
- explicitly gated roles observed: `addressee_bridge`, `adjectival_state`, `conjunction`, `object_pronoun`,
  `preposition`, `result_particle`, `resumption_particle`, `vocative_particle`
- explicitly allowlisted roles observed: `definite_article`, `imperfect_prefix`, `noun`, `verb`, `verb_stem`

Phase 2.8 component-candidate guardrail is active in this sealed run: rich WBW segment evidence is stored separately
from whole-token entry candidates, carries `source:rich_wbw_segment`, role, segment text, and token location provenance,
and does not weaken any lane into `auto_safe` / `propagation_safe_candidate`.

Required rich gate cases were confirmed as `two_vote_required` and non-propagating in the sealed run:

- `quran:22:18:13` `وَٱلشَّمْسُ`
- `quran:22:18:14` `وَٱلْقَمَرُ`
- `quran:22:18:15` `وَٱلنُّجُومُ`
- `quran:22:18:16` `وَٱلْجِبَالُ`
- `quran:22:18:17` `وَٱلشَّجَرُ`
- `quran:2:178:22` `بِٱلْمَعْرُوفِ`
- `quran:2:21:1` `يَٰٓأَيُّهَا`

Public boundary scan:

- public sampled pages: `https://qamus.dawah.wiki/e/5935ecfb1ec5`,
  `https://qamus.dawah.wiki/e/a23a0c853dd8`, `https://qamus.dawah.wiki/e/c59a0161fac8`
- HTTP statuses: all `200`
- public leak count: `0`
- internal-only provenance count: `5` in the live WBW artifact copy
- shadow graph adapter labels: present internally, not public-exposed

Mirror mismatch classification remains unchanged and report-only:

`content-equivalent-or-near-equivalent; metadata/source-hash divergent; not safe for mutation until separately reconciled`.

## Phase 3 Read-Only Admin/Debug Scaffold

Status: started as repo-only tooling. Phase 3 scaffolding is deliberately static and local before any app route exists.
The scaffold consumes durable Phase 2 shadow outputs and produces an inspector pack that a future app/admin route can
mirror after separate app-repo review.

Fresh Phase 3 smoke on the Phase 2.9 sealed graph:

- input shadow graph: `out/live-shadow-runs/20260626-110034/shadow-output-phase2p9-sealed`
- static admin/debug pack: `out/live-shadow-runs/20260626-110034/admin-debug-pack-phase3/admin-debug-pack.json`
- pack counts: `49,900` token rows, `49,900` hover rows, `17,065` parse rows, `9,106` decision rows,
  `2,092` entry rows, `9` blocker classes
- validated pack: `python tools/validate_shadow_admin_debug_pack.py <pack>` -> `PASS`
- exercised reverse traces: `quran:33:63:1`, `quran:22:18:17`, `quran:2:21:1`, `quran:3:66:7`
- exercised future edit scopes without mutation:
  - token-only: `wbw:33:63:1`, affected tokens `1`
  - parse-family: `parse:004b6763a44604bd07253686`, affected tokens `6`, gate `auto_safe_after_preview`
  - entry/sense: `qamus:p:967098527388#sense=1`, affected tokens `1`, gate `two_vote_required`
- validated edit intents and repair previews:
  `python tools/validate_hover_edit_intent.py <all-edit-intents.jsonl>` -> `PASS`;
  `python tools/validate_repair_impact_preview.py <repair-impact-previews.jsonl>` -> `PASS`

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
