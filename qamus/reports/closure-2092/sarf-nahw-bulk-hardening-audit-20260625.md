# Sarf/nahw bulk hardening audit — 2026-06-25

**Status: complete.**

This closes the skill-doc gap exposed by the bulk closure work: a validated source-triangulation table is a
classification surface, not automatically a hover-gloss batch.

## Changed

- Added `sarf/procedures/bulk-source-triangulation.md`.
- Linked it from `sarf/SKILL.md`.
- Added `nahw/procedures/bulk-source-triangulation.md`.
- Linked it from `nahw/SKILL.md`.

## Safety Rules Now Encoded

- `auto_safe` requires root/POS agreement, one applicable sense/form, no `norm_strict` collision, and no syntax-sensitive trigger.
- Derived form, voice, person, nominal-vs-verbal shape, multi-sense, and shared-key rows become two-vote requests.
- Particles, negation/mood, i'rab, idafa, jar-majrur, conditionals, relatives, contronyms, and referent-sensitive rows require two independent checks or precise pending.
- Index misses are resolver/index candidates, not free reindex applies.
- New-entry and entry-repair rows remain owner-gated with blank authored fields until reviewed.
- Public hover output remains `src=qamus`, `kind=authored`, with no external source names.

## Verification

Final verification is recorded in `final-bulk-hover-closure-report-20260625.md`.
