#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builder for the rich-seg KNOWN-DEBT manifest (rich-seg-known-debt.jsonl + .meta.json).

Regenerates the pinned debt manifest by running the AUTHORITATIVE classifier
(tools/validate_segment_completeness.classify_live_row, C1..C5) over the live
rich-hover whitelist. Deterministic, stdlib-only, no live Qamus writes.

Provenance rules (per-manifest-version monotonic contract):
* Every currently-flagged whitelist row becomes one manifest row keyed by
  (canonical_location, row_hash); row_hash = sha256 of the row's RAW whitelist
  line (stripped), byte-identical to what the deploy gate reads — this matches
  the audit@2 / manifest-v1 hash convention exactly.
* first_known_commit is CARRIED from the previous manifest when the same
  canonical_location is already known (debt is not re-dated by regeneration);
  rows newly detected by a recall-corrected classifier get the classifier commit.
* review_status=confirmed_defect is carried from the previous manifest when the
  loc is still flagged AND its live row_hash is unchanged (ground truth sticks
  to bytes, not to locs).
* excluded_now_valid locs from the previous meta are asserted CLEAN: if the
  classifier re-flags one, the build FAILS (repaired rows must stay repaired).
* The ceiling is monotonic non-increasing PER MANIFEST VERSION. A version bump
  (detector-recall correction) restarts the ceiling at the new count and must
  record the previous ceiling + the reason in the meta regeneration block.

Usage:
  python tools/build_richseg_debt_manifest.py \
      --whitelist rh_live_01_beta_whitelist.jsonl \
      --prev-manifest qamus/reports/rich-seg-known-debt.jsonl \
      --prev-meta qamus/reports/rich-seg-known-debt.meta.json \
      --out-manifest qamus/reports/rich-seg-known-debt.jsonl \
      --out-meta qamus/reports/rich-seg-known-debt.meta.json \
      --classifier-commit df89d8c8 --manifest-version 2 \
      --reason "detector-recall correction (...)" \
      [--flagged-out flagged.jsonl] [--as-of 2026-07-12]
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_segment_completeness as vsc  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CLASS_TEMPLATES = {
    "C1": {
        "primary_name": "stem_swallow",
        "skill_rule_ids": ["fusha-sarf:imperfect-agreement-prefix-segmented",
                           "fusha-sarf:verb-prefix-not-folded-into-stem"],
        "validator_gate_ids": ["QAMUS-RICH-SEG-001", "live-class:C1",
                               "validate_segment_completeness.classify_live_row/_c1_stem_swallow",
                               "record-gate:D_stem_swallow", "record-gate:B_finite_imperfect"],
    },
    "C2": {
        "primary_name": "whole_token_root",
        "skill_rule_ids": ["fusha-sarf:derived-nominal-root-must-be-asserted"],
        "validator_gate_ids": ["QAMUS-RICH-SEG-001", "live-class:C2",
                               "validate_segment_completeness.classify_live_row/_c2_whole_token_root"],
    },
    "C3": {
        "primary_name": "misclassified_function",
        "skill_rule_ids": ["fusha-sarf:finite-verb-not-filed-as-function-word",
                           "fusha-nahw:function-class-requires-true-particle"],
        "validator_gate_ids": ["QAMUS-RICH-SEG-001", "live-class:C3",
                               "validate_segment_completeness.classify_live_row/_c3_misclassified_function"],
    },
    "C4": {
        "primary_name": "fallback_leak",
        "skill_rule_ids": ["fusha-sarf:exact-occurrence-no-generic-fallback",
                           "fusha-nahw:exact-features-required"],
        "validator_gate_ids": ["QAMUS-RICH-SEG-001", "live-class:C4",
                               "validate_segment_completeness.classify_live_row/_c4_fallback_leak",
                               "record-gate:E_exact_occurrence"],
    },
    "C5": {
        "primary_name": "suffix_swallow",
        "skill_rule_ids": ["fusha-sarf:attached-pronoun-must-segment",
                           "fusha-nahw:asserted-suffix-must-render"],
        "validator_gate_ids": ["QAMUS-RICH-SEG-001", "live-class:C5",
                               "validate_segment_completeness.classify_live_row/_c5_suffix_swallow",
                               "record-gate:C_feature_to_display"],
    },
}


def raw_line_hash(line):
    """sha256 of the raw (stripped) whitelist line — the manifest/audit@2 convention."""
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def loc_key(loc):
    return tuple(int(x) for x in loc.split(":"))


def load_jsonl(path):
    rows = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def content_sha256(manifest_rows):
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in manifest_rows]
    text = "\n".join(lines) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def review_condition(cls):
    return ("re-review when the live whitelist row for this loc changes (row_hash mismatch), "
            "when the %s repair wave lands, or on any reclassification to clean" % cls)


def build(args):
    wl_rows = []  # (rec, raw_line)
    for line in io.open(args.whitelist, encoding="utf-8"):
        if line.strip():
            wl_rows.append((json.loads(line), line))
    wl_sha = hashlib.sha256(io.open(args.whitelist, "rb").read()).hexdigest()

    prev_manifest = load_jsonl(args.prev_manifest)
    prev_meta = json.load(io.open(args.prev_meta, encoding="utf-8"))
    prev_by_loc = {r["canonical_location"]: r for r in prev_manifest}
    excluded_locs = set(prev_meta.get("excluded_now_valid", {}).get("locs", []))

    flagged = []           # (loc, rhash, evidence[(cls,msg)...])
    reflagged_excluded = []
    for rec, raw in wl_rows:
        loc = rec.get("loc") or rec.get("canonical_location")
        ev = vsc.classify_live_row(rec)
        if not ev:
            continue
        if loc in excluded_locs:
            reflagged_excluded.append(loc)
            continue
        flagged.append((loc, raw_line_hash(raw), ev))

    if reflagged_excluded:
        print("FAIL: classifier re-flags %d excluded_now_valid (repaired) locs: %s"
              % (len(reflagged_excluded), sorted(reflagged_excluded)[:10]))
        return 1

    dup = len(flagged) - len({f[0] for f in flagged})
    if dup:
        print("FAIL: %d duplicate canonical_locations in flagged set" % dup)
        return 1

    manifest = []
    new_locs, carried_confirmed = [], []
    for loc, rhash, ev in sorted(flagged, key=lambda f: loc_key(f[0])):
        classes = []
        for cls, _msg in ev:
            if cls not in classes:
                classes.append(cls)
        primary = classes[0]
        secondary = classes[1:]
        prev = prev_by_loc.get(loc)
        if prev is None:
            first_known = args.classifier_commit
            new_locs.append(loc)
        else:
            first_known = prev["first_known_commit"]
        status = "candidate_flag"
        if prev is not None and prev.get("review_status") == "confirmed_defect" \
                and prev.get("row_hash") == rhash:
            status = "confirmed_defect"
            carried_confirmed.append(loc)
        tpl = CLASS_TEMPLATES[primary]
        manifest.append({
            "canonical_location": loc,
            "detector_message": ev[0][1],
            "expiry": None,
            "first_known_commit": first_known,
            "primary_class": primary,
            "primary_name": tpl["primary_name"],
            "repair_lane": primary,
            "review_condition": review_condition(primary),
            "review_status": status,
            "row_hash": rhash,
            "secondary_flags": secondary,
            "skill_rule_ids": tpl["skill_rule_ids"],
            "validator_gate_ids": tpl["validator_gate_ids"],
        })

    ceiling = len(manifest)
    partition = {}
    for r in manifest:
        partition[r["primary_class"]] = partition.get(r["primary_class"], 0) + 1
    by_status = {}
    for r in manifest:
        by_status[r["review_status"]] = by_status.get(r["review_status"], 0) + 1

    meta = json.loads(json.dumps(prev_meta))  # deep copy; carry stable blocks
    meta["as_of"] = args.as_of or datetime.date.today().isoformat()
    meta["manifest_version"] = args.manifest_version
    meta["debt_ceiling"] = ceiling
    meta["manifest_content_sha256"] = content_sha256(manifest)
    meta["partition_by_primary_class"] = dict(sorted(partition.items()))
    meta["partition_by_review_status"] = dict(sorted(by_status.items()))
    meta["rows_with_secondary_flags"] = sum(1 for r in manifest if r["secondary_flags"])
    meta["authoritative_classifier"] = {
        "classes": ["C1", "C2", "C3", "C4", "C5"],
        "classifier_semantics_commit": args.classifier_commit,
        "entrypoint": "classify_live_row",
        "tool": "tools/validate_segment_completeness.py",
        "tool_commit": args.classifier_commit,
    }
    meta["contract"]["repair_lanes"] = sorted(set(r["repair_lane"] for r in manifest))
    meta["contract"]["ceiling_semantics"] = (
        "debt_ceiling is the CURRENT count and an upper bound; a re-generated manifest at the "
        "SAME manifest_version MUST have count <= previous ceiling. An increase fails closed. "
        "The monotonic rule applies PER-MANIFEST-VERSION: a version bump (detector-recall "
        "correction) restarts the ceiling and must record the previous ceiling in `regeneration`.")
    meta["confirmed_defect_carried"] = {
        "count": len(carried_confirmed),
        "locs": sorted(carried_confirmed, key=loc_key),
        "note": prev_meta.get("confirmed_defect_carried", {}).get("note", ""),
    }
    meta["whitelist"] = {
        "path_basename": os.path.basename(args.whitelist),
        "rows": len(wl_rows),
        "sha256": wl_sha,
        "sha256_16": wl_sha[:16],
    }
    meta["regeneration"] = {
        "manifest_version_bump": "%d -> %d" % (args.manifest_version - 1, args.manifest_version),
        "previous_debt_ceiling": prev_meta.get("debt_ceiling"),
        "previous_classifier_commit": prev_meta.get("authoritative_classifier", {}).get("tool_commit"),
        "reason": args.reason,
        "new_locs_count": len(new_locs),
        "new_locs_by_class": _count_by_class(manifest, set(new_locs)),
        "primary_reclassified": {
            r["canonical_location"]:
                "%s -> %s (v3 catch outranks; previous class retained as secondary flag)"
                % (prev_by_loc[r["canonical_location"]]["primary_class"], r["primary_class"])
            for r in manifest
            if r["canonical_location"] in prev_by_loc
            and prev_by_loc[r["canonical_location"]]["primary_class"] != r["primary_class"]
        },
        "repair_lane_changes": {
            "C3": "REOPENED at detector v3 (%d new C3 candidates); the originally repaired C3 "
                  "locs stay excluded_now_valid (never grandfathered)"
                  % _count_by_class(manifest, set(new_locs)).get("C3", 0),
        },
    }

    with io.open(args.out_manifest, "w", encoding="utf-8", newline="\n") as fh:
        for r in manifest:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    with io.open(args.out_meta, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=2) + "\n")

    if args.flagged_out:
        with io.open(args.flagged_out, "w", encoding="utf-8", newline="\n") as fh:
            for loc, rhash, _ev in sorted(flagged, key=lambda f: loc_key(f[0])):
                fh.write(json.dumps({"canonical_location": loc, "row_hash": rhash},
                                    ensure_ascii=False, sort_keys=True) + "\n")

    print("OK manifest rows=%d (prev ceiling %s) new=%d confirmed_carried=%d partition=%s"
          % (ceiling, prev_meta.get("debt_ceiling"), len(new_locs),
             len(carried_confirmed), meta["partition_by_primary_class"]))
    return 0


def _count_by_class(manifest, locs):
    out = {}
    for r in manifest:
        if r["canonical_location"] in locs:
            out[r["primary_class"]] = out.get(r["primary_class"], 0) + 1
    return dict(sorted(out.items()))


def main(argv=None):
    ap = argparse.ArgumentParser(description="rich-seg known-debt manifest builder")
    ap.add_argument("--whitelist", required=True)
    ap.add_argument("--prev-manifest", required=True)
    ap.add_argument("--prev-meta", required=True)
    ap.add_argument("--out-manifest", required=True)
    ap.add_argument("--out-meta", required=True)
    ap.add_argument("--classifier-commit", required=True)
    ap.add_argument("--manifest-version", type=int, required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--flagged-out", default=None)
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
