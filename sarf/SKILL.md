---
name: sarf
description: Reason about an Arabic word-FORM (root, POS, derived form, clitics) BEFORE authoring or applying a Qamus gloss. Encodes the exact morphology mistakes fought in qamus-highlight. Use whenever adding a hover gloss, repairing a root/form, adding a surface form, moving a token from pending→resolved, or importing a lexeme candidate.
---

# Sarf (morphology) skill

You author or repair a scripture-facing gloss only **after** you can answer: what is the root, what is the
part of speech, is this a homograph risk, and is this safely matchable to a Qamus entry — **or should it stay
pending?** This skill is the discipline that prevents wrong hover glosses. It is **not** a generic Arabic lesson.

## 1. Purpose
Turn a raw surface into a *defensible* morphological decision (or an honest pending) for Qamus authoring,
qamus-highlight resolution, and Nawawī40/Ṣaḥīḥayn candidate classification.

## 2. Input contract
A surface (Arabic, with diacritics if available) + its `quran_loc` (or hadith ref) + optional Qamus
entry candidates + optional QAC root/POS.

## 3. Output contract — emit this object before any gloss/repair/resolve
```json
{
  "surface_ar": "يَأْتِي", "normalized": "ياتي", "strict_normalized": "يأتي", "bare": "يأتي",
  "quran_loc": "2:38:10", "candidate_root": "أ ت ي", "candidate_lemma": "أتى",
  "pos": "verb", "form": "I", "voice": "active_or_passive_or_unknown",
  "attached_clitics": [], "suffix_pronoun": null,
  "qac_root": "أ ت ي", "qac_pos": "V", "qamus_entry_candidates": ["entry_id"],
  "risk_flags": ["multi_sense_root", "hamza_sensitive", "sense_selection_required"],
  "decision": "resolved | pending | quarantine",
  "reason": "root/POS agree but multiple senses; requires context",
  "confidence": "high|medium|low", "allowed_for_hover": false
}
```

## 4. Normalization ladder (each rung is for a different job; never display these)
`tools/normalize_ar.py` provides them.
1. **raw Arabic** — the only display form; never altered.
2. **`norm()`** — lenient recall key (drops hamza + harakāt). **Lookup assistance only — never certifies.**
3. **`norm_strict()`** — keeps the hamza seat; use for scripture-facing matching.
4. **`bare()`** — keeps every base letter distinct (ة≠ه، أ≠ا، ى≠ي); for enclitic detection.
5. **QAC token** — authoritative per-word root + POS (internal evidence).
6. **source-address loc** — `quran:S:A:W` to record + dedup the decision.

## 5. Root decision ladder (stop at the first that certifies)
Qamus source entry → **QAC root** → photographed source page → external reference (triangulation) → **only
then** a heuristic. A heuristic root alone is never enough for a scripture-facing gloss.

## 6. POS decision ladder
QAC POS → Qamus category → morphological shape (wazn) → context. **A POS mismatch is a blocker** (§ principle 3).

## 7. Derived form / wazn hints
Form II/IV often change sense + transitivity (يُحَذِّرُ "warns" ≠ "be cautious"; أَلْقَوْا form IV ≠ "meet";
فَأَخْرَجَ form IV "brought forth" ≠ "come out"). Maṣdar/participle usually need a **nominal** gloss
(تَحْرِير "freeing", not "to free… heat"). Passive vs active changes wording.

## 8. Common clitics & suffixes
Proclitics وَ/فَ/بِ/لِ/كَ/ال and pronoun enclitics ـه/ـها/ـهم/ـكم/ـنا. **Clitic stripping must not invent a
false stem** — and a final tanwīn-alef (ـًا, e.g. قُرْءَانًا) is **not** the pronoun نا (`ends_tanwin_alef`).

## 9. Homograph quarantine rules
If two readings collapse under `norm()`, decide on the **content letter's harakah / hamza seat / shadda**, not
on `norm`. If you cannot decide → **pending**, never a guess. (Full list in `drills/homograph-regressions.md`.)

## 10. When to author a gloss
Root + POS certified, single applicable sense (or context fixed via the nahw skill), no homograph/POS conflict.

## 11. When to make pending (with a precise reason)
`root_exists_form_unresolved` · `pos_mismatch` · `hamza_sensitive_homograph` · `multi_sense_root` ·
`derived_form_needs_review` · `proper_noun` · `source_evidence_needed` · `qamus_entry_needs_repair`.

## 12. When to create a Qamus repair candidate
The token is right but the **entry** is wrong (mis-filed form, impossible root that is a real error, count
mismatch). Emit a repair candidate with a source address + field path — **never** mutate live data here.

## 13. Regression examples
See `examples/qamus-regressions.jsonl` and `examples/root-form-decisions.jsonl`. They encode the exact bug
classes already fixed; a change that would re-introduce any of them is wrong.

## 14. Integration with qamus-highlight
A sarf `decision` maps directly: `resolved`→author the gloss (src=qamus); `pending`→set the pending reason;
`quarantine`→demote/deny the wrong sense. Record the decision at `quran:S:A:W` in the source-address graph so
the same call is reused, never recomputed, across occurrences.

## 15. Integration with Nawawī40 / Ṣaḥīḥayn catalogues
For each catalogue token, run the same ladder to classify: already_in_qamus / new_surface_for_existing_lemma /
new_lemma_existing_root / new_root_or_unknown_root / particle_or_construction / uncertain_needs_review.

---

## The five sarf principles (encode these)
1. **Never infer a root from `norm()` alone.** It drops hamza + harakāt for recall. `إِلَيْنَا` is **not** ل ي ن;
   `إيمان`≠`أيمان`; `يَأْمُرُونَ`≠`يَمُرُّونَ`; `قُرْءَانًا` is not stem+نا; `مَالِكِ` is not مَا لَكَ.
2. **Preserve hamza-seat distinctions** (أ/إ/ؤ/ئ/ء). Recall may be hamza-insensitive; any authored gloss/repair
   must pass `norm_strict` + QAC root/POS.
3. **POS mismatch is a blocker.** No verb gloss on a noun unless the Qamus sense supports the nominal use:
   `رَسُولًا`≠"to send"; `ٱبْن`/`بَنَات`/`بَنِي`≠"to build"; `مُحَمَّد`/`أَحْمَد`≠"to praise"; `صَٰلِحًا` is descriptive,
   not the Prophet Ṣāliḥ unless context supports it.
4. **Derived-form & stem matching must be conservative.** Form IV hamza changes sense; passive ≠ active;
   maṣdar/participle take nominal glosses; clitic stripping must not create a false stem.
5. **Use QAC as INTERNAL morphology evidence, not a public source.** Root/POS/lemma/validation/conflict-detection
   are fine internally; the public hover record is exactly `{"src":"qamus","kind":"authored"}` — no QAC name.

## NEVER DO THIS (wrong-gloss prevention)
- Never gloss from `norm()` alone. Never drop the hamza distinction for an authored gloss.
- Never put a verb infinitive on a noun, proper noun, or participle whose sense differs.
- Never copy an external gloss. Never expose `informed_by`/QAC/Quran.com/Tanzil in a public artifact.
- Never resolve when uncertain — **prefer pending with a precise reason.**
