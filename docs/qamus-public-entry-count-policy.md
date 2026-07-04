# Qamus public entry-count policy (2092)

**Status:** adopted 2026-07-04. Machine-enforced by `tools/validate_public_entry_count.py`
(wired into `tools/check_regressions.py`, alongside the pre-existing
"entries.jsonl has 2092 entries" check).

## 1. The authoritative public count

The public Qamus dataset is **2092 entries**:

| Section | Count |
|---|---|
| noun | 1045 |
| verb | 947 |
| particle | 100 |
| **total** | **2092** |

Verified 2026-07-04 across three surfaces that all agree:
- `qamus/data/current/entries.jsonl` → 2092 lines, section split 1045/947/100.
- `qamus/data/current/entry-manifest.json` → `entry_count: 2092`, `section_counts` identical.
- Live served entries dir → 2092 files, same split, 0 parse-fails, all `status=reviewed`.

**Live == public == manifest == 2092. There is no drift.**

## 2. Internal / projection counts are NOT the public count

Index and projection layers count *other things* and must never be reconciled by adding public
entries:

- The **largelexicon qword crosswalk** projects **117,117 qword rows** (85,877 accepted) — a
  word-occurrence denominator, not entries.
- Index files carry counts like `distinct_lemmas: 2088`, `distinct_norm_surfaces: 2050`,
  `distinct_quran_refs: 3863`, `category_count: 55` — none of which is the entry count.

A prior ledger note of **"live 2096 vs public 2092 (+4 drift)"** was such a
projection/transient artifact. As of 2026-07-04 **no count key equals 2096** anywhere in
`qamus/indexes` or `qamus/data` (the only "2096" substrings are incidental — e.g. quranic
coordinate fragments). The +4 is **not** four missing public entries.

## 3. The rule

> **2092 is the authoritative public entry count. An internal/projection mismatch is not a signal
> to expand the public dataset. Do NOT add public entries to make a projection number line up.**

Real growth of the public dataset happens **only** through owner-approved authoring of genuine new
entries — at which point `EXPECTED_TOTAL` / `EXPECTED_SECTIONS` in
`tools/validate_public_entry_count.py` are bumped **consciously** in the same change. The guard
exists to make accidental drift (a stray add/remove, a section swap that keeps the total, a
manifest that falls out of sync with `entries.jsonl`) fail loudly in CI.

## 4. What the guard checks

`validate_public_entry_count.py` asserts, on the real dataset: `entries.jsonl` line count ==
manifest `entry_count`; `sum(section_counts) == entry_count`; section counts recomputed from
`entries.jsonl` == manifest `section_counts`; no section outside `{noun, verb, particle}`; and the
total + split equal the tripwire constants (2092; 1045/947/100). The live-served side is
additionally covered by the ops-repo `smoke-qamus-entries-integrity.sh` (every entry parses + has a
valid section).
