# Dependent-Impact Report — ṣarf@2 / naḥw@2 skill-release candidate

Scope of this report: what depends on the ṣarf/naḥw skills, and what this release changes
for each dependent. Produced for the release gate (impact must be understood before merge).

## What this release actually changes

This release is **skill documentation + registry + test infrastructure only**. It ships:

- a versioned skill-rule registry (`skills/registry/skill-rule-registry.json`, 107 rules:
  100 `accepted`, 7 `candidate`) with a fail-closed validator;
- a permanent red-first fixture set (`tools/skill_fixtures/`, 36 fixtures) and its harness;
- a drift sentinel (`tools/check_skill_drift.py`, 10 classes) + deterministic mirror
  generation (`tools/generate_skill_mirrors.py`) and the repo-relative mirror map;
- 9 **candidate** rich-segmentation rules (`qamus/skills/rule-registry-richseg.jsonl`) with
  their own fixtures.

It does **not** change any runtime code path, gloss output, renderer, or published data.
No `accepted` rule's *text* changed; the 15 previously-untested accepted rules gained a
`permanent_tests` pointer only. Candidate `@2` rules are DRAFT and do not bind any consumer
until an owner adjudicates `candidate → accepted`.

## Dependents and impact

| Dependent | Relationship | Impact of this release |
|---|---|---|
| `sarf/SKILL.md`, `nahw/SKILL.md` (authoritative skills) | Source of truth the registry indexes | None to text. Now each normative rule is indexed + tested; edits are drift-checked. |
| `skills/registry/skill-rule-registry.json` | Machine index of the skills | Extended: `permanent_tests` set on 15 rows. Validates with 0 errors, no dup ids, no dangling. |
| `skills/registry/skill-mirror-map.json` | Pins skill/mirror/install hashes | Two `local_codex_install` observed hashes regenerated to canonical (stale-debt cleared). Map is regenerated, not hand-edited. |
| Local skill installs (Claude-Code / claude.ai pack / Codex) | Generated mirrors of the skills | The two stale installs are brought to canonical by deterministic regeneration; future staleness is caught by `dc_stale_installs`. |
| `tools/check_regressions.py` (full harness) | Release gate | Adds the four skill-release gate blocks (8/9/10/11). Total checks rise; all green. |
| 29 rules carrying a projector/reviewer consumer | Downstream reviewers that pin a skill commit | No change: `dc_projector_stale` is green; no consumer pins a stale commit. |
| 85 rules carrying a code-implementation citation | Engine code referenced by the rule | No code changed. Citations continue to resolve; `dc_implemented_without_skill` green. |
| Qamus rich-hover / word-by-word authoring (per-occurrence gloss decisions) | Human + tooling consumers of sarf/nahw decisions | No behavioural change. The accepted rules they already follow are now regression-protected; the candidate rich-seg rules are guidance-in-waiting, not yet binding. |

## Risk assessment

- **Regression risk: low.** All added tests are deterministic, offline, stdlib-only, and
  fail closed. No production data, network, or live service is touched.
- **Semantic risk: none introduced.** Every fixture asserts an *existing* documented rule's
  boundary; the corrected label matches current guidance and the superseded label is the
  historical defect it already replaced.
- **Adoption risk: contained.** Candidate `@2` rules stay `candidate` until owner
  adjudication; nothing auto-promotes them.

## Rollback

Revert the `skill-integration-v2` merge (or drop the individual feature-branch merges).
Because the release adds files and one `permanent_tests`/mirror-hash delta rather than
changing behaviour, rollback is a clean revert with no data migration.
