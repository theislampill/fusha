**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — case licensing in exclusion constructions

The construction has three parts: the set excluded from, the exclusion word,
and the excluded item. Case on the excluded item is not assigned by the
exclusion word; it is read off a closed table keyed on two declared inputs —
whether the clause is affirmative or negated, and whether the set excluded
from is overt.

Licensed cells: affirmative clause with an overt set yields the accusative of
exception, and that is the only outcome. A negated clause with an overt set
yields two licensed outcomes together — the accusative of exception and the
appositive substitute copying the set noun's case — and the pack emits the
row as analysis-dependent rather than choosing. A clause with the set left out
yields whatever case the excluded item's own clause role assigns, which may be
nominative, accusative or genitive. The construction with the categorical
negator is recorded as a further analysis-dependent row: the negated noun is
described as a built form occupying an accusative slot with the excepted noun
substituting for it.

The two nominal exclusion words invert the pattern: the exclusion word itself
carries the case the excluded item would have taken, and the noun annexed to
it is genitive unconditionally. An excluded item introduced by a preposition
is analysed as the prepositional phrase rather than as a bare excluded noun.

Refused by design: exclusion words outside the taught closed inventory, and
any input whose polarity or set-overtness is unstated.

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
