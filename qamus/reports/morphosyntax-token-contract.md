# Morphosyntax Token Contract

Status: first contract for the post-Andon parse layer. The public hover stays concise; grammar breakdown lives in a separate per-token metadata record.

## Why This Exists

The same Andon class kept recurring because a token hover could be "lexically true" while hiding real grammar:

- attached prepositions and oath particles: `بِسَلَامٍ`, `وَٱلتِّينِ`
- verb subject/object suffixes: `جَادَلُوكَ`, `يَحْفَظُونَهُ`
- particles with attached pronouns: `إِنَّا`
- iḍāfa and within-token possessives
- adjective agreement, badal/apposition, tamyīz, condition/result, and PP attachment

English hover text alone cannot safely encode POS, person, number, gender, case, mood, state, rationality, and dependency arcs. The remedy is a separate source-addressed parse payload keyed by `loc`.

## Source Of Truth

Add records conforming to `qamus/schemas/morphosyntax-token.schema.json`.

The payload is internal evidence and teaching metadata. It may cite internal labels such as `tafsir-center:analyze_word:13:11:8:irab_sarf`, but the public hover artifact remains `src=qamus`, `kind=authored`.

## Minimum Fields By Class

- Verb: POS, form, voice, aspect, mood when applicable, subject agreement, object suffix if present.
- Nominal: POS subtype, case, state, number, grammatical gender, rationality when relevant.
- Particle/preposition: function, governed token, effect on case/mood where applicable.
- Token-internal clitic: segment role plus visible gloss contribution.
- Dependency: role plus head/governor/linked locs for fāʿil/hidden subject, nāʾib fāʿil, objects, iḍāfa, ṣifa, badal, tamyīz, murakkab compound numbers, PP, condition/result, relative clauses, kāna/kāda sisters, and mā acting like laysa.

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

## Public Boundary

Do not pack grammar tags or source names into `data-tr`.

Future rendering should use a separate scrubbed grammar payload or tooltip section. Public HTML must not expose raw MCP/QAC/source names, internal provenance, or copied source wording.

## Next Gate

Build `tools/validate_morphosyntax_token_metadata.py` to enforce:

- unique `loc`
- bounded enums for POS/case/mood/gender/person/number/state
- public boundary fields
- if `hover_contract.must_surface` is present, the built `wbw-lookup.json` best hover contains those contributions
- no external source labels are emitted in the public artifact
