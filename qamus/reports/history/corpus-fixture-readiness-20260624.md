# Corpus-to-Qamus fixture readiness (closure-2092 Phase 8)

Proves the corpus→Qamus pipeline is **read-only and translation-clean** on a bounded Nawawī40 sample,
and that Ṣaḥīḥayn stays **plan-only**. No live writes, no mass import, no translation copied.

## Fixture run (repo-local, bounded)

```bash
mkdir -p out/corpus-fixture
python3 tools/corpus_to_qamus_candidates.py --corpus corpora/nawawi40/nawawi40.matn.jsonl --out out/corpus-fixture --limit 5
python3 tools/corpus_to_hover_decisions.py  --corpus corpora/nawawi40/nawawi40.matn.jsonl --out out/corpus-fixture --limit 5
python3 tools/validate_corpus_fixture.py out/corpus-fixture
```

## Result

- candidate worklist: 5 hadith → classifications `already_in_qamus` / `new_surface_existing_lemma` /
  `new_root` / `particle_or_construction` / `review_needed`; **live_writes: 0**; every row `live_write:false`.
- hover worklist: rows carry `norm_key, surfaces, occurrences, status, recommended_gate, proposed_gloss,
  used_by, live_write`; **live_writes: 0**.
- `validate_corpus_fixture.py`: **CORPUS FIXTURE OK** — read-only, schema valid, no translation-like field
  (`en`/`translation`/`tafsir`/…), `source_address` all `corpus:*`-scoped, **Ṣaḥīḥayn plan-only**
  (`corpora/sahihayn/` = only `PLAN.md`).

## Boundary

- Ṣaḥīḥayn remains **plan-only** until an explicit owner gate; no committed corpus dump, no translations,
  no commentary. The fixture proves the pipeline mechanics, not a mass import.
- The `out/corpus-fixture/` outputs are gitignored (generated); the validator + this report are the
  committed proof.
