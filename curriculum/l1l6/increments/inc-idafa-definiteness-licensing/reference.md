**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — annexation: exponents, genitive, definiteness

Annexation relates two nouns directly, with no linking particle, and the pack
licenses it on form-side evidence rather than on meaning. The head may not
carry tanwin, the definite article, or the dual and sound-plural final
consonant; the dependent carries an invariant genitive. The head's own case is
assigned by its role in the wider clause and is imported, never derived from
the construction.

Definiteness of the whole phrase is read off the final member. In a chain,
every non-initial member is genitive and only the final member may carry a
definiteness exponent — the two-member rule extended, not a second licence.

One row is a recorded exception rather than a rule: the participial subtype
admits the article on the head and blocks definiteness inheritance. It is
emitted as analysis-dependent, because the label the source material uses for
the descriptive type is the same term the tradition applies to this
structurally different subtype. The semantic classification row is likewise
analysis-dependent: the three-way enumeration is school-dependent, and a
part-whole relation appears in the worked material outside that enumeration.

Refused by design: a definite noun followed by a definite descriptive word,
which is an attributive phrase and the standing false positive; and any noun
pair whose exponents are not supplied.

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
