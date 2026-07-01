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
