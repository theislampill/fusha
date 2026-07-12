# QAMUS-RICH-NORM-001 — Rich-hover normative-defect trace (v024 ح ق ق ANDON + corpus scan)

**Lane:** QAMUS-RICH-NORM (owner ANDON, P1). **Mode:** READ-ONLY on the whitelist (Wave-1 deploy mid-flight; worked from a pinned snapshot).
**Date:** 2026-07-12. **Author:** rich-norm trace agent.

## Provenance / inputs (pinned)

- **Whitelist snapshot:** `/tmp/rhwl_snapshot.jsonl` copied from live
  `/srv/dawah-ops/hermes-workspace/qamus-app/qamus_wbw/rh_live_01_beta_whitelist.jsonl` at task start.
  - `sha256 = 1c06d85a28cb4c2733c1aeb394b15e200e2b483d62b0a740f5cd20d466c0903c`, **34,322 rows**. All analysis below is over this snapshot only.
- **Detector (authoritative classifier):** `tools/validate_segment_completeness.py`, entrypoint `classify_live_row`, classes **C1–C5**, at fusha **origin/main commit `df89d8c8`** (rich-seg detector **v3**). Local fusha checkout HEAD `e87bd62` is a *divergent* lineage that does NOT contain df89d8c — file was extracted from the commit directly.
- **Debt ledger:** `qamus/reports/rich-seg-known-debt.jsonl` (**1,452 rows**, `debt_ceiling=1452`, was 1,395 pre-v3), `rich-seg-audit@2.jsonl` (**1,403 rows**), both on fusha origin/main. `rich-seg-known-debt.meta.json` pins `classifier_semantics_commit=df89d8c8`.
- **Entry data:** `/srv/dawah-ops/hermes-workspace/qamus-service/entries/*.json` (2,092 entries). Root/form map built from `headword` + `senses[].ar` + **`usage[].forms`** (all `/`-split).
- **MCP `analyze_word`** used for per-row ground truth (sarf + iʿrāb).

**Detector-consistency contract confirmed:** my corpus scan of `classify_live_row` over the snapshot reproduces the v3 ledger counts (C1 254 / C2 175 / C3 9 / C4 528 / C5 512; 1,452 rows flagged = the ceiling). Minor C2/C3/C4 drift (175 vs 178 / 9 vs 14 / 528 vs 529) is the expected live-whitelist mutation since the commit's own scan — direction and magnitude confirm the same detector.

---

## Headline numbers

| Metric | Count |
|---|---|
| Snapshot rows | 34,322 |
| Total rootless rows (no root field AND morphline asserts none) | **22,344** |
| Detector-flagged (C1–C5 = the debt ceiling) | 1,452 |
| **7 of the 8 traced rows escape ALL of C1–C5** (only 7:54:23 fires C2) | 7 / 8 |
| **F1** proclitic + rootless-remainder | **509** (141 remainder is a real dictionary form; 495 escape all detectors) |
| **F2** field-language violation (strict def) | **2,260** (Arabic-prose 2,235 · named meta-marker 33; 2,193 escape all detectors) |
| F2 adjacent notation-leak "Visible pieces:" learner template | 3,697 rows |
| F2 adjacent morphline pseudo-explanation ("no public root asserted"/"function only no root") | 1,065 rows |
| **F3-tier0** rootless surface == entry HEADWORD/sense/usage form | **4,542** (headword 2,606 · content-confident bare≥4 = 1,560; 4,481 escape all detectors) |
| F3-internal (extra: sibling whitelist row asserts the root) | +3,082 |

**Root cause (one line):** the v3 classifier's C1–C5 gates fire on *specific segment shapes* (verb-stem clitic swallow, **single**-segment derived whole-token, misfiled function segment, prose fallback phrases, enclitic-pronoun swallow). None of them assert the invariant **"a content word must carry its public root"**, and none inspect **field language**. So a rootless word that is *correctly or plausibly segmented*, or that carries raw-Arabic / internal-meta prose in learner fields, is invisible to the detector and never enters the debt ledger.

---

## The 8 rows — trace table

`classify` = `classify_live_row` v3 output on the snapshot row. Debt/audit@2 = membership in the ledgers.

| # | loc (disp) | surface | classify v3 | root field | MCP ground truth | family | in debt? |
|---|---|---|---|---|---|---|---|
| 1 | 38:14:6 | فَحَقَّ | **∅ (escapes)** | null | ح ق ق · Form I perfect 3ms (geminate, أصله حَقَقَ) | **F1** | no |
| 2 | 39:71:31 | كَلِمَةُ | **∅** | *absent* | ك ل م · noun f.sg, وزن فَعِلَة, فاعل/مضاف | **F2**(arabic) + F3-t0 | no |
| 3 | 36:70:1 (canon 36:70:5) | وَيَحِقَّ | **∅** | null | ح ق ق · Form I **imperfect** subjunctive (يَ prefix), أصله يَحْقِقُ | **F1** | no |
| 4 | 7:105:1 | حَقِيقٌ | **∅** | *absent* | ح ق ق · صفة مشبهة, وزن فَعِيل | **F2**(meta) + F3-t0 | no |
| 5 | 36:70:4 (canon 36:70:8) | الْكَافِرِينَ | **∅** | *absent* | ك ف ر · اسم فاعل, جمع مذكر سالم, وزن فاعل | **F2**(meta+arab) + F3-t0 | no |
| 6 | 16:3:1 | خَلَقَ | **∅** | null | خ ل ق · Form I perfect 3ms (باب نصر) | **F3-tier0** (HEADWORD) | no |
| 7 | 7:54:23 | مُسَخَّرَٰتٍ | **C2** ✓ | null | س خ ر · اسم مفعول, Form II مُفَعَّل, جمع مؤنث سالم, حال منصوب | **F1 + F3-t0 + C5/O-2 gap** | **YES (C2)** |
| — | 39:71:30 | حَقَّتْ | ∅ (clean) | *asserted in morphline* | ح ق ق · Form I perfect 3fs (STEM+SUBJ) | **CORRECT contrast** | no |

Only **7:54:23** is tracked (debt manifest + audit@2, `primary_class C2`). The other six defective rows plus the whole F1/F2/F3 populations are **untracked debt outside the 1,452 ceiling**.

---

## Per-row detail (verbatim key fields · why it escaped · corrected shape)

### Row 1 — 38:14:6 فَحَقَّ  (F1: proclitic + rootless remainder)
- **Live:** `root=null`, `no_root_reason="no_public_root_asserted"`, `morphline="no public root asserted · FA:فَ + TOK:حَقَّ"`, segments `[FA فَ (qg-result-fa)] + [TOK حَقَّ (qg-segment, role token)]`, `learner="…Visible pieces: FA:فَ + TOK:حَقَّ."`
- **MCP truth:** فَ حرف عطف + حَقَّ فعل ماض, ثلاثي مجرد مضعّف, مادّة **حقق** → root **ح ق ق**, Form I perfect 3ms.
- **Why it escaped C1–C5:** the remainder حَقَّ is one `qg-segment` labelled `TOK`, not `qg-verb-stem` → **C1** (`_is_verb_stem`) never looks at it. **C2** requires `len(segments)==1`; this row has **2** segments (FA + TOK) → C2 returns early. C3 needs a function-class segment misfiled as content (TOK isn't a function class). C4 fallback phrases (`as context requires`/`not separately asserted`/`exposes the visible`) aren't present. C5 needs an enclitic pronoun. → **empty**. This is the exact **C2 blind spot**: a proclitic-split leaves a rootless *content remainder* that C2's single-segment rule can't see.
- **Inconsistency vs 39:71:30 حَقَّتْ** (same lexeme, correct): that row asserts `morphline="root ح ق ق · Form I perfect active · feminine subject marker"` with `STEM حَقَّ + SUBJ تْ`. The producer had the root for the identical stem 25 rows away.
- **Corrected shape (propose):** `root:"ح ق ق"`, `morphline:"root ح ق ق · Form I perfect active 3ms (geminate)"`, segments `[FA فَ (qg-result-fa, "so/then")] + [STEM حَقَّ (qg-verb-stem, sarf: Form I perfect active geminate stem)]`, English learner text (drop "Visible pieces: FA:… + TOK:…").

### Row 2 — 39:71:31 كَلِمَةُ  (F2: raw-Arabic iʿrāb dumped into learner fields)
- **Live:** no `root` field; `sarf_note="اسم، مؤنث، مفرد، جامد، على وزن (فَعِلَة)، مادة (كلم)"`; `nahw_note="فاعل مرفوع وعلامة رفعه الضمة وهو مضاف"`; `learner="A noun meaning the word or decree, acting as the doer…"`; single segment (ة unsegmented).
- **MCP truth:** root **ك ل م**, noun f.sg, وزن فَعِلَة, فاعل مرفوع مضاف — **the whitelist `sarf_note`/`nahw_note` are the MCP Arabic strings pasted verbatim into learner-facing fields.**
- **Why it escaped:** **no class inspects field language.** C2 would be the nearest (single `qg-noun-stem` whole token, root unasserted) but the **bare length `كلمة` = 4 < 5** floor of C2's noun/derived branch → returns empty; and the root ك ل م sits in `مادة (كلم)` prose which the detector's `_ROOT_ARABIC_RE` (looks for `root …`, not `مادة …`) does not recognise as asserted. → empty.
- **Corrected shape:** `root:"ك ل م"`, English `sarf_note` ("triliteral feminine noun, pattern faʿila"), English `nahw_note` ("subject (fāʿil), nominative; first term of an iḍāfa"), `morphline:"root ك ل م · noun f.sg · fāʿil / muḍāf"`. (ة may stay unsplit — it's pattern morphology, not a clitic.)

### Row 3 — 36:70:1 (canon 36:70:5) وَيَحِقَّ  (F1 + unsegmented imperfect prefix)
- **Live:** `root=null`, `no_root_reason="function_only_no_root"`, `morphline="function only no root · CONJ:وَ + TOK:يَحِقَّ"`, segments `[CONJ وَ] + [TOK يَحِقَّ (qg-segment)]`. (Carries a `source_address_crosswalk` display/canonical loc mismatch, but `display_surface==canonical_surface` so it is otherwise deployable.)
- **MCP truth:** وَ عطف + يَحِقَّ فعل مضارع منصوب, أصله يَحْقِقُ, مادّة **حقق** → root **ح ق ق**, Form I imperfect. The **يَ is the imperfect agreement prefix**, folded into the TOK.
- **Why it escaped:** same C2 blind spot as Row 1 (CONJ + TOK = 2 segments). Additionally the swallowed يَ prefix inside TOK is invisible because **C1 only looks at `qg-verb-stem` segments** — TOK is `qg-segment`. The page's own v024 entry displays حقق, yet the row is labelled "function only no root" (doubly wrong: it is neither function-only nor rootless).
- **Corrected shape:** `root:"ح ق ق"`, segments `[CONJ وَ] + [PFX يَ (qg-verb-prefix, imperfect 3ms marker)] + [STEM حِقَّ (qg-verb-stem, Form I imperfect subjunctive geminate)]`, `morphline:"root ح ق ق · Form I imperfect active, subjunctive"`.

### Row 4 — 7:105:1 حَقِيقٌ  (F2: internal meta-language leaking into learner text)
- **Live:** no `root`; `morphline="adjectival token with visible nominative tanwin; no unsupported root added"`; segment `sarf_note="sarf: visible piece accounted; no unsupported public source label"`, `nahw_note="nahw: function/context contribution preserved where relevant"`; `learner="حَقِيقٌ contributes \"bound\" here; visible pieces: ADJ:حَقِيقٌ."`
- **MCP truth:** root **ح ق ق**, **صفة مشبهة** on وزن فَعِيل from حَقَّ يَحِقُّ. Gloss "bound/obligated/fit" (contextually "أَنْ لَا أَقُولَ… حَقِيقٌ" = bound/obligated to say only truth).
- **Why it escaped:** field-language not checked. C2 explicitly **exempts adjectives** (`cls=="qg-adjective"` → the clean-participle guard returns early, because a ṣifa's pattern morphology is inseparable) — so a rootless ṣifa mushabbaha has no gate at all. The meta strings ("no unsupported public source label", "preserved where relevant") are pure internal provenance-hedge language, not learner content.
- **Corrected shape:** `root:"ح ق ق"`, `sarf_note:"ṣifa mushabbaha (adjectival), pattern faʿīl"`, `nahw_note:"second khabar of inna, nominative; tanwīn = indefinite"`, `morphline:"root ح ق ق · ṣifa mushabbaha, pattern faʿīl · nominative"`, learner rewritten as a plain gloss.

### Row 5 — 36:70:4 (canon 36:70:8) الْكَافِرِينَ  (F2 on a CORRECTLY segmented row)
- **Live:** segments `[ART الْ] + [STEM كَافِرِ (qg-adjective, role participle_stem)] + [PL ينَ]` — **segmentation is correct** — but **no `root`**, and **every segment** carries `sarf_note="sarf: visible piece accounted; no unsupported public source label"` + `nahw_note="nahw: function/context contribution preserved where relevant"`; `learner="…visible pieces: ART:الْ + STEM:كَافِرِ + PL:ينَ."`
- **MCP truth:** root **ك ف ر**, **اسم فاعل** (active participle) from كَفَرَ يَكْفُرُ, جمع مذكر سالم, وزن فاعل; ينَ = sound masculine plural suffix (genitive here).
- **Why it escaped:** segmentation is complete so no completeness gate applies (C1 needs a verb-stem swallow; STEM is `qg-adjective`; C2 needs 1 segment; here 3). Missing root + boilerplate notes are simply not classes. **This is the key proof that F2 is orthogonal to segmentation** — the row is structurally fine and still normatively defective.
- **Corrected shape:** `root:"ك ف ر"`, per-segment English notes (ART: definite article; STEM: active participle ism fāʿil, pattern fāʿil, root ك ف ر; PL: sound masculine plural, genitive), `morphline:"root ك ف ر · ism fāʿil, definite, sound masc. plural · genitive"`.

### Row 6 — 16:3:1 خَلَقَ  (F3-tier0 at its strongest: the rootless word IS a dictionary headword)
- **Live:** `root=null`, `morphline="no public root asserted · STEM:خَلَقَ"`, single `[STEM خَلَقَ (qg-verb-stem)]`, `learner="…Visible pieces: STEM:خَلَقَ."` (entry_url points at v024 — a crosswalk mis-link; خلق's own entry is v029/`c8190204`).
- **MCP truth:** root **خ ل ق**, Form I perfect 3ms (باب نصر). خَلَقَ is the **headword** of qamus entry `c8190204` (`root:"خ ل ق"`, headword `خَلَقَ / اِخْتِلَاق / خُلُق / خَلَاق`).
- **Why it escaped:** C1 needs a *swallowed* prefix (خَلَقَ has none — clean bare stem, `is_impf` false). C2's whole-token branch does **not** include class `qg-verb-stem`/role `verb_stem`/label `STEM` in its `wholeish` sets (`_C2_WHOLE_CLASSES/ROLES/LABELS`) → C2 returns empty. So a **clean single perfect verb stem with a null root has no gate whatsoever.** A dictionary headword is served rootless.
- **Corrected shape:** `root:"خ ل ق"`, `morphline:"root خ ل ق · Form I perfect active 3ms"`, `sarf_note:"Form I perfect active stem, sound triliteral"`.

### Row 7 — 7:54:23 مُسَخَّرَٰتٍ  (F1 + F3-tier0 + the C5 / O-2 suffix-vocabulary gap — the only tracked row)
- **Live:** `root=null`, `morphline="no public root asserted · TOK:مُسَخَّرَٰتٍۭ"`, single `[TOK مُسَخَّرَٰتٍۭ (qg-segment)]`, source_keys `["v029","v032"]`.
- **MCP truth:** root **س خ ر**, **اسم مفعول** (passive participle) of Form II سَخَّرَ, وزن مُفَعَّل, جمع مؤنث سالم (مفرده مُسَخَّرَة), grammatically حال منصوب. Form `مُسَخَّرَات`/`مُسَخَّرَاتٌ` is listed in entry **v198** (`f12aed82488d`, `root:"س خ ر"`) `usage[1].forms`.
- **Why it is (partly) caught:** `classify_live_row` fires **C2** here — single `qg-segment` whole-token, bare `مسخرت` ≥5, مـ-initial derived signature → "leaves its root unasserted". So it **is** in the debt manifest (`primary_class C2`) and audit@2. **But the segmentation defect is NOT caught:** the correct shape splits a separate **PL-F suffix `ـٰتٍ`** (sound feminine plural + tanwīn — a genuine separable suffix, exactly like الكافرين's `ينَ`). No class detects that swallow — **C5 only knows enclitic *pronouns* (`_ENCLITIC = هما/كما/هم/…/ي`)**; the sound-plural `ـات` and tanwīn are outside C5's vocabulary. **This is exactly the O-2 gap.** So C2 flags "missing root" but silently accepts `TOK:مُسَخَّرَٰتٍ` as one blob.
- **Corrected shape:** `root:"س خ ر"`, segments `[STEM مُسَخَّرَ (qg-adjective/participle-stem — the مُ is derivational مُفَعَّل pattern, stem-internal for colour per the مبينا / DR-1 boundary rule, but MUST be named in the morphline)] + [PL-F ـٰتٍ (qg-plural-suffix, sound feminine plural + tanwīn)]`, `morphline:"root س خ ر · Form II passive participle (ism mafʿūl, wazn mu-faʿʿal) · sound fem. plural + tanwīn · ḥāl (accusative)"`.

### Contrast — 39:71:30 حَقَّتْ  (the correct reference)
Root asserted (`morphline:"root ح ق ق · Form I perfect active · feminine subject marker"`), `[STEM حَقَّ (qg-verb-stem, sarf: Form I perfect active stem)] + [SUBJ تْ (qg-subject-pronoun, 3fs)]`, English notes. `classify` empty (clean), F2 empty. This is the shape all six defective rows should match.

---

## Detector-gap analysis (why C1–C5 miss these families)

| Gap | Class | Mechanism | Consequence |
|---|---|---|---|
| **G1 proclitic split → rootless remainder** | C2 | C2 only fires on `len(segments)==1`. A `[FA/CONJ/…]+[TOK]` split is ≥2 segments and the TOK is `qg-segment`, not a verb-stem → C1 also skips it. | Entire **F1** family (509) invisible. |
| **G2 clean verb-stem, null root** | C1/C2 | `qg-verb-stem` / role `verb_stem` / label `STEM` are absent from `_C2_WHOLE_*` sets; C1 fires only on a *swallowed* prefix. | Bare Form I stems (خَلَقَ) served rootless with no gate. |
| **G3 adjective/participle exemption** | C2 | `cls=="qg-adjective"` and "participle"/"adjective" in morphline hit the clean-participle guard → early return. | Rootless ṣifa/ism-fāʿil (حَقِيقٌ, and root-missing كافرين stem) uncaught. |
| **G4 root in `مادة`/prose, not `root …`** | all | `_ROOT_ARABIC_RE` only recognises `root <radicals>`; the Arabic `مادة (كلم)` idiom isn't parsed as a root assertion. | Rows carry the root in prose but read as rootless. |
| **G5 no field-language gate** | all | No class inspects whether learner_explanation / sarf_note / nahw_note / gloss_contribution are English or contain internal meta-language. | Entire **F2** family (2,260 strict; ~3.7k with the notation template). |
| **G6 C5 pronoun-only vocabulary (O-2)** | C5 | `_ENCLITIC` lists object/possessive/subject *pronouns* only; sound plural `ـات/ـين` + tanwīn are not suffix-swallow triggers. | Feminine-plural/tanwīn swallow (مُسَخَّرَٰتٍ) accepted as one blob even when C2 flags its root. |
| **G7 headword/entry incoherence not asserted** | all | No gate cross-references a rootless row against the entry that owns the surface. | Entire **F3** family (4,542 tier0) — including dictionary headwords — served rootless. |

---

## F1 — proclitic + rootless-remainder  (the فحق / ويحق blind spot)

Definition: ≥1 proclitic segment (class ∈ {qg-result-fa, qg-conjunction, qg-lam, qg-preposition, qg-future-particle} or label ∈ {FA,WA,BI,KA,LI,SIN,CONJ}) **AND** a remainder segment (label TOK/TOKEN, role token, or class qg-segment) **AND** rootless.

- **F1 total = 509.** **495 / 509 escape all C1–C5.**
- **Content-remainder subset = 141** (the remainder's bare surface is itself an entry headword/sense/usage form → a real lexeme denied its root). This is the harmful core; the balance are function words (prepositions مِن/فِى) that legitimately lack a root but also legitimately shouldn't carry a fake TOK.
- Examples (content-remainder): `38:14:6 فَحَقَّ` (rem حق), `36:70:1 وَيَحِقَّ` (rem يحق), `2:59:9 فَأَنزَلْنَا` (rem أنزل), `7:157:18 وَيُحِلُّ` (rem يحل), `3:64:9 وَبَيْنَكُمْ` (rem بين).
- Caveat: short function-word remainders (مِن→من) inflate the 141 via homograph collision with the منّ entry; treat 141 as an upper bound and ~real-verb/noun remainders as the deploy-worthy subset.

## F2 — field-language violation  (measured INDEPENDENTLY of segmentation)

Definition (strict, per ANDON): any of learner_explanation / morphline / segment gloss_contribution / sarf_note / nahw_note is **sustained Arabic prose** (>30% Arabic-script chars over alphabetic chars, ≥6 Arabic letters) **OR** contains an internal meta-marker ∈ {"no unsupported", "public source label", "preserved where relevant", "visible piece accounted"}.

- **F2 total = 2,260** — Arabic-prose **2,235**, named-meta-marker **33**. **2,193 / 2,260 escape all detectors.**

**Overlap matrix (F2 is orthogonal to segmentation):**

| Bucket | Count |
|---|---|
| F2 **&** segmentation-defect (C1/C2/C3/C5 fires) | 67 |
| F2 **&** rootless **&** no seg-defect | 1,020 |
| F2 **&** has-root **&** clean segmentation (**pure F2-only**) | 1,173 |
| (of which) F2 rows escaping **every** detector | 2,193 |

The **1,173 pure-F2-only** rows (well-segmented, root present, yet carrying raw-Arabic or meta prose — the الْكَافِرِينَ case) are the proof that field-language must be gated separately from any structural check.

**Adjacent notation-leak families** (same phenomenon, *not* in the strict named-string list, reported separately so they aren't double-counted):
- `"Visible pieces:"` learner-notation template (label codes `ART:/STEM:/TOK:` embedded in learner text): **3,697 rows**.
- morphline pseudo-explanations `"no public root asserted"` / `"function only no root"`: **1,065 rows**.

**Exact boilerplate-string frequency (occurrences corpus-wide):**

| Occurrences | String |
|---:|---|
| 3,418 | `Visible pieces:` |
| 1,403 | `no public root asserted` |
| 738 | `function only no root` |
| 27 | `sarf: visible piece accounted; no unsupported public source label` |
| 27 | `nahw: function/context contribution preserved where relevant` |
| 6 | `no unsupported root added` |

## F3 — entry-root incoherence  (rootless rows the dictionary can already root)

Definition: a rootless whitelist row whose (normalised) surface matches a form the qamus entries assert a root for. **Normalisation fix required:** whitelist surfaces are Uthmani (dagger-alif U+0670, Quranic annotation marks) while entry forms are plene alif; mapping dagger-alif→ا and **including `usage[].forms`** (not just headwords) raised the tier-0 count from 3,217 to **4,542**.

- **F3-tier0 = 4,542** (rootless surface == entry headword/sense/usage form). **4,481 / 4,542 escape all detectors** — the largest silent inheritable set.
  - headword-match subset: **2,606**; content-confident (bare length ≥4, excludes fn-word homographs مَن/مِن): **1,560** (safe floor).
- **F3-internal (extra) = 3,082** — rootless rows whose surface is NOT in the entry map but a *sibling whitelist row* asserts a root for the same surface (looser; some sibling roots are prose-extraction noise, so treat as secondary).
- **حق worked example:** `39:71:30 حَقَّتْ` asserts `ح ق ق`; the same-family `38:14:6 فَحَقَّ`, `36:70:1 وَيَحِقَّ`, `7:105:1 حَقِيقٌ` are all rootless — the root is inheritable within one card family.
- **Strongest case:** `16:3:1 خَلَقَ` (root null) **is itself the headword** of entry `c8190204` (root خ ل ق); `7:54:23 مُسَخَّرَٰتٍ` (root null) matches `usage.forms` of entry v198 (root س خ ر).

Total rootless rows overall = **22,344** (of 34,322) — F3 tiers are the subset the existing dictionary can already resolve without new authoring.

---

## Cross-reference to C4 / new-C3

- **C4 (fallback_leak)** = 528 live hits, triggered only by the three literal phrases `as context requires` / `not separately asserted` / `exposes the visible`. **None** of the 8 traced rows contain them → C4 does not cover this ANDON. The F2 meta-markers ("no unsupported public source label" etc.) are a *different* prose family C4 doesn't watch.
- **v3 new-C3 content-noun signatures** (definite-article ≥5 minus relatives; tanwīn ≥4) target *function-class* segments misfiled as particles. Rows 2/4/5/6 are already filed as noun/adjective/verb-stem classes (not function classes), so C3 never inspects them; row 5's `الْ` segment is `qg-article` length-2, below C3's ≥5 floor. → the new C3 does not reach this family either.

---

## Disposition (propose only — NOT deployed)

1. **F3-tier0 content-confident (1,560)** is packet-ready root backfill — deterministic inheritance from the owning entry (headword/usage.forms), highest confidence, zero new authoring. Route through the existing 2-vote/append lane.
2. **F1 content-remainder (141)** and **G2 clean-stem** rows need root assertion + (for F1) re-segmentation of the swallowed remainder — author lane.
3. **F2 (2,260 strict; +3.7k notation template)** needs a **new field-language gate** (English-only + meta-marker deny-list on learner-facing fields) — this is a *detector* addition, currently absent from C1–C5.
4. **O-2 / G6:** extend C5's suffix vocabulary to the sound plural `ـات/ـين` + tanwīn so suffix-swallow is caught independently of the root check.
5. All six untracked defective rows should be added to the debt manifest once a detector gate exists to hold them (today they cannot be grandfathered because no class flags them).

**No whitelist/manifest mutation performed. Snapshot sha `1c06d85a…903c` is the analysis basis.**
