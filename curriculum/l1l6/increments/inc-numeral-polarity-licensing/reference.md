**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — numeral polarity and its construct consequences

The table is keyed on two declared inputs: the numeral's band, and the gender
of the counted noun's SINGULAR. The singular is the deciding evidence — the
shape of the plural actually used never substitutes for it.

One and two agree ordinarily and follow their noun. Three to ten invert: a
masculine counted singular licenses the feminine-marked numeral form, and a
feminine counted singular licenses the unmarked form. In that band the numeral
and the counted noun form a construct, so the counted noun is a genitive
plural second term, and its genitive exponent is selected by its own
declension class — the ordinary exponent for a fully declining noun, the
reduced one for a member of the blocked class. The numeral's own case is
external to the construct and comes from its clause role.

Two rows are lexeme-specific rather than general: the feminine form of eight
inflects as a defective noun and drops its final glide in the indefinite
nominative and genitive; and a definite construction placing the article on
both the numeral and the counted noun is recorded as analysis-dependent, since
it sits against the requirement that a construct head be bare.

Refused by design: numerals above ten, which are outside the band; and any
input whose counted-singular gender is unstated.

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
