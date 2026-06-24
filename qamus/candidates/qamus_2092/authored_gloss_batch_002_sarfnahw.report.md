# Authored-gloss batch 002 — sarf/nahw verb-form glosses (SN7, APPLIED LIVE)

Source: the SN6 sarf/nahw hover candidates (`sarfnahw_hover_candidates.jsonl`), distilled from the SN ingest
(verb-measure paradigm + the AMAU corpus). Applied to live qamus-highlight via the established path
(`fusha-hover-decisions.tsv` → `rebuild.sh`), owner-blessed and reversible.

## Two-gate certification

**Gate 1 — adversarial 2-vote** (each candidate refuted by 2 independent Classical-Arabic skeptics; certify only
on 2/2 confirm). 13 candidates → **11 certified, 2 rejected**:
- `تَذَكَّرَ` rejected — cited āyah (6:152) carries the imperfect تَذَكَّرُونَ, not the perfect surface; the bare
  perfect is vanishingly rare → surface key would mis-match.
- `زَلْزَلَتِ` rejected — the Qurʾānic 99:1 form is the **passive** زُلْزِلَتِ, not the active I wrote; "quaked"
  mis-glosses the transitive active. (A genuine vocalization error the gate caught.)

**Gate 2 — empirical norm_strict key-collision test** against the live corpus (the fusha pass keys by
`norm_strict`, which drops the form-distinguishing shadda/voice harakāt). 11 → **8 applied, 3 dropped**:
- `نَزَّلَ` dropped — key `نزل` collides with **نَزَلَ "descended" (4×)** + نُزِّلَ passive (4×): a surface-key gloss
  would mis-serve Form I. (The exact form-collapse hazard the verb-measures work warns about.)
- `إِنفَاق`, `مَخْلُوق` dropped — **0 occurrences** in the live corpus (no effect).

## The 8 applied (key-safe, coverage-bearing)

| surface | key | gloss | form | occ |
|---|---|---|---|---:|
| أَخْرَجَ | أخرج | brought forth | IV | 4 |
| اِتَّقَىٰ | اتقي | was mindful (of Allah) | VIII | 4 |
| اِزْدَادُوا | ازدادوا | they increased | VIII | 1 |
| اِسْتَغْفِرُوا | استغفروا | seek forgiveness | X | 1 |
| يَسْتَكْبِرُونَ | يستكبرون | they act arrogantly | X | 3 |
| كَافِرُونَ | كافرون | disbelievers / those who disbelieve | ism fāʿil | 6 |
| مَدَّ | مد | extended / stretched | geminate | 2 |
| أَقَامُوا | أقاموا | established (the prayer) | IV | 2 |

## Live result (rebuild verified)

- coverage **69.06% → 69.08%** · matched **34,459 → 34,472** · build diff **+13 added / ~3 changed / −0 removed**.
- the 3 "changed" are all ٱتَّقَىٰ: a verbose infinitive spread-gloss → the concise certified "was mindful (of
  Allah)" (an improvement, not a regression).
- `validate` PASS (schema + licensing); health 200; light+dark screenshots viewed (page intact).
- **Rollback:** `fusha-hover-decisions.tsv.bak-sn7` + `wbw-lookup.prev.json` (one-step revert) + flag-off.

Public records ship exactly `{src:"qamus",kind:"authored",lang:"en"}`. No external gloss text, no source name,
no provenance leaves the internal evidence. Qurʾān text unaltered. No entry mutated.
