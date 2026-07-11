# Qamus Grammar V1 Class Map

This is the canonical qg class reference for source-clean rich-hover/color projection.

<!-- GENERATED from qamus/schemas/morphosyntax-token.schema.json by
     tools/validate_schema_coherence.py --emit-class-map. Do NOT hand-edit the table;
     add a class to the schema enum and regenerate. -->

## Canonical classes (generated from the morphosyntax-token schema enum)

| qg class | in CSS/DOM fixture | status |
| --- | --- | --- |
| `qg-adjective` | yes | canonical |
| `qg-alternative` | no | canonical |
| `qg-article` | yes | canonical |
| `qg-case` | yes | canonical |
| `qg-comitative` | no | canonical |
| `qg-conditional` | no | canonical |
| `qg-conjunction` | yes | canonical |
| `qg-demonstrative` | no | canonical |
| `qg-derivative-prefix` | no | canonical |
| `qg-dual-suffix` | yes | canonical |
| `qg-emphasis` | no | canonical |
| `qg-exception` | no | canonical |
| `qg-future-particle` | no | canonical |
| `qg-interrogative` | no | canonical |
| `qg-lam` | yes | canonical |
| `qg-ma-particle` | yes | canonical |
| `qg-negation` | no | canonical |
| `qg-negative` | no | legacy alias of `qg-negation` |
| `qg-noun` | yes | canonical |
| `qg-noun-stem` | yes | canonical |
| `qg-number` | no | canonical |
| `qg-oath` | no | canonical |
| `qg-object-pronoun` | yes | canonical |
| `qg-particle` | yes | canonical |
| `qg-plural-suffix` | yes | canonical |
| `qg-possessive-pronoun` | yes | canonical |
| `qg-preposition` | yes | canonical |
| `qg-pronoun` | yes | canonical |
| `qg-proper-noun` | yes | canonical |
| `qg-question` | no | canonical |
| `qg-referential-pronoun` | no | canonical |
| `qg-relation` | no | canonical |
| `qg-relative` | no | canonical |
| `qg-result` | yes | canonical |
| `qg-result-fa` | yes | canonical |
| `qg-subject-pronoun` | yes | canonical |
| `qg-unknown` | no | canonical |
| `qg-verb` | yes | canonical |
| `qg-verb-prefix` | yes | canonical |
| `qg-verb-stem` | yes | canonical |
| `qg-vocative` | no | canonical |

## Alias policy

`qg-negation` is canonical. `qg-negative` is a documented legacy alias only for validator
migration and should not be newly emitted. Any other qg alias must be added to
`QG_LEGACY_ALIASES` in `tools/validate_schema_coherence.py` and to the schema enum before it
can appear in sarf, nahw, curriculum, or candidate rows.

## Public boundary

qg classes are display roles, not provenance. They must not encode source names, evidence
labels, local paths, or review process text.

**No internal parser / debug ids or parse hashes in any public field.** The public payload
(gloss, learner text, `parse_key.summary`, qg class, data attributes) is grammar-facing only. It
must never contain an internal parse id, node id, candidate id, decision id, or a **parse hash** --
those are internal-only and live in the private evidence sidecar. `parse_key.summary` is compact
learner ASCII (e.g. `V:I:PERF:ACT`, `P:bi`, `ART`), not a symbolic engine key. A learner-facing
colour legend follows the same rule: grammar-role labels + swatches only, never a
source/tool/process label or debug id. Enforced target: parse-hash public exposure stays **0**.
Detectors: `tools/leak_sot.py` (forbidden names/paths, word-anchored),
`tools/validate_public_private_boundary.py` (public-blob label scan); pedagogy:
`curriculum/visual-grammar-legend.md`, `curriculum/dark-mode-accessibility-pedagogy.md`.
