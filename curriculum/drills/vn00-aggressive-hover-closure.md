# VN-00 Aggressive Hover Closure Drills

These drills convert VN-00 false-closure families into reusable Fusha practice.
They are not a live Qamus apply plan. A row passes only when the learner can
name the visible Arabic pieces and explain why the old hover/color state was
not closure.

## Sarf Families

| class | prompt | pass condition | reject |
|---|---|---|---|
| `missing_root_in_hover` | For `يُؤْمِنۢ`, identify the imperfect prefix, Form IV stem, and root family. | root and stem are visible in the parse line and color segments | a fluent "believes" hover with no root/stem |
| `stem_only_hover_or_root_not_asserted` | On a root page such as `ر أ ى`, explain why `وَتَرَى` cannot hide the root. | wāw, prefix, weak-root stem, and source-address link are all named | "root not asserted" while the entry page knows the root |
| `hidden_suffix_or_plural` | For `أَقْسَمْتُمْ`, mark the subject suffix and person/number. | `تُمْ` is visible as second masculine plural subject | a whole-token color span that hides `تُمْ` |
| `hidden_suffix_or_pronoun` | For `تَمْسَسْكُمْ`, distinguish the stem from the object pronoun. | geminate root/stem and `كُمْ` are both explained | "touch" with no "you all" contribution |
| `hidden_prefix_or_derivative` | For `مُتَّكِـِٔينَ`, identify the derivative prefix and plural ending. | derivative shape and masculine plural oblique suffix are visible | a stem-only participle hover |
| `root_present_but_pattern_or_derivative_not_segmented` | For `لِمُؤْمِنٍ` or `مَأْمَنَهُۥ`, show the relation prefix or place/derivative pattern plus the root family. | root/pattern facts are visible in segments, not merely prose | "believer" or "place of safety" with the teachable pattern hidden |
| `root_present_but_nominal_pattern_not_segmented` | For `أَمَٰنَتَهُۥ`, identify the root family, nominal pattern, and attached pronoun. | nominal formation and pronoun are separately learner-visible | a whole-token "his trust" hover only |
| `nominal_ta_morphology_hidden` | For `أَمَٰنَتَهُۥ`, explain the nominal tāʾ before the pronoun. | the tāʾ is taught as word-formation material, not swallowed by the host | host plus pronoun with no nominal formation note |
| `broken_plural_underexplained` | For `أَوْلِيَآءُ`, explain why a plural-shaped noun cannot be a bare singular host. | broken plural/lexical family and plural meaning are represented | a plain "allies/protectors" hover without morphology |
| `uncolored_or_flat_qword` | For `تَكْسِبُونَ`, decide whether the row can be called closed. | no: it must first gain qg color and rich-hover segmentation | packeted/terminal row treated as public closure |

## Nahw Families

| class | prompt | pass condition | reject |
|---|---|---|---|
| `article_or_proclitic_not_explained` | For `وَٱلشَّمْسَ`, show the wāw, article, and host. | every visible function piece contributes to the hover | host-only "sun" |
| `common_particle_role_underexplained` | For `هَلْ`, state the function. | question particle role is explicit | generic particle color with no question function |
| `common_particle_transclusion_miss` | For `لَهُۥٓ` or `وَمَا`, explain why solved peers do not auto-close it. | same-surface reuse is allowed only after context/function checks | blind particle table propagation |
| `preposition_pronoun_undersegmented` | For `فِيهَآ` and `دُونِهِمْ`, name the relation and pronoun. | relation plus attached pronoun are both learner-visible | preposition or pronoun hidden in a phrase gloss |
| `token_gloss_wrong_or_phrase_only` | For `بِجُنُودٍ`, separate the token pieces from any phrase translation. | the token hover teaches bāʾ, host, and ending; phrase context is traceable | readable English with hidden Arabic pieces |

## v003 Addendum

The v003 representatives are terminal regression examples: `لِمُؤْمِنٍ`,
`أَوْلِيَآءُ`, `يُرِيدُونَ`, `أَن`, `يَأْمَنُوكُمْ`,
`وَيَأْمَنُوا۟`, `قَوْمَهُمْ`, `مَأْمَنَهُۥ`, and
`أَمَٰنَتَهُۥ`. A learner or page worker must reject any hover that hides
the suffix/pronoun/plural, derivative or place prefix, nominal tāʾ, broken
plural morphology, common-particle role, or token pieces behind a phrase-only
translation.

## batch05a Postdeploy Gate

Batch05a representatives are terminal projection examples, not advisory notes:
`كَفَرَ`, `مُؤْمِنٌ`, `سَيِّـَٔاتِهِۦ`, `كُفَّارٌ`, `لَكَفَّرْنَا`,
`بِكُفْرِهِمْ`, `لَعَنَهُمُ`, `شَكَرْتُمْ`, `عَمَلًا`, `مَلِكِ`, `كَوْكَبًۭا`,
and `ءَايَةٍۢ`.
Reject any public hover that passes changed-row readback but still hides the
root/stem, derivative prefix, function prefix, attached pronoun, source-clean
fact, source-crosswalk agreement, richer peer payload, or visible final mark
from the learner-facing projection. A page remains not complete until the full
page passes the false-closure audit and the meta-lattice projection gate.

## batch05d Merge09/Merge10 Gate

The later batch05d representatives are terminal reuse checks for pages that
had changed-row readback success but still exposed projection debt:
`وَٱتَّبَعُوا۟`, `يُفَرِّقُونَ`, `مَّٰكِثُونَ`, and `فَإِذَا`.
Reject any carryover that hides a perfect-verb subject suffix, an imperfect
prefix, a derived-form stem, an active-participle mīm, a sound plural suffix,
or a function-token source fact behind a fluent phrase hover. VN-01 reuse must
copy the lattice obligation, not merely the old rendered wording.

## VN-01 Reuse Rule

Before VN-01 page workers copy a same-surface or same-family hover from VN-00,
they must check these fixture classes. If a prefix, suffix, article, particle
role, root/stem, or token-vs-phrase contribution is still hidden, the VN-01 row
inherits the blocker rather than the hover.
