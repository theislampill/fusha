# GrammarProblems — eval-gate summary (GP0 + this tranche)

What the GrammarProblems study became in the Fusha → Qamus loop, and how it changed real decisions.

## The finding → the rule
A 2026 peer-reviewed study put a **free general LLM at ~33.33%** on 72 Arabic-naḥw questions (3 curricula ×
Bloom × objective/essay × direct/deep), collapsing on iʿrāb / advanced / deep / essay. **Operating rule:**
general LLM confidence is not evidence; a correct answer with wrong iʿrāb reasoning is unsafe; grammar-affecting
decisions ride the sarf/nahw evidence ladders + a difficulty-scaled gate.

## What it added (GP0)
- `grammar-problems-matrix.{json,md}` (dimensions + per-topic gate), `grammar-decision-gates.json` (4 tiers),
  `grammar-reasoning-safety.md` drill, `qamus/reports/grammar-risk-policy.md`.
- Warning in `nahw/SKILL.md` + `AGENTS.md`.
- Machine-readable gates: `irab-safety-gates`, `grammar-problems-gates`, `two-vote-required-rules`,
  sarf `verb-measure-gates` / `weak-root-gates` / `masdar-participle-gates`.
- **Enforced:** `validate_linguistic_decisions.py` rejects a decision below its required gate, a two-vote/iʿrāb
  decision missing reasoning, or a never-auto/human-review decision marked exportable. `check_regressions.py`
  carries GrammarProblems gate assertions (25 checks total).

## Where the gate changed a real outcome (this tranche)
The P13 batch is the proof the gate works, not just documents:
- The two-vote gate (corrected with the real `norm_strict` key) **kept out** genuine homographs/polysemy the model
  would have shipped: أَعْلَمُ "knows best" ↔ "I know"; سَوَآء "equal" ↔ "midst"; أَكْثَرَ verb ↔ elative; and the
  divine-Name / referent landmines ٱلْحَقّ, ٱلْعَزِيز, صَٰلِحًا.
- It **passed** 23 genuinely safe content-word glosses (same-lemma case-variant sets), applied live (+694).
- The empirical key-collision probe corrected an over-conservative first pass (bare-root reasoning) — itself a
  GrammarProblems lesson: don't trust a confident-looking judgment; verify against the real evidence.

## Net
GrammarProblems is now a **safety layer that gates production**, not a citation: it shaped which P13 candidates
shipped (23) vs. stayed pending (~21), governs every grammar-affecting Nawawī40 candidate (P17), and is enforced
by the validator + regression checker on every future batch.
