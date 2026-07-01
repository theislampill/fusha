# Packet Versus Hover Projection

Goal: prevent repair packets from becoming learner-visible hover answers.

## Visibility states

- `learner_visible=true`: accepted source identity, accepted projection, source-clean public hover.
- `learner_visible=false`: packet-only, repair, owner, scholar, validator, or source-crosswalk row.

## Examples

| row | state | answer |
|---|---|---|
| accepted canonical loc + qg classes + authored hover | hover | `learner_visible=true` |
| `source_crosswalk_packet_ready` + null canonical loc | packet-only | `learner_visible=false` |
| `governor_irab_fixture_needed` | scholar/i'rab packet | `learner_visible=false` |
| `stem_entry_needed` | sarf flywheel packet | `learner_visible=false` |

Public hovers must not include private evidence labels, local paths, source-card notes, or process prose.
