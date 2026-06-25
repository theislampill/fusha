---
name: nahw
description: Decide how SENTENCE CONTEXT changes the correct gloss of an Arabic token — particles, prepositions, pronouns, negation, conditionals, relatives, iḍāfa, jar-majrūr, case/mood, referent. Use when sarf alone cannot pick the sense, when a particle is multi-function, or when a gloss is lexically valid but contextually wrong. Encodes the exact context mistakes fought in qamus-highlight.
---

# Nahw (syntax) skill

Sarf finds the form; **nahw decides what it means here**. A gloss can be perfectly lexical and still wrong for
its āyah. This skill is operational, not a grammar primer: it tells you when context **resolves** a sense and
when it forces **pending**.

> ⚠️ **Grammar-safety (GrammarProblems eval gate).** General LLM confidence is **not evidence**; grammar decisions
> require the sarf/nahw evidence ladders. A **correct answer with wrong iʿrāb reasoning is unsafe** — do not ship
> it. An independent study put a general LLM at ~33% on Arabic naḥw (worst on iʿrāb/deep/essay), so iʿrāb,
> case/mood, istithnāʾ, لا النافية للجنس, ambiguous iḍāfa/jar-majrūr, multi-sense, and referent-sensitive
> decisions require **two independent checks agreeing on conclusion AND reason**. Uncertain naḥw → pending, never
> a public gloss. Gates: [`evals/grammar-decision-gates.json`](evals/grammar-decision-gates.json); policy:
> [`qamus/reports/grammar-risk-policy.md`](../qamus/reports/grammar-risk-policy.md); drill:
> [`drills/grammar-reasoning-safety.md`](drills/grammar-reasoning-safety.md).

## Procedures (progressive disclosure — load the one you need)
This SKILL is the fast context gate + contract; each step is a short procedure. **Open only what the task needs.**
- [`procedures/particle-decision.md`](procedures/particle-decision.md) — content-letter harakah; مَن/مِن، لَمْ/لِمَ.
- [`procedures/particle-function-decision.md`](procedures/particle-function-decision.md) — pick a particle's FUNCTION in context (مَا/إِنْ/لَا/فاء/واو/لام/أَلَا-أَلَّا); see `references/particle-functions.md`.
- [`procedures/irab-teaching-diagnosis.md`](procedures/irab-teaching-diagnosis.md) — produce the iʿrāb (role·case/mood·governor) or diagnose the learner/draft error; answer AND reasoning.
- [`procedures/preposition-pronoun.md`](procedures/preposition-pronoun.md) — jar-majrūr wording by referent; إِلَيْنَا guard.
- [`procedures/negation.md`](procedures/negation.md) — لَمْ/لَنْ/لَا/مَا/لَيْسَ scope → tense/polarity.
- [`procedures/relative-interrogative.md`](procedures/relative-interrogative.md) — مَا/مَن/أَيّ relative vs interrogative vs negation.
- [`procedures/conditionals.md`](procedures/conditionals.md) — إِنْ/إِذَا/لَوْ + the إِنْ "if" vs إِنَّ "indeed" collision.
- [`procedures/idafa-jar-majrur.md`](procedures/idafa-jar-majrur.md) — construct relationship + definiteness.
- [`procedures/irab-case-mood.md`](procedures/irab-case-mood.md) — case/mood reading → why it forces the two-vote gate.
- [`procedures/referent-context.md`](procedures/referent-context.md) — referent guard, divine-Name vs attribute, contronyms.
- [`procedures/grammar-risk-gate.md`](procedures/grammar-risk-gate.md) — the GrammarProblems gate (answer AND reason).
- [`procedures/hover-application.md`](procedures/hover-application.md) — syntax-sensitive tokens → precise pending, not a one-word gloss.
- [`procedures/bulk-source-triangulation.md`](procedures/bulk-source-triangulation.md) — route bulk pending-table rows by context risk before any hover decision.
- [`procedures/qamus-entry-authoring.md`](procedures/qamus-entry-authoring.md) — nahw evidence → function-word/construction entry candidate.
- [`procedures/corpus-to-qamus.md`](procedures/corpus-to-qamus.md) — the nahw half of the corpus→Qamus pipeline.

**Rules** (`rules/`): particle-context, preposition-pronoun, negation, irab-safety-gates, grammar-problems-gates,
two-vote-required-rules, context-sense, **state-transition-rules** (the syntax side of the
[language state machine](../qamus/reports/language-state-machine-report.md): مَن/مِن، لَمْ/لِمَ، أَن/إِن/أَنَّ/إِنَّ
forbidden collisions). **Evals** (`evals/`): grammar-problems-matrix, **grammar-problems-derived-eval.jsonl**
(≥72 cases, run via [`tools/run_grammar_evals.py`](../tools/run_grammar_evals.py) +
[`tools/grade_grammar_reasoning.py`](../tools/grade_grammar_reasoning.py)), nahw-state-machine-eval, hover-context-eval,
**`particle-function-eval.jsonl`** (each particle × its functions, machine-testable),
**`irab-polysemy-eval.jsonl`** (per-loc iʿrāb regressions: وما/أَلَّا/فما/عاد/جنّة/أمّة/يقدر/حليم).
**References** (`references/`): particles, idafa, jar-majrur, irab-case-mood, quranic-nahw-notes,
**particle-functions** (closed-class function map), **irab-teaching-map** (zero→fluency iʿrāb spine),
**learner-error-remediation** (syntax failure modes → fix).
**Curriculum** (`curriculum/`): `zero-to-fluency-nahw.md` + beginner/intermediate/advanced drills;
**`drills/particle-disambiguation.md`** + **`drills/irab-case-mood.md`**.

## 1. Purpose
Choose the context-correct gloss (or an honest pending) for tokens whose meaning depends on the sentence:
particles, prepositions+pronouns, negation/mood, contronyms, multi-sense roots, referents, iḍāfa.

## 2. Input contract
A token + `quran_ref`/`token_loc` + the surrounding tokens (and, if known, the sarf output object). For a
Qurʾānic token, you MAY consult any **available source adapter** for iʿrāb/role evidence (see `sources/README.md`)
— optional, internal-only, never named here, never public, and never outranking the Qamus entry or the reasoning
gate.

## 3. Output contract
```json
{
  "quran_ref": "28:82", "token_loc": "28:82:7", "surface_ar": "وَيَقْدِرُ",
  "phrase_context": "verbal phrase", "syntactic_role": "verb",
  "nearby_tokens": ["اللَّهَ","يَبْسُطُ","الرِّزْقَ","لِمَن","يَشَاءُ","وَيَقْدِرُ"],
  "particle_context": ["و"], "governing_particle": null, "case_or_mood_signal": "indicative_or_unknown",
  "candidate_glosses": ["ordains","restricts"], "contextual_choice": "restricts",
  "decision": "resolved | pending", "reason": "paired with يبسط الرزق; contrast indicates restricts",
  "confidence": "medium", "allowed_for_hover": true
}
```

## 4. Particle decision ladder
Read the **content-letter harakah** (not the first letter): مَن(fatḥa "who") vs مِن(kasra "from", incl. وَمِنَ);
لَمْ vs لِمَ; أَنْ vs إِنَّ; أَنَّى("how") vs أَنِّي("that I"); إِلَّا vs لَا; مَا = negation/relative/interrogative by
context. **Particles are diacritic- AND context-sensitive.**

## 5. Preposition decision ladder
The same preposition renders differently by referent: بِهِ "with/by/in it"; لَهُ "for/to him, belongs to him";
عِنْدَ "with/near/in the sight of"; إِلَيْنَا "to us" (jar-majrūr — **not** root ل ي ن "soft").

## 6. Pronoun / suffix handling
Attached pronouns ـه/ـها/ـهم/ـكم/ـنا change the wording but not the head sense; do not let a suffix invent a
new stem (and never confuse a tanwīn-alef with the pronoun نا).
For verbs, attached object pronouns are part of the user-visible meaning. Preserve the subject agreement and the
object referent/person/number/gender where material: `جَادَلُوكَ` is not "to argue; dispute", but a plural subject
arguing/disputing with "you" masculine singular in context.

## 7. Negation handling
لَمْ → past negation + jussive; لَنْ → future negation; لَا → negation / prohibition / "no"; مَا → negation or
other roles. **A hover gloss must respect the governing negative if it changes the meaning.**

## 8. Conditionals & relative pronouns
مَن / مَا / إِنْ / إِذَا can be conditional or relative; the apodosis (jawāb) signals which. Distinguish from the
homographic prepositions مِن / and the temporal لَمَّا.

## 9. Iḍāfa & jar-majrūr
A genitive construction or preposition+noun changes gloss wording; gloss the **phrase role**, not just the
lexeme.
Attached باء on a majrūr noun must carry the bāʾ function in the hover. If the entry is بِـ, host-only glosses like
"peace" for بِسَلَـٰمٍ or "Badr" for بِبَدْرٍ are incomplete; use the context sense ("with peace", "at Badr", etc.)
or leave a precise pending when the bāʾ function is not certified.
The visible hover is the contract: do not rely on a hidden `pre` field to teach a relation that the tooltip's best
gloss omits. A token such as `بِسَلَـٰمٍ` needs the preposition inside the best hover text when that is what the page
shows.

## 10. Verb–subject–object context
The object/construction can fix a polysemous verb: أَتَى = come/bring/give/commit by object; يَقْدِرُ in a rizq
context contrasting يَبْسُط = "restricts".

## 11. Nominal-sentence context
Mubtadaʾ/khabar with no verb; a "to be" verb is implied, not lexical.

## 12. Referent / context guard
Do **not** propagate: a divine-Name sense onto a human attribute (حَلِيمٌ for Ibrāhīm = "forbearing", not a
Name); a Prophet's proper name onto a common adjective (صَٰلِحًا); a proper-noun sense onto an ordinary noun; an
ordinary verb gloss onto a proper noun.

## 13. When to resolve vs pending
Resolve when the construction uniquely fixes the sense. Otherwise emit
`pending: context-sensitive; needs nahw review` with the precise blocker.

## 14. How to author a qamus grammatical gloss
Write a concise, original English rendering of the **function in context** (e.g. مَن→"whoever", وَمِنَ→"and from",
بِهِ→"in it"); keep src=qamus/authored; record `informed_by` internally only.

## 15. How to update qamus-highlight pending reasons
Map this decision to: `pending_reason`, an authored-gloss candidate, a `sense_quarantine`, a source-address
note, or the review queue.

## 16. Regression examples
`examples/function-word-decisions.jsonl` + `examples/ayah-context-decisions.jsonl` — real qamus-highlight cases.

## Production finding (hover polish — وَمَا and attached باء)
`وَمَا` is one Qur'anic word token but two syntactic pieces: wāw + mā. Do not count it as two corpus word tokens,
but do decompose it for the hover gloss. The mā may be relative/maṣdariyyah, interrogative, or negative; use
iʿrāb/context evidence before authoring ("and by the One Who", "and not", "and no" are different decisions).
For attached بِـ, the hover must include the preposition's role, not only the governed noun.
For oath waw (واو القسم), the hover must include the oath relation; a governed noun like وَالتِّينِ is not merely
"fig". For attached وَبِـ before a governed noun, preserve both the coordination/resumption and the bāʾ relation
where they are certified, e.g. وَبِالنَّجْمِ as "and by/through the star(s)", not a pending host-only token.
For bāʾ plus possessive suffixes, include both the prepositional relation and the pronoun contribution: `بِذُنُوبِهِمْ`
is not "Sin.", and `بِذُنُوبِكُم` is not a generic suffix pending when iʿrāb confirms bāʾ + majrūr noun + possessive
suffix.

## Production finding (morphosyntax contract — particles, phrases, clauses)
Before authoring a hover for a function-bearing token, classify the syntactic function, not only the surface
particle:

- `و` may be ordinary coordination, oath-preposition, or comitative wāw. Oath and comitative uses must surface
  their contribution; do not collapse them into a bare "and" or a host-only noun hover.
- `ف` may be resumption, coordination, result in a conditional answer, supplemental, or cause. Cause `ف` can govern
  a following imperfect verb into the subjunctive and must not be treated like ordinary "and/then".
- `أ`/hamza may be interrogative or equalization. Equalization hamza contributes "whether" and is not an ordinary
  question.
- `إن` and sisters take `ism_inna` and `khabar_inna`; negative `لا` can act like `أن`; preventive `ما` can block an
  accusative particle's normal case effect.
- Jar-majrūr has two layers: the preposition governs a genitive nominal, and the resulting PP attaches to a verb,
  nominal, hidden hāl, hidden ṣifa, clause, or other explicit head.
- Relative pronouns, subordinating conjunctions, purpose lām, and temporal conditionals must record their clause
  relation (`relative_clause`, `subordinate_clause`, `purpose_clause`, `temporal_condition`, `answer_of_condition`).
- Hāl, interrogative hāl, mafʿūl li-ajlih, and mafʿūl maʿahu are adverbial accusatives; the hover may be concise,
  but the parse record must preserve case, role, and attachment.
- Vocative particles and exceptive particles must preserve the governed noun structure; for exceptions record the
  mustathnā minhu, mustathnā, and whether the construction is muttaṣil, munqaṭiʿ, or mufarragh.

---

## The six nahw principles (encode these)
1. **Particles are context-sensitive** — handle مَن/مِن، لَمْ/لِمَ، أَنْ/إِنَّ، أَنَّى/أَنِّي، إِلَّا/لَا، مَا by diacritic **and**
   context.
2. **Jar-majrūr & iḍāfa change wording** — بِهِ، لَهُ، عِنْدَ، إِلَيْنَا render by referent/role.
3. **Negation & mood matter** — respect لم/لن/لا/ما's effect on the governed verb.
4. **Context resolves contronyms & multi-sense roots** — يَقْدِرُ→"restricts" in rizq context; حذّر→"warn";
   أتى by object; ملك/مُلك/مَلَك by vowels/context.
5. **Referent matters** — never carry a Name/Prophet/proper-noun sense to a common word, or vice-versa.
6. **Prefer phrase-aware pending over a wrong one-word gloss.**

## How nahw feeds the rest
- **Qamus entry authoring/repair:** better sense selection, usage notes, teacher notes.
- **Hover-gloss:** context-aware sense; distinguishes مَن/مِن، لَم/لِمَ، أن/إن; avoids referent errors; honest pending.
- **Pending-reason refinement:** turns vague pendings into precise, reviewable reasons.
- **Catalogues:** classifies particle/construction candidates from Nawawī40/Ṣaḥīḥayn.

## Do not resolve; mark pending (examples)
- A bare لا before a noun vs a verb (لا النافية للجنس vs verbal negation) when the next token's POS is unknown.
- مَا with no clear negation/relative/interrogative signal.
- A multi-sense root with no disambiguating object/referent in range.

## Production finding (P4/P5)
A surface-keyed gloss is safe **only with the harakāt guard in place**: وَمِنَ "and from" (kasra on the mīm,
even under the و proclitic) is the preposition and may be glossed, while وَمَن "and whoever" (fatḥa) must not
inherit it — the content-letter harakah, read by the guard, keeps the two apart across all occurrences.

## References (SN ingest)
The corpus distillation added four operational references and a negation rule file:
- [`references/particles.md`](references/particles.md) — the closed particle/preposition/pronoun inventory + the
  content‑letter‑harakah rule.
- [`references/jar-majrur.md`](references/jar-majrur.md) — preposition+pronoun rendering by referent; the
  إِلَيْنَا ≠ ل‑ي‑ن hard guard.
- [`references/idafa.md`](references/idafa.md) — genitive constructs; gloss the relationship + definiteness.
- [`references/irab-case-mood.md`](references/irab-case-mood.md) — case/mood endings; **لَمْ + jussive → past
  meaning**; quarantine inflection families together.
- [`rules/negation-rules.json`](rules/negation-rules.json) — لَمْ/لَنْ/لَا/مَا/لَيْسَ scope and gloss effect.

## Production finding (SN ingest — negation scope & function-word inventory)
Two additions from the verb‑charts + AMAU corpus:
1. **The governing negative sets the tense, not the verb's surface form.** لَمْ over a present‑tense form yields a
   **past** meaning ("did not"); لَنْ negates the future ("will never"). Resolve the لَمْ/لِمَ homograph (harakāt)
   first, then apply the negation effect — never gloss the bare surface tense under a negative.
2. **The corpus confirms a stable function‑word inventory with English glosses** (prepositions قَبْلَ/بَعْدَ/
   أَمَامَ/فَوْقَ/تَحْتَ/وَرَاءَ, pronouns هُمَا/أَنْتُمْ/أَنْتُمَا, particles). These are safe hover candidates **only**
   through the content‑letter‑harakah guard — a surface key alone still cannot separate مَن/مِن، لَمَّا/لِمَا.

## Production finding (PP1 — particle p001–p100 proofing pilot)
Proofing all 100 particle entries' example āyāt (219 āyāt, 3,757 tokens) confirmed the proving‑ground value:
the function‑word tops in particle āyāt (وَمَآ, لَمْ, أَمْ, وَإِن, وَمَن) are **correctly pending** (homograph /
multi‑function — مَا alone has negation/relative/interrogative/maṣdariyyah readings), while the content tokens are
authorable. 26 content glosses were certified+applied (+141 occ → 70.76%). New **person/POS homograph** classes
the key‑aware 2‑vote caught and kept pending: هَدَيْنَا "We guided" ↔ هَدَىٰنَا "He guided us" (subject person);
حَرَّمَ "forbade" (verb) ↔ حُرُم "sacred" (noun); وَلَدٌ "child" (noun) ↔ وَلَدَ "begot" (verb). Lesson: the live
`norm_strict` key drops the person/voice/POS‑distinguishing harakāt, so a same‑key set must be one *word AND one
person/POS* before a surface gloss is safe.
