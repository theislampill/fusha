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
import json
import os
import re
import sys
import unicodedata

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


# ---------------------------------------------------------------------------
# ROUND-10: an OCCURRENCE is one written word at one exact coordinate
# ---------------------------------------------------------------------------
# tools/fusha_check.resolve_address answers `in_scope_source_addressed` for an AYAH (`quran:2:284`) and for
# word index 0, because it resolves the ayah and treats the word part as optional. Evidence about "somewhere
# in this ayah" is not evidence about the word under decision, and word 0 does not exist: the canonical word
# index is 1-based. A2 therefore requires a positive word-level coordinate and then defers to the repository
# resolver for the upper bound (it rejects `word W > n_tokens`).
WORD_OCCURRENCE_RE = re.compile(r"\Aquran:([1-9][0-9]{0,2}):([1-9][0-9]{0,2}):([1-9][0-9]{0,2})\Z")


def occurrence_defect(address):
    """None only for `quran:S:A:W` with 1 <= W <= the canonical token count of that ayah.

    Closed vocabulary: occurrence_absent | occurrence_not_word_level | occurrence_not_in_spine.
    """
    if not isinstance(address, str) or not address.strip():
        return "occurrence_absent"
    if not WORD_OCCURRENCE_RE.match(address.strip()):
        # covers an ayah-only address, word index 0, a leading-zero coordinate, a wbw: or qamus: address,
        # and anything that is not a Qur'anic word coordinate at all
        return "occurrence_not_word_level"
    from tools.fusha_check import resolve_address     # lazy: the repository's own address authority
    if resolve_address(address.strip()).get("scope") != "in_scope_source_addressed":
        return "occurrence_not_in_spine"
    return None


def exact_surface_equal(left, right):
    """NFC-preserving equality of two WRITTEN surfaces. Nothing is folded away.

    Evidence binding compares what is written. norm_strict/bare/surface families erase exactly the marks
    that carry the decision — harakāt, shadda, hamza seat, Qur'anic signs, tatweel — so مَن and مِنَ,
    مَا and مَّا, حَلِيمٌ and حَلِيمٍ must all compare UNEQUAL here even though they share a normal form.
    NFC is applied only to make two encodings of the SAME characters comparable; it removes nothing.
    """
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    return unicodedata.normalize("NFC", left) == unicodedata.normalize("NFC", right)


def surface_binding_defect(claimed, evidence_surface):
    """None only when the evidence is about the exact written surface under decision."""
    if not isinstance(claimed, str) or not claimed.strip():
        return "surface_absent"
    if not isinstance(evidence_surface, str) or not evidence_surface.strip():
        return "evidence_surface_absent"
    return None if exact_surface_equal(claimed, evidence_surface) else "surface_not_bound"


def source_address_defect(claim):
    """The source address must be RESOLVABLE by the repository's own address authority.

    ROUND-8: a non-empty string used to satisfy the evidence rung, so "x", "quran:demo" and a real-looking but
    out-of-range address all graded as evidence. Authority is tools/fusha_check.resolve_address — the same
    resolver the human/source-review record is already validated against — not truthiness.
    """
    raw = claim.get("source_address")
    if not compact(raw):
        return "source_address_absent"
    # ROUND-10: an ayah-only address and word 0 both resolved in-scope, so "evidence" could be bound to a
    # whole verse rather than to the word under decision. Order matters: an address the repository cannot
    # resolve at all is `not_repository_authorised`; `not_word_level` is reserved for an address the
    # repository DOES resolve but which names a verse rather than one word.
    from tools.fusha_check import resolve_address     # lazy: the repository's own address authority
    if resolve_address(raw).get("scope") != "in_scope_source_addressed":
        return "source_address_not_repository_authorised"
    if occurrence_defect(raw if isinstance(raw, str) else "") is not None:
        return "source_address_not_word_level"
    return None


# ---------------------------------------------------------------------------
# ROUND-8: two-vote EVIDENCE (a boolean is not a vote)
# ---------------------------------------------------------------------------
# `two_vote_done=True` was accepted as proof that a two-vote gate had been cleared. A caller could therefore
# clear the highest routine gate in this lane by setting one boolean. The gate now requires two explicit,
# frozen, contract-valid, independent vote records that agree on the COMPLETE conclusion and reason tuple —
# conclusion, case/mood and its basis, governor/dependency relation and location, fact type, reason key,
# rival-analysis disposition (the contract's `unresolved_points`) and source-address binding. Agreement on the
# conclusion alone is not agreement; neither is agreement on the reason key alone.
TWO_VOTE_TUPLE_FIELDS = ("conclusion", "case_mood", "mood_basis", "governor_relation", "governor_loc",
                         "governor_type", "fact_type", "reason_key", "rival_disposition", "source_address")


def agreement_tuple(vote):
    """The complete tuple two votes must agree on. Projected from the artifact, never from English wording."""
    conclusion = vote.get("conclusion") or {}
    case_or_mood = conclusion.get("case_or_mood") or {}
    governor = conclusion.get("governor") or {}
    occurrence = vote.get("occurrence") or {}
    rivals = vote.get("unresolved_points") or []
    return {
        "conclusion": compact(conclusion.get("contextual_function")),
        "case_mood": normalize_case_mood(case_or_mood.get("value")),
        "mood_basis": compact(case_or_mood.get("mood_basis")),
        "governor_relation": compact(governor.get("relation")),
        "governor_loc": compact(governor.get("loc")),
        "governor_type": JUSTIFICATION_RULE_GOVERNOR_TYPE.get(governor.get("relation")),
        "fact_type": compact((_EXTERNAL_WORKER_RECORD.get(vote.get("vote_id")) or {}).get("fact_type")),
        "reason_key": compact(vote.get("reason_key")),
        "rival_disposition": tuple(sorted(compact(r) for r in rivals)) if isinstance(rivals, list) else None,
        "source_address": compact(occurrence.get("quran_loc")),
    }


# ---------------------------------------------------------------------------
# ROUND-10: the CANONICAL two-vote artifact is the contract; A2 has no vote schema of its own
# ---------------------------------------------------------------------------
# The A2 fixture path used to write `worklist_id` and `fact_type` straight into the vote record. The canonical
# schema is `additionalProperties: false` at every level and permits NEITHER field there, so every A2 "valid"
# pair was in fact schema-INVALID and A2 had no canonical positive path at all. Those two fields are external
# worker-record properties; they are kept beside the artifact, never inside it, and the artifact is validated
# by the repository's own validator plus the repository's own schema.
TWO_VOTE_SCHEMA_PATH = os.path.join(_REPO, "qamus", "schemas", "two-vote-artifact.schema.json")
_TWO_VOTE_SCHEMA = None

# vote_id -> the fields the CANONICAL ARTIFACT DELIBERATELY DOES NOT CARRY. This is a worker record, not
# evidence: see the truthful-limits note on vote_independence_errors().
_EXTERNAL_WORKER_RECORD = {}


def _two_vote_schema():
    global _TWO_VOTE_SCHEMA
    if _TWO_VOTE_SCHEMA is None:
        with open(TWO_VOTE_SCHEMA_PATH, encoding="utf-8") as fh:
            _TWO_VOTE_SCHEMA = json.load(fh)
    return _TWO_VOTE_SCHEMA


LOCALLY_HANDLED_KEYWORDS = frozenset({"allOf", "if", "then", "else", "maxItems"})
_UNIMPLEMENTED_RE = re.compile(r"does not implement: \[(?P<kw>[^\]]*)\]")


def _locally_handled_notice(message):
    """True for an unimplemented-keyword notice listing ONLY keywords this module applies itself."""
    match = _UNIMPLEMENTED_RE.search(message or "")
    if not match:
        return False
    listed = [k.strip().strip("'\"") for k in match.group("kw").split(",") if k.strip()]
    return bool(listed) and all(k in LOCALLY_HANDLED_KEYWORDS for k in listed)


def _apply_local_keywords(value, schema, root, path, errors):
    """allOf / if-then-else / maxItems, applied here because the shared subset validator reports them."""
    from tools.validate_task_packets import _schema_validate  # noqa: PLC0415
    if not isinstance(schema, dict):
        return
    for index, sub in enumerate(schema.get("allOf") or ()):
        sub_errors = []
        _schema_validate(value, sub, root, path, sub_errors)
        errors.extend(e for e in sub_errors if not _locally_handled_notice(e))
        _apply_local_keywords(value, sub, root, path, errors)
    if "if" in schema:
        probe = []
        _schema_validate(value, schema["if"], root, path, probe)
        probe = [e for e in probe if not _locally_handled_notice(e)]
        _apply_local_keywords(value, schema["if"], root, path, probe)
        branch = schema.get("then") if not probe else schema.get("else")
        if isinstance(branch, dict):
            branch_errors = []
            _schema_validate(value, branch, root, path, branch_errors)
            errors.extend(e for e in branch_errors if not _locally_handled_notice(e))
            _apply_local_keywords(value, branch, root, path, errors)
    limit = schema.get("maxItems")
    if isinstance(limit, int) and isinstance(value, list) and len(value) > limit:
        errors.append("%s: %d items exceeds maxItems %d" % (path, len(value), limit))


def canonical_schema_errors(row):
    """Draft 2020-12 errors for a two-vote artifact, reusing the repository's own subset validator.

    tools/validate_task_packets._schema_validate is REUSED rather than reimplemented (a second checker would
    diverge). It REPORTS, rather than silently skips, keywords it does not implement. This schema uses
    allOf, if/then/else and maxItems; those are applied here, and only notices listing exclusively those
    keywords are filtered — any other unimplemented-keyword notice is still surfaced as an error.
    """
    from tools.validate_task_packets import _schema_validate  # noqa: PLC0415 (lazy: stdlib-only, no cycle)
    schema = _two_vote_schema()
    raw = []
    _schema_validate(row, schema, schema, "$", raw)
    errors = [e for e in raw if not _locally_handled_notice(e)]
    _apply_local_keywords(row, schema, schema, "$", errors)
    votes = (row or {}).get("votes") if isinstance(row, dict) else None
    limit = ((schema.get("properties") or {}).get("votes") or {}).get("maxItems")
    if isinstance(votes, list) and isinstance(limit, int) and len(votes) > limit:
        errors.append("$.votes: %d items exceeds maxItems %d" % (len(votes), limit))
    return errors


def two_vote_artifact_defect(row):
    """None only when `row` is a canonical two-vote ARTIFACT that this repository's own tools accept.

    Both authorities must agree: the JSON Schema (shape, enums, additionalProperties) and
    tools/validate_two_vote_artifacts.validate_row (the contract's own semantic rules).
    """
    if not isinstance(row, dict):
        return "artifact_not_an_object"
    if row.get("schema") not in VTV.SCHEMA_VERSIONS:
        return "artifact_schema_unknown"
    schema_errs = canonical_schema_errors(row)
    if schema_errs:
        return "artifact_schema_invalid:%s" % schema_errs[0]
    contract_errs = []
    VTV.validate_row(row, 1, contract_errs)
    if contract_errs:
        return "artifact_contract_invalid:%s" % contract_errs[0]
    return None


# The complete claim/artifact binding. Two agreeing votes prove ONE claim: the one they are about. Comparing
# only the address let a valid pair clear a different claim at the same coordinate.
CLAIM_BINDING_FIELDS = (
    ("source_address", "source_address"), ("surface", "surface"), ("subject", "subject"),
    ("fact_type", "fact_type"), ("conclusion", "conclusion"), ("function", "function"),
    ("governor_relation", "governor_relation"), ("governed_expression", "governed_expression"),
    ("attachment", "attachment"), ("case_mood", "case_mood"), ("sign", "sign"),
    ("sign_visibility", "sign_visibility"), ("mood_basis", "mood_basis"),
    ("reason_key", "reason_key"), ("referent", "referent"),
    ("rival_disposition", "rival_disposition"),
)


def claim_projection(vote):
    """Everything a claim can be bound to, projected from the canonical artifact alone."""
    conclusion = (vote or {}).get("conclusion") or {}
    case_or_mood = conclusion.get("case_or_mood") or {}
    governor = conclusion.get("governor") or {}
    occurrence = (vote or {}).get("occurrence") or {}
    rivals = (vote or {}).get("unresolved_points") or []
    return {
        "source_address": compact(occurrence.get("quran_loc")),
        "surface": occurrence.get("surface"),
        "subject": occurrence.get("surface"),
        "fact_type": compact(_EXTERNAL_WORKER_RECORD.get(vote.get("vote_id"), {}).get("fact_type")
                             if isinstance(vote, dict) else None) or None,
        "conclusion": compact(conclusion.get("contextual_function")),
        "function": compact(conclusion.get("function")),
        "governor_relation": compact(governor.get("relation")),
        "governed_expression": conclusion.get("governed_expression"),
        "attachment": compact(conclusion.get("attachment")),
        "case_mood": normalize_case_mood(case_or_mood.get("value")),
        "sign": compact(case_or_mood.get("sign")),
        "sign_visibility": compact(case_or_mood.get("sign_visibility")),
        "mood_basis": compact(case_or_mood.get("mood_basis")),
        "reason_key": compact(vote.get("reason_key")) if isinstance(vote, dict) else None,
        "referent": compact(conclusion.get("referent")),
        "rival_disposition": tuple(sorted(compact(r) for r in rivals)) if isinstance(rivals, list) else None,
    }


# Every governed field of a canonical vote record. Two records are the SAME evidence only when all of them
# match; a shared `vote_id` is a label, not an identity.
CANONICAL_VOTE_FIELDS = (
    "vote_id", "timestamp", "occurrence", "segmentation", "lexical_identity", "lexical_target", "root",
    "form", "conclusion", "reason_key", "unresolved_points", "reviewer", "root_label_suppressed",
)


def canonical_vote_difference(left, right):
    """None when two canonical vote records are the same evidence; otherwise the first differing field.

    `grammatical_reason` and `gloss` are deliberately EXCLUDED: the v1.1 contract treats that prose as
    uncompared elaboration, so differing wording is not differing evidence. Everything the contract does
    govern must match exactly.
    """
    if not isinstance(left, dict) or not isinstance(right, dict):
        return "not_a_vote_record"
    for field in CANONICAL_VOTE_FIELDS:
        if left.get(field) != right.get(field):
            return field
    return None


def claim_binding_defect(claim, vote):
    """None only when the artifact is about THIS claim — same occurrence, same written surface, same tuple.

    Only fields the claim actually declares are compared (a claim that says nothing about `referent` is not
    contradicted by one), EXCEPT the occurrence and the written surface, which must always be bound.
    """
    projected = claim_projection(vote)
    if occurrence_defect(projected.get("source_address") or "") is not None:
        return "artifact_occurrence_not_word_level"
    if compact(claim.get("source_address")) != projected["source_address"]:
        return "claim_address_not_bound"
    # ROUND-13: the exact written surface is MANDATORY, not "compared when supplied". A claim that names
    # neither `surface` nor `subject` asserts a decision about a word it never identifies, and the previous
    # code let it through — the opposite of the mandatory-surface contract this module documents.
    claimed_surface = claim.get("surface") if claim.get("surface") is not None else claim.get("subject")
    if claimed_surface is None:
        return "claim_surface_absent"
    defect = surface_binding_defect(claimed_surface, projected["surface"])
    if defect is not None:
        return "claim_surface_not_bound"
    # ROUND-13: the claim carries its governor as a NESTED object ({"governor_type": ...}), which the flat
    # field loop below never reached, so a vote whose reason is reversed — "the noun governs the
    # preposition" instead of "the preposition governs the noun" — cleared a claim whose relation is the
    # other way round. A correct label with the wrong reason must fail.
    claimed_governor = claim.get("governor")
    if claimed_governor is not None:
        if not isinstance(claimed_governor, dict):
            return "claim_governor_not_a_record"
        claimed_type = compact(claimed_governor.get("governor_type"))
        projected_type = JUSTIFICATION_RULE_GOVERNOR_TYPE.get(
            (((vote or {}).get("conclusion") or {}).get("governor") or {}).get("relation"))
        if not claimed_type:
            return "claim_governor_type_absent"
        if claimed_type != projected_type:
            return "claim_governor_relation_not_bound"

    for claim_field, projected_field in CLAIM_BINDING_FIELDS:
        if claim_field in ("source_address", "surface"):
            continue
        if claim_field not in claim or claim.get(claim_field) is None:
            continue
        left = claim.get(claim_field)
        right = projected.get(projected_field)
        if claim_field == "case_mood":
            left = normalize_case_mood(left)
        elif claim_field == "rival_disposition" and isinstance(left, (list, tuple)):
            left = tuple(sorted(compact(x) for x in left))
        elif isinstance(left, str):
            left = compact(left)
        if left != right:
            return "claim_%s_not_bound" % claim_field
    return None


def canonical_two_vote_envelope(vote_a, vote_b, *, claim_state="two_vote_verified"):
    """Wrap two votes in a CANONICAL two-vote artifact envelope (fixtures/tests; never a production source).

    The envelope is the contract's own shape — occurrence, agreement block, claim state, reclassification,
    votes_fabricated — so an A2 pair can be validated by the repository's validator and schema rather than by
    an A2-only invention.
    """
    occurrence = dict((vote_a or {}).get("occurrence") or {})
    conclusion_agrees, reason_agrees = recompute_agreement([vote_a, vote_b])
    loc = compact(occurrence.get("quran_loc")) or "unknown"
    return {
        "schema": VTV.SCHEMA_V1,
        "artifact_id": "two-vote-artifact:%s" % loc.replace(":", "_"),
        "claimed_decision_state": "two_vote",
        "claim_state": claim_state,
        "occurrence": occurrence,
        "votes": [vote_a, vote_b],
        "agreement": {
            "conclusion_agrees": bool(conclusion_agrees),
            "reason_agrees": bool(reason_agrees),
            "agreement_key": compact((vote_a or {}).get("reason_key")),
            "compared_fields": ["conclusion", "reason_key"],
            "gloss_text_used_for_agreement": False,
        },
        "reclassification": None,
        "votes_fabricated": False,
    }


def prose_reason_defect(claim):
    """A2 never validates free `grammatical_reason` prose. Asking it to is an error, not a pass.

    The canonical v1.1 contract treats `grammatical_reason` as UNCOMPARED elaboration: agreement is computed
    over the registered reason key and the structured conclusion tuple. Presenting the prose as validated
    proof would claim a check nobody performs, so a caller that asks for it is routed to human/scholar review.
    """
    if not isinstance(claim, dict):
        return "claim_not_a_record"
    if claim.get("validate_reason_prose"):
        return "reason_prose_not_machine_validated:route=scholar_irab_review"
    return None


def two_vote_evidence_defect(claim):
    """Return None only when the claim carries two validated, independent, fully agreeing vote records.

    Closed defect vocabulary: two_vote_declared_without_artifacts | two_vote_evidence_absent |
    two_vote_evidence_not_two_records | two_vote_evidence_not_frozen_records | two_vote_artifact_invalid |
    two_vote_not_independent | two_vote_conclusion_disagreement | two_vote_reason_disagreement |
    two_vote_tuple_disagreement:<fields> | two_vote_claimant_identity_absent |
    two_vote_claimant_not_a_reviewer | two_vote_address_not_bound.
    """
    votes = claim.get("two_vote_evidence")
    if votes is None:
        # A declaration with no artifacts is the exact false pass this gate exists to stop.
        return ("two_vote_declared_without_artifacts" if claim.get("two_vote_done")
                else "two_vote_evidence_absent")
    if not isinstance(votes, (list, tuple)) or len(votes) != 2:
        return "two_vote_evidence_not_two_records"
    if not all(isinstance(v, dict) and v for v in votes):
        return "two_vote_evidence_not_frozen_records"
    if vote_artifact_errors(votes[0], votes[1]):
        return "two_vote_artifact_invalid"
    if vote_independence_errors(votes[0], votes[1]):
        return "two_vote_not_independent"
    conclusion_agrees, reason_agrees = recompute_agreement(list(votes))
    if not conclusion_agrees:
        return "two_vote_conclusion_disagreement"
    if not reason_agrees:
        return "two_vote_reason_disagreement"
    left, right = agreement_tuple(votes[0]), agreement_tuple(votes[1])
    differing = [f for f in TWO_VOTE_TUPLE_FIELDS if left.get(f) != right.get(f)]
    if differing:
        return "two_vote_tuple_disagreement:%s" % ",".join(differing)
    claimant = compact(claim.get("reviewer_id"))
    if not claimant:
        return "two_vote_claimant_identity_absent"
    if claimant not in {compact((v.get("reviewer") or {}).get("reviewer_id")) for v in votes}:
        return "two_vote_claimant_not_a_reviewer"
    # ROUND-10: the pair must be a CANONICAL artifact, not merely two records A2 happens to like.
    envelope = claim.get("two_vote_artifact")
    if envelope is None:
        envelope = canonical_two_vote_envelope(votes[0], votes[1])
    artifact_defect = two_vote_artifact_defect(envelope)
    if artifact_defect is not None:
        return "two_vote_%s" % artifact_defect
    # ROUND-13: comparing ordered vote_id values only let a VALID envelope for one occurrence authorise a
    # separately valid submitted pair for ANOTHER occurrence that happened to reuse the same vote ids.
    # The envelope must carry the same canonical records — every governed evidence field, not the label.
    enveloped = envelope.get("votes") or []
    if len(enveloped) != len(votes):
        return "two_vote_artifact_votes_not_the_submitted_pair"
    for supplied, carried in zip(votes, enveloped):
        if canonical_vote_difference(supplied, carried) is not None:
            return ("two_vote_artifact_votes_not_the_submitted_pair:%s"
                    % canonical_vote_difference(supplied, carried))
    if compact((envelope.get("occurrence") or {}).get("quran_loc")) != left["source_address"]:
        return "two_vote_artifact_occurrence_not_the_submitted_occurrence"
    # ROUND-10: two agreeing votes prove ONE claim — the one they are about. Address equality alone let a
    # valid pair clear a different claim at the same coordinate.
    for vote in votes:
        binding = claim_binding_defect(claim, vote)
        if binding is not None:
            return "two_vote_%s" % binding
    # ROUND-10: free reason prose is never machine-validated proof.
    prose = prose_reason_defect(claim)
    if prose is not None:
        return "two_vote_%s" % prose
    return None


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
    address_defect = source_address_defect(claim)
    if address_defect:
        return False, address_defect

    # ---- the reason key must license this exact tuple, not merely exist ----
    tuple_ = REASON_TUPLES.get(reason_key)
    if tuple_ is None:
        # Registered, but the repository gives no machine authority for its (conclusion, case, governor)
        # tuple. Route pending rather than inventing one.
        return False, "reason_tuple_unavailable"
    kinds, _errs = load_registry()
    # ROUND-8: a MISSING fact type is an absent fact, not a satisfied one. Silently substituting the tuple's
    # own expected value made the check compare a value with itself and always agree.
    fact_type = claim.get("fact_type")
    if not compact(fact_type):
        return False, "fact_type_absent"
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
    # ROUND-8: independence cannot be established against an UNKNOWN claimant. With no claimant identity the
    # comparison below is between a reviewer and nobody, which always "differs" — an absent claimant used to
    # pass the independence test outright. Require the identity first.
    if not compact(claim.get("reviewer_id")):
        return "human_review_claimant_identity_absent"
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
    # ROUND-8: the structured path ALWAYS grades in evidence mode. `two_vote_done` is deliberately not
    # forwarded — a boolean can no longer reach the gate at all.
    # ROUND-10: forward the WHOLE claim (minus the declared boolean, which must never reach the gate) so the
    # evidence gate can bind the artifact to every field the claim actually asserts — conclusion, surface,
    # subject, sign, referent and the rest. Forwarding only a hand-picked subset meant a valid vote pair
    # could clear a claim whose conclusion or written surface it never mentioned.
    judgment = {k: v for k, v in claim.items() if k != "two_vote_done"}
    judgment.update({"final_ok": conclusion_ok, "reasoning_ok": reasoning_ok,
                     "evidence_cited": claim.get("evidence_cited"),
                     "source_address": claim.get("source_address"),
                     "reviewer_id": claim.get("reviewer_id"),
                     "two_vote_evidence": claim.get("two_vote_evidence")})
    result = grade(case, judgment, require_evidence=True)
    result["conclusion_defect"] = concl_defect
    result["human_review_defect"] = hr_defect
    if hr_defect:
        result["pass"] = False
        result["block_reason"] = "human/source review required: %s" % hr_defect
    result["reason_defect"] = defect
    # A structured decision routes to at most a CANDIDATE state. Nothing here certifies.
    if result["pass"]:
        result["route"] = ("candidate_agreed_pending_certification"
                           if result.get("gate_evidence") == "validated_artifacts" else "candidate")
    elif hr_defect or resolve_gate(case.get("required_gate")) == "human_source_review_required":
        result["route"] = "human_source_review"
    else:
        result["route"] = "pending"
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
# canonical fields only — `worklist_id` is not one of them (the schema does not carry it)
TWO_VOTE_INDEPENDENCE_FIELDS = ("vote_id", "reviewer")
WORKLIST_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]*\Z")


def vote_artifact_errors(vote_a, vote_b):
    """Full artifact validation for both votes, delegated to the established validator."""
    errors = []
    bundle = vote_a.get("occurrence") if isinstance(vote_a, dict) else None
    for index, vote in enumerate((vote_a, vote_b)):
        VTV.validate_vote(vote, 0, index, bundle, errors)
    return errors


def vote_independence_errors(vote_a, vote_b):
    """Independence provable from the CANONICAL artifact alone.

    Requires distinct `vote_id`, distinct `reviewer.reviewer_id` and distinct `reviewer.lane`, and refuses two
    byte-identical submissions.

    ROUND-10: `engine` is NO LONGER required to differ. Two genuinely independent reviewers can both work
    through the same CLI surface, so a shared engine string is not evidence of dependence and demanding a
    different one only pushes workers to falsify it. `worklist_id` is likewise gone: the canonical schema does
    not carry it, so A2 cannot prove it from the artifact.

    TRUTHFUL LIMIT — what this function does NOT prove, because the canonical artifact does not carry it:
    CLI version, proof of which model actually produced each vote, a frozen artifact hash, separate worklist
    provenance, and reviewer-isolation (that neither reviewer saw the other's answer). Those remain EXTERNAL
    worker-record requirements for the later owner two-vote lane. A2 must not be read as establishing them.
    """
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
    for field in ("reviewer_id", "lane"):
        if compact(ra.get(field)) == compact(rb.get(field)):
            errs.append("votes are not independent: both votes share %s %r" % (field, compact(ra.get(field))))
    if errs:
        return errs
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
        # not an artifact field: the canonical schema does not carry a fact type (see _EXTERNAL_WORKER_RECORD)
        "fact_type": (_EXTERNAL_WORKER_RECORD.get(vote.get("vote_id")) or {}).get("fact_type"),
        "governor": {"governor_type": gov_type} if gov_type else None,
        "evidence_cited": True,
        "source_address": occurrence.get("quran_loc"),
        # ROUND-13: the projection carries the vote's OWN exact written surface, so an occurrence-bound
        # claim always names the word it is about. The surface is mandatory in claim_binding_defect().
        "surface": occurrence.get("surface"),
        "subject": occurrence.get("surface"),
        "human_review": vote.get("human_review"),
        "reviewer_id": (vote.get("reviewer") or {}).get("reviewer_id"),
        # ROUND-8: a vote does NOT declare its own gate cleared. grade_two_vote() supplies the validated pair
        # as `two_vote_evidence`; a single projected vote carries no gate authority of its own.
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
    pair = [vote_a, vote_b]
    ga = grade_structured(case, dict(project_vote(vote_a), two_vote_evidence=pair))
    gb = grade_structured(case, dict(project_vote(vote_b), two_vote_evidence=pair))
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
    vote["reason_key"] = reason_key
    # ROUND-10: `worklist_id` and `fact_type` are NOT vote_record properties — the canonical schema is
    # additionalProperties:false and writing them into the record made every A2 pair schema-invalid. They are
    # external worker-record fields and are kept beside the artifact, keyed by vote id.
    _EXTERNAL_WORKER_RECORD[vote["vote_id"]] = {"worklist_id": worklist_id, "fact_type": fact_type}
    case_block = ({"value": case_mood, "sign": "kasra", "sign_visibility": "visible"} if case_mood
                  else {"value": "none", "sign": None, "sign_visibility": "not_visible"})
    vote["conclusion"] = dict(vote["conclusion"], contextual_function=conclusion,
                              case_or_mood=case_block,
                              governor=dict(vote["conclusion"]["governor"], relation=relation))
    return vote


def grade(case, judgment, *, require_evidence=True):
    """case: an eval case dict (has required_gate). judgment: {final_ok, reasoning_ok, evidence_cited,
    source_address, two_vote_evidence}. Returns {..., 'pass': bool, 'block_reason': str|None}.

    `require_evidence=True` is the EVIDENCE mode used by every structured decision in this lane: a two-vote
    gate is satisfied only by two validated, independent, fully agreeing vote records, and `two_vote_done` is
    ignored entirely.

    ROUND-10: `require_evidence` now DEFAULTS to True, and the false pass it used to allow is removed. A
    caller that passes `two_vote_done=True` and no artifacts gets `gate_ok=False` with
    `gate_evidence="declared_only_rejected"` in either mode. `require_evidence=False` now means only "do not
    run the artifact validation"; it never means "believe the boolean". The two non-A2 callers of this
    function (tools/run_grammar_evals.py's wrong-reasoning-trap probe and tools/fusha_tutor_runtime.py's
    default-off bridge) grade runtime checkpoints that carry no vote artifacts at all, so under this contract
    a two-vote-gated row of theirs is correctly reported as unproven rather than passed.
    """
    final_ok = bool(judgment.get("final_ok"))
    reasoning_ok = bool(judgment.get("reasoning_ok"))
    evidence_ok = bool(judgment.get("evidence_cited")) and bool(judgment.get("source_address"))
    required_gate = resolve_gate(case.get("required_gate"))
    needs_two_vote = required_gate in ("two_vote_required", "human_source_review_required")
    two_vote_defect = None
    if not needs_two_vote:
        gate_ok, gate_evidence = True, "not_required"
    elif require_evidence:
        two_vote_defect = two_vote_evidence_defect(judgment)
        gate_ok = two_vote_defect is None
        gate_evidence = "validated_artifacts" if gate_ok else "rejected"
    else:
        # ROUND-10: the legacy public false pass is GONE. `require_evidence=False` no longer lets a declared
        # boolean satisfy a two-vote gate; it only suppresses the artifact validation, and the gate still
        # fails closed. A declared Boolean is never evidence, from any entry point.
        two_vote_defect = ("two_vote_declared_without_artifacts" if judgment.get("two_vote_done")
                           else "two_vote_evidence_absent")
        gate_ok = False
        gate_evidence = "declared_only_rejected"
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
            reason = ("two-vote gate required but not proven: %s" % two_vote_defect if two_vote_defect
                      else "two-vote gate required but not done")
    return {"final_ok": final_ok, "reasoning_ok": reasoning_ok, "evidence_ok": evidence_ok,
            "gate_ok": gate_ok, "gate_evidence": gate_evidence, "two_vote_defect": two_vote_defect,
            "pass": ok, "block_reason": reason}


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
        # ROUND-10: a DECLARED boolean is never evidence. This case used to pass on `two_vote_done=True`
        # alone; a two-vote gate now needs the canonical artifact, so the declaration fails closed.
        (case_tv, {"final_ok": True, "reasoning_ok": True, "evidence_cited": True, "source_address": "x",
                   "two_vote_done": True}, False),
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
    print("PASS — grade() AND-gate holds (right answer + wrong reasoning correctly FAILS; a DECLARED "
          "two_vote_done never satisfies a two-vote gate; %d cases)" % len(cases))
    _selftest_structured()


def _selftest_structured():
    """The A2 property: the reasoning verdict comes from STRUCTURED, REGISTERED evidence, not a caller boolean."""
    # Registered reason keys only — these ids come from qamus/skills/reason-key-registry.jsonl.
    KEY_JARR = "lam-jarr-fused-majrur-kasra"        # kind=reason_key, licenses a jarr claim
    KEY_INNA = "inna-ism-nasb-fatha"                # kind=reason_key, licenses a nasb claim
    KEY_ATTACH = "khabar-muqaddam-shibh-jumla"      # kind=ATTACHMENT, deliberately NOT a reason_key
    case = {"id": "s1", "required_gate": "two_vote_required", "expected_reason_keys": [KEY_JARR],
            "expected_conclusion": "genitive"}
    # ROUND-8: the two-vote gate is satisfied by two REAL contract-valid, independent, fully agreeing vote
    # artifacts — never by `two_vote_done`. The claim is PROJECTED from one of them, so its conclusion,
    # case, governor, fact type, reason key and source address all come from the evidence itself.
    VA = mint_fixture_vote(0, reason_key=KEY_JARR, conclusion="genitive", case_mood="genitive",
                           relation="preposition_governs_genitive", worklist_id="wl-a",
                           fact_type="case_assignment", vote_id="vote:selftest:a")
    VB = mint_fixture_vote(1, reason_key=KEY_JARR, conclusion="genitive", case_mood="genitive",
                           relation="preposition_governs_genitive", worklist_id="wl-b",
                           fact_type="case_assignment", vote_id="vote:selftest:b")
    ADDR = VA["occurrence"]["quran_loc"]
    good = dict(project_vote(VA), two_vote_evidence=[VA, VB])
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
         dict(good, conclusion="accusative", case_mood="raf3", mood_basis="tajarrud",
              reason_key=KEY_INNA, fact_type="case_assignment", governor=None),
         False, "reason_tuple_case_mismatch"),
        # ROUND-8: a MISSING fact type is an absent fact, never the expected one
        (case, dict(good, fact_type=None), False, "fact_type_absent"),
        # ROUND-8: a source address must resolve through the repository's authority, not merely be non-empty
        (case, dict(good, source_address="quran:demo"), False,
         "source_address_not_repository_authorised"),
        # ROUND-10: an AYAH-only address and word 0 are not occurrences
        (case, dict(good, source_address="quran:2:13"), False, "source_address_not_word_level"),
        (case, dict(good, source_address="quran:2:13:0"), False, "source_address_not_word_level"),
        (case, dict(good, source_address="qamus:entry:1234"), False,
         "source_address_not_repository_authorised"),
        # a well-formed word coordinate BEYOND the ayah's token count is refused by the repository resolver
        (case, dict(good, source_address="quran:2:13:99"), False,
         "source_address_not_repository_authorised"),
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
    # ROUND-10: the subject IS the exact written surface under decision, bound to the artifact's occurrence.
    SURFACE = VA["occurrence"]["surface"]
    bound = dict(good, subject=SURFACE)
    good_review = {"review_id": "hr:1", "reviewer_id": "human-1", "source_address": ADDR,
                   "subject": SURFACE, "decision": "approved", "timestamp": "2026-07-30T00:00:00Z",
                   "reviewed_conclusion": "genitive", "reviewed_reason_key": KEY_JARR}
    human = [
        ("validated two votes cannot substitute for a human/source review", dict(bound),
         "human_review_absent"),
        # ROUND-8: independence cannot be judged against an unknown claimant
        ("claimant identity absent",
         dict(bound, reviewer_id=None, human_review=dict(good_review)),
         "human_review_claimant_identity_absent"),
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
        # ROUND-10: a same-family but differently-WRITTEN subject is a different occurrence subject
        ("a differently-written subject",
         dict(bound, human_review=dict(good_review, subject=SURFACE + "ً")),
         "human_review_subject_not_bound"),
        ("another conclusion",
         dict(bound, human_review=dict(good_review, reviewed_conclusion="accusative")),
         "human_review_conclusion_not_bound"),
        ("another reason key",
         dict(bound, human_review=dict(good_review, reviewed_reason_key=KEY_INNA)),
         "human_review_reason_not_bound"),
        ("self-review", dict(bound, human_review=dict(good_review, reviewer_id=bound["reviewer_id"])),
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

            ("same reviewer_id", dict(vote_b, reviewer=dict(vote_b["reviewer"],
                                                            reviewer_id=vote_a["reviewer"]["reviewer_id"]))),
            ("same lane", dict(vote_b, reviewer=dict(vote_b["reviewer"],
                                                     lane=vote_a["reviewer"]["lane"]))),
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

    # -----------------------------------------------------------------------
    # ROUND-8: the two-vote EVIDENCE gate (a boolean is not a vote)
    # -----------------------------------------------------------------------
    def _tuple_break(vote, **kw):
        """A vote that still agrees on conclusion AND reason key, but not on the complete tuple."""
        return dict(vote, **kw)

    evidence_cases = [
        # THE round-8 false pass: `two_vote_done=True` used to clear this gate outright. grade_structured()
        # no longer forwards the boolean at all, so it cannot even be seen — the gate reports an absence.
        ("two_vote_done=True with no artifacts",
         dict(good, two_vote_evidence=None, two_vote_done=True), "two_vote_evidence_absent"),
        ("no gate evidence of any kind",
         dict(good, two_vote_evidence=None), "two_vote_evidence_absent"),
        ("one vote is not two", dict(good, two_vote_evidence=[VA]), "two_vote_evidence_not_two_records"),
        ("three votes are not two",
         dict(good, two_vote_evidence=[VA, VB, VA]), "two_vote_evidence_not_two_records"),
        ("booleans in place of vote records",
         dict(good, two_vote_evidence=[True, True]), "two_vote_evidence_not_frozen_records"),
        ("an empty record is not a vote",
         dict(good, two_vote_evidence=[VA, {}]), "two_vote_evidence_not_frozen_records"),
        ("a malformed artifact is rejected by the established validator",
         dict(good, two_vote_evidence=[VA, dict(VB, reason_key=None)]), "two_vote_artifact_invalid"),
        ("two dependent votes",
         dict(good, two_vote_evidence=[VA, dict(VB, reviewer=dict(VA["reviewer"]))]),
         "two_vote_not_independent"),
        ("votes disagreeing on the conclusion",
         dict(good, two_vote_evidence=[VA, mint_fixture_vote(
             1, reason_key=KEY_JARR, conclusion="accusative", case_mood="genitive",
             relation="preposition_governs_genitive", worklist_id="wl-b",
             fact_type="case_assignment", vote_id="vote:selftest:c")]),
         "two_vote_conclusion_disagreement"),
        ("votes disagreeing on the reason key",
         dict(good, two_vote_evidence=[VA, mint_fixture_vote(
             1, reason_key=KEY_INNA, conclusion="genitive", case_mood="genitive",
             relation="preposition_governs_genitive", worklist_id="wl-b",
             fact_type="case_assignment", vote_id="vote:selftest:d")]),
         "two_vote_reason_disagreement"),
        # agreement on conclusion AND reason key, but NOT on the complete tuple
        # ROUND-10: `fact_type` is not a vote_record property at all — writing one in makes the artifact
        # schema-invalid, which is caught before any tuple comparison.
        ("a fact type written into the vote record",
         dict(good, two_vote_evidence=[VA, _tuple_break(VB, fact_type="particle_function")]),
         "two_vote_artifact_schema_invalid:$.votes[1]: additional property 'fact_type' is not allowed"),
        ("votes disagreeing on the rival-analysis disposition",
         dict(good, two_vote_evidence=[VA, _tuple_break(VB, unresolved_points=["rival idafa reading"])]),
         "two_vote_tuple_disagreement:rival_disposition"),
        # the governor location is part of the canonical conclusion projection, so a moved ʿāmil is caught
        # as a conclusion disagreement rather than reaching the tuple comparison
        ("votes disagreeing on the governor location",
         dict(good, two_vote_evidence=[VA, _tuple_break(
             VB, conclusion=dict(VB["conclusion"],
                                 governor=dict(VB["conclusion"]["governor"], loc="quran:2:13:1")))]),
         "two_vote_conclusion_disagreement"),
        # two votes about different occurrences are not a pair at all: the established artifact validator
        # rejects the bundle before agreement is ever computed
        ("votes disagreeing on the source address",
         dict(good, two_vote_evidence=[VA, _tuple_break(
             VB, occurrence=dict(VB["occurrence"], quran_loc="quran:2:26:20"))]),
         "two_vote_artifact_invalid"),
        ("the claimant identity is absent",
         dict(good, reviewer_id=None), "two_vote_claimant_identity_absent"),
        ("the claimant is neither of the two reviewers",
         dict(good, reviewer_id="someone-else"), "two_vote_claimant_not_a_reviewer"),
        ("the votes are about another address than the claim",
         dict(good, source_address="quran:2:26:20"), "two_vote_claim_address_not_bound"),
        # ROUND-10: two agreeing votes must not clear a DIFFERENT claim at the SAME address
        ("a different claim at the same address",
         dict(good, conclusion="accusative"), "two_vote_claim_conclusion_not_bound"),
        ("a different written surface at the same address",
         dict(good, surface="حَلِيمٍ"), "two_vote_claim_surface_not_bound"),
        ("a caller asking A2 to validate free reason prose",
         dict(good, validate_reason_prose=True),
         "two_vote_reason_prose_not_machine_validated:route=scholar_irab_review"),
    ]
    # the declaration itself, inspected directly: a boolean is named as such and never becomes evidence
    if two_vote_evidence_defect({"two_vote_done": True}) != "two_vote_declared_without_artifacts":
        bad += 1
        print("  two-vote evidence FAIL: a bare two_vote_done declaration was not named as such")
    for label, claim, want in evidence_cases:
        r = grade_structured(case, claim)
        if r["pass"] or r.get("two_vote_defect") != want:
            bad += 1
            print("  two-vote evidence FAIL (%s): pass=%s defect=%s (want %s)"
                  % (label, r["pass"], r.get("two_vote_defect"), want))
        if r.get("route") not in ("pending", "human_source_review"):
            bad += 1
            print("  two-vote evidence FAIL (%s): routed %r instead of pending/review"
                  % (label, r.get("route")))

    # the POSITIVE case: two validated agreeing votes route to a CANDIDATE state, never to certification
    r = grade_structured(case, good)
    if not (r["pass"] and r.get("two_vote_defect") is None
            and r.get("gate_evidence") == "validated_artifacts"
            and r.get("route") == "candidate_agreed_pending_certification"):
        bad += 1
        print("  two-vote evidence FAIL: a valid explicit two-vote pair was not accepted (%s / %s / %s)"
              % (r.get("block_reason"), r.get("gate_evidence"), r.get("route")))
    if r.get("certified"):
        bad += 1
        print("  two-vote evidence FAIL: a graded claim reported certification")
    # and grade_two_vote agrees, over the same artifacts, with the same route
    rtv = grade_two_vote(case, VA, VB)
    if not (rtv["pass"] and rtv["route"] == "candidate_agreed_pending_certification"
            and rtv["certified"] is False):
        bad += 1
        print("  two-vote evidence FAIL: grade_two_vote disagreed with grade_structured (%s)" % rtv)
    # a declaration cannot rescue an auto_safe case into a two-vote conclusion either
    if grade({"id": "ev", "required_gate": "two_vote_required"},
             {"final_ok": True, "reasoning_ok": True, "evidence_cited": True,
              "source_address": ADDR, "two_vote_done": True}, require_evidence=True)["pass"]:
        bad += 1
        print("  two-vote evidence FAIL: grade(require_evidence=True) accepted a bare declaration")

    if bad:
        print("FAIL: %d structured-grading case(s) broke" % bad)
        sys.exit(1)
    print("PASS - grade_structured() derives the reason verdict from REGISTERED reason keys + governor "
          "evidence (caller booleans ignored, candidate increments measurement-only); grade_two_vote() "
          "delegates independence to the two-vote artifact contract and never certifies "
          "(%d structured cases + 17 adversarial two-vote cases + %d round-8 two-vote EVIDENCE cases: "
          "a boolean, one vote, three votes, non-records, a malformed artifact, dependent votes, "
          "conclusion/reason/fact-type/rival/governor/address disagreement, an absent or foreign claimant "
          "and an unbound address are all refused; a valid pair routes only to "
          "candidate_agreed_pending_certification)" % (len(structured), len(evidence_cases)))


if __name__ == "__main__":
    _selftest()
