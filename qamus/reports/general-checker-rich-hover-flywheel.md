# General Fusha grammar-checker ⇄ rich-hover candidate flywheel

Status: **repo-only tooling. Dry-run.** No live Qamus mutation, no production touch, no service restart, no live
coverage claim. Every tool asserts `live_writes == 0`; every candidate is `decision_state: rich_candidate` and is
**never** `rich_certified` and **never** live-applied. This document is the bridge between the new general
(Grammarly-like) Fusha text checker and the existing rich-hover **certification** system — it explains how the
controlled Qurʾān/Qamus gold data drives an open-world checker without ever leaking false certainty.

Built as the P0 + smallest-coherent-P1 slice of the plan packet at
`C:/workspace/ai/in/parserplans/general-fusha-grammar-checker/` (see `020-implementation-order-and-stop-conditions.md`).

## The flywheel (five turns; the engine only ever drives the first three)

1. **Seed.** Source-addressed tokens (exact `S:A:W`) are the certainty seed. `tools/fusha_check.py` (the existing
   deterministic verifier) adjudicates a proposed analysis into a verdict + routable grammar issues.
2. **Generalize.** The same normalization / clitic / segment machinery runs on *arbitrary typed* text via
   `tools/fusha_text_check.py`, but stripped of address certainty: it emits an ambiguity-preserving candidate lattice
   and the 12 NEW general diagnostic classes. It never forces one parse for unvoweled Arabic (deep-research F3/F4) and
   never reaches `auto_safe`.
3. **Propose.** For a source-addressed token, `tools/rich_hover_flywheel.py` emits a reviewable **rich-hover
   candidate** (`qamus/schemas/rich-hover-candidate.schema.json`): a morphosyntax-token-shaped token + the
   `fusha_check` verdict/issues + a gate + a `blocker_status` + a `suggested_next_action`, paired by
   `(quran_loc, wbw_loc)`.
4. **Certify (NOT us).** The candidate is **projected into the existing certification-row shape** and round-trips
   through `tools/validate_rich_hover_certification.py` (`validate_certification`). The owner-gated certification lane
   takes it from `preview_only` / `pending` / `blocked` → two-vote / human-source-review → `rich_certified`. The
   flywheel front-end never certifies and never sets `rich_certified` (the renderer is not owner-authorized for it).
5. **Regress.** Certified gold becomes new regression oracles in `tools/check_regressions.py`, tightening the seed.
   The Qurʾān is the canonical oracle because it is byte-stable, manually-verified gold (F10) — only read, never altered.

```
 source-addressed token ──fusha_check──▶ verdict+issues ──rich_hover_flywheel──▶ rich-hover CANDIDATE
        ▲                                                                              │ to_cert_row()
        │ regression oracle                                                            ▼
  check_regressions ◀────── rich_certified ◀── owner two-vote/cert lane ◀── validate_rich_hover_certification
```

## How each loop edge is realised in this slice

- **Accepted rich-hover candidates → parser fixtures.** The committed candidate fixtures
  (`qamus/examples/rich_hover_flywheel.sample.jsonl`) are generated deterministically from authored source tokens and
  validate on both `validate_rich_hover_candidate.py` and `validate_rich_hover_certification.validate_certification`.
  As real candidates are accepted upstream, the same generator regenerates the fixture — coverage grows, no hand-edits.
- **Parser diagnostics → better candidate packets.** `rich_hover_flywheel.candidate_for()` calls `fusha_check.check_unit`;
  a clean verdict yields a `preview_only` candidate ready for cert review, a `weak_irab_reasoning` verdict yields a
  `pending` candidate routed to scholar/iʿrāb review — the diagnostic IS the gate that decides the candidate's next action.
- **Arbitrary-typing diagnostics → "needs source-addressed confirmation".** `fusha_text_check.py` emits
  `source_address_required_for_certainty` (and, on a source-addressed token, `rich_hover_candidate_available_when_source_addressed`),
  so an arbitrary-text checker session can point the user at the gold path without pretending to certainty.
- **Qamus blocker classes → taxonomy refinements.** The 12 NEW general classes (`011`) are the arbitrary-text
  generalization of the 12 existing source-addressed classes; single-letter clitic ambiguity (ه/ك/ي) routes to
  `possible_attached_pronoun` + `gate ≥ two_vote_required` or PENDING(`context_sensitive_needs_nahw`), never a guess.
- **Colour / parse-key decisions → supervised examples.** Candidate qg classes bind to the committed
  `qamus-grammar-v1` palette enum (in `qamus/schemas/morphosyntax-token.schema.json`); no class is ever invented.

## The three modes

| Mode | Tool path | Certainty ceiling | Gate posture |
|---|---|---|---|
| `source_addressed` | `fusha_text_check.py` → `fusha_check.check_unit`; `rich_hover_flywheel.py` | resolves exact `S:A:W`; may produce a real verdict | per `fusha_check` verdict |
| `corpus_backed` | `fusha_text_check.py` (Nawawī40 present; Ṣaḥīḥayn **plan-only**) | corpus IDs, partial | floor `two_vote_required` |
| `arbitrary_typing` | `fusha_text_check.py` | **none** — `surface_only`/`candidate`/`unknown`, `decision_status=pending` | **never** `auto_safe` |

## Boundary / safety (enforced by the validators)

- Published gloss invariant: every public field is `{src:qamus, kind:authored, lang:en}`, `external_source_names_public:false`.
- No external source names / translation brands / local paths in any public field (scanned with `fusha_check.LEAK_RE`).
- No copied external gloss/translation text — authored from scratch; PENDING (with an exact `blocker_status`) beats a wrong gloss.
- No false certainty: arbitrary text never reaches `auto_safe`; unvoweled tokens keep their candidate lattice (never one forced parse).
- Dry-run: `live_writes == 0`; `may_apply_live=false`; segments concatenate to the surface exactly; Qurʾān text byte-for-byte unaltered.

## Smoke A / Smoke B

- **Smoke A (baseline, before any mutation):** `python tools/check_regressions.py` → exit 0, "ALL REGRESSION CHECKS PASS"
  (the prior RH-LIVE manifest FAILs were fixed upstream; the baseline is fully green).
- **Smoke B (after this slice):** `python tools/check_regressions.py` → exit 0 with **6 new gates green** and the
  Smoke A green-gate count preserved (zero regression). The 6 new gates: general text-checker self-test; its validator
  self-test; its fixture validation; the rich-hover flywheel self-test (cert round-trip); the candidate validator
  self-test; the candidate fixture validation.

## What shipped (this slice)

- Schemas: `qamus/schemas/fusha-text-check.schema.json`, `qamus/schemas/rich-hover-candidate.schema.json`.
- Tools: `tools/fusha_text_check.py`, `tools/validate_fusha_text_check.py`, `tools/rich_hover_flywheel.py`,
  `tools/validate_rich_hover_candidate.py`.
- Fixtures: `qamus/examples/fusha_text_check.sample.jsonl` (+ `.meta.json`),
  `qamus/examples/rich_hover_flywheel.sample.jsonl` (+ `.meta.json`).
- Routing: `curriculum/tutor-runtime-routing.md` extended with the 12 general diagnostic classes.
- Regression: `tools/check_regressions.py` extended with the 6 gates above.

## Deferred (NOT in this slice)

- P2: leak-detector source-of-truth consolidation; cross-builder candidate conflict resolution; deeper morphology /
  governor / dependency lattices; the suggestion/correction engine (edit-level retain/reject + NMS, F6); qg/parse-key
  binding depth.
- P3: corpus_backed ingest beyond Nawawī40 fixtures; two-vote consensus storage (link to existing
  `phase4-two-vote-*` schemas; build no new ledger).
- P4: any renderer upgrade enabling `rich_certified` for live display (owner-gated); live apply/rebuild; Ṣaḥīḥayn
  corpus ingest (plan-only this thread); diacritization-as-certainty / supervised-model correction.

## Note for the Qamus rollout thread

Fusha has advanced beyond source-addressed parser checks toward a general Fusha/Classical Arabic grammar-checking
engine. No live Qamus state was changed. Qamus rich-hover remains the gold-data flywheel: accepted rich-hover/color
decisions can become parser fixtures, and parser diagnostics can produce better reviewable rich-hover candidates. Treat
this as checker/tooling progress and review/authoring acceleration, not live coverage progress.

## Note for a future general-editor thread

The current checker is not yet full Arabic Grammarly. It now has a planned three-mode architecture and the first
arbitrary-typing prototype: original-text preservation, normalization tracking, tokenization, clitic-segmentation
candidates, ambiguity-preserving diagnostics, safe gates, and source-addressed handoff where available. It also has a
rich-hover/color flywheel path so Qamus accepted decisions become parser fixtures. Next work should deepen morphology,
syntax/governor reasoning, suggestions, corpus-backed mode, and editor-service integration.
