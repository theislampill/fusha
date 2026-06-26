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
  propagation-safe.
- `tools/validate_phase1_shadow_graph.py`: validates required Phase 1/2 shadow artifacts, nonzero rows, exact
  counts, token/hover/parse linkage, no orphan count, no surface-only auto-safe parse, and public-boundary markers.
- `tools/scan_public_boundary.py`: classifies public readback leaks separately from internal-only provenance.
- `tools/compare_wbw_artifacts.py`: compares WBW artifacts without reconciling or copying either side.
- `tools/summarize_shadow_closure_queue.py`: consumes an already-built shadow graph and emits closure-lane,
  blocker, family-size, sample-token summaries, and optional source-addressed review-pack JSONL rows. It is
  read-only and does not inspect or mutate live inputs.
- `tools/validate_detector_maturity.py`: validates standalone or embedded detector-maturity records so Phase 2
  reports cannot treat `two_vote_required=0` or `source_disagreement=0` as proof that no such cases exist.
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
- `qamus/examples/decision_linkage.sample.jsonl`: tiny fixture slice covering resolved, pending, and superseded
  decision rows with exact token/hover addresses.
- `qamus/examples/hover_edit_intent.sample.jsonl`: tiny fixture slice covering token-only, parse-family, and
  entry/sense edit intents before repair-impact preview generation.
- `qamus/examples/repair_impact_preview.sample.jsonl`: tiny fixture slice covering the three edit scopes without
  touching live Qamus data.
- `qamus/examples/shadow_review_pack.sample.jsonl`: tiny fixture slice covering propagation-preview, collision
  quarantine, and missing-entry lanes without committing live graph dumps.

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
python tools/scan_public_boundary.py --public <public entry URL> --shadow-dir <isolated shadow output>
python tools/compare_wbw_artifacts.py <live wbw lookup> <mirror wbw lookup>
python tools/validate_detector_maturity.py <review pack jsonl or detector maturity json>
```

CI should use fixture/self-test mode only:

```bash
python tools/build_live_shadow_graph.py --self-test
python tools/validate_phase1_shadow_graph.py --self-test
python tools/summarize_shadow_closure_queue.py --self-test
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
```

## Guardrails

- `parse:<hash>` is a grammar-family key, never primary identity.
- `quran:S:A:W` and `wbw:S:A:W` remain the exact token/hover identities.
- Surface-only and norm-only rows must never certify or propagate.
- Two-vote and source-disagreement counts are detector maturity signals; zero does not prove absence. Review-pack
  rows carry this as required `apply_policy.detector_maturity`, and the validator rejects overconfident claims.
- Public hover output remains `src=qamus`, `kind=authored`, `lang=en`.
- Internal provenance may exist, but public scans must remain zero-leak.
- Mirror mismatch is report-only until a separate guarded sync is authorized.
