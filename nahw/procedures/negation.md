# Procedure — negation scope

**Invoke when:** a negative particle governs the token (or the token is one).

**Checks** ([`../rules/negation-rules.json`](../rules/negation-rules.json)):
1. **لَمْ** + jussive → negates the PAST: a present-FORM verb means "did not …" (لَمْ يَلِدْ = "did not beget").
2. **لَنْ** + subjunctive → categorical FUTURE negation ("will never").
3. **لَا** — multi-function: simple negation / prohibition (+jussive) / لا النافية للجنس ("there is no") / "no".
4. **مَا** — negation is only ONE reading (also relative/interrogative/maṣdariyyah).
5. **لَيْسَ** — "is not" (nominal-sentence negation).

**Rule:** the governing negative — not the verb's surface tense — sets the English. Resolve the لَمْ/لِمَ
homograph FIRST (`particle-decision.md`), then apply the negation effect.

**Output:** tense/polarity-correct gloss, or pending(negation_scope) if the governed mood/POS is unknown.

**Forbidden:** glossing the bare surface tense under a negative; defaulting مَا to "not".

**Gate:** لا النافية للجنس / multi-function مَا → two_vote (`grammar-risk-gate.md`).
