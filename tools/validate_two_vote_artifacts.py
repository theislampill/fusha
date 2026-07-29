#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate two-vote artifact bundles (qamus.two_vote_artifact.v1 / v1.1).

A row claiming `two_vote` / `bulk_two_vote_certified` is only `two_vote_verified`
when TWO reconstructible, independent vote records exist and agree on the
grammatical CONCLUSION and the REASON key — never on gloss text alone.
Historical claims without artifacts are representable only as
`two_vote_claimed_unverified` (a reclassification state); votes are never
fabricated for them.

v1.1 (flywheel lessons L1-L6 from the 2026-07-29 canary run) replaces free-prose
comparison with governed vocabulary so that independently-authored honest votes
can actually reach agreement:

- `case_or_mood.value` / `.sign` are closed enums (raf3/nasb/jarr/jazm/none;
  fatha/damma/kasra/sukun/thubut_nun/hadhf_nun/hadhf_harf_illa/alif/waw/ya/none).
- `conclusion.function` and `conclusion.attachment_key` come from the governed
  registry `qamus/skills/reason-key-registry.jsonl`; `reason_key` must be a
  registry id of kind `reason_key`. Prose stays in `contextual_function`,
  `attachment`, `referent`, `grammatical_reason` — uncompared elaboration.
- `case_or_mood.mood_basis` (governed|tajarrud|default): a governor is required
  only when mood_basis is `governed`; raf' by tajarrud (no overt operator) is
  valid with governor null; tajarrud/default can only license raf3.
- `governed_expression` means "the expression THIS token governs (null if it
  governs nothing)"; the optional `governed_by_scope` records what governs this
  token.
- Segment surfaces are recorded as displayed in the mushaf token (including
  shadda from assimilation, e.g. لِّ); `normalized_segment` /
  `governor.normalized_surface` carry the dictionary-normalized clitic form and
  the normalized surface wins in comparison.
- `lexical_target` (clitic_entry|whole_token) declares what the vote's lexical
  identity addresses; `root_label_suppressed` marks public root-label
  suppression policy (if true, root must be null).

v1 artifacts keep validating under the original v1 rules unchanged.
"""
import argparse
import copy
import io
import json
import os
import re
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "two-vote-artifact.schema.json")

ARTIFACT_ID = re.compile(r"^two-vote-artifact:quran_[0-9]{1,3}_[0-9]{1,3}_[0-9]{1,3}(:[A-Za-z0-9._-]+)?$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
VOTE_ID = re.compile(r"^vote:[A-Za-z0-9._:-]+$")
REASON_KEY = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CLAIMED_STATES = {"two_vote", "bulk_two_vote_certified"}
CLAIM_STATES = {"two_vote_verified", "two_vote_disagreement", "two_vote_claimed_unverified"}
SIGN_VISIBILITY = {"visible", "estimated", "not_applicable"}

SCHEMA_V1 = "qamus.two_vote_artifact.v1"
SCHEMA_V11 = "qamus.two_vote_artifact.v1.1"
SCHEMA_VERSIONS = {SCHEMA_V1: 1, SCHEMA_V11: 11}
REGISTRY_PATH = os.path.join(ROOT, "qamus", "skills", "reason-key-registry.jsonl")
REGISTRY_KINDS = {"reason_key", "function", "attachment"}
CASE_VALUES = {"raf3", "nasb", "jarr", "jazm", "none"}
SIGN_VALUES = {
    "fatha", "damma", "kasra", "sukun",
    "thubut_nun", "hadhf_nun", "hadhf_harf_illa",
    "alif", "waw", "ya", "none",
}
MOOD_BASIS = {"governed", "tajarrud", "default"}
LEXICAL_TARGETS = {"clitic_entry", "whole_token"}
FORBIDDEN_PUBLIC_LABELS = (
    "informed_by",
    "mcp",
    "qac",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
)
REQUIRED = [
    "schema",
    "artifact_id",
    "claimed_decision_state",
    "claim_state",
    "occurrence",
    "votes",
    "agreement",
    "reclassification",
    "votes_fabricated",
]
VOTE_REQUIRED = [
    "vote_id",
    "reviewer",
    "timestamp",
    "occurrence",
    "segmentation",
    "lexical_identity",
    "root",
    "form",
    "conclusion",
    "grammatical_reason",
    "reason_key",
    "unresolved_points",
]
CONCLUSION_REQUIRED = [
    "contextual_function",
    "governor",
    "governed_expression",
    "case_or_mood",
    "attachment",
    "referent",
]
REVIEWER_REQUIRED = ["reviewer_id", "engine", "model", "lane"]
AGREEMENT_COMPARED_MINIMUM = {"conclusion", "reason_key"}


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except Exception as exc:
                yield line_no, {"__json_error__": str(exc)}


def compact(value):
    return " ".join(str(value or "").strip().split())


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


_REGISTRY_CACHE = None


def load_registry():
    """Load the governed reason-key/function/attachment registry.

    Returns ({kind: {id, ...}}, [error, ...]).  Cached for the process.
    """
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    kinds = {kind: set() for kind in REGISTRY_KINDS}
    errors = []
    if not os.path.exists(REGISTRY_PATH):
        errors.append("reason-key registry missing: %s" % REGISTRY_PATH)
        _REGISTRY_CACHE = (kinds, errors)
        return _REGISTRY_CACHE
    seen = set()
    for line_no, row in iter_jsonl(REGISTRY_PATH):
        if "__json_error__" in row:
            errors.append("registry line %d: bad JSON (%s)" % (line_no, row["__json_error__"]))
            continue
        key_id = str(row.get("id") or "")
        kind = row.get("kind")
        if not REASON_KEY.match(key_id):
            errors.append("registry line %d: id must be a lowercase-hyphen token" % line_no)
            continue
        if kind not in REGISTRY_KINDS:
            errors.append("registry line %d: kind must be one of %s" % (line_no, sorted(REGISTRY_KINDS)))
            continue
        if key_id in seen:
            errors.append("registry line %d: duplicate id %r" % (line_no, key_id))
            continue
        if not compact(row.get("definition")):
            errors.append("registry line %d: definition is required" % line_no)
        if not isinstance(row.get("applicable_fact_types"), list) or not row.get("applicable_fact_types"):
            errors.append("registry line %d: applicable_fact_types must be a non-empty list" % line_no)
        if not isinstance(row.get("examples"), list) or not row.get("examples"):
            errors.append("registry line %d: examples must be a non-empty list" % line_no)
        seen.add(key_id)
        kinds[kind].add(key_id)
    _REGISTRY_CACHE = (kinds, errors)
    return _REGISTRY_CACHE


def canonical_conclusion(conclusion):
    """Comparable projection of a vote conclusion. Gloss text is deliberately absent."""
    if not isinstance(conclusion, dict):
        return None
    governor = conclusion.get("governor")
    if isinstance(governor, dict):
        governor_key = (
            compact(governor.get("loc")),
            compact(governor.get("surface")),
            compact(governor.get("relation")),
        )
    else:
        governor_key = None
    case = conclusion.get("case_or_mood") or {}
    if not isinstance(case, dict):
        case = {}
    return (
        compact(conclusion.get("contextual_function")),
        governor_key,
        compact(conclusion.get("governed_expression")) or None,
        (
            compact(case.get("value")) or None,
            compact(case.get("sign")) or None,
            compact(case.get("sign_visibility")),
        ),
        compact(conclusion.get("attachment")) or None,
        compact(conclusion.get("referent")) or None,
    )


def canonical_conclusion_v11(conclusion):
    """v1.1 comparable projection: governed enum/registry fields only.

    Prose fields (contextual_function, attachment, referent, governor.relation,
    grammatical_reason) are elaboration and are deliberately excluded; surface
    normalization wins over as-displayed surfaces for the governor.
    """
    if not isinstance(conclusion, dict):
        return None
    governor = conclusion.get("governor")
    if isinstance(governor, dict):
        governor_key = (
            compact(governor.get("loc")),
            compact(governor.get("normalized_surface")) or compact(governor.get("surface")),
        )
    else:
        governor_key = None
    case = conclusion.get("case_or_mood") or {}
    if not isinstance(case, dict):
        case = {}
    return (
        compact(conclusion.get("function")),
        governor_key,
        compact(conclusion.get("governed_expression")) or None,
        (
            compact(case.get("value")),
            compact(case.get("sign")),
            compact(case.get("sign_visibility")),
            compact(case.get("mood_basis")) or None,
        ),
        compact(conclusion.get("attachment_key")) or None,
    )


def validate_vote_v11(vote, line_no, index, registry, errors):
    """v1.1-only rules on top of the shared vote checks."""
    prefix = "votes[%d]" % index
    if not isinstance(vote, dict):
        return
    lexical_target = vote.get("lexical_target")
    if lexical_target not in LEXICAL_TARGETS:
        _err(errors, line_no, "%s.lexical_target must be clitic_entry or whole_token (v1.1)" % prefix)
    suppressed = vote.get("root_label_suppressed")
    if suppressed not in (None, True, False):
        _err(errors, line_no, "%s.root_label_suppressed must be a boolean when present" % prefix)
    if suppressed is True and vote.get("root") is not None:
        _err(errors, line_no, "%s.root_label_suppressed=true requires root=null (public root-label suppression policy)" % prefix)
    segmentation = vote.get("segmentation")
    if isinstance(segmentation, list):
        for seg_index, segment in enumerate(segmentation):
            if isinstance(segment, dict) and "normalized_segment" in segment:
                if not compact(segment.get("normalized_segment")):
                    _err(errors, line_no, "%s.segmentation[%d].normalized_segment must be non-empty when present" % (prefix, seg_index))
    if compact(vote.get("reason_key")) and compact(vote.get("reason_key")) not in registry["reason_key"]:
        _err(errors, line_no, "%s.reason_key %r is not a registered reason_key (see qamus/skills/reason-key-registry.jsonl)" % (prefix, compact(vote.get("reason_key"))))

    conclusion = vote.get("conclusion")
    if not isinstance(conclusion, dict):
        return
    function = conclusion.get("function")
    if not compact(function) or compact(function) not in registry["function"]:
        _err(errors, line_no, "%s.conclusion.function must be a registered function key (v1.1)" % prefix)
    attachment_key = conclusion.get("attachment_key")
    if attachment_key is not None and compact(attachment_key) not in registry["attachment"]:
        _err(errors, line_no, "%s.conclusion.attachment_key %r is not a registered attachment key" % (prefix, compact(attachment_key)))
    governed_by_scope = conclusion.get("governed_by_scope")
    if governed_by_scope is not None and not compact(governed_by_scope):
        _err(errors, line_no, "%s.conclusion.governed_by_scope must be non-empty when present" % prefix)

    case = conclusion.get("case_or_mood")
    if not isinstance(case, dict):
        return
    value = case.get("value")
    sign = case.get("sign")
    mood_basis = case.get("mood_basis")
    if value not in CASE_VALUES:
        _err(errors, line_no, "%s.conclusion.case_or_mood.value must be one of %s (v1.1 governed enum)" % (prefix, "/".join(sorted(CASE_VALUES))))
        return
    if sign not in SIGN_VALUES:
        _err(errors, line_no, "%s.conclusion.case_or_mood.sign must be a governed sign enum value (v1.1)" % prefix)
    governor = conclusion.get("governor")
    if value == "none":
        if sign not in (None, "none"):
            _err(errors, line_no, "%s.conclusion.case_or_mood.value=none requires sign=none" % prefix)
        if case.get("sign_visibility") != "not_applicable":
            _err(errors, line_no, "%s.conclusion.case_or_mood.value=none requires sign_visibility=not_applicable" % prefix)
        if mood_basis is not None:
            _err(errors, line_no, "%s.conclusion.case_or_mood.mood_basis must be null when value=none" % prefix)
        return
    if mood_basis not in MOOD_BASIS:
        _err(errors, line_no, "%s.conclusion.case_or_mood.mood_basis must be governed/tajarrud/default for an inflected value (v1.1)" % prefix)
        return
    if mood_basis == "governed":
        if governor is None:
            _err(errors, line_no, "%s claims a governed case/mood (i'rab) but names no governor" % prefix)
    else:
        # raf' by tajarrud / by default is valid WITHOUT a governor —
        # but tajarrud/default can only ever license raf3.
        if value != "raf3":
            _err(errors, line_no, "%s.conclusion.case_or_mood: mood_basis=%s only licenses raf3, not %s" % (prefix, mood_basis, value))


def validate_vote(vote, line_no, index, bundle_occurrence, errors, version=1):
    prefix = "votes[%d]" % index
    if not isinstance(vote, dict):
        _err(errors, line_no, "%s must be an object" % prefix)
        return
    for field in VOTE_REQUIRED:
        if field not in vote:
            _err(errors, line_no, "%s missing %s" % (prefix, field))
    if not VOTE_ID.match(str(vote.get("vote_id") or "")):
        _err(errors, line_no, "%s.vote_id must be vote:<id>" % prefix)
    reviewer = vote.get("reviewer")
    if not isinstance(reviewer, dict):
        _err(errors, line_no, "%s.reviewer must be an object" % prefix)
    else:
        for field in REVIEWER_REQUIRED:
            if not compact(reviewer.get(field)):
                _err(errors, line_no, "%s.reviewer.%s is required (independent provenance)" % (prefix, field))
    if not TIMESTAMP.match(str(vote.get("timestamp") or "")):
        _err(errors, line_no, "%s.timestamp must be ISO-8601 with timezone" % prefix)

    occurrence = vote.get("occurrence")
    if not isinstance(occurrence, dict):
        _err(errors, line_no, "%s.occurrence must be an object" % prefix)
    else:
        if not QURAN.match(str(occurrence.get("quran_loc") or "")):
            _err(errors, line_no, "%s.occurrence.quran_loc is invalid" % prefix)
        if not WBW.match(str(occurrence.get("wbw_loc") or "")):
            _err(errors, line_no, "%s.occurrence.wbw_loc is invalid" % prefix)
        if not compact(occurrence.get("surface")):
            _err(errors, line_no, "%s.occurrence.surface is required" % prefix)
        if isinstance(bundle_occurrence, dict) and occurrence != bundle_occurrence:
            _err(errors, line_no, "%s.occurrence must match bundle occurrence exactly (loc + exact surface)" % prefix)

    segmentation = vote.get("segmentation")
    if not isinstance(segmentation, list) or not segmentation:
        _err(errors, line_no, "%s.segmentation must be a non-empty list" % prefix)
    else:
        for seg_index, segment in enumerate(segmentation):
            if not isinstance(segment, dict) or not compact(segment.get("segment_surface")) or not compact(segment.get("role")):
                _err(errors, line_no, "%s.segmentation[%d] needs segment_surface and role" % (prefix, seg_index))

    lexical = vote.get("lexical_identity")
    if not isinstance(lexical, dict) or not compact(lexical.get("lemma_ar")):
        _err(errors, line_no, "%s.lexical_identity.lemma_ar is required" % prefix)

    conclusion = vote.get("conclusion")
    if not isinstance(conclusion, dict):
        _err(errors, line_no, "%s.conclusion must be an object" % prefix)
        conclusion = {}
    for field in CONCLUSION_REQUIRED:
        if field not in conclusion:
            _err(errors, line_no, "%s.conclusion missing %s" % (prefix, field))
    if not compact(conclusion.get("contextual_function")):
        _err(errors, line_no, "%s.conclusion.contextual_function is required" % prefix)
    case = conclusion.get("case_or_mood")
    if not isinstance(case, dict):
        _err(errors, line_no, "%s.conclusion.case_or_mood must be an object" % prefix)
        case = {}
    visibility = case.get("sign_visibility")
    if visibility not in SIGN_VISIBILITY:
        _err(errors, line_no, "%s.conclusion.case_or_mood.sign_visibility must be visible/estimated/not_applicable" % prefix)
    governor = conclusion.get("governor")
    if governor is not None:
        if not isinstance(governor, dict) or not compact(governor.get("surface")) or not compact(governor.get("relation")):
            _err(errors, line_no, "%s.conclusion.governor needs surface and relation" % prefix)
        else:
            loc = governor.get("loc")
            if loc is not None and not (QURAN.match(str(loc)) or WBW.match(str(loc))):
                _err(errors, line_no, "%s.conclusion.governor.loc is invalid" % prefix)
    if version == 1:
        # v1 rule (encodes the nominal i'rab picture only; v1.1 replaces it
        # with the mood_basis rule so raf' by tajarrud needs no governor).
        if compact(case.get("value")) and visibility in ("visible", "estimated") and governor is None:
            _err(errors, line_no, "%s claims a governed case/mood (i'rab) but names no governor" % prefix)

    if not compact(vote.get("grammatical_reason")):
        _err(errors, line_no, "%s.grammatical_reason is required" % prefix)
    if not REASON_KEY.match(str(vote.get("reason_key") or "")):
        _err(errors, line_no, "%s.reason_key must be a lowercase-hyphen agreement key" % prefix)
    gloss = compact(vote.get("gloss"))
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in gloss.lower():
            _err(errors, line_no, "%s.gloss leaks forbidden label %r" % (prefix, label))
    unresolved = vote.get("unresolved_points")
    if not isinstance(unresolved, list):
        _err(errors, line_no, "%s.unresolved_points must be a list (may be empty)" % prefix)


def recompute_agreement(votes, version=1):
    """Agreement is computed on conclusion AND reason fields, never on gloss text."""
    first, second = votes
    projector = canonical_conclusion_v11 if version >= 11 else canonical_conclusion
    conclusion_agrees = (
        projector(first.get("conclusion")) is not None
        and projector(first.get("conclusion")) == projector(second.get("conclusion"))
    )
    reason_agrees = bool(
        compact(first.get("reason_key"))
        and compact(first.get("reason_key")) == compact(second.get("reason_key"))
    )
    return conclusion_agrees, reason_agrees


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return
    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    version = SCHEMA_VERSIONS.get(row.get("schema"))
    if version is None:
        _err(errors, line_no, "schema must be %s or %s" % (SCHEMA_V1, SCHEMA_V11))
        version = 1
    if not ARTIFACT_ID.match(str(row.get("artifact_id") or "")):
        _err(errors, line_no, "artifact_id must be two-vote-artifact:quran_S_A_W[:suffix]")
    claimed = row.get("claimed_decision_state")
    if claimed not in CLAIMED_STATES:
        _err(errors, line_no, "claimed_decision_state must be two_vote or bulk_two_vote_certified")
    claim_state = row.get("claim_state")
    if claim_state not in CLAIM_STATES:
        _err(errors, line_no, "claim_state must be two_vote_verified, two_vote_disagreement, or two_vote_claimed_unverified")
        return
    if row.get("votes_fabricated") is not False:
        _err(errors, line_no, "votes_fabricated must be false — historical rows are reclassified, never backfilled with invented votes")

    occurrence = row.get("occurrence")
    if not isinstance(occurrence, dict):
        _err(errors, line_no, "occurrence must be an object")
        occurrence = {}
    if not QURAN.match(str(occurrence.get("quran_loc") or "")):
        _err(errors, line_no, "occurrence.quran_loc is invalid")
    if not WBW.match(str(occurrence.get("wbw_loc") or "")):
        _err(errors, line_no, "occurrence.wbw_loc is invalid")
    if not compact(occurrence.get("surface")):
        _err(errors, line_no, "occurrence.surface (exact surface) is required")

    votes = row.get("votes")
    if not isinstance(votes, list):
        _err(errors, line_no, "votes must be a list")
        votes = []
    for index, vote in enumerate(votes):
        validate_vote(vote, line_no, index, occurrence if occurrence else None, errors, version=version)
    if version >= 11:
        registry, _registry_errors = load_registry()
        for index, vote in enumerate(votes):
            validate_vote_v11(vote, line_no, index, registry, errors)

    agreement = row.get("agreement")
    reclassification = row.get("reclassification")

    if claim_state == "two_vote_claimed_unverified":
        if len(votes) >= 2:
            _err(errors, line_no, "two_vote_claimed_unverified must not carry a full vote pair — verify and reclassify instead")
        if agreement is not None:
            _err(errors, line_no, "two_vote_claimed_unverified must not carry an agreement record")
        if not isinstance(reclassification, dict):
            _err(errors, line_no, "two_vote_claimed_unverified requires a reclassification record")
        else:
            if not compact(reclassification.get("original_claim_source")):
                _err(errors, line_no, "reclassification.original_claim_source is required")
            if not compact(reclassification.get("reason")):
                _err(errors, line_no, "reclassification.reason is required")
            if not DATE.match(str(reclassification.get("reclassified_on") or "")):
                _err(errors, line_no, "reclassification.reclassified_on must be YYYY-MM-DD")
        return

    # verified / disagreement both require exactly two reconstructible votes.
    if len(votes) != 2:
        _err(errors, line_no, "%s requires exactly two vote records (found %d)" % (claim_state, len(votes)))
        return
    if reclassification is not None:
        _err(errors, line_no, "%s must not carry a reclassification record" % claim_state)

    first_reviewer = votes[0].get("reviewer") or {}
    second_reviewer = votes[1].get("reviewer") or {}
    if isinstance(first_reviewer, dict) and isinstance(second_reviewer, dict):
        if compact(first_reviewer.get("engine")) and compact(first_reviewer.get("engine")) == compact(second_reviewer.get("engine")):
            _err(errors, line_no, "votes are not independent: both votes come from engine %r" % compact(first_reviewer.get("engine")))
        if compact(first_reviewer.get("reviewer_id")) and compact(first_reviewer.get("reviewer_id")) == compact(second_reviewer.get("reviewer_id")):
            _err(errors, line_no, "votes are not independent: same reviewer_id on both votes")
    if compact(votes[0].get("vote_id")) and compact(votes[0].get("vote_id")) == compact(votes[1].get("vote_id")):
        _err(errors, line_no, "votes must have distinct vote_ids")

    if not isinstance(agreement, dict):
        _err(errors, line_no, "%s requires an agreement record" % claim_state)
        return
    compared = agreement.get("compared_fields")
    if not isinstance(compared, list) or not AGREEMENT_COMPARED_MINIMUM.issubset({compact(field) for field in compared}):
        _err(errors, line_no, "agreement.compared_fields must include conclusion and reason_key")
    if any(compact(field) == "gloss" for field in (compared or [])):
        _err(errors, line_no, "agreement.compared_fields must not include gloss — gloss text can never carry agreement")
    if agreement.get("gloss_text_used_for_agreement") is not False:
        _err(errors, line_no, "agreement.gloss_text_used_for_agreement must be false")

    conclusion_agrees, reason_agrees = recompute_agreement(votes, version=version)
    if bool(agreement.get("conclusion_agrees")) != conclusion_agrees:
        _err(errors, line_no, "agreement.conclusion_agrees=%r does not match recomputed value %r" % (agreement.get("conclusion_agrees"), conclusion_agrees))
    if bool(agreement.get("reason_agrees")) != reason_agrees:
        _err(errors, line_no, "agreement.reason_agrees=%r does not match recomputed value %r" % (agreement.get("reason_agrees"), reason_agrees))

    if claim_state == "two_vote_verified":
        if not conclusion_agrees:
            _err(errors, line_no, "two_vote_verified requires the two conclusions to agree (recomputed disagreement)")
        if not reason_agrees:
            _err(errors, line_no, "two_vote_verified requires the two reason keys to agree — matching gloss text is not agreement")
        key = compact(agreement.get("agreement_key"))
        if not key:
            _err(errors, line_no, "two_vote_verified requires agreement.agreement_key")
        elif any(compact(vote.get("reason_key")) != key for vote in votes):
            _err(errors, line_no, "agreement.agreement_key must equal both votes' reason_key")
    else:  # two_vote_disagreement
        if conclusion_agrees and reason_agrees:
            _err(errors, line_no, "two_vote_disagreement recomputes as full agreement — reclassify as two_vote_verified")
        if agreement.get("agreement_key") is not None:
            _err(errors, line_no, "two_vote_disagreement must not carry an agreement_key")


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    has_v11 = False
    for line_no, row in iter_jsonl(path):
        count += 1
        if isinstance(row, dict) and row.get("schema") == SCHEMA_V11:
            has_v11 = True
        validate_row(row, line_no, errors)
    if has_v11:
        _registry, registry_errors = load_registry()
        errors = list(registry_errors) + errors
    if count == 0:
        errors.append("zero two-vote artifact rows")
    return count, errors


def sample_vote(vote_index):
    reviewers = [
        {"reviewer_id": "lane-cert-a", "engine": "engine-alpha", "model": "model-a-2026-06", "lane": "sarf-primary"},
        {"reviewer_id": "lane-cert-b", "engine": "engine-beta", "model": "model-b-2026-06", "lane": "nahw-primary"},
    ]
    return {
        "vote_id": "vote:quran_2_13_12:%s" % ("a" if vote_index == 0 else "b"),
        "reviewer": reviewers[vote_index],
        "timestamp": "2026-07-28T0%d:00:00Z" % (vote_index + 1),
        "occurrence": {
            "quran_loc": "quran:2:13:12",
            "wbw_loc": "wbw:2:13:12",
            "surface": "السُّفَهَاءُ",
        },
        "segmentation": [
            {"segment_surface": "ال", "role": "definite_article"},
            {"segment_surface": "سُّفَهَاءُ", "role": "noun_host"},
        ],
        "lexical_identity": {"entry_id": "1ffcc554ec44", "lemma_ar": "سفيه"},
        "root": "س ف ه",
        "form": "fu'ala' broken plural of fa'il",
        "conclusion": {
            "contextual_function": "explicit subject of the comparison clause verb",
            "governor": {"loc": "quran:2:13:11", "surface": "آمَنَ", "relation": "verb_governs_subject_nominative"},
            "governed_expression": "السُّفَهَاءُ",
            "case_or_mood": {"value": "nominative", "sign": "damma", "sign_visibility": "visible"},
            "attachment": "subject inside the kama comparison clause",
            "referent": None,
        },
        "grammatical_reason": "Fa'il of the perfect verb in the comparison clause; nominative by government, damma visible on the final hamza seat.",
        "reason_key": "fail-of-amana-nominative-visible-damma",
        "gloss": "the foolish ones",
        "unresolved_points": [],
    }


def sample_verified_row():
    votes = [sample_vote(0), sample_vote(1)]
    return {
        "schema": "qamus.two_vote_artifact.v1",
        "artifact_id": "two-vote-artifact:quran_2_13_12",
        "claimed_decision_state": "two_vote",
        "claim_state": "two_vote_verified",
        "occurrence": {
            "quran_loc": "quran:2:13:12",
            "wbw_loc": "wbw:2:13:12",
            "surface": "السُّفَهَاءُ",
        },
        "votes": votes,
        "agreement": {
            "conclusion_agrees": True,
            "reason_agrees": True,
            "agreement_key": "fail-of-amana-nominative-visible-damma",
            "compared_fields": ["conclusion", "reason_key"],
            "gloss_text_used_for_agreement": False,
        },
        "reclassification": None,
        "votes_fabricated": False,
    }


def sample_unverified_row():
    return {
        "schema": "qamus.two_vote_artifact.v1",
        "artifact_id": "two-vote-artifact:quran_22_18_17:historical",
        "claimed_decision_state": "bulk_two_vote_certified",
        "claim_state": "two_vote_claimed_unverified",
        "occurrence": {
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "surface": "وَٱلشَّجَرُ",
        },
        "votes": [],
        "agreement": None,
        "reclassification": {
            "original_claim_source": "qamus/reports/closure-2092/bulk-two-vote reconciliation trail (apply receipts only; per-vote artifacts were not retained)",
            "reason": "Historical bulk_two_vote_certified row predates the two-vote artifact contract; no reconstructible vote pair exists, so the claim is downgraded, not backfilled.",
            "reclassified_on": "2026-07-28",
        },
        "votes_fabricated": False,
    }


def sample_vote_v11(vote_index):
    reviewers = [
        {"reviewer_id": "lane-cert-a", "engine": "engine-alpha", "model": "model-a-2026-06", "lane": "sarf-primary"},
        {"reviewer_id": "lane-cert-b", "engine": "engine-beta", "model": "model-b-2026-06", "lane": "nahw-primary"},
    ]
    return {
        "vote_id": "vote:quran_2_173_23:v11:%s" % ("a" if vote_index == 0 else "b"),
        "reviewer": reviewers[vote_index],
        "timestamp": "2026-07-29T0%d:00:00Z" % (vote_index + 1),
        "occurrence": {
            "quran_loc": "quran:2:173:23",
            "wbw_loc": "wbw:2:173:23",
            "surface": "ٱللَّهَ",
        },
        "segmentation": [
            {"segment_surface": "ٱللَّهَ", "role": "proper_divine_name"},
        ],
        "lexical_identity": {"entry_id": None, "lemma_ar": "ٱللَّه"},
        "root": None,
        "form": None,
        "lexical_target": "whole_token",
        "root_label_suppressed": True,
        "conclusion": {
            "contextual_function": "ism of inna - the noun governed by the emphatic particle",
            "function": "ism-inna",
            "governor": {"loc": "quran:2:173:22", "surface": "إِنَّ", "relation": "inna governs its ism in nasb"},
            "governed_expression": None,
            "governed_by_scope": "إِنَّ (quran:2:173:22) governs this token in nasb",
            "case_or_mood": {"value": "nasb", "sign": "fatha", "sign_visibility": "visible", "mood_basis": "governed"},
            "attachment": "ism of inna; the khabar remains nominative",
            "attachment_key": "ism-inna-khabar-marfu3",
            "referent": None,
        },
        "grammatical_reason": "Ism of inna, governed in nasb by the nasikh particle; fatha visible on the final ha'; the khabar stays marfu'.",
        "reason_key": "inna-ism-nasb-fatha",
        "gloss": "Allah",
        "unresolved_points": [],
    }


def sample_verified_row_v11():
    votes = [sample_vote_v11(0), sample_vote_v11(1)]
    return {
        "schema": "qamus.two_vote_artifact.v1.1",
        "artifact_id": "two-vote-artifact:quran_2_173_23:v11-sample",
        "claimed_decision_state": "two_vote",
        "claim_state": "two_vote_verified",
        "occurrence": {
            "quran_loc": "quran:2:173:23",
            "wbw_loc": "wbw:2:173:23",
            "surface": "ٱللَّهَ",
        },
        "votes": votes,
        "agreement": {
            "conclusion_agrees": True,
            "reason_agrees": True,
            "agreement_key": "inna-ism-nasb-fatha",
            "compared_fields": ["conclusion", "reason_key"],
            "gloss_text_used_for_agreement": False,
        },
        "reclassification": None,
        "votes_fabricated": False,
    }


def sample_tajarrud_row_v11():
    """raf' by tajarrud: inflected mood, visible sign, and NO governor — valid in v1.1."""
    row = sample_verified_row_v11()
    row["artifact_id"] = "two-vote-artifact:quran_2_91_23:v11-sample"
    occurrence = {
        "quran_loc": "quran:2:91:23",
        "wbw_loc": "wbw:2:91:23",
        "surface": "تَقْتُلُونَ",
    }
    row["occurrence"] = occurrence
    for index, vote in enumerate(row["votes"]):
        vote["vote_id"] = "vote:quran_2_91_23:v11:%s" % ("a" if index == 0 else "b")
        vote["occurrence"] = dict(occurrence)
        vote["segmentation"] = [
            {"segment_surface": "تَ", "role": "verb_prefix_person_2"},
            {"segment_surface": "قْتُلُ", "role": "verb_stem"},
            {"segment_surface": "ونَ", "role": "verb_suffix_subject_mp_indicative_nun"},
        ]
        vote["lexical_identity"] = {"entry_id": None, "lemma_ar": "قَتَلَ"}
        vote["root"] = "ق ت ل"
        vote["root_label_suppressed"] = False
        vote["form"] = "Form I imperfect 2mp indicative"
        vote["conclusion"] = {
            "contextual_function": "main verb of the interrogative clause introduced by فَلِمَ",
            "function": "fi3l-mudari3-marfu3",
            "governor": None,
            "governed_expression": "أَنۢبِيَآءَ ٱللَّهِ",
            "governed_by_scope": None,
            "case_or_mood": {"value": "raf3", "sign": "thubut_nun", "sign_visibility": "visible", "mood_basis": "tajarrud"},
            "attachment": "clause governed adverbially by the interrogative لِمَ; no jazm/nasb operator present",
            "attachment_key": "lima-muta3allaq-bil-fi3l",
            "referent": None,
        }
        vote["grammatical_reason"] = "Imperfect verb marfu' by tajarrud (absence of any nasib/jazim); mood sign thubut al-nun (al-af'al al-khamsa)."
        vote["reason_key"] = "mudari3-raf3-tajarrud-thubut-nun"
        vote["gloss"] = "you (all) kill"
    row["agreement"]["agreement_key"] = "mudari3-raf3-tajarrud-thubut-nun"
    return row


CANARY_FIXTURE = os.path.join(ROOT, "qamus", "examples", "two_vote_artifact_v11_canaries.jsonl")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _expect_fail(path, rows, needle, label):
    write_jsonl(path, rows)
    count, errors = validate(path)
    if count != len(rows):
        print("SELF-TEST FAIL %s: expected %d rows, saw %d" % (label, len(rows), count))
        return False
    if not any(needle in err for err in errors):
        print("SELF-TEST FAIL %s: expected error containing %r, got:" % (label, needle))
        for err in errors[:10]:
            print("  -", err)
        return False
    return True


def self_test():
    with tempfile.TemporaryDirectory(prefix="two-vote-artifact-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")

        # Green: a verified pair and an honestly reclassified historical row.
        write_jsonl(good, [sample_verified_row(), sample_unverified_row()])
        count, errors = validate(good)
        if count != 2 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1

        # Red 1: single vote behind a two_vote claim.
        single = copy.deepcopy(sample_verified_row())
        single["votes"] = single["votes"][:1]
        if not _expect_fail(bad, [single], "requires exactly two vote records", "single vote"):
            return 1

        # Red 2: gloss-only agreement — glosses identical, reason keys differ.
        gloss_only = copy.deepcopy(sample_verified_row())
        gloss_only["votes"][1]["reason_key"] = "fail-of-amana-nominative-estimated-damma"
        if not _expect_fail(bad, [gloss_only], "matching gloss text is not agreement", "gloss-only agreement"):
            return 1

        # Red 3: same engine on both votes.
        same_engine = copy.deepcopy(sample_verified_row())
        same_engine["votes"][1]["reviewer"]["engine"] = same_engine["votes"][0]["reviewer"]["engine"]
        if not _expect_fail(bad, [same_engine], "votes are not independent: both votes come from engine", "same engine"):
            return 1

        # Red 4: i'rab claim (visible case sign) with no governor named.
        no_governor = copy.deepcopy(sample_verified_row())
        for vote in no_governor["votes"]:
            vote["conclusion"]["governor"] = None
        if not _expect_fail(bad, [no_governor], "names no governor", "missing governor"):
            return 1

        # Red 5: declared agreement flags contradict the recomputed comparison.
        stale_flags = copy.deepcopy(sample_verified_row())
        stale_flags["votes"][1]["conclusion"]["case_or_mood"]["sign_visibility"] = "estimated"
        if not _expect_fail(bad, [stale_flags], "does not match recomputed value", "stale agreement flags"):
            return 1

        # Red 6: historical unverified row must not smuggle a fabricated pair.
        smuggled = copy.deepcopy(sample_unverified_row())
        smuggled["votes"] = [sample_vote(0), sample_vote(1)]
        if not _expect_fail(bad, [smuggled], "must not carry a full vote pair", "smuggled votes on unverified"):
            return 1

        # Red 7: gloss listed as an agreement field.
        gloss_field = copy.deepcopy(sample_verified_row())
        gloss_field["agreement"]["compared_fields"] = ["conclusion", "reason_key", "gloss"]
        if not _expect_fail(bad, [gloss_field], "must not include gloss", "gloss compared field"):
            return 1

        # Red 8: vote surface drifts from the bundle's exact surface.
        drift = copy.deepcopy(sample_verified_row())
        drift["votes"][1]["occurrence"]["surface"] = "السفهاء"
        if not _expect_fail(bad, [drift], "must match bundle occurrence exactly", "surface drift"):
            return 1

        # ---- v1.1 cases ----------------------------------------------------

        # Green v1.1: registry loads cleanly.
        registry, registry_errors = load_registry()
        if registry_errors:
            print("SELF-TEST FAIL registry:", registry_errors[:5])
            return 1
        for kind, needed in (
            ("reason_key", {"mudari3-raf3-tajarrud-thubut-nun", "ma-nafiya-non-operative", "lam-jarr-fused-majrur-kasra", "inna-ism-nasb-fatha"}),
            ("function", {"fi3l-mudari3-marfu3", "harf-nafy-ghayr-3amil", "harf-jarr-lam-fused", "ism-inna"}),
            ("attachment", {"lima-muta3allaq-bil-fi3l", "nafy-jawab-qasam", "khabar-muqaddam-shibh-jumla", "ism-inna-khabar-marfu3"}),
        ):
            missing = needed - registry[kind]
            if missing:
                print("SELF-TEST FAIL registry seed: missing %s ids %s" % (kind, sorted(missing)))
                return 1

        # Green v1.1: governed enums + registry keys verify; v1 row still
        # validates side by side (backward compatibility).
        write_jsonl(good, [sample_verified_row(), sample_verified_row_v11(), sample_tajarrud_row_v11()])
        count, errors = validate(good)
        if count != 3 or errors:
            print("SELF-TEST FAIL v1.1 good:", errors[:10])
            return 1

        # Green v1.1 (the canary-1 contract fix): raf' by tajarrud with NO
        # governor passes — while the SAME conclusion shape under v1 rules
        # still fails (Red 4 above proves the v1 rule is intact).

        # Red 9: nominal nasb (mood_basis=governed) with no governor still fails.
        nominal_no_gov = copy.deepcopy(sample_verified_row_v11())
        for vote in nominal_no_gov["votes"]:
            vote["conclusion"]["governor"] = None
        if not _expect_fail(bad, [nominal_no_gov], "names no governor", "v1.1 nominal nasb without governor"):
            return 1

        # Red 10: tajarrud basis cannot license nasb.
        tajarrud_nasb = copy.deepcopy(sample_tajarrud_row_v11())
        for vote in tajarrud_nasb["votes"]:
            vote["conclusion"]["case_or_mood"]["value"] = "nasb"
            vote["conclusion"]["case_or_mood"]["sign"] = "fatha"
        if not _expect_fail(bad, [tajarrud_nasb], "only licenses raf3", "v1.1 tajarrud cannot license nasb"):
            return 1

        # Red 11: free-prose case value rejected under v1.1.
        prose_value = copy.deepcopy(sample_verified_row_v11())
        for vote in prose_value["votes"]:
            vote["conclusion"]["case_or_mood"]["value"] = "accusative (nasb)"
        if not _expect_fail(bad, [prose_value], "case_or_mood.value must be one of", "v1.1 prose case value"):
            return 1

        # Red 12: free-prose sign rejected under v1.1.
        prose_sign = copy.deepcopy(sample_verified_row_v11())
        for vote in prose_sign["votes"]:
            vote["conclusion"]["case_or_mood"]["sign"] = "fatha on the final ha'"
        if not _expect_fail(bad, [prose_sign], "sign must be a governed sign enum", "v1.1 prose sign"):
            return 1

        # Red 13: missing mood_basis on an inflected value.
        no_basis = copy.deepcopy(sample_verified_row_v11())
        for vote in no_basis["votes"]:
            del vote["conclusion"]["case_or_mood"]["mood_basis"]
        if not _expect_fail(bad, [no_basis], "mood_basis must be governed/tajarrud/default", "v1.1 missing mood_basis"):
            return 1

        # Red 14: unregistered reason_key rejected under v1.1.
        rogue_key = copy.deepcopy(sample_verified_row_v11())
        for vote in rogue_key["votes"]:
            vote["reason_key"] = "inna-ism-nasb-fatha-freestyle-variant"
        rogue_key["agreement"]["agreement_key"] = "inna-ism-nasb-fatha-freestyle-variant"
        if not _expect_fail(bad, [rogue_key], "not a registered reason_key", "v1.1 unregistered reason_key"):
            return 1

        # Red 15: unregistered function key rejected.
        rogue_function = copy.deepcopy(sample_verified_row_v11())
        for vote in rogue_function["votes"]:
            vote["conclusion"]["function"] = "some-free-prose-function"
        if not _expect_fail(bad, [rogue_function], "must be a registered function key", "v1.1 unregistered function"):
            return 1

        # Red 16: unregistered attachment key rejected.
        rogue_attachment = copy.deepcopy(sample_verified_row_v11())
        for vote in rogue_attachment["votes"]:
            vote["conclusion"]["attachment_key"] = "free-prose-attachment"
        if not _expect_fail(bad, [rogue_attachment], "not a registered attachment key", "v1.1 unregistered attachment_key"):
            return 1

        # Red 17: missing lexical_target on a v1.1 vote.
        no_target = copy.deepcopy(sample_verified_row_v11())
        for vote in no_target["votes"]:
            del vote["lexical_target"]
        if not _expect_fail(bad, [no_target], "lexical_target must be clitic_entry or whole_token", "v1.1 missing lexical_target"):
            return 1

        # Red 18: root-label suppression flag contradicts an attested root.
        bad_suppression = copy.deepcopy(sample_verified_row_v11())
        bad_suppression["votes"][0]["root"] = "أ ل ه"
        if not _expect_fail(bad, [bad_suppression], "requires root=null", "v1.1 suppression with root present"):
            return 1

        # Red 19: value=none must not carry a sign or a mood_basis.
        none_with_sign = copy.deepcopy(sample_verified_row_v11())
        for vote in none_with_sign["votes"]:
            vote["conclusion"]["case_or_mood"] = {"value": "none", "sign": "fatha", "sign_visibility": "not_applicable", "mood_basis": None}
        if not _expect_fail(bad, [none_with_sign], "value=none requires sign=none", "v1.1 none with sign"):
            return 1

        # ---- the four 2026-07-29 canaries, re-keyed under v1.1 -------------
        if not os.path.exists(CANARY_FIXTURE):
            print("SELF-TEST FAIL canaries: fixture missing at %s" % CANARY_FIXTURE)
            return 1
        canary_count, canary_errors = validate(CANARY_FIXTURE)
        if canary_count != 4 or canary_errors:
            print("SELF-TEST FAIL canaries: expected 4 clean rows, got %d rows, errors:" % canary_count)
            for err in canary_errors[:10]:
                print("  -", err)
            return 1
        canary_rows = [row for _line, row in iter_jsonl(CANARY_FIXTURE)]
        if any(row.get("claim_state") != "two_vote_verified" for row in canary_rows):
            print("SELF-TEST FAIL canaries: all four must be two_vote_verified under v1.1")
            return 1
        canary1 = next(row for row in canary_rows if "quran_2_91_23" in row.get("artifact_id", ""))
        if any(vote["conclusion"]["case_or_mood"].get("mood_basis") != "tajarrud" or vote["conclusion"].get("governor") is not None
               for vote in canary1["votes"]):
            print("SELF-TEST FAIL canaries: canary 1 must pass with mood_basis=tajarrud and governor null")
            return 1

    print("PASS — two-vote artifact contract validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.jsonl:
        parser.error("jsonl path is required unless --self-test is used")
    count, errors = validate(args.jsonl)
    print("checked %d two-vote artifact rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — every two-vote claim is backed by two independent agreeing vote artifacts or honestly reclassified")


if __name__ == "__main__":
    main()
