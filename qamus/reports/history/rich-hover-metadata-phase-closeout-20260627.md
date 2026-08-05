# Rich Hover Metadata Phase Closeout - 2026-06-27

Status: repo-only closeout report for the committed rich-hover metadata samples. This report does not mutate live
Qamus, rebuild WBW, restart services, sync mirrors, apply hover decisions, or claim live renderer support.

## Input Truth

- Current sample baseline before this closeout fix: `94cdf3e482fd6733ba6412ab4d6ac81782304798`
  (`Add VN-RICH-20 standard metadata`).
- Rich sample artifacts inspected:
  - P-RICH 01-04 particle/function-token samples.
  - VN-RICH-00 calibration sample.
  - VN-RICH 01-20 standard samples.
- Evidence sidecars inspected: one `*_evidence.sample.jsonl` sidecar for each rich sample.
- Live Qamus was not read or changed by this closeout report.

## Sample Inventory

| Metric | Count |
|---|---:|
| rich metadata sample files | 25 |
| rich evidence sidecar files | 25 |
| rich metadata rows | 412 |
| `rich_candidate` rows | 85 |
| `pending` rows | 148 |
| `token_only_override` rows | 179 |
| `rich_certified` rows | 0 |

Gate distribution:

| Gate | Rows |
|---|---:|
| `two_vote_required` | 319 |
| `never_auto_resolve` | 64 |
| `human_source_review_required` | 29 |

The absence of `rich_certified` rows is intentional. These committed samples are review metadata, blockers, and
token-only teaching records; they are not live-apply payloads.

## Renderer-Safety Andon

A stricter raw surface check found 12 rows where `segments[].surface` concatenated back to the Qur'anic token only
after normalization, not byte-for-byte. That is safe enough for broad morphology review, but unsafe as a renderer
fixture because rich display should be able to project grammar color onto the exact written token.

Corrected sample rows:

- `rich_hover_vn_rich_01_standard.sample.jsonl`: `2:187:49`
- `rich_hover_vn_rich_02_standard.sample.jsonl`: `17:70:12`
- `rich_hover_vn_rich_05_standard.sample.jsonl`: `60:8:15`
- `rich_hover_vn_rich_06_standard.sample.jsonl`: `2:57:6`, `1:7:6`
- `rich_hover_vn_rich_07_standard.sample.jsonl`: `2:38:7`, `55:7:4`
- `rich_hover_vn_rich_08_standard.sample.jsonl`: `1:2:2`
- `rich_hover_vn_rich_14_standard.sample.jsonl`: `114:4:3`, `6:76:15`, `57:27:20`
- `rich_hover_vn_rich_16_standard.sample.jsonl`: `37:69:2`

Regression guard added:

- `tools/check_regressions.py` now checks every committed `rich_hover_*.sample.jsonl` row and requires
  concatenated segment surfaces to equal the exact `surface` string.

## Public Boundary

Evidence sidecar public-payload scan result: `0` public boundary issues across 25 evidence sidecars.

This closeout preserves the standing boundary:

- public hover output remains Qamus-authored only: `src=qamus`, `kind=authored`, `lang=en`;
- internal evidence labels may remain in evidence sidecars;
- source names, MCP labels, QAC labels, Quran.com labels, OCR snippets, and local paths must not appear in public
  hover payloads.

## What This Does Not Prove

- It does not prove live hover coverage or correctness.
- It does not prove the live renderer supports every rich row.
- It does not approve any row for live application.
- It does not replace two-vote, source-triangulation, i'rab, sarf, or nahw gates.
- It does not make `parse_key` the token identity.

## Next Gate

The next safe lane is a read-only rich-metadata/full-corpus reconciliation or an owner-approved renderer/admin
scaffold against these contracts. Live hover apply still requires a separate owner-gated plan with backup,
append-only ledger, rebuild, validation, health check, public readback, public-boundary scan, and rollback path.
