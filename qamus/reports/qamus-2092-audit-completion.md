# Qamus 2,092 mechanical audit completion

> **Status vocabulary (honesty):** this report proves **mechanical rollup completeness only** — all 2,092
> entries are **mechanically classified** with terminal rollup fields and 0 unknown buckets. It does **not**
> mean every entry is **hover-complete**, **source-photo-verified**, or **live-page-crawled**; those are
> separate states tracked per-field and are not implied by "audited" here.

Matrix: `qamus/reports/qamus-2092-entry-matrix.jsonl` (2,092 rows, one per entry).

Row keys: entry_id, source_keys, category, root, lemma, section, source_photo_status, field_status{headword,root,forms,senses,counts,total_uses,quran_refs}, hover_status{complete,resolved_tokens,pending_tokens,blockers}, repair_status, next_action.

Terminal-state rules enforced:

- no 'unknown' bucket — every status is from a controlled vocabulary;

- source_photo_status is never 'needs_retake' by default (corpus is complete: 0 missing pages per the rescue audit) — un-verified entries are `photo_present_needs_visual`;

- 'missing' field statuses carry a reason (e.g. proper-noun entry has no triliteral root);

- next_action is exact and per-entry.

Top remaining work: 1,781 entries have ≥1 pending hover token; 1,963 entries await source-photo visual verification.
