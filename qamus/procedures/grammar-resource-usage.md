# Grammar Resource Usage

Grammar screenshots, QAC concept metadata, corpus labels, and external word
tools are internal evidence. They can improve routing, tests, curriculum, and
review packets, but they do not become public hover payload.

Allowed:

- classify a pending row by grammar lane;
- explain why a row needs sarf, nahw, two-vote, owner, source-repair, or scholar review;
- build validators and fixtures for recurring grammar mistakes;
- group curriculum topics and learner drills;
- flag named-entity/common-word collisions for review.
- build a scrubbed parse-key and color-role payload for a future learner hover, using Qamus/Fusha labels rather
  than screenshot/source labels.

Not allowed:

- copying screenshot or external wording into a public hover;
- using a concept relation as a translation;
- exposing QAC, Quran.com, Tafsir Center, OCR text, screenshots, or source paths in public hover records;
- overriding sarf, nahw, i'rab, root/POS, or verse context;
- flattening homographs because a concept map has a nearby class.
- treating a QAC screenshot color, dependency tag, or English note as the public tooltip's authority.

Public hover records stay compact and qamus-authored:

```json
{"src":"qamus","kind":"authored","lang":"en"}
```

When grammar evidence is useful but not decisive, record a precise blocker
instead of authoring a weak hover.

## Parse-key and color usage

The screenshot packs show a useful visual grammar: Arabic pieces are colored and tagged (`P`, `N`, `PRON`, `V`,
`REL`, `ACC`, `PP`, `NS`, etc.), while arcs/lines show dependencies. Qamus should adopt the *idea*, not the source
payload:

1. First create or verify a source-addressed `qamus/schemas/morphosyntax-token.schema.json` record.
2. Put the learner-visible grammar breakdown in `parse_key` and `display`.
3. Use stable Qamus classes such as `qg-preposition`, `qg-pronoun`, `qg-verb`, `qg-noun`, `qg-oath`,
   `qg-comitative`, `qg-result`, `qg-relative`, and `qg-vocative`.
4. Render the public best gloss separately from the parse key. The best gloss stays short; the parse key explains
   why it is short and why attached pieces did not disappear.
5. Keep source labels and screenshot names inside internal evidence only. They may appear in `evidence.labels`,
   never in public hover text, `parse_key`, or `display`.

If the sarf/nahw decision cannot produce a parse key, the hover is not ready for the richer learner display. Leave
it pending or route to the exact blocker rather than inventing a colored explanation.
