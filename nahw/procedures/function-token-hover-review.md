# Function Token Hover Review

Function tokens must be classified before they are glossed. The same surface or
prefix can mark different grammar roles.

Review:

- `ما`: negative, relative, interrogative, masdariyya/source, conditional,
  negative acting like laysa, or preventive/kāffa.
- `و`: conjunction, oath, comitative, resumption, or circumstantial.
- `ف`: resumption, coordination, result, supplement, or cause.
- `ل`: genitive preposition, purpose, imperative, denial, or emphasis.
- `أ`: interrogative or equalization.
- `لا`: simple negation, prohibition, or negation of genus.
- `إلا`: exception structure with polarity and case effects.
- `يا` / `أيها`: vocative call, bridge, attention, and addressee structure.

If function controls meaning and evidence is insufficient, route to two-vote or
scholar review. Do not use a default one-gloss particle policy.

## Production finding: VN-00 public visual ANDON particles

The 2026-07-03 VN-00 public readback found common function tokens that remained
draft-only or generic despite solved peers. These rows block page completion
until the public hover exposes the function role and any attached pronoun.

Regression examples:

- `هَلْ` must be a question particle row with a question-particle qg role,
  not a draft row and not a generic `qg-segment` token shell.
- `إِنَّكُم` must expose `إِنَّ` as the particle/function host and `كُمْ` as
  an attached second-person plural pronoun.
- `وَمَا` must preserve the wāw plus the contextual function of `مَا`; do not
  carry a default "what/that/not" gloss without context.
- `فِيهَآ` must expose preposition `فِي` plus attached `هَا`; the relation
  cannot be hidden in a host-only hover.
- `لَعَلَّهُمْ` must expose the particle and the attached plural pronoun.
- v016 added the same rule for `إِنِّىٓ`, `أَحَدُهُمَآ`, and similar attached
  pronoun clusters: the particle/host and the pronoun must each be visible, and
  person/number must not disappear behind a generic "me/them" gloss.
- `وَٱلشَّمْسَ`, `وَٱلْقَمَرَ`, `ٱلْءَايَةَ`, and `ٱلْعَيْنِ` must expose the
  definite article as a grammar piece. If a richer article-plus-host peer
  exists, a flat noun hover is a transclusion failure.
- `يَوْمَئِذٍۢ` is not just a bare noun gloss. In context it is a temporal
  expression: `يَوْمَ` supplies the time noun and `ئِذٍۢ` supplies the
  attached "then/that time" element. A hover that hides `ئِذٍۢ` fails nahw
  review even if the page is colored.
- n0030 and v030 repeated the preposition/function-token transclusion failure:
  `لَهُمْ`, `بِهِۦ`, `وَلَهُمْ`, `فِيهَآ`, `لَكُمْ`, and `عَلَيْكُمْ` must
  expose the relation plus the attached pronoun. `لَعَلَّكُمْ` must expose the
  visible lām/particle host and plural pronoun, while rows such as `وَإِن` and
  `أَنَّكُمْ` require context-safe particle classification before color or
  hover completion can be claimed.

Rule: common solved function-token peers are transclusion obligations. If a
visible VN page has a flat/draft/generic function token while a richer same
surface or equivalent-function peer exists, emit a repair candidate or exact
nahw blocker before any page-complete claim.

Vocative guard:

- `يَا` contributes the call "O" when it is a real vocative particle.
- `أَيُّهَا` / `أَيَّتُهَا` contributes a bridge/support plus attention
  particle in a vocative formula.
- the following noun or phrase supplies the addressee.
- surfaces such as `يَابِسٍ` are not vocatives merely because their first
  letters resemble `يا`; require sarf segmentation evidence first.

Lexical false-clitic guard:

- `لِبَاسٌۭ` starts with lexical lām from the noun/root `ل ب س`; it is not a
  lām-preposition row and should not be forced into qg-lām relation wording
  unless the written token is actually segmented as a function lām.
- Built particles such as `لَٰكِنِ` can begin with a visible lām-like shape
  while remaining a single contrast particle. Treat the whole token as the
  particle unless sarf/nahw evidence proves a detachable lām relation.
- `أَنتُمْ` and `وَأَنتُمْ` are independent pronouns, not verbs carrying the
  attached subject suffix `تُمْ`. Teach second-person plural pronounhood without
  creating a fake suffix split.
- `أُو۟لَٰٓئِكَ` / `وَأُو۟لَٰٓئِكَ` are demonstratives, and `وَحِينَ` is a time
  noun with a wāw. Their final shapes must not be treated as hidden suffixes.
- `يَٰٓأَيُّهَا` is a vocative formula (`يَا` + `أَيُّ` + `هَا` attention), not
  an object-pronoun suffix row. A weaker same-surface peer should be repaired by
  transclusion or explicitly excepted, not counted as complete by suffix logic.

## Dogfood finding: readable text is not rich certification

The 2026-06-27 full-corpus dogfood batch exposed rows whose fallback text was
readable but whose grammar was still not learner-ready. Classify these before
repair-preview:

- `وَٱلشَّمْسُ`, `وَٱلْقَمَرُ`, `وَٱلنُّجُومُ`, `وَٱلْجِبَالُ`,
  `وَٱلشَّجَرُ`: decide whether `وَ` is ordinary coordination, resumption, oath,
  or another role in context. The learner breakdown must teach `وَ` + article +
  host; the public wording must not be treated as sufficient merely because it
  contains `and + the`.
- `وَخُلِقَ`: keep the wāw/resumption or coordination role separate from the
  passive perfect verb. A correct phrase still needs parse-role proof.
- `بِٱلْمَعْرُوفِ`: bā' governs a definite nominal and the resulting PP needs an
  attachment or a precise blocker. Do not certify from host meaning alone.
- `فَأَهْلَكْنَاهُمْ`: decide the fā' role before treating the finite verb and
  object suffix as a reusable family.
- `يَٰٓأَيُّهَا`: keep call, bridge, attention, and addressee separate; a
  phrase-like "O you (who)" is not rich certification.

If the function role is known enough for a fallback phrase but not enough for a
rich row, classify the row as `string_correct_but_not_rich`,
`needs_renderer_segments`, or `needs_nahw_review`; do not mark it
`rich_certified`.

## Dogfood finding: rich-live is not Plan17 closure

The VN-00 retry for `v046` produced a public page where every visible cited-card
qword was `rich_live`, but Plan17 still found unresolved suffix, tanwin,
preposition/pronoun, contextual definiteness, and known-root families.

Rule: qg color plus rich hover is necessary but not sufficient. A page remains
open while Plan17 false-closure findings remain, and page-worker states such as
`needs_false_closure_repair` are ANDON states, not merge conflicts and not
completion evidence.

## Production finding: case/tanwin wording must teach the contribution

When a noun or adjective ending is shown in a Qamus rich hover, nahw must keep
the governor/context contribution understandable. A public segment gloss like
`indefinite genitive/case ending` is too opaque for ordinary learners and can
look like a new word meaning.

For bāʾ, lām, min, ʿalā, and similar preposition phrases, prefer plain wording:

- segment gloss: `ending mark` or `small final mark`;
- note: `after the preposition, this is the expected noun ending here`;
- explanation: the mark shows how the word fits the phrase; it does not add a
  new lexical meaning.

Do not use a case/tanwin segment to compensate for an uncertified governor.
If the governor or phrase role is not known, route the row to
`governor_irab_fixture_needed` or `pp_attachment_uncertified` instead of
shipping case jargon in public.

Rich-hover readiness:

- emit a compact `parse_key.key`, e.g. `OATH+ART+N:GEN:DEF`,
  `FA:CAUSE+V:SUBJ`, `MA:LAYSALIKE`, or `HAMZA:EQUALIZATION`;
- assign display classes by function, not surface: `qg-oath` for oath wāw,
  `qg-comitative` for comitative wāw, `qg-result` for causal/result fā',
  `qg-relative` for a relative pronoun, and `qg-particle` for ordinary
  particles;
- if the function cannot be certified, do not choose a color or parse key as if
  it were resolved. Route to `particle_function_uncertified`,
  `ma_function_uncertified`, `waw_function_uncertified`, or a more exact blocker.


## VN-00 r29 lesson: a contested-token packet must PRESERVE both parses (decision-ready)

When two independent parses disagree on a contested function token (ما مصدرية/موصولة, مَن
موصولة/شرطية, لا نافية/ناهية, a homograph sense), the hold is only useful if the packet
**preserves the two actual parses**. A packet that says "two independent parses disagree" but
stores `reading_A: null / reading_B: null` is NOT decision-ready — the reviewer cannot rule
without re-deriving the parses. This was a live Run #29 failure: the final report claimed
"exact A/B packets" while the packet JSON had null readings.

Decision-ready packet contract (mechanically checkable — see `vn00_check_packets.py`):
- **scholar packet:** both readings (class-sequence + gloss + verdict + hold-reason), the exact
  grammar question, BOTH proposed public payloads (deploy-if-A / deploy-if-B), and the exact
  reason it cannot be deployed (which authoritative field disagrees with which).
- **owner packet:** ≥2 real sense options, each with a gloss AND a proposed payload; the exact
  grammar question; why owner authority is required; a recommendation.
- **crosswalk packet:** the EXACT missing edge — or, if the display loc renders (no orphan) and
  only entry-provenance metadata differs, reclassify (it is not a real edge gap).

Resolution rule (Run #29b): before escrowing a disagreement to a packet, re-check the
**authoritative parse** (analyzer irab + meaning + qeraat). Many "disagreements" are NOT genuine:
they are segmentation granularity (qg-verb vs qg-verb-stem+subject-pronoun — same lexical unit),
editorial synonymy, or a bad gloss hint the authoritative parse overturns (e.g. مُلْك 'dominion'
mis-hinted as مَلَك 'angels' — قراءة: لا خلاف). Only where the authoritative irab and meaning
fields THEMSELVES diverge (genuine khilāf) is a scholar packet the correct terminal.


## VN-00 FINAL lesson: converging-meaning deploy rule + source-clean boundary

When multiple grammatical analyses of a function token CONVERGE in learner meaning, do NOT block
indefinitely — deploy a conservative hover with a FORMAL/CONTEXTUAL split:
- **بِمَا** — 2:59 causal مصدرية ('because'); 2:164 relative موصولة ('with what' → contextually 'for
  what benefits people'). Deploy the formal token gloss; carry the contextual phrase in the learner note.
- **مَنْ in parables** — relative / described-indefinite ('one whom'), not a live conditional 'whoever',
  when the passage describes a specific figure (e.g. the provided believer at 16:75).
- **فَأَوْلَىٰ** — form is the elative أَفْعَل from و ل ي in every occurrence; the OCCURRENCE sense is
  read per-ayah: 75:34 the threat/waʿīd idiom ('woe to you'), 47:20 the elative 'more fitting' with
  warning force. Gloss the occurrence sense; name the elative form in the learner note.

**SOURCE-CLEAN boundary (hard):** external evidence — web corpora, translation sets, classical iʿrāb/
tafsir/lexical works, or an analyzer — belongs in the packet SIDECAR only. The public payload
(token gloss, contextual gloss, learner explanation, segments, morphline) must never name or quote a
source, path, or process. The deploy-time leak scan enforces this; keep the learner note plain.
