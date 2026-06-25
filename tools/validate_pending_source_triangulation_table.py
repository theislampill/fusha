#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the all-pending source-triangulation table.

The table is internal evidence, not a public artifact. This validator still fails
closed on anything that would make downstream public hover payloads unsafe:
missing pending locs, source-name leaks in public/proposed fields, weak auto rows,
vague blockers, or owner/source lanes without exact gates.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092",
                             "pending-source-triangulation-table.jsonl")
DEFAULT_AUDIT = os.path.join(ROOT, "qamus", "reports", "hover-token-audit-full.jsonl")

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
LEAK_RE = re.compile(r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
                     r"tanzil|saheeh|sahih|tafsir|ocr)\b", re.I)
VAGUE_RE = re.compile(r"^(owner[- ]gated|needs review|needs owner|blocked|unknown|ambiguous|pending)$", re.I)
VERB_GLOSS_RE = re.compile(r"^to\s+\w+", re.I)
CONSTRUCT_KEYS = {"ذو", "ذا", "ذي", "ذات", "ذوات"}

REQUIRED = {
    "loc", "surface_ar", "nk", "strict_nk", "blocker", "root_cause",
    "qac_root", "qac_pos", "qamus_entry_candidate", "qamus_entry_match_type",
    "qac_evidence", "quran_adapter_evidence", "pos_agreement",
    "sarf_procedure", "nahw_procedure", "suggested_lane",
    "deterministic_resolvable", "deterministic_reason", "proposed_gloss",
    "risk", "gate", "public_payload_allowed", "public_provenance_clean",
    "blocker_if_not_resolved",
}

MATCH_TYPES = {"exact_form", "usage_form", "root_match", "sense_match", "no_entry", "collision"}
EVIDENCE = {"available", "unavailable", "conflict"}
POS_AGREE = {"agree", "mismatch", "unknown"}
LANES = {
    "auto_resolve_deterministic", "token_irab", "form_variant", "host_lexeme",
    "verb_clitic", "source_entry_repair", "new_entry_proposal", "index_rebuild",
    "source_photo", "scholar_review", "reject_unsafe",
}
RISKS = {"low", "medium", "high", "scholar"}
GATES = {"auto_rule", "two_vote", "source", "owner", "scholar"}


def load_jsonl(path):
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


def pending_locs_from_audit(path):
    locs = set()
    for _, row in load_jsonl(path):
        if row.get("decision_state") == "pending":
            loc = row.get("quran_loc")
            if loc:
                locs.add(str(loc))
    return locs


def public_text_values(row):
    for key in ("proposed_gloss", "deterministic_reason", "blocker_if_not_resolved"):
        value = row.get(key)
        if isinstance(value, str):
            yield key, value


def enum_check(errors, loc, label, value, allowed):
    if value not in allowed:
        errors.append("%s: %s=%r not in %s" % (loc, label, value, sorted(allowed)))


def validate_row(line_no, row):
    errors = []
    if "__json_error__" in row:
        return ["line %d: bad JSON (%s)" % (line_no, row["__json_error__"])]

    loc = row.get("loc", "line %d" % line_no)
    missing = sorted(k for k in REQUIRED if k not in row)
    if missing:
        errors.append("%s: missing required field(s): %s" % (loc, ", ".join(missing)))
    if not LOC_RE.match(str(row.get("loc", ""))):
        errors.append("line %d: bad loc %r" % (line_no, row.get("loc")))

    enum_check(errors, loc, "qamus_entry_match_type", row.get("qamus_entry_match_type"), MATCH_TYPES)
    enum_check(errors, loc, "qac_evidence", row.get("qac_evidence"), EVIDENCE)
    enum_check(errors, loc, "quran_adapter_evidence", row.get("quran_adapter_evidence"), EVIDENCE)
    enum_check(errors, loc, "pos_agreement", row.get("pos_agreement"), POS_AGREE)
    enum_check(errors, loc, "suggested_lane", row.get("suggested_lane"), LANES)
    enum_check(errors, loc, "risk", row.get("risk"), RISKS)
    enum_check(errors, loc, "gate", row.get("gate"), GATES)
    enum_check(errors, loc, "public_payload_allowed", row.get("public_payload_allowed"), {"yes", "no"})
    if not isinstance(row.get("public_provenance_clean"), bool):
        errors.append("%s: public_provenance_clean must be boolean" % loc)
    if not isinstance(row.get("deterministic_resolvable"), bool):
        errors.append("%s: deterministic_resolvable must be boolean" % loc)

    for key, value in public_text_values(row):
        if LEAK_RE.search(value):
            errors.append("%s: %s leaks an external source name" % (loc, key))

    det = row.get("deterministic_resolvable") is True
    if det:
        if row.get("suggested_lane") != "auto_resolve_deterministic":
            errors.append("%s: deterministic row must use auto_resolve_deterministic lane" % loc)
        if row.get("gate") != "auto_rule":
            errors.append("%s: deterministic row must use auto_rule gate" % loc)
        if not row.get("proposed_gloss"):
            errors.append("%s: deterministic row lacks proposed authored gloss" % loc)
        if row.get("pos_agreement") == "mismatch":
            errors.append("%s: deterministic row has POS mismatch" % loc)
        if row.get("qamus_entry_match_type") == "collision":
            errors.append("%s: collision row cannot be deterministic" % loc)
        if row.get("qac_evidence") != "available" or not row.get("qac_root"):
            errors.append("%s: deterministic row lacks available QAC root evidence" % loc)
        if row.get("strict_nk") in CONSTRUCT_KEYS or row.get("qamus_entry_headword") in {"ذُو", "ذو", "ذَات", "ذات"}:
            errors.append("%s: ذو/ذات construct row cannot be deterministic" % loc)
        reason = row.get("deterministic_reason") or ""
        if not reason or "single sense" not in reason.lower():
            errors.append("%s: deterministic row lacks per-loc deterministic reasoning" % loc)

    qac_pos = row.get("qac_pos")
    gloss = (row.get("proposed_gloss") or "").strip()
    if det and qac_pos == "N" and VERB_GLOSS_RE.match(gloss):
        errors.append("%s: noun/verb POS mismatch marked auto-resolve" % loc)
    if det and qac_pos == "V" and gloss and not VERB_GLOSS_RE.match(gloss):
        errors.append("%s: verb/nominal POS mismatch marked auto-resolve" % loc)
    if qac_pos == "P":
        if not row.get("nahw_procedure"):
            errors.append("%s: particle row lacks function/nahw procedure" % loc)

    if row.get("root_cause") == "verb_clitic_object_or_subject_candidate" and row.get("suggested_lane") == "host_lexeme":
        errors.append("%s: verb-clitic row routed to host_lexeme" % loc)
    if row.get("suggested_lane") == "new_entry_proposal" and row.get("gate") != "owner":
        errors.append("%s: new-entry row lacks owner gate" % loc)
    if row.get("suggested_lane") == "source_entry_repair":
        if row.get("gate") != "source":
            errors.append("%s: source-entry repair row lacks source gate" % loc)
        if not row.get("affected_field_path"):
            errors.append("%s: source-entry repair row lacks affected field path" % loc)
    blocker = (row.get("blocker_if_not_resolved") or "").strip()
    if not blocker or VAGUE_RE.match(blocker):
        errors.append("%s: vague blocker_if_not_resolved" % loc)
    return errors


def validate_files(table_path=DEFAULT_TABLE, audit_path=DEFAULT_AUDIT):
    errors = []
    rows = load_jsonl(table_path)
    pending_locs = pending_locs_from_audit(audit_path)
    table_locs = []

    for line_no, row in rows:
        loc = row.get("loc")
        if loc:
            table_locs.append(str(loc))
        errors.extend(validate_row(line_no, row))

    seen = set()
    for loc in table_locs:
        if loc in seen:
            errors.append("%s: duplicate table row" % loc)
        seen.add(loc)
    table_set = set(table_locs)
    for loc in sorted(pending_locs - table_set)[:50]:
        errors.append("%s: missing table row for pending token" % loc)
    for loc in sorted(table_set - pending_locs)[:50]:
        errors.append("%s: extra table row not pending in hover audit" % loc)
    if len(table_set) != len(pending_locs):
        errors.append("row-count mismatch: table=%d pending_audit=%d" % (len(table_set), len(pending_locs)))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("table", nargs="?", default=DEFAULT_TABLE)
    parser.add_argument("--audit", default=DEFAULT_AUDIT)
    args = parser.parse_args()
    errors = validate_files(args.table, args.audit)
    checked = len(load_jsonl(args.table))
    print("checked %d triangulation row(s)" % checked)
    if errors:
        print("FAIL:")
        for error in errors[:80]:
            print("  -", error)
        if len(errors) > 80:
            print("  ... %d more" % (len(errors) - 80))
        sys.exit(1)
    print("PASS — pending coverage + required fields + safety gates OK")


if __name__ == "__main__":
    main()
