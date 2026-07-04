#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the canonical hover payload table from public hover rows (compiler Task 3).

Input: JSONL of public hover rows (the shape produced by the RH-LIVE / whitelist
projection - source_key, entry_id, loc, surface_norm, pos, root, pattern,
lemma_status, and a public_payload block). This tool GROUPS byte-identical public
payloads into ONE canonical payload identity + many occurrence bindings, so a solved
fact is transcluded, not copied per occurrence.

Rules (from the plan):
  - identical public_payload + compatible identity -> one canonical payload, N bindings;
  - same surface_norm but conflicting root/pos -> SEPARATE payloads (never merged);
  - same (loc, surface) with a richer vs weaker payload -> the richer becomes canonical,
    the weaker is emitted as a repair_candidate (never a silent overwrite);
  - a row missing a load-bearing field (e.g. parse_key/segments) -> repair_candidate
    with reason validator/schema (the builder never invents the missing field).

Bootstrap reality (2026-07-04): certified-lemma coverage is zero, so every emitted
binding is payload_family/binding_gate = source_address_exact until the certified-lemma
table produces rows. The builder DOES NOT deploy; it only writes executor packets.

Dry-run; deterministic; source-clean. See CANONICAL_HOVER_PAYLOAD_COMPILER_PLAN.
"""
import argparse
import io
import json
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.validate_canonical_hover_payload_table import (  # noqa: E402
    payload_id, binding_id, PAYLOAD_ID_FIELDS,
)

IDENTITY_FIELDS = ("surface_norm", "root", "pos", "pattern", "lemma_status")


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as h:
        for r in rows:
            h.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def _payload_from_row(row):
    pp = row.get("public_payload") or {}
    p = {
        "schema": "qamus.canonical_hover_payload.v1",
        "payload_family": "source_address_exact",
        "surface_norm": row.get("surface_norm"),
        "root": row.get("root"),
        "lemma_id": row.get("lemma_id"),
        "lemma_status": row.get("lemma_status") or "missing",
        "pos": row.get("pos"),
        "pattern": row.get("pattern"),
        "sarf_certification": row.get("sarf_certification") or "missing",
        "nahw_certification": row.get("nahw_certification") or "missing",
        "public_payload": pp,
    }
    p["canonical_payload_id"] = payload_id(p)
    return p


def _richness(row):
    pp = row.get("public_payload") or {}
    return len(pp.get("segments") or []), len(pp.get("learner_explanation") or "")


def _has_required(row):
    pp = row.get("public_payload") or {}
    if not pp.get("segments"):
        return False
    for k in ("token_contribution_gloss", "morphline", "learner_explanation"):
        if not pp.get(k):
            return False
    return True


def build(rows):
    payloads = {}      # chp id -> payload row
    bindings = []
    repair_candidates = []
    best_by_locsurface = {}   # (loc, surface_norm) -> (richness, row) to detect richer/weaker

    # first pass: pick the richest row per (loc, surface); weaker ones -> repair_candidate
    for row in rows:
        if not _has_required(row):
            repair_candidates.append({"reason": "validator/schema", "row": row})
            continue
        key = (row.get("canonical_quran_loc") or row.get("loc"), row.get("surface_norm"))
        prev = best_by_locsurface.get(key)
        if prev is None or _richness(row) > prev[0]:
            if prev is not None:
                repair_candidates.append({"reason": "richer-peer", "row": prev[1]})
            best_by_locsurface[key] = (_richness(row), row)
        else:
            repair_candidates.append({"reason": "richer-peer", "row": row})

    # second pass: emit one canonical payload per identity, bindings per occurrence
    for (loc, _surface), (_r, row) in best_by_locsurface.items():
        p = _payload_from_row(row)
        payloads.setdefault(p["canonical_payload_id"], p)
        b = {
            "schema": "qamus.canonical_hover_occurrence_binding.v1",
            "canonical_payload_id": p["canonical_payload_id"],
            "entry_id": row.get("entry_id"),
            "entry_url": row.get("entry_url"),
            "source_key": "qamus",
            "sense_index": row.get("sense_index"),
            "card_index": row.get("card_index"),
            "qword_row_id": row.get("qword_row_id"),
            "visible_surface": row.get("visible_surface") or row.get("surface_norm"),
            "canonical_quran_loc": loc,
            "canonical_wbw_loc": row.get("canonical_wbw_loc") or loc,
            "exact_transclusion_group_key": "quran:%s|%s" % (loc, row.get("surface_norm")),
            "exception_id": None,
        }
        if loc and b["canonical_wbw_loc"]:
            b["binding_status"] = "accepted"
            b["binding_gate"] = "source_address_exact"
            b["reason"] = "source_address_exact_ok"
        else:
            b["binding_status"] = "blocked"
            b["binding_gate"] = "source_address_exact"
            b["reason"] = "source-crosswalk"
        b["binding_id"] = binding_id(b)
        bindings.append(b)

    report = {
        "payloads": len(payloads),
        "bindings": len(bindings),
        "bindings_accepted": sum(1 for b in bindings if b["binding_status"] == "accepted"),
        "bindings_blocked": sum(1 for b in bindings if b["binding_status"] == "blocked"),
        "repair_candidates": len(repair_candidates),
        "by_payload_family": {"source_address_exact": len(payloads)},
    }
    return list(payloads.values()), bindings, repair_candidates, report


def self_test():
    seg2 = [{"role": "ART", "surface": "ال", "qg_class": "definite_article", "gloss": "the"},
            {"role": "STEM", "surface": "كتاب", "qg_class": "noun", "gloss": "book"}]
    pp_rich = {"src": "qamus", "kind": "authored", "lang": "en",
               "token_contribution_gloss": "the book", "contextual_phrase_gloss": None,
               "morphline": "ART+STEM", "segments": seg2, "learner_explanation": "article + noun"}
    base = {"surface_norm": "الكتاب", "root": "كتب", "pos": "noun", "pattern": "فِعال",
            "lemma_status": "missing", "entry_id": "n1", "public_payload": pp_rich}

    # two identical payloads at DIFFERENT locs -> 1 payload, 2 bindings
    r1 = dict(base, canonical_quran_loc="2:2:2")
    r2 = dict(base, canonical_quran_loc="3:7:5")
    payloads, bindings, repairs, rep = build([r1, r2])
    if not (len(payloads) == 1 and len(bindings) == 2):
        print("SELF-TEST FAIL identical-dedup:", rep); return 1

    # same surface, conflicting pos -> 2 separate payloads
    r3 = dict(base, canonical_quran_loc="4:1:1")
    r4 = dict(base, canonical_quran_loc="5:1:1", pos="verb")
    payloads, bindings, repairs, rep = build([r3, r4])
    if len(payloads) != 2:
        print("SELF-TEST FAIL conflict-separate:", rep); return 1

    # same (loc, surface) richer vs weaker -> 1 payload + 1 repair_candidate
    pp_weak = dict(pp_rich, segments=[{"role": "STEM", "surface": "الكتاب",
                   "qg_class": "noun", "gloss": "the book"}], learner_explanation="noun")
    weak = dict(base, canonical_quran_loc="2:2:2", public_payload=pp_weak)
    rich = dict(base, canonical_quran_loc="2:2:2")
    payloads, bindings, repairs, rep = build([weak, rich])
    if not (len(payloads) == 1 and rep["repair_candidates"] == 1):
        print("SELF-TEST FAIL richer-peer:", rep); return 1

    # missing segments -> repair_candidate, no payload
    bad = dict(base, canonical_quran_loc="9:9:9",
               public_payload={"src": "qamus", "kind": "authored", "lang": "en",
                               "token_contribution_gloss": "x", "morphline": "", "segments": [],
                               "learner_explanation": ""})
    payloads, bindings, repairs, rep = build([bad])
    if not (len(payloads) == 0 and rep["repair_candidates"] == 1):
        print("SELF-TEST FAIL missing-required:", rep); return 1

    # emitted rows must pass the validator
    from tools.validate_canonical_hover_payload_table import validate_rows
    payloads, bindings, repairs, rep = build([r1, r2])
    errs = validate_rows(payloads + bindings)
    if errs:
        print("SELF-TEST FAIL emitted rows invalid:", errs); return 1

    # write-out round-trip in a tempdir
    with tempfile.TemporaryDirectory() as td:
        write_jsonl(os.path.join(td, "payloads.jsonl"), payloads)
        write_jsonl(os.path.join(td, "bindings.jsonl"), bindings)
        if read_jsonl(os.path.join(td, "payloads.jsonl")) != payloads:
            print("SELF-TEST FAIL roundtrip"); return 1

    print("PASS - canonical hover payload builder self-test")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Build canonical hover payload table from public rows.")
    ap.add_argument("--input", help="JSONL of public hover rows")
    ap.add_argument("--outdir", help="output directory for payloads/bindings/exceptions + report")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not (args.input and args.outdir):
        ap.error("--input and --outdir are required unless --self-test")
    os.makedirs(args.outdir, exist_ok=True)
    payloads, bindings, repairs, report = build(read_jsonl(args.input))
    write_jsonl(os.path.join(args.outdir, "canonical_payloads.jsonl"), payloads)
    write_jsonl(os.path.join(args.outdir, "occurrence_bindings.jsonl"), bindings)
    write_jsonl(os.path.join(args.outdir, "repair_candidates.jsonl"), repairs)
    with io.open(os.path.join(args.outdir, "build_report.json"), "w", encoding="utf-8", newline="\n") as h:
        json.dump(report, h, ensure_ascii=False, sort_keys=True, indent=2)
        h.write("\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
