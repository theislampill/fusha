# Procedure — homograph / surface-key risk

**Invoke when:** about to ship a surface-keyed hover gloss (the live key is `norm_strict`).

**The rule:** the live hover key is `norm_strict` — it KEEPS the `ال` article + consonant skeleton + hamza
seat, but DROPS harakāt (incl. shadda) and the vowels that distinguish form/voice/person. A surface gloss fires
on **every** token sharing that key. It is safe **iff** every same-key surface is the SAME word AND same
POS/person; unsafe if the key mixes meanings.

**Checks (decide with an EMPIRICAL probe, not bare-root reasoning):**
1. Probe the live corpus: which distinct vocalized surfaces share this `norm_strict` key? (`artifacts/*keysafety_probe.py`.)
2. If all are case/orthographic/tanwīn variants of one word/POS → **safe**.
3. If the set mixes: different lemmas (أُمَّة↔أُمّهُ), POS (فَضْل noun↔فَضَّلَ verb; وَلَد noun↔وَلَدَ verb),
   form (يَخْرُجُ I↔يُخْرِجُ IV; نَزَلَ↔نَزَّلَ), voice (قَتَلَ↔قُتِلَ; يَنظُرُونَ↔يُنظَرُونَ), person
   (هَدَيْنَا "we guided"↔هَدَىٰنَا "He guided us"), or sense (سَوَآء "equal"↔"midst"; الدِّين "religion"↔"judgment")
   → **unsafe → pending**.
4. Diacritic content-letter homographs (مَن/مِن، لَمْ/لِمَ، لِمَا/لَمَّا، كُلّ/كَلَّا، ذِكْر/ذَكَر): decide on the
   content-letter harakah ([`../rules/homograph-quarantines.json`](../rules/homograph-quarantines.json)) or pending.

**Output:** safe → author; unsafe → pending with the precise reason.

**Forbidden:** trusting a 2-vote that reasoned about the bare ROOT instead of the real `norm_strict` key (the P13
over-rejection lesson); shipping a key that mixes meanings.

**Test:** `tools/check_regressions.py` (أُمّ↔أَمْ, الملك vowel-homograph, ذِكْر/ذَكَر, نَزَّلَ/نَزَلَ).
