# Reference — dependency candidate fields

The field contract for a governor/dependency edge. **The source of truth is the committed schema**
[`qamus/schemas/dependency-candidate-lattice.schema.json`](../../qamus/schemas/dependency-candidate-lattice.schema.json) — read it for
the authoritative enums; this page is the orientation map, not a second copy.

## Edge
| field | meaning |
|---|---|
| `dependent` | the governed token ref |
| `candidate_head` / `headless` | the governing token ref, or `headless:true` (a coordinating wāw has no single governor) |
| `governor_type` | the kind of ʿāmil (particle / verb / noun / none) |
| `rel_label` / `rel_label_ar` | the relation (a SUBSET of the morphosyntax-token `syntax.dependency` enum), EN + traditional name |
| `assigned_case_mood` | the case/mood — **null when the ending is not visible** (arbitrary/unvoweled) |
| `governor_justification` | why this governor licenses that case — required before asserting a case |
| `justification_rule` | the rule cited (incl. `governor_not_justified`) |
| `evidence_class` | `source_addressed` vs `heuristic` — a heuristic never overrides source-addressed certainty |
| `unresolved_alternatives[]` | the kept readings for an ambiguous edge (iḍāfa / PP-attachment / homograph) |
| `right_answer_wrong_reason_marker` | true ⇒ correct ending, unjustified/wrong governor → scholar/two-vote |
| `decision_status` | `resolved` only with confirmed evidence; otherwise `pending` |
| `gate` / `route_to` | the canonical 4-tier (never `auto_safe` for iʿrāb) + the review lane |

## Engineering note
Case/mood-as-a-consequence-of-a-stated-governor + the rule that justifies it is an **engineering synthesis** the engine produces
(treebanks store a head-pointer + a relation label, not case-as-consequence). The governor lattice makes the justification explicit so
"right answer, wrong reason" is machine-detectable.

## Boundary
`{src:qamus, kind:authored, lang:en, external_source_names_public:false}`. No QAC/tafsir/source/path label in any edge text.
