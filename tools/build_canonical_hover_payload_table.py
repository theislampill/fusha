#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the canonical hover payload table from public hover rows (compiler Task 3).

Input: JSONL of public hover rows (the shape produced by the RH-LIVE / whitelist
projection - source_key, entry_id, loc, surface_norm, pos, root, pattern,
lemma_status, and a public_payload block). This tool GROUPS byte-identical public
payloads into ONE canonical payload identity + many occurrence bindings, so a solved
fact is transcluded, not copied per occurrence.

Rules (from the plan):
  - identical public_payload + compatible identity -> one canonical payload, N full-carrier bindings;
  - same surface_norm but conflicting root/pos -> SEPARATE payloads (never merged);
  - same location with a richer vs weaker payload -> the richer becomes canonical,
    the weaker is emitted as a repair_candidate while its carrier still binds;
  - equal-richness conflicting content is resolved by lexicographic-min payload id and
    surfaced as tie_unresolved (never input-order dependent);
  - incomplete carrier rows fail closed as conflicts and never emit bindings.

Bootstrap reality (2026-07-04): certified-lemma coverage is zero, so every emitted
binding is payload_family/binding_gate = source_address_exact until the certified-lemma
table produces rows. The builder DOES NOT deploy; it only writes executor packets.

Dry-run; deterministic; source-clean. See CANONICAL_HOVER_PAYLOAD_COMPILER_PLAN.
"""
import argparse
import hashlib
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
        "schema": "qamus.canonical_hover_payload.v2",
        "payload_family": "source_address_exact",
        "surface_norm": row.get("surface_norm") or row.get("visible_surface_norm_strict"),
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


def _loc(row):
    return row.get("canonical_wbw_loc") or row.get("canonical_quran_loc") or row.get("loc")


def _source_dependency_sha256(row):
    supplied = row.get("source_dependency_sha256")
    if isinstance(supplied, str) and len(supplied) == 64:
        return supplied
    dependencies = row.get("source_dependencies")
    if dependencies:
        blob = json.dumps(dependencies, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    lookup_hash = row.get("resolution_wbw_lookup_sha256")
    if isinstance(lookup_hash, str) and len(lookup_hash) == 64:
        return lookup_hash
    return None


def _sort_rows(rows):
    return sorted(rows, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True,
                                                   separators=(",", ":")))


def build(rows):
    payloads = {}      # chp id -> deterministic payload row
    bindings = []
    repair_candidates = []
    conflicts = []
    rows_by_loc = {}

    # First pass: fail closed on rows that cannot form a full carrier or canonical
    # payload. Diagnostics are conflicts; repair_candidates has the deliberately
    # narrow ADR-003 vocabulary only.
    for row in rows:
        loc = _loc(row)
        missing_carrier = [field for field, value in (
            ("canonical_wbw_loc", loc),
            ("entry_id", row.get("entry_id")),
            ("card_id", row.get("card_id")),
            ("qword_row_id", row.get("qword_row_id")),
        ) if not value]
        if missing_carrier:
            conflicts.append({"reason": "carrier_incomplete_waiver",
                              "missing_fields": missing_carrier, "row": row})
            continue
        if not _has_required(row):
            conflicts.append({"reason": "validator/schema", "row": row})
            continue
        dependency_hash = _source_dependency_sha256(row)
        if dependency_hash is None:
            conflicts.append({"reason": "source_dependency_missing", "row": row})
            continue
        prepared = dict(row)
        prepared["canonical_wbw_loc"] = loc
        prepared["source_dependency_sha256"] = dependency_hash
        rows_by_loc.setdefault(loc, []).append(prepared)

    # Second pass: select one canonical content identity per location, then bind
    # every complete citation edge at that location to it.
    for loc in sorted(rows_by_loc):
        loc_rows = rows_by_loc[loc]
        payload_by_row = [(_payload_from_row(row), row) for row in loc_rows]
        max_richness = max(_richness(row) for _payload, row in payload_by_row)
        top = [(payload, row) for payload, row in payload_by_row
               if _richness(row) == max_richness]
        top_ids = sorted({payload["canonical_payload_id"] for payload, _row in top})
        selected_id = top_ids[0]
        selected_variants = [payload for payload, _row in top
                             if payload["canonical_payload_id"] == selected_id]
        selected_payload = _sort_rows(selected_variants)[0]
        previous = payloads.get(selected_id)
        payloads[selected_id] = selected_payload if previous is None else _sort_rows(
            [previous, selected_payload])[0]

        if len(top_ids) > 1:
            conflicts.append({
                "reason": "tie_unresolved",
                "canonical_wbw_loc": loc,
                "candidate_canonical_payload_ids": top_ids,
                "selected_canonical_payload_id": selected_id,
            })
        for _payload, row in payload_by_row:
            if _richness(row) < max_richness:
                repair_candidates.append({"reason": "weaker_peer", "row": row})

        for _payload, row in payload_by_row:
            surface_norm = row.get("surface_norm") or row.get("visible_surface_norm_strict")
            b = {
                "schema": "qamus.canonical_hover_occurrence_binding.v2",
                "canonical_payload_id": selected_id,
                "entry_id": row.get("entry_id"),
                "entry_url": row.get("entry_url"),
                "source_key": "qamus",
                "sense_index": row.get("sense_index"),
                "card_index": row.get("card_index"),
                "card_id": row.get("card_id"),
                "qword_row_id": row.get("qword_row_id"),
                "source_dependency_sha256": row["source_dependency_sha256"],
                "visible_surface": row.get("visible_surface") or surface_norm,
                "canonical_quran_loc": row.get("canonical_quran_loc") or loc,
                "canonical_wbw_loc": loc,
                "exact_transclusion_group_key": "quran:%s|%s" % (loc, surface_norm),
                "binding_status": "accepted",
                "binding_gate": "source_address_exact",
                "reason": "source_address_exact_ok",
                "exception_id": None,
            }
            b["binding_id"] = binding_id(b)
            bindings.append(b)

    payload_rows = sorted(payloads.values(), key=lambda row: row["canonical_payload_id"])
    bindings = sorted(bindings, key=lambda row: row["binding_id"])
    repair_candidates = _sort_rows(repair_candidates)
    conflicts = _sort_rows(conflicts)

    report = {
        "payloads": len(payload_rows),
        "bindings": len(bindings),
        "bindings_accepted": sum(1 for b in bindings if b["binding_status"] == "accepted"),
        "bindings_blocked": sum(1 for b in bindings if b["binding_status"] == "blocked"),
        "repair_candidates": len(repair_candidates),
        "conflicts": len(conflicts),
        "co_occurrence_not_bound": sum(
            1 for r in repair_candidates if r.get("reason") == "co_occurrence_not_bound"),
        "by_payload_family": {"source_address_exact": len(payload_rows)},
    }
    return payload_rows, bindings, repair_candidates, conflicts, report


def self_test():
    seg2 = [{"role": "ART", "surface": "ال", "qg_class": "definite_article", "gloss": "the"},
            {"role": "STEM", "surface": "كتاب", "qg_class": "noun", "gloss": "book"}]
    pp_rich = {"src": "qamus", "kind": "authored", "lang": "en",
               "token_contribution_gloss": "the book", "contextual_phrase_gloss": None,
               "morphline": "ART+STEM", "segments": seg2, "learner_explanation": "article + noun"}
    base = {"surface_norm": "الكتاب", "root": "كتب", "pos": "noun", "pattern": "فِعال",
            "lemma_status": "missing", "entry_id": "n1", "card_id": "n1:u1:e1",
            "source_dependency_sha256": "a" * 64, "public_payload": pp_rich}

    # two identical payloads at DIFFERENT locs -> 1 payload, 2 bindings
    r1 = dict(base, canonical_quran_loc="2:2:2", canonical_wbw_loc="2:2:2",
              qword_row_id="q1")
    r2 = dict(base, canonical_quran_loc="3:7:5", canonical_wbw_loc="3:7:5",
              qword_row_id="q2")
    payloads, bindings, repairs, conflicts, rep = build([r1, r2])
    if not (len(payloads) == 1 and len(bindings) == 2):
        print("SELF-TEST FAIL identical-dedup:", rep); return 1

    # equal-richness identical co-citations at one loc retain both carriers.
    same_loc = dict(r2, canonical_quran_loc="2:2:2", canonical_wbw_loc="2:2:2",
                    entry_id="n2", card_id="n2:u1:e1")
    payloads, bindings, repairs, conflicts, rep = build([r1, same_loc])
    if not (len(payloads) == 1 and len(bindings) == 2 and not repairs and not conflicts):
        print("SELF-TEST FAIL full-carrier-co-citation:", rep); return 1

    # same surface, conflicting pos -> 2 separate payloads
    r3 = dict(base, canonical_quran_loc="4:1:1", canonical_wbw_loc="4:1:1", qword_row_id="q3")
    r4 = dict(base, canonical_quran_loc="5:1:1", canonical_wbw_loc="5:1:1",
              qword_row_id="q4", pos="verb")
    payloads, bindings, repairs, conflicts, rep = build([r3, r4])
    if len(payloads) != 2:
        print("SELF-TEST FAIL conflict-separate:", rep); return 1

    # same (loc, surface) richer vs weaker -> 1 payload + 1 repair_candidate
    pp_weak = dict(pp_rich, segments=[{"role": "STEM", "surface": "الكتاب",
                   "qg_class": "noun", "gloss": "the book"}], learner_explanation="noun")
    weak = dict(r1, qword_row_id="qw", public_payload=pp_weak)
    rich = dict(r1, qword_row_id="qr")
    payloads, bindings, repairs, conflicts, rep = build([weak, rich])
    if not (len(payloads) == 1 and len(bindings) == 2
            and [r["reason"] for r in repairs] == ["weaker_peer"]):
        print("SELF-TEST FAIL weaker-peer:", rep); return 1

    # missing segments -> repair_candidate, no payload
    bad = dict(base, canonical_quran_loc="9:9:9", canonical_wbw_loc="9:9:9",
               qword_row_id="qbad",
               public_payload={"src": "qamus", "kind": "authored", "lang": "en",
                               "token_contribution_gloss": "x", "morphline": "", "segments": [],
                               "learner_explanation": ""})
    payloads, bindings, repairs, conflicts, rep = build([bad])
    if not (len(payloads) == 0 and not repairs and rep["conflicts"] == 1):
        print("SELF-TEST FAIL missing-required:", rep); return 1

    # null qword_row_id is a carrier-incomplete conflict, never a binding.
    waiver = dict(r1, qword_row_id=None)
    payloads, bindings, repairs, conflicts, rep = build([waiver])
    if not (not bindings and conflicts[0]["reason"] == "carrier_incomplete_waiver"):
        print("SELF-TEST FAIL carrier-incomplete-waiver:", rep); return 1

    # emitted rows must pass the validator
    from tools.validate_canonical_hover_payload_table import validate_rows
    payloads, bindings, repairs, conflicts, rep = build([r1, r2])
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
    payloads, bindings, repairs, conflicts, report = build(read_jsonl(args.input))
    write_jsonl(os.path.join(args.outdir, "canonical_payloads.jsonl"), payloads)
    write_jsonl(os.path.join(args.outdir, "occurrence_bindings.jsonl"), bindings)
    write_jsonl(os.path.join(args.outdir, "repair_candidates.jsonl"), repairs)
    write_jsonl(os.path.join(args.outdir, "build_conflicts.jsonl"), conflicts)
    with io.open(os.path.join(args.outdir, "build_report.json"), "w", encoding="utf-8", newline="\n") as h:
        json.dump(report, h, ensure_ascii=False, sort_keys=True, indent=2)
        h.write("\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
