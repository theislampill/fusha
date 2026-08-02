**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Collect the SUPPLIED features about the following element: its category,
   its mood exponent if it is a verb, its case exponent if it is a noun.
2. Test every declared function's discriminators.
3. One survivor -> emit it as the candidate function with the evidence that
   selected it.
4. More than one -> `preserve_alternatives`. Expect this whenever the mood
   exponent is a vowel that the text does not carry; report it as the result.
5. None -> abstain `insufficient_features`.
6. Never use a person feature to exclude the prohibitive. Never emit a mood
   assignment, a case assignment or a government claim from this unit.
