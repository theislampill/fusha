# Procedure — nawāsikh (kāna/inna/ẓanna families) government

**Invoke when:** an edge carries `trigger_family` in `{inna_family, kana_family, zanna_family}`, or
`governing_regime` is one of those three, or the trigger surface belongs to the لكن/إن/أن/كأن/ليت/لعل/كان-sisters
roster.

**Invariant — discrimination BEFORE expectation.** The regime must be established before any case expectation is
emitted. `governing_regime` is populated FIRST; a case expectation produced alongside
`governing_regime=regime_undetermined`, or with no `governing_regime` at all on an abrogator-family trigger, is a
hard failure (`tools/validate_dependency_lattice.py` FAIL 10). No family-first / case-second producer exists in
this codebase — build it that way.

**Surface-key integrity (read before matching a trigger):**
1. Strip the وَ/فَ proclitic before keying the family lookup (`fusha_governor._family_key`, restating
   `tools/fusha_nahw_particle_rules._deproclitic`). وَلَٰكِنَّ keys as لكن, not ولكن.
2. Read the shadda. The light and heavy members of لكن do NOT share a key: only a geminate لكنّ is `inna_family`;
   a light لكنْ is a recognized member of the closed `NONGOVERNING_PREVERBAL` inventory (positive evidence of
   "no governor"), and an unweighted (undiacritized) لكن is `regime_undetermined` — never guessed as either.
3. إن/أن/كأن/ليت/لعل keep their pre-existing unconditional mapping (their light/heavy alternation is out of
   scope for this packet; do not extend the لكن treatment to them without a dedicated review, since
   `tools/test_rm26_nahw.py` pins undiacritized إن to `inna_family`).

**Regime table:**

| regime | ism | khabar | ism rule | khabar rule |
|---|---|---|---|---|
| `inna_family` | accusative | nominative | `nasikh_governs_ism_nasb` | `nasikh_governs_khabar_raf3` |
| `kana_family` | nominative | accusative | `kana_governs_ism_raf3` | `kana_governs_khabar_nasb` |

`zanna_family` (ẓanna/ḥasiba/wajada/...) is TWO senses under one trigger surface: the judgemental (qalbī) sense
takes two accusative objects; the literal-perception sense takes one object and does NOT license the
two-accusative expectation. `sense` is a SUPPLIED feature, never inferred from the surface — with no supplied
sense, the two-accusative expectation is not asserted (`abstain(sense_dependent_gate)`).

**Abstention vocabulary (closed, and each is a DIFFERENT reason from the others):**
- `marking_unknown` — the regime is known but the ism/khabar's own marking is not confirmed (an unknown value, or
  a syncretic exponent such as the sound-masculine-plural oblique ـينَ, which is shared by naṣb and jarr and
  therefore never confirms either — F3, F12).
- `sense_dependent_gate` — a ẓanna-family trigger with no supplied judgemental sense.
- `licenser_absent` — a polarity-licensed kāna-sister (ما زال type) with no supplied negative-polarity licenser
  (`polarity_licenser=absent`). These licensers are SUPPLIED features; they are never added to the
  unconditional kāna roster (that would silently license the family without evidence). M3: `licenser_unknown`
  is NOT a currently produced value — `_h_nawasikh` (`tools/fusha_governor.py`) matches only the literal
  `absent` value; any OTHER supplied `polarity_licenser` value that is not itself a recognized regime name
  falls through to the generic `regime_undetermined` abstention below, not a dedicated "unknown licenser"
  reason. Do not cite `licenser_unknown` as a produced value until a real branch exists for it.
- `bracketing_ambiguous` — more than one abrogator is stacked and the clause bracketing (which one takes scope
  over what) is a SUPPLIED input that was not given. No case is assigned to either.
- `regime_undetermined` — the trigger is recognized but its own weight/shape does not confirm a governing
  regime at all (an unweighted لكن).

**Consistency violation, never a correction.** When the SUPPLIED ism/khabar marking contradicts the discriminated
regime's expectation (for example the kāna pattern — ism raf3, khabar nasb — appearing under an inna-family
head), the edge is `contradiction_marker=True` + `decision_status=pending`. No case is assigned, and the text is
never silently "corrected" to the regime the marking would otherwise imply (`inc-nawasikh` guard g-naw-3).

**Hidden ism.** A kāna/inna-family construction whose ism is not written (mustatir) and whose khabar is realized
as a shibh al-jumla (prepositional phrase) licenses a hidden element via the closed inventory
(`kana_family_hidden_ism` / `inna_family_hidden_ism`, obligatory) — see
`nahw/procedures/hidden-structure-and-taqdir.md`. The khabar in that shape carries no declensional exponent at
all (`assigned_case_mood=null`), only the positional (maḥall) slot (`mahall_positional_case`).

**Boundary.** This family assigns no case by itself when the regime is undetermined or the licensing/sense/
bracketing gate is not cleared. Every emitted edge stays `candidate`/`pending`; a case expectation is never
"resolved" outright by this packet — a two-vote (`irab`/`case_or_mood`) gate is always required.
