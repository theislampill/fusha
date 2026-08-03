# Procedure — hidden structure, maḥall, and the ẓarf ʿāmil-kind correction

**Invoke when:** an edge carries `mabni`, `mabni_on`, `fi_mahall_case_mood`, or `hidden_element`, or its
`justification_rule` is `zarf_idafa_governs_genitive`.

**Hidden elements: a closed, positively enumerated licensing inventory.** `reject_reconstruction` is the DEFAULT
for any construction not named below — a plain nominal sentence or a verbless fragment with an apparent gap
never licenses a reconstructed element just because something "seems missing" (C15/C16).

| `licensing_construction` | hidden element | obligatory |
|---|---|---|
| `kana_family_hidden_ism` | mustatir pronoun (ism of kāna/sisters) | yes |
| `inna_family_hidden_ism` | mustatir pronoun (ism of inna/sisters) | yes |
| `imperative_verb` | mustatir pronoun (subject) | yes |
| `relative_clause_object_gap` | elided ʿāʾid (resumptive pronoun) | no |
| `vocative_ya_noun` | elided calling verb (أُنَادِي/أَدْعُو) | yes |

Obligatory and non-obligatory are separate, per-row facts — flipping `obligatory` on a row changes what a
consumer may assume and must turn a bank that pins it red if flipped silently (C17 vs C18). A `hidden_element`
naming any OTHER `licensing_construction` string is refused outright
(`tools/validate_dependency_lattice.py` FAIL 17) — this is a closed enumeration, not an open pattern match.

**maḥall (positional case).** `mabni`/`mabni_on`/`fi_mahall_case_mood` are populated from the same licensed
inventory, never guessed from surface shape:
- `mabni=True` means the form is built (indeclinable) and therefore carries NO declensional exponent —
  `assigned_case_mood` must be `null` alongside it (FAIL 15: a built form asserting a visible case ending is a
  contradiction, not a fact).
- `fi_mahall_case_mood` is the syntactic slot a built form (or a shibh al-jumla predicate) occupies INSTEAD of an
  exponent, and may only be set together with `mabni=True` (FAIL 16: a positional slot claimed for a form that
  is not built is a category error — a declined form has its OWN exponent, not a maḥall).
- A maḥall is never rendered as if it were a visible sign: لَا رَيْبَ's رَيْبَ is mabni on the fatḥa, in the
  accusative maḥall, with `assigned_case_mood=null` throughout (F6/F7).

**The ẓarf ʿāmil-kind correction (D7).** 15 nouns of place/time — عند قبل بعد فوق تحت أمام وراء خلف بين دون خلال
حول نحو لدى لدن — head an iḍāfa (they take a muḍāf ilayh); they are NOT ḥurūf jarr, even though the traditional
label "majrūr bi-ḥarf jarr" is often applied loosely. `tools/fusha_governor.ZARF_IDAFA_HEADS` is a set disjoint
from `KNOWN_PREPS` (the genuine ḥurūf jarr); a ẓarf head emits `zarf_idafa_governs_genitive` with governor kind
`idafa` (`tools/grade_grammar_reasoning.JUSTIFICATION_RULE_GOVERNOR_TYPE`), never `preposition_governs_genitive`.
`nahw/rules/preposition-pronoun-rules.json#inda` already classifies عِندَ as an adverb of place / iḍāfa head —
this correction agrees with the repository's own consumed rule, it is not a new claim.

A genuine ḥarf jarr (`KNOWN_PREPS`, e.g. عَلَىٰ) is UNCHANGED and stays `preposition_governs_genitive` (F13). A
reason claim naming governor kind `preposition` whose head is in the annexation-head inventory is refused
(`tools/validate_dependency_lattice.py` FAIL 18 — the ʿāmil-kind condition).

**The exponent never rescues the correction.** A dual dependent (e.g. يَدَيْهِ after بَيْنَ) shows the same
oblique exponent (ـَيْ) for both naṣb and jarr; the annexation construction determines genitive categorically,
and that determination is never dressed up as "the visible ending confirms it" when the ending in fact does not
distinguish the two (F12).

**Boundary.** The ẓarf's OWN case and the head it attaches to are NOT modeled by this packet — every
`zarf_idafa_head` edge is headless and abstains on that separate question. Every edge here stays
`candidate`/`pending`.
