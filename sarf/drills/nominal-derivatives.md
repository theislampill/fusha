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

## <a name="vn05-body-part-lemma-shape"></a>14. VN-05: body-part, story noun, and lemma-shape collisions

- Recognition: `ٱلْقَصَصِ` carrying "to relate a story..." is a definite noun
  surface. It needs story/narrative noun review, not verb-infinitive prose.
- Recognition: `غَالِبٌ` carrying "to overcome, defeat" is an active
  participle or nominal/adjectival surface. Do not put a finite/infinitive verb
  gloss on it.
- Recognition: `رَجُلَيْنِ`, `رِجَالًا`, `فَرِجَالًا`, and `أَرْجُلِهِم`
  share a root family but not one hover lane: man/men, on-foot usage, and
  leg/feet readings require lemma-shape and context review.
- Recognition: `ٱلْقُلُوبُ`, `قَلْبَهُۥ`, `يَدَيْهِ`, and `وُجُوهَهُمْ`
  are not rich-certified by bare lemma strings like "heart", "hand", or
  "face". Number, article/state, and suffix/possessor are learner-visible.
- Recognition: `لَّازِبٍ` begins with lām as part of the lexical host; it is
  not a prefixed lām particle.
- Gate: root and entry family are not enough. Separate article, number, state,
  suffix, derivative type, and referent before moving a populated noun hover
  out of `populated_uncertified`.

## <a name="vn06-verb-entry-nouns"></a>15. VN-06: lexical nouns inside verb-entry candidate families

- Recognition: `ثَمَرَةٍ` carrying only fruit-family evidence from
  `أَثْمَرَ` is a noun token. It needs noun case/state and context before rich
  certification.
- Recognition: `ثَمَرِهِۦ` also carries a possessor. A bare host or verb entry
  does not teach the suffix.
- Recognition: `مَرَضٌ` and `مَرَضًا` are sickness/state nouns. Do not use the
  finite `مَرِضْتُ` verb lane as their hover proof.
- Recognition: `ٱلْمَنَّ` is a definite lexical noun ("manna"), not the verb
  `مَنَّ` and not the preposition `مِن`.
- Recognition: `مُصَلًّى` is a place/nominal derivative; a prayer verb
  infinitive is not its token contribution.
- Recognition: `غَضَبٍ`, `خِزْيٌ`, `ذُو`, and `حَوْلَهُۥ` need exact nominal,
  possessed, or adverbial role review when the entry family is broad.
- Gate: a row can gain more useful component candidates while staying
  `two_vote_required`. Component evidence is not a repair-ready hover.

## <a name="vn14-verb-entry-nominals"></a>16. VN-14: verb-entry families can carry nominal rows

- Recognition: `وَسَطًا`, `ٱلْوُسْطَىٰ`, `أَوْسَطِ`, and
  `أَوْسَطُهُمْ` are not automatically finite verbs just because they sit in
  a `و س ط` entry family. Decide exact POS, elative/nominal type, case/state,
  and suffix before trusting the hover.
- Recognition: `ٱلْوَسْوَاسِ` is definite lexical/nominal, not the finite
  verb `وَسْوَسَ`.
- Recognition: `ثَمَرِهِۦ` is a noun host plus suffix/referent. A hover like
  "to fruit; bear fruit" is verb-entry prose leakage.
- Recognition: `بَدِيعُ` and `بِدْعًا` require nominal/adjectival or relation
  review; the entry family "to invent" does not certify the token.
- Gate: if a detector says "finite verb" but the exact surface is nominal,
  stop and reroute. The fix is not a live hover apply; it is POS/derivative
  review plus a precise blocker or repair candidate.

## <a name="vn15-colors-and-nominals"></a>17. VN-15: color and nominal rows in verb families

- Recognition: `ٱلْءَازِفَةُ` is a definite nominal row; a broad "to be fast
  approaching" verb entry is not a token hover.
- Recognition: `ٱلْمُخْبِتِينَ`, `وَالذَّارِيَاتِ`, and
  `مَطْوِيَّٰتٌۢ` are plural, participial, adjectival, or lexical nominal
  rows that need noun/adjective review before entry-family reuse.
- Recognition: `ٱلْأَسْوَدِ`, `ٱلْأَبْيَضُ`, and `ٱلْأَخْضَرِ` are
  color/adjectival surfaces. Their article, case, and ṣifa/context role matter
  before the learner hover is trusted.
- Recognition: `وِفَاقًا` and `تَوْفِيقِىٓ` may sit near a verb entry, but
  the exact row must first be classified as masdar/nominal/possessed or
  finite, not guessed from the English family.
- Gate: a verb source key is only candidate evidence. If the exact token is a
  noun, adjective, participle, elative, color adjective, or masdar, route to
  nominal/POS review and keep `may_apply_live=false`.

## <a name="vn16-material-nouns"></a>18. VN-16: material nouns, participles, and possessed hosts

- Recognition: `مُكِبًّا` is a participial/nominal surface inside a verb-family
  review lane. It is not automatically a finite verb hover.
- Recognition: `لَذَّةٍ` and `لَّذَّةٍۢ` are lexical/masdar-like noun rows whose
  case/state and sentence role matter before a hover can teach them.
- Recognition: `ٱللُّؤْلُؤُ`, `ٱللُّؤْلُؤِ`, `ٱلْحَدِيدِ`,
  `ٱلْحَدِيدَ`, `ٱلْقِطْرِ`, and `ٱلْيَاقُوتُ` are material nouns. Their
  definiteness/case is part of the token, not decoration.
- Recognition: `لُحُومُهَا` is a plural noun host plus suffix/referent. A
  host-only gloss does not explain the written token.
- Gate: exact noun type, state, case, number, and suffix must be named before a
  nominal row can move beyond `populated_uncertified`.
