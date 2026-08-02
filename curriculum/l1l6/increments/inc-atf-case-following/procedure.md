**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Check the declared reading first: an occurrence marked as not-coordination
   (abrogator reading, clause-level join) -> abstain `non_governing_use`.
2. Look the connector up in the lane inventory; absent -> abstain
   `out_of_regime`.
3. Read the SUPPLIED observed case of the head and of the conjunct. Either
   unknown -> abstain `marking_unknown`.
4. Both equal to the lane's declared case -> `consistent`.
5. Otherwise -> `violation_candidate`, routed to review with the expected
   exponent named. Never rewrite the text.
6. Emit no case assignment, no attachment decision, and no semantic verdict
   on the connector's choice.
7. Carry the pack's encoding limit into any card built from this unit, so a
   lane is never read as a claim about the connector.
