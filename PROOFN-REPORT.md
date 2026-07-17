# PROOF-N noun proof: سُفَهَاءُ

Status: candidate, deploy-shaped, pre-deploy. No whitelist, renderer, live, publication, or scholarly mutation was performed.

Owner acceptance (§13): demonstrate the COMPLETE chain — entry → sense → card → selected word → source/card evidence → display-local/canonical crosswalk → canonical occurrence → certified typed facts → shared compiler → rich-at-rest projection → rich hover → every repeated appearance → public readback target → reverse trace to entry/card/source.

## Chain walk-through

The proof uses documented lexical entry 1ffcc554ec44 and retains page-context entry c59a0161fac8 as a separate edge. The actual occurrence is 2:13:12, surface السُّفَهَاءُ, with card reference 2:13.

- entry — deterministic_exact — input:data/entries.jsonl#line=265#id=1ffcc554ec44 — documented lexical entry selected from the exact plural form
- sense — deterministic_exact — entry:1ffcc554ec44:senses[0]
- card — candidate — input:data/rh_live_01_beta_whitelist.jsonl#line=1364#loc=2:13:12#card_ref=2:13
- selected_word — candidate — qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:54c633bbaabb72002edd2ba9
- source_card_evidence — deterministic_exact — input:data/rh_live_01_beta_whitelist.jsonl#line=1364#loc=2:13:12
- selected_example — candidate — qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:076e86e4bb4404f69974aaad
- display_local_to_canonical_crosswalk — deterministic_exact — qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:5ef40f9222187549c2f514c7
- canonical_occurrence — deterministic_exact — qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:2ba28ea66a334b5f3270e82e
- typed_facts — candidate — qamus/examples/proof-noun-sufaha/sufaha-contract.json#/facts
- certified_fact_attachment — candidate — qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:e15da4d21e3f398141e58444
- shared_compiler — candidate — tools/fd_compiler.py#build_sufaha_contract+build_sufaha_payload
- at_rest_projection — candidate — qamus/examples/proof-noun-sufaha/sufaha-normalized-public-payload.json#/at_rest_spans
- compact_projection — candidate — qamus/examples/proof-noun-sufaha/compact-projection.json
- expanded_sarf_projection — candidate — qamus/examples/proof-noun-sufaha/expanded-sarf.json
- expanded_nahw_projection — candidate — qamus/examples/proof-noun-sufaha/expanded-nahw.json
- rich_hover — candidate — qamus/examples/proof-noun-sufaha/rich-hover.json
- repeated_appearances — candidate — input:qamus/indexes/occurrence-appearances.jsonl#line=115#loc=2:13:12
- public_readback_target — declared_not_measured — qamus/examples/proof-noun-sufaha/readback-target.json
- reverse_trace — candidate — qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge_type=reverse_trace_edge

## Owner list and evidence

| Item | Compiled result | Evidence address |
| --- | --- | --- |
| lexical entry | 1ffcc554ec44; documented plural سُفَهَاء | input:data/entries.jsonl#line=265#id=1ffcc554ec44 and entry:1ffcc554ec44:usage[0].forms[1] |
| page-context entry | c59a0161fac8, retained as page context | input:data/rh_live_01_beta_whitelist.jsonl#line=1364#loc=2:13:12 |
| sense/card/example | sense:1ffcc554ec44:s1; card 2:13; occurrence 2:13:12 | entry:1ffcc554ec44:senses[0]; input:data/rh_live_01_beta_whitelist.jsonl#line=1364#loc=2:13:12; qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:076e86e4bb4404f69974aaad |
| selected word | selected-word:repair:sufaha:2:13:12 | qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:54c633bbaabb72002edd2ba9 |
| canonical occurrence | quran:2:13:12 | qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:2ba28ea66a334b5f3270e82e |
| display/local crosswalk | exact السُّفَهَاءُ reconstruction | qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge:5ef40f9222187549c2f514c7 |
| certified facts | 11/11 certified and attached | input:canary-sufaha/sufaha-evidence.jsonl#line=1#fact=1 through input:canary-sufaha/sufaha-evidence.jsonl#line=11#fact=11; decision-evidence edges |
| shared compiler | tools.fd_compiler → proofn.payload.sufaha.v1:ba3b758e79f88bf5505c638645ca79f17431404ced04270437b4ac73d6324c8c | tools/fd_compiler.py#build_sufaha_contract+build_sufaha_payload |
| at-rest spans | article ال (0,2) + lexical body سُّفَهَاء (2,11) + final ُ (11,12) | qamus/examples/proof-noun-sufaha/sufaha-normalized-public-payload.json#/at_rest_spans |
| Ṣarf | سَفِيه / سُفَهَاء; فَعِيل / فُعَلَاء; root س ف ه; removed ي; introduced ا and ء | input:canary-sufaha/sufaha-evidence.jsonl#line=1#fact=1 through input:canary-sufaha/sufaha-evidence.jsonl#line=8#fact=8 |
| Naḥw | final ُ is nominative, not plural-forming; governor آمَنَ; explicit subject relation | input:canary-sufaha/sufaha-evidence.jsonl#line=10#fact=10 and input:canary-sufaha/sufaha-evidence.jsonl#line=11#fact=11 |
| rich hover | shared payload id; public labels Ṣarf — how this piece forms the word / Naḥw — what this piece does here | qamus/examples/proof-noun-sufaha/rich-hover.json |
| repeated appearances | 2/2 indexed appearances carry the same payload id | input:qamus/indexes/occurrence-appearances.jsonl#line=115#loc=2:13:12 and rendered-appearance edges |
| reverse trace | entry → selected word and card → selected word retained | qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl#edge_type=reverse_trace_edge |

## Typed graph and validation

The EDGES candidate repair chain is retained and extended with projection_input_edge and certified_fact_attachment_edge, converting the prior graph-attachment blocker into a candidate graph path.
The generated graph has 35 records. Every record is qamus.graph_edge.v1 and has evidence plus status candidate or deterministic_exact.
The ten existing typed-graph checks are recorded at qamus/examples/proof-noun-sufaha/typed-edge-validation.json.
The committed harness invokes the proofn validator against this fixture; it does not read external source paths.

## Boundary and honest limits

authorization_state=pre_apply_not_authorized; live_mutation_allowed=false; public_materialization_allowed=false.
The public readback target is declared_not_measured. No live deployment or public server readback was attempted.
The جامد/مشتق classification tension is retained as unresolved and is not used to create or alter any certified fact.
The final nominative ُ is a Naḥw overlay. It is outside the lexical body and never treated as plural-forming.
Any screenshot produced by the local render witness is local-only; no PNG is tracked.
