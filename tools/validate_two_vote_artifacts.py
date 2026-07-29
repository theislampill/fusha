#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate two-vote artifact bundles (qamus.two_vote_artifact.v1).

A row claiming `two_vote` / `bulk_two_vote_certified` is only `two_vote_verified`
when TWO reconstructible, independent vote records exist and agree on the
grammatical CONCLUSION and the REASON key — never on gloss text alone.
Historical claims without artifacts are representable only as
`two_vote_claimed_unverified` (a reclassification state); votes are never
fabricated for them.
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


def validate_vote(vote, line_no, index, bundle_occurrence, errors):
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


def recompute_agreement(votes):
    """Agreement is computed on conclusion AND reason fields, never on gloss text."""
    first, second = votes
    conclusion_agrees = (
        canonical_conclusion(first.get("conclusion")) is not None
        and canonical_conclusion(first.get("conclusion")) == canonical_conclusion(second.get("conclusion"))
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

    if row.get("schema") != "qamus.two_vote_artifact.v1":
        _err(errors, line_no, "schema must be qamus.two_vote_artifact.v1")
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
        validate_vote(vote, line_no, index, occurrence if occurrence else None, errors)

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

    conclusion_agrees, reason_agrees = recompute_agreement(votes)
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
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
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
