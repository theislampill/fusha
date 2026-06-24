# Procedure: nominal-derivative decision

**Input:** a surface that looks derived (participle/intensive/adjective/elative/time-place/instrument)
+ root + QAC POS if available.
**Goal:** classify the derivative type and emit its **nominal** gloss shape — never a finite verb.

## Steps

1. **Confirm it is a derivative, not a finite verb.** QAC POS = N/ADJ ⇒ derivative; POS = V ⇒ stop,
   use `verb-form`. A leading مُـ with no subject agreement, or a فاعل/فعيل/أفعل/مفعل/مفعال shape,
   signals a derivative.
2. **Match the pattern (wazn)** against `references/nominal-derivatives.md`:
   - فَاعِل / مُفْعِل (penult **kasra**) → **اسم الفاعل** → "(the) doer".
   - مَفْعُول / مُفْعَل (penult **fatḥa**) → **اسم المفعول** → "(that which is) X-ed".
   - فَعَّال / فَعُول / فَعِيل / فَعِل → **صيغة المبالغة** → intensive "much/All-X" (read prefix vowel:
     فَعَّال a- = intensive; مِفْعَال mi- = instrument).
   - فَعِيل / فَعِل / فَعْلَان / أَفْعَل(colour/defect) → **الصفة المشبهة** → permanent adjective.
   - أَفْعَل (+ مِن / ال) → **اسم التفضيل** → "more/most X".
   - مَفْعَل / مَفْعِل → **اسم الزمان/المكان** → "time/place of X".
   - مِفْعَل / مِفْعَال / مِفْعَلَة → **اسم الآلة** → "instrument for X".
3. **Resolve the load-bearing ambiguities:**
   - مُفْعِل vs مُفْعَل → the **penult vowel** (مُعَلِّم teacher / مُعَلَّم taught).
   - فَعَّال vs مِفْعَال → the **prefix vowel** (غَفَّار / مِفْتَاح).
   - عَلِيم (mubālagha "All-Knowing") vs عَالِم (fāʿil "knower") vs the verb عَلِمَ — never the verb.
   - أَفْعَل elative vs colour/defect vs 1st-sg verb (أَعْلَمُ) → iʿrāb/context (route to nahw if needed).
4. **Referent guard** (hand to nahw `referent-context`): صَالِح, مُحَمَّد, يَحْيَى, عَاد may be common
   derivative OR proper noun — decide by context; never put a verb gloss on a proper noun.
5. **Emit** the nominal gloss shape for the chosen type, or `pending` with the exact ambiguity if the
   penult/prefix vowel or referent cannot be fixed.

## Forbidden
- A finite-verb gloss on any derivative (عَلِيم≠"to be in pain"; كَظِيم≠"to suppress").
- Choosing فاعل vs مفعول without reading the penult vowel.
- `norm()`-certifying (it drops the very vowels that decide the type).

## Test
`evals/nominal-derivative-error-eval.jsonl` — every row's `expected_decision` must hold; a change that
re-introduces a verb gloss for عَلِيم/كَظِيم/عَادٍ is wrong.
