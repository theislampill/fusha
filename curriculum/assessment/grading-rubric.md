# Grading Rubric For Fusha Tutoring

This rubric makes level progression explicit. A learner does not clear a level by vibes, confidence, or a fluent
English paraphrase. They clear it by answering cold, then being checked against an answer key or procedure-linked
rubric.

## Clearance Rules

| level band | clearance rule |
|---|---|
| Levels 0-3 | answer key or one competent check is enough for objective script, particle, noun, and basic root items |
| Levels 4-6 | answer key plus procedure-linked reasoning for root, form, finite verb, iḍāfa, jar-majrūr, sentence type |
| Levels 7+ | answer key/rubric plus two independent checks for hard grammar, or route to pending/remediation |
| Any hard grammar | two independent checks when the item depends on iʿrāb, case, mood, particle function, PP attachment, pronoun referent, exception, vocative, oath, or token-only override |

Machine-readable Level 7+ checkpoint fixtures must mark those hard-grammar rows with `two_vote_required=true`;
`tools/validate_curriculum_assessment.py` rejects rows that try to clear that gate silently.

If two checks agree on the English answer but disagree on the grammatical reason, the answer is not cleared.

## Objective Item Rubric

Credit requires:

- expected answer or accepted variant;
- required reasoning named in the fixture;
- no forbidden answer;
- missed-error log updated if wrong.

Reject:

- root-family guessing without POS/form;
- dictionary infinitive on a finite verb;
- host-only answer when a visible preposition, particle, article, or suffix contributes meaning;
- component evidence used as whole-token certification;
- public source names or copied external wording.

## Open Grammar Item Rubric

Required observations:

- exact token or example;
- visible pieces;
- sarf state where relevant;
- nahw role where relevant;
- blocker if not certifiable;
- procedure path used.

Optional observations:

- parse-key implication;
- renderer/rich-hover implication;
- related production-bug lesson.

Forbidden reasoning:

- "it sounds right";
- "same root, same meaning";
- "external source agrees" when clitic/preposition/suffix contribution is missing;
- "the hover is populated, therefore correct";
- "parse key says so" without exact token address and gate.
