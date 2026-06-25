# dr02 reattempt — repo-operational proof

Verified at HEAD `a0f596b`.

- Stale canonical paths: **0** (validate_canonical_paths over 321 files, no-git fallback). `existing_qamus_index.json` never appears as current canonical (legacy scripts marked LEGACY).
- `build_proofing_matrices.py` computes coverage **dynamically**; matrices regenerated.
- `build_decision_backlinks.py` **fails closed** on entry_nodes==0 (committed entry-matrix fallback).
- Canonical-path + bidirectional-link validators present and PASS.
- Batch + provenance sidecars **hard-gated** (7 committed batches; form_variant_batch_001 provenance parity).
- `usage.examples[].en`: **qamus-authored** per `NOTICE.md` — **report-only boundary**, no dataset rewrite this tranche (see dr03 reattempt for the narrowing).
- claude.ai pack builds + verifies (28 files / 140 KB, excludes dataset/index/candidate/out artifacts). Corpus fixture validator PASS, Ṣaḥīḥayn plan-only.
