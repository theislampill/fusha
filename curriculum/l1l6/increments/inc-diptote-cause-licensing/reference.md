**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — what blocks nunation, and what cancels the blocking

A noun in this class marks the genitive slot with the reduced exponent and
carries no nunation, as long as it stays indefinite and unannexed. Membership
is licensed by a pair on the feature route: one semantic trigger — name-hood or
adjectival status — together with one formal trigger from the listed
inventory: feminine marking, foreign origin, an added alif and nun, a
verb-shaped template, compounding, the comparative and colour template, and
the state-adjective template. Either trigger alone leaves the noun fully
declining, and the pack states that as its own licensed outcome rather than
leaving it to silence.

One family blocks on template evidence alone: broken plurals on the
ultimate-plural templates, regardless of the singular they derive from. That
is a separate route, not an instance of the pair.

Two rows cancel rather than block. The definite article and construct
headship restore the ordinary genitive exponent in prose; this is ordinary
grammar, and the pack tests it before any override, because it explains most
sightings of a restored exponent.

Two rows are attributed. The verse override — nunation or the ordinary
genitive exponent supplied under identified metrical or rhyme pressure — is
register-gated and carries the recorded reservations about the attributed
concession, the heaviness rationale and the celebrated illustration. The
toponym assigned on inherent feminine gender alone bypasses the paired-trigger
test and is school-dependent upstream.

Refused by design: a name sitting on a template the trigger chart does not
list, however many worked examples appear on it; and any noun whose triggers
are unstated.

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
