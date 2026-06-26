#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Qamus hover decision linkage JSONL rows.

Decision linkage rows are the durable bridge between a rendered hover slot,
the exact Qur'an token, the parse-family key, and the entry/sense or blocker.
This validator is deliberately stricter than the historical builder output:
bare locations such as 33:63:1 are not accepted as decision identity.
"""
import argparse
import io
import json
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "decision-linkage.schema.json")
DECISION = re.compile(r"^decision:[A-Za-z0-9_.:-]+$")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:[0-9a-f]+$")
ENTRY_SENSE = re.compile(r"^qamus:.+#sense=\d+$")
BLOCKER = re.compile(r"^blocker:[A-Za-z0-9_.:-]+$")
STATUSES = {"resolved", "pending", "blocked", "superseded"}
GATES = {
    "auto_safe",
    "token_review",
    "auto_safe_after_preview",
    "two_vote_required",
    "human_review_required",
    "owner_review_required",
    "never_auto",
    "unknown",
}
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
UNSAFE_CERT_MARKERS = ("norm_only", "surface_only", "raw_surface")
REQUIRED = ["decision_id", "quran_loc", "wbw_loc", "parse_id", "gate", "status", "public_boundary"]


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


def _err(errors, line_no, msg):
    errors.append("line %d: %s" % (line_no, msg))


def public_boundary_errors(boundary):
    errors = []
    if not isinstance(boundary, dict):
        return ["public_boundary must be an object"]
    expected = {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            errors.append("public_boundary.%s must be %r" % (key, value))
    blob = json.dumps(boundary, ensure_ascii=False).lower()
    for label in FORBIDDEN_PUBLIC_LABELS:
        if label in blob:
            errors.append("public_boundary leaks forbidden label %r" % label)
    return errors


def validate_row(row, line_no, errors):
    if "__json_error__" in row:
        _err(errors, line_no, "bad JSON (%s)" % row["__json_error__"])
        return

    for field in REQUIRED:
        if field not in row:
            _err(errors, line_no, "missing %s" % field)

    if not DECISION.match(str(row.get("decision_id") or "")):
        _err(errors, line_no, "decision_id must be decision:<id>")
    if not QURAN.match(str(row.get("quran_loc") or "")):
        _err(errors, line_no, "quran_loc must be quran:S:A:W")
    if not WBW.match(str(row.get("wbw_loc") or "")):
        _err(errors, line_no, "wbw_loc must be wbw:S:A:W")
    if not PARSE.match(str(row.get("parse_id") or "")):
        _err(errors, line_no, "parse_id must be parse:<hash>")
    if row.get("gate") not in GATES:
        _err(errors, line_no, "bad gate %r" % row.get("gate"))
    status = row.get("status")
    if status not in STATUSES:
        _err(errors, line_no, "bad status %r" % status)

    entry_sense = row.get("entry_sense")
    blocker = row.get("blocker")
    if entry_sense is not None and not ENTRY_SENSE.match(str(entry_sense)):
        _err(errors, line_no, "entry_sense must be qamus:<id>#sense=<n> or null")
    if blocker is not None and not BLOCKER.match(str(blocker)):
        _err(errors, line_no, "blocker must be blocker:<reason> or null")
    if status == "resolved" and not entry_sense:
        _err(errors, line_no, "resolved decision requires entry_sense")
    if status in {"pending", "blocked"} and not blocker:
        _err(errors, line_no, "pending/blocked decision requires blocker")
    if status == "superseded" and row.get("gate") == "auto_safe":
        _err(errors, line_no, "superseded decision cannot remain auto_safe")

    internal_evidence = row.get("internal_evidence") or []
    if not isinstance(internal_evidence, list):
        _err(errors, line_no, "internal_evidence must be an array")
        internal_evidence = []
    for value in internal_evidence:
        lowered = str(value).lower()
        if any(marker in lowered for marker in UNSAFE_CERT_MARKERS) and row.get("gate") in {"auto_safe", "auto_safe_after_preview"}:
            _err(errors, line_no, "norm/surface-only evidence cannot support an auto-safe decision")

    for msg in public_boundary_errors(row.get("public_boundary")):
        _err(errors, line_no, msg)


def validate(path):
    errors = []
    count = 0
    if not os.path.exists(SCHEMA):
        errors.append("schema missing: %s" % SCHEMA)
    for line_no, row in iter_jsonl(path):
        count += 1
        validate_row(row, line_no, errors)
    if count == 0:
        errors.append("zero decision linkage rows")
    return count, errors


def public_boundary():
    return {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
        "public_fields": ["gloss", "src", "kind", "lang"],
        "private_fields": ["internal_evidence", "adapter_labels"],
    }


def good_row(status="resolved"):
    row = {
        "decision_id": "decision:token-33-63-1",
        "quran_loc": "quran:33:63:1",
        "wbw_loc": "wbw:33:63:1",
        "parse_id": "parse:aaaaaaaa",
        "entry_sense": "qamus:5935ecfb1ec5#sense=2",
        "blocker": None,
        "gate": "token_review",
        "status": status,
        "internal_evidence": ["procedure:sarf:clitic-and-host-morphology", "procedure:nahw:pronoun-attachment"],
        "public_boundary": public_boundary(),
    }
    if status in {"pending", "blocked"}:
        row.update({
            "decision_id": "decision:pending-22-18-17",
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "parse_id": "parse:bbbbbbbb",
            "entry_sense": None,
            "blocker": "blocker:human_review_required",
            "gate": "human_review_required",
        })
    if status == "superseded":
        row.update({"gate": "token_review"})
    return row


def self_test():
    with tempfile.TemporaryDirectory(prefix="decision-linkage-") as td:
        good = os.path.join(td, "good.jsonl")
        bad = os.path.join(td, "bad.jsonl")
        with io.open(good, "w", encoding="utf-8", newline="\n") as handle:
            for status in ("resolved", "pending", "blocked", "superseded"):
                handle.write(json.dumps(good_row(status), ensure_ascii=False, sort_keys=True) + "\n")
        bad_row = good_row()
        bad_row["quran_loc"] = "33:63:1"
        with io.open(bad, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(bad_row, ensure_ascii=False, sort_keys=True) + "\n")
        count, errors = validate(good)
        if count != 4 or errors:
            print("SELF-TEST FAIL good:", errors)
            return 1
        count, errors = validate(bad)
        if count != 1 or not any("quran_loc must be quran:S:A:W" in err for err in errors):
            print("SELF-TEST FAIL bad:", errors)
            return 1
    print("PASS — decision linkage validator self-test")
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
    print("checked %d decision linkage rows" % count)
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  -", err)
        raise SystemExit(1)
    print("PASS — decision linkages are exact-addressed and source-clean")


if __name__ == "__main__":
    main()
