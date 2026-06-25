# Procedure — corpus → Qamus (the sarf half of the pipeline)

**Invoke when:** sweeping a corpus span (an āyah window, a sūrah, a lemma family) to discover what Qamus is missing
and emit entry candidates — never to write live.

**Input:** the corpus span (vocalized tokens, each with a `surah:ayah:word` position), the live Qamus index
([`../../qamus/indexes/`](../../qamus/indexes/)), optional QAC root/POS per token (internal evidence only).

**Checks (in order — stop at the first that certifies the token's disposition):**
1. **Tokenize + source-address** — mint/reuse one node per `quran:S:A:W`
   ([`../../qamus/schemas/source-address.schema.json`](../../qamus/schemas/source-address.schema.json)); reuse an
   existing `qamus:v###/n###/p###` before minting a new one (the schema's duplicate-avoidance rule).
2. **Sarf state** — resolve root ([`root-decision.md`](root-decision.md)), then form/voice
   ([`verb-form.md`](verb-form.md)) or noun role ([`noun-plural-gender.md`](noun-plural-gender.md)). This yields the
   `(lemma, root, pos, form)` tuple the classifier keys on. `norm()` recalls; it never certifies the tuple.
3. **Classify** the certified tuple against the index — stop at the first that matches:
   - **already-in-Qamus** — lemma + this surface already covered → no candidate (optionally bump `used_by`).
   - **occurrence-augment** — lemma present, this āyah occurrence not yet attached → candidate adds a `usage[].examples` row.
   - **new-surface-existing-lemma** — a new inflected form of a known lemma → candidate adds to `usage[].forms`.
   - **new-lemma-existing-root** — root present, this lemma absent (a derived measure or a new noun on the root) → new entry candidate, root reused.
   - **new-root** — root absent from Qamus → new entry candidate, root minted (certified, never `norm()`-derived).
4. **Author** the candidate per [`qamus-entry-authoring.md`](qamus-entry-authoring.md) and emit it.

**Evidence-ladder rule:** the classifier acts only on the *certified* tuple. A homograph collision (same `norm_strict`
key, different lemma/POS/voice — see [`homograph-risk.md`](homograph-risk.md)) must split into distinct nodes, never
merge into one entry; a tuple resting on `norm()` alone is routed to review, never auto-classified as "already-in".

**Output object (one JSONL candidate row per disposition; conforms to
[`../../qamus/schemas/qamus-entry.schema.json`](../../qamus/schemas/qamus-entry.schema.json)):**
`source_address` · `lemma_candidate` · `root` · `pos` · `disposition` (the class above) · the entry fields
authored per [`qamus-entry-authoring.md`](qamus-entry-authoring.md) (`headword`/`translit`/`senses[]`/`usage[]`) ·
`status:"candidate"` · `review_status:"needs_human_review"`. Public provenance stays exactly
`{src:"qamus",kind:"authored",lang:"en"}`; internal evidence (QAC/Tanzil/quran.com/OCR/crop) goes only to the sibling
`*.provenance.jsonl`, never the candidate row.

**Forbidden shortcuts:** writing live (emit candidates, owner-gated apply only); classifying on `norm()` instead of
the certified tuple; merging a homograph collision into one entry; minting a duplicate node for an existing
`quran:S:A:W`; surfacing an internal source as public authority; altering Qurʾān text in any āyah.

**Example A — new-lemma-existing-root.**
Span carries أَنزَلَ at `quran:2:23:6`. Root ن ز ل is already in Qamus via نَزَلَ (Form I); أَنزَلَ is Form IV
("to send down") — a *different lemma on the same root*.
```json
{"source_address":"quran:2:23:6","lemma_candidate":"أَنزَلَ","root":"ن ز ل","pos":"verb",
 "disposition":"new-lemma-existing-root",
 "headword":"أَنزَلَ","translit":"anzala","category":"Verbs - Form IV",
 "senses":[{"gloss":"to send down, reveal","note":"Form IV — not the Form I نَزَلَ \"to descend\""}],
 "usage":[{"forms":["أَنزَلَ","أَنزَلْنَا"],"gloss":"send down / We sent down",
   "examples":[{"ar":"وَإِن كُنتُمْ فِى رَيْبٍ مِّمَّا نَزَّلْنَا","ref":"2:23","en":"And if you are in doubt about what We have sent down"}]}],
 "status":"candidate","review_status":"needs_human_review"}
```

**Example B — occurrence-augment vs homograph guard.**
Span carries قُتِلَ at `quran:3:195`. Lemma قَتَلَ is already in Qamus, but قُتِلَ is the *passive*; the `norm_strict`
key قتل collides with active قَتَلَ. The voice difference forbids merging — emit an augment that keeps the passive as
its own form/sense, not a silent "already-in":
```json
{"source_address":"quran:3:195","lemma_candidate":"قَتَلَ","root":"ق ت ل","pos":"verb",
 "disposition":"occurrence-augment",
 "usage":[{"forms":["قُتِلَ","قُتِلُوا"],"gloss":"was killed / were killed",
   "examples":[{"ar":"وَقُٰتَلُوا وَقُتِلُوا","ref":"3:195","en":"and fought and were killed"}]}],
 "status":"candidate","review_status":"needs_human_review"}
```

**Test:** the classifier + row shape are exercised by `tools/corpus_to_qamus_candidates.py` against
`tools/check_regressions.py` (root/norm_strict invariants, homograph-collision split) and the fixtures in
[`../examples/qamus-regressions.jsonl`](../examples/qamus-regressions.jsonl) and
[`../examples/root-form-decisions.jsonl`](../examples/root-form-decisions.jsonl); rows validate against
[`../../qamus/schemas/qamus-entry.schema.json`](../../qamus/schemas/qamus-entry.schema.json).

**Feeds:**
- **/qamus/ entry authoring** — every `new-*` disposition is a ready entry candidate, and every augment is a
  reviewable patch to an existing entry's `usage[]`, landing in [`../../qamus/candidates/`](../../qamus/candidates/).
- **hover-gloss resolution** — the certified `(lemma, root, pos, form)` tuples plus their āyah occurrences become the
  evidence the hover pipeline keys on ([`hover-application.md`](hover-application.md)), so corpus coverage and hover
  coverage grow from the same sweep.
- **ʿajamī learners** — the sweep turns raw scripture into addressable, glossed lemmas in context, so a learner
  meeting a word in an āyah reaches its Qamus entry, its form, and an authored English sense.
