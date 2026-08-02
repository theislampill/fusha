**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — licensing the response connective

A conditional sentence divides into a condition half and a response half. The
pack decides one question: given the categorial class of the LEFTMOST element
of the response, is the response connective required, forbidden, or licensed
only under attribution — and which operator then assigns the response verb its
mood.

The organising principle is a repair: the connective is required exactly when
the response opener cannot itself receive jussive marking. A noun or
independent pronoun offers no verb to mark; a future marker imposes indicative
marking; a negator imposes its own mood; an emphatic particle, a probability
particle and an oath formula each interpose their own clause structure. A
non-second-person command response takes the connective before the command
prefix, and the prefix assigns the jussive. Where the response is a bare
imperfect verb, jussive marking is available and the connective is forbidden —
a stated outcome, not silence.

Two rows are attributed. The command-form opener is emitted
analysis-dependent, because whether a command form counts as jussive is
school-dependent and the whole licence turns on that. The past-time negator
row is likewise attributed: it belongs to the condition half, licenses no
response connective, and whether the trigger and the negator both govern the
condition verb is recorded upstream as analysis-dependent.

The opener inventory is recorded upstream as NOT exhaustive over attested
responses. A bare perfect-tense response is the known gap, and the pack
abstains on it rather than assimilating it to the nearest row.

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
