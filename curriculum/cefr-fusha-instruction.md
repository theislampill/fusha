# CEFR-aligned Fusha instruction

> **Scaffolding, not certification.** This layer adapts the CEFR level ladder (`pre_A1 … C2`) to Fusha/Classical Arabic so
> the checker can scaffold its output to a **caller-supplied** learner level. It never assesses, certifies, or infers a
> learner's level, and it reproduces **no** Council of Europe descriptor prose — only the short level labels. The level
> records are authored Fusha adaptations in [`cefr-fusha-levels.json`](cefr-fusha-levels.json); the gate is
> [`tools/fusha_cefr_gate.py`](../tools/fusha_cefr_gate.py); the validator is
> [`tools/validate_cefr_fusha_instruction.py`](../tools/validate_cefr_fusha_instruction.py).

## What CEFR does here

CEFR gates **display, not linguistics.** The underlying morphology lattice, gates, conflict records, and diagnostics are
unchanged at every level; CEFR only decides *how much to show*:

- **diagnostic visibility** — an allow-list per level (beginners see orthography/clitic notices; iʿrāb-sensitive diagnostics
  appear only at C1+);
- **metalanguage exposure** — `none → minimal → moderate → full` (iʿrāb terminology and root/pattern analysis withheld from
  beginners);
- **correction aggressiveness** — `hint_only → gentle → standard → explicit` (inline fixes only at the upper bands, and only
  for already-safe edits);
- **hint depth** — `point → point_teach → full_ladder` (Bottom-out is still subject to the deliverable-003 withhold rule —
  CEFR can shrink the ladder, never expand past it);
- **example difficulty** — `letters_words → … → classical_prose`.

## CEFR-by-level behaviour (authored Fusha adaptation)

| level | metalanguage | iʿrāb terminology | root/pattern shown | correction | hint depth | examples |
|---|---|---|---|---|---|---|
| pre_A1 | none | no | no | hint_only | point | letters, words |
| A1 | none | no | no | hint_only | point | short phrases |
| A2 | minimal | no | no | gentle | point + teach | simple sentences, common particles, simple attached pronouns/prepositions |
| B1 | moderate | light (named, not analysed) | awareness | standard | point + teach | routine Fusha, common case/mood, basic root/pattern |
| B2 | moderate | yes (explained) | yes | explicit | full ladder | longer sentences, common subordination, richer morphology |
| C1 | full | yes (governor/dependency) | yes | explicit | full ladder | complex Classical/Fusha prose, nuanced particles |
| C2 | full | yes (fine ambiguity, detailed iʿrāb) | yes | explicit | full ladder | advanced rhetorical / Classical usage |

These are **authored project adaptations**, not official certification claims.

## Hard rules (also enforced by the validator)

1. **No certification / assessment.** No field may claim CEFR certification or assess a learner. Allowed framing:
   *"CEFR-aligned hint level"* / *"estimated learner support level"*. Each level enumerates `forbidden_overclaims[]`.
2. **No copied descriptor prose.** CoE CEFR / Companion-Volume descriptor text is never reproduced; all descriptors are short,
   authored Fusha adaptations. (A length/leak heuristic flags a suspected copy.)
3. **Beginner safety.** `pre_A1/A1/A2` carry no iʿrāb-sensitive diagnostic and no heavy metalanguage — a checker must never dump
   C2 iʿrāb terminology on an A1 learner.
4. **Projection is monotonic-safe.** The CEFR view can only remove detail or downgrade a suggestion to a hint; it never lowers a
   safety gate, forces a parse, reveals a withheld Bottom-out, or asserts a learner's level.
5. **Source-clean + dry-run.** Every rendered string passes `leak_sot.scan()`; `{src:qamus, kind:authored, lang:en,
   external_source_names_public:false}`; `live_writes == 0`.

## Research note

The P2b CEFR-licensing research lane was interrupted (session limit) and returned no verified claim. The rules above are therefore
**conservative by construction** — copying nothing and certifying nothing — which is the copyright-safe and mandate-compliant default
regardless of the unverified licensing detail. See `parserplans/general-fusha-grammar-checker-p2b-learning-cefr/{004,009}`.
