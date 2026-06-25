# Closure Lane Routing

Classify before authoring. Every pending or suspect hover must have a lane,
evidence need, stop condition, and terminal status.

Primary lanes:

- `source_triangulatable`: unique surface, source agreement, clitic role
  preserved, public payload clean.
- `clitic_compositional`: written token contains a host plus visible
  proclitic/enclitic/preposition/pronoun.
- `governing_particle_mood`: imperfect verb or clause function is controlled by
  a governor such as `لم`, `لن`, purpose/imperative lām, causal fā', or
  prohibition `لا`.
- `function_particle`: `ما`, `و`, `ف`, `ل`, `أ`, `إن`, `لا`, `إلا`, or similar
  requires contextual function selection.
- `pp_attachment`: preposition plus governed nominal/pronoun needs attachment
  status: verb, nominal, visible head, hidden hal, hidden sifa, or unknown.
- `named_entity_span`: QAC/concept metadata or syntax suggests a person, people,
  place, book, plant, body part, or named span.
- `clause_scope`: relative, subordinate, purpose, temporal condition, condition
  result, or answer-of-condition scope matters.
- `advanced_nahw`: hal, maf'ul li-ajlih, maf'ul ma'ahu, vocative, exception, or
  case/mood rule decides the hover.
- `owner_gated`: entry wording, licensing/provenance, or public policy decision.
- `source_repair_gated`: bad source location, source surface, or entry-form
  evidence.
- `scholar_gated`: i'rab disagreement or unresolved grammar ambiguity.

Stop a broad lane when a sample repeatedly hits the same blocker, yield drops to
zero, or failures show the tool is choosing the wrong token or wrong grammatical
piece. Switch from authoring to validator/tool repair at that point.
