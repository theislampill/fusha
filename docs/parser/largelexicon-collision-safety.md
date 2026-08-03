# Largelexicon Collision Safety

Largelexicon increases recall by exposing many more Qamus-authored forms to the
parser. That also increases the collision surface for short Arabic tokens,
especially particles, proper names, and tokens that can be mechanically split
into clitic-looking pieces.

The rule is simple: coverage is not disambiguation. A larger table may add a
candidate, but it does not make that candidate safe for a public hover.

> **Train E repair note.** An assembled Opus review of the R1-R8 packet found
> that `_gate` implemented R1's cap as an early `return`, which preempted R4,
> R5, `_candidate_collision`, and the legacy `unsafe_bare_match` guard for any
> candidate that carried both `requires_nahw_function` and a real collision
> (B1), and that the trichotomy corpus invariant's own antecedent check made
> it vacuous in the direction that mattered (B2). Both are repaired below
> (`_gate`'s monotone lattice; `_check_trichotomy_invariant_rows`'s
> fail-closed corpus check). `_skeleton_collision`'s scope source (I4) and the
> Mode C validator's collision-unawareness (I2) are repaired in the same
> pass. I1/M5 (missing/dishonest `decided_by`) are repaired as part of the
> lattice change. I3, I5, I7, and I8 remain open spec decisions, recorded but
> **not** solved here (see "Deferred spec decisions" below); I6 and M1-M4/M6
> are unresolved because their fix sites are outside this repair's edit scope
> (`fusha_pattern_engine.py`, `check_regressions.py`, fixture data).

> **Train E follow-up repair.** A second targeted Opus review of the R1-R8
> packet found three IMPORTANT interaction gaps that survived the first
> repair, all confirmed against the real corpus, not just synthetic fixtures.
> **(1)** `_skeleton_collision` read `collision.competitors` off the SELECTED
> (highest-scoring) morphology candidate only. A `function_inventory`
> candidate is built directly and never carries a `collision` field of its
> own, so when its fixed score (6.5) outscored a sibling lexicon candidate for
> the same bare surface, a real corpus `pos_trichotomy_conflict` sitting on
> the outscored sibling was invisible to the gate -- bare `من`, `لا`, and
> `إلا` (real corpus rows: verb `مَنَّ` vs particle `مِنْ`/`مَنْ`; particle
> `لَا` vs its noun/verb competitors; particle `إِلَّا` vs noun `إِلًّا`) all
> reached `pending_context` with a full function-word gloss instead of
> abstaining. `_skeleton_collision` now falls back to any sibling in
> `morph_cands` sharing the same `segment_candidate_ref` (never a different
> segmentation hypothesis, preserving R6) that carries its own >= 2
> competitors, and `tools/validate_largelexicon_parser.py` gained a dedicated
> corpus-vs-production agreement check
> (`_validate_function_inventory_corpus_agreement`) so this class of gap
> fails closed automatically instead of needing a fixture per surface.
> **(2)** `_scope_collision_segments` degraded pronoun-role clitics
> (`object_pronoun`/`subject_pronoun`) to `clitic_undetermined` but left
> `verb_prefix`, `future_particle`, `derivative_prefix`, and `plural_suffix`
> untouched, even though their role/label/gloss (`"imperfect marker"`,
> `"will"`, `"Form X seeker/doer shape"`, `"masculine plural/oblique
> ending"`) each presuppose the very noun/verb/adjective class the collision
> leaves open. These now degrade to `affix_undetermined` the same way,
> keeping the surface span visible but withholding the class-committing
> label/gloss. **(3)** The Mode C validator's ordered-subset check
> (`_retained_segments_ordered_subset`) only proved that surviving segments
> land in order somewhere in the surface; it never asserted that the
> withheld stem or a class-presupposing affix was actually absent from
> `qg_segments`, so a regression reintroducing one of the roles from (2)
> would still pass as long as the leftover pieces happened to be in order.
> `validate_record` now checks `qg` roles against
> `CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES` directly for every
> `scope == "stem_identity"` collision row. All three are repaired below;
> none required touching `fusha_pattern_engine.py` or the registry.

## Required behavior

- Candidate enumeration remains broad.
- The selected preview is suppressed or context-gated when a high-risk candidate
  is only a `bare_match` / weak match or competes with a function-token route.
- `morphology_candidates[0]` is never a deploy signal by itself.
- `safe_for_qamus_executor_autopromote` remains `false` for local arbitrary-text
  CLI output.
- Function-token alternatives route to `pending_context` instead of being
  collapsed into a content-word hover.
- Real clitics remain visible when the token has a single top-scored
  segmentation. A stable morphology identity across rival segmentations is
  NOT sufficient on its own (Train E finding 1, below): `بالله` (bā' + Allah)
  ties a rival whole-token segmentation at top score and correctly abstains
  with `qg_segments` fully withheld, since its two rivals share no identical
  span to agree on. `بالنيات` (bā' + article + host) also ties, but its two
  rivals (splitting `ال` off as its own morpheme vs. leaving it fused with the
  stem) DO independently agree on the exact same leading `بِ` preposition
  span -- a genuine `competing_segmentation` tie only ever withholds the
  disputed stem and any host-class-presupposing material; an exact-span,
  exact-ownership class-neutral prefix/article every tied rival agrees on is
  not actually contested and now survives (Train E finding 2, below), same as
  the ordinary `stem_identity` scope already does for a single selected
  candidate's own affixes.

## Skeleton-collision and source-provenance abstention (Train E)

A shared consonant skeleton and a source lexicon row are recall evidence, not
identity. `tools/fusha_pattern_engine.py` preserves each largelexicon row's
`risk_flags`/`no_root_reason`/`entry_id`, and returns the full set of
competing entries that share the query's `norm_strict` key (never a
lemma/root/pos claim by itself).

`tools/fusha_standalone_parse.py::_gate` evaluates every filter below and
casts one VOTE per filter that fires: `(rank, gate, collision_or_None,
tie_break_priority)`. Ranks form an explicit MONOTONE LATTICE, weakest to
strongest: `likely_from_internal_pattern` (0) < `ambiguous` (1) <
`pending_context` (2) < `lexical_collision_requires_context` (3) < `blocked`
(4, handled before the lattice — a dangling segment ref or missing morphology
candidate is terminal). The final `confidence_gate` is the highest-ranked
vote; ties within one rank are broken by `tie_break_priority` (lower wins),
preserving the historical evaluation order. This is a genuine CAP-not-MASK
semantics: a weaker vote (source-risk `pending_context`) can demote the
result when nothing stronger fired, but it can never suppress a stronger vote
that also fired for the same candidate. `decided_by` evidence is recorded on
the source-risk cap and on identity withholding (below) whether or not that
particular vote ends up winning the lattice; the winning collision object
also keeps its own `decided_by` (the collision `kind`).

> Earlier revision of this document (superseded): `_gate` implemented R1 as
> an early `return "pending_context", None` before R4/R5/`_candidate_collision`
> ever ran. That IS the short-circuit the previous paragraph here warned
> against (Train E review M5) — for any candidate carrying BOTH
> `requires_nahw_function` and a real skeleton/segmentation collision, the
> pipeline used to emit the weaker gate and skip `_strip_collision_identity`
> entirely (Train E review B1). The lattice above replaces that short-circuit.

1. **source_provenance** (`R1`) — if the selected candidate's matched entry
   declares `risk_flags` including `requires_nahw_function`, this filter
   casts a `pending_context`-ranked vote and records
   `features.gate_cap_decided_by = {"filter": "source_requires_nahw_function",
   "evidence_keys": ["features.source_risk_flags"]}` on the candidate. The
   token still routes to `nahw_function_review` when this vote wins.
   Entries lacking the flag are unaffected. This vote is a CAP: it wins only
   when no stronger filter (R4/R5/`_candidate_collision`) also fired for the
   same candidate; when one does, that stronger vote wins the lattice and
   keeps its own collision descriptor, while this filter's `decided_by`
   evidence remains on the candidate as a record of what else was true.
2. **entry_identity** (`R2`) — if the matched entry's `lemma` is a
   slash-joined bundle of more than one headword (a `compound_headword` row),
   `features.entry_identity_status = unresolved_bundle_member`, the
   projected identity becomes the MATCHED FORM (not the bundle string), and
   no gloss is projected. `confidence_gate` is left untouched: demoting it
   breaks `rm12-harakah-agreeing-control` (verified in review), so this
   stage withholds identity and gloss, never the gate.

   Alongside it, **root_identity_unresolved** (`R3`) applies when the
   matched entry's `root` is not a single well-formed radical sequence
   (contains a `/` separator): the candidate's `root` becomes `null`,
   `features.root_identity_status = unresolved_root_set`, and no gloss is
   projected. Neither rule repairs `fusha/lexicon/largelexicon/**`; both
   only withhold a claim the source itself did not make cleanly.
3. **skeleton_collision** (`R4`/`R5`) — computed from the SELECTED
   candidate's own `collision.competitors` (the norm_strict-key competitor
   set fusha_pattern_engine.py attaches to that one candidate; see R6
   below). `pos_trichotomy_conflict` (`R4`) fires when >= 2 distinct entries
   span >= 2 of the trichotomy classes {ism, fil, harf}
   (noun|proper_noun -> ism, verb -> fil, particle -> harf).
   `root_conflict` (`R5`) fires when the competitors agree on trichotomy
   class but carry >= 2 distinct NON-NULL roots (a null root is an absent
   claim, never a competing one). Either sets
   `confidence_gate = lexical_collision_requires_context` and strips
   `lemma`/`root`/`pos`/`pattern`/`gloss_hint` plus any `voice`/`verb_form`/
   `number` features from the withheld candidate, recording
   `features.identity_withheld_decided_by = {"filter": kind, "evidence_keys":
   ["collision.competitors"]}` (`kind` is `pos_trichotomy_conflict` or
   `root_conflict`). A shared root between competitors never clears a
   `pos_trichotomy_conflict` — that is the forbidden root-to-identity
   inference (`LLX-COLL-022`).

   Scope (`R7`, below) is derived from the segment candidate `_selected()`
   actually returned for this token, not from
   `morph["segment_candidate_ref"]`: `_selected()` can promote a richer
   multi-segment candidate over a collapsed whole-token largelexicon match
   for the same surface, and reading the collapsed ref directly (as an
   earlier revision did) can wrongly compute `scope="whole_token"` and empty
   `qg_segments` that should have preserved a real prefix/clitic (Train E
   review I4). `_skeleton_collision` accepts the resolved `selected_seg` as
   its scope source, falling back to the ref-based lookup only for callers
   that have not resolved one.

   **Sibling fallback (Train E follow-up gap 1).** The SELECTED candidate is
   whichever morphology candidate scored highest, and a `function_inventory`
   candidate (fixed score 6.5, built directly rather than via
   `_candidate_from_row`) routinely outscores a lexicon-matched sibling for
   the same bare surface. That sibling's `collision.competitors` is where a
   real corpus `pos_trichotomy_conflict`/`root_conflict` lives, so when the
   selected candidate itself carries fewer than 2 competitors,
   `_skeleton_collision` now also checks `morph_cands` for a sibling sharing
   the SAME `segment_candidate_ref` (the same stem attempt, per R6 — never a
   different segmentation hypothesis) that does carry >= 2 competitors, and
   uses that sibling's competitor set (and `competing_entry_ids`) instead.
   Which candidate wins scoring must never decide whether a corpus-defined
   collision is reported. This is scoped to same-`segment_candidate_ref`
   siblings only: a surface with a genuine competing SEGMENTATION (e.g. bare
   `لما` also splitting as `ل + ما`, tied at top score with the whole-token
   `لما` reading) is a distinct, deliberately unresolved ambiguity question
   (see "Deferred spec decisions"), not this gap, and R6 forbids importing a
   different, unselected split's data into the selected reading.
4. **existing gate ladder** — unchanged: function-token context routing,
   `_candidate_collision` (bare high-risk-match and cross-segmentation
   collisions), then the internal-pattern/ambiguous fallback. Each of these
   is a lattice vote too (see above), not a short-circuit.

Two rules constrain how the above is computed, not what class fires:

- **R6 — rejected segmentation is not a competitor.** Competitors are
  computed ONLY over the stem of the SELECTED segment candidate, plus the
  whole-token candidate when it matched — never unioned over every
  hypothesized split. Unioning over all segment candidates imports a
  lām-particle row via the rejected article+lahu split and flips both
  `الله` fixtures to a `pos_trichotomy_conflict` (R4/R5) collision,
  amplifying the exact artifact `LLX-COLL-001`/`LLX-COLL-002` exist to
  suppress (`LLX-COLL-010`). This is a distinct concern from `بالله` now
  correctly reaching `competing_segmentation` (R9, Train E finding 1, below)
  — R6 stops R4/R5 from firing for the WRONG reason; it says nothing about
  whether R9 should fire.
- **R7 — scoped collision.** When `R4`/`R5` fires, `collision.scope` is
  `stem_identity` if the selected segment candidate has more than one
  segment, else `whole_token`. Under `stem_identity` the affix/clitic `qg`
  segments and their letter spans are PRESERVED (`LLX-COLL-009`); only the
  stem segment is withheld, and a clitic pronoun role (`object_pronoun`/
  `subject_pronoun`) degrades to `clitic_undetermined` rather than keeping a
  role that presupposes the disputed host class. Under `whole_token`,
  `qg_segments` is emptied as before.

  **Class-presupposing affixes (Train E follow-up gap 2).** The same
  reasoning that degrades a pronoun role applies to any OTHER affix whose
  role/label/gloss presupposes the disputed class: `verb_prefix` ("imperfect
  marker"), `future_particle` ("will"), `derivative_prefix` ("Form X
  seeker/doer shape" / "derived-form prefix"), and `plural_suffix`
  ("masculine plural/oblique ending") each assert a specific verb- or
  noun/adjective-shaped analysis of the disputed stem. These now degrade to
  `affix_undetermined` (surface preserved, role/label/gloss withheld)
  exactly like the pronoun-role discriminator, rather than surviving
  unchanged while only the stem and pronoun roles were withheld. Genuinely
  class-neutral material — an independently licensed preposition,
  conjunction, or article, or the pronoun/affix undetermined roles
  themselves — is preserved unchanged; only material whose role or gloss
  presupposes the disputed trichotomy class degrades.

> **Train E follow-up repair, second pass.** A further targeted review of the
> gap 2/gap 3 repair found two more IMPORTANT defects, both confirmed against
> real `qamus/examples/largelexicon/hover-candidates.sample.jsonl` rows (six
> of the sample's eight `stem_identity` collisions were affected), not just
> synthetic fixtures. **Defect A (residual class assertion).**
> `_scope_collision_segments` renamed `role` (to `affix_undetermined` or
> `clitic_undetermined`) but left `class` untouched, so
> `qg-verb-prefix`/`qg-derivative-prefix`/`qg-plural-suffix` (from the gap 2
> affix roles) and `qg-object-pronoun`/`qg-subject-pronoun` (from the
> pronoun-clitic roles) kept asserting the disputed verb/noun host category
> by class alone. Both degraded branches now also overwrite `class` with an
> honest, class-neutral replacement — `qg-affix-undetermined` or
> `qg-clitic-undetermined` (`CLASS_PRESUPPOSING_QG_CLASSES`,
> `NEUTRAL_AFFIX_QG_CLASS`, `NEUTRAL_CLITIC_QG_CLASS` in
> `tools/fusha_standalone_parse.py`). A `future_particle` affected by a
> `stem_identity` collision is also degraded to `affix_undetermined` with
> `qg-affix-undetermined`; `qg-particle` remains allowed only where the role is
> independently licensed outside that degraded branch. `validate_record` now checks
> retained segment `class` against `CLASS_PRESUPPOSING_QG_CLASSES`
> independently of the `role` check, so a future rename that forgets to also
> neutralize `class` still fails closed. The two new classes were added to
> `tools/validate_fusha_standalone_parse.py::ALLOWED_QG_CLASSES` and to
> `tools/fusha_mode_a.py::ALLOWED_QG_CLASSES` (the producer contract
> `tools/project_largelexicon_qamus_hover_candidates.py` and
> `tools/validate_largelexicon_qg_projection.py` both import), and the sample
> was regenerated through `project_largelexicon_qamus_hover_candidates.py`
> (six rows changed: `qg-object-pronoun` → `qg-clitic-undetermined`, same
> surfaces/spans/ordering). **Defect B (vocabulary drift).**
> `tools/validate_fusha_standalone_parse.py` hand-typed its own copy of the
> parser's withheld/degraded role union
> (`CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES`), which could silently drift from
> production. The parser now owns this union plus a `CLASS_NEUTRAL_QG_ROLES`
> set naming every independently-licensed role
> (`prefix_conjunction`/`prefix_resumption_fa`/`prefix_preposition`/
> `definite_article`/`particle_inna`/`ma_particle` — the complete triage of
> every role the clitic splitter and pattern engine currently place into
> `qg_segments`), and the validator imports
> `CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES` directly (same object, not a copy).
> `_scope_collision_segments`'s catch-all is fail-closed: a role that is in
> none of the withheld/degraded/class-neutral sets is now WITHHELD rather
> than assumed safe and passed through — self-tested with a synthetic
> untriaged role. The validator's self-test also runs every fixture surface
> through the real parser (both `db=smoke` and `db=largelexicon`) and asserts
> every observed role and `class` is accounted for in the parser's own sets
> and in both `ALLOWED_QG_CLASSES` copies (validator and producer), so a
> future production role/class that nobody triaged fails the self-test
> instead of silently validating. Neither defect required touching
> `fusha_pattern_engine.py` or `fusha_clitic_splitter.py`.

## Competing segmentation is not a same-stem collision (I9, resolved)

A prior revision's `_candidate_collision` exempted every top-score tie where
all tied candidates were `function_inventory` particles, regardless of which
`segment_candidate_ref` each one matched. That let bare `لما` (a `ل + ما`
split, ref 0, tied at top score against the whole-token `لَمَّا` particle
reading, ref 1) and `وما` (`و + ما` vs whole-token `وما`) silently commit to
the prefix+`ما` split -- a full function-word gloss, a `P+PART`/`CONJ+PART`
`selected_preview`, and no acknowledgement that a tied, structurally different
whole-token rival existed. This is exactly the gap the "Deferred spec
decisions" section below used to record as I9: the sibling-fallback repair
(gap 1, above) is deliberately scoped to siblings sharing one
`segment_candidate_ref` (one stem attempt, per R6); a genuine tie ACROSS
different `segment_candidate_ref` values is a different question -- rival
segmentations of the surface itself, not rival entries for one already-chosen
segmentation.

`_candidate_collision`'s exemption is now scoped to same-ref ties only, so it
can never mask a real cross-segmentation tie. A new registered class,
`competing_segmentation` (`R9`), fires when the tied top-scored
`morphology_candidates` span >= 2 distinct `segment_candidate_ref` values.
When `competing_segmentation` fires: every rival `segment_candidate_ref` is
preserved in `collision.candidate_refs` (`lemma_values`/`pos_values` name
whatever identity each rival ref carries, for provenance), the gate is
`lexical_collision_requires_context`, `selected_preview` is cleared,
`qg_segments` is emptied (there is no `scope` key -- see R7's "no scope key at
all" case, so no partial affix retention is attempted across two structurally
different segmentations), and the selected candidate's `lemma`/`root`/`pos`/
`pattern`/`gloss_hint` are stripped exactly like R4/R5's identity withholding,
just with `evidence_keys` naming `morphology_candidates`/`segment_candidate_ref`
instead of `collision.competitors` (there is no single stem's competitor list
to point at -- the tie is across segmentations). `إنما` (one top-scored
segmentation, the pinned particle cluster) is unaffected and remains the
positive control it always was.

> **Train E finding 1 (repair).** The revision above originally also required
> the tied candidates to disagree on identity (pos/lemma/root) before firing,
> so a same-identity, different-ref tie stayed silently uncollided -- the
> reasoning being that "real clitics remain visible when the morphology
> identity is stable" (see "Required behavior" above) excused it. That is
> wrong: two different `segment_candidate_ref` values are two different
> claims about which letters belong to which morpheme, and agreeing on the
> resulting lemma/pos/root does not settle which claim is correct. `بالله`
> (a bā'+Allah split, ref 0, tied at top score against a whole-token
> largelexicon match, ref 1) is the paradigm case: both resolve to the same
> `اللَّه` entry, but the letters are still contested between "bā' prefix +
> Allah" and "one indivisible surface token" -- same identity never
> authorizes choosing one segmentation over the other. `_candidate_collision`
> now fires `competing_segmentation` on ref multiplicity ALONE; the
> identity-disagreement check is removed, and a same-ref tie (rival lexicon
> rows for the SAME segmentation) is left to R4/R5 via `collision.competitors`
> instead, as it always should have been. `LLX-COLL-002` (`بالله`) and
> `LLX-COLL-007` (`بالنيات`, which ties splitting `ال` off as its own morpheme
> against leaving it fused with the stem) both moved from a same-identity
> "stays uncollided" expectation to a `competing_segmentation` requirement
> with `>= 2` preserved `candidate_refs` and a cleared `selected_preview`. The
> same shape appears in the smoke lexicon fixtures `يسألك` and `بالكتاب`
> (each also listed verbatim as its own entry's whole-token form alongside its
> separable stem), which now correctly abstain instead of exposing their
> prefix/object-pronoun or preposition/article/stem roles; verb_prefix/
> verb_stem/object_pronoun role coverage remains via `فسيكفيكهم`.
> `qamus/examples/largelexicon/hover-candidates.sample.jsonl` was regenerated
> through `project_largelexicon_qamus_hover_candidates.py` against the real
> corpus: 18 rows that used to silently commit to one segmentation (e.g.
> `قَبْلِكُمْ`, `وَأَكْثَرَ`, `فَٱسْتَمْتَعُوا۟`) now correctly type
> `segment_coverage=none`/`collision.kind=competing_segmentation` instead of
> `complete`.

> **Train E ambiguity-envelope repair (this round).** An independent Opus
> review of the assembled I9/finding-1 packet (verdict `TRAIN_E_REVIEW_BLOCK`)
> found four further reproduced defects in `_candidate_collision` and its
> consumers, all fixed together:
>
> **Finding 1 (evidence floor).** `tools/fusha_pattern_engine.py` emits one
> no-evidence fallback candidate per segmentation
> (`evidence_class=surface_candidate`, constant `score=1.0`) whenever nothing
> in the lexicon/pinned-pattern/function-inventory tables matched. The
> `18 rows` the previous round moved to `competing_segmentation` (`قَبْلِكُمْ`,
> `وَأَكْثَرَ`, `فَٱسْتَمْتَعُوا۟`, and others) turned out to be exactly this: EVERY
> tied top-scored candidate was a `surface_candidate` fallback, so the tie
> proved an absence of evidence for either segmentation, not a real lexical
> collision -- firing here falsely wiped the token's own class-neutral prefix
> clitic via the (then-unconditional) empty-`qg_segments` branch and diverted
> an ordinary ambiguous token into the collision queue. `_candidate_collision`
> now requires at least one tied-top candidate to carry real evidence
> (`evidence_class != "surface_candidate"`) before firing; an all-fallback tie
> returns `None` and keeps the pre-existing `ambiguous` (or, independently,
> `pending_context` via the unrelated `jar_majrur` context rule for a
> preposition-prefixed host) posture instead. `LLX-COLL-028`/`LLX-COLL-029`
> (`وفرتش`/`بفرتش`, synthetic no-evidence hostile probes) cover this at the
> parser layer.
>
> **Finding 2 (shared-span scoping).** A genuine tie (>= 1 tied-top candidate
> carries real evidence) still must not blanket-delete a class-neutral
> prefix/article that EVERY tied rival segmentation places at the exact same
> character span with the exact same role and surface -- that piece is not
> actually contested; only the letters after it are. `_candidate_collision`
> now calls `_shared_class_neutral_segments(seg_cands, candidate_refs)`, which
> intersects each rival's own `{(start, end): segment}` span map (offsets are
> the cumulative surface length within that rival's own segmentation, valid
> because `split_clitics` guarantees each candidate's segments concatenate
> exactly to the token surface) and keeps only spans where role, surface, AND
> membership in `CLASS_NEUTRAL_QG_ROLES` all agree across every rival -- the
> disputed stem, and any host-class-presupposing affix/clitic, can never
> survive this intersection because those roles are never members of that
> set. When the intersection is non-empty, the collision gains
> `scope="shared_class_neutral_prefix"` and a `shared_segments` list;
> `parse_text` projects exactly that list as `qg_segments` (see finding 4 for
> how the projector may report it). `بالله`, `يسألك`, and `بالكتاب` keep their
> prior fail-closed (empty `qg_segments`) behavior unchanged -- their tied
> rivals do not share an identical span (a whole-token match has no prefix
> segment to agree with; `لما`/`وما`'s whole-token rival likewise has none) --
> while a real corpus example, `وَمِيثَٰقَهُ` (`وَ` prefix_conjunction shared by
> both rivals) and `فَـَٔازَرَهُۥ` (`فَـَٔ` prefix_resumption_fa shared by both
> rivals), now correctly retain that shared prefix instead of emptying
> `qg_segments`. `LLX-COLL-030` covers `وَمِيثَٰقَهُ` at the parser layer.
>
> **Finding 3 (rival identity withholding).** Collision MEMBERSHIP in
> `_candidate_collision` is tie membership -- every candidate at the equal top
> score across >= 2 `segment_candidate_ref` values is a disputed rival, not
> only whichever one happens to sort to rank 1. `parse_text` used to strip
> `lemma`/`root`/`pos`/`gloss_hint` and mark `selection_status=candidate_only`
> on rank 1 alone, leaving every OTHER co-tied rival (rank 2+, same top score)
> still exposing its own identity in `morphology_candidates` -- a public leak
> of one of the contested readings even though the token's `hover_preview`
> and `selected_preview` were correctly withheld. For a `competing_segmentation`
> collision, `parse_text` now recomputes the tied top score directly from
> `tok["morphology_candidates"]` and strips/marks every candidate matching it
> (not only rank 1); every rival record is preserved (none removed), and a
> non-tied lower-score rival keeps its own identity untouched. This is scoped
> to `competing_segmentation` specifically -- `_candidate_collision`'s tied-
> top-score-across-refs mechanism is the only place "collision membership" and
> "rank 1" can actually diverge; R4/R5's skeleton collision reads a single
> selected candidate's own `collision.competitors` metadata, not separate
> tied `morphology_candidates` records, so it is unaffected.
>
> **Finding 4 (exact partial-span contract).** A `stem_identity` or
> `shared_class_neutral_prefix` collision can retain more than one
> `qg_segments` piece with the disputed stem withheld between them -- a real
> prefix+gap+suffix shape (e.g. a class-neutral prefix plus a degraded
> `clitic_undetermined` suffix). `tools/project_largelexicon_qamus_hover_candidates.py`
> used to concatenate ALL retained segment surfaces unconditionally
> (`"".join(...)`), which for a non-contiguous retained set would splice two
> spans that are not actually adjacent in the visible surface into an Arabic
> form that was never written. `_contiguous_projected_surface(segments,
> surface)` now walks each retained piece through the surface left-to-right
> and returns the literal contiguous slice `surface[start:end]` only when
> every piece sits immediately adjacent to the previous one (no gap, no
> reorder, no overlap); otherwise it returns `None` and the projector
> withholds `segment_surface` entirely (`segment_coverage` stays `"partial"`
> -- the individual retained segments in `segments` still stand on their own,
> just not spliced into a joined string). `tools/validate_largelexicon_qg_projection.py`
> independently re-derives the same contiguity check (never trusting the
> producer) and now accepts `collision.scope in {stem_identity,
> shared_class_neutral_prefix}` for `segment_coverage=partial`, requiring
> `segment_surface` to equal the exact contiguous slice when one exists and to
> be `null` when it does not.
>
> `qamus/examples/largelexicon/hover-candidates.sample.jsonl` was regenerated
> through `project_largelexicon_qamus_hover_candidates.py` against the real
> corpus: 17 rows changed. Fifteen of those (e.g. `وَأَكْثَرَ`, `فَٱسْتَمْتَعُوا۟`,
> `وَٱذْكُرُوا۟`) were finding 1's false positives -- they revert from
> `segment_coverage=none`/`collision.kind=competing_segmentation` back to
> `segment_coverage=complete` with no collision at all, because every one of
> their tied top candidates was in fact a no-evidence `surface_candidate`
> fallback. The remaining two (`فَـَٔازَرَهُۥ`, `وَمِيثَٰقَهُ`) are finding 2's
> positive case: they move from `segment_coverage=none` to
> `segment_coverage=partial`/`collision.scope=shared_class_neutral_prefix`,
> retaining only their shared prefix span. No row in the regenerated sample
> exhibits a non-contiguous (finding 4 gap) retention -- that case is covered
> by a direct hostile unit test of `_contiguous_projected_surface` (a
> synthetic prefix+gap+suffix construction) since none of the current 160
> sample rows happen to retain a prefix AND a suffix simultaneously around a
> withheld stem.

## Registry-authoritative gate metadata (I8, partially resolved)

`fusha/parser/collision-classes.json` names every registered class's gate
cap, route, and `filter_order`. Those used to be duplicated as literals at
each call site in `tools/fusha_standalone_parse.py` (`_gate`,
`_skeleton_collision`, `_candidate_collision`), with no consistency check, so
the registry could drift from the implementation silently (I8's original
framing). The registry is now the source of truth for a FIRED class's cap,
route, and lattice tie-break order: `_registry_vote(class_id)` looks up
`gate_effect.cap` and `filter_order` from `_CLASS_BY_ID` (built once from the
loaded registry) and returns the matching `GATE_RANK` entry; `_registry_route`
does the same for `route`. `_gate`'s votes for `source_requires_nahw_function`,
the skeleton-collision classes, and the `_candidate_collision` classes
(`unsafe_bare_match`/`competing_segmentation`) all read through these helpers
instead of hardcoding `"lexical_collision_requires_context"` or a tie-break
integer. WHETHER a class fires is unchanged -- the trigger predicates
(`_skeleton_collision`'s competitor-class check, `_candidate_collision`'s
tied-top-score-ref-multiplicity check) remain reviewed Python, per this
repair's scope; only the cap/route/order VALUES a fired class emits are now
registry-driven. This is a scoped, behavior-preserving resolution of I8's
"drift gap" question for cap/route/order specifically; I8's larger
architecture question (should trigger predicates themselves move into the
registry) remains open.

> **Train E finding 2 (repair, fail-closed authority).** `_registry_vote` and
> `_registry_route` originally accepted `default_cap`/`default_order`/
> `default_route` keyword arguments and silently substituted them whenever a
> fired class's registry entry was missing, or missing its `gate_effect.cap` /
> `filter_order` / `route`. That recreated exactly the shadow authority this
> repair claims not to have: a fired class with incomplete registry metadata
> would still parse through using a hardcoded historical literal instead of
> surfacing the drift. Both helpers now take only `class_id` and raise
> `RegistryAuthorityError` (defined in `tools/fusha_standalone_parse.py`) --
> deterministically, with no `try`/`except` anywhere in the module to swallow
> it, so it propagates straight out of `parse_text` -- whenever the class has
> no registry entry, or the entry's `gate_effect.cap` is not a valid
> `GATE_RANK` key, `filter_order` is not an `int`, or `route` is not a list.
> `tools/validate_fusha_standalone_parse.py`'s registry-mutation self-test
> mutates the loaded `competing_segmentation` entry in place (removing it
> entirely, then nulling `gate_effect.cap`/`route`/`filter_order` one at a
> time) and asserts each call raises `RegistryAuthorityError`, restoring the
> entry afterward so later assertions see the real registry. Unknown or
> incomplete class metadata for a class that fired can no longer parse
> through with a historical default -- it fails the token parse outright.

## Partial-coverage projection typing (I3, resolved)

`tools/project_largelexicon_qamus_hover_candidates.py` now types every row's
`segment_coverage` as `"complete"` (no collision; the ordinary full
concatenation), `"partial"` (a `scope=stem_identity` collision whose retained,
already-safe `qg_segments` are non-empty -- `segment_surface` becomes their
ordered concatenation, e.g. `بِهِمُ` types `partial`/`بِ`, retaining only the
preposition span, and `أَعْمَٰلَهُمْ` types `partial`/`هُمْ`, retaining only the
`clitic_undetermined` suffix), or `"none"` (a `whole_token` collision, a
`competing_segmentation`/`unsafe_bare_match` collision with no `scope` key at
all, or a `stem_identity` collision whose retained segments happen to be
empty). `token_contribution` stays `null` under every collision regardless of
coverage, so no gloss claim survives partial typing. `segment_surface` is
never asked to reconstruct the full `visible_surface` under any collision --
only the already-scoped, already-class-neutralized affix/clitic material the
parser itself decided was safe to retain. `tools/validate_largelexicon_qg_projection.py`
enforces `segment_coverage in {complete, partial, none}` and its agreement
with `collision`/`segments`/`segment_surface`, closing the "vacuous under
partial-withheld rows" gap this document used to record here.

The eight implemented collision/provenance classes (`source_requires_nahw_function`,
`compound_headword_bundle`, `root_identity_unresolved`, `pos_trichotomy_conflict`,
`root_conflict`, `scoped_collision`, the legacy `unsafe_bare_match` guard, and
`competing_segmentation`) are registered machine-readably in
`fusha/parser/collision-classes.json` (schema at
`fusha/parser/schemas/collision-class-registry.schema.json`), each with its
trigger keys, gate effect, route, and licensing canonical unit ids.
`scoped_collision`'s canonical unit ids also name
`cu-orthographic-connectivity-classes` and `cu-definite-article-assimilation`
as scoped-collision provenance ONLY -- this repair does not execute either
unit's own unresolved linguistic decisions (letter-connectivity classing, laam
assimilation); it only records that R7's scoping (preserving affix/clitic
segments while withholding a disputed stem) is provenance those units may
eventually license, alongside the pronoun-role and nisba-suffix units already
there.

`tools/project_largelexicon_qamus_hover_candidates.py` reconciles with this:
any token carrying a `collision` is projected with `token_contribution=null`,
`status=parser_packet`, `route=executor_parser_or_sarf_nahw_packet_ready`,
and the collision descriptor. `segment_surface` is `null` for a fully
withheld token (`whole_token` scope, or no `scope` key at all -- an unshared
`competing_segmentation`/`unsafe_bare_match`), and for a `stem_identity` or
`shared_class_neutral_prefix` scope whose retained segments turn out not to
be a single contiguous slice of `visible_surface` (Train E finding 4, above);
otherwise it is the literal contiguous substring those retained segments
cover. `tools/validate_largelexicon_qg_projection.py` independently
re-derives that same contiguity from `segments`/`visible_surface` (never
trusting the projector's decision) and enforces
`segment_surface == that contiguous slice` whenever one exists, and
`segment_surface == null` whenever it does not.

`tools/validate_fusha_standalone_parse.py::validate_record` (the Mode C
parse-record validator, distinct from the projection validator above) is
now COLLISION-AWARE: a token carrying `collision.scope == "stem_identity"`
must retain a non-empty, left-to-right, non-overlapping ordered SUBSET of the
surface in `qg_segments` (the withheld stem creates a gap; the check walks
each retained segment's surface through the token surface in order rather
than requiring full concatenation); a token carrying `collision` with any
other scope (`whole_token`, or a `_candidate_collision` result with no
`scope` key at all) must project no `qg_segments`; and any token carrying
`collision` must have `hover_preview.token_contribution_gloss == null`.

**Semantic role assertion (Train E follow-up gap 3).** The ordered-subset
check alone only proves the surviving segments land in order somewhere in
the surface — it does not prove the disputed stem or a class-presupposing
affix was actually withheld, so a regression reintroducing `stem`/
`verb_stem`/`adjective_stem`, an un-degraded `object_pronoun`/
`subject_pronoun`, or an un-degraded `verb_prefix`/`future_particle`/
`derivative_prefix`/`plural_suffix` into a `stem_identity` row would still
pass the ordered-subset check as long as the leftover pieces happened to be
in the right order. `validate_record` now additionally checks every
`scope == "stem_identity"` token's `qg` roles against
`CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES` (the same role set gap 2 withholds
or degrades) and flags any that leaked through undegraded. `validate_record`
also checks every retained segment's `class` against
`CLASS_PRESUPPOSING_QG_CLASSES` independently of `role` (Train E follow-up
defect A above): a role can be honestly renamed to `affix_undetermined`/
`clitic_undetermined` while its `class` still asserts the disputed host
category, and that leak is caught even when the role check alone would pass.

Ordinary, non-collision tokens keep the original unweakened
full-concatenation check. Before this repair, the validator applied the
ordinary full-concatenation and preposition/pronoun-headline checks
unconditionally, which would reject a correct `stem_identity` row (partial
coverage never equals the full surface) and would separately accept an
incorrect whole-token row whose leftover `qg_segments` happened to still
concatenate the full surface (Train E review I2).

This is candidate-boundary work only: nothing here calls or imitates
`tools/certify_typed_fact.py`, `shares_root`/`realizes_form`/
`occurrence_instantiates_lexeme`/`root_family_member` remain distinct
edges, `morphology_candidates[0]` is still never a deploy signal, and
`safe_for_qamus_executor_autopromote` stays `false`.

## Deferred spec decisions (recorded, not solved)

An assembled Opus review of the R1-R8 packet raised several IMPORTANT findings
that each needed a spec decision before a patch, not a patch first. **I3, I8
(partially), and I9 are now resolved** -- see "Partial-coverage projection
typing (I3, resolved)", "Registry-authoritative gate metadata (I8, partially
resolved)", and "Competing segmentation is not a same-stem collision (I9,
resolved)" above. I5 and I7 remain open and are recorded here so they are not
lost; neither is solved by this repair, and their fix sites
(`tools/fusha_pattern_engine.py`) remain outside this repair's edit scope.

- **I5 — whether `pos` is withheld under R2/R3.** `_candidate_from_row` keeps
  `pos` when only `lemma`/`root`/gloss are withheld (compound-headword /
  unresolved-root), and that `pos` still selects a qg class and renders into
  `hover_preview.morphline` (e.g. a verb-shaped qg class for a withheld noun
  stem). Is a bare part-of-speech assertion an identity claim that R2/R3
  should also withhold, or is it in-bounds recall evidence like the
  skeleton itself? This is a spec decision about what R2/R3 promise, not a
  bug in what they currently do.
- **I7 — single-entry over-projection policy.** Abstention is keyed on >= 2
  competing entries; a surface matched by exactly one (possibly wrong) entry
  still projects a full gloss at the highest gate (`likely_from_internal_pattern`)
  with no source-address proof. Is single-row confidence acceptable as
  "recall evidence," or does the "a source lexicon row is recall evidence,
  not identity" framing this document opens with also require a floor on
  single-entry gloss projection? Needs a decision on acceptable false-positive
  rate for the un-collided majority, not a widening of R4/R5's trigger.

(I8's remaining open question -- whether trigger predicates themselves, not
just the cap/route/order values a fired class emits, should move into the
registry -- is an architecture decision beyond this repair's scope; see
"Registry-authoritative gate metadata (I8, partially resolved)" above.)

## Regression bank

Executable fixtures live at:

- `fusha/parser/eval/largelexicon-collision-regressions.jsonl`

They cover:

- `الله` must not project `ال + له`;
- `بالله` must reach competing_segmentation (Train E finding 1) rather than
  silently picking either the bā'+Allah split or the whole-token reading;
- `من` must not top-rank the verb `مَنَّ` in arbitrary text;
- `إله` must not render as host + object pronoun or a source-certified hover
  without context;
- `إلا` must not project the noun `إِلًّا` where the exception-particle lane is
  required;
- `إنما` remains a positive control for particle-cluster visibility (one
  top-scored segmentation); `بالنيات` moved from a real-clitic-visibility
  positive control to a competing_segmentation hostile fixture alongside
  `بالله` (Train E finding 1) once its own tied splits were found.
- `LLX-COLL-008..022` cover the skeleton-collision/source-provenance rules
  above: `pos_trichotomy_conflict`, `scoped_collision`,
  `rejected_segmentation_is_not_a_competitor`, `compound_headword_bundle`,
  `root_identity_unresolved`, `source_requires_nahw_function`,
  `root_conflict`, `plural_template_not_identity`, three negative controls
  (same-lemma same-class, ordinary harakah-only risk, rm12 gate stability),
  and mim-initial/afal-shape/participle-voice/shared-root hostile probes.
- `LLX-COLL-023`/`LLX-COLL-024` cover `competing_segmentation` (I9, resolved):
  `لما` and `وما` each tie a prefix+`ما` split against a whole-token particle
  reading across two different `segment_candidate_ref` values, and neither
  rival may be silently selected. `LLX-COLL-025` is the paired positive
  control (`إنما` has exactly one top-scored segmentation and must stay
  unaffected). `LLX-COLL-026`/`LLX-COLL-027` cover the I3 partial-coverage
  typing consumer surfaces (`بِهِمُ` retains only the preposition span;
  `أَعْمَٰلَهُمْ` retains only the `clitic_undetermined` suffix) at the parser
  layer; `tools/project_largelexicon_qamus_hover_candidates.py --self-test`
  covers the same two surfaces' `segment_coverage`/`segment_surface` typing at
  the projection layer.
- `LLX-COLL-002`/`LLX-COLL-007` cover `competing_segmentation` on a
  same-identity, different-ref tie (Train E finding 1): `بالله` and `بالنيات`
  each tie two rival segmentations that resolve to the SAME lemma/pos/root,
  and neither may be silently selected -- `require_candidate_refs_min: 2`
  asserts both rival refs survive, and `forbid_selected_preview` asserts no
  preview is emitted for either rival.
- `LLX-COLL-028`/`LLX-COLL-029` cover the finding 1 evidence-floor guard:
  `وفرتش`/`بفرتش` tie two `surface_candidate` no-evidence fallbacks at top
  score and must never reach `lexical_collision_requires_context`, only the
  pre-existing `ambiguous`/`pending_context` posture, with the class-neutral
  prefix clitic surviving. `LLX-COLL-030` covers the finding 2 shared-span
  positive: `وَمِيثَٰقَهُ`'s two tied rival segmentations agree on the same
  leading `وَ` prefix_conjunction span, so `collision.scope` must be
  `shared_class_neutral_prefix` and that span must survive while the disputed
  stem never does.

> **Open verification item.** No fixture currently pairs
> `require_source_risk_flags` with `require_collision_kind` (Train E review
> B1's missing probe) — `LLX-COLL-008..022` never combine the two. If
> `LLX-COLL-013`'s surface (`ٱلَّذِى`) turns out to have >= 2 conflicting
> `norm_strict`-key competitors once the lattice above runs against the full
> corpus, its `or_gate` must widen to accept
> `lexical_collision_requires_context`, and a dedicated combined-condition
> fixture should be added. This repair does not touch fixture data or verify
> corpus reachability; both are deferred to the deterministic regeneration/
> gate run.

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools\validate_largelexicon_parser.py --self-test
python tools\validate_largelexicon_cli_contract.py --self-test
python tools\validate_fusha_standalone_parse.py --self-test
python tools\project_largelexicon_qamus_hover_candidates.py --self-test
python tools\validate_largelexicon_qg_projection.py
```

Regenerating the committed projection sample after a parser/projector change
(byte-fresh, from the generator, never hand-edited):

```powershell
python tools\project_largelexicon_qamus_hover_candidates.py
```

## Executor consumption

The Qamus rollout executor may use largelexicon output as a worklist accelerator,
not as a live deployment decision. A row must either carry source-addressed
proof and pass executor validation, or route to an exact packet:

- `sarf_collision_review`;
- `nahw_function_review`;
- `source_crosswalk_packet`;
- `validator_packet`;
- `executor_validation_required`.

This preserves the Project-Xanadu-style architecture: parser candidates are
transclusions of source facts, not orphan copies. If a lemma, function inventory
rule, clitic splitter rule, or source/crosswalk row changes, dependent hover
projections must regenerate or become stale.
