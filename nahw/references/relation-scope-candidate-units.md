# Relation licensing, scope, hidden government, rival preservation — TRAIN-B candidate units

**Status discipline:** every unit below is `candidate` only. None certifies an occurrence
(`tools/certify_typed_fact.py` is the only certifier) and none claims whole-lesson absorption. A unit's
"executable surface" line names what actually runs today; `pending_authoring` means the concept is scoped and
discriminated here but has no dedicated consumer yet — the honest state, not a promise. Two independent votes
that agree on conclusion AND reason still only reach `candidate_agreed_pending_certification`
(`tools/grade_grammar_reasoning.grade_two_vote`) — never certification.

Twelve units: `cu-bound-fa-function-discrimination`, `cu-fa-function-and-mood-licensing`,
`cu-preposition-sense-discriminators`, `cu-verb-particle-selection-licensing`,
`cu-clitic-pronoun-role-discriminator`, `cu-hal-licensing-conditions`, `cu-ishtighal-fronted-noun-case`,
`cu-ighra-tahdhir-licensing`, `cu-tanazu-governor-selection`, `cu-badal-typology-discriminator`,
`cu-badal-vs-atf-bayan`, `cu-la-negative-vs-prohibitive-discriminator`.

---

## cu-bound-fa-function-discrimination

**Concept:** فاء's own grammatical function (istiʾnāfiyya / sababiyya / rābiṭa) is decided from an
occurrence-specific CONTEXTUAL FRAME, never from fa's bare surface (fa carries no content-letter diacritic of
its own — always fatḥa — so the homograph-haraka registry does not apply here).

**Positive conditions:** a typed frame observation binds to exactly one function in
`nahw/rules/particle-context-rules.json#fa_function_frame`'s `frame_table`.
**Negative conditions:** no frame, an off-vocabulary frame, or a frame the table marks
`unique_within_axis: false` all abstain (`pending`, both/all rivals preserved) rather than defaulting to the
most frequent reading (istiʾnāfiyya).

**Worked occurrences (candidate, not certified):**
- `quran:2:37:1` فَتَلَقَّىٰٓ — narrative perfect, no mood in play. This observable cannot exclude a plain
  listing ʿāṭifa reading (out-of-axis), so it stays **pending** with istinafiyya/sababiyya/rabita all
  preserved as rivals — never a silent istinafiyya default.
- `quran:17:22:7` فَتَقْعُدَ — after a prohibition, visible subjunctive fatḥa → sababiyya (genuinely
  discriminating: a plain ʿāṭifa could not itself license that subjunctive).
- `quran:2:283:14` فَلْيُؤَدِّ — links the apodosis; the jussive is governed by لْ (lām al-amr), not fa →
  rābiṭa (genuinely discriminating: the lām al-amr apodosis shape is not what a plain ʿāṭifa produces).
- `quran:7:39:4` فَمَا — links/resumes; مَا is a DISTINCT negation particle, decided independently. Fa's own
  frame here likewise cannot exclude ʿāṭifa, so fa's own function candidate stays **pending** (the linked
  مَا's negation reading is unaffected and decided separately).
- `quran:80:4:3` فَتَنفَعَهُ — same sababiyya frame as 17:22:7, but ayah 80:4 is absent from the repository's
  address spine (a coverage accident). Correct disposition: the ordinary pending/`caller_occurrence_invalid`
  refusal, never fabricated evidence — matches the established N1/N2/N4 refusal-control pattern
  (`tools/test_nahw_governor_families.py`).

**Executable surface:** `tools.fusha_nahw_particle_rules.fa_context_frame()` (new).
**Machine fixture:** `nahw/evals/fa-function-occurrence-eval.jsonl`.
**Tests:** `tools/test_nahw_relation_scope_train_b.py::TB1FaFunctionDiscrimination`.

---

## cu-fa-function-and-mood-licensing

**Concept:** the mood question a discriminated فاء frame implies is answered by naming the ACTUAL governor —
never fa itself. `fa_context_frame()`'s `mood_licensing` field is structural: `fa_governs_mood` is `false` on
every row in the table; `governor` names `implied_an_after_fa_sababiyya` (sababiyya) or `lam_al_amr` (a
rābiṭa-linked jussive apodosis), or is `null` (istiʾnāfiyya / a rābiṭa link to a distinct particle).

**Positive conditions:** the linked/following verb's visible mood marking agrees with the named governor's
regime (subjunctive fatḥa under sababiyya's implied أَنْ; jussive apocope/sukūn under lām al-amr).
**Negative conditions:** fa is never itself cited as `governor`; a mood claim naming "fa" as governor is a
malformed row this table cannot produce (no frame row sets `fa_governs_mood: true`).

**Worked occurrences:** the two frames that actually reach `candidate` in the previous unit (`17:22:7`
sababiyya, `2:283:14` rabita) are the ones with a non-null `governor`; the two that stay pending
(`2:37:1`, `7:39:4`) report `mood_licensing: null` — a pending decision names no governor at all. `2:283:14`
is the clearest guard —
`governor: "lam_al_amr"`, explicitly `governor != "fa"`.

**Executable surface:** `tools.fusha_nahw_particle_rules.fa_context_frame()` (`mood_licensing` field, new).
**Tests:** `TB1FaFunctionDiscrimination.test_fa_occ_002_*`, `test_fa_occ_004_2_283_14_fa_is_not_the_mood_governor`.

---

## cu-preposition-sense-discriminators

**Concept:** a genuine ḥarf jarr (`KNOWN_PREPS`) vs. a ẓarf/iḍāfa-annexation noun that merely LOOKS
preposition-like (`ZARF_IDAFA_HEADS`, e.g. عِندَ، بَيْنَ، لَدَى) govern the following noun by two DIFFERENT
mechanisms that both happen to license the genitive — so the case value alone never proves which. A
preposition's SENSE (locative/causal/instrumental/comparative — بِـ alone spans all four in
`nahw/evals/particle-function-eval.jsonl` PF-041/043/044/047) additionally requires occurrence context, never
the bare preposition surface.

**Positive conditions:** the immediately preceding token's surface/membership decides governor KIND
(`_is_prep()` in `tools.fusha_governor`); a claim naming the wrong kind over a genuine ẓarf/iḍāfa head is
`right_answer_wrong_reason_marker=True` even when the claimed CASE is correct (F11, 2:80:10-11; and the new
2:97:14-15 dual-syncretic hostile positive — the dependent's syncretic ending never rescues the wrong kind).
**Negative conditions:** a genuine ḥarf jarr (عَلَىٰ, 2:7:3-4 / F13) must stay resolved and is never
"corrected" into a ẓarf reading — the two mechanisms are disjoint by membership, not by heuristic guessing.

**Executable surface:** `tools.fusha_governor.build_dependency_lattice()` (`ZARF_IDAFA_HEADS`,
`_zarf_idafa_edges`, the claim-lint zarf/preposition check — existing) + `nahw/rules/preposition-pronoun-rules.json`
(sense/referent guard — existing).
**Tests:** `TB3AttachmentGovernorSafety` (F11/F13 regression + new 2:97:14-15 hostile positive).

---

## cu-verb-particle-selection-licensing

**Concept:** many verbs select a SPECIFIC governing particle for their complement (taʿdiya bi-ḥarf al-jarr,
e.g. رَغِبَ فِي "to desire" vs. رَغِبَ عَنْ "to shun" — same verb, opposite sense by particle) — the particle is
lexically licensed by the verb entry, not freely chosen, and swapping it changes the meaning rather than being
a stylistic variant.

**Positive conditions:** the verb's entry names its licensed particle(s) and the attached PP's preposition
matches one of them.
**Negative conditions:** a PP attachment decided purely by adjacency (nearest verb) without checking the
verb's own particle-licensing table is exactly the `pp_attachment_unresolved` guard already enforced generally
in `tools.fusha_governor` (`_zarf_idafa_edges`/branch (2) leaves attachment `unresolved`, never forced).

**Executable surface:** `pending_authoring` — no dedicated verb-particle licensing table exists yet; the
closest committed surface is the general PP-attachment abstention in `tools.fusha_governor` (branch (2),
`pp_attachment_unresolved`) and `nahw/procedures/pp-attachment-review.md`.
**Status:** candidate, scoped and discriminated here; not implemented this batch.

---

## cu-clitic-pronoun-role-discriminator

**Concept:** an attached (enclitic) pronoun's grammatical ROLE — object of a verb, object of a preposition
(jar-majrūr), or muḍāf ilayh of a noun — is decided by its HOST's category, never by the pronoun's own shape
(the same ـهُ/ـهَا/ـهُمْ family serves all three roles).

**Positive/negative conditions and referent-context requirement:** already enforced by the existing referent
guard (`nahw/rules/referent-guard-rules.json`, `nahw/rules/pronoun-attachment-rules.json`) — a proper-noun or
divine-Name referent may never carry a homographic sibling gloss, and (per `nahw/references/particle-functions.md`
PF-069 مِنِّى) a preposition+pronoun compound's referent is always occurrence-bound, never surface-inherited.

**Executable surface:** `tools.fusha_nahw_particle_rules` (referent/quarantine plumbing) +
`nahw/rules/pronoun-attachment-rules.json` — existing, `fixture_gated`.
**Machine fixture:** `nahw/evals/suffix-pronoun-eval.jsonl` (71 rows) + `tools/test_suffix_pronoun.py` — existing.
**Status:** candidate; this batch adds no new code, only the discriminator statement above tying the existing
machinery to this unit name.

---

## cu-hal-licensing-conditions

**Concept:** ḥāl (circumstantial accusative) requires (a) an indefinite, derived (participle-shaped or
clause) complement, (b) a definite ṣāḥib al-ḥāl (the noun/pronoun it describes), and (c) answers "how" at the
moment of the main verb — distinguishing it from tamyīz (answers "in what respect", not tied to a definite
referent) is exactly the discriminator already stated in unit `u-n04` (`curriculum/l1l6/units/instructional-units.jsonl`,
read-only reference, not edited by this batch): "indefinite participle-like → ḥāl candidate; measure/number
ambiguity → tamyīz".

**Positive conditions:** derived/participle shape + indefinite + a definite ṣāḥib al-ḥāl identifiable in the
clause.
**Negative conditions:** an accusative role asserted from the bare naṣb ending alone, without checking these
three conditions, is exactly the `nasb_role_from_ending_alone` defect the mansubat unit already guards against.

**Executable surface:** `pending_authoring` — no dedicated ḥāl discriminator consumer exists yet.
**Status:** candidate, scoped here; not implemented this batch.

---

## cu-ishtighal-fronted-noun-case

**Concept:** ٱشْتِغَال — a fronted noun followed by a verb whose OWN pronoun object (not the fronted noun
itself) satisfies its transitivity licenses TWO case readings for the fronted noun: raf' (mubtadaʾ, the more
common/preferred reading) or naṣb (a mafʿūl bihi of an implied verb matching the stated one) — both are
grammatically licensed; neither is "the" answer without a school/register signal.

**Positive conditions:** fronted noun + a verb whose object slot is filled by a coreferential pronoun (never
the fronted noun directly) → both raf'/naṣb candidates open, preserved as rivals (never silently defaulted to
raf').
**Negative conditions:** if the verb's object IS the fronted noun directly (no resumptive pronoun), this is not
ishtighāl at all — ordinary fronting/topicalization applies instead, and asserting ishtighāl here would be a
construction-misidentification defect.

**Executable surface:** `pending_authoring` — no dedicated ishtighāl consumer exists yet; the general rival-
preservation posture it needs (`analysis_attribution: {"status": "both_licensed", ...}`, no silent selection)
is the same posture already implemented for `cu-badal-vs-atf-bayan` (`tools.fusha_governor._h_rivals`).
**Status:** candidate, scoped here; not implemented this batch.

---

## cu-ighra-tahdhir-licensing

**Concept:** إِغْرَاء (urging, e.g. "ٱلصِّدْقَ ٱلصِّدْقَ") and تَحْذِير (warning, e.g. "إِيَّاكَ وَٱلْكَذِبَ") both put a
noun in the accusative governed by an OBLIGATORILY DELETED verb (a `mahdhuf` verb, never written) — licensed
only by the closed set of fixed patterns (bare repetition; noun + wa + noun; إِيَّاكَ + wa/min + noun), never a
free "any accusative noun implies a hidden verb" inference.

**Positive conditions:** the token sequence matches one of the closed ighrāʾ/taḥdhīr surface patterns.
**Negative conditions:** an accusative noun outside these closed patterns must NOT be assigned a `mahdhuf`-verb
governor — this is exactly the `HIDDEN_ELEMENT_LICENSING_INVENTORY` discipline already enforced generally in
`tools.fusha_governor` (a positively enumerated licence is required; anything else is `reject_reconstruction`,
never a free-form "understood verb").

**Executable surface:** `pending_authoring` — ighrāʾ/taḥdhīr are not yet members of
`tools.fusha_governor.HIDDEN_ELEMENT_LICENSING_INVENTORY`; adding them is a future increment, not this batch
(this batch documents the discriminator and confirms the closed-inventory discipline they must join).
**Status:** candidate, scoped here; not implemented this batch.

---

## cu-tanazu-governor-selection

**Concept:** تَنَازُع ٱلْعَامِلَيْنِ — two verbs (or verb-like elements) both able to govern ONE shared argument.
Neither governor is selected; both attributed assignments are preserved on a single edge (school-attributed:
Basran "the second governs, the first takes a pronoun placeholder" vs. Kufan "the first governs" are both
`party_source_ref`-able alternatives, never picked by this repository).

**Positive conditions:** two verbs, one shared argument, no overt displacement (`displacement: "absent"`) —
`tools.fusha_governor._h_rivals` already emits exactly this: one edge, two attributed governor candidates
(`governed by verb_1` / `governed by verb_2`), `decision_status` never `resolved`.
**Negative conditions:** silently picking "the nearer verb governs" (a common learner/heuristic shortcut) is
the exact defect this construction family exists to refuse.

**Executable surface:** `tools.fusha_governor._h_rivals()` (existing, `construction_family="rivals"`,
`two_verbs`+`one_argument` features) — abstract/constructed mode only; no occurrence-bound address exists yet.
**Machine fixture:** `nahw/evals/coordination-case-following-eval.jsonl#C21` (already named this unit by id in
its own `restates` field: `"cu-tanazu-governor-selection (no increment fixture exists)"`).
**Tests:** `TB4RivalPreservation.test_c21_tanazu_school_attributed_alternatives_preserved` (regression).

---

## cu-badal-typology-discriminator

**Concept:** badal (substitution/apposition) has four sub-types — badal kull min kull (total, same referent),
badal baʿḍ min kull (partial, requires a pronoun back-referencing the mubdal minhu), badal ishtimāl
(inclusion, an abstract property of the mubdal minhu), badal ghalaṭ (correction, a genuine speech-error
repair) — all four agree in case with the mubdal minhu, so CASE AGREEMENT ALONE never distinguishes the
sub-type; the referential relationship between the two members does.

**Positive conditions:** total-identity referent → kull min kull; a following possessive pronoun pointing back
at the mubdal minhu → baʿḍ min kull or ishtimāl (distinguished by whether the second member is a literal part
or an abstract property); an explicit correction context → ghalaṭ.
**Negative conditions:** matching case alone, with no referential-relationship evidence, must abstain
(`insufficient_features`) rather than default to the most frequent sub-type (kull min kull) — the same
discipline `_h_rivals`/the ṣifa-vs-badal branch (2.5) already enforces generally for this label
(`not_determinable`, both readings preserved, never auto-selected).

**Executable surface:** `pending_authoring` for the four-way sub-type split specifically; the badal LABEL
itself (undifferentiated) already surfaces as a preserved rival reading in `tools.fusha_governor` branch (2.5)
(`sifa`/`badal` alternatives) and in `_h_rivals` (badal/atf_bayan).
**Status:** candidate, scoped here; sub-type discrimination not implemented this batch.

---

## cu-badal-vs-atf-bayan

**Concept:** badal (kull min kull) and ʿaṭf bayān (explanatory apposition, e.g. a title following a proper
name) share an identical surface signature — a rigid, referentially-identical second member in the same case
as the first, with no coordinating particle — so neither is selected without an explicit disambiguating
signal (a coordinating waw would rule out both; none of the committed fixtures currently supply one).

**Positive conditions:** referentially-identical pair, second member rigid (no independent modification) →
`analysis_attribution: {"status": "both_licensed", "alternatives": ["badal", "atf_bayan"]}`, no `selected` key.
**Negative conditions:** picking badal by default (the more frequent construction in most grammars) without a
disambiguating signal is exactly the defect this unit exists to refuse.

**Executable surface:** `tools.fusha_governor._h_rivals()` (existing, `construction_family="rivals"`,
`pair="referentially_identical"` feature).
**Machine fixture:** `nahw/evals/coordination-case-following-eval.jsonl#C20` (already named this unit by id:
`"cu-badal-vs-atf-bayan (no increment fixture exists)"`).
**Tests:** `TB4RivalPreservation.test_c20_badal_vs_atf_bayan_both_licensed_preserved` (regression).

---

## cu-la-negative-vs-prohibitive-discriminator

**Concept:** لَا's THREE governing readings — لا النافية للجنس (genus negation, mabnī ism on the accusative
maḥall), لا الناهية (prohibition, jussive verb), لا النافية (simple negation, non-operative, no case/mood
effect) — are decided by the FOLLOWING token's category and features, never by لا's own bare presence.

**Positive conditions:** following=indefinite noun with no declensional exponent (fatḥa, no tanwīn) → la_jins
(`quran:2:2:3` لَا رَيْبَ — NOTE: the task packet's canary cited `2:2:2`, which is ٱلْكِتَٰبُ; لا النافية للجنس is
word 3, verified against `qamus/indexes/quran-loc-surface/index.jsonl` (the repository's own internal
word-index authority); the pre-existing `nahw/evals/particle-function-eval.jsonl#PF-011` carries the same off-by-one and was left
untouched — see `tools/test_nahw_relation_scope_train_b.py::TB2LaNegativeVsProhibitive` for the corrected,
address-verified regression test); following=verb with visible jussive mood → la_nahiya
(`quran:4:43:4` لَا تَقْرَبُوا۟); following=verb with visible indicative/subjunctive mood → la_nafiya
(non-operative).
**Negative conditions:** no evidence on the following token → abstain (no edge emitted), never a majority-vote
default. A right-looking ending (fatḥa) reached through the WRONG reasoning (muʿrab manṣūb instead of mabnī
fatḥ on a mufrad ism lā) fails even though the visible ending is correct — `nahw/evals/grammar-wrong-reasoning-cases.jsonl#GP-WR-002`,
required_gate `two_vote_required`, never `auto_safe`.

**Executable surface:** `tools.fusha_governor._la_family()`, `_la_jins_address_edges()`, `_la_nahiya_edge()`,
`_la_nafiya_edge()` — existing.
**Tests:** `TB2LaNegativeVsProhibitive` (regression + address-corrected canary + GP-WR-002 grader check).
