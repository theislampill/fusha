# AGENTS.md — rules for agents working in the Fusha repo

This is the **portable language-intelligence** repo for the Qamus project. It is **public** and it is **not** the
live app. Read `provenance/source-boundaries.md`, then `sarf/SKILL.md` + `nahw/SKILL.md` before authoring or
classifying any Arabic gloss.

## Hard rules (non-negotiable)
1. **No live-site mutation from this repo.** Never write to qamus.dawah.wiki, the live app repo, entry data, or
   any production system. Fusha produces *candidates and reports*; applying them is a separate, owner-gated step.
2. **No app code copied in.** No live qamus/qamus-highlight runtime, no systemd/deploy/service scripts, no
   website CSS/JS/theme, no smokes, no production backups.
3. **No secrets, no private paths, no images, no weights, no large OCR dumps.** Never commit `/srv/...` paths,
   IPs, SSH wrappers, API keys, raw source photos, model weights, or bulk OCR text. Public repo.
4. **External references are internal evidence only.** You may consult Quran.com, QAC, Tanzil, sunnah.com and
   **name** them as `informed_by` labels in internal records/schemas — but you must **never copy their gloss
   text**, and nothing external may appear in a public-facing artifact.
5. **Authored glosses must be original.** Write concise, original qamus-style English from your *understanding*;
   do not paraphrase-launder an external gloss. Preserve uncertainty when it exists.
6. **Public artifacts must not leak `informed_by`** or any external source name, OCR snippet, or source path.
   The shipped hover record is exactly `{"src":"qamus","kind":"authored","lang":"en"}`.
7. **Qurʾān text is never altered.** Treat scripture as read-only; certification of scripture-facing fields is
   owner-gated (a human verifies refs/counts; OCR is discovery, never authority).

## Decision discipline (from hard-won qamus-highlight regressions)
- **`norm()` never certifies anything.** It drops hamza seats + harakāt for recall only. Use `norm_strict` /
  `bare` / QAC root+POS for any root, sense, or hover decision. (`إِلَيْنَا` is **not** root ل ي ن; `إيمان`≠`أيمان`.)
- **Preserve hamza-seat distinctions** (أ/إ/ؤ/ئ/ء) and read short-particle harakāt on the **content** letter, not
  the first letter (مَن "who" vs مِن "from", incl. وَمِنَ; لِمَا vs لَمَّا; كُلّ vs كَلَّا; نِعْمَ vs نَعَمْ; أَنِّي vs أَنَّى; لَمْ vs لِمَ).
- **POS mismatch is a blocker.** Don't put a verb gloss on a noun/proper-noun (رَسُولًا≠"to send"; ٱبْن/بَنَات≠"to
  build"; مُحَمَّد/صَٰلِحًا are proper/descriptive, not the verbal root).
- **Context decides multi-sense roots** (يَقْدِرُ in rizq-context = "restricts"; حَلِيمٌ for Ibrahim = "forbearing",
  not a divine Name). Use the source-address graph to avoid duplicate decisions.
- **Prefer pending over wrong**, always, with a precise reason. Wrong public glosses are worse than honest gaps.
- **Grammar-safety gate (GrammarProblems eval).** General LLM confidence is **not evidence**; grammar decisions
  require the sarf/nahw evidence ladders. A **correct answer with wrong iʿrāb reasoning is unsafe.** iʿrāb,
  case/mood, istithnāʾ, لا النافية للجنس, ambiguous iḍāfa/jar-majrūr, multi-sense, and referent-sensitive
  decisions need **two independent checks agreeing on conclusion AND reason**; uncertain naḥw → pending. See
  `nahw/evals/grammar-decision-gates.json` + `qamus/reports/grammar-risk-policy.md`.

## Commit rules
- Commit only to this repo's paths. Stage explicit paths; verify staged set before committing.
- Commit a **sample + generator** for large outputs; keep full output gitignored under `out/`.
- Every committed index/report names the script that regenerates it.
