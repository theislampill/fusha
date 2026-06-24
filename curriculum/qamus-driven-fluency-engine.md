# The Qamus-driven fluency engine (cart + engine)

**Architecture principle.** The **Qamus is the cart** — the lexicon/output (entries, senses, hover glosses). The
**sarf + nahw skills are the engine** that pulls it. External sources are **fuel/evidence**, never public output.
The **source-address + state graphs are the transmission** that connects engine to cart without losing power
(every decision is addressed, reused, never duplicated).

```
  fuel (internal evidence)        ENGINE (sarf + nahw)                 CART (Qamus / hover)
  Qamus entry · QAC · source-  →  morphology + syntax decisions   →    entries · senses
  photo · adapters (optional)     + GrammarProblems reasoning gate      hover glosses {src:qamus}
        │                                   │                                  │
        └──────────  TRANSMISSION: source-address graph + language state machine  ──────────┘
```

## What the engine does (not just catch bugs)
1. **Pull the existing Qamus** — resolve hover tokens against entries (the four-gate + token + suffix/pronoun lanes).
2. **Generate new Qamus** — corpus → candidate entries/occurrence-augments (`tools/corpus_to_qamus_candidates.py`).
3. **Author hover glosses** — original, surface-safe, per-token where needed; never copy external text.
4. **Audit grammar** — the GrammarProblems gate: a decision needs the right answer AND the right reasoning.
5. **Teach ajami learners** — `curriculum/` lessons/drills built from live Qamus + hover state.
6. **Know when to stop** — keep a token pending with a precise blocker rather than ship a guess.
7. **Prevent bad public glosses** — homograph/POS/form guards + the no-leak invariant.

## The engine in five worked examples (each a regression fixture)
| input | engine decision | why | fixture |
|---|---|---|---|
| أَعْمَالُنَا | "our deeds" | noun stem أعمال + possessive نا; POS-gate (noun, not verb) | `nahw/evals/suffix-pronoun-eval.jsonl` (SP-001) |
| لَمْ vs لِمَ | "did not" vs "why" | nahw particle state split — same `norm_strict` key, distinct vocalized surface → per-token | `token_hover_decisions_batch_001` |
| مِن vs مَن | "from" vs "who/whoever" | preposition vs relative/interrogative — harakat split | `token_hover_decisions_batch_001` |
| كَظِيم | "(one) suppressing grief" (ṣifa) | ism, NOT the infinitive verb "to suppress" | `sarf/evals/qamus-regression-eval.json` |
| نَزَّلَ vs نَزَلَ | form II "sent down" vs I "descended" | form/voice split — shadda distinguishes; key نزل collides | `sarf/rules/surface-state-transition-rules.json` |

## Learner path (cart pulled by engine)
A learner picks a root → reads the Qamus entry → studies the forms (sarf) → reads example āyāt with hover (engine
resolves each token) → drills (generated from the entry + hover state) → errors map back to the exact sarf/nahw
procedure. `curriculum/zero-to-fluency-roadmap.md` sequences this from script to independent Fusha reading.

The engine is MCP-free and portable: install it (`INSTALL.md`) and point it at any Qamus or corpus.

## Live polysemy worked examples (2026-06-24b, each a per-loc iʿrāb decision)
These joined the engine's regression set from the B3 token-iʿrāb + B2 host-lexeme batches:
- **وَمَا** — negation "and not" (3:7) vs relative "and whatever" (30:39): the clause decides (nahw).
- **أَلَّا** = أَنْ+لَا "that … not" (4:3) vs **ألَا** istiftāḥ "indeed" (39:3) — same norm key, distinct particles.
- **عَادٍ** = ism fāʿil "transgressor" from عدا (2:173), **not** the tribe ʿĀd; **عَادَ** "returned" (36:39).
- **جِنَّة** = "a garden" (2:266) vs "madness" (7:184).
- **ذَهَب** "gold" (noun) vs went (verb); **أَذِنَ** "permitted" vs **أُذُن** "an ear"; **يَحْيَىٰ** "Yaḥyā (John)" (proper noun) vs "gives life".
- **host-lexeme possessives** authored from the root when the noun has no entry: سَيِّئَاتِهِمْ "their evil deeds",
  ءَالِهَتَكُمْ "your gods", قِبْلَتِهِمْ "their prayer direction" — broken plural shares the root, POS-gated.
