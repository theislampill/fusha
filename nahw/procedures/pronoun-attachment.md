# Procedure — pronoun attachment (what an enclitic IS, by host)

**Invoke when:** a token carries an attached pronoun (enclitic) and you must decide its **syntactic role** before
glossing — because the same enclitic means different things on different hosts.

**The rule (host decides):**
- **Noun host** → the enclitic is **possessive** (مضاف إليه): أَعْمَالُنَا = "our deeds", قُلُوبِهِمْ = "their
  hearts". Resolve via [`sarf/procedures/suffix-pronoun-state.md`](../../sarf/procedures/suffix-pronoun-state.md).
- **Verb host** → the enclitic is a **subject** (نا الفاعلين = "we": عَلِمْنَا "we knew", خَلَقْنَا "We created") or
  an **object** (هم/كم = "them/you": خَلَقَكُمْ "He created you"). **Never** a possessive — do not gloss عَلِمْنَا as
  "our knowledge".
- **Preposition host** → the enclitic is the **object of the preposition**: بِكَ "with you", لَهُم "for them",
  عَلَيْهِ "upon him".

**Checks:**
1. Determine host POS (QAC/Tafsir-adapter/sarf). If verb → subject/object, not possessive.
2. Identify the enclitic from the **vocalized** surface (نا/كم/هم/ه/ها/ي/كما/هما); guard the tanwīn-alef
   false-positive (قُرْءَانًا ≠ ...+نا).
3. Referent sensitivity: ه/ها render his/its or her/its by antecedent — keep the pronoun-faithful default
   (his/her/their); if the referent flips the sense materially, two-vote or pending.

**Output:** the attachment classification (possessive | subject | object) feeding the gloss; for the possessive
case emit a `suffix_pronoun_decision`. Grammar-affecting → the GrammarProblems reasoning gate still applies.

**Forbidden:** treating a verb-subject نا as possessive "our"; treating tanwīn-alef as the نا pronoun; exporting a
possessive gloss without confirming a noun host.

## Dogfood finding: populated verb hovers can still omit the object

The 2026-06-27 full-corpus dogfood suffix batch found populated hovers whose
entry text exists but whose token contribution still drops an attached object
pronoun. Rows such as `ثَقِفْتُمُوهُمْ`, `تُخَالِطُوهُمْ`,
`تُمْسِكُوهُنَّ`, `تَمَسُّوهُنَّ`, and `تَكْتُبُوهَا` are not
rich-certified if the visible hover is only a lemma/root-family gloss or if the
object suffix appears only in hidden metadata.

For a verb host, record the suffix as object or subject before accepting the
hover:

- `ـهُمْ` -> object "them" when attached to a transitive verb.
- `ـهُنَّ` -> object "them" feminine plural where context supports it.
- `ـهَا` -> object "it/her" and therefore a referent/reasoning gate when the
  antecedent changes the English.

If the row is already string-populated but lacks this breakdown, route it to
`token_only_override` or `needs_nahw_review`; do not mark it complete from hover
presence alone.

## Dogfood finding: VN-11 standalone pronouns are not verb-entry proof

VN-11 found high-volume `هُمْ` / `هُمُ` rows linked through a verb-entry family.
These are standalone pronoun/function-token rows, not finite verb hosts and not
nominal suffixes.

For these rows:

- keep the exact token identity (`quran:S:A:W`, `wbw:S:A:W`) as the address;
- classify the token as independent pronoun or function-token evidence before
  any Qamus entry/sense reuse;
- require referent and sentence role review before rich certification;
- block parse-family propagation from a verb-entry source key.

Do not treat "they, their" string presence as dogfood completion. It is only a
candidate public wording until the token has pronoun role, referent, and rich
display breakdown.

## Dogfood finding: VN-12 verb objects and possessive hosts

VN-12 added more populated rows where suffixes must be reasoned by host:

- `يُحَرِّفُونَهُۥ`, `ثَقِفْتُمُوهُمْ`, `جَاوَزَهُۥ`,
  `تُخَالِطُوهُمْ`, and `فَرَشْنَٰهَا` are verb hosts. Their suffixes are
  object/referent decisions, never possessive endings.
- `أَسْرَهُمْ` is a noun host; its suffix is a possessive/referent decision
  and cannot be hidden under the host noun alone.
- Component-only rows with suffixes remain blockers until exact token
  analysis agrees on host POS, suffix role, and contextual referent.

If the proposed hover is English-readable but does not account for the suffix,
route it to `verb_object_pronoun_review`, `suffix_pronoun_decision`, or
`referent_unresolved`. Do not pass a row merely because two sources share a
host gloss.

## Dogfood finding: VN-13 suffixes include noun possessors and verb objects

VN-13 added a mixed suffix control set:

- `سُهُولِهَا`, `نُورَهُۥ`, `نُورِهِۦ`, `نُّورِكُمْ`,
  `سَمْكَهَا`, and `أَهْلِهِۦ` are noun hosts. Their suffixes are
  possessive or referent decisions and cannot disappear under the host noun.
- `لَأَعْنَتَكُمْ`, `ٱقْتَرَفْتُمُوهَا`, `فَاتَكُمْ`,
  `يَسْتَصْرِخُهُۥ`, and `فَتَطْرُدَهُمْ` are verb hosts. Their suffixes
  are object/addressee decisions, not possessives.
- `بِمُصْرِخِكُمْ` adds a preposition/nominal-host/suffix layer; the
  suffix still needs host-POS and attachment review before English wording is
  trusted.

If a populated hover can be read without the suffix, it is not rich-certified.
Route it to exact-address review, and require two compatible reasons when the
referent or clause role affects the English.

## Dogfood finding: VN-14 mixed noun and verb suffix rows

VN-14 confirmed the same suffix rule across noun hosts, verb hosts, and
prepositional constructions:

- `أَصْوَافِهَا`, `حَرْثَكُمْ`, and `ثَمَرِهِۦٓ` are nominal hosts.
  Their suffixes are possessive or referent-sensitive and cannot disappear
  under the host noun or a verb-family entry gloss.
- `ٱبْتَدَعُوهَا`, `خَرَقَهَا`, `جَهَّزَهُم`, `يَطْلُبُهُۥ`,
  `يَلْمِزُكَ`, `يُطِيقُونَهُۥ`, and `وَدَّعَكَ` are verb hosts.
  Their suffixes are object/addressee decisions and require exact-address
  review before the English can be trusted.
- `بِجَهَازِهِمْ` adds bā' + governed host + suffix. The suffix role and PP
  attachment must be reasoned with the preposition, not hidden as host metadata.

If the learner can read the hover without the suffix, the row is still
`populated_uncertified` or `token_only_override`. Route it to suffix-pronoun
review, not live apply.

**Test:** [`nahw/evals/suffix-pronoun-eval.jsonl`](../evals/suffix-pronoun-eval.jsonl);
rules [`nahw/rules/pronoun-attachment-rules.json`](../rules/pronoun-attachment-rules.json).

**Feeds:** hover-gloss resolution (subject vs object vs possessive) · /qamus/ entry authoring · ajami learners.
