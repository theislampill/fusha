# Qamus certification policy (certified-lemma gated fanout)

**Status:** adopted 2026-07-04. Machine-enforced by `qamus/schemas/certified-lemma.schema.json` +
`tools/validate_certified_lemma_fanout.py` (self-test + fixtures wired into `tools/check_regressions.py`).
This doc is the human statement of the policy those files enforce.

## 0. Two distinct certification layers — do not conflate
- **Token-level two-vote certification** — per-occurrence hover-decision rows (`decision_state:
  bulk_two_vote_certified`, keyed by `loc`, carrying a `gloss`). **Well-populated** (thousands of rows
  across `qamus/candidates/qamus_2092/bulk_twovote_certified_batch_*.jsonl`). Certifies *this
  occurrence's* gloss; it does **not** authorize reuse elsewhere.
- **Certified-lemma fanout** (this policy) — `qamus.certified_lemma.v1` rows that authorize a solved
  sarf/nahw fact to **fan out** (be reused) across occurrences via a typed gate. **Near-zero real
  coverage today** (only illustrative sample + reject fixtures). When a claim says "certified coverage
  is zero," it means *this* layer, not the token layer.

Fanout is a **lattice projection from certified source facts, never a surface-string replacement.**

## 1. The three fanout gates (orthogonal; there is deliberately no surface-only gate)

| Gate | For | Requires | Review |
|---|---|---|---|
| **`source_address_exact`** | any POS incl. particles | same exact `quran:S:A:W` / `wbw:S:A:W`; validated payload; no semantic fanout | mechanical gates + owner/operator (no two-vote required) |
| **`lemma_pattern_pos`** | **content words only** — noun, verb, adjective, participle | stable lemma/root/base/form/POS/pattern | **two-vote** (`review_votes >= 2`) where grammar can affect reuse |
| **`function_context`** | particles, pronouns, relatives, interrogatives, negation, conditionals, prepositions | function + context agreement | **two-vote** OR owner/scholar review |

**Particles/function words may NEVER fan out via `lemma_pattern_pos`** — only `source_address_exact`
or `function_context`. (Enforced: `pos=="particle"` guard + the `lemma_pattern_pos` content-POS
allow-list.)

## 2. Forbidden (each is a validator FAIL, not a guideline)
- **surface-only certification** — impossible by construction (no surface-only gate value; legacy
  `never_surface_only` fails the closed enum).
- **particle fanout through `lemma_pattern_pos`**.
- **component-only evidence certifying a whole token** — `evidence_scope=component` + `fanout_allowed`
  is rejected (case h).
- **fanout when sarf/nahw reasoning disagrees** — `reason_agreement=disagree` + `fanout_allowed` is
  rejected; **block and classify the blocker** (case g).
- **right English gloss with wrong Arabic grammar reason** — this lives in the rich-hover
  certification substrate (a `preview_only`/`pending` row must never be promoted by English
  readability alone); do not certify-fanout a lemma whose grammatical reason is unverified.
- **public-source / provenance leakage** — public fields (`lemma_ar, root, pos, pattern, fanout_gate`)
  are `FORBIDDEN_LABELS`-clean; QAC/MCP/Quran.com/tafsir/OCR/`/srv/`/`C:\` labels live only in
  `evidence_private` and are stripped before any public artifact. `fanout_allowed` requires
  `public_safe=true`.

## 3. Why particles need function_context, not lemma_pattern_pos (internal evidence)
Deep-research triangulation (Qur'an MCP; internal only, never surfaced in public hover):
- **مِن / مَن** (skeleton من, both in 2:8): preposition ("of/among") vs relative pronoun ("who") —
  defeats surface/skeleton fanout.
- **إِنْ / إِنَّ** (skeleton ان): conditional-jussive particle (2:23) vs emphatic-accusative particle
  (2:6) — different operators under one skeleton.
- **عَلَىٰ** (the decisive case): same lemma/pattern/POS, yet "upon (guidance)" (2:5, حال) vs "against"
  (2:286) — the gloss flips by **context**, so `lemma_pattern_pos` is insufficient for a function word.

No source disagreed. This is a linguistic-safety argument, not a claim about any public string.

## 4. Content-addressed identity (homograph safety)
`lemma_id = "lemma:" + sha256(canonical(lemma_ar, root, pos, pattern))[:16]`. Two distinct-meaning
homographs (مِن vs مَن) get **different** ids by construction and cannot collide on one identity; the
batch guard rejects any `lemma_id` mapping to two `(lemma_ar,pos,root,pattern)` signatures.

## 5. What becomes eligible under this policy (no real rows written yet)
Once reviewers produce evidence, the eligible classes are:
- **`source_address_exact`** — immediately eligible for any well-formed, validated, source-clean row at
  an exact loc (incl. particles). This is the L15/L49 transclusion canary path (still owner-gated to
  deploy).
- **`lemma_pattern_pos`** — content-word lemmas (noun/verb/adjective/participle) with a stable
  lemma/root/POS/pattern **after two-vote review**.
- **`function_context`** — particle/pronoun/relative/interrogative/negation/conditional/preposition
  lemmas **after two-vote or owner/scholar review**, gated on function+context agreement.
Not eligible: any particle via `lemma_pattern_pos`; any row with component-only evidence; any row where
sarf and nahw disagree; any surface-only claim.

**No production certified-lemma rows are written by adopting this policy** — it defines the gate that
future certified rows must pass. Writing real `certified` rows remains owner decision #1
(certification authority).
