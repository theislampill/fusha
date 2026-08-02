**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Collect the SUPPLIED features: which preposition, the governing
   predicate's class, the complement's semantic type, the paraphrase-test
   outcome. Never infer any of them from the token.
2. Test every declared sense row; the preposition's identity is itself a
   discriminator, so rows for other prepositions can never survive.
3. One survivor -> emit it as the candidate sense with its selecting
   evidence.
4. More than one -> `preserve_alternatives`, listing every survivor; expect
   this in the contested bringing-and-presenting environment.
5. None -> abstain `insufficient_features`, including when a required
   paraphrase test was not run.
6. Verify the complement's genitive marking independently; never derive it
   from the sense and never derive the sense from it.
