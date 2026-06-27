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

## <a name="vn00-family-spread"></a>9. VN-00: family spread is not a nominal hover
- Recognition: `عَذَابٌ` carrying only "to punish" or a verb family is a noun/maṣdar result, not the verb.
- Recognition: `إِحْسَانًا` carrying "good, beautiful, excellent, best..." mixes adjective, doer, elative, and maṣdar
  meanings. Classify the maṣdar/action noun before authoring a hover.
- Recognition: `ٱلْمُحْسِنِينَ` is an active participle plural. It needs plural/doer shape, not a broad "goodness" family.
- Recognition: `ٱلْعَٰلَمِينَ` may need concept teaching elsewhere, but the hover slot needs a concise token contribution,
  not a paragraph.
- Gate: `masdar_gets_semantic_family_spread` and `possessive_plural_noun_gets_concept_entry_spread` rows stay
  token-address gated until the noun class, number, definiteness, and any attached possessor are explicit.

## <a name="vn01-nominal-leak"></a>10. VN-01: nominal surfaces inside verb entries

- Recognition: `مَّخْتُومٍ` carrying "to seal" is passive/nominal, not a verb infinitive.
- Recognition: `مِثْلُ` carrying "to be like" is a nominal comparison token; nahw certifies the construction after
  sarf blocks the infinitive.
- Recognition: `وَعْدُ` is a maṣdar/noun "promise", not the finite act "to promise".
- Recognition: `مَيْتًا` is an adjectival/nominal state "dead", not a verbal phrase.
- Recognition: `شَرِيكَ` is a nominal "partner/associate" in context, not an omnibus shirk-family entry.
- Gate: if a token is nominal but linked through a verb/root entry, route as `token_only_override` or
  `needs_sarf_review`; never let the entry family choose the hover by surface alone.

## <a name="vn02-proper-common"></a>11. VN-02: title, proper name, and common-word collisions

- Recognition: `يُحْيِي` is a finite verb in 36:78, not the proper noun
  `يَحْيَى`. Vocalization and POS block the name hover.
- Recognition: `صَالِحًا` may be the Prophet Ṣāliḥ or the common adjective
  "righteous"; exact context decides.
- Recognition: `ٱلْمَسِيحُ` is a definite title token. It needs article +
  title/case metadata even when the English gloss "the Messiah" is safe.
- Recognition: `عَادَ` is a finite verb in some rows and the people-name in
  others. Harakāt/POS decide.
- Gate: proper-name, title, and common/adjectival uses remain
  `populated_uncertified` until proper/common status, case, and source address
  are explicit. A safe-looking name string is not rich certification.

## <a name="vn03-noun-verb-entry"></a>12. VN-03: noun surfaces inside verb or concept entries

- Recognition: `ضَعِيفًا` carrying only component evidence from a verb entry
  is not a finite verb. It is an accusative indefinite nominal/adjectival token;
  exact i'rab still gates rich certification.
- Recognition: `ٱلدِّينِ` carrying "to be bound..." is a noun in a definite or
  genitive construction, not a verb infinitive.
- Recognition: `دِينُكُمْ` must preserve the `كُمْ` possessor; a broad
  "Faith, religion..." entry gloss is string-populated but not rich.
- Recognition: `مُسْلِمَيْنِ` and `مُسَلَّمَةٌ` are shaped nominal/participle
  or adjectival tokens. The concept "Islam" alone is not the token hover.
- Recognition: `زِينَتَهُنَّ` is a nominal host plus feminine-plural possessor,
  even if it appears in a زين verb family.
- Gate: concept entries and component candidates are internal routing evidence.
  They do not replace noun type, number, gender, state, case, and possessor
  review.

## <a name="vn04-dhikr-dhakar"></a>13. VN-04: ذ ك ر is not one hover family

- Recognition: `ٱلذِّكْرَ` carrying "to take note of, mention; remember..."
  is a definite noun/reminder surface, not a verb infinitive.
- Recognition: `ذُكِرَ` carrying the same broad entry prose is a passive finite
  verb surface; it needs voice/POS review, not a noun-entry shortcut.
- Recognition: `ذَكَرٍ`, `ٱلذَّكَرُ`, and `ٱلذُّكُورَ` are male/masculine
  nominal rows; they do not certify `ذِكْر` reminder rows.
- Recognition: `سَآئِبَةٍ`, `وَصِيلَةٍ`, `بَحِيرَةٍ`, and `حَامٍ` are
  customary livestock noun rows. Their entry strings may be readable, but rich
  certification still needs noun shape, case, and any visible particle such as
  `وَ`.
- Gate: vowels and article/case are source evidence. Do not collapse `ذَكَر`,
  `ذِكْر`, and `ذُكِرَ` under a root-family hover.
