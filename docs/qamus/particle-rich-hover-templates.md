# Particle rich-hover component templates (P00 pilot) — learner-language spec

**Status:** documented template spec, 2026-07-29 (P00-vertical-slice pilot dogfood; candidate,
owner adjudicates). **Sits beside** `particle-projection-contract.md` §1.2 (the hover teaching
plane) and `RICH-HOVER-NORMALIZATION-CONTRACT.md` (rendered-field discipline). It fills the gap
between the contract's ordered hover-card ITEM list and the actual English a learner reads.

**Why a spec and not fd_compiler code.** The natural consumer is the `_fd2_*` note-builder layer
in `tools/fd_compiler.py` (`_fd2_sarf_note`, `_fd2_local_nahw_note`, `_fd2_relation_text`). That
layer is a set of **closed deterministic functions with byte-pinned expectations** in
`tools/test_fd_compiler.py` — not a data-driven template layer. Adding these particle templates
there changes committed fd2 verdict artifacts, which is an fd-lane decision. Until the fd lane
adopts them (adoption path in §4), this document is the normative wording source; the pilot's
`p00-vertical-slice/projections.jsonl` artifacts instantiate every template below verbatim.

## 1. The five component templates

Every particle/clitic hover card renders these five components, in contract §1.2 order. All
placeholders are typed-fact projections — a template slot may only be filled from a certified (or
honestly-unresolved) fact; an unfillable slot forces the honest-generic variant, never a guess
(norm@1 N-PED/N-LANG discipline: learner-register English; Arabic only as object language; no
Arabic iʿrāb formulas in teaching fields; no workflow/process prose).

### T1 — particle identity

> **{component_surface}** — from the tool-word entry **{headword}** ({sense_label}).

Source facts: entry edge (`particle_identity.entry_id`, headword, sense). Links to
`/qamus/entry/{entry_id}`.

### T2 — rootlessness (ṣarf line; never a blank root)

> Ṣarf — how this piece forms or attaches: This little {letter_name} is not built from a
> three-letter root — it is an indeclinable tool word (a particle). It attaches to the word
> after it.{fused_note}

`{fused_note}` variants (written-form keyed, from the segmentation fact):
- joined clitic: " Written joined to its host; the host keeps its own letters."
- fused rasm (لِلَّهِ): " Here the writing fuses: this letter keeps only its own lām, and the
  rest of the written word belongs to the name it attaches to."

Source fact: `particle_rootlessness` (certified at entry level in the pilot). The root field
renders as *no root — tool word*, never as an empty root slot.

### T3 — jarr relation (naḥw line)

> Naḥw — what this piece does here: it governs the next word, pulling it into the jarr
> (genitive) state{sign_clause}.

`{sign_clause}` variants (from the case fact — sign AND the reason the sign is what it is):
- visible kasra: ", whose sign here is the kasra under its last letter"
- diptote fatḥa (لِءَادَمَ): ", whose sign here is a fatha because the name does not take tanwīn"
- pronoun host: " — here the word it governs is already a fixed pronoun, so no ending changes"

Government convention: the stated governor of the majrūr is **the preposition itself**
(`preposition-governs-majrur`); the mutaʿalliq/attachment is T5's business, never this line's.

### T4 — governed expression

> It governs: **{governed_expression}** {host_gloss_paren}

Source facts: `governor_relation` + the host segment. The governed expression is the HOST
(e.g. آدم، الملائكة), quoted as object language inside the English sentence.

### T5 — case sign + attachment (where the phrase lands)

> Together they make one phrase ("{phrase_gloss}") that {attachment_clause}.

`{attachment_clause}` variants (from the attachment fact):
- verb attachment: "belongs to the verb {verb_surface} — it tells you where/for whom the action lands"
- fronted predicate (khabar muqaddam): "stands first in the sentence as its predicate — Arabic
  fronts the 'for …' phrase, and the subject follows"
- temporal (لِدُلُوكِ): "marks the time the verb happens"

Both khabar-muqaddam notations ("khabar muqaddam" / "mutaʿalliq to an elided fronted khabar")
render THIS SAME clause — one analysis, one reason key (`khabar-muqaddam-shibh-jumla`).

## 2. Honest-unresolved variants

Contract §1.3: an unresolved function renders the alternatives symmetrically; these templates
then swap T3–T5 for: "Scholars read this little word more than one way here: {alt_list}. Each
reading is shown; none is certified yet." Never render one rival as the winner.

## 3. Worked instantiations (pilot-certified)

- **لِءَادَمَ (quran:2:34:5)** — T2 joined + T3 diptote-fatḥa + T5 verb attachment (اسجدوا).
  The pilot's best pedagogical catch: the hover *teaches why the sign is a fatḥa*.
- **لِلَّهِ (quran:12:31:24)** — T2 fused-rasm + T3 visible-kasra + carve لِ ∣ لَّهِ.
- **لِأَهْلِ (quran:9:120:3)** — T5 fronted-predicate clause (khabar of كان fronted).
- **لِى (quran:31:14:14)** — outside the noun-host family: T3 pronoun-host variant; both
  segments rootless (T2 for the lām; the pronoun renders its own closed-class card).

## 4. Adoption path into fd_compiler (when the fd lane takes it)

1. Add a `particle_jarr` branch to `_fd2_component_gloss` (currently returns the generic
   "a prepositional prefix") keyed on `typed_kind`/role `jarr_clitic_lam`.
2. `_fd2_sarf_note` gains the T2 rootlessness form for rootless function segments (the current
   generic line "is one typed piece of the written composition" under-teaches rootlessness).
3. `_fd2_relation_text` already has `preposition_governs`; add the T3 sign clauses keyed on
   `case_or_mood.sign` + `sign_reason` and the T5 attachment clauses keyed on `attachment.role`.
4. Re-pin `tools/test_fd_compiler.py` expectations in the same change; fd2 verdict artifacts
   regenerate — an fd-lane release, gated by its own regression checks.
