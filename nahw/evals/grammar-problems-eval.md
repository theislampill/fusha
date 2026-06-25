# GrammarProblems — derived eval (the runnable companion)

`grammar-problems-derived-eval.jsonl` is the **executable** half of the GrammarProblems gate. Where
[`grammar-problems-matrix.json`](grammar-problems-matrix.json) encodes the *structure* of the study and
[`grammar-problems-summary.md`](grammar-problems-summary.md) records what the finding *became*, this dataset is
**80 original, isomorphic naḥw cases** an agent (or a candidate model) must answer — with the right conclusion
**and** the right reasoning — before any grammar-affecting decision is trusted to ship.

> Every case is authored from first principles to mirror the study's *shape*, never its text. No exam item,
> textbook sentence, or external answer key is copied. Arabic examples are vowelized and self-contained; the
> public hover artifact still emits only `{src:"qamus", kind:"authored", "lang":"en"}`.

Run it with [`tools/run_grammar_evals.py`](../../tools/run_grammar_evals.py), which reads the JSONL, scores each
answer, and — critically — scores the **reasoning** against the sarf/nahw ladders, then asserts the gate.

---

## Why a reasoning-graded eval (not an answer key)

The GrammarProblems study put a free general LLM at **~33.33%** on 72 Arabic-naḥw questions, collapsing on
iʿrāb / advanced / deep / essay / higher-Bloom items. The engineering reading is blunt: **a correct-looking
final answer with wrong iʿrāb reasoning is unsafe and must not ship.** So this eval does not stop at "is the
case right?" — it grades the *path*. A case **passes only when ALL of the following hold**:

1. **Final answer** — the conclusion (case/mood/role/transformation) matches `expected_answer`.
2. **Reasoning** — the stated *why* (the governing particle, the case/mood, the wazn, the referent, the
   iḍāfa/definiteness) matches the substance of `expected_reasoning`. A right answer for a wrong reason **fails**.
3. **Evidence ladder** — the reasoning rests on the sarf ladder (root/POS/form via `norm_strict` + QAC, never
   bare `norm()`) and the nahw ladder (the governor, the iʿrāb, the referent), not on "the model is confident."
4. **Source-address** — any candidate that would touch a live hover gloss carries its source-address; external
   corpora are `informed_by` evidence only, never quoted as authority.
5. **Two-vote (when required)** — for every case whose `required_gate` is `two_vote_required`, two independent
   checks must **agree on the conclusion AND the reasoning**. Disagreement → pending, never a coin-flip ship.

If any one of the five fails, the case is **not** a pass — mirroring the production rule that a single weak link
(a guessed reason, a `norm`-only match, a missing second vote on an iʿrāb call) blocks the whole decision.

---

## The dimensions (and what each one stresses)

| dimension | values | what it probes |
|---|---|---|
| **level** | `ajurrumiyyah` (beginner, al-Ājurrūmiyyah) · `qatr_al_nada` (intermediate, Qaṭr al-Nadā) · `awdah_al_masalik` (advanced, Awḍaḥ al-Masālik) | curriculum depth; the study's accuracy fell sharply from beginner → advanced |
| **bloom** | `recall` · `understanding` · `application` · `analysis` · `evaluation` · `generation` | cognitive load; the model collapsed at `analysis` and above |
| **format** | `objective` · `essay` | objective = a single parse/sign; essay = a justified iʿrāb/contrast where reasoning is the whole point |
| **depth** | `direct` · `deep` | direct = the rule applies on the surface; deep = an exception, a competing analysis, or a transformation must be reasoned through |

`hover_safety` (`auto_safe` · `two_vote_required` · `never_auto`) and `required_gate` route each case to a tier of
[`grammar-decision-gates.json`](grammar-decision-gates.json). The mapping is deliberate:

- **`auto_safe`** — only beginner, direct, objective, low-Bloom items on non-reasoning-dependent topics (a sound
  raf‘ sign, a plain iḍāfa, a jār-majrūr by referent). These are the *only* cases a pipeline may auto-author.
- **`two_vote_required`** — anything deep / essay / `analysis`+ / advanced, or on a reasoning-dependent topic
  (iʿrāb assignment, case/mood, the two-object verbs, transformations). Two agreeing votes on answer + reason.
- **`never_auto`** — the construction-sensitive landmines where a right answer with the wrong structure is most
  likely: لا النافية للجنس, istithnāʾ case, tanāzu‘, ikhtiṣāṣ, prohibitive-vs-negating لا, diptote re-enabling.
  These are surfaced for human/source review and **never** ship from model confidence alone.

---

## Coverage — topic × level (80 cases)

Each topic is exercised across the curriculum band where its difficulty actually lives (e.g. tanāzu‘ and
ikhtiṣāṣ are advanced-only; the iʿrāb signs and the nominal sentence start at the beginner level). A `—` means
the topic is not posed at that level by design, not an omission.

| topic | ajurrūmiyyah | qaṭr al-nadā | awḍaḥ al-masālik | total |
|---|:--:|:--:|:--:|:--:|
| building of the present verb | 3 | 1 | — | 4 |
| signs of iʿrāb | 6 | 1 | — | 7 |
| mubtadaʾ / khabar | 2 | 1 | 1 | 4 |
| kāna and its sisters | — | 4 | — | 4 |
| ẓanna and its sisters | — | 2 | 1 | 3 |
| mafʿūl li-ajlih | — | 3 | — | 3 |
| mafʿūl muṭlaq | — | 2 | 2 | 4 |
| lā nāfiyah lil-jins | — | 1 | 2 | 3 |
| istithnāʾ (exception) | — | 2 | 3 | 5 |
| passive / agent transformation | — | 1 | 2 | 3 |
| mamnūʿ min al-ṣarf (diptote) | — | 2 | 2 | 4 |
| ḥāl | — | 2 | 3 | 5 |
| badal | — | 3 | 1 | 4 |
| tamyīz | — | 1 | 3 | 4 |
| iḍāfa | 2 | 2 | 1 | 5 |
| jār-majrūr | 2 | 2 | — | 4 |
| tanāzuʿ | — | — | 3 | 3 |
| ism fāʿil / ism mafʿūl operation | — | 2 | 1 | 3 |
| niʿma / biʾsa | — | 2 | 1 | 3 |
| ikhtiṣāṣ | — | — | 2 | 2 |
| negation & mood (لم/لن/لا scope) | — | 2 | 1 | 3 |
| **total** | **15** | **36** | **29** | **80** |

Secondary spread (each case carries all four dimensions): Bloom — recall 15, understanding 13, application 17,
analysis 22, evaluation 9, generation 4; format — objective 45, essay 35; depth — direct 43, deep 37; gate —
`auto_safe` 13, `two_vote_required` 67 (of which the `never_auto` landmines are flagged in `hover_safety`).
The mass deliberately sits in the intermediate/advanced, deep, analysis+ band — exactly where the study showed
a general LLM is least reliable, so the eval pressure-tests the dangerous region, not the easy one.

---

## The failure modes the deep cases catch

These are the "right answer, wrong reason → wrong generalization" traps the eval is built to fail (see also the
drill [`drills/grammar-reasoning-safety.md`](../drills/grammar-reasoning-safety.md)):

| case shape | naive answer | what the reasoning must catch |
|---|---|---|
| `لَمْ يَكْتُبْ` time | "present → does not write" | `لَمْ` + jussive flips time → **past** "did not write" |
| `حَضَرَ ... إِلَّا خَالِدًا` | "exception, so badal" | positive complete istithnāʾ → **naṣb obligatory**, not badal |
| `مَا نَجَحَ إِلَّا مُجْتَهِدٌ` | "manṣūb mustathnā" | negative + omitted minhu (mufarragh) → case by **position** (fā‘il marfū‘) |
| `قَالَ` → passive | "*قُولَ* by ḍamma" | hollow verb iʿlāl → **قِيلَ** (kasra + medial yā’) |
| `بِأَحْمَدَ` | "kasratayn like any noun" | diptote → jarr by **fatḥa**, no tanwīn |
| `لَا طَالِبَ مُهْمِلٌ` | "manṣūb by fatḥa" | lā lil-jins → ism is **mabnī ʿalā al-fatḥ fī maḥall naṣb** |
| `قَامَ وَقَعَدَ زَيْدٌ` | "one verb, one subject" | tanāzu‘ → second verb operates; first takes a **hidden** pronoun |
| `لَا تَيْأَسُوا` vs `لَا يَيْأَسُونَ` | "لا = not, both same" | prohibitive (jazm, نون deleted) vs negating (raf‘, نون kept) |

Each passes a "does the answer look plausible?" glance and still mis-assigns case, mood, or structure — which is
precisely why the gate is the **reasoning**, not the surface.

---

## How `tools/run_grammar_evals.py` scores

```
for each case in grammar-problems-derived-eval.jsonl:
    answer_ok   = matches(candidate.answer,    expected_answer)
    reason_ok   = matches(candidate.reasoning, expected_reasoning)   # substance, not wording
    ladder_ok   = reasoning rests on sarf(norm_strict+QAC) / nahw(governor·case·referent), not norm/OCR/confidence
    address_ok  = candidate carries source_address (informed_by only; no copied gloss)
    votes_ok    = (required_gate != two_vote_required) or two_independent_checks_agree(answer AND reasoning)
    PASS  iff  answer_ok AND reason_ok AND ladder_ok AND address_ok AND votes_ok
    else  →  PENDING with the precise failing link (prefer pending over a wrong gloss)
```

The runner reports accuracy sliced by every dimension (level / Bloom / format / depth / topic / gate) so a
regression that *only* shows up on deep-essay-advanced items — the study's collapse zone — is visible immediately
rather than hidden behind a healthy beginner average. The same five-link contract is enforced on real decision
objects by `tools/validate_linguistic_decisions.py`, and the GrammarProblems gate assertions ride
`tools/check_regressions.py` — so this eval and production share one rule:

> **General LLM confidence is not evidence. A correct conclusion with wrong iʿrāb reasoning is unsafe.
> Prefer a precise pending over a confident wrong answer — every link in the ladder must hold.**

## Hard rules honored here

- No exam/textbook item, answer key, or external gloss text is copied; all 80 cases are original and isomorphic.
- External corpora (QAC, Tanzil, etc.) are `informed_by` evidence only — never surfaced as public authority.
- Qurʾān text is never altered; where an āyah-shaped pattern is referenced it is evidence, not a public claim.
- Arabic examples are vowelized; the public artifact emits only `{src:"qamus", kind:"authored", "lang":"en"}`.
- **PENDING beats a wrong gloss, always** — a failed link is a pending with a reason, not a ship.
