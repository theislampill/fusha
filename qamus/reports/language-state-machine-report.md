<!-- HISTORICAL: point-in-time record. Current canonical scoreboard: hover-gloss-terminal-scoreboard.md + hover-token-audit-full.jsonl (current) -->

> **⚠ HISTORICAL** — point-in-time record; numbers below reflect when this landed. Current state: **hover-gloss-terminal-scoreboard.md + hover-token-audit-full.jsonl (current)**.

# Language state machine — report

**What it is.** An OSM-style hidden-state model for Arabic surface tokens, built read-only from the live corpus.
The live qamus-highlight aid keys ONLY by a vowel-stripped `norm_strict` key, so a single visible observation
(the key) may **emit from more than one hidden state** — different lemma, POS, verb-form, or voice. Collapsing
everything through one surface key is exactly what produced earlier regressions. This graph makes the splits
explicit and gates public export on single-owner keys.

- Schemas: [`language-state.schema.json`](../schemas/language-state.schema.json),
  [`token-state.schema.json`](../schemas/token-state.schema.json),
  [`state-transition.schema.json`](../schemas/state-transition.schema.json).
- Builder (read-only, env-var driven): [`tools/build_language_state_graph.py`](../../tools/build_language_state_graph.py).
- Query: [`tools/query_language_state.py`](../../tools/query_language_state.py).
- Committed slice: [`language_state_graph.sample.json`](../indexes/language_state_graph.sample.json)
  (full graph is a generated artifact — rebuild with the builder; gitignored per the repo's generated-output rule).

## Current state (built at live coverage 80.68%)

| decision class | n keys | meaning |
|---|---:|---|
| `resolved_qamus_authored` | **1,222** | one owner, authored gloss live, fires on its occurrences |
| `quarantine_homograph` | **156** | key splits across >1 QAC root/POS — **no single gloss may fire** |
| `pending` | **11,345** | single apparent owner, gloss not yet authored (the authoring pool) |
| **total distinct keys** | **12,723** | every hover token maps to exactly one key-state; **0 unknown** |

`total_tokens` = 49,900; the 1,222 resolved keys cover the 40,260 resolved token occurrences (80.68%). The
resolved class grew 376 → 562 → 743 → 933 → **1,222** across B2–B5 + the particle hard-tail.

## How it prevents the prior regressions

The state machine encodes each known collision as a refusal:

- **Root/POS splits are auto-quarantined.** When QAC assigns the same key two different roots or POS across its
  occurrences, the node becomes `quarantine_homograph` and `public_export_allowed=false`. Query any with
  `python3 tools/query_language_state.py --split`.
- **Lemma collisions under one root** (مُلْك "dominion" vs مَلِك "king"; أُمَّة "community" vs أُمّ "mother") share a
  QAC root, so they are not auto-split — they stay `pending` and are caught at **authoring time** by the key-aware
  2-vote, then recorded as **forbidden transitions** (`state-transition.schema.json`, kind=`forbidden`). The
  morphology/syntax forbidden sets live in
  [`sarf/rules/surface-state-transition-rules.json`](../../sarf/rules/surface-state-transition-rules.json) and
  [`nahw/rules/state-transition-rules.json`](../../nahw/rules/state-transition-rules.json).
- **Form/voice collisions** (كَذَّبَ II / كَذَبَ I / كُذِبَ passive under key كذبوا; يَخْرُجُ I / يُخْرِجُ IV under
  يخرج) and **particle-sense collisions** (إِن "if" / إِنَّ "indeed"; لِمَ "why" / لَمْ "not"; مَا "not" / "what")
  were all rejected by the batch-2 2-vote and are recorded as forbidden transitions.

## Worked examples (from the committed sample)

- `state:key:الحق` → one hidden state (root ح ق ق, noun "the truth"), 9 case-variant surfaces all the same lemma →
  `resolved_qamus_authored`, gloss "the truth". Why this gloss: one owner, fires on every occurrence.
- `state:key:الملك` → surfaces include both مُلْك (dominion) and مَلِك (king). Same QAC root → stays `pending`; the
  authoring 2-vote refuses a single gloss (`lemma_collision`). Why pending: two lemmas, no safe single gloss.
- `state:key:كذبوا` → emits كَذَّبُوا (II), كَذَبُوا (I), كُذِبُوا (passive) → `form_voice_collision`, pending;
  but `state:key:وكذبوا` emits only وَكَذَّبُوا (II) → single owner → resolved "and they denied".

## Reading the graph

```
python3 tools/query_language_state.py --stats          # reconciliation
python3 tools/query_language_state.py --key الحق        # why this gloss / why pending
python3 tools/query_language_state.py --split           # all quarantined homograph keys
python3 tools/query_language_state.py --pending 30      # next authoring pool (top by occurrence)
python3 tools/query_language_state.py --share ملك       # keys whose hidden states include this root
```

Every wrong-gloss regression becomes a new forbidden transition; every certified authoring/repair becomes a
reusable resolve transition. PP1 (particles) → N1/V1 → batch-2 (nouns/verbs) are staged learning over this graph,
not isolated scripts.
