# FC1 Naḥw Dependency Producers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and verify a fail-closed F-A naḥw dependency producer and bounded calibration packet for FC1.

**Architecture:** A stdlib-only producer joins explicit external inputs, extracts only source-addressed naḥw evidence, and emits one F-A governed contract per selected occurrence. A separate validator/test fixture layer enforces required governor/governed/relationship/case-or-mood/ending/source/certification fields, typed abstention, and lexical-surface preservation. The existing regression harness invokes self-tests and committed fixtures without reading external corpus files.

**Tech Stack:** Python 3.11 standard library, existing F-A contract helpers, JSONL, `unittest`, Git.

## Global Constraints

- Naḥw dependency producers remain separate from morphology producers.
- A bare role is invalid without exact governor, governed occurrence, relationship evidence, case/mood where applicable, ending status and estimation reason when needed, source, and certification status.
- Naḥw facts never repaint lexical letters; projection uses explanations, brackets, relations, ending classes, or expanded views.
- External corpus inputs are explicit CLI arguments only; committed fixtures are self-contained and contain no lane-workspace paths.
- Outputs are candidate/review-only; no whitelist, renderer, live app, deploy, push, or production mutation changes.
- All commits use the `fc1:` prefix.

---

### Task 1: Add red-first producer contract tests and fixtures

**Files:** `tools/test_fc_nahw_producer.py`, `qamus/examples/fc1-nahw/producer-fixtures.jsonl`

**Interfaces:** Tests import `build_dependency_fact`, `build_unresolved_record`, `validate_dependency_fact`, and `surface_is_preserved` from `tools.fc_nahw_producer`. Fixtures contain exact occurrences, relationships, case/mood, endings, source, and certification fields.

- [ ] Write tests for five positive cases: subject governor, object governor, preposition-to-governed relation, pronoun attachment with referent, and an estimated ending.
- [ ] Write adversarial tests for bare-role rejection, missing-governor abstention, required estimated-ending flag, case-without-governor rejection, and lexical-surface repaint rejection.
- [ ] Run `python -m unittest tools.test_fc_nahw_producer -v`; confirm the import failure is red because the producer does not exist.
- [ ] Commit with `fc1: add red-first nahw producer fixtures` after `git diff --check`.

### Task 2: Implement strict dependency fact construction and typed abstention

**Files:** `tools/fc_nahw_producer.py`, `tools/test_fc_nahw_producer.py`

**Interfaces:**

- `build_dependency_fact(input_row: dict, *, source_record_id: str, projector_id: str = ...) -> dict` returns a validated F-A fact envelope or raises `ValueError` with a precise blocker.
- `build_unresolved_record(input_row: dict, *, blocker: str, source_record_id: str) -> dict` returns a validated `syntax_pending` F-A envelope with no linguistic claim.
- `validate_dependency_fact(fact: dict) -> list[str]` returns semantic errors.
- `surface_is_preserved(source_surface: str, projected_surface: str) -> bool` compares exact Unicode text.

- [ ] Implement immutable alias normalization, stable SHA-256 IDs, exact quran/wbw occurrence helpers, and the closed producer/projector metadata.
- [ ] Require role, exact governor, exact governed occurrence, relationship evidence, case/mood applicability/value where relevant, ending status, source addresses, and F-A certification/evidence fields.
- [ ] Accept visible endings; accept estimated endings only with a reason and candidate/review certification; reject lexical-surface changes.
- [ ] Emit `syntax_pending` with `evidence_mode: unresolved`, a blocker, the existing English unresolved statement, `learner_visible: true`, and `claim: null` when evidence is missing.
- [ ] Run the focused suite to green and commit with `fc1: implement strict nahw dependency facts`.

### Task 3: Implement explicit-input calibration selection and sample artifacts

**Files:** `tools/fc_nahw_producer.py`, `qamus/examples/fc1-nahw/fc1-calibrated-sample.jsonl`, `qamus/examples/fc1-nahw/fc1-calibrated-sample.meta.json`, `qamus/examples/fc1-nahw/fc1-unresolved-sample.jsonl`, `qamus/examples/fc1-nahw/fc1-unresolved-sample.meta.json`, `qamus/examples/fc1-nahw/README.md`

**Interfaces:** The calibration CLI requires `--strat-455`, `--v575-verdicts`, `--whitelist`, and `--output-dir`; it has no external-input defaults. `build_calibration_packet(strat_rows, verdict_rows, corpus_rows, *, positive_limit: int = 30, unresolved_rows: Sequence[dict] = ()) -> dict` returns records and accounting.

- [ ] Join on exact `loc`, verify verdict/source surface agreement, and fail closed on missing or duplicate joins.
- [ ] Ignore morphology-only notes; resolve same-token and neighboring governor/governed occurrences from source addresses and classify the priority family.
- [ ] Select a stable priority-balanced sample of at least 30 valid rows; route nonqualifying rows and no-evidence rows to typed unresolved output.
- [ ] Run the explicit-input CLI to generate only the committed calibration sample and meta sidecars; commit with `fc1: add calibrated nahw sample packet`.

### Task 4: Add validator, full-harness gate, and FC1 report

**Files:** `tools/validate_fc1_nahw_producer.py`, `tools/check_regressions.py`, `docs/reports/history/2026-07-16-FC1-REPORT.md`

**Interfaces:** `--self-test` prints `FC1 NAHW PRODUCER SELF-TEST PASS`; `--fixtures qamus/examples/fc1-nahw` prints `FC1 NAHW PRODUCER FIXTURES PASS`.

- [ ] Validate every committed F-A envelope, positive/unresolved accounting, surface preservation, source/certification fields, and absence of lane paths.
- [ ] Wire both repo-self-contained validator invocations into `tools/check_regressions.py` without external corpus arguments.
- [ ] Write `docs/reports/history/2026-07-16-FC1-REPORT.md` with outcome table, abstention formula/value, evidence-mode counts, command results, and an `EXACT NONCLAIMS` section.
- [ ] Commit with `fc1: wire nahw producer harness and report` after `git diff --check`.

### Task 5: Final verification

- [ ] Run `python -m unittest tools.test_fc_nahw_producer -v`.
- [ ] Run `python tools/validate_fc1_nahw_producer.py --self-test` and `--fixtures qamus/examples/fc1-nahw`.
- [ ] Run `python tools/check_artifact_ergonomics.py`, `git diff --check`, and `python tools/check_regressions.py`.
- [ ] Confirm fresh output contains `ALL REGRESSION CHECKS PASS`, inspect status/diff, and do not push.
