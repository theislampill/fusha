# F-A governed typed-claim fixtures

These fixtures exercise the authoring boundary introduced by F-A.

- prose-only.invalid.jsonl is a real Qamus row shape with learner prose and segment labels but no governed typed fact bindings. It must be rejected.
- tranche1-canary.valid.jsonl reuses tranche-1's 3:141:4 candidate observation and projection lineage. It is a candidate fixture, not linguistic certification.
- alias-normalization.jsonl proves that input qg-negative becomes canonical qg-negation.
- legacy-valid.jsonl is an internal compatibility record. legacy_valid is never learner-visible and never live-materialized.
- unresolved-language-map.json is the typed internal-status to plain-English learner-statement table consumed by the validator.

No fixture authorizes whitelist changes, renderer changes, deployment, publication, or a linguistic conclusion.
