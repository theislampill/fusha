# Next-batch resume plan (PP1G continues — exact, no vague "standing by")

## Where we are (live, reconciled this tranche)
- Live coverage **75.28%** · 37,567 / 49,900 resolved · **12,333 pending** · tsv **377 lines** · 2,092 entries.
- Distinct pending surfaces: **6,266** (was 6,422). Authorable lever `pending_needs_sarf` = **10,544**.
- Processed this tranche: **batch-2** = the top-frequency 230-candidate tier of the pending pool (POS N/V/P,
  deduped vs the live tsv) → 159 certified + applied, 71 rejected as true homographs.
- Cumulative live trail: 51.52 → 60.01 → 69.06 → 69.08 → 70.47 → 70.76 → 72.14 → **75.28**.

## Exactly what was processed vs. what remains
The candidate pool is the live `export_audit_state.py` top-500 pending surfaces, taken by descending frequency.
- **Done:** the top SAFE-classified slice (≈ first 230 by frequency) — certified survivors applied.
- **Remaining same-tier rejects (do NOT re-author as single glosses):** the 71 homographs are now forbidden
  transitions; they need either (a) per-surface (vocalized) keys, which the current `norm_strict` pass cannot
  carry, or (b) entry-level disambiguation. Track in the state graph `--split`.
- **Remaining pool:** ~6,036 distinct pending surfaces below the processed tier — a long, lower-frequency tail
  that is increasingly proper nouns, multi-sense, and source-photo-gated entries (each further batch yields a
  smaller, harder-won increment, by design of the gate).

## Exact next command chain (batch-3)
Run from this repo + the server wrappers (`/tmp/sshx`, `/tmp/sshxr` recreated per session):

```bash
# 1. refresh the pending pool (read-only on server)
cat tools/build_language_state_graph.py | /tmp/sshx 'cat > /tmp/build_lsg.py'   # if not present
cat qamus/scripts/export_audit_state.py | /tmp/sshx 'cat > /tmp/export_audit_state.py'
/tmp/sshx 'cd .../services && QAMUS_WBW_SERVICES=.../services QAMUS_ENTRIES=.../entries \
  QAMUS_WBW_ARTIFACT=.../qamus-app/qamus_wbw/build/wbw-lookup.json \
  python3 /tmp/export_audit_state.py --out /tmp/audit_export3'
# 2. select + key-probe the NEXT tier (skip the 377 live keys; POS N/V/P; auto-class SAFE)
#    reuse: artifacts/batch2_select_probe.py (edit the slice to safe[230:460])
# 3. author + key-aware 2-vote: assemble artifacts/batch2_wf_template.js with the new candidates
#    (file->file via the Python injector) then Workflow({scriptPath: ".../batch3_wf.js"})
# 4. apply certified -> tsv (artifacts/b2_apply_local.py pattern, backup .bak-b3) -> rebuild.sh
# 5. re-export -> build_audit_completion.py + build_nv_matrices.py -> update scoreboards -> commit/push
```

The harness is fully reusable: `artifacts/batch2_select_probe.py` (selection+probe), `artifacts/batch2_wf.js`
(author+2-vote workflow — edit the injected `CANDS`), `artifacts/b2_apply_local.py` (apply), `qamus_wbw/rebuild.sh`
(rebuild), `qamus/scripts/build_nv_matrices.py` + `build_audit_completion.py` (matrices).

## Continuation rule
Do not stop after batch-3 if green. Continue the tiers (particles where safe → nouns → verbs) until every key is
`resolved`/`quarantine_homograph`/`pending-with-exact-blocker` in the language state graph, or a real
evidence/safety gate blocks (the source-photo floor below). Each applied batch must re-reconcile the scoreboards.

## The floor (where authoring stops and source verification begins)
190 entries are `needs_source_photo_review` (āyāt hover-complete, entry fields unverified) and require the
photographed source corpus — owner-gated. See [`retake-source-photo-requests.md`](retake-source-photo-requests.md).
