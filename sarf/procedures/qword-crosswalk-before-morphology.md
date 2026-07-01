# Qword Crosswalk Before Morphology

Use this procedure when a visible qword can be analyzed morphologically but its canonical source address is not
accepted.

## Rule

Morphology can be true but not deployable. A row with `source_crosswalk_packet_ready` or another unaccepted
crosswalk status is a repair packet, not a public hover candidate, even if sarf can identify the root, stem,
pattern, or suffix.

## Required gates

Before sarf certification:

1. visible qword row from the qword denominator;
2. displayed source-card text;
3. source-card repair status;
4. accepted crosswalk or exact source-crosswalk packet;
5. Arabic surface match inside the cited source;
6. duplicate-surface ambiguity check;
7. forward trace and reverse trace.

## Route outcomes

- `accepted crosswalk` -> continue to sarf route family.
- `source_crosswalk_packet_ready` -> packet-only, not learner-visible as a hover.
- `source_card_repair_needed` -> repair source-card first.
- `duplicate_surface_ambiguous` -> require uniqueness proof.
- `surface_not_found` -> source repair/owner packet.

## Teaching note

When tutoring, use packet rows to teach repair workflow only. They are not answer-key hovers.
