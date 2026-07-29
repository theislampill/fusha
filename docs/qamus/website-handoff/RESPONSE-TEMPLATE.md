# Website-agent response template — `qamus.website_projection_payload.v1`

**Purpose.** The standing reply format for the website agent's answer to the
handoff (`HANDOFF-RECORD.md` §2–§3). One response per adoption round. Copy
this file's section skeleton verbatim; every section is REQUIRED — write
"none" rather than deleting a section, so absence is always explicit. File the
completed response as an appended entry in `HANDOFF-RECORD.md` §3 (or as a
sibling file referenced from there).

Boundary reminders (contract §, `HANDOFF-RECORD.md` §4): the website agent
never edits payloads or linguistic facts; defects are REPORTED here, never
repaired renderer-side; no server paths or private corpus labels may appear
in this response in either direction (RM-09 / FORBIDDEN_LABELS).

---

## 1. Response header

| Field | Value |
|---|---|
| Responding agent | *(id/version of the website agent)* |
| Date | YYYY-MM-DD |
| Contract version read | `WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md` @ *(commit sha)* |
| Payload `schema_version` consumed | *(e.g. 1.1.0)* |
| Samples consumed | *(list of `qamus/examples/website-payloads/*.payload.json` actually rendered)* |
| Validator run | `python tools/validate_website_payload.py` output: PASS / FAIL @ *(commit sha)* |

## 2. Supported fields

Enumerate every payload field the renderer CONSUMES and renders, at the
granularity of the contract's field list (envelope, `projection.*`,
`hover_cards[*].*`, `reverse_links.*`). For each: where it renders (at-rest /
hover-compact / hover-expanded / not-visual-but-used), and any transformation
applied (must be presentation-only — sorting, styling; never content).

| Field | Rendered where | Notes |
|---|---|---|
| … | … | … |

## 3. Unsupported fields

Every field the renderer currently IGNORES or renders degraded. For each:
why, what the degraded behavior is, and whether support is planned. Unknown
keys ignored under forward-compatibility (§9) are listed here too — silence
is not compliance.

| Field | Behavior today | Planned? |
|---|---|---|
| … | … | … |

## 4. Renderer assumptions

Every assumption the renderer makes that the contract does not state
explicitly (font availability, bidi handling, CSS inheritance of the `qg-*`
classes, caching keyed on `projection_hash`, page-kind routing, treatment of
`null` vs absent). Each assumption is a candidate contract clarification —
state it so Fable can confirm or correct it in `HANDOFF-RECORD.md` §3.

- …

## 5. Parity results

The contract §5 obligations, verified and reported:

| Check | Result |
|---|---|
| Same `occurrence_id` ⇒ same `projection_hash` across all rendered appearances | PASS / FAIL (list forks) |
| Renderer never mutates a `projection` field (incl. re-serialization) | PASS / FAIL |
| Readback: slice-by-span and join-segments reconstruct the same surface, byte-identical, for every consumed payload | PASS / FAIL (list failures) |
| Same-surface/different-analysis pair renders as two DIFFERENT analyses (`ma_relative_2_284_10` vs `ma_nafiya_93_3_1`) with no cross-contamination and no shared cache entry | PASS / FAIL |
| Multi-entry token renders each `entry_links` relation kind in its own register (sample 7) | PASS / FAIL |
| `qg-unresolved` renders neutral only; alternatives in the alternatives plane | PASS / FAIL |

Any FAIL row is a defect report: include payload file, field, observed vs
expected, and screenshot/DOM reference (internal ids only).

## 6. Open questions

Questions for Fable, numbered, one per row — each will be answered in place
in `HANDOFF-RECORD.md` §3. Contract-change requests belong here (never
unilateral renderer-side workarounds).

1. …

## 7. Adoption blockers

What prevents rendering payloads on live pages today, in priority order.
Distinguish: (a) contract blockers (payload lacks something), (b) renderer
blockers (website-side work outstanding), (c) decision blockers (owner input
needed). Nothing in this section authorizes deployment — deploy remains
owner-gated on the Fusha side regardless of renderer readiness.

| # | Blocker | Class (a/b/c) | Proposed resolution |
|---|---|---|---|
| … | … | … | … |
