**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — definite article assimilation discriminator

The definite article is written identically in every case; only its
pronunciation varies with the first consonant of the following word. The
letter inventory that can open that word splits into a closed fourteen-member
sun set and a closed fourteen-member moon set. Membership alone decides
whether assimilation is even POSSIBLE — a moon letter can never geminate the
article's laam, full stop — but membership alone never decides whether
assimilation actually happened in a given surface: that needs the shadda
itself, observed and declared, not assumed from the letter class.

A sun-letter context with a declared observed shadda resolves as completed
assimilation. A sun-letter context with no observed shadda — an unvocalized
surface, most commonly — withholds the claim rather than assuming the mark
would be there if written. A moon-letter context resolves as non-assimilating
from its closed-set membership alone, with no shadda evidence needed, because
gemination is structurally excluded there; a shadda that is nonetheless
declared observed on a moon letter is a contradiction of the closed inventory
and is refused rather than reinterpreted.

In every resolved outcome the article's own written laam stays article-owned.
Assimilation is a fact about how that laam is pronounced, never a
re-attribution of it to the following consonant, and an observed shadda on
that consonant is never read back as evidence of a doubled root or a Form II
stem — the shadda belongs to the assimilation process, not to the following
word's own morphology.

With no declared article at all, the table is out of regime: it never
activates on a bare following-letter observation.

## Pack shape — how a classification becomes a consumer row

The registered `discriminator_table` analyzer matches declared evidence
against each function's `discriminators` and returns the single surviving
`function` id, or abstains.

- `article_observed` — must be `yes`; otherwise no function requires it and
  the row is out of regime.
- `following_letter` — the declared consonant; membership in the sun or moon
  fourteen-member list is the closed-inventory test.
- `shadda_observed` — required `yes` for the sun-letter resolution, required
  `no` for the moon-letter resolution; any other combination — sun without an
  observed shadda, moon with one, or a letter outside both lists — survives
  no function and abstains `insufficient_features`.
