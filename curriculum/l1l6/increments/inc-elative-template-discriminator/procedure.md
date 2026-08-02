**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Collect the SUPPLIED features: entry evidence, comparison complement,
   definiteness behaviour, feminine counterpart template, person and tense
   evidence. Never infer any of them from the skeleton.
2. Test all five readings' discriminators.
3. One survivor -> emit it as a candidate reading with the evidence that
   selected it.
4. More than one -> `preserve_alternatives`, listing every survivor.
5. None -> abstain `insufficient_features`.
6. Emit no comparative or superlative label without the construction that
   fixes it, and never emit a licence to form an elative from the fact that
   one was recognised.
