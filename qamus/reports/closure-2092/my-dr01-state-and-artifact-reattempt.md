# DR01 — state, canonical artifacts, liveness — my re-attempt (2026-06-25, HEAD d67f873)

Settled the truth-source problem head-on (Phase 0). The real current HEAD is **d67f873**, identical across the working tree, the local tracking ref, AND the actual GitHub remote (`git ls-remote`). `a0f596b` is the prior open-stem tranche tip (a stale reviewer view); `3d621c1` is stale text inside the prior final report (its HEAD-at-generation). Coverage is **86.18% (43,005/49,900), now LIVE-verified** by reading the live wbw-lookup `_meta.coverage` (built 2026-06-25T03:48:30Z) — equal to repo. The one open DR01 item is the **public 2,092-page crawl**, executed in Phase 2 of this tranche.

| id | status | blocks | finding | remaining |
|---|---|---|---|---|
| DR01-1 | **confirmed_fixed** | — | Commit identity inconsistent across GitHub UI (a0f596b), report JSON (3d621c1),  | none — real HEAD=origin/main=GitHub=d67f873; a0f596b=prior-tranche tip(stale vie |
| DR01-2 | **confirmed_fixed** | — | Coverage numbers must be labelled repo-verified / live-verified / claimed / stal | none |
| DR01-3 | **confirmed_fixed** | — | Live coverage was only 'private-deploy-claimed' (86.18%) — never read back from  | none — upgraded to live-verified; live==repo exactly |
| DR01-4 | **confirmed_fixed** | — | 2,092-entry 'audited' could be mis-read as 'fully checked / hover-complete / sou | none — 'mechanically classified' != hover-complete/source-verified, stated expli |
| DR01-5 | **confirmed_unfixed** | — | Public 2,092-page crawl never performed (only a home-page 200 check) | execute throttled read-only crawl + live-vs-repo reconciliation (Phase 2) |
| DR01-6 | **confirmed_fixed** | — | Historical/superseded reports could masquerade as current | none |