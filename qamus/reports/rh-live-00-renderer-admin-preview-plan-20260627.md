# RH-LIVE-00 Renderer/Admin Preview Plan - 2026-06-27

Status: repo-only plan. No live Qamus mutation, WBW rebuild, service restart, mirror sync, hover ledger mutation, or public
rich-hover rollout is authorized by this document.

## Goal

Provide an admin-only or feature-flagged preview path for the nine RH-LIVE-00 rows so maintainers can inspect rich hover
metadata without changing ordinary public hover behavior.

## Preview Scope

Initial preview rows:

- `33:63:1` `يَسْأَلُكَ`
- `26:139:2` `فَأَهْلَكْنَاهُمْ`
- `22:18:13` `وَٱلشَّمْسُ`
- `22:18:14` `وَٱلْقَمَرُ`
- `22:18:15` `وَٱلنُّجُومُ`
- `22:18:16` `وَٱلْجِبَالُ`
- `22:18:17` `وَٱلشَّجَرُ`
- `3:123:4` `بِبَدْرٍ`
- `2:213:37` `لِمَا`

## Implementation Shape

1. Add a disabled-by-default preview flag, for example `rich_preview=1` on an authenticated/admin route or an internal
   config flag. Public pages without the flag continue to render the existing hover payload.
2. Load rich preview rows from a review artifact or admin-only endpoint, not from public WBW data unless an owner-gated
   live plan later approves that.
3. If no rich preview row exists for a token, fall back to the normal hover with no DOM or text change.
4. Render tooltip content as:
   - authored Qamus gloss;
   - Arabic surface;
   - parse-key line;
   - colored segment rows with role labels and concise contribution text.
5. Use the `qamus-grammar-v1` palette and stable classes such as `qg-verb`, `qg-verb-prefix`, `qg-verb-stem`,
   `qg-pronoun`, `qg-particle`, `qg-conjunction`, `qg-preposition`, `qg-article`, and `qg-noun`.

## Repo-Side Route Contract

The static shadow-admin contract now reserves an admin-only/read-only `rich_hover_preview` view at
`/admin/qamus/shadow/rich-hover-preview/:wbw_loc`. The route may read exact-addressed `hover_inspectors` and
`parse_family_views` from a validated shadow admin pack, then join separately reviewed RH-LIVE preview rows by exact
`wbw:S:A:W`/`quran:S:A:W` identity. It is not an apply route, does not permit public payloads, and must not infer a
preview from raw Arabic surface text or from parse key alone.

Preview candidate validation also requires the exact `quran:S:A:W`/`wbw:S:A:W` row to exist in its committed renderer
fixture with a compact parse key, matching segments/display classes, `segments_concat_equals_surface`, and
`live_renderer_claim=false`.

## Arabic Rendering Rules

- The Qur'anic written token remains an atomic visual word.
- No spaces, gaps, flex children, grid children, margins, padding, or inline-block boxes inside a written Arabic token.
- Segment spans, if used for colored letters, must remain `display:inline` with zero spacing.
- The token wrapper uses `dir="rtl"`, `lang="ar"`, `unicode-bidi:isolate`, and `white-space:nowrap`.
- Ayah ornaments stay outside the RTL Arabic token run as isolated siblings.
- Tooltip Arabic lines must have enough vertical padding/line-height to avoid clipping diacritics.

## Public Boundary

The preview must not expose internal source labels or raw evidence in public payloads. The only public-safe fields are
Qamus-authored fields such as:

```json
{"src":"qamus","kind":"authored","lang":"en"}
```

Internal MCP/source triangulation remains in internal evidence sidecars and review reports only.

## Smoke And Readback Plan

Before any live preview enablement:

1. Run validators for preview candidates, source readiness, two-vote requests, two-vote responses, and reconciliation.
2. Run a public-boundary scan over generated preview JSON/HTML fixtures.
3. In a browser, inspect the preview route at desktop and narrow widths for:
   - `33:63:1`;
   - `26:139:2`;
   - `22:18:13-17`;
   - `3:123:4`;
   - `2:213:37`.
4. Assert:
   - `.qg-seg` or equivalent segment markers exist in preview mode;
   - parse-key element exists in preview tooltip;
   - visible Arabic token textContent equals the original token with no inserted spaces;
   - segment classes are role-aware;
   - normal public hover remains unchanged when the flag is disabled;
   - no public HTML/payload contains internal source labels.

## Rollback Plan

- Disable the preview flag.
- Remove the admin-only preview artifact from the runtime path.
- Re-read public pages without the flag and confirm normal hover behavior.
- Do not touch live WBW artifacts or the hover decision ledger as part of rollback.

## Explicit Non-Goals

- No broad public rich-hover rollout.
- No hover coverage claim.
- No WBW rebuild.
- No live hover decision apply.
- No mirror sync.
- No service restart unless separately owner-authorized.
