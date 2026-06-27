# Morphosyntax Token Contract

Status: first contract for the post-Andon parse layer. The public hover stays concise; grammar breakdown lives in a separate per-token metadata record.

## Why This Exists

The same Andon class kept recurring because a token hover could be "lexically true" while hiding real grammar:

- attached prepositions and oath particles: `بِسَلَامٍ`, `وَٱلتِّينِ`
- verb subject/object suffixes: `جَادَلُوكَ`, `يَحْفَظُونَهُ`
- particles with attached pronouns: `إِنَّا`
- iḍāfa and within-token possessives
- adjective agreement, badal/apposition, tamyīz, condition/result, and PP attachment
- clause builders: relative pronouns, subordinating particles, purpose lām, temporal conditionals
- adverbial accusatives: hāl, mafʿūl li-ajlih, mafʿūl maʿahu
- particle-function collisions: interrogative hamza versus equalization hamza, ordinary wāw versus oath or comitative wāw

English hover text alone cannot safely encode POS, person, number, gender, case, mood, state, rationality, and dependency arcs. The remedy is a separate source-addressed parse payload keyed by `loc`.

## Source Of Truth

Add records conforming to `qamus/schemas/morphosyntax-token.schema.json`.

The payload is internal evidence and teaching metadata. It may cite internal labels such as `tafsir-center:analyze_word:13:11:8:irab_sarf`, but the public hover artifact remains `src=qamus`, `kind=authored`, `lang=en`.

## Phase RICH-00 Record Shape

The rich-hover phase upgrades this payload from "metadata attached to a gloss" into the token-level contract that
answers: can this hover teach the learner what each Arabic piece contributes?

Every rich record must keep identity and reuse keys separate:

- `loc`: exact Qur'an token identity (`S:A:W`).
- `wbw_loc`: exact rendered hover slot identity (`wbw:S:A:W`).
- `parse_key.key`: compact grammar-family key. This is useful for reuse and debugging, but it is **not** the
  primary identity and never authorizes propagation by itself.
- `src`, `kind`, `lang`: source-clean public boundary, always `qamus`, `authored`, `en`.
- `decision_state`: one of `rich_candidate`, `rich_certified`, `pending`, `blocked`, or `token_only_override`.

The record carries two teaching views:

- `sarf`: morphology state (`ism` / `fiʿl` / `ḥarf`, root, pattern, verb form, voice, mood, person, number, gender,
  definiteness, case, derivative type).
- `nahw`: syntax/function state (function, i'rab role, governor, governed relation, PP attachment, idafa relation,
  pronoun referent, clause relation, source-clean reasoning summary).

The `segments[]`, `parse_key`, `display`, `hover_contract`, and `learner_explanation` fields must agree. A readable
English hover is not enough; the row must explain the visible Arabic pieces. If the row cannot do that safely, it
uses `pending` or `blocked` with an exact `blocker` reason.

The accepted schema deliberately duplicates public boundary fields at the top level and inside `public_boundary`.
That makes public-leak checks simple for exporters while keeping older validators able to assert the boundary.

## Minimum Fields By Class

- Verb: POS, form, voice, aspect, mood when applicable, subject agreement, object suffix if present.
- Nominal: POS subtype, case, state, number, grammatical gender, rationality when relevant.
- Particle/preposition: function, governed token, effect on case/mood where applicable.
- Token-internal clitic: segment role plus visible gloss contribution.
- Dependency: role plus head/governor/linked locs for fāʿil/hidden subject, nāʾib fāʿil, objects, iḍāfa, ṣifa, badal, tamyīz, murakkab compound numbers, PP, condition/result, relative clauses, kāna/kāda sisters, and mā acting like laysa.

## Particle And Phrase Gate

Do not collapse same-letter particles into one hover rule:

- ordinary `و` may coordinate, oath `و` governs a genitive noun like a preposition, and comitative `و` means "with" and licenses mafʿūl maʿahu.
- `ف` may resume, coordinate, mark a conditional/result answer, be supplemental, or cause a following imperfect verb to be subjunctive.
- `إن` and its sisters are verb-like accusative particles: record `ism_inna` and `khabar_inna`, with the subject accusative and predicate nominative.
- negative `لا` may behave like `أن`: record its subject/predicate relation instead of treating it as bare "no".
- preventive `ما` after an accusative particle forms kāffa wa makfūfa and blocks the usual case effect.
- vocative particles govern an addressee and can affect case; record the vocative dependency and addressee loc.
- exceptive particles need the exception structure: mustathnā minhu, mustathnā, and whether the expression is muttaṣil, munqaṭiʿ, or mufarragh.
- prefixed `بـ`, `لـ`, and similar prepositions create jar-majrūr even when fused to a noun or pronoun.
- definite articles are visible grammar pieces. A token such as `وَٱلْقَمَرُ` must preserve `and + the + moon`,
  while `ٱلسُّفَهَاءُ` must not become `the + the foolish ones`.
- hamza/alif may be interrogative or equalization; the equalization use should surface a "whether" contribution and is not an ordinary question.
- purpose lām, imperative lām, and genitive lām are distinct segment roles.

A PP record needs both the internal jar-majrūr relation and its attachment target: verb, nominal, hidden hāl, hidden ṣifa, clause, or other explicit loc. A public hover like `Badr`, `figs`, or `stars` is invalid for an entry/sense that is teaching the attached preposition or oath relation.

## Clause Gate

Record clause builders explicitly:

- relative pronoun plus ṣilat al-mawṣūl: `relative_clause`
- subordinating conjunction such as `أن`: `subordinate_clause`
- purpose lām with implied `أن`: `purpose_clause`
- temporal condition such as `إذا`: `temporal_condition` plus `answer_of_condition`

The hover may stay concise, but the parse record must preserve the syntactic function that selected it.

## Adverbial Accusative Gate

For accusative adverbial constructions, record the role and attachment:

- hāl: accusative circumstance; the head may be a verb, nominal, pronoun, hidden pronoun, or a previous-verse pronoun.
- interrogative hāl: words such as `كيف` can function as circumstantial accusatives.
- mafʿūl li-ajlih: accusative of purpose or motive.
- mafʿūl maʿahu: comitative object after comitative wāw, not ordinary coordination.

## Verb Dependency Gate

An active verb needs a fāʿil, explicit or hidden by inflection. A passive verb needs nāʾib fāʿil. Objects may be separate words or same-token pronoun suffixes, and object roles are accusative. Do not model every verb as subject plus object:

- kāna and sisters: `ism_kana` nominative plus `khabar_kana` accusative.
- kāda and sisters: `ism_kada` plus imperfect-verb `khabar_kada`.
- negative mā acting like laysa: `ism_ma_laysa` plus `khabar_ma_laysa`.

## Imperfect Mood Gate

Mood applies to imperfect verbs. Record `indicative`, `subjunctive`, or `jussive` and the governing relation:

- Subjunctive governors include `لن`, lām of purpose/denial, cause fāʾ, comitative wāw, `أن`, `كي`, and `حتى`.
- Jussive governors include `لم`, imperative lām, prohibitive `لا`, imperative results, and conditional particles.
- A hover under negation or mood must reflect the governed meaning, not the bare surface tense.

## Imperative Gate

Record imperative expressions explicitly:

- direct imperative verb: `imperative`
- lām of command plus imperfect jussive: `imperative_lam`
- prohibitive `لا` plus imperfect jussive: `prohibition`
- imperfect jussive result of a preceding command: `jawab_amr`

## Verb Form Gate

Record triliteral form I-X or quadriliteral form I-IV before resolving a verb hover. Form is part of meaning:

- I: base transitive/intransitive action.
- II: causative or intensive/repeated action.
- III: interaction with another participant; often mutual.
- IV: causative or transformative.
- V: reflexive/effective counterpart of II.
- VI: reciprocal or conative counterpart of III.
- VII: submission/reflexive or agentless passive sense.
- VIII: reflexive/conative/reciprocal sense.
- IX: stative, especially colors/defects.
- X: seeking, reflexive-causative, or transformative.
- Quadriliteral forms I-IV: four-radical patterns with their own reflexive/stative behavior.

The hover must be shaped by form, voice, person, number, gender where relevant, and attached subject/object pronouns.

## Hover Contract

The parse payload should drive validators:

- `جَادَلُوكَ`: hover must surface plural subject and masculine-singular object, not bare `to argue`.
- `إِنَّا`: hover must surface emphasis plus `We`, not particle-only `surely/indeed`.
- `يَحْفَظُونَهُ`: hover must surface plural subject and object `him`, not bare root-family `to guard`.
- `أَنزَلْنَاهُ`: hover must keep `We sent it down`.
- `وَٱلشَّمْسُ` and `وَٱلْقَمَرُ`: hover must keep `and + the + host`, not host-only or missing-article wording.
- `ٱلسُّفَهَاءُ`: hover must keep one visible article contribution, not `the + the foolish ones`.
- `يَا` versus `أَيُّهَا`: the vocative particle contributes `O`; `أَيُّهَا` carries the addressee bridge and attention particle, so the two split tokens must not share one flattened hover.
- `فَأَهْلَكْنَاهُمْ`: hover must account for fāʾ, Form IV/perfect stem, `We` subject, and `them` object before leaving pending.

## Segment Rendering Target

The live renderer should be able to color both the Arabic token and the hover breakdown from this payload. Keep the
public best gloss concise, but expose a scrubbed learner view with stable segment classes:

- conjunction/resumption/result/cause particles (`qg-particle`, `qg-result`)
- prepositions, oath wāw, and comitative wāw (`qg-preposition`, `qg-oath`, `qg-comitative`)
- definite article (`qg-article`)
- verb stem and verb form (`qg-verb`)
- nouns and proper-name hosts (`qg-noun`, `qg-proper-noun`)
- subject, object, and possessive pronouns (`qg-pronoun`)
- relative, vocative, exception, and case pieces (`qg-relative`, `qg-vocative`, `qg-exception`, `qg-case`)

The color layer must be generated from scrubbed segment roles, not from external source names or copied source text.
For Arabic shaping safety, `display.segments[]` does not require visible segment elements inside the word. A live
renderer may keep the visible Arabic token as one text run and project the segment roles through gradient stops,
overlays, rails, or tooltip rows. The hard invariant is that every grammatical piece has a scrubbed segment record
and that the visible token text remains unchanged.

## Parse-Key Contract

Every morphosyntax token record now carries a `parse_key` object and a `display` object. These are the bridge from
the sarf/nahw decision to a future hover UI:

```json
{
  "parse_key": {
    "key": "V:III:PERF:ACT:3MP+OBJ.2MS",
    "summary": "Form III perfect verb with plural subject and second-person masculine singular object suffix.",
    "components": [
      {"label": "V", "value": "Form III perfect active"},
      {"label": "SUBJ", "value": "3rd masculine plural"},
      {"label": "OBJ", "value": "2nd masculine singular"}
    ]
  },
  "display": {
    "palette": "qamus-grammar-v1",
    "segments": [
      {"segment_index": 0, "role": "stem", "class": "qg-verb", "label": "STEM"},
      {"segment_index": 1, "role": "object_pronoun", "class": "qg-pronoun", "label": "PRON"}
    ]
  }
}
```

Rules:

- `parse_key.key` is compact ASCII for machines and logs. It should be stable across renderer changes.
- `parse_key.summary` is short learner/reviewer prose, authored by Qamus/Fusha, not copied from a screenshot/source.
- `parse_key.components[]` is the line the tooltip can render: label, value, optional note.
- `display.palette` is currently `qamus-grammar-v1`.
- `display.segments[]` aligns one-for-one with `segments[]` and supplies scrubbed classes for token coloring.
  These are semantic/display records, not a requirement to split the visible Arabic word into DOM segment boxes.
- `surface` and every `segments[].surface` are nonempty and whitespace-free. Token composition may be explained in
  rows, parse keys, or color metadata, but the metadata must not encode spaces or gaps inside a written Arabic word.
- These fields are grammar metadata. They are not public provenance and must not contain QAC/Tafsir/source names.

The screenshot packs justify the shape: QAC uses colored segment labels under Arabic tokens plus dependency arcs and
phrase labels. Qamus should keep the intuitive color idea, but drive it from its own role classes and authored
parse keys so the public boundary remains clean.

## Public Boundary

Do not pack grammar tags or source names into `data-tr`.

Future rendering should use a separate scrubbed grammar payload or tooltip section. Public HTML must not expose raw MCP/QAC/source names, internal provenance, or copied source wording.

## Validator Gate

Run `tools/validate_morphosyntax_token_metadata.py` against morphosyntax JSONL to enforce:

- unique `loc`
- exact `wbw_loc=wbw:<loc>`
- top-level `src=qamus`, `kind=authored`, `lang=en`, matching `public_boundary`
- `decision_state` with blocker text required for `pending` and `blocked`
- required `sarf`, `nahw`, and `learner_explanation` fields for the rich teaching layer
- bounded enums for POS/case/mood/gender/person/number/state
- required `parse_key` and `display` payloads
- ASCII `parse_key.key`
- `display.palette=qamus-grammar-v1`
- `display.segments[]` alignment with `segments[]`
- whitespace-free token and segment surfaces, so renderer inputs cannot physically split a Qurʾānic written token
- public boundary fields: `public_gloss_src=qamus`, `public_gloss_kind=authored`, `public_gloss_lang=en`, and `external_source_names_public=false`
- function-bearing segments carry `gloss_contribution` and a `hover_contract.must_surface`
- attached subject/object/possessive pronouns preserve person and number tags
- no external source labels leak into public-facing hover-contract, parse-key, or display text

Future live/staged render validation should additionally compare `hover_contract.must_surface` against the built
`wbw-lookup.json` best hover and assert that any visible Arabic token keeps the same normalized text content as
the source token.

## Certification Gates

A row may be `rich_certified` only after these gates pass:

1. Address gate: `loc` and `wbw_loc` are exact and do not drift.
2. Public gate: authored Qamus gloss only; no source labels, snippets, screenshots, private paths, or copied text.
3. Sarf gate: POS, root/pattern/form/voice/mood/agreement/clitics/suffixes/articles are accounted for where
   applicable.
4. Nahw gate: function, i'rab, case/mood, governor, PP/jar-majrur, idafa, clause relation, vocative/exception/oath,
   and referent are accounted for where applicable.
5. Learner gate: the explanation teaches the visible Arabic contribution rather than merely restating the English.
6. Two-vote/source gate: grammar-sensitive rows require two independent checks that agree on conclusion and reason;
   source triangulation is internal-only evidence.
7. Renderer gate: `display.palette=qamus-grammar-v1` and segment classes are valid. If live rendering cannot display
   the data yet, emit a renderer requirement rather than claiming live support.

The Nature paper about orthogonalized state-machine learning may be cited in curriculum architecture as an analogy
for hidden-state separation, but it is not Arabic linguistic evidence and must never appear in hover provenance.

## Kawkab Coverage Gate

Run `tools/audit_wbw_lookup_morphosyntax.py <wbw-lookup.json> --fail-on none` on staged or live lookup artifacts
before treating rich hover coverage as broad. The summary includes a `rich_metadata` section with:

- total WBW records;
- records carrying complete `parse_key` + `display` + `segments`;
- records with partial rich metadata, which must not render as certified rich hovers;
- records whose segment surfaces align to the atomic Arabic token under Kawkab Mono character-width math;
- missing candidate lanes such as `candidate_art_nominal`, `candidate_conj_art_nominal`,
  `candidate_ba_art_nominal`, and `candidate_suffix_or_pronoun`.

For Kawkab-safe coloring, the normalized segment surfaces must add up to the normalized visible token. A mismatch
means the gradient/color stops may drift across the monospaced glyph run, so the record should stay blocked until
the segment surfaces are repaired. This gate measures metadata readiness; it does not mutate live Qamus data and
does not authorize heuristic renderer coloring for unparsed words.
