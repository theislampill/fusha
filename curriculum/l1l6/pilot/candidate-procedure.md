# CANDIDATE procedure — root vs pattern vs affix letter ownership

**Status: CANDIDATE (curriculum-derived, review-needed). Not part of
`sarf/SKILL.md`; not registered in any rule registry; certifies nothing.**
Promotion path: `curriculum/l1l6/packets/TP-CURR-ROOTPATTERN-PROMOTION.json`
→ Sol review → owner adjudication alongside the sarf@2.4 letter-ownership
candidates. This file deliberately lives outside `sarf/` so no Sol-owned
skill surface changes in this PR.

## Input

A single Arabic token (with diacritics where available), its sarf output
object if known. No Qurʾānic location required — this procedure assigns
**letter ownership**, not occurrence analysis.

## Output

For every base letter of the surface, exactly one owner class:

| Owner class | Meaning | Example letter |
|---|---|---|
| `root` | one of the (up to 4) radicals | س / ج / د in مَسْجِد |
| `pattern_augment` | a letter contributed by the wazn template | the م of مَفْعِل |
| `clitic` | proclitic/enclitic (ال، و، ف، ب، ل، ك، pronoun tails) | ال in المَسْجِد |
| `inflection` | person/number/mood/tense affix | the ي of يَسْجُدُ |

Short case/mood vowels are `hover_only` — displayed in the hover plane,
never a coloured base-letter segment.

## Steps

1. **Strip clitics conservatively** (sarf skill §8): never invent a false
   stem; a tanwīn-alef is not the pronoun نا.
2. **Recover the root by the evidence ladder** (sarf skill §5): Qamus entry →
   QAC → source page → adapter → heuristic-last. A heuristic root alone
   forces `pending`, not ownership assignment.
3. **Fit the wazn template** against the de-cliticized stem: every stem
   letter must map to either a template slot (ف/ع/ل position → `root`) or a
   template augment (→ `pattern_augment`).
4. **Classify remaining affixes** as `inflection` (imperfect prefixes
   أ/ن/ي/ت, suffix pronouns are `clitic`, number/gender endings are
   `inflection`).
5. **Abstain on residue.** If any letter cannot be owned by exactly one
   class (weak-root suppletion, fused orthography, geminate collapse),
   emit `pending_letter_ownership` for the whole token — a partial colouring
   is worse than none.

## Hard guards (from the adversarial fixtures)

- An initial م is **ambiguous** (pf-adv-01 مَلِك: radical; pt-01 مَسْجِد:
  augment): ownership follows the certified root, never the surface shape.
- A weak root may hide radicals from the surface (pf-adv-02 مَاء): never
  force three visible radicals.
- `inflection` ≠ `pattern_augment` ≠ `clitic` (pf-adv-03 يَسْجُدُ).
- Rootless particles get NO root and no invented ownership (pf-adv-04 مِن);
  rootlessness is taught, never blank.
- Shared radicals never merge lexemes (pf-adv-05 سَجَدَ vs مَسْجِد): the only
  edge licensed by root sharing is `shares_root`.

## Projection contract (pilot-scoped)

Colour segmentation and rich-hover explanation are BOTH compiled from the
same facts record (`pilot-facts.json`); the validator enforces letter-perfect
parity between the two projections and the facts. One fact source, two
surfaces — the meta-transclusive discipline at pilot scale.
