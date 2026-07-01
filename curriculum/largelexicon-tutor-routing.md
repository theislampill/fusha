# Largelexicon Tutor Routing

Largelexicon feeds tutoring by turning parser and Qamus rollout findings into
repeatable learning routes.

| Finding | Route |
| --- | --- |
| hidden clitic/proclitic | sarf clitic drill, then hover segmentation drill |
| host-only preposition hover | nahw jar-majrur drill, then public hover rewrite |
| `ما` unresolved | function-token decision drill |
| suffix pronoun missing | sarf/nahw pronoun attachment drill |
| passive/participle hidden | sarf derived-form drill |
| right gloss, wrong i'rab reason | nahw governor reasoning drill |
| source-address crosswalk missing | Qamus source graph repair packet, not learner drill |

The tutor may show Point and Teach levels from candidate data. Bottom-out
answers stay gated when i'rab, source repair, owner review, or scholar review is
needed.

## Using the Full Tables

The committed full tables let tutoring choose many more Qamus-backed surfaces
without network access:

- `lemma-source.full.jsonl` gives the entry/root/POS/no-root reason.
- `form-source.full.jsonl` gives listed forms and normalized keys.
- `largelexicon-stems.full.jsonl` gives segmentable morphology candidates and
  `generation_key` handles.
- `qamus-qword-denominator.full.jsonl` gives all visible Qamus example qwords
  as teaching targets, but source-address crosswalks may still be pending.

The tutor should phrase this as "Qamus has a candidate analysis" unless the
Mode A source-address and nahw/sarf gates have passed. For Mode C arbitrary
typing, unknown or ambiguous tokens should become questions, not corrections.
