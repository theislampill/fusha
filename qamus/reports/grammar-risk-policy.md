# Grammar-risk policy (GP0)

Governance policy for grammar-affecting decisions in the Fusha → Qamus → qamus-highlight loop, derived from the
GrammarProblems naḥw-accuracy study. **Binding** on every agent and batch in this repo.

## The premise

An independent 2026 study found a free general LLM answered Arabic naḥw at **~33% accuracy**, collapsing on
higher Bloom levels, the intermediate/advanced curricula, deep questions, and essay/iʿrāb reasoning. Therefore:

> **General LLM confidence is not evidence. A correct-looking answer with wrong iʿrāb reasoning is unsafe.**

## Policy

1. **No naḥw from memory alone.** Every grammar-affecting decision cites the sarf and/or nahw evidence ladder
   (`sarf/SKILL.md`, `nahw/SKILL.md`) and a source address — never the model's self-assurance.
2. **Conclusion + reason.** A decision is valid only if both the conclusion and the syntactic reasoning are
   correct. Right answer + wrong reason = **unsafe** = do not ship.
3. **Gate by difficulty** (`nahw/evals/grammar-decision-gates.json`):
   - iʿrāb · case/mood · istithnāʾ · لا النافية للجنس · ambiguous iḍāfa/jar-majrūr · multi-sense · referent-
     sensitive · deep · essay · advanced → **two independent checks** that agree on conclusion *and* reason.
   - ambiguous grammar · source conflict · suspected entry error · proper-vs-common · uncertain Qurʾān ref →
     **human/source review**.
   - norm-only · OCR-only · copied external gloss · wrong reasoning · QAC/POS conflict → **never auto-resolve**.
4. **Uncertain naḥw → pending, not a public gloss.** A precise pending reason beats a confident wrong gloss.
5. **iʿrāb-affecting changes** to a Qamus entry require a source address + the sarf/nahw decision object + the
   appropriate gate, and follow the owner-gated app-helper/DawahAgent apply path — never a direct write.
6. **Public artifacts stay clean.** The hover record is exactly `{src:"qamus",kind:"authored",lang:"en"}`; the
   study, QAC, Quran.com, Tanzil, OCR, and crops are internal evidence only and never named publicly.

## Enforcement

- `nahw/rules/grammar-problems-gates.json`, `two-vote-required-rules.json`, `irab-safety-gates.json` encode the
  triggers machine-readably.
- `tools/validate_linguistic_decisions.py` rejects a grammar-affecting decision lacking its required gate.
- `tools/check_regressions.py` includes a GrammarProblems-inspired gate assertion.
- This tranche's batches (P13 hover, P14 repair) route every grammar-affecting candidate through these gates.
