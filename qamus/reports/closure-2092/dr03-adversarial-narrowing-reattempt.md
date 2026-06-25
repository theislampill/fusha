# dr03 reattempt — adversarial narrowing proof

Verified at HEAD `a0f596b`.

**False positives** (proven not real): (1) 'repo still anchored at the old 82.49 figure as current' — the bridge-status banner is 85.87%; (2) 'check_regressions uses git ls-files' — it uses filesystem existence checks.

**Real, now fixed:** stale canonical paths, missing claude.ai pack, missing corpus-fixture validator, missing lane generators (now built: verb-clitic/new-entry/source-entry-repair), candidate schema gaps.

**Narrowed:** the no-git fallback was needed only in the ergonomics + reconciliation validators (added there, not everywhere); `examples[].en` is qamus-authored (NOTICE.md) and only leak-pattern-checkable — under-validated, not a policy defect; learner **production drills already exist**, only the tutor routing/packaging was missing (added); corpus readiness is read-only and bounded.

**No overbuild:** existing validators were extended (suffix-pronoun, report-reconciliation, artifact-ergonomics) rather than duplicated; only genuinely-missing validators were added.
