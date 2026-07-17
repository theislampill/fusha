# PROOF-P: contextual مَا

This is the §12 candidate-only end-to-end particle proof. The compiler selects
the p099 entry, sense 1, card `2:284`, and the exact source-addressed occurrence
`مَا` at `2:284:10`.

The source packet under `source/` is a small, read-only capture of the canonical
entry, whitelist rows, and forward/reverse crosswalk facts used by the compiler.
It contains no live runtime state. Recompilation from the packet is deterministic:

```text
python tools/proofp_compiler.py
```

To recapture the packet from the lane's read-only inputs, pass the four input
paths and `--capture-source` as recorded in the lane report. The raw inputs are
never written by the compiler.

The durable proof surfaces are:

- `particle-contract.json` — typed entry, sense, occurrence, function, scope,
  gloss, colour, root-silence, ambiguity routes, and reciprocity facts.
- `particle-graph-edges.jsonl` — the selected-word/card/entry/occurrence/
  appearance chain with candidate guards.
- `particle-normalized-public-payload.json` — deploy-shaped at-rest, compact,
  expanded, hover, appearance, and readback descriptors.
- `particle-rich-hover-candidate.jsonl` — schema-compatible rich Ṣarf/Naḥw
  candidate with the exact public boundary.
- `particle-card.html` and `render-proof.json` — local visual proof; the PNG is
  deliberately ignored and must not be committed.
- `PROOFP-MANIFEST.json` — artifact checksums, gates, and honest pre-deploy
  limits.

Render and run the full gate:

```text
node tools/render_proof_particle.js
python tools/proofp_compiler.py
python tools/proofp_harness.py --full
```

The card has two identical `مَا` surfaces. The exact contextual row is therefore
source-addressed, but the card-to-occurrence and entry-to-occurrence graph hops
remain `candidate`; the source crosswalk's empty `occurrence_id` and reverse
empty `occurrence_ids` are preserved in the traces.
