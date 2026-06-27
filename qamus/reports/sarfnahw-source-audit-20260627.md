# Sarf/Nahw Source Folder Audit - 2026-06-27

Status: repo-only audit. No live Qamus data, WBW artifact, service, mirror, or
hover decision ledger was changed.

Audit root: owner-provided local `sarfnahw` source folder outside this repo.

Local extraction scratch, not committed: `out/sarfnahw-audit-20260627/`

## Implementaudit Frame

Truth owners:

- Fusha repo source remains the authority for sarf/nahw procedures, curriculum,
  validators, and candidate reports.
- The `sarfnahw` folder is internal evidence and lesson material only. It is not
  a source of public hover text and does not override Qamus, sarf, nahw, i'rab,
  or exact token context.
- QAC screenshots and grammar captions are internal routing/curriculum evidence.
- AMAU Anki decks are internal sequencing/vocabulary-course evidence only; do
  not copy card text or public-facing wording.
- `GrammarProblems.pdf` is grammar-risk evidence for the existing
  wrong-reasoning gate.

Contract boundary:

- Public hover payload remains source-clean: `src=qamus`, `kind=authored`,
  `lang=en`.
- No QAC, AMAU, Quran.com, Tafsir MCP, OCR, screenshot, local path, or source
  adapter label belongs in public browser payloads.
- Rich hover metadata may expose scrubbed Qamus role classes and authored
  learner explanations, not external source labels.

Cutover status:

- This audit does not cut over any live path.
- The output is a repo-side curriculum/skill synthesis and source-boundary map
  to inform future dogfood and owner-gated apply planning.

Abort conditions held:

- No live mutation authorized.
- No full OCR/import of external source files into the repo.
- No external wording copied into public artifacts.
- No hover coverage or correctness-completion claim.

## Inventory Summary

The folder contains 81 filesystem items: 75 files and 6 directories.

| suffix | count | audit result |
|---|---:|---|
| `.png` | 46 | QAC grammar screenshots; internal visual reference only |
| `.apkg` | 11 | AMAU Anki decks; internal sequencing metadata only |
| `.pdf` | 10 | GrammarProblems plus nine verb-chart PDFs |
| `.md` | 4 | Three QAC pack reviews plus one Nature architecture/learning-theory article |
| `.json` | 3 | QAC pack manifests |
| `.docx` | 1 | Verb-table supplement |

## Full File Inventory

| path | type | audit disposition |
|---|---|---|
| `GrammarProblems.pdf` | PDF | Useful internal grammar-risk source; already represented by grammar evals and wrong-reasoning gates. |
| `learn-arabic-with-amau--section-7-getting-used-to-arabic.apkg` | APKG | Internal sequencing metadata; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-4_-getting-used-to-arabic.apkg` | APKG | Internal beginner sentence sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-4_-vocab.apkg` | APKG | Internal vocabulary category sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-5_-getting-used-to-arabic.apkg` | APKG | Internal sentence sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-5_-vocab.apkg` | APKG | Internal verb/preposition/verbal-noun sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-6_-getting-used-to-arabic.apkg` | APKG | Internal sentence sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-6_-vocab.apkg` | APKG | Internal adjective/body/family/number vocabulary sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-6_-vocab__vocabulary-of-comprehension-lessons.apkg` | APKG | Internal comprehension-vocabulary sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-7_-vocab.apkg` | APKG | Internal food/desert/weather/number vocabulary sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-8_-getting-used-to-arabic.apkg` | APKG | Internal sentence sequencing; no public/card text import. |
| `learn-arabic-with-amau__amau-arabic-section-8_-vocab.apkg` | APKG | Internal office/kitchen/customs vocabulary sequencing; no public/card text import. |
| `qac_grammar_review_pack/README_review.md` | Markdown | Useful internal synthesis; aligns with current Qamus/Fusha boundaries. |
| `qac_grammar_review_pack/manifest.json` | JSON | Useful manifest for screenshot coverage and hashes; internal only. |
| `qac_grammar_review_pack/images/01_097_1_inna_anzalnahu_morphology.png` | PNG | Inna/verb-pronoun morphology visual reference. |
| `qac_grammar_review_pack/images/02_097_1_laylat_al_qadr_named_entity.png` | PNG | Named entity span/idafa visual reference. |
| `qac_grammar_review_pack/images/03_067_1_al_mulk_dependency.png` | PNG | Dependency, PP, relative, idafa visual reference. |
| `qac_grammar_review_pack/images/04_013_11_yahfazunahu_verb_pronouns.png` | PNG | Verb subject/object pronoun visual reference. |
| `qac_grammar_review_pack/images/05_013_11_muaqqibat_participle.png` | PNG | Participle/gender visual reference. |
| `qac_grammar_review_pack/images/06_001_3_sifa_adjectives.png` | PNG | Sifa/adjective dependency visual reference. |
| `qac_grammar_review_pack/images/07_088_1_idafa_possessive.png` | PNG | Idafa visual reference. |
| `qac_grammar_review_pack/images/08_096_16_apposition_adjectives.png` | PNG | Badal/apposition and adjectives visual reference. |
| `qac_grammar_review_pack/images/09_069_32_tamyiz_specification.png` | PNG | Tamyiz/specification visual reference. |
| `qac_grammar_review_pack/images/10_074_30_compound_number.png` | PNG | Compound-number visual reference. |
| `qac_grammar_review_pack/images/11_roots_derivation_overview.png` | PNG | Root/pattern derivation visual reference. |
| `qac_grammar_review_pack/images/12_triliteral_forms_I_III.png` | PNG | Verb forms I-III visual reference. |
| `qac_grammar_review_pack/images/13_triliteral_forms_IV_V.png` | PNG | Verb forms IV-V visual reference. |
| `qac_grammar_review_pack/images/14_triliteral_forms_VI_X.png` | PNG | Verb forms VI-X visual reference. |
| `qac_grammar_review_pack/images/15_quadrilateral_verb_forms.png` | PNG | Quadrilateral forms visual reference. |
| `qac_grammar_review_pack/images/16_verb_subjects_active_passive_99_1.png` | PNG | Active/passive subject-representative visual reference. |
| `qac_grammar_review_pack/images/17_verb_subject_object_99_2.png` | PNG | Subject/object dependency visual reference. |
| `qac_grammar_review_pack/images/18_kana_and_sisters_110_3.png` | PNG | Kana/subject/predicate visual reference. |
| `qac_grammar_review_pack/images/19_extra_grammar_capture_400.png` | PNG | Extra QAC grammar capture; internal review only. |
| `qac_grammar_review_pack/images/20_extra_grammar_capture_401.png` | PNG | Extra QAC grammar capture; internal review only. |
| `qac_grammar_review_pack_part2/README_review.md` | Markdown | Useful internal synthesis for governing particles, moods, PP attachment. |
| `qac_grammar_review_pack_part2/manifest.json` | JSON | Useful manifest for screenshot coverage and hashes; internal only. |
| `qac_grammar_review_pack_part2/images/01_kada_and_negative_ma_laysa_067_8_086_14.png` | PNG | Kada and negative ma/laysa visual reference. |
| `qac_grammar_review_pack_part2/images/02_subjunctive_mood_particles_072_12.png` | PNG | Subjunctive-governing particles visual reference. |
| `qac_grammar_review_pack_part2/images/03_jussive_mood_particle_table.png` | PNG | Jussive-governing particles visual reference. |
| `qac_grammar_review_pack_part2/images/04_jussive_negation_094_1.png` | PNG | Jussive negation visual reference. |
| `qac_grammar_review_pack_part2/images/05_imperative_command_and_lam_087_1_106_3.png` | PNG | Imperative and imperative lam visual reference. |
| `qac_grammar_review_pack_part2/images/06_prohibition_and_imperative_result_068_8_070_42.png` | PNG | Prohibition and jawab amr visual reference. |
| `qac_grammar_review_pack_part2/images/07_preposition_phrase_attached_to_verb_100_5.png` | PNG | PP attached to verb visual reference. |
| `qac_grammar_review_pack_part2/images/08_oath_particles_as_prepositions_068_1.png` | PNG | Oath waw/preposition-like function visual reference. |
| `qac_grammar_review_pack_part2/images/09_preposition_phrase_attachment_004_141.png` | PNG | PP attachment visual reference. |
| `qac_grammar_review_pack_part2/images/10_attachment_to_hidden_implicit_words_004_98.png` | PNG | Hidden hal/sifa attachment visual reference. |
| `qac_grammar_review_pack_part2/images/11_coordinating_conjunction_verbs_080_1.png` | PNG | Verb coordination visual reference. |
| `qac_grammar_review_pack_part2/images/12_coordination_nouns_and_pp_092_3_080_32.png` | PNG | Noun/PP coordination visual reference. |
| `qac_grammar_review_pack_part2/images/13_relative_clauses_103_3.png` | PNG | Relative-clause visual reference. |
| `qac_grammar_review_pack_part2/images/14_lam_of_purpose_subordinate_clause_072_17.png` | PNG | Purpose lam/subordinate clause visual reference. |
| `qac_grammar_review_pack_part3/README_review.md` | Markdown | Useful internal synthesis for conditionals, hal, inna, fa, vocative, exception. |
| `qac_grammar_review_pack_part3/manifest.json` | JSON | Useful manifest for screenshot coverage and hashes; internal only. |
| `qac_grammar_review_pack_part3/images/01_conditional_expressions_temporal_idha_083_30.png` | PNG | Conditional/temporal idha visual reference. |
| `qac_grammar_review_pack_part3/images/02_circumstantial_accusative_hal_100_5_004_143.png` | PNG | Hal visual reference. |
| `qac_grammar_review_pack_part3/images/03_circumstantial_accusative_interrogative_kayfa_089_6.png` | PNG | Interrogative kayfa/hal visual reference. |
| `qac_grammar_review_pack_part3/images/04_accusative_of_purpose_maful_li_ajlihi_080_32.png` | PNG | Accusative of purpose visual reference. |
| `qac_grammar_review_pack_part3/images/05_comitative_object_maful_maahu_005_36_010_71.png` | PNG | Comitative waw/object visual reference. |
| `qac_grammar_review_pack_part3/images/06_alif_interrogative_and_equalization_095_8_002_6.png` | PNG | Hamza interrogative/equalization visual reference. |
| `qac_grammar_review_pack_part3/images/07_inna_and_sisters_accusative_particles_100_6.png` | PNG | Inna and sisters visual reference. |
| `qac_grammar_review_pack_part3/images/08_negative_particles_like_anna_preventive_ma_075_11_079_13.png` | PNG | Negative la/preventive ma visual reference. |
| `qac_grammar_review_pack_part3/images/09_particle_fa_resumption_and_cause_069_16_080_4.png` | PNG | Fa function visual reference. |
| `qac_grammar_review_pack_part3/images/10_vocative_particle_munada_089_27.png` | PNG | Vocative/munada visual reference. |
| `qac_grammar_review_pack_part3/images/11_exceptive_particles_092_20.png` | PNG | Exceptive particle visual reference. |
| `qac_grammar_review_pack_part3/images/12_exceptive_expression_types_rules.png` | PNG | Exception type/rule visual reference. |
| `s41586-024-08548-w.md` | Markdown | Architecture/learning-theory evidence for hidden-state separation and parse-key pedagogy; not Arabic linguistic evidence. |
| `set-of-9-important-arabic-verb-charts_1.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_2.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_3.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_4.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_5.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_6.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_7.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_8.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `set-of-9-important-arabic-verb-charts_9.pdf` | PDF | Verb chart; extraction is glyph-name-heavy, use only as internal visual/checklist material. |
| `verb-tables-supplement--r21.docx` | DOCX | Useful internal weak/geminate verb table pointer; source mentions Qutrub; no direct public import. |

## Useful Concepts Extracted

### QAC grammar review packs

The three QAC packs are directly useful for rich-hover and dogfood design:

- written-token segmentation: proclitic, article, host, suffix pronoun;
- internal POS/function tags: verb, noun, pronoun, preposition, relative,
  vocative, exception, resumption, comitative, cause/result;
- syntax relations: subject/object, passive representative, idafa, sifa,
  badal, tamyiz, PP attachment, hidden hal/sifa attachment, kana/inna
  subject-predicate frames;
- mood/governor decisions: subjunctive, jussive, imperative/prohibition,
  purpose lam, causal fa, comitative waw, conditional particles;
- function-token splits: waw as conjunction/resumption/oath/comitative, fa as
  resumption/coordination/result/cause, ma as negative/relative/preventive or
  laysa-like by context;
- named-entity and concept spans as internal routing metadata, not hover text.

These concepts already match the Fusha guardrails. No contradiction was found
with the current repo policy that external material is internal evidence only.

### GrammarProblems.pdf

The PDF extracts 73 pages / 84,839 text characters. Its useful lesson is not
new public content; it is the existing gate: a grammar answer with wrong i'rab
reasoning is unsafe. This is already represented by:

- `nahw/evals/grammar-problems-derived-eval.jsonl`;
- `nahw/evals/grammar-wrong-reasoning-cases.jsonl`;
- `nahw/procedures/grammar-risk-gate.md`;
- `tools/run_grammar_evals.py`.

No new import is needed unless future Phase 3.25 mining finds unanswered
questions or a new root-cause cluster.

### Verb chart PDFs and verb-table DOCX

The nine verb-chart PDFs are mostly machine-extracted as glyph names, which
makes them poor text sources. They are still useful as visual cross-checks for
verb measures, voice, and person/number/gender tables.

The DOCX cleanly identifies a small weak/geminate verb-table set:

- `وَجَدَ / يَجِدُ`;
- `قَالَ / يَقُولُ`;
- `بَاعَ / يَبِيعُ`;
- `نَامَ / يَنَامُ`;
- `مَشَى / يَمْشِي`;
- `دَعَا / يَدْعُو`;
- `رَضِيَ / يَرْضَى`;
- `أَخَذَ / يَأْخُذُ`;
- `رَدَّ / يَرُدُّ`.

These should inform sarf drills for hollow, defective, hamzated, and doubled
roots. The exact external table wording should not be copied into public
Qamus/curriculum text.

### AMAU Anki decks

The APKG packages contain 1,132 notes/cards across sections 4 through 8. They
are valuable as an internal sequencing signal:

- early sentence habit before abstract grammar;
- prepositions before deeper PP attachment;
- common verbs before derived forms;
- verbal nouns, adjectives, colors, body parts, family, weather, and number
  vocabulary as gradual learner layers;
- repeated "getting used to Arabic" sentence practice.

They should not be imported as public text. The safe reuse is structural:
spacing, ordering, and drill cadence.

### Architecture-only material

`s41586-024-08548-w.md` is a neuroscience article about hippocampal state
machines, hidden-state inference, and decorrelation of initially similar
representations. It is related to Fusha as a conceptual architecture analogy:
surface-near Arabic tokens must be separated into distinct hidden sarf/nahw
states before a hover can be trusted.

Safe use:

- support the parse-key/state-machine doctrine;
- explain why dogfood tranches split false surface-family merges;
- frame curriculum as movement from surface recognition to structured state
  distinctions;
- motivate rich hover metadata as the learned hidden grammar state.

Unsafe use:

- do not cite it for Arabic grammar decisions;
- do not use it as source evidence for Qur'anic token analysis;
- do not put it in public Qamus hover provenance;
- do not copy its wording into learner/public hover text.

## Proposed Skill And Curriculum Changes

| area | proposal | current status |
|---|---|---|
| sarf root/form | Use verb-chart/DOCX concepts to keep weak, hollow, hamzated, doubled, and derived-form rows separate from dictionary infinitives. | Covered by `sarf/procedures/verb-form-and-mood-review.md`; add future drills only when a new failure appears. |
| sarf clitics | Require positive segmentation evidence before splitting b/f/l/k/w/y-looking initial letters. | Covered by `sarf/procedures/clitic-and-host-morphology.md`; no duplicate edit needed. |
| sarf nominal derivatives | Teach maṣdar, participle, adjective, elative, lexical noun, and proper/common collisions as non-verb tokens. | Covered by `sarf/procedures/nominal-derivative-decision.md`; synthesis report adds learner units. |
| nahw particles | Treat waw/fa/ma/la/inna/hamza/vocative/exception particles by function, not surface. | Covered by particle/vocative/grammar-risk procedures; continue dogfood fixtures. |
| nahw PP attachment | Attach preposition phrase to visible or hidden head before rich certification. | Covered by `nahw/procedures/pp-attachment-review.md`; no duplicate edit needed. |
| nahw suffix/referent | Host decides suffix role; referent-sensitive rows need two-vote or pending. | Covered by `nahw/procedures/pronoun-attachment.md`; VN synthesis adds learner units. |
| curriculum | Add a post-VN dogfood synthesis mapping repeated defects to learner units. | Implemented in `curriculum/vn-dogfood-to-curriculum-synthesis-20260627.md`. |
| rich hover | Expand field checklist for rich hover tooltip/parse key. | Already covered by `curriculum/qamus-hover-parse-key-and-color.md`; this audit restates the field set below. |
| architecture | Use hidden-state/decorrelation language to explain why parse keys are grammar-state records rather than flat strings. | Added as conceptual framing only; no Arabic evidence or public provenance role. |

## Proposed Rich-Hover / Parse-Key Fields

A rich hover should be able to expose or internally carry:

- exact `quran:S:A:W` and `wbw:S:A:W`;
- public best gloss plus `src=qamus`, `kind=authored`, `lang=en`;
- Arabic surface and non-destructive visible segment classes;
- `parse_key.key`, summary, and component rows;
- POS: ism/fi'l/harf or more specific class;
- root, lemma/headword, and wazn/pattern where certified;
- verb form/measure, voice, aspect, mood, person, number, gender;
- noun number, gender, definiteness, state, case, derivative type;
- clitic/proclitic/article/host/suffix segmentation;
- attached pronoun role, host type, and referent status;
- particle/preposition function and governance;
- PP attachment, idafa, sifa, hal, exception, vocative, condition, or other
  nahw relation when it controls the hover;
- linked Qamus entry/sense or no-entry function-token rationale;
- token-only override status and affected-sibling preview;
- blocker and exact next gate when unresolved;
- learner-facing explanation that preserves visible grammar.

## Conflicts And No-Op Reasons

- QAC images: use internal concepts only; no QAC labels, screenshots, or
  wording in public hovers.
- AMAU APKG decks: useful for learning-sequence design, but card text/audio and
  deck content are external; do not import public wording.
- Verb-chart PDFs: useful visually, but text extraction is glyph-name-heavy; do
  not treat extracted text as authoritative.
- DOCX verb list: useful as weak/geminate examples, but examples should be
  rewritten with Qamus/Qur'anic tokens when promoted to public drills.
- Nature markdown: architecture/learning-theory support only; no Arabic
  evidence, public provenance, copied wording, or grammar-decision authority.
- No new sarf/nahw procedure edit is required solely by this folder audit,
  because the relevant procedure gaps were already updated by the dogfood
  tranche series. Future edits should be driven by a concrete failing row or
  validator, not by duplicating this report.

## Follow-Up

Use this audit with
[`../../curriculum/vn-dogfood-to-curriculum-synthesis-20260627.md`](../../curriculum/vn-dogfood-to-curriculum-synthesis-20260627.md)
before any final hover-decision apply plan. The folder improves the teaching
and review substrate; it does not authorize live apply.
