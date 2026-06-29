# VN-RH-LIVE-00 source-photo locator repair - 2026-06-29

## Scope

Repo-only graph-spine repair for the VN-RH-LIVE-00 preparation gate.

No live Qamus mutation was performed by this patch. No whitelist append, WBW rebuild,
service restart, hover ledger mutation, public rollout expansion, or public coverage
claim is authorized or implied by this report.

## Trigger

The RH-LIVE NorthStar addendum requires every tranche to start from an edge join
table instead of page-by-page rediscovery. Preflight for VN-RH-LIVE-00 showed that
the particle rollout was closed, but the VN-00 graph worklists were dominated by
`source_photo_candidate_needs_visual` because the source-photo locator still used
rank-only candidates for many early verb and noun entries.

## Inputs

Read-only source-photo worker packets covered:

- `v001-v020`
- `v021-v047`
- `n001-n045`

The current Fusha source-key convention for noun entries is `n001-n1045`; external
rollout reports may display the same range as `n0001-n1045`, but the repo graph
keys remain `n001`-style.

## Files changed

- `qamus/reports/source-photo-verified-samples.jsonl`
- `qamus/indexes/source_photo_entry_locator.json`
- `tools/build_source_photo_entry_locator.py`
- `tools/check_regressions.py`
- `qamus/examples/rh_live_00_admin_preview_bundle_manifest.sample.json`

## Repair

Added verified `entry_locator` samples for the missing VN-RH-LIVE-00 visual source
photo edges and regenerated the source-photo entry locator.

Coverage after regeneration:

| Range | Verified source-photo locator rows |
|---|---:|
| `v001-v047` | 47 / 47 |
| `n001-n045` | 45 / 45 |
| VN-RH-LIVE-00 total | 92 / 92 |

The generated locator now reports `160` verified entries overall. The generator's
section-span note now matches the photographed corpus sections used by the graph:
verbs begin at `pg002`, nouns begin at `pg279`, and particles begin at `pg453`.

## Edge impact

This repair is only the source-photo edge step. It should allow the live rollout
engine to rebuild VN-RH-LIVE-00 worklists without treating all early VN rows as
source-photo-candidate blockers.

Rows still need the normal RH-LIVE gates before deployment:

- exact entry / sense / card / selected-word edge
- exact Qur'an / WBW edge or explicit crosswalk
- sarf and nahw certification
- public-safe rich-hover payload
- segment/class validation
- public DOM and interactive readback

## Flywheel impact

- sarf: no-op; this patch does not alter morphology rules or drills.
- nahw: no-op; this patch does not alter syntax/function rules or drills.
- curriculum: no-op; the related rollout-control lessons were already promoted in
  `curriculum/reports/rh-live-andon-flywheel-backfill-20260629.md`.
- assessment: no-op; no new learner-facing grammar error class is introduced here.
- schema/validator: updated `tools/check_regressions.py` so the source-photo
  locator regression checks the corrected noun section start (`n001` on `pg279`)
  and accepts verified overrides where a row has been visually certified.
- renderer/admin bundle: refreshed
  `qamus/examples/rh_live_00_admin_preview_bundle_manifest.sample.json` hashes to
  match the current committed RH-LIVE admin-preview fixtures; no fixture content
  or live renderer behavior was changed by this source-photo patch.
- future tranche routing: VN-RH-LIVE-00 should be regenerated from the graph after
  this patch is synced to the server-side Fusha input used by the rollout scripts.

## Validation

Recorded checks for this patch:

- `python tools/build_source_photo_entry_locator.py` - passed; wrote `2092` entries,
  `160` verified, `1932` candidate.
- VN-RH-LIVE-00 locator assertion - passed; `v001-v047` and `n001-n045` are all
  `verified`.
- `python tools/validate_sarf_skill.py` - passed.
- `python tools/validate_nahw_skill.py` - passed.
- `python tools/run_grammar_evals.py` - passed; `cases=88 errors=0`.
- `python tools/validate_rh_live_admin_preview_bundle_manifest.py --self-test` -
  passed.
- `python tools/validate_rh_live_admin_preview_bundle_manifest.py
  qamus/examples/rh_live_00_admin_preview_bundle_manifest.sample.json` - passed.
- `git diff --check` - passed.

Further tranche validation must happen after the server-side graph input is synced
and VN-RH-LIVE-00 worklists are regenerated.
