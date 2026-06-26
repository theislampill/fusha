# Live Rich-Hover Renderer Acceptance - 2026-06-26

Status: verified against public Qamus entry pages after the rich-hover renderer/data-contract update and the
visible-segment browser repair. This report records the acceptance shape only; it does not copy live app source,
deploy scripts, private paths, external source wording, or production credentials.

## Contract Accepted

Rich WBW hover rendering is not satisfied by fallback strings such as `and + the sun`. A certified rich token
needs all of the following in the rendered DOM:

- visible `.qg-seg` spans for grammatical pieces of the written token;
- function-aware classes such as `qg-conjunction`, `qg-article`, `qg-noun`, `qg-result`, `qg-verb`,
  `qg-verb-prefix`, `qg-verb-stem`, `qg-pronoun`, `qg-vocative`, and `qg-preposition`;
- a tooltip parse-key element (`.qg-parse-key`);
- tooltip breakdown rows that account for each visible piece;
- no public source/provenance labels in word HTML or tooltip HTML.

## Passing Live Cases

| Loc | Surface | Required composition | Parse key observed |
|---|---|---|---|
| 22:18:13 | `وَٱلشَّمْسُ` | conjunction + article + noun | `CONJ+ART+N:NOM:DEF:SG` |
| 22:18:14 | `وَٱلْقَمَرُ` | conjunction + article + noun | `CONJ+ART+N:NOM:DEF:SG` |
| 26:139:2 | `فَأَهْلَكْنَاهُمْ` | result particle + Form IV verb + object pronoun | `RESULT+V:IV:PERF:ACT:1P+OBJ.3MP` |
| 2:21:1 | `يَا` / `أَيُّهَا` | vocative particle + addressee formula | `VOC:YAA+AYYUHA` |
| 33:63:1 | `يَسْأَلُكَ` | imperfect prefix + Form I stem + 2ms object pronoun | `V:I:IMPF:ACT:3MS+OBJ.2MS` |
| 2:178:22 | `بِٱلْمَعْرُوفِ` | attached bāʾ + article + genitive noun host | `P:BI+ART+N:GEN:DEF` |

The lookup data also carries Qamus-authored rich metadata for nearby `22:18:15`-`22:18:17` conjunction/article/noun
tokens, but this report does not count them as public-page DOM acceptance because the current inspected public entry
pages did not expose those locs as rendered examples.

## Verification Shape

Browser readback asserted, for each named public-page case:

- at least one rendered `.qword[data-loc="..."]`;
- `.qg-seg` spans inside the word;
- expected grammar classes in the word spans;
- tooltip `.qg-seg` spans after hover;
- tooltip `.qg-parse-key` containing the expected parse key;
- expected learner-facing gloss text, including `ask you` for `33:63:1`;
- no public DOM leakage of external source/provenance labels.

The blocking exemplar `33:63:1` specifically exposed `يَـ`, `سْـَٔلُ`, and `كَ` as `qg-verb-prefix`,
`qg-verb-stem`, and `qg-pronoun` segments, with `كَ` contributing `you`; the former lemma gloss
`to ask, question` is no longer acceptable for that token. The split vocative `2:21:1` readback also
confirmed `يَا` as `O` and `أَيُّهَا` as `you (who)`.

## Runner Boundary

The durable live probe is a browser/DOM check: it requires Playwright in the runner environment and inspects public
pages, rendered word nodes, hover tooltips, classes, and parse keys. A server without Playwright can still host the
checked-in probe, but the current evidence came from a Playwright-enabled local browser run against the public site.

## Boundary

This report is a renderer/data-contract acceptance note. It is not a claim that every one of the 2,092 Qamus
entries now has complete rich metadata. Remaining closure still needs the same source-clean, token-addressed
pipeline: certify morphology and syntax, author original Qamus hover text, emit parse-key/display metadata, and
leave uncertain cases precisely pending. It is also not a claim that every certified lookup loc is currently visible
on a public entry page.
