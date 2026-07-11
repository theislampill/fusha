# RM-20 morphline repair apply plan

Status: preparation only. This document authorizes no data mutation, whitelist edit, production action, commit beyond the two prep artifacts, or application of the repairs.

## Frozen authority and inputs

The owner approved only the nine proposal rows whose independent review verdict is `agree`. The exact machine-readable allowlist, payload values, source locations, old and final content-addressed IDs, binding rebinds, fact IDs, expected shadow delta, and refusal fixtures are in `prep/morphline-approved-manifest.json`.

The apply implementation must hash and compare all three inputs before doing any work:

- `.inputs/proposals.jsonl`: `c3a6e461426ca265a494ca9f93cb264115c5281e9d8c8843989688211158c15d`
- `.inputs/reviews.jsonl`: `58ee053dc1afd6bdd307f97ec3f52dd751849dc71b7dc07236c3f16c14ae79a2`
- `qamus/indexes/largelexicon/crosswalk-gap/lane-d/rm20-dryrun-reports.jsonl`: `729455873b1fb8d8de0e7dac461a1102b23a3441b4f38e04d4726a21da1a46d9`

Stop if a hash differs. Stop if the proposal/review join does not produce exactly 9 `agree`, 2 `alternative`, and 3 `insufficient_exemplars` proposal rows. Stop if any approved proposal does not match exactly one merged dry-run row by exact surface plus exact location set, if that row is not `verify_status=PASS`, or if any dependent binding is absent.

## Approved payloads and exact reach

| Proposal payload | Locations that must classify `modify` | Bindings | Old payload | Final payload |
|---|---|---:|---|---|
| `payload:%D9%84%D9%84%D8%B0%D9%89:to-the-one-who` | `12:42:2` | 2 | `chp:97e6c1ab1ec04b6e` | `chp:a1569b8bec4791be` |
| `payload:%D9%84%D9%84%D8%B0%D9%89:to-the-One-Who` | `6:79:4` | 1 | `chp:a9ef13bf2fc79238` | `chp:a7351d01770c5ca2` |
| `payload:%D9%84%D9%84%D9%87:to-for-Allah` | `7:128:9`, `31:12:7` | 4 | `chp:bc83d1f1e105b273` | `chp:926bad4e26ed0dcc` |
| `payload:%D9%84%D8%A7%D8%A8%D8%B1%D8%A7%D9%87%D9%8A%D9%85:Abraham` | `22:26:3` | 4 | `chp:7bb8430940ad0fdf` | `chp:6c8fedefb186acb2` |
| `payload:%D9%84%D9%84%D9%85%D9%84%D8%A7%D8%A6%D9%83%D8%A9:angels` | `7:11:7` | 1 | `chp:856ed8c6da758e72` | `chp:a9b93af17acfff49` |
| `payload:%D8%A8%D9%88%D8%A7%D9%84%D8%AF%D9%8A%D9%87:to-his-parents` | `31:14:3`, `46:15:3` | 9 | `chp:c7f7edff8ad4a9f5` | `chp:a982b01796857636` |
| `payload:%D9%84%D9%82%D9%88%D9%85%D9%87:people` | `7:128:3` | 2 | `chp:081e78afe8ba4372` | `chp:0b6f244faf7a6516` |
| `payload:%D9%84%D9%84%D9%83%D8%A7%D9%81%D8%B1%D9%8A%D9%86:for-the-disbelievers` | `18:100:4` | 1 | `chp:482193d587ab57ec` | `chp:b1547524ab0f1357` |
| `payload:%D8%B6%D8%B1%D8%A7%D8%B1%D8%A7:to-cause-harm` | `9:107:4` | 2 | `chp:fffc4175204a8176` | `chp:199fe78d7f4a282f` |

The merged dry-run report's `new_payload_id` values are marker-only rehearsal IDs with blank morphlines. They are not application IDs. The final IDs above are recomputed from the old payload with exactly two public-payload changes: `morphline` becomes the approved value and `morphline_repair_wave` becomes `RM-20`. Every other payload field remains byte-for-byte equivalent under canonical JSON.

## Apply construction on `tools/rebind_canonical_hover.py`

For each allowlisted payload, in manifest order:

1. Load the `old_payload` and every `old_binding` from its unique merged `qamus.lane_d_rm20_dryrun.v1` row. Confirm the old payload ID, old binding IDs, carrier fields, and dependent count match the manifest exactly.
2. Deep-copy `old_payload`. Set `new_payload.public_payload.morphline` to the manifest's exact `proposed_morphline`; set `new_payload.public_payload.morphline_repair_wave` to `RM-20`; recompute `canonical_payload_id` with `validate_canonical_hover_payload_table.payload_id`.
3. Call `rebind_canonical_hover.build_rebind_report([old_payload], old_bindings, old_payload_id, new_payload)`. Do not hand-build IDs or lineage.
4. Require `schema=qamus.canonical_hover_rebind_report.v1` and `mode=dry_run`. Require the generated payload ID, binding IDs, and counts to equal the manifest.
5. Preserve the report structure exactly: `payload_edge.canonical_payload_id` is the final ID and `payload_edge.supersedes` is the old ID; `tombstone` names the old ID, reason `payload_repaired_pending_binding_rebind`, and final replacement ID; every new binding points to the final payload and has `supersedes=<old_binding_id>`; every old binding receives the matching conflict row and replacement binding ID.
6. Run `rebind_canonical_hover.verify_dataset` before staging any replacement. A non-empty error list is a hard stop.

No whitelist row is added, deleted, or edited. The repair is canonical SHADOW content only.

## Fact-ledger lifecycle

Create one occurrence-scoped `morphline_rendering` fact per binding (26 facts). The open fact-type registry permits this new identifier; do not overload `gloss_contribution`. The manifest gives each exact `morphline_fact_id`, carrier, and value.

Each fact must be appended through the existing `FactLedgerStore` lifecycle, never inserted directly in a terminal state:

1. `candidate`: full `surface_occurrence` identity (`loc`, `entry_id`, `card_id`, `qword_row_id`), exact approved morphline as `candidate_or_value.value`, no competing alternatives, exact proposal-row reasoning evidence, empty votes, and `supersedes=null`.
2. `review_required`: same fact ID and value, with `supersedes=<same fact_id>` and the independent `Opus-author` approval bound to the exact proposal row.
3. `certified`: same fact ID and value, with both independent approval votes and evidence references:
   - `voter_id=Opus-author`, `vote=approve`, `evidence_ref=rm20-proposal-row:<input_row_ordinal>`, `independent=true`;
   - `voter_id=Codex-reviewer`, `vote=approve`, `evidence_ref=rm20-review-row:<input_row_ordinal>`, `independent=true`.
4. `materialized`: only after the final payload and replacement bindings validate, append the same fact ID, value, evidence, and two votes with `supersedes=<same fact_id>` and materialization target `canonical_hover_payload.public_payload.morphline`.

The manifest binds each payload to its exact proposal/review row ordinal and evidence IDs. The proposal evidence must carry the author row's exact `proposed_morphline` and reasoning; the review evidence must carry the matching `agree` verdict and independent reasoning. Pin one apply timestamp and the three frozen input hashes in provenance. Validate the append-only ledger before projection, require `certified`, then validate it again after projection and require `materialized`. Any collision, illegal transition, missing evidence reference, changed fact ID, or wrong current state is a hard stop.

## Red-first refusal gate

Before enabling the positive path, exercise all five `refusal_fixtures` from the manifest. The tooling must reject them before payload construction, lineage generation, ledger append, or shadow compilation:

- The two `alternative` proposals (`19:32:2` and `7:39:3`) return `tie_unresolved`. Their proposed text is not allowlisted even where the reviewer considered the value usable, because value-and-reason agreement was not reached.
- The two distinct `5:6:56` qg-lam proposal rows and the `9:62:4` qg-lam proposal row return `blocked_insufficient_convention_exemplars`.

The red test fails if any refusal fixture reaches `build_rebind_report`, produces a ledger candidate, changes a payload/binding, or appears in the modify set. The positive path must accept only IDs in `apply_allowlist_payload_ids`; absence from that list is itself sufficient refusal.

## Predeclared SHADOW delta and post-apply gates

The expected `modify` location set is exactly:

`6:79:4`, `7:11:7`, `7:128:3`, `7:128:9`, `9:107:4`, `12:42:2`, `18:100:4`, `22:26:3`, `31:12:7`, `31:14:3`, `46:15:3`.

Compare sets, not only counts. Exact equality is expected. Any additional modify, any missing expected modify, any append/remove/conflict/blocked classification caused by this repair, or any appearance of `5:6:56`, `7:39:3`, `9:62:4`, or `19:32:2` in the changed set is an alert and a hard stop.

Required application-time checks:

- Re-run the 9 final report constructions and `verify_dataset`; require 9 reports, 26 dependent bindings, 26 replacement bindings, and 26 matching tombstone conflicts.
- Validate all payloads and bindings with the canonical table validators and recompute every content-addressed ID.
- Validate all 26 fact histories as `candidate -> review_required -> certified -> materialized` with the two named engines.
- Compile SHADOW twice from the same inputs and require byte-identical output.
- Compare the exact modify location set to the predeclared set and require no other delta class.
- Re-run artifact ergonomics, source-boundary, and repository regression checks before any owner-gated application commit.

Rollback is lineage-preserving: do not delete history. If a post-stage gate fails, abandon the staged generation before promotion. If failure is discovered after an owner-authorized promotion, append replacement payload/binding and ledger revisions that supersede the RM-20 results; never resurrect old rows by erasing tombstones or ledger history.

## Done when

Preparation is complete when the manifest parses, all nine approved payloads uniquely join to PASS dry-run reports, all final payload/binding/fact IDs recompute, the five refusal fixtures are exhaustive, the predeclared modify set equals the union of approved locations, repository checks pass, and the commit contains only this plan and `prep/morphline-approved-manifest.json`. Application remains a separate owner-gated task.
