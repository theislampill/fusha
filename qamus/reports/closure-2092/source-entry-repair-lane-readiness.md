# Source-entry repair lane readiness (closure-2092 Phase 4C)

`tools/build_source_entry_repair_candidates.py` + `tools/validate_source_entry_repair_candidates.py` +
`qamus/schemas/source-entry-repair-candidate.schema.json`.

Three modes, all review-only, all field-level (before/after), **no blind add_form**, **no live mutation**,
**no authored gloss** (validator rejects any `gloss` field), no external-source leak:

| `--mode` | input lane | candidates | tokens | field | gate |
|---|---|---:|---:|---|---|
| `forms_array` | forms_array_missing_surface | 89 | 158 | `usage[].forms` | two_vote (POS-correct gloss still required) |
| `quran_refs` | quran_refs_missing_or_incomplete | 40 | 72 | `usage[].examples[].ref` | source (verify before adding) |
| `source_photo` | source_photo_visual_needed | 4 | 4 | `source_photo` | source (head-on crop; never infer digits) |

- `forms_array` repairs note that a **POS-correct authored gloss is still required at 2-vote** — adding the
  form alone is not a resolution (the form-variant lane authors the gloss).
- `quran_refs`/`source_photo` are entry-completeness / source-gated; they do not directly author hovers.
- Gate: `forms_array` wired into `check_regressions`; all three pass their validator.
