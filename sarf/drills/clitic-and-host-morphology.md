# Drill — clitic and host morphology

**Goal:** before accepting a host gloss, segment the written token into every
visible piece that carries meaning: proclitic, article, stem, suffix pronoun,
subject marker, object marker, or tanwin. A host-only answer is wrong when a
visible attached piece changes what the learner should see.

This drill trains the production closure lesson now encoded in
[`../procedures/clitic-and-host-morphology.md`](../procedures/clitic-and-host-morphology.md):
an exact/form match can still be unsafe if it bypasses clitic inspection.

## The gate

For every token, write this before you gloss:

```text
raw token:
visible pieces:
host/root/POS:
suffix or subject/object marker:
needs nahw for function? yes/no
public hover may show:
parse_key.key:
display classes:
pending reason if unsafe:
```

If the public hover only shows one best text, the best text must include the
attached piece's contribution. A hidden `pre` field is not enough for a learner.

## Items

| token | segmentation to name | safe lesson | reject this |
|---|---|---|---|
| `بِسْمِ` | `بِـ` + host noun `اسم` | bā' contributes "in/with"; host is majrur | host-only "name" |
| `بِسَلَامٍ` | `بِـ` + host noun `سلام` | bā' contributes the relation; host is majrur | host-only "peace" |
| `بِبَدْرٍ` | `بِـ` + place name `بدر` | bā' contributes locative/contextual relation | host-only "Badr" |
| `لِلَّهِ` | `لِـ` + article + proper noun | lām contributes "for/to/belonging to" in context | host-only "Allah" |
| `بِذُنُوبِهِمْ` | bā' + plural noun + possessive suffix | preposition and "their" both matter | "sins" with no bā' or pronoun |
| `بِذُنُوبِكُم` | bā' + plural noun + possessive suffix | preposition and "your" both matter | suffix-pending with no bā' lane |
| `بِرُوحِ` | bā' + host noun | bā' relation and referent review both matter | host-only "spirit" |
| `بِبَابِلَ` | bā' + proper place name | bā' contributes locative/contextual relation | host-only "Babylon" |
| `وَبِالنَّجْمِ` | wāw + bā' + article + noun | route wāw/bā' to nahw; preserve both if certified | bare "star" |
| `وَالتِّينِ` | oath/conjunction wāw + article + noun | route wāw function; oath reading must preserve "by" | bare "figs" |
| `وَالزَّيْتُونِ` | wāw + article + noun | preserve oath/coordination contribution in context | bare "olives" |
| `وَطُورِ` | oath/conjunction wāw + host/place noun | oath reading must preserve "by Mount" | host-only "Mount" |
| `وَهَٰذَا` | oath/conjunction wāw + demonstrative | frame plus demonstrative both matter | bare "this" with no oath/coordination |
| `كَأَنَّهُمْ` | kāf-like particle cluster + pronoun | do not reduce to a root of the host letters | host-root guess |
| `فَذَٰلِكُنَّ` | fā' + demonstrative + feminine plural suffix | fā' and addressed group both matter | bare "that" with no fā'/suffix |
| `جَادَلُوكَ` | verb + plural subject + `كَ` object | verb clitic is visible: "they ... you" | infinitive "to argue" |
| `أَنزَلْنَاهُ` | Form IV verb + `نا` subject + `ه` object | person/object shape belongs in the hover | bare "sent down" |
| `يَسْـَٔلُكَ` | imperfect prefix + verb stem + `كَ` object | suffix is visible: "ask you" plus parse proof | lemma-only "to ask, question" |
| `فَأَهْلَكْنَاهُمْ` | fā' + Form IV perfect 1pl verb + `هم` object | fā', subject, form, and object all matter | phrase with no component breakdown |
| `يَحْفَظُونَهُ` | imperfect verb + plural subject + object `ه` | subject and object are part of the token's contribution | bare "guard" |
| `ظَلَمُونَا` | perfect verb + plural subject + object `نا` | object suffix contributes "us/Us"; referent decides casing | root-only "to wrong" |
| `وَيُرِيكُمْ` | wāw + Form IV imperfect verb + object `كم` | conjunction/resumption, causative form, and "you" all need proof | broad "see/show" family |
| `وَيُعَلِّمُكُمُ` | wāw + Form II imperfect verb + object `كم` | Form II teaching sense and object suffix both matter | omnibus "know/teach/learn" |
| `ثَقِفْتُمُوهُمْ` | perfect verb + plural subject + object `هم` | finite verb and object matter: "you all found/came upon them" | lemma-only "to find/come upon" |
| `تُخَالِطُوهُمْ` | imperfect verb + plural subject + object `هم` | object suffix must be visible: "you mix/associate with them" | nominal/root leakage such as "partners" |
| `تُمْسِكُوهُنَّ` | imperfect verb + plural subject + object `هن` | feminine plural object belongs in the hover | bare "to hold/keep" |
| `تَكْتُبُوهَا` | imperfect verb + plural subject + object `ها` | object suffix triggers "write it/her" plus referent review | bare "to write" |
| `تُبَٰشِرُوهُنَّ` | imperfect verb + object `هن` | contextual wording must still expose the feminine plural object | action phrase with no `هُنَّ` proof |
| `تَجِدُوهُ` | imperfect verb + object `ه` | "it/him" belongs in the token contribution | bare "to find" |
| `أَبْوَٰبِهَا` | plural noun + possessive suffix `ها` | noun-host suffix: "its doors/gates" when certified | host-only "doors" |
| `شَيَٰطِينِهِمْ` | plural noun host + possessive suffix `هم` | preserve plural host and "their"; concept prose belongs elsewhere | concept paragraph or host-only "devils" |
| `أُجُورَكُمْ` | plural noun host + possessive suffix `كم` | preserve "your" before entry-family prose | generic "reward" with no possessor |
| `قُرْءَانًا` | noun + tanwin-alif | final `ـًا` is tanwin, not pronoun `نا` | false split into stem + "us" |
| `دِهَاقًۭا` | noun/adjective + tanwīn/case | no suffix pronoun exists; detector must not invent one | treating case/tanwīn as an object suffix |
| `ٱلْمُلْك` | article + noun | article is part of the noun; no lām preposition | false split `لـ` + host |
| `وَٱلشَّجَرُ` | wāw + article + noun | rich hover teaches all three pieces | `and + the trees` as the only explanation |
| `بِٱلْمَعْرُوفِ` | bā' + article + nominal host | preposition, definiteness, and host all appear in breakdown | generic phrase with no bā' component |
| `يَابِسٍ` | one lexical adjective/noun host, not `يا` + host | yā is part of the stem; keep the token out of the vocative lane | false vocative split from `startswith("يا")` |
| `يَابِسَٰتٍ` | one lexical feminine plural host | stem letters stay together before nahw routing | false vocative/addressee split |
| `أُورِثْتُمُوهَا` | passive verb host + 2mp subject/deputy-subject marker + object `ها` | passive, addressee group, and object must all be visible | host-only "inherited" |
| `بُرْهَٰنَانِ` | noun host + dual suffix | dual is visible morphology and belongs in the display contract | one plain noun span |
| `قاعدون` | participial/adjectival host + sound plural ending | plural ending changes the learner-facing contribution | unmarked "sitting" |
| `مُّطَاعٍۢ` | derivative/participial host shape | adjective/passive participle, not an infinitive | "to obey" |
| `يُحْيِي` | imperfect prefix + verb stem | prefix and stem need distinct roles | one undifferentiated verb span |

## Parse-key extension

After each segmentation, produce the rich-hover handoff:

- `parse_key.key`: compact ASCII, such as `P:BI+N:GEN`, `CONJ+P:BI+ART+N:GEN:DEF`,
  or `V:IV:PERF:ACT:1P+OBJ.3MS`.
- `display classes`: one class per grammatical piece, such as `qg-preposition`,
  `qg-article`, `qg-noun`, `qg-verb`, and `qg-pronoun`. When exact morphology is known, prefer role-aware classes:
  `qg-verb-prefix`, `qg-verb-stem`, `qg-subject-pronoun`, `qg-object-pronoun`, `qg-noun-stem`,
  `qg-adjective`, `qg-dual-suffix`, `qg-plural-suffix`, and `qg-derivative-prefix`.

If the class would depend on nahw (`و` as oath/comitative/conjunction, `ف` as cause/result,
`ل` as purpose/imperative/genitive), write `pending: particle_function_uncertified` instead of
choosing a color by surface shape.

## Decision rule

- If segmentation is clear and the host/root/POS is certified, hand the function
  pieces to nahw and author only when the visible contribution is preserved.
- If the host is certified but the attached preposition, particle, or pronoun
  function is not, emit a precise pending such as
  `preposition_role_uncertified`, `verb_suffix_role_uncertified`, or
  `particle_function_uncertified`.
- If segmentation itself is uncertain, keep the row pending; do not let `norm()`
  choose the root.

## Graduation check

Take ten covered hover rows and ten pending rows. For each, prove that no visible
attached piece disappeared from the learner-facing answer. Any host-only hover
on a token with a visible bā', lām, kāf, oath/comitative wāw, fā', or suffix
pronoun fails the drill.
For rich-hover readiness, the answer must also include a parse key and exactly one
display class for each grammatical piece. The UI may keep the written Arabic word atomic;
the classes still prove that no proclitic, article, stem, or suffix vanished.

Dogfood batch check: for the 2026-06-27 known-defect rows, write a
`skill_impact` note for each repeated class. If sarf already has the rule, say
which procedure/eval enforces it; if not, add the rule before routing the row
back to Qamus data repair.

## Qamustyping4 visual morphology check

These rows are the final all-qword regression samples. They are not new live
claims; they are the fixture-backed minimum that prevents a future agent from
calling a card complete while visible morphology is still hidden.

| token | required visible pieces | unsafe shortcut |
|---|---|---|
| `تَعْبُدُوا۟` | `تَ` imperfect prefix + `عْبُدُ` stem + `وا۟` plural subject marker | one verb-colored span with only "worship" |
| `تَكُونَ` | imperfect prefix + stem, then nahw governor/mood if relevant | bare "there be" with no governed-verb proof |
| `يَهْتَدُوا۟` | `يَ` prefix + Form VIII stem + plural subject marker | "they were guided" with no prefix/subject display |
| `جَاهَدَاكَ` | finite verb host + attached `كَ` object | "strive" without "you" |
| `وَمَلَـٰٓئِكَتِهِۦ` | wāw + plural noun host + possessive suffix | host-only "angels" |
| `ءَادَمَ` / `عِمْرَٰنَ` / `جِبْرِيلَ` | proper-name/no-root terminal state | inventing a root to satisfy a field |

Rule: qamustyping4 rows fail sarf readiness when a visible prefix, suffix,
object, subject marker, article, or no-root status is absent from the teaching
layer, even if the English hover sounds acceptable.
