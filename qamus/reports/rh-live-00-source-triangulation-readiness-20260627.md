# RH-LIVE-00 Source-Triangulation Readiness - 2026-06-27

Status: repo-only readiness packet. This report does not mutate live Qamus, rebuild WBW, restart services, sync mirrors,
mutate the hover ledger, or claim public rich-hover support.

## Purpose

`qamus/examples/rh_live_00_preview_candidates.sample.jsonl` proves a tiny admin/renderer preview shape. This follow-up
adds a bounded source-triangulation readiness layer for the same nine rows so the next owner-gated review can tell which
rows have compact internal grammar support for exact-address two-vote review.

The packet is not a public hover artifact. Public-facing fields remain limited to Qamus-authored preview text:
`src=qamus`, `kind=authored`, `lang=en`.

## Artifacts

| artifact | role |
|---|---|
| `qamus/examples/rh_live_00_source_triangulation_readiness.sample.jsonl` | nine-row internal readiness packet |
| `tools/validate_rh_live_source_triangulation_readiness.py` | fail-closed validator and self-test |
| `qamus/examples/rh_live_00_preview_candidates.sample.jsonl` | renderer/admin preview candidate source packet |

## Readiness Summary

| class | rows | meaning |
|---|---:|---|
| `exact_address_two_vote_ready_not_applyable` | 9 | internal MCP analysis supports the segment roles; still requires exact-address two-vote before any apply |
| `source_retry_required_not_certified` | 0 | no rows remain in this retry lane in the current packet |

Rows with fresh internal MCP support:

- `33:63:1` `يَسْأَلُكَ` - finite imperfect verb plus attached object pronoun; dictionary-infinitive hover is unsafe.
  This row also requires phrase-context support because the contextual gloss `the people ask you` depends on the
  following explicit subject `النَّاسُ` at `quran:33:63:2` / `wbw:33:63:2`. The token contribution remains `ask you`;
  `they/people` is not an attached pronoun inside the token.
- `26:139:2` `فَأَهْلَكْنَاهُمْ` - fā' relation plus finite past verb, subject pronoun, and object pronoun.
- `22:18:13` `وَٱلشَّمْسُ` - conjunction plus definite noun host; host-only or unsegmented hover remains incomplete.
- `22:18:14` `وَٱلْقَمَرُ` - conjunction plus definite noun host; conjoined nominative role needs reason agreement.
- `22:18:15` `وَٱلنُّجُومُ` - conjunction plus article plus broken-plural noun host.
- `22:18:16` `وَٱلْجِبَالُ` - conjunction plus article plus broken-plural noun host.
- `22:18:17` `وَٱلشَّجَرُ` - conjunction plus article plus noun host; renderer must keep the written token atomic.
- `3:123:4` `بِبَدْرٍ` - prefixed bā' plus proper-noun host; host-only place-name hover is incomplete.
- `2:213:37` `لِمَا` - lām plus contextual `ما` function; flat surface treatment is unsafe.

## Boundary

The readiness packet may name internal evidence status, but it stores no raw MCP text and no copied external wording.
Rows remain `may_apply_live=false`, `live_mutation_allowed=false`, and `public_exposable=false`.

## Word-Level Versus Phrase-Context Evidence

Every readiness row now records `token_contribution_gloss` and `contextual_phrase_gloss`. If those differ, the row must
also record `adjacent_context_required=true`, exact adjacent context locs, a context source field, and
`phrase_context_level` inside `source_triangulation.evidence_scopes`.

For `يَسْأَلُكَ`, the source-readiness row records both `word_level` and `phrase_context_level` evidence scopes plus a
`phrase_context_review` object. That object stores only source-clean support labels, not raw MCP text, and records that
the following `النَّاسُ` supplies the phrase subject. Rows without phrase/context support must stay pending or route
back to source retry rather than promoting a readable contextual English gloss from word-internal evidence alone.

## Next Gate

All nine rows can enter exact-address two-vote review. No row is live-applyable from this packet, and the compact support
labels are internal evidence only.

Run:

```powershell
python tools\validate_rh_live_source_triangulation_readiness.py --self-test
python tools\validate_rh_live_source_triangulation_readiness.py qamus\examples\rh_live_00_source_triangulation_readiness.sample.jsonl
python tools\check_regressions.py
```
