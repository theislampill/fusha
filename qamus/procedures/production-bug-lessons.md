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

When the failure starts from a Phase 3 hover inspector or edit intent, build the
lesson row from that graph-addressed intent instead of retyping the token by
surface:

```bash
python tools/build_production_bug_lesson.py \
  --intent-jsonl <isolated admin-debug output>/all-edit-intents.jsonl \
  --edit-intent-id edit-intent:token-33-63-1 \
  --bug-class verb_object_suffix_omitted \
  --what-failed "The entry/lemma gloss omitted the attached object pronoun." \
  --sarf-lesson "Segment the host and suffix pronoun before choosing a hover." \
  --nahw-lesson "The explicit following subject does not erase the attached object." \
  --learner-explanation "The final kaaf contributes 'you'." \
  --drill-prompt "Mark the prefix, stem, and object pronoun in يَسْأَلُكَ." \
  --level beginner \
  --procedure-link sarf/procedures/clitic-and-host-morphology.md \
  --procedure-link nahw/procedures/pronoun-attachment.md \
  --regression-fixture-link qamus/examples/production_bug_lesson.sample.jsonl \
  --out-jsonl <isolated admin-debug output>/production-bug-lesson.jsonl
```

The builder copies the exact `quran:S:A:W`, `wbw:S:A:W`, `parse:<hash>`,
decision, entry/sense, gate, target address, and scope from the edit intent, then
validates the row. It does not write live Qamus data, rebuild WBW, mutate entry
JSON, or apply a repair.

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
- optional graph provenance from the edit intent: `edit_intent_id`,
  `requested_scope`, `target_address`, `parse_id`, `decision_id`,
  `entry_sense`, `gate`, and `blocker`

Do not use this file to apply live changes. It is a bridge from production evidence back into reusable instruction,
fixtures, and gates.

Each lesson must remain graph-addressed. A lesson that says "the word X was wrong" is not enough; it must identify
the exact rendered hover slot, link to the sarf/nahw/qamus procedure that should prevent recurrence, and point to a
validator or regression fixture. This keeps ANDON reports from becoming chat-only corrections.
