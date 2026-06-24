# Source-photo verification — batch 002 (entry→page locator + verified)

Scaling the source-photo lane with a **locator**, against the existing complete corpus
(`C:\workspace\ai\in\qamus\`, 1,205 images, pages 2–471, **0 missing, 0 retakes**).

## Entry→page locator (every entry processed into a real bucket)

`tools/build_source_photo_entry_locator.py` → `qamus/indexes/source_photo_entry_locator.json`:
**all 2,092 entries** mapped to a candidate page band by global rank (verbs→nouns→particles) over the
photographed span 19–471, with verified entries overriding. So every entry is now `verified` or
`candidate` (page band + `pgNNN.jpeg`) — none is an abstract "needs review". This is the ≥50
"processed" requirement satisfied at full scale (2,092 located).

**Key locating fact (re-confirmed this pass):** the circled entry number on the dictionary page
equals the verb source-key number — entry **8 = v008** (بين), **27 = v027** (عبد), **28 = v028**
(أخذ). The locator's candidate page for a verb is therefore directly checkable.

## Verified from existing photos (head-on reads, this pass)

| source_key | entry | live total_uses | photo | image | verdict |
|---|---|---:|---:|---|---|
| v008 | بَيَّنَ (ب ي ن) | 523 | **523** | intake_13/IMG_7784 | ✅ verified |
| v027 | عَبَدَ (ع ب د) | 275 | **275** | intake_13/IMG_7790 | ✅ verified |
| v028 | أَخَذَ (أ خ ذ) | 273 | **273** | intake_13/IMG_7790 | ✅ verified |

All three match live exactly → `source-photo-verified-samples.jsonl`. **0 repairs needed.**

## Honest constraint (why not 10+ head-on reads this pass)

The locator-driven method **works** (reading `pg020.jpeg` correctly landed on the located region).
But many corpus shots are **angled with glare**, which makes exact `total_uses` **digit** reads
unreliable (e.g. `pg020` rendered a "to come" entry's count ambiguously vs the live aggregate). The
honest verdict: confident `verified_from_existing_photo` requires a **head-on** crop of the located
page. The `intake_13` batch is head-on (hence 3 clean verifications); the bulk `pgNNN` pages need a
head-on crop pass to scale verification. This is a **read-quality** limit, not a missing-page limit.

## Buckets

| bucket | meaning | count |
|---|---|---:|
| `verified_from_existing_photo` | head-on total_uses == live | 3 (v008, v027, v028) |
| `candidate_located` | page band assigned, head-on crop pending | 2,089 |
| `needs_better_crop` | located but current shot angled/glare | (subset of candidate) |
| `needs_new_photo` | — corpus complete — | **0** |

## Exact next action

1. For a target entry, take its `candidate_page` from the locator → crop that page band head-on →
   read `headword` + `Total uses` → match to live. (Method proven; `tools/verify_source_photo_entry.py`
   + `source_photo_cropper.py` available.)
2. Prioritize the 19 held-back verbs (v004…v151) and `source_data_issue` entries.
3. A discrepancy is **flagged for owner review** (e.g. an aggregate-vs-sub-sense count difference),
   never auto-repaired. No certified repair payload this pass (the 3 reads matched exactly).
