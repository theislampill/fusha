# Jar–majrūr (الجار والمجرور) — preposition + governed noun/pronoun

A preposition (حرف جر) plus the noun or pronoun it governs forms a **phrase** whose English wording depends on the
referent and the construction — not on the preposition's lexeme alone. Gloss the **phrase role**, not the bare
preposition. Machine‑readable renderings: [`rules/preposition-pronoun-rules.json`](../rules/preposition-pronoun-rules.json).

## Preposition + pronoun: the wording moves with the referent

| surface | analysis | gloss by referent |
|---|---|---|
| بِهِ | بِ + ـهِ (3sg) | "in it / in him / by it" (instrument, belief‑object, or oath by context) |
| لَهُ | لِ + ـهُ (3sg) | "for him / to him / belongs to him"; لَهُ ٱلْمُلْك → "to Him belongs …" |
| فِيهِ | فِي + ـهِ | "in it / therein" |
| عَلَيْهِ | عَلَى + ـهِ | "upon him / against him" |
| مِنْهُ | مِنْ + ـهُ | "from it / of it" |
| إِلَيْنَا | إِلَى + ـنا (1pl) | "to us / unto us" |

The lexeme is fixed; only the rendered English changes with who/what the suffix points to. If the referent is
unknown in range → pending(referent_unresolved).

## The hard guard (do not regress)

**إِلَيْنَا is the jar‑majrūr إِلَى + ـنا (root أ‑ل‑ي), NOT the root ل‑ي‑ن "soft/pliant".** `norm()` over‑recalls
toward لين; re‑read with `norm_strict`/`bare` before glossing. Likewise the final ـنا of a jar‑majrūr is the 1pl
pronoun, while a final ـًا on other tokens is ʾalif al‑tanwīn (قُرْءَانًا), **not** the pronoun نا — use
`ends_tanwin_alef()`.

## Pronoun suffix ≠ new stem

Attached ـه/ـها/ـهم/ـكم/ـنا change wording, never the head sense, and never invent a new root. A suffix is stripped
for lemma lookup but its referent is what the gloss renders.

## Hand‑off

Emit the phrase‑level gloss ("to us", "in it") with `decision: resolved` when the referent is fixed by context;
otherwise pending(referent_unresolved). The preposition itself is never glossed as a content word.
