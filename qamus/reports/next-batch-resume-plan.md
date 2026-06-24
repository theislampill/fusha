# Next-batch resume plan (PP1G continues — exact, no vague "standing by")

## Where we are (live, reconciled)
- **NEW: suffix/pronoun lane is LIVE** — noun-stem + possessive-enclitic resolver (POS-gated, verb hosts excluded), fixed the visible أَعْمَالُنَا→"our deeds" class; 182 applied; 888 stem_base_unknown (next: author noun stems), 1,050 verb-suffix (verb lane).
- **NEW: token-addressed override layer is LIVE** (per-`quran:S:A:W` > surface-key TSV > pending) — resolves homograph collisions the TSV cannot; 363 decisions applied; same-surface polysemy (وَمَا, bare إِنْ, لَمَّا) is the next tier (needs per-token iʿrāb).
- Live coverage **81.77%** · 40,805 / 49,900 resolved · **9,095 pending** · tsv 1,223 + 545 token decisions · 2,092 entries.
- Distinct pending surfaces: **5,435** (was 6,422). Authorable lever `pending_needs_sarf` = **7,990**.
- Processed: B2 (230→159) + B3 (230→186) + B4 (230→181) + B5 (230→190, 61 MCP-backed) + **particle-hardtail
  (311→289)**, each excluding prior rejects. Combined **+1,005 glosses, +4,264 occ, −0 removed**.
- **Tafsir MCP lane AVAILABLE** (direct HTTP + now native in-runtime) — internal grammar/morphology evidence;
  build tool, NOT a skill dependency (skills verified MCP-free).
- Particle example āyāt: **90.51% resolved** (was 81.51%); remaining = 157 documented homograph blockers +
  35 single-surface content tokens in the global queue.
- Cumulative live trail: 51.52 → … → 79.93 → 80.68 → **81.41** (B6 token-addressed layer).
- State graph: 1,222 resolved keys, 156 quarantine_homograph, 11,345 pending (every token has a state, 0 unknown).

## Exactly what was processed vs. what remains
The candidate pool is the live `export_audit_state.py` top-500 pending surfaces, taken by descending frequency.
- **Done:** the top SAFE-classified slice (≈ first 230 by frequency) — certified survivors applied.
- **Remaining same-tier rejects (do NOT re-author as single glosses):** the 71 homographs are now forbidden
  transitions; they need either (a) per-surface (vocalized) keys, which the current `norm_strict` pass cannot
  carry, or (b) entry-level disambiguation. Track in the state graph `--split`.
- **Remaining pool:** ~6,036 distinct pending surfaces below the processed tier — a long, lower-frequency tail
  that is increasingly proper nouns, multi-sense, and source-photo-gated entries (each further batch yields a
  smaller, harder-won increment, by design of the gate).

## Exact next command chain (batch-6 — B2..B5 already applied)
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
Do not stop after batch-5 if green. Continue the tiers (particles where safe → nouns → verbs) until every key is
`resolved`/`quarantine_homograph`/`pending-with-exact-blocker` in the language state graph, or a real
evidence/safety gate blocks (the source-photo floor below). Each applied batch must re-reconcile the scoreboards.

## The floor (where authoring stops and source verification begins)
190 entries are `needs_source_photo_review` (āyāt hover-complete, entry fields unverified) and require the
photographed source corpus — owner-gated. See [`retake-source-photo-requests.md`](retake-source-photo-requests.md).
