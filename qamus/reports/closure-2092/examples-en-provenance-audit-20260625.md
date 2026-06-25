# examples[].en provenance audit — 20260625

> **Finding: EXTERNAL-TRANSLATION-PRESENT.** bracketed-interpolation density at this level is the signature of the Saheeh International published translation; examples[].en is a verbatim external translation, NOT Qamus-authored

| metric | value |
|---|---:|
| total example āyāt | 7,700 |
| with English (examples[].en) | 7,700 (100%) |
| unique English strings | 5,537 |
| **with [bracket] interpolation (Saheeh-Intl signature)** | **3,179 (41.3%)** |
| explicit translator-name string | 0 |

## Scope (honest)

this is the entry-level example-āyah translation field in the PUBLIC dataset; it is SEPARATE from the per-word hover output (wbw-lookup 'words'), which is live-verified Qamus-authored and leak-free

**This is SEPARATE from the hover output.** The per-word glosses shipped on hover (`wbw-lookup.json` → `words`) are live-verified Qamus-authored, `src:"qamus"`, 0 leaks. The exposure is the **entry-level example-āyah translation field** in the committed public dataset.

## Classification: owner-gated (source/licensing decision)

The example translations are a deliberate owner sourcing choice (scripture accuracy), not an accidental leak. Redistribution rights are a licensing question only the owner can settle. Remediation options:

- A) confirm Saheeh International redistribution rights for da'wah + add explicit attribution + license notice to the dataset/repo
- B) replace examples[].en with an openly-licensed translation (CC0/CC-BY) — see the open-gloss deep-research
- C) author original Qamus example renderings (large effort)
- D) drop examples[].en from the PUBLIC dataset, keep examples[].ar + ref only (Arabic is Tanzil CC BY 3.0, already attributed)

## Does NOT block coverage-to-90

Hover authoring proceeds on the clean authored layer. This item is a parallel governance/licensing decision, recorded as an exact owner blocker.
