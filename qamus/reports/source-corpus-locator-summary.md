# Source-corpus locator — summary

How the physical source corpus is *located* so candidate authoring knows **where** in the book
to look for each Qamus root — without this repo storing any image, scan, raw OCR, or path.

> **What this report deliberately omits:** image paths, scan filenames, page-image URLs, OCR
> text dumps, and any private storage location. The locator is expressed only as **rank → page
> number** and **section windows** — portable integers, no bytes.

## The problem

The existing Qamus corpus is **2,092** entries. To repair or extend an entry we need the
*physical page* in the source book where that root is treated, so a reviewer can verify against
the original. Opening the whole book per root does not scale; we need a locator that maps an
entry to a likely page (or a small window of pages).

## Two locator strategies (by class)

### Verbs — Table-of-Contents rank → page

Verbs in the source are ordered, and the book's Table of Contents gives an **ordinal rank** per
verb. Because the printed order is monotonic, a verb's ToC rank maps directly to its page:

```
locate(verb_rank) -> page    via the ToC rank→page table (monotone, exact where ToC is legible)
```

This is exact wherever the ToC line for that rank is legible. The index assigns verb
addresses (`qamus:v###`) in the **same frequency/printed order**, so the address ordinal and
the ToC rank line up, and the locator is a lookup, not a search.

### Nouns (and particles) — section windows

Nouns are grouped by **semantic section** (the categories you see in the 2,092 scoreboard:
*Animals & Birds*, *Plants & Fruits*, *Sky*, *Places*, *Prophets*, …). There is no per-noun
ToC rank, so instead each section maps to a **page window** `[first_page, last_page]`. A noun
is located to its section's window, narrowing the search from the whole book to a handful of
pages:

```
locate(noun) -> [first_page, last_page]   via section→window table
```

## Located vs. needs-search (current figures)

| state | count | meaning |
|---|---:|---|
| **located** | **69** | verb-rank→page resolved, or noun pinned to a tight section window |
| **needs-search** | **87** | ToC rank illegible/missing, or section window too broad to pin — flagged for manual locate |
| total in this pass | 156 | the working set this locator round covered |

- **Located (69)** entries carry a verified page or a tight window and are ready for a reviewer
  to open the source and verify a candidate against it.
- **Needs-search (87)** entries could not be pinned automatically — usually because the ToC
  line for that verb rank is unreadable, or a noun's section window is too wide to be useful.
  These are queued for a manual locate pass; they are **not** blocked from authoring, but their
  candidates stay `pending` until a human can confirm the source page.

## How the locator feeds the bridge

The locator output is an **internal derived view** (see the source-address model): each
located entry gets `{address, page | window, locator_basis}` recorded as evidence under
`provenance.evidence_pointer`. This:

- gives the reviewer in Stage 3 a fast path to the original page;
- never exposes the image or path — only the integer page/window and a basis label;
- lets `needs-search` entries be triaged without copying any scan into the repo.

## Reproducibility (no images in the loop)

The rank→page table and section→window table are the **only** locator artifacts the repo would
carry (as plain JSON/integers). Anyone can rebuild the locator from a fresh ToC transcription
and section list — no image, OCR dump, or private path is required or permitted. If a future
pass converts more `needs-search` entries to `located`, only those integer tables change; the
public reports update their counts and nothing else.
