# Largelexicon Claim Boundary

`largelexicon` is a source-clean candidate layer built from Qamus-authored entry
data. It is not live Qamus progress, not arbitrary-text certification, and not a
completed CAMeL/MADAMIRA/Stanza-style Classical Arabic NLP stack.

What this branch may claim after validation:

- it can inventory the 2,092 Qamus entries and their listed forms;
- it can generate reviewable lemma/form/stem samples from Qamus-owned data;
- it can run an opt-in `largelexicon` parser preview over those samples;
- it can produce Qamus Mode A worklist rows for all visible qword-style
  planning;
- it preserves public hover boundaries: `src=qamus`, `kind=authored`,
  `lang=en`;
- it routes uncertain rows to candidate/packet states instead of pretending
  they are deploy-ready.

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
