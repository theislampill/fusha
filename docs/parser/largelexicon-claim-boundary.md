# Largelexicon Claim Boundary

`largelexicon` is a source-clean candidate layer built from Qamus-authored entry
data. It is not live Qamus progress, not arbitrary-text certification, and not a
completed CAMeL/MADAMIRA/Stanza-style Classical Arabic NLP stack.

What this branch may claim after validation:

- it can inventory the 2,092 Qamus entries and their listed forms;
- it can generate reviewable lemma/form/stem samples and allowlisted
  source-clean full tables from Qamus-owned data;
- it can run an opt-in `largelexicon` parser preview over those Qamus-derived
  tables;
- it can produce Qamus Mode A worklist rows for all visible qword-style
  planning;
- it can expose a local JSON/JSONL CLI contract for `analyze-token`,
  `analyze-card`, `project-hover`, and `validate-mode-a`;
- it preserves public hover boundaries: `src=qamus`, `kind=authored`,
  `lang=en`;
- it routes uncertain rows to candidate/packet states instead of pretending
  they are deploy-ready.
- it detects high-risk short-token collisions and prevents the first
  largelexicon candidate from becoming a public hover preview when context or
  source-address proof is missing (see
  `docs/parser/largelexicon-collision-safety.md`).

What it must not claim:

- live Qamus append, replacement, readback, health, DUV, or tranche closure;
- arbitrary-text Classical Arabic correctness;
- trained statistical disambiguation;
- trained dependency parsing;
- copied external source wording;
- public provenance from MCP, QAC, Quran.com, Tanzil, Tafsir, source photos, or
  server paths.

Stronger language requires measured analyzer coverage, OOV/error rates,
disambiguation accuracy, dependency/i'rab evaluation, source-license review,
model/rule cards, and Qamus public readback owned by the rollout executor.

The long-horizon target is a dependency-free Classical Arabic NLP stack across
Mode A authoring, Mode B tutoring, and Mode C standalone parsing. That is a
target-state claim, not a present-tense equivalence claim.

Largelexicon coverage is not disambiguation. If a larger table creates a
homographic, function-token, or segmentation collision, parser output must route
to `lexical_collision_requires_context`, `pending_context`, `ambiguous`, or a
two-vote/scholar packet rather than projecting `morphology_candidates[0]` as a
public hover. CLI fields such as `safe_for_public_hover` and
`safe_for_qamus_executor_autopromote` are the consumer contract; downstream
workers must not infer safety from candidate order.
