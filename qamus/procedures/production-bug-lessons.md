# Production Bug Lessons

Every production hover or parse failure must feed the sarf/nahw engine, not only the live row.

Required loop:

```text
production failure -> typed graph diagnosis -> sarf/nahw procedure update -> regression fixture -> learner explanation -> drill -> validator -> future closure batch
```

Use `qamus/schemas/production-bug-lesson.schema.json` and validate with:

```bash
python tools/validate_production_bug_lessons.py qamus/examples/production_bug_lesson.sample.jsonl
```

Minimum fields:

- `bug_class`
- exact `quran:S:A:W` token addresses
- visible bad hover
- corrected hover or exact pending reason
- what failed
- sarf lesson
- nahw lesson
- learner-facing explanation
- drill prompt
- level
- procedure links
- regression fixture link
- validator link

Do not use this file to apply live changes. It is a bridge from production evidence back into reusable instruction,
fixtures, and gates.
