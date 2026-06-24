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
  3 function-word inventories) from **451 singular→plural pairs** + 338m/246f gender tags.

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

## Boundaries held

- No raw decks/PDFs/DOCX, no media/audio, no copyrighted body text committed.
- No external gloss text copied; external source names internal-only; public hover = `{src:"qamus",kind:"authored"}`.
- Qurʾān text unaltered; **0 Qamus entries mutated**; the one live change is hover-only via the established path.
- No Ṣaḥīḥayn live import. No OCR used as authority.
