# New-entry proposal lane readiness (closure-2092 Phase 4B)

`tools/build_new_entry_proposals.py` + `tools/validate_new_entry_proposals.py` +
`qamus/schemas/new-entry-proposal.schema.json`.

- Input: `missing_qamus_entry_candidate` (326) after the flattened-root reroute.
- Output: **52 OWNER-GATED review-only** proposals covering 278 tokens (gitignored `out/`). **No live id, no
  live apply, no authored definition** (`definition_draft` blank — the owner authors it). Validator enforces
  `gate=owner`, `proposed_entry_id` = `PROPOSE:*`, and **never** a root that already has an entry (أتي/رأي
  excluded by construction).
- Each proposal: proposed_entry_id, root, headword_candidate, forms_observed, example_locs, occurrences,
  why_existing_insufficient, source_evidence_ids (qac:root), sarf/nahw procedure, public_provenance_clean.
- **Confirms the dr05 recurring families**: سوأ(40), رضو(24), ربب(16), صلو(12), زكو(12), يدي(8), سمو(7),
  كلل(7), صوب(7), بلو(7) — all genuinely absent from the 2,092-entry dataset.
- Gate: wired into `check_regressions`. **NO-GO for autonomous authoring** — owner approval required before any
  entry is created; this repo never creates a live entry.
