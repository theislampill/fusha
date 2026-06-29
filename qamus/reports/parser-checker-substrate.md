# Fusha parser/checker substrate — contract + integration

The first source-addressed Classical/Qurʾānic Arabic **parser/checker** layer for Fusha. It turns the existing
sarf/nahw + morphosyntax-token + source-address-graph assets into a deterministic **verifier**: given a *proposed
analysis* (a claim from an untrusted model/tutor), it returns grammar **issues** + a per-claim **verdict** + a
machine **route**. It never writes live data, never copies external gloss text, and never guesses about
unaddressed text. Full design + roadmap: the Phase-0 plan packet at `C:\workspace\ai\in\parserplans\` (start with
`000-parser-northstar.md`).

## What shipped (P0 + the smallest coherent P1 slice)
| Artifact | Role |
|---|---|
| `qamus/schemas/parser-check-ir.schema.json` | the FPC-IR **CheckUnit** (SourceUnit→Segment→Token→Claim→Issue→Verdict) |
| `qamus/schemas/grammar-issue.schema.json` | the first-class, source-addressed, routable **grammar Issue** (12 classes) |
| `tools/fusha_check.py` | the **checker**: resolver + 12 detectors + verdict pipeline + CLI + `--self-test` + `--emit-fixture` |
| `tools/validate_parser_check.py` | the **validator**: schema + the 6 FAIL conditions + `--self-test` |
| `qamus/examples/parser_check_regression.sample.jsonl` (+`.meta.json`) | the regression fixture (7 required examples + all 12 classes) |
| `curriculum/tutor-runtime-routing.md` (extended) | parser diagnostics → learner-facing routes |
| this report | the contract + sarf/nahw integration points |
Registered in `tools/check_regressions.py` (3 gate assertions). Reuses `tools/normalize_ar.py`,
`tools/validate_linguistic_decisions.py` (mini schema validator + GP0 `required_gate`), and the source-address
indexes under `qamus/indexes/current/`. Stdlib only; dry-run (`live_writes == 0`).

## The IR in one screen (see `parserplans/000` §3)
`CheckUnit = {source_unit, segments[], tokens[], claims[], issues[], verdicts[], public_boundary, summary}`.
- **SourceUnit** anchors to the source-address graph; an address that does not resolve ⇒ `scope=out_of_scope`.
- **Token** = a `morphosyntax-token` record (`qamus/schemas/morphosyntax-token.schema.json`): `loc`, `surface`
  (whitespace-free), `segments[]` (clitic/host/suffix), `sarf{}`, `nahw{}`, `hover_contract`, public boundary.
- **Claim** = a proposed analysis: `{target, claim_type, claimed_value, claimed_reasoning, claimed_gate, proposer}`.
- **Issue** = `{issue_id (stable, namespaced), issue_class, severity, target_address (req), token_or_card_edge
  (req), trigger_address, gate, route_to (req), explanation (source-clean), public_boundary}`.
- **Verdict** ∈ `{grounded, pending, contradicted, out_of_scope, needs_two_vote, needs_human_review,
  unsafe_reasoning}` — `pending` is preferred over a wrong resolution; `out_of_scope` is the safe arbitrary-text
  boundary; `unsafe_reasoning` is "right answer, wrong/weak iʿrāb reason → never ship".

## The 12 issue classes (deterministic, source-clean detectors)
`hidden_clitic_or_proclitic`, `host_only_preposition_hover`, `ma_function_unresolved_or_wrong`,
`phrase_translation_used_as_token_hover`, `suffix_pronoun_missing`, `passive_voice_hidden`,
`dual_or_plural_suffix_hidden`, `derivative_or_participle_prefix_hidden`, `weak_irab_reasoning`,
`graph_edge_missing`, `display_local_canonical_crosswalk_missing`, `source_clean_boundary_violation`.
Detection is a structural predicate over the token record + claim + graph (no external text). Routing for each
class is in `tools/fusha_check.py:ISSUE_ROUTE` (every target procedure exists on disk).

## Gate-vocabulary reconciliation (a real finding)
The repo carries three gate vocabularies (GP0 4-tier; decision-linkage 8-value; parse-key 5-value). The checker
canonicalizes on the **GP0 4-tier** and aliases the others (`tools/fusha_check.py:GATE_ALIAS`):
`token_review`/`auto_safe_after_preview`→`auto_safe`; `human_review_required`/`owner_review_required`→
`human_source_review_required`; `never_auto`→`never_auto_resolve`; `unknown`→`two_vote_required`. The required gate
is computed from `grammar_triggers` via the reused GP0 resolver (`validate_linguistic_decisions.required_gate`).

## sarf / nahw integration points
The checker is the deterministic verifier; the sarf/nahw skills + rule tables are the evidence it consumes.
- **sarf** (`sarf/SKILL.md` + `sarf/rules/*.json` + `sarf/evals/*`): supplies the morphology the structural
  detectors read on the token record — `sarf.voice` (→ `passive_voice_hidden`), `sarf.noun_number`/`number`
  (→ `dual_or_plural_suffix_hidden`), `sarf.derivative_type` (→ `derivative_or_participle_prefix_hidden`), and the
  `segments[].role` clitic/host/suffix decomposition (→ `hidden_clitic_or_proclitic` / `host_only_preposition_hover`
  / `suffix_pronoun_missing`). The standing order "PENDING beats wrong; `norm()` never certifies" is honored:
  unresolved morphology yields `pending`/`contradicted`, never a guess. Deepening lane: `parserplans/005`.
- **nahw** (`nahw/SKILL.md` + `nahw/evals/grammar-decision-gates.json` + `tools/grade_grammar_reasoning.py`):
  supplies the gate ladder + the two-vote/reasoning rule. `weak_irab_reasoning` operationalizes "two-fold
  correctness" (governor-justification, `parserplans/000` §6): an iʿrāb/case-mood claim that is right-valued but
  unjustified (no governor / no reasoning) or marked `auto_safe` when its trigger requires `two_vote_required`
  fires the issue and yields `unsafe_reasoning`. `ma_function_unresolved_or_wrong` requires the particle's function
  be resolved (negation/relative/interrogative/preventive). Deepening lanes: `parserplans/006`, `007`.

## Public boundary (every artifact)
Public output is exactly `{src:'qamus',kind:'authored',lang:'en'}`. A leak tripwire (`fusha_check.LEAK_RE`) scans
public-facing fields for `qac|quran.com|tanzil|tafsir|mcp|informed_by|/srv/|…`; it is an accidental-paste tripwire,
**not** proof of independence (that rests on the authoring procedure). Qurʾānic surfaces are verbatim; the
fixture uses real `S:A:W` addresses verified present in `quran-usage-spine-full.jsonl`; no external gloss/
translation text is stored. The substrate is **tooling**, not a live-coverage change — see
`parserplans/017-boundary-do-not-touch-live-qamus.md`.

## RH-LIVE candidate adapter rule
When the checker scores a proposed RH-LIVE rich-hover row, the `hover_gloss` claim must represent the learner-visible
public hover text that would actually ship, not a private reviewer summary and not only the main English title. The
row must still preserve `token_contribution_gloss` separately from `contextual_phrase_gloss`. If those differ, the
candidate must carry the adjacent-context fields (`adjacent_context_required`, `adjacent_context_locs`, and the
appropriate `context_*_source`) so a phrase gloss such as “the people ask you” cannot hide that the token itself only
contributes “ask you.” Segment rows, morphline facts, and learner explanation are part of the visible teaching surface
and should be represented in the `Token`/`hover_contract` so clitics, suffixes, articles, roots, passive/active voice,
dual/plural endings, and derivative shapes cannot be silently dropped. Any emitted issue or non-`grounded` verdict
blocks live rollout; `live_writes` must remain `0`.

## Run it
```
python3 tools/fusha_check.py --self-test            # 7 regression examples + 12 classes + out_of_scope + dry-run
python3 tools/validate_parser_check.py --self-test  # 6 FAIL conditions reject; good units clean
python3 tools/fusha_check.py --emit-fixture qamus/examples/parser_check_regression.sample.jsonl   # regenerate
python3 tools/fusha_check.py --in <units.jsonl> --out -   # check a batch
```
