# Qamus Mode A Thin Slice

This fixture is the P0.5 gate for the Qamus/Fusha parser/checker path.

It proves a small end-to-end loop only:

visible Qamus qword -> source-address row -> morphology/syntax analysis -> public-safe hover projection -> private trace -> bidirectional edge manifest -> rendered/readback fixture -> flywheel artifact -> claim validator.

It does not claim live Qamus progress, arbitrary-text parsing, or complete Classical Arabic grammar checking.

## Smoke Cases

- `n0005_all_qword_card`: every qword in the visible 2:98 card is represented, colored, hover-projected, and reverse-traceable.
- `v100_am_lahum_particle_cluster`: `أَمْ لَهُمْ` stays function-sensitive and preserves `لَ + هُمْ`.
- `p011_verb_prefix_stem_subject`: `تَعْبُدُوا۟` exposes prefix, stem, and subject marker.
- `p018_participle_prefix_plural_suffix`: `ٱلْمُبْطِلُونَ` exposes article, derivative prefix, participial host, and plural suffix.
- `p050_vocalized_interrogative_particle`: `أَيَّانَ` keeps the cited example vocalized and function-token aware.

## Generate and Validate

```powershell
python tools\fusha_mode_a.py --source-rows qamus\examples\mode_a_thin_slice\source-address-rows.jsonl --out-dir qamus\examples\mode_a_thin_slice
python tools\validate_qamus_mode_a_adoption.py --self-test --out qamus\examples\mode_a_thin_slice\claim-validation-report.json
```

The validator should fail if public fields leak source labels or paths, segments do not concatenate to the visible surface, qg classes are unsupported, a card with an all-qword denominator is incomplete, a required fixture lacks vocalization, or a row has no forward/reverse trace.
