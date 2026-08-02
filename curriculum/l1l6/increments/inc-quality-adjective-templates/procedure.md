**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Require supplied root radicals; absent -> abstain `no_root_evidence`.
2. Match every declared row's shape exactly against the letters, radicals
   filling R1..R3 in order.
3. One survivor -> emit its class, template id, and the row's inflection and
   feminine-template facts as attached evidence.
4. Two survivors -> abstain `ambiguous_template`. Expect this on the
   disposition/short skeleton (vowel-only split) and on the augmented
   skeleton (colour vs elative, routed out).
5. No survivor -> abstain `no_template`.
6. If the surviving row is declared shared, emit the template but mark the
   class as unresolved and name the test that would decide it. Never author
   the semantic decision.
7. Emit the restricted-inflection flag as a prompt, never as a case fact.
