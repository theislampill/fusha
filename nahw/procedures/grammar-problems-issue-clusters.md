# Procedure — GrammarProblems issue clusters

Use this procedure after the Phase 3.25 mining ledger classifies a case and
before Phase 4 corpus-facing grammar authoring.

The machine-readable owner is
[`../rules/grammar-problems-issue-clusters.json`](../rules/grammar-problems-issue-clusters.json).
The ledger is
[`../evals/grammar-problems-phase3p25-mining.jsonl`](../evals/grammar-problems-phase3p25-mining.jsonl).

## Issue #1 — right answer with wrong reasoning

Reject a hover or repair when the final English looks plausible but the iʿrāb,
case, mood, exception, or deep reasoning is wrong or conclusion-only.

- Required action: answer and reasoning must both pass.
- Gate: `two_vote_required`.
- Teach: the parse is part of the answer.
- Typical rows: deep, essay, analysis, evaluation, generation, and explicit
  wrong-reasoning traps.

## Issue #2 — function and attachment ambiguity

Reject host-only or phrase-flattened hovers when a particle, preposition,
iḍāfa, PP attachment, hāl, tamyīz, badal, istithnāʾ, or tanāzuʿ relation is the
reason the token means what it means.

- Required action: identify the function or attachment before authoring.
- Gate: `two_vote_required` unless the referenced procedure explicitly permits
  a narrower safe path.
- Teach: small grammar pieces change the learner-facing contribution.
- Typical rows: iḍāfa, jar-majrūr, hāl, tamyīz, badal, istithnāʾ, tanāzuʿ.

## Issue #3 — morphosyntax preservation

Reject lemma hovers that hide form, voice, case, mood, suffix pronouns, or
visible clitic contribution.

- Required action: preserve material morphology in the visible hover or parse
  metadata; otherwise mark precise pending.
- Gate: `two_vote_required` for grammar-sensitive rows.
- Teach: the same root is not the same token once form, voice, mood, case, or
  suffix changes.
- Typical rows: present-verb building, signs of iʿrāb, passive transformation,
  kāna/zanna/la-nāfiyah-lil-jins, mamnūʿ min al-ṣarf, suffix pronouns.

## New root-cause cluster

If a mined row does not fit Issues #1-#3, do not improvise a production fix.
Create a named production bug lesson with:

- bug class,
- concrete token/source addresses,
- sarf lesson,
- nahw lesson,
- learner explanation,
- drill,
- regression fixture,
- validator link.

Then update the issue-cluster contract and rerun
`tools/validate_grammar_issue_clusters.py`.

## Positive controls

The `correct_positive_regression` rows prove that direct rows are still
accepted when they pass all other gates. They are not evidence for broad
auto-propagation and must not weaken the grammar-risk policy.
