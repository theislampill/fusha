#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioural + mutation gates for the naḥw rule consumers (A2).

Existence checks prove a file is committed; they do not prove a rule is load-bearing. This suite is the
behavioural half: every assertion here fails if the rule DATA changes, if a wrong conclusion is accepted, if a
right conclusion is accepted with an absent/wrong governor reason, if a rival analysis is dropped, or if an
iʿrāb decision is auto-resolved.

Five mutation classes are exercised on real rule/eval content (not toy fixtures):

  M1 wrong conclusion        — the discriminator must not return the sibling reading.
  M2 wrong/absent reason     — a correct case/mood with no (or a non-licensing) governor must FAIL from
                               structured evidence; a caller-supplied `reasoning_ok=True` must not rescue it.
  M3 absent governor         — `mood_basis` exemptions are the ONLY governor-free path, and only for rafʿ.
  M4 lost rival              — context-sense / iḍāfa / PP-attachment alternatives must survive resolution.
  M5 unsafe auto-resolution  — no iʿrāb-sensitive path may return auto_safe; never_auto_resolve is terminal.

Data-drivenness is proven by MUTATING the loaded rule dict in memory and asserting the consumer's answer
changes (a hard-coded consumer would be immune). Run:  python tools/test_nahw_behavioural_gates.py
"""
import copy
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_nahw_context_rules as CTX  # noqa: E402
from tools import fusha_nahw_gate_rules as GATE  # noqa: E402
from tools import fusha_nahw_particle_rules as PR  # noqa: E402
from tools import validate_two_vote_artifacts as VTV  # noqa: E402
from tools.fusha_nahw_particle_rules import mint_fixture_observation  # noqa: E402
from tools.grade_grammar_reasoning import (  # noqa: E402
    grade, grade_structured, grade_two_vote, mint_fixture_vote, project_vote,
)

# ROUND-8: a two-vote gate is satisfied only by two REAL contract-valid, independent, fully agreeing vote
# artifacts. Every fixture below that grades under such a gate carries this pair, and its claim is PROJECTED
# from vote A, so the conclusion, case, governor, fact type, reason key and source address all come from the
# evidence rather than from a hand-written literal. `two_vote_done` no longer appears anywhere.
GATE_VOTE_A = mint_fixture_vote(0, reason_key="lam-jarr-fused-majrur-kasra", conclusion="genitive",
                                case_mood="genitive", relation="preposition_governs_genitive",
                                worklist_id="wl-gates-a", fact_type="case_assignment",
                                vote_id="vote:gates:a")
GATE_VOTE_B = mint_fixture_vote(1, reason_key="lam-jarr-fused-majrur-kasra", conclusion="genitive",
                                case_mood="genitive", relation="preposition_governs_genitive",
                                worklist_id="wl-gates-b", fact_type="case_assignment",
                                vote_id="vote:gates:b")
GATE_ADDR = GATE_VOTE_A["occurrence"]["quran_loc"]
GATE_CLAIM = dict(project_vote(GATE_VOTE_A), two_vote_evidence=[GATE_VOTE_A, GATE_VOTE_B])

FAILS = []


def check(name, cond, detail=""):
    if cond:
        return True
    FAILS.append("%s%s" % (name, (" — " + detail) if detail else ""))
    return False


# ---------------------------------------------------------------------------
# M1 — wrong conclusion: the homograph discriminator must never emit the sibling
# ---------------------------------------------------------------------------
def test_m1_wrong_conclusion():
    # positives: the discriminating mark is present and the correct branch fires
    pos = [
        ("مِنَ", "man_vs_min", "B", "preposition"),
        ("وَمِنَ", "man_vs_min", "B", "preposition"),
        ("مَن", "man_vs_min", "A", "pronoun"),
        ("لَمْ", "lam_vs_lima", "A", "negative"),
        ("لِمَ", "lam_vs_lima", "B", "interrogative"),
        ("لَمَّا", "lima_vs_lamma", "A", "temporal"),
        ("لِّمَا", "lima_vs_lamma", "B", "relative"),
        ("أَنَّ", "an_vs_inna", "A", "hamza-above"),
        ("إِنَّ", "an_vs_inna", "B", "hamza-below"),
        ("كُلًّا", "kull_vs_kalla", "A", "quantifier"),
        ("كَلَّا", "kull_vs_kalla", "B", "deterrent"),
        ("نِعْمَ", "nima_vs_naam", "A", "praise verb"),
        ("نَعَمْ", "nima_vs_naam", "B", "affirmation"),
        ("أَنِّي", "anni_vs_anna", "A", "that I"),
        ("أَنَّى", "anni_vs_anna", "B", "how"),
    ]
    for surface, rule_id, branch, why in pos:
        r = PR.resolve_particle_homograph(surface)
        check("M1 %s -> %s/%s (%s)" % (surface, rule_id, branch, why),
              r.get("rule_id") == rule_id and r.get("branch") == branch and r.get("decision") == "resolved",
              json.dumps(r, ensure_ascii=False))

    # negatives: undiacritized input MUST stay pending, never default to the common reading
    for surface, rule_id, pending_reason in [("من", "man_vs_min", "homograph_haraka"),
                                             ("لم", "lam_vs_lima", "homograph_haraka"),
                                             ("لما", "lima_vs_lamma", "homograph_haraka"),
                                             ("ان", "an_vs_inna", "seat_collapsed"),
                                             ("كلا", "kull_vs_kalla", "homograph_haraka"),
                                             ("نعم", "nima_vs_naam", "homograph_haraka")]:
        r = PR.resolve_particle_homograph(surface)
        check("M1-neg bare %s stays pending" % surface,
              r.get("decision") == "pending" and r.get("rule_id") == rule_id
              and r.get("pending_reason") == pending_reason, json.dumps(r, ensure_ascii=False))

    # adversarial: the verb مَنَّ (shadda on nūn) is neither pronoun nor preposition
    r = PR.resolve_particle_homograph("مَنَّ")
    check("M1-adv مَنَّ is excluded from the من family", r.get("branch") is None
          and r.get("decision") == "pending", json.dumps(r, ensure_ascii=False))

    # adversarial: the proclitic must not move the decision letter (وَمَن ≠ وَمِنَ)
    a = PR.resolve_particle_homograph("وَمَن")
    b = PR.resolve_particle_homograph("وَمِنَ")
    check("M1-adv proclitic does not move the content letter",
          a.get("branch") == "A" and b.get("branch") == "B")

    # forbidden-transition backstop: a resolved مِن may never carry the مَن gloss
    v = PR.forbidden_gloss_violations("مِنَ", "and whoever")
    check("M1 forbidden gloss مِن->'whoever' is rejected", any(x["id"] == "min_not_man" for x in v),
          json.dumps(v, ensure_ascii=False))
    check("M1 forbidden gloss carries correct_instead + reason_code",
          bool(v) and v[0].get("correct_instead") and v[0].get("reason_code"))
    check("M1 licit مِن gloss is not rejected", not PR.forbidden_gloss_violations("مِنَ", "from / among"))
    check("M1 forbidden gloss لَمْ->'why' is rejected",
          any(x["id"] == "lam_not_lima" for x in PR.forbidden_gloss_violations("لَمْ", "why")))

    # data-drivenness: mutate the rule gloss in memory; the consumer must follow the data
    rules = PR.load_particle_rules()
    mutated = copy.deepcopy(rules)
    for rule in mutated["rules"]:
        if rule["id"] == "man_vs_min":
            rule["decision_if_B"]["gloss"] = "MUTATED-GLOSS"
    r = PR.resolve_particle_homograph("مِنَ", rules=mutated)
    check("M1 mutation: consumer reads the gloss from rule DATA", r.get("gloss") == "MUTATED-GLOSS",
          json.dumps(r, ensure_ascii=False))


# ---------------------------------------------------------------------------
# M2 — right conclusion, wrong/absent reason must FAIL from structured evidence
# ---------------------------------------------------------------------------
def test_m2_wrong_reason():
    case = {"id": "T-M2", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
            "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]}
    base = dict(GATE_CLAIM, governor={"surface": "بِ", "governor_type": "preposition"})

    ok = grade_structured(case, base)
    check("M2 honest claim passes", ok["pass"], json.dumps(ok, ensure_ascii=False))

    # right ending, WRONG reason key -> FAIL
    bad = dict(base, reason_key="inna-ism-nasb-fatha")
    r = grade_structured(case, bad)
    check("M2 right answer + wrong reason_key FAILS", not r["pass"] and r["block_reason"],
          json.dumps(r, ensure_ascii=False))

    # ROUND-3: a registered reason key and a registered governor that are individually valid but form an
    # INVALID licensing pair. A fused-preposition GENITIVE reason cannot ride a verb_object governor.
    r = grade_structured(case, dict(base, governor={"governor_type": "verb_object"}))
    check("M2 individually-valid reason + governor that form an invalid pair FAIL",
          not r["pass"] and r.get("reason_defect") == "reason_tuple_governor_mismatch",
          json.dumps(r, ensure_ascii=False))
    r = grade_structured({"id": "T-M2b", "required_gate": "two_vote_required",
                          "expected_conclusion": "accusative",
                          "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]},
                         dict(base, conclusion="accusative", case_mood="accusative",
                              governor={"governor_type": "verb_object"}))
    check("M2 the reproduced fused-genitive/accusative/verb_object tuple FAILS",
          not r["pass"] and r.get("reason_defect") == "reason_tuple_conclusion_mismatch",
          json.dumps(r, ensure_ascii=False))
    # a registered key with no repository tuple authority routes pending rather than being invented
    r = grade_structured({"id": "T-M2c", "required_gate": "two_vote_required",
                          "expected_conclusion": "nominative",
                          "expected_reason_keys": ["mudari3-raf3-tajarrud-thubut-nun"]},
                         dict(base, conclusion="nominative", case_mood="nominative",
                              reason_key="mudari3-raf3-tajarrud-thubut-nun", fact_type=None))
    check("M2 a reason key with no tuple authority routes pending",
          not r["pass"] and r.get("reason_defect") == "reason_tuple_unavailable",
          json.dumps(r, ensure_ascii=False))

    # right ending, governor type that does NOT license the case -> still fails closed
    bad = dict(base, governor={"surface": "ضَرَبَ", "governor_type": "verb_subject"})
    r = grade_structured(case, bad)
    check("M2 non-licensing governor fails closed",
          not r["pass"] and r.get("reason_defect") == "reason_tuple_governor_mismatch",
          json.dumps(r, ensure_ascii=False))

    # THE load-bearing property: a caller-supplied boolean may not rescue a bad reason
    bad = dict(base, reason_key=None, reasoning_ok=True)
    r = grade_structured(case, bad)
    check("M2 caller-supplied reasoning_ok=True does NOT rescue an absent reason", not r["pass"],
          json.dumps(r, ensure_ascii=False))
    check("M2 caller boolean is reported as ignored", r.get("caller_boolean_ignored") is True)

    # a case with no structured reason contract fails closed (never silently passes)
    r = grade_structured({"id": "T", "required_gate": "two_vote_required",
                          "expected_conclusion": "genitive"}, base)

    # ADVERSARIAL: mutate ONLY the conclusion; omit ONLY the expected conclusion
    r = grade_structured(case, dict(base, conclusion="accusative"))
    check("M2 a mutated conclusion alone fails closed",
          not r["pass"] and r.get("conclusion_defect") == "conclusion_mismatch")
    r = grade_structured({"id": "T-NOEXP", "required_gate": "two_vote_required",
                          "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]}, base)
    check("M2 a case with no expected conclusion fails closed",
          not r["pass"] and r.get("conclusion_defect") == "expected_conclusion_absent")
    r = grade_structured(case, dict(base, conclusion="banana"))
    check("M2 an arbitrary conclusion fails closed",
          not r["pass"] and r.get("conclusion_defect") == "conclusion_mismatch")
    r = grade_structured({"id": "T", "required_gate": "two_vote_required",
                          "expected_conclusion": "genitive"}, base)
    check("M2 missing expected_reason_keys fails closed",
          not r["pass"] and r.get("reason_defect") == "reason_contract_absent"
          and r.get("conclusion_defect") is None, json.dumps(r, ensure_ascii=False))

    # the legacy boolean grader must still block right-answer/wrong-reasoning (unchanged contract)
    r = grade({"id": "L", "required_gate": "auto_safe"},
              {"final_ok": True, "reasoning_ok": False, "evidence_cited": True, "source_address": "x"})
    check("M2 legacy grade() still blocks right answer + wrong reasoning", not r["pass"])


# ---------------------------------------------------------------------------
# M3 — absent governor
# ---------------------------------------------------------------------------
def test_m3_absent_governor():
    case = {"id": "T-M3", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
            "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]}
    claim = dict(GATE_CLAIM, governor=None)
    r = grade_structured(case, claim)
    check("M3 case asserted with no governor -> governor_not_justified",
          not r["pass"] and r.get("reason_defect") == "governor_not_justified",
          json.dumps(r, ensure_ascii=False))

    # naḥw@2.4 `mood_basis=tajarrud` is a CANDIDATE increment. The RELEASED path must still require a
    # governor, so the candidate exemption may never authorize a pass here.
    tj = {"id": "T-TJ", "required_gate": "two_vote_required", "expected_conclusion": "accusative",
          "expected_reason_keys": ["inna-ism-nasb-fatha"]}
    tajarrud = dict(GATE_CLAIM, conclusion="accusative", case_mood="accusative", mood_basis="tajarrud",
                    reason_key="inna-ism-nasb-fatha", governor=None)
    r = grade_structured(tj, tajarrud)
    check("M3 the released path does NOT implement the @2.4 tajarrud exemption",
          not r["pass"] and r.get("reason_defect") == "governor_not_justified",
          json.dumps(r, ensure_ascii=False))
    # the candidate may be MEASURED, but a measurement can never authorize a decision
    r = grade_structured(tj, dict(tajarrud, candidate_increment="nahw@2.4"))
    check("M3 a candidate-increment measurement never passes",
          not r["pass"] and r.get("candidate_measurement") is True, json.dumps(r, ensure_ascii=False))

    # a governed mood_basis without a governor is a contract error
    bad = grade_structured(tj, dict(GATE_CLAIM, conclusion="accusative", case_mood="accusative",
                                    mood_basis="governed", reason_key="inna-ism-nasb-fatha",
                                    governor=None))
    check("M3 mood_basis=governed without a governor FAILS", not bad["pass"])


# ---------------------------------------------------------------------------
# M4 — lost rival: alternatives must survive
# ---------------------------------------------------------------------------
def test_m4_lost_rival():
    MORPH = {"pos": "verb", "derived_form": "I", "voice": "active", "lemma": "قَدَرَ"}
    alt = CTX.context_sense_alternatives("يَقْدِرُ", MORPH)
    check("M4 contronym keeps >= 2 candidate readings", len(alt.get("candidate_glosses") or []) >= 2,
          json.dumps(alt, ensure_ascii=False))
    check("M4 contronym is NOT auto-resolved by the consumer", alt.get("decision") == "pending",
          json.dumps(alt, ensure_ascii=False))
    check("M4 contronym rival table is preserved verbatim", len(alt.get("rival_readings") or []) >= 2)
    check("M4 contronym decision_table prose is marked documentary",
          alt.get("prose_conditions_are_documentary") is True)

    # iḍāfa / PP-attachment alternatives from the state-transition consumer
    t = PR.transition("noun_noun_to_idafa")
    check("M4 unfired iḍāfa transition holds pending", t.get("decision") == "pending"
          and t.get("pending_reason") == "idafa_ambiguous", json.dumps(t, ensure_ascii=False))
    check("M4 unfired transition keeps its alternatives", bool(t.get("unresolved_alternatives")),
          json.dumps(t, ensure_ascii=False))
    # ADVERSARIAL: a bare caller boolean is an assertion, never a source-addressed observation
    t = PR.transition("noun_noun_to_idafa", evidence=True)
    check("M4 bare trigger boolean cannot fire a transition",
          t.get("decision") == "pending" and t.get("evidence_defect") == "caller_label",
          json.dumps(t, ensure_ascii=False))
    IDEV = mint_fixture_observation("second_noun_majrur_first_stripped", source_address="quran:2:2:1",
                                    quran_loc="2:2", word=1, surface="ذَٰلِكَ", target_kind="state",
                                    target_value="noun_noun_to_idafa")
    t = PR.transition("noun_noun_to_idafa", evidence=IDEV, at="quran:2:2:1",
                          from_state="noun_followed_by_noun")
    check("M4 typed evidence yields a CANDIDATE, never a resolution",
          t.get("decision") == "candidate" and t.get("requires_two_vote") is True
          and t.get("gate") != "auto_safe", json.dumps(t, ensure_ascii=False))
    t = PR.transition("noun_noun_to_idafa", evidence=dict(IDEV, evidence_class="heuristic"),
                      at="quran:2:2:1", from_state="noun_followed_by_noun")
    check("M4 heuristic evidence cannot fire a transition",
          t.get("evidence_defect") == "evidence_class_not_source_addressed",
          json.dumps(t, ensure_ascii=False))

    # polyseme quarantine: the blocked sibling sense may never leak onto the token
    v = CTX.polyseme_quarantine_violations("ٱلْمُلْك", "angels")
    check("M4 blocked sibling sense (angels) is rejected on ٱلْمُلْك", bool(v),
          json.dumps(v, ensure_ascii=False))
    check("M4 correct sense is not rejected",
          not CTX.polyseme_quarantine_violations("ٱلْمُلْك", "sovereignty / dominion"))

    # referent guard keeps rivals until the referent is supplied
    r = CTX.referent_gloss("حَلِيمٌ")
    check("M4 unidentified referent -> pending(referent_unresolved)",
          r.get("decision") == "pending" and r.get("pending_reason") == "referent_unresolved",
          json.dumps(r, ensure_ascii=False))
    # ADVERSARIAL: a caller-supplied referent label is not evidence
    r = CTX.referent_gloss("حَلِيمٌ", "human")
    check("M4 caller referent label cannot resolve a referent",
          r.get("decision") == "pending" and r.get("evidence_defect") == "caller_label",
          json.dumps(r, ensure_ascii=False))
    r = CTX.referent_gloss("حَلِيمٌ", mint_fixture_observation(
        "martian", source_address="quran:2:26:20", quran_loc="2:26", word=20, surface="حَلِيمٌ",
        target_kind="referent", target_value="halim_referent"), at="quran:2:26:20")
    check("M4 unsupported referent label is rejected",
          r.get("evidence_defect") == "observation_off_vocabulary", json.dumps(r, ensure_ascii=False))
    EV = mint_fixture_observation("human", source_address="quran:2:26:20", quran_loc="2:26", word=20,
                                  surface="حَلِيمٌ", target_kind="referent", target_value="halim_referent")
    r = CTX.referent_gloss("حَلِيمٌ", EV, at="quran:2:26:20")
    check("M4 typed referent evidence -> CANDIDATE at human/scholar routing",
          r.get("decision") == "candidate" and r.get("gate") == "human_source_review_required"
          and "forbear" in (r.get("gloss_candidate") or "").lower(), json.dumps(r, ensure_ascii=False))
    check("M4 referent rivals are preserved", len(r.get("candidate_glosses") or []) >= 2)

    # data-drivenness: drop a rival from the rule data; the consumer must notice
    rules = CTX.load_context_sense_rules()
    mutated = copy.deepcopy(rules)
    for rule in mutated["rules"]:
        if rule["id"] == "qadara_contronym":
            rule["candidate_glosses"] = rule["candidate_glosses"][:1]
    alt = CTX.context_sense_alternatives("يَقْدِرُ", MORPH, rules=mutated)
    check("M4 mutation: dropping a rival changes the consumer output",
          len(alt.get("candidate_glosses") or []) == 1, json.dumps(alt, ensure_ascii=False))

    # ADVERSARIAL: a surface key is not a lexeme - Form II and passive must not inherit the Form I table
    check("M4 Form II يُقَدِّرُ does not inherit the Form I contronym table",
          CTX.context_sense_alternatives("يُقَدِّرُ", dict(MORPH, derived_form="II"))
          .get("morphology_defect") == "morphology_mismatch:derived_form")
    check("M4 passive أُتِيَ does not inherit the active أَتَى table",
          CTX.context_sense_alternatives("أُتِيَ", {"pos": "verb", "derived_form": "I",
                                                    "voice": "passive", "lemma": "أَتَى"})
          .get("morphology_defect") == "morphology_mismatch:voice")
    check("M4 absent morphology never authorizes a same-surface match",
          CTX.context_sense_alternatives("يَقْدِرُ").get("pending_reason") == "identity_not_established")

    # ADVERSARIAL: reordering the referent table must not re-pair a class with another row gloss
    rg = copy.deepcopy(CTX.load_referent_guard_rules())
    for rule in rg["rules"]:
        if rule.get("id") == "salihan_proper_vs_common":
            rule["decision_table"].reverse()
    ev = mint_fixture_observation("deed", source_address="quran:2:26:20", quran_loc="2:26", word=20,
                                  surface="صَٰلِحًا", target_kind="referent",
                                  target_value="salihan_proper_vs_common")
    r = CTX.referent_gloss("صَٰلِحًا", ev, at="quran:2:26:20", rules=rg)
    check("M4 reordering the referent table keeps the deed class on the deed gloss",
          "righteous" in (r.get("gloss_candidate") or "").lower(), json.dumps(r, ensure_ascii=False))
    check("M4 the referent class map is total and injective", not CTX.class_coverage_errors())

    # ADVERSARIAL: removing the target role must be visible in the structured rival set
    st = copy.deepcopy(PR.load_state_rules())
    target_role = None
    for row in st["transitions"]:
        if row["id"] == "noun_noun_to_idafa":
            target_role = row["to_nahw_role"]
            row["to_nahw_role"] = None
    t = PR.transition("noun_noun_to_idafa", evidence=IDEV, at="quran:2:2:1",
                      from_state="noun_followed_by_noun", rules=st)
    check("M4 removing the target role is visible in the rival set",
          all(x.get("role") != target_role for x in t.get("unresolved_alternatives") or []),
          json.dumps(t, ensure_ascii=False))


# ---------------------------------------------------------------------------
# M5 — unsafe auto-resolution
# ---------------------------------------------------------------------------
def test_m5_unsafe_auto_resolution():
    for rule_id in GATE.irab_rule_ids():
        g = GATE.irab_rule_gate(rule_id)
        check("M5 iʿrāb safety rule %s is never auto_safe" % rule_id, g != "auto_safe", g)

    # the consumer must STRENGTHEN, never weaken, relative to the gates SSOT
    for topic in GATE.topic_ids():
        eff = GATE.effective_gate(topic=topic)
        declared = GATE.topic_gate(topic)
        check("M5 effective gate for %s is >= declared" % topic,
              GATE.gate_rank(eff) >= GATE.gate_rank(declared), "%s vs %s" % (eff, declared))

    check("M5 proper_vs_common is lifted to the SSOT human-review tier",
          GATE.effective_gate(topic="proper_vs_common") == "human_source_review_required",
          GATE.effective_gate(topic="proper_vs_common"))

    # never_auto_resolve is terminal: no combination may relax it
    check("M5 never_auto_resolve is terminal",
          GATE.effective_gate(triggers=["norm_only_match", "irab"]) == "never_auto_resolve")
    check("M5 reasoning_path_wrong forces never_auto_resolve",
          GATE.effective_gate(triggers=["reasoning_path_wrong"]) == "never_auto_resolve")

    # a never_auto case can never pass the structured grader, however good the evidence
    r = grade_structured({"id": "NA", "required_gate": "never_auto_resolve",
                          "expected_conclusion": "genitive",
                          "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]},
                         dict(GATE_CLAIM))
    check("M5 never_auto_resolve blocks even a perfect claim", not r["pass"], json.dumps(r, ensure_ascii=False))

    # the rule files themselves must be trigger-vocabulary clean against the SSOT
    errs = GATE.validate_rule_files()
    check("M5 gate rule files are SSOT-consistent", not errs, json.dumps(errs, ensure_ascii=False))

    # data-drivenness: weaken a gate in memory; the consumer must refuse it
    rules = GATE.load_irab_safety_gates()
    mutated = copy.deepcopy(rules)
    mutated["rules"][0]["gate"] = "auto_safe"
    errs = GATE.validate_rule_files(irab_gates=mutated)
    check("M5 mutation: an auto_safe iʿrāb gate is rejected", bool(errs),
          json.dumps(errs, ensure_ascii=False))


# ---------------------------------------------------------------------------
# two-vote agreement: conclusion AND reason
# ---------------------------------------------------------------------------
def test_two_vote_agreement():
    """Full artifact validation is delegated to tools/validate_two_vote_artifacts.py; this asserts it holds."""
    KJ = "lam-jarr-fused-majrur-kasra"
    case = {"id": "TV", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
            "expected_reason_keys": [KJ, "inna-ism-nasb-fatha"]}

    def v(index, **kw):
        base = dict(reason_key=KJ, conclusion="genitive", case_mood="genitive",
                    relation="preposition_governs_genitive", fact_type="case_assignment",
                    worklist_id="worklist-%s" % ("a" if index == 0 else "b"))   # external worker record
        base.update(kw)
        return mint_fixture_vote(index, **base)

    a, b = v(0), v(1)
    r = grade_two_vote(case, a, b)
    check("TV two independent agreeing artifacts reach agreement", r["pass"],
          json.dumps(r, ensure_ascii=False)[:400])
    check("TV agreement is a CANDIDATE state and never certifies",
          r.get("certified") is False and r.get("route") == "candidate_agreed_pending_certification")

    # ROUND-3: the established validator's own vote contract must be enforced, not a local subset
    for label, pair in (("malformed vote ids", (dict(a, vote_id="a"), dict(b, vote_id="b"))),
                        ("empty segmentation", (a, dict(b, segmentation=[]))),
                        ("bad timestamp", (a, dict(b, timestamp="yesterday"))),
                        ("occurrence mismatch",
                         (a, dict(b, occurrence=dict(b["occurrence"], surface="OTHER"))))):
        r = grade_two_vote(case, pair[0], pair[1])
        check("TV %s is rejected by the shared artifact validator" % label,
              not r["pass"] and r.get("disagreement") == "invalid_artifact",
              json.dumps(r, ensure_ascii=False)[:200])

    # ADVERSARIAL: cloned votes and every shared-provenance axis
    check("TV cloned votes are rejected", not grade_two_vote(case, a, dict(a))["pass"])
    for label, mutated in (
            ("cloned provenance", dict(b, reviewer=dict(a["reviewer"]))),
            ("reviewer_id", dict(b, reviewer=dict(b["reviewer"],
                                                  reviewer_id=a["reviewer"]["reviewer_id"]))),
            ("lane", dict(b, reviewer=dict(b["reviewer"], lane=a["reviewer"]["lane"]))),
            ("vote_id", dict(b, vote_id=a["vote_id"]))):
        r = grade_two_vote(case, a, mutated)
        check("TV shared %s breaks independence" % label,
              not r["pass"] and r.get("disagreement") == "not_independent")
    # ROUND-10: A2's OWN independence check no longer treats a shared ENGINE as dependence. Two genuinely
    # independent reviewers can both work through the same CLI surface; demanding different engine strings
    # proves nothing and only rewards falsifying the field. Reviewer identity, lane and vote id still differ.
    from tools.grade_grammar_reasoning import vote_independence_errors  # noqa: PLC0415
    _same_engine = dict(b, reviewer=dict(b["reviewer"], engine=a["reviewer"]["engine"]))
    check("TV A2's own independence check does NOT flag a shared CLI engine",
          vote_independence_errors(a, _same_engine) == [],
          repr(vote_independence_errors(a, _same_engine)[:1]))
    # TRUTHFUL RESIDUAL: the CANONICAL contract (tools/validate_two_vote_artifacts.py, not editable in this
    # lane) still rejects a shared engine at the artifact level, so the pair is refused there rather than by
    # A2. The refusal is attributed to the canonical contract, and relaxing it belongs to the owner lane.
    _r = grade_two_vote(case, a, _same_engine)
    check("TV a shared engine is refused by the CANONICAL contract, not by A2's own independence rule",
          not _r["pass"] and "artifact_contract_invalid" in (_r.get("block_reason") or "")
          and "engine" in (_r.get("block_reason") or ""),
          json.dumps(_r.get("block_reason"), ensure_ascii=False)[:160])

    check("TV an unregistered reason key cannot reach agreement",
          not grade_two_vote(case, v(0, reason_key="tv-expected"),
                             v(1, reason_key="tv-expected"))["pass"])
    check("TV a nonsense conclusion cannot reach agreement",
          not grade_two_vote({"id": "TV-NC", "required_gate": "two_vote_required",
                              "expected_reason_keys": [KJ]},
                             v(0, conclusion="banana"), v(1, conclusion="banana"))["pass"])
    r = grade_two_vote(case, a, v(1, reason_key="inna-ism-nasb-fatha"))
    check("TV same conclusion + different reason routes to arbitration",
          not r["pass"] and r.get("route") == "arbitration")
    check("TV a single vote never satisfies the gate", not grade_two_vote(case, a, None)["pass"])

    # ROUND-10: `worklist_id` is NOT a canonical vote_record property — qamus/schemas/two-vote-artifact
    # .schema.json is additionalProperties:false and does not carry it, so writing one into a vote makes the
    # artifact schema-INVALID and A2 cannot prove worklist separation from the artifact at all. Separate
    # worklist provenance, CLI version, actual-model proof, a frozen artifact hash and reviewer isolation
    # remain EXTERNAL worker-record requirements for the later owner two-vote lane.
    check("TV a worklist_id written into a vote record makes the artifact schema-invalid",
          not grade_two_vote(case, dict(a, worklist_id="wl-a"), b)["pass"])
    from tools.grade_grammar_reasoning import (  # noqa: PLC0415
        canonical_two_vote_envelope, two_vote_artifact_defect,
    )
    check("TV the A2 pair forms a CANONICAL, schema-valid two-vote artifact",
          two_vote_artifact_defect(canonical_two_vote_envelope(a, b)) is None,
          repr(two_vote_artifact_defect(canonical_two_vote_envelope(a, b))))
    check("TV an extra field in a vote record is refused by the canonical schema",
          two_vote_artifact_defect(canonical_two_vote_envelope(a, dict(b, fact_type="x"))) is not None)
    check("TV a third vote exceeds the canonical maxItems",
          two_vote_artifact_defect(dict(canonical_two_vote_envelope(a, b), votes=[a, b, a])) is not None)
    for label, row in (("genuine v1 fixture", VTV.sample_verified_row()),
                       ("genuine v1.1 fixture", VTV.sample_verified_row_v11())):
        check("TV the canonical %s validates" % label, two_vote_artifact_defect(row) is None,
              repr(two_vote_artifact_defect(row)))

    # human/source review remains a DISTINCT gate
    hcase = {"id": "TV-HR", "required_gate": "human_source_review_required",
             "expected_conclusion": "genitive", "expected_reason_keys": [KJ]}
    claim = dict(GATE_CLAIM)
    r = grade_structured(hcase, claim)
    check("human review is not satisfied by a validated two-vote pair",
          not r["pass"] and r.get("human_review_defect") == "human_review_absent")
    r = grade_structured(hcase, dict(claim, human_review=True))
    check("a boolean is not a human review",
          not r["pass"] and r.get("human_review_defect") == "human_review_not_a_record")

    # ROUND-4: a human review must be BOUND to the exact claim it is offered for
    # ROUND-10: the subject is the exact WRITTEN surface under decision, bound to the artifact occurrence
    SURFACE = GATE_VOTE_A["occurrence"]["surface"]
    bound_claim = dict(claim, subject=SURFACE)
    good_review = {"review_id": "hr:round4:1", "reviewer_id": "human-1",
                   "source_address": GATE_ADDR, "subject": SURFACE, "decision": "approved",
                   "timestamp": "2026-07-30T00:00:00Z", "reviewed_conclusion": "genitive",
                   "reviewed_reason_key": KJ}
    r = grade_structured(hcase, dict(bound_claim, human_review=good_review))
    check("a complete review bound to the claim is accepted", r["pass"],
          json.dumps(r, ensure_ascii=False)[:250])
    # ROUND-8: independence against an UNKNOWN claimant is not independence — the comparison would be
    # between a named reviewer and nobody, which always differs and therefore always passed.
    r = grade_structured(hcase, dict(bound_claim, reviewer_id=None, human_review=good_review))
    check("a review whose claimant identity is absent is rejected",
          not r["pass"] and r.get("human_review_defect") == "human_review_claimant_identity_absent",
          json.dumps({"got": r.get("human_review_defect")}))
    for label, mutated, want in (
            ("another valid address", dict(good_review, source_address="quran:2:26:20"),
             "human_review_address_not_bound"),
            ("another subject", dict(good_review, subject="OTHER"), "human_review_subject_not_bound"),
            ("another conclusion", dict(good_review, reviewed_conclusion="accusative"),
             "human_review_conclusion_not_bound"),
            ("another reason key", dict(good_review, reviewed_reason_key="inna-ism-nasb-fatha"),
             "human_review_reason_not_bound"),
            ("a malformed timestamp", dict(good_review, timestamp="yesterday"),
             "human_review_timestamp_invalid"),
            ("a malformed review id", dict(good_review, review_id="1"), "human_review_id_invalid"),
            ("the claimant reviewing themselves",
             dict(good_review, reviewer_id=bound_claim["reviewer_id"]),
             "human_review_not_independent")):
        r = grade_structured(hcase, dict(bound_claim, human_review=mutated))
        check("a review with %s is rejected" % label,
              not r["pass"] and r.get("human_review_defect") == want,
              json.dumps({"got": r.get("human_review_defect"), "want": want}))


def test_runner_contract():
    """ROUND-3: the eval runner must not be silently neuterable, and --json must emit only JSON."""
    import subprocess

    import tools.run_nahw_evals as RUN

    def hover_errors():
        errs, stats = [], {}
        RUN.run_hover_context(errs, stats)
        return errs, stats

    original = PR.resolve_particle_homograph
    try:
        for label, fake in (
                ("no-op consumer", lambda *a, **k: {}),
                ("wrong pending reason", lambda *a, **k: dict(original(*a, **k), **(
                    {"pending_reason": "WRONG"} if original(*a, **k).get("decision") == "pending" else {}))),
                ("wrong gloss", lambda *a, **k: dict(original(*a, **k), gloss="WRONG")),
                ("wrong reading", lambda *a, **k: dict(original(*a, **k), reading="WRONG"))):
            RUN.PR.resolve_particle_homograph = fake
            errs, _stats = hover_errors()
            check("runner detects a %s" % label, bool(errs), "no errors raised")
    finally:
        RUN.PR.resolve_particle_homograph = original

    # quarantine authority: a fabricated status and an unrelated packet may not suppress a comparison
    data = RUN._json(os.path.join(RUN.EVAL_DIR, "hover-context-eval.json"))
    row = next(c for c in data["cases"] if c["id"] == "min_preposition_safe")
    row.update({"contract_status": "totally-made-up", "packet": "TP-DOC-LINKCHECK",
                "quarantine_reason": "because"})
    original_json = RUN._json
    try:
        RUN._json = lambda path: data if "hover" in path else original_json(path)
        errs, stats = hover_errors()
        check("a fabricated quarantine status is rejected",
              any("closed quarantine vocabulary" in e for e in errs), json.dumps(errs[:2]))
        row["contract_status"] = "no_consumer"
        errs, stats = hover_errors()
        check("an unrelated packet cannot authorise a quarantine",
              any("not a valid quarantine authority" in e or "no typed QUARANTINE-BINDING" in e
                  for e in errs), json.dumps(errs[:2]))
    finally:
        RUN._json = original_json

    # ROUND-4: a quarantine may excuse an unimplemented consumer, NEVER a weaker gate
    state = RUN._json(os.path.join(RUN.EVAL_DIR, "nahw-state-machine-eval.json"))
    weakened = next(c for c in state["cases"] if c["id"] == "in_nafiya_negating")
    weakened["gate"] = "two_vote_required"
    original_json = RUN._json
    try:
        RUN._json = lambda path: state if "state-machine" in path else original_json(path)
        errs, _stats = [], {}
        RUN.run_state_machine(errs, _stats)
        check("a quarantined row cannot hide a weakened gate",
              any("quarantine" in e and "gate" in e for e in errs), json.dumps(errs[:3]))
    finally:
        RUN._json = original_json

    # ROUND-4/7: a fabricated packet whose text merely mentions bank+row+status authorises nothing.
    # ROUND-7 isolation: the fixture lives in a UNIQUE temporary packet root that is injected for the probe.
    # It never writes a fixed repository path, never destroys a pre-existing file, and is safe under
    # concurrent runs.
    import tempfile

    fake_id = "TP-NAHW-A2-FAKE-PROBE"
    hover = RUN._json(os.path.join(RUN.EVAL_DIR, "hover-context-eval.json"))
    target = next(c for c in hover["cases"] if c["id"] == "min_preposition_safe")
    target.update({"contract_status": "no_consumer", "packet": fake_id, "quarantine_reason": "x"})
    original_packet_dir = RUN.PACKET_DIR
    import shutil

    with tempfile.TemporaryDirectory(prefix="a2-packet-probe-") as tmp:
        # copy the GENUINE packets in, so the only bogus authority in the probe root is the fabricated one and
        # the other 12 quarantines must still resolve normally
        for _fn in os.listdir(original_packet_dir):
            if _fn.endswith(".json"):
                shutil.copyfile(os.path.join(original_packet_dir, _fn), os.path.join(tmp, _fn))
        with open(os.path.join(tmp, "%s.json" % fake_id), "w", encoding="utf-8") as fh:
            fh.write('{"note": "hover-context min_preposition_safe no_consumer"}')
        try:
            RUN.PACKET_DIR = tmp
            RUN._PACKET_BINDINGS.clear()
            RUN._json = lambda path: hover if "hover" in path else original_json(path)
            errs, stats = hover_errors()
            check("a fabricated packet cannot authorise a quarantine",
                  any("not a valid quarantine authority" in e or "no typed QUARANTINE-BINDING" in e
                      for e in errs), json.dumps(errs[:3]))
            check("the fabricated quarantine did not suppress the row",
                  stats["hover-context"]["quarantined"] == 12, str(stats["hover-context"]["quarantined"]))
        finally:
            RUN.PACKET_DIR = original_packet_dir
            RUN._json = original_json
            RUN._PACKET_BINDINGS.clear()
    check("the probe never created a fixed repository packet path",
          not os.path.exists(os.path.join(original_packet_dir, "%s.json" % fake_id)))

    # ROUND-4: the bank's own gloss_if_safe is bound and a mutation must fail
    hover2 = RUN._json(os.path.join(RUN.EVAL_DIR, "hover-context-eval.json"))
    next(c for c in hover2["cases"]
         if c["id"] == "min_preposition_safe")["gloss_if_safe"] = "COMPLETELY WRONG GLOSS"
    try:
        RUN._json = lambda path: hover2 if "hover" in path else original_json(path)
        errs, _stats = [], {}
        RUN.run_hover_context(errs, _stats)
        check("a wrong gloss_if_safe is detected",
              any("gloss_if_safe" in e for e in errs), json.dumps(errs[:3]))
    finally:
        RUN._json = original_json

    # ROUND-4: the LLX forbidden expectation is typed, so unrelated non-empty text must fail
    llx = RUN._jsonl(os.path.join(RUN.EVAL_DIR, "largelexicon-function-collision-safety.jsonl"))
    llx[0]["forbidden"] = "totally unrelated text"
    original_jsonl = RUN._jsonl
    try:
        RUN._jsonl = lambda path: llx if "largelexicon" in path else original_jsonl(path)
        errs, _stats = [], {}
        RUN.run_llx_collision(errs, _stats)
        check("an unrelated LLX forbidden value is detected",
              any("bank forbidden" in e for e in errs), json.dumps(errs[:3]))
    finally:
        RUN._jsonl = original_jsonl

    # --json emits exactly one parseable document and nothing else
    proc = subprocess.run([sys.executable, os.path.join(_REPO, "tools", "run_nahw_evals.py"), "--json"],
                          capture_output=True, cwd=_REPO)
    stdout = proc.stdout.decode("utf-8", errors="replace")
    try:
        payload = json.loads(stdout)
        parsed = True
    except ValueError:
        payload, parsed = None, False
    check("--json stdout parses as exactly one JSON document", parsed, repr(stdout[-120:]))
    if parsed:
        check("--json payload carries stats, errors and ok",
              {"stats", "errors", "ok"} <= set(payload))
        check("--json exit code matches the payload",
              proc.returncode == (0 if payload["ok"] else 1))


# ---------------------------------------------------------------------------
# negation + attachment consumers (domain-specific, not one generic resolver)
# ---------------------------------------------------------------------------
def test_domain_consumers():
    # negation: the homograph must be settled BEFORE the negation effect (standing order)
    n = PR.negation_effect("لَمْ")
    check("negation لَمْ resolves to jussive past", n.get("decision") == "resolved"
          and "jussive" in (n.get("governs") or "").lower(), json.dumps(n, ensure_ascii=False))
    n = PR.negation_effect("لم")
    check("negation on an unresolved homograph stays pending", n.get("decision") == "pending"
          and n.get("pending_reason") == "homograph_haraka", json.dumps(n, ensure_ascii=False))
    n = PR.negation_effect("مَا")
    check("negation مَا is never defaulted to negation", n.get("decision") == "pending"
          and n.get("pending_reason") == "maa_category_unresolved", json.dumps(n, ensure_ascii=False))
    n = PR.negation_effect("لَا")
    check("negation لَا without the governed verb's mood stays pending",
          n.get("decision") == "pending" and n.get("pending_reason") == "negation_scope",
          json.dumps(n, ensure_ascii=False))

    # pronoun attachment by host POS (nahw/rules/pronoun-attachment-rules.json, GAP-N3)
    check("attachment: verb host enclitic is never possessive",
          "NOT possessive" in CTX.attachment_role("V"), CTX.attachment_role("V"))
    check("attachment: noun host enclitic is possessive", "possessive" in CTX.attachment_role("N").lower())
    check("attachment: preposition host is an object of the preposition",
          "preposition" in CTX.attachment_role("P").lower())
    check("attachment: tanwīn-alef is not the pronoun نا",
          CTX.is_forbidden_attachment("قُرْءَانًا", "نا", "N") is not None)
    check("attachment: a genuine possessive is allowed",
          CTX.is_forbidden_attachment("أَعْمَالُنَا", "نا", "N") is None)
    check("attachment: ambiguous host POS routes to two-vote",
          "ambiguous host POS" in CTX.attachment_two_vote_triggers())

    # preposition + pronoun rendering by referent
    r = CTX.preposition_pronoun_render("بِهِ", "thing")
    check("pp-pronoun: a caller referent label never renders",
          r.get("decision") == "pending" and r.get("evidence_defect") == "caller_label",
          json.dumps(r, ensure_ascii=False))
    r = CTX.preposition_pronoun_render("بِهِ", mint_fixture_observation(
        "thing", source_address="quran:2:26:20", quran_loc="2:26", word=20, surface="بِهِ",
        target_kind="referent", target_value="bihi"), at="quran:2:26:20")
    check("pp-pronoun: typed evidence yields a CANDIDATE with rivals kept",
          r.get("decision") == "candidate" and "it" in (r.get("gloss_candidate") or "")
          and len(r.get("renderings") or []) >= 3, json.dumps(r, ensure_ascii=False))
    r = CTX.preposition_pronoun_render("بِهِ", None)
    check("pp-pronoun: unknown referent -> pending(referent_unresolved)",
          r.get("decision") == "pending" and r.get("pending_reason") == "referent_unresolved",
          json.dumps(r, ensure_ascii=False))
    check("pp-pronoun: إِلَيْنَا must never take the root ل ي ن",
          CTX.root_guard_violation("إِلَيْنَا", "ل ي ن") is not None)
    check("pp-pronoun: the correct root is not flagged",
          CTX.root_guard_violation("إِلَيْنَا", "أ ل ي") is None)

    # proper-noun guard: no verb gloss on a name
    check("referent guard: مُحَمَّد may not be glossed 'to praise'",
          bool(CTX.proper_noun_verb_violations("مُحَمَّد", "to praise")))
    check("referent guard: the name itself is fine",
          not CTX.proper_noun_verb_violations("مُحَمَّد", "Muḥammad"))


def test_quarantine_authority_is_exact():
    """ROUND-8: the quarantined row sets and their packets' typed bindings must be EXACTLY equal both ways.

    Cardinality is not authority. Every mutation below preserves a plausible-looking quarantine (several
    preserve the exact count) and must still be rejected. The committed table is never mutated on disk: each
    probe passes its own table into quarantine_authority_errors(), and the packet-schema probe runs against a
    unique temporary packet root with the genuine packets copied in.
    """
    import io
    import shutil
    import tempfile

    import tools.run_nahw_evals as RUN

    cases = RUN._json(os.path.join(RUN.EVAL_DIR, "nahw-state-machine-eval.json"))["cases"]
    hover = RUN._json(os.path.join(RUN.EVAL_DIR, "hover-context-eval.json"))["cases"]
    base = RUN.QUARANTINE_AUTHORITY

    check("committed quarantine authority is exactly equal for state-machine",
          RUN.quarantine_authority_errors("state-machine", cases) == [],
          repr(RUN.quarantine_authority_errors("state-machine", cases)[:2]))
    check("committed quarantine authority is exactly equal for hover-context",
          RUN.quarantine_authority_errors("hover-context", hover) == [],
          repr(RUN.quarantine_authority_errors("hover-context", hover)[:2]))
    check("the committed quarantine sets are exactly 9 state rows + 12 hover rows",
          len([r for r in cases if r.get("contract_status")]) == 9
          and len([r for r in hover if r.get("contract_status")]) == 12)

    def mutate(**kw):
        table = [dict(b) for b in base]
        table[0] = dict(table[0], **kw)
        return tuple(table)

    rows0 = tuple(base[0]["rows"])
    swapped = ("man_relative_in_sila",) + rows0[1:]          # same cardinality, different membership
    for label, table in (
            ("a duplicate binding", tuple([dict(b) for b in base] + [dict(base[0], rows=("kulla_vs_kalla",))])),
            ("a stale extra binding", mutate(rows=rows0 + ("man_relative_in_sila",))),
            ("a wrong uncovered property", mutate(property="consumer_branch")),
            ("a wrong permitted disposition", mutate(disposition="excuse_gate")),
            ("a wrong authorizing packet id", mutate(packet="TP-NAHW-A2-TYPED-WR-BANK")),
            ("a row-set swap that preserves the total", mutate(rows=swapped)),
    ):
        check("%s is rejected" % label,
              RUN.quarantine_authority_errors("state-machine", cases, table) != [])
    check("a row-set swap really preserves the cardinality", len(swapped) == len(rows0))

    # a packet reaching into a bank it does not own is not authority, however well-formed the binding reads
    cross = [b for b in base if b["bank"] != "state-machine"]
    cross.append({"bank": "state-machine", "packet": "TP-NAHW-A2-HOVER-KEY-SEAT",
                  "status": "state_vocab_pending", "property": "state_axis_pair",
                  "disposition": "excuse_semantic_consumer", "rows": rows0})
    check("a cross-bank binding is rejected",
          RUN.quarantine_authority_errors("state-machine", cases, tuple(cross)) != [])

    # a duplicate row id in the bank must be caught BEFORE any set comparison can be satisfied
    check("a duplicate row id in the bank is rejected",
          RUN.quarantine_authority_errors("state-machine", list(cases) + [dict(cases[0])]) != [])

    # SCHEMA authority: a packet that is not a valid task packet authorises nothing, even when its
    # QUARANTINE-BINDING sentence is syntactically perfect.
    with tempfile.TemporaryDirectory(prefix="a2-authority-probe-") as tmp:
        for name in os.listdir(RUN.PACKET_DIR):
            if name.endswith(".json"):
                shutil.copyfile(os.path.join(RUN.PACKET_DIR, name), os.path.join(tmp, name))
        plausible = {
            "packet_id": "TP-NAHW-A2-PROBE-MINIMAL",
            "candidate_population": {"selection_rule":
                                     "QUARANTINE-BINDING bank=state-machine; status=state_vocab_pending; "
                                     "rows=kulla_vs_kalla; property=state_axis_pair; "
                                     "disposition=excuse_semantic_consumer"},
            "non_deployment": {"status": "NOT_DEPLOYED"},
        }
        genuine = json.load(io.open(os.path.join(tmp, "TP-NAHW-A2-STATE-VOCAB.json"), encoding="utf-8"))
        near_miss = dict(genuine, packet_id="TP-NAHW-A2-PROBE-NEARMISS")
        near_miss["acceptance_tests"] = [dict(near_miss["acceptance_tests"][0], pass_condition="exit 0")]
        for pid, body in (("TP-NAHW-A2-PROBE-MINIMAL", plausible), ("TP-NAHW-A2-PROBE-NEARMISS", near_miss)):
            io.open(os.path.join(tmp, pid + ".json"), "w", encoding="utf-8").write(
                json.dumps(body, ensure_ascii=False, indent=2))
        saved_dir, saved_cache = RUN.PACKET_DIR, dict(RUN._PACKET_BINDINGS)
        try:
            RUN.PACKET_DIR = tmp
            RUN._PACKET_BINDINGS.clear()
            for pid in ("TP-NAHW-A2-PROBE-MINIMAL", "TP-NAHW-A2-PROBE-NEARMISS"):
                bindings, errs = RUN.packet_quarantine_bindings(pid)
                check("%s: a schema-invalid packet authorises nothing" % pid,
                      bindings == {} and any("schema-valid" in e for e in errs), repr(errs[:1]))
            RUN._PACKET_BINDINGS.clear()
            bindings, errs = RUN.packet_quarantine_bindings("TP-NAHW-A2-STATE-VOCAB")
            check("a genuine schema-valid packet still authorises its 9 rows",
                  len(bindings) == 9 and errs == [], repr(errs[:1]))
        finally:
            RUN.PACKET_DIR = saved_dir
            RUN._PACKET_BINDINGS.clear()
            RUN._PACKET_BINDINGS.update(saved_cache)
    check("the authority probe never created a fixed repository packet path",
          not os.path.exists(os.path.join(RUN.PACKET_DIR, "TP-NAHW-A2-PROBE-MINIMAL.json")))


def test_r10_exact_occurrence_and_surface():
    """ROUND-10 A: an occurrence is ONE written word at ONE exact coordinate, bound by its exact surface."""
    from tools.grade_grammar_reasoning import (  # noqa: PLC0415
        exact_surface_equal, occurrence_defect, source_address_defect, surface_binding_defect,
    )
    for label, address in (("an ayah-only address", "quran:2:284"),
                           ("word index 0", "quran:2:284:0"),
                           ("a qamus: address", "qamus:entry:1234"),
                           ("a wbw: address", "wbw:2:284:1"),
                           ("a leading-zero coordinate", "quran:002:284:1"),
                           ("an empty address", ""),
                           ("a word beyond the token count", "quran:2:284:99")):
        check("R10 %s is not an occurrence" % label, occurrence_defect(address) is not None,
              repr(occurrence_defect(address)))
    check("R10 a genuine word occurrence is accepted", occurrence_defect("quran:2:284:1") is None)
    check("R10 the claim source address inherits the word-level rule",
          source_address_defect({"source_address": "quran:2:284"}) == "source_address_not_word_level"
          and source_address_defect({"source_address": "quran:2:284:1"}) is None)

    # exact written surface — nothing folded away
    for left, right, why in ((u"\u0645\u064e\u0646", u"\u0645\u0650\u0646\u064e", "man vs mina"),
                             (u"\u0645\u064e\u0627", u"\u0645\u064e\u0651\u0627", "ma vs mma"),
                             (u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c",
                              u"\u062d\u064e\u0644\u0650\u064a\u0645\u064d", "halimun vs halimin"),
                             (u"\u0645\u064e\u0646", u"\u0648\u064e\u0627\u0644\u0644\u064e\u0651"
                              u"\u0647\u064f", "an unrelated token")):
        check("R10 exact surface: %s must differ" % why, not exact_surface_equal(left, right))
        check("R10 exact surface: %s is not bound" % why,
              surface_binding_defect(left, right) == "surface_not_bound")
    import unicodedata as _ud
    _s = u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c"
    check("R10 NFC-equal encodings of the SAME characters compare equal",
          exact_surface_equal(_ud.normalize("NFD", _s), _ud.normalize("NFC", _s)))
    check("R10 tatweel is not erased for evidence binding",
          not exact_surface_equal(u"\u0645\u064e\u0646", u"\u0645\u064e\u0640\u0646"))

    # typed observation: cross-occurrence replay and surface mismatch
    ev = PR.mint_fixture_observation("human", source_address="quran:2:26:20", quran_loc="2:26", word=20,
                                     surface=u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c",
                                     target_kind="referent", target_value="halim")
    for label, kw, want in (
            ("cross-occurrence replay",
             {"surface": u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c", "at": "quran:2:284:1"},
             "occurrence_not_current"),
            ("a surface differing only in the final tanwin",
             {"surface": u"\u062d\u064e\u0644\u0650\u064a\u0645\u064d", "at": "quran:2:26:20"},
             "surface_mismatch"),
            ("an ayah-only caller address",
             {"surface": u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c", "at": "quran:2:26"},
             "caller_occurrence_invalid"),
            ("caller word index 0",
             {"surface": u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c", "at": "quran:2:26:0"},
             "caller_occurrence_invalid")):
        value, defect, _art = PR.typed_observation(ev, **kw)
        check("R10 typed observation refuses %s" % label, value is None and defect == want,
              "defect=%s" % defect)
    value, defect, _art = PR.typed_observation(
        ev, surface=u"\u062d\u064e\u0644\u0650\u064a\u0645\u064c", at="quran:2:26:20")
    check("R10 the genuine occurrence still validates", value is not None, "defect=%s" % defect)

    # transition() validates the caller surface and the caller address
    t = PR.transition("noun_noun_to_idafa", at="quran:2:284:1",
                      surface=u"\u0630\u064e\u0670\u0644\u0650\u0643\u064e",
                      from_state="noun_followed_by_noun")
    check("R10 transition() refuses a surface unrelated to its from-state", t.get("decision") == "pending")
    t = PR.transition("noun_noun_to_idafa", at="quran:2:284", surface=None,
                      from_state="noun_followed_by_noun")
    check("R10 transition() refuses an ayah-only caller address", t.get("decision") == "pending")


def test_r10_homograph_fails_closed():
    """ROUND-10 C: a contradicted or missing mark is uncertainty, never positive evidence."""
    for surface in (u"\u0625\u0650\u0646\u0651\u0650\u064a",        # إِنِّي
                    u"\u0645\u064f\u0646",                             # مُن
                    u"\u0644\u064e\u0645\u064e",                      # لَمَ
                    u"\u0644\u0650\u0645\u0652",                      # لِمْ
                    u"\u0623\u0646",                                    # أن (unvowelled)
                    u"\u0623\u064e\u0646\u0651\u0650\u0649",        # أَنِّى
                    u"\u0623\u064e\u0646\u0651\u064e\u064a",        # أَنَّي
                    u"\u0643\u064e\u0644",                             # كَل
                    u"\u0643\u064f\u0644\u064e\u0627",               # كُلَا
                    u"\u0646\u064e\u0639\u0650\u0645"):              # نَعِم
        res = PR.resolve_particle_homograph(surface)
        check("R10 homograph %s fails closed" % surface,
              res.get("decision") == "pending" and res.get("branch") is None,
              "decision=%s branch=%s" % (res.get("decision"), res.get("branch")))
    for surface in (u"\u0645\u064e\u0646\u0652", u"\u0645\u0650\u0646\u0652",
                    u"\u0644\u064e\u0645\u0652", u"\u0644\u0650\u0645\u064e",
                    u"\u0623\u064e\u0646\u0651\u064e", u"\u0625\u0650\u0646\u0651\u064e"):
        check("R10 the fully marked %s still resolves" % surface,
              PR.resolve_particle_homograph(surface).get("decision") == "resolved")

    # public gloss safety
    for surface, gloss in ((u"\u0645\u0646", "whoever"),
                           (u"\u0625\u0650\u0646\u0651\u0650\u0649", "that I"),
                           (u"\u0625\u0650\u0646\u0651\u064e", "if"),
                           (u"\u0625\u0650\u0646\u0652", "indeed")):
        check("R10 public gloss %s -> %r is refused" % (surface, gloss),
              PR.public_gloss_defect(surface, gloss) is not None,
              repr(PR.public_gloss_defect(surface, gloss)))
    for surface, gloss in ((u"\u0645\u0650\u0646\u0652", "from"),
                           (u"\u0625\u0650\u0646\u0651\u064e", "indeed"),
                           (u"\u0625\u0650\u0646\u0652", "if")):
        check("R10 public gloss %s -> %r is allowed" % (surface, gloss),
              PR.public_gloss_defect(surface, gloss) is None,
              repr(PR.public_gloss_defect(surface, gloss)))

    # local rival lattice
    rules = PR.load_state_rules()
    row = next(r for r in rules["transitions"] if r["id"] == "min_preposition_to_jar_majrur")
    rivals = PR.transition_rivals(row, rules, selected=None, evidence_id="e")
    check("R10 rivals are the transition's LOCAL collision set",
          all(r.get("rival_lattice") == "local:man_vs_min" for r in rivals) and len(rivals) <= 4,
          "n=%d" % len(rivals))
    check("R10 no rival is pre-marked rejected before evidence defeats it",
          all(r["decision_status"] != "rejected_rival" for r in rivals))
    check("R10 rival gates use registered ladder values only",
          all(r["gate"] in ("auto_safe", "two_vote_required", "human_source_review_required",
                            "never_auto_resolve") for r in rivals))
    unbound = next(r for r in rules["transitions"] if r["id"] == "noun_noun_to_idafa")
    blocked = PR.transition_rivals(unbound, rules, selected=None, evidence_id="e")
    check("R10 a transition with no authorized rival lattice preserves an exact blocker",
          len(blocked) == 1 and blocked[0].get("rival_lattice") == "absent" and blocked[0].get("blocker"))


def test_r10_gate_reconciliation():
    """ROUND-10 B4/B5: the required gate reconciles upward and bad trigger sets fail closed."""
    for triggers in (["irab"], ["case_or_mood"], ["referent_sensitive_gloss"], ["reasoning_path_wrong"]):
        got = GATE.reconcile_required_gate("auto_safe", triggers)
        check("R10 caller-declared auto_safe cannot weaken %s" % triggers[0],
              GATE.gate_rank(got) >= GATE.gate_rank("two_vote_required"), got)
    for label, triggers in (("a non-list", "irab"), ("None", None), ("a duplicate", ["irab", "irab"]),
                            ("an unknown trigger", ["not_a_trigger"]), ("a non-string", [1])):
        check("R10 %s trigger set fails closed" % label,
              GATE.reconcile_required_gate("auto_safe", triggers) == "never_auto_resolve")
    check("R10 the committed irab rule-id set is exact", GATE.irab_rule_id_defects() == [])
    _rows = GATE.load_irab_safety_gates()["rules"]
    check("R10 a duplicated irab row is a failure",
          GATE.irab_rule_id_defects({"rules": _rows + [dict(_rows[0])]}) != [])
    check("R10 a dropped irab row is a failure", GATE.irab_rule_id_defects({"rules": _rows[1:]}) != [])


def _r13_pair(vid_a="vote:r13:a", vid_b="vote:r13:b", **kw):
    base = dict(reason_key="lam-jarr-fused-majrur-kasra", conclusion="genitive", case_mood="genitive",
                relation="preposition_governs_genitive", fact_type="case_assignment")
    base.update(kw)
    return (mint_fixture_vote(0, worklist_id="wl-a", vote_id=vid_a, **base),
            mint_fixture_vote(1, worklist_id="wl-b", vote_id=vid_b, **base))


def test_r13_envelope_and_claim_binding():
    """ROUND-13 (1,2,3): envelope equivalence, mandatory surface, nested governor relation."""
    from tools.grade_grammar_reasoning import (  # noqa: PLC0415
        canonical_two_vote_envelope, canonical_vote_difference, two_vote_evidence_defect,
    )
    va, vb = _r13_pair()
    case = {"id": "r13", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
            "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]}
    good = dict(project_vote(va), two_vote_evidence=[va, vb])
    check("R13 a genuine occurrence-bound claim still passes", grade_structured(case, good)["pass"],
          repr(grade_structured(case, good).get("block_reason")))

    # 1. same vote IDs, a DIFFERENT canonical occurrence
    fa, fb = _r13_pair()
    for v in (fa, fb):
        v["occurrence"] = dict(v["occurrence"], quran_loc="quran:2:26:20", wbw_loc="wbw:2:26:20",
                               surface="حَلِيمٌ")
    check("R13 an envelope for another occurrence with the SAME vote ids is refused",
          two_vote_evidence_defect(dict(good, two_vote_artifact=canonical_two_vote_envelope(fa, fb)))
          is not None)
    check("R13 canonical_vote_difference names the differing governed field",
          canonical_vote_difference(va, fa) == "occurrence",
          repr(canonical_vote_difference(va, fa)))
    check("R13 two copies of the same record are the same evidence",
          canonical_vote_difference(va, dict(va)) is None)

    # 2. the exact written surface is mandatory
    stripped = {k: v for k, v in good.items() if k not in ("surface", "subject")}
    check("R13 a claim naming neither surface nor subject fails closed",
          two_vote_evidence_defect(stripped) == "two_vote_claim_surface_absent",
          repr(two_vote_evidence_defect(stripped)))
    check("R13 a mismatched exact surface is refused",
          two_vote_evidence_defect(dict(good, surface="حَلِيمٍ")) == "two_vote_claim_surface_not_bound")

    # 3. the nested governor relation is part of the reason tuple
    check("R13 a REVERSED governor relation is refused (a right label with the wrong reason)",
          two_vote_evidence_defect(dict(good, governor={"governor_type": "idafa"}))
          == "two_vote_claim_governor_relation_not_bound")
    check("R13 a fabricated governor_type is refused",
          two_vote_evidence_defect(dict(good, governor={"governor_type": "not_a_governor"}))
          == "two_vote_claim_governor_relation_not_bound")
    check("R13 an absent governor_type is refused",
          two_vote_evidence_defect(dict(good, governor={})) == "two_vote_claim_governor_type_absent")


def test_r13_transition_surface_and_gates():
    """ROUND-13 (4,5): transition evidence is surface-bound; every public gate API fails closed."""
    def _obs(surface):
        return PR.mint_fixture_observation("second_noun_majrur_first_stripped",
                                           source_address="quran:2:2:1", quran_loc="2:2", word=1,
                                           surface=surface, target_kind="transition",
                                           target_value="min_preposition_to_jar_majrur")

    mismatched = PR.transition("min_preposition_to_jar_majrur", evidence=_obs("مَنْ"),
                               at="quran:2:2:1", surface="مِنَ")
    check("R13 a مَنْ observation cannot fire a مِنَ transition at the same address",
          mismatched.get("decision") == "pending"
          and mismatched.get("evidence_defect") == "surface_mismatch",
          "decision=%s defect=%s" % (mismatched.get("decision"), mismatched.get("evidence_defect")))
    matched = PR.transition("min_preposition_to_jar_majrur", evidence=_obs("مِنَ"),
                            at="quran:2:2:1", surface="مِنَ")
    check("R13 the surface check is the discriminator, not a blanket refusal",
          matched.get("evidence_defect") != "surface_mismatch",
          repr(matched.get("evidence_defect")))

    for label, kw in (("a malformed trigger", {"triggers": ["not_a_trigger"], "declared": "auto_safe"}),
                      ("a duplicate trigger", {"triggers": ["irab", "irab"], "declared": "auto_safe"}),
                      ("a non-string trigger", {"triggers": [1], "declared": "auto_safe"})):
        check("R13 effective_gate(): %s never reduces to auto_safe" % label,
              GATE.effective_gate(**kw) != "auto_safe", GATE.effective_gate(**kw))
    check("R13 effective_gate(): a clean trigger still reconciles upward",
          GATE.gate_rank(GATE.effective_gate(triggers=["irab"], declared="auto_safe"))
          >= GATE.gate_rank("two_vote_required"))
    check("R13 irab_rule_gate(): an unknown rule id holds",
          GATE.gate_rank(GATE.irab_rule_gate("no_such_rule")) >= GATE.gate_rank("two_vote_required"))
    _bad = {"rules": [{"id": "irab_assignment", "gate": "auto_safe", "triggers": ["not_a_trigger"]}]}
    check("R13 irab_rule_gate(): a malformed trigger in the table holds",
          GATE.irab_rule_gate("irab_assignment", _bad) != "auto_safe",
          GATE.irab_rule_gate("irab_assignment", _bad))
    check("R13 irab_rule_gate(): the committed table still resolves every rule",
          all(GATE.irab_rule_gate(r) in ("auto_safe", "two_vote_required",
                                         "human_source_review_required", "never_auto_resolve")
              for r in GATE.irab_rule_ids()))


def test_r13_homographs_rivals_gloss():
    """ROUND-13 (6,7,8): fail-closed homographs, symmetric rivals, context-free gloss refusal."""
    for surface in ("أَنِ", "أَنَ", "إِنِ", "إِنَ", "كَلّ", "نَعَمَ", "نِعْمْ"):
        res = PR.resolve_particle_homograph(surface)
        check("R13 homograph %s fails closed" % surface,
              res.get("decision") == "pending" and res.get("branch") is None,
              "decision=%s branch=%s" % (res.get("decision"), res.get("branch")))
    for surface in ("أَنْ", "أَنَّ", "إِنْ", "إِنَّ", "كَلَّا", "نَعَمْ", "نِعْمَ", "مَنْ", "مِنْ"):
        check("R13 the fully marked %s still resolves" % surface,
              PR.resolve_particle_homograph(surface).get("decision") == "resolved")
    check("R13 light/heavy weight needs an EXPLICIT mark",
          PR.an_family_weight("أَنْ") == "light" and PR.an_family_weight("أَنَّ") == "heavy"
          and PR.an_family_weight("أَن") is None and PR.an_family_weight("أَنِ") is None,
          repr([PR.an_family_weight(x) for x in ("أَنْ", "أَنَّ", "أَن", "أَنِ")]))

    rules = PR.load_state_rules()
    rows = {r["id"]: r for r in rules["transitions"]}
    man = PR.transition_rivals(rows["man_relative_to_mubtada_or_object"], rules, selected=None,
                               evidence_id="e")
    mn = PR.transition_rivals(rows["min_preposition_to_jar_majrur"], rules, selected=None, evidence_id="e")
    man_roles = {r["role"] for r in man}
    min_roles = {r["role"] for r in mn}
    check("R13 a مَن candidate preserves the مِن preposition sibling rival",
          any("مِنْ" in r for r in man_roles), repr(sorted(man_roles))[:90])
    check("R13 sibling rivalry is symmetric across the governed family",
          (man_roles - {rows["man_relative_to_mubtada_or_object"]["to_nahw_role"], "hold:homograph_haraka"})
          == (min_roles - {rows["min_preposition_to_jar_majrur"]["to_nahw_role"],
                           "hold:jar_majrur_ambiguous"}),
          "man=%s min=%s" % (len(man_roles), len(min_roles)))
    check("R13 no rival is pre-marked rejected before evidence defeats it",
          all(r["decision_status"] != "rejected_rival" for r in man + mn))

    for gloss in ("whoever", "who", "he who"):
        check("R13 a context-free gloss مَنْ -> %r is refused" % gloss,
              PR.public_gloss_defect("مَنْ", gloss) == "branch_gloss_is_disjunctive",
              repr(PR.public_gloss_defect("مَنْ", gloss)))
    check("R13 the مِنْ preposition gloss is still allowed (vocalization DOES separate مَن from مِن)",
          PR.public_gloss_defect("مِنْ", "from") is None,
          repr(PR.public_gloss_defect("مِنْ", "from")))


def test_r13_tutor_content_vs_fact():
    """ROUND-13 (9,10): malformed second_check fails closed; a held row is not a learner miss."""
    import tools.fusha_tutor_runtime as TUT  # noqa: PLC0415
    bank = TUT._authored_bank()
    idx = TUT._bank_index(bank)
    row = idx["T2-hardgrammar"]
    payload = {"answer": row["expected_answer"], "reasoning": list(row.get("required_reasoning") or [])}

    for label, bad in (("true", True), ("1", 1), ('"yes"', "yes"), ("[1]", [1]), ("{}", {}),
                       ("0", 0), ("null", None)):
        try:
            g = TUT.grade(row, dict(payload, second_check=bad))
        except Exception as exc:  # noqa: BLE001
            check("R13 malformed second_check %s fails closed without a crash" % label, False,
                  "%s: %s" % (type(exc).__name__, exc))
            continue
        check("R13 malformed second_check %s fails closed without a crash" % label,
              g["two_vote_status"] == "pending" and not g["cleared"], "status=%s" % g["two_vote_status"])

    result = TUT.step(row, None, payload, now_day=0)
    g = result["grade"]
    check("R13 a content-correct held answer is reported as content-mastered",
          g["content_mastered"] is True and g["held_for_fact_gate"] is True and g["cleared"] is False)
    check("R13 the scheduler label is 'held', never 'miss'",
          result["outcome"] == "hold" and not result["event"]["note"].startswith("miss"),
          "%s / %s" % (result["outcome"], result["event"]["note"]))
    check("R13 the held row is not counted as a lapse",
          int(result["state"].get("lapses", 0)) == 0, repr(result["state"].get("lapses")))
    check("R13 a fact hold is not routed to remediation",
          result["event"]["remediation_route"] is None, repr(result["event"]["remediation_route"]))
    progress = TUT.new_progress()
    TUT.apply_event_to_progress(progress, row, result, 1)
    check("R13 a fact hold does not enter progress.missed",
          not any(m["item_id"] == row["id"] for m in progress["missed"]), repr(progress["missed"]))
    # a REAL content miss still lands in missed and still gets remediation
    wrong = TUT.step(row, None, {"answer": "totally wrong", "reasoning": []}, now_day=0)
    TUT.apply_event_to_progress(progress, row, wrong, 2)
    check("R13 a real content miss still lands in missed with a remediation route",
          any(m["item_id"] == row["id"] for m in progress["missed"])
          and wrong["event"]["remediation_route"], repr(wrong["event"]["remediation_route"]))
    # an unclearable fact-held row must not starve unseen content
    prog2 = TUT.new_progress()
    TUT.apply_event_to_progress(prog2, row, TUT.step(row, None, payload, now_day=0), 1)
    nxt, why = TUT.select_next(bank, prog2, now_day=30)
    check("R13 an unclearable fact-held row does not starve unseen content",
          nxt != row["id"] and why == "new_item", "%s / %s" % (nxt, why))


def main():
    for fn in (test_m1_wrong_conclusion, test_m2_wrong_reason, test_m3_absent_governor,
               test_m4_lost_rival, test_m5_unsafe_auto_resolution, test_two_vote_agreement,
               test_runner_contract, test_domain_consumers, test_quarantine_authority_is_exact,
               test_r10_exact_occurrence_and_surface, test_r10_homograph_fails_closed,
               test_r10_gate_reconciliation, test_r13_envelope_and_claim_binding,
               test_r13_transition_surface_and_gates, test_r13_homographs_rivals_gloss,
               test_r13_tutor_content_vs_fact):
        fn()
    if FAILS:
        print("FAIL — %d behavioural gate(s) broke:" % len(FAILS))
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print("PASS — naḥw behavioural gates hold "
          "(M1 wrong conclusion, M2 wrong/absent reason, M3 absent governor, M4 lost rival, "
          "M5 unsafe auto-resolution, two-vote conclusion+reason, domain consumers, "
          "exact two-way quarantine authority, exact occurrence + written-surface binding, "
          "fail-closed homograph selection, upward gate reconciliation, canonical envelope equivalence, "
          "mandatory surface + governor-relation binding, surface-bound transitions, symmetric rivals, "
          "context-free gloss refusal, learner mastery separated from fact readiness)")


if __name__ == "__main__":
    main()
