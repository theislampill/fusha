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

## Required behavior

- Candidate enumeration remains broad.
- The selected preview is suppressed or context-gated when a high-risk candidate
  is only a `bare_match` / weak match or competes with a function-token route.
- `morphology_candidates[0]` is never a deploy signal by itself.
- `safe_for_qamus_executor_autopromote` remains `false` for local arbitrary-text
  CLI output.
- Function-token alternatives route to `pending_context` instead of being
  collapsed into a content-word hover.
- Real clitics remain visible when the morphology identity is stable, e.g.
  bā' + Allah or bā' + article + host.

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
  `الله` fixtures to collision, amplifying the exact artifact
  `LLX-COLL-001`/`LLX-COLL-002` exist to suppress (`LLX-COLL-010`).
- **R7 — scoped collision.** When `R4`/`R5` fires, `collision.scope` is
  `stem_identity` if the selected segment candidate has more than one
  segment, else `whole_token`. Under `stem_identity` the affix/clitic `qg`
  segments and their letter spans are PRESERVED (`LLX-COLL-009`); only the
  stem segment is withheld, and a clitic pronoun role (`object_pronoun`/
  `subject_pronoun`) degrades to `clitic_undetermined` rather than keeping a
  role that presupposes the disputed host class. Under `whole_token`,
  `qg_segments` is emptied as before. Unconditionally emptying `qg_segments`
  breaks `LLX-COLL-002`'s `required_roles=[prefix_preposition]`.

The seven implemented collision/provenance classes (`source_requires_nahw_function`,
`compound_headword_bundle`, `root_identity_unresolved`, `pos_trichotomy_conflict`,
`root_conflict`, `scoped_collision`, and the legacy `unsafe_bare_match` guard)
are registered machine-readably in `fusha/parser/collision-classes.json`
(schema at `fusha/parser/schemas/collision-class-registry.schema.json`), each
with its trigger keys, gate effect, route, and licensing canonical unit ids.

`tools/project_largelexicon_qamus_hover_candidates.py` reconciles with this:
any token carrying a `collision` (fully or partially withheld stem) is
projected with `segment_surface=null`, `token_contribution=null`,
`status=parser_packet`, `route=executor_parser_or_sarf_nahw_packet_ready`,
and the collision descriptor. **This is honestly incomplete** for
`scope=stem_identity` rows whose `segments` array is non-empty (see I3 under
"Deferred spec decisions" below): `segment_surface=null` is set for every
collision row alike, even one that retains real affix segments and could
report a partial, ordered affix concatenation instead. `token_contribution`
does stay `null` either way, so no identity/gloss claim survives; the gap is
in the (unused for now) partial-coverage typing, not in the abstention.
`tools/validate_largelexicon_qg_projection.py` enforces the
`segment_surface == visible_surface` concatenation invariant only when
`segment_surface` is non-null, and requires `token_contribution` to be
null whenever `segments` is empty; because the projector always nulls
`segment_surface` under any collision, that invariant is currently vacuous
for partially-withheld rows too. Neither file is in this repair's edit scope.

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

An assembled Opus review of the R1-R8 packet raised four IMPORTANT findings
that each need a spec decision before a patch, not a patch first. They are
recorded here so they are not lost; none are solved by this repair, and none
of their fix sites are in this repair's edit scope
(`tools/fusha_pattern_engine.py`, `tools/project_largelexicon_qamus_hover_candidates.py`,
`tools/validate_largelexicon_qg_projection.py`, `fusha/parser/collision-classes.json`).

- **I3 — partial-coverage typing.** Should a `scope=stem_identity` collision
  row emit a typed `segment_coverage: "partial"` plus the retained affix
  concatenation (required to be a contiguous ordered subsequence of
  `visible_surface`), instead of `segment_surface=null` unconditionally? This
  needs a decision on the projected schema shape, not a patch to
  `project_largelexicon_qamus_hover_candidates.py`.
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
- **I8 — registry-as-source-of-truth.** `fusha/parser/collision-classes.json`
  records every class's `gate_effect.cap`/`route`/`filter_order`, but
  `_gate`/`_skeleton_collision`/`_candidate_collision` duplicate those as
  code literals with no consistency check, so the registry can drift from
  the implementation silently. Should the registry become the executable
  source of truth (code reads caps/routes/order from it), or stay documentary
  (and if so, what closes the drift gap)? This is an architecture decision,
  not a bug in either the registry or the code as they stand today.

## Regression bank

Executable fixtures live at:

- `fusha/parser/eval/largelexicon-collision-regressions.jsonl`

They cover:

- `الله` must not project `ال + له`;
- `بالله` must preserve bā' plus Allah without turning Allah into lām + pronoun;
- `من` must not top-rank the verb `مَنَّ` in arbitrary text;
- `إله` must not render as host + object pronoun or a source-certified hover
  without context;
- `إلا` must not project the noun `إِلًّا` where the exception-particle lane is
  required;
- `إنما` and `بالنيات` remain positive controls for particle-cluster and real
  clitic visibility.
- `LLX-COLL-008..022` cover the skeleton-collision/source-provenance rules
  above: `pos_trichotomy_conflict`, `scoped_collision`,
  `rejected_segmentation_is_not_a_competitor`, `compound_headword_bundle`,
  `root_identity_unresolved`, `source_requires_nahw_function`,
  `root_conflict`, `plural_template_not_identity`, three negative controls
  (same-lemma same-class, ordinary harakah-only risk, rm12 gate stability),
  and mim-initial/afal-shape/participle-voice/shared-root hostile probes.

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
