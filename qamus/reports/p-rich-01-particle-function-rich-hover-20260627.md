# P-RICH-01 Particle Function Rich-Hover Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW build artifact, service, mirror, or hover decision ledger was changed.

## Scope

P-RICH-01 starts the post-VN rich-hover layer with high-impact particle and function-token cases from the completed particle dogfood tranches.

Sample artifacts:

- `qamus/examples/rich_hover_p_rich_01_particle_function.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_01_particle_function_evidence.sample.jsonl`

The tranche is deliberately small and validator-facing. It proves that the RICH-00 morphosyntax contract can represent whole-token function particles, not only clitic-plus-host rows.

## Contract Change

The morphosyntax token schema and validator now allow whole-token function segment roles:

- `particle`
- `preposition`
- `conjunction_particle`
- `negative_particle`
- `exceptive_particle`
- `conditional_particle`
- `subordinating_particle`
- `interrogative_particle`
- `time_adverb`
- `resumption_particle`
- `result_particle`
- `accusative_particle`
- `relative_particle`
- `purpose_particle`

These roles map to existing public-safe display classes such as `qg-preposition`, `qg-particle`, `qg-negative`, `qg-exception`, `qg-result`, and `qg-relative`.

This is not a live renderer claim. It is a metadata contract for future renderer support and admin review.

## Rows

| Loc | Surface | State | Function class | Parse key | Gate |
|---|---|---|---|---|---|
| `2:4:8` | `مِن` | `rich_candidate` | preposition | `P:MIN` | `two_vote_required` |
| `2:9:5` | `وَمَا` | `rich_candidate` | conjunction + negative mā | `CONJ+MA:NEG` | `two_vote_required` |
| `2:9:7` | `إِلَّآ` | `pending` | exception | `EXP:ILLA` | `two_vote_required` |
| `2:30:1` | `وَإِذْ` | `rich_candidate` | conjunction + temporal particle | `CONJ+T:IDH` | `two_vote_required` |
| `2:19:1` | `أَوْ` | `rich_candidate` | disjunction | `CONJ:AW` | `two_vote_required` |
| `2:210:1` | `هَلْ` | `pending` | interrogative | `INTG:HAL` | `two_vote_required` |
| `2:6:1` | `إِنَّ` | `rich_candidate` | accusative particle | `ACC:INNA` | `two_vote_required` |
| `112:3:1` | `لَمْ` | `rich_candidate` | jussive-governing negation | `NEG:LAM:JUSS` | `two_vote_required` |
| `72:12:9` | `وَلَن` | `rich_candidate` | conjunction + subjunctive-governing negation | `CONJ+NEG:LAN:SUBJ` | `two_vote_required` |
| `68:8:1` | `فَلَا` | `pending` | fa + lā requiring prohibition/negation review | `FA+LA:NEG_OR_PRO` | `two_vote_required` |

No row is `rich_certified`. The tranche is intentionally conservative: function particles are grammar-sensitive, so readable English alone is not enough.

## Public Boundary

All candidate records keep:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The evidence sidecar uses internal labels only. It does not authorize public exposure of source names, adapter names, screenshots, MCP names, or raw evidence.

## Blockers And Pending Reasons

Rows left pending:

- `إِلَّآ`: exception structure needs mustathnā review.
- `هَلْ`: interrogative frame needs context review.
- `فَلَا`: `لا` function and following-verb mood need review.

These are not failures. They are correct rich-hover blockers: the learner view cannot safely claim the hidden grammar state until the nahw gate is satisfied.

## Flywheel Impact

Sarf updates: no change. The tranche is primarily ḥarf/function-token work, and the current sarf skill already routes particles out of root/form inference.

Nahw updates: no change. The needed doctrine is already present in:

- `nahw/procedures/particle-function-decision.md`
- `nahw/procedures/ma-function-decision.md`
- `nahw/procedures/function-token-hover-review.md`
- `nahw/procedures/governing-particle-mood-review.md`
- `nahw/procedures/exception-and-vocative-review.md`

Curriculum updates: no change. RICH-00 already added the parse-key/color contract; this tranche instantiates it with particle rows.

Drills/evals/regressions: no new drill yet. The repeated learner error is already covered by particle dogfood drills and evals; this tranche contributes a rich metadata sample that future renderer/admin work can consume.

Production-bug lessons: no new lesson. The repeated defect classes here are already represented by particle dogfood lesson samples; this tranche is the rich-display form of those lessons.

Renderer requirements: extended. Whole-token function particles now have display roles and labels so the renderer can color and label a function token without pretending it is a lexical stem.

Future tranche routing: continue P-RICH over the remaining high-impact particles, then use VN-RICH calibration for verbs/nouns whose current English gloss is readable but cannot yet teach segment contribution.

## Acceptance

Required checks for this tranche:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_01_particle_function.sample.jsonl
python -c "import json, pathlib; [json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_p_rich_01_particle_function_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]"
```

The broader repo gates remain required before commit.
