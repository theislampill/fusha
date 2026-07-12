#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic builder for the INCREMENT-21 (sarf@2.1 / nahw@2.1) candidate rows + fixtures.

Single source of two committed artifacts, emitted byte-deterministically (sorted keys, LF, trailing
newline) so re-running is a no-op:
  * qamus/skills/rule-registry-increment-21.jsonl   — candidate registry rows (schema-conformant)
  * tools/skill_fixtures/skill_fixtures_increment21.jsonl — red-first + branch-control fixtures

Every rule carries: source-addressed evidence, a positive (red-first) example, a boundary/control
example that proves the corrected discriminator BRANCHES (non-constant), defeaters, an abstention
condition, and a `projector` sketch keyed for the transclusion/projection lattice.

Run:  python tools/skill_fixtures/_build_increment21.py            # write both files
      python tools/skill_fixtures/_build_increment21.py --check    # verify committed == regenerated
Stdlib only, deterministic, no network.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REGISTRY_OUT = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-21.jsonl")
FIXTURES_OUT = os.path.join(HERE, "skill_fixtures_increment21.jsonl")

IMPL = "impl-records/calibration"
SKEV = "impl-records/skill-evolution/INCREMENT-21-NOTES.md"


def q(loc):
    return "quran:" + loc


def _exid(prefix, sid, loc):
    return "%s-%s-%s" % (prefix, sid.upper().replace("-", "_"), loc.replace(":", "_"))


# Each rule: the projector-lattice metadata + a positive (red-first) fixture + a branch control.
# proj.readiness ∈ {projector_ready, review_gated}.
RULES = [
    # ------------------------------- SARF @2.1 -------------------------------
    {
        "sid": "sarf-pattern-never-certifies-root", "skill": "sarf", "rule": "pattern_cert",
        "fam": "root-certification-gate", "phen": "pattern-shape-root-inference",
        "scope": ("A surface pattern (وزن) NEVER certifies a root. است/مست may be Form VIII of a "
                  "weak/hamza root (استوى→سوي, مستمعون→سمع); a ت-initial shape may be ibdāl "
                  "(تتخذوا→أخذ). Roots are two-tier: candidate_root from any inference, certified_root "
                  "ONLY from an explicit مادة in a reviewed-lexicography source."),
        "ev": [q("7:54:12"), q("26:15:7"), q("5:51:5"), "%s/C2-reviewerA.md" % IMPL,
               "%s/C2-reviewerA.jsonl" % IMPL],
        "defeaters": ["an explicit certified مادة from a reviewed-lexicography source certifies the root",
                      "MCP/QAC agreement on the root (after orthography normalization) certifies"],
        "abst": "no certified مادة present → stay candidate_root; never certify from pattern shape",
        "readiness": "review_gated",
        "proj": {"condition": "root asserted with provenance root_from=='surface_pattern' and no certified_madda",
                 "projection": "downgrade to candidate_root_uncertified; block public root certification",
                 "guards": ["certified-source مادة required to certify", "cross-source agreement guard"],
                 "scope": "root-match"},
        "rels": [("extends", "so-ownership-evidence-set", "registry",
                  "Adds a pattern-shape certification bar upstream of the ownership evidence set.")],
        "pos": {"locs": ["7:54:12"], "surfaces": ["استوى"],
                "case": {"root_from": "surface_pattern", "certified_madda": False},
                "correct": "candidate_root_uncertified", "wrong": "root_certified",
                "cite": "است in استوى mimics Form X but MCP certifies Form VIII of سوي; pattern never certifies"},
        "ctl": {"locs": ["39:42:2"], "surfaces": ["يتوفى"],
                "case": {"root_from": "certified_source", "certified_madda": True},
                "correct": "root_certified",
                "cite": "with an explicit certified مادة (و ف ي) the root certifies — the rule branches"},
    },
    {
        "sid": "sarf-weak-whole-token-detector", "skill": "sarf", "rule": "weak_whole_token",
        "fam": "completeness-false-negative", "phen": "weak-root-whole-token-miss",
        "scope": ("A whole-token verb whose certified root is weak (lafīf/nāqiṣ/ajwaf) and whose weak "
                  "radicals are absent from the contiguous surface (يتوفى exposes neither و nor ي) must "
                  "be flagged as an incompleteness defect; the ت-prefix nominal allow-lists miss it."),
        "ev": [q("39:42:2"), q("2:189:6"), q("36:39:3"), "%s/C2-reviewerA.md" % IMPL,
               "%s/MEASURED-EFFECT-2026-07-12.md" % "impl-records"],
        "defeaters": ["the weak radicals are visible contiguously in the surface (strong verb)",
                      "the token is a ت-prefix nominal already covered by the nominal detector"],
        "abst": "root weakness unconfirmed by a certified source → route to review, do not silently pass",
        "readiness": "review_gated",
        "proj": {"condition": "is_whole_token_verb and certified root_is_weak and weak radicals absent from surface",
                 "projection": "flag as a C2 completeness defect (candidate for repair)",
                 "guards": ["certified مادة needed to confirm root weakness", "2-vote before wave"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf §5 root ladder (rich-seg completeness), SKILL.md:5", "external",
                  "Extends the completeness gate to weak whole-token verbs.")],
        "pos": {"locs": ["39:42:2"], "surfaces": ["يتوفى"],
                "case": {"is_whole_token_verb": True, "root_is_weak": True, "weak_radicals_visible": False},
                "correct": "flag_weak_whole_token", "wrong": "no_flag",
                "cite": "يتوفى Form V لفيف مفروق of و ف ي (24 attested); surface hides both weak radicals"},
        "ctl": {"locs": ["36:39:3"], "surfaces": ["منازل"],
                "case": {"is_whole_token_verb": True, "root_is_weak": False, "weak_radicals_visible": True},
                "correct": "no_flag",
                "cite": "a strong-root token stays clean — the detector does not over-fire"},
    },
    {
        "sid": "sarf-cross-source-root-conflict-no-majority-vote", "skill": "sarf", "rule": "root_conflict",
        "fam": "root-source-conflict", "phen": "cross-source-root-disagreement",
        "scope": ("When two certified sources give roots that DIFFER after orthography normalization "
                  "(MCP ألك vs QAC ملك for ملائكة), neither certifies alone: record both candidates, "
                  "route the engine-diverse 2-vote, and NEVER majority-vote a root. Normalize MCP ي-final "
                  "vs QAC w/y before comparing so romanization never false-alarms."),
        "ev": [q("66:6:12"), q("39:42:2"), "%s/C2-reviewerA.md" % IMPL],
        "defeaters": ["the two roots are identical after w/y→و/ي normalization (false alarm) → certify agreed",
                      "only one certified source is present → single-source candidate, not a conflict"],
        "abst": "sources disagree post-normalization → block certification, route 2-vote / owner-gate",
        "readiness": "projector_ready",
        "proj": {"condition": "two certified source roots present and normalized(root_a) != normalized(root_b)",
                 "projection": "block certification; emit both candidate roots; route engine-diverse 2-vote",
                 "guards": ["orthography normalization before compare", "never majority-vote", "owner-gate on tie"],
                 "scope": "root-match"},
        "rels": [("extends", "so-ownership-evidence-set", "registry",
                  "Adds a cross-source conflict veto to root certification.")],
        "pos": {"locs": ["66:6:12"], "surfaces": ["ملائكة"],
                "case": {"root_source_a": "ألك", "root_source_b": "ملك"},
                "correct": "conflict_two_vote_no_majority", "wrong": "certify_agreed_root",
                "cite": "MCP مادة ألك vs QAC ملك — unresolvable single-source; 2-vote, never majority"},
        "ctl": {"locs": ["39:42:2"], "surfaces": ["يتوفى"],
                "case": {"root_source_a": "وفي", "root_source_b": "w f y"},
                "correct": "certify_agreed_root",
                "cite": "MCP وفي and QAC w/y agree after normalization — no false conflict; certify"},
    },
    {
        "sid": "sarf-jamid-vs-mushtaqq-routing", "skill": "sarf", "rule": "jamid_routing",
        "fam": "jamid-mushtaqq-split", "phen": "jamid-contested-nominal-routing",
        "scope": ("Split C2 into C2a (مشتق, root certified, derived) → wave-eligible after review, and "
                  "C2b (جامد / etymology-contested: ملكوت فَعَلُوت, مثاني, مسكين-debate) → auto-route "
                  "2-vote and the gloss may ship ROOT-SILENT. The detector must not message a jāmid "
                  "token as 'derived whole-token'."),
        "ev": [q("23:88:4"), q("39:23:7"), q("90:16:2"), q("46:24:4"), "%s/C2-reviewerA.md" % IMPL],
        "defeaters": ["token is مشتق with a certified root → wave-eligible after review (C2a)",
                      "certified source itself marks the token جامد or foreign → root-silent (C2b)"],
        "abst": "jāmid/etymology-contested → 2-vote; do not root-assert from a single source",
        "readiness": "projector_ready",
        "proj": {"condition": "token flagged is_jamid (certified) → route; else is_derived with certified root → wave",
                 "projection": "route jāmid to 2-vote + suppress root-assertion; route مشتق to review-then-wave",
                 "guards": ["jāmid flag from a certified source", "root-silent gloss allowed for C2b"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf §5 derived-form root exposure, SKILL.md:5", "external",
                  "Distinguishes derived (root-exposing) from jāmid (root-silent) C2 tokens.")],
        "pos": {"locs": ["23:88:4"], "surfaces": ["ملكوت"],
                "case": {"is_jamid": True, "is_derived": False, "root_certified": False},
                "correct": "route_two_vote_root_silent", "wrong": "wave_eligible_after_review",
                "cite": "ملكوت is jāmid (فَعَلُوت); root ملك recoverable but non-derived → 2-vote, root-silent OK"},
        "ctl": {"locs": ["46:24:4"], "surfaces": ["مستقبل"],
                "case": {"is_jamid": False, "is_derived": True, "root_certified": True},
                "correct": "wave_eligible_after_review",
                "cite": "مستقبل is مشتق (اسم فاعل Form X of قبل) with a certified root → wave-eligible"},
    },
    {
        "sid": "sarf-loc-integrity-address-xcheck", "skill": "sarf", "rule": "loc_integrity",
        "fam": "loc-integrity-prevalidation", "phen": "canonical-loc-surface-mismatch",
        "scope": ("Before emitting or deploying a row, resolve canonical_location→surface against the "
                  "corpus/wbw tokenization and FAIL CLOSED on mismatch or impossibility. FIVE independent "
                  "finds across C1/C2/C5 — 25:33:2→8, 61:4:3→11 (C2); 17:92:2→9 (C5); 2:91:3→word23 "
                  "(measured-effect); and the IMPOSSIBLE 4:91:103 (the āyah has 32 words) (C1) — prove any "
                  "wave keyed on a stated loc could write a gloss onto the wrong word or a non-existent one. "
                  "Mis-addressed rows reroute to the addressing lane; impossible addresses fail closed."),
        "ev": [q("25:33:2"), q("61:4:3"), q("17:92:2"), q("2:91:3"), q("4:91:103"),
               "%s/C2-reviewerA.md" % IMPL, "%s/C5-reviewerA.md" % IMPL, "%s/C1-reviewerA.md" % IMPL],
        "defeaters": ["stated word-index resolves byte-exact to the row surface within the āyah → emit"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "stated_word_index > āyah word count (impossible) OR stated != resolved (mismatch)",
                 "projection": "fail closed; block the wave write; reroute mismatches to the addressing lane",
                 "guards": ["validator-grade, no LLM judgment", "resolve against the live wbw index + āyah word count"],
                 "scope": "loc-match"},
        "rels": [("cites", "sarf §17 byte-exact carve/resplit, SKILL.md:332", "external",
                  "Extends deploy-mechanics: a loc must resolve to its surface before any write.")],
        "pos": {"locs": ["25:33:2"], "surfaces": ["تفسيرا"],
                "case": {"stated_word_index": 2, "resolved_word_index": 8},
                "correct": "fail_closed_reroute_addressing", "wrong": "loc_ok_emit",
                "cite": "25:33:2 surface تفسيرا actually resolves to word 8 — a wave at :2 mis-writes يأتونك"},
        "extra": [
            {"locs": ["4:91:103"], "surfaces": ["يأمنوكم"],
             "case": {"stated_word_index": 103, "ayah_word_count": 32, "resolved_word_index": 5},
             "correct": "fail_closed_impossible_address", "wrong": "loc_ok_emit",
             "cite": "4:91:103 is impossible — the āyah has 32 words; يأمنوكم is word 5 (fail closed)"},
        ],
        "ctl": {"locs": ["2:189:6"], "surfaces": ["مواقيت"],
                "case": {"stated_word_index": 6, "resolved_word_index": 6},
                "correct": "loc_ok_emit",
                "cite": "2:189:6 مواقيت resolves to word 6 — cross-check passes, emit"},
    },
    {
        "sid": "sarf-hamza-initial-disambiguation", "skill": "sarf", "rule": "hamza_initial",
        "fam": "hamza-initial-verb", "phen": "hamza-initial-lazy-disjunction",
        "scope": ("An أ-initial verb token must be resolved among {1s imperfect, Form IV perfect, Form IV "
                  "imperative, interrogative particle + verb} BEFORE any person/aspect tag is emitted. The "
                  "lazy disjunction '1st person singular or Form IV' is a BLOCKED output — commit via "
                  "diacritics/MCP or abstain. This disjunction caused 4/10 C4 hard errors."),
        "ev": [q("2:62:9"), q("2:283:11"), q("38:5:1"), q("33:37:9"), q("28:7:10"),
               "%s/C4-reviewerA.md" % IMPL, "%s/C4-authoring-packet-format.md" % IMPL],
        "defeaters": ["diacritics/MCP commit one reading → emit that reading, not the disjunction",
                      "hamza is the interrogative particle (أَجَعَلَ) → segment it as harf istifhām, not morphology"],
        "abst": "hamza unresolved after diacritic + MCP check → abstain; never emit the 1s-or-FormIV disjunction",
        "readiness": "review_gated",
        "proj": {"condition": "output would emit the '1s imperfect or Form IV' disjunction on an أ-initial verb",
                 "projection": "BLOCK the disjunction string; require a committed reading or abstention",
                 "guards": ["diacritic/MCP resolution required to commit", "interrogative-hamza exclusion"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf §5 form/باب derivation, SKILL.md:5", "external",
                  "Bars the lazy hamza disjunction from the form-derivation output.")],
        "pos": {"locs": ["38:5:1"], "surfaces": ["أجعل"],
                "case": {"emits_1s_or_formIV_disjunction": True},
                "correct": "blocked_disjunction", "wrong": "emit_1s_or_formIV_disjunction",
                "cite": "38:5:1 أَجَعَلَ: hamza is harf istifhām + māḍī 3ms; the '1s or Form IV' disjunction is banned"},
        "ctl": {"locs": ["2:62:9"], "surfaces": ["ءامن"],
                "case": {"emits_1s_or_formIV_disjunction": False, "resolved_reading": "formIV_perfect"},
                "correct": "committed:formIV_perfect",
                "cite": "2:62:9 ءَامَنَ resolves to Form IV perfect 3ms — committed, not disjoined"},
    },
    {
        "sid": "sarf-imperative-second-person-invariant", "skill": "sarf", "rule": "imperative_person",
        "fam": "imperative-person-invariant", "phen": "imperative-person-hard-invariant",
        "scope": ("HARD invariant (validator-grade): if aspect == imperative the subject person is 2nd "
                  "(2ms/2fs/2mp/2fp) and a 3rd-person tag or SUBJ gloss 'they' is a violation. 'Imperative "
                  "+ person-tag that is 3rd' caught 9/10 C4 hard errors with zero MCP; 5/5 sampled tagged "
                  "imperatives were wrong."),
        "ev": [q("2:40:3"), q("3:79:20"), q("34:13:12"), q("49:10:4"), q("28:7:10"), q("33:37:9"),
               "%s/C4-reviewerA.md" % IMPL],
        "defeaters": ["the form is genuinely 3rd-person and NOT imperative (perfect/imperfect) → invariant n/a"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "aspect == imperative and person does not start with '2'",
                 "projection": "hard violation; block deploy; SUBJ gloss must be 2nd person, never 'they'",
                 "guards": ["deterministic, no MCP needed", "aspect must first be committed (see hamza/vocalism rules)"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf rich-seg occurrence-committed rule (sarf-richseg-occurrence-voice-mood-aspect-form-committed)",
                  "external", "The imperative-person invariant is a hard check on the committed occurrence.")],
        "pos": {"locs": ["2:40:3"], "surfaces": ["اذكروا"],
                "case": {"aspect": "imperative", "person": "3mp"},
                "correct": "violation_imperative_non_second", "wrong": "accepted_no_violation",
                "cite": "2:40:3 ٱذْكُرُوا۟ is fiʿl amr lil-mukhāṭabīn → 2mp; a 3mp 'they' tag is a hard violation"},
        "ctl": {"locs": ["28:7:10"], "surfaces": ["فألقيه"],
                "case": {"aspect": "imperative", "person": "2fs"},
                "correct": "ok_second_person",
                "cite": "28:7:10 فَأَلْقِيهِ is a 2fs imperative — a genuine 2nd-person tag passes"},
    },
    {
        "sid": "sarf-passive-vocalism-voice-commit", "skill": "sarf", "rule": "passive_vocalism",
        "fam": "voice-commit", "phen": "passive-vocalism-hedge",
        "scope": ("ُ-ِ perfect / ُ-َ imperfect vocalism ⇒ commit voice=passive; a-a perfect / a-u imperfect "
                  "⇒ active. 'active/passive as context requires' is legal ONLY for an undiacritized or "
                  "qirāʾāt-split address — none exist in the fully-vocalized Uthmani corpus in-sample."),
        "ev": [q("21:35:10"), q("2:62:9"), q("2:282:11"), "%s/C4-reviewerA.md" % IMPL,
               "%s/C1-reviewerA.md" % IMPL],
        "defeaters": ["address is qirāʾāt-split on voice, or undiacritized → named-ambiguity abstention is legal"],
        "abst": "qirāʾāt-split or undiacritized on voice → abstain with a named qiraat_note; else commit",
        "readiness": "review_gated",
        "proj": {"condition": "diacritized surface has u-i (perfect) or u-a (imperfect) vocalism",
                 "projection": "commit voice=passive (or active for a-a/a-u); replace the 'as context requires' hedge",
                 "guards": ["qirāʾāt-split escape hatch", "requires a reliable vocalism read"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf rich-seg occurrence-committed rule (sarf-richseg-occurrence-voice-mood-aspect-form-committed)",
                  "external", "Voice is one of the per-occurrence facts that must be committed, not hedged.")],
        "pos": {"locs": ["21:35:10"], "surfaces": ["ترجعون"],
                "case": {"vocalism": "u_a_imperfect"},
                "correct": "commit_passive", "wrong": "hedge_active_or_passive",
                "cite": "21:35:10 تُرْجَعُونَ has ُ-َ imperfect vocalism → passive; the hedge hides a knowable fact"},
        "ctl": {"locs": ["2:62:9"], "surfaces": ["ءامن"],
                "case": {"vocalism": "a_a_perfect"},
                "correct": "commit_active",
                "cite": "2:62:9 ءَامَنَ has a-a perfect vocalism → active; the rule branches on vocalism"},
    },
    {
        "sid": "sarf-completeness-claim-requires-asserted-facts", "skill": "sarf", "rule": "completeness_claim",
        "fam": "learner-text-honesty", "phen": "false-completeness-template",
        "scope": ("The learner_explanation 'the hover exposes … the person/number/mood facts' may render "
                  "ONLY when the morphline actually asserts person AND mood; otherwise the generator must "
                  "emit the honest-generic variant. 523/523 C4 rows carried this claim while the morphline "
                  "abstained on exactly those facts."),
        "ev": [q("2:40:3"), q("6:84:20"), "%s/C4-reviewerA.md" % IMPL,
               "%s/C4-authoring-packet-format.md" % IMPL],
        "defeaters": ["morphline asserts person AND mood → the completeness claim is truthful and may render"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "learner text claims person/number/mood completeness while morphline abstains on person or mood",
                 "projection": "swap to the honest-generic learner variant (deterministic, zero morphology work)",
                 "guards": ["render-time string/field check", "no morphology authoring required for the honesty fix"],
                 "scope": "occurrence-match"},
        "rels": [("cites", "sarf §13d VN-00 visual completeness ANDON, SKILL.md:236", "external",
                  "The completeness claim must reconcile with the asserted morphline facts.")],
        "pos": {"locs": ["2:40:3"], "surfaces": ["اذكروا"],
                "case": {"morphline_asserts_person": False, "morphline_asserts_mood": False},
                "correct": "render_honest_generic", "wrong": "render_completeness_claim",
                "cite": "the C4 template claims person/number/mood while the morphline abstains → honest-generic"},
        "ctl": {"locs": ["6:84:20"], "surfaces": ["نجزي"],
                "case": {"morphline_asserts_person": True, "morphline_asserts_mood": True},
                "correct": "render_completeness_claim",
                "cite": "once person AND mood are actually asserted, the completeness claim may render"},
    },
    {
        "sid": "sarf-segment-morphline-person-consistency", "skill": "sarf", "rule": "person_consistency",
        "fam": "internal-consistency", "phen": "person-cross-field-contradiction",
        "scope": ("Internal consistency (validator-grade): the PFX-segment person, the morphline person, "
                  "the SUBJ-segment person and the learner-text person must all agree. 17:12:16 self-"
                  "contradicts (PFX seg '2nd person' while the morphline tags 3mp) and no gate caught it."),
        "ev": [q("17:12:16"), "%s/C4-reviewerA.md" % IMPL, "%s/C4-authoring-packet-format.md" % IMPL],
        "defeaters": ["all present person fields agree → consistent"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "distinct person values across {pfx_seg, morphline, subj_seg, learner_text} > 1",
                 "projection": "hard violation; block deploy until the fields are reconciled",
                 "guards": ["cross-field equality check", "runs before any wave"],
                 "scope": "occurrence-match"},
        "rels": [("cites", "sarf rich-seg attached-unit segmentation rule (sarf-richseg-attached-pronoun-subject-marker-own-segment)",
                  "external", "Person carried by segments must equal the morphline's person.")],
        "pos": {"locs": ["17:12:16"], "surfaces": ["ولتعلموا"],
                "case": {"pfx_person": "2mp", "morphline_person": "3mp", "subj_person": "3mp"},
                "correct": "violation_person_mismatch", "wrong": "no_check_passed_consistent",
                "cite": "17:12:16 وَلِتَعْلَمُوا۟: PFX seg says 2nd, morphline tags 3mp — a self-contradiction"},
        "ctl": {"locs": ["21:35:10"], "surfaces": ["ترجعون"],
                "case": {"pfx_person": "2mp", "morphline_person": "2mp", "subj_person": "2mp"},
                "correct": "consistent",
                "cite": "when every person field agrees (2mp) the row is consistent — the rule branches"},
    },
    {
        "sid": "sarf-form-v-vi-ta-is-wazn-augment", "skill": "sarf", "rule": "form_v_vi_ta",
        "fam": "over-segmentation-guard", "phen": "form-v-vi-ta-mispeel",
        "scope": ("The ت of Form V (تفعّل) and Form VI (تفاعل) is a زائد wazn augment (Shadhā al-ʿArf, "
                  "primary source) — it is stem-internal and is NEVER peeled as a proclitic. An "
                  "inflectional muḍāriʿ ت prefix (a different ت) IS its own segment; the two must not be "
                  "conflated."),
        "ev": [q("83:26:5"), q("39:42:2"), "%s/INCREMENT-21-NOTES.md#DR-1" % "impl-records/skill-evolution"],
        "defeaters": ["the ت is an inflectional muḍāriʿ prefix (يَـ/تَـ/نَـ/أَـ seat) not a Form V/VI wazn augment"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "wazn ∈ {تفعّل, تفاعل} and the token has a leading ت",
                 "projection": "keep the ت in the stem as a wazn augment; do NOT emit it as a proclitic segment",
                 "guards": ["distinguish inflectional muḍāriʿ ت (own segment) from the wazn ت", "QAC 3-seg precedent 83:26:5"],
                 "scope": "construction-match"},
        "rels": [("cites", "sarf rich-seg mudari-prefix rule (sarf-richseg-mudari-prefix-own-segment)", "external",
                  "Boundary partner: the inflectional ت IS a segment; the Form V/VI wazn ت is NOT.")],
        "pos": {"locs": ["83:26:5"], "surfaces": ["يتنافس"],
                "case": {"wazn": "تفاعل", "leading_ta": True},
                "correct": "ta_is_wazn_keep_in_stem", "wrong": "peel_ta_as_proclitic",
                "cite": "83:26:5 فَلْيَتَنَافَسِ (Form VI تفاعل): the ت is a wazn augment, never a proclitic"},
        "ctl": {"locs": ["2:91:23"], "surfaces": ["تقتلون"],
                "case": {"wazn": "يفعلون", "leading_ta": True, "prefix_is_inflectional": True},
                "correct": "ta_is_inflectional_prefix_segment",
                "cite": "2:91:23 تَقْتُلُونَ: the ت is an inflectional muḍāriʿ prefix — its OWN segment"},
    },
    {
        "sid": "sarf-root-radical-not-clitic", "skill": "sarf", "rule": "root_radical",
        "fam": "clitic-false-positive-guard", "phen": "root-radical-homograph",
        "scope": ("A suffix-shaped surface letter (ك/ي/ه/ا/و) that is a ROOT RADICAL — final (تملك ك of "
                  "م ل ك, تهدي ي of ه د ي, تأتي ي of أ ت ي) or initial (وعد و of و ع د, not a conjunction) "
                  "— is NEVER a clitic. Resolve the root and refuse the peel when the letter is a radical. "
                  "The ي-family was 2-for-2 FP in C5."),
        "ev": [q("5:41:46"), q("28:56:3"), q("17:92:9"), q("9:72:1"), "%s/C5-reviewerA.md" % IMPL],
        "defeaters": ["the letter is not among the root radicals → it is a genuine clitic and keeps its segment"],
        "abst": "root unresolved → do not assert a clitic peel of a possibly-radical letter",
        "readiness": "projector_ready",
        "proj": {"condition": "candidate_clitic_letter ∈ root_radicals (final or initial)",
                 "projection": "PREVENT the clitic projection; the letter stays part of the stem/root",
                 "guards": ["compare against the morphline root or certified مادة", "initial-wāw وعد guard"],
                 "scope": "surface-match"},
        "rels": [("extends", "so-clitic-host-evidence-required", "registry",
                  "A radical-homograph veto on the clitic-peel side of ownership.")],
        "pos": {"locs": ["28:56:3"], "surfaces": ["تهدي"],
                "case": {"candidate_clitic_letter": "ي", "root_radicals": ["ه", "د", "ي"]},
                "correct": "radical_not_clitic", "wrong": "peel_as_clitic",
                "cite": "28:56:3 تَهْدِي: the final ي is the ي of root ه د ي, not an attached pronoun"},
        "ctl": {"locs": ["2:235:17"], "surfaces": ["ستذكرونهن"],
                "case": {"candidate_clitic_letter": "ه", "root_radicals": ["ذ", "ك", "ر"]},
                "correct": "genuine_clitic",
                "cite": "2:235:17 سَتَذْكُرُونَهُنَّ: the ه of هن is a genuine object pronoun (not a radical of ذ ك ر)"},
    },
    {
        "sid": "sarf-zero-marker-agreement-no-segment", "skill": "sarf", "rule": "zero_agreement",
        "fam": "clitic-false-positive-guard", "phen": "mustatir-demanded-segment",
        "scope": ("A mustatir / zero-marker subject (3ms perfect, 2ms/2fs imperative) requires NO suffix "
                  "segment; only an OVERT clitic (ـتُ/ـتَ/ـتم/ـتن/نا/وا/ألف الاثنين/نون النسوة/ي/ك/ه…) does. "
                  "The C5 detector wrongly demanded a segment for mustatir agreement mentions."),
        "ev": [q("2:258:32"), q("9:72:1"), "%s/C5-reviewerA.md" % IMPL],
        "defeaters": ["the token carries an overt clitic → a segment IS required"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "subject_realization == mustatir (no overt clitic present)",
                 "projection": "PREVENT the 'missing subject segment' projection — none is expected",
                 "guards": ["overt-clitic exception", "distinguish agreement mention from realized morpheme"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf rich-seg attached-unit segmentation rule (sarf-richseg-attached-pronoun-subject-marker-own-segment)",
                  "external", "Only overt morphemes get a segment; mustatir agreement does not.")],
        "pos": {"locs": ["2:258:32"], "surfaces": ["فأت"],
                "case": {"subject_realization": "mustatir"},
                "correct": "no_segment_expected", "wrong": "segment_required",
                "cite": "2:258:32 فَأْتِ: the 2ms imperative subject is mustatir — no suffix segment is due"},
        "ctl": {"locs": ["2:235:17"], "surfaces": ["ستذكرونهن"],
                "case": {"subject_realization": "suffix", "overt_clitic": True},
                "correct": "segment_required",
                "cite": "2:235:17 has an overt واو الجماعة + هن — those DO require segments; the rule branches"},
    },
    {
        "sid": "sarf-negated-mention-no-keyword-fire", "skill": "sarf", "rule": "negated_mention",
        "fam": "detector-negation-window", "phen": "negated-keyword-false-fire",
        "scope": ("Morphline keyword matching (e.g. 'pronoun/ضمير') must parse the negation window: a "
                  "NEGATED mention ('not an attached pronoun') must NOT trip the detector. ٱلْكُبْرَىٰ fired "
                  "on its own disclaimer."),
        "ev": [q("79:34:4"), "%s/C5-reviewerA.md" % IMPL],
        "defeaters": ["the keyword occurs as a positive assertion (not inside a negation window) → fire"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "detector keyword occurs inside a negation window ('not a …')",
                 "projection": "PREVENT the false detector fire on the negated mention",
                 "guards": ["negation-window parse before keyword match", "validator-grade"],
                 "scope": "occurrence-match"},
        "rels": [("cites", "sarf §16 consume-the-lattice / never-rebuild, SKILL.md:302", "external",
                  "A detector must read what the morphline asserts, not merely that a word appears.")],
        "pos": {"locs": ["79:34:4"], "surfaces": ["الكبرى"],
                "case": {"keyword_present": True, "keyword_negated": True},
                "correct": "suppress_negated_mention", "wrong": "fire_detector",
                "cite": "79:34:4 ٱلْكُبْرَىٰ: the morphline literally says 'not an attached pronoun' — do not fire"},
        "ctl": {"locs": ["2:235:17"], "surfaces": ["ستذكرونهن"],
                "case": {"keyword_present": True, "keyword_negated": False},
                "correct": "fire_detector",
                "cite": "a genuine, positively-asserted attached pronoun DOES fire — the rule branches"},
    },
    {
        "sid": "sarf-epenthetic-ishbaa-waw-not-segment", "skill": "sarf", "rule": "ishbaa_waw",
        "fam": "clitic-false-positive-guard", "phen": "ishbaa-waw-mispeel",
        "scope": ("In ـتُمُو + pronoun (آتيتموهن, أُورِثْتُمُوهَا) the و is حرف إشباع (epenthetic) — it stays "
                  "with the تم subject segment and is never its own segment nor a root radical. A genuine "
                  "واو الجماعة, by contrast, IS its own subject segment."),
        "ev": [q("7:43:33"), "%s/C5-reviewerA.md" % IMPL,
               "%s/MEASURED-EFFECT-2026-07-12.md" % "impl-records"],
        "defeaters": ["the و is a واو الجماعة subject marker (not the تُمُو epenthesis) → its own segment"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "context is ـتُمُو + pronoun and the letter is و",
                 "projection": "PREVENT an ishbāʿ-waw segment; keep it with the تم subject segment",
                 "guards": ["distinguish ishbāʿ waw from واو الجماعة", "byte-exact resplit"],
                 "scope": "construction-match"},
        "rels": [("cites", "sarf §17 byte-exact carve/resplit, SKILL.md:332", "external",
                  "Epenthetic fillers are not segments and must not break the byte-exact carve.")],
        "pos": {"locs": ["7:43:33"], "surfaces": ["أورثتموها"],
                "case": {"context": "tumu_plus_pronoun", "letter": "و"},
                "correct": "ishbaa_stays_with_tum", "wrong": "split_ishbaa_as_segment",
                "cite": "7:43:33 أُورِثْتُمُوهَا: the و between تم and ها is ishbāʿ, not a segment/radical"},
        "ctl": {"locs": ["2:40:3"], "surfaces": ["اذكروا"],
                "case": {"context": "waw_al_jamaa", "letter": "و"},
                "correct": "waw_jamaa_own_segment",
                "cite": "2:40:3 ٱذْكُرُوا۟: the واو الجماعة IS its own subject segment — the rule branches"},
    },
    {
        "sid": "sarf-jam-marker-single-pronoun-segment", "skill": "sarf", "rule": "jam_marker",
        "fam": "pronoun-segmentation-template", "phen": "jam-marker-orphan",
        "scope": ("The canonical split of a jamʿ/dual-marked pronoun (هُمْ، هُنَّ، هُمَا، كُمُ) is ONE pronoun "
                  "segment carrying its jamʿ/ʿimād/dual letters with a sarf note decomposing them MCP-style "
                  "(هاء + الميم للجمع); never a bare هـ segment that orphans the mīm/nūn."),
        "ev": [q("2:235:17"), q("7:43:33"), "%s/C5-reviewerA.md" % IMPL],
        "defeaters": ["the token has no jamʿ/dual pronoun cluster → rule n/a"],
        "abst": None,
        "readiness": "review_gated",
        "proj": {"condition": "an enclitic pronoun cluster (هم/هن/هما/كم) is present",
                 "projection": "emit ONE pronoun segment carrying the jamʿ letters + a decomposition note",
                 "guards": ["never orphan the جمع mīm/nūn", "sarf decomposition note attached"],
                 "scope": "construction-match"},
        "rels": [("cites", "sarf rich-seg attached-unit segmentation rule (sarf-richseg-attached-pronoun-subject-marker-own-segment)",
                  "external", "Refines the attached-pronoun segment to keep the jamʿ letters together.")],
        "pos": {"locs": ["2:235:17"], "surfaces": ["ستذكرونهن"],
                "case": {"pronoun_cluster": True, "keeps_jam_letters": True},
                "correct": "one_pronoun_segment_with_jam", "wrong": "orphaned_jam_letter",
                "cite": "2:235:17 هُنَّ: one pronoun segment carrying هاء + نون النسوة, not a bare هـ"},
        "ctl": {"locs": ["7:43:33"], "surfaces": ["أورثتموها"],
                "case": {"pronoun_cluster": False},
                "correct": "na",
                "cite": "a single ها object pronoun is not a jamʿ cluster — the rule does not fire"},
    },
    {
        "sid": "sarf-within-root-pos-arm", "skill": "sarf", "rule": "pos_arm",
        "fam": "within-root-halt-arm", "phen": "within-root-pos-ownership-arm",
        "scope": ("Within-root HALT amendment: when a surface resolves to TWO candidate roots (قُل → ق ل ل "
                  "/ ق و ل), a POS reading that only ONE candidate root supports is a valid OWNERSHIP ARM. "
                  "The imperative 'say' exists only for قول, so قُل rebinds to ق و ل. Absent such an arm, "
                  "HALT (entry-level selection deferred to the 2-vote)."),
        "ev": [q("10:59:1"), q("13:16:6"), "%s/W13-reviewerA-round2.md" % IMPL],
        "defeaters": ["no POS/surface arm distinguishes the candidate roots → HALT, do not certify",
                      "more than one candidate root supports the POS reading → HALT"],
        "abst": "no deciding arm → HALT (review_required); never certify a root without an arm",
        "readiness": "projector_ready",
        "proj": {"condition": "two candidate roots and exactly one supports the token's POS reading",
                 "projection": "rebind to the single POS-supporting root; entry-level selection deferred to 2-vote",
                 "guards": ["POS reading must be certified", "HALT if 0 or >1 roots support the POS"],
                 "scope": "root-match"},
        "rels": [("extends", "so-w13-deterministic-ownership-gate", "registry",
                  "Adds a POS-reading ownership arm to the within-root HALT.")],
        "pos": {"locs": ["10:59:1"], "surfaces": ["قل"],
                "case": {"candidate_roots": ["ق ل ل", "ق و ل"], "roots_supporting_pos": ["ق و ل"]},
                "correct": "rebind_pos_arm:ق و ل", "wrong": "halt_no_deciding_arm",
                "cite": "10:59:1 قُلْ: MCP فِعْلُ أَمْرٍ أَجْوَفُ وَاوِيٌّ من مادة (قول) — imperative excludes ق ل ل"},
        "ctl": {"locs": ["13:16:6"], "surfaces": ["قل"],
                "case": {"candidate_roots": ["ق ل ل", "ق و ل"], "roots_supporting_pos": ["ق ل ل", "ق و ل"]},
                "correct": "halt_no_deciding_arm",
                "cite": "if both candidate roots supported the POS reading there is no deciding arm → HALT"},
    },
    {
        "sid": "sarf-content-hold-absent-ownership-arm", "skill": "sarf", "rule": "content_hold",
        "fam": "content-ownership-hold", "phen": "content-hold-no-forms-arm",
        "scope": ("A content token whose root morphology NAMES the root (رَبَّكَ → ر ب ب, ٱلشَّيَٰطِينُ → ش ط ن) "
                  "but whose surface is documented by NO entry's usage[].forms → HOLD (review_required). "
                  "Absence of an ownership arm is INVENTORY, not proof; never fabricate a rebind edge on "
                  "morphology alone."),
        "ev": [q("16:125:13"), q("2:102:4"), q("13:11:17"), "%s/W13-reviewerA-round2.md" % IMPL],
        "defeaters": ["an entry's usage[].forms documents the surface → the rebind IS supported"],
        "abst": "root named but no forms arm → HOLD; route engine-diverse 2-vote / new-entry authoring",
        "readiness": "projector_ready",
        "proj": {"condition": "content token: morphology names a root but no entry usage[].forms documents the surface",
                 "projection": "route to review_required HOLD; block any rebind edge",
                 "guards": ["absence-of-arm is inventory not proof", "never fabricate an ownership edge"],
                 "scope": "surface-match"},
        "rels": [("extends", "so-adjacency-not-ownership", "registry",
                  "The content-side hold: a named root without a forms arm is not ownership.")],
        "pos": {"locs": ["16:125:13"], "surfaces": ["ربك"],
                "case": {"root_named": True, "forms_arm_present": False},
                "correct": "hold_review_required", "wrong": "rebind_on_morphology_alone",
                "cite": "16:125:13 رَبَّكَ: MCP names ر ب ب but no entry forms-arm documents it → HOLD, never rebind"},
        "ctl": {"locs": ["13:11:17"], "surfaces": ["بقوم"],
                "case": {"root_named": True, "forms_arm_present": True},
                "correct": "rebind_supported",
                "cite": "13:11:17 بِقَوْمٍ: قَوْمٍ من مادة (قوم) with a documented forms arm → rebind supported"},
    },
    {
        "sid": "sarf-coarse-tier-verb-subject-one-unit", "skill": "sarf", "rule": "coarse_tier_verb",
        "fam": "coarse-tier-completeness", "phen": "verb-subject-one-unit-refutes-c1",
        "scope": ("A finite verb + its subject/agreement morphology is ONE sarf unit at the coarse tier "
                  "(MCP: {يُنْفِقُونَ}, {يَنْكِحْنَ}) — a committed whole-token verb with root+form+person is "
                  "VALID, not a stem_swallow. The C1 theory 'an imperfect agreement prefix inside the verb "
                  "segment is a defect' is REFUTED (34.1% precision). The OBJECT pronoun, by contrast, is "
                  "ALWAYS its own segment; a genuinely rootless whole-token is still a defect."),
        "ev": [q("2:3:8"), q("2:270:11"), q("2:85:16"), q("2:259:53"), "%s/C1-reviewerA.md" % IMPL],
        "defeaters": ["the whole-token verb is genuinely ROOTLESS (no root/form/person committed) → defect",
                      "an OBJECT pronoun is fused into the verb segment → the object must split (C5)"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "whole-token finite verb commits root+form+person and no object pronoun is fused",
                 "projection": "PREVENT the C1 stem_swallow flag — the verb+subject unit is valid at the coarse tier",
                 "guards": ["rootless whole-token still flagged", "object pronoun must be its own segment"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf rich-seg mudari-prefix rule (sarf-richseg-mudari-prefix-own-segment)", "external",
                  "The inflectional prefix is a segment in FINE tier; the coarse tier keeps verb+subject as one valid unit.")],
        "pos": {"locs": ["2:3:8"], "surfaces": ["ينفقون"],
                "case": {"root_committed": True, "object_pronoun_fused": False},
                "correct": "valid_coarse_verb_subject_unit", "wrong": "flag_prefix_swallow",
                "cite": "2:3:8 يُنفِقُونَ commits root ن ف ق + 3mp — a valid coarse verb+subject unit, not a swallow"},
        "ctl": {"locs": ["2:270:11"], "surfaces": ["يعلمه"],
                "case": {"root_committed": True, "object_pronoun_fused": True},
                "correct": "object_must_split",
                "cite": "2:270:11 يَعْلَمُهُۥ: the object pronoun هُ must be its own segment — the rule branches"},
    },
    # ------------------------------- NAHW @2.1 -------------------------------
    {
        "sid": "nahw-mood-from-governor", "skill": "nahw", "rule": "mood_governor",
        "fam": "mood-from-governor", "phen": "mood-hedge-with-visible-governor",
        "scope": ("Mood is decidable from a visible governor (لِ/أَنْ/لَمْ/لَا الناهية/شرط) plus the final "
                  "vowel: commit the mood, or state an explicit named ambiguity — never 'mood context not "
                  "separately asserted' when a governor is visible."),
        "ev": [q("17:12:16"), q("102:3:3"), q("2:282:11"), q("2:283:14"),
               "%s/C4-reviewerA.md" % IMPL, "%s/C1-reviewerA.md" % IMPL],
        "defeaters": ["no governor is visible and the verb is indicative by default → commit indicative",
                      "genuinely qirāʾāt-split mood → named ambiguity"],
        "abst": "no governor and mood genuinely ambiguous → named-ambiguity reason, not a silent hedge",
        "readiness": "review_gated",
        "proj": {"condition": "a mood governor (لِ/أَنْ/لَمْ/لَا-nāhiya/shart) is visible before the muḍāriʿ",
                 "projection": "commit the governed mood; replace 'not separately asserted'",
                 "guards": ["governor identification (contextual)", "final-vowel confirmation"],
                 "scope": "construction-match"},
        "rels": [("extends", "ONH-B5", "registry",
                  "Mood is a stated consequence of a visible governor, per-occurrence.")],
        "pos": {"locs": ["17:12:16"], "surfaces": ["ولتعلموا"],
                "case": {"governor": "lam_taleel"},
                "correct": "commit:subjunctive", "wrong": "mood_not_separately_asserted",
                "cite": "17:12:16 لِتَعْلَمُوا۟: مضارع منصوب بأن مضمرة after لام التعليل — commit subjunctive"},
        "ctl": {"locs": ["102:3:3"], "surfaces": ["تعلمون"],
                "case": {"indicative_default": True},
                "correct": "commit:indicative",
                "cite": "102:3:3 تَعْلَمُونَ has no governor and a marfūʿ ending → indicative; the rule branches"},
    },
    {
        "sid": "nahw-lam-prefix-typology", "skill": "nahw", "rule": "lam_typology",
        "fam": "lam-prefix-typology", "phen": "lam-prefix-undifferentiated",
        "scope": ("The lām prefix has distinct types, each its OWN segment with its own consequence: لام "
                  "الأمر (jussive governor), لام التعليل/كي (subjunctive via أن مضمرة), لام الجر (jarr), لام "
                  "الابتداء/التوكيد (emphasis, no mood effect). The type must be resolved before glossing "
                  "or segmenting."),
        "ev": [q("83:26:5"), q("65:7:1"), q("17:12:16"), q("2:282:11"), q("2:283:18"),
               "%s/C1-reviewerA.md" % IMPL,
               "%s/INCREMENT-21-NOTES.md#DR-1-DR-6" % "impl-records/skill-evolution"],
        "defeaters": ["a following muḍāriʿ vs a noun disambiguates أمر/تعليل from jarr",
                      "sukūn (jussive) vs fatḥa (subjunctive) on the verb confirms أمر vs تعليل"],
        "abst": "lām type genuinely ambiguous → named ambiguity; do not fold it into the verb",
        "readiness": "review_gated",
        "proj": {"condition": "a prefixed lām is present; classify {amr, taleel, jarr, ibtida} then apply its consequence",
                 "projection": "emit the lām as its own segment with the type-specific mood/case consequence",
                 "guards": ["type identification is contextual (review)", "consequence is deterministic once typed"],
                 "scope": "construction-match"},
        "rels": [("cites", "nahw rich-seg imperative-lām governor rule (nahw-richseg-imperative-lam-governor-jussive-segment)",
                  "external", "Generalizes the imperative-lām rule to the full lām typology.")],
        "pos": {"locs": ["65:7:1"], "surfaces": ["لينفق"],
                "case": {"lam_type": "lam_al_amr"},
                "correct": "governor_jussive", "wrong": "lam_undifferentiated_folded",
                "cite": "65:7:1 لِيُنفِقْ: لام الأمر governs the muḍāriʿ into jussive — its own segment"},
        "ctl": {"locs": ["17:12:16"], "surfaces": ["ولتعلموا"],
                "case": {"lam_type": "lam_taleel"},
                "correct": "governor_subjunctive_an_mudmara",
                "cite": "17:12:16 لام التعليل governs subjunctive via أن مضمرة — a distinct type/consequence"},
    },
    {
        "sid": "nahw-jazm-only-on-mudari", "skill": "nahw", "rule": "jazm_only_mudari",
        "fam": "mood-domain-invariant", "phen": "mood-on-non-mudari",
        "scope": ("HARD invariant: mood (and jazm/naṣb specifically) is a category of the muḍāriʿ ONLY. A "
                  "perfect (mabnī) or an imperative is never 'majzūm/manṣūb'; asserting a mood on a "
                  "non-imperfect is a violation."),
        "ev": [q("2:62:9"), q("39:42:2"), "%s/INCREMENT-21-NOTES.md#DR-6" % "impl-records/skill-evolution"],
        "defeaters": ["the verb is a muḍāriʿ → mood is applicable and should be asserted"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "aspect != imperfect and a mood (jussive/subjunctive/indicative) is asserted",
                 "projection": "hard violation; strip the mood label from the perfect/imperative",
                 "guards": ["deterministic on committed aspect", "mabnī perfect/imperative carry no iʿrāb mood"],
                 "scope": "surface-match"},
        "rels": [("cites", "nahw rich-seg imperative-lām governor rule (nahw-richseg-imperative-lam-governor-jussive-segment)",
                  "external", "Only the muḍāriʿ receives jazm from a governor.")],
        "pos": {"locs": ["2:62:9"], "surfaces": ["ءامن"],
                "case": {"aspect": "perfect", "asserted_mood": "jussive"},
                "correct": "violation_mood_on_non_mudari", "wrong": "mood_allowed_on_non_mudari",
                "cite": "2:62:9 ءَامَنَ is a perfect (mabnī) — a 'jussive' mood label on it is a hard violation"},
        "ctl": {"locs": ["39:42:2"], "surfaces": ["يتوفى"],
                "case": {"aspect": "imperfect", "asserted_mood": "indicative"},
                "correct": "mood_applicable",
                "cite": "39:42:2 يَتَوَفَّى is a muḍāriʿ — mood IS applicable; the invariant branches on aspect"},
    },
    {
        "sid": "nahw-ma-man-function-per-occurrence", "skill": "nahw", "rule": "ma_man_occurrence",
        "fam": "function-word-occurrence-scope", "phen": "ma-man-reading-propagation",
        "scope": ("مَا/مَن function (نافية/موصولة/استفهامية/…) is resolved PER OCCURRENCE. The SAME surface "
                  "can carry DIFFERENT functions in the SAME āyah (5:116 has relative مَا AND nāfiya مَا); "
                  "never carry one occurrence's reading to another."),
        "ev": [q("5:116:18"), q("6:3:11"), "%s/INCREMENT-21-NOTES.md#DR-6" % "impl-records/skill-evolution"],
        "defeaters": ["each occurrence is resolved on its own local function + scope (not the lexicon default)"],
        "abst": "occurrence function genuinely ambiguous → named ambiguity for THAT occurrence only",
        "readiness": "projector_ready",
        "proj": {"condition": "a مَا/مَن reading is being applied from a different occurrence of the same surface",
                 "projection": "PREVENT the cross-occurrence propagation; resolve each occurrence independently",
                 "guards": ["per-occurrence isolation (deterministic)", "function ID is contextual (review)"],
                 "scope": "occurrence-match"},
        "rels": [("extends", "ONH-B5", "registry",
                  "Makes the ما/مَن split strictly per-occurrence, even within one āyah.")],
        "pos": {"locs": ["5:116:18"], "surfaces": ["ما"],
                "case": {"propagated_from_other_occurrence": True},
                "correct": "violation_propagated_reading", "wrong": "propagated_reading_accepted",
                "cite": "5:116 carries both relative مَا and nāfiya مَا — a reading may not propagate between them"},
        "ctl": {"locs": ["6:3:11"], "surfaces": ["ما"],
                "case": {"occurrence_function": "mawsula"},
                "correct": "function_per_occurrence:mawsula",
                "cite": "6:3:11 مَا موصولة, resolved on its own occurrence — the rule branches"},
    },
    {
        "sid": "nahw-la-nahiya-jussive-governor", "skill": "nahw", "rule": "la_nahiya",
        "fam": "negation-governor", "phen": "la-nahiya-vs-nafiya",
        "scope": ("لا الناهية is a jussive-forcing governor that OWNS the following verb (verb → majzūm) — "
                  "distinct from لا النافية — and the verb after it is a CONTENT verb keeping its root; the "
                  "negation is owned by the لا particle, not by the verb. Gloss-ownership corollary: the "
                  "verb's gloss contributes only its own meaning (تَحْزَنُوا۟ = 'grieve'); the negation "
                  "belongs to the لا token, so a token gloss 'do not grieve' wrongly imports لا's negation."),
        "ev": [q("2:104:6"), q("2:6:7"), q("3:139:4"), "%s/C1-reviewerA.md" % IMPL,
               "%s/INCREMENT-21-NOTES.md#DR-6" % "impl-records/skill-evolution"],
        "defeaters": ["the لا is لا النافية (no jussium; indicative verb) → negation particle, no governor role"],
        "abst": "nāhiya-vs-nāfiya genuinely ambiguous → named ambiguity; verb still keeps its root either way",
        "readiness": "projector_ready",
        "proj": {"condition": "the particle is لا الناهية before a muḍāriʿ",
                 "projection": "the لا governs the verb into jussive; the verb is content keeping its root",
                 "guards": ["nāhiya-vs-nāfiya identification (contextual)", "jussium consequence is deterministic"],
                 "scope": "construction-match"},
        "rels": [("cites", "nahw rich-seg negation-ownership rule (nahw-richseg-negation-owned-by-particle)",
                  "external", "Extends negation-ownership with the jussive-governor consequence of لا الناهية.")],
        "pos": {"locs": ["2:104:6"], "surfaces": ["لا"],
                "case": {"particle": "la_nahiya"},
                "correct": "governor_forces_jussive_verb_is_content", "wrong": "la_folded_no_governor",
                "cite": "2:104 لَا تَقُولُوا۟: لا الناهية governs the verb into jussive; تقولوا keeps root ق و ل"},
        "ctl": {"locs": ["2:6:7"], "surfaces": ["لا"],
                "case": {"particle": "la_nafiya"},
                "correct": "negation_particle_no_jussium",
                "cite": "2:6 لَا يُؤْمِنُونَ: لا النافية — no jussium (verb stays marfūʿ); the rule branches"},
    },
    {
        "sid": "nahw-ha-tanbih-not-pronoun", "skill": "nahw", "rule": "ha_tanbih",
        "fam": "vocative-particle-guard", "phen": "ha-tanbih-false-pronoun",
        "scope": ("ها in the vocative compounds يا+أيها / أيتها is حرف تنبيه (attention particle) — its own "
                  "vocative element, NEVER an attached pronoun clitic. Whitelist the يا+أيها/أيتها vocative "
                  "compounds."),
        "ev": [q("8:65:1"), q("12:78:2"), "%s/C5-reviewerA.md" % IMPL],
        "defeaters": ["the ها is not in a يا+أيها/أيتها vocative frame → it may be a genuine pronoun clitic"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "surface family is يا+أيها/أيتها and the segment under test is ها",
                 "projection": "PREVENT the pronoun-clitic projection; type ها as حرف تنبيه (vocative element)",
                 "guards": ["vocative-compound whitelist", "not applied to ها outside the vocative frame"],
                 "scope": "construction-match"},
        "rels": [("cites", "nahw rich-seg negation/particle ownership rule (nahw-richseg-negation-owned-by-particle)",
                  "external", "A vocative-particle analog: ها التنبيه is a particle, not a pronoun.")],
        "pos": {"locs": ["8:65:1"], "surfaces": ["يأيها"],
                "case": {"surface_family": "ya_ayyuha", "segment": "ها"},
                "correct": "ha_tanbih_particle", "wrong": "ha_pronoun_clitic",
                "cite": "8:65:1 يَٰٓأَيُّهَا: ها is حرف تنبيه (MCP), never a swallowed attached pronoun"},
        "ctl": {"locs": ["7:43:33"], "surfaces": ["أورثتموها"],
                "case": {"surface_family": "verb_plus_object", "segment": "ها"},
                "correct": "ha_pronoun_clitic",
                "cite": "7:43:33 أُورِثْتُمُوهَا: here ها IS a genuine object pronoun — the rule branches"},
    },
    {
        "sid": "nahw-fused-preposition-closed-class-floor", "skill": "nahw", "rule": "fused_prep",
        "fam": "function-word-floor", "phen": "fused-preposition-parked-in-review",
        "scope": ("Fused jarr+pronoun surfaces (فِيهَا, عَلَيْكُم(ُ), مِنْهُ) are closed-class function words on "
                  "the affirm/function-word floor; the deterministic closed-class set must include the "
                  "fused-preposition inventory so they are affirmed, not parked in review."),
        "ev": [q("2:30:12"), q("2:74:30"), "%s/W13-reviewerA-round2.md" % IMPL],
        "defeaters": ["the surface is a content token (verb-shaped root / documented noun) → not the function floor"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "surface ∈ fused-preposition+pronoun inventory (فيها/عليكم/منه/…)",
                 "projection": "affirm on the function-word floor; do not park in review",
                 "guards": ["deterministic closed-class membership", "content-token exclusion"],
                 "scope": "surface-match"},
        "rels": [("extends", "so-adjacency-not-ownership", "registry",
                  "Extends the function-word floor with fused jarr+pronoun surfaces.")],
        "pos": {"locs": ["2:30:12"], "surfaces": ["فيها"],
                "case": {"surface": "فيها"},
                "correct": "affirm_function_floor", "wrong": "parked_review",
                "cite": "2:30:12 فِيهَا = فِي (jarr) + هاء: a closed-class function surface — affirm, don't park"},
        "ctl": {"locs": ["9:107:3"], "surfaces": ["مسجدا"],
                "case": {"surface": "مسجدا", "is_content_token": True},
                "correct": "not_function_floor",
                "cite": "9:107:3 مَسْجِدًا is a content noun (root س ج د) — not the function floor; the rule branches"},
    },
    {
        "sid": "nahw-lam-qasam-nun-tawkid-finite", "skill": "nahw", "rule": "lam_qasam",
        "fam": "lam-qasam-tawkid", "phen": "lam-qasam-infinitive-leak",
        "scope": ("لام جواب القسم + نون التوكيد welds to a FINITE energic verb that stays مرفوع "
                  "(فَلَيُبَتِّكُنَّ → 'they will surely cut off'), NEVER a dictionary infinitive ('to slit'). "
                  "It is distinguished from لام الأمر — which forces the muḍāriʿ into jussive (majzūm) — by "
                  "mood: marfūʿ + energic vs jussive. Blocking the dictionary-infinitive leak is the guard."),
        "ev": [q("4:119:4"), q("2:282:11"), "%s/C1-reviewerA.md" % IMPL,
               "%s/INCREMENT-21-NOTES.md#DR-1-DR-6" % "impl-records/skill-evolution"],
        "defeaters": ["the lām is لام الأمر (verb majzūm, no energic nūn) → jussive command, a different type",
                      "no نون التوكيد / no oath frame → not جواب القسم"],
        "abst": "lām genuinely ambiguous between qasam and amr → resolve by mood (marfūʿ vs majzūm), never leak an infinitive",
        "readiness": "projector_ready",
        "proj": {"condition": "لام + نون التوكيد on an energic verb in an oath-answer frame",
                 "projection": "gloss as a finite energic future (marfūʿ); BLOCK any dictionary-infinitive/maṣdar gloss",
                 "guards": ["mood distinction qasam(marfūʿ) vs amr(majzūm)", "infinitive-leak ban is deterministic"],
                 "scope": "construction-match"},
        "rels": [("cites", "sarf rich-seg occurrence-committed rule (sarf-richseg-occurrence-voice-mood-aspect-form-committed)",
                  "external", "A committed finite energic reading forbids the dictionary-infinitive leak.")],
        "pos": {"locs": ["4:119:4"], "surfaces": ["فليبتكن"],
                "case": {"lam_type": "lam_qasam"},
                "correct": "finite_energic_marfu_no_infinitive", "wrong": "infinitive_leak_labeled_amr",
                "cite": "4:119:4 فَلَيُبَتِّكُنَّ: لام جواب القسم + نون التوكيد, finite energic marfūʿ → 'they will surely cut off', not 'to slit'"},
        "ctl": {"locs": ["2:282:11"], "surfaces": ["وليكتب"],
                "case": {"lam_type": "lam_al_amr"},
                "correct": "jussive_amr",
                "cite": "2:282:11 وَلْيَكْتُب: لام الأمر forces jussive (majzūm) — the mood distinguishes it from qasam"},
    },
]


def build_registry_rows():
    rows = []
    for r in RULES:
        sid = r["sid"]
        sk = r["skill"]
        pos_ex = [_exid("INC21", sid, r["pos"]["locs"][0])]
        for i, f in enumerate(r.get("extra", [])):
            pos_ex.append(_exid("INC21X%d" % (i + 1), sid, f["locs"][0]))
        ctl_ex = _exid("INC21CTL", sid, r["ctl"]["locs"][0])
        rels = [{"type": t, "target_id": tid, "target_kind": kind, "note": note}
                for (t, tid, kind, note) in r["rels"]]
        proj = {"readiness": r["readiness"]}
        proj.update(r["proj"])
        row = {
            "skill_rule_id": sid,
            "skill": sk,
            "skill_version": sk + "@2.1",
            "status": "candidate",
            "fact_family": r["fam"],
            "scope": r["scope"],
            "evidence_addresses": r["ev"],
            "positive_examples": pos_ex,
            "negative_or_boundary_examples": [ctl_ex],
            "defeaters": r["defeaters"],
            "abstention_condition": r["abst"],
            "gate": "@2.1-candidate:redfirst+branch-proven",
            "code_references": ["tools/skill_fixtures/skill_rules_increment21.py"],
            "test_references": ["tools/skill_fixtures/test_skill_fixtures_increment21.py"],
            "relationships": rels,
            "provenance": {
                "origin": "increment-21-calibration-cycle",
                "cycle": "2026-07-12",
                "source": SKEV,
                "projector_readiness": r["readiness"],
                "phenomenon": r["phen"],
            },
            "projector": proj,
        }
        rows.append(row)
    return rows


def build_fixture_rows():
    fixtures = []
    for r in RULES:
        sid = r["sid"]
        for kind, red in (("pos", True), ("ctl", False)):
            f = r[kind]
            ex = _exid("INC21" if red else "INC21CTL", sid, f["locs"][0])
            fx = {
                "fixture_id": ("inc21-%s-%s" % (sid, "pos" if red else "ctl")),
                "example_id": ex,
                "rule_id": sid,
                "rule": r["rule"],
                "skill_version": r["skill"] + "@2.1",
                "phenomenon": r["phen"],
                "canonical_locations": f["locs"],
                "surfaces": f.get("surfaces", []),
                "case": f["case"],
                "correct_label": f["correct"],
                "redfirst": red,
                "citation": f["cite"],
            }
            if red:
                fx["wrong_label"] = f["wrong"]
            fixtures.append(fx)
        for i, f in enumerate(r.get("extra", [])):
            ex = _exid("INC21X%d" % (i + 1), sid, f["locs"][0])
            fx = {
                "fixture_id": ("inc21-%s-x%d" % (sid, i + 1)),
                "example_id": ex,
                "rule_id": sid,
                "rule": r["rule"],
                "skill_version": r["skill"] + "@2.1",
                "phenomenon": r["phen"],
                "canonical_locations": f["locs"],
                "surfaces": f.get("surfaces", []),
                "case": f["case"],
                "correct_label": f["correct"],
                "redfirst": True,
                "citation": f["cite"],
                "wrong_label": f["wrong"],
            }
            fixtures.append(fx)
    return fixtures


def _dump(path, rows):
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return body


def _read(path):
    if not os.path.exists(path):
        return None
    return open(path, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify committed == regenerated (exit 1 on drift)")
    a = ap.parse_args()
    reg_rows = build_registry_rows()
    fx_rows = build_fixture_rows()
    reg_body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in reg_rows)
    fx_body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in fx_rows)
    if a.check:
        drift = []
        if _read(REGISTRY_OUT) != reg_body:
            drift.append("rule-registry-increment-21.jsonl")
        if _read(FIXTURES_OUT) != fx_body:
            drift.append("skill_fixtures_increment21.jsonl")
        if drift:
            print("DRIFT (regenerate via _build_increment21.py): " + ", ".join(drift))
            return 1
        print("increment-21 builder: committed artifacts match regeneration (%d rules, %d fixtures)"
              % (len(reg_rows), len(fx_rows)))
        return 0
    _dump(REGISTRY_OUT, reg_rows)
    _dump(FIXTURES_OUT, fx_rows)
    sarf = sum(1 for r in reg_rows if r["skill"] == "sarf")
    nahw = sum(1 for r in reg_rows if r["skill"] == "nahw")
    print("wrote %s (%d rules: %d sarf, %d nahw)" % (os.path.relpath(REGISTRY_OUT, REPO), len(reg_rows), sarf, nahw))
    print("wrote %s (%d fixtures)" % (os.path.relpath(FIXTURES_OUT, REPO), len(fx_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
