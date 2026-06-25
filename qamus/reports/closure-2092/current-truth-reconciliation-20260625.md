# Current-truth reconciliation — 2026-06-25 (Phase 0, FINALIZATION tranche)

> **Mandate:** prove the real repo/live state before any authoring. Do not trust the prior
> final message, the committed report JSON, or the GitHub UI. This report labels every number by
> evidence class: `repo-verified` · `live-verified` · `raw-report-claimed` · `private-deploy-claimed`
> · `stale/historical`.

## 1. The HEAD question — SETTLED

| ref | value | how verified | class |
|---|---|---|---|
| working-tree `HEAD` | **d67f873** | `git rev-parse HEAD` | repo-verified |
| local `origin/main` | **d67f873** | `git rev-parse origin/main` | repo-verified |
| **actual GitHub** `refs/heads/main` | **d67f873** | `git ls-remote origin main` | **live-verified (remote)** |
| working tree | **clean, 0 dirty** | `git status --short` (only `## main...origin/main`) | repo-verified |
| branch | `main` | `git branch --show-current` | repo-verified |

**The real current HEAD is `d67f873`, and it is identical across the working tree, the local
tracking ref, AND the actual GitHub remote.** The three candidate hashes reconcile as:

- **`d67f873`** — the real tip (this report's baseline). `git log` lineage:
  `a0f596b → 3d88d04 → a0e6e1f → 3d621c1 → 2a95bd2 → d67f873`.
- **`a0f596b`** — *stale/historical*. It is the tip of the **prior open-stem hygiene tranche**, five
  commits back. A reviewer who saw `a0f596b` on the GitHub commits page was looking at a cached/older
  view (or before the post-hygiene push propagated). It is **not** current.
- **`3d621c1`** — *stale internal text*. It is the HEAD **at the moment the prior tranche's final
  report was generated** (authoring cycle 002), two commits before the final report + regen landed.
  The committed `final-post-hygiene-completion-report-20260624.json` therefore records
  `"head": "3d621c1"` — true when written, **superseded** by `2a95bd2` (the report itself) and
  `d67f873` (xanadu regen). This is flagged in §6 below and corrected by this report.

**Conclusion:** public GitHub, the local tree, the local tracking ref all **agree at `d67f873`**.
The only disagreements were *temporal* (a reviewer/report capturing an earlier commit), not a real
fork or unpushed divergence.

## 2. Coverage — repo AND live agree at 86.18%

| metric | repo-verified | live-verified | agree? |
|---|---:|---:|:--:|
| resolved (glossed) | **43,005** | **43,005** | ✅ |
| word_locs (universe) | 49,900 | 49,900 | ✅ |
| coverage pct | **86.18%** | **86.18%** | ✅ |
| pending (repo full residual) | 6,895 | — | n/a |
| pending_marked (live emitted) | — | 4,867 | see note |

- **repo-verified** source: `tools/validate_blocker_root_cause_ledger.py` →
  "6,895 pending tokens … reconciled to coarse blockers (4723/1792/380/0)"; resolved = 49,900 − 6,895 =
  **43,005**.
- **live-verified** source: live artifact `_meta.coverage` =
  `{glossed: 43005, word_locs: 49900, pct: 86.18, pending_marked: 4867}`, `built_at`
  `2026-06-25T03:48:30Z`, `source_sha 65797d7d5599fadd`, `entry_count 2092`. Artifact:
  `/srv/dawah-ops/hermes-workspace/qamus-app/qamus_wbw/build/wbw-lookup.json` (8,242,823 B,
  sha16 `8d3c077abac42890`). Live-served copy == git-mirror copy (identical sha) → two-copy rule holds.
  Rollback `wbw-lookup.prev.json` (sha16 `afd8e613…`) present → cycle-002's +156 live apply confirmed.

> **pending reconciliation (honest):** live `pending_marked` = 4,867 is the subset of word_locs the
> live expand step emits an explicit pending marker for; the remaining `6,895 − 4,867 = 2,028` are
> word_locs that are un-resolved but carry no explicit live pending marker (silent pending outside the
> emitted set). The **coverage numerator (43,005) and pct (86.18) are byte-for-byte identical** live
> vs repo — the pending count differs only by live marking convention, not by a coverage discrepancy.

The prior tranche's "live 86.18%" — previously `private-deploy-claimed` — is now **`live-verified`**.

## 3. Blocker counts — repo-verified, reconciled

| blocker | count | class |
|---|---:|---|
| `stem_base_unknown` | 4,723 | repo-verified (ledger validator) |
| `source_entry_unverified` | 1,792 | repo-verified |
| `same_surface_polysemy_requires_i3rab` | 380 | repo-verified |
| `proper_noun_no_qamus_entry` | 0 | repo-verified |
| **total pending** | **6,895** | reconciles to 49,900 − 43,005 |

## 4. Public Qamus entry count + split — live-verified

- entry count **2,092** — live `_meta.entry_count = 2092`; repo
  `validate_entry_completion_rollup.py` → "2,092 terminal".
- section split **947 verb / 1,045 noun / 100 particle** — repo-verified (`audit_qamus_2092_entries.py`
  hard invariant `dict(sec)=={"verb":947,"noun":1045,"particle":100}`); reconciles to the public index.
- live home page HTTP **200**.

## 5. Gates run — 14/14 PASS (repo-verified, this session)

| gate | result |
|---|---|
| check_artifact_ergonomics | PASS — all committed artifacts reviewable/diffable |
| check_report_ergonomics | PASS — 89 reports reviewable (19 soft warnings) |
| validate_report_reconciliation | PASS — no stale current-claims |
| validate_canonical_paths | PASS — 377 files, 0 stale current-path refs |
| validate_current_qamus_dataset | PASS — public-safe dataset acceptance |
| validate_surface_index_covers_usage_forms | PASS — 10,405 form/headword tokens indexed |
| validate_open_stem_lane_sanity | PASS — host-lexeme noun-only, roots flattened |
| validate_blocker_root_cause_ledger | PASS — 6,895 pending, reconciled |
| validate_qamus_completion_manifest | PASS — 49,900 terminal, exact blockers |
| validate_entry_completion_rollup | PASS — 2,092 terminal, 0 unknown |
| validate_bidirectional_links | PASS — 28,393 addr rows, 2,092 entry nodes |
| run_grammar_evals | PASS — 88 cases, 0 errors, 8 wrong-reasoning traps |
| verify_claude_ai_pack | PASS — 28 files, 139,983 B, no leak/stale |
| check_regressions | PASS — all (incl. Phase-4 lanes, scar fixtures, corpus fixture) |

## 6. Stale internal HEAD text — flagged

- `qamus/reports/closure-2092/final-post-hygiene-completion-report-20260624.json` and `.md` record
  `head: 3d621c1` / `origin_main: 3d621c1`. **Stale** — true at generation, superseded by `d67f873`.
  Not corrected in-place (it is a dated historical report; correcting it would rewrite history); this
  reconciliation is the current authority. `validate_report_reconciliation.py` passes because the dated
  report is not a "current-claims" scoreboard.

## 7. Live-claim provenance ledger

| claim | class |
|---|---|
| HEAD = d67f873 = GitHub | repo-verified + live-verified (remote) |
| coverage 86.18% (43,005/49,900) | repo-verified + live-verified |
| 0 public provenance leaks in live `words` | live-verified (scanned live artifact: 0 `informed_by/qac/tanzil/ocr/source_photo` keys) |
| public hover output `src:"qamus" kind:"authored"` | live-verified (sampled live `words`) |
| 2,092 entries / 947·1045·100 | live-verified + repo-verified |
| cycle-002 +156 applied live | live-verified (`.prev.json` rollback + decisions file 2,745 lines) |

## 8. Verdict

**GATE CLEAN.** Repo, local tracking ref, GitHub remote, and the live artifact all agree at
`d67f873` / 86.18% / 43,005 resolved. No fork, no unpushed divergence, no coverage inflation, no live
leak. Authoring may proceed (Phase 1+).
