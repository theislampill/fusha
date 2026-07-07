# Qamus Grammar V1 Class Map

This is the canonical qg class reference for source-clean rich-hover/color projection.

## Canonical classes

- `qg-particle`
- `qg-preposition`
- `qg-article`
- `qg-noun`
- `qg-noun-stem`
- `qg-proper-noun`
- `qg-adjective`
- `qg-verb`
- `qg-verb-prefix`
- `qg-verb-stem`
- `qg-subject-pronoun`
- `qg-object-pronoun`
- `qg-possessive-pronoun`
- `qg-dual-suffix`
- `qg-plural-suffix`
- `qg-derivative-prefix`
- `qg-relation`
- `qg-negation`

## Alias policy

`qg-negation` is canonical. `qg-negative` is a documented legacy alias only for validator migration and should
not be newly emitted. Any other qg alias must be added here before it can appear in sarf, nahw, curriculum, or
candidate rows.

## Public boundary

qg classes are display roles, not provenance. They must not encode source names, evidence labels, local paths, or
review process text.

**No internal parser / debug ids or parse hashes in any public field.** The public payload (gloss, learner
text, `parse_key.summary`, qg class, data attributes) is grammar-facing only. It must never contain an internal
parse id, node id, candidate id, decision id, or a **parse hash** — those are internal-only and live in the
private evidence sidecar. `parse_key.summary` is compact learner ASCII (e.g. `V:I:PERF:ACT`, `P:bi`, `ART`), not
a symbolic engine key. A learner-facing colour legend follows the same rule: grammar-role labels + swatches only,
never a source/tool/process label or debug id. Enforced target: parse-hash public exposure stays **0**.
Detectors: `tools/leak_sot.py` (forbidden names/paths, word-anchored), `tools/validate_public_private_boundary.py`
(public-blob label scan); pedagogy: `curriculum/visual-grammar-legend.md`, `curriculum/dark-mode-accessibility-pedagogy.md`.
