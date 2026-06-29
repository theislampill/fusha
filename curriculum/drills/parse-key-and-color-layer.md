# Drill — Parse-Key And Color Layer

**Goal:** turn a composed written token into a safe parse key and stable display classes. This
is the learner/reviewer bridge between grammar analysis and a future rich Qamus hover.

Use this after
[`hover-composition-and-routing.md`](hover-composition-and-routing.md) and alongside
[`../../qamus/reports/morphosyntax-token-contract.md`](../../qamus/reports/morphosyntax-token-contract.md).

## The Four Fields

For each token, fill:

```text
best gloss:
Arabic pieces:
parse_key.key:
display classes:
pending blocker, if any:
```

The best gloss is authored English. The parse key is a compact grammar explanation. The
display classes are scrubbed Qamus role classes, not screenshot/source labels.

## Role Classes To Use

| Piece | Display class | Tag |
|---|---|---|
| verb prefix / imperfect marker | `qg-verb-prefix` | `PFX` |
| verb stem | `qg-verb` / `qg-verb-stem` | `V` / `STEM` |
| subject marker or subject pronoun | `qg-subject-pronoun` | `SUBJ` |
| object pronoun | `qg-object-pronoun` | `OBJ` |
| possessive pronoun | `qg-possessive-pronoun` / `qg-pronoun` | `POSS` |
| noun/common host | `qg-noun` / `qg-noun-stem` | `N` |
| adjective / ṣifa host | `qg-adjective` | `ADJ` |
| proper name host | `qg-proper-noun` | `N` |
| generic pronoun | `qg-pronoun` | `PRON` |
| preposition | `qg-preposition` | `P` |
| conjunction wāw | `qg-conjunction` | `CONJ` |
| oath waw | `qg-oath` | `OATH` |
| comitative waw | `qg-comitative` | `COM` |
| ordinary/function particle | `qg-particle` | `PART` |
| cause/result fa | `qg-result` / `qg-result-fa` | `CAUS` / `RES` |
| lām segment | `qg-lam` | `LAM` |
| mā segment | `qg-ma-particle` | `MA` |
| definite article | `qg-article` | `ART` |
| derivative prefix | `qg-derivative-prefix` | `DER` |
| dual suffix | `qg-dual-suffix` | `DUAL` |
| plural suffix | `qg-plural-suffix` | `PL` |
| relative pronoun | `qg-relative` | `REL` |
| vocative | `qg-vocative` | `VOC` |
| exception | `qg-exception` | `EXC` |
| case ending | `qg-case` | `CASE` |

## Items

| token | required parse-key decision | display classes |
|---|---|---|
| `إِنَّا` | accusative particle + attached 1st plural pronoun | `qg-particle`, `qg-pronoun` |
| `أَنزَلْنَاهُ` | Form IV perfect active + `نا` subject + `ه` object | `qg-verb`, `qg-pronoun`, `qg-pronoun` |
| `بِيَدِهِ` | bā preposition + noun host + possessive pronoun | `qg-preposition`, `qg-noun`, `qg-pronoun` |
| `يَحْفَظُونَهُ` | imperfect verb + plural subject marker + object pronoun | `qg-verb`, `qg-pronoun` |
| `بِسَلَامٍ` | preposition + genitive host; host-only gloss fails | `qg-preposition`, `qg-noun` |
| `وَٱلْعَصْرِ` | decide oath waw versus conjunction before glossing | `qg-oath` or `qg-particle`, `qg-article`, `qg-noun` |
| `فَتَنفَعَهُ` | decide fa function; preserve verb and object suffix | `qg-result` or `qg-particle`, `qg-verb`, `qg-pronoun` |
| `وَمَا` | one written token; waw plus function-specific `ما` | `qg-particle`, `qg-relative`/`qg-negative`/`qg-particle` |
| `أَيُّهَا` | vocative support plus attention particle | `qg-vocative`, `qg-particle` |
| `إِلَّا` | exception particle; type/case may require nahw/scholar lane | `qg-exception` |
| `أُورِثْتُمُوهَا` | passive perfect host + 2mp subject/deputy-subject marker + object `ها` | `qg-verb-stem`, `qg-subject-pronoun`, `qg-object-pronoun` |
| `بُرْهَٰنَانِ` | noun host plus visible dual ending; dual cannot hide inside a white host span | `qg-noun-stem`, `qg-dual-suffix` |
| `قاعدون` | participial/adjectival host plus sound masculine plural ending | `qg-noun-stem` or `qg-adjective`, `qg-plural-suffix` |
| `مُّطَاعٍۢ` | passive participle / ṣifa shape, not the infinitive "to obey" | `qg-derivative-prefix`, `qg-adjective` |
| `يُحْيِي` | imperfect prefix plus Form IV lexical stem | `qg-verb-prefix`, `qg-verb-stem` |
| `كُلُّ شَيْءٍ قَدِيرٌ` | quantifier/noun/adjective relation; each visible host needs its own role | `qg-noun-stem`, `qg-noun-stem`, `qg-adjective` |

## Worked Shape

```text
token: أَنزَلْنَاهُ
best gloss: We sent it down
Arabic pieces: أَنزَلْ + نَا + هُ
parse_key.key: V:IV:PERF:ACT:1P+OBJ.3MS
display classes: qg-verb, qg-pronoun, qg-pronoun
pending blocker: none if root/form/voice/object are certified; otherwise verb_suffix_role_uncertified
```

```text
token: وَٱلْعَصْرِ
best gloss: by time / by the declining day, only if oath frame is certified
Arabic pieces: وَ + ٱل + عَصْرِ
parse_key.key: OATH+ART+N:GEN:DEF
display classes: qg-oath, qg-article, qg-noun
pending blocker: waw_function_uncertified if oath versus conjunction is not established
```

## Pass Bar

For ten tokens:

- no visible piece disappears from `Arabic pieces`;
- `parse_key.key` is compact ASCII;
- `display classes` align one-for-one with the pieces;
- source names and screenshot labels do not appear in best gloss, parse key, or display text;
- any uncertain function becomes an exact pending blocker.

## RICH-CERT State Drill

For each reviewed token, write one of `pending`, `token_only_override`, `preview_only`, or
`rich_certified`, then justify the state.

| example | likely state before live apply | why |
|---|---|---|
| `يَسْأَلُكَ` | `token_only_override` | exact address has a verb stem plus visible `كَ`; family propagation is unsafe |
| `فَأَهْلَكْنَاهُمْ` | `pending` | fāʾ, Form IV host, subject `نا`, and object `هم` need compatible two-vote reasoning |
| `وَٱلشَّجَرُ` | `pending` | conjunction/article/host segment evidence exists, but component evidence cannot certify the whole token |
| `بِبَدْرٍ` | `token_only_override` | bāʾ plus place-name host needs exact preposition/locative review |

Reject any answer that says "the tooltip can show colors, therefore the hover is certified." Renderer preview data is a
study aid until the sarf, nahw, source/two-vote, public-boundary, and owner gates all pass.

## RH-LIVE Color Regression Items

Use these as quick checks after any public or fixture renderer change:

- `يُحْيِي`: the `يُ` prefix and `حْيِي` stem must begin as separate segment records. A single verb-colored span
  hides the imperfect marker.
- `بُرْهَٰنَانِ`: the dual ending must be visible in the breakdown and morphline. A gloss that says "two proofs"
  while the token remains one unmarked host fails the lesson.
- `قاعدون`: the plural ending must be visible; the hover should teach "sitting/staying ones" as a plural nominal
  contribution, not only a root family.
- `مُّطَاعٍۢ`: the row must show passive participle / adjective shape and avoid an infinitive such as "to obey".
- `أُورِثْتُمُوهَا`: the passive host, 2mp marker, and object `ها` each need a contribution row.
- `ٱل...` hosts: the article remains `qg-article`; do not let a definite article vanish into a plain noun/adjective span.
- Learner explanations must explain Arabic pieces only. Phrases about authoring process, source-boundary policy,
  deployment, or internal evidence are report/admin text, not hover text.

Run the metadata validator against a JSONL version of the answers when converting this drill
into fixtures:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/morphosyntax_token.sample.jsonl
```
