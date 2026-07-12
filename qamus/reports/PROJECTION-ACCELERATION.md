# Projection-acceleration report — transclusion lattice (T12)

**Branch:** `fact-lattice-t12` · **base:** origin/main `a60c38c`
**Whitelist (read-only):** `rh_live_01_beta_whitelist.jsonl`, 34,322 rows, sha256 `1c06d85a…`
**Corpus denominator:** `qamus/indexes/quran-loc-surface/index.jsonl` — 77,881 Qurʾanic tokens (Tanzil Uthmani, CC BY 3.0)
**Machine-generated companion:** `qamus/reports/lattice-instrumentation.json` (regenerate with the command at the bottom)

The lattice takes **certified sarf/naḥw SEGMENTATION facts** (deployed whitelist rows — already 2-vote-certified through VN-00/01/02) and projects them **deterministically** onto byte-exact same-surface corpus occurrences that are **not yet covered**. It emits **candidate projections only**. Nothing here writes the whitelist; the known-debt manifest ceiling and the renderer completeness gate remain the deploy authorities.

## Coverage denominator

| Quantity | Count |
|---|---|
| Corpus tokens (full Qurʾan) | 77,881 |
| Covered by the certified whitelist | 34,322 |
| **Uncovered debt tokens** | **43,581** |
| Homographic surfaces (>1 certified analysis) | 2,467 |

The brief's **known-debt manifest ceiling (1,395)** is a much smaller owner-gated subset of these 43,581 uncovered tokens (the residual exact-packeted debt after VN-00/01/02). It is not enumerated in this public repo, so the reachability below is computed against the full uncovered set and split by class; the ceiling remains the deploy authority.

## The three registered projectors

Registered data-driven in `qamus/lattice/registered-projectors.json`, keyed to released `sarf@2`/`nahw@2` rule ids (skill-registry commit `73566927`). Each carries a `projector-record.v1` `registry_entry` validated against the shared schema. **A new `@2.1` rule registers by appending one JSON object** whose `class_predicate`/`guards` resolve to named callables in `tools/lattice_projectors.py` — no code change when the shipped declarative set (morphline-token + role-presence predicates; homograph / surface-exact / Form V-VI-ت / construction guards) suffices.

Every reachable occurrence is scored against four guards:
- **homograph_surface_ambiguity** → a surface bearing more than one certified analysis **routes to 2-vote** (never auto-projects).
- **surface_byte_exact** → NFC byte-exact source↔target (defensive block).
- **meta_form56_ta_split** → the rule-level **negative meta-projector** (below).
- **construction_match** → defers to the homograph route for ambiguous surfaces.

### Instrumentation against the live whitelist

| Projector | Certified source rows | Distinct source surfaces | Reachable uncovered rows | **Auto-candidates** (clean) | Routed to 2-vote (homograph) | Accel (rows / source surface) |
|---|---:|---:|---:|---:|---:|---:|
| **P-C1-IMPF** `sarf.c1_impf_segmentation.v1` | 679 | 381 | 1,020 | **215** | 805 | 2.68 |
| **P-C5-SUFFIX** `sarf.c5_enclitic_segmentation.v1` | 4,822 | 1,725 | 8,027 | **1,242** | 6,785 | 4.65 |
| **P-META-FORM56** `sarf.meta_form56_ta_negative.v1` | — (negative) | — | — | blocks, does not project | — | — |

- **Auto-candidates** = clean, non-homographic byte-exact transclusions. These need only 2-vote confirmation (the gate tier), **not authoring** — the source segmentation transcludes verbatim to the target loc.
- **Routed-to-2-vote** = reachable but homographic: the candidate is pre-filled with the source reading and the reviewer picks per-occurrence (semi-accelerated; never majority-voted).
- P-C1-IMPF's 215 auto-candidates land against the calibration target of ~254 C1 rows; P-C5-SUFFIX's enclitic population is far larger (the brief's ~493 target is a subset of the 8,027 reachable).

### P-META-FORM56 — the meta-transclusive negative projector

The ṣarf rule (DR-1 primary-source grounding): in **Form V (تفعّل)** and **Form VI (تفاعل)** the initial **ت is a derivational augment that is stem-internal** — never an inflectional/clitic prefix, so it must never be carved as a separate segment. This is encoded **rule-level, not occurrence-level**: it emits no rows; it forbids any projection that would peel a derivational ت off the stem.

The detector isolates *exactly* that case (a bare-ت non-stem segment preceding a stem whose skeleton no longer starts with ت), and correctly does **not** fire on: the legitimate imperfect person-prefix تَ of a Form V/VI *imperfect* verb (the stem keeps its ت), a plural/feminine suffix ت, or Form VIII/VII (excluded by exact form-token parsing — "Form VI" is a substring of "Form VIII", a bug this guard's precise tokenizer avoids).

Running it over the certified base surfaced a genuine, small finding:

- **Form V/VI certified base rows:** 47
- **Derivational-ت-split violations (flagged, not modified):** **6** — locs `2:259:58`, `4:115:7`, `9:114:12`, `11:56:2`, `52:33:3`, `69:44:2` (lemmas تَبَيَّنَ ×3, تَوَكَّلْتُ, تَقَوَّلَ ×2 — all Form V **perfect**, where the leading تَ can only be the derivational augment). Each carves تَ as a `verb_prefix`, leaving the stem (بَيَّنَ / وَكَّلْ / قَوَّلَ) without its augment.

These are surfaced for **owner review** under the `never_auto_resolve` gate — the lattice does not touch certified content. Downstream, the guard blocks any C1/C5 candidate that would transclude one of these mis-carves (proven by self-test `t3`).

## Acceleration thesis — reachable-by-projection vs needs-authoring

Split of the uncovered debt reachable by the two shipped positive projectors:

| Route | C1 (muḍāriʿ) | C5 (enclitic) | Total |
|---|---:|---:|---:|
| **Auto-candidate** (2-vote confirm only, no authoring) | 215 | 1,242 | **1,457** |
| 2-vote disambiguation (homograph; candidate pre-filled) | 805 | 6,785 | 7,590 |
| **Reachable total** | 1,020 | 8,027 | **9,047** |

Interpretation:

1. **The 1,457 auto-candidates already exceed the 1,395 known-debt ceiling** — from only two projectors, before any homograph disambiguation. The deterministic lattice can retire the ceiling's worth of rows via **projection + 2-vote confirmation** rather than row-by-row MCP authoring. Each certified source surface yields 2.7 (C1) to 4.7 (C5) downstream rows — that is the acceleration multiplier.
2. A further **7,590 rows** are reachable but homographic — semi-accelerated: the reviewer confirms a reading against a pre-filled candidate instead of authoring from scratch.
3. Everything beyond the 9,047 reachable (≈34,500 uncovered tokens with no byte-exact certified twin of these two classes) still needs **authoring** or additional projector classes (nominal iḍāfa, particle-function, article+host, oath — future `@2.1` registrations).

**Deploy path (unchanged authorities):** projection candidate → `merge_rh_live_packet` gated seam → 2-vote review flow → completeness gate + known-debt manifest. The lattice is a *candidate generator*, never a deploy step.

## Reproduce

```bash
python3 tools/lattice_projectors.py self-test          # red-first safety proof (7 checks)
python3 -m unittest tools.test_lattice_projectors       # 9 unit tests
python3 tools/lattice_projectors.py project \
  --whitelist <read-only rh_live_01_beta_whitelist.jsonl> \
  --corpus qamus/indexes/quran-loc-surface/index.jsonl \
  --out-instrumentation qamus/reports/lattice-instrumentation.json \
  --out-ledger qamus/lattice/projection-ledger.jsonl
```
