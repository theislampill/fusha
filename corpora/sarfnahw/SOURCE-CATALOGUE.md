# Sarf/Nahw ingest corpus — SOURCE CATALOGUE (SN0)

Local, uncommitted ingest corpus. **No raw APKG/PDF/DOCX, no media, no audio, no copyrighted body text is committed** — only counts, checksums, and safe derived samples. Raw files live in a git-ignored local dir (`SARFNAHW_CORPUS_DIR`).

| metric | value |
|---|---:|
| total files | 21 |
| `.apkg` files | 11 |
| `.docx` files | 1 |
| `.pdf` files | 9 |
| APKG notes (total) | 1132 |
| APKG cards (total) | 1132 |
| APKG media files (total, NOT committed) | 694 |
| PDF pages (total) | 14 |

## Files

| file | type | size | detail | topic | extraction | source review | raw committed |
|---|---|---:|---|---|---|---|---|
| `learn-arabic-with-amau--section-7-getting-used-to-arabic.apkg` | anki_package | 7.30 MB | 34 notes · 34 cards · 34 media | getting_used_to_arabic | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-4_-getting-used-to-arabic.apkg` | anki_package | 1.29 MB | 25 notes · 25 cards · 25 media | mixed:nahw+getting_used_to_arabic | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-4_-vocab.apkg` | anki_package | 10.81 MB | 113 notes · 113 cards · 75 media | vocabulary | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-5_-getting-used-to-arabic.apkg` | anki_package | 27.92 MB | 25 notes · 25 cards · 25 media | mixed:nahw+getting_used_to_arabic | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-5_-vocab.apkg` | anki_package | 8.37 MB | 171 notes · 171 cards · 72 media | vocabulary | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-6_-getting-used-to-arabic.apkg` | anki_package | 15.78 MB | 35 notes · 35 cards · 35 media | getting_used_to_arabic | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-6_-vocab.apkg` | anki_package | 23.80 MB | 248 notes · 248 cards · 168 media | vocabulary | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-6_-vocab__vocabulary-of-comprehension-lessons.apkg` | anki_package | 11.69 MB | 108 notes · 108 cards · 83 media | vocabulary | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-7_-vocab.apkg` | anki_package | 14.58 MB | 152 notes · 152 cards · 71 media | vocabulary | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-8_-getting-used-to-arabic.apkg` | anki_package | 7.53 MB | 49 notes · 49 cards · 49 media | getting_used_to_arabic | pending | needs_review | false |
| `learn-arabic-with-amau__amau-arabic-section-8_-vocab.apkg` | anki_package | 4.92 MB | 172 notes · 172 cards · 57 media | vocabulary | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_1.pdf` | pdf | 0.06 MB | 2 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_2.pdf` | pdf | 0.07 MB | 1 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_3.pdf` | pdf | 0.09 MB | 3 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_4.pdf` | pdf | 0.06 MB | 1 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_5.pdf` | pdf | 0.08 MB | 3 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_6.pdf` | pdf | 0.05 MB | 1 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_7.pdf` | pdf | 0.04 MB | 1 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_8.pdf` | pdf | 0.05 MB | 1 pp · text | verb_charts | pending | needs_review | false |
| `set-of-9-important-arabic-verb-charts_9.pdf` | pdf | 0.05 MB | 1 pp · text | verb_charts | pending | needs_review | false |
| `verb-tables-supplement--r21.docx` | docx | 2.04 MB | 40 paras · 0 tables | verb_charts | pending | needs_review | false |

## Acceptance (SN0)
- All files in the ingest dir accounted for: **21**.
- No raw large source file committed (gitignore blocks `*.apkg *.pdf *.docx *.zip` + media).
- Catalogue committed; full extraction stays under git-ignored `corpora/sarfnahw/out/`.

> Licensing: the AMAU decks and verb-chart PDFs are third-party teaching material; their full text/media are **not** redistributed here. Internal linguistic *features* (patterns, POS, root behaviour) are extracted for reuse; verbatim deck/chart content is not. Each file is marked `source_review_status: needs_review` pending owner licensing confirmation.
