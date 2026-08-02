**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — licensing the attributive descriptive follower

A descriptive follower is licensed against exactly one head, by simultaneous
agreement on case, gender, number and definiteness. The pack treats referent
animacy as a declared input and applies it before gender and number are set: a
plural head with non-human referents licenses feminine singular modification,
and that is agreement rather than a mismatch.

Definiteness is the axis that decides construction type. A definite head
followed by an indefinite descriptive word is not a phrase at all but a
two-term nominal reading, and the pack emits that as the outcome instead of
forcing modification.

Two rows carry reduced agreement. The elative-shaped modifier agrees only in
case and definiteness and keeps its base shape; that row is emitted
analysis-dependent, because the restriction of its distinct feminine shapes to
non-follower position is recorded upstream as requiring review. The causal
descriptive follower takes its gender from the noun that follows it rather
than from the head, and stays singular.

After an annexation chain, the modifier's case identifies which member it
attaches to. Where both members carry the same case, the licensed outcome is
an explicit undecidable — a stated result, not an abstention and not a silent
choice. Several modifiers on one head are each licensed independently and need
no coordinator.

Refused by design: the indefinite circumstantial accusative, which occupies
the same slot and fails definiteness parity; and any head whose features or
referent animacy are unstated.

## Pack shape — how a licence becomes a consumer row

The registered `licensing_table` analyzer emits `hidden_type` and `obligatory`.
In this pack the `hidden` object is the LICENSED OUTCOME slot, not a
reconstructed word:

- `construction` — the declared input configuration the licence is keyed on.
- `hidden.type` — the OUTCOME label the licence yields for that configuration.
- `hidden.value_class` — the qualifying refinement of that outcome (which
  member, which exponent, which operator, which evidence route).
- `obligatory` — true when the row's outcome is the only licensed one; false
  when the row records one licensed option among preserved alternatives.
- `note` containing `analysis-dependent` — the consumer flags the emission
  `analysis_dependent: true`; such a row is attributed analysis and never
  certifies.

A construction absent from the table is refused with `reject_reconstruction`:
the table is closed, and no outcome is ever inferred from a resemblance.
