# Skill usage in production (D0/E0)

Proof that the installed `/fusha-sarf` + `/fusha-nahw` skills **drive** the live decisions, not just
document them. Every applied batch this tranche cites the procedure(s) used and the eval that would
catch a wrong version. Skills load via the Skill tool; the engine SKILL.md + procedures are also read
directly from `sarf/` + `nahw/`.

## Per-batch skill provenance

| batch | sarf procedure | nahw procedure | eval that catches a wrong version |
|---|---|---|---|
| **B3 token-iʿrāb** (188 applied) | `homograph-risk` (root split: عاد عدا≠tribe, ذهب noun≠verb, أذن) | `particle-decision` + `negation` + `relative-interrogative` (وما/فما/ألا/أمّ) + `referent-context` (يحيى=John) | `nahw/evals/grammar-problems-derived-eval` (relative/negation/istithnāʾ); `nahw/rules/state-transition-rules` |
| **B2 host-lexeme** (suffix hosts) | `suffix-pronoun-state` + `noun-plural-gender` (broken plural: سيئات/مساكن/آلهة) | `pronoun-attachment` | `nahw/evals/suffix-pronoun-eval` (verb-exclusion, tanwīn-alef, false-split) |
| P4 suffix/pronoun (prior) | `suffix-pronoun-state` (POS-gate) | `pronoun-attachment` | `suffix-pronoun-eval` SP-005/006/007 |
| P5/P6 content (prior) | `homograph-risk` + `verb-form` | `referent-context` | `sarf/evals/qamus-regression-eval` |

## New failure-mode classes this tranche → regressions

- **function-word per-loc polysemy** (وما negation vs relative vs interrogative; ألا = أن+لا vs
  istiftāḥ; فما; لمّا vs لِما) — resolved only by iʿrāb, never by the surface key. Encoded in the B3
  verifier gates; representative resolved locs in `token_irab_batch_001` + `token-irab-polysemy-report.md`.
- **content-homograph by root** (عاد transgressor/tribe/returned; جنّة garden/madness; ذكر
  male/reminder/mention; ذهب gold/went; أذن ear/permitted) — sarf root split + nahw context.
- **false enclitic split** (ٱلْمُلْك root م-ل-ك ≠ مُلك+ك; لَهُ preposition+pronoun ≠ possessed noun) —
  the B2 host generator + verifier reject these (sarf principle 4: clitic stripping must not invent a
  false stem). Tested by `test_suffix_pronoun.py` + the `false_split` verifier class.

## E0 — external-source triangulation (internal evidence only)

Allowed internal evidence: Tafsir MCP (iʿrāb/sarf/meaning), QAC (root/POS), Quran.com WBW, Tanzil
text, source photos, the Qamus dataset, the Fusha rules. **Public output is exactly
`{"src":"qamus","kind":"authored"}`** — no source name, no copied gloss text.

This tranche used the **Tafsir MCP** (`mcp.tafsir.net`) as internal iʿrāb evidence for a sample of B3
locs (وما 3:7, عاد 2:173 = ism fāʿil "transgressor" NOT the tribe, أذن 78:38, ذهب 43:71, ألا 17:23 =
أن+لا, فما 7:39). Each is cached **source-hashed** under the gitignored `sources/tafsir_mcp/cache/`
(a tiny redacted example is committed under `sources/tafsir_mcp/examples/redacted/`), and each
MCP-backed decision records internal provenance separately:

```json
{"public_record":{"src":"qamus","kind":"authored"},
 "internal_provenance":{"informed_by":["qac","quran-text","tafsir-mcp"],"mcp_used":true,"method":"per-loc iʿrāb"}}
```

`tools/validate_token_irab_decisions.py` fails closed on any provenance leak in the public fields
(checked: 0 leaks across the 188-row batch). The skills themselves remain **MCP-free** (verified by
`check_regressions.py` / `verify_skill_install.py`): they consult *available source adapters* generically.
