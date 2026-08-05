# Sarf engine completion (Phase 2)

The sarf skill is hardened into a production-grade morphology engine **and** an ajamī teaching engine,
gated by `tools/validate_sarf_skill.py` (wired into `check_regressions.py`).

## Added (not from scratch — extended the existing 13-procedure skill)

- **References:** `references/nominal-derivatives.md` (the 7 derived-noun types → pattern → gloss-shape
  contract, with the penult-vowel and prefix-vowel reads); `references/learner-error-remediation.md`
  (the 15 Madinah-study failure modes → diagnosis procedure → fix).
- **Procedures:** `procedures/nominal-derivative-decision.md` (classify fāʿil/mafʿūl/mubālagha/ṣifa-
  mushabbaha/tafḍīl/zamān-makān/āla; never a verb gloss on a derivative);
  `procedures/learner-error-diagnosis.md` (name the error class → fix + drill; teaching + engine share one loop).
- **Drills:** `drills/nominal-derivatives.md` (recognition + production per type).
- **Machine-testable evals:** `evals/nominal-derivative-error-eval.jsonl` (24 cases, all 7 types +
  confusions, each with `expected_decision` + `madina_error_class`); `evals/false-clitic-split-eval.jsonl`
  (20 cases: ٱلْمُلْك, لَهُ/فَلَهُ/وَلَهُ, بِيَدِهِ, أَنَّا, قُرْءَانًا/بُنْيَانًا tanwīn-alif, رَحْمَة ة, root-final
  ن/ك/ه, + positive controls أَعْمَالُنَا/سَيِّئَاتِهِمْ/إِيمَانِهِمْ).

## Madinah-study failure modes now encoded (where)

nominal-derivative confusion · اسم الفاعل/اسم المفعول · صيغة المبالغة · الصفة المشبهة · اسم التفضيل ·
اسم الزمان/اسم المكان · اسم الآلة · ignorance of rule constraints · long-vowel vs short-vowel ·
tanwīn-nūn vs original nūn · faulty segmentation · mother-tongue transfer ·
weak/hamzated/geminated/quadriliteral · broken plural/gender/number · false clitic stripping —
all in `references/learner-error-remediation.md` + tested in the two eval fixtures.

## Engine capabilities proven

- analyze form before authoring (root/POS/pattern/clitics/derivative type);
- the five live scars are regression fixtures: عَلِيم "All-Knowing" (not "to be in pain"),
  كَظِيم adjectival (not verb), عَادٍ "transgressor" (not the tribe), مُعَلِّم/مُعَلَّم penult split,
  ٱلْمُلْك false-split rejected;
- MCP-free (consults *available source adapters* only); public output `{src:qamus,kind:authored}`.
