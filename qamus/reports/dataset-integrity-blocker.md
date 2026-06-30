# Dataset-integrity blocker — `qamus/data/current/entries.jsonl` checksum mismatch

Status: **BLOCKED — owner decision required.** This is owner-territory data. Nothing was regenerated, edited,
or hard-gated. The blocked item P2-9 delivers a precise statement of the mismatch plus a NON-FATAL reporter
(`tools/report_dataset_integrity.py`) so CI can observe the drift without breaking. Dry-run; source-clean.

## The mismatch (filesystem facts, this worktree)

`tools/validate_current_qamus_dataset.py` runs purely offline and PASSes every check except the checksum
reconciliation for one file:

| File | Working-tree sha256 | bytes | `checksums.json` expected sha256 | bytes | Verdict |
|---|---|---|---|---|---|
| `data/entries.jsonl` | `a68245e93ce1a8b76858b672a449ff94475abf010e8102575e7c0285c540a78f` | 4 830 755 | `61a53671e62ec1f7b42f18e1444cb8f022d7b4b99b743c2e286c778c851ba19c` | 4 830 763 | **MISMATCH** |
| `data/entries.min.jsonl` | `782f0287…912f2d81` | 374 290 | `782f0287…912f2d81` | 374 290 | match |
| `data/entry-manifest.json` | `d0239eb7…29f13eb8` | 871 | `d0239eb7…29f13eb8` | 871 | match |
| `data/source-keys.json` | `5dc17e46…f5618dd9d` | 88 049 | `5dc17e46…f5618dd9d` | 88 049 | match |
| (7 index files) | — | — | — | — | match |

Only `entries.jsonl` drifts. The drift is **8 bytes** (4 830 755 working vs 4 830 763 recorded).

## It is NOT a CRLF / line-ending artifact

- `.gitattributes` forces `*.jsonl text eol=lf` (and `*.json`, `*.md`, `*.py` likewise), so the working tree
  is normalized to LF on checkout.
- Direct byte scan of the working-tree file: **0 `\r` (CR) bytes**, 2092 `\n` (LF) bytes, total 4 830 755 bytes.
- A CRLF round-trip would have *added* one byte per line (≈ +2092 bytes), not removed 8. The size moved the
  wrong direction and the wrong magnitude for an EOL artifact.

Therefore the two byte-streams differ in **content**, not in line endings. One side is stale relative to the other:
either `checksums.json` was recorded against an earlier/later revision of `entries.jsonl`, or the working-tree
`entries.jsonl` was regenerated without re-running the export's checksum step. The 8-byte / single-file shape is
consistent with a small in-place data edit (e.g. one entry's text changed) whose checksum was never refreshed.

## Why this is owner-territory — and what NOT to do

`qamus/data/current/` is the committed public dataset (2092 entries). Both `entries.jsonl` and `checksums.json`
are authored/exported artifacts under owner control. Without knowing which side is authoritative, any automated
"fix" would silently rewrite owner data:

- **Do NOT regenerate `checksums.json`** to match the working tree — that would bless a possibly-stale
  `entries.jsonl` and erase the evidence of drift.
- **Do NOT edit / re-export `entries.jsonl`** to match the recorded checksum — that would discard a possibly-newer
  edit.
- **Do NOT hard-gate** `validate_current_qamus_dataset.py` in CI while this is open — it FAILs closed (by design,
  correctly), so wiring it as a required gate would red-flag every run on a pre-existing condition this lane is
  not authorized to resolve.

## Owner decision needed

Decide which artifact is authoritative for `entries.jsonl`, then (owner / a data-owning lane, not this one):

1. **If the working-tree `entries.jsonl` is correct** (a real data edit landed): re-run the export's checksum
   step so `checksums.json` records `a68245e9…` / 4 830 755 bytes, and re-derive any dependent index/manifest
   counts. Then `validate_current_qamus_dataset.py` PASSes and can be promoted to a hard CI gate.
2. **If `checksums.json` is correct** (`entries.jsonl` drifted unintentionally): restore `entries.jsonl` to the
   `61a53671…` / 4 830 763-byte revision, then re-validate.

Until that decision lands, the strict validator must remain advisory (run, observe, do not block).

## Interim: observe drift without breaking CI

`tools/report_dataset_integrity.py` (new, this item) re-runs the same sha256 reconciliation as the strict
validator but is **non-fatal**: it prints the per-file match/mismatch list and **always exits 0**. A `--strict`
flag exits 1 when any file mismatches, for the day the owner decision lands and the gate is promoted. Its
`--self-test` proves the logic on SYNTHETIC matching/mismatching file sets only — it does NOT assert anything
about the real (currently-mismatched) dataset, so it stays green and is the only thing wired into
`tools/check_regressions.py` for this item.

```
PYTHONUTF8=1 python tools/report_dataset_integrity.py            # observe (always exit 0)
PYTHONUTF8=1 python tools/report_dataset_integrity.py --strict   # would exit 1 today (the real mismatch)
PYTHONUTF8=1 python tools/report_dataset_integrity.py --self-test
```
