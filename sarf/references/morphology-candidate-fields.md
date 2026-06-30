# Reference — morphology candidate fields

The field contract for a morphology candidate. **The source of truth is the committed schema**
[`qamus/schemas/morphology-candidate-lattice.schema.json`](../../qamus/schemas/morphology-candidate-lattice.schema.json) — read it for
the authoritative enums; this page is the orientation map, not a second copy.

## Container (the per-token lattice)
`{ token_ref, candidates[≥1], top_rank, n_candidates, all_unvoweled_kept: true }`. `>1` candidate ⇒ the token is `pending` /
`parse_confidence ∈ {surface_only, candidate}`.

## Candidate
| field | meaning |
|---|---|
| `pos` | coarse part-of-speech (a closed SUBSET of the morphosyntax-token `pos` enum) |
| `features{}` | `verb_form, voice, aspect, mood, person, number, gender, case, state, derivative_type, particle_function` — KEYS are closed; map 1:1 onto `morphosyntax-token` `sarf{}`; an unconfirmed feature stays null |
| `lemma` / `root` / `pattern` | authored, or **null** — never fabricated from resemblance |
| `confidence` | `low \| medium \| high` (derived from the score band) |
| `score` AND `rank` | two DISTINCT fields — additive score + 1-based ordering; **never a boolean `correct`** |
| `evidence_class` | `voweled_confirmable \| source_addressed_confirmable \| unvoweled_competing \| homograph_split \| weak_root_gated \| component_only` |
| `gate` | the canonical 4-tier; `unvoweled_competing`/`homograph_split` are never `auto_safe` |
| `ambiguity_reason` | why this stays a candidate — authored, source-clean (scanned by `leak_sot`) |
| `segment_candidate_ref` | integer index into the token's `segment_candidates` (a real row; never a rebuilt segmentation) |

## How features map to the public hover
The chosen reading (`rank == 1`) maps onto `morphosyntax-token` `sarf{}` and drives one `qamus-grammar-v1` `qg-*` display class per
visible piece (see SKILL §8). Unsupported morphology facts park in `derivative_type` / the segment label / the learner explanation —
never a minted `qg-*` class.

## Boundary
`{src:qamus, kind:authored, lang:en, external_source_names_public:false}`. No QAC/tafsir/source/path label in any candidate text.
