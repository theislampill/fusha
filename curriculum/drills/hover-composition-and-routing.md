# Drill — hover composition and routing

**Goal:** learn the same pre-hover discipline the Qamus closure process uses: a written token
may contain several grammatical pieces, and each piece must be accounted for before the learner
trusts or authors a gloss.

**Rule of the drill:** compose the token before accepting the hover. For each item, write six
fields:

1. written token,
2. visible pieces,
3. sarf class of the host,
4. nahw function of attached particles or clause pieces,
5. semantic/concept flag, if any,
6. parse-key/display readiness,
7. result: allowed hover, learner explanation, or `pending:` blocker.

Public hover output stays source-clean: `{src:'qamus', kind:'authored', lang:'en'}`. QAC,
grammar screenshots, external dictionaries, source-triangulation output, and Tafsir/i'rab notes
may route review internally, but they never become public provenance and never supply copied
hover wording.

## Items

| token | visible pieces | safe result |
|---|---|---|
| `بِسْمِ` | `بِـ` + host noun `ٱسْمِ` | hover/explanation must preserve the bā': "in the name of"; host-only "name" fails |
| `لِلَّهِ` | `لِـ` + definite proper noun | preserve the lām: "for/to Allah"; host-only "Allah" fails |
| `كَأَنَّ` | `كَـ` + `أَنَّ` particle frame | route to nahw; not host-only "that" and not ordinary lexical kāf |
| `وَمَا` | `وَ` + `مَا` | one written token, multiple grammar pieces; decide `مَا` by function before glossing |
| `وَٱلْعَصْرِ` | clause-initial `وَ` + jarr noun | oath frame: "by"; ordinary "and" fails if the frame is oath |
| `فَتَنفَعَهُ` | `فَـ` + imperfect verb + object suffix | route fā' function and mood; suffix pronoun cannot disappear |
| `أَعْطَيْنَاكَ` | verb + subject suffix `ـنا` + object suffix `ـكَ` | "We gave you"; bare "gave" fails |
| `قُرْءَانًا` | host noun + tanwin fatḥ alif | `ـًا` is nunation, not pronoun `نا`; no clitic split |
| `صَٰلِحًا` | common adjective/noun surface | concept flag may warn about Ṣāliḥ the messenger, but context decides |
| `بِبَدْرٍ` | `بِـ` + proper place name | preserve both the preposition and named-place status; concept metadata is a routing flag |
| `بِبَابِلَ` | `بِـ` + proper place name | preserve locative/contextual bā'; host-only "Babylon" fails |
| `بِذُنُوبِهِمْ` | `بِـ` + plural host + possessive `هِمْ` | causal/prepositional relation and "their" both need learner-visible proof |
| `بِرُوحِ` | `بِـ` + host noun | relation and referent stay gated; host-only "spirit" is not rich-certified |
| `وَطُورِ` | oath/coordinating `وَ` + host noun | oath frame must be named before a family-wide hover can propagate |
| `وَهَٰذَا` | oath/coordinating `وَ` + demonstrative | demonstrative text may be right while the particle function remains gated |
| `إِلَيْنَا` | preposition stem + pronoun `ـنا` | "to us"; hamza-seat/root guard prevents false `ل ي ن` |
| `وَٱلشَّجَرُ` | `وَ` + `ٱل` + host noun | fallback "and + the trees" is not enough; breakdown and segment roles must be present |
| `يَسْـَٔلُكَ` | imperfect prefix + verb stem + object suffix `كَ` | token contribution is "ask you"; in `يَسْأَلُكَ النَّاسُ`, phrase-level "the people ask you" comes from following `النَّاسُ`, not from a hidden pronoun inside this token |
| `فَأَهْلَكْنَاهُمْ` | `فَ` + Form IV verb with 1pl subject + object `هم` | fluent phrase must still expose form, subject, object, and fā' role |
| `ثَقِفْتُمُوهُمْ` | perfect verb + subject marker + object `هم` | "you all found/came upon them"; root-family text without "them" fails |
| `تُخَالِطُوهُمْ` | imperfect verb + subject marker + object `هم` | "you mix/associate with them"; noun leakage such as "partners" fails |
| `تُمْسِكُوهُنَّ` | imperfect verb + subject marker + object `هن` | "you hold/keep them" feminine plural; suffix must be teachable |
| `أَبْوَٰبِهَا` | plural noun + possessive `ها` | noun-host suffix: "its doors/gates" if base and referent are certified |
| `يَٰٓأَيُّهَا` | vocative call + bridge + attention particle | phrase "O humanity" belongs to the construction; token pieces still need roles |
| `يَٰقَوْمِ` | vocative call + addressee/possessed host | "O my people" still needs call + addressee/possession in the learner breakdown |
| `يَابِسٍ` | lexical host only | not every initial yā is a vocative; sarf must block false `يا` splitting |
| `وَخُلِقَ` | wāw + passive perfect verb | phrase may be correct while still missing resumption/passive proof |
| `ضَعِيفًۭا` | nominal/adjectival host + accusative indefinite ending | "weak" is not rich-certified until case/role and entry linkage are explicit |
| `ٱلْمُفْلِحُونَ` | `ٱل` + nominal active-participle plural host | reject entry-root "to succeed"; token contributes "the successful ones" |
| `بِنَآءً` | nominal result/object form | reject verb gloss "to build"; token contributes a noun such as "a structure/building/canopy" |
| `إِنْ ... لَسَٰحِرَٰنِ` | particle frame plus following lām and dual predicate | do not certify `إِنْ` or the lām/dual noun without the full frame |
| `أُورِثْتُمُوهَا` | passive verb host + 2mp marker + object `ها` | "you were made to inherit it" needs passive, subject/deputy-subject, and object evidence |
| `بُرْهَٰنَانِ` | noun host + dual ending | the learner must see the dual ending; "proofs" with no dual morphology is under-explained |
| `قاعدون` | participial/adjectival host + sound plural ending | the plural ending must be visible; a root-family hover is not enough |
| `مُّطَاعٍۢ` | passive participle / adjective shape | token contribution is adjectival ("obedient/obeyed" by context), not infinitive "to obey" |
| `يُحْيِي` | imperfect prefix + Form IV stem | the initial yāʾ is morphology and must not disappear into one verb-colored host |
| `كُلُّ شَيْءٍ قَدِيرٌ` | quantifier + noun + adjective phrase | `كل`, `شيء`, and `قدير` each need visible role/color and phrase relation |

## Train C — KC-bound practice items

These items are graded objectively against
[`keys/hover-composition-and-routing.keys.jsonl`](keys/hover-composition-and-routing.keys.jsonl) and each names a
Knowledge Component in `curriculum/kc-catalog.json`. A miss routes back to this drill and is held pending
(`two_vote_required`); a learner-declared second check never clears it.

| item id | token | task |
|---|---|---|
| `HC-6-laam-sun-letter` | `ٱلْقَمَرُ` | Decide whether the article's lām is audible or assimilated before this letter, and state the rule in both directions (sun letters vs. moon letters). |
| `HC-7-laam-gemination-merge` | `ٱلنَّهْرُ` | Decide whether the article's lām has been deleted or merged into the following letter, and explain what the doubled consonant represents. |
| `HC-8-nun-wiqaya-drop` | `يُكْرِمُنِي` | Decide what the final `نِي` marks, and what is lost from the reading if it is treated the way a noun's possessive `ي` is treated. |

## Parse-key handoff

After the routing decision, produce a renderable handoff:

```text
parse_key.key:
parse_key.summary:
display classes:
```

Examples:

- `جَادَلُوكَ` → `V:III:PERF:ACT:3MP+OBJ.2MS`, display `qg-verb + qg-pronoun`.
- `بِسْمِ` → `P:BI+N:GEN`, display `qg-preposition + qg-noun`.
- `وَٱلْعَصْرِ` in an oath frame → `OATH+ART+N:GEN:DEF`, display
  `qg-oath + qg-article + qg-noun`.

If the row cannot produce a parse key because the function or attachment is not certified, the
result is not a rich hover. Route to the exact blocker and keep the public hover blank or
minimal according to the closure lane.

## Routing rules

- **Sarf first:** identify the host class, root/form where relevant, visible affixes, and suffix
  pronouns. If exact/form matching hides a clitic, route to
  [`../../sarf/procedures/clitic-and-host-morphology.md`](../../sarf/procedures/clitic-and-host-morphology.md).
- **Nahw next:** decide particle function, PP attachment, mood governance, relative/condition
  frames, and pronoun referents. If a function token lacks a standalone entry but its function
  is clear, it may be certifiable as a token contribution; if the frame is not clear, it stays
  `pending:`.
- **Separate token contribution from phrase context:** a contextual English subject, object,
  governor, or attachment may come from a neighboring word. Record the adjacent source address
  before using it in the learner explanation. For `يَسْأَلُكَ النَّاسُ`, the token contributes
  "ask you"; `النَّاسُ` supplies the phrase subject "the people."
- **Concept map last:** use concept metadata only to flag named-entity/common-word collisions
  and curriculum families. It cannot override sarf, nahw, i'rab, or verse context.
- **Public boundary always:** do not publish source labels, QAC labels, screenshot labels, or
  external wording. A public hover is authored Qamus text or blank.
- **Learner explanation is Arabic-only:** source-triangulation, authoring, deployment, live-readback,
  and public-boundary process notes belong in reports or admin gates. A tooltip explanation should
  say what the Arabic pieces contribute, not why the row is source-clean.
- **Source text before grammar:** if a Qurʾān usage card loses a hamza seat, maddah, diacritic, word
  boundary, or selected target word, stop as a display/source-text blocker. Do not build a rich
  segmentation on a corrupted citation.
- **Coverage is card-level as well as word-level:** a tranche report may not hide a visible flat
  example card behind a denominator that counts only already-selected rows. Every listed example card
  is either fully live, partially live with an explicit blocker, or blocked with a precise next action.
- **Graph edges drive rollout:** build the edge join table before probing pages by hand. The route is
  entry -> sense -> example card -> selected word -> quran/wbw loc -> payload -> rendered span. If that
  edge chain exists, use it for URLs, smoke targets, and DOM selectors. If it is missing, record the
  exact missing edge instead of widening to a full-occurrence sweep.
- **Four denominators, not one:** report entries, listed example cards, visible selected word rows, and
  rich-live rows separately. A page is not complete until every visible selected word is rich-live or the
  visible card has an exact blocker.
- **Renderer changes need cache proof:** if a role color, tooltip layout, or public JS/CSS behavior changes,
  record the asset version/cachebuster, public HTML readback, and affected CSS/JS URL. A color fix that is
  still hidden behind stale assets is not learner-visible.
- **Restart health is a gate, not a guess:** after a qamus restart, wait for service health and source/runtime
  payload parity before deciding whether content failed. Immediate transient public errors are an ops signal;
  they do not prove the Arabic payload is wrong.

## Checklist

- [ ] Did every visible proclitic (`وَ`, `فَـ`, `بِـ`, `لِـ`, `كَـ`) receive a role?
- [ ] Did every suffix pronoun receive a referent or a `pending: referent_unresolved`?
- [ ] Did `مَا`, `وَ`, and `فَـ` get a function decision rather than a default gloss?
- [ ] Did preposition + host tokens avoid host-only hovers?
- [ ] Did semantic concept metadata stay internal and non-authoritative?
- [ ] Did the final result separate token hover, phrase explanation, and learner note?
- [ ] Did the result include a compact ASCII `parse_key.key` and one display class per
      grammatical piece, without requiring the visible Arabic word to be physically split?

Use this drill before [`ayah-reading-drills.md`](ayah-reading-drills.md), after hard misses in
[`quranic-function-words.md`](quranic-function-words.md), and whenever a Qamus closure row looks
"obvious" only because the attached piece was ignored.
Then run [`parse-key-and-color-layer.md`](parse-key-and-color-layer.md) to turn the composition
into a renderer-ready parse-key/color contract.

## Authoring-append gate (loc must render as a qword before you append)

Lesson from an RH-LIVE authoring pass: the whitelist/renderer loc scheme is **mixed**. Some card
words are numbered with a **canonical** `surah:ayah:word` address; others are numbered with a
**card-local / example-scoped** index that only looks canonical (e.g. `17:15:102` and `17:15:104`,
even though canonical 17:15 has 21 words). A loc that reads like `S:A:W` is therefore **not**
proof that a hover keyed to it will attach to anything.

Rule: **an authored-append row is orphan-safe only if its loc renders as a qword span on the row's
own live page.** Verify before you append, never after:

- Read back the **real** route. The live entry page is `/vNNN` (verb) / `/nNNN` (noun) /
  `/pNNN` (particle); `?e=vNNN` is **inert** and must not be used for readback. For preview
  overlays use the real page with `?wbw_preview=1`.
- Confirm the exact loc is present as a rendered qword before append:
  `curl <base>/vNNN?wbw_preview=1 | grep 'data-loc="LOC"'`. No matching `data-loc` span means the
  loc is card-local/orphan — do **not** append; route to the crosswalk/source-card repair lane
  (`qword-denominator-and-crosswalk.md`) to obtain the address that actually renders.
- **`data-loc` presence is necessary but not sufficient — check the rendered SURFACE too.** A span at
  `data-loc="LOC"` can render a *different word* than the row targets (VN-00: an authored row keyed to
  `17:92:2` for `تَأْتِيَ`, but `17:92:2` renders `تُسْقِطَ` on the live page). Require both:
  `data-loc == row.loc` AND the rendered span's normalized surface == the row's target surface. A
  loc↔surface mismatch is a `loc_surface_mislabel` — do not append; re-key to the address where the
  target surface actually renders, or route to the crosswalk lane.
- A two-vote reviewer must check the address contract itself, not only the gloss: a card-local
  index such as `17:15:102`/`104` is an **invalid canonical `S:A:W`** and fails the contract even
  when the English gloss is correct. (This is the exact miss one RH-LIVE critic caught and the
  other did not — the address is part of what two independent checks must agree on.)

### `data-loc` is MIXED-BY-CARD (the four card types)

A later crosswalk pass established the exact rule (do not assume): the rendered `data-loc` always
equals the word's position in the **per-ref word list the renderer aligns the card against**, and
that list is one of four things — so whether `data-loc` is canonical depends on the *card*, not the
page:

1. **override with canonical range** (curator range, word numbers < 100) → `data-loc == canonical`
   → **RESOLVED**, author directly (`quran_loc == "quran:"+loc`).
2. **non-override full āyah** (the aligned list is the whole āyah) → `data-loc == canonical` →
   **RESOLVED**.
3. **override synthetic placeholder** (curator word numbers ≥ 100, e.g. `2:136:101`) → canonical is
   **not derivable offline** → **BLOCKER** (needs the curator's source-card map).
4. **non-override mid-āyah excerpt** (the aligned list is a fragment) → excerpt-local re-indexed →
   canonical **not derivable offline** → **BLOCKER** (needs a fragment→verse anchor).

Two consequences: (a) a stale/narrow sweep window makes rows look "orphaned" when they actually
render on a *different* live page — always sweep the **full live entry set**, not a fixed page range
(the live entry pages grow over time). (b) Encode a **no-orphan validator** as a hard gate: before
accepting an RH-LIVE row, require a live span at `data-loc == row.loc`, and if
`quran_loc != "quran:"+row.loc` then a `source_address_crosswalk` with `displayed_qword_loc == row.loc`
and `status == "resolved"`. Types 3–4 stay `pending:` with the exact missing anchor — never authored
at a guessed canonical loc.

### Safest authoring pattern — mirror a certified-live row

When you must author a new row for an inflected surface, do **not** hand-build the parse from the
dictionary entry. Mirror a row that is **already certified-live for the identical raw surface**:

1. Find a CERTIFIED-LIVE row whose raw surface (diacritics and all) matches the target token, and
   whose gloss is context-independent for that surface (e.g. passive `يُقَالُ` -> "is said").
2. Copy it, then **re-key** `loc` / `quran_loc` / `wbw_loc` to the target address — after passing
   the loc-attachment gate above.
3. **Blank `parse_key`** on the copy (a mirrored surface reuse is not a certified grammar-family
   propagation; leaving a stale parse key falsely asserts family safety).
4. Never substitute the dictionary **infinitive** when the inflected form differs in voice,
   person, or number. `يُقَالُ` is passive "is said", not the entry infinitive "to say"; a mirrored
   row inherits the *surface's* certified gloss, not the lemma headword. (Same trap as
   `ٱلْمُفْلِحُونَ` -> reject "to succeed"; see the Items table and
   `sarf/examples/qamus-regressions.jsonl`.)

Blank beats wrong: if no certified-live row exists for the exact surface and the loc will not
render, keep the row `pending:` with the exact blocker rather than appending an orphan.

## Dogfood controller prompt

For every production hover defect batch, add a `skill_impact` row:

- `sarf_update`: procedure/eval/drill changed, or exact no-op reason;
- `nahw_update`: procedure/eval/drill changed, or exact no-op reason;
- `qamus_only`: true only when the skill already covers the class and the row
  only needs data, renderer, or entry linkage repair;
- `next_gate`: controller reconciliation, two-vote, owner repair preview, or
  human review.

Do not count a batch as skill-dogfooded until repeated defect classes either
changed sarf/nahw artifacts or have documented no-op reasons tied to existing
rules.
