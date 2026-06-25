# Hover-gloss terminal scoreboard

Source artifact `source_sha=65797d7d5599fadd`. Every one of the **49,900** hover tokens has a terminal state (no generic pending).

| state | count | pct |
|---|---|---|
| **resolved** | 49,255 | 98.71% |
| **pending (exact blocker)** | 645 | 1.29% |
| **total** | 49,900 | 100% |

## Resolved by confidence

| conf | count |
|---|---|
| low | 25,112 |
| high | 13,964 |
| med | 10,179 |

## Pending by blocker (exact, controlled vocabulary)

| blocker | count | next action |
|---|---|---|
| `stem_base_unknown` | 359 | author the host stem/lexeme in Qamus, then re-run the resolver |
| `same_surface_polysemy_requires_i3rab` | 198 | author a per-loc token-addressed decision (iʿrāb) selecting the sense |
| `source_entry_unverified` | 88 | add the inflected form to the entry forms[] (or verify the entry from source photo) and re-run |

Untagged-unresolved reclassified from dataset: {'source_entry_unverified': 11, 'stem_base_unknown': 106}
