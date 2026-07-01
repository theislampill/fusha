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

Largelexicon-specific routing:

1. A generated Qamus form can certify the surface/POS/root candidate, but not a
   context-sensitive function. The function decision remains nahw-owned.
2. For Mode A Qamus cards, require the bidirectional row handles:
   `entry_id`, `card_id`, `qword_index`, `visible_surface`, `quran_ref`, and a
   canonical/crosswalk packet when the Qur'anic word address is missing.
3. For Mode B tutoring, expose function alternatives as learner-facing hints;
   do not reveal a final i'rab answer until the level and evidence gate allow it.
4. For Mode C standalone parsing, prefer abstention/packet output over a
   confident correction when source-address evidence is absent.

Use `python tools/fusha_largelexicon_cli.py analyze-card --input ...` to inspect
clusters through the same local contract used by rollout workers.
