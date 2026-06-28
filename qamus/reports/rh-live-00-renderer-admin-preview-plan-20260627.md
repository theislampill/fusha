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

## RH-LIVE-00.5 Role-Aware Palette

The admin preview must teach grammatical contribution, not only broad POS. The visible Arabic segment can carry a
broad family through the label, but the color class should identify the known role.

| Role | Class | Visual treatment | Explanation | Example |
|---|---|---|---|---|
| `verb_prefix` | `qg-verb-prefix` | cyan role color | inflectional or imperfect marker | `يَ` in `يَسْأَلُكَ` |
| `verb_stem` | `qg-verb-stem` | bright cyan | lexical verb host | `سْأَلُ`, `أَهْلَكْ` |
| `subject_pronoun` | `qg-subject-pronoun` | violet role color | attached subject marker | `نَا` in `فَأَهْلَكْنَاهُمْ` |
| `object_pronoun` | `qg-object-pronoun` | magenta role color | attached object/addressee | `كَ`, `هُمْ` |
| `prefix_conjunction` | `qg-conjunction` | blue | coordination/list relation | `وَ` |
| `prefix_result_fa` | `qg-result-fa` | rose role color | result/resumption relation | `فَ` |
| `prefix_preposition` | `qg-preposition` | teal role color | jarr / PP relation | `بِ` |
| `prefix_lam` | `qg-lam` | amber role color | lām relation or governor under review | `لِ` in `لِمَا` |
| `particle_ma` | `qg-ma-particle` | orange | context-sensitive mā function | `مَا` |
| `definite_article` | `qg-article` | gold role color | definiteness | `ال`, `ٱل` |
| `noun_stem` | `qg-noun-stem` | light neutral | nominal host | `شَّمْسُ` |
| `proper_noun_stem` | `qg-proper-noun` | warm gold | proper-name host | `بَدْرٍ` |

Color is never the only cue. Tooltip rows and segment tables must also show role labels, display classes, gloss
contribution, sarf contribution, nahw contribution, segment kind, and what the segment affects. If the exact grammar
field is absent from the current review artifact, the admin preview must show a pending/null value rather than inventing
a fact.

Underlines are not part of the default role-color treatment. They are reserved for explicit interaction or uncertainty:
solid underline means a selected/current segment, and dotted underline means a pending or uncertain relation. Role
classes themselves must not add default underline decoration because that makes the Arabic look like links and competes
with diacritics.

## RH-LIVE-00.6 Admin Preview IA

The preview route should make the rich hover understandable before it exposes the full review payload:

1. Header: atomic Arabic token, authored Qamus gloss, exact `quran:S:A:W` and `wbw:S:A:W`, and state chips for
   `admin preview`, `certified-not-applied`, `not live`, and `owner not authorized`.
2. Primary hover preview: role-colored atomic Arabic token, compact segment chips, parse key, and one learner-facing
   sentence that explains why the flat hover is insufficient.
3. Secondary panels: sarf, nahw, gates, segment contribution table, learner note, and evidence/readiness are available
   through collapsed details panels. Raw review details should not visually compete with the token/gloss.
4. Gates: render the gate states as compact chips:
   `address pass`, `public boundary pass`, `sarf pass/preview`, `nahw preview`, `source/two-vote certified-not-applied`,
   `renderer fixture-only`, `owner blocked/not authorized`, and `live apply blocked`.
5. Mobile: the token and gloss come first; segment tables switch to stacked labeled rows; detail panels remain
   touch-friendly; no horizontal overflow is allowed.

The fixture validator guards this IA shape with required header/primary/secondary containers, collapsed secondary
panels, state chips, gate chips, segment chips, and mobile table labels. These checks are renderer-planning guards only;
they do not claim live support.

## RH-LIVE-00.7 Split-Layer Route IA

The admin route should clearly separate the compact hover from the inspector:

1. Actual hover preview (`.qg-hover-preview`) appears first and contains only the atomic role-colored Arabic token,
   authored gloss, compact parse key, learner-readable segment chips or short breakdown, one learner explanation
   sentence, and tiny `admin preview` / `not live` markers.
2. Admin inspector (`.qg-admin-inspector`) appears below and owns the debug surfaces: admin evidence, sarf details,
   nahw details, segment contribution table, gate status, and readiness notes.
3. Defaults: hover preview and learner explanation are open; identity/evidence, sarf, nahw, segment table, and gate
   status are collapsed.
4. Segment chips in the compact hover use learner labels such as `FA · result`, `STEM · lexical host`, `SUBJ · subject`,
   and `OBJ · object`. Raw role names are reserved for the admin table.
5. If chips are not wired to synchronized token/table highlighting, they should remain static and should not look like
   buttons or links.

The route `/admin/qamus/shadow/rich-hover-preview/:wbw_loc` remains admin-only/read-only. It is not a public hover
rollout, does not mutate the hover ledger, and must keep normal public hover behavior unchanged when preview mode is
disabled.

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
   - known segment roles use role-aware classes, not only broad POS colors;
   - the token identity, sarf, nahw, segment table, learner explanation, and gate/status panels are present;
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
