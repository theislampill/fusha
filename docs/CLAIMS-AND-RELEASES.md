# Claims and Releases

What Fusha may claim, what it may not, and where the truth of each claim lives. A claim is only
sayable if its cited validator/artifact backs it.

## 1. Claim boundary (`docs/parser/claim-boundary.md`, `largelexicon-claim-boundary.md`)

The current Fusha parser/checker work is a **dependency-free smoke substrate** for Qamus Mode A and
learner-facing development. It is **NOT**: live Qamus progress; arbitrary-text certification; a
trained dependency parser; equivalent to CAMeL Tools, MADAMIRA, or Stanza.

## 2. Allowed claims ↔ validators (each cites an executable source of truth)

| Claim | Validator (`--self-test`) |
|---|---|
| Mode A fixture mechanics | `tools/validate_qamus_mode_a_adoption.py` |
| morphology smoke substrate | `tools/validate_fusha_morph_db.py`, `tools/eval_fusha_morphology.py` |
| rule-ranked parser baseline | `tools/validate_fusha_parser_baseline.py` |
| eval / model-card / source-ledger gates | `tools/validate_fusha_evaluation.py` |
| public wording | `tools/validate_parser_claims.py` |
| largelexicon table integrity | `tools/validate_largelexicon_*` (see largelexicon-implementation) |
| qamustyping4 all-qword acceptance | `tools/validate_qamustyping4_acceptance.py` |
| public entry count (2092) | `tools/validate_public_entry_count.py` |

Stronger claims require new source-ledger review, split manifests, metrics, model cards, and owner
authorization.

## 3. Certified vs inferred vs live claims (evidence-tier tags)

Each claim below carries its evidence tier. **`[inferred]` claims are NOT directly committed** — they
are deduced from committed receipts and must be labeled so no reader treats them as verified rows.

- **Token-level two-vote certification is well-populated.** `[direct]` — evidence trail committed at
  `qamus/reports/closure-2092/bulk-two-vote-*` (arbitration/reconciliation files) + the
  `bulk-certified-apply-batch-20260625-*.json` apply receipts.
- **The certified token *store* lives live-side, not as a committed table here.** `[inferred]` —
  live-side placement is inferred from the apply receipts (per `docs/certification-policy.md` §0), not
  from a committed store in this repo.
- **Certified-lemma fanout coverage is near-zero.** `[direct]` — only illustrative sample + reject
  fixtures exist; no production `certified` rows are written.
- **Glossed coverage — see `docs/STATUS.md` (SSOT; live-side, not transcribed here).** `[live]` — measured on the
  deployed artifact; **not recomputable from this repo**. SSOT `docs/STATUS.md`.
- **Largelexicon accepted crosswalk rows** =
  read live from `qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json#status_counts.canonical_crosswalk_accepted` (moves per promotion wave; not transcribed here).
  `[direct]` — but these are **support evidence, not live coverage** (see TRANSCLUSION defect box).

## 4. Release / freeze state (`docs/STATUS.md`)

- VN-00 / VN-01 / VN-02 rich-span gates **frozen at 100%** (regression smokes assert per tranche).
- VN-03 **measured but NOT started** (percentage in `docs/STATUS.md`) — normative-future only.
- Artifact built 2026-07-07, verified current 2026-07-10 (currency check, not a fresh measurement).

## 5. Owner-gated — not yet claimable

- **Writing real `certified` rows** — owner decision #1 (certification authority);
  `docs/certification-policy.md` §5 ("No production certified-lemma rows are written by adopting this
  policy").
- **Dataset licensing (D-01)** — OPEN; see `NOTICE` (interim wording only, no conclusion conceded).
  This lane does not touch it.
- **Any VN-02→full-Qamus rollout claim** — not made; only VN-00/01/02 windows are closed.
