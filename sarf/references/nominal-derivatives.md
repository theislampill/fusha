# Nominal derivatives (المشتقات) — pattern → gloss-shape contract

The derived nouns are the densest source of qamus-highlight POS errors: a derivative is a NOUN, so it
takes a **nominal** gloss, never a finite-verb gloss. Read the pattern (wazn) and the penult vowel
before authoring. Each type below gives its pattern(s), the gloss shape, and the confusion to avoid.

| type | pattern(s) | gloss shape | confusion to block |
|---|---|---|---|
| **اسم الفاعل** active participle | فَاعِل (I); مُفْعِل/مُفَعِّل/مُفاعِل… (derived, penult **kasra**) | "(the) doer / one who X-es" | vs the finite verb; vs اسم المفعول (penult vowel) |
| **اسم المفعول** passive participle | مَفْعُول (I); مُفْعَل/مُفَعَّل… (derived, penult **fatḥa**) | "(that which is) X-ed" | vs اسم الفاعل; vs maṣdar |
| **صيغة المبالغة** intensive | فَعَّال، فَعُول، فَعِيل، مِفْعَال، فَعِل | "much/ever-X-ing; All-X" | vs اسم الفاعل (عَلِيم≠عَالِم); vs اسم الآلة (فَعَّال vs مِفْعَال — read prefix vowel) |
| **الصفة المشبهة** assimilate adjective | فَعِيل، فَعِل، فَعْل، أَفْعَل (colour/defect), فَعْلَان | "(permanently) X" (adjective) | vs the verb (كَظِيم≠"to suppress"); vs اسم التفضيل (أَفْعَل) |
| **اسم التفضيل** elative | أَفْعَل (+ من / definite) | "more / most / -er / -est X" | vs الصفة المشبهة أَفْعَل (colour); vs 1st-sg verb (أَعْلَمُ) |
| **اسم الزمان/المكان** time/place | مَفْعَل، مَفْعِل | "time/place of X-ing" | vs the verb; vs maṣdar mīmī |
| **اسم الآلة** instrument | مِفْعَل، مِفْعَال، مِفْعَلَة (and modern فَعَّالَة) | "tool/instrument for X" | vs صيغة المبالغة (مِفْعَال vs فَعَّال) |
| **المصدر** verbal noun | many (فَعْل، فُعُول، فِعَالَة، تَفْعِيل، إِفْعَال…) | "the act of X-ing" (nominal) | vs participle; never a finite verb |

## The two load-bearing reads

1. **Penult vowel decides فاعل vs مفعول in derived forms:** مُعَلِّم (kasra) = teacher (active);
   مُعَلَّم (fatḥa) = taught one (passive). Same for مُنزِل/مُنزَل, مُرسِل/مُرسَل.
2. **The prefix vowel decides مبالغة vs آلة:** فَعَّال (a-) = intensive doer (غَفَّار "Ever-Forgiving");
   مِفْعَال (mi-) = instrument (مِفْتَاح "key").

## Hard "never a verb" examples (live qamus-highlight scars)

- عَلِيم "All-Knowing" (mubālagha) — the live wrong was "to be in pain" (root ألم) → POS + homograph error.
- كَظِيم "(one) suppressing grief" (ṣifa mushabbaha) — the live wrong was the verb "to suppress anger".
- عَادٍ "a transgressor" (ism fāʿil, منقوص, root عدا) — **not** the tribe ʿĀd.
- صَالِحًا "righteous" (ṣifa/ism fāʿil) — not the Prophet Ṣāliḥ unless context demands.
- رَسُول "messenger", ٱبْن "son", مُحَمَّد/أَحْمَد (proper) — nouns, never "to send / to build / to praise".

See [`procedures/nominal-derivative-decision.md`](../procedures/nominal-derivative-decision.md),
[`procedures/masdar-participle.md`](../procedures/masdar-participle.md), and the machine fixture
[`evals/nominal-derivative-error-eval.jsonl`](../evals/nominal-derivative-error-eval.jsonl).
