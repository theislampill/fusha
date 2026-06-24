# Artifact ergonomics report (A1)

The repo must be **dogfoodable** — every committed artifact reviewable by a human and diffable by
an agent. This pass fixed a real defect: large machine-written indexes were committed as **one-line
mega-JSON** (compact `separators=(",",":")`), unreviewable and undiffable.

## Contract (enforced by `tools/check_artifact_ergonomics.py`, gated in `check_regressions.py`)

Reviewer-facing JSON: **indent=2 · sort_keys=True · ensure_ascii=False · trailing newline**.
Large row-record artifacts: **JSONL** (one JSON object per line). Compact single-line is allowed
**only** for `*.min.json` and `checksums.json`. Fails closed on: one-line JSON > 2,000 bytes (not
`.min`), missing trailing newline, escaped Arabic (`ensure_ascii=True` leak), or a top-level JSON
array > 50 elements (should be JSONL).

## Taxonomy (see `artifact-taxonomy.md`)

| class | rule | count |
|---|---|---:|
| `reviewer-facing` | pretty JSON | 66 |
| `canonical-machine` | JSONL row-records | 57 |
| `source-boundary` | provenance / adapters (pretty) | 11 |
| `sample` | `*.sample.*` | 8 |
| `compact-checksum` | `*.min.json` / `checksums.json` | 1 |

## What changed

**Converted to JSONL** (large row-records, line-diffable) + a pretty `*.meta.json` sidecar:
`qamus/indexes/current/source-address-full.jsonl` (28,393 address rows),
`quran-usage-spine-full.jsonl` (3,854 āyah rows),
`qamus-entry-field-addresses.jsonl` (2,092 entry rows).

**Pretty-printed** (indent=2) the navigational lookup indexes (`by-entry-id/source-key/root/lemma/
normalized-surface/quran-ref/category`, `decision-backlinks-full`, `quran_usage_spine`,
`*-proofing-matrix.json`, `qamus-2092-terminal-matrix`, the source-adapter manifests, the Tafsir-MCP
redacted samples, and ~10 other small indexes) — all now multi-line with trailing newlines.

**Renamed `.min.json`** (compact-machine, internal corpus dedup lookup, regenerable from the
reviewable dataset): `qamus/indexes/existing_qamus_index.min.json`.

**Builders updated** so regeneration stays ergonomic: `export_current_qamus_dataset.py` (pretty
indexes + checksums over the pretty bytes), `build_full_source_address_graph.py` (JSONL + meta +
pretty backlinks), `build_existing_qamus_index.py` (`.min.json`). Readers updated:
`query_source_address_graph.py` (JSONL loaders), `corpus_to_qamus_candidates.py` (`.min` path).

## Checksums

`checksums.json` (and the dataset validator) were regenerated over the **pretty** index bytes — the
only bytes that changed are whitespace/newlines from compact→pretty; entry **content is identical**
(same 2,092 entries, same keys, same values). `validate_current_qamus_dataset.py` → VALIDATE OK.

## Acceptance

- [x] ergonomics validator passes (0 violations); wired into `check_regressions.py`
- [x] no one-line mega-indexes remain (only `*.min.json` / `checksums.json` may be compact)
- [x] README + AGENTS explain how humans/agents review artifacts
- [x] dataset validator still passes after reformatting (checksums regenerated intentionally)
