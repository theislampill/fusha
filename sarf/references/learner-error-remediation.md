# Learner error remediation (sarf) — Madinah-study failure modes → diagnosis → fix

Encodes the morphological-error classes documented in the Islamic University of Madinah study of
non-Arab (ʿajamī) learners' errors in nominal derivatives, mapped to the exact sarf procedure that
diagnoses and fixes each. Used both to (a) **teach** ajamī learners zero→fuṣḥā and (b) **guard** the
qamus-highlight authoring engine against the same mistakes. The engine and the learner share one map.

| # | error class | symptom | diagnosis procedure | fix / rule |
|---|---|---|---|---|
| 1 | nominal-derivative confusion | wrong derivative type chosen | `nominal-derivative-decision` | read pattern + penult vowel; `references/nominal-derivatives.md` |
| 2 | اسم الفاعل / اسم المفعول | active vs passive swapped | `nominal-derivative-decision` | penult kasra=active, fatḥa=passive (مُعَلِّم/مُعَلَّم) |
| 3 | صيغة المبالغة confusion | intensive read as plain فاعل | `nominal-derivative-decision` | فَعَّال/فَعُول/فَعِيل intensive (عَلِيم≠عَالِم) |
| 4 | الصفة المشبهة confusion | adjective read as verb | `nominal-derivative-decision` + `homograph-risk` | فعيل/فعل permanent quality (كَظِيم) |
| 5 | اسم التفضيل confusion | elative read as verb/colour | `nominal-derivative-decision` | أَفْعَل elative vs colour/defect vs 1st-sg verb |
| 6 | اسم الزمان / اسم المكان | time/place read as verb | `nominal-derivative-decision` | مَفْعَل/مَفْعِل (مَوْعِد, مَسْجِد) |
| 7 | اسم الآلة confusion | instrument read as intensive | `nominal-derivative-decision` | مِفْعَال vs فَعَّال (prefix vowel) |
| 8 | ignorance of rule constraints | applies a pattern where the root forbids it | `verb-form` + `weak-root` + `root-pattern-risk-rules` | check root class before pattern |
| 9 | long-vowel vs short-vowel | كَاتِب vs كَتَبَ; مِيزَان vs … | `root-decision` (normalization ladder) | the ا/و/ي length changes the lexeme; never `norm()`-certify |
| 10 | tanwīn-nūn vs original nūn | إِنسَان's ن read as added نون | `root-decision` | distinguish a radical ن from tanwīn (ـٌ/ـٍ/ـً) — `false-clitic-split-eval` |
| 11 | faulty separation/segmentation | stress-based mis-split | `suffix-pronoun-state` + `false-clitic-split-eval` | segment proclitic+stem+enclitic by morphology, not sound |
| 12 | mother-tongue transfer | L1 pattern imposed | `learner-error-diagnosis` | name the L1 interference; drill the Arabic pattern |
| 13 | weak/hamzated/geminated/quadriliteral | hidden/altered radicals | `weak-root` / `hamza-root` / `doubled-root` | recover the radical before glossing |
| 14 | broken plural / gender / number | plural keyed by surface, gender guessed | `noun-plural-gender` | broken plural shares the ROOT, not the surface; gender is data |
| 15 | false clitic stripping | root-final ك/ه/ي taken as a pronoun | `suffix-pronoun-state` + `false-clitic-split-eval` | ٱلْمُلْك, لَهُ, رَحْمَة, قُرْءَانًا guards |

## Teaching use (ajamī, zero → fuṣḥā)

For each class: show the contrast pair (مُعَلِّم/مُعَلَّم, عَالِم/عَلِيم, كَظِيم vs the verb), state the rule,
drill it ([`drills/nominal-derivatives.md`](../drills/nominal-derivatives.md)), then test recognition +
production. A learner error is mapped back to the exact class above and re-drilled — same loop the
engine uses to refuse an unsafe gloss. See [`procedures/learner-error-diagnosis.md`](../procedures/learner-error-diagnosis.md).
