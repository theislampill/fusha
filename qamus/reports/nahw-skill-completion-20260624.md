# Nahw engine completion (Phase 3)

The nahw skill is hardened into a production-grade syntax/iʿrāb engine **and** an ajamī teaching
engine, gated by `tools/validate_nahw_skill.py` (wired into `check_regressions.py`).

## Added (extended the existing 13-procedure skill)

- **References:** `references/particle-functions.md` (the closed-class particle inventory × all
  functions, content-letter-harakah rule); `references/irab-teaching-map.md` (zero→fluency iʿrāb
  spine: sentence types, cases, moods, the inna/kāna/ẓanna/lā-of-genus flippers, the confusable
  accusatives); `references/learner-error-remediation.md` (15 syntax failure modes → fix).
- **Procedures:** `procedures/particle-function-decision.md` (pick the function in context, two-vote
  when iʿrāb-dependent); `procedures/irab-teaching-diagnosis.md` (produce iʿrāb / diagnose error;
  reject conclusion-only reasoning).
- **Drills:** `drills/particle-disambiguation.md`, `drills/irab-case-mood.md`.
- **Machine-testable evals:** `evals/particle-function-eval.jsonl` (32 cases covering مَا/مَن/مِن/إِنْ/
  أَنْ/أَنَّ/إِنَّ/لَا/لَمْ/لَمَّا/لَنْ/أَلَا/أَلَّا/فَمَا/وَمَا/أَمْ/أَوْ/فاء/واو/لام/حَتَّى/إذ/إذا/حيث/كأنّ/لكنّ/لعلّ/كلّا/لِمَ,
  each with `functions[]` + `context_function`); `evals/irab-polysemy-eval.jsonl` (25 per-loc
  regressions incl. 3:7:27 وَمَا="and not", 2:173:18 عَادٍ="transgressor", أَلَّا/أَلَا, فَمَا, 7:184
  جِنَّة="madness", 16:120 أُمَّة="model", يَقْدِرُ="restricts", حَلِيم="forbearing").

## Particle disambiguation now explicit + testable

Every multi-function particle has its functions enumerated and a context decision rule; the
content-letter-harakah homographs (مَن/مِن، لِمَ/لَمْ، أَمْ/أُمّ، أَلَا/أَلَّا) are split per loc.

## Safety gates

- conclusion-only reasoning is rejected (`grammar-risk-gate` + `grade_grammar_reasoning.py` AND-gate;
  88-case eval bank + 8 wrong-reasoning traps);
- same-surface polysemy is resolved per loc (the token-iʿrāb lane, B3) or kept pending with an exact blocker;
- MCP-free; public output `{src:qamus,kind:authored}`; external sources internal-evidence only.
