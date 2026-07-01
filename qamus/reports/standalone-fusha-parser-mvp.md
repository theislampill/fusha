# Standalone Fusha Parser MVP

Status: implemented on branch `feature/fusha-standalone-parser-qamus-kernel`.

This branch adds a small, source-clean Fuṣḥā/Classical Arabic parser/checker kernel. It is designed to support Qamus/RH-LIVE authoring, learner tutoring, and standalone typing experiments without pretending that arbitrary text has source-address certainty.

## What It Adds

- `tools/fusha_clitic_splitter.py`: wraps the existing mark-aware splitter and adds qg labels/gloss hints.
- `tools/fusha_pattern_engine.py`: seed lexicon and conservative pinned-pattern analysis.
- `tools/fusha_context_parser.py`: context candidates for prepositions, function particles, attached pronouns, and `ما`.
- `tools/fusha_standalone_parse.py`: CLI and JSON producer for `fusha/standalone-parse@1`.
- `tools/validate_fusha_standalone_parse.py`: self-test and output validator.
- `fusha/lexicon/fusha-lemmas.jsonl`: small authored seed lexicon.
- `qamus/examples/standalone_fusha_parser_mvp.fixtures.jsonl`: generated fixture outputs.
- `docs/parser/index.html`: static JSON preview for qg segments and hover preview rows.

## Mode Boundaries

### Mode A: Qamus/RH-LIVE

Use this parser as a candidate generator and validator aid only. It can help produce qg role segments and catch host-only clitic hovers. It does not replace source-address, sarf, nahw, owner, scholar/iʿrāb, public-boundary, source/runtime, or DOM readback gates.

### Mode B: Learner Tutoring

Use the output to teach visible token pieces: clitics, article, preposition, verb prefix, stem, subject pronoun, object pronoun, derivative prefix, and plural suffix. The hover preview prefers segment contribution glosses so a token like `بالكتاب` does not collapse to a host-only "book" gloss.

### Mode C: Standalone Typing

The parser preserves raw input, emits candidates, keeps ambiguity, and never fabricates Qur'an/WBW locs. Arbitrary text cannot become RH-LIVE certified from this output alone.

## Regression Coverage

The validator currently covers:

- `وما`: one written token, wāw + function-sensitive `ما`.
- `بالكتاب`: bāʾ + article + host, not host-only.
- `فسيكفيكهم`: fāʾ + future sīn + imperfect prefix + verb stem + stacked object pronouns.
- `فأهلكناهم`: fāʾ + verb host + `نا` subject + `هم` object.
- `يسألك`: imperfect prefix + verb host + object pronoun.
- `مستغفرين`: derivative prefix + participial/adjectival host + plural suffix.
- `إنما` and `لمّا`: function-sensitive particles remain context-gated.

## Current Limits

- The seed lexicon is intentionally tiny.
- Pattern handling is conservative and only pins a few forms needed by the MVP.
- It is not a full arbitrary-text grammar checker.
- It does not consult live Qamus, MCP, QAC, Quran.com, or source photos directly.
- It does not deploy or append any RH-LIVE payloads.

## Validation

Run:

```powershell
python tools\validate_fusha_standalone_parse.py --self-test
python tools\fusha_text_check.py --self-test
python tools\fusha_morphology_lattice.py --self-test
python tools\fusha_governor.py --self-test
python tools\validate_fusha_text_check.py --self-test
python scripts\verify_skill_install.py
git diff --check
```

## Qamus Executor Note

Use this branch as a parser/checker flywheel input. It should help turn repeated RH-LIVE blockers into reusable qg segment candidates, sarf/nahw checks, parser fixtures, and curriculum drills. Do not treat it as live coverage progress and do not append its arbitrary Mode C output directly to production.
