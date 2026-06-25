# claude.ai Qamus-review-runtime self-test (closure-2092 Phase 10)

For a Qamus reviewer using the claude.ai pack (review/draft only; no validators/apply).

| reviewer question | route | answer shape |
|---|---|---|
| is this token form-variant-safe? | review-only-casebook.md + sarf/procedures/homograph-risk.md | bucket + collision-free? + 2-vote gate |
| is this gloss too generic? | nahw/procedures/particle-decision.md | needs particle function, not from/what/it |
| may I copy this source wording? | provenance/source-boundaries.md | no — authored Qamus only; informed_by internal |
| is this a verb-clitic or a possessive? | verb-clitic-lane-readiness.md + nahw/procedures/preposition-pronoun.md | verb enclitic = object/subject, not possessive |
| does this root need a new entry? | new-entry-proposal-lane-readiness.md | owner-gated proposal; never autonomous |

**Boundary:** claude.ai drafts candidate JSONL + reviews; Claude Code runs the validators and commits.
