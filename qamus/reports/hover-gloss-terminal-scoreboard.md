# Hover-gloss terminal scoreboard

Source artifact `source_sha=65797d7d5599fadd`. Every one of the **49,900** hover tokens has a terminal state (no generic pending).

| state | count | pct |
|---|---|---|
| **resolved** | 40,875 | 81.91% |
| **pending (exact blocker)** | 9,025 | 18.09% |
| **total** | 49,900 | 100% |

## Resolved by confidence

| conf | count |
|---|---|
| low | 25,114 |
| med | 10,179 |
| high | 5,582 |

## Pending by blocker (exact, controlled vocabulary)

| blocker | count | next action |
|---|---|---|
| `stem_base_unknown` | 6,969 | author the host stem/lexeme in Qamus, then re-run the resolver |
| `source_entry_unverified` | 1,505 | add the inflected form to the entry forms[] (or verify the entry from source photo) and re-run |
| `same_surface_polysemy_requires_i3rab` | 550 | author a per-loc token-addressed decision (iʿrāb) selecting the sense |
| `proper_noun_no_qamus_entry` | 1 | create a proper-noun entry or token-address as a proper noun (no gloss) |

Untagged-unresolved reclassified from dataset: {'stem_base_unknown': 2257, 'source_entry_unverified': 283}
