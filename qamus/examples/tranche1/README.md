# Tranche 1 fixture projection

This directory is the Q7 eight-canary architecture proof. It is generated from exactly eight read-only rows in the sibling `data/rh_live_01_beta_whitelist.jsonl` checkout by `tools/tranche1_projection.py` and is intentionally fixture-only.

Regenerate from the repository root:

```powershell
python tools/tranche1_projection.py compile --whitelist ..\data\rh_live_01_beta_whitelist.jsonl --policy qamus/examples/tranche1/canary-policy.json --out-dir qamus/examples/tranche1 --source-commit f706698a9f682de1731b1913221538c7a4289870
```

Validate exact surfaces, segment concatenation, field mappings, fact/projector lineage, typed routing, DOM fixture expectations, and source/output row hashes:

```powershell
python tools/validate_tranche1_projection.py qamus/examples/tranche1 --whitelist ..\data\rh_live_01_beta_whitelist.jsonl --source-commit f706698a9f682de1731b1913221538c7a4289870
```

The four candidate rows are review-gated projections, not linguistic certifications. The four adversarial rows remain typed queue records with blockers and routes. No file here authorizes whitelist writes, renderer writes, live DOM claims, apply, SSH, push, publication, or deployment.
