**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack read by the NON-AUTHORITATIVE fixture harness `tools/curriculum_unit_consumer.py`; every non-abstention outcome is `candidate_pending`.**

# Procedure (model-facing)

1. Require supplied root radicals (evidence ladder). 2. Require the supplied
letters to be exactly the bare letters of the written surface, and reject a
weak declaration the supplied radicals do not bear
(`weak_declaration_contradicts_root`). 3. Test each template's exact shape
against the letters with radicals in R-slots. 4. For **every** weak radical
of the matched template — whether it surfaces altered or stands literally —
require the exact bound declaration (`weak_position` + `weak_radical`,
otherwise `weak_declaration_unbound`) and a realization the pack licenses
**for that template, slot and radical** in `weak_realizations.by_template`:
an altered letter must appear in that entry's `substituted` list, and a weak
radical may stand unchanged only where `literal_licensed` is true. Nothing is
licensed by default; an unlicensed realization abstains
`weak_realization_unlicensed`. 5. If the
survivor is mu_participle, require the penult vowel AND verify the claimed
mark on the written surface: unpointed -> `penult_mark_not_in_surface`, a
different written mark -> `penult_mark_mismatch`; over a weak-radical root the
bound weak declaration is required before voice is decided. 6. Zero or
multiple survivors -> abstain with the named reason. 7. Emit class + template
+ evidence as a CANDIDATE proposal; flag any verbal-gloss pairing for review
(never author a gloss).
