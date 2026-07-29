# Evidence custody — what lives public in-repo vs private custody

**Status:** adopted 2026-07-29 (institutionalization lane D, handoff steer §18).
This doc governs where EVIDENCE lives, and what any out-of-git evidence must
carry before a certification, packet, or report may rely on it. It extends —
never forks — `docs/certification-authority.md` (evidence bundles),
`docs/certification-policy.md` §2 (`FORBIDDEN_LABELS`), and the RM-09 boundary
rule restated in
`docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`.

## 1. The custody split

### 1.1 Public, in-repo (this repository)

The public repo carries everything a continuation agent needs to verify or
reconstruct a claim WITHOUT server access:

- **Verbatim Arabic source snippets, per the sufaha precedent.** The model is
  `qamus/examples/proof-noun-sufaha/` (source-inputs, contract, payloads) and
  the pilot's verbatim MCP evidence
  (`qamus/examples/p007-li-pilot/mcp-evidence.jsonl`,
  `qamus/examples/p007-li-pilot/votes-b-mcp-calls.jsonl`): the exact quoted
  source text used by a certification is committed byte-exact, in the evidence
  plane, at the exact address it was read from. Quoted object-language Arabic
  is public-safe; what may never appear is a private corpus *label*
  (`FORBIDDEN_LABELS`) or a server path (RM-09).
- **Hashes.** Hash-chained certification event trails
  (`qamus/examples/p007-li-pilot/certification/events.jsonl`,
  `qamus/certification/p007-geometry-wave/events.jsonl`), projection hashes
  (parity invariant), and row hashes in ledgers. A hash committed in-repo is
  the public anchor for evidence whose body lives elsewhere.
- **Structured facts.** Typed-fact tables, two-vote artifact bundles, lattice
  classifications, indexes, and reports — the full structured derivation of
  every claim, with `evidence_mode`, dependencies, and defeaters per
  `docs/certification-authority.md` §3.
- **Sanitized references to out-of-git evidence.** Pattern:
  `qamus/lattice/p007-mcp-evidence-refs.jsonl` — each row carries the
  occurrence, tool, verdict, and an opaque packet ref
  (`dawahwiki:packets/...#loc`), never a filesystem path.

### 1.2 Private custody (never committed here)

- **Server paths and topology.** No string in this repo may contain a server
  filesystem path (RM-09 — enforced mechanically in
  `tools/validate_website_payload.py` and `tools/validate_task_packets.py`).
  Ops runbooks that need paths live in the private ops tree, not here.
- **Full corpora.** Complete source corpora, morphology databases, and
  external tooling dumps. In-repo artifacts may quote them verbatim at exact
  addresses (1.1) and name their *kind* (`source_kind`), but the corpus label
  itself is private-side provenance (`FORBIDDEN_LABELS` discipline).
- **Calibration files carrying topology.** The 2026-07-29 custody review
  found 47 calibration files NOT public-safe because they embed server
  topology. These are designated to the custody plan's **private
  `fusha-evidence` mirror** (its designation is citable; its location is
  not — no server paths here, per this doc's own rule).
- **Live-store snapshots.** The live whitelist, rendered pages, and
  decisions-store are consumed read-only by lanes; captures committed here
  are bounded, sanitized excerpts (e.g.
  `qamus/examples/p007-li-pilot/live-rows.jsonl`), never the store itself.

## 2. Requirements on out-of-git evidence

Any artifact in this repo that RELIES on evidence not committed here must
satisfy all three, or the reliance is invalid:

1. **Manifest.** The out-of-git evidence is enumerated in a committed
   manifest row: what it is, its `source_kind`, the opaque ref (packet id +
   fragment, never a path), row/record count, and the producing lane.
2. **Hash.** A content hash (sha256 preferred) of the evidence body is
   committed alongside the ref, so custody transfer or later re-materialization
   is verifiable byte-exact. The sufaha lane's byte-exact rematerialization of
   `sufaha-evidence.jsonl` is the worked precedent: the committed hash let
   the evidence be restored and proven identical.
3. **Reconstruction statement.** The manifest states HOW the evidence can be
   regenerated (exact tool + inputs + commands) or, if irreplaceable
   (one-time captures), that it is archival and where custody sits
   (public repo / private `fusha-evidence` mirror / owner archive — as a
   designation, not a path).

## 3. The continuation rule

**Continuation must not depend on undocumented server-only files.** A task
packet (`qamus/schemas/task-packet.schema.json`), lane report, or tutorial is
defective if executing or verifying it requires a server-only file that has no
§2 manifest+hash+reconstruction row. The 2026-07-29 losses are the standing
lesson: `vnrec-authoritative-membership.json` was never persisted and had to
be reconstructed (`qamus/reports/vnrec/` — marked as reconstruction, not
original), and ~156 irreplaceable server-only evidence paths were queued for
an archival window precisely because they had no custody rows. New work may
not add to that debt:

- a lane that produces evidence out-of-git must commit the §2 rows in the
  same change that cites the evidence;
- a validator or gate may only consume committed fixtures (the
  `check_regressions.py` fixture-first rule) — never a live or server file;
- when custody of out-of-git evidence transfers (server → mirror → archive),
  the committed hash is the identity check; a transfer without hash
  verification is a custody gap and must be recorded as one.

## 4. Quick classification table

| Evidence class | Custody | In-repo form |
|---|---|---|
| Verbatim Arabic snippet at exact address | public | committed byte-exact (sufaha precedent) |
| Structured typed facts / two-vote bundles | public | committed JSONL + schema |
| Certification event trails | public | committed hash-chained JSONL |
| MCP call records used as evidence | public (bounded) | committed verbatim, or §2 ref+hash when bulk |
| Full corpora / morphology DBs | private | `source_kind` + address + quotation only |
| Calibration files with server topology | private `fusha-evidence` mirror | §2 manifest+hash rows |
| Server paths, ops topology | private | never — RM-09 |
| Live whitelist / decisions store | private (read-only consumption) | bounded sanitized captures |
