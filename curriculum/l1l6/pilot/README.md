# Pilot — root vs pattern vs affix ownership (candidate mode, end-to-end)

One isolated proof of the complete instructional backprop path:
curriculum lesson family → qualified concept records → candidate procedure →
fixtures → colour segmentation → rich hover → reusable second token — with
every unsafe simplification named and every artifact candidate.

| # | Requirement | Where satisfied |
|---|---|---|
| 1 | lesson family | L1.M2 (speech divisions; ṣarf vs naḥw; root-and-pattern) — anchor lesson `L1.M2.03` |
| 2 | normalized concept records | `graph/concepts.jsonl` rows with `lesson_id: L1.M2.03` (registry-linked, stable IDs) |
| 3 | instructional explanation | `candidate-procedure.md` (original wording; staged steps M1/M3/M4 style) |
| 4 | unsafe simplifications detected | ledger `cl-002` (every-word-has-a-root), `cl-003` (root implies meaning kinship) — both guarded |
| 5 | candidate ṣarf increment | `candidate-procedure.md` (CANDIDATE; outside `sarf/`; promotion via `TP-CURR-ROOTPATTERN-PROMOTION`) |
| 6 | positive + adversarial fixtures | `fixtures.jsonl` — 2 positive, 5 adversarial |
| 7 | multi-morpheme word | `المَسْجِدُ` = definite article (clitic) + pattern augment م + root س ج د + hover-only case vowel |
| 8 | exact letter ownership | `pilot-facts.json` `letters[]`: every base letter → exactly one owner class |
| 9 | candidate colour segmentation | `projection.json` `segments` (compiled from the facts record) |
| 10 | hover from the same facts | `projection.json` `hover` (compiled from the SAME record; parity validator-enforced) |
| 11 | second analogous token | `مَكْتَب` (`pt-02`): same reusable lesson, different root, zero re-derivation |
| 12 | shared-root boundary | `pilot-facts.json` `boundary_records` (bd-sjd) + fixture `pf-adv-05`: only `shares_root` is licensed |

## Clean-room note

Example tokens are independently selected standard grammar examples
(مَسْجِد، مَكْتَب، مَلِك، مَاء، مِن) — **not** lesson-passage words — per the
controlling source-site rights ruling (see `../custody/custody-decision.md`).

## Candidate boundary

Nothing here touches live Qamus facts, entry data, or any Sol-owned surface.
No Qurʾānic occurrence is analysed (occurrence analysis needs per-occurrence
evidence; og-2). Status stays `candidate` until owner adjudication; repository
evidence does not currently permit stronger status (the sarf@2.4
letter-ownership rules it parallels are themselves candidate-only).

## Verify

```
python tools/validate_curriculum_l1l6.py --pilot-only
```

Checks: single-ownership partition, facts↔segments↔hover letter parity,
fixture schema, boundary-record honesty (no root→lexeme inference), and that
`projection.json` is byte-identical to a recompilation from `pilot-facts.json`
(`--write-pilot-projection` regenerates it).
