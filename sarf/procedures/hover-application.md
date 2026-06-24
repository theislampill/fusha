# Procedure — apply a hover gloss to live qamus-highlight

**Invoke when:** a batch of authored glosses has been certified and you intend to apply it live.

**Pre-apply gates (all must hold):**
1. Each decision passed its gate ([`../rules/verb-measure-gates.json`](../rules/verb-measure-gates.json),
   `homograph-risk.md`): `auto_safe` (QAC agrees · one sense · no homograph) or `two_vote` (2 independent checks
   agree on conclusion AND reason).
2. **Empirical `norm_strict` key-collision probe** clean for every key (`homograph-risk.md`).
3. `validate_linguistic_decisions.py` passes (no below-gate, no missing reasoning, no provenance leak, public
   record exactly `{src:"qamus",kind:"authored",lang:"en"}`).

**Apply (the established path — never a direct artifact hand-edit):**
1. Back up the ref: `cp fusha-hover-decisions.tsv fusha-hover-decisions.tsv.bak-<batch>`.
2. Append `norm_strict<TAB>gloss` (skip keys already present).
3. `rebuild.sh` (read-only over entries → expand → validate → build → deploy → restart → smoke).
4. Verify: coverage delta, `+added / ~changed / −removed` (**−0 removed** expected), health 200, the changed
   slots are improvements (spread→certified), a screenshot of a covered page.

**Rollback:** restore `*.bak-<batch>` (or `wbw-lookup.prev.json`) + `rebuild.sh`, or flag-off.

**Forbidden:** hand-editing `wbw-lookup.json`; applying with `−removed > 0` unexplained; entry mutation through
this path (entry repairs use the owner-gated `edit_entry_record` path — see `../../qamus/candidates/repairs/`).

**Test:** the rebuild smoke + `validate_linguistic_decisions.py --self-test`.
