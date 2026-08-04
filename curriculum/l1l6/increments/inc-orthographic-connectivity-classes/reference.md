**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — orthographic connectivity classes

The letter inventory splits into two closed classes by whether a letter sends
an outgoing connection to what follows it. Six members never do: bare alif
together with its hamza-bearing and madda/wasla variants counted as one
member, then dal, dhal, ra, zay, and waw as four further single members. The
remaining twenty-two letters attach forward whenever a following letter is
declared present.

Whether a letter also carries an INCOMING connection is a separate question,
decided by its declared predecessor: word start and a non-attaching
predecessor both withhold it, because neither can send an outgoing connection
in the first place; any attaching predecessor supplies it. Crossing the two
questions gives every letter's classified shape: a non-attaching letter is
either standalone (no incoming) or final (incoming); an attaching letter is
standalone, initial, final, or medial depending on both answers.

This table decides one letter's joining behaviour from declared neighbor
evidence. It is never asked to, and never does, turn that behaviour into a
word or morpheme boundary — a non-attaching letter's forced break is a visual
fact about rendering, not a segmentation claim.

Two variant families are visually close to members of the non-attaching set
but are outside this lesson's closed inventory and are refused rather than
folded in by resemblance: the tied taa (visually close to hā') and the
variant final a-spelling (visually close to alif). A hamza-bearing variant of
a letter other than alif is likewise refused unless it is separately licensed
— only the alif family's hamza-bearing forms are unified here.

## Pack shape — how a classification becomes a consumer row

The registered `discriminator_table` analyzer matches declared evidence
against each function's `discriminators` and returns the single surviving
`function` id, or abstains.

- `letter` — the declared base letter; membership in the six- or
  twenty-two-member list is the closed-inventory test.
- `preceding_neighbor_class` — `word_start`, `non_attaching_letter`, or
  `attaching_letter`; only an attaching predecessor supplies an incoming
  connection.
- `following_neighbor_present` — `yes`/`no`; only checked for attaching
  letters, since a non-attaching letter's outgoing connection is already
  ruled out by its own class.

A letter absent from both lists, or evidence missing a required key, survives
no function and abstains `insufficient_features`: the table is closed, and no
shape is ever inferred from resemblance.
