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

## Dogfood finding: VN-00 derivative prefix is not enough by itself

VN-00 found `ٱلْمُؤْمِنُ` at 59:23:11 with a visible `مُـ` derivative prefix,
but the post-prefix host still rendered as a generic `NOUN`. That is not
instructionally complete for a derived nominal token.

For definite active-participle rows such as `ٱلْمُؤْمِنُ`:

- keep the article visible as article metadata;
- keep `مُـ` visible as the derivative-prefix signal, not as a root letter;
- label the remaining host as the active-participle stem/host, not a generic
  noun when richer role metadata is available;
- keep the supported renderer class (`qg-noun-stem` or `qg-adjective`) while
  recording the active-participle fact in the role, label, morphline, and
  learner explanation;
- expose the certified root/base such as `أ م ن` where the evidence supports
  it.

If the renderer/schema cannot display the derivative prefix plus stem/host
without minting a new unsupported class, route to `renderer_and_nominal_review`
or a renderer fixture packet. Do not call the row rich-certified merely because
the prefix is colored.

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

## Dogfood finding: VN-08 nominal rows near verb or particle candidates

VN-08 added several nominal/POS traps:

- `تَرَبُّصُ` is a masdar/nominal row in the waiting family, not a finite
  "to wait" token.
- `إِلًّۭا` is a lexical noun ("bond/tie") and must not be routed as the
  exception particle `إِلَّا`.
- `بِكْرٌ` is a lexical noun/adjective row; a leading bā-looking spelling in
  the transliteration or stripped shape must not create a bā' + host PP route.
- `لِلَّهِ` is a preposition/proper-name phrase, not a possessed noun suffix
  row.

If a row's English is readable but its evidence path is root/entry/component
candidate rather than exact token POS, keep it in `token_only_review`,
`needs_nahw_review`, or `component_only_blocker`.

## Dogfood finding: VN-09 entry-family collision and nominal suffixes

VN-09 repeated nominal/POS leakage inside verb and mixed families:

- `ٱلشَّهَوَٰتِ` is a plural nominal row in the desire family, not a finite
  "to desire" token.
- `مَوَٰقِيتُ` is a plural noun/time row, not a finite appointed-time verb
  hover.
- `ٱلسِّجْنُ` is a prison noun, not a "to imprison" verb.
- `ٱلْأَشْقَى` is an elative/superlative adjective, not a finite misery verb.
- `مَوَاخِرَ`, `وَالنَّاشِطَاتِ`, `وَمُهَيْمِنًا`, and `وَأَجْدَرُ` need
  nominal derivative or adjective review before any root-family gloss is
  trusted.
- `أَقْوَٰتَهَا` and `تَفَثَهُمْ` are suffix-bearing nominal hosts; the suffix
  must survive in sarf output even if nahw later decides the exact English.

VN-09 also found entry-family collisions such as `لِمَا` / `لَّمَّا` /
`ٱللَّمَمَ`, and `يَعْصِمُكَ` / `عَاصِمٍۢ` / `بِعِصَمِ`. Split by strict
surface, POS, form, suffix, and function before any candidate is reusable.

## Dogfood finding: VN-10 verb-entry nominal/POS leakage

VN-10 found more nominal surfaces travelling through verb-entry families:

- `ٱلْمُسْتَعَانُ` is nominal/passive-participle-like, not the infinitive
  "to assist".
- `ٱلْغَيْظِ` / `ٱلْغَيْظَ` are anger/rage nouns inside an enrage family.
- `ٱلْمَفَرُّ`, `ٱلْوِرْدُ`, `ٱلْبَطْشَةَ`, and `ٱلرِّعَآءُ` need lexical
  noun, masdar, place, or plural/person review before any verb-entry wording.
- `ٱلْمُوقَدَةُ` is definite passive-participle/adjectival-looking; do not
  certify it from an active "to kindle" entry alone.
- `ٱلْأَسْوَدِ` is adjectival/color morphology; exact POS and i'rab/context
  outrank root-family prose.

Rule: if a verb-entry tranche yields a definite noun, masdar, participle,
elative, adjective, or lexical noun, route to nominal/POS review. The row may
be string-readable, but it is not rich-certified until noun type, case/state,
derivative class, and any suffix/referent are visible.

## Dogfood finding: VN-15 nominal rows inside verb families

VN-15 found another set of nominal or derivative rows that cannot inherit
finite verb prose:

- `وِفَاقًا` and `تَوْفِيقِىٓ` are nominal or maṣdar-like rows in a
  reconcile/success family. Do not certify them from a finite verb gloss.
- `ٱلْءَازِفَةُ`, `ٱلْمُخْبِتِينَ`, `وَالذَّارِيَاتِ`, and
  `مَطْوِيَّٰتٌۢ` are definite, plural, participial, adjectival, or lexical
  nominal rows near verb entries. They need POS, derivative class, case/state,
  and any article/function pieces before hover trust.
- `ٱلْأَسْوَدِ`, `ٱلْأَبْيَضُ`, and `ٱلْأَخْضَرِ` show that color/adjectival
  morphology is not a verb infinitive. Exact article, case, and ṣifa/context
  review decide the learner hover.

Rule: a verb-entry source key is not token POS evidence. If the exact surface
is nominal, adjective, participle, elative, or lexical noun, route to
nominal/POS review even when the entry-family English string is plausible.

## Dogfood finding: VN-11 nominal/POS and pronoun/function collisions

VN-11 added more rows where entry-family reuse would mis-teach the token:

- `مَغَانِمُ`, `مَغَانِمَ`, and `غَنَمُ` sit near a war-gains verb family, but
  the first two are plural nominal spoils and the last is sheep/livestock by
  exact context.
- `ٱلْغَيْثَ`, `غَيْثٍ`, `فِضَّةٍۢ`, and `فُرُوجَهُمْ` are nouns or nominal
  hosts; they must not inherit finite verb prose.
- `كُفُّوٓا۟` appeared in a noun tranche while the live string looked like a
  verb infinitive. Route by exact POS/mood/context, not by entry family.
- `هُمْ` / `هُمُ` rows near a verb-entry source key are standalone pronoun or
  function-token evidence, not nominal derivatives and not finite verbs.

Rule: strict surface plus POS decides the lane before root or source-key
familiarity. If the candidate is a pronoun/function token, route to nahw; if it
is a noun, record noun type, number, state/case, and suffix before hover trust.

## Dogfood finding: VN-12 nominal/POS leakage in verb families

VN-12 found verb-entry families attached to nominal or POS-sensitive rows:

- `ٱلصَّيْدِ`, `ٱلصَّيْدَ`, and `صَيْدُ` must be reviewed as game/hunting
  nouns or masdars by exact context, not as the finite/infinitive "to hunt".
- `مَالَ` and `مَالِ` are surface-collision rows where wealth, mā/lām, and
  verb-family readings can collide. Treat them as exact-address nahw/POS
  decisions, not surface-family propagation.
- `شِفَآءٌۭ`, `جُوعٍۢ`, `زَرْعٍ`, `ضَيْفِ`, and `أَسَفًا` are nominal or
  lexical rows near verb/root families. The live English may be readable but
  is not rich-certified until noun type, case/state, and syntactic role are
  visible.
- `تُخَالِطُوهُمْ` exposed the inverse defect: a nominal word such as
  "partners" must not be used for a finite verb host.

Rule: VN-12 candidates must pass strict surface, POS, derivative class, and
context before reuse. If the row is nominal, do not import verb-infinitive
prose; if the row is finite, do not import a nominal gloss.

## Dogfood finding: VN-13 noun rows can leak verb prose

VN-13 found noun and derivative rows whose populated hovers still look like
verb-entry prose:

- `مَطَرَ`, `مَّطَرًۭا`, and `مَطَرُ` were linked to a rain noun entry while
  the visible text said "to rain or shower as torment"; exact noun/POS and
  context must decide the token contribution.
- `طَٰٓئِرٍۢ`, `ٱلطَّيْرُ`, `عَجَلٍۢ`, and `ٱلْغَيْثَ` are
  nominal or context-sensitive rows that must not inherit
  infinitive wording such as "to be stunned", "to fly", "to hasten", or
  "to be aided with water".
- Verb-entry families also yielded nominal-looking rows such as
  `ٱلْحَمِيَّةَ`, `إِعْصَارٌۭ`, `الْمُعْصِرَاتِ`, `شُرَّعًۭا`,
  `تَفَٰوُتٍۢ`, and `قَتَرٌۭ`. These require noun type, derivative class,
  case/state, and context before learner wording.

Rule: a string can be populated and still be a POS leak. VN-13 noun/derivative
rows route to exact-address repair candidates or blockers, not to family-wide
propagation.

## Dogfood finding: VN-14 nominal rows inside verb-entry families

VN-14 added another mixed tranche where verb-entry families produce useful
candidate evidence for non-verb rows:

- `وَسَطًا`, `ٱلْوُسْطَىٰ`, `أَوْسَطِ`, and `أَوْسَطُهُمْ`
  are middle/best/moderation nominal or elative-looking rows near a
  `و س ط` verb family. They require noun/adjective type, state/case, and any
  suffix review before reuse.
- `ٱلْوَسْوَاسِ` is a definite lexical/nominal surface in a whisper verb
  family. Do not treat the article-bearing noun as the finite verb
  `وَسْوَسَ`.
- `بَدِيعُ`, `بِدْعًا`, and `ٱبْتَدَعُوهَا` show the opposite pressures in
  one family: nominal/adjectival surfaces need POS/case review while the finite
  verb row needs form/object review.
- `ثَمَرِهِۦٓ` remains a noun host plus suffix/referent row. The visible
  hover "to fruit; bear fruit" is entry prose leakage, not a rich noun hover.

Rule: if the exact surface is a noun, adjective, elative, masdar, participle,
or lexical noun, block verb-infinitive reuse even when the entry family is
morphologically related. Rich certification needs the nominal class plus
case/state, article, and suffix/referent contribution.

## Dogfood finding: VN-16 material nouns, participles, and lexical rows

VN-16 adds another mixed tranche where entry-family evidence can misroute the
learner hover:

- `مُكِبًّا` is not a finite verb; route it as participial/nominal or hāl-like
  by exact context before wording.
- `لَذَّةٍ`, `لَّذَّةٍۢ`, `ٱللُّؤْلُؤُ`, `ٱللُّؤْلُؤِ`,
  `ٱلْحَدِيدِ`, `ٱلْحَدِيدَ`, `ٱلْقِطْرِ`, and `ٱلْيَاقُوتُ`
  are lexical/material noun rows. Their article, case/state, number, and
  context must be visible before rich certification.
- `لُحُومُهَا` is a noun host plus suffix/referent row. Do not accept
  "flesh, meat" as learner-complete until `هَا` is accounted for.

Rule: material nouns and participles can be string-correct but not
rich-certified. Keep them in renderer/nominal review or exact-address repair
until noun type, definiteness, case/state, and suffix contribution are clear.

## Dogfood finding: VN-17 noun/POS rows can sit inside verb-looking families

VN-17 found more rows where root-family or entry prose would mis-teach the
token:

- `رَجًّا`, `زَلَقًا`, `شُغُلٍۢ`, `ظُفُرٍ`, and `عَبَثًۭا`
  are nominal, masdar, lexical, or adverbial-looking rows. They do not accept
  a finite-verb infinitive hover merely because their root has a verb entry.
- `سَٰبِغَٰتٍۢ`, `شَٰخِصَةٌ`, `عُتُلٍّ`, and `وَغَوَّاصٍۢ` need
  derivative/adjective/participle class plus case/state/context before reuse.
- `سَلَّمَ` exposed a POS-linkage collision: a noun-entry lane can still show
  verb-infinitive prose. Exact POS and source address decide whether this is a
  noun repair candidate, a token-only override, or a blocker.

Rule: if a VN-17 row is nominal, derivative, adjective, masdar, lexical noun,
or POS-colliding, block verb-infinitive reuse. Rich certification needs noun
type, derivative class, definiteness, case/state, suffix/referent when present,
and nahw role.

## Dogfood finding: VN-18 one/only rows and POS leakage

VN-18 adds high-frequency nominal rows where a populated string can still be
too broad for learners:

- `أَحَدُهُمْ`, `أَحَدِهِم`, `أَحَدِهِمَا`, `أَحَدَكُم`,
  and related forms require exact case/state plus suffix/referent review. The
  bare family gloss "one / anyone" is only a candidate.
- `وَٰحِدٍۢ`, `ٱلْوَٰحِدُ`, and `وَٰحِدَةًۭ` require definiteness,
  gender/number, and sentence role before a family-wide gloss is safe.
- `ثَانِىَ`, `كُلًّۭا`, `أُو۟لِى`, and `كُرْهٌۭ` show noun or adjective
  rows receiving verb-infinitive-looking prose; exact POS and i'rab decide the
  learner contribution.
- `مَّوْبِقًۭا` and `وَاجِفَةٌ` are nominal/adjectival rows near verb-entry
  families and must not inherit finite-verb wording.

Rule: VN-18 nominal rows stay below rich certification until noun type,
derivative class, definiteness, case/state, suffix/referent, and context are
visible. Root or entry-family agreement alone is not enough.

## Dogfood finding: VN-19 day, Sabbath, and edge rows require nominal review

VN-19 adds nominal rows where a populated string can still mis-teach the token:

- `ٱلسَّبْتِ` is a noun row; a hover shaped like "to observe the Sabbath" is
  verb-infinitive leakage unless the exact token is reviewed as a nominal.
- `قِطَّنَا`, `يَوْمُكُمُ`, `يَوْمِكُمْ`, `يَوْمِهِمْ`, and
  `يَوْمَهُمُ` are nominal hosts with suffix/referent or case/context
  contribution. A bare "day" or "share" family gloss is not learner-complete.
- `أَطْرَافِهَا`, `طَرْفُهُمْ`, and `وَأَطْرَافَ` need noun type, case,
  number, and suffix or wāw contribution before entry reuse is safe.
- `وَأَتْرَفْنَٰهُمْ` shows why root-near component evidence must not pull a
  finite verb into a noun lane.

Rule: VN-19 nominal rows stay below rich certification until noun type,
definiteness, case/state, number, suffix/referent, and nahw role are visible.
Root or surface-family agreement alone is not enough.

## Dogfood finding: VN-20 noun rows still reject verb-infinitive leakage

VN-20 added a small but important POS leakage set:

- `خَلْفٌ` is a nominal row. Do not teach it with an infinitive-shaped hover
  such as "to succeed someone" unless the exact token is separately reviewed
  as a noun and contextual role.
- `جُنُبٍۢ` is a nominal/adjectival side-distance row. It needs case,
  definiteness/state, and sentence role before wording can propagate.
- `ٱلْأَسْوَاقِ`, `ٱلْكَعْبَةِ`, `ٱلْمَجَٰلِسِ`, `ٱلْجُودِىِّ`,
  `ٱلصَّفَا`, and `ٱلْأَيْمَٰنَ` also show that article-bearing noun rows
  can be string-populated while still needing rich article + host metadata.

Rule: VN-20 nominal rows remain below rich certification until noun type,
definiteness/article, case/state, number, suffix or referent where present, and
nahw role are explicit. A verb-entry paraphrase on a noun token is a blocker,
not a candidate hover.
