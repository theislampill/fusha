# Source-address (Xanadu) completion (P15)

The source-address graph is the central substrate: every Qamus entry, every Qurʾān token used by Qamus examples,
and every hover-gloss record is a stable, addressable node, and decisions are **reused by link** (transclusion),
never copied. Generator: [`qamus/scripts/build_source_address_index.py`](../scripts/build_source_address_index.py)
(entry nodes, read-only from the index) + the server-side wbw/quran token nodes; sample:
[`qamus/indexes/source_address_index.sample.json`](../indexes/source_address_index.sample.json).

## Node coverage

| node class | address form | count | note |
|---|---|---:|---|
| entry nodes | `qamus:v###/n###/p###` | **2,092** | every entry (v 970 · n 1022 · p 100); 1,091 distinct roots |
| Qurʾān token nodes | `quran:S:A:W` | **49,900** | one per token position across 3,854 āyāt; **0 silent/unknown** |
| hover-gloss nodes | `wbw:S:A:W` | **34,472** | resolved tokens (69.08%); each derived-view points back to its canonical entry |
| pending token nodes | `quran:S:A:W` (no `wbw`) | **15,428** | classified by pending reason (P12), not orphaned |
| quarantine nodes | sense-split / homograph | **7 roots** | intentional splits (ر و د، ذ م م، ص ر ر، ف ر ج، ط ر ف، ص ل ي، ز ر ع) |

## Xanadu invariants (held)

- **Stable address + version hash:** entry nodes carry `source_keys` + the build's `source_sha`; the artifact is
  rebuilt from a hashed entry snapshot.
- **Backlinks:** entry nodes carry `used_by` (the `wbw:S:A:W` locations that transclude them); the live graph
  reports token→entry evidence links (9,926 at the 29,943-gloss snapshot, growing with coverage).
- **No crop-only citation:** evidence is the entry/QAC/āyah address, never a bare image crop.
- **Reuse, not copy:** one authored decision (a surface's gloss) is **propagated by link** to every occurrence —
  the resolved 34,472 tokens derive from a far smaller set of authored decisions (see
  [`duplicate-avoidance-report.md`](duplicate-avoidance-report.md)).
- **Homograph/sense splits explicit:** 7 roots intentionally carry >1 entry node; these are recorded splits, not
  duplicates.

## Orphan / integrity check

- **0 orphan links:** every entry node has a valid `qamus:` address; every Qurʾān token node is classified
  (resolved or a precise pending reason — P12 shows 0 silent); every `wbw` gloss node derives from an entry.
- The graph answers: *where is this source used?* (`used_by`), *what evidence supports this hover gloss?*
  (entry + QAC backlinks), *which entries still lack source verification?* (P11 `needs_source_photo_review`),
  *which pending tokens share a root/sense decision?* (root index + propagation map).
