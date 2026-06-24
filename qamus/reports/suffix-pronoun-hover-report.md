# Suffix/pronoun hover resolution (the أَعْمَالُنَا class)

Fixes the visible failure class on the live site: tokens shown as "stem recognized — suffix/pronoun pending" when
they are a **noun stem + a possessive enclitic** that the Qamus stem + the vocalized suffix fully determine.

## The fix (general, not a per-token patch)
[`tools/build_suffix_pronoun_decisions.py`](../../tools/build_suffix_pronoun_decisions.py): split the enclitic from
the vocalized surface → POS-gate (noun host only) → compose **possessor + stem-base-gloss** → emit a
`suffix_pronoun_decision` per `quran:S:A:W` (applied through the token layer). The stem base is learned from
already-resolved sibling forms (أعمالهم "their deeds" → base "deeds") + a curated noun seed.

## Live result
- **182 suffix/pronoun decisions applied** (your 68, their 54, his 21, our 19, her 16, dual 4). Coverage
  **81.41% → 81.77%** (+182 occ, **−0 removed**), validate PASS, health 200.
- **The reported failure is fixed:** أَعْمَالُنَا @ 2:139:2 and 42:15:23 → **"our deeds"** (was pending);
  أَعْمَالُكُمْ → "your deeds". Screenshot: `b10a1ee04666` renders "Our deeds are for us, and your deeds are for you".

## POS gate (the noun-vs-verb-suffix trap, caught and fixed)
A first pass wrongly produced عَلِمْنَا → "our knowledge". عَلِمْنَا is a **verb** — نا is the subject ("we knew"),
not a possessive. The generator now **excludes verb hosts** (QAC POS=V): **1,050 verb-suffix tokens correctly
skipped**, 888 stayed `stem_base_unknown` (need stem authoring — next tier). 0 verb tokens in the applied batch.

## Blockers (precise, not vague)
| blocker | n | meaning / next action |
|---|---:|---|
| `verb_suffix_not_possessive` | 1,050 | verb host — enclitic is subject/object; handled by the verb lane, not here |
| `stem_base_unknown` | 888 | noun stem whose base gloss isn't yet known → author the stem (B7 noun sweep) |

## Acceptance
≥100 suffix/pronoun pending resolved (**182**) ✓; أعمالنا/أعمالكم correct live ✓; regression covers
1st/2nd/3rd-person, sg/pl, noun-vs-verb-suffix, and the tanwīn-alef false-positive
([`nahw/evals/suffix-pronoun-eval.jsonl`](../../nahw/evals/suffix-pronoun-eval.jsonl)) ✓; rebuild PASS, health 200,
0 leaks ✓. Schema: `suffix-pronoun-decision.schema.json`. Rules: `sarf/rules/suffix-pronoun-rules.json` +
`nahw/rules/pronoun-attachment-rules.json`. Procedures: `sarf/procedures/suffix-pronoun-state.md` +
`nahw/procedures/pronoun-attachment.md`. Mirror: `suffix_pronoun_hover_batch_001.*`. Rollback: `*.bak-suffix2`.
