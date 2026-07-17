# FB1 calibration report: clitic-pronoun compositions

## Scope and result

FB1 is a calibration packet for the STRAT family
`clitic_pronoun_compositions` (234 source rows; STRAT rank 1). It is not a
corpus-wide producer run. The committed packet contains 48 selected rows:

- 41 candidate records
- 7 typed `source_gap` records
- abstention rate: `7 / 48 = 14.6%`

The producer is `tools.build_clitic_pronoun_producer` v1.0.0 and the registered
projector is `sarf.fb1_clitic_pronoun_composition.v1` at the required
`two_vote_required` gate. Every output record is a governed
`qamus.typed_claim_contract.v1` record. No record is learner-visible, publicly
materializable, or allowed to mutate a live surface.

## Evidence and guards

The candidate path consumes only structured source segment fields: ordered
segment index, exact written surface, typed role, typed class, and optional
typed labels. It proves both Unicode-span and UTF-8-byte reconstruction. It
does not parse or trust English glosses, morphline prose, or inferred roots.

The packet exercises these binding rules:

- closed-class function words cannot project a root;
- `لا`/`إلا` function ambiguity routes to `nahw.function_word_review`;
- idghām A/B requires an explicit byte-clean boundary attestation;
- idghām C fused and D ambiguous boundaries are unresolved and route to
  `sarf.idgham_boundary_review`;
- protective nūn is emitted only as `sarf.protective_nun`, never as a particle;
- an inferred or fused protective-nūn split routes to
  `sarf.protective_nun_review`.

The fixture set has 8 positive cases and 9 adversarial negatives. The
adversarial set includes a fused-boundary case, a spurious-root case, both
`لا` and `إلا` ambiguity cases, a reconstruction mismatch, protective-nūn
boundary failure, protective-nūn-as-particle misclassification, and missing
segments. The producer self-test and F-A validation pass over all of them.

## Per-row outcome table

| # | Quran location | Written surface | Calibration sub-shapes | Outcome | Typed result or blocker |
|---:|---|---|---|---|---|
| 1 | `12:59:5` | `ٱئْتُونِى` | attached object; protective-nūn context | **candidate** | `clitic_component`, `host_component`, `clitic_composition` |
| 2 | `10:90:7` | `وَجُنُودُهُۥ` | attached possessive; proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_component`, `clitic_composition` |
| 3 | `2:247:13` | `يَكُونُ` | attached subject | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 4 | `100:10:1` | `وَحُصِّلَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 5 | `100:10:4` | `ٱلصُّدُورِ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 6 | `101:5:2` | `الْجِبَالُ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 7 | `101:5:3` | `كَالْعِهْنِ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 8 | `11:44:10` | `ٱلْأَمْرُ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 9 | `11:44:11` | `وَٱسْتَوَتْ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 10 | `11:44:13` | `ٱلْجُودِىِّ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 11 | `11:44:7` | `وَغِيضَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 12 | `11:44:8` | `ٱلْمَآءُ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 13 | `11:44:9` | `وَقُضِىَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 14 | `11:78:1` | `وَجَاءَهُ` | attached possessive; proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_component`, `clitic_composition` |
| 15 | `11:8:2` | `أَخَّرْنَا` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 16 | `12:45:5` | `وَٱدَّكَرَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 17 | `12:51:13` | `عَلِمْنَا` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 18 | `12:51:19` | `ٱلْعَزِيزِ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 19 | `12:51:20` | `ٱلْـَٰٔنَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 20 | `12:51:28` | `لَمِنَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 21 | `14:17:12` | `بِمَيِّتٍۢ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 22 | `14:17:14` | `وَرَآئِهِۦ` | attached possessive; proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_component`, `clitic_composition` |
| 23 | `14:17:4` | `يُسِيغُهُۥ` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 24 | `14:17:5` | `وَيَأْتِيهِ` | attached possessive; proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_component`, `clitic_composition` |
| 25 | `14:26:1` | `وَمَثَلُ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 26 | `14:26:2` | `كَلِمَةٍ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 27 | `16:24:9` | `ٱلْأَوَّلِينَ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 28 | `16:94:5` | `بَيْنَكُمْ` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 29 | `17:17:4` | `الْقُرُونِ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 30 | `17:40:8` | `إِنَّكُمْ` | proclitic combination | **candidate** | `function_component`, `clitic_component`, `clitic_composition` |
| 31 | `17:44:3` | `ٱلسَّمَٰوَٰتُ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 32 | `17:44:4` | `ٱلسَّبْعُ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 33 | `17:5:14` | `ٱلدِّيَارِ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 34 | `17:5:5` | `بَعَثْنَا` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 35 | `17:62:12` | `لَأَحْتَنِكَنَّ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 36 | `17:62:5` | `كَرَّمْتَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 37 | `17:64:1` | `وَٱسْتَفْزِزْ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 38 | `17:64:12` | `ٱلْأَمْوَٰلِ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 39 | `17:64:14` | `وَعِدْهُمْ` | attached possessive; proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_component`, `clitic_composition` |
| 40 | `17:64:17` | `ٱلشَّيْطَٰنُ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 41 | `17:64:6` | `وَأَجْلِبْ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 42 | `17:64:9` | `وَرَجِلِكَ` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 43 | `17:6:2` | `رَدَدْنَا` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 44 | `17:6:4` | `ٱلْكَرَّةَ` | boundary-ambiguous idghām; proclitic combination | **source_gap** | `idgham_D_ambiguous_boundary`; `sarf.idgham_boundary_review` |
| 45 | `17:97:13` | `دُونِهِۦ` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 46 | `17:97:18` | `وُجُوهِهِمْ` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |
| 47 | `17:97:21` | `وَصُمًّۭا` | proclitic combination | **candidate** | `function_component`, `host_component`, `clitic_composition` |
| 48 | `17:97:26` | `زِدْنَٰهُمْ` | attached possessive | **candidate** | `host_component`, `clitic_component`, `clitic_composition` |

## Abstention rate and zero-false-projection attestation basis

The 48-row result is a calibration measurement, not a production denominator.
The 7 abstentions are all D-boundary source gaps. The sample's only protective
context (`12:59:5`) remains an ordinary source-attested object-pronoun span;
the producer makes no protective-nūn claim without an explicit typed source
boundary.

The zero-false-projection attestation is limited to the checked packet:

1. All 8 positive fixtures have exact reconstructed spans and typed component
   facts; the explicit protective-nūn fixture is `sarf.protective_nun`, and the
   two explicit idghām fixtures are A/B byte-clean candidates.
2. All 9 adversarial fixtures abstain with a non-empty typed blocker. In
   particular, the fused C boundary, spurious root, `لا`, `إلا`, and
   protective-nūn-as-particle cases do not produce candidates.
3. All 48 output lines pass the F-A validator. Candidate facts carry source
   addresses, exact spans, ownership, guards/defeaters, dependencies, and
   reconstruction proofs. The output contains no gloss or morphline fields.
4. The registered projector is candidate-only, the materialization target has
   both mutation flags false, and no certification transition was performed.

This is a zero-false-projection attestation for the fixtures and selected
sample under the stated gates. It is not a claim about the remaining 186 family
rows or any other corpus rows.

## EXACT NONCLAIMS

- No corpus-wide `clitic_pronoun_compositions` output was produced.
- No public hover payload, whitelist row, Qamus entry, release artifact, or
  live runtime was changed by this lane.
- No root was inferred, inherited, or certified. Morphline text and English
  glosses are not evidence for any FB1 fact.
- No protective nūn was inferred from a surface shape or an object-pronoun
  label. Only an explicit structured `sarf.protective_nun` source segment may
  produce that fact.
- No idghām claim was made for the seven D-boundary rows. A fused C boundary
  remains unresolved even when the visible token can be partitioned into
  source-provided segment strings.
- No `لا`/`إلا` function was selected from context, translation, or
  morphline; both are routed to owner review in the adversarial fixtures.
- “Candidate” means a governed calibration projection pending its gate. It does
  not mean certified linguistic truth or permission to materialize.
