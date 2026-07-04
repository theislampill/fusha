#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile accepted bindings back into a public RH-LIVE whitelist packet (compiler Task 4).

Input: canonical payload table + occurrence bindings + exceptions + (optional) the
current whitelist baseline. Output: an executor PACKET, never a live deploy:
  - append/replace rows (accepted bindings rendered as public whitelist rows);
  - a no-op set (rows already byte-identical to the baseline);
  - a conflict set (rows blocked / needing owner/scholar/source/validator action);
  - a compile report (counts).

Invariants: public rows stay src=qamus, kind=authored, lang=en; a replacement row
carries prior_payload_hash + expected movement; an exception row names its reason;
the compiler MUST NOT deploy - the Qamus executor deploys the packet through its own
serial live gate (Task 6). Dry-run; deterministic; source-clean.
See CANONICAL_HOVER_PAYLOAD_COMPILER_PLAN.
"""
import argparse
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


def read_jsonl(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
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


def _public_row(binding, payload):
    pp = payload.get("public_payload") or {}
    row = {
        "schema": "qamus.rh_live_whitelist_row.v1",
        "row_id": binding["binding_id"],
        "entry_id": binding.get("entry_id"),
        "canonical_quran_loc": binding.get("canonical_quran_loc"),
        "canonical_wbw_loc": binding.get("canonical_wbw_loc"),
        "surface": binding.get("visible_surface"),
        "src": "qamus", "kind": "authored", "lang": "en",
        "public_gloss": pp.get("token_contribution_gloss"),
        "contextual_phrase_gloss": pp.get("contextual_phrase_gloss"),
        "morphline": pp.get("morphline"),
        "segments": pp.get("segments"),
        "learner_explanation": pp.get("learner_explanation"),
        "canonical_payload_id": payload["canonical_payload_id"],
    }
    return row


def compile_packet(payloads, bindings, exceptions, baseline):
    by_id = {p["canonical_payload_id"]: p for p in payloads}
    exc_by_binding = {e["binding_id"]: e for e in exceptions}
    base_by_rowid = {b.get("row_id"): b for b in baseline}

    append_replace, no_ops, conflicts = [], [], []
    for b in bindings:
        exc = exc_by_binding.get(b["binding_id"])
        if b.get("binding_status") != "accepted":
            conflicts.append({"binding_id": b["binding_id"], "reason": b.get("reason") or "blocked"})
            continue
        pid = b["canonical_payload_id"]
        if exc:
            pid = exc.get("replacement_canonical_payload_id") or pid
            if exc.get("review_status") not in ("owner_accepted", "scholar_accepted"):
                conflicts.append({"binding_id": b["binding_id"],
                                  "reason": "exception:%s" % exc.get("exception_reason")})
                continue
        payload = by_id.get(pid)
        if payload is None:
            conflicts.append({"binding_id": b["binding_id"], "reason": "missing-payload"})
            continue
        row = _public_row(b, payload)
        prev = base_by_rowid.get(row["row_id"])
        if prev == row:
            no_ops.append(row["row_id"])
        else:
            if prev is not None:
                row["prior_payload_hash"] = prev.get("canonical_payload_id")
                row["expected_movement"] = "replace"
            else:
                row["expected_movement"] = "append"
            append_replace.append(row)

    report = {
        "append_replace": len(append_replace),
        "no_ops": len(no_ops),
        "conflicts": len(conflicts),
        "input_payloads": len(payloads),
        "input_bindings": len(bindings),
    }
    return append_replace, no_ops, conflicts, report


def self_test():
    from tools.build_canonical_hover_payload_table import build
    from tools.validate_public_private_boundary import FORBIDDEN_LABELS
    seg = [{"role": "ART", "surface": "ال", "qg_class": "definite_article", "gloss": "the"},
           {"role": "STEM", "surface": "كتاب", "qg_class": "noun", "gloss": "book"}]
    pp = {"src": "qamus", "kind": "authored", "lang": "en",
          "token_contribution_gloss": "the book", "contextual_phrase_gloss": None,
          "morphline": "ART+STEM", "segments": seg, "learner_explanation": "article + noun"}
    base = {"surface_norm": "الكتاب", "root": "كتب", "pos": "noun", "pattern": "فِعال",
            "lemma_status": "missing", "entry_id": "n1", "public_payload": pp,
            "visible_surface": "الكتاب"}
    rows = [dict(base, canonical_quran_loc="2:2:2"), dict(base, canonical_quran_loc="3:7:5")]
    payloads, bindings, repairs, _ = build(rows)

    # first compile: no baseline -> 2 appends, 0 no-op, 0 conflict
    ar, no, conf, rep = compile_packet(payloads, bindings, [], [])
    if not (rep["append_replace"] == 2 and rep["no_ops"] == 0 and rep["conflicts"] == 0):
        print("SELF-TEST FAIL first-compile:", rep); return 1
    # public rows are source-clean
    for r in ar:
        if (r["src"], r["kind"], r["lang"]) != ("qamus", "authored", "en"):
            print("SELF-TEST FAIL public-fields"); return 1
        blob = json.dumps(r, ensure_ascii=False).lower()
        if any(lbl in blob for lbl in FORBIDDEN_LABELS):
            print("SELF-TEST FAIL public leak"); return 1

    # recompile with the just-produced rows as baseline -> all no-ops
    baseline = [dict(r) for r in ar]
    for r in baseline:
        r.pop("expected_movement", None)
    ar2, no2, conf2, rep2 = compile_packet(payloads, bindings, [], baseline)
    if not (rep2["no_ops"] == 2 and rep2["append_replace"] == 0):
        print("SELF-TEST FAIL no-op recompile:", rep2); return 1

    # a blocked binding -> conflict
    blocked = dict(bindings[0]); blocked["binding_status"] = "blocked"; blocked["reason"] = "source-crosswalk"
    ar3, no3, conf3, rep3 = compile_packet(payloads, [blocked], [], [])
    if rep3["conflicts"] != 1:
        print("SELF-TEST FAIL blocked-conflict:", rep3); return 1

    # an unreviewed exception -> conflict naming the reason
    exc = {"schema": "qamus.canonical_hover_exception.v1", "exception_id": "che:0000000000000000",
           "binding_id": bindings[0]["binding_id"], "exception_reason": "page_local_context",
           "replacement_canonical_payload_id": None, "review_status": "candidate", "notes_private": None}
    ar4, no4, conf4, rep4 = compile_packet(payloads, [bindings[0]], [exc], [])
    if not (rep4["conflicts"] == 1 and "exception" in conf4[0]["reason"]):
        print("SELF-TEST FAIL exception-conflict:", rep4); return 1

    print("PASS - canonical hover whitelist compiler self-test")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Compile accepted bindings into a public whitelist packet.")
    ap.add_argument("--payloads")
    ap.add_argument("--bindings")
    ap.add_argument("--exceptions")
    ap.add_argument("--baseline")
    ap.add_argument("--outdir")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not (args.payloads and args.bindings and args.outdir):
        ap.error("--payloads, --bindings, --outdir required unless --self-test")
    ar, no, conf, report = compile_packet(
        read_jsonl(args.payloads), read_jsonl(args.bindings),
        read_jsonl(args.exceptions), read_jsonl(args.baseline))
    os.makedirs(args.outdir, exist_ok=True)
    write_jsonl(os.path.join(args.outdir, "whitelist_append_replace.jsonl"), ar)
    write_jsonl(os.path.join(args.outdir, "whitelist_conflicts.jsonl"), conf)
    with io.open(os.path.join(args.outdir, "whitelist_noops.json"), "w", encoding="utf-8", newline="\n") as h:
        json.dump(no, h, ensure_ascii=False, indent=2); h.write("\n")
    with io.open(os.path.join(args.outdir, "compile_report.json"), "w", encoding="utf-8", newline="\n") as h:
        json.dump(report, h, ensure_ascii=False, sort_keys=True, indent=2); h.write("\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("NOTE: packet only - the Qamus executor deploys it through its serial live gate (Task 6).")


if __name__ == "__main__":
    main()
