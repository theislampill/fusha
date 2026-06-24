# Procedure — grammar-risk gate (GrammarProblems)

**Invoke when:** any grammar-affecting decision (iʿrāb, case/mood, particle, construct, referent).

**The premise:** a 2026 study put a free general LLM at ~33% on Arabic naḥw. **LLM confidence is not evidence; a
correct answer with wrong iʿrāb reasoning is unsafe.** ([`../evals/grammar-decision-gates.json`](../evals/grammar-decision-gates.json),
[`../../qamus/reports/grammar-risk-policy.md`](../../qamus/reports/grammar-risk-policy.md))

**Choose the gate by triggers:**
- **auto_safe** — QAC root+POS agree, one Qamus sense, no homograph, no grammar-context dependency.
- **two_vote_required** — iʿrāb / case-mood / istithnāʾ / لا النافية للجنس / ambiguous iḍāfa-jar-majrūr /
  multi-sense / referent-sensitive / deep / essay / advanced. **Two independent checks must agree on conclusion
  AND reasoning.**
- **human_source_review_required** — ambiguous grammar / source conflict / suspected entry error / proper-vs-common
  / uncertain Qurʾān ref.
- **never_auto_resolve** — norm-only / OCR-only / copied external gloss / wrong reasoning / QAC-POS conflict.

**Output contract:** the decision object carries `gate`, `grammar_triggers`, and `reasoning`;
`validate_linguistic_decisions.py` REJECTS it if the gate is weaker than triggers require, a two-vote/iʿrāb
decision lacks reasoning, or a never-auto/human decision is marked exportable.

**Forbidden:** shipping a grammar decision on the answer alone; gating below the trigger tier.

**Test:** `tools/check_regressions.py` (grammar-gate assertions); `validate_linguistic_decisions.py --self-test`.
