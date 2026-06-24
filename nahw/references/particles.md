# Particles (الحروف / الأدوات) — the closed set, and its traps

Particles are a small, closed set, but they carry an outsized share of qamus‑highlight's wrong‑gloss risk: they
are short, high‑frequency, and many are **diacritic homographs** of each other. This reference is the inventory +
the decisive feature; the machine‑readable disambiguation lives in
[`rules/particle-context-rules.json`](../rules/particle-context-rules.json) (harakāt) and
[`rules/negation-rules.json`](../rules/negation-rules.json) (negation scope).

## The first rule of particles

**Read the harakah on the content letter, after any و/ف proclitic — not the first letter.** وَمِنَ is the
preposition (kasra on the mīm), not وَمَن (fatḥa). This single rule prevented the corpus‑wide مَن/مِن regression.

## Inventory (corpus‑attested + Qurʾānic core)

| particle | reading(s) | gloss | decisive feature |
|---|---|---|---|
| مَن / مِن | relative–interrogative / preposition | "whoever" / "from, among" | harakah on ميم (fatḥa vs kasra) |
| مَا | negation / relative / interrogative / maṣdariyyah | "not / that which / what?" | context (no default) |
| لَا / لَنْ / لَمْ | negations | "no, not / will never / did not" | mood of the governed verb; لَمْ vs لِمَ by lām harakah |
| إِنْ / أَنْ / إِنَّ / أَنَّ | conditional / maṣdariyyah / emphatic | "if / to / indeed / that" | hamza seat (أ/إ) + shadda |
| قَدْ | + past = "already / indeed"; + present = "sometimes / may" | "already / indeed" | tense of the following verb |
| حَتَّى | preposition / conjunction | "until / so that / even" | following structure |
| إِلَّا | exception | "except / but" | vs لا (negation) |
| لَوْ / لَوْلَا | conditional | "if (only) / were it not for" | — |
| إِذَا / إِذْ | temporal / conditional | "when / since" | future vs past clause |
| بَلْ / أَوْ / ثُمَّ / فَـ / وَ | conjunctions | "rather / or / then / so / and" | — |
| نَعَمْ / بَلَى / كَلَّا | response particles | "yes / yes-indeed / nay" | نِعْمَ (praise verb) ≠ نَعَمْ |

## Prepositions (حروف الجر) — attested in corpus with glosses

مِنْ "from", فِي "in", عَلَى "on/upon", إِلَى "to/toward", عَنْ "about/from", مَعَ "with", بِ "with/by/in",
لِ "for/to", كَ "like/as", عِنْدَ "with/near/in the sight of", قَبْلَ "before", بَعْدَ "after", أَمَامَ "in front of",
فَوْقَ "above", تَحْتَ "under", بَيْنَ "between", وَرَاءَ "behind", حَوْلَ "around", مُنْذُ "since". A preposition +
pronoun reshapes wording by referent — see [`jar-majrur.md`](jar-majrur.md).

## Pronouns (الضمائر) — attested

أَنَا "I", نَحْنُ "we", أَنْتَ/أَنْتِ "you", أَنْتُمْ "you (m.pl)", أَنْتُمَا "you two", هُوَ "he", هِيَ "she",
هُمَا "the two of them", هُمْ "they", هُنَّ "they (f)". Demonstratives هَذَا/هَذِهِ/ذَلِكَ/تِلْكَ/أُولَٰئِكَ and relatives
الَّذِي/الَّتِي/الَّذِينَ behave as referential closed‑set words, not content roots.

## Hand‑off

A particle token is glossed from this closed set, **distinguished by the content‑letter harakah**, never by `norm()`.
If the decisive diacritic is absent → pending(homograph_haraka). A particle never receives a content‑verb or
content‑noun gloss (the §referent guard and §POS‑mismatch blockers apply).
