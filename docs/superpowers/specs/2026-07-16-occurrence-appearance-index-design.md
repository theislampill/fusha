# Canonical Occurrence-to-Appearance Index Design

## Goal

Build a deterministic, repository-owned index that keeps each corpus `loc` as one canonical occurrence while recording reader and entry-page appearances without merging distinct occurrences that happen to share a normalized surface.

## Inputs and identity

The sibling `data/rh_live_01_beta_whitelist.jsonl` is the reader projection source. Every non-empty row contributes its `loc` as a canonical occurrence and one `reader` appearance. Entry-page evidence comes from a non-canonical `entry_url`, a normalized `source_key`, a known `entry_id`, or explicit entry-example flags. Entry IDs are resolved against `entries.jsonl` by direct ID, `/e/<id>` URL, or numeric-normalized `nNNN`/`vNNN`/`pNNN` source keys.

The entry store is scanned independently. Exact word-level refs are attached directly. Ayah-only refs are attached only to whitelist rows already carrying the same entry-page relationship in that ayah; they are not fanned out to every word. Unresolvable ayah-only references are counted and reported as attribution gaps.

## Output and hash contract

`qamus/indexes/occurrence-appearances.jsonl` contains one sorted JSON object per `loc`:

```json
{"loc":"...","unique":true,"appearances":[{"surface_kind":"reader"}],"appearance_count":1,"entry_relationships":[],"projection_hash":"<sha256>"}
```

The projection hash is SHA-256 over canonical JSON containing exactly `segments`, `glosses`, `morphline`, `root`, and `facts`. In the current whitelist, `glosses` is the pair `token_contribution_gloss`/`contextual_phrase_gloss`, and `facts` is the pair `sarf_facts`/`nahw_facts`; explicit top-level `glosses`/`facts` values are supported for future fixtures. JSON keys are sorted and UTF-8 is used.

## Validation and proof

`tools/validate_appearance_parity.py` validates record shape, count fields, hash syntax, optional per-appearance hashes, duplicate `loc` records, and source rows supplied through `--whitelist`. A repeated `loc` with divergent hashes fails. Different `loc` values with the same normalized surface and ayah context are intentionally allowed and are tested explicitly with `39:63:3`/`22:18:9`.

The validator's self-test is red-first: a synthetic same-`loc` fork must fail, while a same-surface/different-`loc` pair must pass. The real invocation reports source row count, duplicate analysis count, and unresolved entry refs without claiming linguistic correctness, browser impressions, or exact word emphasis where the source lacks it.

## Integration

The builder and validator remain stdlib-only and offline. A focused unittest fixture suite protects the resolver and parity rules. `tools/check_regressions.py` receives one F-B/F-C gate block invoking the validator self-test and the real validator against the committed artifact and sibling whitelist. `IDX-REPORT.md` records the exact commands and verbatim outputs used for closure.
