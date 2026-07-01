# Largelexicon Function Token Routing

Use this procedure when largelexicon encounters particles, prepositions,
pronouns, particle clusters, or no-entry function tokens.

Largelexicon may segment and queue the token, but nahw decides function:

- `ما` / `وما`: negative, relative, interrogative, conditional, masdariyya,
  laysa-like, preventive, oath/source, or unresolved.
- `بـ` and `لـ`: preposition plus governed host or attached pronoun; no
  host-only hover.
- `أم لهم`: particle cluster plus lam/pronoun relation, not isolated dictionary
  substitutions.
- finite verbs under particles: mood/governor must be recorded before a strong
  hover claim.

If two independent checks agree on the English gloss but not the grammatical
reason, the row remains unsafe. Emit a scholar/i'rab packet or nahw review
packet with the exact question and evidence lane.
