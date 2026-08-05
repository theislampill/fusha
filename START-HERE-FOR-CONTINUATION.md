# START HERE FOR CONTINUATION

You are (probably) an agent or engineer arriving with **zero chat context**.
This file is the single entry point for continuing the Fusha/Qamus programme
from the repo alone. Everything here is either verifiable from committed
artifacts or explicitly marked as reported-elsewhere.

## 1. What this programme is

One sentence (controlling thesis):

> The Qurʾān is the canonical anchor; Classical Arabic is the generative
> engine; transclusion preserves provenance; the lattice preserves structured
> possibility; meta-projection governs reuse; the flywheel turns reviewed
> Qamus occurrences into progressively stronger machinery.

Four systems, one architecture. **(1) The Qamus** — a public learner's
dictionary of 2,092 Arabic entries (947 verbs, 1,045 nouns, 100 particles)
whose example āyāt are live-rendered with rich, letter-level hover glosses.
**(2) Fusha (this repo)** — the portable language-intelligence layer: ṣarf/naḥw
skills, deterministic parsers and validators, and the typed-fact plane that
turns each Qurʾānic occurrence into evidence-backed, certifiable linguistic
facts. **(3) The meta-transclusive lattice** — the graph of entries, senses,
occurrences, morpheme occurrences and appearances, with fact-level
certification (`tools/certify_typed_fact.py`) and hash-paritied projections,
so one reviewed analysis is *transcluded* (reused with provenance) everywhere
the same occurrence appears, and never laundered across distinct occurrences.
**(4) The delivery plane** — the live website consumes owner-gated deploy
packets built from certified projections; a separate website agent owns the
renderer. This repo produces candidates, evidence and reports; it **never**
mutates anything live.

## 2. Current HEAD and how to verify

- Branch off `origin/main`. Machine-readable state: `docs/current-state.yaml`
  (generated — regenerate with `python tools/build_current_state.py`, check
  freshness with `--check`).
- Verify the checkout before trusting anything:

```
git rev-parse HEAD
python tools/check_regressions.py     # must end: ALL REGRESSION CHECKS PASS
```

If the harness does not pass, stop and fix that first — nothing else is
trustworthy on a red harness.

## 3. Completed milestones (verbatim scope — do not inflate)

- **P007_LI_NOUN_HOST_PILOT — 12 / 78 / 49**: the jarr clitic **لِـ** (entry
  p007) on noun hosts: **12 morpheme occurrences / 78 appearances / 49
  certified typed facts** (13 direct + 36 two-vote rung), with genuinely
  independent reviewer-B, 12 two-surface projections, and **0 hash forks**
  across all 78 appearances. This pilot scope is NOT "p007 accounted".
  Artifacts: `qamus/examples/p007-li-pilot/`.
- **p007 full population — the 11-state tally** (recomputed by
  `tools/validate_p007_universe.py`; authoritative store
  `qamus/lattice/p007-reverse-universe.jsonl` + `.meta.json`): discovered
  2,999 / dispositioned 2,999 (partition: 454 deterministic-attachment-
  geometry · 866 direct-source-attested-function · 340 two-vote-required ·
  2 scholar-required · 1,337 rejected-false-candidate) / entry links certified
  12 / sense edges certified 12 / function certified 12 / governor+case
  certified 12 / geometry certified **454 rows = 1,362 facts** / direct-source
  function queue 1,308 / two-vote queue 340 / scholar queue 2 / rejected
  closed 1,337. The 11 `P007_*` states are the ONLY completion vocabulary for
  p007 (owner ruling).
- **VN span gates**: VN-00 (12,775 spans) · VN-01 (14,052) · VN-02 (12,185)
  each re-verified **100% span-live** on 2026-07-28 (server-side smokes;
  tranche-level claim). the next unverified window measured 69.38% (3,280-row worklist) under the
  pre-2026-08-05 windowing (then called VN-03 = v142–v188 + n0136–n0180); the
  2026-08-05 owner respec re-cut boundaries (see `docs/VN-OPERATIONS.md` §1),
  so that measurement spans the respec's VN-03/VN-04 and is per-page in
  `qamus/reports/pvn-rollout-map.jsonl`. Span-live ≠ rich.
- **~2,057 lane-certified typed facts** — exact strata, never merge them:
  49 pilot (in-repo, event-verified) + 1,362 geometry wave (in-repo,
  event-verified; mechanical attachment geometry ONLY — not identity, function
  or sense) + 520 direct-source w1 function facts + 126 two-vote w1 facts
  (both w1 lanes live in owner packets, **not yet committed to this repo**;
  in-repo verifiable subtotal = 1,411). **Warning: facts ≠ occurrences ≠
  entries ≠ appearances** — four different denominators; conflating them is a
  reportable defect.

## 4. Accepted owner decisions

`docs/decision-ledger.md` (public-safe copy of the owner's controlling
ledger). Nothing listed there is open — never re-present a decided item as a
question. Highlights you will trip over otherwise: VN-03 namespace
(VNPROP-xx is the proposal namespace, never the contract window), the p007
completion vocabulary, the direct-source function-certification rung, "no
deployment without owner window + website-agent confirmation".

## 5. Prohibited actions (hard boundary)

1. **No live mutation** of any kind — website, whitelist, entry store,
   renderer, services, ops. This repo produces candidates and reports only.
2. **No website frontend edits** — the website agent owns templates, renderer,
   CSS/JS (see `docs/qamus/website-handoff/`). No competing renderers.
3. **No shadow runs** — shadow scheduling was retired by the owner; any future
   run needs explicit bounded owner authorization.
4. **No root-sharing → identity inference** — root sharing NEVER implies entry
   identity; letter resemblance ≠ morpheme identity; surface match NEVER
   authorizes reuse.
5. **No candidate promotion without evidence** — the certifier
   (`tools/certify_typed_fact.py`) is the only path to `certified`; general
   LLM confidence is not evidence; prefer pending over wrong.
6. **No majority-voting scripture** — Qurʾān text is read-only; scripture-
   facing certification is owner-gated; genuine source disagreements become
   attributed-unresolved, never a vote.
7. **No source-prose leakage** into public output; no page-context laundering;
   the shipped hover record is exactly `{"src":"qamus","kind":"authored","lang":"en"}`.

## 6. Current work queues

`qamus/work-queues/next-actions.jsonl` — 4 queue heads (direct-source w2,
two-vote w2 incl. the 6 convention re-votes, بِـ pre-flight verification,
VN-00 note-normalize wave), each pointing at its full packet and repo queue
source. **The public, executable task packets live in `qamus/task-packets/`**
(one `TP-*.json` per queue head, validated by
`tools/validate_task_packets.py`); each queue row's `repo_packet` field names
its committed packet — the `full_packet` owner packets are private-workspace
supplements, not prerequisites. Blockers that only the
owner/arbitration/scholars can close: `docs/blockers.yaml`.

## 7. Exact commands

`docs/golden-commands.md` — one canonical command per operation, with inputs,
outputs, mutation scope, exit expectations and report locations. GAP-marked
where no command exists yet. Do not invent alternative invocations.

## 8. Evidence locations

- **Certification event trails** (append-only, hash-chained):
  `qamus/examples/p007-li-pilot/certification/events.jsonl`,
  `qamus/certification/p007-geometry-wave/events.jsonl`.
- **Typed facts**: `qamus/examples/p007-li-pilot/typed-facts.jsonl`,
  `qamus/certification/p007-geometry-wave/typed-facts.jsonl`.
- **Universe / lattice**: `qamus/lattice/` (example-āyah universe 117,117
  rows / 50,041 unique occurrences; particle matrix; p007 reverse universe;
  entry-occurrence edges; projection ledger).
- **Rollout state**: `qamus/reports/pvn-rollout-map.jsonl` (+ meta) — one row
  per entry, per-tranche rollups.
- **Tafsir MCP evidence refs**: `qamus/lattice/p007-mcp-evidence-refs.jsonl`
  (verbatim source text stays in the evidence plane, never public payloads).
- **Owner packets** (private workspace, referenced by name only): the
  `dawahwiki packets/` series — method + wave evidence for lanes not yet
  committed here.

## 9. Verification requirements

- **Workspace hygiene before baseline** (discovered by the 2026-07-29 cold
  trial): the baseline harness requires a normalized, generated-artifact-clean
  tree — a long-lived checkout can fail up to 7 checks spuriously from
  (a) tracked files checked out before the `.gitattributes` `eol=lf` rules
  landed (fix: `git rm --cached -r -q . && git reset --hard HEAD`) and
  (b) stale git-ignored generated files — dist/ packs, caches, installs
  (fix: `git clean -fdX`; all ignored files are regenerable by repo
  convention). Prefer a fresh clone/worktree for baseline verification; if
  using an existing checkout, run both commands first.
- Run `python tools/check_regressions.py` before and after any change; a PR
  is mergeable only on ALL PASS.
- Recompute, never trust: tallies come from validators
  (`tools/validate_p007_universe.py`, `tools/build_pvn_rollout_map.py
  --self-test`, `tools/build_current_state.py --check`), not from prose.
- Data artifacts must pass `python tools/check_artifact_ergonomics.py`.
- Grammar decisions require the ṣarf/naḥw evidence ladders (`sarf/SKILL.md`,
  `nahw/SKILL.md`); iʿrāb-bearing conclusions need two independent checks
  agreeing on conclusion AND reason; a correct answer with wrong iʿrāb
  reasoning is unsafe.
- Tafsir MCP: surface-match returned words, never index-trust; ≤3 bounded
  retries; MCP is an evidence source, never reviewer-B.

## 10. Escalation rules

- **Abstain-and-packetize**: when a task exceeds your tier
  (`docs/model-routing-guide.md`) or evidence is insufficient, do NOT guess —
  write a self-contained packet (row ids, evidence addresses, the precise
  question) and queue it.
- Genuine linguistic disputes → arbitration/scholar rows in
  `docs/blockers.yaml`; they never block other lanes.
- Owner-only: deployment windows, entry-store mutation, rule adjudication,
  anything touching the live site. The owner is never asked to guess
  linguistic answers.
- Authority precedence: verified repo artifacts+tests → owner decision ledger
  → handoff steer → canonical architecture docs → historical charters → chat.

## 11. Next recommended task

Head of `qamus/work-queues/next-actions.jsonl`: **p007 direct-source function
certification wave 2** (bounded Tafsir MCP + triangulation per row over the
remaining direct-source queue, under the decided function-certification rung).
It is tier-2, non-blocking, fully specified, and its machinery already exists.
Its committed executable packet is `qamus/task-packets/TP-P007-DS-W2.json`
(the wave-1 exclusion set is the committed coverage manifest
`qamus/task-packets/tp-p007-ds-w1-covered-locs.json`).

## 12. Glossary (controlling senses)

- **entry** — one of the 2,092 public dictionary pages (p/v/n `source_key`,
  stable `entry_id`); a first-class knowledge node with typed edges.
- **occurrence** — one canonical Qurʾānic token location
  (`quran:s:a:w`); the unit analysis attaches to.
- **morpheme occurrence** — a sub-token unit: one morpheme (e.g. clitic لِـ)
  at one occurrence; distinct node from the host token's occurrence.
- **appearance** — one *rendering* of an occurrence on some card/page; one
  occurrence has many appearances; all appearances of one occurrence must
  carry the same projection hash.
- **candidate** — any produced row/edge/fact not yet through the certifier;
  candidates never reach public output.
- **certified** — passed `tools/certify_typed_fact.py` with a reconstructible
  evidence bundle on the correct ladder rung; recorded in a hash-chained event
  trail; revocable.
- **transclusion** — reuse of one reviewed analysis at the *same occurrence*
  everywhere it appears, provenance preserved (location-first: same-occurrence
  transclusion is distinct from guarded analogous projection).
- **meta-transclusion** — governed reuse *across* occurrences/entries via
  typed edges and guards (never surface-match).
- **lattice** — the *parser-engineering* sense: the structure holding multiple
  admissible analyses (structured possibility) until evidence collapses them;
  NOT a UI or décor metaphor.
- **projection** — deterministic compilation of certified facts into a
  render-ready artifact; parity = identical hash across appearances (modulo
  the closed presentation whitelist).
- **fully rich** — an occurrence whose rendered span carries the complete
  letter-level rich hover; fully rich ≠ deployed.
- **dogfood** — using the machinery on our own corpus to find defects before
  deployment; dogfood findings become fixtures and regression guards.
- **VN tranche** — a contract window of verb+noun pages on the authoritative
  page ordering (owner respec 2026-08-05: VN-00 = 47v+45n, then 45v+50n evenly; VN-00..VN-20).
- **VNPROP** — the balanced-partition *proposal* namespace (VNPROP-00..
  VNPROP-20 + universe labels); preserved for comparison only; never a
  contract window and never quoted as VN-xx.
