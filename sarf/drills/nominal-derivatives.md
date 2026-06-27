# Drills — nominal derivatives (المشتقات)

Recognition + production drills built from the qamus-highlight scars. Each drill: contrast pair →
rule → recognition Q → production Q → answer. Generated/extendable from
`evals/nominal-derivative-error-eval.jsonl`.

## <a name="fail-maful"></a>1. اسم الفاعل vs اسم المفعول (penult vowel)
- Pair: مُعَلِّم (teacher) / مُعَلَّم (taught one). Rule: penult **kasra**=active, **fatḥa**=passive.
- Recognition: read مُنزَل — active or passive? **Passive** (penult fatḥa) → "(that which is) sent down".
- Production: form the active participle of أَرْسَلَ → **مُرْسِل** "sender"; the passive → **مُرْسَل** "sent".

## <a name="mubalagha"></a>2. صيغة المبالغة vs اسم الفاعل
- Pair: عَالِم (a knower) / عَلِيم (All-Knowing). Rule: فَعِيل/فَعَّال/فَعُول = intensive.
- Recognition: غَفُور — plain or intensive? **Intensive** → "Most Forgiving" (not "forgiver").
- Production: intensive of كَفَرَ on فَعَّال → **كَفَّار** "utterly ungrateful". Never the verb.

## <a name="sifa"></a>3. الصفة المشبهة vs the verb
- Pair: كَظِيم (adjective "suppressing grief") / كَظَمَ (verb "suppressed"). Rule: فعيل/فعل = permanent quality.
- Recognition: حَلِيم with a human referent → "forbearing" (adjective), not a divine Name, not a verb.
- Production: ṣifa from عَطِشَ on فَعْلَان → **عَطْشَان** "thirsty".

## <a name="tafdil"></a>4. اسم التفضيل vs colour/defect vs 1st-sg verb
- Pair: أَكْبَر "greater" / أَحْمَر "red" / أَعْلَمُ "I know". Rule: أَفْعَل elative needs مِن or ال or genitive.
- Recognition: أَعْلَمُ in هُوَ أَعْلَمُ → elative "knows best"; in 1st-sg context → verb "I know" (iʿrāb decides).
- Production: elative of حَسُنَ → **أَحْسَن** "better/best".

## <a name="zaman-makan"></a>5. اسم الزمان/المكان vs the verb
- Pair: مَوْعِد (appointed time/place) / وَعَدَ (promised). Rule: مَفْعَل/مَفْعِل time-or-place.
- Recognition: مَسْجِد → "place of prostration", not a verb.
- Production: place-noun of طَلَعَ → **مَطْلَع** "rising-place/time".

## <a name="ala"></a>6. اسم الآلة vs صيغة المبالغة
- Pair: مِفْتَاح (key) / غَفَّار (Ever-Forgiving). Rule: مِفْعَال (mi-) instrument vs فَعَّال (a-) intensive.
- Recognition: مِيزَان → "scale" (instrument), not an intensive doer.
- Production: instrument of فَتَحَ on مِفْعَال → **مِفْتَاح**.

## <a name="false-split"></a>7. False clitic split (segmentation)
- ٱلْمُلْك ≠ مُلك+ك (ك is a radical); لَهُ = "for him" (preposition+pronoun); قُرْءَانًا ≠ stem+نا (tanwīn-alif);
  رَحْمَة's ة is feminine, not the pronoun ه. Drill: segment each into proclitic+stem+enclitic by morphology.

## <a name="populated-pos-leak"></a>8. Populated hover still wrong: nominal POS leakage
- Pair: أَفْلَحَ "to succeed" / ٱلْمُفْلِحُونَ "the successful ones". Rule: a live hover can be populated and still
  fail dogfooding if it uses the entry/root infinitive on a nominal token.
- Recognition: `ٱلْمُفْلِحُونَ` currently carrying "to succeed" is not rich-certified. It is a plural nominal
  contribution — **"the successful ones"** — and needs token-only review.
- Recognition: `بِنَآءً` carrying "to build" is a noun/result such as **"a structure / building / canopy"**, not the
  verb "to build".
- Recognition: `مُّطَهَّرَةٌ` carrying "to purify" is a passive participle/adjectival form: **"purified"**.
- Production: reshape `جَاعِلٌ` from "to make" to an active participle contribution: **"one who makes/places"**.
- Gate: these are `populated_hover_pos_leakage` rows. Do not move them to repair-ready until exact token address,
  sarf shape, and token contribution are reviewed; do not propagate by surface family.
