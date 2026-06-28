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

## RH-LIVE-00.5 Enrichment

The fixture now models a grammar-rich admin/learner preview rather than a color-only segment demo. Each card adds:

- token identity panel: exact `quran:S:A:W`, `wbw:S:A:W`, surface, fixture source, certification/preview state, next
  gate, and owner/live status;
- sarf panel: POS, root/form/voice/aspect/person or explicit pending/null values where the current artifacts do not
  certify a field;
- nahw panel: role/function/attachment/pronoun notes and preview-only grammar tags inspired by the local sarfnahw review
  packs;
- segment contribution table: surface, role, display class, label, gloss contribution, sarf contribution, nahw
  contribution, segment kind, and what the segment affects;
- learner explanation panel: the mistake the row prevents and why a flat hover is insufficient;
- gate/status panel: address, public-boundary, sarf, nahw, source/two-vote, renderer, owner, and live-apply states.

Missing grammar fields are deliberately shown as `pending` or `null` in the preview instead of being fabricated. The
fixture remains admin-only/read-only and does not claim live renderer support.

## Role-Aware Color Guard

The palette is now role-aware rather than broad-POS-only. For example:

- `يَسْأَلُكَ` distinguishes `qg-verb-prefix`, `qg-verb-stem`, and `qg-object-pronoun`;
- `فَأَهْلَكْنَاهُمْ` distinguishes `qg-result-fa`, `qg-verb-stem`, `qg-subject-pronoun`, and
  `qg-object-pronoun`;
- `وَٱلشَّمْسُ` distinguishes `qg-conjunction`, `qg-article`, and `qg-noun-stem`;
- `بِبَدْرٍ` distinguishes `qg-preposition` and `qg-proper-noun`;
- `لِمَا` distinguishes `qg-lam` and `qg-ma-particle`.

The validator rejects a known segment role if it is assigned only a generic broad POS class where a specific role class
is available.

## RH-LIVE-00.6 IA/UX Hierarchy

The fixture now models the admin preview as a readable inspection card rather than a flat debug dump:

- header row: atomic Arabic token, authored gloss, exact `quran:S:A:W`/`wbw:S:A:W` chips, and explicit state chips
  (`admin preview`, `certified-not-applied`, `not live`, `owner not authorized`);
- primary hover preview: role-colored atomic Arabic token, compact segment chips, parse key, and a one-sentence learner
  explanation;
- secondary panels: token identity/readiness, sarf, nahw, segment contribution table, learner note, and gates are
  collapsed by default so raw/debug details remain available without dominating the preview;
- gate chips: address, public-boundary, sarf, nahw, source/two-vote, renderer, owner, and live-apply states render as
  compact chips instead of a long bullet list;
- mobile behavior: segment tables are wrapped and become stacked labeled rows on narrow screens, while the token/gloss
  remains first.

The DOM validator now rejects missing header/primary/secondary containers, missing state chips, expanded-by-default
secondary panels, non-chip gate rows, missing segment chips, missing mobile table labels, and missing mobile table CSS.
The Arabic integrity guard remains strict, but it is scoped to `.qg-word`/`.qg-seg` token internals so ordinary card
layout can use flex/grid/gap without being confused for destructive Arabic segmentation.

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
The DOM validator also checks the enriched identity/sarf/nahw/segment/learner/gate panels and role-specific color
classes.

## Non-Goals

- This is not live app code.
- This is not browser proof from qamus.dawah.wiki.
- This is not public rich-hover rollout.
- This is not permission to mutate the live hover ledger.
- This does not make `parse_key` the primary identity.

Any live RH-LIVE preview implementation still needs separate owner authorization, backup/rollback plan, health check,
feature/admin gating, public-boundary scan, and browser readback.
