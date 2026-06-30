---
name: sarf
description: Reason about an Arabic word-FORM (root, POS, derived form, clitics) BEFORE authoring or applying a Qamus gloss. Encodes the exact morphology mistakes fought in qamus-highlight. Use whenever adding a hover gloss, repairing a root/form, adding a surface form, moving a token from pending→resolved, or importing a lexeme candidate.
---

# Sarf (morphology) skill

You author or repair a scripture-facing gloss only **after** you can answer: what is the root, what is the
part of speech, is this a homograph risk, and is this safely matchable to a Qamus entry — **or should it stay
pending?** This skill is the discipline that prevents wrong hover glosses. It is **not** a generic Arabic lesson.

## Procedures (progressive disclosure — load the one you need)
This SKILL is the fast gate + contract; each step is a short procedure (input · checks · evidence ladder ·
output · forbidden · test). **Open only the one the task needs.**
- [`procedures/root-decision.md`](procedures/root-decision.md) — find the root via the evidence ladder.
- [`procedures/verb-form.md`](procedures/verb-form.md) — measure I–X, voice, person/number, negation tense-flip.
- [`procedures/verb-form-and-mood-review.md`](procedures/verb-form-and-mood-review.md) — keep form, voice, person/number, and governing mood visible before a verb hover.
- [`procedures/weak-root.md`](procedures/weak-root.md) — recover hidden و/ي/ا radicals (مثال/أجوف/ناقص/لفيف).
- [`procedures/hamza-root.md`](procedures/hamza-root.md) — hamza as radical + seat orthography (norm collapses it).
- [`procedures/doubled-root.md`](procedures/doubled-root.md) — geminate roots hidden by shadda (رَدَّ→ر د د).
- [`procedures/noun-plural-gender.md`](procedures/noun-plural-gender.md) — role/shape, plural, gender, proper vs common.
- [`procedures/masdar-participle.md`](procedures/masdar-participle.md) — maṣdar vs ism fāʿil/mafʿūl vs ṣifa mushabbaha gloss shape.
- [`procedures/clitic-and-host-morphology.md`](procedures/clitic-and-host-morphology.md) — segment proclitic + host + suffix; reject host-only hovers for composed tokens.
- [`procedures/nominal-derivative-decision.md`](procedures/nominal-derivative-decision.md) — classify the 7 derivative types (fāʿil/mafʿūl/mubālagha/ṣifa-mushabbaha/tafḍīl/zamān-makān/āla); penult+prefix vowel reads; **never a verb gloss** on a derivative.
- [`procedures/learner-error-diagnosis.md`](procedures/learner-error-diagnosis.md) — name the Madinah-study error class, route to fix + drill (ajamī teaching + engine guard share one loop).
- [`procedures/proper-noun.md`](procedures/proper-noun.md) — detect أعلام; no root-verb gloss; route to pending_proper_noun.
- [`procedures/homograph-risk.md`](procedures/homograph-risk.md) — the `norm_strict` surface-key safety probe.
- [`procedures/hover-application.md`](procedures/hover-application.md) — the certified live-apply path + rollback.
- [`procedures/bulk-source-triangulation.md`](procedures/bulk-source-triangulation.md) — classify bulk pending-table rows into auto-safe, two-vote, owner-gated, or pending.
- [`procedures/qamus-entry-authoring.md`](procedures/qamus-entry-authoring.md) — sarf evidence → reviewable entry candidate.
- [`procedures/corpus-to-qamus.md`](procedures/corpus-to-qamus.md) — the sarf half of the corpus→Qamus pipeline.

**Rules** (`rules/`): root-decision, verb-measure-gates, weak-root-gates, hamza-gates, plural-gender-rules,
masdar-participle-gates, homograph-quarantines, **surface-state-transition-rules** (the morphology side of the
[language state machine](../qamus/reports/language-state-machine-report.md) — forbidden single-gloss collisions).
**References** (`references/`): verb-measures-table, masdar-participle-notes, weak-verbs, quranic-morphology-notes,
**nominal-derivatives** (pattern→gloss-shape contract for the 7 derived nouns), **learner-error-remediation**
(Madinah-study failure modes → diagnosis → fix).
**Evals** (`evals/`): `sarf-state-machine-eval.json`, `qamus-regression-eval.json`, `corpus-authoring-eval.json`,
**`nominal-derivative-error-eval.jsonl`** (7 types + the Madinah confusions, machine-testable),
**`false-clitic-split-eval.jsonl`** (ٱلْمُلْك/لَهُ/قُرْءَانًا/رَحْمَة false-split guards + positive controls).
**Curriculum** (`curriculum/`): `zero-to-fluency-sarf.md` + beginner/intermediate/advanced drills (ajami path);
**`drills/nominal-derivatives.md`** (recognition+production for each derivative type).

## 1. Purpose
Turn a raw surface into a *defensible* morphological decision (or an honest pending) for Qamus authoring,
qamus-highlight resolution, and Nawawī40/Ṣaḥīḥayn candidate classification.

## 2. Input contract
A surface (Arabic, with diacritics if available) + its `quran_loc` (or hadith ref) + optional Qamus
entry candidates + optional QAC root/POS.

## 3. Output contract — emit this object before any gloss/repair/resolve
```json
{
  "surface_ar": "يَأْتِي", "normalized": "ياتي", "strict_normalized": "يأتي", "bare": "يأتي",
  "quran_loc": "2:38:10", "candidate_root": "أ ت ي", "candidate_lemma": "أتى",
  "pos": "verb", "form": "I", "voice": "active_or_passive_or_unknown",
  "person": "3rd_or_unknown", "gender": "masculine_or_unknown", "number": "singular_or_unknown",
  "case_or_mood": "raf_or_nasb_or_jazm_or_jarr_or_unknown",
  "visible_morphology": {"proclitics": [], "host": "يأتي", "suffixes": [], "inflection": null},
  "parse_key": {"key": "V:I:IMPF:ACT:3MS", "summary": "Form I imperfect active verb, third masculine singular"},
  "display": {"palette": "qamus-grammar-v1", "segments": [{"segment_index": 0, "role": "stem", "class": "qg-verb", "label": "STEM"}]},
  "attached_clitics": [], "suffix_pronoun": null,
  "qac_root": "أ ت ي", "qac_pos": "V", "qamus_entry_candidates": ["entry_id"],
  "risk_flags": ["multi_sense_root", "hamza_sensitive", "sense_selection_required"],
  "decision": "resolved | pending | quarantine",
  "reason": "root/POS agree but multiple senses; requires context",
  "confidence": "high|medium|low", "allowed_for_hover": false
}
```

## 4. Normalization ladder (each rung is for a different job; never display these)
`tools/normalize_ar.py` provides them.
1. **raw Arabic** — the only display form; never altered.
2. **`norm()`** — lenient recall key (drops hamza + harakāt). **Lookup assistance only — never certifies.**
3. **`norm_strict()`** — keeps the hamza seat; use for scripture-facing matching.
4. **`bare()`** — keeps every base letter distinct (ة≠ه، أ≠ا، ى≠ي); for enclitic detection.
5. **QAC token** — authoritative per-word root + POS (internal evidence).
6. **source-address loc** — `quran:S:A:W` to record + dedup the decision.

## 5. Root decision ladder (stop at the first that certifies)
Qamus source entry → **QAC root** → photographed source page → any **available source adapter** (triangulation,
internal-only) → **only then** a heuristic. A heuristic root alone is never enough for a scripture-facing gloss.
Adapters are optional and never named here (see `sources/README.md`); the Qamus entry always outranks them, and
nothing an adapter returns is ever public.

## 6. POS decision ladder
QAC POS → Qamus category → morphological shape (wazn) → context. **A POS mismatch is a blocker** (§ principle 3).

## 7. Derived form / wazn hints
Form II/IV often change sense + transitivity (يُحَذِّرُ "warns" ≠ "be cautious"; أَلْقَوْا form IV ≠ "meet";
فَأَخْرَجَ form IV "brought forth" ≠ "come out"). Maṣdar/participle usually need a **nominal** gloss
(تَحْرِير "freeing", not "to free… heat"). Passive vs active changes wording. The full forms I–X paradigm
(wazn, active/passive, imperative, maṣdar, ism fāʿil/mafʿūl, sense, Qurʾānic examples) is machine‑readable in
[`rules/verb-measures.json`](rules/verb-measures.json) with the readable table in
[`references/verb-measures-table.md`](references/verb-measures-table.md) and the gloss‑shape contract in
[`references/masdar-participle-notes.md`](references/masdar-participle-notes.md). Irregular roots
(hollow/defective/assimilated/hamzated/doubled/quadriliteral): [`references/weak-verbs.md`](references/weak-verbs.md).

## 8. Common clitics & suffixes
Proclitics وَ/فَ/بِ/لِ/كَ/ال and pronoun enclitics ـه/ـها/ـهم/ـكم/ـنا. **Clitic stripping must not invent a
false stem** — and a final tanwīn-alef (ـًا, e.g. قُرْءَانًا) is **not** the pronoun نا (`ends_tanwin_alef`).
If an exact/form match resolves the host before the clitic pass runs, still inspect the raw token for an attached
proclitic. A hover for بِسَلَـٰمٍ or بِبَدْرٍ must not silently display only the host noun ("peace", "Badr") when
the entry/sense being taught is the bāʾ. Add a separate `pre` channel or a source-addressed phrase gloss, and keep
the false-split guards in force.
If the public tooltip renders only the best gloss text, the best gloss itself must carry the attached clitic's
contribution; metadata like `pre: "with / by"` is evidence, not a user-visible repair. For example, `بِسَلَـٰمٍ`
must surface as "with peace" or "in peace" where certified, not best=`peace` plus hidden preposition metadata.
For any future rich hover, sarf must also emit the morphology side of the parse-key/display contract:
`parse_key.key` (compact ASCII), `parse_key.summary`, and one `qamus-grammar-v1` display class per grammatical
piece. These display classes may drive non-destructive color on an atomic visible Arabic word; they do not require
splitting the word into DOM segment boxes.
Use broad classes such as `qg-verb`, `qg-noun`, `qg-proper-noun`, `qg-pronoun`, `qg-preposition`,
`qg-article`, or `qg-case` when only the broad role is certified. Use the role-aware classes when the morphology
is known and learner-relevant: `qg-verb-prefix`, `qg-verb-stem`, `qg-subject-pronoun`, `qg-object-pronoun`,
`qg-possessive-pronoun`, `qg-noun-stem`, `qg-adjective`, `qg-dual-suffix`, `qg-plural-suffix`, and
`qg-derivative-prefix`. A rich hover that teaches dual, plural, participle/adjective shape, or a finite verb prefix
must make that visible in display metadata and the morphline. If sarf cannot account for a grammatical piece, the row
is not ready for rich-hover rendering and should defer to nahw or pending with an exact blocker.

Do not mint unsupported renderer classes for real sarf facts. If a live schema does not accept `qg-active-participle`
or a similar fine-grained class, keep the participle fact in `derivative_type`, the segment label, the morphline, and
the learner explanation, and render with a supported class such as `qg-adjective` plus visible derivative/number
pieces. A new visual class is safe only when the schema, renderer, fixture, validator, and regression checks are
updated together.

Every certifiable noun/adjective/participle host should carry an appropriate root or base where the tradition and
entry data support one. Proper names, pure particles, pronouns, and function-only cases must carry an explicit
`no_root`, `proper_name_no_root`, or `function_only_no_root` reason rather than a guessed root. Do not fill root fields
from resemblance alone.

A broad root-family gloss is dictionary metadata, not a hover. Do not put an omnibus entry gloss such as
"to know — also to teach and learn" on a concrete token. Pick the token's form-aware contribution ("knows",
"taught", "learned", "known", "the All-Knowing") or leave the token pending with the exact blocker.
Verb suffix pronouns are also visible morphology, not metadata. A token like `جَادَلُوكَ` contains the verb stem,
plural subject marker, and a second-person masculine singular object suffix; the hover must not collapse it to
"to argue; dispute". Use a subject/object-aware gloss such as "they argue/dispute with you (masc. sg.)" when
certified, or keep the row pending with the exact suffix blocker.
Verb form is a semantic gate, not decoration. Record triliteral form I-X or quadriliteral form I-IV before
authoring: II can be causative/intensive, III can be mutual, VI reciprocal, VII/VIII reflexive or agentless,
IX stative/color, X seeking/reflexive-causative. A hover that ignores the form, voice, person, number, or suffix
is a dictionary gloss, not a token gloss. A passive participle such as `مُعَلَّمٌ` needs a token-form gloss
like "taught", not a lemma gloss such as "to teach".
Prefix shape is not enough to classify a segment. A raw `و`, `ف`, `أ`, `ل`, or `ما` must be handed to nahw for
function before hover authoring: ordinary conjunction, oath, comitative, resumption, cause, equalization,
interrogation, purpose, imperative, genitive, preventive, vocative, exceptive, and negation can share deceptively
similar surface pieces. Sarf may segment the token; nahw certifies the grammatical contribution.

## 9. Homograph quarantine rules
If two readings collapse under `norm()`, decide on the **content letter's harakah / hamza seat / shadda**, not
on `norm`. If you cannot decide → **pending**, never a guess. (Full list in `drills/homograph-regressions.md`.)

## 10. When to author a gloss
Root + POS certified, single applicable sense (or context fixed via the nahw skill), no homograph/POS conflict.

## 11. When to make pending (with a precise reason)
`root_exists_form_unresolved` · `pos_mismatch` · `hamza_sensitive_homograph` · `multi_sense_root` ·
`derived_form_needs_review` · `proper_noun` · `source_evidence_needed` · `qamus_entry_needs_repair`.

## 12. When to create a Qamus repair candidate
The token is right but the **entry** is wrong (mis-filed form, impossible root that is a real error, count
mismatch). Emit a repair candidate with a source address + field path — **never** mutate live data here.

## 13. Regression examples
See `examples/qamus-regressions.jsonl` and `examples/root-form-decisions.jsonl`. They encode the exact bug
classes already fixed; a change that would re-introduce any of them is wrong.

## 13b. Executable gates (P10 — enforced, not advisory)
A decision is now machine-checked. Every `linguistic-decision` carries a `gate`, `grammar_triggers`, and
`reasoning`; [`tools/validate_linguistic_decisions.py`](../tools/validate_linguistic_decisions.py) **rejects** any
decision whose gate is weaker than its triggers require, any two-vote/iʿrāb decision missing its reasoning, and
any `never_auto`/`human-review` decision marked exportable. Gate rules:
[`rules/verb-measure-gates.json`](rules/verb-measure-gates.json), [`rules/weak-root-gates.json`](rules/weak-root-gates.json),
[`rules/masdar-participle-gates.json`](rules/masdar-participle-gates.json),
[`nahw/rules/irab-safety-gates.json`](../nahw/rules/irab-safety-gates.json),
[`nahw/rules/two-vote-required-rules.json`](../nahw/rules/two-vote-required-rules.json). Tiers:
`auto_safe` (QAC agrees · one sense · no homograph · no grammar dependency) → `two_vote_required` (iʿrāb/derived-
sense/multi-sense/referent) → `human_source_review_required` → `never_auto_resolve` (norm-only/OCR-only/copied/
QAC-conflict). **A surface-key gloss is auto_safe only if its `norm_strict` key is collision-free** (the
نَزَّلَ→نزل collides with نَزَلَ lesson).

## 13c. Production findings (P13 — reference-assisted batch, +694 live)
- **The live key is `norm_strict`, which KEEPS the `ال` article + the consonant skeleton but drops harakāt.** So
  a surface-keyed gloss is **safe** when the same-key surfaces are mere case/orthographic/tanwīn variants of ONE
  word (ٱلْكِتَٰبِ/ٱلْكِتَٰبَ/ٱلْكِتَٰبُ = "the Book" — and `الكتاب` does NOT collide with the verb `كتب`), and
  **unsafe** when the key mixes different words/POS. Decide with an **empirical key-collision probe** against the
  live corpus, not by reasoning about the bare root (which over-rejects).
- **True homographs that share a `norm_strict` key stay pending:** أُمّ "mother" ↔ أَمْ "or"; ٱلْمُلْك "dominion"
  ↔ ٱلْمَلِك "king"; هُدَى noun ↔ هَدَى verb; وَعَدَ verb ↔ وَعْد noun; كُذِبُوا۟ ↔ كَذَّبُوا "denied"; أَعْلَمُ
  elative "knows best" ↔ أَعْلَمُ verb "I know"; أَكْثَرَ verb ↔ أَكْثَرُ elative; سَوَآء "equal" ↔ "midst".
- **Referent landmines stay pending:** ٱلْحَقّ / ٱلْعَزِيز (divine-Name vs common), صَٰلِحًا (Prophet Ṣāliḥ vs
  "righteous").
- **A verbose/verb-shape spread-gloss is improved by a concise certified one** (basmala ٱلرَّحْمَٰنَ "to show mercy
  and compassion to" → "the Most Gracious (ar-Rahman)") — the fusha override fixes shape on non-primary slots.
- **كَظِيم (صفة مشبهة) carried a "to suppress anger" verb gloss** → entry-repair candidate (P14): reshape to
  adjectival; the source fix propagates, so prefer it over a partial hover override.

## 14. Integration with qamus-highlight
A sarf `decision` maps directly: `resolved`→author the gloss (src=qamus); `pending`→set the pending reason;
`quarantine`→demote/deny the wrong sense. Record the decision at `quran:S:A:W` in the source-address graph so
the same call is reused, never recomputed, across occurrences.

## 15. Integration with Nawawī40 / Ṣaḥīḥayn catalogues
For each catalogue token, run the same ladder to classify: already_in_qamus / new_surface_for_existing_lemma /
new_lemma_existing_root / new_root_or_unknown_root / particle_or_construction / uncertain_needs_review.

## 16. Morphology candidate lattice (the P2/P2b grammar-checker engine)
The general checker now emits a **ranked morphology candidate lattice** for a token — every competing out-of-context reading
KEPT, never one forced parse for unvoweled Arabic. This is the *executable* form of the discipline above. Use it whenever you
analyse a typed/arbitrary token or stage a rich-hover candidate.

- **Analyse-then-rank, never force one.** The analyser emits ALL readings; a SEPARATE step RANKS them (`score` AND `rank` — two
  distinct fields, **never a boolean `correct`**). The chosen reading is `rank == 1`; the alternatives stay. A token with `>1`
  candidate stays **pending** / `parse_confidence ∈ {surface_only, candidate}` with an exact blocker — blank beats a forced parse.
- **Consume the clitic lattice; never rebuild it.** Each candidate's `segment_candidate_ref` points back at a real
  `segment_candidates` row (the proclitic/enclitic peel). Never invent a segmentation the clitic lattice did not produce.
- **Three distinct layers — keep them apart:** (1) a *segmentation candidate* (one clitic peel), (2) a *morphology candidate* (one
  ranked reading over a segmentation), (3) the single *public hover segment* you ultimately render. Many candidates → one chosen
  reading → one source-clean hover. Never collapse (1)/(2) into the hover before evidence confirms `rank == 1`.
- **Blank beats wrong for root/pattern/lemma.** A `null` root/pattern/lemma is correct when you cannot certify one; never fabricate
  one from resemblance. The lattice's value is the POS/segmentation COMPETITION + `evidence_class` + ranking, not a guessed analysis.
- **Evidence class drives the gate** (closed set): `voweled_confirmable` / `source_addressed_confirmable` / `unvoweled_competing` /
  `homograph_split` / `weak_root_gated` / `component_only`. An `unvoweled_competing`/`homograph_split` candidate is **never
  `auto_safe`**; a lone clitic is `component_only` — a repair candidate, never a whole-token certification.
- **CEFR is scaffolding, not certification.** How much morphology metalanguage you expose depends on a *caller-supplied* level:
  root/pattern only at B1+, the full competing lattice at C1+. The skill never asserts or certifies a learner's level.
- **How a sarf fault becomes a suggestion + learner hint.** An unvoweled morphology correction **abstains** (never overcorrects); a
  clitic MERGE/SPLIT span comes only from `segment_candidates`. A diagnostic becomes a Point→Teach→Bottom-out learner event whose
  **Bottom-out is withheld past the gate**. sarf routes to these tools; it does not re-implement them.

**Executable gates (the source of truth — consult, never restate):**
[`tools/fusha_morphology_lattice.py`](../tools/fusha_morphology_lattice.py) (`build_morphology_lattice`) builds the lattice;
[`tools/fusha_text_check.py`](../tools/fusha_text_check.py) hosts `segment_candidates` + the arbitrary-typing path;
[`qamus/schemas/morphology-candidate-lattice.schema.json`](../qamus/schemas/morphology-candidate-lattice.schema.json) is the field
contract; [`tools/fusha_suggest.py`](../tools/fusha_suggest.py) is the abstain-first suggestion engine;
[`tools/fusha_learner_feedback.py`](../tools/fusha_learner_feedback.py) is the hint ladder;
[`tools/fusha_cefr_gate.py`](../tools/fusha_cefr_gate.py) gates explanation depth by level. Procedures:
[`procedures/morphology-candidate-lattice.md`](procedures/morphology-candidate-lattice.md),
[`procedures/clitic-segmentation-and-ambiguity.md`](procedures/clitic-segmentation-and-ambiguity.md); fields:
[`references/morphology-candidate-fields.md`](references/morphology-candidate-fields.md); eval:
[`evals/morphology-candidate-lattice.jsonl`](evals/morphology-candidate-lattice.jsonl).

---

## The five sarf principles (encode these)
1. **Never infer a root from `norm()` alone.** It drops hamza + harakāt for recall. `إِلَيْنَا` is **not** ل ي ن;
   `إيمان`≠`أيمان`; `يَأْمُرُونَ`≠`يَمُرُّونَ`; `قُرْءَانًا` is not stem+نا; `مَالِكِ` is not مَا لَكَ.
2. **Preserve hamza-seat distinctions** (أ/إ/ؤ/ئ/ء). Recall may be hamza-insensitive; any authored gloss/repair
   must pass `norm_strict` + QAC root/POS.
3. **POS mismatch is a blocker.** No verb gloss on a noun unless the Qamus sense supports the nominal use:
   `رَسُولًا`≠"to send"; `ٱبْن`/`بَنَات`/`بَنِي`≠"to build"; `مُحَمَّد`/`أَحْمَد`≠"to praise"; `صَٰلِحًا` is descriptive,
   not the Prophet Ṣāliḥ unless context supports it.
4. **Derived-form & stem matching must be conservative.** Form IV hamza changes sense; passive ≠ active;
   maṣdar/participle take nominal glosses; clitic stripping must not create a false stem.
5. **Use QAC as INTERNAL morphology evidence, not a public source.** Root/POS/lemma/validation/conflict-detection
   are fine internally; the public hover record is exactly `{"src":"qamus","kind":"authored"}` — no QAC name.

## NEVER DO THIS (wrong-gloss prevention)
- Never gloss from `norm()` alone. Never drop the hamza distinction for an authored gloss.
- Never put a verb infinitive on a noun, proper noun, or participle whose sense differs.
- Never copy an external gloss. Never expose `informed_by`/QAC/Quran.com/Tanzil in a public artifact.
- Never resolve when uncertain — **prefer pending with a precise reason.**

## Production findings (P4/P5 authored-gloss batch)
- **Surface-stable dominant-sense authoring works at scale.** For a high-frequency multi-sense root whose
  *surface form* has a single stable meaning (قَالَ "he said", ٱلنَّاسُ "the people"), author the concise
  **form-aware** dominant sense — it is safe surface-wide and resolves thousands of tokens the single-sense
  filter left pending. Context-sensitive surfaces stay pending (the nahw skill decides).
- **A verified authored gloss may OVERRIDE a non-primary (spread) gloss** — this is how the batch fixed
  pre-existing data-error wrongs (عَلِيمٌ "to be in pain" → "All-Knowing"; عِند "stubborn" → "with/near").
  Never override a curator-placed primary.
- **Quarantine the whole inflection family.** A data-error quarantine on عَلِيمًا (accusative) must also cover
  عَلِيمٌ (nominative) — match on the stem, not one case ending.

## Production findings (SN ingest — verb charts + AMAU vocab corpus)
The 1995 verb‑charts and the 11 AMAU decks (1,132 notes) were distilled into the verb‑measure paradigm + 451
singular↔plural pairs (gender‑tagged); see [`rules/verb-measures.json`](rules/verb-measures.json),
[`rules/root-pattern-risk-rules.json`](rules/root-pattern-risk-rules.json),
[`drills/verb-measures.md`](drills/verb-measures.md), and the knowledge base `corpora/sarfnahw/knowledge_base.json`.
Operational additions:
- **A broken plural shares the root, not the surface.** كِتَاب→كُتُب, رَجُل→رِجَال, قَلَم→أَقْلَام link by lemma/root,
  never by `norm()` shape — match a plural occurrence via the entry's plural field or QAC lemma, or pending.
- **Sound‑plural tails are morphology, not roots.** ـُونَ/ـِينَ (masc) and ـَاتٌ (fem) are number+case; ـون is not a
  verb ending, ـات is not part of the root.
- **مُـ participles split active/passive on the penult vowel** (مُعَلِّم "teacher" vs مُعَلَّم "taught one"); read the
  vowel before the gloss, and never put a finite verb on either.
- **A leading أ is ambiguous:** أَفْعَال (plural noun, أَقْلَام) vs أَفْعَلَ (Form IV verb, أَنزَلَ). Use QAC POS, not the أ.
- **Form II vs IV vs I are different verbs of one root** (نَزَّلَ / أَنزَلَ / نَزَلَ): the shadda, the hamza, the bare
  stem each select a distinct Qamus sense.
- **Gender is data, not a guess.** The corpus carries explicit m/f on nouns; use the entry's gender for agreement
  and participle‑form choice rather than inferring from the tail.
