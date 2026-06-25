# Verb Suffix Omission Scan - 2026-06-25

Status: read-only subagent scan, not bulk-applied. This is a queue for source-triangulated repair, not a claim that all rows are certified.

## Finding

A scan of `out/hover_stage/wbw-lookup.json` found 1,128 likely verb-suffix/object omissions. These are cases where a verb token has attached subject/object morphology but the current hover is a bare lemma, pending suffix row, or otherwise omits visible pronoun contribution.

The same Andon class was live-confirmed by `جَادَلُوكَ`, `يَحْفَظُونَهُۥ`, and earlier bāʾ/host-only rows: the visible hover text must account for the token's actual composition.

## Top Candidates

| loc | surface | current hover/state | missing contribution |
|---|---|---|---|
| 26:139:2 | فَأَهْلَكْنَاهُمْ | PENDING:suffix | we + them |
| 37:148:1 | فَمَتَّعْنَاهُمْ | PENDING:suffix | we + them |
| 26:198:2 | نَزَّلْنَاهُ | PENDING:suffix | we + it |
| 37:101:1 | فَبَشَّرْنَاهُ | PENDING:suffix | we + him |
| 37:145:1 | فَنَبَذْنَاهُ | PENDING:suffix | we + him |
| 54:13:1 | وَحَمَلْنَاهُ | PENDING:suffix | we + him |
| 90:10:1 | وَهَدَيْنَاهُ | PENDING:suffix | we + him |
| 95:5:2 | رَدَدْنَاهُ | PENDING:suffix | we + him |
| 23:29:2 | أَنْزِلْنِي | PENDING:suffix | me |
| 4:16:2 | يأتيانها | PENDING:suffix | her/it |
| 33:14:9 | لَءَاتَوْهَا | PENDING:suffix | her/it |
| 2:191:3 | ثَقِفْتُمُوهُمْ | to find/come upon in battle | you all + them |
| 47:4:9 | أَثْخَنتُمُوهُمْ | to subdue (an enemy in battle) | you all + them |
| 9:24:10 | ٱقْتَرَفْتُمُوهَا | to commit or earn | you all + it |
| 2:73:8 | وَيُرِيكُمْ | to see / show someone | you all |
| 2:159:17 | يَلْعَنُهُمُ | to condemn, curse | them |
| 2:220:22 | لَأَعْنَتَكُمْ | to make difficult | you all |
| 2:237:6 | تَمَسُّوهُنَّ | to touch one's spouse | them feminine |
| 2:251:1 | فَهَزَمُوهُم | to defeat | them |
| 2:260:22 | فَصُرْهُنَّ | to cut into pieces | them feminine |
| 3:28:22 | وَيُحَذِّرُكُمُ | to warn someone | you all |
| 3:49:7 | جِئْتُكُم | to come / come with | you all |
| 3:103:26 | فَأَنقَذَكُم | to save | you all |
| 3:118:10 | يَأْلُونَكُمْ | to fall short / spare no effort | you all |
| 3:152:6 | تَحُسُّونَهُم | to finish someone off | them |
| 3:153:18 | فَاتَكُمْ | to miss/escape | you all |
| 3:154:14 | أَهَمَّتْهُمْ | to be disturbed/worried | them |
| 3:159:19 | وَشَاوِرْهُمْ | to consult | them |
| 3:160:8 | يَخْذُلْكُمْ | to abandon | you all |
| 4:11:1 | يُوصِيكُمُ | to instruct/command | you all |

## Heuristic

The scan joined the WBW artifact to QAC token roots and kept QAC `POS=V`. It matched attached suffixes such as `كم`, `هم`, `هن`, `هما`, `ني`, `نا`, `ها`, `ه`, and `ك`, guarded weak-final and root-final false positives, and flagged resolved hovers only when the expected English pronoun contribution was absent.

## Next Lane

Use Tafsir MCP/QAC/source triangulation to certify batches. Each applied row should record:

- loc, surface, authored hover
- form/voice/aspect/person/number/gender
- subject and object suffix roles
- internal evidence labels
- public boundary `{src:qamus, kind:authored}`

Rows with `ـنا` need special review because it can be subject "we" or object "us".
