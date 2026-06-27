# Answer-Key Fixture Schema

Machine-usable checkpoint rows live in JSONL files such as
`curriculum/assessment/level-checkpoints.sample.jsonl`. Each line is one object.

Required fields:

| field | type | meaning |
|---|---|---|
| `id` | string | stable fixture id |
| `level` | string | roadmap level or range |
| `concept` | string | concept being checked |
| `prompt` | string | question shown to the learner |
| `quran_example` | string or null | Qurʾānic token/address if used |
| `expected_answer` | string | short model answer |
| `accepted_variants` | array of strings | acceptable alternate wording |
| `forbidden_answers` | array of strings | common wrong answers or forbidden reasoning |
| `required_reasoning` | array of strings | observations needed for credit |
| `sarf_procedure` | string or null | repo path for morphology remediation |
| `nahw_procedure` | string or null | repo path for syntax remediation |
| `remediation_route` | string | drill or procedure to assign on miss |
| `two_vote_required` | boolean | whether hard grammar requires independent agreement |

Rules:

- The fixture is Qamus/Fusha-authored. Do not copy external textbook, QAC, Quran.com, Tafsir, or lexicon wording.
- `two_vote_required=true` for iʿrāb, case, mood, particle function, PP attachment, pronoun referent, exception,
  vocative, oath, token-only override, and wrong-reasoning traps.
- The validator enforces this especially for Level 7+ rows: a hard-grammar checkpoint at Level 7 or later may not
  set `two_vote_required=false`.
- `forbidden_answers` should name the actual dogfood failure when possible: dictionary infinitive leakage,
  host-only preposition gloss, suffix omission, component-only overclaim, or root-family vibes.
- Open-ended items may use rubrics, but the rubric must say what is required, optional, and forbidden.
