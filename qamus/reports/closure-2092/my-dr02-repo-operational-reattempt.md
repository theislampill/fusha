# DR02 — repo operations, paths, provenance, claude.ai pack — my re-attempt (2026-06-25, HEAD d67f873)

Canonical-path hygiene, batch/provenance parity, the claude.ai pack, and the corpus fixture are all validator-gated and PASS. The hover output is leak-free (0 private keys live + structural gating at every dataset level). **The decisive DR02 finding: `examples[].en` is NOT qamus-authored — it is verbatim Saheeh International** (7,700 examples, 41.3% carry the `[bracket]` interpolation signature), copied into the PUBLIC dataset. The dataset validator gates structure/leak/private keys but has no anti-copy guard. Built `audit_examples_en_provenance.py` to quantify it. **Classification: owner-gated (source/licensing).** It blocks public-repo redistribution cleanliness only — NOT coverage-to-90 and NOT the (clean) hover output.

| id | status | blocks | finding | remaining |
|---|---|---|---|---|
| DR02-1 | **confirmed_fixed** | — | Canonical path drift must be gated | none |
| DR02-2 | **confirmed_fixed** | — | Batch / provenance parity must be hard-gated | none |
| DR02-3 | **confirmed_fixed** | — | claude.ai pack must be a small text-only operational pack, not giant JSONL | none |
| DR02-4 | **confirmed_fixed** | — | Corpus fixture must be read-only (no live write, no translation copy) | none |
| DR02-5 | **confirmed_unfixed_owner_gated** | public-redistribution | examples[].en must be qamus-authored public text, NOT a copied translation — is  | OWNER DECISION: confirm Saheeh-Intl redistribution rights+attribute / replace wi |
| DR02-6 | **confirmed_fixed** | — | Public-output (hover) provenance leak risk | none for hover output |