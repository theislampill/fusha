# Qamus dataset export report

**Source:** live authoritative entry store (`qamus-service/entries/*.json`, 2,092 files, 22.2 MB raw).
**Generator:** `tools/export_current_qamus_dataset.py` (read-only; never writes the live site).
**Schema:** `qamus-entry-public/1.0` (`qamus/schemas/qamus-entry-public.schema.json`).

## Result

| metric | value |
|---|---|
| entries exported | **2,092** |
| — verb / noun / particle | 947 / 1,045 / 100 |
| senses | 3,037 |
| usage blocks | 3,038 |
| example āyāt | 7,700 |
| distinct Qurʾān refs | 3,863 |
| distinct roots | 1,091 |
| distinct lemmas | 2,088 |
| distinct norm_strict surfaces | 2,050 |
| categories | 55 |
| output size (data + indexes) | ≈5.9 MB |

## Sanitization

- **Dropped unknown fields:** none (every live field is explicitly kept or stripped).
- **Stripped private fields:** `author_uid, author_name, last_edited_by, actor_type, created_at,
  updated_at, edit_count, version, versions, status, visibility, image, source` — present on the
  live entries (717 carried version history) and **absent from every exported object**.
- **Leak sweep:** 0 hits for path / email / secret / private-field patterns in the projected
  public objects (export aborts on any hit).
- **Scope:** all 2,092 entries were `status=reviewed` / `visibility=public`; recorded once in
  the manifest, not per entry.

## Source keys

- 2,092 entries, **all** carry ≥1 `source_keys`; **0** entries without a source key.
- Source keys are **unique** (0 duplicated keys across entries).

## Acceptance (P0)

- [x] all 2,092 entries exported
- [x] validator passes (`validate_current_qamus_dataset.py` → VALIDATE OK)
- [x] indexes resolve every entry (by-entry-id == entry set; 0 orphan ids)
- [x] source_keys unique
- [x] no private leakage (0 hits)
- [x] homepage counts match export (947 verb · 1,045 noun · 100 particle = 2,092)
- [x] README explains offline agent use

## Reproduce

```bash
QAMUS_ENTRIES_DIR=.../qamus-service/entries QAMUS_EXPORT_OUT=/tmp/qamus_export \
  python3 tools/export_current_qamus_dataset.py
python3 tools/validate_current_qamus_dataset.py
```
