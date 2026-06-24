# Nawawī40 corpus → Qamus candidates (review-only)

Outputs of the corpus→Qamus engine run over the **Nawawī 40 ḥadīth** matn (and synthetic Arabic
fixtures), deduped against the **committed 2,092-entry Qamus dataset** (`qamus/data/current/`).

> **Review-only. No live writes.** Every row is `review_status: needs_human_review` and flows
> through the bridge → human review → owner-gated apply. Nothing here mutates live Qamus, and **no
> ḥadīth text is bundled** — only the derived lexical candidates (the matn stays in `corpora/`).

## Files

| file | what |
|---|---|
| `new_entries.sample.jsonl` | sample candidate **entries** (new lemma / new root) for review |
| `review_queue.sample.jsonl` | sample tokens needing a human sense/root decision |

## How produced

```bash
python3 tools/build_existing_qamus_index.py                      # index from committed dataset (2092)
python3 tools/corpus_to_qamus_candidates.py --corpus <matn> --plain --out out/c2q
# classify: already_in_qamus | occurrence_augment | new_surface_existing_lemma |
#           new_lemma_existing_root | new_root | particle_or_construction | uncertain
```

Each candidate is then routed through `/fusha-sarf` (root/POS) + `/fusha-nahw` (function/sense)
and only authored via the certified author + key-aware 2-vote pipeline. Deduplication is by
`norm_strict` key against the committed dataset, so a word already in Qamus produces at most an
**occurrence augment**, never a duplicate entry (e.g. the ḥadīth الأَعْمَالُ binds to the existing
ع م ل entry rather than minting a new one).

## Boundaries

- No external gloss text is copied; authored glosses are original qamus-style English.
- Public output carries `{src:"qamus",kind:"authored"}` only — no `informed_by`, no source names.
- Ṣaḥīḥayn remains **plan-only** (`corpora/sahihayn/`); no hadith text is committed here.
