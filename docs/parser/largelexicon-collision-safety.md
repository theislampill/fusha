# Largelexicon Collision Safety

Largelexicon increases recall by exposing many more Qamus-authored forms to the
parser. That also increases the collision surface for short Arabic tokens,
especially particles, proper names, and tokens that can be mechanically split
into clitic-looking pieces.

The rule is simple: coverage is not disambiguation. A larger table may add a
candidate, but it does not make that candidate safe for a public hover.

## Required behavior

- Candidate enumeration remains broad.
- The selected preview is suppressed or context-gated when a high-risk candidate
  is only a `bare_match` / weak match or competes with a function-token route.
- `morphology_candidates[0]` is never a deploy signal by itself.
- `safe_for_qamus_executor_autopromote` remains `false` for local arbitrary-text
  CLI output.
- Function-token alternatives route to `pending_context` instead of being
  collapsed into a content-word hover.
- Real clitics remain visible when the morphology identity is stable, e.g.
  bā' + Allah or bā' + article + host.

## Regression bank

Executable fixtures live at:

- `fusha/parser/eval/largelexicon-collision-regressions.jsonl`

They cover:

- `الله` must not project `ال + له`;
- `بالله` must preserve bā' plus Allah without turning Allah into lām + pronoun;
- `من` must not top-rank the verb `مَنَّ` in arbitrary text;
- `إله` must not render as host + object pronoun or a source-certified hover
  without context;
- `إلا` must not project the noun `إِلًّا` where the exception-particle lane is
  required;
- `إنما` and `بالنيات` remain positive controls for particle-cluster and real
  clitic visibility.

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools\validate_largelexicon_parser.py --self-test
python tools\validate_largelexicon_cli_contract.py --self-test
python tools\validate_fusha_standalone_parse.py --self-test
```

## Executor consumption

The Qamus rollout executor may use largelexicon output as a worklist accelerator,
not as a live deployment decision. A row must either carry source-addressed
proof and pass executor validation, or route to an exact packet:

- `sarf_collision_review`;
- `nahw_function_review`;
- `source_crosswalk_packet`;
- `validator_packet`;
- `executor_validation_required`.

This preserves the Project-Xanadu-style architecture: parser candidates are
transclusions of source facts, not orphan copies. If a lemma, function inventory
rule, clitic splitter rule, or source/crosswalk row changes, dependent hover
projections must regenerate or become stale.
