# claude.ai learner-runtime self-test (closure-2092 Phase 10)

Each scenario routes to a sarf/nahw skill + procedure + curriculum checkpoint + drill, with the expected
answer shape and the claude.ai-vs-Claude-Code boundary. (Routing source: `curriculum/tutor-runtime-routing.md`.)

| scenario | route | expected answer shape | claude.ai can? |
|---|---|---|---|
| alphabet / harakah beginner placement | `curriculum/placement-test.md` → `zero-to-fluency-roadmap.md` L0–L1 | placement level + next checkpoint | yes (teach) |
| confuses tanwīn-nūn vs original nūn | `sarf/procedures/noun-plural-gender.md` + `references/learner-error-remediation.md` | "ـٌ/ـٍ/ـً is case+nunation, not a root nūn"; drill | yes |
| confuses ism fāʿil / ism mafʿūl | `sarf/procedures/masdar-participle.md` + `nominal-derivative-decision.md` | penult-vowel rule (مُعَلِّم vs مُعَلَّم); drill | yes |
| gives a verb gloss to a noun derivative | `sarf/procedures/masdar-participle.md` + sarf principle 3 | "POS mismatch is a blocker — noun takes a noun gloss" | yes |
| how to speak a simple Fuṣḥā sentence | `curriculum/zero-to-fluency-roadmap.md` (nominal/verbal sentence) + drills | model sentence + production drill | yes (teach; no runtime) |
| is this token form-variant-safe? | `closure-2092/review-only-casebook.md` + `sarf/procedures/homograph-risk.md` | bucket + collision check + gate | partial (review; cannot run validators) |
| is this particle gloss too generic? | `nahw/procedures/particle-decision.md` + `audit_hover_gloss_quality` flag | "needs particle function, not 'from'/'what'" | yes (review) |
| may a candidate copy external source wording? | `provenance/source-boundaries.md` | "no — authored Qamus output only; PENDING beats a copied gloss" | yes |

**Boundary:** claude.ai teaches/reasons/reviews/drafts; it CANNOT run validators, edit the repo, or apply
live decisions — those need Claude Code (per `fusha-project-instructions.md`).
