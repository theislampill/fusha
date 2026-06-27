# P-RICH-02 Particle Collision And Composite Function Tranche

Status: repo-only rich-hover metadata tranche. No live Qamus data, WBW artifact, service, mirror, renderer, or hover ledger was changed.

## Scope

P-RICH-02 follows P-RICH-01 by targeting high-risk particle/function families where the English hover may be readable while the hidden grammar state is not learner-safe:

- `إِذًا` versus `إِذَا`
- `ثُمَّ` sequence scope
- `مَاذَا` blended `ما` function
- `لِّكَيْلَا` purpose + subordinator + negation
- `أَنَا` independent pronoun versus shadda-bearing subordinator families
- `لِمَا` lām + mā function/attachment
- `لَّمَّا` construction collision
- `فَإِنَّمَا` fa + innamā restrictive compound

Sample artifacts:

- `qamus/examples/rich_hover_p_rich_02_particle_collision.sample.jsonl`
- `qamus/examples/rich_hover_p_rich_02_particle_collision_evidence.sample.jsonl`

## Rows

| Loc | Surface | State | Rich issue | Parse key | Next gate |
|---|---|---|---|---|---|
| `2:145:30` | `إِذًۭا` | `pending` | result/inferential vs temporal-condition collision | `RES:IDHAN` | no auto; clause relation review |
| `2:28:7` | `ثُمَّ` | `rich_candidate` | sequence conjunction scope | `CONJ:THUMMA` | two-vote when scope matters |
| `2:26:24` | `مَاذَآ` | `pending` | blended mā-dhā fallback | `INTG:MADHA:PENDING` | classify mā + clause frame |
| `3:153:14` | `لِّكَيْلَا` | `token_only_override` | composite purpose/subordinator/negation | `LAM:PURP+SUB:KAY+NEG:LA` | exact-address mood/scope review |
| `2:258:21` | `أَنَا۠` | `pending` | independent pronoun vs subordinator collision | `PRON:1S:INDEP` | no auto; strict surface and clause review |
| `2:213:37` | `لِمَا` | `pending` | lām relation plus mā function | `P:LI+MA:FUNC_PENDING` | exact-address mā + attachment review |
| `86:4:4` | `لَّمَّا` | `pending` | lammā function construction collision | `PART:LAMMA:FUNC_PENDING` | exact construction review |
| `3:47:19` | `فَإِنَّمَا` | `pending` | fa + innamā compound and restriction scope | `FA+INNA+MA:RESTRICTIVE_PENDING` | restriction-scope review |

No row is `rich_certified`. This tranche is about making the hidden state explicit enough to block false certainty.

## State Transitions

- `populated_uncertified -> pending`: `إِذًۭا`, `مَاذَآ`, `أَنَا۠`, `لِمَا`, `لَّمَّا`, `فَإِنَّمَا`.
- `populated_uncertified -> rich_candidate`: `ثُمَّ`, with sequence scope still gated.
- `token_only_override -> token_only_override rich metadata`: `لِّكَيْلَا`, with exact-address review preserved.

The important movement is not row count. The movement is that each readable hover now has a reasoned rich-state lane, explicit blocker, and segment contribution.

## Public Boundary

Every row keeps:

- `src=qamus`
- `kind=authored`
- `lang=en`
- `public_boundary.external_source_names_public=false`

The sidecar is internal-only and does not authorize public source labels. Public hover output remains authored Qamus wording only.

## Flywheel Impact

Sarf updates: no repo change. The current sarf procedures already contain the strict-surface and homograph guard needed here, especially `sarf/procedures/homograph-risk.md` and `sarf/procedures/clitic-and-host-morphology.md`.

Nahw updates: no repo change. The concepts are already represented by:

- `nahw/procedures/particle-function-decision.md`
- `nahw/procedures/ma-function-decision.md`
- `nahw/procedures/conditionals.md`
- `nahw/procedures/governing-particle-mood-review.md`
- `nahw/procedures/exception-and-vocative-review.md`
- `nahw/references/particle-functions.md`

Curriculum updates: no new prose needed in this tranche. The RICH-00 contract plus existing particle drills already teach the doctrine; P-RICH-02 supplies concrete rich metadata examples for renderer/admin consumers.

Drills/evals/regressions: no new drill added. Existing fixtures already cover the repeated classes: `لِمَا`/`لَمَّا`, `إِذَا`/`إِذًا`, `مَاذَا`, `لِكَيْلَا`, and `أَنَا`/`أَنَّا`.

Production-bug lessons: no new lesson added. The relevant lessons already exist in `dogfood_particle_remaining67_production_bug_lesson.sample.jsonl` and `dogfood_vn09_production_bug_lesson.sample.jsonl`.

Renderer requirements: extended by example. The renderer must support whole-token function particles and composite particles without splitting the visible Arabic word or turning component evidence into whole-token certification.

Future tranche routing: P-RICH can continue with prefixed `أَفَلَا`, `بِأَنَّ`, `وَإِن`, `أَنْ`, `أَنَّ`, and remaining composite particles. VN-RICH should then use the same pending-first discipline for verbs/nouns with readable but non-teaching hovers.

## Acceptance

Required checks:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/rich_hover_p_rich_02_particle_collision.sample.jsonl
python -c "import json, pathlib; rows=[json.loads(line) for line in pathlib.Path('qamus/examples/rich_hover_p_rich_02_particle_collision_evidence.sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]; assert rows and all(not r.get('public_exposable') for r in rows)"
```

Broader repo gates remain required before commit.
