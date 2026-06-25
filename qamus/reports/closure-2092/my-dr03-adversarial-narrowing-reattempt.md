# DR03 — adversarial narrowing / false-positive control — my re-attempt (2026-06-25, HEAD d67f873)

Old concerns triaged: the '82.49% anchor' is a **false positive** (now 86.18% repo+live); 'historical hygiene broken' is **narrowed** to soft warnings; 'learner content missing' is **narrowed** (it was a packaging/runtime gap, not absence). The real residuals all have wired, passing validators. The one **reopened** item is the opposite of over-statement: the examples[].en copied-translation was UNDER-stated by every prior pass and is now escalated to an owner-gated blocker.

| id | status | blocks | finding | remaining |
|---|---|---|---|---|
| DR03-1 | **false_positive** | — | Repo is still globally anchored at 82.49% | none — old 82.49 figure is historical, not current |
| DR03-2 | **narrowed** | — | Historical-report hygiene still broken | soft warnings only (non-blocking) |
| DR03-3 | **narrowed** | — | Learner production / drill content is missing | gap was packaging/runtime, not absence of content |
| DR03-4 | **confirmed_fixed** | — | Real remaining gaps: stale docs, candidate schema parity, corpus validation, cla | none of these block; examples[].en is the one real residual |
| DR03-5 | **reopened** | public-redistribution | All concerns were over-stated (nothing serious remains) | escalated to owner-gated (DR02-5) |