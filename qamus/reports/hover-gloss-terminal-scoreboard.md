# Hover-gloss terminal scoreboard

Source artifact `source_sha=65797d7d5599fadd`. Every one of the **49,900** hover tokens has a terminal state (no generic pending).

| state | count | pct |
|---|---|---|
| **resolved** | 42,849 | 85.87% |
| **pending (exact blocker)** | 7,051 | 14.13% |
| **total** | 49,900 | 100% |

## Resolved by confidence

| conf | count |
|---|---|
| low | 25,114 |
| med | 10,179 |
| high | 7,556 |

## Pending by blocker (exact, controlled vocabulary)

| blocker | count | next action |
|---|---|---|
| `stem_base_unknown` | 4,874 | author the host stem/lexeme in Qamus, then re-run the resolver |
| `source_entry_unverified` | 1,797 | add the inflected form to the entry forms[] (or verify the entry from source photo) and re-run |
| `same_surface_polysemy_requires_i3rab` | 380 | author a per-loc token-addressed decision (iʿrāb) selecting the sense |

Untagged-unresolved reclassified from dataset: {'stem_base_unknown': 1684, 'source_entry_unverified': 396}
