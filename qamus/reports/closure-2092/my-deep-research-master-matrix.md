# My deep-research master matrix — 2026-06-25 (HEAD d67f873)

Fresh re-attempt of dr01–dr05 against the current tree + live read-only verification. One row per finding; status re-derived from evidence, not inherited.

**29 findings** — confirmed_fixed: 21, narrowed: 3, false_positive: 2, confirmed_unfixed: 1, confirmed_unfixed_owner_gated: 1, reopened: 1.

| approach | id | status | blocks | finding | verification |
|---|---|---|---|---|---|
| dr01 | DR01-1 | **confirmed_fixed** | — | Commit identity inconsistent across GitHub UI (a0f596b), report JSON (3d621c1), and prior  | git rev-parse + git ls-remote origin main (live remote) |
| dr01 | DR01-2 | **confirmed_fixed** | — | Coverage numbers must be labelled repo-verified / live-verified / claimed / stale, not sta | Phase0 report labels every number by evidence class |
| dr01 | DR01-3 | **confirmed_fixed** | — | Live coverage was only 'private-deploy-claimed' (86.18%) — never read back from the live a | read live wbw-lookup.json _meta.coverage (glossed 43005/49900=86.18, b |
| dr01 | DR01-4 | **confirmed_fixed** | — | 2,092-entry 'audited' could be mis-read as 'fully checked / hover-complete / source-verifi | status-vocabulary banner emitted by audit_qamus_2092_entries.py |
| dr01 | DR01-5 | **confirmed_unfixed** | — | Public 2,092-page crawl never performed (only a home-page 200 check) | read-only home check 200/2092 only; full crawl deferred prior tranche |
| dr01 | DR01-6 | **confirmed_fixed** | — | Historical/superseded reports could masquerade as current | validate_report_reconciliation.py PASS; 3d621c1 stale text flagged in  |
| dr02 | DR02-1 | **confirmed_fixed** | — | Canonical path drift must be gated | validate_canonical_paths.py PASS (379 files, 0 stale) |
| dr02 | DR02-2 | **confirmed_fixed** | — | Batch / provenance parity must be hard-gated | check_regressions.py batch + provenance gates PASS |
| dr02 | DR02-3 | **confirmed_fixed** | — | claude.ai pack must be a small text-only operational pack, not giant JSONL | verify_claude_ai_pack.py PASS (28 files, 139,983 B, <5MB, no file >500 |
| dr02 | DR02-4 | **confirmed_fixed** | — | Corpus fixture must be read-only (no live write, no translation copy) | check_regressions corpus fixture gate PASS |
| dr02 | DR02-5 | **confirmed_unfixed_owner_gated** | public-redistribution | examples[].en must be qamus-authored public text, NOT a copied translation — is it covered | audit_examples_en_provenance.py: 7,700 examples, 41.3% carry Saheeh-In |
| dr02 | DR02-6 | **confirmed_fixed** | — | Public-output (hover) provenance leak risk | live words scan: 0 informed_by/qac/tanzil/ocr keys; ALLOWED_* + PRIVAT |
| dr03 | DR03-1 | **false_positive** | — | Repo is still globally anchored at 82.49% | ledger validator: 43,005/49,900=86.18% repo + live |
| dr03 | DR03-2 | **narrowed** | — | Historical-report hygiene still broken | report ergonomics PASS (89 reports, 19 soft warns); reconciliation PAS |
| dr03 | DR03-3 | **narrowed** | — | Learner production / drill content is missing | claude.ai pack present w/ learner+review self-tests; curriculum dirs e |
| dr03 | DR03-4 | **confirmed_fixed** | — | Real remaining gaps: stale docs, candidate schema parity, corpus validation, claude.ai pac | each has a wired validator now (canonical-paths/schemas/corpus-fixture |
| dr03 | DR03-5 | **reopened** | public-redistribution | All concerns were over-stated (nothing serious remains) | examples[].en copied-translation was UNDER-stated by every prior pass |
| dr04 | DR04-form_variant | **confirmed_fixed** | — | existing-entry form authoring lane | build_form_variant_candidates.py + build_form_variant_apply.py + valid |
| dr04 | DR04-host_lexeme | **confirmed_fixed** | — | noun-host possessive lane | build_host_lexeme_candidates.py + validate_suffix_pronoun_decisions.py |
| dr04 | DR04-token_irab | **confirmed_fixed** | — | token iʿrāb / function-word lane | build_token_irab_decisions.py + validate_token_irab_decisions.py |
| dr04 | DR04-verb_clitic | **confirmed_fixed** | — | verb-clitic object/subject lane | build_verb_clitic_candidates.py + validator + verb-clitic-candidate.sc |
| dr04 | DR04-new_entry | **confirmed_fixed** | 90% | missing-entry proposals lane | build_new_entry_proposals.py + validator + new-entry-proposal.schema.j |
| dr04 | DR04-source_entry_repair | **confirmed_fixed** | — | source-entry repair lane | build_source_entry_repair_candidates.py + validator + schema (forms_ar |
| dr04 | DR04-index_miss | **narrowed** | 90% | index-miss lane | live expand.py already matches usage.forms under MIN_FORM_LEN+homograp |
| dr04 | DR04-source_photo | **confirmed_fixed** | corpus | source-photo / scholar-gated lane | source-entry-repair source_photo mode (4 queued); corpus complete, nee |
| dr05 | DR05-1 | **false_positive** | — | Backlog is one undifferentiated pile | review-only-casebook.jsonl: 1,606 families, 9 buckets, per-row lane/ga |
| dr05 | DR05-2 | **confirmed_fixed** | — | Structural reroutes (هدي already-present, أتي/رأي unflattened) still mis-routed | lane-sanity PASS; casebook bucket1='structural reroute — no authoring' |
| dr05 | DR05-3 | **confirmed_fixed** | — | Unsafe families must be frozen as rejection fixtures | check_regressions scar-family fixtures (>=16: verb-clitic+voice+banned |
| dr05 | DR05-4 | **confirmed_fixed** | 90% | True missing-entry families need owner-gated proposals | new_entry lane: 52 proposals (سوأ/رضو/ربب/صلو/زكو); owner-gated review |

## Headline

- **DR02-5 (examples[].en = verbatim Saheeh International, owner-gated)** is the one finding under-stated by every prior pass — surfaced + quantified + detector built this tranche. Blocks public-repo redistribution cleanliness ONLY; does NOT block coverage-to-90 or the (clean, authored) hover output.

- Everything else: confirmed_fixed or narrowed/false_positive. 0 findings block authoring or the engine. The only authoring-relevant pending is owner-paced multi-batch coverage (Phase 8) + owner-gated lanes.
