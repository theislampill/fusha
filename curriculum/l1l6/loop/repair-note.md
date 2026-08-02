# Flywheel loop — repair note (candidate plane)

The complete required chain, each step a committed artifact:

1. **lesson-derived unit** — `increments/inc-ownership/unit-v1.json`
   (machine pack derived from the L1.M2 root-and-pattern lesson family via
   instructional unit `u-s01`).
2. **consumer invocation** — `tools/curriculum_unit_consumer.py` loads the
   pack at runtime; the rules live in the pack (mutation-proven by its
   `--self-test`).
3. **candidate analysis** — run 1 (`run-1-ownership-v1.json`): 7 fixtures
   decided under v1.
4. **positive and adversarial decisions** — positives pass; adversarial
   `own-adv-01` (مَلِك, radical م) and abstention probe `own-abs-01`
   (no evidence) FAIL.
5. **recorded failure** — `failure-record.json`: defect classes
   `shape_rule_cannot_represent_radical_mim` and
   `overgeneralization_og2_og6`.
6. **fixture/procedure repair** — `unit-v2.json` replaces `own-r2-v1` with
   `own-r2-v2`: ownership REQUIRES supplied root evidence; an initial م is
   an augment only when the evidence excludes it from the radicals; missing
   evidence abstains (`no_root_evidence`); weak radicals become
   `hidden_radical` records, never forced onto surface letters.
7. **second token through the repaired consumer** — run 2
   (`run-2-ownership-v2.json`): 7/7 pass, including `own-pos-03`
   (مَجْلِس, root ج ل س) — a token neither version was written against,
   analyzed by the repaired RULES with zero per-token re-derivation. Method
   transferred; no conclusion was copied.

Both runs are deterministic recompilations (`--record`); the curriculum
validator recomputes them and byte-compares, so drift between the packs,
the consumer and the recorded loop is red in CI. Everything stays candidate;
nothing certified, nothing live.
