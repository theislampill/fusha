#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grade a grammar answer on BOTH final answer and reasoning — the GrammarProblems lesson made executable.

The paper's core finding: a model can give the right final answer for the WRONG reason (or a confident wrong
answer). For our pipeline that is unsafe — a correct-looking grammar answer with bad reasoning must NOT export to
a hover gloss or an entry repair. So a grammar-affecting decision passes only when ALL hold:

    final_ok       final answer matches expected
    reasoning_ok   reasoning cites the correct rule/iʿrāb path (not a wrong path that happens to land right)
    evidence_ok    an evidence rung + source-address is cited
    gate_ok        two-vote present when the case requires it

grade() is deterministic over supplied judgments (the model/verifier supplies final/reasoning judgments; this
module enforces the AND-gate). The CLI runs a self-test proving the load-bearing case — right answer + wrong
reasoning => FAIL — and exits non-zero if that property ever breaks.
"""
import os
import re
import sys

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools.fusha_check import resolve_gate
from tools.fusha_governor import GOVERNOR_TYPE_LICENSED_CASES
from tools import validate_two_vote_artifacts as VTV  # the ESTABLISHED two-vote contract
from tools.validate_two_vote_artifacts import (  # never reimplemented here — delegated to
    compact, load_registry, recompute_agreement,
)

# ---------------------------------------------------------------------------
# reason/governor LICENSING TUPLES
# ---------------------------------------------------------------------------
# A registered reason key and a licensing governor are not independent facts. Checking them separately lets a
# fused-preposition GENITIVE reason ride along with case_mood=accusative and governor_type=verb_object, because
# each component is individually valid. A reason key therefore licenses exactly ONE closed tuple:
#
#     reason_key -> (conclusion, case_mood, governor_type, fact_type)
#
# `fact_type` is checked against the repository's own authority: the key's `applicable_fact_types` in
# qamus/skills/reason-key-registry.jsonl. The (conclusion, case_mood, governor_type) triple has no machine
# authority in the repository, so it is enumerated here ONLY for keys whose registry id names its own
# government, each with an explicit citation. Any registered key absent from this table yields
# `reason_tuple_unavailable` and routes pending — the tuple is never inferred from the registry prose.
REASON_TUPLES = {
    "lam-jarr-fused-majrur-kasra": {
        "conclusion": "genitive", "case_mood": "genitive", "governor_type": "preposition",
        "fact_type": "case_assignment",
        "cites": "reason-key-registry#lam-jarr-fused-majrur-kasra (lam al-jarr governs its majrur in jarr)"},
    "inna-ism-nasb-fatha": {
        "conclusion": "accusative", "case_mood": "accusative", "governor_type": "inna_family_ism",
        "fact_type": "case_assignment",
        "cites": "reason-key-registry#inna-ism-nasb-fatha (ism of inna in nasb, sign fatha)"},
    "ma-nafiya-non-operative": {
        "conclusion": "negation", "case_mood": None, "governor_type": None,
        "fact_type": "particle_function",
        "cites": "reason-key-registry#ma-nafiya-non-operative (la 'amal laha: assigns no case and no mood)"},
}
# justification_rule (dependency-candidate-lattice enum) -> governor_type. Anything unmapped stays pending.
JUSTIFICATION_RULE_GOVERNOR_TYPE = {
    "preposition_governs_genitive": "preposition",
    "idafa_governs_genitive": "idafa",
    "verb_governs_subject_nominative": "verb_subject",
    "verb_governs_object_accusative": "verb_object",
    "mubtada_governs_khabar_nominative": "mubtada_khabar",
}

# ---------------------------------------------------------------------------
# structured reason/governor evidence (A2)
# ---------------------------------------------------------------------------
# grade() below takes the reasoning verdict as a caller-supplied boolean. That is enough to encode the
# GrammarProblems AND-gate, but it is NOT evidence: whoever supplies `reasoning_ok=True` decides the outcome.
# grade_structured() closes that hole — it DERIVES the reasoning verdict from the claim's own structure:
#
#   * a `reason_key` that must be REGISTERED in qamus/skills/reason-key-registry.jsonl (the governed vocabulary
#     the two-vote artifact validator already enforces) AND declared by the case's `expected_reason_keys`;
#   * a `governor` whose `governor_type` must LICENSE the asserted case/mood
#     (tools/fusha_governor.GOVERNOR_TYPE_LICENSED_CASES — the same table the dependency lattice uses);
#   * a source address for the claim.
#
# Any caller-supplied `reasoning_ok` is IGNORED and reported, so a boolean can never rescue a bad reason.
#
# RELEASED vs CANDIDATE. naḥw@2.1–@2.4 are candidate increments; owner adjudication is open. The released path
# therefore does NOT implement the @2.4 `mood_basis=tajarrud` governor exemption: a case asserted with no
# governor is `governor_not_justified`, full stop. A caller may pass `candidate_increment="nahw@2.4"` to
# MEASURE the candidate behaviour, but that path can never return pass=True — it returns
# `candidate_measurement=True` with `pass=False`, so a candidate rule can neither authorize a decision nor
# appear as consumed authority in a green release assertion.
CASE_MOOD_ALIASES = {
    "jarr": "genitive", "majrur": "genitive", "genitive": "genitive", "kasra": "genitive",
    "raf3": "nominative", "rafa": "nominative", "marfu": "nominative", "marfoo": "nominative",
    "nominative": "nominative", "damma": "nominative",
    "nasb": "accusative", "mansub": "accusative", "accusative": "accusative", "fatha": "accusative",
    "jazm": "jussive", "majzum": "jussive", "jussive": "jussive",
    "subjunctive": "subjunctive", "none": None, "": None,
}
# Vocabulary only. The exemption itself is NOT implemented in the released path (see above).
CANDIDATE_MOOD_BASIS = {"tajarrud", "default"}
CANDIDATE_INCREMENTS = {"nahw@2.1", "nahw@2.2", "nahw@2.3", "nahw@2.4"}


def normalize_case_mood(value):
    if value is None:
        return None
    return CASE_MOOD_ALIASES.get(str(value).strip().lower(), str(value).strip().lower())


def registered_reason_keys():
    """The governed reason-key vocabulary, loaded from the repository registry (never invented here)."""
    kinds, errors = load_registry()
    return set(kinds.get("reason_key") or ()), list(errors)


_REGISTRY_ROWS = None


def _registry_row(reason_key):
    """The registry row for a key, so `applicable_fact_types` is read from the repository, not restated."""
    global _REGISTRY_ROWS
    if _REGISTRY_ROWS is None:
        _REGISTRY_ROWS = {}
        for _line_no, row in VTV.iter_jsonl(VTV.REGISTRY_PATH):
            if isinstance(row, dict) and row.get("id"):
                _REGISTRY_ROWS[row["id"]] = row
    return _REGISTRY_ROWS.get(reason_key)


def derive_reasoning(case, claim):
    """Derive the reasoning verdict from structured evidence alone.

    Returns (reasoning_ok: bool, defect: str|None). `defect` is a closed vocabulary:
    reason_contract_absent | reason_key_absent | reason_key_unregistered | reason_key_mismatch |
    governor_not_justified | mood_basis_not_licensed | source_address_absent.
    """
    expected = case.get("expected_reason_keys")
    if not expected:
        # No structured reason contract => nothing to check against => fail closed. A case that wants
        # structured grading must declare the registered reason keys that count as the right path.
        return False, "reason_contract_absent"
    reason_key = (claim.get("reason_key") or "").strip()
    if not reason_key:
        return False, "reason_key_absent"
    registered, _reg_errors = registered_reason_keys()
    if reason_key not in registered:
        # An unregistered key is not a reason. This is the same governed vocabulary the two-vote artifact
        # validator enforces, so a fabricated or fixture-derived key can never grade as a correct path.
        return False, "reason_key_unregistered"
    if reason_key not in set(expected):
        return False, "reason_key_mismatch"
    if not compact(claim.get("source_address")):
        return False, "source_address_absent"

    # ---- the reason key must license this exact tuple, not merely exist ----
    tuple_ = REASON_TUPLES.get(reason_key)
    if tuple_ is None:
        # Registered, but the repository gives no machine authority for its (conclusion, case, governor)
        # tuple. Route pending rather than inventing one.
        return False, "reason_tuple_unavailable"
    kinds, _errs = load_registry()
    fact_type = claim.get("fact_type") or tuple_["fact_type"]
    registry_row = _registry_row(reason_key)
    if registry_row is not None and fact_type not in (registry_row.get("applicable_fact_types") or ()):
        return False, "fact_type_not_applicable"
    if fact_type != tuple_["fact_type"]:
        return False, "fact_type_not_applicable"
    if claim.get("conclusion") != tuple_["conclusion"]:
        return False, "reason_tuple_conclusion_mismatch"
    if normalize_case_mood(claim.get("case_mood")) != normalize_case_mood(tuple_["case_mood"]):
        return False, "reason_tuple_case_mismatch"
    claimed_gov = (claim.get("governor") or {}).get("governor_type")
    if tuple_["governor_type"] and not claimed_gov:
        # the case/mood is asserted with no ʿāmil at all — keep the named defect visible
        return False, "governor_not_justified"
    if claimed_gov != tuple_["governor_type"]:
        return False, "reason_tuple_governor_mismatch"

    case_mood = normalize_case_mood(claim.get("case_mood"))
    if case_mood is None:
        return True, None                       # no case/mood asserted => no governor obligation

    basis = (claim.get("mood_basis") or "").strip().lower() or None
    governor = claim.get("governor") or None
    gov_type = (governor or {}).get("governor_type")

    if basis in CANDIDATE_MOOD_BASIS:
        # naḥw@2.4 candidate; NOT released. The released rule still requires a stated governor.
        return False, "governor_not_justified"
    if basis == "governed" and not gov_type:
        return False, "governor_not_justified"
    if basis and basis != "governed":
        return False, "mood_basis_not_licensed"

    # Case/mood is a CONSEQUENCE of a stated governor (nahw/SKILL.md §governor lattice).
    if not gov_type:
        return False, "governor_not_justified"
    licensed = GOVERNOR_TYPE_LICENSED_CASES.get(gov_type)
    if licensed is None:
        return False, "governor_not_justified"           # unrecognised governor type is not evidence
    if case_mood not in licensed:
        return False, "governor_not_justified"           # right ending, governor that cannot assign it
    return True, None


# A two-vote gate and a human/source-review gate are DIFFERENT gates. `two_vote_done` can never satisfy
# `human_source_review_required`: that tier needs a separately validated, source-addressed human-review record.
# A boolean is not a review.
# A human/source review is evidence about ONE claim at ONE address. It must therefore be BOUND to the claim it
# is offered for: same source address, same subject (the exact surface/token under decision), same conclusion
# and same reason key. A valid review of a different address, subject, conclusion or reason is not evidence
# here. Identifier and timestamp must be machine-valid — the timestamp reuses the established two-vote
# artifact contract's own ISO-8601 pattern rather than accepting free text such as "yesterday".
HUMAN_REVIEW_REQUIRED_FIELDS = ("review_id", "reviewer_id", "source_address", "subject", "decision",
                                "timestamp", "reviewed_conclusion", "reviewed_reason_key")
HUMAN_REVIEW_DECISIONS = frozenset({"approved", "rejected", "needs_more_evidence"})
REVIEW_ID_RE = re.compile(r"\Ahr:[A-Za-z0-9._:-]+\Z")


def human_review_defect(claim):
    """Return None when the claim carries a validated human/source-review record BOUND to this claim."""
    record = claim.get("human_review")
    if record is None:
        return "human_review_absent"
    if isinstance(record, bool) or not isinstance(record, dict):
        return "human_review_not_a_record"          # a boolean is not a review
    if any(f not in record or not compact(record.get(f)) for f in HUMAN_REVIEW_REQUIRED_FIELDS):
        return "human_review_incomplete"
    if not REVIEW_ID_RE.match(str(record.get("review_id") or "")):
        return "human_review_id_invalid"
    if not VTV.TIMESTAMP.match(str(record.get("timestamp") or "")):
        return "human_review_timestamp_invalid"
    if record.get("decision") not in HUMAN_REVIEW_DECISIONS:
        return "human_review_decision_invalid"
    if record.get("decision") != "approved":
        return "human_review_not_approved"
    from tools.fusha_check import resolve_address     # lazy: the repository's own address authority
    if resolve_address(record["source_address"]).get("scope") != "in_scope_source_addressed":
        return "human_review_address_not_in_scope"
    # ---- binding to the claim under grading ----
    if compact(record.get("source_address")) != compact(claim.get("source_address")):
        return "human_review_address_not_bound"
    if compact(record.get("subject")) != compact(claim.get("subject")):
        return "human_review_subject_not_bound"
    if compact(record.get("reviewed_conclusion")) != compact(claim.get("conclusion")):
        return "human_review_conclusion_not_bound"
    if compact(record.get("reviewed_reason_key")) != compact(claim.get("reason_key")):
        return "human_review_reason_not_bound"
    if compact(record.get("reviewer_id")) == compact(claim.get("reviewer_id")):
        return "human_review_not_independent"        # the claimant may not be their own reviewer
    return None


def conclusion_defect(case, claim):
    """The case must declare a typed expected conclusion, and the claim must match it EXACTLY."""
    expected = case.get("expected_conclusion")
    if not (isinstance(expected, str) and expected.strip()):
        return "expected_conclusion_absent"
    submitted = claim.get("conclusion")
    if not (isinstance(submitted, str) and submitted.strip()):
        return "conclusion_absent"
    if submitted != expected:
        return "conclusion_mismatch"
    return None


def grade_structured(case, claim):
    """The AND-gate of grade(), with `reasoning_ok` DERIVED from structured reason/governor evidence.

    A caller-supplied `reasoning_ok` is ignored (and reported as such): a boolean is not evidence.
    A `candidate_increment` measurement can never return pass=True.
    The case MUST declare a typed `expected_conclusion`; an arbitrary or absent conclusion fails closed.
    `human_source_review_required` needs its own validated review record — `two_vote_done` cannot substitute.
    """
    caller_boolean_ignored = "reasoning_ok" in claim
    increment = claim.get("candidate_increment")
    reasoning_ok, defect = derive_reasoning(case, claim)
    concl_defect = conclusion_defect(case, claim)
    conclusion_ok = concl_defect is None
    hr_defect = None
    if resolve_gate(case.get("required_gate")) == "human_source_review_required":
        hr_defect = human_review_defect(claim)
    result = grade(case, {"final_ok": conclusion_ok, "reasoning_ok": reasoning_ok,
                          "evidence_cited": claim.get("evidence_cited"),
                          "source_address": claim.get("source_address"),
                          "two_vote_done": claim.get("two_vote_done")})
    result["conclusion_defect"] = concl_defect
    result["human_review_defect"] = hr_defect
    if hr_defect:
        result["pass"] = False
        result["block_reason"] = "human/source review required: %s" % hr_defect
    result["reason_defect"] = defect
    result["reason_key"] = claim.get("reason_key")
    result["derived_reasoning_ok"] = reasoning_ok
    result["caller_boolean_ignored"] = caller_boolean_ignored
    result["candidate_measurement"] = False
    if increment:
        # A candidate increment may be MEASURED, never released. It cannot authorize a pass.
        result["candidate_measurement"] = True
        result["candidate_increment"] = increment
        result["pass"] = False
        note = ("unknown candidate increment %r" % increment) if increment not in CANDIDATE_INCREMENTS else (
            "candidate increment %s is not released; measurement only" % increment)
        result["block_reason"] = note
        return result
    if not result["pass"] and defect and result.get("block_reason") in (
            None, "reasoning wrong (right answer, wrong path => unsafe)"):
        result["block_reason"] = "structured reason evidence rejected: %s" % defect
    return result


# The two-vote contract is owned by tools/validate_two_vote_artifacts.py. This helper DELEGATES the complete
# vote-artifact validation to that module's own validate_vote() — vote-id format, reviewer provenance,
# timestamp, occurrence, segmentation, lexical identity, root, form, conclusion shape, grammatical reason and
# reason key — and only then projects the two votes for agreement. Independence adds engine / reviewer_id /
# lane / vote_id / worklist_id distinctness. TRUTHFUL NOTE: the shared contract does not model a worklist, so
# `worklist_id` is an A2-level requirement layered on top, not a delegated one.
TWO_VOTE_INDEPENDENCE_FIELDS = ("vote_id", "reviewer", "worklist_id")
WORKLIST_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]*\Z")


def vote_artifact_errors(vote_a, vote_b):
    """Full artifact validation for both votes, delegated to the established validator."""
    errors = []
    bundle = vote_a.get("occurrence") if isinstance(vote_a, dict) else None
    for index, vote in enumerate((vote_a, vote_b)):
        VTV.validate_vote(vote, 0, index, bundle, errors)
    return errors


def vote_independence_errors(vote_a, vote_b):
    """Reviewer / engine / lane / vote-id / worklist independence over two fully-validated artifacts."""
    errs = []
    for i, vote in enumerate((vote_a, vote_b)):
        if not isinstance(vote, dict):
            errs.append("votes[%d] must be a vote record object" % i)
            continue
        for field in TWO_VOTE_INDEPENDENCE_FIELDS:
            if field not in vote:
                errs.append("votes[%d] missing %s (independent provenance)" % (i, field))
        if not isinstance(vote.get("reviewer"), dict):
            errs.append("votes[%d].reviewer must be an object" % i)
    if errs:
        return errs
    ra, rb = vote_a["reviewer"], vote_b["reviewer"]
    for field in ("engine", "reviewer_id", "lane"):
        if compact(ra.get(field)) == compact(rb.get(field)):
            errs.append("votes are not independent: both votes share %s %r" % (field, compact(ra.get(field))))
    # A worklist id must be a valid, non-empty canonical identifier BEFORE the two are compared: None,
    # "", whitespace and malformed ids are not "different worklists", they are missing provenance.
    for i, vote in enumerate((vote_a, vote_b)):
        raw = vote.get("worklist_id")
        if not isinstance(raw, str) or not WORKLIST_ID_RE.match(raw):
            errs.append("votes[%d].worklist_id %r is not a valid canonical worklist identifier" % (i, raw))
    if errs:
        return errs
    if vote_a["worklist_id"] == vote_b["worklist_id"]:
        errs.append("votes are not independent: both votes come from worklist %r" % vote_a["worklist_id"])
    if compact(vote_a.get("vote_id")) == compact(vote_b.get("vote_id")):
        errs.append("votes must have distinct vote_ids")
    if vote_a == vote_b:
        errs.append("votes are not independent: the two submissions are identical records")
    return errs


def project_vote(vote):
    """Project a validated vote artifact onto the structured-claim shape grade_structured() grades."""
    conclusion = vote.get("conclusion") or {}
    case_or_mood = conclusion.get("case_or_mood") or {}
    governor = conclusion.get("governor") or {}
    gov_type = JUSTIFICATION_RULE_GOVERNOR_TYPE.get(governor.get("relation"))
    occurrence = vote.get("occurrence") or {}
    value = case_or_mood.get("value")
    return {
        "conclusion": conclusion.get("contextual_function"),
        "case_mood": None if value in (None, "none") else value,
        "mood_basis": case_or_mood.get("mood_basis"),
        "reason_key": vote.get("reason_key"),
        "fact_type": vote.get("fact_type"),
        "governor": {"governor_type": gov_type} if gov_type else None,
        "evidence_cited": True,
        "source_address": occurrence.get("quran_loc"),
        "human_review": vote.get("human_review"),
        "reviewer_id": (vote.get("reviewer") or {}).get("reviewer_id"),
        "two_vote_done": True,
    }


def grade_two_vote(case, vote_a, vote_b):
    """Two-vote agreement over CONCLUSION and registered REASON KEY — never over English wording.

    This helper NEVER certifies. Agreement routes to `candidate_agreed_pending_certification`; only
    tools/certify_typed_fact.py certifies, and only from a validated two-vote artifact. Substantive
    disagreement becomes arbitration and is never majority-voted (charter section 7.11).
    """
    if not vote_a or not vote_b:
        return {"pass": False, "disagreement": "missing_vote", "route": "arbitration",
                "certified": False,
                "block_reason": "a two-vote gate needs two independent submissions"}
    artifact_errs = vote_artifact_errors(vote_a, vote_b)
    if artifact_errs:
        return {"pass": False, "disagreement": "invalid_artifact", "route": "arbitration",
                "certified": False, "artifact_errors": artifact_errs,
                "block_reason": "vote artifact rejected by the established validator: %s" % artifact_errs[0]}
    indep = vote_independence_errors(vote_a, vote_b)
    if indep:
        return {"pass": False, "disagreement": "not_independent", "route": "arbitration",
                "certified": False, "independence_errors": indep,
                "block_reason": "votes are not independent: %s" % indep[0]}
    ga = grade_structured(case, project_vote(vote_a))
    gb = grade_structured(case, project_vote(vote_b))
    if not (ga["pass"] and gb["pass"]):
        bad = ga if not ga["pass"] else gb
        return {"pass": False, "disagreement": "invalid_vote", "route": "arbitration",
                "certified": False, "block_reason": bad["block_reason"], "vote_a": ga, "vote_b": gb}
    # Agreement is recomputed by the established contract's own projector, over the real artifacts.
    conclusion_agrees, reason_agrees = recompute_agreement([vote_a, vote_b])
    if not conclusion_agrees:
        return {"pass": False, "disagreement": "conclusion", "route": "arbitration", "certified": False,
                "block_reason": "votes disagree on the conclusion", "vote_a": ga, "vote_b": gb}
    if not reason_agrees:
        return {"pass": False, "disagreement": "reason", "route": "arbitration", "certified": False,
                "block_reason": "votes agree on the conclusion but not the grammatical reason "
                                "(right answer, different path => not agreement)",
                "vote_a": ga, "vote_b": gb}
    return {"pass": True, "disagreement": None, "route": "candidate_agreed_pending_certification",
            "certified": False,
            "certification_note": "agreement is a CANDIDATE state; only tools/certify_typed_fact.py may "
                                  "certify, and only from a validated two-vote artifact",
            "agreed_conclusion": (vote_a.get("conclusion") or {}).get("contextual_function"),
            "agreed_reason_key": vote_a.get("reason_key"), "vote_a": ga, "vote_b": gb}


def mint_fixture_vote(index, *, reason_key, conclusion, case_mood, relation, worklist_id, fact_type=None,
                      vote_id=None):
    """A complete, contract-valid vote artifact for fixtures/tests (never a production vote source)."""
    vote = VTV.sample_vote(index)
    vote["vote_id"] = vote_id or ("vote:fixture:%d" % index)
    vote["worklist_id"] = worklist_id
    vote["reason_key"] = reason_key
    vote["fact_type"] = fact_type
    case_block = ({"value": case_mood, "sign": "kasra", "sign_visibility": "visible"} if case_mood
                  else {"value": "none", "sign": None, "sign_visibility": "not_visible"})
    vote["conclusion"] = dict(vote["conclusion"], contextual_function=conclusion,
                              case_or_mood=case_block,
                              governor=dict(vote["conclusion"]["governor"], relation=relation))
    return vote


def grade(case, judgment):
    """case: an eval case dict (has required_gate). judgment: {final_ok, reasoning_ok, evidence_cited,
    source_address, two_vote_done}. Returns {..., 'pass': bool, 'block_reason': str|None}."""
    final_ok = bool(judgment.get("final_ok"))
    reasoning_ok = bool(judgment.get("reasoning_ok"))
    evidence_ok = bool(judgment.get("evidence_cited")) and bool(judgment.get("source_address"))
    required_gate = resolve_gate(case.get("required_gate"))
    needs_two_vote = required_gate in ("two_vote_required", "human_source_review_required")
    gate_ok = (not needs_two_vote) or bool(judgment.get("two_vote_done"))
    never_auto = required_gate == "never_auto_resolve"
    ok = final_ok and reasoning_ok and evidence_ok and gate_ok and not never_auto
    reason = None
    if not ok:
        if never_auto:
            reason = "never_auto: human source review required"
        elif not final_ok:
            reason = "final answer wrong"
        elif not reasoning_ok:
            reason = "reasoning wrong (right answer, wrong path => unsafe)"
        elif not evidence_ok:
            reason = "missing evidence rung or source-address"
        elif not gate_ok:
            reason = "two-vote gate required but not done"
    return {"final_ok": final_ok, "reasoning_ok": reasoning_ok, "evidence_ok": evidence_ok,
            "gate_ok": gate_ok, "pass": ok, "block_reason": reason}


def _selftest():
    case_tv = {"id": "t1", "required_gate": "two_vote_required"}
    case_auto = {"id": "t2", "required_gate": "auto_safe"}
    cases = [
        # (case, judgment, expected_pass)
        (case_auto, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x"}, True),
        # THE load-bearing case: right final answer, WRONG reasoning -> must FAIL
        (case_auto, {"final_ok": True, "reasoning_ok": False, "evidence_cited": True, "source_address": "x"}, False),
        # confident wrong answer -> FAIL
        (case_auto, {"final_ok": False, "reasoning_ok": True, "evidence_cited": True, "source_address": "x"}, False),
        # two-vote required but not done -> FAIL even if everything else right
        (case_tv, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x",
                   "two_vote_done": False}, False),
        (case_tv, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x",
                   "two_vote_done": True}, True),
        # missing source-address -> FAIL
        (case_auto, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": ""}, False),
    ]
    bad = 0
    for i, (c, j, exp) in enumerate(cases, 1):
        r = grade(c, j)
        if r["pass"] != exp:
            bad += 1
            print("  self-test %d FAIL: expected pass=%s got %s (%s)" % (i, exp, r["pass"], r["block_reason"]))
    if bad:
        print("FAIL: %d self-test case(s) broke the AND-gate" % bad); sys.exit(1)
    print("PASS — grade() AND-gate holds (right answer + wrong reasoning correctly FAILS; %d cases)" % len(cases))
    _selftest_structured()


def _selftest_structured():
    """The A2 property: the reasoning verdict comes from STRUCTURED, REGISTERED evidence, not a caller boolean."""
    # Registered reason keys only — these ids come from qamus/skills/reason-key-registry.jsonl.
    KEY_JARR = "lam-jarr-fused-majrur-kasra"        # kind=reason_key, licenses a jarr claim
    KEY_INNA = "inna-ism-nasb-fatha"                # kind=reason_key, licenses a nasb claim
    KEY_ATTACH = "khabar-muqaddam-shibh-jumla"      # kind=ATTACHMENT, deliberately NOT a reason_key
    case = {"id": "s1", "required_gate": "two_vote_required", "expected_reason_keys": [KEY_JARR],
            "expected_conclusion": "genitive"}
    good = {"conclusion": "genitive", "case_mood": "genitive", "reason_key": KEY_JARR,
            "fact_type": "case_assignment",
            "governor": {"surface": "li", "governor_type": "preposition"},
            "evidence_cited": True, "source_address": "quran:2:284:1", "two_vote_done": True}
    structured = [
        (case, good, True, None),
        # right ending, governor that cannot assign it (a preposition never assigns nasb - GP-WR-005)
        (case, dict(good, conclusion="accusative", case_mood="accusative"), False,
         "reason_tuple_conclusion_mismatch"),
        # ROUND-3 counterexample: individually valid reason key + individually valid governor, INVALID pair.
        # A fused-preposition genitive reason cannot license accusative under a verb_object governor.
        ({"id": "s1t", "required_gate": "two_vote_required", "expected_conclusion": "accusative",
          "expected_reason_keys": [KEY_JARR]},
         dict(good, conclusion="accusative", case_mood="accusative",
              governor={"governor_type": "verb_object"}), False, "reason_tuple_conclusion_mismatch"),
        # same pair, but with the tuple conclusion honoured: the GOVERNOR is still the wrong half
        (case, dict(good, governor={"governor_type": "verb_object"}), False,
         "reason_tuple_governor_mismatch"),
        # a fact type outside the registry row's applicable_fact_types
        (case, dict(good, fact_type="verb_mood"), False, "fact_type_not_applicable"),
        # a registered key with no repository tuple authority routes pending, never passes
        ({"id": "s1u", "required_gate": "two_vote_required", "expected_conclusion": "nominative",
          "expected_reason_keys": ["mudari3-raf3-tajarrud-thubut-nun"]},
         dict(good, conclusion="nominative", case_mood="nominative", reason_key="mudari3-raf3-tajarrud-thubut-nun",
              fact_type=None), False, "reason_tuple_unavailable"),
        # right ending, NO governor named
        (case, dict(good, governor=None), False, "governor_not_justified"),
        # right ending, a registered key that is not THIS case's path
        (case, dict(good, reason_key=KEY_INNA), False, "reason_key_mismatch"),
        # ADVERSARIAL: an unregistered / fabricated key can never grade as a correct path
        (case, dict(good, reason_key="s1:expected"), False, "reason_key_unregistered"),
        # ADVERSARIAL: an ATTACHMENT key is not a reason key
        ({"id": "s1b", "required_gate": "two_vote_required", "expected_reason_keys": [KEY_ATTACH],
          "expected_conclusion": "genitive"},
         dict(good, reason_key=KEY_ATTACH), False, "reason_key_unregistered"),
        # ADVERSARIAL: a caller boolean must not rescue an absent reason key
        (case, dict(good, reason_key="", reasoning_ok=True), False, "reason_key_absent"),
        # no structured contract on the case => fail closed
        ({"id": "s2", "required_gate": "two_vote_required", "expected_conclusion": "genitive"},
         good, False, "reason_contract_absent"),
        # a claim with no source address is not source-addressed evidence
        (case, dict(good, source_address=""), False, "source_address_absent"),
        # nahw@2.4 tajarrud is CANDIDATE, not released: it may not license a governor-free raf'
        ({"id": "s3", "required_gate": "two_vote_required", "expected_reason_keys": [KEY_INNA],
          "expected_conclusion": "accusative"},
         {"conclusion": "accusative", "case_mood": "raf3", "mood_basis": "tajarrud",
          "reason_key": KEY_INNA, "fact_type": "case_assignment", "governor": None,
          "evidence_cited": True, "source_address": "quran:2:91:23", "two_vote_done": True},
         False, "reason_tuple_case_mismatch"),
    ]
    bad = 0
    for i, (c, claim, exp_pass, exp_defect) in enumerate(structured, 1):
        r = grade_structured(c, claim)
        if r["pass"] != exp_pass or r["reason_defect"] != exp_defect:
            bad += 1
            print("  structured %d FAIL: pass=%s (want %s) defect=%s (want %s)"
                  % (i, r["pass"], exp_pass, r["reason_defect"], exp_defect))
    # ---- conclusion + human-review negatives (defect round 2) ----
    concl = [
        ("mutated conclusion only", case, dict(good, conclusion="accusative"), "conclusion_mismatch"),
        ("arbitrary conclusion", case, dict(good, conclusion="banana"), "conclusion_mismatch"),
        ("absent conclusion", case, dict(good, conclusion=None), "conclusion_absent"),
        ("expected conclusion omitted",
         {"id": "s4", "required_gate": "two_vote_required", "expected_reason_keys": [KEY_JARR]},
         good, "expected_conclusion_absent"),
    ]
    for label, c, claim, want in concl:
        r = grade_structured(c, claim)
        if r["pass"] or r["conclusion_defect"] != want:
            bad += 1
            print("  conclusion FAIL (%s): pass=%s defect=%s (want %s)"
                  % (label, r["pass"], r["conclusion_defect"], want))
    hcase = {"id": "s5", "required_gate": "human_source_review_required",
             "expected_reason_keys": [KEY_JARR], "expected_conclusion": "genitive"}
    # ROUND-4: the review must be BOUND to the exact claim (address, subject, conclusion, reason key),
    # carry a valid identifier and a machine-valid timestamp, and come from someone other than the claimant.
    bound = dict(good, subject="li-llahi", reviewer_id="claimant-1")
    good_review = {"review_id": "hr:1", "reviewer_id": "human-1", "source_address": "quran:2:284:1",
                   "subject": "li-llahi", "decision": "approved", "timestamp": "2026-07-30T00:00:00Z",
                   "reviewed_conclusion": "genitive", "reviewed_reason_key": KEY_JARR}
    human = [
        ("two_vote_done cannot substitute", dict(bound), "human_review_absent"),
        ("boolean is not a review", dict(bound, human_review=True), "human_review_not_a_record"),
        ("incomplete review", dict(bound, human_review={"review_id": "hr:1"}), "human_review_incomplete"),
        ("malformed review id", dict(bound, human_review=dict(good_review, review_id="1")),
         "human_review_id_invalid"),
        ("malformed timestamp", dict(bound, human_review=dict(good_review, timestamp="yesterday")),
         "human_review_timestamp_invalid"),
        ("unapproved review", dict(bound, human_review=dict(good_review, decision="rejected")),
         "human_review_not_approved"),
        ("out-of-scope review address",
         dict(bound, human_review=dict(good_review, source_address="quran:999:999:999")),
         "human_review_address_not_in_scope"),
        ("another valid address",
         dict(bound, human_review=dict(good_review, source_address="quran:2:26:20")),
         "human_review_address_not_bound"),
        ("another subject", dict(bound, human_review=dict(good_review, subject="OTHER")),
         "human_review_subject_not_bound"),
        ("another conclusion",
         dict(bound, human_review=dict(good_review, reviewed_conclusion="accusative")),
         "human_review_conclusion_not_bound"),
        ("another reason key",
         dict(bound, human_review=dict(good_review, reviewed_reason_key=KEY_INNA)),
         "human_review_reason_not_bound"),
        ("self-review", dict(bound, human_review=dict(good_review, reviewer_id="claimant-1")),
         "human_review_not_independent"),
    ]
    for label, claim, want in human:
        r = grade_structured(hcase, claim)
        if r["pass"] or r["human_review_defect"] != want:
            bad += 1
            print("  human-review FAIL (%s): pass=%s defect=%s (want %s)"
                  % (label, r["pass"], r["human_review_defect"], want))
    r = grade_structured(hcase, dict(bound, human_review=good_review))
    if not r["pass"]:
        bad += 1
        print("  human-review FAIL: a complete bound independent review was rejected (%s)"
              % r["block_reason"])

    # a candidate-increment MEASUREMENT can never authorize a pass
    r = grade_structured(case, dict(good, candidate_increment="nahw@2.4"))
    if r["pass"] or not r["candidate_measurement"]:
        bad += 1
        print("  candidate-increment FAIL: a candidate measurement returned pass=%s" % r["pass"])

    # ---- two-vote: FULL artifact validation delegated to the established validator ----
    tv = {"id": "tv", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
          "expected_reason_keys": [KEY_JARR, KEY_INNA]}

    def _v(index, **kw):
        base = dict(reason_key=KEY_JARR, conclusion="genitive", case_mood="genitive",
                    relation="preposition_governs_genitive", fact_type="case_assignment",
                    worklist_id="worklist-%s" % ("a" if index == 0 else "b"))
        base.update(kw)
        return mint_fixture_vote(index, **base)

    vote_a, vote_b = _v(0), _v(1)
    ok = grade_two_vote(tv, vote_a, vote_b)
    if not ok["pass"]:
        bad += 1
        print("  two-vote FAIL: two independent agreeing artifacts did not agree (%s)" % ok["block_reason"])
    if ok.get("certified") is not False or ok.get("route") != "candidate_agreed_pending_certification":
        bad += 1
        print("  two-vote FAIL: agreement route %r implies certification" % ok.get("route"))

    # ROUND-3: the established validator's own vote-id contract must be enforced
    for label, mutated in (("malformed vote_id", (dict(vote_a, vote_id="a"), dict(vote_b, vote_id="b"))),
                           ("missing segmentation", (vote_a, dict(vote_b, segmentation=[]))),
                           ("bad timestamp", (vote_a, dict(vote_b, timestamp="yesterday"))),
                           ("occurrence mismatch",
                            (vote_a, dict(vote_b, occurrence=dict(vote_b["occurrence"],
                                                                  surface="OTHER"))))):
        r = grade_two_vote(tv, mutated[0], mutated[1])
        if r["pass"] or r["disagreement"] != "invalid_artifact":
            bad += 1
            print("  two-vote FAIL: %s was accepted (disagreement=%s)" % (label, r.get("disagreement")))
    # ADVERSARIAL: cloned votes, shared engine / reviewer_id / lane / worklist / vote_id
    if grade_two_vote(tv, vote_a, dict(vote_a))["disagreement"] not in ("not_independent",
                                                                       "invalid_artifact"):
        bad += 1
        print("  two-vote FAIL: cloned votes were accepted")
    for label, mutated in (
            ("cloned provenance", dict(vote_b, reviewer=dict(vote_a["reviewer"]))),
            ("same engine", dict(vote_b, reviewer=dict(vote_b["reviewer"],
                                                       engine=vote_a["reviewer"]["engine"]))),
            ("same reviewer_id", dict(vote_b, reviewer=dict(vote_b["reviewer"],
                                                            reviewer_id=vote_a["reviewer"]["reviewer_id"]))),
            ("same lane", dict(vote_b, reviewer=dict(vote_b["reviewer"],
                                                     lane=vote_a["reviewer"]["lane"]))),
            ("same worklist", dict(vote_b, worklist_id=vote_a["worklist_id"])),
            ("same vote_id", dict(vote_b, vote_id=vote_a["vote_id"]))):
        r = grade_two_vote(tv, vote_a, mutated)
        if r["pass"] or r["disagreement"] != "not_independent":
            bad += 1
            print("  two-vote FAIL: %s was accepted as independent" % label)
    # an unregistered reason key can never agree
    if grade_two_vote(tv, _v(0, reason_key="tv-expected"), _v(1, reason_key="tv-expected"))["pass"]:
        bad += 1
        print("  two-vote FAIL: an unregistered reason key reached agreement")
    # a nonsense conclusion can never agree, even on a case declaring no expected conclusion
    if grade_two_vote({"id": "tv-nc", "required_gate": "two_vote_required",
                       "expected_reason_keys": [KEY_JARR]},
                      _v(0, conclusion="banana"), _v(1, conclusion="banana"))["pass"]:
        bad += 1
        print("  two-vote FAIL: a nonsense conclusion reached agreement")
    # same conclusion, different registered reason key -> arbitration, never agreement
    r = grade_two_vote(tv, vote_a, _v(1, reason_key=KEY_INNA))
    if r["pass"] or r.get("route") != "arbitration":
        bad += 1
        print("  two-vote FAIL: same conclusion + different reason must route to arbitration")
    if grade_two_vote(tv, vote_a, None)["pass"]:
        bad += 1
        print("  two-vote FAIL: a single vote satisfied the gate")

    if bad:
        print("FAIL: %d structured-grading case(s) broke" % bad)
        sys.exit(1)
    print("PASS - grade_structured() derives the reason verdict from REGISTERED reason keys + governor "
          "evidence (caller booleans ignored, candidate increments measurement-only); grade_two_vote() "
          "delegates independence to the two-vote artifact contract and never certifies "
          "(%d structured cases + 17 adversarial two-vote cases)" % len(structured))


if __name__ == "__main__":
    _selftest()
