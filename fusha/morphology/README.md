# Fusha Morphology Core

Status: dependency-free smoke morphology substrate plus opt-in Qamus-derived
largelexicon candidate table.

This directory is the P1 implementation for the qamustyping2 plan. It is small by design: it proves the morphology families needed by the Mode A smoke fixtures before broad lexicon/generator expansion.

It does not vendor external morphology databases, train a model, or claim broad arbitrary-text coverage. The full
largelexicon table is the **lookup / evidence baseline (documented forms only)**: every row is a surface lifted
from an owner/Qamus-authored entry with `pattern/form/features` deliberately null — it contains **no generated
morphology**. Paradigm-licensed *generated* candidate forms (RM-40) are candidates-never-facts and live in a
separate, provably disjoint store; they are never merged into this baseline table.

## Data

- `data/prefixes.jsonl`: repo-authored proclitic, inflectional, and derivational prefix rows.
- `data/stems.sample.jsonl`: repo-authored smoke stems and full-token surfaces.
- `data/suffixes.jsonl`: repo-authored suffix rows.
- `data/compatibility-prefix-stem.jsonl`: allowed prefix/stem pairings for the smoke substrate.
- `data/compatibility-stem-suffix.jsonl`: allowed stem/suffix pairings for the smoke substrate.
- `data/patterns.jsonl`: small pattern labels.
- `data/particles.jsonl`: function-token rows.
- `data/largelexicon-stems.full.jsonl`: the Qamus-authored full stem/form
  **lookup / evidence baseline** (documented forms only; `table_role:
  lookup_evidence_baseline`), allowed by
  `fusha/lexicon/largelexicon/source-clean-table-allowlist.json`.
- `data/generated-candidates.sample.jsonl`: tiny synthetic sample of RM-40
  paradigm-generated candidates (candidates-never-facts; disjoint from the
  baseline). Runtime candidates are written to
  `qamus/indexes/largelexicon/generated-candidates/`.

## Tools

```powershell
python tools\validate_fusha_morph_db.py --self-test
python tools\eval_fusha_morphology.py --self-test
python tools\fusha_morph_analyze.py --surface "ٱلْمُبْطِلُونَ"
python tools\fusha_morph_generate.py --generation-key participle-btl-def-mp
python tools\fusha_morph_analyze.py --db largelexicon --surface "خَاضُوا"
python tools\fusha_morph_generate.py --db largelexicon --generation-key "qamus:00107b99a50e:000"
python tools\validate_largelexicon_morph_db.py --self-test
```

The analyzer emits candidate rows with visible segment surfaces. A candidate is invalid if the segment surfaces do not concatenate back to the displayed token.
