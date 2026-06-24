# Suffix/pronoun class — expansion (P4)

The suffix/pronoun lane is the dataset-fed engine: a possessed surface (noun stem + vocalized
enclitic) resolves to `<possessor> <base noun>` only when the host is a **noun** and the base
gloss comes from a real Qamus entry. Sarf/nahw skills decide; the committed dataset supplies bases.

## What changed this pass

- **Audit (P3):** all 1,652 `suffix`-coded pending tokens (and the rest) now carry an exact
  blocker, not a generic "pending". The host-stem-missing ones are `stem_base_unknown` with the
  next action "author the host lexeme". No token shows "stem recognized — suffix/pronoun pending".
- **Dataset-sourced candidates:** of the 888 `stem_base_unknown` stems, **82** had a host lemma
  in the committed Qamus noun entries (55 headword, 27 form). 785 have no Qamus noun entry yet →
  stay `stem_base_unknown` (next: author those lexemes). This is the cart feeding the engine: the
  P0 dataset replaces hand-curated base glosses.
- **Adversarial 2-vote verification** (`suffix-pronoun-verify` workflow, 18 sarf/nahw verifier
  agents): **40 approved, 43 rejected.** The rejections are exactly the skill failure classes:
  - `tanwin_alef_false_stem` — بُنْيَٰنًا, وَأَمْنًا (ـًا is not the pronoun نا; sarf principle 1)
  - `homograph_wrong_lemma` — ذِكْرِنَا must not borrow ذَكَر "male"; أَبَاهُ ≠ أَبًّا "fodder"
  - `preposition_or_particle_not_possessive` — فَمِنكُم "from you" is a phrase, not a possessed noun
  - `number_wrong` — وَثُلُثَهُ "a third of it", not "three"; `referent_unsafe`; sense disagreement
- **Applied:** 40 certified token decisions → live. Coverage **81.77% → 81.85%** (40,805 → 40,845),
  **−0 removed, −0 changed** (rebuild diff: +40/−0/~0). Health 200; screenshot of `b10a1ee04666`
  confirms "Our deeds are for us, and your deeds are for you" renders.

Examples applied: وَجُنُودَهُمَا "and their troops", أَبِينَا "our father", يَمِينُكَ "your right hand",
وَكَلْبُهُم "and their dog", خَلْفِهِۦ "behind him", أُمُّهُۥ "his mother", وَنُورُهُمْ "and their light".

## Safety (skills cited)

- **/fusha-sarf** §8 + principle 1/4: clitic strip must not invent a false stem; tanwīn-alef ≠ نا;
  broken plural shares the root (جُنْد→جُنُود), not the surface.
- **/fusha-sarf** principle 3 + **/fusha-nahw** §6: POS-gate — on a **verb** the enclitic is
  subject/object ("we knew"), never possessive ("our knowledge"). 1,050 verb-suffix tokens skipped;
  verifiers rejected every verb host. `عَلِمْنَا`/`خَلَقْنَا` stay pending (tests SP-005/006).
- **/fusha-nahw** principle 2: preposition+pronoun renders as a phrase by referent, not a possessive.

## Tests (gated by `tools/check_regressions.py`)

`nahw/evals/suffix-pronoun-eval.jsonl` (18 cases) + `tools/test_suffix_pronoun.py` cover the named
classes أَعْمَالُنَا/كُمْ/هُمْ, رَبِّكُمْ, كِتَابَهُمْ, قُلُوبِهِمْ, أَمْوَالَهُمْ, أَيْدِيهِمْ, the verb-exclusion
(SP-005/006), the tanwīn-alef trap (SP-007/017), the homograph rejection (SP-016 ذكرنا), and the
preposition-phrase case (SP-018 فمنكم). `test_suffix_pronoun.py` is green.

## Remaining (exact next)

- Author the **785** host lexemes with no Qamus noun entry (e.g. خَلَاق "share", رِضْوَان "good
  pleasure", سِيمَا "mark", مَثَل "likeness") → re-run `build_suffix_pronoun_candidates.py` → verify.
  Tracked in the P3 audit under `stem_base_unknown` and the P2 matrix `next_action`.
- Re-run candidate generation after each noun-entry batch (the resolver is dataset-driven).
