# Skill integration plan — one authoring/repair flow

Four research skills compose into a single, ordered authoring-and-repair flow. Each skill is a
focused decision-maker; the flow is the contract that wires their outputs together into a
certified candidate payload (see `fusha-to-qamus-highlight-bridge.md`).

| Skill | Lives in | Decides | Reads | Emits |
|---|---|---|---|---|
| **sarf** (morphology) | `../sarf/` | root, lemma, wazn/pattern, POS | surface token + `tools/normalize_ar.py` | `{root, lemma, wazn, pos}` |
| **nahw** (syntax) | `../nahw/` | the disambiguating reading; homograph + polyseme resolution | sarf output + āyah context | `{reading, disambiguation_basis, context_refs}` |
| **source-address** | `source-address-model.md` + `indexes/` | is this a known address (repair) or new (add); who else touches it | `existing_qamus_index.json` | `{op, target_address?, used_by}` |
| **linguistic-decision** | this report (§ decision protocol) | certify / pending / reject; which check gates apply | all of the above | `{decision, checks, public_render}` |

## Composition order (and why this order)

```
surface token (S, A, W)
      │
      ▼
[ sarf ] ──► root + wazn + POS  ───────────────┐
      │                                         │  POS gates the gloss class:
      │                                         │  verb-gloss-only-on-verb,
      ▼                                         │  noun-pattern-blocks-verb-sense
[ source-address ] ──► op (repair|add) + addr  │
      │   (dedup against existing_qamus_index)  │
      ▼                                         ▼
[ nahw ] ──► reading + homograph/polyseme resolution
      │   (harakah on CONTENT letter; context refs)
      ▼
[ linguistic-decision ] ──► certify | pending | reject + public_render
```

1. **sarf first** because POS is a *gate*, not a hint. If sarf says the token is a noun of
   pattern *faʿūl* (`رَسُولًا`), no verb gloss may attach downstream, full stop. Same for
   `ٱبْن`/`بَنَات` (nouns, not "to build") and proper names (`مُحَمَّد` is a name, not the verb
   "to praise"; `صَٰلِحًا` is an adjective/name, not "the Prophet Ṣāliḥ").
2. **source-address second** so authoring knows whether it is repairing a known entry or
   adding a new one *before* it spends effort, and so `used_by` backlinks reveal parallel work.
3. **nahw third** because the homograph/polyseme decision needs the candidate's intended sense
   *and* the āyah context together. nahw owns the harakah-on-the-content-letter rule and the
   context-sensitive polysemes (`ٱلْمُلْك` ≠ "angels"; `أَنْهَٰر` ≠ "daytime"; `يَقْدِرُ` in a
   *rizq* context = "restricts").
4. **linguistic-decision last** as the single point that can say *certified*, applying the gate
   checks and writing the public render tag.

## Decision protocol (the `linguistic-decision` skill)

A candidate advances to `certified` **only if every gate passes**. Any failure → `pending`
(safe, renders plain) or `reject` (logged with reason). The gates, in code-checkable form:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import norm, norm_strict, bare, haraka_on, shadda_on, is_man_who

KASRA, FATHA = "ِ", "َ"

def gate_not_norm_only(cand):
    # certification must use norm_strict (hamza-seat aware) or QAC, never bare norm()
    return cand["checks"].get("certified_via") in ("norm_strict", "qac")

def gate_hamza_seat(cand):
    # norm() collapses these; norm_strict() must keep them distinct
    s = cand["surface_ar"]
    return norm_strict(s) == norm_strict(cand["proposed_surface"])  # seats must agree

def gate_pos(cand):
    # a verb gloss may not land on a noun/name; a verb sense needs a verb POS
    is_verb_gloss = cand["proposed"]["pos"] == "verb"
    return not (is_verb_gloss and cand["sarf"]["pos"] in ("noun", "name", "adj"))

def gate_particle_harakah(cand):
    # short homographs decided by the harakah on the CONTENT letter (after any و/ف proclitic)
    s = cand["surface_ar"]
    fam = cand.get("particle_family")
    if fam == "man":     # مَن 'who' vs مِن 'from' (incl. وَمِنَ) vs مَنَّ 'to bestow'
        return cand["proposed"]["gloss_en"].startswith("who") == is_man_who(s)
    if fam == "lamma":   # لِمَا vs لَمَّا (shadda on the mīm)
        return ("when" in cand["proposed"]["gloss_en"]) == shadda_on(s, "م")
    return True

GATES = [gate_not_norm_only, gate_hamza_seat, gate_pos, gate_particle_harakah]

def decide(cand):
    if all(g(cand) for g in GATES):
        cand["decision"] = "certified"
        cand["public_render"] = {"src": "qamus", "kind": "authored"}
    else:
        cand["decision"] = "pending"   # never auto-reject; pending renders plain & safe
    return cand
```

> The functions above are **illustrative wiring**, not redefinitions: all normalization /
> harakah logic comes from `tools/normalize_ar.py`. The gate code only *composes* those
> primitives into pass/fail decisions.

## Provenance handling across the flow

- sarf/nahw may **consult** external corpora (QAC, Quran.com, Tanzil) and **name** them in the
  candidate's internal `provenance.informed_by`.
- The `linguistic-decision` skill is the last hop that touches provenance: on `certified` it
  copies **nothing** external into the public payload — it writes only
  `public_render: {src:"qamus", kind:"authored"}`.
- Therefore the composition has exactly one egress point for public copy, and it is hard-wired
  to authored-only. There is no path by which an `informed_by` label or external gloss reaches
  the reader.

## Outputs of the composed flow

For each surface token the flow emits one candidate object (schema in the bridge report):
- a **repair** payload (`op:"repair"`, `target_address`) when the address is known, or
- an **add** payload (`op:"add"`) when it is new and certified,
- or nothing actionable (`pending`/`reject`) — the safe default.

These feed Stage 4 of the bridge unchanged.
