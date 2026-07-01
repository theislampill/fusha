# Largelexicon Function Token Routing

Use this procedure when largelexicon encounters particles, prepositions,
pronouns, particle clusters, or no-entry function tokens.

## Source identity before function certification

Before certifying a function token for Qamus rollout, verify that the row is not merely a qword
denominator, source-card repair, or source-crosswalk packet. A `source_crosswalk_packet_ready`
row can carry internal nahw evidence, but it is packet-only until accepted and must not be
learner-visible as a finished hover.

## Plan 15 nahw route families

Use exact route names:

- `governor_irab_fixture_needed` — the row needs a governor/case/mood/attachment fixture before certification.
- `particle_function_rule_needed` — the row needs a reusable function-token or particle-cluster rule.

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

## Collision safety

When the larger Qamus-derived table introduces a valid content homograph for a
function surface, keep the function lane explicit:

- `من` / `مِن` / `مَن` routes to function/context review before any content-verb
  hover.
- `إلا` routes to exception-particle review unless the noun reading is proven
  by source/context.
- `لا` routes to negation/prohibition context before public projection.
- `وما` keeps wāw plus function-sensitive mā visible, but remains
  `pending_context`.

Use the parser/CLI safety fields; do not consume `morphology_candidates[0]`
directly.
