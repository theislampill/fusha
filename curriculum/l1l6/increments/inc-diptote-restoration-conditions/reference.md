**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — when the reduced exponent is suspended

This pack is the suspension side of the reduced-exponent class. Membership is
decided elsewhere; here the question is which environments restore the
ordinary case vowel, which restore nothing, and which term of an annexation
the restoration reaches.

Two prose environments restore: the definite article, and first-term-of-
annexation status. Both work through the same cause — they definitise the
token. Because nunation belongs to indefiniteness, neither brings the nunation
back, and the outcome labels keep the two halves apart: the case vowel is
restored and the nunation is withheld. Adding the nunation once the vowel has
returned is itself a licensed row with a negative outcome, so the mistake is
refuted by the table rather than left to inference.

Two environments restore nothing: an indefinite, unannexed class member, and a
class member sitting as the SECOND term of an annexation — the construction
definitises only its first term, so each term is evaluated on its own state.

Verse may supply nunation where prose forbids it; that row is register-bound
and is evaluated before a nunated occurrence is judged an error.

Three rows are attributed. A following relational adjective is claimed
upstream to restore the ordinary vowel although it does not definitise the
head; an illustration attaching the article directly to proper toponyms is
recorded as requiring review; and a shortened noun ending in a non-vocalisable
alif is listed as a class member in a way recorded as unsafe for automatic
projection. All three are emitted attributed and none certifies.

Refused by design: a neighbouring governor that makes a token look annexed
without definitising it; and any token whose definiteness state is unstated.

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
