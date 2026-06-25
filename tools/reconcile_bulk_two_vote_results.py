#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile independent two-vote results into certified or unresolved packets.

This tool never authors a vote. It only accepts two independent reviewer outputs
that already carry conclusion, authored gloss, sarf/nahw reasoning, and an
explicit reason_agreement_key. Only rows where both lenses approve the same
public gloss and the same reason key become public-clean hover decisions.
"""
import argparse
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REQUESTS = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                                "bulk_twovote_requests_batch_001.jsonl")
DEFAULT_OUT = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                           "bulk_twovote_certified_batch_001.jsonl")
DEFAULT_PROV = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                            "bulk_twovote_certified_batch_001.provenance.jsonl")
DEFAULT_UNRESOLVED = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                                  "bulk_twovote_unresolved_batch_001.jsonl")
DEFAULT_SUMMARY = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                               "bulk-two-vote-reconciliation-batch-001.json")
DEFAULT_MD = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                          "bulk-two-vote-reconciliation-batch-001.md")

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK_RE = re.compile(r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
                     r"tanzil|saheeh|sahih|tafsir|ocr|informed_by)\b", re.I)
VOTE_LENSES = ["sarf-primary", "nahw-primary"]
DECISIONS = {"approve", "reject", "pending"}


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def dump_review_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def compact(value):
    return " ".join((value or "").strip().split())


def request_by_loc(request_path):
    rows = read_jsonl(request_path)
    return {str(row["loc"]): row for row in rows}


def validate_vote(vote, requests):
    errors = []
    loc = str(vote.get("loc") or "")
    if not LOC_RE.match(loc):
        errors.append("%s: bad or missing loc" % (loc or "<missing>"))
    request = requests.get(loc)
    if request is None:
        errors.append("%s: vote loc is not in request packet" % (loc or "<missing>"))
    lens = vote.get("lens")
    if lens not in VOTE_LENSES:
        errors.append("%s: lens must be one of %s" % (loc or "<missing>", VOTE_LENSES))
    elif request and lens not in request.get("vote_lenses", []):
        errors.append("%s: lens %s not requested for this loc" % (loc, lens))
    decision = vote.get("decision")
    if decision not in DECISIONS:
        errors.append("%s/%s: decision must be approve, reject, or pending" % (loc, lens))

    gloss = compact(vote.get("concise_authored_gloss"))
    sarf_reasoning = compact(vote.get("sarf_reasoning"))
    nahw_reasoning = compact(vote.get("nahw_reasoning"))
    reason_key = compact(vote.get("reason_agreement_key"))
    if decision == "approve":
        if not gloss:
            errors.append("%s/%s: approved vote lacks concise_authored_gloss" % (loc, lens))
        if LEAK_RE.search(gloss):
            errors.append("%s/%s: public gloss leaks external source/provenance label" % (loc, lens))
        if not sarf_reasoning:
            errors.append("%s/%s: approved vote lacks sarf_reasoning" % (loc, lens))
        if not nahw_reasoning:
            errors.append("%s/%s: approved vote lacks nahw_reasoning" % (loc, lens))
        if not reason_key:
            errors.append("%s/%s: approved vote lacks reason_agreement_key" % (loc, lens))
    if decision in ("reject", "pending") and not compact(vote.get("blocker_if_rejected")):
        errors.append("%s/%s: %s vote lacks blocker_if_rejected" % (loc, lens, decision))
    return errors


def unresolved_row(request, reason, votes):
    loc = request["loc"]
    return {
        "loc": loc,
        "surface": request.get("surface_ar") or "",
        "key": request.get("key") or "",
        "suggested_lane": request.get("suggested_lane"),
        "risk": request.get("risk"),
        "unresolved_reason": reason,
        "vote_lenses_seen": sorted(votes),
        "known_blocker": request.get("known_blocker") or "",
        "vote_summaries": [
            {
                "lens": vote.get("lens"),
                "decision": vote.get("decision"),
                "gloss": compact(vote.get("concise_authored_gloss")),
                "reason_agreement_key": compact(vote.get("reason_agreement_key")),
                "blocker_if_rejected": compact(vote.get("blocker_if_rejected")),
            }
            for vote in votes.values()
        ],
    }


def _slug(value):
    value = compact(value).lower()
    out = []
    for ch in value:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")[:48] or "gloss"


def _canonical_reason_key(request, gloss):
    candidate = request.get("qamus_entry_candidate") or {}
    entry_id = candidate.get("id") or "no_entry"
    lane = request.get("suggested_lane") or "two_vote"
    return "%s:%s:%s" % (lane, entry_id, _slug(gloss))


def certified_rows_for(request, votes, request_path, reason_key=None, reconciliation_mode="exact_reason_key"):
    loc = request["loc"]
    sarf_vote = votes["sarf-primary"]
    nahw_vote = votes["nahw-primary"]
    gloss = compact(sarf_vote.get("concise_authored_gloss"))
    reason_key = reason_key or compact(sarf_vote.get("reason_agreement_key"))
    public = {
        "loc": loc,
        "gloss": gloss,
        "surface": request.get("surface_ar") or "",
        "key": request.get("key") or "",
        "state_id": "state:tok:%s" % loc,
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "decision_state": "bulk_two_vote_certified",
    }
    provenance = {
        "loc": loc,
        "surface": request.get("surface_ar") or "",
        "key": request.get("key") or "",
        "gloss": gloss,
        "review_status": "two_vote_certified",
        "votes": 2,
        "gate": "two_vote_required",
        "vote_lenses": VOTE_LENSES,
        "reason_agreement_key": reason_key,
        "reconciliation_mode": reconciliation_mode,
        "original_reason_keys": {
            "sarf-primary": compact(sarf_vote.get("reason_agreement_key")),
            "nahw-primary": compact(nahw_vote.get("reason_agreement_key")),
        },
        "sarf_reasoning": compact(sarf_vote.get("sarf_reasoning")),
        "nahw_reasoning": compact(nahw_vote.get("nahw_reasoning")),
        "qamus_entry_candidate": request.get("qamus_entry_candidate"),
        "qac": request.get("qac"),
        "suggested_lane": request.get("suggested_lane"),
        "risk": request.get("risk"),
        "source_request": os.path.relpath(request_path, ROOT),
        "public_provenance_clean": True,
    }
    return public, provenance


def reconcile_one(request, votes, allow_same_gloss_reason_reconcile=False):
    missing = [lens for lens in VOTE_LENSES if lens not in votes]
    if missing:
        return None, None, unresolved_row(request, "missing_vote", votes)
    decisions = {lens: votes[lens].get("decision") for lens in VOTE_LENSES}
    if decisions["sarf-primary"] == "pending" and decisions["nahw-primary"] == "pending":
        return None, None, unresolved_row(request, "both_votes_pending", votes)
    if decisions["sarf-primary"] == "reject" and decisions["nahw-primary"] == "reject":
        return None, None, unresolved_row(request, "both_votes_rejected", votes)
    if decisions["sarf-primary"] != "approve" or decisions["nahw-primary"] != "approve":
        return None, None, unresolved_row(request, "vote_disagreement", votes)

    sarf_gloss = compact(votes["sarf-primary"].get("concise_authored_gloss"))
    nahw_gloss = compact(votes["nahw-primary"].get("concise_authored_gloss"))
    sarf_key = compact(votes["sarf-primary"].get("reason_agreement_key"))
    nahw_key = compact(votes["nahw-primary"].get("reason_agreement_key"))
    if sarf_gloss != nahw_gloss or sarf_key != nahw_key:
        if allow_same_gloss_reason_reconcile and sarf_gloss == nahw_gloss and sarf_key and nahw_key:
            return "certified_same_gloss", _canonical_reason_key(request, sarf_gloss), None
        return None, None, unresolved_row(request, "vote_disagreement", votes)
    return "certified", sarf_key, None


def load_votes(vote_paths):
    rows = []
    for path in vote_paths:
        for row in read_jsonl(path):
            row["_vote_file"] = os.path.relpath(path, ROOT)
            rows.append(row)
    return rows


def reconcile_files(request_path, vote_paths, out_path=DEFAULT_OUT, provenance_path=DEFAULT_PROV,
                    unresolved_path=DEFAULT_UNRESOLVED, summary_path=DEFAULT_SUMMARY, report_md_path=None,
                    allow_same_gloss_reason_reconcile=False):
    requests = request_by_loc(request_path)
    votes_by_loc = collections.defaultdict(dict)
    errors = []
    votes = load_votes(vote_paths)

    for vote in votes:
        errors.extend(validate_vote(vote, requests))
        loc = str(vote.get("loc") or "")
        lens = vote.get("lens")
        if loc and lens:
            if lens in votes_by_loc[loc]:
                errors.append("%s/%s: duplicate vote lens" % (loc, lens))
            votes_by_loc[loc][lens] = vote
    if errors:
        raise ValueError("invalid vote packet:\n" + "\n".join(errors[:80]))

    public_rows = []
    provenance_rows = []
    unresolved_rows = []
    for loc in sorted(requests):
        request = requests[loc]
        status, reason_key, unresolved = reconcile_one(request, votes_by_loc.get(loc, {}),
                                                       allow_same_gloss_reason_reconcile)
        if status in ("certified", "certified_same_gloss"):
            public, provenance = certified_rows_for(
                request,
                votes_by_loc[loc],
                request_path,
                reason_key=reason_key,
                reconciliation_mode=("same_gloss_independent_approval"
                                     if status == "certified_same_gloss"
                                     else "exact_reason_key"),
            )
            public_rows.append(public)
            provenance_rows.append(provenance)
        else:
            unresolved_rows.append(unresolved)

    write_jsonl(out_path, public_rows)
    write_jsonl(provenance_path, provenance_rows)
    write_jsonl(unresolved_path, unresolved_rows)

    by_unresolved = collections.Counter(row["unresolved_reason"] for row in unresolved_rows)
    summary = {
        "_generator": "tools/reconcile_bulk_two_vote_results.py",
        "request_file": os.path.relpath(request_path, ROOT),
        "vote_files": [os.path.relpath(path, ROOT) for path in vote_paths],
        "certified_batch": os.path.relpath(out_path, ROOT),
        "provenance": os.path.relpath(provenance_path, ROOT),
        "unresolved": os.path.relpath(unresolved_path, ROOT),
        "total_requests": len(requests),
        "votes_seen": len(votes),
        "certified_rows": len(public_rows),
        "unresolved_rows": len(unresolved_rows),
        "by_unresolved_reason": dict(sorted(by_unresolved.items())),
        "allow_same_gloss_reason_reconcile": allow_same_gloss_reason_reconcile,
        "status": "reconciled_not_applied",
    }
    dump_review_json(summary_path, summary)
    if report_md_path:
        os.makedirs(os.path.dirname(report_md_path), exist_ok=True)
        lines = [
            "# Bulk two-vote reconciliation batch 001",
            "",
            "Reconciliation only. Certified rows remain unapplied until owner-gated live apply.",
            "",
            "| metric | value |",
            "|---|---:|",
            "| requests | %d |" % len(requests),
            "| votes seen | %d |" % len(votes),
            "| certified rows | %d |" % len(public_rows),
            "| unresolved rows | %d |" % len(unresolved_rows),
            "",
            "## Unresolved Reasons",
            "",
        ]
        for reason, count in sorted(by_unresolved.items()):
            lines.append("- `%s`: **%d**" % (reason, count))
        with open(report_md_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", default=DEFAULT_REQUESTS)
    parser.add_argument("--votes", action="append", required=True,
                        help="JSONL vote file. May be passed multiple times.")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--provenance", default=DEFAULT_PROV)
    parser.add_argument("--unresolved", default=DEFAULT_UNRESOLVED)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--report-md", default=DEFAULT_MD)
    parser.add_argument("--allow-same-gloss-reason-reconcile", action="store_true",
                        help=("Also certify rows where both independent lenses approve the exact same "
                              "public gloss but used different non-empty reason keys. Provenance keeps "
                              "both original keys and marks reconciliation_mode accordingly."))
    args = parser.parse_args()
    try:
        summary = reconcile_files(args.requests, args.votes, args.out, args.provenance,
                                  args.unresolved, args.summary, args.report_md,
                                  args.allow_same_gloss_reason_reconcile)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
