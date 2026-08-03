# Largelexicon Collision Safety

Largelexicon increases recall by exposing many more Qamus-authored forms to the
parser. That also increases the collision surface for short Arabic tokens,
especially particles, proper names, and tokens that can be mechanically split
into clitic-looking pieces.

The rule is simple: coverage is not disambiguation. A larger table may add a
candidate, but it does not make that candidate safe for a public hover.

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
lemma/root/pos claim by itself). `tools/fusha_standalone_parse.py::_gate` runs
an ORDERED pipeline before the pre-existing gate ladder. A later filter never
raises confidence an earlier filter lowered, and every collision or
demotion carries `decided_by` naming the filter.

1. **source_provenance** (`R1`) — if the selected candidate's matched entry
   declares `risk_flags` including `requires_nahw_function`,
   `confidence_gate` is capped at `pending_context` and the token routes to
   `nahw_function_review`. Entries lacking the flag are unaffected. This
   check runs first and short-circuits.
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
   `number` features from the withheld candidate. A shared root between
   competitors never clears a `pos_trichotomy_conflict` — that is the
   forbidden root-to-identity inference (`LLX-COLL-022`).
4. **existing gate ladder** — unchanged: function-token context routing,
   `_candidate_collision` (bare high-risk-match and cross-segmentation
   collisions), then the internal-pattern/ambiguous fallback.

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
and the collision descriptor.
`tools/validate_largelexicon_qg_projection.py` enforces the
`segment_surface == visible_surface` concatenation invariant only when
`segment_surface` is non-null, and requires `token_contribution` to be
null whenever `segments` is empty.

This is candidate-boundary work only: nothing here calls or imitates
`tools/certify_typed_fact.py`, `shares_root`/`realizes_form`/
`occurrence_instantiates_lexeme`/`root_family_member` remain distinct
edges, `morphology_candidates[0]` is still never a deploy signal, and
`safe_for_qamus_executor_autopromote` stays `false`.

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
