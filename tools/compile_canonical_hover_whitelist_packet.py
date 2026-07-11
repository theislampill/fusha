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
import hashlib
import io
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.validate_canonical_hover_payload_table import (  # noqa: E402
    BINDING_SCHEMA_V2, PAYLOAD_SCHEMA_V2, validate_binding, validate_payload,
)

COMPILER_VERSION = "2.0.0"
PUBLIC_CONTENT_FIELDS = (
    "surface", "src", "kind", "lang", "public_gloss", "contextual_phrase_gloss",
    "morphline", "segments", "learner_explanation",
)
SCHEMAS_CONSUMED = (
    PAYLOAD_SCHEMA_V2, BINDING_SCHEMA_V2, "qamus.canonical_hover_exception.v2",
    "qamus.rh_live_whitelist_row.legacy-or-v1",
)
SCHEMAS_PRODUCED = ("qamus.rh_live_whitelist_row.v1", "qamus.compile_report.v2")


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


def _canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _rows_sha256(rows):
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest()


def _source_head():
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False)
    except OSError as exc:
        return "unknown+git-unavailable-%s" % exc.__class__.__name__
    value = proc.stdout.strip()
    if proc.returncode == 0 and value:
        return value
    reason = (proc.stderr.strip().splitlines() or ["not-a-git-tree"])[0]
    reason = "-".join(reason.lower().split())[:96]
    return "unknown+%s" % (reason or "not-a-git-tree")


def canonical_public_loc(row):
    """Canonical public join key: bare S:A:W. Legacy deployed rows carry the wbw: prefix
    (wbw:S:A:W) while crosswalk/compiled rows carry bare coordinates - normalize both
    (NF-T6-1: without this, the real-baseline join misses every legacy deployed row)."""
    loc = row.get("canonical_wbw_loc") or row.get("wbw_loc") or row.get("loc")
    if isinstance(loc, str) and loc.startswith("wbw:"):
        loc = loc[4:]
    return loc


def public_content(row):
    """Project compiled and legacy rows onto renderer-consumed public meaning."""
    preview = row.get("public_preview") or {}
    return {
        "surface": row.get("surface", row.get("visible_surface")),
        "src": row.get("src", preview.get("src")),
        "kind": row.get("kind", preview.get("kind")),
        "lang": row.get("lang", preview.get("lang")),
        "public_gloss": row.get(
            "public_gloss", row.get("token_contribution_gloss", row.get("gloss"))),
        "contextual_phrase_gloss": row.get(
            "contextual_phrase_gloss", row.get("contextual_gloss")),
        "morphline": row.get("morphline"),
        "segments": row.get("segments"),
        "learner_explanation": row.get(
            "learner_explanation", row.get("learner")),
    }


def public_content_bytes(row):
    return _canonical_bytes(public_content(row))


def _whitelist_row_id(canonical_wbw_loc):
    digest = hashlib.sha256(canonical_wbw_loc.encode("utf-8")).hexdigest()[:16]
    return "chw:" + digest


def _public_row(binding, payload):
    pp = payload.get("public_payload") or {}
    row = {
        "schema": "qamus.rh_live_whitelist_row.v1",
        "row_id": _whitelist_row_id(binding["canonical_wbw_loc"]),
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


def compile_packet(payloads, bindings, exceptions, baseline, source_head=None,
                   input_artifacts=None):
    by_id = {p["canonical_payload_id"]: p for p in payloads}
    invalid_payload_ids = set()
    input_conflicts = []
    for payload in payloads:
        errors = (["accepted payload schema is %s" % PAYLOAD_SCHEMA_V2]
                  if payload.get("schema") != PAYLOAD_SCHEMA_V2 else validate_payload(payload))
        if errors:
            invalid_payload_ids.add(payload.get("canonical_payload_id"))
            input_conflicts.append({"canonical_payload_id": payload.get("canonical_payload_id"),
                                    "reason": "compiler-input-validation", "errors": errors})
    exc_by_binding = {}
    for exc in exceptions:
        exc_by_binding.setdefault(exc.get("binding_id"), []).append(exc)
    for binding_exceptions in exc_by_binding.values():
        binding_exceptions.sort(key=lambda row: json.dumps(
            row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    base_by_loc = {}
    for base in baseline:
        loc = canonical_public_loc(base)
        if not loc:
            input_conflicts.append({"reason": "baseline-join-missing-loc", "row": base})
            continue
        if loc in base_by_loc:
            input_conflicts.append({"canonical_wbw_loc": loc,
                                    "reason": "baseline-join-duplicate-loc"})
            continue
        base_by_loc[loc] = base

    append_replace, no_ops, conflicts = [], [], list(input_conflicts)
    resolved_by_loc = {}
    conflicted_locs = set()
    for b in sorted(bindings, key=lambda row: row.get("binding_id") or ""):
        loc = b.get("canonical_wbw_loc")
        boundary_errors = (["accepted binding schema is %s" % BINDING_SCHEMA_V2]
                           if b.get("schema") != BINDING_SCHEMA_V2
                           else validate_binding(
                               b, {key: value.get("lemma_status") for key, value in by_id.items()}))
        if b.get("source_key") != "qamus":
            boundary_errors.append("binding source_key must be qamus")
        if b.get("canonical_payload_id") in invalid_payload_ids:
            boundary_errors.append("binding references payload rejected at compiler boundary")
        if boundary_errors:
            conflicts.append({"binding_id": b.get("binding_id"), "canonical_wbw_loc": loc,
                              "reason": "compiler-input-validation", "errors": boundary_errors})
            conflicted_locs.add(loc)
            continue
        binding_exceptions = exc_by_binding.get(b.get("binding_id"), [])
        if len(binding_exceptions) > 1:
            conflicts.append({"binding_id": b.get("binding_id"),
                              "canonical_wbw_loc": loc,
                              "reason": "multiple-exceptions"})
            conflicted_locs.add(loc)
            continue
        if b.get("binding_status") != "accepted":
            conflicts.append({"binding_id": b.get("binding_id"),
                              "canonical_wbw_loc": loc,
                              "reason": b.get("reason") or "blocked"})
            conflicted_locs.add(loc)
            continue
        pid = b["canonical_payload_id"]
        if binding_exceptions:
            exc = binding_exceptions[0]
            if exc.get("reviewed_against_canonical_payload_id") != pid:
                conflicts.append({"binding_id": b["binding_id"],
                                  "canonical_wbw_loc": loc,
                                  "reason": "exception-review-pin-mismatch"})
                conflicted_locs.add(loc)
                continue
            if exc.get("review_status") not in ("owner_accepted", "scholar_accepted"):
                conflicts.append({"binding_id": b["binding_id"],
                                  "canonical_wbw_loc": loc,
                                  "reason": "unapproved-exception:%s" % exc.get("exception_reason")})
                conflicted_locs.add(loc)
                continue
            pid = exc.get("replacement_canonical_payload_id")
            if pid is None:
                conflicts.append({"binding_id": b["binding_id"],
                                  "canonical_wbw_loc": loc,
                                  "reason": "exception-without-replacement"})
                conflicted_locs.add(loc)
                continue
        payload = by_id.get(pid)
        if payload is None:
            conflicts.append({"binding_id": b["binding_id"],
                              "canonical_wbw_loc": loc,
                              "reason": "missing-payload"})
            conflicted_locs.add(loc)
            continue
        resolved_by_loc.setdefault(loc, []).append((b, payload))

    # The executor packet is one row per canonical location. Any binding-level
    # conflict withholds that location so a co-citation cannot bypass a failed
    # exception gate.
    for loc in sorted(resolved_by_loc, key=lambda value: value or ""):
        if loc in conflicted_locs:
            continue
        resolved = resolved_by_loc[loc]
        payload_ids = sorted({payload["canonical_payload_id"] for _binding, payload in resolved})
        if len(payload_ids) != 1:
            conflicts.append({"canonical_wbw_loc": loc,
                              "binding_ids": sorted(b["binding_id"] for b, _p in resolved),
                              "reason": "payload-collision-at-loc"})
            continue
        b, payload = min(resolved, key=lambda pair: pair[0]["binding_id"])
        row = _public_row(b, payload)
        prev = base_by_loc.get(loc)
        if prev is not None and public_content_bytes(prev) == public_content_bytes(row):
            no_ops.append(row["row_id"])
        else:
            if prev is not None:
                row["prior_payload_hash"] = hashlib.sha256(public_content_bytes(prev)).hexdigest()
                row["expected_movement"] = "replace"
            else:
                row["expected_movement"] = "append"
            append_replace.append(row)

    append_replace.sort(key=lambda row: row["row_id"])
    no_ops.sort()
    conflicts.sort(key=lambda row: json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    packet_body = {"append_replace": append_replace, "no_ops": no_ops, "conflicts": conflicts}
    if input_artifacts is None:
        input_artifacts = [
            {"identity": "canonical_payloads", "path": None, "sha256": _rows_sha256(payloads)},
            {"identity": "occurrence_bindings", "path": None, "sha256": _rows_sha256(bindings)},
            {"identity": "exceptions", "path": None, "sha256": _rows_sha256(exceptions)},
            {"identity": "deployed_baseline", "path": None, "sha256": _rows_sha256(baseline)},
        ]
    report = {
        "source_head": source_head if source_head is not None else _source_head(),
        "input_artifacts": input_artifacts,
        "schemas_consumed": list(SCHEMAS_CONSUMED),
        "schemas_produced": list(SCHEMAS_PRODUCED),
        "compiler_version": COMPILER_VERSION,
        "packet_sha256": hashlib.sha256(_canonical_bytes(packet_body)).hexdigest(),
        "append_replace": len(append_replace),
        "no_ops": len(no_ops),
        "conflicts": len(conflicts),
        "input_payloads": len(payloads),
        "input_bindings": len(bindings),
        "whitelist_locations": len(append_replace) + len(no_ops),
        "row_denominators": {
            "input_payloads": len(payloads), "input_bindings": len(bindings),
            "input_exceptions": len(exceptions), "baseline_locations": len(base_by_loc),
            "modeled_locations": len(append_replace) + len(no_ops),
        },
        "conflict_denominators": {
            "conflicts": len(conflicts), "input_bindings": len(bindings),
            "modeled_locations": len(append_replace) + len(no_ops) + len(conflicted_locs),
        },
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
    dependency = [{"id": "self-test-index", "sha256": "a" * 64}]
    dependency_sha = hashlib.sha256(_canonical_bytes(dependency)).hexdigest()
    base = {"schema": "qamus.canonical_hover_compiler_input.v1",
            "source_key": "qamus", "source_row_id": "compiler-self-test",
            "source_artifact_sha256": "a" * 64, "source_dependencies": dependency,
            "surface_norm": "الكتاب", "root": "كتب", "pos": "noun", "pattern": "فِعال",
            "lemma_status": "missing", "entry_id": "n1", "card_id": "n1:u1:e1",
            "source_dependency_sha256": dependency_sha, "public_payload": pp,
            "visible_surface": "الكتاب"}
    rows = [dict(base, canonical_quran_loc="2:2:2", canonical_wbw_loc="2:2:2", qword_row_id="q1"),
            dict(base, canonical_quran_loc="3:7:5", canonical_wbw_loc="3:7:5", qword_row_id="q2")]
    payloads, bindings, repairs, conflicts, _ = build(rows)

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

    # A real deployed-shape row has no row_id or canonical lineage ids. Public
    # meaning still joins by canonical loc and classifies no-op.
    binding_loc = bindings[0]["canonical_wbw_loc"]
    compiled_at_binding = next(row for row in baseline
                               if row["canonical_wbw_loc"] == binding_loc)
    legacy = dict(public_content(compiled_at_binding), loc=binding_loc)
    ar_legacy, no_legacy, conf_legacy, rep_legacy = compile_packet(
        payloads, [bindings[0]], [], [legacy])
    if not (not ar_legacy and len(no_legacy) == 1 and not conf_legacy):
        print("SELF-TEST FAIL legacy-public-no-op:", rep_legacy); return 1

    # a blocked binding -> conflict
    blocked = dict(bindings[0]); blocked["binding_status"] = "blocked"; blocked["reason"] = "source-crosswalk"
    ar3, no3, conf3, rep3 = compile_packet(payloads, [blocked], [], [])
    if rep3["conflicts"] != 1:
        print("SELF-TEST FAIL blocked-conflict:", rep3); return 1

    # an unreviewed exception -> conflict naming the reason
    exc = {"schema": "qamus.canonical_hover_exception.v2", "exception_id": "che:0000000000000000",
           "binding_id": bindings[0]["binding_id"], "exception_reason": "page_local_context",
           "replacement_canonical_payload_id": None,
           "reviewed_against_canonical_payload_id": bindings[0]["canonical_payload_id"],
           "review_status": "candidate", "notes_private": None}
    ar4, no4, conf4, rep4 = compile_packet(payloads, [bindings[0]], [exc], [])
    if not (rep4["conflicts"] == 1 and "exception" in conf4[0]["reason"]):
        print("SELF-TEST FAIL exception-conflict:", rep4); return 1

    # LAT-05: accepted exception without replacement never falls back to original.
    accepted_null = dict(exc, review_status="owner_accepted")
    ar5, no5, conf5, rep5 = compile_packet(payloads, [bindings[0]], [accepted_null], [])
    if not (not ar5 and conf5[0]["reason"] == "exception-without-replacement"):
        print("SELF-TEST FAIL exception-without-replacement:", rep5); return 1

    # More than one exception for a binding is order-independent and emits nothing.
    exc2 = dict(exc, exception_id="che:1111111111111111", exception_reason="owner_style_override")
    a = compile_packet(payloads, [bindings[0]], [exc, exc2], [])
    z = compile_packet(payloads, [bindings[0]], [exc2, exc], [])
    if not (not a[0] and a[2] == z[2] and a[2][0]["reason"] == "multiple-exceptions"):
        print("SELF-TEST FAIL multiple-exceptions-order:", a[3]); return 1

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
    payloads = read_jsonl(args.payloads)
    bindings = read_jsonl(args.bindings)
    exceptions = read_jsonl(args.exceptions)
    baseline = read_jsonl(args.baseline)

    def artifact_record(identity, path, rows):
        if path and os.path.exists(path):
            with io.open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
        else:
            digest = _rows_sha256(rows)
        return {"identity": identity, "path": path, "sha256": digest}

    input_artifacts = [
        artifact_record("canonical_payloads", args.payloads, payloads),
        artifact_record("occurrence_bindings", args.bindings, bindings),
        artifact_record("exceptions", args.exceptions, exceptions),
        artifact_record("deployed_baseline", args.baseline, baseline),
    ]
    ar, no, conf, report = compile_packet(
        payloads, bindings, exceptions, baseline, input_artifacts=input_artifacts)
    full_packet, _full_noops, _full_conflicts, _full_report = compile_packet(
        payloads, bindings, exceptions, [], source_head=report["source_head"])
    os.makedirs(args.outdir, exist_ok=True)
    write_jsonl(os.path.join(args.outdir, "whitelist_packet.jsonl"), full_packet)
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
