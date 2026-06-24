# GrammarProblems — naḥw evaluation matrix (GP0)

Machine-readable: [`grammar-problems-matrix.json`](grammar-problems-matrix.json). This turns a 2026 peer-reviewed
Arabic-naḥw LLM-accuracy study into an **evaluation gate** for grammar-affecting agent decisions. The study's
questions and body text are **not reproduced** — only its tested dimensions, headline findings, and the
engineering rule they imply. The source is internal evidence only; it never appears in a public hover artifact.

## What the study tested

| dimension | values |
|---|---|
| level | beginner (al-Ājurrūmiyyah) · intermediate (Qaṭr al-Nadā) · advanced (Awḍaḥ al-Masālik) |
| Bloom | recall · understanding · application · analysis · evaluation · generation |
| format | objective · essay |
| depth | direct · deep |

## Headline finding (why this is a gate)

A **free general LLM scored ~33.33% overall** on 72 Arabic-naḥw questions, and **collapsed** on the higher Bloom
levels, the intermediate/advanced curricula, deep questions, and essay/iʿrāb reasoning. It did best on
beginner / direct / objective / recall.

**Engineering reading:** general LLM confidence is **not evidence** for a grammar decision. A correct-looking
final answer with **wrong iʿrāb reasoning is unsafe** and must not ship. Grammar-affecting decisions must pass the
sarf + nahw evidence ladders, not the model's self-assurance.

## The gate (per cell)

The decision gate scales with difficulty — exactly where the study shows the model fails:

- **deep / essay / analysis-evaluation-generation / advanced** → `two_vote_advanced` (two independent checks),
  hover `pending_if_reason_uncertain`.
- **iʿrāb · case/mood · لا النافية للجنس · istithnāʾ · ambiguous iḍāfa/jar-majrūr** → `two_vote_advanced`,
  hover **`never_auto`** (these are reasoning-dependent and the study's worst areas).
- **beginner / direct / objective / recall** → `nahw_only` (or `sarf_only`), hover `safe_if_cited`.

## Topic → gate (representative)

| topic | gate | hover safety |
|---|---|---|
| iʿrāb (case/mood assignment) | two_vote_advanced | never_auto |
| لا النافية للجنس | two_vote_advanced | never_auto |
| istithnāʾ (إلّا/غير/سوى) | two_vote_advanced | never_auto |
| conditional vs relative | two_vote_advanced | pending_if_reason_uncertain |
| negation scope (لم/لن/لا/ما/ليس) | sarf_plus_nahw | pending_if_reason_uncertain |
| iḍāfa | sarf_plus_nahw | pending_if_reason_uncertain |
| proper vs common noun | sarf_plus_nahw | never_auto |
| jar-majrūr (prep + pronoun) | nahw_only | safe_if_cited |
| particles (harakah-decided) | nahw_only | safe_if_cited |
| nominal sentence | nahw_only | safe_if_cited |
| verb measure (form I-X) | sarf_only | safe_if_cited |

## How it plugs in

- `nahw/rules/grammar-problems-gates.json` + `two-vote-required-rules.json` encode these as machine-readable gates.
- `tools/validate_linguistic_decisions.py` rejects a grammar-affecting decision that lacks the required gate.
- `qamus/reports/grammar-risk-policy.md` is the governance policy; `nahw/drills/grammar-reasoning-safety.md` is the
  agent drill ("answer + reason must both be right").
