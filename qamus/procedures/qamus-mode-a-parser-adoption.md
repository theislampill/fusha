# Qamus Mode A Parser Adoption

Status: fixture-first contract for source-addressed Qamus cards.

Mode A means:

`entry -> sense -> example card -> visible qword -> canonical/crosswalk source address -> public-safe hover projection -> rendered span -> reverse trace`.

It is not arbitrary-text parsing and it is not a live deployment path by itself.

## Required Consumer Contract

Use the local JSON/JSONL tools before any executor or residual worker tries to infer parser behavior from scattered files:

```powershell
python tools\fusha_analyze_token.py --input token.json
python tools\fusha_analyze_card.py --input qamus\examples\mode_a_thin_slice\source-address-rows.jsonl --out scratch\analysis.jsonl
python tools\fusha_project_hover.py --source-rows qamus\examples\mode_a_thin_slice\source-address-rows.jsonl --analysis scratch\analysis.jsonl --out scratch\public-hover-projection.jsonl
python tools\validate_qamus_mode_a_adoption.py --self-test
```

The stable contract is:

- input: a visible qword/card source-address row;
- output: morphology candidates, syntax/function facts, public hover projection, private trace, edge manifest, rendered/readback fixture, and flywheel artifact;
- public boundary: `src=qamus`, `kind=authored`, `lang=en`, no external source labels or paths in public fields.

No HTTP endpoint is required for this stage. A later service can wrap these commands once the contract is stable.

## P0.5 Gate

Broad P1/P2 parser expansion is blocked until the thin slice passes:

```powershell
python tools\fusha_mode_a.py --source-rows qamus\examples\mode_a_thin_slice\source-address-rows.jsonl --out-dir qamus\examples\mode_a_thin_slice
python tools\validate_qamus_mode_a_adoption.py --self-test --out qamus\examples\mode_a_thin_slice\claim-validation-report.json
python tools\validate_source_artifact_ledger.py --self-test
python tools\validate_human_review_packet.py qamus\examples\mode_a_thin_slice\scholar-packet.sample.json --self-test
python tools\validate_human_review_packet.py qamus\examples\mode_a_thin_slice\owner-packet.sample.json --self-test
```

The gate must fail on:

- a visible qword without a source-address row;
- public/source boundary leakage;
- qg class not in the approved grammar palette;
- segments that do not concatenate to the visible qword;
- missing forward or reverse trace;
- missing private decision backlink;
- all-qword card denominator mismatch;
- required vocalization missing from a fixture surface or card;
- owner/scholar packet without exact question, required evidence, and accept/reject behavior.

## ANDON Handling

An ANDON is a closure object, not a terminal shrug.

For each blocked row/card, route it to exactly one of:

- `fixed_locally_and_revalidated`;
- `deploy_ready_candidate`;
- `already_live_or_noop`;
- `shared_compiler_template_patch`;
- `renderer_qg_fixture_patch`;
- `validator_schema_patch`;
- `source_crosswalk_repair_packet`;
- `owner_decision_packet`;
- `scholar_irab_packet`;
- `narrow_residual_worker_input`;
- `proven_impossible_under_current_authority_with_next_owner_action`.

Forbidden final labels:

- `external_boundary` without next action;
- `validator_unavailable` without validator patch or substitute;
- `template_unsupported` without a template family patch;
- `pending_two_vote` without exact iʿrāb/function question;
- `locally_exhausted` without owner/source gap and next action.

## Minimum Viable Morphology Cutoff

Do not build a large morphology database before these Mode A families stay green:

- attached preposition + host/pronoun, including `لَهُمْ` and later `بِـ` cases;
- verb prefix + stem + subject/object suffix, including `تَعْبُدُوا۟`;
- derivative/participle prefix and plural suffix, including `ٱلْمُبْطِلُونَ`;
- function particles such as `أَمْ` and `أَيَّانَ`;
- full all-qword card denominator with visible qword coverage, including `n0005`.

Each new family should add a source row, public projection, private trace, edge manifest, rendered fixture, and flywheel artifact before it is generalized.

## Human Review Workflow

Owner and scholar packets are not a backlog label. They must be small and action-shaped.

- Maximum default packet size: 25 rows.
- Each row needs source address, surface, exact question, required evidence, allowed decisions, and accept/reject effects.
- Accepted decisions become fixtures, validator cases, sarf/nahw rules, or curriculum examples.
- Rejected decisions update blockers so the same row is not sent through the same failed lane again.

## Freshness

Generated reports and worklists must include:

- `generated_at`;
- `generated_by`;
- `source_head`;
- `source_branch`;
- `supersedes`;
- `stale_after`;
- `status`.

Treat stale artifacts as historical evidence only. Do not use them as live rollout truth.

## Executor Use

For Qamus rollout workers, this substrate should be used to:

- construct all-qword source-address worklists locally before live deployment;
- detect sparse-page false closure;
- preserve clitics, particles, suffixes, and derivative pieces in qg coloring;
- keep public hovers source-clean;
- emit exact owner/scholar/source packets instead of vague blockers;
- feed reusable sarf, nahw, parser, validator, and curriculum fixtures.

Live deployment still belongs to the rollout executor and must run the established source/runtime/readback gates.
