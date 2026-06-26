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
- exact `source_addresses` including both the `quran:S:A:W` token and its `wbw:S:A:W` hover slot
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

Each lesson must remain graph-addressed. A lesson that says "the word X was wrong" is not enough; it must identify
the exact rendered hover slot, link to the sarf/nahw/qamus procedure that should prevent recurrence, and point to a
validator or regression fixture. This keeps ANDON reports from becoming chat-only corrections.
