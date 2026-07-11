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

- **No external gloss, translation, tafsīr, or OCR text is ever copied into public output.** The
  published qamus-highlight hover carries only qamus's own authored English; a word we cannot
  confidently author stays `PENDING` rather than being filled from an external gloss. During authoring,
  external references (dictionaries, translations, corpora, tafsīr) are consulted only as *comparative
  evidence*. Because every rendering describes the same Arabic source text, ordinary overlap of
  individual words, conventional expressions, or semantically constrained passages with existing
  translations can occur and should not by itself be read as evidence that a rendering was copied from
  any particular source. Where wording is *intentionally reproduced* from an identified external edition
  rather than independently authored or synthesized, that source is recorded and attributed under its
  applicable terms. (The deeper provenance question — **D-01** — is open; this bullet states the output
  boundary and does not preempt it. See `qamus/data/current/NOTICE.md` (D-12) and
  `provenance/source-boundaries.md`.)
- Public output carries `{src:"qamus",kind:"authored",lang:"en"}` only — no `informed_by`, no source names.
- Ṣaḥīḥayn remains **plan-only** (`corpora/sahihayn/`); no hadith text is committed here.
