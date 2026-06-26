# Drill — hover composition and routing

**Goal:** learn the same pre-hover discipline the Qamus closure process uses: a written token
may contain several grammatical pieces, and each piece must be accounted for before the learner
trusts or authors a gloss.

**Rule of the drill:** compose the token before accepting the hover. For each item, write six
fields:

1. written token,
2. visible pieces,
3. sarf class of the host,
4. nahw function of attached particles or clause pieces,
5. semantic/concept flag, if any,
6. parse-key/display readiness,
7. result: allowed hover, learner explanation, or `pending:` blocker.

Public hover output stays source-clean: `{src:'qamus', kind:'authored', lang:'en'}`. QAC,
grammar screenshots, external dictionaries, source-triangulation output, and Tafsir/i'rab notes
may route review internally, but they never become public provenance and never supply copied
hover wording.

## Items

| token | visible pieces | safe result |
|---|---|---|
| `بِسْمِ` | `بِـ` + host noun `ٱسْمِ` | hover/explanation must preserve the bā': "in the name of"; host-only "name" fails |
| `لِلَّهِ` | `لِـ` + definite proper noun | preserve the lām: "for/to Allah"; host-only "Allah" fails |
| `كَأَنَّ` | `كَـ` + `أَنَّ` particle frame | route to nahw; not host-only "that" and not ordinary lexical kāf |
| `وَمَا` | `وَ` + `مَا` | one written token, multiple grammar pieces; decide `مَا` by function before glossing |
| `وَٱلْعَصْرِ` | clause-initial `وَ` + jarr noun | oath frame: "by"; ordinary "and" fails if the frame is oath |
| `فَتَنفَعَهُ` | `فَـ` + imperfect verb + object suffix | route fā' function and mood; suffix pronoun cannot disappear |
| `أَعْطَيْنَاكَ` | verb + subject suffix `ـنا` + object suffix `ـكَ` | "We gave you"; bare "gave" fails |
| `قُرْءَانًا` | host noun + tanwin fatḥ alif | `ـًا` is nunation, not pronoun `نا`; no clitic split |
| `صَٰلِحًا` | common adjective/noun surface | concept flag may warn about Ṣāliḥ the messenger, but context decides |
| `بِبَدْرٍ` | `بِـ` + proper place name | preserve both the preposition and named-place status; concept metadata is a routing flag |
| `إِلَيْنَا` | preposition stem + pronoun `ـنا` | "to us"; hamza-seat/root guard prevents false `ل ي ن` |

## Parse-key handoff

After the routing decision, produce a renderable handoff:

```text
parse_key.key:
parse_key.summary:
display classes:
```

Examples:

- `جَادَلُوكَ` → `V:III:PERF:ACT:3MP+OBJ.2MS`, display `qg-verb + qg-pronoun`.
- `بِسْمِ` → `P:BI+N:GEN`, display `qg-preposition + qg-noun`.
- `وَٱلْعَصْرِ` in an oath frame → `OATH+ART+N:GEN:DEF`, display
  `qg-oath + qg-article + qg-noun`.

If the row cannot produce a parse key because the function or attachment is not certified, the
result is not a rich hover. Route to the exact blocker and keep the public hover blank or
minimal according to the closure lane.

## Routing rules

- **Sarf first:** identify the host class, root/form where relevant, visible affixes, and suffix
  pronouns. If exact/form matching hides a clitic, route to
  [`../../sarf/procedures/clitic-and-host-morphology.md`](../../sarf/procedures/clitic-and-host-morphology.md).
- **Nahw next:** decide particle function, PP attachment, mood governance, relative/condition
  frames, and pronoun referents. If a function token lacks a standalone entry but its function
  is clear, it may be certifiable as a token contribution; if the frame is not clear, it stays
  `pending:`.
- **Concept map last:** use concept metadata only to flag named-entity/common-word collisions
  and curriculum families. It cannot override sarf, nahw, i'rab, or verse context.
- **Public boundary always:** do not publish source labels, QAC labels, screenshot labels, or
  external wording. A public hover is authored Qamus text or blank.

## Checklist

- [ ] Did every visible proclitic (`وَ`, `فَـ`, `بِـ`, `لِـ`, `كَـ`) receive a role?
- [ ] Did every suffix pronoun receive a referent or a `pending: referent_unresolved`?
- [ ] Did `مَا`, `وَ`, and `فَـ` get a function decision rather than a default gloss?
- [ ] Did preposition + host tokens avoid host-only hovers?
- [ ] Did semantic concept metadata stay internal and non-authoritative?
- [ ] Did the final result separate token hover, phrase explanation, and learner note?
- [ ] Did the result include a compact ASCII `parse_key.key` and one display class per
      grammatical piece, without requiring the visible Arabic word to be physically split?

Use this drill before [`ayah-reading-drills.md`](ayah-reading-drills.md), after hard misses in
[`quranic-function-words.md`](quranic-function-words.md), and whenever a Qamus closure row looks
"obvious" only because the attached piece was ignored.
Then run [`parse-key-and-color-layer.md`](parse-key-and-color-layer.md) to turn the composition
into a renderer-ready parse-key/color contract.
