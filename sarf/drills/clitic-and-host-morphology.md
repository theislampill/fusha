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
| `وَبِالنَّجْمِ` | wāw + bā' + article + noun | route wāw/bā' to nahw; preserve both if certified | bare "star" |
| `وَالتِّينِ` | oath/conjunction wāw + article + noun | route wāw function; oath reading must preserve "by" | bare "figs" |
| `وَالزَّيْتُونِ` | wāw + article + noun | preserve oath/coordination contribution in context | bare "olives" |
| `كَأَنَّهُمْ` | kāf-like particle cluster + pronoun | do not reduce to a root of the host letters | host-root guess |
| `فَذَٰلِكُنَّ` | fā' + demonstrative + feminine plural suffix | fā' and addressed group both matter | bare "that" with no fā'/suffix |
| `جَادَلُوكَ` | verb + plural subject + `كَ` object | verb clitic is visible: "they ... you" | infinitive "to argue" |
| `أَنزَلْنَاهُ` | Form IV verb + `نا` subject + `ه` object | person/object shape belongs in the hover | bare "sent down" |
| `يَسْـَٔلُكَ` | imperfect prefix + verb stem + `كَ` object | suffix is visible: "ask you" plus parse proof | lemma-only "to ask, question" |
| `فَأَهْلَكْنَاهُمْ` | fā' + Form IV perfect 1pl verb + `هم` object | fā', subject, form, and object all matter | phrase with no component breakdown |
| `يَحْفَظُونَهُ` | imperfect verb + plural subject + object `ه` | subject and object are part of the token's contribution | bare "guard" |
| `ثَقِفْتُمُوهُمْ` | perfect verb + plural subject + object `هم` | finite verb and object matter: "you all found/came upon them" | lemma-only "to find/come upon" |
| `تُخَالِطُوهُمْ` | imperfect verb + plural subject + object `هم` | object suffix must be visible: "you mix/associate with them" | nominal/root leakage such as "partners" |
| `تُمْسِكُوهُنَّ` | imperfect verb + plural subject + object `هن` | feminine plural object belongs in the hover | bare "to hold/keep" |
| `تَكْتُبُوهَا` | imperfect verb + plural subject + object `ها` | object suffix triggers "write it/her" plus referent review | bare "to write" |
| `أَبْوَٰبِهَا` | plural noun + possessive suffix `ها` | noun-host suffix: "its doors/gates" when certified | host-only "doors" |
| `قُرْءَانًا` | noun + tanwin-alif | final `ـًا` is tanwin, not pronoun `نا` | false split into stem + "us" |
| `ٱلْمُلْك` | article + noun | article is part of the noun; no lām preposition | false split `لـ` + host |
| `وَٱلشَّجَرُ` | wāw + article + noun | rich hover teaches all three pieces | `and + the trees` as the only explanation |
| `بِٱلْمَعْرُوفِ` | bā' + article + nominal host | preposition, definiteness, and host all appear in breakdown | generic phrase with no bā' component |

## Parse-key extension

After each segmentation, produce the rich-hover handoff:

- `parse_key.key`: compact ASCII, such as `P:BI+N:GEN`, `CONJ+P:BI+ART+N:GEN:DEF`,
  or `V:IV:PERF:ACT:1P+OBJ.3MS`.
- `display classes`: one class per grammatical piece, such as `qg-preposition`,
  `qg-article`, `qg-noun`, `qg-verb`, and `qg-pronoun`.

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
