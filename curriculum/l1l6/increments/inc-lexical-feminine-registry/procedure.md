**Status: CANDIDATE. Declarative addition proof: reuses the registered discriminator_table capability — zero consumer edits. Promotion via TP-CURR packets under Sol/owner control.**

# Procedure (model-facing)

1. Receive the declared `lexeme_surface` feature (exact written lexeme,
never a stemmed/normalized form). 2. Test EXACT membership in the closed
registry list — never a substring, root, or shape match. 3. A member ->
`lexically_feminine_noun`; anything else (no declared lexeme, a masculine
noun, a regularly ة-marked feminine, or a near-collision surface built on a
registered root) -> abstain `insufficient_features`. 4. Never infer
membership from morphology; the registry only ever grows through a
reviewed pack edit.
