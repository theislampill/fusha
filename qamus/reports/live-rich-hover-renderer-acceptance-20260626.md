# Live Rich-Hover Renderer Acceptance - 2026-06-26

Status: verified against public Qamus entry pages after the rich-hover renderer/data-contract update. This
report records the acceptance shape only; it does not copy live app source, deploy scripts, private paths,
external source wording, or production credentials.

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
| 22:18:13 | `وَٱلشَّمْسُ` | conjunction + article + noun | `CONJ+ART+N:DEF:NOM` |
| 22:18:14 | `وَٱلْقَمَرُ` | conjunction + article + noun | `CONJ+ART+N:DEF:NOM` |
| 22:18:15 | `وَٱلنُّجُومُ` | conjunction + article + noun | `CONJ+ART+N:DEF:NOM:PL` |
| 22:18:16 | `وَٱلْجِبَالُ` | conjunction + article + noun | `CONJ+ART+N:DEF:NOM:PL` |
| 22:18:17 | `وَٱلشَّجَرُ` | conjunction + article + collective noun | `CONJ+ART+N:DEF:NOM:COLL` |
| 26:139:2 | `فَأَهْلَكْنَاهُمْ` | result particle + Form IV verb + object pronoun | `RES+V:IV:PERF:ACT:1P+OBJ.3MP` |
| 2:21:1 | `يَا` / `أَيُّهَا` | vocative particle + addressee formula | `VOC:YAA+AYYUHA` |
| 33:63:1 | `يَسْأَلُكَ` | imperfect prefix + Form I stem + 2ms object pronoun | `V:I:IMPF:ACT:3MS+OBJ.2MS` |
| 2:178:22 | `بِٱلْمَعْرُوفِ` | attached bāʾ + article + genitive noun host | `P:BI+ART+N:GEN:DEF` |

## Verification Shape

Browser readback asserted, for each named case:

- at least one rendered `.qword[data-loc="..."]`;
- `.qg-seg` spans inside the word;
- expected grammar classes in the word spans;
- tooltip `.qg-seg` spans after hover;
- tooltip `.qg-parse-key` containing the expected parse key;
- expected learner-facing gloss text;
- no public DOM leakage of external source/provenance labels.

The blocking exemplar `33:63:1` specifically exposed the suffix `كَ` as its own `qg-pronoun` segment with
the contribution `you`, so the former lemma gloss `to ask, question` is no longer acceptable for that token.

## Boundary

This report is a renderer/data-contract acceptance note. It is not a claim that every one of the 2,092 Qamus
entries now has complete rich metadata. Remaining closure still needs the same source-clean, token-addressed
pipeline: certify morphology and syntax, author original Qamus hover text, emit parse-key/display metadata, and
leave uncertain cases precisely pending.
