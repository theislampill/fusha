# RH-LIVE-00 Source-Triangulation Readiness - 2026-06-27

Status: repo-only readiness packet. This report does not mutate live Qamus, rebuild WBW, restart services, sync mirrors,
mutate the hover ledger, or claim public rich-hover support.

## Purpose

`qamus/examples/rh_live_00_preview_candidates.sample.jsonl` proves a tiny admin/renderer preview shape. This follow-up
adds a bounded source-triangulation readiness layer for the same nine rows so the next owner-gated review can tell which
rows have fresh internal grammar evidence and which rows still need source retry.

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
| `exact_address_two_vote_ready_not_applyable` | 3 | internal MCP analysis supports the segment roles; still requires exact-address two-vote before any apply |
| `source_retry_required_not_certified` | 6 | MCP/session evidence was unavailable after token expiry; row remains not certified |

Rows with fresh internal MCP support:

- `33:63:1` `يَسْأَلُكَ` - finite imperfect verb plus attached object pronoun; dictionary-infinitive hover is unsafe.
- `26:139:2` `فَأَهْلَكْنَاهُمْ` - fā' relation plus finite past verb, subject pronoun, and object pronoun.
- `22:18:13` `وَٱلشَّمْسُ` - conjunction plus definite noun host; host-only or unsegmented hover remains incomplete.

Rows requiring retry before certification:

- `22:18:14` `وَٱلْقَمَرُ`
- `22:18:15` `وَٱلنُّجُومُ`
- `22:18:16` `وَٱلْجِبَالُ`
- `22:18:17` `وَٱلشَّجَرُ`
- `3:123:4` `بِبَدْرٍ`
- `2:213:37` `لِمَا`

## Boundary

The readiness packet may name internal evidence status, but it stores no raw MCP text and no copied external wording.
Rows remain `may_apply_live=false`, `live_mutation_allowed=false`, and `public_exposable=false`.

## Next Gate

The three supported rows can enter exact-address two-vote review. The six retry rows must first re-run source
triangulation after MCP authentication/session recovery. No row is live-applyable from this packet.

Run:

```powershell
python tools\validate_rh_live_source_triangulation_readiness.py --self-test
python tools\validate_rh_live_source_triangulation_readiness.py qamus\examples\rh_live_00_source_triangulation_readiness.sample.jsonl
python tools\check_regressions.py
```
