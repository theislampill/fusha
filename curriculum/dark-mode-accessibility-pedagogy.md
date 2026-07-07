# Dark-mode accessibility is pedagogy, not UI polish

Flywheeled from the **D7 colour-key legend ANDON** (2026-07-07, qamus-highlight production).
Companion to [visual-grammar-legend.md](visual-grammar-legend.md) and
[drills/parse-key-and-color-layer.md](drills/parse-key-and-color-layer.md).

## Why this is a learning lesson, not a cosmetics lesson

The rich-hover reader teaches grammar **through colour** (qg-* roles) and **through readable
English glosses**. If either the swatch colour or the label text is unreadable in the learner's
theme, the pedagogy silently fails — the learner sees a panel but cannot decode it. A low-contrast
colour key is not "slightly ugly"; it is a **non-functional teaching aid**. Extended scripture
reading happens in both light and dark; a grammar cue that only works in one theme teaches only
half your readers.

## The exact failure (D7)

A public "colour key" legend rendered a **white panel with near-white text in dark mode**
(measured contrast **1.22 : 1** — WCAG AA needs ≥ 4.5 : 1). Root cause: the panel was styled
with **token names that did not exist** in the theme engine (`--du-surface`, `--du-border`), so it
fell back to a hardcoded white in *both* modes, while the text token *was* theme-aware and went
near-white in dark. Separately, the colour swatches referenced grammar-colour variables that were
**out of scope** for the legend subtree, so the chips rendered transparent (no colour shown at all).

## Rules (encode these for any learner-facing colour/legend surface)

1. **Theme-aware tokens only.** A teaching surface must use the *actual* theme tokens for
   background / text / border / shadow. Verify the token names against the live token file before
   authoring — never style from a remembered generic-kit name. A non-existent CSS var silently
   falls back and desyncs from the theme.
2. **Never use a pale role-colour as label text.** The grammar colour belongs on a **swatch, chip,
   border, or marker** — not as the label's text fill. Pale role colours (near-white verb/noun in
   dark, pale yellow article in light) fail contrast as text but read fine as a bordered chip.
3. **Both themes, both devices, every colour change.** Any change to a colour, swatch, or legend is
   verified in **light + dark × desktop + mobile** before deploy. A screenshot glance is not a
   measurement.
4. **Measure, don't eyeball.** Compute WCAG contrast for the title and every label vs the panel
   background. Fail the deploy if normal text is below **4.5 : 1**, or if a swatch cannot be
   separated from the panel by *any* channel (fill, border, or a neutral inset ring).
5. **Swatch must match running text.** The legend chip for a role must show the **same colour the
   learner sees in the āyah in the current theme** (feed the legend the same mode-scoped palette),
   or the key mis-teaches the mapping.
6. **Source-clean still applies.** A colour legend must expose grammar-role labels only — never a
   source/tool/process label or internal parser/debug id. See
   [../docs/parser/qamus-grammar-v1-class-map.md](../docs/parser/qamus-grammar-v1-class-map.md).

## Poka-yoke

A contrast smoke opens the legend in light + dark, computes WCAG contrast for the title + every
label vs the panel background, asserts ≥ 4.5, asserts the panel background differs from the page
background (proves theme-aware, not hardcoded), and asserts every swatch is distinguishable.
It runs before any legend/colour deploy. See the fixture
`qamus/examples/dogfood_d7_darkmode_contrast_lesson.sample.jsonl` and the ops-side smoke
`smokes/smoke-d7-legend-contrast.js`.

## 5-Whys (why the false "dark inspected" pass)

1. Unreadable in dark → panel hardcoded white while text was theme-near-white.
2. Hardcoded white → styled with token names that don't exist → fallback.
3. Wrong token names → authored from memory, not grepped from the live token file.
4. "Inspected" passed → the screenshot was *not contrast-measured*; "renders" was read as "readable".
5. No test → there was **no computed-contrast smoke**. Now there is.
