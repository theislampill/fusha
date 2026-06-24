# Procedure — root decision

**Invoke when:** you need the root of a surface before authoring/repairing/resolving a gloss.

**Input:** surface (with diacritics if available), optional QAC root/POS, optional Qamus entry candidates.

**Checks (in order — stop at the first that certifies):**
1. Qamus entry root for this surface/form (highest authority for our gloss).
2. QAC root for this token position (`(ref, norm_strict)` — internal evidence).
3. photographed source page (when seeding).
4. external reference triangulation (internal only).
5. heuristic (`normalize_ar`) — **never sufficient alone**.

**Evidence ladder rule:** `norm()` drops hamza + harakāt → recall only, never certifies. Certify with
`norm_strict` + QAC. `إِلَيْنَا` ≠ root ل ي ن; `إيمان` ≠ `أيمان`.

**Output:** `candidate_root`, the rung used, `confidence`. If weak/hamzated/doubled and the radical is hidden →
recover from the muḍāriʿ/QAC ([`verb-form.md`](verb-form.md), `../references/weak-verbs.md`).

**Forbidden:** inferring a root from `norm()`; asserting a weak root by subsequence match (the Nawawī40 ~50%
false-tie lesson).

**Test:** `tools/check_regressions.py` (norm-vs-norm_strict invariants); fixtures `examples/root-form-decisions.jsonl`.
