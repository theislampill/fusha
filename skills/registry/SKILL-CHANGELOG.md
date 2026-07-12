# Skill Changelog — ṣarf & naḥw

Versioned, evidence-backed record of what the sarf/nahw skill flywheel has learned and
how each lesson is now protected by an executable test. One entry per release. Newest first.

The skills themselves are the authoritative source (`sarf/SKILL.md`, `nahw/SKILL.md`); this
changelog is the human-readable narrative of the machine-checked registry
(`skills/registry/skill-rule-registry.json`) and its mirror map.

---

## ṣarf@2 / naḥw@2 — skill-release candidate

**Theme:** turn the skill corpus into a *versioned, drift-protected, test-backed* release.
Every normative rule now has a home in the registry, an executable boundary test, and a
deterministic mirror so a stale local install can never silently diverge.

### What the flywheel learned (and how it is now protected)

1. **A rule with no executable test is unprotected acceptance.**
   The 15 `accepted` rules that had `permanent_tests: MISSING` were the release's largest
   risk: they were correct guidance with nothing to stop a regression. Each now has a
   permanent **red-first** fixture (green on the corrected rule, red on the exact pre-fix
   behaviour it replaced), plus a `permanent_tests` pointer in the registry. Drift class 4
   (`dc_accepted_without_test`) now reports **0**. The boundaries encoded include:
   - *Blank beats wrong* — a `null` root/pattern/lemma is correct when none can be
     certified; never fabricate one from resemblance.
   - *Deploy mechanics gate content* — a correct morphological decision must not ship when
     the surface bytes do not match; the retry/bytes are part of the sarf author's job.
   - *Quarantine the whole inflection family* — a data-error quarantine matches on the
     stem, not one case ending (accusative quarantine also covers the nominative).
   - *Source-backed retry before "impossible"* — a row is almost never truly impossible;
     retry with a per-occurrence source-backed reading before emitting a blocked disposition.
   - *Token-right / entry-wrong* — emit a repair candidate with a source address; never
     mutate live data.
   - *Prefer pending with a precise reason over a guessed resolution* (sarf), and
     *prefer a phrase-aware pending over a wrong one-word gloss* (nahw).
   - *Resolve only when the construction uniquely fixes the sense* (nahw), and
     *resolve a layer-1-safe rule only with confirmed evidence* — an unvoweled ending keeps
     even a "safe" preposition-governs-genitive rule at a two-vote candidate.
   - *Record the clause relation* for relative pronouns, subordinating conjunctions, the
     purpose lām and temporal conditionals; *expose both* the relation and the attached
     pronoun for preposition/host+pronoun rows; give compound temporals
     (time-noun + attached "then") a real review instead of a bare "day" hover.

2. **A stale local install is a drift class, and its only fix is regeneration.**
   The two `local_codex_install` mirrors were regenerated deterministically from the
   authoritative SKILL.md sources so each observed hash equals its canonical regeneration
   (the tool's documented fix — never a hand-sync). Drift class 8 (`dc_stale_installs`)
   now reports **0**. Prior stale hashes are preserved in git history.

3. **Mirror paths must be logical, not machine-specific.**
   The mirror map was recut (RM-09) to hold repo-relative logical identities only — no
   absolute install paths. `generate_skill_mirrors.py` emits repo-relative paths and the
   drift sentinel proves the committed map equals the regenerated one byte-for-byte.

4. **Rich segmentation is where the next lessons come from (candidate @2).**
   Five ṣarf and four naḥw **candidate** rich-segmentation rules were added (owner
   adjudicates before they move `candidate → accepted`): the muḍāriʿ prefix, attached
   pronouns/subject markers, and derived-form roots are each their own segment; per
   occurrence the voice/mood/aspect/Form is committed, never hedged; the imperative lām is
   a governor segment; negation is owned by its particle, not the following verb; a
   verb-shaped triliteral is content, not a bare particle; the attached pronoun's iʿrāb
   role is stated per occurrence. Two **boundary negatives** guard against
   over-segmentation (a zero-clitic Form IV participle is a single token; a deliberately
   coarse learner split is complete, not a defect).

### Machine-checked gates at this release
- Registry validates (self-test + real), no duplicate ids, no dangling.
- Every `accepted` rule has an evidence-backed `permanent_tests` entry.
- Every skill fixture is red-first (corrected green / superseded red).
- Drift sentinel: all 10 classes trip on synthetic red-first inputs; `--real` = 0 findings.
- Mirror generation is deterministic; committed map == regenerated map.
- Rich-seg candidate fixtures: all 9 rules covered, both boundary negatives present.

*No runtime application behaviour changes in this release — it is skill documentation,
registry, and test infrastructure. Candidate @2 rules are DRAFT pending owner adjudication.*
