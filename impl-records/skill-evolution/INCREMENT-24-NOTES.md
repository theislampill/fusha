# INCREMENT-24 — sarf@2.4 / nahw@2.4 candidate increment (P00-vertical-slice pilot dogfood)

Cycle: 2026-07-29. Status: **candidate** (Fable adjudicates; does not amend accepted @2).
Registry rows: `qamus/skills/rule-registry-increment-24.jsonl` (9 rules: 5 sarf + 4 nahw).
Discriminators: `tools/skill_fixtures/skill_rules_increment24.py`.
Fixtures: `tools/skill_fixtures/skill_fixtures_increment24.jsonl` (26: 15 red-first + 11 branch-control).
Harness: `tools/skill_fixtures/test_skill_fixtures_increment24.py` (check_regressions SKILL-RELEASE gate 15).

## Inputs (measured, not speculative)

1. **P00 vertical slice** (packet `P00-VERTICAL-SLICE-2026-07-29`, external to this repo): the
   p007 jarr clitic **لِـ** (entry `b10a1ee04666`, sense 2) on noun hosts — 12 canonical
   occurrences taken discovery → candidate lattice → MCP evidence → independent two-vote review
   (12/12 `two_vote_verified`) → fact-level certification (49/49 typed facts, lane-local store) →
   two-surface projection with exact letter ownership (0 hash forks over 78 appearances) → live
   reverse-check (2 true carve forks, 12/12 colour-class deltas, NFC normalization exception).
2. **Two-vote canary run** (packet `TWO-VOTE-AGREEMENT-2026-07-29`): 4 canaries; canary 1
   (quran:2:91:23 تَقْتُلُونَ) exposed the tajarrud/no-governor contract bug; canary 3
   (quran:2:284:1 لِّلَّهِ) exposed the khabar-muqaddam notation-variant false disagreement.
   The governed reason-key vocabulary itself lands with PR #120
   (`qamus/skills/reason-key-registry.jsonl`).
3. **Particle-denominator calibration** (packet `PARTICLE-DENOMINATOR-CALIBRATION-2026-07-29`):
   stratified precision of the discovery classifier — S7 (lexical words with particle-like
   initial radicals) at 16.7% entry-level precision is the measured motivation for the
   host-routing and lexical-lām rules.

## The 9 rules (one line each)

sarf@2.4:
- `sarf-li-kasra-noun-host-clitic-carve` — لِ+kasra routes by HOST (noun/lexical-lām/pronoun/verb), never by shape.
- `sarf-lexical-initial-lam-madda-guard` — a candidate clitic lām that is the host's initial root radical rejects the carve (لِبَاسٌ) unless the per-occurrence iʿrāb attests the jarr clause (لِّلَّذِينَ).
- `sarf-li-pronoun-host-outside-noun-family` — لِى is jarr + pronoun host: rootless pair, own family, no noun-host template.
- `sarf-fused-lil-exact-letter-ownership` — لِلَّهِ carves لِ ∣ لَّهِ with exact base-letter span ownership; one canonical carve per surface (live carved للناس two ways).
- `sarf-nfc-normalize-before-span-parity` — NFC both sides before span parity; mark-order differences are not forks; post-NFC differences are.

nahw@2.4:
- `nahw-preposition-governs-majrur-governor` — the governor of a majrūr is the preposition itself; attachment is a separate plane; never null (the pilot's governor-null defect, caught by the validator, re-voted and endorsed).
- `nahw-khabar-muqaddam-two-notations-one-analysis` — "khabar muqaddam" ≡ "mutaʿalliq to elided fronted khabar": one analysis, one reason key (`khabar-muqaddam-shibh-jumla`).
- `nahw-mood-basis-tajarrud-governor-exemption` — rafʿ by tajarrud needs no overt governor (`mood_basis=tajarrud`; reason key `mudari3-raf3-tajarrud-thubut-nun`); nominal claims keep the requirement.
- `nahw-lam-talil-vs-jarr-host-pos` — token-initial لِ types by host POS+mood: jarr / taʿlīl / amr; no jarr claim over a verb host.

## Companion artifacts in this increment

- `qamus/skills/particle-function-registry.jsonl` — p007 function entries (jarr senses, rivals,
  and the lexical-lām non-membership guard) keyed to the PR #120 reason-key-registry ids where
  registered and carrying PROPOSED ids where the vocabulary has gaps (diptote-fatḥa sign,
  pronoun-host, lām-taʿlīl).
- `docs/qamus/particle-rich-hover-templates.md` — the pilot's rich-hover component-card template
  spec (particle identity + rootlessness + jarr relation + governed expression + case sign),
  documented beside the projection contract because the fd_compiler `_fd2_*` note builders are
  closed deterministic functions with byte-pinned test expectations, not a data-driven template
  layer (changing them changes committed fd2 verdicts — an fd-lane decision, not a skills-lane
  side effect).
- `curriculum/drills/jarr-clitic-li.md` — learner drills: jarr-clitic recognition, lexical-lām
  contrast, diptote sign.
- `qamus/scripts/find_li_noun_host_rows.py` — the dependent-row discovery query the
  full-population lane runs (analogous noun-host لِـ rows from the particle-occurrence matrix,
  with the pilot's guard classes pre-flagged).

## Adjudication asks

1. Accept/reject each @2.4 rule (all candidate; red-first fixtures wired at gate 15).
2. Adopt or amend the PROPOSED reason keys in `particle-function-registry.jsonl` into the PR #120
   registry (owner/two-vote lane owns that file).
3. Decide whether the tajarrud rule should also land as a validator change in
   `tools/validate_two_vote_artifacts.py` (two-vote lane owns that file; this increment only
   encodes the skill rule).
