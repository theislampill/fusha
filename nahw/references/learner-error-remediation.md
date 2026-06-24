# Learner error remediation (nahw) — syntax failure modes → diagnosis → fix

The syntax half of the ajamī remediation loop (pairs with sarf's). Each class maps to the nahw
procedure that diagnoses and fixes it; the engine uses the same map to refuse an unsafe gloss.

| # | error class | symptom | diagnosis procedure | fix / rule |
|---|---|---|---|---|
| 1 | particle-function confusion | مَا/إِنْ/لَا read in the wrong function | `particle-function-decision` | `references/particle-functions.md`; content-letter harakah + clause |
| 2 | مَن/مِن، لِمَ/لَمْ، أَمْ/أُمّ | homograph particle collapsed | `particle-decision` | read the content-letter harakah |
| 3 | أَلَا vs أَلَّا | istiftāḥ vs أن+لا confused | `particle-function-decision` | subjunctive verb after أَلَّا |
| 4 | negation scope/tense | لَمْ/لَنْ/لَا effect on the verb missed | `negation` | لَمْ+jussive→past; لَنْ→future neg |
| 5 | case (rafʿ/naṣb/jarr) | wrong case assigned | `irab-case-mood` + `irab-teaching-diagnosis` | sign + governor; diptote jarr=fatḥa |
| 6 | mood (rafʿ/naṣb/jazm) | muḍāriʿ mood wrong | `irab-case-mood` | naṣb after أن/لن; jazm after لم/لا-nāhiya |
| 7 | iḍāfa vs naʿt | construct vs adjective confused | `idafa-jar-majrur` | muḍāf has no tanwīn/ال; agreement |
| 8 | jar-majrūr attachment | preposition+pronoun mis-rooted | `preposition-pronoun` | إِلَيْنَا ≠ root ل-ي-ن; gloss the phrase |
| 9 | pronoun referent | wrong antecedent | `referent-context` | divine-Name vs human attribute guard |
| 10 | ḥāl vs tamyīz | accusative type confused | `irab-teaching-diagnosis` | ḥāl mushtaqq/state; tamyīz jāmid/respect |
| 11 | istithnāʾ | mustathnā case wrong | `irab-teaching-diagnosis` | tāmm vs mufarragh; إلا effect |
| 12 | inna/kāna/ẓanna sisters | iʿrāb flip missed | `irab-teaching-diagnosis` | who gets rafʿ vs naṣb |
| 13 | lā of genus | mabnī ism treated as muʿrab | `irab-teaching-diagnosis` | mufrad ism lā = mabnī on fatḥ |
| 14 | mother-tongue transfer | L1 word-order/case imposed | `irab-teaching-diagnosis` | name the interference; drill VSO/agreement |
| 15 | conclusion-only reasoning | right answer, wrong iʿrāb | `grammar-risk-gate` | reject; answer AND reasoning must pass |

## Teaching + engine loop
Show the minimal contrast (مَن/مِن، أَلَا/أَلَّا، جِنَّة/جَنَّة), state the rule, drill recognition+production
([`../drills/particle-disambiguation.md`](../drills/particle-disambiguation.md),
[`../drills/irab-case-mood.md`](../drills/irab-case-mood.md)), test. A learner error maps to a class
here and is re-drilled; an engine draft that trips a class is rejected and the token stays pending with
the exact blocker. See [`../procedures/irab-teaching-diagnosis.md`](../procedures/irab-teaching-diagnosis.md).
