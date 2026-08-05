# VN Operations — tranche completion playbook

The reusable, tested method that took Qamus **VN-00, VN-01, and VN-02 to 100% rich-hover**, all three
frozen by regression gates. Port it forward for every future VN tranche; do not rediscover it.

## 0. What "rich-hover complete" means
Every rendered Qurʾān word span on the tranche's pages is one of: rich-hover (`qword qg-colored`
+ `data-rh-live`), proven-not-visible, or covered by an **exact durable packet** (scholar/iʿrāb,
source-crosswalk, owner-decision, or impossible-with-exact-missing-evidence). Flat `data-tr` only,
plain `qword`, `qw-pending`, "authoring-needed", "needs-sarf/nahw" are **not** completion.

## 1. Authoritative window map (NOT a created_at proxy)
The qamus app routes `/vNNN /nNNNN /pNNN` by each entry's own `source_key`
(`entry_primary_source_key`). Rebuild `{page → entry_id}` straight from `source_key`
(`vn_window_map.py`): 2,092 entries =
947 v +
1,045 n +
100 p, contiguous,
0 gaps/dups. A VN tranche is a page range on this ordering.

**Owner respec — 2026-08-05 (supersedes the repeated 47/45 blocks):** VN-00 stays irregular,
`v001-v047 + n0001-n0045`; the remainder (900 v + 1,000 n) splits **evenly** across
**VN-01..VN-20** as **45 verb + 50 noun pages per tranche** (so VN-01 = `v048-v092 + n0046-n0095`,
VN-20 = `v903-v947 + n0996-n1045`; 21 tranches total, no VN-21+). Span-verification history is
per page and was recorded under the pre-respec windows (old VN-00..02 = `v001-v141 + n0001-n0135`);
pages keep that state under renumbering, so a respec tranche may honestly mix states.
`tools/build_pvn_rollout_map.py` encodes this rule and self-tests the boundaries.

## 2. Live matrix = the completion denominator
`vn_matrix_build.py <WINDOW> "<ranges>"` curls every `/vNNN?wbw_preview=1`, counts qword spans,
classifies rich / flat / pending, and dispositions every not-yet-rich row. The **visible rendered
span** is the denominator — never a hardcoded count. Rebuild after every deploy.

## 3. Wave taxonomy (apply in yield order; each per-row correctness-gated + purely additive)
1. **Seed class-transclusion** — single-segment surfaces with invariant class AND gloss.
2. **Auto-seed** — surfaces whose live class-signature is ≥92% dominant, single-segment, gloss-invariant.
3. **Multi-seg transclusion** — article+stem, prep+pronoun, noun+possessive, verb+pronoun. Pure
   flat→rich: keep the flat gloss as token gloss; only ADD the vetted colored segmentation.
4. **Cross-proof transclusion** — content words with an exact-surface rich twin: transclude the twin's
   inflected gloss + segments; never copy its context-specific learner.
5. **Class-invariant function words** — single dominant class regardless of function nuance (لا/ولا/فلا).
6. **Clean mis-bucketed verbs** — plural perfects routed to scholar only by the segment fallback minority.
7. **Per-occurrence 2-vote** (contested homographs) — never majority-voted; deploy agreed, packet disagreed.

## 4. Deploy protocol (`vn00_deploy.py`, fail-closed)
prevalidate (per-row) → stop rebuild timer → merge (live validator, count-check, `--allow-append`) →
backup src+runtime → replace source → `deploy_runtime.sh` → restart qamus → health 200 → src/runtime
sha parity → canary-wait → per-appended-loc readback rich → control-row liveness → public-payload leak
scan → commit whitelist (explicit path) → restart timer. Rollback = `.bak-<tag>`.

## 5. Hard guards (each an ANDON lesson)
- COLORED_QG allowlist: a class outside it validates but renders colorless (not actually rich).
- Segment concat must equal the token surface byte-exact.
- Dedup packet by `loc` (a word on >1 page is one whitelist key).
- Never seed a genuine homograph (min/man, ما, ان, الا, اذا, من/ومن) — 2-vote instead.
- Never blind-transclude oath-ambiguous و-forms (والله).
- Skip infinitive-leakage flat glosses on inflected verbs — author the inflected gloss.
- Public payload source-clean: evidence in sidecars only.

## 6. Completed tranches (done + frozen — `docs/STATUS.md`)
- **VN-00, VN-01, VN-02 — 100% rich-hover, frozen** by `smoke-vn00/01/02-regression.sh`.
- Run both/all completed gates before claiming any later tranche done; never let a new worklist
  regress a frozen one.

## T3. Future tranches (VN-03 and later — NORMATIVE-FUTURE, not accomplished)
VN-03 is **measured but NOT started** (`docs/STATUS.md`). No
VN-02→full-Qamus rollout is claimed. When a future tranche is authorized, it **MUST**:
- rebuild its own window map + live matrix denominator (§1–§2) before any deploy;
- apply the wave taxonomy in yield order (§3), each wave per-row correctness-gated and additive;
- pass the fail-closed deploy protocol (§4) and every hard guard (§5);
- ship its own `smoke-vnNN-regression.sh` freeze and pass all prior frozen gates;
- keep the public payload source-clean and measure light+dark × desktop+mobile contrast before any
  colour/legend change.

This section is a specification of required future work, not a record of completed work.

## 7. ANDON lessons (carry forward)
Leak-scanner word-boundary matching for acronym labels; extend diacritic-strip to U+06D6..06ED;
keep the flat gloss as token on multi-seg verbs; dedup analysis by `loc`; test the canonical question
directly before packeting a `source_crosswalk` row; run heavy Workflows SEQUENTIALLY and harvest
author/vote rows from transcripts so throttling never wastes completed work. D7 colour-legend: use the
real theme tokens, measure computed contrast (≥4.5) in light AND dark — never eyeball.
