> **Historical lane report** (moved from the repo root 2026-08-05). Point-in-time evidence; tallies herein are superseded — current state lives in `docs/current-state.yaml` and the generated ledgers. Do not quote numbers from this file.

# PROOF-V report — §11 real end-to-end verb proof

## Result

PROOF-V selected the owner-preferred surface `فَٱتَّبِعْنِىٓ` at `19:43:10`.
The packet is complete as a candidate proof and is not a certified or
publishable linguistic decision. Every written base letter is represented by
exactly one primary display class in the shared compiler payload.

## Selection survey

The whitelist was searched by `normalize_ar.norm_strict(surface)` and then
the selected row was checked by exact surface equality. The owner-preferred
surface has one match: whitelist line `31349`, `quran:19:43:10`. The raw
source codepoint sequence is preserved in every packet; it is not NFC-rewritten.

The fallback `تَوَكَّلْتُ` has seven surface matches:
`10:71:19`, `11:56:2`, `11:88:33`, `12:67:24`, `13:30:26`, `42:10:13`, and
`9:129:11`. Those rows have page-context entry IDs, but the repo crosswalk
does not backlink any of them to a selected-word occurrence. The fallback
therefore does not materially strengthen the target chain and was not chosen.

The target is reader-only, not a card-selected word. The nearest real
same-lexeme chain is retained and shown separately:

`entry:5d89e690256d` → `sense:5d89e690256d:s1` →
`card:5d89e690256d:u1:x12` →
`selected-word:5d89e690256d:s1:u1:f1:c28:50:x12:o28:50:12` →
`occurrence:28:50:12`.

The forward and reverse crosswalks are `deterministic_exact`; the selected
word has documented-form evidence and a canonical occurrence edge. The target
has only its rendered-appearance edge plus one explicit `source_gap`
decision-evidence edge routed to
`scholar-packet:proofv.target-lexeme-occurrence-link`. No page-context
`entry_id` was promoted into a target lexeme edge.

## Canonical typed facts and letter ownership

The producer emits seven typed fact records. They remain `candidate`, except
the absent Naḥw fact, which is `pending`/`unresolved`; none is `certified`.
The registered projector is `sarf.proofv.verb.v1`, two-vote gated, and its
result has `materialization_allowed: false`.

| Written span | Primary display class | Plane / role |
| --- | --- | --- |
| `فَ` | `qg-result-fa` | Naḥw plane; linking/result fāʾ |
| `ٱ` | `qg-verb-prefix` | Ṣarf; governed hamzat al-waṣl |
| `تَّ` | `qg-root-radical` | Ṣarf; root ت₁ and Form-VIII infix ت share one written letter |
| `بِ` | `qg-root-radical` | Ṣarf; root ب₂ |
| `عْ` | `qg-root-radical` | Ṣarf; root ع₃ |
| `نِ` | `qg-protective-nun` | Ṣarf; `sarf.protective_nun`, explicitly not a particle |
| `ىٓ` | `qg-object-pronoun` | Ṣarf; attached first-person singular object pronoun |

The derived-verb fact records root `ت ب ع`, Form VIII, active imperative,
2nd-person masculine singular, the governed hamzat al-waṣl class, and the
Form-VIII derivative-infix registry record. Treatment-C is explicit:
`C_shared_written_letter`, with idghām classification
`B_shared_letter_clean_split`; split authorization and split tone are both
false. The first root radical is explicitly inside the shared geminate. The
weak-root defeater registry is checked and records `none_triggered` for this
sound root.

Diacritics are carried as hover-only marks. The Naḥw color policy is
`overt_letters_only`; only the overt fāʾ span is on the Naḥw plane.

## Shared compiler and render proof

`shared-compiler-payload.json` is generated from the canonical typed facts and
contains at-rest spans, compact and expanded views, expanded Ṣarf and Naḥw,
hover, per-appearance identity, and readback descriptors. The public labels
are exactly:

- `Ṣarf — how this piece forms the word`
- `Naḥw — what this piece does here`

The compact view and hover remain visibly `PENDING`. Public hover provenance is
`src=qamus`, `kind=authored`, `lang=en`, with no internal `informed_by` field.
The exact raw surface reconstructs from seven spans, and compact, expanded,
per-appearance, and readback payload identities agree.

`render-proof.json` is a local fixture-payload readback proof. Its exact,
compact, expanded, identity, uncertainty, and no-mutation gates pass. No PNG
is tracked. A browser screenshot and font check were not run, and the packet
does not claim those checks.

## Verification evidence

- `python tools/build_proofv_verb.py ...` — selected `19:43:10`, nearest
  `28:50:12`, 7 facts, 10 typed graph edges, fixture readback mode.
- `python tools/validate_proofv_verb.py --self-test` —
  `PROOF-V VALIDATION PASS`.
- `python -m unittest tools.test_proofv_verb tools.test_fact_projectors -v` —
  20 tests, `OK`.
- `python tools/check_regressions.py` — exit 0, `ALL REGRESSION CHECKS PASS`;
  the three PROOF-V harness gates passed.
- `python tools/check_artifact_ergonomics.py` —
  `ARTIFACT ERGONOMICS OK`.
- `python tools/classify_artifacts.py` — dry run only; no writes.

## §13 closure boundary

### Implemented

The source survey, selection rationale, canonical typed facts, candidate-only
projector registration, FAM4/FAM5 carrier use, verb-affix registry record,
weak-root defeater state, Treatment-C gemination record, typed graph subset,
forward/reverse crosswalk readback, shared compiler payload, render-proof
fixture, manifest, validator, focused tests, full harness gate, and this report
are committed in this lane.

### Owner-gated

The direct target entry/form/lexeme/card/selected-word relationship is not in
the repo packets. The exact source-addressed Naḥw governor/object relation is
also absent. Both remain explicit scholar-packet routes. No MCP-certified fact
was invented or implied.

### Artifact-gated

The nearest chain is supported by the committed EDGES crosswalk and graph
artifacts plus the entry root/sense evidence. Public learner materialization
still requires the repository’s source-review/two-vote transitions; the
candidate packet cannot perform them.

### Partial / unverified

The durable render proof verifies payload/readback invariants only. Browser
layout, font rendering, live MCP lookup, public deployment, and live readback
remain unverified and are not represented as complete.

### Deferred by scope

No whitelist, entry corpus, EDGES artifact, deployment surface, or public
hover was mutated. There was no commit push, publication, or live mutation.
