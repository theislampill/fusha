# Corpus adapter design (later corpora: Nawawī 40, Ṣaḥīḥayn)

Verified against: commit `637d7da` (origin/main), audited 2026-07-29. **DESIGN ONLY — no ingestion is performed or authorized by this document.** Ṣaḥīḥayn work is owner-gated and plan-only: "No owner gate is present → no Ṣaḥīḥayn work performed; the pipeline mechanics are proven on Nawawī40 only" (`qamus/reports/closure-2092/hadith-owner-gate-readiness.md:3-5`). The phrase "corpus adapter" does not previously appear in the repo; this doc names the existing catalogue→diff→stage pipeline plus a per-corpus stage-1 reader as the adapter contract.

## 0. Preserved invariants (non-negotiable)

1. **The Qurʾān stays the anchor.** The 2,092-entry Qurʾānic lexicon is the spine; every other corpus is additive and owner-gated (`corpora/README.md:1-8`). "Later-corpus expansion from a Qurʾānic anchor" is an ARCHITECTURAL COMMITMENT (`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md:86`).
2. **Shareable across corpora:** entry/lexeme/root/pattern/form/sense facts, guarded rules (with their guards and defeaters), provenance, and exception records.
3. **Never auto-transferable:** Qurʾānic occurrence-specific syntax and meaning. An occurrence-level iʿrāb or sense decision certifies only its own `quran:S:A:W` address; a new corpus occurrence gets its own candidate lattice and its own two-vote decision. This is the same non-transfer rule already enforced inside the Qurʾān corpus itself (surface-similarity inference forbidden; the p007 pattern ceiling requires per-occurrence evidence — `qamus/examples/p007-li-pilot/vn-unlock.json#pattern_ceiling_li_kasra_clitic`).
4. **PENDING beats a wrong gloss**; no raw corpus text committed; Qurʾān/ḥadīth text read-only and verbatim; external references are evidence, never content (`corpora/README.md:25-45`).

## 1. What already exists (the audited baseline)

- **Pipeline (implemented, proven on Nawawī40):** catalogue → diff → stage. Scripts: `qamus/scripts/catalogue_nawawi40.py`, `diff_against_qamus.py`, `make_candidate_payloads.py`, `refine_nawawi40.py`; generalized `tools/corpus_to_qamus_candidates.py`, `tools/corpus_to_hover_decisions.py`, `tools/corpus_paths.py`, `tools/validate_corpus_fixture.py`. The 9-step contract (`qamus/reports/corpus-to-qamus-pipeline.md:14-24`): tokenize → source-address node `corpus:<ref>:<idx>` → sarf state decision → nahw state decision → Qamus index lookup → 7-way classify → author only through certified-author + key-aware two-vote → emit JSONL for review → **`live_write:false` on every row**.
- **Nawawī40 results** (`corpora/nawawi40/nawawi40.summary.md:13-30`): 42 refs, 2,818 token occurrences, 1,183 distinct lexeme candidates; buckets 394 already_in_qamus / 6 new_surface / 272 new_lemma_existing_root / 499 new_root / 6 particle / 6 uncertain; 720 new-entry candidates, 789 review-queue, **0 live writes**. Candidate record shape: `qamus/candidates/nawawi40/new_entries.sample.jsonl:1` (`status:"candidate"`, `review_status:"needs_review"`, `source_scope:["nawawi40"]`, `public_provenance:{src:"qamus",kind:"authored"}`); no ḥadīth text bundled (`qamus/candidates/nawawi40/README.md:6-9`).
- **Ṣaḥīḥayn plan** (`corpora/sahihayn/PLAN.md`, aspirational `:1-6`): stages 2–3 reused unchanged; only a corpus-specific stage-1 reader is net-new (`:37-53`); three prerequisites before scale-up (`:13-19`: human-reviewed Nawawī40 candidates with measured diff-classifier false-positive rate; owner licensing/provenance posture; normalization guardrails held); four owner-gated phases (`:55-82`).
- **Qurʾān storage model to match:** Tanzil Uthmani v1.1, CC BY 3.0, one transmitted reading (`qamus/data/current/NOTICE.md:1-19`); token addressing `S:A:W` (`qamus/indexes/quran-loc-surface/index.jsonl`); ayah spine with per-token gloss state (`qamus/indexes/current/quran-usage-spine-full.jsonl`); source-address graph `qamus:<entry_id>[#field=…]` with 28,392 addresses (`qamus/indexes/current/source-address-full.meta.json`).

## 2. Adapter contract (design)

### 2.1 Namespace

Each corpus gets a registered namespace prefix used in every ref, source-address node, and `source_scope`: `nawawi40:` (existing), proposed `bukhari:` / `muslim:` (or a joint `sahihayn:` only if the owner rules the two texts share an identity scheme — default: separate). Namespaces are registered in the canonical source ledger `sources/source-artifact-ledger.json`; later work "must not create a competing source ledger" (`docs/parser/source-ledger-and-split-policy.md:3-5`). Note: the existing "VN namespace" vocabulary (plan-table vs partition vs staging, `docs/superpowers/specs/2026-07-17-vn-readiness-v2-design.md:7-60`) is ledger scoping, not corpus prefixing; the adapter must not overload it.

### 2.2 Source-address format

- Ref level: `<ns>:<work-local id>` — for ḥadīth: book/chapter/ḥadīth numbering of the NAMED edition (`corpora/sahihayn/PLAN.md:48`).
- Token level (GAP-C1, net-new): `<ns>:<ref>:<token_idx>` following the existing `corpus:<ref>:<idx>` node convention (`qamus/reports/corpus-to-qamus-pipeline.md:17`). Token indexes are matn-local (isnād excluded, §2.4) and stable only relative to the pinned edition + tokenizer version, both recorded in the corpus manifest.
- The canonical-loc rule generalizes: never trust an external word number by itself — match the Arabic surface in the unit, require uniqueness, and emit a source-address crosswalk when display-local and canonical addresses differ (`docs/parser/source-ledger-and-split-policy.md:50-54`).

### 2.3 Text identity and variants

- Pin ONE named edition per corpus (identity = edition + version + numbering scheme), recorded as `access_method` in every output record (`corpora/README.md:88-92`) and in `corpora/sources/SOURCE-CATALOGUE.md` (citation label, never a path/URL-to-gloss; licence column; `:7-28`).
- Variants: the Qurʾān corpus deliberately models a single transmitted reading; qirāʾāt exist only as external MCP evidence, never a stored corpus dimension. The adapter keeps the same posture for riwāyāt/manuscript variants: variant readings are evidence attached to a decision, not additional corpus rows (GAP-C2 — no variant/riwāya data model exists; any future variant modeling is a separate owner decision).
- Text fidelity: verbatim, read-only, never "corrected" (`corpora/README.md:25-45`; `corpora/sources/SOURCE-CATALOGUE.md:17-18`).

### 2.4 Tokenization and corpus-specific structure

The stage-1 reader (the only net-new code per corpus) must: accept the edition's numbering as `ref`; **split matn from isnād before tokenizing and drop the isnād**; normalize recurring transmission formulae so they don't flood the candidate set; record `access_method` (`corpora/sahihayn/PLAN.md:48-53`). Normalization uses only `tools/normalize_ar.py` (single source of truth; `norm_strict()` is the only key allowed to certify a match, `norm()` recall-only, `bare()` conservative clitic peel — `corpora/README.md:96-127`).

### 2.5 Provenance

Every candidate row carries the existing split: source-clean `public_record`/`public_provenance` (`{src:qamus, kind:authored, lang:en}`) vs `internal_provenance.informed_by` (`qamus/candidates/qamus_2092/hover_batch_004_b2.provenance.jsonl:1`; label policy `provenance/source-boundaries.md:47-56`). Sources absent from the per-source boundary table are "may not consult for publication" until added with an explicit role (`provenance/source-boundaries.md:21-22`); the current table already scopes sunnah.com to reference confirmation only and excludes ḥadīth from the public hover artifact (`:11-19`). Generated artifacts carry the freshness header `generated_at/generated_by/source_head/source_branch/supersedes/stale_after/status` (`docs/parser/source-ledger-and-split-policy.md:9-17`).

### 2.6 Candidate generation via the Qurʾān-stabilized machinery

Reuse unchanged: `diff_against_qamus.py` + `make_candidate_payloads.py` (`corpora/sahihayn/PLAN.md:37-53`); the batch-JSONL + `.provenance.jsonl` sidecar + `.report.md` convention of `qamus/candidates/`; the sarf/nahw decision skills and their gate ladder; the two-vote SSOT; homograph splits preserved and routed to two-vote, never auto-glossed (`qamus/reports/corpus-to-qamus-pipeline.md:41-45`); the dependency-lattice `input_mode: corpus_backed` with its `two_vote_required` floor (`tools/fusha_text_check.py:5-8`; `qamus/schemas/dependency-candidate-lattice.schema.json:46`).

### 2.7 Corpus-specific facts

New fact rows a later corpus may add: attestation facts (this lexeme/form occurs at `<ns>:<ref>:<idx>`), frequency-in-corpus, corpus-local sense candidates (two-vote gated, `source_scope`-tagged), and new-entry proposals (the Nawawī40 bucket taxonomy). These are additive to the entry/lexeme plane; they never edit Qurʾānic occurrence records. Qurʾānic occurrence syntax/meaning facts are excluded from transfer in both directions (§0.3).

### 2.8 Evidence policy

Per-fact `evidence_mode` follows the (proposed) certification authority — closed enum, per-mode minimum bundles, `unresolved` may never be certified (`docs/certification-authority.md:39-51`); the three orthogonal fanout gates apply per corpus occurrence (`source_address_exact` / `lemma_pattern_pos` two-vote / `function_context` two-vote-or-scholar; particles never fan out via `lemma_pattern_pos` — `docs/certification-policy.md:23-32`); the five forbidden patterns (surface-only certification, component-evidence-certifying-whole-token, sarf/nahw-disagreement fanout, right-gloss-wrong-reason, provenance leakage) each remain validator FAILs (`:34-49`).

### 2.9 Licensing and boundary review (pre-ingestion gates)

Ordered gate list a new corpus passes BEFORE any stage-1 run:
1. Source-catalogue entry with licence note (`corpora/sources/SOURCE-CATALOGUE.md`).
2. Provenance-boundary table row with explicit role (`provenance/source-boundaries.md`).
3. Licensing adjudication: the repo inherits open item D-01 (interim wording D-12; overlap-not-copying doctrine, `qamus/data/current/NOTICE.md:24-40`; `docs/CLAIMS-AND-RELEASES.md:58`) — a new corpus must not widen this exposure (GAP-C4).
4. Source-selection decision record (`docs/source-selection-policy.md`, enforced by `tools/validate_source_selection.py`; the L15 lesson applies: majority class-signature, never segment-count maximization, `:23-58`).
5. Owner gate (explicit, recorded; `hadith-owner-gate-readiness.md`).
6. Leak detectors extended with the new corpus's private source names (`tools/leak_sot.py`, `tools/validate_public_private_boundary.py`).

### 2.10 Reverse trace

Every projected row must close the same reverse chain the Qurʾān corpus closes: projection → facts → events → two-vote → votes → evidence → entry/card/source (`PROOFN-MANIFEST.json:268`; worked machine artifact `qamus/examples/p007-li-pilot/reverse-trace.json`; general rule "Rows that lack a forward and reverse path must not be silently projected", `docs/parser/fusha-cli-contract.md:109-110`). Corpus rows lacking either direction are repair packets, not closure (`qamus/procedures/largelexicon-rollout-consumption.md:95-100`).

### 2.11 Projection

Corpus-backed hovers/drills project through the same candidate-only projector registries (`qamus/lattice/registered-projectors.json` gate authority; `tools/fact_projectors.py` abstention-first contract) and the same completeness/normalization validators (`tools/validate_segment_completeness.py`, `tools/check_rich_hover_norm.py`). Public boundary unchanged: `{src:qamus, kind:authored, lang:en}`, no edition prose, no external labels. Note the canonical hover machinery is currently hard-wired to `quran_loc`/`wbw_loc`/`exact_transclusion_group_key = quran:S:A:W|…` (`docs/parser/canonical-hover-payload-table.md:40-62`) — the principal implementation gap (GAP-C1).

### 2.12 Dogfood return

Corpus reading feeds back through the existing dogfood event ledger (`qamus/schemas/dogfood-event-ledger.schema.json`) and the curriculum return edge (reading paths already staged: `curriculum/hadith-reading-path.md` — which itself reproduces no ḥadīth text, `:8-16`; drills `curriculum/drills/nawawi40-reading-drills.md`; ladder rungs 10–12, `curriculum/README.md:47-49`). Defects found while reading a later corpus become typed events routed to sarf/nahw/Qamus exactly as VN dogfood does today.

## 3. GAPs (with work-packet stubs)

- **GAP-C1 — no token-level addressing or canonical-payload support for non-Qurʾān corpora.** The Ṣaḥīḥayn plan specifies only `ref`; there is no `<ns>:<ref>:<idx>` loc→surface index analogue and the hover/occurrence-binding machinery is hard-wired to `quran:`/`wbw:` keys. WP-CORPUS-TOKEN-ADDRESSING: extend the occurrence-binding schema with a namespaced `corpus_loc` and a per-corpus loc→surface index, without touching Qurʾān semantics.
- **GAP-C2 — no variant/riwāya model** (and none for qirāʾāt either, by design). WP-CORPUS-VARIANT-POLICY: owner decision memo on whether variants stay evidence-only.
- **GAP-C3 — no isnād model.** Isnād is dropped at tokenization by design; if isnād vocabulary is ever wanted for teaching, it is a separate corpus decision. WP-CORPUS-ISNAD-DECISION.
- **GAP-C4 — licensing posture open** (D-01/D-12 unresolved; hadith edition rights unadjudicated). WP-CORPUS-LICENSING-REVIEW.
- **GAP-C5 — Ṣaḥīḥayn prerequisites unmet**: Nawawī40 candidate human review + measured diff-classifier false-positive rate not yet done (`corpora/sahihayn/PLAN.md:13-19`); 720 new-entry candidates and 789 review-queue rows await review. WP-CORPUS-NAWAWI40-REVIEW.
- **GAP-C6 — no cross-corpus experiment run** (flywheel hypotheses H1–H7 untested, `docs/QURANIC-ANCHOR-AND-FLYWHEEL.md:109-136`); the claim that Qurʾān-stabilized machinery lowers later-corpus cost is a TESTABLE HYPOTHESIS, not an observed result. WP-CORPUS-H1-EXPERIMENT: measure candidate acceptance/abstention rates on a reviewed Nawawī40 slice against the Qurʾān baseline.
- **GAP-C7 — certification authority still `proposed`** (`docs/certification-authority.md:3`); §2.8 rests partly on an unadopted policy. WP-CERT-AUTHORITY-ADOPT.
