# Clitic And Host Morphology

Before accepting a host gloss, segment the written token into visible pieces:

- proclitics such as `و`, `ف`, `ب`, `ل`, `ك`, article `ال`;
- the host stem and its root/form/POS;
- suffix pronouns and inflectional endings;
- false-clitic traps such as tanwin-alif, long vowels, and lexical final letters.

An exact host match does not certify the whole written token. The public hover
must account for visible clitics when they affect the token contribution.
For rich-hover readiness, also emit a compact `parse_key.key` and one
`qamus-grammar-v1` display class per segment, following
[`../../curriculum/qamus-hover-parse-key-and-color.md`](../../curriculum/qamus-hover-parse-key-and-color.md).

Examples:

- `بِسَلَامٍ` cannot be only `peace`;
- `بِبَدْرٍ` cannot be only `Badr`;
- `جَادَلُوكَ` cannot be only `to argue/dispute`;
- `وَلْيَعْفُوا` cannot be only `pardon`.

## Dogfood finding: plus-sign hovers are not learner explanations

The 2026-06-27 full-corpus dogfood batch found populated hovers that were
string-correct enough to be readable, but not rich-certified enough to teach the
token. Treat `and + the stars`-style text as a fallback symptom, not completion.

For tokens such as `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`,
`وَٱلْجِبَالُ`, and `وَٱلشَّجَرُ`:

- segment the written token as `وَ` + `ٱل` + host noun;
- keep the visible Arabic token intact in any renderer handoff;
- emit component roles for the renderer and learner breakdown;
- do not count the row rich-certified merely because the visible gloss says
  `and + the ...`;
- send the `وَ` function to nahw before allowing any parse-family propagation.

For tokens such as `بِٱلْمَعْرُوفِ`, record bā' + article + host. A generic
"by what is right/customary" gloss can be understandable, but it is not a
complete rich-hover certification unless the preposition, article, host, and PP
role are visible in the breakdown.

If the clitic function is syntactic rather than purely morphological, sarf
records the segmentation and defers to nahw. Do not invent a color/parse-key
explanation for a segment whose function is still unknown; use an exact blocker
such as `particle_function_uncertified` or `preposition_role_uncertified`.

## Dogfood finding: lexical yā is not automatically vocative

The vocative dogfood packet also exposed the opposite failure: rows such as
`يَابِسٍ` and `يَابِسَٰتٍ` were pulled into the vocative lane by surface shape.
Sarf must not split a lexical stem merely because the raw surface begins with a
yā-like sequence.

Before routing to the vocative procedure, prove a real vocative piece:

- an independent or prefixed call particle `يَا`;
- a vocative support form such as `أَيُّهَا` / `أَيَّتُهَا`;
- a following addressee or a fused munāda form;
- corpus/morphology evidence that the initial letters are not part of the host
  noun/adjective/verb.

If the token is a lexical word such as `يَابِسٍ` ("dry") or `يَابِسَٰتٍ`
("dry [feminine plural]"), keep the whole stem as the host and record
`not_vocative_surface_prefix`. Do not send it to nahw as a vocative merely from
`startswith("يا")`.

## Dogfood finding: lexical initial letters are not clitics

The particle-first dogfood tranche found the same false-positive shape outside
vocatives. A raw token can begin with bā', lām, fā', or kāf without containing a
real attached particle. Examples include `بُكْمٌ`, `بِكْرٌ`, `بِطَانَةً`,
`لِسَانِ`, and `فَالِقُ`.

Before routing a row to preposition/oath/result/clitic review, require positive
segmentation evidence:

- a corpus/morphology segment for the particle;
- a governed majrūr host for `بِـ` / `لِـ` / `كَـ`;
- a clause/function trigger for `فَـ` or `وَ`;
- a token-internal segment record from a trusted parser or rich WBW layer.

If only the raw first letter matches a particle, keep the written token as one
lexical host and record `not_clitic_surface_prefix`. Do not let component-level
candidate evidence from a particle-like initial letter create a whole-token
Qamus entry candidate, propagation-safe parse family, or closure-coverage claim.

## Dogfood finding: component candidates stay below the whole token

The remaining-particle dogfood tranche found rows where component candidates are
real and useful, but still unsafe as whole-token entry evidence:

- `فَأَهْلَكْنَاهُمْ`: result/sequence `فَـ` + Form IV verb host + object
  pronoun `هُمْ`;
- `يَسْـَٔلُكَ`: imperfect verb host + object suffix `كَ`;
- `لَيْتَنِي`: wishing particle host + first-person suffix `نِي`;
- `لِكَيْلَا`: purpose lām + `كَيْ` + negation `لا`.

These pieces may feed a rich renderer or learner breakdown. They must not create
a whole-token particle/pronoun candidate, an `auto_safe` parse family, or a
surface-family hover. If a suffix or composite particle is visible, the
token-addressed hover must account for it or remain pending.

## Dogfood finding: preposition and oath hosts need their governors

The 2026-06-27 preposition/oath dogfood batch found host-only hovers on tokens
whose visible governor is part of the written word.

Sarf must preserve these pieces before nahw chooses the contextual function:

- `بِذُنُوبِهِمْ`: `بِـ` + plural noun host + possessive suffix `هِمْ`.
- `بِذُنُوبِكُم`: `بِـ` + plural noun host + possessive suffix `كُم`.
- `بِرُوحِ` / `بِرُوحٍ`: `بِـ` + host noun; referent and relation stay gated.
- `بِبَابِلَ`: `بِـ` + proper place host.
- `وَطُورِ`: oath/coordinating `وَ` + governed host.
- `وَهَٰذَا`: oath/coordinating `وَ` + demonstrative host.

Do not let an article, preposition, oath particle, or suffix pronoun become
component-only metadata while the public hover reads like the bare host. If the
host is known but the governor/function is not, emit the segmentation and route
to nahw with `preposition_role_uncertified`, `oath_function_uncertified`, or
`pp_attachment_uncertified`.

## Dogfood finding: VN-05 false lām and component-only noun rows

VN-05 added two clitic hygiene guards:

- `لَّازِبٍ` is a lexical adjective with root-initial lām/shadda, not an
  attached lām preposition, oath lām, or purpose lām. Do not route an initial
  lām-looking host to nahw unless segmentation evidence proves a real lām
  particle.
- `وَرَجِلِكَ`, `وَأَرْجُلَكُم`, `فَرِجَالًا`, and similar rows can contain
  useful component candidates, but the component candidate is below the
  written token. Whole-token review must preserve the proclitic, host noun,
  number/case, and suffix before any hover can be certified.

Use `not_clitic_surface_prefix` for lexical initial letters and
`component_only_candidate_no_whole_token_propagation` for rows where a
component is real but the whole token is not yet certified.

## Dogfood finding: VN-06 component candidate vs whole token

VN-06 repeated the component-only guard at larger scale:

- A `مِن` or `مَنْ` function-token row may be discovered while reviewing a
  `مَنَّ` verb entry. The token is still a particle/function token, not a verb
  host.
- A row such as `حَوْلَهُۥ` contains a lexical/adverbial host plus `هُ`; the
  suffix must be accounted for, but the row is not certified by the verb/root
  family alone.
- `بَيْنَ`, `مِن`, and `بِكُمُ` require nahw preposition/function review; a
  first-letter or source-key match is not morphology proof.
- `ٱلْمَنَّ`, `ثَمَرَةٍ`, and `مَرَضٌ` can be useful entry candidates, but they
  are noun hosts and stay below whole-token certification until POS/state/case
  are explicit.

Record component candidates with provenance (`source=rich_wbw_segment`, role,
segment text, token loc) when available, but never let them weaken the gate.
Component candidates do not create `auto_safe`, source agreement, closure
coverage, or hover coverage.

## Dogfood finding: VN-07 suffixes survive candidate enrichment

VN-07 added fresh examples where a candidate is useful for routing but unsafe
for certification:

- `مِنِّى` is `مِن` plus a first-person suffix pronoun. A `تَمَنَّى`
  entry-family candidate is not allowed to hide the preposition or the suffix.
- `يَتَمَنَّوْهُ` must expose the finite host and the `هُ` object. The suffix
  cannot be stored only as private metadata while the visible hover remains a
  bare infinitive.
- `مَوَازِينُهُۥ` and `بَالَهُمْ` are noun hosts with attached possessor or
  reference suffixes. A host-only hover such as "scales" or "state" remains
  below rich certification until the suffix is explained.

When a row gains component candidates, preserve two facts separately: the
component evidence and the whole-token gate. Component evidence may tell the
reviewer what pieces exist, but it never authorizes parse-family propagation.

## Dogfood finding: VN-09 suffixes and component rows remain visible

VN-09 added fresh suffix and component-only controls:

- `يَعْصِمُكَ` and `يَجْتَبِيكَ` are finite verb hosts plus `كَ` object. A
  hover that reads like "to protect" or an entry explanation without "you" is
  not learner-ready.
- `أَقْوَٰتَهَا` and `تَفَثَهُمْ` are nominal hosts with attached possessor or
  referent suffixes. The suffix contribution must be in the best hover or in
  rich segment rows before certification.
- `لِتُضَيِّقُوا۟`, `وَفَدَيْنَٰهُ`, `كَلَمْحِ`, and `لَأَوَّٰهٌ` can yield
  useful component candidates, but the whole token still carries a proclitic,
  function, finite form, suffix, or lexical-host decision that must be proven.

When VN-09-style component evidence is present, store it as component evidence
with provenance. Do not add it to whole-token candidate counts, propagation
safety, source agreement, closure coverage, or hover coverage.

## Dogfood finding: VN-10 suffix and component evidence remain below apply

VN-10 added more rows where a visible suffix or component is easy to miss:

- `وَارِدَهُمْ` and `تَرْهَقُهُمْ` need the `هُمْ` contribution recorded in
  the learner breakdown before any wording is trusted.
- `وَقُودُهَا` is a nominal host with `هَا`; a host-only "fuel" style hover
  is not rich-certified until the suffix/referent is visible.
- `رَٰعِنَا` and `رَعَوْهَا` require exact host plus suffix or address-context
  review. The final letters must not be hidden under entry-family prose.
- `فَدَمَّرْنَٰهُمْ`, `فَأَعِينُونِى`, and `وَأَعَانَهُۥ` are useful
  component candidates, but fā'/wāw, finite form, and attached objects keep
  them below whole-token certification.
- `بِغَيْظِكُمْ` is bā' + host + `كُمْ`; both the preposition and suffix are
  visible morphology that must be routed to nahw for relation/attachment.

Rule: a VN-10 row with component evidence or a visible suffix can become a
repair candidate only after exact-address review. It is never live-applyable
from the dogfood tranche, and component evidence never contributes to hover
coverage or propagation safety.

## Dogfood finding: VN-11 suffixes and component blockers

VN-11 found another suffix-heavy tranche:

- `ٱقْذِفِيهِ`, `قَبَضْنَٰهُ`, `أَهَمَّتْهُمْ`, and `فَأَهْلَكْنَاهُمْ`
  need the verb host plus attached suffix/object relation visible before any
  hover wording is trusted.
- `ظَعْنِكُمْ`, `كَسَادَهَا`, and `نَحْبَهُۥ` are nominal hosts with suffix
  or referent contribution. They cannot be treated as host-only noun hovers.
- `لِفُرُوجِهِمْ` contains lām + host + `هِمْ`; component evidence may find a
  candidate entry, but the whole token remains blocked until the preposition,
  host, suffix, and attachment are all reviewed.
- `فَٱسْتَغَٰثَهُ`, `فَٱقْذِفِيهِ`, and `فَقَذَفْنَٰهَا` are useful
  component candidates only. Keep the candidate provenance separate from
  whole-token entry candidates.

Rule: a visible suffix, even on a row whose English looks plausible, must have
its own learner-facing accounting. A component-only hit can create a blocker or
review packet, but never an applyable token decision.

## Dogfood finding: VN-12 component candidates and object suffixes

VN-12 added another control set for component-only evidence and attached
pronouns:

- `يُحَرِّفُونَهُۥ`, `ثَقِفْتُمُوهُمْ`, `جَاوَزَهُۥ`, and
  `فَرَشْنَٰهَا` are verb hosts with attached object suffixes. A hover that
  exposes only the host action remains below rich certification.
- `أَسْرَهُمْ` is a nominal host with a suffix/referent contribution. It needs
  host class and suffix role before any entry-family wording is safe.
- `فَلْيُؤَدِّ`, `فَٱصْطَادُوا۟`, `وَجَٰوَزْنَا`, `كَزَرْعٍ`, and
  `وَفُرُشٍۢ` may gain useful component candidates, but those candidates must
  stay separate from whole-token Qamus entry candidates.

Rule: component candidates can improve review routing only. They do not count
toward source agreement, propagation safety, hover coverage, or live apply.
If the visible token contains a clitic, conjunction, preposition/comparison
piece, or suffix pronoun, keep that piece visible in the learner breakdown or
emit an exact blocker.

## Dogfood finding: VN-13 suffixes and component routes stay separated

VN-13 added suffix-heavy noun and verb rows:

- `سُهُولِهَا`, `نُورَهُۥ`, `نُورِهِۦ`, `نُّورِكُمْ`,
  `سَمْكَهَا`, and `أَهْلِهِۦ` are noun hosts with possessor or referent
  suffixes. A host-only hover such as "plains", "light", "height", or
  "family" remains below rich certification until the suffix is taught.
- `لَأَعْنَتَكُمْ`, `ٱقْتَرَفْتُمُوهَا`, `يَسْتَصْرِخُهُۥ`,
  `فَاتَكُمْ`, and `فَتَطْرُدَهُمْ` are finite hosts with object or
  addressee-sensitive suffixes. Do not hide them behind an infinitive.
- `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَخَابَ`, `فَصَبَّ`, and
  `وَقَدَّتْ` show that component candidates can identify a host but still
  leave the whole token blocked for the prefixed function and exact context.

Rule: keep `component_only_evidence` separate from `whole_token_candidate`.
VN-13 rows can gain better component evidence without weakening the gate or
creating a source-agreement, hover-coverage, or live-apply claim.

## Dogfood finding: VN-14 component evidence and suffixes stay separated

VN-14 repeated the component-boundary and suffix-accounting controls:

- `وَٱلشَّجَرُ`, `فَوَسَطْنَ`, `بِجَهَازِهِمْ`,
  `وَخَرَقُوا۟`, and `وَمُسْتَوْدَعَهَا` are component-only rows in the
  dogfood inventory. Component candidates may improve routing, but they do not
  become whole-token decisions and they do not count toward propagation
  safety.
- `أَصْوَافِهَا`, `حَرْثَكُمْ`, and `ثَمَرِهِۦٓ` are noun hosts
  with visible suffix or referent contribution. Host-only nouns such as
  "wool", "harvest", or fruit-family prose are not rich-certified.
- `ٱبْتَدَعُوهَا`, `خَرَقَهَا`, `جَهَّزَهُم`, `يَلْمِزُكَ`,
  `يُطِيقُونَهُۥ`, and `وَدَّعَكَ` are finite verb hosts with object or
  addressee-sensitive suffixes. The suffix must be visible in the learner
  breakdown before candidate wording can move forward.

Rule: a VN-14 row may gain component candidates and still remain
`component_only_blocker`, `rich_metadata_plus_exact_address_review`, or
`two_vote_exact_address_review`. Component candidates never weaken the gate.

## Dogfood finding: VN-15 component evidence is review fuel only

VN-15 repeated the component-boundary rule with finite, nominal, and function
pieces:

- `وَتَوْفِيقًا`, `وَقِفُوهُمْ`, `فَيُحْفِكُمْ`, `وَالذَّارِيَاتِ`,
  `لِيُطْفِـُٔوا۟`, and `وَتُعَزِّرُوهُ` may expose useful pieces, but the
  evidence is below the written-token decision.
- A component candidate may record `source=rich_wbw_segment`, role, segment
  text, and token loc. It must not become a whole-token Qamus candidate.
- Do not infer a missing host noun or verb entry from an article, preposition,
  conjunction, vocative, lām, fā', or suffix component.

Rule: component evidence can route review, lessons, and blocker queues. It
cannot contribute to `auto_safe`, source agreement, propagation safety,
closure coverage, hover coverage, or live apply.

## Dogfood finding: VN-16 component rows still block whole-token reuse

VN-16 repeated the component boundary in rows such as `فَكُبْكِبُوا`,
`فَكُبَّتْ`, `وَيُكَوِّرُ`, `وَتَلَذُّ`, `لِتَلْفِتَنَا`,
`وَٱلْتَفَّتِ`, `وَأَلْفَيَا`, and `يَمْحُوا۟`.

These may reveal useful host-family evidence, but the whole written token still
needs:

- the prefixed function piece, if any;
- the finite or nominal host;
- every visible suffix pronoun;
- the nahw function/mood/attachment when a particle governs the host.

Rule: in VN-16, component candidates remain review fuel only. They may create
blocker rows and drills; they must not create whole-token certification or
family-wide propagation.

## Dogfood finding: VN-17 component candidates still cannot certify the token

VN-17 repeated the same boundary in a fresh verb/noun tranche:

- `بِمُزَحْزِحِهِۦ`, `لَيُزْلِقُونَكَ`, `وَأَسْبَغَ`,
  `وَسَعِيدٌۭ`, `وَيَسْفِكُ`, `أَشْكُوا۟`, `وَاضْمُمْ`,
  and `وَٱضْمُمْ` may expose a useful host or function component.
- Those components remain `source=rich_wbw_segment` evidence below the written
  token. They cannot supply a whole-token Qamus entry, source agreement,
  propagation safety, hover coverage, or live apply.
- If the token contains a prefix, article, lām/bā'/wāw/fā' function, or suffix
  pronoun, the learner breakdown must show that piece before the hover can be
  trusted.

Rule: VN-17 rows can gain component candidates while remaining blockers. Keep
component candidates in their own field or edge label, and keep the whole-token
lane at `component_only_blocker`, `rich_metadata_plus_exact_address_review`, or
`two_vote_exact_address_review` until the full surface is parsed.

## Dogfood finding: VN-18 component rows include high-frequency function hosts

VN-18 repeated the component boundary in a tranche with very frequent learner
tokens:

- `بِٱلْمَعْرُوفِ` is not certified by the host "known/customary" alone; it
  requires bā' + article + governed host and attachment review.
- `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`,
  `وَٱلْجِبَالُ`, and `وَٱلشَّجَرُ` expose wāw + article + noun hosts, but
  the component evidence cannot certify the whole written token.
- `يَـُٔودُهُۥ` and `يُوبِقْهُنَّ` show why a host-family match still needs
  suffix/object accounting before a learner hover can move forward.

Rule: VN-18 component candidates remain review fuel only, even when the current
visible string looks plausible. A row can gain rich component evidence while
staying blocked; do not count component candidates toward propagation safety,
closure coverage, hover coverage, or live apply.
