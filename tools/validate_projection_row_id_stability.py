#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate public-hover projection row_id STABILITY (FUSHA plan P1-B).

Projection rows already carry a row_id (public-hover-projection.schema.json). This
gate makes that id STABLE and content-addressed, so a row's identity survives a
rebuild and never drifts because a timestamp or a provenance breadcrumb changed.

Enforced:
  - row_id is content-addressed: 'proj:' + sha256[:16] over the IDENTITY fields
    (entry_id, card_id, surface, canonical_quran_loc, canonical_wbw_loc, public_gloss)
    - never over src/kind/lang provenance, timestamps, or private trace;
  - two rows with different identity get different ids (no collision);
  - same identity -> same id (stability / idempotent rebuild);
  - public fields stay source-clean (reuses the canonical FORBIDDEN_LABELS);
  - src/kind/lang, when present, are qamus/authored/en.

Additive; dry-run; deterministic; source-clean. Touches no existing data - it is a
contract the projection BUILDER's output is validated against. No live Qamus is read.
See FUSHA_TRANSCLUSION_P0_P1_P2_PLAN P1-B (fablehardening).
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
sys.path.insert(0, ROOT)
from tools.validate_public_private_boundary import FORBIDDEN_LABELS  # noqa: E402

IDENTITY_FIELDS = ("entry_id", "card_id", "surface",
                   "canonical_quran_loc", "canonical_wbw_loc", "public_gloss")
REQUIRED = ("row_id",) + IDENTITY_FIELDS


def projection_id(row):
    canonical = json.dumps({k: row.get(k) for k in IDENTITY_FIELDS},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "proj:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_row(row):
    e = []
    if not isinstance(row, dict):
        return ["projection row must be a JSON object"]
    for f in REQUIRED:
        if f not in row:
            e.append("missing required field %r" % f)
    if e:
        return e
    expected = projection_id(row)
    if row.get("row_id") != expected:
        e.append("row_id must be content-addressed %r (got %r) - unstable/provenance-derived id"
                 % (expected, row.get("row_id")))
    for k, v in (("src", "qamus"), ("kind", "authored"), ("lang", "en")):
        if k in row and row.get(k) != v:
            e.append("%s must be %r when present" % (k, v))
    blob = json.dumps(row, ensure_ascii=False).lower()
    for label in FORBIDDEN_LABELS:
        if label in blob:
            e.append("projection row leaks forbidden label %r" % label)
    return e


def validate_rows(rows):
    errors = []
    identity = {}
    for i, row in enumerate(rows):
        for m in validate_row(row):
            errors.append("row[%d]: %s" % (i, m))
        rid = row.get("row_id")
        sig = tuple(row.get(k) for k in IDENTITY_FIELDS)
        if rid in identity and identity[rid] != sig:
            errors.append("row[%d]: row_id %r collides on two identities" % (i, rid))
        else:
            identity[rid] = sig
    return errors


def _good():
    r = {"schema": "qamus.public_hover_projection.v1", "entry_id": "n0030", "card_id": 0,
         "surface": "الكتاب", "canonical_quran_loc": "2:2:2", "canonical_wbw_loc": "2:2:2",
         "src": "qamus", "kind": "authored", "lang": "en", "public_gloss": "the book"}
    r["row_id"] = projection_id(r)
    return r


def self_test():
    g = _good()
    if validate_row(g):
        print("SELF-TEST FAIL good:", validate_row(g)); return 1
    # stability: recompute is identical
    if projection_id(g) != g["row_id"]:
        print("SELF-TEST FAIL stability"); return 1
    # changing a NON-identity field (provenance) must NOT change the id
    g2 = dict(g); g2["generated_at"] = "2026-07-04T00:00:00Z"
    if projection_id(g2) != g["row_id"]:
        print("SELF-TEST FAIL non-identity field changed id"); return 1
    # FAIL: wrong / provenance-derived id
    bad = dict(g); bad["row_id"] = "proj:0000000000000000"
    if not any("content-addressed" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL wrong-id not caught"); return 1
    # FAIL: id built including a timestamp (drifts) -> mismatch caught
    bad = dict(g)
    bad["row_id"] = "proj:" + hashlib.sha256(b"n0030|2026-07-04T00:00:00Z").hexdigest()[:16]
    if not any("content-addressed" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL timestamp-derived id not caught"); return 1
    # FAIL: public leak
    bad = _good(); bad["public_gloss"] = "per tafsir"; bad["row_id"] = projection_id(bad)
    if not any("forbidden label" in x for x in validate_row(bad)):
        print("SELF-TEST FAIL leak not caught"); return 1
    # different identity -> different id; no collision
    other = dict(g, canonical_quran_loc="3:7:5"); other["row_id"] = projection_id(other)
    if g["row_id"] == other["row_id"]:
        print("SELF-TEST FAIL distinct identities share id"); return 1
    if validate_rows([g, other]):
        print("SELF-TEST FAIL distinct pair rejected:", validate_rows([g, other])); return 1
    # forced collision -> caught
    coll = dict(other); coll["row_id"] = g["row_id"]
    if not any("collides" in x for x in validate_rows([g, coll])):
        print("SELF-TEST FAIL collision not caught"); return 1
    print("PASS - projection row_id stability validator self-test")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Validate public-hover projection row_id stability.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        ap.error("path is required unless --self-test")
    errors = validate_rows(read_jsonl(args.path))
    if errors:
        print("FAIL:")
        for e in errors[:80]:
            print("  - " + e)
        raise SystemExit(1)
    print("PASS - projection row_ids are stable, content-addressed, and source-clean")


if __name__ == "__main__":
    main()
