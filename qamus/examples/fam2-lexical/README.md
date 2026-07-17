# FAM2 lexical formation fixtures

These are a small, repo-owned fixture subset for the candidate-only lexical formation producer. They are not the external corpus and do not authorize a whitelist or renderer change.

`entry-fixtures.jsonl` contains only the exact Qamus entry-form evidence needed by `producer-fixtures.jsonl`. `producer-fixtures.jsonl` has eight positive formation cases and eight adversarial cases. The `sufaha-proof` row is the positive worked proof; `sufaha-label-only-canary` is the original label-only shape and must remain typed unresolved.

The pattern registry is closed and named. A pair is usable only when the registered rule matches the written forms exactly. Hamza-seat, defective-spelling, and unsupported `tāʾ marbūṭa` changes are defeaters rather than recall normalizations.
