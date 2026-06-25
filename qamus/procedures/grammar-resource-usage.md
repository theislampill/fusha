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

Not allowed:

- copying screenshot or external wording into a public hover;
- using a concept relation as a translation;
- exposing QAC, Quran.com, Tafsir Center, OCR text, screenshots, or source paths in public hover records;
- overriding sarf, nahw, i'rab, root/POS, or verse context;
- flattening homographs because a concept map has a nearby class.

Public hover records stay compact and qamus-authored:

```json
{"src":"qamus","kind":"authored","lang":"en"}
```

When grammar evidence is useful but not decisive, record a precise blocker
instead of authoring a weak hover.
