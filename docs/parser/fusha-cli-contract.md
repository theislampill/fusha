# Fusha Local CLI Contract

This contract is the first machine interface for Fusha parser/checker work.
It is a local CLI and JSON/JSONL contract, not an HTTP endpoint.

The goal is to let Qamus workers and future Codex threads call a stable surface
instead of inferring behavior from internal fixture files.

## Claim Boundary

Current status: not live Qamus, not arbitrary-text, not a trained dependency
parser, and not equivalent to CAMeL Tools, MADAMIRA, or Stanza.

The CLI may produce source-clean candidates, blockers, private traces, and
validator results for repo fixtures. It must not claim live coverage progress.

## Commands

### `fusha analyze-token`

Prototype equivalent:

```bash
python tools/fusha_analyze_token.py --input token.json
```

Input: one visible token or qword row with a source address.

Output:

- normalized surface facts
- morphology candidates
- sarf gates
- nahw/i'rab gates when available
- blockers if the row is not safe to project

### `fusha analyze-card`

Prototype equivalent:

```bash
python tools/fusha_analyze_card.py --input rows.jsonl --out analysis.jsonl
```

Input: every visible qword row on one cited Qamus example card.

Output: one analysis row per visible qword. A card is not complete unless every
visible qword is accounted as projected, already-live/no-op, or exact packet.

### `fusha project-hover`

Prototype equivalent:

```bash
python tools/fusha_project_hover.py \
  --source-rows rows.jsonl \
  --analysis analysis.jsonl \
  --out public-hover-projection.jsonl
```

Input: source rows and analysis rows.

Output: public-safe hover candidates with:

- `src=qamus`
- `kind=authored`
- `lang=en`
- segment surfaces that concatenate to the visible token
- qamus-grammar-v1 class names only
- no external source labels, paths, MCP labels, or process prose

### `fusha validate-mode-a`

Prototype equivalent:

```bash
python tools/validate_qamus_mode_a_adoption.py --self-test
python tools/validate_qamustyping3_acceptance.py --self-test
```

Input: Mode A fixture bundle and qamustyping3 implementation ledger.

Output: stage status, source rows, all-qword fixture rows, external-source
policy, public/private projection checks, and claim-boundary checks.

## Stable Row Shape

Every row entering the contract should preserve both directions of the edge
graph:

- entry id or public entry key
- source key
- sense/card index
- visible card text
- selected or all-qword visible surface
- display-local loc when present
- canonical Qur'an/WBW loc or crosswalk packet
- current rich/no-op/blocker state
- public projection target
- private trace target
- flywheel target

Rows that lack a forward and reverse path must not be silently projected. Route
them to source-crosswalk or graph repair.

## Human Review Packets

Owner and scholar packets are not vague backlog labels. A packet requires:

- exact row/card address
- visible surface
- source edge status
- question to answer
- internal evidence references
- allowed decisions
- validator to rerun after decision
- flywheel target for accepted or rejected decisions

Accepted decisions become fixtures or validator cases. Rejected decisions update
the blocker and next action.
