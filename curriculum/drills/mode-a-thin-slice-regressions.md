# Mode A Thin Slice Regressions

These drills convert recent Qamus visual-closure ANDONs into learner-facing checks.

## Full Visible Card

Given the card in 2:98 for `n0005`, every visible qword must have:

- a source address;
- a qg class;
- a token contribution gloss;
- a private trace;
- a reverse rendered-span edge.

The page is not visually closed if only the originally selected word is rich-hovered.

## Function Particle Cluster

`أَمْ لَهُمْ` is not a single dictionary substitution.

- `أَمْ`: function-sensitive particle.
- `لَهُمْ`: `لَ` preposition plus `هُمْ` pronoun.

The hover may be compact, but the teaching layer must preserve the pieces.

## Verb Pieces

`تَعْبُدُوا۟` should show:

- `تَ`: imperfect prefix;
- `عْبُدُ`: stem from root `ع ب د`;
- `وا۟`: plural subject marker.

A host-only "worship" hover hides the learner-relevant morphology.

## Participle And Plural

`ٱلْمُبْطِلُونَ` should show:

- `ٱلْ`: article;
- `مُ`: derivative prefix;
- `بْطِلُ`: participial host from `ب ط ل`;
- `ونَ`: masculine plural suffix.

The learner should see why the word means "the falsifiers," not just memorize a phrase translation.

## Vocalized Function Token

`أَيَّانَ` must remain vocalized in the cited card. A page marked complete while the example text drops diacritics is a failed visual-closure claim.

## Qamustyping4 Final Regression Set

Qamustyping4 turns these into the minimum all-qword smoke set. For each row,
the learner or agent must prove the source address, public-safe hover, private
trace, qg classes, and reverse rendered-span edge. The proof is fixture-only
until the live Qamus executor performs public readback.

| family | learner-visible failure | required route |
|---|---|---|
| `p011` | a finite verb looks translated, but `تَ` / stem / `وا۟` are not all explained | sarf finite-verb segmentation, then nahw governor/mood if governed |
| `p014` | a suspicious hidden segment or POS guess is treated as fact | sarf POS/segment review; segment only what is visible |
| `p016` | imperfect prefix and plural subject marker vanish inside one verb-colored span | sarf verb prefix + subject marker drill |
| `p018` | `ٱلْمُبْطِلُونَ` hides article, participle prefix, stem, or plural suffix | sarf nominal-derivative + visible plural drill |
| `p050` | the card is marked complete while a function token or verb loses vocalization | source-text/readback blocker before any hover claim |
| `n0005` | draft-gloss counter says complete, but every visible qword is not hover/color accounted | all-visible-card denominator; selected-word closure is insufficient |
| `n0100` | proper names receive fake roots or generic noun colors | proper-name/no-root route |
| `v033` | `بِـ`, `مَعَ`, or attached pronoun contribution is omitted | nahw preposition + host/pronoun route |
| `v100` | particles such as `أَمْ` and `لَهُمْ` remain plain or phrase-translated | function-token cluster route, not phrase-only hover |

### Completion Drill

For any cited card, write:

```text
entry:
card address:
visible qword count:
hover/color accounted count:
uncounted visible qwords:
source-text/vocalization mismatches:
one qword with sarf pieces:
one qword with nahw/function pieces:
public hover source fields:
private trace target:
reverse rendered-span edge:
```

Pass only when every visible qword is either rich-hover/color accounted or has
an exact owner, scholar/i'rab, source-crosswalk, renderer/qg, validator/schema,
or no-entry/function-token packet. A "draft glosses: N of N" badge is not proof.
