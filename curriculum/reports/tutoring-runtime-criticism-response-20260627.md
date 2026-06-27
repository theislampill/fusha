# Tutoring Runtime Criticism Response - 2026-06-27

Status: repo-only curriculum/assessment hardening. No live Qamus data, WBW artifacts, services, mirrors, or hover
decision ledgers were changed.

## Criticism Response

| criticism | valid? | response in this pass | remaining limitation |
|---|---|---|---|
| The repo has a syllabus but no enforceable grading. | yes | Added `assessment/grading-rubric.md` and sample JSONL checkpoint fixture. | Not a full LMS; tutors still apply rubrics. |
| Checkpoints lack answer keys or structured rubrics. | partly | Added `assessment/answer-key.schema.md` and `assessment/level-checkpoints.sample.jsonl`; updated checkpoint instructions. | Existing prose checkpoints are not all converted yet. |
| There is no learner progress state. | yes | Added `progress/learner-progress.template.md`. | Real learner files stay outside repo. |
| There is no missed-error log. | yes | Added `progress/missed-error-log.template.md` with dogfood error classes. | Real missed logs are private and uncommitted. |
| Level progression is too honor-system. | yes | Roadmap now requires cold attempt, rubric/key, progress update, miss log, and remediation. | Human honesty still matters; structure is now explicit. |
| Hard grammar needs two independent checks in tutoring, not only in authoring. | yes | Roadmap, mastery checkpoints, rubric, and tutor protocol all require two checks/rubric for hard grammar. | Automated dual-check scoring remains future work. |
| Skills may not auto-load in live tutoring. | yes | Added `tutor-session-protocol.md` and updated routing to tell agents what to load explicitly. | Hosted chat tools may still ignore unless user provides files/project pack. |
| Installed/project packs may omit curriculum files. | yes | Installer docs clarify repo-level tutoring runtime; project pack allowlist now includes protocol, assessment, progress, and remediation index. | Skill wrappers include skill-local curriculum, not every repo-level curriculum file. |
| Fluency scope needs to be reading-focused and honest. | yes | README and roadmap now state the scope and what is out of scope. | Speaking/listening curriculum must be sourced elsewhere. |

## Files Changed

- `curriculum/README.md`
- `curriculum/zero-to-fluency-roadmap.md`
- `curriculum/mastery-checkpoints.md`
- `curriculum/tutor-runtime-routing.md`
- `curriculum/tutor-session-protocol.md`
- `curriculum/assessment/*`
- `curriculum/progress/*`
- `curriculum/drills/dogfood-error-remediation-index.md`
- `curriculum/reports/dogfood-curriculum-crosswalk-20260627.md`
- `sarf/curriculum/dogfood-sarf-map.md`
- `sarf/drills/dogfood-sarf-remediation.md`
- `nahw/curriculum/dogfood-nahw-map.md`
- `nahw/drills/dogfood-nahw-remediation.md`
- `INSTALL.md`
- `dist/claude-ai/README.md`
- `dist/claude-ai/pack.include.txt`
- `tools/validate_curriculum_assessment.py`
- `tools/check_regressions.py`

## Scope Boundaries

- Repo curriculum work: changed.
- Rich metadata work: not regenerated; existing RICH/P-RICH/VN-RICH artifacts were mined as inputs.
- Live Qamus hover decisions: not changed.
- Renderer implementation: not changed.
- Future live apply planning: unchanged and owner-gated.

## Future Work

- Convert more prose checkpoints into machine-graded JSONL rows.
- Add a richer answer-key validator if a future tutoring UI consumes these fixtures.
- Add learner-state import/export tooling only if a real tutoring runtime needs it.
- Keep all real learner progress and missed-error logs outside the public repo.
