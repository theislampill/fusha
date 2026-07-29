# The two-surface contract — rich-at-rest + rich-hover, one artifact

Status: adopted 2026-07-29 (canonical architecture doc, precedence tier 4).
This doc **consolidates by reference** — the binding texts are:

- `docs/qamus/particle-projection-contract.md` — the contract itself
  (executable twin: `tools/validate_particle_projection_parity.py`; where
  prose and validator disagree, "the validator is the bug and this doc is
  the spec").
- `docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md` — `norm@1`, what a
  correct rich-hover row looks like (DRAFT, authored, not yet enforced).
- `docs/qamus/particle-rich-hover-templates.md` — the learner-language
  wording templates T1–T5.
- `docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`
  — how the projection crosses to the renderer
  (`qamus.website_projection_payload.v1`; executable twin
  `tools/validate_website_payload.py`).

Nothing here overrides those documents; this page states the relationship
once so no future doc restates it divergently.

## 1. The one-artifact rule

From the particle projection contract §1, verbatim:

> A particle occurrence teaches on exactly two surfaces. **Both are
> projections of the SAME canonical typed-fact artifact for that occurrence;
> neither may carry a fact the artifact does not carry.**

Corollaries (contract §2):

- **Appearance parity.** Every appearance of one canonical occurrence has the
  SAME projection hash on every page — "One occurrence, one analysis,
  everywhere." Permitted per-page variation is a closed 4-key presentation
  whitelist: `selected_highlight`, `entry_relationship`, `focus`,
  `navigation`.
- **Sharing is per-occurrence, never per-surface.** Two identical surfaces in
  one āyah are distinct artifacts (the PROOF-P مَا 2:284:2 vs 2:284:10 lesson).
- The renderer treats `projection_hash` as a cache key, never mutates
  projection fields, and reports mismatches back — it never picks a winner
  (handoff contract §5; the website agent never authors linguistic payloads,
  Fusha never edits renderer files).

## 2. The two surfaces

**Rich-at-rest** (contract §1.1): stable colour class as a function of the
semantic class (never of the page), visible host boundary, attached pronoun
as its own segment. "Rich-at-rest carries NO analysis prose. It is colour,
boundary, and segmentation only — the invitation to hover, not the lesson."

**Rich-hover — the teaching plane** (contract §1.2): the 13 ordered items
(component, contextual gloss, identity, function, ṣarf note, naḥw note,
governor/governed, scope, attachment, alternatives, reason, unresolved state,
entry link), in learner-register English only (no Arabic iʿrāb formulas —
contract §1.4, `norm@1` N-LANG); rootlessness is taught, never blank
(§1.3, `rootless_pedagogy`); unresolved is honest and neutral-coloured,
never colour-guessed.

## 3. Status boundaries

- The rich letter-level projection is the **target** quality (owner decision
  D-1); coarse `PFX/STEM/SUF` rows are legacy-valid only, superseded as a
  target (`docs/INDEX.md` §3).
- Everything two-surface in this repo is **candidate-mode**:
  `LIVE_QAMUS_MUTATION: NOT_AUTHORIZED`; committed payloads are samples and
  proofs, and the p007 production-difference table is an owner-gated
  candidate upgrade set, NOT DEPLOYED.
- `WEBSITE_FRONTEND: OWNED_BY_THE_SEPARATE_WEBSITE_AGENT` — the payload
  files and their validator are the entire interface.

---
Verified against: commit 637d7da (origin/main, 2026-07-29). Artifacts:
`docs/qamus/particle-projection-contract.md`,
`docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md`,
`docs/qamus/particle-rich-hover-templates.md`,
`docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`,
`tools/validate_particle_projection_parity.py`,
`tools/validate_website_payload.py`,
`qamus/examples/particle_projection_parity.sample.json`,
`qamus/examples/p007-li-pilot/{projections.jsonl,parity-report.json,production-difference.json}`;
`tools/check_regressions.py` ALL REGRESSION CHECKS PASS.
