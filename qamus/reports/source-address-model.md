# Source-address model (Xanadu-style)

Every fact in this repo has a **stable address** and every derived claim **points back** to the
address(es) it came from. This is the Xanadu idea — content lives at an address, and other
content *transcludes* / references it rather than copying it. Here it does two concrete jobs:

1. **De-duplication** — an address is the canonical identity of a Qamus entry, so two authors
   cannot independently re-create the same work.
2. **Provenance without leakage** — derived views link to addresses (internal evidence) while
   the public render carries only `{src:'qamus', kind:'authored', lang:'en'}`.

## Address grammar

```
qamus:v###          existing/derived Qamus entry, verb class      e.g. qamus:v443
qamus:n###          existing/derived Qamus entry, noun class       e.g. qamus:n621
qamus:p###          existing/derived Qamus entry, particle class   e.g. qamus:p007
quran:S:A:W         a single Qurʾān word — surah:ayah:word index   e.g. quran:43:83:5
wbw:S:A:W           the hover-gloss slot for that word              e.g. wbw:43:83:5
```

- `qamus:` class ids are **frequency-ordered within class** and assigned by
  `scripts/build_existing_qamus_index.py` (verbs follow the printed book order). They are the
  keys of `indexes/existing_qamus_index.min.json`.
- `quran:S:A:W` addresses a Qurʾān **word position**, never altering the text — it is a
  pointer, so the same verbatim word is referenced, never re-typed with changes.
- `wbw:S:A:W` is the live hover slot that a certified gloss eventually fills. The repo only
  *names* these addresses; it does not write them (that's the off-repo `qamus_wbw` rebuild).

An address may carry a **fragment** for the specific thing referenced:

```
qamus:v443#root=خ و ض           the entry's root
qamus:v443#sense=0              the first sense/gloss
qamus:v443#form=خَائِضِينَ        one of the entry's attested forms
qamus:v443#ref=43:83           one of the entry's usage refs
```

(`indexes/existing_qamus_index.min.json` already stores `source_address` as
`qamus:v###=root=...` per record — see `build_existing_qamus_index.py`.)

## Record shape at an address

Each addressed record (as built into the index) carries:

| field | role |
|---|---|
| `source_address` | the canonical address (+ root fragment) |
| `entry_id` | opaque live-entry id (for the apply side; not a URL) |
| `source_keys` | **backlinks**: prior ids/keys this entry was known by (e.g. `["v426"]`) |
| `surface_ar`, `headword`, `root`, `forms[]` | the Arabic surface data |
| `norm`, `norm_strict`, `bare` | match keys (from `tools/normalize_ar.py`) |
| `glosses[]`, `n_senses`, `total_uses`, `usage_refs[]` | the sense + usage data |
| `pos_category`, `section`, `class`, `tags[]` | classification |
| `status`, `visibility` | lifecycle (`reviewed`/`public`, etc.) |

## Repair fields (overlay, never overwrite the address)

A repair does **not** mutate the addressed record in place in this repo. It is an **overlay**
that references the address and proposes field-level changes — so the original remains the
stable target and the diff is auditable:

```json
{
  "op": "repair",
  "target_address": "qamus:v443",
  "repairs": [
    {"field": "senses[0].gloss", "from": "to indulge in falsehood",
     "to": "to indulge in idle / false talk", "basis": "nahw:context"},
    {"field": "usage_refs", "add": ["68:65"], "basis": "quran:68:65:4"}
  ],
  "informed_by": ["qac", "quran.com"],     // INTERNAL
  "public_render": {"src": "qamus", "kind": "authored"}
}
```

`from`/`to` make the change reversible and reviewable; `basis` points at the address (sarf,
nahw, or a `quran:S:A:W` word) that justifies it. `informed_by` is internal evidence only.

## Derived views (transclusion, including OCR)

Higher-level artifacts are **derived views** computed *from* addresses, never from copies:

- **OCR-derived view** — the physical source corpus is OCR'd into structured candidate fields
  that point at the `qamus:` address they will repair/add to. The repo stores the *structured
  derived view* (root, headword, refs as text/JSON) — **never the raw OCR dump and never the
  image**. The image/scan is referenced only as an internal locator (see
  `source-corpus-locator-summary.md`), by rank/page, with no path.
- **Coverage view** — the hover scoreboard is a derived view over `wbw:S:A:W` slots and the
  `qamus:` addresses that resolve them.
- **Frequency view** — `../corpora/` token counts joined to addresses by match key.

Because views transclude (link) rather than copy, fixing the source address fixes every view —
no fan-out of stale duplicates.

## `used_by` backlinks

The inverse of a reference is a backlink. For each address we can answer *"what points here?"*:

```
qamus:v443
  used_by:
    - wbw:43:83:5      (hover slot resolved by this entry's gloss)
    - wbw:52:12:7
    - cand_2026_0001   (an open candidate repairing this address)
    - source_keys←v426 (a prior id that resolves to this address)
```

`source_keys` in the index is the persisted form of one backlink class (prior ids → current
address). Candidate runners add transient backlinks (`cand_*`) so parallel agents can see an
address is already being worked.

## Duplicate avoidance (the payoff)

A new observation is resolved to an address **before** any authoring:

1. Compute `norm_strict(surface)` and the bare root via `tools/normalize_ar.py`.
2. Probe `existing_qamus_index.min.json` by `norm_strict`, `root`, and `forms[]`.
3. **Hit** → `op:"repair"` against that address; show the reviewer the "before".
4. **Miss** → `op:"add"`; a *new* address is reserved **only on certification**, appended after
   the highest id in that class (addresses are append-only and never reused).
5. Before authoring, check the address's `used_by` for an open `cand_*` — if present, defer
   instead of duplicating.

So identity is structural: the address is the dedup key, `used_by` shows contention, and
append-only assignment means no two adds ever collide.

> **Certification caveat (carried from the highlight regressions):** the probe in step 2 uses
> `norm()` for *recall* (gathering possibles) but the **match is only certified on
> `norm_strict()`** (hamza-seat-aware) plus the relevant harakah check — because `norm()`
> would wrongly merge `إيمان`/`أيمان`, `يَأْمُرُونَ`/`يَمُرُّونَ`, and the short-particle
> homographs. A `norm()`-only "hit" is a *suggestion to the reviewer*, not a resolved address.
