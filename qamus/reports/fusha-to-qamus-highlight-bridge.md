# Fusha → Qamus → highlight bridge

How a linguistic observation in this **public research repo** becomes a corrected word-by-word
hover gloss on the **live Qamus app** — without this repo ever touching the live site, and
without any external source's text leaking into public copy.

```
 fusha/ (public research)            human review              live (private, out of scope)
┌───────────────────────┐   ┌──────────────────────┐   ┌──────────────────────────────┐
│ 1 candidate authoring │   │ 3 reviewer certifies  │   │ 5 DawahAgent applies          │
│   (sarf+nahw+index)   │──▶│   or rejects          │──▶│   (owner-gated)               │
│ 2 dedup vs index      │   │ 4 repair/add payload  │   │ 6 qamus_wbw rebuild → live    │
└───────────────────────┘   └──────────────────────┘   └──────────────────────────────┘
        ▲   provenance (informed_by) stays INTERNAL until step 3 certifies the claim
        └── source-address graph prevents two agents authoring the same address twice
```

The repo owns steps **1–2** and the **payload format** of step 4. A human owns step 3. The
live deployment owns steps 5–6. The repo can describe and validate the payload but **cannot
execute the apply** — that is owner-gated and lives elsewhere.

---

## Stage 1 — Candidate authoring (in `qamus/candidates/`)

An author (agent or human) produces a **candidate payload** for either a *repair* of an
existing entry or an *addition* of a new one. Authoring is driven by three inputs:

- **`../sarf/`** decides the lemma/root and wazn: given a surface token from the Qurʾān, what
  root and pattern is it? This is what stops a verb gloss from landing on a noun
  (`رَسُولًا` is the pattern *faʿūl*, a noun — **not** the verb "to send"; `ٱبْن`/`بَنَات` are
  nouns, **not** the verb "to build").
- **`../nahw/`** decides the syntactic reading that disambiguates homographs: the harakah on
  the **content letter** distinguishes `مَن` (fatḥa, "who") from `مِن` (kasra, "from", incl.
  `وَمِنَ`), `لِمَا` from `لَمَّا` (shadda), `كُلّ` from `كَلَّا`, `نِعْمَ` from `نَعَمْ`. nahw also
  flags same-root polysemes that need context (`ٱلْمُلْك` ≠ "angels"; `يَقْدِرُ` in a *rizq*
  context = "restricts", not "is able").
- **`indexes/existing_qamus_index.min.json`** is the existing-corpus ground truth.

Every candidate carries a `match_key_set` computed **only** via `tools/normalize_ar.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import norm, norm_strict, bare, haraka_on, shadda_on, is_man_who
```

> **Certification rule:** a candidate may **not** be certified to a root/sense on `norm()`
> alone. `norm()` drops the hamza seat and all harakāt — so it cannot tell `إِلَيْنَا` (root
> `ل ي ن`? no) apart, cannot tell `إيمان` from `أيمان`, cannot tell `يَأْمُرُونَ` from
> `يَمُرُّونَ`. Certification requires `norm_strict()` (or QAC) **plus** the relevant
> `haraka_on` / `shadda_on` / `is_man_who` check for short particles. `norm()` is a recall
> net for *gathering* candidates, never the deciding key.

A candidate is one JSON object:

```json
{
  "candidate_id": "cand_2026_0001",
  "op": "repair",                          // "repair" | "add"
  "target_address": "qamus:v443",          // present iff op=="repair"
  "surface_ar": "خَاضُوا",
  "match_keys": {"norm": "خاضوا", "norm_strict": "خاضوا", "bare": "خاضوا"},
  "proposed": {
    "root": "خ و ض",
    "lemma": "خوض",
    "wazn": "faʿala",                      // from ../sarf/
    "pos": "verb",
    "gloss_en": "to indulge in idle / false talk",
    "senses": [{"gloss": "to indulge in falsehood"}],
    "applies_to_refs": ["43:83", "52:12", "74:45", "9:69"]
  },
  "provenance": {                          // INTERNAL — never rendered to readers
    "informed_by": ["qac", "quran.com", "tanzil"],
    "notes": "QAC POS confirms V; harakah on content letter confirms reading.",
    "evidence_pointer": "provenance/khwd.md"
  },
  "checks": {
    "norm_only_certified": false,          // MUST be false to advance
    "haraka_checked": true,
    "verb_gloss_on_noun": false,
    "proper_name_as_verb": false
  },
  "decision": "pending",                   // pending | certified | rejected
  "public_render": {"src": "qamus", "kind": "authored"}
}
```

`provenance.informed_by` records **which external sources were consulted**, by name, as a
label. It does **not** contain their text. When the candidate ships, the public render object
is the **only** thing exposed: `{"src": "qamus", "kind": "authored"}`. No `informed_by`, no
external gloss, ever crosses the line.

## Stage 2 — De-duplication against the source-address graph

Before authoring, the candidate runner queries `existing_qamus_index.min.json`:

1. Compute `norm_strict(surface_ar)` and the bare root.
2. Look for any existing record whose `norm_strict`, `root`, or `forms[]` matches.
3. If a match exists → this is a **repair** (`op:"repair"`, `target_address` set to that
   record's source-address). The existing glosses/refs are shown to the reviewer as the
   "before".
4. If no match exists → this is an **add**, and the runner reserves a *new* address only after
   the reviewer certifies (addresses are append-only; see the source-address model).

This is what stops two parallel agents from independently re-authoring the root `خ و ض`: the
address is the dedup key, and `used_by` backlinks on the address (see source-address model)
show who is already working it. Duplicate-avoidance is structural, not by convention.

## Stage 3 — Human review (the gate)

A reviewer (the owner, or a delegated linguist) certifies or rejects each candidate. The
review surface shows: surface token in context, the proposed gloss, the *internal* provenance
(so the reviewer can sanity-check against QAC/Quran.com **for verification only**), the
sarf/nahw rationale, and the existing entry's "before" state if it's a repair.

Certification flips `decision` to `certified` and **strips/locks** the provenance from
anything downstream. Rejection is logged with a reason and the candidate stays in the repo as a
negative example (useful regression material). **When in doubt, the reviewer leaves it
`pending` — a pending token renders as plain, un-glossed text, which is always safe.**

## Stage 4 — Repair / addition payload

A certified candidate is compiled into an **apply payload** — the minimal, validated diff the
live app needs. For a repair it is `{address, field-level changes}`; for an add it is a full
entry record matching the live schema. The payload:

- carries `public_render: {src:"qamus", kind:"authored"}` and **no** `informed_by`;
- references Qurʾān by `surah:ayah` only, never embedding altered text;
- is schema-validated locally (stdlib JSON) before it is allowed to leave the repo.

The repo emits the payload; it does **not** transmit it.

## Stage 5 — DawahAgent apply (owner-gated, off-repo)

Applying a payload to the live corpus is an **owner-gated** action performed by the live
deployment's agent. The repo has no credentials, no path, and no runner for this — by design.
The gate is a human approval step; the agent never self-approves. (Mechanism intentionally
omitted here; it lives in the private deployment.)

## Stage 6 — `qamus_wbw` rebuild → live

Once the entry corpus changes, the live hover layer (`qamus_wbw`) is **regenerated** from the
entries by its own pipeline (expand → validate → build → deploy). Coverage grows as entries
grow; un-glossed tokens stay plain. A rebuild is reversible (a flag/restart). None of this is
in this repo — the repo's contribution ended at the certified payload.

---

## What the bridge guarantees

- **No external text on the page.** `informed_by` is a research label; the reader sees only
  authored Qamus content tagged `{src:'qamus', kind:'authored'}`.
- **No wrong glosses by construction.** Certification can't ride on `norm()`; verb glosses are
  blocked from nouns; proper names are blocked from verb senses (`مُحَمَّد` ≠ "to praise";
  `صَٰلِحًا` ≠ Prophet Ṣāliḥ); short particles are decided by the harakah on the content letter.
- **No duplicate work.** The source-address graph + `existing_qamus_index.min.json` make every
  candidate either a typed repair of a known address or a fresh, reserved address.
- **No repo→live coupling.** The repo proposes and validates; a human gates; the live side
  applies and rebuilds.
