# Hadith owner-gate readiness (closure-2092 Phase 11)

- **Ṣaḥīḥayn remains PLAN-ONLY** — `corpora/sahihayn/` contains only `PLAN.md` (enforced by `validate_corpus_fixture.py`). No corpus dump, no translations, no commentary committed.
- Requirements documented for any future owner-gated run: matn/isnād separation (consume matn `ar` only, drop isnād), `live_write:false`, no translation/commentary copied, every candidate `status:candidate`, link to sarf/nahw procedures.
- **No owner gate is present** → no Ṣaḥīḥayn work performed; the pipeline mechanics are proven on Nawawī40 only.
