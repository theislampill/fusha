# qamustyping4 closure state

AUDIT_START

Goal: implement the qamustyping4 plan packet as far as the public Fusha repo can
safely and truthfully support, with every finding ending in `done`, `changed`,
`blocked`, `deferred`, or `unverified`.

Boundaries:

- no live Qamus mutation;
- no server mutation;
- no installed Codex skill mutation;
- no commit, push, tag, release, or merge;
- external sources remain internal evidence only;
- public hover fixtures stay `src=qamus`, `kind=authored`, `lang=en`.

Smoke A:

- `python tools/validate_qamustyping3_acceptance.py --self-test`: green
- `python tools/validate_source_artifact_ledger.py --self-test`: green
- `python tools/validate_fusha_morph_db.py --self-test`: green
- `python tools/validate_fusha_parser_baseline.py --self-test`: green
- `python tools/validate_fusha_evaluation.py --self-test`: green
- `python tools/validate_parser_claims.py --self-test`: green

Current abnormality:

The requested phrase "deliver ALL plans COMPLETELY" includes stronger
capabilities than the current repo can truthfully claim: broad corpus-backed
morphology, trained statistical disambiguation, trained dependency parsing, and
general arbitrary-text Grammarly equivalence. Those are not implementation
details; they require source permission, corpora, gold labels, metrics, and
release evidence.

5 Whys:

1. Why can qamustyping3 not be called a full stack? It has smoke fixtures and
   rule baselines, not broad corpora or trained models.
2. Why not simply train/build them now? The public repo does not yet have
   reviewed, license-cleared corpora and gold splits for that claim.
3. Why not import external systems? External references are internal evidence;
   public repo policy forbids copying external corpora/glosses without a
   reviewed source boundary.
4. Why not still claim arbitrary text? Source-addressed Qamus Mode A has graph
   oracles; arbitrary text does not, so the safety regime differs.
5. Why does this matter? Overclaiming would recreate the rollout failure mode:
   infrastructure labels looking green while actual words/pages remain sparse or
   unverified.

Countermeasure:

Add qamustyping4-specific ledger, regression fixtures, acceptance validator, and
claim gates so every stage is terminal and future executors know exactly what is
implemented versus blocked/deferred.

Changed:

- added `docs/parser/qamustyping4-implementation.md`;
- added `qamus/reports/qamustyping4-implementation-ledger.json`;
- added `qamus/examples/mode_a_all_qword/qamustyping4-regression-worklist.sample.jsonl`;
- added `qamus/examples/mode_a_all_qword/qamustyping4-visual-readback.fixture.jsonl`;
- added `fusha/parser/eval/qamustyping4-eval-matrix.json`;
- added `tools/validate_qamustyping4_acceptance.py`;
- added this run ledger;
- extended `sources/source-artifact-ledger.json` with the qamustyping4 artifacts;
- extended `tools/validate_parser_claims.py` to require the qamustyping4
  implementation, ledger, and evaluation matrix for stronger parser claims;
- fixed `scripts/build_claude_ai_project_pack.py` so manifest bytes and hashes
  use the same line-ending normalization as the drift validator;
- regenerated `dist/claude-ai/knowledge-manifest.md` after the pack drift fix.

Smoke B:

- `python tools/validate_qamustyping4_acceptance.py --self-test`: green
- `python tools/validate_source_artifact_ledger.py --self-test`: green
- `python tools/validate_parser_claims.py --self-test`: green
- JSON parse check for qamustyping4 ledgers/fixtures/eval/ledger: green
- `python tools/validate_qamustyping3_acceptance.py --self-test`: green
- `python tools/validate_fusha_morph_db.py --self-test`: green
- `python tools/eval_fusha_morphology.py --self-test`: green
- `python tools/validate_fusha_parser_baseline.py --self-test`: green
- `python tools/validate_fusha_evaluation.py --self-test`: green
- `python tools/validate_fusha_standalone_parse.py --self-test`: green
- `python tools/validate_qamus_mode_a_adoption.py --self-test`: green
- `python tools/validate_source_boundary.py qamus/examples/mode_a_all_qword/qamustyping4-regression-worklist.sample.jsonl`: green
- `python tools/validate_source_boundary.py --self-test`: green
- `python tools/check_artifact_ergonomics.py sources/source-artifact-ledger.json qamus/reports/qamustyping4-implementation-ledger.json fusha/parser/eval/qamustyping4-eval-matrix.json qamus/examples/mode_a_all_qword/qamustyping4-regression-worklist.sample.jsonl qamus/examples/mode_a_all_qword/qamustyping4-visual-readback.fixture.jsonl`: green
- `python tools/validate_claude_ai_pack_drift.py`: green after pack-generator fix
- `python tools/check_regressions.py`: green
- `git diff --check`: green

ANDON: source-boundary command-selection error

Observed: `validate_source_boundary.py` failed when pointed at Markdown or pretty
JSON files, because that validator is intentionally a JSONL public-payload
scanner.

5 Whys:

1. Why did it fail? The validator parsed Markdown/pretty JSON as JSONL rows.
2. Why was it invoked that way? The hygiene pass over-broadened a row scanner
   into a generic document scanner.
3. Why is that unsafe? It could convert a tool-use mistake into a false artifact
   defect.
4. Why not change the validator? Its current contract is useful for public
   payload rows; broadening it here would change an unrelated tool.
5. What prevents recurrence? Use `check_artifact_ergonomics.py`, `rg` leak
   checks, and JSON parsing for non-JSONL artifacts; reserve
   `validate_source_boundary.py` for JSONL public-row fixtures.

Disposition: command-selection error, not an artifact defect. Revalidated with
the correct tools.

ANDON: claude.ai pack drift after existing skill edits

Observed: broad regression initially failed on the pack drift gate. Direct drift
validation showed the manifest was stale after existing `README.md`,
`sarf/SKILL.md`, and `nahw/SKILL.md` edits.

5 Whys:

1. Why did regression fail? The manifest no longer matched the pack sources.
2. Why did rebuilding still show drift? The builder hashed raw checkout bytes,
   while the validator normalizes line endings.
3. Why did that matter here? Some generated scoreboard files had CRLF/LF
   differences even after rebuild.
4. Why not weaken the validator? The validator's normalized comparison is the
   stable user-visible contract.
5. What is the durable fix? Make the builder compute manifest size/hash using
   the same normalized text bytes as the validator.

Disposition: fixed locally and revalidated. `check_regressions.py` now passes.

Terminal stage ledger:

- P0 claim boundary/source ledger/public-private split: done.
- P0.5 thin all-qword vertical slice: done through fixtures and qamustyping3
  acceptance; qamustyping4 adds regression coverage against observed live
  sparse-color families.
- P1 morphology/generator expansion: changed with guarded qamustyping4
  regression coverage; broad corpus-backed morphology remains deferred behind
  source/corpus gates.
- P2 disambiguator/dependency/i`rab parser: changed with rule-baseline/eval
  gates; statistical/trained parser claim remains deferred behind gold labels,
  metrics, and model-card evidence.
- P3 Qamus Mode A all-qword adoption: changed with all-qword regression and
  visual-readback fixtures; live deployment remains out of scope.
- P4 evidence/release gates: changed with claim validator, eval matrix, and
  stronger public-boundary checks.
- P5 external corpora/model imports: deferred; no external corpus or model
  artifact imported.
- P6 skill/curriculum flywheel: changed through existing skill edits plus
  claim/pack validation; installed Codex skills were not mutated.
- P7 handoff/install: changed through docs, ledger, and pack manifest; no
  commit, push, install, or live deployment performed.

AUDIT_COMPLETE
