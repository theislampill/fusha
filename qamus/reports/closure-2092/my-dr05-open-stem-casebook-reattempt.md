# DR05 — open-stem casebook / unsafe families — my re-attempt (2026-06-25, HEAD d67f873)

The backlog is fully differentiated: `review-only-casebook.jsonl` holds **1,606 families across 9 buckets**, each row carrying bucket / family_key / root_cause / gate / generator / validator / next_command / contributes_to_90 — i.e. an open-stem-casebook-v2 already. Structural reroutes (هدي already-present → reindex; أتي/رأي flattened), function-word lanes, owner-gated missing entries (52), and frozen scar fixtures (كذبوا/ويقتلون/فاستقيموا/جاءني, all REJECT in the gate) are each routed to the correct lane with the correct gate.

| id | status | blocks | finding | remaining |
|---|---|---|---|---|
| DR05-1 | **false_positive** | — | Backlog is one undifferentiated pile | none — fully differentiated |
| DR05-2 | **confirmed_fixed** | — | Structural reroutes (هدي already-present, أتي/رأي unflattened) still mis-routed | owner-gated live reindex for index-miss families |
| DR05-3 | **confirmed_fixed** | — | Unsafe families must be frozen as rejection fixtures | none |
| DR05-4 | **confirmed_fixed** | 90% | True missing-entry families need owner-gated proposals | owner decision to author entries |