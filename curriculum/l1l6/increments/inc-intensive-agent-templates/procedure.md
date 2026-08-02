**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Require supplied root radicals; absent -> abstain `no_root_evidence`.
2. Match every declared row exactly against the letters, radicals filling
   R1..R3 in order.
3. One survivor -> emit its class, template id and declared degree.
4. Two survivors -> abstain `ambiguous_template`; expect this on the
   augmented row (person vs tool) and on the rare row (intensive vs nominal).
5. No survivor -> abstain `no_template`. The plain agent noun lands here by
   design: it is the base of the scale, not a member.
6. For a shared row, emit the template and mark the class unresolved, naming
   the transitivity test as the missing evidence. Never run the test.
7. Never emit a gender claim from a closing taa. Flag an annexed complement
   as an underlying object without re-analysing the clause.
