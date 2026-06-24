# Token-iʿrāb polysemy resolution (B3)

Surface keys (`norm_strict`, drops harakāt) cannot separate same-surface polysemy. This lane resolves
it **per loc by iʿrāb** — the token-addressed layer's exact purpose — with a sarf+nahw 2-vote and
Tafsir-MCP iʿrāb as internal evidence.

## Result

- **300 polysemy decision-requests** generated (`tools/build_token_irab_decisions.py`), spanning **27
  keys**: function words (وما, ألا, فما, لمّا, أمّ, أنّي…) + content homographs (عاد, ملك, ذكر, ذهب,
  أذن, جنّة, البر, أمر, أمة, يحيى…).
- **2-vote resolution** (`token-irab-verify` workflow, 50 sarf/nahw verifiers): **188 applied / 112
  rejected** (rejections = both agreed-pending, or iʿrāb-ambiguous / phrase-level — never a guess).
- Applied → live **82.29%** (40,875 → 41,063, **−0 removed, −0 changed**, 0 wrong).

## Worked resolutions (per-loc iʿrāb, the engine in action)

| surface | key | locs → context-correct gloss | skill |
|---|---|---|---|
| وَمَا | وما | 3:7:27 "and not" (نافية) · 30:39 "and whatever" (relative) | nahw `negation`/`relative-interrogative` |
| أَلَّا / ألَا | الا | 4:3 "that … not" (أن+لا) · 39:3 "indeed" (istiftāḥ) · 51:27 "will you not" | nahw `particle-decision` |
| فَمَا | فما | 7:39 "so not" · 4:24 "so whatever" | nahw `negation` |
| عَادَ / عَادٍ | عاد | 36:39 "returned" (verb) · 2:173 "transgressor" (ism fāʿil from عدا — **not** the tribe) | sarf `homograph-risk` + MCP iʿrāb |
| جِنَّة | جنه | 2:266 "a garden" · 7:184 "madness" | sarf `homograph-risk` |
| ذِكْر / ذَكَر | ذكر | "remembrance/reminder/is mentioned" vs "male" | sarf root + nahw context |
| ذَهَب | ذهب | 43:71 "gold" (noun) | sarf POS |
| أَذِنَ / أُذُن | اذن | 78:38 "permitted" (verb) · 9:61 "an ear" (noun) | sarf POS + nahw |
| يَحْيَىٰ | يحيي | "Yaḥyā (John)" (proper noun) vs "gives life to" (verb) | nahw `referent-context` |
| أُمَّة | أمه | "a community" · 16:120 "a model of excellence" | nahw context |

## Tafsir-MCP triangulation (E0, internal only)

6 locs were enriched with authoritative MCP iʿrāb (وما 3:7 = حرف نفي; عاد 2:173 = اسم فاعل من عدا;
أذن 78:38; ذهب 43:71; ألا 17:23 = أن+لا; فما 7:39). Cached source-hashed under the **gitignored**
`sources/tafsir_mcp/cache/` (one redacted example committed); each MCP-backed decision records
`internal_provenance.mcp_used=true`. Public records stay `{src:qamus,kind:authored}` (0 leaks,
`validate_token_irab_decisions.py`).

## Remaining

`same_surface_polysemy_requires_i3rab` dropped 550 → **520**. Remaining = the harder وما/لمّا locs the
2-vote kept pending (genuinely ambiguous or phrase-level) + lower-frequency content homographs — each
exact-blocked with `next_action` in `hover-token-audit-full.jsonl`. Re-run the harness for the next tier.
