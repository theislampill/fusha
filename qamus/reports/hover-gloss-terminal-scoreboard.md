# Hover-gloss terminal scoreboard

Source artifact `source_sha=65797d7d5599fadd`. Every one of the **49,900** hover tokens has a terminal state (no generic pending).

| state | count | pct |
|---|---|---|
| **resolved** | 43,515 | 87.20% |
| **pending (exact blocker)** | 6,385 | 12.80% |
| **total** | 49,900 | 100% |

## Resolved by confidence

| conf | count |
|---|---|
| low | 25,114 |
| med | 10,179 |
| high | 8,222 |

## Pending by blocker (exact, controlled vocabulary)

| blocker | count | next action |
|---|---|---|
| `stem_base_unknown` | 4,227 | author the host stem/lexeme in Qamus, then re-run the resolver |
| `source_entry_unverified` | 1,778 | add the inflected form to the entry forms[] (or verify the entry from source photo) and re-run |
| `same_surface_polysemy_requires_i3rab` | 380 | author a per-loc token-addressed decision (iʿrāb) selecting the sense |

Untagged-unresolved reclassified from dataset: {'stem_base_unknown': 1408, 'source_entry_unverified': 379}
