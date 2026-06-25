# dr05 reattempt — open-stem casebook proof

Verified at HEAD `a0f596b`.

- **Structural reroutes:** أتي/رأي rerouted (missing-entry residual 0); ظمأ frozen as a verb-on-noun reject fixture; 1,050 already-in-`usage.forms` tokens marked `already_entry_form_present_index_miss` (non-authoring).
- **Function-word bundles** (وما/وإن/وأن/وأنا/فإنما/وله/فله/بكم/فهل) routed OUT of stem authoring into the function-word / particle-pronoun token lanes.
- **True missing-entry owner-gated families** confirmed in the current ledger and emitted by `build_new_entry_proposals.py`: سوأ(40), رضو(24), ربب(16), صلو(12), زكو(12), يدي(8), سمو(7), … (review-only).
- **Unsafe/reject families** frozen as fixtures (`qamus/examples/form_variant_rejections.jsonl`, 20): فاستقيموا/نعف/جاءني/أرجه/بالبنين/كذبوا/ويقتلون/ظمأ/الملك/صالحا/يدعون/تولوا/ينظرون/يكفر — each with wrong-lane / correct-lane / reason / sarf+nahw procedure / expect=reject.
