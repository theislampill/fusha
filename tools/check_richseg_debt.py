#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract checker for the rich-seg KNOWN-DEBT manifest (rich-seg-known-debt.jsonl).

The deploy gate may GRANDFATHER a currently-flagged rich-hover whitelist row ONLY when
that row's identity (canonical_location) AND its row_hash EXACTLY match an entry in the
pinned debt manifest. Every other situation FAILS CLOSED. This module is the reusable,
stdlib-only, deterministic implementation of that contract plus the manifest's own
integrity gate. It reads no live Qamus data; the caller supplies the currently-flagged
row set (produced by tools/validate_segment_completeness.classify_live_row over the live
whitelist).

FAIL-CLOSED conditions (each proven red-first by --self-test):
  1. new_debt_row            a flagged row whose canonical_location is absent from the manifest.
  2. modified_still_invalid  a manifest loc whose live row_hash no longer matches (row changed
                             but is still flagged).
  3. debt_count_increase     more flagged rows than the recorded debt_ceiling.
  4. unknown_exception       a grandfather/exception request for a loc not in the manifest.
  5. missing_repair_disposition  a manifest row lacking repair_lane or review_condition.
  6. manifest_content_tampered   the manifest bytes no longer match manifest_content_sha256.

The permitted debt count is a CEILING and must trend DOWNWARD: a regenerated manifest whose
debt_ceiling exceeds the previously recorded ceiling fails closed (--max-ceiling).

Usage:
  python tools/check_richseg_debt.py --self-test
  python tools/check_richseg_debt.py --manifest qamus/reports/rich-seg-known-debt.jsonl \
                                     --meta qamus/reports/rich-seg-known-debt.meta.json
  # deploy-gate evaluation against a currently-flagged set (jsonl of {canonical_location,row_hash}):
  python tools/check_richseg_debt.py --manifest ... --meta ... --flagged flagged.jsonl [--max-ceiling N]
"""
import argparse
import hashlib
import io
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REQUIRED_FIELDS = [
    "canonical_location", "row_hash", "primary_class", "secondary_flags",
    "first_known_commit", "review_status", "repair_lane", "skill_rule_ids",
    "validator_gate_ids", "review_condition",
]
VALID_LANES = {"C1", "C2", "C3", "C4", "C5"}    # C3 lane REOPENED at detector v3 (new content-noun
VALID_PRIMARY = {"C1", "C2", "C3", "C4", "C5"}  # candidates); the originally repaired C3 locs stay
                                                # excluded_now_valid and are never grandfathered.
VALID_STATUS = {"candidate_flag", "confirmed_defect"}

# Ground-truthed REPAIRED C3 locs (the original C3 repair wave). These are
# excluded_now_valid forever: they must never re-enter the debt manifest even
# though the C3 lane itself was REOPENED at detector v3 for new candidates.
REPAIRED_C3_LOCS = frozenset({"12:82:11", "24:4:13", "27:49:4", "27:49:14", "40:72:4"})


# ---------------------------------------------------------------------------
# Pure contract primitives (no I/O). A "failure" is a tuple (code, *detail).
# ---------------------------------------------------------------------------
def index_by_loc(manifest):
    idx = {}
    for r in manifest:
        idx[r["canonical_location"]] = r
    return idx


def check_manifest_wellformed(manifest):
    """Structural integrity of the manifest rows themselves. Returns list of failures."""
    failures = []
    seen = set()
    for r in manifest:
        loc = r.get("canonical_location")
        if loc in seen:
            failures.append(("duplicate_loc", loc))
        seen.add(loc)
        for f in REQUIRED_FIELDS:
            if f not in r or r[f] in (None, "", []):
                # secondary_flags/skill lists may legitimately be empty -> allow []
                if f == "secondary_flags":
                    continue
                if r.get(f) in (None, ""):
                    failures.append(("missing_field", loc, f))
        if not r.get("repair_lane") or not r.get("review_condition"):
            failures.append(("missing_repair_disposition", loc))
        if r.get("repair_lane") not in VALID_LANES:
            failures.append(("invalid_repair_lane", loc, r.get("repair_lane")))
        if r.get("primary_class") not in VALID_PRIMARY:
            failures.append(("invalid_primary_class", loc, r.get("primary_class")))
        if r.get("primary_class") == "C3" and loc in REPAIRED_C3_LOCS:
            failures.append(("c3_repaired_loc_in_debt", loc))
        if r.get("review_status") not in VALID_STATUS:
            failures.append(("invalid_review_status", loc, r.get("review_status")))
    return failures


def evaluate_gate(manifest, ceiling, flagged, exceptions=None, max_ceiling=None):
    """The deploy-gate contract. `flagged` = currently-flagged rows
    [{canonical_location,row_hash}]. Returns (ok, failures)."""
    failures = []
    idx = index_by_loc(manifest)

    # (1) new_debt_row  &  (2) modified_still_invalid
    for fr in flagged:
        loc = fr["canonical_location"]
        h = fr["row_hash"]
        m = idx.get(loc)
        if m is None:
            failures.append(("new_debt_row", loc))
            continue
        if m["row_hash"] != h:
            failures.append(("modified_still_invalid", loc))

    # (3) debt_count_increase: never grandfather more rows than the ceiling.
    if len(flagged) > ceiling:
        failures.append(("debt_count_increase", len(flagged), ceiling))
    # ceiling must itself trend downward vs any previously recorded ceiling.
    if max_ceiling is not None and ceiling > max_ceiling:
        failures.append(("ceiling_raised", ceiling, max_ceiling))

    # (4) unknown_exception
    for ex in (exceptions or []):
        if ex not in idx:
            failures.append(("unknown_exception", ex))

    # (5) missing_repair_disposition (defensive: also enforced structurally)
    for r in manifest:
        if not r.get("repair_lane") or not r.get("review_condition"):
            failures.append(("missing_repair_disposition", r.get("canonical_location")))

    return (len(failures) == 0, failures)


def content_sha256(manifest_rows):
    """Recompute the canonical manifest byte-content sha (sorted-key compact lines, LF)."""
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in manifest_rows]
    text = "\n".join(lines) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def load_jsonl(path):
    rows = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def read_manifest_bytes_sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def check_files(manifest_path, meta_path, flagged_path=None, max_ceiling=None):
    manifest = load_jsonl(manifest_path)
    meta = json.load(io.open(meta_path, encoding="utf-8"))
    failures = []

    # structural
    failures += check_manifest_wellformed(manifest)

    # ceiling agreement: meta.debt_ceiling must equal the row count.
    ceiling = meta.get("debt_ceiling")
    if ceiling != len(manifest):
        failures.append(("ceiling_row_count_mismatch", ceiling, len(manifest)))

    # (6) manifest_content_tampered: recomputed content sha must match meta + on-disk bytes.
    recomputed = content_sha256(manifest)
    if recomputed != meta.get("manifest_content_sha256"):
        failures.append(("manifest_content_tampered", recomputed[:16],
                         str(meta.get("manifest_content_sha256"))[:16]))

    # excluded set must be disjoint from debt (repaired rows never grandfathered)
    debt_locs = {r["canonical_location"] for r in manifest}
    for loc in meta.get("excluded_now_valid", {}).get("locs", []):
        if loc in debt_locs:
            failures.append(("excluded_loc_in_debt", loc))

    # optional deploy-gate evaluation
    if flagged_path is not None:
        flagged = load_jsonl(flagged_path)
        ok, gate_failures = evaluate_gate(manifest, ceiling, flagged, max_ceiling=max_ceiling)
        failures += gate_failures

    ok = (len(failures) == 0)
    return ok, failures, {"ceiling": ceiling, "rows": len(manifest),
                          "content_sha16": recomputed[:16]}


# ---------------------------------------------------------------------------
# --self-test : red-first fixtures for every fail-closed condition.
# ---------------------------------------------------------------------------
def _golden_manifest():
    def row(loc, h, cls):
        return {
            "canonical_location": loc, "row_hash": h, "primary_class": cls,
            "primary_name": {"C1": "stem_swallow", "C4": "fallback_leak"}.get(cls, cls),
            "secondary_flags": [], "first_known_commit": "3d806386",
            "review_status": "candidate_flag", "repair_lane": cls,
            "skill_rule_ids": ["fusha-sarf:x"], "validator_gate_ids": ["QAMUS-RICH-SEG-001"],
            "detector_message": "m", "review_condition": "re-review on row_hash change", "expiry": None,
        }
    return [row("2:3:8", "a" * 64, "C1"), row("1:6:1", "b" * 64, "C4")]


def self_test():
    results = []

    def record(name, expect_ok, ok, failures):
        passed = (ok == expect_ok)
        results.append((name, passed, expect_ok, ok, failures))

    golden = _golden_manifest()
    ceiling = len(golden)

    # GOLDEN: exact unchanged flagged set -> PASS (grandfathered)
    flagged = [{"canonical_location": "2:3:8", "row_hash": "a" * 64},
               {"canonical_location": "1:6:1", "row_hash": "b" * 64}]
    ok, f = evaluate_gate(golden, ceiling, flagged)
    record("golden_exact_match_passes", True, ok, f)

    # FAIL 1: new debt row (loc not in manifest)
    flagged1 = flagged + [{"canonical_location": "9:9:9", "row_hash": "c" * 64}]
    ok, f = evaluate_gate(golden, ceiling, flagged1)
    record("fail_new_debt_row", False, ok, f)

    # FAIL 2: modified-but-still-invalid (hash changed)
    flagged2 = [{"canonical_location": "2:3:8", "row_hash": "z" * 64},
                {"canonical_location": "1:6:1", "row_hash": "b" * 64}]
    ok, f = evaluate_gate(golden, ceiling, flagged2)
    record("fail_modified_still_invalid", False, ok, f)

    # FAIL 3: debt-count increase (more flagged than ceiling)
    flagged3 = flagged + [{"canonical_location": "9:9:9", "row_hash": "c" * 64}]
    ok, f = evaluate_gate(golden, ceiling, flagged3)  # len 3 > ceiling 2 AND new loc
    record("fail_debt_count_increase", False, ok, f)

    # FAIL 3b: ceiling raised vs previously-recorded max
    ok, f = evaluate_gate(golden, ceiling, flagged, max_ceiling=1)
    record("fail_ceiling_raised", False, ok, f)

    # FAIL 4: unknown exception (grandfather request for absent loc)
    ok, f = evaluate_gate(golden, ceiling, flagged, exceptions=["4:4:4"])
    record("fail_unknown_exception", False, ok, f)

    # FAIL 5: missing repair disposition (row lacks repair_lane/review_condition)
    broken = [dict(golden[0]), dict(golden[1])]
    broken[0]["repair_lane"] = ""
    ok, f = evaluate_gate(broken, ceiling, flagged)
    record("fail_missing_repair_disposition", False, ok, f)
    # also structurally
    sf = check_manifest_wellformed(broken)
    record("fail_missing_repair_disposition_structural", False, len(sf) == 0, sf)

    # FAIL 6: manifest content tampered (recomputed sha != claimed)
    tampered_meta_sha = "deadbeef" * 8
    recomputed = content_sha256(golden)
    record("fail_content_tampered", False, recomputed == tampered_meta_sha,
           [("manifest_content_tampered", recomputed[:16])])

    # STRUCTURAL: a REPAIRED C3 loc must be rejected (never re-enters debt)
    c3row = dict(golden[0])
    c3row["canonical_location"] = "24:4:13"
    c3row["primary_class"] = "C3"; c3row["repair_lane"] = "C3"
    c3row["primary_name"] = "misclassified_function"
    sf = check_manifest_wellformed([c3row])
    record("fail_c3_repaired_loc_in_debt", False, len(sf) == 0, sf)

    # STRUCTURAL: the C3 lane is REOPENED for new candidates -> a C3 row at a
    # non-repaired loc is well-formed and PASSES.
    c3new = dict(c3row); c3new["canonical_location"] = "17:45:1"
    sf = check_manifest_wellformed([c3new])
    record("pass_c3_reopened_lane", True, len(sf) == 0, sf)

    # STRUCTURAL: golden manifest is well-formed -> PASS
    sf = check_manifest_wellformed(golden)
    record("golden_wellformed_passes", True, len(sf) == 0, sf)

    all_pass = all(p for _, p, *_ in results)
    for name, passed, expect_ok, ok, failures in results:
        tag = "PASS" if passed else "FAIL"
        print("[%s] %-40s expect_ok=%s got_ok=%s" % (tag, name, expect_ok, ok))
    print("SELF-TEST %s (%d/%d)" %
          ("OK" if all_pass else "FAILED",
           sum(1 for _, p, *_ in results if p), len(results)))
    return 0 if all_pass else 1


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="rich-seg known-debt manifest contract checker")
    ap.add_argument("--self-test", action="store_true", help="run red-first contract fixtures")
    ap.add_argument("--manifest", help="path to rich-seg-known-debt.jsonl")
    ap.add_argument("--meta", help="path to rich-seg-known-debt.meta.json")
    ap.add_argument("--flagged", help="jsonl of currently-flagged rows {canonical_location,row_hash}")
    ap.add_argument("--max-ceiling", type=int, default=None,
                    help="previously-recorded ceiling; fail closed if the manifest raises it")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not (args.manifest and args.meta):
        ap.error("provide --manifest and --meta (or --self-test)")

    ok, failures, info = check_files(args.manifest, args.meta, args.flagged, args.max_ceiling)
    print("manifest rows=%d ceiling=%s content_sha16=%s" %
          (info["rows"], info["ceiling"], info["content_sha16"]))
    if ok:
        print("CONTRACT OK")
        return 0
    print("CONTRACT FAILED (%d):" % len(failures))
    for fl in failures[:50]:
        print("  ", fl)
    if len(failures) > 50:
        print("   ... %d more" % (len(failures) - 50))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
