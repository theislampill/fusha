# Procedure — suffix/pronoun state (noun stem + enclitic possessive)

**Invoke when:** a token is a recognized **noun stem + an attached enclitic pronoun** and the renderer left it
"stem recognized — suffix/pronoun pending" (e.g. أَعْمَالُنَا, قُلُوبِهِمْ, رَبِّنَا). The goal: resolve it to
**possessor + base** (our deeds / their hearts / our Lord), not leave it pending.

**Input:** the vocalized token + its `quran:S:A:W`, its QAC POS, and the stem's base gloss (from a resolved
sibling form, the bare stem, or a curated noun base).

**Checks (in order):**
1. **Split the enclitic from the VOCALIZED surface** (not `norm()`): نا→our, كم→your(pl), هم/هِم→their, ه/هُ/هِ→his,
   ها→her, ي→my, ك→your, كما/هما→dual. A final tanwīn-alef (قُرْءَانًا) is **not** the نا pronoun
   (`ends_tanwin_alef`).
2. **POS gate (load-bearing):** the host must be a **noun** (QAC POS N/ADJ/PN). On a **verb**, the enclitic is a
   subject/object pronoun — عَلِمْنَا = "we knew" (نا = فاعل), NOT "our knowledge"; خَلَقْنَا = "We created", not
   "our creation". If POS=V → this procedure does not apply (see [`verb-form.md`](verb-form.md)).
3. **Resolve the stem base gloss:** reuse a resolved sibling (أعمالهم "their deeds" → base "deeds"), or the bare
   stem, or a curated noun base. If unknown → pending (`stem_base_unknown`), do not guess.

**Output:** a token-addressed decision (`suffix_pronoun_decision`) for the loc: `[and/so ]possessor base`. Conforms
to [`qamus/schemas/suffix-pronoun-decision.schema.json`](../../qamus/schemas/suffix-pronoun-decision.schema.json);
applied via the token layer ([`../../qamus/reports/token-addressed-hover-layer.md`](../../qamus/reports/token-addressed-hover-layer.md)).

**Forbidden:** possessive gloss on a verb host; overwriting a proper noun/idiom; turning every enclitic into
"his/their" regardless of the actual pronoun; guessing the base gloss when the stem is unknown.

**Test:** [`nahw/evals/suffix-pronoun-eval.jsonl`](../../nahw/evals/suffix-pronoun-eval.jsonl) (أعمالنا resolves;
عَلِمْنَا verb stays pending; قُرْءَانًا not-a-suffix). Generator
[`tools/build_suffix_pronoun_decisions.py`](../../tools/build_suffix_pronoun_decisions.py) (POS-gated);
validator [`tools/validate_suffix_pronoun_decisions.py`](../../tools/validate_suffix_pronoun_decisions.py).

**Feeds:** /qamus/ entry usage notes (possessed forms) · hover-gloss resolution (the suffix/pronoun class) ·
ajami learners (how إضافة of a pronoun renders in English). Pairs with [`nahw/procedures/pronoun-attachment.md`](../../nahw/procedures/pronoun-attachment.md).
