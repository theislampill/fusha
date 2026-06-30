# Public-runnability matrix

This repo is public, but not every tool runs on a fresh clone. Some need **your own local data** (a QAC export, the
qamus dataset) and some need the maintainer's **private `qamus_wbw` services** package, which is deliberately not
shipped (see [`source-boundaries.md`](source-boundaries.md) §0/§6). This matrix is the honest map so a public clone
never breaks silently. It is kept in sync with reality by `tools/validate_public_runnability.py` (a regression gate).

## Three buckets

### 1. Offline / zero-data — runs on a fresh clone, no env, no data
The engines, validators, and the new learning-runtime tools. Examples (all `--self-test`-able):
`tools/fusha_check.py`, `tools/fusha_text_check.py`, `tools/fusha_governor.py`, `tools/fusha_conflicts.py`,
`tools/fusha_morphology_lattice.py`, `tools/fusha_suggest.py`, `tools/fusha_learner_feedback.py`,
`tools/fusha_cefr_gate.py`, `tools/leak_sot.py`, `tools/normalize_ar.py`,
`tools/fusha_review_scheduler.py`, `tools/fusha_tutor_runtime.py`, `tools/fusha_checkpoint_coverage.py`,
`tools/validate_*` — and the whole `tools/check_regressions.py` gate. These need nothing but Python stdlib.

### 2. Needs your own local data (no private package, but you supply a file)
- `tools/qac_adapter.py` and its callers: need **your own** local QAC TSV (QAC is GPL v3; never bundled — you
  fetch it offline and point the adapter at it). With no TSV the adapter raises a clear `FileNotFoundError`.
- The morphology lattice's optional QAC consult (`tools/fusha_morphology_lattice.py --self-test` runs offline; the
  real QAC-confirmed `root` only appears when you pass a loaded `QacAdapter`).

### 3. Maintainer-only — needs the private `qamus_wbw` services package
These import `qamus_wbw` (the live WBW services). On a public clone they need `QAMUS_WBW_SERVICES` to point at the
package; otherwise they cannot run. They are **builders/exporters of live artifacts**, not part of the public test
gate (none is executed by `check_regressions.py`), so the public CI stays green without them.

| File | Status | Note |
|---|---|---|
| `tools/build_token_irab_decisions.py` | **maintainer_only (graceful)** | guarded `load_qamus_wbw()` → actionable `SystemExit`; `--from`/`--help` run with no services. The model pattern. |
| `tools/build_content_hover_candidates.py` | maintainer_only (guarded) | lazy `load_qamus_wbw()` → `qamus_wbw_adapter.load_services()` in `main()`; imports + `--help` run with no services, run raises an actionable `SystemExit` (P1 done). |
| `tools/build_coverage_yield_ledger.py` | maintainer_only (guarded) | same lazy `load_services()` seam in `main()`. |
| `tools/build_host_lexeme_candidates.py` | maintainer_only (guarded) | same lazy `load_services()` seam in `main()`. |
| `tools/build_language_state_graph.py` | maintainer_only (guarded) | same lazy seam; in `check_regressions` only as an *existence* check. |
| `tools/build_suffix_pronoun_candidates.py` | maintainer_only (guarded) | same lazy `load_services()` seam in `main()`. |
| `tools/build_suffix_pronoun_decisions.py` | maintainer_only (guarded) | same lazy seam; existence-check only in CI. |
| `tools/export_token_hover_decisions.py` | maintainer_only (guarded) | same lazy seam (module global `X` bound in `main()`); existence-check only in CI. |
| `qamus/scripts/export_audit_state.py` | maintainer_only (guarded) | same lazy seam (resolves repo `tools/` from `__file__`). |
| `qamus/scripts/export_hover_state.py` | maintainer_only (guarded) | same lazy seam (resolves repo `tools/` from `__file__`). |

The public-safe seam is `tools/qamus_wbw_adapter.py` (`available()` / `load_services()`): a SIGNPOST, never a stub
that fakes data. All the importers above now call `qamus_wbw_adapter.load_services()` lazily inside `main` (the **P1**
conversion, S16), so each one **imports cleanly and answers `--help` on a fresh clone**, and only raises the actionable
`SystemExit` when actually *run* without services. This matrix + the validator keep the situation honest and prevent
NEW unguarded (module-top-level) importers from sneaking in unrecorded.

> `tools/test_token_irab_help.py` is the public-runnable proof that the maintainer-only `build_token_irab_decisions.py`
> still answers `--help` with no services — it has no `qamus_wbw` import of its own.

<!-- runnability-matrix: {
"shared_adapter": "tools/qamus_wbw_adapter.py",
"public_runnable_proof": "tools/test_token_irab_help.py",
"importers": {
  "tools/build_token_irab_decisions.py": "maintainer_only_guarded",
  "tools/build_content_hover_candidates.py": "maintainer_only_guarded",
  "tools/build_coverage_yield_ledger.py": "maintainer_only_guarded",
  "tools/build_host_lexeme_candidates.py": "maintainer_only_guarded",
  "tools/build_language_state_graph.py": "maintainer_only_guarded",
  "tools/build_suffix_pronoun_candidates.py": "maintainer_only_guarded",
  "tools/build_suffix_pronoun_decisions.py": "maintainer_only_guarded",
  "tools/export_token_hover_decisions.py": "maintainer_only_guarded",
  "qamus/scripts/export_audit_state.py": "maintainer_only_guarded",
  "qamus/scripts/export_hover_state.py": "maintainer_only_guarded"
}
} -->
