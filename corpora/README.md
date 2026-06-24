# corpora/

Local, catalogue-first staging area for the Arabic-language corpora that feed Fusha's
lexicon work. A *corpus* here is a defined body of Arabic text whose **surface vocabulary**
we catalogue, diff against the existing Qamus, and stage as reviewable candidates. The
Qurʾanic lexicon (the 2,092 Qamus entries) is the spine; everything else is additive and
owner-gated.

## What lives here

```
corpora/
  README.md                  ← this file
  sources/
    SOURCE-CATALOGUE.md      ← every language source + how it was accessed (citation labels)
  nawawi40/
    out/                     ← pilot outputs (raw tokens, lexeme candidates, diff)
  sahihayn/
    PLAN.md                  ← FUTURE expansion plan (no hadith content staged yet; owner-gated)
```

The active pilot is **nawawī40** — al-Arbaʿīn al-Nawawiyyah (the "Forty", ḥadīth 1–42 with
Ibn Rajab's additions). It is small, canonical, and lets us prove the catalogue → diff →
candidate pipeline end-to-end before anything larger.

## Hard rules (non-negotiable)

1. **No raw text is committed by these tools.** Corpus dumps you feed in (the Arabic matn)
   are *inputs you point at with `--src`*, not artifacts this repo redistributes. The
   pipeline writes **vocabulary catalogues and candidates**, not source paragraphs. Do not
   commit raw OCR dumps, image data, or full source paragraphs into this tree.
2. **Qurʾān / ḥadīth text is read-only.** Surface forms are preserved verbatim; nothing is
   reshaped, corrected, or re-pointed. It is scripture and sacred tradition — the owner
   verifies every gloss.
3. **External references are evidence, never content.** Quran.com, the Quranic Arabic Corpus
   (QAC), Tanzil, sunnah.com, named dictionaries — you may **name** them as `informed_by` /
   `access_method` labels in the catalogue, but you must **never copy their gloss text**.
   Anything that could reach the public hover artifact carries `{"src":"qamus","kind":"authored"}`
   and an authored-only draft.
4. **No private paths, no secrets, no live-site code.** Citation labels only — never machine
   paths, IPs, or service internals.
5. **PENDING beats a wrong gloss.** Every ambiguous candidate is routed to human review, not
   auto-certified. The normalization guardrails (see below) are there to keep a verb gloss off
   a noun, a name out of a root, and a homograph particle from being decided by bare letters.

## The pipeline (catalogue-first)

All three scripts are stdlib-only and import `tools/normalize_ar.py`. None touch the network
or any live service.

| stage | script | reads | writes |
|---|---|---|---|
| 1. catalogue | `qamus/scripts/catalogue_nawawi40.py` | local matn dump (`--src`) | `nawawi40.raw_tokens.jsonl`, `nawawi40.lexeme_candidates.jsonl` |
| 2. diff | `qamus/scripts/diff_against_qamus.py` | `existing_qamus_index.json` + lexeme candidates | `nawawi40.diff_against_quran_qamus.jsonl` |
| 3. stage | `qamus/scripts/make_candidate_payloads.py` | the diff + the index | `nawawi40.new_entries.candidate.jsonl`, `nawawi40.occurrence_augments.candidate.jsonl`, `nawawi40.review_queue.jsonl` |

### Run the nawawī40 pilot

```bash
# 0) (once) build the Qamus index from a local export of the 2,092 entries:
python qamus/scripts/build_existing_qamus_index.py --entries <local-entries-dir>

# 1) catalogue the surface vocabulary of the Forty (point --src at YOUR local matn dump):
python qamus/scripts/catalogue_nawawi40.py \
    --src corpora/nawawi40/nawawi40.matn.jsonl \
    --access-method "<named edition / public dataset label>" \
    --out corpora/nawawi40/out

# 2) diff every distinct surface form against the existing Qamus:
python qamus/scripts/diff_against_qamus.py \
    --index qamus/indexes/existing_qamus_index.json \
    --lex   corpora/nawawi40/out/nawawi40.lexeme_candidates.jsonl \
    --out   corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl

# 3) stage reviewable candidates (nothing is published):
python qamus/scripts/make_candidate_payloads.py \
    --diff  corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl \
    --index qamus/indexes/existing_qamus_index.json \
    --out   qamus/candidates/nawawi40
```

### Input shape for `--src`

A JSON list, a `{"access_method": "...", "hadith": [...]}` object, or JSONL — one ḥadīth
object per line. Each object:

```json
{"ref": "nawawi:1", "ar": "<Arabic matn>", "title": "...", "access_method": "<optional>"}
```

The `access_method` is a **citation label** describing the named edition or public dataset the
Arabic came from — recorded into every output record's provenance. It is never a file path or
a URL to copyrighted gloss text. See `sources/SOURCE-CATALOGUE.md`.

## Classification buckets (stage 2)

Every distinct surface form lands in exactly one bucket:

- `already_in_qamus` — matches an existing entry at the **hamza-aware** `norm_strict` key (or
  one of its inflected `forms`). The only auto-certified path. No work.
- `new_surface_for_existing_lemma` — a new surface of a lemma Qamus already has → stage an
  **occurrence augment**.
- `new_lemma_existing_root` — the root exists in Qamus but this looks like a different lemma on
  it → human confirms before a new entry.
- `new_root_or_unknown_root` — genuinely new lexis → author an original entry.
- `particle_or_construction_candidate` — short function word / proclitic-glued cluster; a
  **diacritic homograph** (مَن/مِن، لِمَا/لَمَّا، كُلّ/كَلَّا …). Decided by the harakah-aware checker
  in `normalize_ar.py`, never by bare letters.
- `uncertain_needs_review` — lenient (`norm()`) match only, with weak/hamza-letter risk → do
  **not** auto-fold.

## Normalization guardrails (why three keys)

`tools/normalize_ar.py` is the single source of truth — **reference it, do not redefine it.**

- `norm_strict()` keeps the hamza seat → it is the only key allowed to *certify* a match
  (إيمان ≠ أيمان; إِلَيْنَا is **not** root ل ي ن).
- `norm()` is lenient *recall only* — never enough alone to declare a match.
- `bare()` keeps every base letter distinct → used to peel clitics for a conservative root tie.
- The harakah helpers (`haraka_on`, `shadda_on`, `is_man_who`) decide short homographs by the
  vowel on the **content** letter (which may sit after a و/ف proclitic — وَمِنَ is "and from",
  not "and whoever").

These exist because the live qamus-highlight pass learned them the hard way: verb glosses must
not land on nouns (رَسُولًا ≠ "to send"; ٱبْن/بَنَات ≠ "to build"), proper names are not verbs
(مُحَمَّد ≠ "to praise"; صَٰلِحًا ≠ Prophet Ṣāliḥ), and same-root polysemes need context.

## Status

- **nawawī40** — pilot; pipeline ready, candidates are review-staged (never published).
- **sahihayn** — planned only. See `sahihayn/PLAN.md`. No ḥadīth content is staged or
  committed; expansion is owner-gated.
