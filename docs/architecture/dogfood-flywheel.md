# The dogfood flywheel — the loop and its accounting obligations

Status: adopted 2026-07-29 (canonical architecture doc, precedence tier 4).
The charter statement of the flywheel is
`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md` (owner-adopted, ARCHITECTURAL
COMMITMENT §2); this doc states the **engineering obligations** that make the
loop honest — the executable loop-stage vocabulary and the per-family
accounting every tranche owes. It adds no new policy.

## 1. The loop

Charter form (`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md` §2, verbatim):

```
canonically addressed Qurʾānic occurrences
→ provenance-tracked lexical and grammatical facts
→ competing and compatible ṣarf/naḥw analyses
→ reusable candidate-generation and proof rules
→ faster later Qurʾānic review
→ increasingly capable arbitrary-text analysis
→ controlled expansion into later Fusha corpora
→ new examples, exceptions, and rules flowing back into the engine
```

Executable form — the closed `loop_stage` enum of
`qamus/schemas/dogfood-event-ledger.schema.json`:

`defect_found` → `certified_or_preserved` → `typed_fact` → `rule_change` →
`fixture_added` → `projector_change` → `validator_change` → `skill_update` →
`analogous_discovery` → `shadow_test` → `deploy` → `readback` →
`lesson_return`

Event chains must start at `defect_found` with non-decreasing timestamps
(`tools/validate_acceleration_ledgers.py`). "Events are evidence, not
narrative." Note `deploy` remains in the enum but is owner-gated and
currently `LIVE_QAMUS_MUTATION: NOT_AUTHORIZED`; `shadow_test` runs only
under explicit bounded owner authorization (shadow scheduling is
RETIRED_BY_OWNER — see `docs/INDEX.md` §2–§3).

Dogfooding means the repo eats its own output: every batch that touches
occurrences must run the projected result back through the skills/validators
and commit the production-bug lessons it finds
(`tools/build_dogfood_production_bug_lessons.py`; ~30 committed
`qamus/examples/dogfood_vn*_production_bug_lesson.sample.jsonl` files;
front-end `tools/rich_hover_flywheel.py`, which "NEVER certifies, NEVER
applies live").

## 2. Per-family accounting requirements

Every tranche/family lane owes structural accounting — schema-enforced, so
honesty is not a prose promise:

- **Compounding-impact report**
  (`qamus/schemas/vn-compounding-impact-report.schema.json`,
  `qamus.vn_compounding_impact_report.v1`): per tranche, five outcome
  sections — `content_outcomes`, `graph_outcomes`, `skill_outcomes`,
  `automation_outcomes`, `pedagogy_outcomes`. Every leaf metric carries a
  `measurement_basis`; `acceleration_claimed=true` requires at least one
  non-rowcount metric with `measurement_basis=measured`.
- **Acceleration ledger** (`qamus/schemas/acceleration-ledger.schema.json`):
  per-tranche/family rows; required keys include `tranche` and `family`.
  `not_measured ⇒ value null`; acceleration is never claimed from row counts
  alone; every evidence path must exist.
- **Dogfood event ledger**
  (`qamus/schemas/dogfood-event-ledger.schema.json`): required `tranche` +
  `family` + `loop_stage` per event.
- Validator for all three: `tools/validate_acceleration_ledgers.py`.
  Committed samples: `qamus/examples/acceleration_ledger_vn02.sample.jsonl`,
  `qamus/examples/vn_compounding_impact_report_vn02.sample.json`.
- Family completion language is the named state vocabularies only: the
  12-state entry ladder (`tools/build_entry_completion_state.py`), the
  p007 rule that "p007 accounted" without a named `P007_*` state is
  forbidden, and per-occurrence quality states. Bare percentages or row
  counts never constitute completion.
- Measured **reuse** is part of the accounting: a follow-on family (e.g. the
  next P-family, بِـ) must reuse the previous family's machinery and report
  measured reuse, not rebuild in parallel.

## 3. "Occurrence-specific must state why"

Any fact, rule, or hover scoped to a single occurrence must state **why it is
occurrence-specific** — the discriminating reason, not just the scope:

- Hover **Reason** item: "why the winning analysis wins (the discriminating
  guard / defeater that eliminated the alternatives)"
  (`docs/qamus/particle-projection-contract.md` §1.2 item 11).
- Adjudication artifacts record "the ruling, grounds, and scope (this
  occurrence only vs. rule-level)" (`docs/certification-authority.md` §4).
- Abstentions name the ambiguity "for THAT occurrence only"
  (`tools/skill_fixtures/_build_increment21.py`).
- Two-vote v1.1 compares registry `reason_key`s, so the "why" is a governed
  vocabulary item, not prose.

The flywheel depends on this: a scoped fact without a stated reason can
neither become a rule (`lesson_return`) nor guard against unsafe analogous
reuse — the reason IS the defeater the next projector run needs.

---
Verified against: commit 637d7da (origin/main, 2026-07-29). Artifacts:
`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md`,
`qamus/schemas/{dogfood-event-ledger,acceleration-ledger,vn-compounding-impact-report}.schema.json`,
`tools/validate_acceleration_ledgers.py`, `tools/rich_hover_flywheel.py`,
`tools/build_dogfood_production_bug_lessons.py`,
`tools/build_entry_completion_state.py`,
`qamus/examples/acceleration_ledger_vn02.sample.jsonl`,
`qamus/examples/vn_compounding_impact_report_vn02.sample.json`;
`tools/check_regressions.py` ALL REGRESSION CHECKS PASS.
