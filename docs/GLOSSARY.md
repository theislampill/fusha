# Fusha / Qamus Glossary

Canonical vocabulary for Fusha parser/checker + Qamus rollout work. Where a term has an executable
or schema source of truth, it is cited; that source wins over this prose.

## 1. Coverage metrics (never conflate — `docs/STATUS.md` is the SSOT)

These three are **distinct measurements**; mixing them is a data-honesty defect.

- **Glossed coverage** — `glossed_word_locs / total_word_locs` over the deployed wbw lookup
  artifact. Current figure lives in **`docs/STATUS.md`** (live-side; not
  recomputable from this repo). SSOT: `docs/STATUS.md`.
- **Per-window rich-span coverage** — share of rendered Qurʾān word spans in a VN window that are
  rich-hover (`qword qg-colored` + `data-rh-live`). Gated per tranche; VN-00/01/02 frozen at 100%.
- **Whitelist-row share** — deployed whitelist rows over the loc ceiling (`docs/STATUS.md`:
  34,322 rows = 68.8% of ≤49,902). A row count, **not** a coverage percentage.

## 2. Entry vs lemma vs qword (never reconcile by adding entries)

Per `docs/qamus-public-entry-count-policy.md` §2, index/projection layers count *other things*.

- **Public entry** — a reviewed dictionary entry. Authoritative count
  **2,092**
  (noun/verb/particle split `entry-manifest.json#section_counts`). CI-guarded by
  `tools/validate_public_entry_count.py`.
- **Lemma** — a headword lexeme; largelexicon lemma rows
  **2,092**.
- **qword** — a single visible Qurʾānic word occurrence; the largelexicon denominator is
  **117,117** rows.
  A qword count is an occurrence denominator, **not** an entry count.

## 3. qg display classes

The **qamus-grammar-v1 (qg)** classes are display roles for source-clean rich-hover colouring —
not provenance. The canonical enum is **generated** in
`docs/parser/qamus-grammar-v1-class-map.md` from `qamus/schemas/morphosyntax-token.schema.json`;
consult it, do not retype it here. `qg-negation` is canonical; `qg-negative` is a legacy alias for
validator migration only.

## 4. Public / private boundary terms

- **Public payload** — `{ "src":"qamus", "kind":"authored", "lang":"en" }` + gloss + learner text +
  `parse_key.summary` + qg class. Grammar-facing only; no source/tool/process labels, no parse
  hashes or internal ids. Enforced by `tools/leak_sot.py`,
  `tools/validate_public_private_boundary.py`.
- **`informed_by`** — an **internal** provenance breadcrumb (e.g. `['qac']`); never surfaced in the
  public hover.
- **`parse_key.summary`** — compact learner ASCII (e.g. `V:I:PERF:ACT`, `P:bi`, `ART`), not a
  symbolic engine key.

## 5. Certification / fanout gates (`docs/certification-policy.md`)

- **Token-level two-vote certification** — per-occurrence hover decision; certifies *this* loc, does
  not authorize reuse.
- **Certified-lemma fanout** — authorizes a solved sarf/nahw fact to reuse across occurrences via one
  of three gates: **`source_address_exact`** (any POS, exact loc), **`lemma_pattern_pos`** (content
  words only, two-vote), **`function_context`** (particles/functions, function+context agreement).
  Particles may never fan out via `lemma_pattern_pos`.

## 6. Transclusion terms (`docs/parser/meta-transclusive-lattice-projection.md`)

- **Source-address transclusion** — reuse keyed by stable entry/card/qword handles + canonical
  `quran:S:A:W` / `wbw:S:A:W`. **Loc-first**; surface-only keys are diagnostic, not reuse authority.
- **Meta-transclusive lattice projection** — reuse of sarf/nahw/typed-edge/renderer facts across
  equivalent occurrences; every equivalent occurrence must either project the richer fact or carry an
  exact exception. Accepted crosswalk rows are **support evidence, not visual closure**.

## 7. VN / tranche terms (`docs/vn-tranche-completion-playbook.md`)

- **VN window** — a page range on the authoritative `source_key` ordering (e.g. VN-00 =
  `v001-v047 + n0001-n0045`). NOT a `created_at` proxy.
- **Rich-hover complete** — every rendered span is rich-hover, proven-not-visible, or covered by an
  exact durable packet. Flat `data-tr` only / `qw-pending` / "needs-sarf" are **not** completion.
- **Disposition buckets** — `deploy_ready_authorable` / `scholar_iurab` / `source_crosswalk` /
  `owner_decision` / `impossible`.
