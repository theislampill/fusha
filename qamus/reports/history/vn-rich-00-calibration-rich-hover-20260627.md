# VN-RICH-00 Calibration Rich-Hover Tranche

Status: repo-only rich-hover metadata calibration. No live Qamus data, WBW artifact, service, mirror, renderer, or hover ledger was changed.

## Scope

VN-RICH-00 converts a small set of previously dogfooded verb/noun hard cases into rich-hover metadata shape before repeating broad VN ranges. The tranche deliberately samples different failure classes:

- verb-object suffix omission: `يَسْأَلُكَ`
- lām/function plus finite host plus suffix: `لَيُزْلِقُونَكَ`
- bā' plus governed participial host plus suffix: `بِمُزَحْزِحِهِۦ`
- finite verb dictionary-gloss leakage: `تَذْهَلُ`
- passive voice plus connector: `وَأُحِلَّتْ`
- conjunction plus imperative host: `وَاضْمُمْ`

Sample artifacts:

- `qamus/examples/rich_hover_vn_rich_00_calibration.sample.jsonl`
- `qamus/examples/rich_hover_vn_rich_00_calibration_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `33:63:1` | `يَسْأَلُكَ` | `token_only_override` | imperfect prefix + stem + `كَ` object | `V:I:IMPF:ACT:3MS+OBJ.2MS` | owner-gated repair preview before live apply |
| `68:51:5` | `لَيُزْلِقُونَكَ` | `pending` | lām/function + finite host + `كَ` object | `PART+V:IV:IMPF:ACT:3MP+OBJ.2MS:PENDING` | lām/function and suffix two-vote |
| `2:96:17` | `بِمُزَحْزِحِهِۦ` | `pending` | bā' + governed host + suffix | `P:BI+N:PTCP:GEN+POSS.3MS:PENDING` | PP attachment and referent review |
| `22:2:3` | `تَذْهَلُ` | `pending` | finite imperfect verb, not dictionary infinitive | `V:I:IMPF:ACT:3FS:PENDING` | contextual verb wording review |
| `22:30:11` | `وَأُحِلَّتْ` | `rich_candidate` | connector plus passive perfect verb | `CONJ+V:IV:PERF:PASS:3FS` | passive/form two-vote before propagation |
| `20:22:1` | `وَاضْمُمْ` | `pending` | connector plus imperative host | `CONJ+V:I:IMPV:2MS:PENDING` | component-only imperative review |

No row is `rich_certified`. Readable English or existing token-decision text is not enough for certification without sarf, nahw, learner, and source/two-vote gates.

## State Transitions

- `known_defect -> token_only_override metadata`: `33:63:1`.
- `component_only_evidence -> pending rich metadata`: `68:51:5`, `2:96:17`, `20:22:1`.
- `finite_verb_dictionary_gloss_leakage -> pending rich metadata`: `22:2:3`.
- `resolved token decision -> rich_candidate metadata`: `22:30:11`, still without live claim.

The movement is from old dogfood classifications into exact segment roles, parse-key summaries, learner explanations, and fail-closed next gates.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The sidecar is internal-only and does not authorize public source labels. Public hover output remains authored Qamus wording only.

## Flywheel Impact

Sarf updates: no repo change in this tranche. These cases reuse procedures and fixtures already strengthened by VN dogfood:

- `sarf/procedures/clitic-and-host-morphology.md`
- `sarf/procedures/verb-form-and-mood-review.md`
- `sarf/evals/false-clitic-split-eval.jsonl`

Nahw updates: no repo change in this tranche. These cases reuse:

- `nahw/procedures/pronoun-attachment.md`
- `nahw/procedures/preposition-pronoun.md`
- `nahw/procedures/pp-attachment-review.md`
- `nahw/procedures/token-only-overrides.md`
- `nahw/evals/suffix-pronoun-eval.jsonl`
- `nahw/evals/particle-function-eval.jsonl`

Curriculum updates: no new prose needed. The committed VN synthesis and hover composition curriculum already teach that a rich hover must explain visible pieces rather than only a readable English string.

Drills/evals/regressions: no new fixture needed. The selected rows are already represented by VN dogfood lesson samples and the suffix/clitic/particle fixtures; this tranche tests that those lessons can be rendered as rich metadata.

Production-bug lessons: no new lesson added. The repeated classes are already `verb_object_suffix_omitted`, `component_only_candidate_no_whole_token_propagation`, and `finite_verb_dictionary_gloss_leakage`.

Renderer requirements: reinforced by example. The live renderer must keep each written token atomic while exposing segment rows/classes for prefix, host, and suffix contributions.

Future tranche routing: VN-RICH can now continue by defect-class packets or the completed VN tranche order, using this calibration as the sample shape.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_vn_rich_00_calibration.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_vn_rich_00_calibration_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
