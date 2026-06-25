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
| `يَحْفَظُونَهُ` | imperfect verb + plural subject + object `ه` | subject and object are part of the token's contribution | bare "guard" |
| `قُرْءَانًا` | noun + tanwin-alif | final `ـًا` is tanwin, not pronoun `نا` | false split into stem + "us" |
| `ٱلْمُلْك` | article + noun | article is part of the noun; no lām preposition | false split `لـ` + host |

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
