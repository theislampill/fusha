# Surface-index coverage delta (closure-2092 Phase 1)

Fixes F1: `by-normalized-surface.json` was built from headwords only, so inflected forms already stored
in an entry's `usage[].forms` were miscounted as unresolved. Companion: `.json`.

## What changed

- **Code:** `export_current_qamus_dataset.py` now builds the surface index via shared
  `build_surface_index()` over **headword + every `usage[].forms` token**, and emits a metadata sidecar
  `by-normalized-surface-detail.json` ({nk → [{eid, kind: headword|form, section, root}]}).
- **Regen (repo-local):** `rebuild_surface_index_from_dataset.py` rebuilds the index from the committed
  `entries.jsonl` (the exporter needs the server entries dir; this shares the exact logic — no faked run).
- **Gate:** `validate_surface_index_covers_usage_forms.py` fails closed if any form/headword token is
  absent from the index.

## Before / after

| metric | before | after |
|---|---:|---:|
| `by-normalized-surface.json` keys | 2,050 | **7,125** (+5,075) |
| keys removed | — | **0** (additive-only, asserted) |
| `usage[].forms` keys absent from index | 5,075 | **0** |
| form-bearing keys (carry ≥1 inflected form) | 0 | 5,246 |

## Classification effect (repo-local; coverage unchanged)

Re-running `audit_all_hover_tokens.py` over the corrected index reclassifies tokens whose form is now
found in an entry — **only classification changed, not live coverage** (this tranche does not touch the
live resolver):

| coarse blocker | before | after | Δ |
|---|---:|---:|---:|
| `stem_base_unknown` | 5,595 | 4,874 | −721 |
| `source_entry_unverified` | 1,076 | 1,797 | +721 |
| `same_surface_polysemy_requires_i3rab` | 379 | 380 | +1 |
| `proper_noun_no_qamus_entry` | 1 | 0 | −1 |
| total pending | 7,051 | 7,051 | 0 |

**721 tokens moved out of `stem_base_unknown`** (their form is hosted by an existing entry). In the
root-cause ledger these become `already_entry_form_present_index_miss` (a live index/resolver miss,
**not** authoring) plus host/form lanes — see `open-stem-hygiene-delta.md`. No coverage gain is claimed:
these resolve only when the **live** index/resolver is rebuilt (owner-gated; out of this repo-local scope).

## Collisions

Adding form keys introduces multi-entry keys (one normalized surface hosted by >1 entry). These are not
errors — the detail sidecar records every (eid, kind) hit so a consumer can disambiguate; the audit/ledger
already guard homographs via QAC root + the `norm_strict` collision rules.
