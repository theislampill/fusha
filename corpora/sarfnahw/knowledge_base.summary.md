# Sarf/Nahw knowledge base — summary (SN3)

Normalized, deduped concept base distilled from the APKG vocab decks + verb-chart structure.
Concepts carry source refs + review status; the full vocabulary stays git-ignored under `corpora/sarfnahw/out/`. Only linguistic *features* are committed.

| metric | value |
|---|---:|
| concepts | 28 |
| APKG notes scanned | 1132 |
| distinct singular→plural pairs | 451 |
| gender-tagged nouns (m/f) | 338 / 246 |

## Concepts by topic

| topic | n |
|---|---:|
| verb_measure | 10 |
| verb_class | 7 |
| plural_pattern | 7 |
| gender | 1 |
| particle | 1 |
| preposition | 1 |
| pronoun | 1 |

## Concept index

| concept_id | label | examples | review |
|---|---|---:|---|
| `sarf:verb-measure:I` | فَعَلَ — Form I | 3 | curated |
| `sarf:verb-measure:II` | فَعَّلَ — Form II | 4 | curated |
| `sarf:verb-measure:III` | فَاعَلَ — Form III | 3 | curated |
| `sarf:verb-measure:IV` | أَفْعَلَ — Form IV | 4 | curated |
| `sarf:verb-measure:V` | تَفَعَّلَ — Form V | 3 | curated |
| `sarf:verb-measure:VI` | تَفَاعَلَ — Form VI | 3 | curated |
| `sarf:verb-measure:VII` | اِنْفَعَلَ — Form VII | 3 | curated |
| `sarf:verb-measure:VIII` | اِفْتَعَلَ — Form VIII | 4 | curated |
| `sarf:verb-measure:IX` | اِفْعَلَّ — Form IX | 3 | curated |
| `sarf:verb-measure:X` | اِسْتَفْعَلَ — Form X | 4 | curated |
| `sarf:verb-class:quadriliteral` | فَعْلَلَ — Quadriliteral فَعْلَلَ | 3 | curated |
| `sarf:verb-class:geminate` | Geminate مضاعف — Geminate مضاعف | 4 | curated |
| `sarf:weak-verb:hamzated` | المهموز — Hamzated verb | 1 | curated |
| `sarf:weak-verb:doubled` | المضاعف — Doubled verb | 1 | curated |
| `sarf:weak-verb:assimilated` | المثال — Assimilated verb | 1 | curated |
| `sarf:weak-verb:hollow` | الأجوف — Hollow verb | 1 | curated |
| `sarf:weak-verb:defective` | الناقص — Defective verb | 1 | curated |
| `sarf:plural:broken_plural_afʿaal` | وزن أَفْعَال — broken plural afʿaal | 8 | needs_review |
| `sarf:plural:broken_plural_fiʿaal` | وزن فِعَال — broken plural fiʿaal | 8 | needs_review |
| `sarf:plural:broken_plural_fuʿul` | وزن فُعُل — broken plural fuʿul | 8 | needs_review |
| `sarf:plural:broken_plural_fuʿuul` | وزن فُعُول — broken plural fuʿuul | 8 | needs_review |
| `sarf:plural:broken_plural_other` | جمع تكسير (نمط آخر) — broken plural other | 8 | needs_review |
| `sarf:plural:sound_feminine_plural` | جمع مؤنث سالم — sound feminine plural | 8 | needs_review |
| `sarf:plural:sound_masculine_plural` | جمع مذكر سالم — sound masculine plural | 8 | needs_review |
| `sarf:noun-gender` | المذكر / المؤنث — noun gender | 0 | needs_review |
| `nahw:function-word:particle` | الحروف / الأدوات — particle inventory (corpus-attested) | 2 | needs_review |
| `nahw:function-word:preposition` | حروف الجر — preposition inventory (corpus-attested) | 8 | needs_review |
| `nahw:function-word:pronoun` | الضمائر — pronoun inventory (corpus-attested) | 3 | needs_review |

> `needs_review` concepts are corpus-derived (vocab pairs, function words) pending linguist/owner sign-off; `curated` concepts are the authored verb measures/classes. Feeds SN4/SN5 skills and SN6 candidate generation.
