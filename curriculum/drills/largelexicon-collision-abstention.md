# Largelexicon Collision Abstention Drill

Purpose: teach why "more lexicon rows" improves recall but does not certify the
first parser candidate.

## Cases

1. `الله`
   - Mechanical split to reject as a public hover: `ال + له`.
   - Safer reading: whole proper-name candidate, no invented root.
   - Lesson: a legal-looking split is not automatically the token's grammar.

2. `بالله`
   - Keep visible bā': `بـ + الله`.
   - Reject: `بـ + ال + له`.
   - Lesson: real clitics stay visible, but splitter artifacts do not get to
     overrule the host.

3. `من`
   - Candidate inventory may include particle/function readings and the verb
     `مَنَّ`.
   - Without source/context evidence, route to function/context review.
   - Lesson: unvoweled short forms are not resolved by frequency or row order.

4. `إلا`
   - Candidate inventory may include exception particle and noun homograph.
   - Without context, do not project the noun reading.

5. `إله`
   - Reject object-pronoun segmentation in a hover preview.
   - Keep the row pending when the large table only provides weak/bare-match
     evidence.

## Agent check

Run:

```powershell
python tools\validate_largelexicon_parser.py --self-test
python tools\validate_largelexicon_cli_contract.py --self-test
```

Passing means the system can still discover candidates while refusing to
publish a misleading first guess.
