# INCREMENT-21 — ṣarf@2.1 / naḥw@2.1 CANDIDATE increment notes

**Lane:** SKILL-INCREMENT (O-6). **Date:** 2026-07-12. **Repo:** PUBLIC github.com/theIslampill/fusha.
**Status:** CANDIDATE, drafted forward off `origin/main`. Does NOT amend released @2 text (appended as clearly-marked
@2.1-candidate sections). Fable adjudicates; nothing merged, nothing promoted to `accepted`.

Consolidates nine calibration-cycle evidence sources into 27 candidate rules (19 ṣarf, 8 naḥw), each with a
source-addressed `projector` block, positive + boundary/control examples, defeaters, and an abstention condition.

- Registry rows: `qamus/skills/rule-registry-increment-21.jsonl` (27 rows, schema-conformant, `sarf@2.1`/`nahw@2.1`, status `candidate`).
- Fixtures: `tools/skill_fixtures/skill_fixtures_increment21.jsonl` (55) + discriminators `skill_rules_increment21.py` + harness `test_skill_fixtures_increment21.py`.
- Deterministic builder: `tools/skill_fixtures/_build_increment21.py` (`--check` proves regeneration-clean).
- SKILL amendments: `sarf/SKILL.md` §18 + `nahw/SKILL.md` "naḥw@2.1" section (append-only; mirrors regenerated, drift --real 0).

## Evidence → rule map (which source produced which rule, and what it would have accelerated)

### C2 (whole_token_root calibration; precision 1.000, 0 FP; يتوفى FN)
- `sarf-pattern-never-certifies-root` (review) ← است/مست ≠ Form X (استوى→سوي VIII); two-tier candidate→certify (DR-2).
  Would have stopped a pattern-shape root certification on the 4 jāmid/contested C2 tokens.
- `sarf-weak-whole-token-detector` (review) ← يتوفى 39:42:2 FN (و ف ي Form V لفيف مفروق, DR-2's 24 attested).
  Closes the C2/measured-effect gate blind spot the abstention rules only routed, never detected.
- `sarf-cross-source-root-conflict-no-majority-vote` (projector) ← ملائكة 66:6:12 MCP ألك vs QAC ملك.
  Would have kept the 4 C2 two-vote rows from a single-source root assertion.
- `sarf-jamid-vs-mushtaqq-routing` (projector) ← C2a/C2b split (ملكوت, مثاني, مسكين).
  Auto-routes the jāmid FP reservoir to 2-vote instead of a "derived whole-token" root assertion.
- `sarf-loc-integrity-address-xcheck` (validator) ← 25:33:2→8, 61:4:3→11 (joined by C5 + C1 + measured-effect below).

### C4 (fallback_leak; hard-error rate 20.4%; imperative-person filter caught 9/10)
- `sarf-hamza-initial-disambiguation` (review) ← 2:62:9/2:283:11/38:5:1/33:37:9 — bans the "1s or Form IV" disjunction (4/10 hard errors).
- `sarf-imperative-second-person-invariant` (projector, validator-grade) ← 2:40:3/3:79:20/34:13:12/49:10:4 — 5/5 tagged imperatives were wrong; catches 9/10 with zero MCP.
- `sarf-passive-vocalism-voice-commit` (review) ← 21:35:10 تُرْجَعُونَ — vocalism decides voice; the hedge was lazy.
- `nahw-mood-from-governor` (review) ← 17:12:16 منصوب بأن مضمرة — replaces "mood not separately asserted".
- `sarf-completeness-claim-requires-asserted-facts` (projector) ← 523/523 C4 rows carried the false completeness claim; the honesty swap is committable today with zero morphology.
- `sarf-segment-morphline-person-consistency` (projector) ← 17:12:16 self-contradiction no gate caught.

### C5 (suffix_swallow; precision 84%, 8 FP all in named families)
- `sarf-root-radical-not-clitic` (projector) ← تهدي/تأتي (ي-family 2/2 FP), تملك, initial-wāw وعد.
- `sarf-zero-marker-agreement-no-segment` (projector) ← فأت/وعد mustatir demanded a segment.
- `sarf-negated-mention-no-keyword-fire` (projector) ← الكبرى fired on "not an attached pronoun".
- `sarf-epenthetic-ishbaa-waw-not-segment` (projector) ← أورثتموها ـتُمُو + pronoun.
- `sarf-jam-marker-single-pronoun-segment` (review) ← هُنَّ cluster, never a bare هـ orphaning the mīm/nūn.
- `nahw-ha-tanbih-not-pronoun` (projector) ← يأيها 8:65:1/12:78:2 — ها is حرف تنبيه, not a pronoun.
- Each C5 FP family is now a deterministic NEGATIVE guard that PREVENTS a bad projection — the highest-value class for the lattice.

### W13-round2 (ownership remediation; the @2 rules HELD 6/11 round-1 rebinds)
- `sarf-within-root-pos-arm` (projector) ← قُل 10:59:1 — a POS reading only one candidate root supports is an ownership arm.
- `sarf-content-hold-absent-ownership-arm` (projector) ← ربك/الشياطين — root named, no forms arm → HOLD, never fabricate a rebind.
- `nahw-fused-preposition-closed-class-floor` (projector) ← فيها/عليكم — extend the closed-class floor so they affirm, not park.

### DR-1 / DR-6 (verified deep-research claims)
- `sarf-form-v-vi-ta-is-wazn-augment` (projector, DR-1) ← the Form V/VI ت is a زائد wazn augment (Shadhā al-ʿArf), never a proclitic; QAC 3-seg precedent 83:26:5.
- `nahw-lam-prefix-typology` (review, DR-1/DR-6) ← distinct lām types (أمر/تعليل/جر/ابتداء), each its own segment + consequence.
- `nahw-jazm-only-on-mudari` (projector, DR-6) ← jazm/mood applies only to the muḍāriʿ; a mabnī perfect/imperative is never majzūm.
- `nahw-ma-man-function-per-occurrence` (projector, DR-6) ← 5:116 has relative مَا AND nāfiya مَا in one āyah; never propagate a reading.
- `nahw-la-nahiya-jussive-governor` (projector, DR-6) ← لا الناهية governs jussive and owns the verb; distinct from لا النافية.

### C1 (stem_swallow; precision 34.1% — the C1 theory REFUTED)
- `sarf-coarse-tier-verb-subject-one-unit` (projector) ← MCP treats verb+subject as ONE sarf unit ({يُنْفِقُونَ}); the object pronoun always splits. Kills the 27 C1 FP; the S1-defeater codified.
- `nahw-lam-qasam-nun-tawkid-finite` (projector) ← فَلَيُبَتِّكُنَّ 4:119:4 — لام جواب القسم + نون التوكيد, finite energic marfūʿ; blocks the dictionary-infinitive leak ("to slit"); mood distinguishes it from لام الأمر (majzūm).
- Address-validity gate: C1's IMPOSSIBLE address 4:91:103 (32-word āyah) folded into `sarf-loc-integrity-address-xcheck` — now **five** independent loc-integrity finds across C1/C2/C5, one validator-grade rule + fixture family.

### MEASURED-EFFECT (n=14 A/B against MCP)
- The only disposition-changing rule was the morphline-authored (content-quality) rule; derivational-morphology rules added **no lift**.
  Consequence honored here: the high-value cluster is the C4 authoring rules + the C5/W13 function-word / host-ownership guards; this
  increment deliberately does NOT add new pure-derivational rules (they would be justification-only). The measured structural gaps —
  non-morphological defect classes and function-word/ownership discipline — are exactly what the projector-ready rules encode.

## Projector-readiness assessment (per rule)

**Projector-ready (18)** — machine-checkable condition, deterministic projection (guard / routing / consistency / negative-guard).
Safe to key a transclusion/projection lattice on: `sarf-cross-source-root-conflict-no-majority-vote`,
`sarf-jamid-vs-mushtaqq-routing`, `sarf-loc-integrity-address-xcheck`, `sarf-imperative-second-person-invariant`,
`sarf-completeness-claim-requires-asserted-facts`, `sarf-segment-morphline-person-consistency`,
`sarf-form-v-vi-ta-is-wazn-augment`, `sarf-root-radical-not-clitic`, `sarf-zero-marker-agreement-no-segment`,
`sarf-negated-mention-no-keyword-fire`, `sarf-epenthetic-ishbaa-waw-not-segment`, `sarf-within-root-pos-arm`,
`sarf-content-hold-absent-ownership-arm`, `sarf-coarse-tier-verb-subject-one-unit`, `nahw-jazm-only-on-mudari`,
`nahw-ma-man-function-per-occurrence`, `nahw-la-nahiya-jussive-governor`, `nahw-ha-tanbih-not-pronoun`,
`nahw-fused-preposition-closed-class-floor`, `nahw-lam-qasam-nun-tawkid-finite`.
(Note: the C5/C1 negative guards PREVENT projections rather than emit facts — they are the lattice's fail-closed defenders.)

**Review-gated (7)** — the linguistic identification (which root / which lām type / which reading) needs an authoring or
2-vote pass; only the *consequence* is deterministic once identified. These carry a `review_gated` projector block whose
condition is the identification and whose projection is the governed consequence: `sarf-pattern-never-certifies-root`,
`sarf-weak-whole-token-detector`, `sarf-hamza-initial-disambiguation`, `sarf-passive-vocalism-voice-commit`,
`sarf-jam-marker-single-pronoun-segment` (repair template), `nahw-mood-from-governor`, `nahw-lam-prefix-typology`.

## Negative results recorded (no rule authored)

- **Derivational-tāʼ control PASSED (C1 #9):** the detector did not confuse Form V/VI derivational تَ with the agreement تـ
  (يَتَرَاجَعَ, تَنَافَس unflagged on that axis) — no guard needed beyond `sarf-form-v-vi-ta-is-wazn-augment`'s wazn keying.
- **Article ٱل stratum EMPTY in C1** — all 254 C1 rows are verbs; article-swallow lives in other classes, not samplable here.
- **Surface-fidelity (C1 #8):** bare-rasm vs Uthmani storage (تقتلون 2:91:3, يأتيانها 4:16:2) is a data-fidelity smoke, out of scope for a skill rule.
- **Over-expansion guard (measured-effect):** no new pure-derivational rules — they add justification only, not disposition change.

## Validation results (all green at author time)

- `validate_skill_registry.py --self-test` → **15/15** (adds @2.1 candidate/blocked transitions; @2.1-accepted correctly rejected).
- Merged registry (`rule-registry.jsonl` + increment) → **198 rows, 0 errors** (0 dup / 0 dangling; increment `extends` targets resolve in main).
- `jsonschema` Draft7 against `skill-rule-registry-row.schema.json` → **27/27 rows, 0 errors**; @2.1-accepted rejected by schema.
- `test_skill_fixtures_increment21.py` → **55 fixtures, 28 red-first, 27 rules, 27 registry ids covered**; every corrected discriminator branches (non-constant / anti-send-back); loc-integrity mismatch + impossible finds present; builder regeneration-clean.
- `check_skill_drift.py --real` → **0 findings**; `--self-test` green. `generate_skill_mirrors.py --self-test` green; mirror map + knowledge manifest regenerated (sarf 41,935 / nahw 35,173 bytes).
- Released @2 registry (171 rows) and the @2 richseg fixtures untouched and still green.
