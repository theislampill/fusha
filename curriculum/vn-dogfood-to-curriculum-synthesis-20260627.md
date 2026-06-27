# VN Dogfood To Curriculum Synthesis - 2026-06-27

Status: repo-only synthesis after completion of VN-00 through VN-20. No live
Qamus data, WBW artifact, service, mirror, or hover decision ledger was
changed.

Use this file to turn the verb/noun dogfood series into learner-facing units.
It does not replace the tranche reports or skill procedures; it indexes the
repeatable lessons that a teacher, tutor agent, or future rich-hover reviewer
should reuse.

## Evidence Basis

Git log was used only as the index. Canonical content came from:

- `qamus/reports/full-corpus-dogfood-vn00-20260627.md` through
  `qamus/reports/full-corpus-dogfood-vn20-20260627.md`;
- committed VN inventory and skill-impact samples under `qamus/examples/`;
- changed sarf/nahw procedures and eval fixtures cited by each tranche;
- production-bug lesson samples;
- controller tables inside each report.

Aggregate checked from committed reports:

| item | count |
|---|---:|
| VN reports | 21 |
| Qamus verb/noun entries covered | 1,992 |
| live hover rows reviewed in VN reports | 24,888 |
| `known_defect` rows | 21 |
| `populated_uncertified` rows | 20,267 |
| `token_only_override` rows | 4,432 |
| `pending/blocker` rows | 168 |

Repeated issue counts from reports with explicit issue tables:

| issue class | count |
|---|---:|
| `missing_rich_renderer_segments` | 3,615 |
| `surface_family_requires_token_only_override` | 884 |
| `suffix_or_attached_pronoun_requires_visible_accounting` | 679 |
| `finite_verb_dictionary_gloss_or_form_review` | 517 |
| `article_definiteness_requires_rich_segments` | 387 |
| `preposition_or_attached_relation_requires_nahw_review` | 221 |
| `component_only_candidate_no_whole_token_propagation` | 181 |
| `verb_entry_nominal_derivative_or_lexical_noun_pos_review` | 181 |
| `noun_hover_may_leak_verb_infinitive` | 14 |

These are dogfood movements and review routes, not live applies.

## Instructional Units

### 1. Finite Verbs Are Not Dictionary Entries

Defect class:
`finite_verb_dictionary_gloss_or_form_review`

Qur'anic examples:

- `قَالُوا`
- `ظَلَمُونَا`
- `وَيُعَلِّمُكُمُ`
- `ثَقِفْتُمُوهُمْ`
- `فَأَهْلَكْنَاهُمْ`
- `لِيَسْحَتَكُم`
- `يُوبِقْهُنَّ`

Explanation:

A finite verb token carries form, voice, aspect, person, number, gender, and
often a subject or object suffix. A dictionary-like hover such as "to say",
"to wrong", "to teach", or "to destroy" may be a useful entry gloss, but it is
not the token contribution unless it preserves finite morphology.

Common learner error:

Seeing a root-family entry and reading every occurrence as an infinitive.

Sarf procedure:
[`../sarf/procedures/verb-form-and-mood-review.md`](../sarf/procedures/verb-form-and-mood-review.md)

Nahw procedure:
[`../nahw/procedures/pronoun-attachment.md`](../nahw/procedures/pronoun-attachment.md)
when a suffix object or referent affects wording.

Drill:
[`drills/hover-composition-and-routing.md`](drills/hover-composition-and-routing.md)
and [`../sarf/drills/verb-measures.md`](../sarf/drills/verb-measures.md)

Regression/eval fixture:
[`../sarf/evals/false-clitic-split-eval.jsonl`](../sarf/evals/false-clitic-split-eval.jsonl)
and [`../nahw/evals/suffix-pronoun-eval.jsonl`](../nahw/evals/suffix-pronoun-eval.jsonl)

Hover correctness improvement:

The hover must show token action, not entry infinitive. The rich layer should
surface form/voice/person and any visible suffix.

Renderer support:

Needed for verb stem + suffix pronoun colors and parse-key rows.

Remaining gate:

Exact-address review; two-vote when suffix referent, mood, or context changes
the English.

### 2. Suffix Pronouns Must Survive The Host

Defect class:
`suffix_or_attached_pronoun_requires_visible_accounting`

Qur'anic examples:

- `يَسْـَٔلُكَ`
- `جَادَلُوكَ`
- `مَنَاكِبِهَا`
- `بَيْنَهُمْ`
- `أَحَدُهُمْ`
- `يَوْمِكُمْ`
- `أَطْرَافِهَا`

Explanation:

The same suffix can be an object on a verb, a possessor on a noun, or the
object of a preposition. Host POS decides the role; context may decide the
referent. A hover that can be read without the suffix is not learner-ready.

Common learner error:

Treating every attached pronoun as "his/her/their" or hiding it under the
host gloss.

Sarf procedure:
[`../sarf/procedures/suffix-pronoun-state.md`](../sarf/procedures/suffix-pronoun-state.md)

Nahw procedure:
[`../nahw/procedures/pronoun-attachment.md`](../nahw/procedures/pronoun-attachment.md)

Drill:
[`../sarf/drills/clitic-and-host-morphology.md`](../sarf/drills/clitic-and-host-morphology.md)

Regression/eval fixture:
[`../nahw/evals/suffix-pronoun-eval.jsonl`](../nahw/evals/suffix-pronoun-eval.jsonl)

Hover correctness improvement:

Learners see why `يَسْـَٔلُكَ` contributes "ask you" and why `مَنَاكِبِهَا`
is host plus an attached referent.

Renderer support:

Needed for separate `qg-pronoun` segment and tooltip breakdown row.

Remaining gate:

Two-vote when referent-sensitive, token-only when siblings differ by suffix,
case, or context.

### 3. Component Evidence Is Below Whole-Token Certification

Defect class:
`component_only_candidate_no_whole_token_propagation`

Qur'anic examples:

- `وَٱلشَّمْسُ`
- `وَٱلْقَمَرُ`
- `وَٱلنُّجُومُ`
- `وَٱلْجِبَالُ`
- `وَٱلشَّجَرُ`
- `بِٱلْمَعْرُوفِ`
- `فَأَلْهَمَهَا`

Explanation:

Rich WBW segment evidence can identify pieces such as waw, article, host, and
suffix. That evidence helps the reviewer, but it does not certify the whole
token or allow parse-family propagation.

Common learner error:

Believing that "and + the trees" is complete just because it visibly names
pieces.

Sarf procedure:
[`../sarf/procedures/clitic-and-host-morphology.md`](../sarf/procedures/clitic-and-host-morphology.md)

Nahw procedure:
[`../nahw/procedures/particle-function-decision.md`](../nahw/procedures/particle-function-decision.md)

Drill:
[`drills/parse-key-and-color-layer.md`](drills/parse-key-and-color-layer.md)

Regression/eval fixture:
[`../sarf/evals/false-clitic-split-eval.jsonl`](../sarf/evals/false-clitic-split-eval.jsonl)

Hover correctness improvement:

The public hover can stay concise, but the rich layer must preserve each
visible piece and gate the function before sibling propagation.

Renderer support:

Required for non-destructive colored Arabic segments and matching tooltip rows.

Remaining gate:

Component-only rows are blockers until whole-token parse and function agree.

### 4. Prepositions And PP Attachment Are Part Of The Meaning

Defect class:
`preposition_or_attached_relation_requires_nahw_review`

Qur'anic examples:

- `بِبَدْرٍ`
- `بِبَكَّةَ`
- `بِذُنُوبِهِمْ`
- `بِغَيْظِكُمْ`
- `لِلْمَلَٰٓئِكَةِ`
- `لِتُضَيِّقُوا۟`

Explanation:

Attached bā', lām, kāf, and similar particles can govern a host, change mood,
or create a PP whose attachment decides the English. A host-only hover drops
visible grammar.

Common learner error:

Reading the host noun or place name and ignoring the relation carried by the
preposition.

Sarf procedure:
[`../sarf/procedures/clitic-and-host-morphology.md`](../sarf/procedures/clitic-and-host-morphology.md)

Nahw procedure:
[`../nahw/procedures/pp-attachment-review.md`](../nahw/procedures/pp-attachment-review.md)
and
[`../nahw/procedures/preposition-pronoun.md`](../nahw/procedures/preposition-pronoun.md)

Drill:
[`../nahw/drills/idafa-and-jar-majrur.md`](../nahw/drills/idafa-and-jar-majrur.md)

Regression/eval fixture:
[`../nahw/evals/particle-function-eval.jsonl`](../nahw/evals/particle-function-eval.jsonl)

Hover correctness improvement:

Rows like `بِبَدْرٍ` cannot teach only "Badr"; they must preserve "at/by/in
Badr" according to context and attachment.

Renderer support:

Needed for preposition + host + suffix rows.

Remaining gate:

Two-vote when attachment, governor, or particle function controls wording.

### 5. Nominal Tokens Must Not Leak Verb Glosses

Defect class:
`verb_entry_nominal_derivative_or_lexical_noun_pos_review`

Qur'anic examples:

- `مَّخْتُومٍ`
- `مِثْلُ`
- `وَعْدُ`
- `ٱلسَّبْتِ`
- `وِفَاقًا`
- `ٱلْمُخْبِتِينَ`
- `مُعَلَّمٌ`

Explanation:

A token may share a root with a verb entry while being a noun, maṣdar,
participle, adjective, elative, place noun, or lexical noun. POS, pattern,
case, and context decide the hover shape.

Common learner error:

Turning every root-family surface into "to X".

Sarf procedure:
[`../sarf/procedures/nominal-derivative-decision.md`](../sarf/procedures/nominal-derivative-decision.md)

Nahw procedure:
[`../nahw/procedures/referent-context.md`](../nahw/procedures/referent-context.md)
when sense or referent is context-sensitive.

Drill:
[`../sarf/drills/nominal-derivatives.md`](../sarf/drills/nominal-derivatives.md)

Regression/eval fixture:
[`../sarf/evals/nominal-derivative-error-eval.jsonl`](../sarf/evals/nominal-derivative-error-eval.jsonl)

Hover correctness improvement:

The learner sees the token as nominal/adjectival rather than a disguised verb
definition.

Renderer support:

Useful for noun/adjective/derivative class labels and case/state rows.

Remaining gate:

Token-only or human review when same root/surface supports multiple senses.

### 6. Same Family Does Not Mean Same Hover

Defect class:
`surface_family_requires_token_only_override`

Qur'anic examples:

- `قَوَارِيرَ` / `قَوَارِيرَا۠`
- `سَيْنَآءَ` / `سِينِينَ`
- `أَحَدُهُمْ` / `أَحَدَكُم`
- `ٱلْأَنفَالِ` / `ٱلْأَنفَالُ`
- `يَوْمُكُمُ` / `يَوْمِهِمْ`

Explanation:

Exact token identity outranks surface family, parse family, and root family.
Siblings can differ by case, suffix, referent, article, function, or i'rab
role.

Common learner error:

Learning one surface and assuming every similar-looking token carries the same
hover.

Sarf procedure:
[`../sarf/procedures/root-decision.md`](../sarf/procedures/root-decision.md)
for strict surface/root checks.

Nahw procedure:
[`../nahw/procedures/token-only-overrides.md`](../nahw/procedures/token-only-overrides.md)

Drill:
[`../sarf/drills/homograph-regressions.md`](../sarf/drills/homograph-regressions.md)

Regression/eval fixture:
[`../nahw/evals/irab-polysemy-eval.jsonl`](../nahw/evals/irab-polysemy-eval.jsonl)

Hover correctness improvement:

Prevents family-wide over-propagation and keeps exact-address repairs from
silently altering unrelated rows.

Renderer support:

Useful for token-only badge/status and affected-sibling preview.

Remaining gate:

Token-only two-vote, never blind surface propagation.

### 7. Rich Renderer Is A Learning Requirement, Not Cosmetic Polish

Defect class:
`missing_rich_renderer_segments`

Qur'anic examples:

- All VN tranches emitted rows where the current hover is populated but lacks
  learner-visible segmentation.
- Repeated examples include suffix-bearing verbs, article-bearing nouns,
  preposition-host rows, and nominal derivative rows.

Explanation:

A string can be correct enough to read and still fail as a teaching hover. A
rich-certified hover must expose segmentation, parse key, grammar role,
entry/sense or function rationale, and learner-facing explanation.

Common learner error:

Trusting the English gloss without seeing how the Arabic token produced it.

Sarf procedure:
[`../sarf/procedures/clitic-and-host-morphology.md`](../sarf/procedures/clitic-and-host-morphology.md)

Nahw procedure:
[`../nahw/procedures/grammar-risk-gate.md`](../nahw/procedures/grammar-risk-gate.md)

Drill:
[`drills/parse-key-and-color-layer.md`](drills/parse-key-and-color-layer.md)

Regression/eval fixture:
[`../qamus/reports/morphosyntax-token-contract.md`](../qamus/reports/morphosyntax-token-contract.md)
and `tools/validate_morphosyntax_token_metadata.py`

Hover correctness improvement:

Distinguishes visible hover presence from grammatical dogfood completion.

Renderer support:

Required.

Remaining gate:

Renderer metadata backfill plus browser/DOM checks before live claim.

## Source Folder Audit Link

The post-VN audit of the owner-provided local `sarfnahw` source folder found useful internal
materials for the same units: QAC grammar visuals for syntax and segmentation,
verb charts/DOCX for weak/geminate/derived-form tables, AMAU decks for staged
learner sequencing, and GrammarProblems for grammar-risk gating. See
[`../qamus/reports/sarfnahw-source-audit-20260627.md`](../qamus/reports/sarfnahw-source-audit-20260627.md).

## No-Op Reasons

- Renderer-only rows do not automatically require sarf/nahw text edits when the
  relevant procedure already exists. They route to rich-hover metadata.
- External source files do not authorize public wording. They inform procedure,
  sequence, and internal evidence only.
- Pending/blocker rows stay pending unless exact-address, row-level, two-vote,
  source-triangulation, and rich-certification gates pass.
- This synthesis does not make any row live-applyable.

## Teaching Loop

For future batches, keep the loop explicit:

`production failure -> typed graph diagnosis -> sarf/nahw procedure update or no-op reason -> regression fixture -> learner explanation -> drill -> validator -> future closure batch`

The learner-facing version is:

`written token -> visible pieces -> sarf host class -> nahw function/attachment -> entry/sense or function rationale -> safe hover or named pending reason`.
