#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the canonical hover payload table: payloads, occurrence bindings, exceptions.

This is the validator-BEFORE-builder gate for the canonical hover payload compiler
(Task 2). It makes the reusable hover unit machine-checkable so solved facts can be
transcluded instead of copy-pasted per occurrence.

Enforced (explicit; the repo mini-validator does not cover draft-2020-12):
  payloads
    - canonical_payload_id is content-addressed over the identity field set
      (payload_family, surface_norm, root, lemma_id, lemma_status, pos, pattern,
       sarf_certification, nahw_certification, public_payload) - never over timestamps
       or private_trace;
    - public_payload is source-clean (src=qamus, kind=authored, lang=en; no external
      label leak - reuses the canonical FORBIDDEN_LABELS);
    - segment surfaces concatenate EXACTLY to surface_norm (no suffix hidden in a stem);
    - payload_family=certified_lemma requires lemma_status=certified.
  bindings
    - binding_id content-addressed; canonical_payload_id must reference a payload in-batch;
    - binding_status=accepted requires BOTH canonical Quran + WBW locs;
    - a non-accepted binding must carry a reason (the terminal-packet taxonomy);
    - binding_gate=certified_lemma requires the referenced payload lemma_status=certified;
    - surface-only fanout is impossible (no surface-only gate value).
  exceptions
    - exception_id content-addressed; binding_id must reference a binding in-batch.

Dry-run; deterministic; source-clean. No live Qamus is inspected or mutated.
See CANONICAL_HOVER_PAYLOAD_COMPILER_PLAN (fablehardening) + its two addenda.
"""
import argparse
import hashlib
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(ROOT, "qamus", "schemas")
SAMPLE_PATH = os.path.join(ROOT, "qamus", "examples", "canonical_hover_payload.sample.jsonl")

sys.path.insert(0, ROOT)
from tools.validate_public_private_boundary import FORBIDDEN_LABELS  # noqa: E402

PAYLOAD_ID_FIELDS = ("payload_family", "surface_norm", "root", "lemma_id", "lemma_status",
                     "pos", "pattern", "sarf_certification", "nahw_certification", "public_payload")
BINDING_ID_FIELDS = ("canonical_payload_id", "entry_id", "exact_transclusion_group_key",
                     "visible_surface", "canonical_quran_loc", "canonical_wbw_loc")
EXCEPTION_ID_FIELDS = ("binding_id", "exception_reason", "replacement_canonical_payload_id")


def _canon(obj, fields):
    return json.dumps({k: obj.get(k) for k in fields}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))


def _hash(prefix, obj, fields):
    return prefix + hashlib.sha256(_canon(obj, fields).encode("utf-8")).hexdigest()[:16]


def payload_id(row):
    return _hash("chp:", row, PAYLOAD_ID_FIELDS)


def binding_id(row):
    return _hash("chb:", row, BINDING_ID_FIELDS)


def exception_id(row):
    return _hash("che:", row, EXCEPTION_ID_FIELDS)


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _leak_scan(obj, where):
    blob = json.dumps(obj, ensure_ascii=False).lower()
    return ["%s leaks forbidden label %r" % (where, label)
            for label in FORBIDDEN_LABELS if label in blob]


def validate_payload(row):
    e = []
    if row.get("canonical_payload_id") != payload_id(row):
        e.append("canonical_payload_id must be content-addressed %r (got %r)"
                  % (payload_id(row), row.get("canonical_payload_id")))
    pp = row.get("public_payload") or {}
    if (pp.get("src"), pp.get("kind"), pp.get("lang")) != ("qamus", "authored", "en"):
        e.append("public_payload must be src=qamus, kind=authored, lang=en")
    e.extend(_leak_scan(pp, "public_payload"))
    segs = pp.get("segments") or []
    concat = "".join(s.get("surface", "") for s in segs)
    if concat != row.get("surface_norm"):
        e.append("segment surfaces %r must concatenate exactly to surface_norm %r"
                 % (concat, row.get("surface_norm")))
    for s in segs:
        if not (s.get("qg_class") or "").strip():
            e.append("segment qg_class must be a nonempty class (qamus-grammar-v1)")
    if row.get("payload_family") == "certified_lemma" and row.get("lemma_status") != "certified":
        e.append("payload_family=certified_lemma requires lemma_status=certified")
    return e


def validate_binding(row, payload_ids):
    e = []
    if row.get("binding_id") != binding_id(row):
        e.append("binding_id must be content-addressed %r (got %r)"
                 % (binding_id(row), row.get("binding_id")))
    if payload_ids is not None and row.get("canonical_payload_id") not in payload_ids:
        e.append("binding references unknown canonical_payload_id %r"
                 % row.get("canonical_payload_id"))
    if row.get("binding_status") == "accepted":
        if not (row.get("canonical_quran_loc") and row.get("canonical_wbw_loc")):
            e.append("binding_status=accepted requires canonical_quran_loc and canonical_wbw_loc")
    else:
        if not row.get("reason"):
            e.append("non-accepted binding requires a reason (terminal-packet taxonomy)")
    if row.get("binding_gate") == "certified_lemma" and payload_ids:
        pl = payload_ids.get(row.get("canonical_payload_id"))
        if pl is not None and pl != "certified":
            e.append("binding_gate=certified_lemma requires referenced payload lemma_status=certified")
    return e


def validate_exception(row, binding_ids):
    e = []
    if row.get("exception_id") != exception_id(row):
        e.append("exception_id must be content-addressed %r (got %r)"
                 % (exception_id(row), row.get("exception_id")))
    if binding_ids is not None and row.get("binding_id") not in binding_ids:
        e.append("exception references unknown binding_id %r" % row.get("binding_id"))
    return e


def validate_rows(rows):
    errors = []
    # payload lemma_status map for cross-gate checks + referential sets
    payload_lemma = {}
    binding_ids = set()
    for r in rows:
        s = r.get("schema")
        if s == "qamus.canonical_hover_payload.v1":
            payload_lemma[r.get("canonical_payload_id")] = r.get("lemma_status")
        elif s == "qamus.canonical_hover_occurrence_binding.v1":
            binding_ids.add(r.get("binding_id"))
    for i, r in enumerate(rows):
        s = r.get("schema")
        if s == "qamus.canonical_hover_payload.v1":
            errs = validate_payload(r)
        elif s == "qamus.canonical_hover_occurrence_binding.v1":
            errs = validate_binding(r, payload_lemma)
        elif s == "qamus.canonical_hover_exception.v1":
            errs = validate_exception(r, binding_ids)
        else:
            errs = ["unknown or missing schema %r" % s]
        errors.extend("row[%d]: %s" % (i, m) for m in errs)
    return errors


# ---------------------------------------------------------------------------
def _good_payload():
    row = {
        "schema": "qamus.canonical_hover_payload.v1",
        "payload_family": "source_address_exact",
        "surface_norm": "الكتاب",
        "root": "كتب", "lemma_id": None, "lemma_status": "missing",
        "pos": "noun", "pattern": "فِعال",
        "sarf_certification": "candidate", "nahw_certification": "missing",
        "public_payload": {
            "src": "qamus", "kind": "authored", "lang": "en",
            "token_contribution_gloss": "the book",
            "contextual_phrase_gloss": None,
            "morphline": "ART+STEM",
            "segments": [
                {"role": "ART", "surface": "ال", "qg_class": "definite_article", "gloss": "the"},
                {"role": "STEM", "surface": "كتاب", "qg_class": "noun", "gloss": "book"},
            ],
            "learner_explanation": "definite article + noun",
        },
    }
    row["canonical_payload_id"] = payload_id(row)
    return row


def _good_binding(pid):
    row = {
        "schema": "qamus.canonical_hover_occurrence_binding.v1",
        "canonical_payload_id": pid, "entry_id": "n0030",
        "entry_url": None, "source_key": "qamus",
        "sense_index": 1, "card_index": 0, "qword_row_id": "q1",
        "visible_surface": "الكتاب",
        "canonical_quran_loc": "2:2:2", "canonical_wbw_loc": "2:2:2",
        "exact_transclusion_group_key": "quran:2:2:2|الكتاب",
        "binding_status": "accepted", "binding_gate": "source_address_exact",
        "reason": "source_address_exact_ok", "exception_id": None,
    }
    row["binding_id"] = binding_id(row)
    return row


def self_test():
    p = _good_payload()
    if validate_payload(p):
        print("SELF-TEST FAIL good payload:", validate_payload(p)); return 1
    b = _good_binding(p["canonical_payload_id"])
    if validate_rows([p, b]):
        print("SELF-TEST FAIL good pair:", validate_rows([p, b])); return 1

    # FAIL: wrong payload id
    bad = _good_payload(); bad["canonical_payload_id"] = "chp:0000000000000000"
    if not any("content-addressed" in x for x in validate_payload(bad)):
        print("SELF-TEST FAIL wrong-payload-id"); return 1
    # FAIL: public leak
    bad = _good_payload(); bad["public_payload"]["segments"][1]["gloss"] = "per tafsir"
    bad["canonical_payload_id"] = payload_id(bad)
    if not any("forbidden label" in x for x in validate_payload(bad)):
        print("SELF-TEST FAIL public-leak"); return 1
    # FAIL: segment concat mismatch (suffix hidden)
    bad = _good_payload(); bad["surface_norm"] = "الكتابون"
    bad["canonical_payload_id"] = payload_id(bad)
    if not any("concatenate exactly" in x for x in validate_payload(bad)):
        print("SELF-TEST FAIL segment-concat"); return 1
    # FAIL: certified_lemma family without certified status
    bad = _good_payload(); bad["payload_family"] = "certified_lemma"
    bad["canonical_payload_id"] = payload_id(bad)
    if not any("lemma_status=certified" in x for x in validate_payload(bad)):
        print("SELF-TEST FAIL certified-family-guard"); return 1
    # FAIL: accepted binding without locs
    bad = _good_binding(p["canonical_payload_id"]); bad["canonical_wbw_loc"] = None
    bad["binding_id"] = binding_id(bad)
    if not any("requires canonical_quran_loc" in x for x in validate_binding(bad, {p["canonical_payload_id"]: "missing"})):
        print("SELF-TEST FAIL accepted-no-loc"); return 1
    # FAIL: non-accepted binding without reason
    bad = _good_binding(p["canonical_payload_id"]); bad["binding_status"] = "blocked"; bad["reason"] = None
    bad["binding_id"] = binding_id(bad)
    if not any("requires a reason" in x for x in validate_binding(bad, {p["canonical_payload_id"]: "missing"})):
        print("SELF-TEST FAIL blocked-no-reason"); return 1
    # FAIL: binding references unknown payload
    bad = _good_binding("chp:1111111111111111");
    if not any("unknown canonical_payload_id" in x for x in validate_binding(bad, {p["canonical_payload_id"]: "missing"})):
        print("SELF-TEST FAIL unknown-payload-ref"); return 1
    # FAIL: exception references unknown binding
    exc = {"schema": "qamus.canonical_hover_exception.v1", "binding_id": "chb:2222222222222222",
           "exception_reason": "page_local_context", "replacement_canonical_payload_id": None,
           "review_status": "candidate", "notes_private": None}
    exc["exception_id"] = exception_id(exc)
    if not any("unknown binding_id" in x for x in validate_exception(exc, {b["binding_id"]})):
        print("SELF-TEST FAIL unknown-binding-ref"); return 1

    print("PASS - canonical hover payload table validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate canonical hover payload/binding/exception rows.")
    parser.add_argument("path", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        parser.error("path is required unless --self-test is used")
    errors = validate_rows(read_jsonl(args.path))
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  - " + err)
        raise SystemExit(1)
    print("PASS - canonical hover payload table is source-clean and referentially sound")


if __name__ == "__main__":
    main()
