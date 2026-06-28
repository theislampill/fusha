# RH-LIVE-00 Admin Preview Bundle Manifest - 2026-06-28

Status: repo-only bundle guard. This does not mutate live Qamus, rebuild WBW, restart services, sync mirrors, mutate the
hover ledger, or claim public rich-hover support.

## Purpose

The RH-LIVE-00 packet already has separate preview candidates, source-readiness rows, exact-address two-vote review
rows, certified-not-applied rows, route-contract scaffolding, and renderer/admin planning. This manifest adds a single
machine-checkable bundle gate so a future admin-preview implementation cannot silently mix different row sets.

## Artifacts

| artifact | role |
|---|---|
| `qamus/examples/rh_live_00_admin_preview_bundle_manifest.sample.json` | manifest tying all RH-LIVE-00 preview/review inputs together by path, count, and hash |
| `tools/validate_rh_live_admin_preview_bundle_manifest.py` | fail-closed validator for bundle identity, policies, route contract, reports, and cross-artifact row parity |

## Enforced Bundle Facts

- Preview candidates: 9 rows.
- Source-readiness rows: 9 rows, all `exact_address_two_vote_ready_not_applyable`.
- Two-vote requests: 9 rows.
- Two-vote responses: 18 rows, exactly `sarf-primary` and `nahw-primary` per request.
- Certified-not-applied rows: 9 rows.
- Unresolved rows: 0.
- The `rich_hover_preview` route exists only as an admin-only/read-only route contract.
- All live/apply/public-rollout flags remain false.
- Public boundary remains `src=qamus`, `kind=authored`, `lang=en`.
- Component candidates remain evidence only and do not certify whole-token meaning.

## Validation

Run:

```powershell
python tools\validate_rh_live_admin_preview_bundle_manifest.py --self-test
python tools\validate_rh_live_admin_preview_bundle_manifest.py qamus\examples\rh_live_00_admin_preview_bundle_manifest.sample.json
python tools\check_regressions.py
```

## Boundary

This manifest is not an owner authorization request and not a live apply plan. It is a repo-side proof that the existing
RH-LIVE-00 admin preview packet is internally coherent before any future owner-authorized app work.
