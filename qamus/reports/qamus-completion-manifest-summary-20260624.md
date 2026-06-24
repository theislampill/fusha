# Qamus completion manifest — summary (Phase 4)

The completion manifest is **canonical, not duplicated**: the existing reproducible artifacts ARE the
manifest, now risk-tagged and validator-gated.

## Canonical artifacts

| role | artifact | rows | generator | validator |
|---|---|---|---|---|
| **per-token completion manifest** | `qamus/reports/hover-token-audit-full.jsonl` | 49,900 | `audit_all_hover_tokens.py` | `validate_qamus_completion_manifest.py` |
| **per-entry completion rollup** | `qamus/reports/qamus-2092-entry-matrix.jsonl` | 2,092 | `audit_qamus_2092_entries.py` | `validate_entry_completion_rollup.py` |
| address graph (per-token entry/decision/source links) | `qamus/indexes/current/{source-address-full,quran-usage-spine-full,qamus-entry-field-addresses}.jsonl` | 28,393 / 3,854 / 2,092 | `build_full_source_address_graph.py` | (0 orphans) |

Both gated in `check_regressions.py`. No 9 MB duplicate file is committed — the audit JSONL already
carries `quran_loc, surface_ar, decision_state, public_gloss, conf, blocker, next_action,
sarf_procedure, nahw_procedure, token_decision, risk`; āyah-level `entry_contexts` join via the spine.

## Per-token completeness (49,900 — every token terminal)

| state | count |
|---|---|
| resolved | 41,164 (82.49%) |
| pending (exact blocker) | 8,736 |
| — stem_base_unknown | 6,866 |
| — source_entry_unverified | 1,349 |
| — same_surface_polysemy_requires_i3rab | 520 |
| — proper_noun_no_qamus_entry | 1 |

**Risk taxonomy** (added this phase): `LOW` deterministic high-conf resolved · `MEDIUM` med/low-conf or
2-vote resolved, and stem/source pending · `HIGH` iʿrāb-dependent homograph pending · `SCHOLAR`
proper-noun/owner-gated. No "generic pending" — `validate_qamus_completion_manifest.py` fails on any.

## Per-entry completeness (2,092 — 0 unknown buckets)

terminal `source_photo_status` ∈ {verified, photo_present_needs_visual, repair_ready, missing_locator,
deferred, needs_retake}; per-field status (root-empty-on-noun = curator style, not error); hover
status (resolved/pending/blockers); repair status; **exact `next_action` per entry**.
`validate_entry_completion_rollup.py` enforces 2,092 rows, section split 947/1045/100, 0 unknown.
