# Dogfood-to-Curriculum Crosswalk - 2026-06-27

Status: repo-only consolidation. This report maps completed particle dogfood, VN-00 through VN-20 dogfood, the
post-VN `sarfnahw` audit, P-RICH / VN-RICH rich-hover metadata work, source-triangulation failures, renderer
Andons, and Phase 4 review-only artifacts into durable teaching surfaces. It does not mutate live Qamus, rebuild
WBW, restart services, sync mirrors, or apply hover decisions.

## Method

Git history was used only as an index. Canonical inputs were the committed reports, procedures, drills, eval
fixtures, production-bug lesson samples, controller tables, rich-hover samples, and validation reports.

Public-facing curriculum wording below is Qamus/Fusha-authored. External screenshots, QAC-style morphology,
Quran.com, Tafsir MCP, lexicons, and source photos remain internal evidence only unless a separate source-boundary
rule explicitly allows public citation.

## Crosswalk

| repeated finding | phases | examples | concept | already taught | action |
|---|---|---|---|---|---|
| flat English hover is not rich certification | particle, VN, RICH | `peace`, `Badr`, `ask` | gloss string vs grammar state | `qamus-hover-parse-key-and-color.md` | update roadmap/session protocol; add assessment fixture |
| readable English with wrong reasoning | GrammarProblems, VN-RICH | case/mood/i'rab items | answer and reason must agree | `grammar-risk-gate.md` | add two-vote tutoring clearance rule |
| finite verb inheriting dictionary infinitive prose | VN | `قَالُوا`, `فَأَهْلَكْنَاهُمْ`, `يَسْأَلُكَ` | finite verb features | sarf stages 3-4 | add sarf remediation drill and checkpoint fixture |
| finite verb person/number/gender | VN, VN-RICH | `قَالُوا`, `ظَلَمُونَا` | PNG agreement | sarf verb procedures | cross-link in sarf map |
| active/passive voice | VN, sarfnahw | `خُلِقَ`, passive VN rows | voice from vowel pattern | sarf curriculum | add drill index target |
| weak/hamzated/doubled verbs | VN, sarfnahw | `قَالَ`, `زَاغَ`, `خَفَّت` | hidden radicals | sarf curriculum | no-op: already represented; cross-link |
| verb form/measure | VN, sarfnahw | Form I/II/IV contrasts | measure changes meaning | sarf procedures | cross-link to drill |
| suffix-bearing verbs | VN, Phase 4 | `يَسْأَلُكَ`, `جَادَلُوكَ` | host + object pronoun | sarf/nahw pronoun procedures | add assessment fixture |
| attached object/addressee pronouns | VN, Phase 4 | `كَ`, `هُمْ` suffixes | role depends on host POS | suffix-pronoun evals | add missed-error category |
| suffix pronoun referents | VN, nahw | `بَيْنَهُمْ`, `يَوْمِكُمْ` | referent-sensitive wording | `pronoun-attachment.md` | add two-vote clearance condition |
| noun/verb/POS collisions | VN | `رَسُولًا`, `ذِكْر` | POS before gloss | sarf procedures | cross-link in sarf map |
| nominal derivatives | VN | maṣdar/participle rows | noun-shaped derivation | sarf stage 6 | add drill index target |
| maṣdar vs finite verb | VN | `ذِكْر`, `إيمان` | nominal action vs verb | sarf curriculum | add fixture row |
| participles / ṣifa | VN, sarfnahw | `مُعَلِّم`, `مُعَلَّم`, ṣifa rows | derivative adjective/noun | sarf/nahw drills | cross-link |
| proper/common noun collisions | VN, QAC concept map | `صالح`, `مريم`, places | name flag is not translation | proper-noun procedure | add advanced unit target |
| scripture/group/name collisions | VN | book/group/place rows | concept metadata internal only | source-boundary docs | no-op: represented; cross-link |
| body-part and relational nouns | VN, sarfnahw | `يد`, `وجه`, `صدر` style rows | relational noun context | VN synthesis | add learner drill route |
| iḍāfa | VN, nahw | `كتاب الله`, body-part constructs | relationship not isolated word | nahw stage 4 | add checkpoint route |
| jar-majrūr | particle, VN | `بِسَلَامٍ`, `بِبَدْرٍ` | preposition + governed object | nahw stage 2 | add assessment fixture |
| PP attachment | particle, VN-RICH | hidden hāl/ṣifa, verb attachment | attachment affects English | `pp-attachment-review.md` | add two-vote clearance rule |
| preposition-host relation | particle, VN | `بِـ`, `لِـ`, `كَـ` host rows | attached relation cannot vanish | clitic drill | add sarf/nahw remediation maps |
| bāʾ contribution | particle, RICH | `بِسَلَامٍ`, `بِبَدْرٍ` | with/in/by/at by context | hover composition drill | add fixture row |
| lām contribution | particle, RICH | `لِمَا`, lām-on-verb | preposition/purpose/command/mood | nahw procedures | add nahw remediation drill |
| wāw/fāʾ relation | particle, RICH | conjunction, oath, causal/result | function is context-sensitive | function-token procedure | add assessment row |
| hamza/question particle | particle, sarfnahw | interrogative/equalization hamza | particle function | nahw procedure | cross-link |
| `مَا` function | particle, RICH | negative, relative, interrogative, maṣdariyyah | function by frame | `ma-function-decision.md` | add fixture row |
| `وَمَا` decomposition and function | particle, RICH | one token, multiple pieces | written token vs grammar pieces | hover composition drill | add fixture row |
| `لِمَا` | particle | lām + classified mā | preposition plus function word | nahw procedures | add drill route |
| `لَمَّا` | particle | temporal/negative/context rows | shadda/context distinction | homograph drills | cross-link |
| `إِلَّا` | particle | exception frames | mustathnā frame | exception/vocative procedure | add hard two-vote fixture |
| `لَا` | particle | simple negation/prohibition/nafy jins | negation governs case/mood | negation procedure | cross-link |
| `لَمْ` | particle | jussive past negation | mood changes tense | negation procedure | add fixture row |
| `لَنْ` | particle | future negation + subjunctive | mood/function | negation procedure | cross-link |
| relative/interrogative/conditional particles | particle, RICH | `مَنْ`, `مَا`, `إِنْ`, `إِذَا` | clause relation | nahw stage 7 | cross-link |
| negation | particle | `ما`, `لا`, `لم`, `لن` | polarity plus grammar effect | nahw procedures | add assessment fixture |
| vocative | particle, RICH | `يَا`, `أَيُّهَا` | address frame split | exception/vocative procedure | add hard fixture |
| exception | particle, RICH | `إلا` rows | negative/positive frame | exception procedure | add hard fixture |
| oath | particle | oath wāw | preposition-like role | function-token procedure | add rich-hover drill route |
| token-only overrides | VN | surface-family siblings diverge | exact address beats surface | source-address graph docs | add progress/missed-error field |
| component-only evidence cannot certify whole token | RICH | article/preposition candidates | component candidates are evidence only | morphosyntax contract | add assessment fixture |
| renderer-only segmentation | RICH renderer | colored Arabic/tooltip rows | display metadata not proof | renderer contract | add rich-hover curriculum note |
| parse-key/display segments as semantic records | RICH | `display.segments[]` | grammar records, not word splitting | parse-key guide | add session protocol cue |
| source-locator drift | source-triangulation | stale loc/source rows | exact address required | source-address reports | add blocker route |
| same-verse duplicate/function-token collision | particle | repeated function tokens | surface alone unsafe | graph/parse-key docs | cross-link |
| source agreement still unsafe if clitic/preposition omitted | source-triangulation | external gloss agrees but loses bāʾ/suffix | grammar contribution required | grammar-risk gate | add no-copy/no-certify note |
| root-family vibes are not evidence | VN, sarfnahw | same root/POS collisions | root proposes, state certifies | sarf stage 7 | add answer-key forbidden reasoning |

## Target Files Updated In This Pass

- General curriculum: `README.md`, `zero-to-fluency-roadmap.md`, `mastery-checkpoints.md`,
  `tutor-runtime-routing.md`, `tutor-session-protocol.md`.
- Assessment/progress: `curriculum/assessment/*`, `curriculum/progress/*`.
- Drill indexes: `curriculum/drills/dogfood-error-remediation-index.md`,
  `sarf/drills/dogfood-sarf-remediation.md`, `nahw/drills/dogfood-nahw-remediation.md`.
- Skill maps: `sarf/curriculum/dogfood-sarf-map.md`, `nahw/curriculum/dogfood-nahw-map.md`.

## Explicit No-Op Reasons

- RICH sample generation: already complete through VN-RICH-20; this pass cross-links it instead of producing more.
- Live renderer behavior: not changed here; renderer requirements stay documented and owner-gated.
- Live hover decisions: not changed here; Phase 4 examples remain review-only, `apply_allowed=false`.
- External source prose: not imported; only internally learned structures are rewritten into Qamus/Fusha wording.
- Installed skill trees: manifests already include `sarf/curriculum`, `sarf/drills`, `nahw/curriculum`, and
  `nahw/drills`; this pass documents the project-pack boundary rather than copying live installs.
