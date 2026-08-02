**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — licensed written carriers for hamza

Hamza is treated as a full root consonant, and its subclass is fixed by which
of the three root positions it occupies. On top of that morphology sits an
orthographic layer: which letter the hamza is written on. This pack licenses
that written carrier from a declared vowel environment.

The precedence is kasra over damma over fatha, with a bare hamza after a
vowelless letter. Each precedence outcome is a row, so a carrier is emitted
only where the environment is actually supplied — a wrong carrier is a
spelling error, not a variant, so an unread environment abstains.

The carrier is a property of the written form, not of the stem. Rows for the
plural cells of a final-hamza paradigm and for the passive of a medial-hamza
verb license the same outcome — re-evaluate after affixation — reached from
two different environments, because affixation changes the vowels. Two further
rows are stored lookups rather than derivations: three initial-hamza verbs
whose imperative has no hamza, and one medial-hamza lexeme with no hamza in
the imperfect. The first-person singular imperfect of an initial-hamza root
contracts prefix and root hamza into a long alif.

One row is attributed. The upstream account presents the carrier as fully
determined by adjacent vowels, its tabulated and summary statements of that
rule do not agree, and word-final position and editorial convention condition
the carrier as well; that row is emitted analysis-dependent and never
certifies.

The purpose of the table is identity: variant spellings licensed here are
recognised as one token rather than as separate entries.

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
