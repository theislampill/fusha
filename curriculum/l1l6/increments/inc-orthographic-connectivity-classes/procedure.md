**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Procedure (model-facing)

1. Collect SUPPLIED evidence: the letter itself, whether the preceding
neighbor is word-start, a non-attaching letter, or an attaching letter, and
whether a following letter is declared present. 2. Test every function. 3.
One survivor -> candidate classification; none -> abstain
insufficient_features. 4. A non-attaching letter never needs following-letter
evidence: its own class already rules out an outgoing connection. 5. Never
classify a letter absent from the closed six/twenty-two inventory by
resemblance to a member. 6. The classification is a joining-shape label only;
never emit or imply a token, morpheme, root, entry, or sense boundary from it.
