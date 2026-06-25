# Live Targeted Hover Fix — 2026-06-25

Scope: owner-authorized live Qamus repair for three reported entries plus the previously certified batch018 token
decisions. This note records evidence only; it does not add live scripts, credentials, or deployment paths.

## Named Entry Repairs

- `b8e480aebafe` (`مَا`): 10 example fragments were vocalized; public readback confirmed diacritics and hovers for
  `وَمَا`/`مَا` in the cited examples.
- `19de33871698` (`لَا`): 6 example fragments were vocalized; public readback confirmed diacritics.
- `2fcbd8198aa6` (`بِـ`): 6 example fragments were vocalized; public readback confirmed `بِسَلَـٰمٍ` now hovers as
  `with peace` and `بِبَدْرٍ` as `at Badr`.

## Token Decisions

Added 7 source-addressed function-token decisions:

- `15:46:2` → `with peace`
- `3:123:4` → `at Badr`
- `92:3:1` → `and by the One Who`
- `93:3:1` → `not`
- `93:3:4` → `and not`
- `42:47:13` → `no`
- `42:47:18` → `and no`

Then applied certified batch018, 10 rows:

- `10:22:21`, `10:22:36`, `10:50:4`, `10:73:1`, `11:3:7`, `11:27:28`, `11:29:20`, `11:31:20`, `11:34:14`, `11:116:17`

## Rebuild Evidence

- First rebuild after named repairs: `47,124 / 49,900 = 94.44%`, `+3 added`, `-0 removed`, `~5 changed`, health `200`.
- Second rebuild after batch018: `47,134 / 49,900 = 94.46%`, `+10 added`, `-0 removed`, `~0 changed`, health `200`.
- Public readback passed on:
  - `https://qamus.dawah.wiki/e/b8e480aebafe`
  - `https://qamus.dawah.wiki/e/19de33871698`
  - `https://qamus.dawah.wiki/e/2fcbd8198aa6`
  - `https://qamus.dawah.wiki/healthz`
- Public hover artifact check: `47,134` word records, `0` bad gloss objects for `src=qamus`, `kind=authored`,
  `lang=en`; Arabic-source metadata remains separate from gloss provenance.

## Skill Lessons Folded Back

- `sarf/SKILL.md` and `sarf/procedures/hover-application.md`: exact/form host matches can bypass clitic
  decomposition; inspect safe attached proclitics after host resolution and use token-addressed phrase glosses when
  the preposition sense is contextual.
- `nahw/SKILL.md` and `nahw/procedures/hover-application.md`: `وَمَا` remains one Qur'anic word token but must be
  decomposed as wāw + mā for function; attached bāʾ on majrūr nouns must include the bāʾ role in the hover.

## Residual

After this pass, live hover coverage still has `2,766` unresolved word locations. Continue with the pending
triangulation table and the exact owner/source/safety blocker lanes; do not use broad `مَا` or bāʾ surface defaults.
