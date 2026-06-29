# RH-LIVE source-only Qur'an annotation token lesson

Date: 2026-06-29

## Trigger

During RH-LIVE public readback, a Qur'an usage card exposed a source-boundary bug class:
located Qur'an words were rendered from canonical word-addressed data, but source-only
pause or annotation glyphs from an entry/example string could fall through as inert
plain spans.

This is unsafe for two reasons:

- it makes a non-addressable annotation mark look like a displayed word in the usage card;
- it lets source/example text become public Qur'an display authority after alignment has
  already found the canonical word sequence.

## Durable Rule

When `quran:S:A:W` / `wbw:S:A:W` canonical word data exists for a usage card, every public
Arabic word-like span must be one of:

- a located canonical Qur'an word;
- a located pending word with an explicit pending reason;
- an honestly blocked source/example card that is not silently counted as complete.

Source-only pause marks, sajdah/rub markers, separators, or OCR/source-card annotation glyphs
must not become standalone public hover words. They may remain internal evidence for source
alignment, but they are not selected example-word rows and cannot carry Qamus rich-hover
certification.

## Regression Seed

Use fragments like:

```text
مِنكُم مَّن يُرِيدُ ٱلدُّنْيَا ۖ ۞
```

Expected renderer behavior when canonical WBW words are available:

- render the four addressed words once each;
- render no standalone plain span for `ۖ`;
- render no standalone plain span for `۞`;
- keep the canonical word spelling from the addressed Qur'an/WBW source;
- keep source-photo/card text as corpus evidence, not public scripture display authority.

## Flywheel Impact

- Sarf: no new morphology rule; this is a renderer/source-boundary guard, not a word-form
  classification issue.
- Nahw: no new syntax rule; the lesson is that non-addressable annotation marks cannot
  participate in i'rab, governance, or phrase attachment.
- Curriculum: source-boundary examples should distinguish Qur'an words from visual or
  source-card marks before asking learners to reason about grammar.
- Assessment: add a future checker item for "do not count non-addressable marks as tokens"
  in hover/readback audits.
- Renderer requirements: public usage cards must drop or separately handle unlocated
  annotation marks once canonical verse words are available.
- Future tranche routing: any card with source text that includes pause marks or non-word
  glyphs needs a canonical-word readback check before being marked fully live.

## No-Op Boundaries

No live Qamus mutation is authorized by this Fusha report. No WBW rebuild, hover ledger
change, service restart, or public rollout is encoded here. The live app must implement and
verify this through its own owner-gated deployment lane.
