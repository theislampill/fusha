# Duplicate-avoidance report (P15)

How the source-address graph avoids duplicate decisions: a sense/gloss is authored **once** against a canonical
address and **reused by link** across every occurrence, and one root may carry several entries only as an
**intentional split** (recorded), never an accidental duplicate.

## Reuse, not copy (transclusion)

| metric | value | meaning |
|---|---:|---|
| resolved hover tokens | 34,472 | total `wbw:S:A:W` gloss nodes |
| distinct resolved surfaces | ~ a few thousand | one authored decision per surface, **propagated** to all its occurrences |
| reuse mechanism | propagation pass | the engine links the same decision to every same-surface token, not a copied gloss per token |

The propagation/fnauth/fusha passes are **link reuse**: the authored gloss for قَالَ "he said" resolves all 383
`used_by` locations of its entry node `qamus:v001` by reference — there are not 383 copies of the decision.

## Intentional root splits (NOT duplicates)

7 roots carry more than one entry node, recorded as deliberate sense/homograph splits:

| root | entry nodes | why split |
|---|---|---|
| ر و د | qamus:v507 / qamus:v072 | distinct lemmas/senses on one root |
| ذ م م | qamus:n443 / qamus:n582 | — |
| ص ر ر | qamus:v512 / qamus:n356 | verb vs noun split |
| ف ر ج | qamus:v520 / qamus:n234 | verb vs noun split |
| ط ر ف | qamus:n169 / qamus:v543 | noun vs verb split |
| ص ل ي | qamus:v105 / qamus:v309 | distinct senses |
| ز ر ع | qamus:v583 / qamus:v412 | distinct senses |

## Reconciliation

- **0 orphan/duplicate entry nodes** (`build_source_address_index.py` dup-report).
- Every authored hover decision links to a source address; the P13 batch records each decision's
  `source_address` + `internal_provenance` so a reused decision is a link, not a re-author.
- Homograph quarantines (مَن/مِن, ذِكْر/ذَكَر, نَزَّلَ/نَزَلَ) are recorded as **distinct** addresses/decisions —
  the graph keeps them apart rather than collapsing them, which is the inverse of duplication.
