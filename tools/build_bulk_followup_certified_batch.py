#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert follow-up review JSONL into certified hover decisions.

This is for bounded second-pass lanes after the primary two-vote pass, such as:
- arbiter review of two approved but differently worded glosses;
- sarf recheck of rows where nahw approved and sarf originally pended.

It does not author decisions. It accepts only explicit follow-up approvals and
writes public-clean token hover decisions plus internal provenance.
"""
import argparse
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK_RE = re.compile(
    r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
    r"tanzil|saheeh|sahih|tafsir|ocr|informed_by)\b",
    re.I,
)
DECISIONS = {"approve", "reject", "pending"}


def compact(value):
    return " ".join((value or "").strip().split())


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def dump_review_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def request_by_loc(path):
    return {str(row["loc"]): row for row in read_jsonl(path)}


def _review_public_fields(review):
    return {
        "confidence": compact(review.get("confidence")),
        "evidence_note": compact(review.get("evidence_note")),
        "reason_key": compact(review.get("reason_key")),
        "selected_from": compact(review.get("selected_from")),
        "agrees_with_nahw": review.get("agrees_with_nahw"),
    }


def validate_review(review, requests, require_agrees_with_nahw=False):
    errors = []
    loc = str(review.get("loc") or "")
    if not LOC_RE.match(loc):
        errors.append("%s: bad or missing loc" % (loc or "<missing>"))
    if loc and loc not in requests:
        errors.append("%s: review loc is not in request packet" % loc)
    decision = review.get("decision")
    if decision not in DECISIONS:
        errors.append("%s: decision must be approve, reject, or pending" % (loc or "<missing>"))
    gloss = compact(review.get("concise_authored_gloss"))
    reason_key = compact(review.get("reason_key"))
    evidence_note = compact(review.get("evidence_note"))
    if decision == "approve":
        if not gloss:
            errors.append("%s: approved review lacks concise_authored_gloss" % loc)
        if LEAK_RE.search(gloss):
            errors.append("%s: public gloss leaks external source/provenance label" % loc)
        if not reason_key:
            errors.append("%s: approved review lacks reason_key" % loc)
        if not evidence_note:
            errors.append("%s: approved review lacks evidence_note" % loc)
        if require_agrees_with_nahw and review.get("agrees_with_nahw") is not True:
            errors.append("%s: approved recheck must explicitly agree with nahw" % loc)
    if decision in ("pending", "reject") and gloss:
        errors.append("%s: unresolved review should not carry public gloss text" % loc)
    return errors


def public_row(request, review, decision_state):
    loc = str(request["loc"])
    return {
        "decision_state": decision_state,
        "gloss": compact(review.get("concise_authored_gloss")),
        "key": request.get("key") or "",
        "kind": "authored",
        "lang": "en",
        "loc": loc,
        "src": "qamus",
        "state_id": "state:tok:%s" % loc,
        "surface": request.get("surface_ar") or "",
    }


def provenance_row(request, review, request_path, review_path, batch_label, review_lens):
    loc = str(request["loc"])
    return {
        "batch_label": batch_label,
        "confidence": compact(review.get("confidence")),
        "evidence_note": compact(review.get("evidence_note")),
        "gate": "followup_review_required",
        "gloss": compact(review.get("concise_authored_gloss")),
        "key": request.get("key") or "",
        "loc": loc,
        "public_provenance_clean": True,
        "qac": request.get("qac"),
        "qamus_entry_candidate": request.get("qamus_entry_candidate"),
        "reason_key": compact(review.get("reason_key")),
        "review_lens": review_lens,
        "review_status": "followup_certified",
        "reviewer_fields": _review_public_fields(review),
        "risk": request.get("risk"),
        "source_request": os.path.relpath(request_path, ROOT),
        "source_review": os.path.relpath(review_path, ROOT),
        "suggested_lane": request.get("suggested_lane"),
        "surface": request.get("surface_ar") or "",
        "votes": 3,
    }


def unresolved_row(request, review, review_lens):
    loc = str(request["loc"])
    return {
        "decision": review.get("decision"),
        "evidence_note": compact(review.get("evidence_note")),
        "key": request.get("key") or "",
        "loc": loc,
        "reason_key": compact(review.get("reason_key")),
        "review_lens": review_lens,
        "risk": request.get("risk"),
        "suggested_lane": request.get("suggested_lane"),
        "surface": request.get("surface_ar") or "",
        "unresolved_reason": compact(review.get("reason_key")) or str(review.get("decision")),
    }


def build_batch(
    request_path,
    review_path,
    out_path,
    provenance_path,
    unresolved_path,
    summary_path,
    report_md_path=None,
    batch_label="followup",
    review_lens="followup",
    decision_state="bulk_followup_certified",
    require_agrees_with_nahw=False,
):
    requests = request_by_loc(request_path)
    reviews = read_jsonl(review_path)
    errors = []
    seen = set()
    for review in reviews:
        loc = str(review.get("loc") or "")
        if loc in seen:
            errors.append("%s: duplicate follow-up review" % loc)
        seen.add(loc)
        errors.extend(validate_review(review, requests, require_agrees_with_nahw))
    if errors:
        raise ValueError("invalid follow-up review packet:\n" + "\n".join(errors[:80]))

    public_rows = []
    provenance_rows = []
    unresolved_rows = []
    for review in reviews:
        loc = str(review["loc"])
        request = requests[loc]
        if review.get("decision") == "approve":
            public_rows.append(public_row(request, review, decision_state))
            provenance_rows.append(
                provenance_row(request, review, request_path, review_path, batch_label, review_lens)
            )
        else:
            unresolved_rows.append(unresolved_row(request, review, review_lens))

    write_jsonl(out_path, public_rows)
    write_jsonl(provenance_path, provenance_rows)
    write_jsonl(unresolved_path, unresolved_rows)

    by_decision = collections.Counter(row.get("decision") for row in reviews)
    by_unresolved = collections.Counter(row["unresolved_reason"] for row in unresolved_rows)
    summary = {
        "_generator": "tools/build_bulk_followup_certified_batch.py",
        "batch_label": batch_label,
        "review_lens": review_lens,
        "request_file": os.path.relpath(request_path, ROOT),
        "review_file": os.path.relpath(review_path, ROOT),
        "certified_batch": os.path.relpath(out_path, ROOT),
        "provenance": os.path.relpath(provenance_path, ROOT),
        "unresolved": os.path.relpath(unresolved_path, ROOT),
        "reviews_seen": len(reviews),
        "certified_rows": len(public_rows),
        "unresolved_rows": len(unresolved_rows),
        "by_decision": dict(sorted(by_decision.items())),
        "by_unresolved_reason": dict(sorted(by_unresolved.items())),
        "require_agrees_with_nahw": require_agrees_with_nahw,
        "status": "followup_certified_not_applied",
    }
    dump_review_json(summary_path, summary)
    if report_md_path:
        os.makedirs(os.path.dirname(report_md_path), exist_ok=True)
        lines = [
            "# Bulk follow-up review certification",
            "",
            "Certification only. Rows remain unapplied until owner-gated live apply.",
            "",
            "| metric | value |",
            "|---|---:|",
            "| reviews seen | %d |" % len(reviews),
            "| certified rows | %d |" % len(public_rows),
            "| unresolved rows | %d |" % len(unresolved_rows),
            "",
            "## Decisions",
            "",
        ]
        for decision, count in sorted(by_decision.items()):
            lines.append("- `%s`: **%d**" % (decision, count))
        lines.extend(["", "## Unresolved Reasons", ""])
        for reason, count in sorted(by_unresolved.items()):
            lines.append("- `%s`: **%d**" % (reason, count))
        with open(report_md_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--unresolved", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--report-md")
    parser.add_argument("--batch-label", default="followup")
    parser.add_argument("--review-lens", default="followup")
    parser.add_argument("--decision-state", default="bulk_followup_certified")
    parser.add_argument("--require-agrees-with-nahw", action="store_true")
    args = parser.parse_args()
    try:
        summary = build_batch(
            args.requests,
            args.reviews,
            args.out,
            args.provenance,
            args.unresolved,
            args.summary,
            args.report_md,
            args.batch_label,
            args.review_lens,
            args.decision_state,
            args.require_agrees_with_nahw,
        )
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
