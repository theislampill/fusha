# Drills — particle disambiguation

Recognition + production from the qamus-highlight scars. Built from
[`../evals/particle-function-eval.jsonl`](../evals/particle-function-eval.jsonl).

For rich-hover work, every answer must also name the display class. Same surface, different
function, different class: oath `و` is `qg-oath`, comitative `و` is `qg-comitative`, ordinary
`و` is `qg-particle`; causal/result `ف` is `qg-result`, not generic connector color.

## 1. مَا (negation / relative / interrogative / maṣdariyya)
- وَمَا يَعْلَمُ تَأْوِيلَهُ إِلَّا اللَّهُ → **negation** "and not". | مَا عِندَكُم → **relative** "what". | مَا تِلْكَ → **interrogative** "what?".
- Test: مَا أَصْبَرَهُمْ → **exclamatory** "how patient they are!".

## 2. مَن / مِن (content-letter harakah)
- مَن(fatḥa) = who/whoever (relative/interrogative/conditional). | مِن(kasra) = from (preposition), even وَمِنَ.
- Test: وَمِنَ ٱلنَّاسِ مَن يَقُولُ → "and among the people is **he who** says" (مِن prep + مَن relative in one clause).

## 3. إِنْ (conditional / negation / lightened إنّ)
- إِن كُنتُم → "if". | إِنِ ٱلكافرون إلا في غرور → "**not** … except". | وَإِن كُلٌّ لَّمَّا → lightened.

## 4. لَا (negation / prohibition / genus)
- لَا رَيْبَ → "**there is no**" (genus, mabnī ism). | لَا تَقْرَبُوا → "**do not**" (prohibition+jussive). | لَا يُؤْمِنُونَ → "do not believe" (simple neg).

## 5. أَلَا vs أَلَّا
- أَلَآ إِنَّهُمْ → "**behold/indeed**" (istiftāḥ). | أَلَّا تَعْبُدُوا → "**that … not**" (أن+لا, subjunctive). Test: which is in 11:2? → أَلَّا.

## 6. لَمْ / لِمَ (and لَمَّا / لِمَا)
- لَمْ يَلِدْ → "**did not**" (jussive→past). | لِمَ تَقُولُونَ → "**why**". | لَمَّا جَآءَ → "**when**". | لِمَا بَيْنَ → "**for what**".

## 7. أَمْ / أُمّ ; كَلَّا / كُلّ
- أَمْ لَهُمْ → "or (is it that)" (particle). | أُمّ = "mother" (noun). | كَلَّا → "nay!" (radʿ). | كُلّ → "every/all" (noun).

## 8. فاء / واو / لام (multi-function)
- فَتَلَقَّىٰ → "then". | وَٱلْعَصْرِ → "**by**" (oath واو). | لِيُنفِقْ → "**let** him spend" (lām amr). | لِلَّهِ → "to/for Allah" (lām jarr).

Parse-key practice:

- `وَٱلْعَصْرِ` in an oath frame → `OATH+ART+N:GEN:DEF`, classes
  `qg-oath + qg-article + qg-noun`.
- `فَتَنفَعَهُ` with causal fā' → `FA:CAUSE+V:SUBJ+OBJ`, classes
  `qg-result + qg-verb + qg-pronoun`.
- `وَمَا` → do not finalize until `ما` is classified; classes depend on the function.

## 9. Particle dogfood triage

For each row, choose the route and explain why it is not automatically safe:

| token | visible hover | route |
|---|---|---|
| `ثُمَّ` | then, later | sequence/scope review; add clause relation before rich certification |
| `ثَمَّ` | then, later | locative/adverbial review; do not inherit the `ثُمَّ` sequence lane |
| `هَلْ` | has/have/is/are...? | question-frame review; yes/no interrogative, not a bundled English list |
| `إِذَا` / `إِذًا` | therefore, then | split temporal-condition from inferential/result before certification |
| `مَاذَا` | what, whatever, that or who | classify `ما` and the clause role; no blended default hover |
| `لِكَيْلَا` | so that ... not | segment lām + `كَيْ` + `لا`; record purpose, negation, and governed mood |
| `لَيْتَنِي` | it is wished that | preserve `لَيْتَ` plus first-person suffix; exact-token review only |
| `أَنَا` / `أَنَّا` | that, because | split independent pronoun from subordinator+pronoun by shadda and clause role |
| `إِلَّا` | except | exception review; mustathnā/minhu, polarity, type, and case are required |
| `وَإِذَا` | and when | temporal-condition review; preserve leading wāw separately |
| `مِنْهَا` | from | PP/referent review, not `مَن/ما` relative review |

If the row is already covered by an eval or procedure, write the no-op reason.
Do not invent a new skill rule merely to show activity.

## 10. Qamustyping4 function-cluster readback

These are fixture-backed visual-closure checks. They do not claim live page
completion; they make the nahw route explicit before a future executor does
public readback.

| token | classify first | unsafe shortcut |
|---|---|---|
| `أَمْ` in `أَمْ لَهُمْ` | alternative/interrogative particle in this clause | leaving it plain because the phrase translation reads well |
| `لَهُمْ` | lām relation + attached `هُمْ` pronoun and clause role | one undivided "for, belongs to; certainly" hover |
| `أَيَّانَ` | vocalized interrogative time particle | accepting an unvocalized card as complete |
| `بِٱللَّهِ` | bā' relation + proper-name host + PP attachment/frame | host-only "Allah" |
| `مَعَكُمْ` | preposition/relational host + second-person plural pronoun | host-only "with" or dropped `كُمْ` |

Graduation check: explain each qamustyping4 row with the smallest token-level
contribution, then say what would make the row stay pending: missing
vocalization, missing reverse span, uncertified PP attachment, or function
uncertainty.
