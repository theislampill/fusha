# Qword Denominator And Crosswalk

Goal: distinguish visible qword obligations from accepted hover rows.

## States

- `denominator_only`: the visible qword exists in the all-qword count but has no accepted source address.
- `source_crosswalk_packet`: the row needs Arabic-surface matching, uniqueness proof, or display-local/canonical repair.
- `source_card_repair_needed`: the card text/source evidence must be corrected before crosswalk.
- `accepted_crosswalk_hover_candidate`: canonical address is accepted and the row can proceed to sarf/nahw gates.
- `already_live_or_noop`: public hover/readback already covers the row.

## Drill

A qword row has visible surface, card index, and entry id. It also has `source_crosswalk_packet_ready` and null
canonical loc.

Questions:

1. Is it a hover?
2. Can sarf certify it?
3. What is the next action?

Expected:

1. No; it is `source_crosswalk_packet`.
2. Sarf may analyze internally, but cannot certify deployment.
3. Accept a crosswalk through Arabic-surface matching and uniqueness proof, or route source-card repair.
