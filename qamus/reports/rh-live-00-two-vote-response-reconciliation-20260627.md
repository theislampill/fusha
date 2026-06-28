# RH-LIVE-00 Two-Vote Response Reconciliation - 2026-06-27

Status: repo-only review artifact. This report does not mutate live Qamus, rebuild WBW, restart services, sync mirrors,
mutate the hover ledger, or claim public rich-hover support.

## Purpose

The RH-LIVE-00 source-readiness packet now has nine rows with compact internal support labels. This packet records two
independent review responses for each exact-address row and reconciles them into certified-not-applied rows.

Certification here means only that the review packet agrees internally on the public preview gloss and grammar reason.
It is not live authorization.

## Artifacts

| artifact | role |
|---|---|
| `qamus/examples/rh_live_00_two_vote_request_from_source_readiness.sample.jsonl` | nine exact-address two-vote request rows |
| `qamus/examples/rh_live_00_two_vote_response_from_source_readiness.sample.jsonl` | eighteen response rows, two per request |
| `qamus/examples/rh_live_00_two_vote_certified_not_applied.sample.jsonl` | nine reconciled certified-not-applied rows |
| `qamus/examples/rh_live_00_two_vote_unresolved.sample.jsonl` | zero unresolved rows in this bounded packet |
| `tools/validate_phase4_two_vote_responses.py` | response validator |
| `tools/reconcile_phase4_two_vote_responses.py` | review-only reconciler |

## Reconciliation Summary

| metric | count |
|---|---:|
| requests | 9 |
| response rows | 18 |
| certified-not-applied rows | 9 |
| unresolved rows | 0 |
| live mutation rows | 0 |

## Reconciled Rows

| loc | surface | agreed public preview | reason key |
|---|---|---|---|
| `33:63:1` | `يَسْأَلُكَ` | `ask you` | `finite-verb-object-pronoun-token` |
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | `so We destroyed them` | `fa-finite-verb-subject-object-pronouns` |
| `22:18:13` | `وَٱلشَّمْسُ` | `and + the sun` | `conj-definite-noun-coordinated-subject` |
| `22:18:14` | `وَٱلْقَمَرُ` | `and + the moon` | `conj-definite-noun-coordinated-subject` |
| `22:18:15` | `وَٱلنُّجُومُ` | `and + the stars` | `conj-definite-noun-coordinated-subject` |
| `22:18:16` | `وَٱلْجِبَالُ` | `and + the mountains` | `conj-definite-noun-coordinated-subject` |
| `22:18:17` | `وَٱلشَّجَرُ` | `and + the trees` | `conj-definite-noun-coordinated-subject` |
| `3:123:4` | `بِبَدْرٍ` | `at Badr` | `preposition-proper-noun-host-genitive` |
| `2:213:37` | `لِمَا` | `for what / that which` | `lam-relative-ma-preposition-function` |

## Boundaries

- `apply_policy.apply_allowed=false` remains in every upstream request.
- `live_mutation_allowed=false` remains in every upstream request.
- Component candidates are evidence for segment review, not certification by themselves.
- The identity is the exact `quran:S:A:W` plus `wbw:S:A:W`; `parse_key` is not primary identity.
- Public preview fields remain `src=qamus`, `kind=authored`, `lang=en`.
- No raw external text, source labels, or internal adapter names are present in public preview fields.

## Validation

Run:

```powershell
python tools\validate_phase4_two_vote_requests.py qamus\examples\rh_live_00_two_vote_request_from_source_readiness.sample.jsonl
python tools\validate_phase4_two_vote_responses.py qamus\examples\rh_live_00_two_vote_response_from_source_readiness.sample.jsonl --requests qamus\examples\rh_live_00_two_vote_request_from_source_readiness.sample.jsonl
python tools\reconcile_phase4_two_vote_responses.py --requests qamus\examples\rh_live_00_two_vote_request_from_source_readiness.sample.jsonl --responses qamus\examples\rh_live_00_two_vote_response_from_source_readiness.sample.jsonl --certified-out out\rh_live_00_certified.tmp.jsonl --unresolved-out out\rh_live_00_unresolved.tmp.jsonl
```
