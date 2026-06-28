# RICH-CERT Flywheel Synthesis - 2026-06-27

Status: repo-only flywheel checkpoint after completing `VN-RICH-CERT-20`. This report does not mutate live Qamus,
rebuild WBW, restart services, sync mirrors, mutate the hover ledger, or claim live rich-hover coverage.

## Inputs Audited

- P-RICH-CERT certification reports: 4.
- VN-RICH-CERT reports: calibration plus 20 standard tranches.
- Certification JSONL samples: 25 files / 414 rows.
- Evidence sidecars: 25 files.
- Renderer fixtures: 25 files.
- Previous curriculum surfaces:
  - `curriculum/drills/dogfood-error-remediation-index.md`
  - `curriculum/drills/parse-key-and-color-layer.md`
  - `curriculum/assessment/grading-rubric.md`
  - `curriculum/progress/missed-error-log.template.md`
  - `sarf/drills/dogfood-sarf-remediation.md`
  - `nahw/drills/dogfood-nahw-remediation.md`

## Certification State Summary

| state | rows | meaning |
|---|---:|---|
| `token_only_override` | 180 | exact-address review candidate; no family propagation |
| `pending` | 147 | blocker or required gate remains |
| `preview_only` | 85 | rich segment/display metadata is useful but not certification |
| `blocked` | 2 | explicit non-certification row |

No row is live-applyable and no row is public rich-hover coverage. `parse_key` remains a grammar-family key, not
identity. Identity remains exact `quran:S:A:W` plus `wbw:S:A:W`.

## Repeated Teaching Opportunities

| repeated class | examples | durable action |
|---|---|---|
| preview metadata mistaken for certification | `preview_only` noun/verb rows across VN15-VN20 | added `rich_cert_preview_overclaim` to remediation/progress/rubric surfaces |
| pending/two-vote row cleared from readable English | `لِمَا`, `فَأَهْلَكْنَاهُمْ`, `وَٱلشَّجَرُ` | added `rich_cert_pending_gate` to remediation/progress/rubric surfaces |
| component-only evidence used as whole-token proof | prefixed verbs and conjunction/article/host rows | reinforced sarf/nahw RICH-CERT gate drills |
| renderer/admin preview confused with public rollout | all renderer fixtures | added `rh_live_preview_only` to remediation/progress/rubric surfaces |
| suffix or object pronoun must remain visible | `يَسْأَلُكَ`, suffix-bearing verbs/nouns | reinforced sarf drill pass bar |
| function/attachment/case remains hidden state | `وَمَا`, `لِمَا`, `إِلَّا`, `بِبَدْرٍ` | reinforced nahw drill pass bar |

## Flywheel Compliance Audit

All 25 RICH-CERT reports now contain a `## Flywheel Impact` section covering:

- sarf updates made, or explicit no-op reason;
- nahw updates made, or explicit no-op reason;
- curriculum updates made, or explicit no-op reason;
- assessment/checkpoint updates made, or explicit no-op reason;
- progress/missed-error categories added, or explicit no-op reason;
- drills/evals/regressions added, or explicit no-op reason;
- production-bug lessons added, or explicit no-op reason;
- renderer requirements added, or explicit no-op reason;
- future tranche-routing implications.

Backfilled reports:

- `p-rich-cert-01-particle-function-20260627.md`
- `p-rich-cert-02-particle-collision-20260627.md`
- `p-rich-cert-03-an-inna-family-20260627.md`
- `p-rich-cert-04-la-temporal-family-20260627.md`
- `vn-rich-cert-00-calibration-20260627.md`
- `vn-rich-cert-01-standard-20260627.md`
- `vn-rich-cert-02-standard-20260627.md`
- `vn-rich-cert-03-standard-20260627.md`
- `vn-rich-cert-04-standard-20260627.md`
- `vn-rich-cert-05-standard-20260627.md`
- `vn-rich-cert-06-standard-20260627.md`

Later reports already had complete flywheel coverage; only label normalization or already-complete wording was needed
for `VN-RICH-CERT-19` and `VN-RICH-CERT-20`.

## Durable Repo Promotions

| surface | update |
|---|---|
| `curriculum/drills/dogfood-error-remediation-index.md` | added RICH-CERT preview, pending gate, and RH-LIVE preview-only remediation rows |
| `curriculum/progress/missed-error-log.template.md` | added missed-error categories for RICH-CERT preview and pending-gate overclaims |
| `curriculum/assessment/grading-rubric.md` | added rich-certification item rubric and rejects preview-only certification |
| `curriculum/drills/parse-key-and-color-layer.md` | added RICH-CERT state drill |
| `sarf/drills/dogfood-sarf-remediation.md` | added RICH-CERT morphology gate drill |
| `nahw/drills/dogfood-nahw-remediation.md` | added RICH-CERT nahw gate drill |

No new sarf or nahw procedure file was needed: the repeated findings reuse existing finite-verb, suffix-pronoun,
article/host, component-only, particle-function, preposition/governor, case/i'rab, PP attachment, and token-only gates.
The durable change belongs in drills, assessment, and progress state because the gap was a tutoring/certification-state
overclaim risk, not a new grammar doctrine.

## Explicit No-Op Reasons

| area | no-op reason |
|---|---|
| sarf procedures | no new morphology class appeared; the problem was distinguishing pending/preview/token-only from certification |
| nahw procedures | no new syntax/function doctrine appeared; existing gates already require two-vote for the affected rows |
| production-bug lessons | existing lessons already cover suffix omission, function flattening, component-only traps, and readable-English wrong reasoning |
| validator code | existing rich-cert, morphosyntax, assessment, and regression validators can enforce the checkpoint artifacts |
| live renderer | not owner-authorized; renderer work remains RH-LIVE preview/admin only |

## RH-LIVE-00 Preview Shortlist

These rows are good admin/renderer preview candidates because they exercise visible composition while staying
non-live/non-public until owner gates are opened.

| loc | surface | source fixture | preview reason | required gate |
|---|---|---|---|---|
| `33:63:1` | `يَسْأَلُكَ` | `rich_cert_vn_rich_cert_00_renderer_fixture.sample.jsonl` | verb prefix + stem + object suffix exemplar | exact-address two-vote and owner authorization |
| `26:139:2` | `فَأَهْلَكْنَاهُمْ` | `rich_cert_vn_rich_cert_03_standard.sample.jsonl` / `rich_cert_vn_rich_cert_11_standard.sample.jsonl` | fā' + Form IV perfect + subject/object pronouns | component-only blocker resolution |
| `22:18:13` | `وَٱلشَّمْسُ` | `rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl` | conjunction + article + host noun | component-only blocker resolution |
| `22:18:14` | `وَٱلْقَمَرُ` | `rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl` | conjunction + article + host noun | component-only blocker resolution |
| `22:18:15` | `وَٱلنُّجُومُ` | `rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl` | conjunction + article + host noun | component-only blocker resolution |
| `22:18:16` | `وَٱلْجِبَالُ` | `rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl` | conjunction + article + host noun | component-only blocker resolution |
| `22:18:17` | `وَٱلشَّجَرُ` | `rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl` | conjunction + article + host noun | component-only blocker resolution |
| `3:123:4` | `بِبَدْرٍ` | `rich_cert_vn_rich_cert_20_renderer_fixture.sample.jsonl` | bā' + place-name host | token-only two-vote and owner authorization |
| `2:213:37` | `لِمَا` | `rich_cert_vn_rich_cert_09_standard.sample.jsonl` | lām + `ما` function/attachment example | `ما` function and attachment review |

## RH-LIVE-00 Renderer/Admin Preview Plan

Allowed shape, if owner-authorized later:

1. Build an admin-only preview route or offline HTML fixture that reads the committed renderer fixtures.
2. Keep `live_renderer_claim=false` and display a visible "preview only / not live apply" banner.
3. Render Arabic tokens atomically; segment colors may not introduce spaces, gaps, flex children, or fake word breaks.
4. Show the public preview payload separately from internal evidence.
5. Keep public payload fields source-clean: `src=qamus`, `kind=authored`, `lang=en`.
6. Scan preview DOM/API output for internal labels, source names, MCP/QAC/Quran.com labels, OCR snippets, and local paths.
7. Require screenshots and DOM text invariants for `33:63:1`, `22:18:13-17`, and `3:123:4`.

Forbidden in RH-LIVE-00 without a separate owner apply plan:

- live WBW rebuild;
- service restart;
- hover decision ledger mutation;
- public rich-hover rollout;
- family propagation from parse key;
- treating renderer fixture data as certification.

## Next Gate

RICH-CERT through VN20 is complete as repo-only certification queue work. The next safe lane is either:

- owner-authorized RH-LIVE-00 admin/renderer preview scaffolding using the shortlist above; or
- further curriculum/assessment hardening using the promoted error categories.

Do not proceed to broad public rich-hover rollout or hover application from this report.
