# RH-LIVE-00 Admin Preview DOM Fixture - 2026-06-28

Status: repo-only renderer/admin preview guard. No live Qamus mutation, WBW rebuild, service restart, mirror sync,
hover ledger mutation, public rollout, or rich-hover coverage claim is made by this fixture.

## What This Adds

The RH-LIVE-00 packet already validates preview candidates, source-readiness rows, exact-address two-vote review, and
the read-only admin route contract. This fixture adds a static DOM/readback model for the renderer failures that must
not recur:

- visible Arabic tokens remain atomic and readable;
- `.qg-seg` role spans exist and concatenate to the exact written token;
- segment spans stay inline with no inserted spaces, flex, grid, gap, margin, padding, or inline-block behavior;
- each card exposes exact `quran:S:A:W` and `wbw:S:A:W` identity;
- each card exposes `src=qamus`, `kind=authored`, `lang=en`;
- parse-key text appears in the tooltip;
- tooltip breakdown rows reuse the same role keys as the visible token;
- source labels and private provenance remain absent from the fixture.

## Scope

The fixture covers the nine RH-LIVE-00 rows:

- `33:63:1` `يَسْأَلُكَ`
- `26:139:2` `فَأَهْلَكْنَاهُمْ`
- `22:18:13` `وَٱلشَّمْسُ`
- `22:18:14` `وَٱلْقَمَرُ`
- `22:18:15` `وَٱلنُّجُومُ`
- `22:18:16` `وَٱلْجِبَالُ`
- `22:18:17` `وَٱلشَّجَرُ`
- `3:123:4` `بِبَدْرٍ`
- `2:213:37` `لِمَا`

## Validation

Validator:

```text
python tools/validate_rh_live_admin_preview_dom_fixture.py --self-test
python tools/validate_rh_live_admin_preview_dom_fixture.py qamus/examples/rh_live_00_admin_preview_dom_fixture.sample.html
```

The bundle manifest validator now requires the DOM fixture as part of the RH-LIVE-00 admin preview packet.

## Non-Goals

- This is not live app code.
- This is not browser proof from qamus.dawah.wiki.
- This is not public rich-hover rollout.
- This is not permission to mutate the live hover ledger.
- This does not make `parse_key` the primary identity.

Any live RH-LIVE preview implementation still needs separate owner authorization, backup/rollback plan, health check,
feature/admin gating, public-boundary scan, and browser readback.
