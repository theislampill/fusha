**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Require supplied root radicals; absent -> abstain `no_root_evidence`.
2. Test every declared row's shape against the letters exactly, with the
   radicals filling R1..R3 in order.
3. Exactly one survivor -> emit the row's class and template id.
4. More than one survivor -> abstain `ambiguous_template` and name the rival
   rows; this is the expected outcome on the فعال skeleton.
5. No survivor -> abstain `no_template`. A suffixal plural, a participle or
   any unlisted shape lands here; "unclassified by this pack" is never
   "ill-formed".
6. Never emit a concord claim, never rank rival attested plurals, and never
   propose a plural for a singular that was not supplied with one.
