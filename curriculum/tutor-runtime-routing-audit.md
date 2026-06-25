# Tutor-runtime routing audit (updated 2026-06-25)

Verifies `curriculum/tutor-runtime-routing.md` maps every learner-error class to a REAL procedure that exists.

The router is a thin dispatcher, not a duplicate skill. It now routes the original sarf/nahw
error classes plus the current closure-hard classes:

- host-only attached-particle/clitic hovers;
- false tanwīn/pronoun splits;
- `مَا` and `وَمَا` function decisions;
- `وَ` and `فَـ` function splits;
- governing-particle mood;
- PP attachment / hidden attachment;
- QAC concept-map misuse and named-entity/common-word collisions.

Before treating this audit as release proof, re-run a link/procedure existence check after any
router edit. Avoid stale count claims such as "sarf 15 / nahw 15" unless the current tree was
just counted in the same run.
