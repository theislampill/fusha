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

## Dogfood finding: VN-03 nominal rows inside verb families

The VN-03 tranche found nominal/adjectival rows that were still linked through
verb-entry or component evidence:

- `ضَعِيفًا` is an accusative indefinite nominal/adjectival token. The visible
  word "weak" may be reasonable, but a verb-entry component cannot certify its
  noun/adjective role or i'rab.
- `ٱلدِّينِ`, `دِينُكُمْ`, and other `دِين` rows are lexical nouns in
  definite, genitive, or possessed constructions. Reject "to be bound..." as a
  token hover unless the exact row is actually verbal.
- `مُسَلَّمَةٌ`, `مُسْلِمَيْنِ`, `مُسْلِمَات`, and `ٱلْمُسْلِمُونَ` are
  shaped nominal/participle/person tokens. The abstract concept "Islam" is
  curriculum metadata, not a complete hover for these surfaces.
- `زِينَتَهُنَّ` and similar rows carry a nominal host plus possessor even
  when they sit in a verb/root family.

When a token is nominal but the only evidence is a verb/root family, route to
`token_only_review` or `component_only_blocker`. Do not let component
candidates become whole-token certification.

## Dogfood finding: VN-04 ذ ك ر shape collisions

The VN-04 tranche exposed a compact POS/voice collision in the `ذ ك ر` family:

- `ذَكَرٍ`, `ٱلذَّكَرُ`, and `ٱلذُّكُورَ` are male/masculine nominal rows.
- `ذِكْر`, `ٱلذِّكْرَ`, and `ذِكْرِ` are remembrance/reminder nominal rows.
- `ذُكِرَ` and `ذُكِّرَ` are passive finite-verb surfaces.

These surfaces cannot share a hover by root family or lenient normalization.
The vowels, article, case ending, and passive signature are the gate. If the
surface is `ٱلذِّكْرَ`, reject a verb infinitive such as "to remember"; if the
surface is `ذُكِرَ`, reject a nominal "male" or root-family noun row. Route the
row to exact-address sarf + nahw review when the entry linkage cannot prove
which POS/voice is intended.

## Dogfood finding: VN-05 verb-entry nouns and lemma-shape collisions

VN-05 found nominal rows that were still traveling through verb/root families:

- `ٱلْقَصَصِ` is a definite/genitive noun surface in the ق ص ص family. It must
  not inherit the finite/infinitive gloss "to relate a story".
- `غَالِبٌ` is a nominal or active-participle-looking surface. It must not
  inherit the verb infinitive "to overcome, defeat" without nominal role
  review.
- `رَجُلَيْنِ`, `رِجَالًا`, `فَرِجَالًا`, and `أَرْجُلِهِم` show that
  ر ج ل is not one hover family. Man/men, leg/feet, and "on foot" readings
  require lemma/shape/context separation.
- `وُجُوهَهُمْ`, `وَجْهِهِۦ`, and related `وَجْه` rows must keep
  singular/plural and suffix morphology before choosing a common, idiomatic,
  or referent-sensitive sense.

If the row is string-correct but lacks number/state/case/suffix or
referent/context proof, route it to `needs_renderer_segments` or
`needs_nahw_review`. A root-family entry cannot certify a noun token merely
because the English word is plausible.

## Dogfood finding: VN-06 lexical nouns inside verb-entry families

VN-06 found nominal rows that were easy to read in English but unsafe as
verb-entry hovers:

- `ثَمَرَةٍ` and `ثَمَرِهِۦ` are fruit nouns. They must not be certified from
  `أَثْمَرَ` ("to bear fruit") without noun number/state/case and any
  possessive suffix.
- `مَرَضٌ` / `مَرَضًا` are sickness/state nouns. They can be context-sensitive
  ("illness", "spiritual sickness", "hypocrisy") and are not the finite verb
  `مَرِضْتُ`.
- `ٱلْمَنَّ` is a lexical noun ("manna") and not the verb `مَنَّ`; the article
  and host noun shape are part of the decision.
- `مُصَلًّى` is a place/nominal derivative; do not turn it into a finite
  prayer verb.
- `غَضَبٍ`, `خِزْيٌ`, `ذُو`, and `حَوْلَهُۥ` need nominal/adverbial or
  possessed-noun review before the hover can teach a learner.

When a live row is populated but the evidence path is "verb entry -> nominal
surface", emit `verb_entry_nominal_derivative_pos_leak` or
`nominal_pos_may_leak_verbal_infinitive`. This is a skill defect unless the
row is explicitly documented as renderer-only or Qamus-data-only.

## Dogfood finding: VN-07 obligation derivatives inside a verb tranche

VN-07 found `فَرِيضَةً`, `مَّفْرُوضًا`, and `فَارِضٌ` near the `فَرَضَ`
verb-entry family. These are nominal, participial, or adjectival surfaces,
not finite "to ordain" hovers.

For obligation/allotment rows:

- Read the exact surface before reusing a verb-entry gloss.
- If the token is `مفعول`-like (`مَّفْرُوضًا`), route as passive participle or
  nominal derivative: "ordained / prescribed / allotted" by context.
- If the token is a lexical noun (`فَرِيضَةً`), route as a noun such as
  "portion / obligation / prescribed share" by exact context.
- If the token is adjectival or active-participle-looking (`فَارِضٌ`), do not
  certify from the finite verb family without POS and context review.

The repeated defect class is `verb_entry_nominal_derivative_pos_leak`: the row
may be English-readable, but it is not rich-certified until the nominal shape,
case/state, and syntactic role are visible to the learner.
