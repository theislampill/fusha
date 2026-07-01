# Plan 15 Nahw Route Families

Use this procedure when Plan 15 or largelexicon flywheel rows need a syntax/function-owned terminal route.

## Routes

| route | nahw meaning | next action |
|---|---|---|
| `governor_irab_fixture_needed` | case, mood, attachment, or governor is not justified | create scholar/i'rab fixture packet |
| `particle_function_rule_needed` | particle or cluster function lacks a reusable rule | create function-token rule packet |

## Required fields

Every nahw route packet needs:

- visible surface;
- context window;
- qword denominator/source-address row;
- source-card/source-crosswalk status;
- candidate function or governor question;
- public-hover eligibility;
- private evidence references;
- exact reviewer question.

## Examples

`أَمْ` cannot be accepted from the English gloss "or" alone. It needs contextual function: interrogative,
disjunctive, transition, or rhetorical. If the function rule is missing, route `particle_function_rule_needed`.

`لَهُمْ` contains lām plus attached pronoun. Sarf preserves pieces; nahw decides relation and referent. If the
relation/governor is not justified, route `governor_irab_fixture_needed`.

`وَمَا` is one written Quranic token but two grammar pieces: wāw plus function-specific mā. If mā's function is
unresolved, route `particle_function_rule_needed`.

## Scholar packet

Use `scholar_irab_packet` only with one exact question. Do not create broad backlog buckets. A right gloss with
wrong or weak i'rab reasoning remains unsafe.
