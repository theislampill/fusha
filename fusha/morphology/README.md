# Fusha Morphology Core

Status: dependency-free smoke morphology substrate.

This directory is the P1 implementation for the qamustyping2 plan. It is small by design: it proves the morphology families needed by the Mode A smoke fixtures before broad lexicon/generator expansion.

It does not vendor external morphology databases, train a model, or claim broad arbitrary-text coverage.

## Data

- `data/prefixes.jsonl`: repo-authored proclitic, inflectional, and derivational prefix rows.
- `data/stems.sample.jsonl`: repo-authored smoke stems and full-token surfaces.
- `data/suffixes.jsonl`: repo-authored suffix rows.
- `data/compatibility-prefix-stem.jsonl`: allowed prefix/stem pairings for the smoke substrate.
- `data/compatibility-stem-suffix.jsonl`: allowed stem/suffix pairings for the smoke substrate.
- `data/patterns.jsonl`: small pattern labels.
- `data/particles.jsonl`: function-token rows.

## Tools

```powershell
python tools\validate_fusha_morph_db.py --self-test
python tools\eval_fusha_morphology.py --self-test
python tools\fusha_morph_analyze.py --surface "ٱلْمُبْطِلُونَ"
python tools\fusha_morph_generate.py --generation-key participle-btl-def-mp
```

The analyzer emits candidate rows with visible segment surfaces. A candidate is invalid if the segment surfaces do not concatenate back to the displayed token.
