# Rich WBW Segment Role Taxonomy - 2026-06-27

Status: repo-only taxonomy report generated from the latest available sealed
shadow-graph parse-key artifact in `out/`. This is a read-only reconciliation
artifact. It does not mutate live Qamus, rebuild WBW, restart services, sync a
mirror, apply hover decisions, or claim live renderer support.

Generator:

- `tools/summarize_rich_wbw_roles.py --strict`

Input boundary:

- input parse-key rows were read from an ignored local shadow output under
  `out/`;
- the full parse-key JSONL is not committed;
- this report records only aggregate role taxonomy, samples, lanes, and gates.

## Summary

- parse keys: `17065`
- rich parse rows: `12`
- observed roles: `13`
- strict pass: `yes`
- risks: `0`

## Role Classification

All observed rich segment roles are either explicitly allowlisted or explicitly
gated by the current taxonomy. No grammar-sensitive/gated role appears in an
`auto_safe` gate or `propagation_safe` lane.

| Role | Occurrences | Parse rows | Policy | Lanes | Gates |
|---|---:|---:|---|---|---|
| `addressee_bridge` | 1 | 1 | `explicitly_gated` | two_vote_required=1 | two_vote_required=1 |
| `adjectival_state` | 1 | 1 | `explicitly_gated` | two_vote_required=1 | two_vote_required=1 |
| `conjunction` | 5 | 5 | `explicitly_gated` | two_vote_required=5 | two_vote_required=5 |
| `definite_article` | 7 | 7 | `explicitly_allowlisted` | token_only_required=1, two_vote_required=6 | auto_safe=1, two_vote_required=6 |
| `imperfect_prefix` | 1 | 1 | `explicitly_allowlisted` | two_vote_required=1 | two_vote_required=1 |
| `noun` | 7 | 7 | `explicitly_allowlisted` | token_only_required=1, two_vote_required=6 | auto_safe=1, two_vote_required=6 |
| `object_pronoun` | 2 | 2 | `explicitly_gated` | two_vote_required=2 | two_vote_required=2 |
| `preposition` | 1 | 1 | `explicitly_gated` | two_vote_required=1 | two_vote_required=1 |
| `result_particle` | 1 | 1 | `explicitly_gated` | two_vote_required=1 | two_vote_required=1 |
| `resumption_particle` | 1 | 1 | `explicitly_gated` | two_vote_required=1 | two_vote_required=1 |
| `verb` | 2 | 2 | `explicitly_allowlisted` | two_vote_required=2 | two_vote_required=2 |
| `verb_stem` | 1 | 1 | `explicitly_allowlisted` | two_vote_required=1 | two_vote_required=1 |
| `vocative_particle` | 1 | 1 | `explicitly_gated` | two_vote_required=1 | two_vote_required=1 |

## Gate Cases Confirmed

The current shadow role taxonomy still covers the earlier high-risk rich WBW
gate cases:

- `quran:22:18:13` `وَٱلشَّمْسُ`: `conjunction` + `definite_article` + `noun`, all in `two_vote_required`.
- `quran:22:18:14` `وَٱلْقَمَرُ`: `conjunction` + `definite_article` + `noun`, all in `two_vote_required`.
- `quran:22:18:15` `وَٱلنُّجُومُ`: `conjunction` + `definite_article` + `noun`, all in `two_vote_required`.
- `quran:22:18:16` `وَٱلْجِبَالُ`: `conjunction` + `definite_article` + `noun`, all in `two_vote_required`.
- `quran:22:18:17` `وَٱلشَّجَرُ`: `conjunction` + `definite_article` + `noun`, all in `two_vote_required`.
- `quran:2:178:22` `بِٱلْمَعْرُوفِ`: `preposition` remains `two_vote_required`.
- `quran:2:21:1` `يَٰٓأَيُّهَا`: `vocative_particle` and `addressee_bridge` remain `two_vote_required`.

Additional reviewed examples:

- `quran:33:63:1` `يَسْـَٔلُكَ`: `imperfect_prefix`, `verb_stem`, and `object_pronoun`; the object pronoun is gated.
- `quran:26:139:2` `فَأَهْلَكْنَاهُمْ`: `result_particle`, `verb`, and `object_pronoun`; function and suffix remain gated.
- `quran:4:28:6` `وَخُلِقَ`: `resumption_particle` plus passive verb remain gated.

## Interpretation

This report proves only the taxonomy/gate state of the currently committed rich
shadow sample layer. It does not certify public hovers, does not approve
propagation, and does not make `parse_key` a primary identity. Rows with
grammar-sensitive functions remain behind sarf/nahw, two-vote, source-boundary,
and learner-explanation gates.

## Next Gate

The next safe lane is still read-only unless the owner separately authorizes a
live apply plan. Practical options:

- renderer/admin scaffolding against the existing rich display contract;
- further rich metadata reconciliation against a fresh live-readonly shadow graph;
- owner-reviewed two-vote/adjudication work that produces source-clean draft
  decisions but still stops before live mutation.

## Current-HEAD Phase 4 Packet Sanity

Status: current-code validation smoke only. This does not rerun the live
shadow graph, does not reopen Phase 2.9, and does not authorize apply.

- `validated_code_head`: `676be98dd8e35219fae6340d033e325cf5b722bb`
- report-only commits after `validated_code_head` update this evidence note;
  the current branch/report head must be read with `git rev-parse HEAD`
  because embedding a report commit's own hash would make the report stale on
  every commit;
- these report-only commits do not reopen the Phase 2.9 live-shadow graph gate;
- previous live-shadow counts remain historical evidence from their recorded
  run heads; this section proves only that the committed Phase 4 sample packet
  chain still validates under the current code.

Current-HEAD validation evidence:

- `python tools/validate_phase4_closure_tranche.py qamus/examples/phase4_closure_tranche.sample.jsonl`
  -> `PASS`, 2 review-only rows.
- `python tools/validate_phase4_two_vote_requests.py qamus/examples/phase4_two_vote_request.sample.jsonl`
  -> `PASS`, 1 exact-addressed review-only row.
- `python tools/validate_phase4_two_vote_responses.py qamus/examples/phase4_two_vote_response.sample.jsonl`
  -> `PASS`, 1 exact-addressed review-only row.
- `python tools/validate_phase4_gloss_adjudication_requests.py qamus/examples/phase4_gloss_adjudication_request.sample.jsonl`
  -> `PASS`, 1 exact-addressed review-only row.
- `python tools/validate_phase4_gloss_adjudication_responses.py qamus/examples/phase4_gloss_adjudication_response.sample.jsonl`
  -> `PASS`, 1 exact-addressed review-only row.
- `python tools/validate_phase4_hover_decision_plan.py qamus/examples/phase4_hover_decision_plan.sample.jsonl`
  -> `PASS`, 2 exact-addressed review-only rows.
- `python tools/validate_phase4_apply_readiness_manifest.py qamus/examples/phase4_apply_readiness_manifest.sample.json --plan-jsonl qamus/examples/phase4_hover_decision_plan.sample.jsonl`
  -> `PASS`, 1 source-only non-mutating manifest.
- `python tools/validate_phase4_draft_token_decision_ledger.py qamus/examples/phase4_draft_token_decision_ledger.sample.jsonl --plan-jsonl qamus/examples/phase4_hover_decision_plan.sample.jsonl`
  -> `PASS`, 2 source-only non-mutating draft rows.
- `python tools/validate_phase4_owner_authorization_request.py qamus/examples/phase4_owner_authorization_request.sample.json --manifest-json qamus/examples/phase4_apply_readiness_manifest.sample.json --draft-ledger-jsonl qamus/examples/phase4_draft_token_decision_ledger.sample.jsonl`
  -> `PASS`, 1 source-only owner request with authorization not provided.

The Phase 4 sample chain therefore remains a valid owner-review scaffold, not
a live token-decision ledger and not a closure/correctness claim.
