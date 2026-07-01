# `qamus/` — Fusha ⇄ Qamus bridge (research artifacts)

This directory holds the **reusable, public research layer** that sits beside (never inside)
the live Qamus root-dictionary application. Everything here is data, schemas, scripts, and
reports. Nothing here writes to a live site, talks to a server, or ships a runtime.

> **Boundary in one line:** `qamus/` *proposes*; a human *reviews*; the live app *applies*.
> The live Qamus app and its `qamus_wbw` hover layer live in a separate, private deployment
> and are out of scope for this repo.

## What lives here

| Path | Kind | What it is |
|---|---|---|
| `indexes/existing_qamus_index.min.json` | data (generated) | Read-only snapshot of the **2,092** existing Qamus entries, keyed by source-address (`qamus:v###` / `n###` / `p###`). One record per entry with `norm` / `norm_strict` / `bare` keys, root, forms, glosses, usage refs, `source_keys` backlinks. **De-duplication ground truth** — check here before authoring any candidate. |
| `scripts/build_existing_qamus_index.py` | script | Rebuilds the index + `reports/qamus-2092-terminal-scoreboard.md` from a directory of entry JSON files. Stdlib only; imports `tools/normalize_ar.py`. No live writes. |
| `reports/qamus-2092-terminal-scoreboard.md` | report (generated) | Counts of the existing corpus by class / category. Regenerate with the script above. |
| `reports/fusha-to-qamus-highlight-bridge.md` | report | The end-to-end pipeline: Fusha candidate → review → repair/addition payload → owner-gated apply → `qamus_wbw` rebuild → live. |
| `reports/skill-integration-plan.md` | report | How the `sarf`, `nahw`, `source-address`, and `linguistic-decision` skills compose into one authoring/repair flow. |
| `reports/source-address-model.md` | report | The Xanadu-style source-address graph: address grammar, repair fields, derived views, `used_by` backlinks, duplicate avoidance. |
| `reports/source-corpus-locator-summary.md` | report | The ToC-rank → page locator method for the physical source corpus (counts only; **no image paths**). |
| `reports/hover-gloss-terminal-scoreboard.md` | report | Portable scoreboard template (tokens / resolved / pending-by-reason / wrong-fixed / coverage) + latest figures. |
| `procedures/` | procedure docs | Review routing for closure batches, source triangulation/public-boundary checks, and grammar-resource use. Start with [`procedures/grammar-resource-usage.md`](procedures/grammar-resource-usage.md), [`procedures/closure-lane-routing.md`](procedures/closure-lane-routing.md), and [`procedures/source-triangulation-and-public-boundary.md`](procedures/source-triangulation-and-public-boundary.md). |
| `candidates/` | data (authored, gitignored draft area) | Proposed new/repaired entries awaiting human review. Each is a self-contained payload (see the bridge report). Not present until candidate runs land. |

Largelexicon/Qamus rollout surfaces:

- [`procedures/largelexicon-rollout-consumption.md`](procedures/largelexicon-rollout-consumption.md) — executor contract for all-visible-qword worklists, accepted crosswalks, source-clean projection, and forward/reverse trace.
- [`procedures/source-card-repair-decision-application.md`](procedures/source-card-repair-decision-application.md) — machine-readable source-card decisions and downstream invalidation.
- [`schemas/source-card-example-repair-decision.schema.json`](schemas/source-card-example-repair-decision.schema.json) — source-card repair decision schema.

Sibling research areas referenced by these docs:

- `../sarf/` — morphology (wazn/pattern, root extraction, derivation tables).
- `../nahw/` — syntax (iʿrāb, governance, particle behaviour).
- `../provenance/` — informed-by evidence ledger (kept **internal** until a claim is approved).
- `../corpora/` — frequency / token corpora used for coverage math.
- `../tools/normalize_ar.py` — the single shared normalization + harakāt module. **Never redefine `norm` / `norm_strict` / `bare` / `haraka_on` / `shadda_on` / `is_man_who`; import them.**

## The boundary vs. the live app (hard rules)

1. **No live-site code here.** No service/deploy/systemd scripts, no secrets, no private
   server paths or IPs, no raw OCR dumps, no image bytes. Scripts are stdlib-only and operate
   on local JSON you point them at.
2. **Informed-by stays internal.** External references (Quran.com, the Quranic Arabic Corpus,
   Tanzil, sunnah.com) are *evidence used during review*. They may be **named** as
   `informed_by` labels in schemas and reports, but their gloss **text is never copied**. The
   public hover artifact a reader sees must carry only `{src:'qamus', kind:'authored', lang:'en'}`.
3. **Qurʾān text is never altered.** Āyah text is reproduced verbatim or not at all.
4. **All content is original.** Glosses, definitions, and notes are authored, not lifted.
5. **Prefer PENDING over a wrong gloss.** A blank is recoverable; a confident error in
   scripture-facing copy is not.

## Quick start

```bash
# from the repo root
python qamus/scripts/build_existing_qamus_index.py --entries /path/to/local/entry/json/dir
# -> rewrites qamus/indexes/existing_qamus_index.min.json and qamus/reports/qamus-2092-terminal-scoreboard.md
```

Read [`reports/fusha-to-qamus-highlight-bridge.md`](reports/fusha-to-qamus-highlight-bridge.md)
first — it is the spine that the other reports hang off.
