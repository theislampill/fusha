# Batch-2 (B2) — noun + verb + particle-cluster sweep (APPLIED LIVE)

The second production sweep after N1/V1, run through the four-gate pipeline (empirical `norm_strict` key-collision
probe → author → **key-aware 2-vote** → apply). The 2-vote verifiers were shown the actual same-key surface set
and had to confirm `same_lemma` AND `same_pos` AND `gloss_ok` (both votes) before a key could ship.

## Result
- **230 candidates** (top-frequency pending pool, POS N/V/P, deduped vs the live tsv) → **159 certified, 71
  rejected**.
- Applied to the live hover-decisions tsv: **tsv 218 → 377 lines**, backup `*.bak-b2`.
- Rebuild: **coverage 72.14% → 75.28%** (matched 35,996 → 37,567, **+1,571 occurrences, ~50 improved, −0
  removed**), validate PASS, health 200, smoke OK. Light + dark screenshots verified.

## What certified (159)
- **Proper nouns** (one referent): Adam, Abraham, Israel, Noah, David, Moses, the Torah.
- **Divine attributes** as adjectival glosses: the Merciful, the All-Hearing, All-Seeing, All-Knowing,
  the All-Forgiving, the Living, the All-Wise.
- **Case-variant content nouns/adjectives**: the truth, the cattle, the disbelievers, the wrongdoers, the
  hypocrites, provision, spouses, a soul, great, noble…
- **Finite verbs with person/number**: We seized, We sent down, you worship, they possess, came to them, enter!,
  and stable particle clusters (and indeed we, because they, and as for, whenever).

## What the gate rejected (71 — the safety property working)
- **lemma_collision** (one root, two words): الملك مُلْك "dominion" vs مَلِك "king"; أمه أُمَّة "community" vs أُمّ
  "mother"; الهدي, الءاخر, أجل, أولي, ملك.
- **form_voice_collision**: كذبوا (كَذَّبَ II / كَذَبَ I / كُذِبَ passive); يخرج (يَخْرُجُ I / يُخْرِجُ IV).
- **particle_sense_collision**: وإن "if"/"indeed"; لم "why"/"not"; وما, فما, لمن, بما, وأن, وأنا.
- **pos_collision**: أعلم (verb "I know" / elative "knows best"); أكثر.
- **referent/polysemy** caught by a single verifier (both votes required): الدين "religion"/"judgment"; العزيز
  divine-Name vs the minister of Egypt; عزيز "mighty"/"dear"; سواء "equal"/"midst"; صالحا.

These are recorded as forbidden transitions in
[`sarf/rules/surface-state-transition-rules.json`](../../../sarf/rules/surface-state-transition-rules.json) and
[`nahw/rules/state-transition-rules.json`](../../../nahw/rules/state-transition-rules.json).

## Provenance
Public records carry only `{src:"qamus", kind:"authored", lang:"en"}`. `internal_provenance` (informed_by:
[qac, quran-text]) is methodology, never shipped. Mirror: `hover_batch_004_b2.jsonl` +
`hover_batch_004_b2.provenance.jsonl`. Rollback: `fusha-hover-decisions.tsv.bak-b2` + `wbw-lookup.prev.json`.
