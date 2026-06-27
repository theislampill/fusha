# Full-Corpus Dogfood VN-03 - Third Standard Verb/Noun Tranche

Status: repo-only dogfood output. No live Qamus data, WBW artifact, mirror repo,
service, rebuild, hover apply, or hover coverage claim was changed.

Source batch: `out/standard-tranche-vn03-20260627/`

## Scope

- Verbs: `v138` through `v182`.
- Nouns: `n146` through `n195`.
- Entries inventoried: `95` total (`45` verb, `50` noun).
- Live hover rows: `904`, including `618` whole/resolved rows and `286`
  component-only evidence rows.
- Zero-row entries: `n147`, `n148`, `n154`, `n159`, `n160`, `n164`,
  `n165`, `n168`, `n179`, `n186`, `n190`, `n191`, `n193`, `n194`,
  `v147`.

## Controller Counts

| class | rows |
|---|---:|
| populated_uncertified | 675 |
| token_only_override | 223 |
| pending/blocker | 4 |
| known_defect | 2 |

Routes:

- `blocker_queue_row`: `679`
- `repair_candidate`: `225`
- `production_bug_lesson`: `607`
- `drill_regression_fixture`: `607`
- `sarf_nahw_procedure_improvement`: controller route only; applied skill
  changes are listed below.

These are next-state routes, not live applies.

## Review Packets

Bounded reviewer packets were generated:

- verb sarf: `180` rows;
- noun sarf: `180` rows;
- nahw context: `200` rows;
- rich renderer: `200` rows;
- Qamus entry linkage: `200` rows;
- learner explanation: `200` rows.

The VN-03 controller converged on five findings:

1. Finite verbs such as `عَقَلُوهُ`, `أَعْجَلَكَ`, and
   `وَيَسْتَعْجِلُونَكَ` are still string-populated by dictionary infinitives
   unless the suffix object and finite morphology are visible.
2. Component-only rows such as `فَأَهْلَكْنَاهُمْ` can be linguistically
   readable but must not certify or propagate without whole-token evidence and
   a two-vote gate.
3. Nominal/adjectival tokens such as `ضَعِيفًا` may have good English strings
   while still failing rich certification because the exact noun/adjective role
   and i'rab link are not established.
4. Noun entries in this tranche expose repeated POS leakage: `ٱلدِّينِ`
   receives verb-family prose, and Islam-derived participles/person nouns such
   as `مُسْلِمَيْنِ` receive the abstract concept gloss.
5. Jar-majrur or possessed nominal rows inside verb families, such as
   `بِعَهْدِ` and `زِينَتَهُنَّ`, require nahw attachment/possessor review
   before any repair packet can be considered.
6. Proper/group/common and scripture-title rows (`هُود`, `وَدّ`, `زَبُور`,
   `صُحُف`, `ٱلرُّوم`, `قُرَيْش`) need referent and number/class metadata
   before any family-wide propagation.

## Compact Controller Table

| loc | surface | current gloss | defect class | expected contribution | state movement | next gate |
|---|---|---|---|---|---|---|
| 26:139:2 | `فَأَهْلَكْنَاهُمْ` | so We destroyed them | component-only finite verb/suffix blocker | `فَ` + Form IV perfect 1cp + `هُمْ` object | known_defect -> lesson + suffix regression | two-vote |
| 4:28:8 | `ضَعِيفًا` | weak | nominal/adjectival token via verb-entry component | accusative indefinite noun/adjective role, not a finite verb | known_defect -> nominal/i'rab fixture | two-vote |
| 1:4:3 | `ٱلدِّينِ` | to be bound by an authority such as faith or judgment | noun gets verb infinitive | definite/genitive noun in construction | token_only_override -> nominal/idafa fixture | token-only two-vote |
| 109:6:2 | `دِينُكُمْ` | Faith, religion, or way of life. | possessed noun missing suffix accounting | noun + `كُمْ` possessor | token_only_override -> suffix/idafa fixture | exact-address suffix review |
| 2:71:13 | `مُسَلَّمَةٌ` | Islam, full submission to the Will of Allah. | concept gloss on adjectival/passive token | safe/sound/submitted by exact morphology | token_only_override -> nominal-derivative fixture | token-only two-vote |
| 2:128:3 | `مُسْلِمَيْنِ` | Islam, full submission to the Will of Allah. | concept gloss on participle/person token | two submitters/Muslims by case/number review | token_only_override -> nominal-derivative fixture | token-only two-vote |
| 2:75:17 | `عَقَلُوهُ` | to reason; understand | finite verb suffix omitted | perfect plural verb + `هُ` object | token_only_override -> suffix regression | exact-address form/suffix review |
| 13:6:1 | `وَيَسْتَعْجِلُونَكَ` | to hasten | component-only finite verb suffix omitted | `وَ` + Form X imperfect 3mp + `كَ` object | populated_uncertified -> blocker row | component-only blocker |
| 20:83:2 | `أَعْجَلَكَ` | to hasten | finite verb suffix omitted | finite verb host + `كَ` object | token_only_override -> suffix regression | exact-address form/suffix review |
| 16:91:2 | `بِعَهْدِ` | to make a covenant... | jar-majrur noun inherits verb prose | `بِـ` + majrūr noun, attachment pending | populated_uncertified -> nahw fixture | component-only blocker |
| 24:31:10 | `زِينَتَهُنَّ` | their adornment; their finery | possessed nominal inside verb family | noun + `هُنَّ` possessor with rich metadata | populated_uncertified -> renderer/suffix row | exact-address suffix review |
| 30:2:2 | `ٱلرُّومُ` | The Romans. | string-only proper group noun | article + proper group noun + case metadata | token_only_override -> needs_renderer_segments | token-only two-vote |

## Skill Impact

Updated sarf:

- `sarf/procedures/verb-form-and-mood-review.md` adds VN-03 examples for
  `عَقَلُوهُ`, `أَعْجَلَكَ`, `وَيَسْتَعْجِلُونَكَ`, and
  `فَأَهْلَكْنَاهُمْ`.
- `sarf/procedures/nominal-derivative-decision.md` adds the VN-03 rule that
  nominal/adjectival tokens in verb-entry component rows are not certified by
  the verb family.
- `sarf/drills/verb-measures.md` adds VN-03 finite/suffix rows.
- `sarf/drills/nominal-derivatives.md` adds VN-03 Islam and dīn rows.
- `sarf/evals/false-clitic-split-eval.jsonl` adds VN-03 suffix/finite controls.
- `sarf/evals/nominal-derivative-error-eval.jsonl` adds VN-03 nominal/POS
  leakage controls.
- `sarf/procedures/proper-noun.md` and `sarf/drills/homograph-regressions.md`
  add VN-03 group/proper/common and scripture-title collision notes.

Updated nahw:

- `nahw/drills/grammar-routing-hard-cases.md` adds VN-03 context gates for
  `ضَعِيفًا`, `بِعَهْدِ`, `وَيَسْتَعْجِلُونَكَ`, and `زِينَتَهُنَّ`.
- `nahw/drills/idafa-and-jar-majrur.md` adds VN-03 dīn/possessive and covenant
  rows.
- `nahw/procedures/referent-context.md` adds VN-03 group, named-object,
  scripture-title, and collective-noun referent guards.
- `nahw/evals/irab-polysemy-eval.jsonl` adds exact-address fixtures for
  `ضَعِيفًا`, `ٱلدِّينِ`, `دِينُكُمْ`, `بِعَهْدِ`, and `زِينَتَهُنَّ`.

No-op reasons:

- Proper group-name rows such as `إِرَم`, `ٱلرُّومُ`, and `قُرَيْشٍ` mainly
  need renderer/parse-key metadata. Existing sarf/nahw doctrine already blocks
  string-only proper-name rows from rich certification.
- Component-only evidence remains component evidence only; it does not create
  new `auto_safe` rows, source agreement, closure coverage, or hover coverage.
- Repair-preview-ready rows remain `0`; this tranche did not run source
  triangulation, two-vote response, owner approval, or apply planning.

## Production-Bug Lessons

Committed sample: `qamus/examples/dogfood_vn03_production_bug_lesson.sample.jsonl`

Rows:

- `quran:2:75:17` / `wbw:2:75:17` - finite verb plus object suffix hidden by
  dictionary prose.
- `quran:26:139:2` / `wbw:26:139:2` - component-only Form IV verb/suffix row
  must not certify the whole token.
- `quran:4:28:8` / `wbw:4:28:8` - nominal/adjectival token collides with a
  verb-entry component.
- `quran:1:4:3` / `wbw:1:4:3` - dīn noun receives verb infinitive prose.
- `quran:2:128:3` / `wbw:2:128:3` - Islam concept gloss applied to a shaped
  participial/person token.
- `quran:16:91:2` / `wbw:16:91:2` - bā' plus nominal host inherits verb-family
  covenant prose.

## Renderer Requirements

VN-03 generated renderer requirements for string-populated but non-rich rows:

- finite verbs need prefix/stem/suffix classes and parse keys, especially when
  object suffixes are visible;
- nominal/adjectival rows need article/case/state display metadata before rich
  certification;
- possessive nominal rows need host + possessor segmentation without breaking
  the Arabic surface;
- proper group nouns need public-safe proper-noun/title segment readiness.

## Repair Preview Status

Repair-preview-ready rows: `0`.

Reason: this tranche produced dogfood evidence and regression targets only. No
live source triangulation, two-vote response, owner approval, or apply plan was
run.

## Outputs

- `qamus/examples/full_corpus_dogfood_vn03_inventory.sample.jsonl`
- `qamus/examples/full_corpus_dogfood_vn03_skill_impact.sample.jsonl`
- `qamus/examples/dogfood_vn03_production_bug_lesson.sample.jsonl`
- `sarf/evals/nominal-derivative-error-eval.jsonl`
- `sarf/evals/false-clitic-split-eval.jsonl`
- `nahw/evals/irab-polysemy-eval.jsonl`
- sarf/nahw drill and procedure updates listed above

## Boundaries

- Public output remains source-clean: `src=qamus`, `kind=authored`,
  `lang=en`.
- No public source labels, adapter names, or internal evidence were introduced.
- No live Qamus data was changed.
- No hover coverage improvement or correctness-completion claim is made.
