# Index-miss live-rebuild instructions (closure-2092 Phase 3, owner-gated)

**Not applied this session.** Investigation corrects the prior framing: the live `expand.py` ALREADY matches `usage[].forms` (lines 515-567) under `MIN_FORM_LEN=3` + multi-root/homograph quarantine. So the 1,050 repo-classified `already_entry_form_present_index_miss` tokens are **forms the live resolver intentionally declines** — NOT a guaranteed rebuild win.

## Why this is not authoring

The inflected form is already stored in the entry; resolving it is an index/resolver MATCH, not a new gloss.

## Corrected expectation

- Upper bound ≤ 1,050; the real safe-recoverable subset = forms excluded ONLY by length/single-root rules. Many of the 1,050 are correctly-quarantined homographs/multi-root and MUST stay pending. The prior "~1,050 recoverable" was optimistic.

## Owner-gated procedure (live `expand.py` is a two-copy production file)

1. Per-token: split the 1,050 into (a) safe-relaxable (length-excluded, single-root, collision-free) vs (b) correctly-quarantined. Only (a) is eligible.
2. Back up both copies of `expand.py` + `wbw-lookup.prev.json`; relax matching ONLY for (a); keep homograph quarantine.
3. `rebuild.sh`; health `curl :8791` == 200; diff report (expect (a)-subset resolved, −0 removed/changed, no new gloss).
4. Regenerate audit/scoreboards/ledgers; run all gates.

## Boundary

`expand.py` is owner-gated/backed-up; this public repo never writes live; no public gloss authored in this lane.
