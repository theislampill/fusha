# Procedure — morphology candidate lattice

Build and read a **ranked candidate lattice** for a token without forcing one parse. This is the sarf entry point to the
P2/P2b checker engine. Source of truth: [`tools/fusha_morphology_lattice.py`](../../tools/fusha_morphology_lattice.py) +
[`qamus/schemas/morphology-candidate-lattice.schema.json`](../../qamus/schemas/morphology-candidate-lattice.schema.json).

## Input
A token surface (with diacritics if available), its `segment_candidates` (the clitic peel from
[`tools/fusha_text_check.py`](../../tools/fusha_text_check.py) `segment_candidates`), whether it is voweled, and whether it is
source-addressed.

## Checks (in order)
1. **Consume, never rebuild.** Use the existing `segment_candidates`; set each morphology candidate's `segment_candidate_ref` to the
   integer index of the segmentation it assumes. Do not invent a segmentation.
2. **Enumerate competing readings, then rank.** For each segmentation, derive the plausible POS reading(s) (a bare unvoweled content
   stem is genuinely noun-or-verb — keep both). Score each (voweling and a multi-letter proclitic raise the score; a lone
   single-letter peel lowers it — it is almost always a radical). Assign `rank` by descending `score`. **`score` and `rank` are two
   distinct fields; never emit a boolean `correct`.**
3. **Class the evidence.** Set `evidence_class` from the closed set (`voweled_confirmable` / `source_addressed_confirmable` /
   `unvoweled_competing` / `homograph_split` / `weak_root_gated` / `component_only`).
4. **Gate.** An `unvoweled_competing`/`homograph_split` candidate is never `auto_safe`; arbitrary/corpus tokens are never `auto_safe`.
5. **Blank beats wrong.** Leave `root`/`pattern`/`lemma` null when you cannot certify them; never fabricate from resemblance. Leave an
   unresolved feature unset with an `ambiguity_reason`, never an error.

## Evidence ladder (for promoting a candidate to the chosen reading)
Qamus source entry → QAC root/POS (internal) → a confirmed visible ending (voweled / source-addressed) → only then a heuristic rank.
A heuristic rank alone never certifies `rank == 1` for a scripture-facing hover.

## Output
The lattice container `{token_ref, candidates[], top_rank, n_candidates, all_unvoweled_kept:true}`. A token with `>1` candidate stays
`pending` / `surface_only|candidate` with a closed blocker (`root_exists_form_unresolved`, `multi_sense_root`,
`hamza_sensitive_homograph`, `derived_form_needs_review`, `context_sensitive_needs_nahw`, `source_evidence_needed`).

## Forbidden
A boolean `correct`/`is_correct`; a single forced parse for an unvoweled token; a fabricated root/pattern/lemma; a
`segment_candidate_ref` that does not index a real row; an `auto_safe` unvoweled/homograph candidate; a source/provenance/path leak in
`ambiguity_reason`.

## Test
`python tools/fusha_morphology_lattice.py --self-test` (the engine) + `sarf/evals/morphology-candidate-lattice.jsonl` (the skill cases),
checked by `tools/validate_sarf_nahw_skill_backprop.py`.
