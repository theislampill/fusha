# Xanadu source-graph completion

Status of the operational source-address graph. Builders: `tools/build_source_address_index.py` (entry nodes), `tools/build_decision_backlinks.py` (backlinks), `tools/build_language_state_graph.py` (key-states).

| component | state |
|---|---|
| stable addresses (11 families) | defined (`qamus/schemas/source-address.schema.json`) |
| entry nodes | 2092 |
| resolved key-states with backlinks | 120 |
| intentional homograph splits | 159 keys + 7 roots |
| every hover decision has a source address | yes (key-state id) |
| every repair has a field address (`repair:<batch>#field=`) | yes (كَظِيم repair recorded) |
| orphan links | **0** |
| duplicate authoring prevented | yes (reuse-by-backlink) |

Acceptance: 0 orphan links; every hover decision addressed; every repair field-addressed; duplicate authoring prevented by graph lookup. Remaining work tracked by the entry source-photo queue (`qamus/reports/retake-source-photo-requests.md`).
