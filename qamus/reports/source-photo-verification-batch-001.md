# Source-photo verification — batch 001 (from the EXISTING corpus)

Verification is done against the **existing** photographed corpus at the local intake
(`C:\workspace\ai\in\qamus\`, 1,205 images, pages 2–471). **No retakes were requested** — the
corpus is complete (0 missing pages per the indexer), so `source_photo_status` is never
`needs_retake` by default.

## The real queue (not "everything")

The genuine source-data-issue queue is the **19 held-back verb entries** named in the corpus
`HANDOFF.md` (`v004, v006, v007, v008, v012, v016, v027, v031, v044, v045, v047, v058, v059, v063,
v083, v123, v135, v149, v151`) — high-frequency roots flagged for certified transcription before
any live write. (Per the handoff, **no live writes** occur here; repairs stay owner-gated.)

## Visually verified this pass (read by me, not trusted from prior work)

| source_key | headword | field | live | photo | verdict | source image |
|---|---|---|---|---|---|---|
| v008 | بَيَّنَ (ب ي ن) | total_uses | 523 | **523** | ✅ verified_correct | intake_13/IMG_7784 |
| v027 | عَبَدَ / عَبْد (ع ب د) | total_uses | 275 | **275** | ✅ verified_correct | intake_13/IMG_7790 |

Both `total_uses` lines were read directly off the photographed dictionary page and match the live
entry exactly → recorded in `source-photo-verified-samples.jsonl`. **0 repairs needed** for these.

## Located but not yet visually read (exact locators)

`intake_13` (IMG_7784–7795, 12 shots) spans verb entries ~6–28, so the following held-back IDs are
**locatable in that batch** (next: crop + read each): `v006 أتى, v007 كفر, v012 عمل, v016 رأى`
(plus v008/v027 done). The remaining held-back IDs (`v031…v151`, entries 31–151) are on **other
pages** of the complete corpus and need the entry→page index (below) to locate.

## Buckets (real, no vague "needs review")

| bucket | meaning | count (held-back queue) |
|---|---|---|
| `verified_from_existing_photo` | total_uses read off photo == live | 2 (v008, v027) |
| `photo_located_needs_visual` | page batch identified (intake_13), crop+read pending | 4 (v006, v007, v012, v016) |
| `photo_present_needs_locator` | corpus has the page; entry→page index needed | 13 (v031…v151) |
| `needs_retake` | — corpus complete — | **0** |

## Scaling bottleneck → exact next action

The one missing piece is a **`source_key → book-entry-number → page` index**. The mapping
`vNNN = the NNNth verb entry` is confirmed (the circled entry number on the page equals the v-number:
entry 8 = بين = v008; entry 27 = عبد = v027), and `pages.md` maps entry ranges to page images. Building
that index from `pages.md` + the frontmatter manifests is the exact next action; it turns
`photo_present_needs_locator` into `photo_located_needs_visual` for the whole 2,092 set, after which
visual verification scales. This was **not** done this pass (bounded by budget); it is the single
documented next step, not a vague backlog.

> Honesty note: this pass visually verified **2** entries from existing photos and located **4** more
> in a known image batch; it did not reach a 50-entry visual sweep because the entry→page index is not
> yet built. The corpus is complete and **no** retakes are needed.
