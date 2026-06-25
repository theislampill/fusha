#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a bulk two-vote request packet against the triangulation table.

Request packets are review inputs, not approved decisions. This validator fails
closed when a row loses table parity, weakens the two-vote boundary, omits the
reason-agreement field needed by reconciliation, or permits public source leaks.
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REQUESTS = os.path.join(ROOT, "qamus", "candidates", "qamus_2092",
                                "bulk_twovote_requests_batch_001.jsonl")
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                             "pending-source-triangulation-table.jsonl")
DEFAULT_MANIFEST = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                                "bulk-two-vote-requests-batch-001.json")

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK_RE = re.compile(r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
                     r"tanzil|saheeh|sahih|tafsir|ocr|informed_by)\b", re.I)
REQUIRED = {
    "loc", "surface_ar", "key", "ayah_context", "qac", "qamus_entry_candidate",
    "suggested_lane", "gate", "risk", "sarf_procedure", "nahw_procedure",
    "known_blocker", "vote_lenses", "requested_output", "public_boundary",
}
REQUESTED_OUTPUT_FIELDS = {
    "decision", "concise_authored_gloss", "sarf_reasoning", "nahw_reasoning",
    "reason_agreement_key", "blocker_if_rejected",
}
VOTE_LENSES = ["sarf-primary", "nahw-primary"]


def read_jsonl(path):
    rows = []
    for line_no, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((line_no, json.loads(line)))
        except Exception as exc:
            rows.append((line_no, {"__json_error__": str(exc)}))
    return rows


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def table_by_loc(table_path):
    rows = {}
    for _, row in read_jsonl(table_path):
        if row.get("loc"):
            rows[str(row["loc"])] = row
    return rows


def _expect(errors, loc, condition, message):
    if not condition:
        errors.append("%s: %s" % (loc, message))


def _public_strings(row):
    for key in ("known_blocker",):
        value = row.get(key)
        if isinstance(value, str):
            yield key, value
    requested = row.get("requested_output")
    if isinstance(requested, dict):
        for key, value in requested.items():
            if isinstance(value, str):
                yield "requested_output.%s" % key, value


def validate_row(line_no, row, source_row=None, require_lang_en=False):
    errors = []
    if "__json_error__" in row:
        return ["line %d: bad JSON (%s)" % (line_no, row["__json_error__"])]
    loc = str(row.get("loc") or "line %d" % line_no)

    missing = sorted(k for k in REQUIRED if k not in row)
    if missing:
        errors.append("%s: missing required field(s): %s" % (loc, ", ".join(missing)))
    if not LOC_RE.match(str(row.get("loc", ""))):
        errors.append("line %d: bad loc %r" % (line_no, row.get("loc")))
    if row.get("gate") != "two_vote":
        errors.append("%s: gate must be two_vote" % loc)
    if row.get("risk") not in ("low", "medium"):
        errors.append("%s: risk must be low or medium for request packet" % loc)
    if row.get("vote_lenses") != VOTE_LENSES:
        errors.append("%s: vote_lenses must be %s" % (loc, VOTE_LENSES))

    boundary = row.get("public_boundary")
    if not isinstance(boundary, dict):
        errors.append("%s: public_boundary must be object" % loc)
    else:
        _expect(errors, loc, boundary.get("src") == "qamus", "public_boundary.src must be qamus")
        _expect(errors, loc, boundary.get("kind") == "authored", "public_boundary.kind must be authored")
        if require_lang_en or "lang" in boundary:
            _expect(errors, loc, boundary.get("lang") == "en", "public_boundary.lang must be en")
        _expect(errors, loc, boundary.get("external_text_allowed") is False,
                "external text must not be allowed")
        _expect(errors, loc, boundary.get("external_source_names_public_allowed") is False,
                "external source names must not be public-allowed")

    requested = row.get("requested_output")
    if not isinstance(requested, dict):
        errors.append("%s: requested_output must be object" % loc)
    else:
        missing_requested = sorted(k for k in REQUESTED_OUTPUT_FIELDS if k not in requested)
        if missing_requested:
            errors.append("%s: requested_output missing field(s): %s" %
                          (loc, ", ".join(missing_requested)))
        if requested.get("decision") != "approve | reject | pending":
            errors.append("%s: requested_output.decision template changed" % loc)

    qac = row.get("qac")
    if not isinstance(qac, dict):
        errors.append("%s: qac must be object" % loc)
    candidate = row.get("qamus_entry_candidate")
    if not isinstance(candidate, dict):
        errors.append("%s: qamus_entry_candidate must be object" % loc)

    for field, value in _public_strings(row):
        if LEAK_RE.search(value):
            errors.append("%s: %s leaks an external source/provenance label" % (loc, field))

    if source_row is None:
        return errors

    _expect(errors, loc, source_row.get("gate") == "two_vote", "source table row is not two_vote")
    _expect(errors, loc, source_row.get("public_payload_allowed") == "yes",
            "source table row is not public-payload-eligible")
    _expect(errors, loc, source_row.get("risk") in ("low", "medium"),
            "source table row risk is not low/medium")
    _expect(errors, loc, row.get("surface_ar") == source_row.get("surface_ar"), "surface parity mismatch")
    expected_key = source_row.get("strict_nk") or source_row.get("nk") or ""
    _expect(errors, loc, row.get("key") == expected_key, "key parity mismatch")
    if isinstance(qac, dict):
        _expect(errors, loc, qac.get("root") == source_row.get("qac_root"), "qac parity mismatch: root")
        _expect(errors, loc, qac.get("pos") == source_row.get("qac_pos"), "qac parity mismatch: pos")
    if isinstance(candidate, dict):
        _expect(errors, loc, candidate.get("id") == source_row.get("qamus_entry_candidate"),
                "qamus candidate parity mismatch: id")
        _expect(errors, loc, candidate.get("headword") == source_row.get("qamus_entry_headword"),
                "qamus candidate parity mismatch: headword")
        _expect(errors, loc, candidate.get("match_type") == source_row.get("qamus_entry_match_type"),
                "qamus candidate parity mismatch: match_type")
        _expect(errors, loc, candidate.get("pos_agreement") == source_row.get("pos_agreement"),
                "qamus candidate parity mismatch: pos_agreement")
    _expect(errors, loc, row.get("suggested_lane") == source_row.get("suggested_lane"), "lane parity mismatch")
    _expect(errors, loc, row.get("risk") == source_row.get("risk"), "risk parity mismatch")
    _expect(errors, loc, row.get("known_blocker") == source_row.get("blocker_if_not_resolved"),
            "known_blocker parity mismatch")
    return errors


def _manifest_errors(request_path, request_rows, manifest_path, table_path=None, require_checksums=False):
    if not manifest_path:
        return []
    errors = []
    if not os.path.exists(manifest_path):
        return ["manifest not found: %s" % manifest_path]
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    if manifest.get("rows") != len(request_rows):
        errors.append("manifest rows %r != request rows %d" % (manifest.get("rows"), len(request_rows)))
    manifest_table = manifest.get("source_table")
    if manifest_table and table_path:
        expected = os.path.normpath(os.path.relpath(table_path, ROOT))
        observed = os.path.normpath(manifest_table)
        if expected != observed:
            errors.append("manifest source_table %r != %r" % (manifest_table, expected))
    manifest_request = manifest.get("request_file")
    if manifest_request:
        expected = os.path.normpath(os.path.relpath(request_path, ROOT))
        observed = os.path.normpath(manifest_request)
        if expected != observed:
            errors.append("manifest request_file %r != %r" % (manifest_request, expected))

    source_hash = manifest.get("source_table_sha256")
    request_hash = manifest.get("request_file_sha256")
    if require_checksums and table_path and not source_hash:
        errors.append("manifest missing source_table_sha256")
    if require_checksums and not request_hash:
        errors.append("manifest missing request_file_sha256")
    if source_hash and table_path and os.path.exists(table_path):
        got = sha256_file(table_path)
        if got != source_hash:
            errors.append("manifest source_table_sha256 %r != current %r" % (source_hash, got))
    if request_hash and os.path.exists(request_path):
        got = sha256_file(request_path)
        if got != request_hash:
            errors.append("manifest request_file_sha256 %r != current %r" % (request_hash, got))

    chunk_hashes = manifest.get("chunk_sha256") or {}
    if require_checksums and manifest.get("chunks") and not chunk_hashes:
        errors.append("manifest missing chunk_sha256")
    chunk_locs = []
    for chunk in manifest.get("chunks") or []:
        chunk_path = chunk if os.path.isabs(chunk) else os.path.join(ROOT, os.path.normpath(chunk))
        if not os.path.exists(chunk_path):
            errors.append("manifest chunk not found: %s" % chunk)
            continue
        expected_hash = chunk_hashes.get(chunk)
        if expected_hash:
            got = sha256_file(chunk_path)
            if got != expected_hash:
                errors.append("manifest chunk_sha256[%s] %r != current %r" % (chunk, expected_hash, got))
        elif require_checksums:
            errors.append("manifest missing chunk_sha256 for %s" % chunk)
        chunk_locs.extend(str(row.get("loc")) for _, row in read_jsonl(chunk_path))
    if chunk_locs:
        request_locs = [str(row.get("loc")) for row in request_rows]
        if chunk_locs != request_locs:
            errors.append("manifest chunk concatenation does not match request row order")
    return errors


def validate_files(request_path=DEFAULT_REQUESTS, table_path=DEFAULT_TABLE, manifest_path=None, require_lang_en=False,
                   require_checksums=False):
    errors = []
    table = table_by_loc(table_path) if table_path else {}
    request_pairs = read_jsonl(request_path)
    request_rows = []
    seen = set()

    for line_no, row in request_pairs:
        loc = str(row.get("loc") or "")
        request_rows.append(row)
        if loc:
            if loc in seen:
                errors.append("%s: duplicate request row" % loc)
            seen.add(loc)
        source_row = table.get(loc) if table else None
        if table and source_row is None:
            errors.append("%s: loc not present in source table" % (loc or "line %d" % line_no))
        errors.extend(validate_row(line_no, row, source_row, require_lang_en=require_lang_en))
    errors.extend(_manifest_errors(request_path, request_rows, manifest_path, table_path=table_path,
                                   require_checksums=require_checksums))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("requests", nargs="?", default=DEFAULT_REQUESTS)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--no-manifest", action="store_true")
    parser.add_argument(
        "--require-lang-en",
        action="store_true",
        help="require public_boundary.lang='en' for newly generated review packets; legacy packets may omit it",
    )
    parser.add_argument(
        "--require-checksums",
        action="store_true",
        help="require and verify manifest source/request/chunk sha256 fields for fresh generated packets",
    )
    args = parser.parse_args()
    manifest = None if args.no_manifest else args.manifest
    errors = validate_files(args.requests, table_path=args.table, manifest_path=manifest,
                            require_lang_en=args.require_lang_en,
                            require_checksums=args.require_checksums)
    checked = len(read_jsonl(args.requests))
    print("checked %d two-vote request row(s)" % checked)
    if errors:
        print("FAIL:")
        for error in errors[:80]:
            print("  -", error)
        if len(errors) > 80:
            print("  ... %d more" % (len(errors) - 80))
        sys.exit(1)
    print("PASS — two-vote request packet table parity + public boundary OK")


if __name__ == "__main__":
    main()
