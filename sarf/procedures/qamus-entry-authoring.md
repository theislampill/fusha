# Procedure — author a reviewable Qamus ENTRY candidate

**Invoke when:** sarf evidence on a surface/lemma has resolved far enough to propose a Qamus dictionary entry
(new lemma, or an occurrence-augment of an existing one) — and you need a *review-only candidate*, not a live write.

**Input:** the resolved surface(s) + root ([`root-decision.md`](root-decision.md)), the form/voice or noun role
([`verb-form.md`](verb-form.md), [`noun-plural-gender.md`](noun-plural-gender.md)), the source-address node that
located the lemma ([`../../qamus/schemas/source-address.schema.json`](../../qamus/schemas/source-address.schema.json)),
and the candidate āyāt where the lemma occurs (each with a `surah:ayah` ref).

**Checks (in order — stop at the first that certifies each field):**
1. **headword / translit** — the vocalized display form from the located node, never `norm()`-stripped; translit
   follows the display harakāt (خَلَقَ → *khalaqa*, خُلِقَ → *khuliqa*).
2. **root** — certified by [`root-decision.md`](root-decision.md) (Qamus root > QAC > photographed page); space-separated
   radicals `خ ل ق`. Nouns may key by headword where the root field is `null` (rootless particles always `null`).
3. **pos / category** — from sarf state, not surface shape: maṣdar/participle/plural are nominal, not verbs
   ([`noun-plural-gender.md`](noun-plural-gender.md)); a derived form is its own lemma, never the Form I lemma.
4. **senses[]** — each `gloss` is ORIGINAL English authored from your own knowledge; one sense per distinct meaning,
   `count` only where occurrence evidence supports it. Never paste an external dictionary/textbook line.
5. **usage[]** — group `forms[]` (vocalized inflections of this lemma) under a sense, with `examples[]` carrying
   `ar` (vowelized āyah), `ref` (`^[0-9]{1,3}:[0-9]{1,3}$`), and an authored `en`. Transcribe the āyah against its
   ref — Qurʾān text is verified by the owner, never paraphrased or altered.
6. **total_uses** — the occurrence count for the lemma when corpus-backed; `null` if not certified (never a guess).

**Evidence-ladder rule:** a field is only as strong as its highest certifying rung. `norm()` recalls candidates but
certifies nothing — a headword, root, or count that rests on `norm()` alone stays uncertified and the candidate goes
to review, never live.

**Output object (one JSONL row, `status:"candidate"`, conforming to
[`../../qamus/schemas/qamus-entry.schema.json`](../../qamus/schemas/qamus-entry.schema.json)):**
`source_address` · `headword` · `translit` · `root` · `root_translit` · `category` · `pos` ·
`senses[]{gloss,count,note}` · `usage[]{forms[],gloss,examples[]{ar,ref,en}}` · `total_uses` ·
`status:"candidate"` · `review_status:"needs_human_review"`. Public provenance is exactly
`{src:"qamus",kind:"authored"}` — no QAC/Tanzil/quran.com/OCR/crop/book-scan names leak into the row (they live only
in the sibling `*.provenance.jsonl`).

**Forbidden shortcuts:** writing live (entries are JSON content, applied only through the owner-gated path — emit a
candidate row); copying any external gloss verbatim; a Form I sense on a derived form; a verb gloss on a noun; an
āyah whose `ar` does not match its `ref`; naming an internal source as public authority.

**Example A — verb, new occurrence-augment.**
Surface خَلَقَ, root خ ل ق (Qamus root, rung 1), Form I active, 3ms past.
```json
{"source_address":"qamus:v021#root=خ ل ق","headword":"خَلَقَ","translit":"khalaqa","root":"خ ل ق",
 "root_translit":"kh-l-q","category":"Verbs - Form I","pos":"verb",
 "senses":[{"gloss":"to create, bring into being","count":null}],
 "usage":[{"forms":["خَلَقَ","خُلِقَ"],"gloss":"create / be created",
   "examples":[{"ar":"خَلَقَ ٱلسَّمَٰوَٰتِ وَٱلْأَرْضَ","ref":"6:1","en":"He created the heavens and the earth"},
               {"ar":"وَخُلِقَ ٱلْإِنسَٰنُ ضَعِيفًا","ref":"4:28","en":"and man was created weak"}]}],
 "total_uses":null,"status":"candidate","review_status":"needs_human_review"}
```
The passive خُلِقَ is grouped as a *form*, not re-glossed as Form I — the voice flip ("was created" ≠ "created") is the
sarf evidence carried into `usage`.

**Example B — maṣdar, nominal not verbal.**
Surface ذِكْر, root ذ ك ر — a maṣdar; the gloss is nominal and must not collapse onto the verb.
```json
{"source_address":"qamus:n014#root=ذ ك ر","headword":"ذِكْر","translit":"dhikr","root":"ذ ك ر",
 "root_translit":"dh-k-r","category":"Nouns - Maṣdar","pos":"masdar",
 "senses":[{"gloss":"remembrance; mention","note":"nominal — not \"he remembered\""}],
 "usage":[{"forms":["ذِكْر","ٱلذِّكْرَ"],"gloss":"remembrance / the Reminder",
   "examples":[{"ar":"إِنَّا نَحْنُ نَزَّلْنَا ٱلذِّكْرَ","ref":"15:9","en":"It is We who sent down the Reminder"}]}],
 "total_uses":null,"status":"candidate","review_status":"needs_human_review"}
```

**Test:** entry rows validate against [`../../qamus/schemas/qamus-entry.schema.json`](../../qamus/schemas/qamus-entry.schema.json);
sense/POS/āyah-ref invariants are covered by `tools/check_regressions.py` and the fixtures in
[`../examples/qamus-regressions.jsonl`](../examples/qamus-regressions.jsonl) (POS/verb-vs-noun, ref-format,
provenance-leak assertions).

**Feeds:**
- **/qamus/ entry authoring** — the candidate row is the exact shape an approved entry takes; once owner-reviewed it
  applies as a live JSON entry (content, not git), with `status` advancing candidate → published.
- **hover-gloss resolution** — each `usage[].examples[].ar`+`ref` and the lemma forms become certified evidence the
  hover pipeline reuses ([`hover-application.md`](hover-application.md)), so a glossed token traces back to this entry.
- **ʿajamī learners** — finite, vocalized examples with original English teach the lemma in context (the form, the
  voice, the āyah it lives in), not a bare root list.
