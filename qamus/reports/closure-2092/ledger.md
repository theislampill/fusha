# Closure-2092 — implementaudit run ledger

Audit object for the Qamus/engine closure tranche. States: `done` · `in_progress` ·
`blocked_exact` · `deferred_with_owner_gate` · `rejected_as_unsafe`. No item is generically "open".

Updated 2026-06-24. Live coverage at close: **85.87%** (42,849 / 49,900). HEAD: see final report.

| phase | item | state | evidence / exact next |
|---|---|---|---|
| 0 | skill + audit bootstrap | done | ran under implementaudit; ledger under `qamus/reports/closure-2092/` |
| 1 | baseline + gates + repo reality | done | `baseline-20260624.{md,json}`; 9 gates green; verified from live (not memory); found+fixed batch_002 provenance gap |
| 2 | repo-org + report-ergonomics audit | done | `repo-organization-audit-20260624.*`; `tools/check_report_ergonomics.py` added+wired (0 crushed reports) |
| 3 | blocker root-cause ledger | done | `blocker-root-cause-ledger.{jsonl,md}` + `validate_blocker_root_cause_ledger.py` (wired); 7,051 pending → specific root causes, reconciled |
| 4 | root-cause yield ledger v2 | done | `root-cause-yield-ledger.{md,json}`; **corrects prior "86% frontier" → 90% reachable via root-known authoring** (ceiling 92.83%) |
| 5 | source_entry_unverified closure | in_progress | forms_array sub-cause (657) folded into the form-variant batch; `quran_refs_missing` (394) + `source_photo_visual_needed` (49) NOT yet repaired — see resume |
| 6 | stem_base_unknown closure | in_progress | **form-variant sub-lane EXECUTED: +425 live, 0 wrong**. Remaining: host_lexeme_possessive (1,210), missing_qamus_entry new-entry proposals (473, owner-gated), particle/pronoun-miscoded (418) — see resume |
| 7 | remaining iʿrāb + proper noun | deferred | 379 polysemy + 1 proper noun; prior tranche ran 3 iʿrāb tiers; exact next = `build_token_irab_decisions.py` → `token-irab-verify` → apply |
| 8 | full 2,092-entry + live-page crawl | deferred | read-only public crawl not run this session; repo-side rollup exists (`qamus-2092-entry-matrix.jsonl`, 2,092 rows, reconciled); exact next = `crawl_qamus_public_entries.py` (throttled, no login) |
| 9 | grammar-metadata + hover-quality audit | done | `hover-gloss-quality-audit.*`: 42,849 resolved, 91.20% clean, **0 public source-leaks** (provenance invariant proven) |
| 10 | source-photo verification scale-up | deferred | corpus complete; method proven (2 verified); bulk digit-reads need head-on crops; exact next = `source_photo_verify_entry.py` over `source_photo_entry_locator.json` |
| 11 | skill runtime + claude.ai packaging | deferred | Claude Code/Codex install present + verified; claude.ai project pack (`dist/claude-ai/*`) NOT yet built — design in resume |
| 12 | zero-to-fluency + speaking drills | deferred | curriculum present; speaking/production-drill layer + tutor-mode pack NOT yet added — design in resume |
| 13 | corpus-to-Qamus / hadith readiness | deferred | Qur'an + Nawawī40 pipeline present (prior); dedicated readiness audit + Ṣaḥīḥayn owner-gate doc NOT written this session |
| 14 | bidirectional graph audit | in_progress | graph regen invariant green (**0 orphan links**, 28,393 addresses); dedicated `validate_bidirectional_links.py` for all required traversals NOT yet built |
| 15 | apply/build boundary + coverage report | done | +425 applied via scoped qamus deploy loop; before/after measured; rollback artifact kept (`wbw-lookup.prev.json`) |
| 16 | loop until frontier | in_progress | ONE full cycle executed + measured (44.6% approval); continuation documented (resume plan) — not looped to 90% in one session by design |
| 17 | commits | done | A `b9a6ca0`, B `2c50af8`, C (this) — all pushed |
| 18 | final deliverables | done | `final-closure-report-20260624.{md,json}` + this ledger + memory update |

## Rejected as unsafe (the gate working)

- 122 form-variant families rejected by 2-vote (homograph / Form-I-vs-II / active-vs-passive voice
  collisions, e.g. كذبوا, ويقتلون, قتل, ضرب). 28 dropped on author-disagreement. A precise pending
  blocker beats a wrong gloss.
- The naive "free `add_form`" reading of `missing_form_variant` — rejected after sampling proved POS
  mismatch (ظَمَأٌ noun vs verbal entry) and same-root/different-lexeme collisions (بَنِين/بَنَى).

## Not done — exact, no vague "standing by"

The genuine-ambiguity residue is small (~148 `genuinely_ambiguous_pending`); everything else is
authorable. The remaining safe-realizable pool is ~3,473 tokens (ceiling 92.83%) — **90% needs only
+2,061 more**, reachable by repeating the executed lane plus the host-lexeme / new-entry / iʿrāb
lanes. See `next-batch-resume-plan.md` for the exact command chain per lane.
