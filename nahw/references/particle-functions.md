# Particle functions (الحروف ووظائفها) — the closed-class disambiguation map

A particle's meaning is its **function in context**, decided by the content-letter harakah AND the
clause — never by the bare surface. This is the inventory the engine and the learner share. Machine
fixture: [`../evals/particle-function-eval.jsonl`](../evals/particle-function-eval.jsonl).

| particle | functions | how to decide | example |
|---|---|---|---|
| **مَا** | negation · relative · interrogative · maṣdariyya · exclamatory · extra (zāʾida) | is something negated? a relative antecedent? a question? a "the fact that"? | وَمَا يَعْلَمُ (neg) / مَا عِندَكُم (rel) / مَا تِلْكَ (interr) |
| **مَن / مِن** | مَن: relative/interrogative/conditional · مِن: preposition | content-letter: **fatḥa** مَن (who) vs **kasra** مِن (from), even under و (وَمِنَ) | مَن يَعْمَلْ / مِنَ ٱلنَّاسِ |
| **إِنْ** | conditional · negation · lightened إِنَّ | jawāb present? paired with إلا (neg)? | إِن كُنتُم (cond) / إِنِ ٱلكافرون إلا (neg) |
| **أَنْ / أَنَّ / إِنَّ** | أَنْ maṣdariyya-nāṣiba/mukhaffafa/tafsīriyya · أَنَّ & إِنَّ emphasis (sisters) | subjunctive after أَنْ; naṣb of ism after إنّ/أنّ | أَن تَعْبُدُوا / إِنَّ ٱللَّهَ |
| **لَا** | simple negation · prohibition (nāhiya) · lā of genus | jussive after? mabnī ism after? | لَا رَيْبَ (genus) / لَا تَقْرَبُوا (prohib) |
| **لَمْ / لَنْ / لَمَّا** | لَمْ jussive→**past** neg · لَنْ future neg · لَمَّا 'when'/'not yet' | mood of the governed verb; temporal vs jussive | لَمْ يَلِدْ / لَن تَنَالُوا / فَلَمَّا جَآءَ |
| **أَلَا / أَلَّا** | أَلَا istiftāḥ 'behold' · أَلَّا = أَنْ+لَا 'that not' | subjunctive verb after أَلَّا; sentence-opener أَلَا | أَلَآ إِنَّهُمْ / أَلَّا تَعْبُدُوا |
| **فَمَا / وَمَا** | proclitic فـ/وـ + مَا (any مَا function) | resolve the فـ/وـ (rābiṭa/ʿāṭifa/istiʾnāf) then مَا | فَمَا كَانَ لَكُم (neg) |
| **أَمْ / أَوْ** | أَمْ interrogative-or (muttaṣila/munqaṭiʿa) · أَوْ disjunction/takhyīr | preceded by hamza? | أَمْ لَهُمْ / أَوْ كَصَيِّبٍ |
| **فاء** | ʿāṭifa · sababiyya (consequence) · istiʾnāf · jawāb al-sharṭ | sequence? cause+subjunctive? new sentence? apodosis? | فَتَلَقَّىٰ |
| **واو** | ʿāṭifa · istiʾnāf · qasam (oath) · ḥāl (circumstantial) | followed by an oath noun? a circumstantial clause? | وَٱلْعَصْرِ (oath) |
| **لام** | jarr · amr (command+jussive) · taʿlīl · tawkīd/ibtidāʾ | kasra+noun=jarr; sukūn+jussive verb=amr; لـ+sentence=tawkīd | لِيُنفِقْ (amr) / لِلَّهِ (jarr) |
| **حَتَّىٰ** | ghāya (until)+jarr · ʿāṭifa · ibtidāʾ | end-limit? | حَتَّىٰ مَطْلَعِ ٱلْفَجْرِ |
| **إِذْ / إِذَا / إِذًا** | إِذْ past ẓarf · إِذَا future conditional-temporal / fujāʾiyya · إِذًا inferential/result | tense and result relation of the clause; final alif/tanwīn matters | وَإِذْ قَالَ / إِذَا جَآءَ / إِذًا |
| **حَيْثُ** | place ẓarf (mabnī) | "where/from where" | مِنْ حَيْثُ |
| **كَأَنَّ / لَٰكِنَّ / لَعَلَّ** | sisters of inna: tashbīh · istidrāk · tarajjī | naṣb of ism | كَأَنَّهُمْ / وَلَٰكِنَّ / لَعَلَّكُمْ |
| **كَلَّا** | radʿ (deterrence) 'nay!' | ≠ كُلّ 'all' | كَلَّا سَيَعْلَمُونَ |
| **لِمَ** | interrogative 'why' (لـ+ما) | ≠ لَمْ 'did not' (content-letter harakah) | لِمَ تَقُولُونَ |
| **ثُمَّ / ثَمَّ** | ثُمَّ sequence/transition · ثَمَّ locative/adverbial "there" | shadda/vowelized strict surface and clause/locative role | ثُمَّ أَمَاتَهُ / ثَمَّ |
| **هَلْ** | yes/no interrogative | following question frame and clause scope | هَلْ أَتَىٰكَ |
| **كَيْ / لِكَيْلَا** | purpose/subjunctive governor · composite purpose+negation | governed subjunctive, purpose relation, negation scope | كَيْ / لِكَيْلَا |
| **مَاذَا** | interrogative/relative composite (`ما` + `ذا`) | classify `ما` function and clause role; no blended default | مَاذَا يُرِيدُ |
| **أَنَا / أَنَّا** | أَنَا independent pronoun · أَنَّا subordinator plus pronoun/clause | shadda and clause role | أَنَا / أَنَّا |

**The rule:** read the content-letter harakah first (مَن/مِن، لِمَ/لَمْ، أَمْ/أُمّ), then the clause role.
A surface key alone can never separate these — only iʿrāb + context can.
