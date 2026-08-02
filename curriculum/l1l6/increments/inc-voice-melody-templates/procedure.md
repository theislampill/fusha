**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Require supplied root radicals; absent -> abstain `no_root_evidence`. For
   a medial-weak stem, the supplied radicals are the two sound radicals and
   the evidence record carries the weak radical and its position.
2. Match every declared row's letter shape exactly.
3. One survivor -> emit its class (active or passive) with the form number,
   tense, stem class and the melody that decided it.
4. More than one survivor -> abstain `ambiguous_template`. Report the rival
   rows. Do NOT fall back to the more frequent voice, to the meaning, or to
   the absence of an agent.
5. No survivor -> abstain `no_template`; this covers the uncovered stem
   classes and any non-verbal surface.
6. Never report the active imperfect vowel from a passive surface. Never
   emit case or agreement facts from a voice decision.
