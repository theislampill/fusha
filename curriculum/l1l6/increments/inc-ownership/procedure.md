**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Peel clitics outside-in from the closed inventory; verify a stem of >=2
   letters survives (else abstain `false_stem_risk`).
2. Require `root_evidence` (radicals + basis from the sarf evidence ladder).
   Absent -> abstain `no_root_evidence`. The consumer NEVER derives a root.
3. Walk the stem left-to-right against the expected radical sequence:
   match -> `root`; non-match template letter (م، ت، ا، ن، س، همزة وصل) ->
   `pattern_augment`; declared imperfect prefix -> `inflection`.
4. Any unowned/doubly-owned letter -> whole-token `pending_letter_ownership`.
5. Emit the ownership record; colour + hover are COMPILED from it (never
   authored separately).
