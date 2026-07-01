# Private Acquisition Cache Policy

Largelexicon may use private acquisition caches to consult QAC, Tafsir MCP,
Quran.com-style visual checks, source photos, OCR, and future source adapters as
internal evidence. Those raw records are private and never committed to this
public repo.

## Artifact Buckets

- `raw_private_cache`: raw TSV, MCP/API response, source-photo/OCR output,
  tokens, request logs, retry logs, and rate-limit data. This bucket is private
  and never committed.
- `normalized_private_fact`: parsed root/POS/i'rab/source-address facts derived
  from private cache. This bucket is still private unless projected.
- `source_clean_projection`: committed candidate/support rows that carry only
  Qamus-authored or factual fields and the public invariant `src=qamus`,
  `kind=authored`, `lang=en`.
- `executor_live_state`: live whitelist, service state, source/runtime parity,
  DOM/mobile readback, DUV/static state, backup, rollback, and closure claims.
  This bucket is owned by the Qamus executor, not by Fusha.

## Projection Rule

Private evidence can inform a source-clean projection, but the projection must
not carry raw cache pointers, copied wording, source labels, OCR snippets,
private paths, service paths, tokens, or process prose. Public-facing hover rows
remain Qamus-authored.

## Required Fields

Every acquisition manifest should record `generated_at`, `generated_by`,
`source`, `source_version`, `request_key`, `raw_sha256`, `projection_status`,
`rate_limit_policy`, `resume_cursor`, `stale_after`, and `status`.

Every source-clean projection should record `schema`, `fact_class`,
`source_address`, `public_boundary`, `generated_at`, `generated_by`,
`source_head`, `supersedes`, `stale_after`, and `status`.

## ANDON

If a projection needs copied external wording, it is not a projection; route it
to Qamus authoring. If raw evidence is accidentally staged, stop and quarantine
the file before continuing.
