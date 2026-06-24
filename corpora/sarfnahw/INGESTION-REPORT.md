# Sarf/Nahw corpus ingestion — final report (SN0–SN9)

Turned a local APKG/PDF/DOCX Arabic-learning corpus into reusable sarf/nahw intelligence, fed it through the
existing Fusha → Qamus bridge, and applied a small certified hover batch live. **Fusha wrote nothing live; the
single live change went through the established owner-blessed rebuild path and is reversible.**

## Ingested (SN0)

| type | files | detail |
|---|---:|---|
| Anki decks (`.apkg`) | 11 | AMAU "Learn Arabic" sections 4–8; **1,132 notes**, 694 media (not committed) |
| verb-chart PDFs | 9 | 14 pages; legacy non-Unicode Arabic font (not OCR'd) |
| verb-tables DOCX | 1 | 11 text paras + 9 image-tables (not committed) |

Raw sources, media, and audio are **git-ignored** (gitignore blocks `*.apkg *.pdf *.docx` + media); only
counts, checksums, safe samples, and distilled features are committed. Each file is `source_review_status:
needs_review` pending owner licensing confirmation.

## Extracted (SN1–SN3)

- **APKG (SN1):** 1,132 notes → clean Arabic (Latin/translit stripped), classified **765 vocabulary / 161
  nahw-drill / 197 phrase / 8 uncertain**; singular↔plural pairs + gender parsed. Reproducible extractor;
  media never read.
- **PDF/DOCX (SN2):** verb-chart **structure + English slot labels** extracted (past/present × active/passive,
  command, maṣdar, ism fāʿil/mafʿūl, لم/لن negations, forms I–XV). The Arabic glyphs are a 1995 legacy font and
  were **not** OCR-copied; canonical wazn patterns are authored from standard morphology with the chart as an
  internal `informed_by` reference only.
- **Knowledge base (SN3):** **28 deduped concepts** (10 verb measures, 7 verb classes, 7 plural patterns, gender,
  3 function-word inventories) from **486 singular→plural pairs** (202 sound-plural = orientation-certain, 284 broken = orientation-heuristic) + 338m/246f gender tags.

## Skills strengthened (SN4–SN5)

- **sarf:** SKILL.md + `rules/verb-measures.json`, `rules/root-pattern-risk-rules.json`, `references/`
  (verb-measures-table, weak-verbs, masdar-participle-notes), `drills/verb-measures.md`, +5 regression fixtures.
- **nahw:** SKILL.md + `rules/negation-rules.json`, `references/` (particles, jar-majrur, idafa, irab-case-mood),
  +7 function-word fixtures.
- **regression checker:** 19 checks (+4 new: Form IV hamza distinctness, Form II shadda, ذِكْر/ذَكَر homograph),
  6 fixture files (93 rows) — **ALL PASS**.

## Bridge to Qamus / hover (SN6–SN7)

- **SN6 candidates (review-only):** 16 hover + 1 entry-repair (كَظِيم pos/gloss-shape) + 26 review-queue
  (homograph + 13 plural-coverage ops). Deduped vs the live batch + 2,092 index; homographs routed to review.
- **SN7 applied live:** the 13 export-ready candidates were certified by **two gates** — adversarial 2-vote
  (13→11) and an empirical `norm_strict` **key-collision test** against the live corpus (11→8). The 8 key-safe
  glosses were applied via `fusha-hover-decisions.tsv` → `rebuild.sh`:
  - coverage **69.06% → 69.08%**, matched **34,459 → 34,472** (+13 added, ~3 improved, **−0 removed**),
    `validate` PASS, health 200, light+dark screenshots viewed.
  - Dropped by the gates: نَزَّلَ (key `نزل` collides with نَزَلَ "descended"), إِنفَاق/مَخْلُوق (0 occ),
    تَذَكَّرَ/زَلْزَلَتِ (2-vote — the latter a real passive-vocalization catch).
  - **Rollback:** `*.bak-sn7` tsv + `wbw-lookup.prev.json` + flag-off.

## Nawawī40 (SN8)

Refinement adds reviewer signals (189 weak-root **hints** flagged low-confidence, 112 POS guesses, priority
ranking 205/558/420, 14 hadith-technical, 166 Ṣaḥīḥayn-recurrence-likely). Automated weak-root tying measured
~50% precision, so it is **not** used to re-bucket or assert roots — classification is unchanged. No live writes.

## SN9 review (8 read-only reviewers) + remediation

An 8-dimension adversarial panel audited the work: **6 PASS** (PDF/chart extraction, sarf morphology,
nahw grammar, Qamus/hover integration incl. the 2-gate certification logic, candidate dedup, test quality),
**2 concerns** — all findings closed:

| finding | severity | fix |
|---|---|---|
| `export_hover_state.py` hardcoded two `/srv/...` paths (pre-existing) | blocker (leakage) | now env-var driven (`QAMUS_WBW_SERVICES`/`QAMUS_WBW_ARTIFACT`); no server path in the repo |
| gender field passed through raw Anki values (e.g. بِطَاءٌ) | major | clamped to `{m,f,""}` — 0 non-mf values remain |
| singular/plural label inverted for some broken↔broken pairs | blocker | sound plurals (ون/ين/ات) now oriented with certainty; broken pairs fall back to the paren convention but are **flagged `orientation:"paren"` (heuristic, not certified)** rather than asserted — the honest fix for an inherently ambiguous skeleton |

Post-fix: regression checker 19/19 PASS; leakage scan clean (no raw sources/media tracked, no secrets/keys/IPs).

## GrammarProblems eval-gate tranche (GP0 + P10–P18)

`GrammarProblems.pdf` (73-pp study: a free LLM ~33% on Arabic naḥw) was ingested as a **safety/eval gate**, not a
reference: `nahw/evals/grammar-problems-matrix.*` + `grammar-decision-gates.json` (4 tiers) + policy + drill, with
the warning in `nahw/SKILL.md`/`AGENTS.md`.
- **P10 executable gates:** `validate_linguistic_decisions.py` now REJECTS a decision below its required gate, a
  two-vote/iʿrāb decision missing reasoning, or a never-auto decision marked exportable; schema gained
  `gate`/`grammar_triggers`/`reasoning`; 6 new rule files; **25 regression checks PASS**.
- **P11/P12 completion matrices:** 2,092 entries (0 unknown, **0 fully_verified** — honest) + 49,900 tokens
  (0 silent).
- **P13 reference-assisted batch — 23 APPLIED LIVE:** coverage **69.08% → 70.47%** (+694 occ, ~51 improved,
  −0 removed). Certified by four gates (author+2vote → empirical key-collision probe → key-aware 2-vote → apply);
  ~21 homograph/referent/polysemy candidates terminally classified as pending.
- **P14:** كَظِيم entry-repair **certified payload** (owner-gated; 0 entries mutated).
- **P15:** source-address completion (2,092 nodes, 0 orphan) + duplicate-avoidance report.
- **P17:** Nawawī40 re-run under GP gates (189 weak-root hints kept low-confidence; 0 live writes).
- **P18:** rebuild verified — validate PASS, health 200, light+dark screenshots viewed; rollback `*.bak-p13` +
  `wbw-lookup.prev.json`.

## Boundaries held

- No raw decks/PDFs/DOCX (incl. GrammarProblems.pdf), no media/audio, no copyrighted body text committed.
- No external gloss text copied; external source names internal-only; public hover = `{src:"qamus",kind:"authored"}`.
- Qurʾān text unaltered; **0 Qamus entries mutated**; the one live change is hover-only via the established path.
- No Ṣaḥīḥayn live import. No OCR used as authority.
