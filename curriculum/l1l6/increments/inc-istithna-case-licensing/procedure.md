**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Read the declared construction key: polarity, set-overtness and the
category of the exclusion word are inputs, never inferred from wording.
2. Match it against the closed licensing table. 3. Licensed -> emit the
outcome label with its refinement and its obligatoriness flag. 4. A row that
records two licensed readings is emitted analysis-dependent, with both
readings preserved and neither preferred. 5. Unlisted exclusion word, or a
missing polarity or set-overtness input -> reject_reconstruction. 6. Nothing
here certifies; the output is candidate analysis.
