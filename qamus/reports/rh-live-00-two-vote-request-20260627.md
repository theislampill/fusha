# RH-LIVE-00 Two-Vote Requests From Source Readiness - 2026-06-27

Status: repo-only exact-address review packet. This report does not mutate live Qamus, rebuild WBW, restart services,
sync mirrors, mutate the hover ledger, or claim public rich-hover support.

## Purpose

`qamus/examples/rh_live_00_source_triangulation_readiness.sample.jsonl` separated RH-LIVE preview rows into:

- rows with fresh internal source support for segment roles; and
- rows blocked on source retry.

This packet moves the source-supported rows into the established Phase 4 two-vote request format. It does not certify,
apply, or preview them publicly.

## Artifacts

| artifact | role |
|---|---|
| `qamus/examples/rh_live_00_two_vote_request_from_source_readiness.sample.jsonl` | nine exact-address two-vote request rows |
| `qamus/examples/rh_live_00_source_triangulation_readiness.sample.jsonl` | upstream readiness packet |
| `tools/validate_phase4_two_vote_requests.py` | existing request validator reused for this packet |

## Rows

| loc | surface | requested review |
|---|---|---|
| `33:63:1` | `يَسْأَلُكَ` | finite verb plus attached object pronoun; reject dictionary-infinitive reasoning |
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | fā' relation plus finite verb, subject pronoun, and object pronoun |
| `22:18:13` | `وَٱلشَّمْسُ` | conjunction plus article plus conjoined host noun |
| `22:18:14` | `وَٱلْقَمَرُ` | conjunction plus article plus conjoined host noun |
| `22:18:15` | `وَٱلنُّجُومُ` | conjunction plus article plus broken-plural host noun |
| `22:18:16` | `وَٱلْجِبَالُ` | conjunction plus article plus broken-plural host noun |
| `22:18:17` | `وَٱلشَّجَرُ` | conjunction plus article plus host noun; renderer must preserve atomic token layout |
| `3:123:4` | `بِبَدْرٍ` | bā' preposition plus proper-noun host; host-only hover is incomplete |
| `2:213:37` | `لِمَا` | lām plus contextual `ما` function; surface-only certification is unsafe |

## Explicit Non-Application Boundary

Each request row keeps:

- `apply_policy.apply_allowed=false`;
- `apply_policy.live_mutation_allowed=false`;
- `apply_policy.closure_claim_allowed=false`;
- `component_candidates_can_certify=false`;
- `raw_surface_identity_allowed=false`;
- `parse_key_primary_identity=false`;
- public boundary `src=qamus`, `kind=authored`, `lang=en`.

The rows are exact-address review requests only. Review success may create certified-not-applied artifacts, but cannot
mutate live Qamus or public hover behavior by itself.

## Validation

Run:

```powershell
python tools\validate_phase4_two_vote_requests.py qamus\examples\rh_live_00_two_vote_request_from_source_readiness.sample.jsonl
python tools\check_regressions.py
```
