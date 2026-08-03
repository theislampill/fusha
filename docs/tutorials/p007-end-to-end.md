# P007 end-to-end tutorial — the worked vertical slice, step by step

**Status:** adopted 2026-07-29 (institutionalization lane D, handoff steer §17).
**Audience:** a continuation agent — including a cheaper model — that must run
the NEXT family or wave by copying the METHOD below. The one rule that governs
this whole document: **the method transfers; the linguistic conclusions never
do.** Every worked value shown here (a gloss, a function, a root) is evidence
about ONE exact occurrence; reusing it on another occurrence without that
occurrence's own evidence is the exact failure mode this pipeline exists to
prevent (surface match never authorizes reuse).

Everything below is reconstructed from the committed pilot artifacts in
`qamus/examples/p007-li-pilot/` — the jarr clitic **لِـ** (entry
`b10a1ee04666`, sense 2) on **noun hosts**: 12 canonical occurrences, 78
entry-page appearances, 49 typed facts, scope name `P007_LI_NOUN_HOST_PILOT`.
NOT DEPLOYED: candidate mode throughout; nothing here mutates a live surface.

Gate: `python tools/validate_p007_pilot.py --self-test` then
`python tools/validate_p007_pilot.py` (wired in `tools/check_regressions.py`,
P007PILOT block). If those two commands are green, every artifact this
tutorial cites is intact.

---

## The 18 steps

### Step 1 — Fix the family predicate BEFORE looking at rows

File: `qamus/examples/p007-li-pilot/family-selection.json`.
Write the selection predicate first (entry + sense + host class: "jarr clitic
لِـ attached to a NOUN host"), with explicit inclusion criteria and explicit
exclusions. A family chosen after seeing the data is not a family, it is a
rationalization. The predicate names the pilot population (12 occurrences)
and links every occurrence to its entry-page appearances.

### Step 2 — Build the candidate lattice, rivals included

File: `qamus/examples/p007-li-pilot/candidate-lattice.jsonl` (15 rows).
Enumerate candidates from the committed occurrence universe
(`qamus/lattice/particle-occurrence-matrix.jsonl` — p007 has 2,999 candidate
rows) — 12 in-family plus **3 deliberately retained rivals** that look like
members but are not. Rivals are kept in the lattice so the method must defeat
them explicitly, not silently drop them.

### Step 3 — Reject the rivals WITH defeaters, not by silence

File: `qamus/examples/p007-li-pilot/locations.json`
(`rejected_false_candidates`). Each rejection records its defeater + evidence
ref:

- `quran:2:187:9` لِبَاسٌۭ — lexical-initial lām (the source reads the whole
  token as a noun, wazn فِعَال; no jarr-harf clause). Letter resemblance ≠
  morpheme identity.
- `quran:48:29:42` لِيَغِيظَ — lām of taʿlīl over a verb host: genuinely a
  jarr harf, but the host is not a noun → outside THIS family.
- `quran:31:14:14` لِى — genuine jarr lam on a PRONOUN host (yāʾ
  al-mutakallim) → outside the noun-host family.

A wave that cannot show its rejections with defeaters has not done step 3.

### Step 4 — Warm up the evidence source, then evidence per occurrence

File: `qamus/examples/p007-li-pilot/mcp-evidence.jsonl` (warm-up + 12+3
`analyze_word` records + `fetch_ayah`). Method rules: warm up first
(`fetch_ayah(1,1)`); ONE call per row; **surface-match the returned word
against the row surface — never trust the index**; capture the response
verbatim into the evidence plane; ≤3 bounded retries. Evidence is per
occurrence: the 3 rivals get evidence too (that is what defeats them).

### Step 5 — Mint morpheme-occurrence identity nodes

File: `qamus/examples/p007-li-pilot/morpheme-occurrences.jsonl` (12 rows,
`qamus.particle_morpheme_occurrence.v1`). The unit of certification is the
MORPHEME OCCURRENCE at an exact canonical loc with an exact base-letter span
— not the token, not the surface string. Exact char spans (first base letter
+ trailing combining marks) are recorded here; the NFC lessons live in
`locations.json` (shadda/vowel order, fused wasla elision, diptote fatha
sign).

### Step 6 — Author typed facts, one fact = one claim = one evidence policy

File: `qamus/examples/p007-li-pilot/typed-facts.jsonl` (49 rows). Facts are
per-plane and per-occurrence (identity, attachment geometry, function,
governor, case sign, …), each carrying its `evidence_mode`, dependencies, and
defeaters per `docs/certification-authority.md`. Certification is per-fact,
never per-word (the sufaha model: one word, eleven facts, four evidence
modes).

### Step 7 — Build the sanitized reviewer-B worklist

File: `qamus/examples/p007-li-pilot/reviewer-b-worklist.json`. Reviewer B
must be genuinely independent: the worklist carries rows, controlled
vocabulary, and encoding conventions — **rival-symmetric** (members and
rivals look identical) and with ZERO expected answers. Anything that leaks
lane-A's conclusions poisons the second vote.

### Step 8 — Vote lane A

File: `qamus/examples/p007-li-pilot/votes-a.jsonl`. Lane A votes each row
with its own evidence, recording conclusion fields in the governed vocabulary
(function key, attachment key, case/mood with sign visibility, reason key
from `qamus/skills/reason-key-registry.jsonl`), plus prose left uncompared.

### Step 9 — Vote lane B, independently, with its own MCP calls

Files: `qamus/examples/p007-li-pilot/votes-b.jsonl`,
`votes-b-mcp-calls.jsonl` (24 records). Reviewer B sees only the step-7
worklist and gathers its OWN evidence. Distinct engine + reviewer id are
recorded; independence is auditable, not asserted.

### Step 10 — Assemble two-vote artifacts; agreement on conclusion + reason

File: `qamus/examples/p007-li-pilot/two-vote-artifacts.v1.jsonl` (12 bundles;
migrated form `two-vote-artifacts.v1_1.jsonl` with
`migration-provenance.json`). Agreement is computed on **conclusion AND
reason key, never on gloss text** (`gloss_text_used_for_agreement: false`).
Gate: `python tools/validate_two_vote_artifacts.py <bundles.jsonl>`.
Disagreements become arbitration packets; they are never averaged (see
`two-vote-diff-report.json` — empty in the pilot, 12/12 verified).

### Step 11 — Certify through the engine, and let it refuse

File: `qamus/examples/p007-li-pilot/certification/events.jsonl` (303
hash-chained events: the original 147 plus 156 append-only GAP-N12 migration
events). The 36 location-only legacy claims are now `review_required`; 36
versioned successors bind exact v1.1 fact values and remain the current
certified facts; 12 dependency-rebind events point the segmentation facts at
those successors. Mapping and terminal-hash provenance live in
`certification/claim-binding-migration.json`. Command:
`python tools/certify_typed_fact.py --validate qamus/examples/p007-li-pilot/certification`.
Facts certify only when their ladder rung is satisfied
(`docs/certification-authority.md` §2): direct source attestation for
read-offs, two-vote bundles for iʿrāb-bearing conclusions. The certifier
REFUSING a fact until the bundle passed is the system working — refusal is
recorded, never re-worded around.

### Step 12 — Draw the transclusion edges without laundering sense identity

File: `qamus/examples/p007-li-pilot/transclusion-edges.jsonl`. Every
certified morpheme occurrence carries the explicit certified entry edge
(`morpheme_occurrence_instantiates_particle_entry` → `entry:b10a1ee04666`)
and a candidate-only sense edge (→ `sense:b10a1ee04666:2`), plus clitic-host /
governor / governed-expression edges. The contextual-function fact contains no
entry/sense identity, so it cannot certify that sense edge. A separate
occurrence-to-sense fact is required before public transclusion.

### Step 13 — Build the reverse index (entry → occurrences)

File: `qamus/examples/p007-li-pilot/entry-reverse-index.json`. p007 → its 12
certified morpheme occurrences → 78 appearances grouped by page class (n:22 /
v:54 / p:2), while sense 2 remains candidate-pending. Transclusion is
bidirectional or it is not transclusion.

### Step 14 — Project two surfaces with exact letter ownership

File: `qamus/examples/p007-li-pilot/projections.jsonl` (12 canonical candidate
projections + 78 appearance hashes). Regenerate the exact-claim boundary and
hash consumers with `python tools/migrate_p007_claim_binding.py --apply`.
Projection carries exact spans, `qg-*`
renderer classes, and learner-register notes — compiled FROM certified facts,
never authored ad hoc.

### Step 15 — Prove cross-page parity

File: `qamus/examples/p007-li-pilot/parity-report.json`. Every appearance of
one occurrence carries the SAME projection hash (NFC normalization lesson
lives here). A hash fork between two pages is a defect, full stop.

### Step 16 — Read back the live surfaces, read-only, and record the deltas

Files: `qamus/examples/p007-li-pilot/live-rows.jsonl` (read-only capture),
`production-difference.json`. Compare candidate projections against the live
rows: the pilot found 10/12 boundary-identical, 2 true live carve forks
(2:187:63, 4:11:5) + 12 colour-class deltas. The difference table is the
owner-gated candidate upgrade set — recorded, NOT deployed.

### Step 17 — Close the reverse trace

File: `qamus/examples/p007-li-pilot/reverse-trace.json`. From any projection
you can walk: projection → facts → certification events → two-vote bundle →
votes → MCP evidence → matrix row → live row. If any hop is missing the
slice is not closed. This is also the custody proof: nothing on the chain
depends on an undocumented server-only file (`docs/evidence-custody.md` §3).

### Step 18 — Measure what the slice unlocks, then gate everything

File: `qamus/examples/p007-li-pilot/vn-unlock.json` (direct 78 appearances;
pattern ceiling 580 rows / 1,266 appearances — a GUARDED CEILING, not a
certification: per-row evidence stays mandatory). Then wire the whole slice
into CI: `tools/validate_p007_pilot.py` (red-first `--self-test`), gated in
`tools/check_regressions.py` (P007PILOT block). A slice that is not gated
will drift.

---

## Mini-example 1 (verb/noun): root-family ≠ entry-identity

Committed proof: `qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json`
(the multi-entry token canary, `quran:61:5:4` لِقَوْمِهِ) plus the vn-entry-canaries
lane evidence cited in its `evidence_refs`/`provenance.source_refs`.

One token, THREE entry relationships with three DIFFERENT edge kinds:

| edge target | relation_kind | what it claims |
|---|---|---|
| p007 `b10a1ee04666` | `clitic_component_of_entry` | the لِ segment instantiates the particle entry |
| n912 `65d3d5c51f24` | `candidate_entry` | the written form may belong to this noun entry (candidate) |
| v005 `3041d6f44a27` | `root_family_of_entry` | the occurrence SHARES THE ROOT ق و م with the verb entry — and nothing more |

The `root_family_of_entry` relation (added in payload schema 1.1.0) is "a
root-agreement relation ONLY, never a lexeme/entry-membership claim"
(`tools/validate_website_payload.py`). قَوْم shares a root with قَامَ; it is not
an occurrence OF the verb entry. A cheaper model copying this method must
never collapse `shares_root` into `instantiates` — different edges, and
root-sharing NEVER implies entry identity. The renderer contract makes the
same point visually: each relation kind renders in its own register
(`docs/qamus/website-handoff/HANDOFF-RECORD.md` §1.3).

## Mini-example 2 (verb/noun): documented claims ≠ current certification authority

Committed proof: `qamus/examples/website-payloads/verb_qamu_2_20_13.payload.json`
(قَامُوا, `quran:2:20:13`) and `noun_rajulayni_2_282_59.payload.json`
(رَجُلَيْنِ, `quran:2:282:59`) — the verb/noun entry canaries.

Both carry `provenance_class: illustrative-from-live` and
`certification.status: unresolved` today. Their `provenance.source_refs`
document that a separate `vn-entry-canaries` lane store once claimed root and
lexeme-attachment facts as certified (cross-source corroboration, its own
event trail) — but that lane store is not one of the two committed
certification stores `tools/website_evidence_resolver.py` consults, so those
facts resolve `evidence_unresolved`, not `certified`. **Citing a fact id in
`evidence_refs` never certifies it by presence** — only resolution against
the repository's own committed certification-event trail does. Look at the
per-fact plane map after `tools/migrate_website_evidence_fail_closed.py`'s
honest downgrade:

- قَامُوا: `root: review_required`, `lexeme_attachment: review_required`
  (the documented lane-store claim, not currently repository-authoritative)
  — `segmentation: candidate`, `function: candidate`.
- رَجُلَيْنِ: form attestation + lexeme attachment `review_required` — root
  and case honestly `candidate`.

That a FORM is documented somewhere (a dictionary, a lane store) certifies
nothing about what the word is DOING on this page — case, governor, and
function are page-context facts that need their own rung (two-vote for
iʿrāb-bearing conclusions) — and it certifies nothing about this repository's
CURRENT certification authority either, until that documented claim is
re-run through this repository's own certifier and its evidence resolves
against a committed store. The certifier refused the page-context facts
pending bundles, and the payloads honestly carry them as candidate; the
form-level facts are honestly carried as `review_required` pending
re-certification here. The same lesson in particle form is the مَا pair:
`ma_relative_2_284_10.payload.json` vs `ma_nafiya_93_3_1.payload.json` — one
entry (`b8e480aebafe`), one surface, two occurrences, two DIFFERENT
occurrence-specific candidate analyses, neither currently certified, each
citing its own occurrence-level evidence ref (PROOF-P candidate-contract fact
`sha256:c5e69dac…`, which is candidate-only and never certification
authority; two-vote bundle `two-vote-artifact:quran_93_3_1:v11`, valid review
evidence not yet bound by a certification-event trail). Function is an
occurrence edge, not a property of the entry — and neither leg's evidence ref
currently resolves as certification authority.

---

## What a continuation wave copies, and what it must not copy

COPY: the 18-step order; the per-occurrence evidence discipline; the
rival-symmetric two-vote method; per-fact evidence modes; certified-entry plus
candidate-sense boundary; parity hashing; read-only live checks; the NOT-DEPLOYED
honesty table; the CI gate pattern. The wave-shaped instances of this method
are issued as task packets in `qamus/task-packets/`
(`qamus/schemas/task-packet.schema.json`,
`python tools/validate_task_packets.py`).

NEVER COPY: any gloss, function, root, carve, or colour class from a worked
example onto a new occurrence. If the method is right, the new occurrence's
own evidence will say what it is.
