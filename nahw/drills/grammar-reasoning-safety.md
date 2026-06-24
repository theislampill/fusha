# Drill — grammar reasoning safety (the answer AND the reason must be right)

The GrammarProblems study (a general LLM at ~33% on Arabic naḥw, worst on iʿrāb/deep/essay) makes one rule
load-bearing: **a correct-looking answer with wrong reasoning is unsafe.** A hover gloss or an iʿrāb-affecting
repair is shipped only when both the conclusion and the syntactic reason are defensible against the sarf+nahw
ladders — not because the answer "looks right."

## The failure mode to catch

The model can output the *right gloss for the wrong reason*, which then generalizes to the wrong place:

| surface | plausible-but-wrong reasoning | correct reasoning | safe action |
|---|---|---|---|
| لَمْ يَلِدْ | "present tense → 'does not beget'" | لَمْ + jussive → **past** "did not beget" | gloss past; cite negation gate |
| وَمِنَ ٱلنَّاسِ | "starts و+م+ن → 'and whoever'" | kasra on mīm → preposition "and from" | gloss prep; harakah on content letter |
| إِلَيْنَا | "root ل ي ن → 'soft'" | إِلَى + نا (root أ ل ي) "to us" | gloss "to us"; norm_strict, not norm |
| لَا إِلَٰهَ | "لا = simple 'not'" | لا النافية للجنس → "there is no" | two-vote; never auto |
| صَٰلِحًا | "= the Prophet Ṣāliḥ" | descriptive "righteous" by referent | referent guard; never auto |
| زُلْزِلَتِ | "active 'quaked'" | **passive** "was shaken" (ḍamma vowelling) | read voice; pending if unvocalized |

Each of these passes a naive "does the answer look right?" check and still ships a wrong or over-generalized
gloss. The gate is the reasoning, not the vibe.

## The drill (run before any grammar-affecting decision)

1. **State the conclusion AND the reason.** "X means Y because [iʿrāb/wazn/harakah/referent]." No reason → pending.
2. **Check the reason against the ladder.** sarf: root/POS/form via norm_strict + QAC (never norm). nahw: the
   governing particle / case / mood / referent. If the reason rests on `norm()` alone, OCR alone, or "the model
   said so" → **never_auto**.
3. **Classify the gate** (`grammar-decision-gates.json`): iʿrāb / case-mood / istithnāʾ / lā-nāfiyah-lil-jins /
   ambiguous iḍāfa / multi-sense / referent-sensitive / deep / essay / advanced → **two-vote** (two independent
   checks that agree on conclusion *and* reason).
4. **Surface-key safety.** Before shipping a surface-keyed hover gloss, confirm the `norm_strict` key does not
   collide with a different-meaning form (the نَزَّلَ→نزل collides with نَزَلَ lesson). If it collides → pending.
5. **Prefer pending.** A precise pending reason is progress; a confident wrong gloss is a regression the owner
   will catch.

## Hand-off

A grammar-affecting decision object must carry `gate`, `reasoning`, `source_address`, and the sarf/nahw decisions.
`validate_linguistic_decisions.py` rejects any that ship below the gate their triggers require.
