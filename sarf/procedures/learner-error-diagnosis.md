# Procedure: learner-error diagnosis (sarf)

**Input:** a learner's (or the engine's draft) morphological output for a surface.
**Goal:** name the exact error class (the Madinah-study map), then route to the fixing procedure +
drill. Same loop the engine uses to refuse an unsafe gloss.

## Steps

1. Compare the learner/draft analysis to the certified analysis (root, POS, derivative type, segmentation).
2. Localize the mismatch and map it to an error class in
   [`references/learner-error-remediation.md`](../references/learner-error-remediation.md):
   - wrong derivative type / فاعل↔مفعول / مبالغة↔فاعل / صفة↔verb / تفضيل↔colour-or-verb / زمان↔مكان /
     آلة↔مبالغة → `nominal-derivative-decision`.
   - hidden/altered radical (weak/hamza/doubled/quadriliteral) → `weak-root` / `hamza-root` /
     `doubled-root`.
   - long↔short vowel, tanwīn-nūn↔radical-nūn → `root-decision` (normalization ladder).
   - false clitic split / faulty segmentation → `suffix-pronoun-state` + `false-clitic-split-eval`.
   - broken plural / gender / number → `noun-plural-gender`.
   - L1 (mother-tongue) transfer → name the interference explicitly, drill the Arabic pattern.
3. State the rule that was violated (cite the rule file), give the minimal contrast pair
   (e.g. مُعَلِّم/مُعَلَّم, عَالِم/عَلِيم), and assign the matching drill.
4. Re-test recognition **and** production before marking the error remediated.

## Output object
```json
{"surface":"...","error_class":"sifa_mushabbaha_vs_verb","violated_rule":"nominal-derivatives",
 "contrast_pair":["كَظِيم (adj)","كَظَمَ (verb)"],"fix_procedure":"nominal-derivative-decision",
 "drill":"drills/nominal-derivatives.md#sifa","remediated":false}
```

## For the engine
A draft gloss that trips any class here is **rejected**, the token stays `pending` with the exact
blocker, and the rejection is stored as a regression fixture (the good rejections train the gate).
