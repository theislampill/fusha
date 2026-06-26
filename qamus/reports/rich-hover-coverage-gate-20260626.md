# Rich Hover Coverage Gate - 2026-06-26

Status: repo-side audit/gating note. No live Qamus data, renderer files, token decisions, closure batches, or
production artifacts were mutated by this report.

## Why This Gate Exists

The rich renderer can only color words that carry scrubbed morphosyntax metadata: `parse_key`, `display`, and
`segments`. The current renderer keeps the visible Arabic token atomic and uses Kawkab Mono-compatible color-stop
math. It should not guess colors for every word from the raw surface string alone.

Therefore the next closure problem is a metadata/parser coverage problem, not a renderer-color problem.

## Current Evidence

Direct live readback of `/srv/dawah-ops/hermes-workspace/qamus-app/qamus_wbw/build/wbw-lookup.json` reported:

```json
{"rich_complete": 9, "rich_partial": 0, "words": 49260}
```

The local staged artifact at `out/hover_stage/wbw-lookup.json` reported:

```json
{
  "rich_metadata": {
    "total_records": 49259,
    "rich_complete": 0,
    "rich_partial": 0,
    "rich_missing": 49259,
    "kawkab_aligned_complete": 0,
    "kawkab_misaligned_complete": 0,
    "missing_candidate_lanes": {
      "candidate_art_nominal": 7592,
      "candidate_ba_art_nominal": 368,
      "candidate_conj_art_nominal": 923,
      "candidate_fa_art_nominal": 49,
      "candidate_prefix_or_function_piece": 756,
      "candidate_suffix_or_pronoun": 151
    }
  }
}
```

These numbers explain why only a few words are colored on public pages: only a few token records currently have the
rich metadata needed by the renderer.

## Gate

Run:

```bash
python tools/audit_wbw_lookup_morphosyntax.py <wbw-lookup.json> --fail-on none
```

Before applying a rich metadata tranche, require:

- each rich record has all three fields: `parse_key`, `display`, and `segments`;
- `display.segments[]` aligns one-for-one with `segments[]`;
- segment surfaces add up to the atomic Arabic token after Arabic mark normalization;
- public-facing parse/display/segment payloads do not expose QAC, MCP, Quran.com, Tafsir, or other source labels;
- missing records are routed to exact lanes instead of colored heuristically.

## Next High-Yield Lanes

- `ART+N`: large deterministic display class, but case/number/gender should come from certified metadata.
- `CONJ+ART+N` and guarded `FA+ART+N`: high-yield for visible `وَ/فَ + ال + host`, but oath/comitative/result
  functions must be routed explicitly.
- `P:BI+ART+N` and `CONJ+P:BI+ART+N`: required to stop host-only preposition loss.
- `V+suffix pronoun`: high learner value, but not auto-safe; requires sarf/nahw evidence for subject/object roles.
- `N+possessive pronoun`: useful with POS/context guard.

`tools/build_rich_hover_morphosyntax_candidates.py` is the first review-candidate generator for this coverage
work. It emits scrubbed, public-boundary-safe metadata candidates only when staged root/POS evidence agrees with
the lane shape, and it keeps every segment surface concatenating back to the exact atomic Arabic token. That
Kawkab Mono alignment guard is intentional: color may be applied to grammar pieces, but the visible Qur'anic word
must not acquire spaces or layout gaps.

The generator currently covers:

- `ART+N`
- `CONJ+ART+N`
- bare nominal host candidates
- particle-plus-verb candidates
- reviewed verb-object suffix candidates such as `33:63:1` (`يَسْـَٔلُكَ`)
- review-gated verb-clitic rows such as `26:139:2` (`فَأَهْلَكْنَاهُمْ`)
- vocative `يَٰٓأَيُّهَا` candidates with `yā` / `ayyu` / attention-marker pieces preserved

It intentionally does not treat this as a live hover apply and does not claim final case, number, gender, particle
function, or syntax where those still need sarf/nahw certification.

On the current local staged artifact, the generator produced 22,510 schema-valid review candidates:

```json
{
  "art_nominal": 5165,
  "bare_nominal": 12133,
  "conj_art_nominal": 556,
  "particle_verb": 2896,
  "verb_object_suffix": 1664,
  "vocative_ayyuhā": 96
}
```

The full generated file was validated with `tools/validate_morphosyntax_token_metadata.py`. These are not live
applies; they are a reviewable metadata tranche that can be routed through the normal token-decision/rebuild/readback
gate.

## Non-Negotiables

- Do not split visible Arabic into layout segment boxes.
- Do not remove color to preserve shaping.
- Do not invent public provenance from internal sources.
- Do not count a fallback string as rich hover completion.
- Do not mutate live Qamus without the explicit backup/rebuild/readback gate.
