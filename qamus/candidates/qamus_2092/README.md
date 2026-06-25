# `candidates/qamus_2092/` — linguistic-decision batches (dry-run → review → owner-gated apply)

This directory is the **batch staging area** for the 2,092-entry Qamus pass: the hover-token
candidates that the runner turns into auditable **linguistic decisions**, awaiting a human eye before
anything touches a live system. Nothing here is published. Every record is a *proposal*.

> **Boundary in one line:** the runner *proposes*, a human *reviews*, the live app *applies* — and the
> three are separate steps with a human gate between the last two. See
> [`../../reports/fusha-to-qamus-highlight-bridge.md`](../../reports/fusha-to-qamus-highlight-bridge.md).

## What a batch is

A batch is one run of [`tools/run_linguistic_decisions.py`](../../../tools/run_linguistic_decisions.py)
over a slice of enriched candidate tokens. It produces a single JSONL of **linguistic-decision** objects
(schema: [`../../schemas/linguistic-decision.schema.json`](../../schemas/linguistic-decision.schema.json)).
Each decision is one of four types, with the sarf (morphology) + nahw (syntax) reasoning attached:

| decision type | meaning | ships? |
|---|---|---|
| `authored_gloss` | one clean, original gloss chosen with confidence | only if `public_export_allowed:true` |
| `repair_candidate` | a wrong gloss was offered; the authored correction is proposed (e.g. مَن→"who", not "from"; ٱلْمُلْك→"dominion", not "angels") | never directly — review first |
| `quarantine` | the offered gloss is categorically wrong and withheld (e.g. a "to …" verb gloss on the noun رَسُولًا) | never |
| `pending` | undecidable from the evidence at hand; a blank beats a wrong gloss | never |

Every record carries `review_status:"needs_human_review"` until a human changes it.

### Inputs each batch consumes

- **`../../indexes/existing_qamus_index.min.json`** — the 2,092-entry de-dup ground truth (read-only). Used to
  confirm a claimed root/POS and to find the matching live entry for a clean gloss.
- **an enriched candidate JSON** — a list of tokens, each `{norm_strict, surface, qac_root, qac_pos,
  ayah, qamus_glosses[]}` (plus optional `loc`, `nearby_tokens`, `referent`). The `qac_*` fields are
  internal **facts** (root + part-of-speech) used to *confirm* our own content; they are never shipped.
- **a sarf/nahw rule JSON** (optional) — declares the homograph / POS-guard / polyseme / referent rules.
  Omit it to use the runner's built-in `DEFAULT_RULES`, which encode the live qamus-highlight regressions.

## The flow

```
                 ┌─────────────────────────── dry-run (this dir) ───────────────────────────┐
enriched         │  run_linguistic_decisions.py                                              │
candidate  ─────▶│    --candidates <batch>.candidates.json                                   │──▶  <batch>.decisions.jsonl
tokens           │    --index   ../../indexes/existing_qamus_index.min.json                       │      (authored / repair /
                 │    --rules   <sarf-nahw-rules.json>   (optional; defaults built in)        │       quarantine / pending)
                 └───────────────────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼  ALWAYS validate before review
                 validate_linguistic_decisions.py <batch>.decisions.jsonl   # schema + regression invariants; non-zero on any breach
                                                  │
                                                  ▼  HUMAN REVIEW (the gate)
                 a reviewer reads each decision, flips review_status to "approved" (or sends it back),
                 confirming the sarf/nahw reason, the referent, and that no wrong gloss slips through.
                                                  │
                                                  ▼  OWNER-GATED APPLY (out of this repo)
                 apply_linguistic_decision.py stages approved records into repair/addition payloads
                 (still dry-run here). The actual write to the live Qamus + the qamus_wbw hover rebuild
                 happens behind the owner's gate, in the private deployment — never from this repo.
```

### 1. Dry-run (produce a batch)

```bash
# from the repo root
python tools/run_linguistic_decisions.py \
    --candidates qamus/candidates/qamus_2092/<batch>.candidates.json \
    --index      qamus/indexes/existing_qamus_index.min.json \
    --out        qamus/candidates/qamus_2092/<batch>.decisions.jsonl
# no network, no live writes — only the --out file is touched
```

The runner's own self-test (`python tools/run_linguistic_decisions.py --fixture`) proves the regression
fixes on a tiny inline example: مَن/مِن never collapse, no "to …" gloss lands on a noun, ٱلْمُلْك never
reads "angels", حَلِيمٌ of Ibrāhīm is "forbearing" (not a divine Name).

### 2. Validate (always, before a human looks)

```bash
python tools/validate_linguistic_decisions.py qamus/candidates/qamus_2092/<batch>.decisions.jsonl
```

This gate is hard — it exits non-zero on **any** schema breach or regression-invariant violation:

- مَن "who" and مِن "from" never collapse (incl. وَمِنَ under the proclitic);
- no "to …" verb gloss on a noun / proper-noun;
- إِلَيْنَا never reduces to the root ل ي ن;
- `public_export_allowed:true` implies an `authored_gloss` whose shipped text leaks **no** internal
  provenance (no `qac` / `tanzil` / `informed_by` / source paths).

### 3. Human review (the gate)

A reviewer reads each decision — the surface, the `sarf.reason` and `nahw.reason`, the referent — and
flips `review_status` to `approved`, or sends it back. `repair_candidate`, `quarantine`, and `pending`
**always** wait for a person; an `authored_gloss` with `public_export_allowed:true` is the only kind that
can flow forward, and only after approval.

### 4. Owner-gated apply (outside this repo)

Approved decisions are staged into repair/addition payloads by
[`tools/apply_linguistic_decision.py`](../../../tools/apply_linguistic_decision.py) (itself dry-run: it
never writes live and never ships a record that would leak provenance). The real write to the live Qamus
and the `qamus_wbw` hover rebuild happen in the private deployment, behind the owner's gate. **This repo
never performs that apply.**

## Naming + hygiene

- `*.candidates.json` — the enriched input tokens for a batch (the `qamus_glosses` here are the candidate
  meanings under consideration, not yet authored decisions).
- `*.decisions.jsonl` — the runner's output for that batch (one linguistic-decision per line).
- `*.rules.json` — an optional per-batch sarf/nahw rule override.
- Keep a small committed **sample** (`*.sample.jsonl`) per batch type; large generated runs are gitignored
  (see the repo `.gitignore` "generated-artifact rules") — commit the generator + a sample, not the bulk.

## Hard rules (inherited from `../../README.md`)

1. **No live-site code, secrets, server paths, IPs, or image/OCR bytes** here. Stdlib-only tools over local
   JSON you point them at.
2. **Informed-by stays internal.** External references may be *named* as evidence labels; their gloss text
   is **never** copied. The public hover artifact a reader sees carries only `{src:'qamus', kind:'authored'}`.
3. **Qurʾān text is reproduced verbatim or not at all.** Āyah text is never altered.
4. **All content is original** — glosses, definitions, notes are authored, not lifted.
5. **Prefer `pending` over a wrong gloss.** A blank is recoverable; a confident error in scripture-facing
   copy is not.
