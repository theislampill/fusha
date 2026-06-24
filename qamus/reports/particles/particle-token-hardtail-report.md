# Particle hard-tail — token-addressed rescue (B6A)

The particle hard-tail left 157 function-word homograph keys as surface-key blockers (لَمْ/لِمَ، مَن/مِن،
وَمَنْ/وَمِنْ، إِنْ/إِنَّ، أَمْ/أُمّ، …). The token-addressed layer ([token-addressed-hover-layer.md](../token-addressed-hover-layer.md))
resolves the **surface-distinct** ones per token; the **same-surface polysemy** stays pending for iʿrāb.

## Resolved per-token (363 decisions, applied live)
| reading | gloss | n | basis |
|---|---|---:|---|
| لَمْ / لَّمْ (+فَ) | did not | 121 | jussive negative particle (MCP iʿrāb: حرف نفي وجزم) |
| مَنْ (+وَ/فَ) | who / whoever | 161 | relative/interrogative pronoun (MCP: اسم موصول) |
| أَمْ | or | 65 | disjunctive particle |
| أُمّ | mother | 7 | noun (distinct surface from أَمْ) |
| مِنْ (+فَ) | from | 4 | preposition |
| لِمَ | why | 3 | interrogative |

The discriminator is the **vocalized surface** (harakāt) the artifact already stores — only `norm_strict` had
collapsed them. Each decision is keyed by `quran:S:A:W` + a `state:tok:*` id; provenance cites MCP iʿrāb internally.

## Still pending — same-surface polysemy (needs per-token iʿrāb, the next tier)
- وَمَا / فَمَا — مَا is "not" (negation) OR "what/that which" (relative/interrogative) under ONE surface.
- bare إِنْ / وَإِن — conditional "if" OR lightened-emphatic (إنْ مخففة من الثقيلة, MCP-confirmed at 12:91).
- لَمَّا — "when" (temporal) OR "not yet" (jussive) under one surface.
These cannot be disambiguated by surface; they require per-loc iʿrāb (Tafsir MCP `fetch_ayah(include=["irab"])`)
to assign each token its reading. They remain precise blockers, not vague pending.

## Effect
Particle example-āyah pending is further reduced (the لَمْ/مَنْ/أَمْ/أُمّ classes are now resolved wherever they
occur in the corpus, including the particle āyāt). Combined with the prior particle hard-tail, the function-word
floor is now only the same-surface polysemy classes above. Mirror: `particle_token_hover_batch_003.*`.
