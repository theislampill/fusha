# L1–L6 curriculum → instructional & skill-backprop substrate

This subtree turns the six-level "Arabic for English Speakers" curriculum
(A1–C2, 226 lessons) into a **qualified, machine-usable substrate** for the
ṣarf/naḥw skills, the tutor/drills surfaces, and the linguistic flywheel. It
is NOT a static curriculum archive, and curriculum prose is NOT linguistic
authority: every extracted proposition carries an explicit qualification
status, and nothing here is certified (only `tools/certify_typed_fact.py`
certifies; this subtree contains zero certified rows).

**Custody boundary (read first):** [`custody/custody-decision.md`](custody/custody-decision.md).
The full lesson corpus is private source custody; committed artifacts carry
hashes, counts, titles/slugs/heading labels and independently authored derived
structures only.

## Layout

| Path | Contents | Generated? |
|---|---|---|
| `custody/` | source manifest (232 files, SHA-256, counts, custody status) + custody decision | manifest: yes |
| `registry/` | levels (6) / modules (32) / lessons (226) with stable IDs (`L4.M2.07`) | yes |
| `graph/` | 1,740 concept nodes (per-lesson section headings, 15-domain classification) + curriculum-order and concept-revisit edges | yes |
| `eval-separation/` | material-class census: what may and may not serve as evaluation (3,096 quiz questions have NO answer key) | yes |
| `crosswalk/` | ṣarf / naḥw capability crosswalks (curriculum domain → repository executable state) + instructional-method crosswalk | authored |
| `ledger/` | claim qualification ledger: extracted linguistic propositions with statuses + overgeneralization guards | authored |
| `links/` | candidate links from curriculum concepts to P/V/N entries and occurrences (ALL candidate) | authored |
| `packets/` | `TP-CURR-*` skill-backprop task packets (schema `qamus.task_packet.v1`) | authored |
| `pilot/` | root-vs-pattern-vs-affix letter-ownership pilot: candidate procedure, fixtures, colour segmentation + hover parity | authored |

Generated artifacts name their generator (`tools/build_curriculum_l1l6.py`);
regenerate with the private corpus, verify with `--check`. Validate everything
standalone with `python tools/validate_curriculum_l1l6.py` (self-test:
`--self-test`). Neither script is wired into `tools/check_regressions.py` by
this lane (Sol-owned shared harness); the one-line integration is in the PR
description.

## Status vocabulary (hard boundary)

Concept/claim statuses used here: `repository-certified` (never asserted by
this subtree on its own authority) · `source-supported-not-executable` ·
`pedagogical-simplification` · `analysis-dependent` · `school-dependent` ·
`candidate-requiring-review` · `contradicted-by-repository-authority` ·
`unsafe-for-automatic-projection`. Curriculum inclusion never implies
linguistic certification; shared root never implies shared lexeme, sense or
translation; identical surface never implies identical function.
