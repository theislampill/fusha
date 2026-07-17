# FAM3 Number-Word Producer Calibration

Candidate-mode calibration for the `number_words` family. This report is rendered from the committed 57-row packet; no materialization or live mutation is authorized.

## Survey

The family contains **57 rows** with exact verdict coverage. The caller-supplied whitelist joins rows to entry IDs, but an entry ID is treated as a verse-context edge until the observed surface matches an entry field.

| survey measure | rows |
| --- | ---: |
| family rows | 57 |
| rows with a whitelist join | 57 |
| joined entries with usable forms | 52 |
| hosting-entry-only joins | 5 |
| rows with exact entry surface match | 16 |
| orthography-near entry matches held out | 10 |
| rows without exact entry surface match | 31 |
| rows carrying join ambiguity flags | 14 |

The 57 rows are classified from written surface and available local context. A label, gloss, morphline, or learner copy is never used as formation evidence.

## Precision + abstention by sub-shape

Typed-candidate precision below means **contract-valid candidates / emitted candidates**. It is not a linguistic gold-label precision estimate; no external adjudication is invented. `n/a` means the family shape had no candidate emitted.

| sub-shape | population | candidates | abstentions | abstention rate | typed-candidate precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| bare_cardinal | 9 | 4 | 5 | 55.6% | 100.0% |
| gender_polarity_cardinal | 6 | 0 | 6 | 100.0% | n/a |
| ordinals | 1 | 0 | 1 | 100.0% | n/a |
| compound_11_19 | 4 | 0 | 4 | 100.0% | n/a |
| tens | 6 | 2 | 4 | 66.7% | 100.0% |
| fractions | 0 | 0 | 0 | n/a | n/a |
| first_last_edge | 0 | 0 | 0 | n/a | n/a |
| other_number_form | 10 | 2 | 8 | 80.0% | 100.0% |
| unclassified | 21 | 0 | 21 | 100.0% | n/a |

Overall: **8 candidates**, **49 typed abstentions**, and **86.0% abstention rate**. The packet validator accepts all emitted records; candidate contract precision is 100.0%.

Fractions and أول/آخر-type edge words have zero population in this 57-row family. Their absence is reported rather than filled by a generic number rule.

## Per-row outcome table

| quran location | surface | sub-shape | outcome | route or pattern | entry edge |
| --- | --- | --- | --- | --- | --- |
| quran:2:51:4 | أَرْبَعِينَ | tens | candidate | tens.base_to_tens | eccba8b4d3f3 |
| quran:2:96:13 | أَلْفَ | bare_cardinal | abstention | homograph_ambiguity | 1196fc7289e8 |
| quran:2:96:14 | سَنَةٍۢ | unclassified | abstention | homograph_ambiguity | 1196fc7289e8 |
| quran:2:196:57 | عَشَرَةٌۭ | gender_polarity_cardinal | abstention | counted_noun_evidence_missing | 99b49971385c |
| quran:2:243:9 | أُلُوفٌ | other_number_form | candidate | cardinal.base_to_number_form | 1196fc7289e8 |
| quran:2:259:19 | مِا۟ئَةَ | other_number_form | abstention | orthography_mismatch | 57ff5ef29e13 |
| quran:4:3:13 | مَثْنَىٰ | other_number_form | candidate | cardinal.base_to_pairwise | 8e2506f45485 |
| quran:4:12:63 | مِّنْهُمَا | unclassified | abstention | surface_not_number_word | 1c4c58d664ab |
| quran:7:54:9 | سِتَّةِ | gender_polarity_cardinal | abstention | counted_noun_evidence_missing | 5575581aa220 |
| quran:7:155:4 | سَبْعِينَ | tens | abstention | entry_lookup_missing | 68fbbd2981cf |
| quran:8:66:12 | مِّا۟ئَةٌۭ | other_number_form | abstention | orthography_mismatch | 57ff5ef29e13 |
| quran:8:66:13 | صَابِرَةٌۭ | unclassified | abstention | surface_not_number_word | 57ff5ef29e13 |
| quran:8:66:14 | يَغْلِبُوا۟ | unclassified | abstention | surface_not_number_word | 57ff5ef29e13 |
| quran:8:66:15 | مِا۟ئَتَيْنِ | other_number_form | abstention | orthography_mismatch | 57ff5ef29e13 |
| quran:8:66:19 | أَلْفٌۭ | bare_cardinal | abstention | homograph_ambiguity | 1196fc7289e8 |
| quran:8:66:20 | يَغْلِبُوٓا۟ | unclassified | abstention | surface_not_number_word | 1196fc7289e8 |
| quran:8:66:21 | أَلْفَيْنِ | other_number_form | abstention | entry_lookup_missing | 1196fc7289e8 |
| quran:9:36:7 | عَشَرَ | compound_11_19 | abstention | homograph_ambiguity | 8e2506f45485 |
| quran:9:36:8 | شَهْرًۭا | unclassified | abstention | surface_not_number_word | 8e2506f45485 |
| quran:9:40:10 | ثَانِىَ | ordinals | abstention | homograph_ambiguity | 8e2506f45485 |
| quran:9:40:11 | ٱثْنَيْنِ | other_number_form | abstention | homograph_ambiguity | 8e2506f45485 |
| quran:9:80:10 | سَبْعِينَ | tens | candidate | tens.base_to_tens | 36ffe82c1c8a |
| quran:12:4:9 | عَشَرَ | compound_11_19 | abstention | homograph_ambiguity | 1c4c58d664ab |
| quran:15:44:2 | سَبْعَةُ | gender_polarity_cardinal | abstention | counted_noun_evidence_missing | 36ffe82c1c8a |
| quran:15:44:3 | أَبْوَٰبٍۢ | unclassified | abstention | surface_not_number_word | 36ffe82c1c8a |
| quran:16:24:8 | أَسَٰطِيرُ | unclassified | abstention | homograph_ambiguity | 372ada9ad6f0 |
| quran:16:51:5 | إِلَٰهَيْنِ | unclassified | abstention | surface_not_number_word | 8e2506f45485 |
| quran:17:44:1 | تُسَبِّحُ | unclassified | abstention | surface_not_number_word | 36ffe82c1c8a |
| quran:17:101:4 | تِسْعَ | bare_cardinal | candidate | cardinal.base_exact | ce12698e1d42 |
| quran:18:22:1 | سَيَقُولُونَ | unclassified | abstention | surface_not_number_word | eccba8b4d3f3 |
| quran:18:22:6 | خَمْسَةٌۭ | gender_polarity_cardinal | abstention | counted_noun_evidence_missing | 7ea2cfcc722e |
| quran:18:22:12 | سَبْعَةٌۭ | gender_polarity_cardinal | abstention | entry_lookup_missing | 764a0d39f699 |
| quran:18:26:20 | يُشْرِكُ | unclassified | abstention | surface_not_number_word | 1c4c58d664ab |
| quran:18:26:22 | حُكْمِهِۦٓ | unclassified | abstention | surface_not_number_word | 1c4c58d664ab |
| quran:18:26:23 | أَحَدًۭا | bare_cardinal | candidate | cardinal.base_exact | 1c4c58d664ab |
| quran:24:4:10 | ثَمَٰنِينَ | tens | abstention | orthography_mismatch | 764a0d39f699 |
| quran:24:4:11 | جَلْدَةًۭ | unclassified | abstention | surface_not_number_word | 764a0d39f699 |
| quran:24:9:3 | غَضَبَ | unclassified | abstention | surface_not_number_word | 7ea2cfcc722e |
| quran:24:45:19 | يَمْشِى | unclassified | abstention | surface_not_number_word | eccba8b4d3f3 |
| quran:24:45:21 | أَرْبَعٍۢ | bare_cardinal | candidate | cardinal.base_exact | eccba8b4d3f3 |
| quran:28:27:12 | ثَمَٰنِىَ | gender_polarity_cardinal | abstention | orthography_mismatch | 764a0d39f699 |
| quran:28:27:13 | حِجَجٍۢ | unclassified | abstention | homograph_ambiguity | 764a0d39f699 |
| quran:37:147:3 | مِا۟ئَةِ | other_number_form | abstention | orthography_mismatch | 57ff5ef29e13 |
| quran:37:147:4 | أَلْفٍ | bare_cardinal | abstention | homograph_ambiguity | 57ff5ef29e13 |
| quran:38:23:5 | تِسْعٌۭ | bare_cardinal | candidate | cardinal.base_exact | ce12698e1d42 |
| quran:38:23:7 | نَعْجَةًۭ | unclassified | abstention | surface_not_number_word | ce12698e1d42 |
| quran:40:11:2 | رَبَّنَآ | unclassified | abstention | surface_not_number_word | 8e2506f45485 |
| quran:40:11:4 | ٱثْنَتَيْنِ | other_number_form | abstention | orthography_mismatch | 8e2506f45485 |
| quran:40:11:6 | ٱثْنَتَيْنِ | other_number_form | abstention | orthography_mismatch | 8e2506f45485 |
| quran:46:15:12 | ثَلَٰثُونَ | tens | abstention | orthography_mismatch | 85d4f8dee30f |
| quran:46:15:13 | شَهْرًا | unclassified | abstention | surface_not_number_word | 85d4f8dee30f |
| quran:70:4:9 | خَمْسِينَ | tens | abstention | entry_lookup_missing | 7ea2cfcc722e |
| quran:70:4:10 | أَلْفَ | bare_cardinal | abstention | homograph_ambiguity | 7ea2cfcc722e |
| quran:70:4:11 | سَنَةٍۢ | unclassified | abstention | homograph_ambiguity | 7ea2cfcc722e |
| quran:74:30:2 | تِسْعَةَ | compound_11_19 | abstention | entry_lookup_missing | ce12698e1d42 |
| quran:74:30:3 | عَشَرَ | compound_11_19 | abstention | homograph_ambiguity | ce12698e1d42 |
| quran:89:2:2 | عَشْرٍۢ | bare_cardinal | abstention | homograph_ambiguity | 99b49971385c |

## Zero-false-projection attestation basis

The packet supports a zero-false-projection attestation for this candidate run on these bounded grounds:

- every candidate contains an entry-backed base attestation and exactly one formation fact dependent on it;
- every formation fact names a registry rule, carries source addresses, and has a passed reconstruction proof over the preserved written span;
- unresolved records carry one typed `number_formation_pending` blocker and no formation fact or claim;
- homograph ambiguity, wrong gender polarity, context-only joins, and orthographic near misses are guarded as abstentions;
- every projection remains `pre_apply_not_authorized`, with public and live mutation flags false.

This is a producer-contract attestation, not a claim that every Quranic number analysis is linguistically complete.

## Exact nonclaims

This packet does not claim: Quranic scripture facts beyond the supplied row and entry addresses; roots or lexical senses from labels alone; counted-noun gender where the context carrier does not provide it; ordinal, compound, fraction, or أول/آخر formation where the registered rule prerequisites are absent; construct-state or iʿrāb analysis; source approval; whitelist append; public publication; or live mutation.

## Compounding Impact

The reusable asset is the existing FAM2 pattern/carrier discipline: an entry-backed source fact, a named registry rule, exact-span and orthography guards, source-addressed reconstruction, and a typed pending route. The same carrier shape can support the finite_verbs lane without transferring number semantics. F-C numeral-governance rules can consume the explicit `compound_partner`, counted-noun context, and source addresses as inputs, but they must not auto-certify a syntactic relation from a FAM3 formation candidate.

## Status

- Candidate mode: `pre_apply_not_authorized`.
- Corpus inputs are caller-supplied at calibration time; the committed packet contains only the resulting typed records and no external filesystem path.
- Recommended next gate: independent owner review of the named patterns and unresolved queues; no automatic promotion is defined here.
