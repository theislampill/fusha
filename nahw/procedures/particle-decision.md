# Procedure — particle decision

**Invoke when:** the surface is a closed-set particle / function word.

**Input:** surface (with diacritics), surrounding tokens.

**Checks:**
1. Read the harakah on the **content letter** (after any و/ف proclitic), never the first letter:
   مَن(fatḥa "who") vs مِن(kasra "from", incl. وَمِنَ); لَمْ vs لِمَ; لِمَا vs لَمَّا(shadda); كُلّ vs كَلَّا;
   نِعْمَ vs نَعَمْ; أَنِّي vs أَنَّى ([`../rules/particle-context-rules.json`](../rules/particle-context-rules.json)).
   Use `normalize_ar.haraka_on/shadda_on/is_man_who`.
2. مَا is multi-function (negation / relative / interrogative / maṣdariyyah) — no default; needs context.
3. أَنْ vs إِنَّ by hamza seat (kept by `norm_strict`) + shadda.

**Output:** the function gloss (مَن→"whoever", وَمِنَ→"and from", قَدْ+past→"indeed/already") or pending.

**Forbidden:** deciding on the first letter or on `norm()`; a surface key when undiacritized input collapses the
pair → pending(homograph_haraka). A particle never takes a content-verb/noun gloss.

**Test:** `examples/function-word-decisions.jsonl`; `tools/check_regressions.py` (مَن/مِن، لَمْ/لِمَ، لِمَا/لَمَّا).
