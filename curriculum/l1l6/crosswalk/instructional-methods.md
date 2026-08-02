# Instructional-method crosswalk (L1–L6 → repo tutoring surfaces)

Extracted from the 226-lesson corpus by structural analysis (section
inventories in `registry/lessons.jsonl`); each method is mapped to the
repository surface that can consume it. Methods are pedagogy, not linguistic
authority; adopting a method never changes a decision gate.

| # | Method (as practised in the corpus) | Corpus evidence (structural) | Existing repo surface | Adoption state |
|---|---|---|---|---|
| M1 | **Staged explanation** — one concept per `###` section, ordered easy→hard inside a lesson, lessons ordered inside modules | 1,740 concept sections over 226 lessons; strict L→M→lesson ordering | `curriculum/zero-to-fluency-roadmap.md`, `sarf/curriculum/`, `nahw/curriculum/` | repo has level docs but no per-concept staging graph → `graph/concept-edges.jsonl` supplies it |
| M2 | **Narrative-embedded grammar** — a continuous 9th-century Baghdad story carries every new form in context before analysis | 315 reading passages with translations, recurring cast across all six levels | none (repo drills are item-based) | candidate method; usable by the tutor for context-first presentation without committing story prose |
| M3 | **Pattern recognition before rules** — tables of same-pattern words precede the pattern's formal statement | pattern-reference tables (e.g. "Complete Pattern Reference Table" sections) | `curriculum/drills/root-pattern-practice.md`, `tools/fusha_paradigm_generate.py` | aligned; paradigm generator can drive M3 drills directly |
| M4 | **Contrastive examples** — minimal pairs and "X vs Y" sections (67 ambiguity concept nodes) | contrast headings across levels (صرف vs نحو, مَن vs مِن families) | `sarf/rules/homograph-quarantines.json`, `nahw/rules/state-transition-rules.json` forbidden tables | strong fit: contrast sets restate into quarantine/prepass fixtures (TP-CURR-MISTAKES-TO-FIXTURES) |
| M5 | **Common-error diagnosis** — 199 lessons carry a Common Mistakes section (wrong form → why wrong → correction) | 199 mistake sections (`registry/lessons.jsonl` counts) | `curriculum/drills/dogfood-error-remediation-index.md`, `tools/fusha_learner_feedback.py` (KC violation records) | direct feed: restated mistake patterns become learner-error KC entries and adversarial fixtures |
| M6 | **Guided analysis** — worked iʿrāb-style walkthroughs before independent practice (L4+) | analysis sections in L4–L6 grammar lessons | `nahw/procedures/irab-case-mood.md`, `tools/grade_grammar_reasoning.py` | walkthrough steps map to reason-key sequences; NEVER bypasses the two-vote gate |
| M7 | **Production exercises** — quizzes ask the learner to produce/choose forms | 3,096 quiz questions (NO answer keys published) | `curriculum/drills/keys/*.keys.jsonl` pattern | blocked until keys pass review (TP-CURR-QUIZ-KEY-REVIEW); an answer-visible or keyless item is never an eval |
| M8 | **Cumulative review** — later lessons re-invoke earlier concepts | concept-revisit edges in `graph/concept-edges.jsonl` | `curriculum/mastery-checkpoints.md`, `curriculum/placement-test.md` | revisit edges give the checkpoint builder a real interleaving schedule |
| M9 | **Adaptive remediation** — mistake sections cross-reference the lesson that taught the violated rule | mistake sections + prerequisite ordering | `curriculum/tutor-runtime-routing.md`, `tools/fusha_cefr_gate.py` | routing table can key on concept_ids; CEFR gate already withholds iʿrāb terminology below C1 |
| M10 | **Passage-level application** — grammar immediately re-encountered in the next passage; classical excerpts (Ṭabarī, poetry) from L3 | passage counts + quranic_classical concept nodes (24) | `curriculum/quran-reading-path.md`, `curriculum/hadith-reading-path.md`, rich-hover teaching order (`docs/qamus/particle-projection-contract.md`) | the rich-hover 13-item teaching order is the repo's passage-level surface; lesson claims reach it only via candidate links + certification |

## Boundary

- Methods M1–M10 are transferable **as method**; the corpus's linguistic
  content transfers only through the claim ledger with qualification statuses.
- The corpus has **no abstention pedagogy** (xn-10): every tutor adoption must
  wrap lesson-derived answers in the gate ladder
  (`tools/validate_linguistic_decisions.py`); hints never downgrade a gate.
- No story prose, passage text or quiz bodies leave private custody;
  method adoption uses structure, ordering and restated patterns only.
