# FAM5 derived-verb calibration fixtures

These fixtures are local, source-shaped test inputs for the FAM5 producer. They
are not Qur'an corpus data and are never a publication input.

- `entry-fixtures.jsonl` supplies the exact entry-form attestations used by the
  focused producer tests.
- `derived-form-registry.jsonl` is the deliberately closed registry for the
  derived-form classes attested by this lane.
- `producer-fixtures.jsonl` contains positive and adversarial rows. The
  adversarial rows assert typed abstention, including the explicit
  surface-template-only prohibition.

Run the focused tests from the repository root:

```powershell
python -m unittest tools.test_fam5_derived_verb_producer -v
```

The committed seven-row packet is generated in candidate mode with the lane
inputs and read-only corpus records supplied by the owner:

```powershell
python tools/fam5_derived_verb_producer.py `
  --stratified ../lanes/FAM5/strat-455.jsonl `
  --verdicts ../lanes/FAM5/v575-verdicts.jsonl `
  --entries ../data/entries.jsonl `
  --fam4-packet qamus/examples/fam4-finite-verbs/generated/calibration-sample.jsonl `
  --whitelist ../data/rh_live_01_beta_whitelist.jsonl `
  --output-dir qamus/examples/fam5-derived-verbs/generated
python tools/build_fam5_report.py
```

`../data` is a read-only input surface; the producer writes only the
candidate/unresolved packet under this fixture directory and the report.

All fixture records remain candidate-only and use
`pre_apply_not_authorized`.
