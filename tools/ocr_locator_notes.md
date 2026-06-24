# OCR / locator notes (reusable approach)

How Fusha uses OCR and visual locating **as a discovery aid** when working from a
printed reference (e.g. a physical root dictionary). These are method notes only.
**No private paths, no image data, no scans, and no raw OCR dumps live in this
repo** — see [`../provenance/source-boundaries.md`](../provenance/source-boundaries.md)
§6. What follows is the *technique*, written so it can be re-applied to any page
layout, with none of the material it operated on.

---

## First principle: OCR is discovery, never authority

- OCR (and any visual locator) **proposes** where a root, headword, or example
  *might* be on a page. It never **certifies** anything.
- Every fact that ships — the root letters, the part of speech, the reading of a
  word, the verse reference, the gloss — is **authored and verified by a human**,
  not lifted from an OCR string. OCR output is a pointer, not a source.
- This is scripture-adjacent work. **Visual certification of scripture is
  owner-gated**: a machine reading of a Qurʾanic word is a *candidate* for a human
  to confirm against the canonical text, never a value to commit unseen.

Concretely: an OCR result enters the workflow as a *suggestion to look here*, and
leaves it only after a person has read the actual page and authored the entry.

## The column-crop technique (avoid the verb-margin loop)

Printed root dictionaries are typically **multi-column**, and a root's **verb
forms / conjugation tables often run down a narrow margin** beside the body text.
Naïve full-page OCR tends to:

- **snake across columns**, interleaving an entry's body with the next column's,
  producing garbled, mis-attributed lines; and
- **loop on the verb-form margin** — the repetitive conjugation strip confuses
  line segmentation and the recognizer re-emits the same short tokens, drowning the
  actual headword/definition.

The fix is to **crop to a single logical column before OCR**, so each pass sees one
clean reading order:

1. **Detect column geometry first** (whitespace gutters / projection profile), then
   crop each text column into its own region. Do not OCR the whole page at once.
2. **Exclude the verb-form margin** from the body-text crop — give it its own,
   separate pass (or skip it; the forms are re-derived and human-authored anyway,
   per `normalize_ar.py` form handling). This is what stops the margin loop.
3. **OCR one column-crop at a time**, top-to-bottom, so reading order is
   unambiguous and lines stay attached to their own entry.
4. **Locate, don't transcribe wholesale.** Use the crop's OCR to find *where* a
   headword/root/example sits (a bounding region + a rough string), then hand that
   region to a human to read and author.

The crop is the unit that makes the rest reliable: clean reading order in, a
human-checkable region out.

## Locator output is a pointer, not content

A locator pass should emit, per candidate, something like:

```
{ "page": <n>, "column": <c>, "region": [x0,y0,x1,y1],
  "kind": "headword|root|example|form",
  "ocr_hint": "<rough string, for FINDING only — never published>",
  "status": "needs_human_read" }
```

- `ocr_hint` exists **only to help a person find the spot**. It is not committed as
  content and is not published. Once the human authors the entry, the hint is
  discarded.
- `status` starts at `needs_human_read` and only a human moves it forward. There is
  no automatic promotion from OCR string to committed entry.
- Cross-check the eventual authored root/POS against an **internal** reference
  (e.g. `tools/qac_adapter.py`) and record `informed_by` **internally** — never in
  the public artifact.

## Matching the located word back to a key (do it strictly)

When a located word is matched to a root/sense/entry, key it with
`tools/normalize_ar.py` **`norm_strict`** (hamza-preserving), not the lenient
`norm` — the lenient key drops the hamza seat and harakāt and will mis-certify
(`إِلَيْنَا` is not root `ل ي ن`; `إيمان ≠ أيمان`). For short particles, the harakah
on the **content** letter decides (`مَن` vs `مِن`/`وَمِنَ`, `لِمَا` vs `لَمَّا`) — use
`haraka_on` / `shadda_on` / `is_man_who`. **When unsure, mark `PENDING`** rather
than commit a guess. (Full regression list: `source-boundaries.md` §5.)

## What never leaves the OCR stage

- **No image data, no scans, no page crops** are committed to this repo.
- **No raw OCR dumps** are committed — they are scratch, discarded after a human
  authors from them.
- **No private paths** to where any of the above lived. The location of source
  material is not recorded here.
- The Qurʾanic text a located example points at is reproduced **only** from the
  canonical text, **unaltered** — never from the OCR string.

## Reusability checklist (any printed source)

- [ ] Detect columns; crop to one logical column before OCR.
- [ ] Give the verb-form margin its own pass (or skip it) — never let it loop the body.
- [ ] Treat OCR as a *locator hint*; author + verify every committed fact by hand.
- [ ] Key matches with `norm_strict`; disambiguate particles by content-letter harakah.
- [ ] Prefer `PENDING` over a wrong reading; visual scripture certification is
      owner-gated.
- [ ] Commit no images, no raw OCR, no private paths.
