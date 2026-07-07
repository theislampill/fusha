# VN-00 → VN-20 tranche completion playbook

The reusable, tested method that took Qamus **VN-00 to 100%** rich-hover and is now driving VN-01.
Port it forward for every VN tranche; do not rediscover it. (Companion to `nahw/procedures/hover-application.md`
and `function-token-hover-review.md`.)

## 0. What "rich-hover complete" means
Every rendered Qurʾān word span on the tranche's pages is one of: rich-hover (`qword qg-colored`
+ `data-rh-live="01"`), proven-not-visible, or covered by an **exact durable packet** (scholar/iʿrāb,
source-crosswalk, owner-decision, or impossible-with-exact-missing-evidence). Flat `data-tr` only,
plain `qword`, `qw-pending`, "authoring-needed", "needs-sarf/nahw" are **not** completion.

## 1. Authoritative window map (NOT a created_at proxy)
The qamus app routes `/vNNN /nNNNN /pNNN` by each entry's own `source_key`
(`entry_primary_source_key`). Rebuild `{page → entry_id}` straight from `source_key`
(`vn_window_map.py`): 2092 entries = 947 v + 1045 n + 100 p, contiguous, 0 gaps/dups. A VN tranche is
a page range on this ordering. VN-00 = `v001-v047 + n0001-n0045`; VN-01 = `v048-v094 + n0046-n0090`
(mirror VN-00's shape; owner may override the boundary — the ordering itself is authoritative).

## 2. Live matrix = the completion denominator
`vn_matrix_build.py <WINDOW> "<ranges>"` curls every `/vNNN?wbw_preview=1`, counts qword spans,
classifies rich / flat / pending, and dispositions every not-yet-rich row (deploy_ready_authorable /
scholar_iurab / source_crosswalk / owner_decision / impossible). The **visible rendered span** is the
denominator — never a hardcoded count. Rebuild after every deploy; never let a stale worklist regress.

## 3. Wave taxonomy (apply in yield order; each is per-row correctness-gated + purely additive)
1. **Seed class-transclusion** (`vn_seed_transclude.py`) — single-segment surfaces with an invariant
   class AND invariant gloss (proper nouns, single-class particles): الله→proper-noun, أو→alternative.
2. **Auto-seed** (`vn_auto_seed.py`) — data-driven: any surface whose live whitelist class-signature is
   ≥92% dominant, single-segment, and gloss-invariant across all its occurrences.
3. **Multi-seg transclusion** (`vn_multiseg_transclude.py`) — article+noun-stem, prep+pronoun,
   noun+possessive, verb+pronoun. **Pure flat→rich**: keep the existing flat `data-tr` gloss as the
   token gloss (text-neutral, zero risk of a wrong meaning) and only ADD the vetted colored
   segmentation, re-carved byte-exact by base-letter resplit.
4. **Cross-proof transclusion** (`vn_crossproof_transclude.py`) — content words with an **exact-surface**
   rich twin elsewhere: transclude the twin's inflected gloss + segments (exact surface ⇒ same
   inflection ⇒ gloss transfers). Never copy the twin's context-specific learner (Moses trap) — generate
   a generic one.
5. **Class-invariant function words** — verified single dominant class regardless of function nuance:
   لا/ولا/فلا (qg-negation is invariant across nafiya/nahiya).
6. **Clean mis-bucketed verbs** — plural perfects (قالوا/كفروا/كانوا/ءامنوا) routed to scholar only by
   the qg-segment fallback minority; deploy with an authored inflected gloss.
7. **Per-occurrence 2-vote** (contested homographs) — never majority-voted; deploy agreed, packet disagreed.

## 4. Deploy protocol (`vn00_deploy.py`, Lane-8, fail-closed)
prevalidate (per-row `_validate_row` so 1 bad row ≠ batch abort) → stop rebuild timer → merge (live
validator, count-check, `--allow-append`) → backup src+runtime → replace source → `deploy_runtime.sh`
→ restart qamus → health 200 → src/runtime sha parity → **canary-wait** (poll a new loc until rich,
absorbs restart-overlap) → per-appended-loc readback rich → control-row 33:63:1 liveness → public-payload
leak scan → commit whitelist (explicit path) → restart timer. Rollback = `.bak-<tag>`.

## 5. Hard guards (each an ANDON lesson — see §6)
- COLORED_QG allowlist: a class outside it validates but renders colorless (not actually rich).
- Segment concat must equal the token surface byte-exact (resplit by base-letter count fixes mark reorder).
- Dedup packet by `loc` (a word rendering on >1 page is still one whitelist key).
- Never seed a genuine homograph (min/man, ما, ان, الا, اذا, من/ومن); those go to per-occurrence 2-vote.
- Never blind-transclude oath-ambiguous و-forms (والله = wāw al-qasam vs al-ʿaṭf).
- Skip infinitive-leakage flat glosses on inflected verbs ("to say" on قالوا) — author the inflected gloss.
- Public payload source-clean: evidence in sidecars only; no source/tool/process labels in gloss/learner.

## 6. Session ANDON lessons (VN-01, 2026-07-06)
| ANDON | Root cause | Countermeasure (poka-yoke) |
|---|---|---|
| Leak scanner blocked "hypocrites" | acronym labels (mcp/qac/ocr) matched as **substrings** | match those 3 on **word boundaries** (`\bocr\b`); phrases/paths stay substring. Fixed `_validate_row` + `render._public_json_attr` + the deploy tool's scan. |
| Wave F matched 0 rows | `norm()` didn't strip Qurʾānic annotation marks (U+06D6..06ED, e.g. ۟) so قالوا۟ ≠ قالوا | extend the diacritic-strip range to U+06D6..06ED in every normalizer |
| Garbage token gloss on multi-seg verbs | template `gloss_contribution` on affixes is a **morphology note**, not a gloss | for flat→rich, keep the existing flat gloss as token; use segment glosses only for the breakdown |
| Duplicate-loc merge refusal | worklist is per (loc,page); a shared āyah word appears on >1 page | dedup analysis by `loc` before assemble |
| 1,627 "source_crosswalk" = false gate | the `loc_attaches` heuristic (ayah ∈ entry examples) ≠ "is display loc canonical" | test the canonical question directly (loc ∈ wbw-lookup w/ matching surface); most "crosswalk" rows are deployable |
| Two 200-agent Workflows concurrently → API throttle/session-limit | shared 16-cap × 2 = overload | run heavy Workflows SEQUENTIALLY; resume-until-converged (cached agents skip) |
| Throttling killed the critic/vote-B stage, not the authors | author StructuredOutput was saved in transcripts | **harvest author/vote rows from the workflow transcripts** (`harvest_author_rows.py` / `harvest_scholar_2vote.py`) and deploy through the deterministic gates — throttling never wastes completed work |

## 7b. Run #32 ANDON lessons (deploy-mechanics that were mistaken for hard gates)
| symptom | root cause | fix |
|---|---|---|
| owner/impossible rows refuse assembly (`no surface in wbw-lookup`) | the loc is **absent from wbw-lookup** (canonical Tanzil map) even though it renders on the page | build a `loc → rendered-surface` **surfacemap** from the live worklist and pass `--surfacemap` to resplit+assemble |
| authored/agreed rows fail byte-exact concat and never deploy | agent single-segment surface differs byte-wise from wbw | **drop the agent surface on single-segment rows** → assemble fills it byte-exact from wbw/surfacemap |
| "impossible" bucket | classifier said "no Qamus sense" | almost never truly impossible — MCP `analyze_word` + āyah context author a conservative gloss (وكأسا/زمهريرا/سبعون/سلاسلا…); leave impossible only if the exact evidence is still missing |
| "owner sense selection" with placeholder options | packet lacked concrete senses | owner supplies the sense once; **seed it as ground truth** in the author prompt (`owner_gloss_hint` used verbatim) |
| 2-vote "disagreement" floor | granularity/label difference, not khilāf | **Tier-1**: identical token_gloss → deploy A; **Tier-2**: POS-family normalize; **Tier-3**: MCP tie-break; **Tier-4**: true packet only |
| "content not in harvest" / "engine exhausted" | rows fell out on concat/filter, not authoring | re-harvest transcripts + re-deploy the *covered-but-stuck* set with the surfacemap + single-seg fixes before declaring residual |

## 8. MCP-grounded per-occurrence authoring (the content/scholar engine)
Because every VN row's display loc **is canonical**, MCP `analyze_word(surah,ayah,word_no)` works directly:
- **content (non-homograph):** author→critic Workflow; author uses `irab`+`sarf` to pick qg class + fix the
  inflection (dictionary-infinitive → inflected gloss; passive vs active). Deterministic gates
  (COLORED_QG/concat/`_validate_row`/leak-scan) + a critic (or spot-check) gate the deploy.
- **homograph (scholar):** two INDEPENDENT MCP-verified parses; deploy only where the segment
  class-sequence agrees; disagreement → row-level packet preserving both readings. Never majority-vote.

## 7. Regression freeze
`smoke-vn00-regression.sh` asserts the completed tranche stays 100% (rebuilds the window map + matrix,
asserts rich==denominator/flat 0/pending 0, final-approved spans render rich with exact glosses,
source-clean). A twin `smoke-vn01-regression.sh` freezes VN-01 (14,052/14,052, every disposition 0,
92-route source-clean + parse-hash scan). Run both before claiming any later tranche done — never let a
new worklist regress a frozen one.

## 9. Public UX / readability ANDON (D7 colour-key, 2026-07-07)
The rich-hover reader teaches grammar through **colour + readable gloss**; a learner-facing surface that
is unreadable in the user's theme is a **non-functional teaching aid**, not a cosmetic nit. The D7 colour
legend rendered a white panel with near-white text in dark mode (measured **1.22 : 1**; AA needs ≥ 4.5).
| symptom | root cause | fix / poka-yoke |
|---|---|---|
| legend unreadable in dark | panel styled with token names that don't exist (`--du-surface`/`--du-border`) → hardcoded-white fallback in **both** modes while the text token was theme-aware (near-white in dark) | use the **real** theme tokens (surface/text/border/shadow); grep the live token file — never author from a remembered generic-kit name |
| colour swatches blank | grammar-colour vars were **out of scope** for the legend subtree | scope the legend into the same qg palette (incl. the light-mode override) so chips match running text per mode |
| "dark inspected" false pass | the screenshot was **not contrast-measured**; "renders" read as "readable" | a **computed-contrast smoke** (`smoke-d7-legend-contrast.js`) asserts title+label ≥ 4.5, panel≠page, swatch distinguishable, in light **and** dark, before any legend/colour deploy |
Rules: theme-aware tokens only; never a pale role-colour as **label text** (colour goes on a swatch/border/marker);
verify light+dark × desktop+mobile on every colour change; measure, don't eyeball; keep it source-clean (no
source/tool/process label, no parse-hash/debug id). Pedagogy: `curriculum/dark-mode-accessibility-pedagogy.md`,
`curriculum/visual-grammar-legend.md`.
