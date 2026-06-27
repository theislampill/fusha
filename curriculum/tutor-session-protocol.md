# Tutor Session Protocol

Use this file when running a Fusha tutoring session from the repo. It is a routing protocol, not a live Qamus
apply plan.

## Session Startup

Copy-paste starter:

```text
We are using the Fusha repo as the tutoring runtime. Load curriculum/zero-to-fluency-roadmap.md,
curriculum/tutor-runtime-routing.md, my progress file, and the relevant sarf/nahw procedures. Do not grade hard
grammar from confidence alone. For iʿrāb, case/mood, particle function, PP attachment, exception, vocative, oath,
or pronoun referent questions, check the reasoning independently before marking me correct. Update my missed-error
log and tell me what to review next.
```

## Required Inputs

1. Learner progress file, if present. If not, start with
   `curriculum/progress/learner-progress.template.md`.
2. Missed-error log, if present. If not, start with
   `curriculum/progress/missed-error-log.template.md`.
3. `curriculum/zero-to-fluency-roadmap.md`.
4. `curriculum/mastery-checkpoints.md`.
5. `curriculum/assessment/grading-rubric.md`.
6. `curriculum/assessment/level-checkpoints.sample.jsonl` or another approved checkpoint fixture.
7. Relevant `sarf/` and `nahw/` procedures named by the route.

## Loop

1. Identify the learner's current level.
2. Pick the next lesson or checkpoint from the roadmap.
3. Ask the learner to answer cold.
4. Grade against an answer key or rubric.
5. If wrong, record the miss in the missed-error log.
6. Route the miss to the exact sarf/nahw procedure and remediation drill.
7. For hard grammar, require two independent checks or an answer-key-backed rubric before clearing.
8. Update the progress file with pass/fail, remediation, and next step.
9. Prefer `pending / not yet certified` over confident guessing.

## Hard Grammar Escalation

Require two independent checks when an item depends on:

- iʿrāb role, case, or mood;
- particle function, including `مَا`, `و`, `ف`, `ل`, `ب`, `لا`, `لم`, `لن`, `إلا`;
- PP attachment, jar-majrūr attachment, or iḍāfa relation;
- pronoun referent;
- relative, interrogative, conditional, vocative, exception, or oath frame;
- token-only override;
- component-only evidence.

If two checks agree on English but disagree on grammatical reason, do not mark the level cleared. Route to
remediation or teacher/owner review.

## Skill Loading Boundary

Claude/Codex skill triggering is not guaranteed in free-flowing tutoring. The tutor should explicitly load this
repo's curriculum and the named procedures. Installed `fusha-sarf` and `fusha-nahw` skill wrappers include their
own curriculum/drill trees, but the full zero-to-fluency tutoring runtime is the repo checkout plus the project
pack files listed in `dist/claude-ai/pack.include.txt`.

## Scope

This is a reading-focused Fusha path for Qurʾānic and classical/register-adjacent reading. It builds script,
sarf, nahw, hover-gloss reasoning, and parse-key discipline for unseen texts. It is not a complete speaking,
listening, dialect, or general MSA news/conversation course. Those skills need supplementation elsewhere.
