# Final post-hygiene completion report (closure-2092, 2026-06-24)

HEAD `3d621c1` = origin/main. **Live coverage 85.87% → 86.18%** (+156, 0 wrong). Companion: `.json`.

## Proof half (the tranche's primary ask) — DELIVERED

- **Deep-research reattempt matrix**: 40 findings across dr01–05, finding-by-finding closure — 31 confirmed_fixed, 6 narrowed, 2 false_positive, 1 owner-gated; **0 high-severity blocking authoring**. Five approach reports (`dr01–dr05-*-reattempt`).
- Baseline re-verified TRUE (by_norm 7,125; host_lexeme qac_pos==V=0; verb_clitic 822; أتي/رأي residual 0); live == repo-local.

## Completion half

| metric | before | after |
|---|---:|---:|
| live coverage | 85.87% | **86.18%** |
| resolved | 42,849 | **43,005** |
| pending | 7,051 | 6,895 |
| wrong-gloss open | 0 | **0** |

- **Missing generators built** (Phase 4): verb-clitic (638 review-only), new-entry proposals (52 owner-gated; confirms dr05 families سوأ/رضو/ربب/صلو/زكو), source-entry-repair (forms_array 89 / quran_refs 40 / source_photo 4) — all with schema + validator, wired.
- **Authoring cycle 002** (Phase 7): 173 families → 60 certified / 90 rejected / 23 disagree (34.7%); **applied +156 LIVE** via the scoped gate (−0 removed/changed). The gate rejected exactly the scar fixtures (كذبوا/ويقتلون/فاستقيموا/جاءني).
- **Engine completion audit** (Phase 9): sarf 11/11, nahw 16/16 named failure modes operational.
- **Grammar-metadata audit** (Phase 6): POS 99% / root 62% derivable; quality 91.20% clean; **0 public source leaks**.
- **claude.ai pack** self-tests + tutor-routing audit (Phase 10); **corpus** Nawawī40 read-only, Ṣaḥīḥayn plan-only (Phase 11).
- **Index-miss** (Phase 3): owner-gated; CORRECTED — live expand.py already matches usage.forms under MIN_FORM_LEN+homograph quarantine, so ≤1,050 is an upper bound, not a guaranteed rebuild win.

## 90% — not yet reached; precise blocker

- Live **86.18%**; **+1,905 needed**; expected-safe-realizable **~3,442** → **93.08% ceiling** (reachable).
- **Blocker:** owner-paced **multi-batch authoring** (~10–14 form-variant cycles at 34–45% approval over the ~3,000-token lane) + owner-gated lanes (new-entry 52, index-miss live tuning, source-entry repair). The mechanism is **proven** (cycle 002 +156, 0 wrong) and every generator/validator/gate is ready.

## Deferred (with exact continuation)

- **Live 2,092-page crawl** (Phase 5): read-only home check only (200 / 2,092 entries). Full crawl deferred (site load + budget). Next: `crawl_qamus_public_entries.py` (throttled, no login).
- **Source-photo** (Phase 8): 4 candidates queued; corpus complete, needs head-on crops (owner-gated).

## Exact next command chain

```
build_form_variant_candidates.py --max-b 200 --max-c 200 -> form-variant-2vote -> build_form_variant_apply.py
  -> validate_form_variant_family_batches -> append(backup)+rebuild.sh -> re-stage+regenerate+gates+commit  (repeat ~10-14x for +1,905)
then: host-lexeme(255) / token-irab(380) / owner-gated new-entry(52) / index-miss owner tuning
```
