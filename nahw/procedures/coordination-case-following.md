# Procedure — coordination case-following, wāw sense gating, apposition rivals

**Invoke when:** an edge carries `rel_label` in `{coordination, matuf, matuf_alayh, atf_bayan}`, or
`trigger_family` is `atf_candidate`, or the token is a bare وَ/فَ/أَوْ/أَمْ/بَلْ/لكن(light)-family connector.

**Invariant — the connector reading is decided FIRST; case identity is never a coordination signature.** Whether
a token is even functioning as a coordinator (as opposed to, say, an oath wāw, a maʿiyya wāw, or two adjacent
nominals that merely share a case by coincidence — sifa/badal/apposition) is decided before any case-following
claim is made. Two adjacent nominals sharing one case with NO connector are never treated as coordinated (F10).

**A bare wāw no longer resolves (D6 withdrawn).** `coordination-headless` in `tools/fusha_governor.py` used to be
the ONE resolved edge an arbitrary-mode lattice ever emitted — a function decision made from surface alone.
Headless stays true (a coordinating wāw has no governor of its own), but with no supplied sense feature the
edge `abstain(insufficient_features)`. With enough supplied features to know the wāw is genuinely ambiguous
between coordination and maʿiyya (accompaniment), both readings are preserved
(`unresolved_alternatives=[coordination, maiyya]`, `decision_status=unresolved`) — never a forced pick.

**Case-following, not a fixed rule.** A conjunct's case is not a property of the connector; it is a CONSEQUENCE
of the case of the element it is joined to (the maʿṭūf ʿalayh), whatever that case is:
- The joined-to element (the head) must be SUPPLIED (guard g-atf-3). `head_not_supplied` is an abstention, not a
  guess.
- If the head's case is known but the conjunct's OWN marking is not confirmed, the head's case is NEVER copied
  onto the conjunct — abstain `marking_unknown` (C7). "Unknown" includes a head that itself bears only a
  positional maḥall case (`head_bears_mahall`) and an exponent that is case/mood-syncretic
  (`exponent_syncretic`), not only an outright absent exponent.
- A clause-level connector (joining two CLAUSES, not two nominals sharing one case slot) has no head case to
  follow at all — `abstain(non_governing_use)`.
- An iḍāfa edge must never ASSIGN genitive to a conjunct whose real connector/governor is TOKEN-INTERNAL (fused
  proclitic, outside this cross-token lattice's declared layer, e.g. بِٱللَّهِ وَٱلْيَوْمِ...). That case is named
  as a `cross_token_layer_boundary` abstention, never silently modeled as iḍāfa (F9).
- A FOLLOWING token explicitly typed `adjective` is never emitted as a muḍāf ilayh/iḍāfa dependent merely because
  it follows a noun and happens to bear the same (even genitive) case — an adjective agrees with its mawṣūf
  rather than being independently governed. Such a pair is `rel_label=sifa`, headless, `unresolved_alternatives=
  [ṣifa, badal]`, never `idafa_dependent` (F9, ٱلْيَوْمِ ٱلْـَٔاخِرِ: token 15 is POS-adjective, not a candidate
  muḍāf ilayh of token 14).

**Disputed coordinator membership.** Whether a particular token is even a coordinating particle at all can itself
be analysis-dependent. Such a dispute is recorded as `analysis_attribution.status=analysis_dependent` with both
readings preserved and no school named — never resolved by picking a side (C10).

**Apposition rivals.** badal and ʿaṭf bayān can both license a referentially-identical, rigid second member with
no formal way to choose between them. That is `both_licensed`, a DISTINCT attribution status from
`preserve_alternatives`: `both_licensed` means the grammar itself does not decide (two rival ANALYSES of one
configuration), while `preserve_alternatives` means the CONSTRUCTION itself is ambiguous between two functions
(e.g. coordination vs maʿiyya for one wāw). Never conflate the two.

**Contention (tanāzuʿ).** Two verbs competing to govern one shared argument produce TWO attributed governor
assignments living on ONE unresolved edge, each carrying the pronoun/argument it requires. Two heads on one edge
is a validator failure (FAIL 4); attribution on one edge with two alternatives is the correct shape.

**Reason key.** `atf-tabaiyya-follows-matuf-alayh` (`qamus/skills/reason-key-registry.jsonl`) is the ONE key for
case-following. Its tuple carries two sentinels (`case_mood=$follows_head`, `governor_type=$head_governor`)
rather than one fixed case, because the construction itself does not fix a case — see
`tools/grade_grammar_reasoning._derive_coordination_following`. A coordination claim with no `head_case`/
`head_governor_type` routes `pending(reason_tuple_head_unavailable)`; a claim whose `head_governor_type` does not
license `head_case` is refused; a claim whose `source_address` is another occurrence's registry `examples`
citation is refused (an illustration is never evidence for a different occurrence).

**Boundary.** This family never resolves a disputed coordinator, never names a school without a
`party_source_ref`, and never adds a governor kind that licenses every case (that would make the licensing check
vacuous). Every emitted edge stays `candidate`/`pending`/`unresolved`.
