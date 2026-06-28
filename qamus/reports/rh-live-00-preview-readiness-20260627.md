# RH-LIVE-00 Preview Readiness - 2026-06-27

Status: repo-only preview-readiness packet. This does not mutate live Qamus, rebuild WBW, restart services, sync
mirrors, mutate the hover ledger, or claim public rich-hover rollout.

## Purpose

`RICH-CERT` produced renderer fixtures across P/VN tranches and a flywheel shortlist. This report turns that shortlist
into a small, validator-backed RH-LIVE-00 preview packet that a future owner-authorized admin/renderer preview can read.

The packet is not live data. It is a contract probe for future app work:

- exact `quran:S:A:W` and `wbw:S:A:W` identity;
- public preview fields remain `src=qamus`, `kind=authored`, `lang=en`;
- all rows are `admin_only`, `read_only`, `public_exposable=false`, and `may_apply_live=false`;
- every row preserves `surface_text_invariant=segments_concat_equals_surface`;
- every row requires DOM checks for atomic Arabic text, non-destructive coloring, parse-key tooltip, segment rows, and
  no public provenance leakage.

## Artifacts

| artifact | role |
|---|---|
| `qamus/examples/rh_live_00_preview_candidates.sample.jsonl` | nine-row admin/renderer preview candidate packet |
| `tools/validate_rh_live_preview_candidates.py` | fail-closed validator and self-test |
| `qamus/reports/rich-cert-flywheel-synthesis-20260627.md` | source shortlist and flywheel summary |
| `qamus/reports/live-rich-hover-renderer-acceptance-20260626.md` | historical renderer acceptance shape, not current live proof |

## Preview Rows

| loc | surface | certification state | next gate | why useful |
|---|---|---|---|---|
| `33:63:1` | `يَسْأَلُكَ` | `token_only_override` | exact-address two-vote | verb prefix + stem + object pronoun |
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | `pending` | component-only blocker resolution | fā' + Form IV verb + subject/object pronouns |
| `22:18:13` | `وَٱلشَّمْسُ` | `preview_only` | component-only blocker resolution | conjunction + article + host noun |
| `22:18:14` | `وَٱلْقَمَرُ` | `preview_only` | component-only blocker resolution | conjunction + article + host noun |
| `22:18:15` | `وَٱلنُّجُومُ` | `preview_only` | component-only blocker resolution | conjunction + article + host noun |
| `22:18:16` | `وَٱلْجِبَالُ` | `preview_only` | component-only blocker resolution | conjunction + article + host noun |
| `22:18:17` | `وَٱلشَّجَرُ` | `preview_only` | component-only blocker resolution | conjunction + article + host noun |
| `3:123:4` | `بِبَدْرٍ` | `token_only_override` | exact-address two-vote | bā' + place-name host |
| `2:213:37` | `لِمَا` | `pending` | function/attachment review | lām + `ما` function/attachment |

## Admin Preview Acceptance

Future RH-LIVE-00 implementation, if owner-authorized, should load the packet only behind an authenticated admin or
offline preview surface. It must assert:

1. visible Arabic `textContent` equals `surface`;
2. no inserted spaces or layout gaps inside a written Qur'anic token;
3. role coloring is visible and non-destructive;
4. tooltip exposes parse key and segment rows;
5. public preview payload contains only Qamus-authored public fields;
6. internal source/evidence labels do not appear in DOM, public JSON, or tooltip payload;
7. every row visibly shows a preview-only/non-applyable banner.

## Forbidden Without Separate Owner Gate

- public rich-hover rollout;
- live WBW rebuild;
- service restart;
- hover ledger mutation;
- mirror sync;
- treating this packet as certification;
- treating component-only evidence as whole-token proof;
- family propagation from parse key.

## Validation

Run:

```powershell
python tools\validate_rh_live_preview_candidates.py --self-test
python tools\validate_rh_live_preview_candidates.py qamus\examples\rh_live_00_preview_candidates.sample.jsonl
python tools\check_regressions.py
```

## Next Gate

The next safe lane is owner-authorized RH-LIVE-00 admin/renderer preview scaffolding. If the owner does not authorize
app work, continue repo-only closure by expanding exact-address review packets, curriculum drills, or source-triangulated
candidate decisions without changing live Qamus.
