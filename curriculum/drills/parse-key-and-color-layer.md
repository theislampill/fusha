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
| verb stem | `qg-verb` | `V` |
| noun/common host | `qg-noun` | `N` |
| proper name host | `qg-proper-noun` | `N` |
| pronoun | `qg-pronoun` | `PRON` |
| preposition | `qg-preposition` | `P` |
| oath waw | `qg-oath` | `OATH` |
| comitative waw | `qg-comitative` | `COM` |
| ordinary/function particle | `qg-particle` | `PART` |
| cause/result fa | `qg-result` | `CAUS` / `RES` |
| definite article | `qg-article` | `ART` |
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

Run the metadata validator against a JSONL version of the answers when converting this drill
into fixtures:

```text
python tools/validate_morphosyntax_token_metadata.py qamus/examples/morphosyntax_token.sample.jsonl
```
