#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an immutable, deterministic, BLIND calibration packet.

Purpose
-------
Two independent reviewers (Reviewer-A and the later, gated Reviewer-B) must
adjudicate the *same* frozen inputs so their agreement is measured on identical
material.  This tool draws a stratified sample of a rich-segmentation defect
class (C1 / C5 ...) from an audit candidate set, binds every item to the CURRENT
canonical source row (never a stale whitelist copy), and emits a packet that
carries NO ground-truth / disposition (blind).

Guarantees
----------
* Deterministic: identical inputs -> byte-identical packet (no clocks, no RNG).
* Grounded: each item's ``row_hash`` is the sha256 of the *live* whitelist row
  (canonical JSON), so if the live row changes the packet no longer matches.
* Blind: item objects contain only the fields a reviewer needs to judge the
  segmentation; no audit class, detector evidence, or ground-truth leaks in.

Row hash
--------
``row_hash`` = sha256 of the canonical JSON of the live whitelist row, where
canonical JSON = ``json.dumps(row, sort_keys=True, ensure_ascii=False,
separators=(",",":"))`` encoded UTF-8.  This is robust to key order / whitespace
differences in the source file.

Stdlib only.  Run ``--self-test`` to validate build determinism + blindness.
"""

import argparse
import hashlib
import json
import sys

BUILDER_VERSION = "calibration-packet-builder/1"

# Fixed stratum order.  Stratum = segment-count bucket of the LIVE row -- a
# structural property directly relevant to segmentation-defect classes
# (stem_swallow / suffix_swallow), carrying no disposition hint.
STRATA_ORDER = ["seg1", "seg2", "seg3", "seg4plus"]

STRATA_DEFINITION = {
    "axis": "segment_count_bucket",
    "note": (
        "Stratum is the count of segments in the CURRENT live whitelist row: "
        "structural and blind (does not encode any defect/valid disposition)."
    ),
    "buckets": {
        "seg1": "1 segment",
        "seg2": "2 segments",
        "seg3": "3 segments",
        "seg4plus": "4 or more segments",
    },
}

# Fields projected from a live segment into the blind item.  These describe the
# CURRENT segmentation under review; none encodes an audit disposition.
SEGMENT_FIELDS = [
    "segment_index",
    "surface",
    "class",
    "role",
    "label",
    "gloss_contribution",
    "sarf_note",
    "nahw_note",
]

# The exact, closed key set a blind item may contain.  Enforced by --self-test.
ITEM_KEYS = {
    "item_id",
    "loc",
    "row_hash",
    "surface",
    "current_segments",
    "stratum",
    "packet_id",
}

# Keys that would leak a disposition/ground-truth; must NEVER appear in an item.
FORBIDDEN_ITEM_KEYS = {
    "primary_defect_class",
    "primary_defect_name",
    "detector_evidence",
    "ground_truth_state",
    "review_state",
    "recommended_action",
    "secondary_flags",
    "false_positive_reason",
    "source_evidence",
}


def canonical_json(obj):
    """Deterministic compact JSON bytes (sorted keys, UTF-8)."""
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def row_hash(row):
    return hashlib.sha256(canonical_json(row)).hexdigest()


def loc_key(loc):
    """Natural numeric sort key for a 'surah:ayah:word' location."""
    parts = str(loc).split(":")
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p), ""))
        else:
            key.append((1, 0, p))
    return tuple(key)


def seg_bucket(n):
    if n <= 1:
        return "seg1"
    if n == 2:
        return "seg2"
    if n == 3:
        return "seg3"
    return "seg4plus"


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def allocate(size, populations):
    """Deterministic stratified allocation.

    ``populations`` is a dict stratum->count (only non-empty strata).  Returns a
    dict stratum->draw.  Strategy: guarantee coverage (floor of 1 per non-empty
    stratum, in STRATA_ORDER, while size allows), then distribute the remainder
    by largest-remainder (Hamilton) proportional to population, capped at each
    stratum's population, ties broken by STRATA_ORDER.  Fully deterministic.
    """
    strata = [s for s in STRATA_ORDER if populations.get(s, 0) > 0]
    total_pop = sum(populations[s] for s in strata)
    size = min(size, total_pop)
    alloc = {s: 0 for s in strata}

    # 1) coverage floor
    remaining = size
    for s in strata:
        if remaining <= 0:
            break
        alloc[s] = 1
        remaining -= 1

    # 2) largest-remainder for the rest
    if remaining > 0:
        # ideal extra beyond the floor, proportional to population
        quotas = {}
        for s in strata:
            quotas[s] = size * populations[s] / total_pop
        # desired-minus-floor, but never below 0 and never above cap
        # iterate: assign one at a time to the stratum with the largest
        # (quota - current_alloc) gap that still has capacity -- deterministic.
        while remaining > 0:
            best = None
            best_gap = None
            for s in strata:
                if alloc[s] >= populations[s]:
                    continue
                gap = quotas[s] - alloc[s]
                if best is None or gap > best_gap + 1e-12:
                    best = s
                    best_gap = gap
            if best is None:  # everyone at cap
                break
            alloc[best] += 1
            remaining -= 1
    return alloc


def build_packet(cls, audit_rows, whitelist_rows, size, created_note,
                 audit_sha, whitelist_sha):
    # index whitelist by loc (unique in the RH-LIVE whitelist)
    wl = {}
    for r in whitelist_rows:
        loc = r.get("loc")
        if loc is not None:
            wl[loc] = r

    # candidate locs for this class, present in the CURRENT whitelist
    cand_locs = []
    missing = 0
    seen = set()
    for a in audit_rows:
        if a.get("primary_defect_class") != cls:
            continue
        loc = a.get("canonical_location")
        if loc in seen:
            continue
        seen.add(loc)
        if loc in wl:
            cand_locs.append(loc)
        else:
            missing += 1
    cand_locs.sort(key=loc_key)

    # bucket into strata
    by_stratum = {s: [] for s in STRATA_ORDER}
    for loc in cand_locs:
        segs = wl[loc].get("segments") or []
        by_stratum[seg_bucket(len(segs))].append(loc)

    populations = {s: len(by_stratum[s]) for s in STRATA_ORDER if by_stratum[s]}
    alloc = allocate(size, populations)

    packet_id = "CALIB-%s@%s+%s" % (cls, audit_sha[:7], whitelist_sha[:8])

    chosen = []
    for s in STRATA_ORDER:
        n = alloc.get(s, 0)
        for loc in by_stratum[s][:n]:
            chosen.append((s, loc))
    chosen.sort(key=lambda t: loc_key(t[1]))

    items = []
    for idx, (stratum, loc) in enumerate(chosen):
        row = wl[loc]
        segs = row.get("segments") or []
        current_segments = []
        for seg in segs:
            current_segments.append(
                {k: seg.get(k) for k in SEGMENT_FIELDS if k in seg}
            )
        items.append({
            "item_id": "%s-%03d" % (cls, idx),
            "loc": loc,
            "row_hash": row_hash(row),
            "surface": row.get("surface"),
            "current_segments": current_segments,
            "stratum": stratum,
            "packet_id": packet_id,
        })

    packet_sha256 = hashlib.sha256(canonical_json(items)).hexdigest()

    strata_counts = {s: alloc.get(s, 0) for s in STRATA_ORDER}
    manifest = {
        "packet_id": packet_id,
        "packet_sha256": packet_sha256,
        "class": cls,
        "item_count": len(items),
        "created_note": created_note,
        "source_whitelist_sha": whitelist_sha,
        "audit_sha": audit_sha,
        "builder_version": BUILDER_VERSION,
        "blind": True,
        "row_hash_algorithm": (
            "sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,"
            "separators=(',',':')).encode('utf-8'))"
        ),
        "packet_sha256_algorithm": (
            "sha256 over canonical JSON of the items array"
        ),
        "strata_definition": STRATA_DEFINITION,
        "strata_order": list(STRATA_ORDER),
        "candidate_population": populations,
        "strata_allocation": strata_counts,
        "candidate_total_present_in_whitelist": len(cand_locs),
        "candidate_locs_missing_from_whitelist": missing,
    }
    return {"manifest": manifest, "items": items}


def serialize_packet(packet):
    """Byte-stable serialization for the on-disk packet file."""
    return json.dumps(
        packet, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def _self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print("  [%s] %s" % (status, msg))

    # synthetic whitelist: 6 rows across strata, plus one row the audit points
    # at that is ABSENT from the whitelist (miss handling).
    def mkrow(loc, nsegs):
        return {
            "loc": loc,
            "surface": "S" + loc,
            "segments": [
                {
                    "segment_index": i,
                    "surface": "x%d" % i,
                    "class": "qg-verb-stem",
                    "role": "verb_stem",
                    "label": "STEM",
                    "gloss_contribution": "g",
                    "sarf_note": "sarf",
                    "nahw_note": "nahw",
                    # a field NOT in SEGMENT_FIELDS -> must be dropped
                    "internal_debug": "SECRET",
                }
                for i in range(nsegs)
            ],
            # fields that must never surface in an item
            "morphline": "m",
            "parse_key": {"key": "k"},
        }

    whitelist = [
        mkrow("2:1:1", 1),
        mkrow("2:1:2", 1),
        mkrow("2:2:1", 2),
        mkrow("2:2:2", 2),
        mkrow("3:1:1", 3),
        mkrow("10:5:4", 4),
    ]
    audit = [
        {"canonical_location": "2:1:1", "primary_defect_class": "C1",
         "ground_truth_state": "confirmed_defect", "detector_evidence": [1]},
        {"canonical_location": "2:1:2", "primary_defect_class": "C1"},
        {"canonical_location": "2:2:1", "primary_defect_class": "C1"},
        {"canonical_location": "2:2:2", "primary_defect_class": "C1"},
        {"canonical_location": "3:1:1", "primary_defect_class": "C1"},
        {"canonical_location": "10:5:4", "primary_defect_class": "C1"},
        # different class -> excluded
        {"canonical_location": "2:1:1", "primary_defect_class": "C5"},
        # points at a loc absent from the whitelist -> counted as miss
        {"canonical_location": "99:9:9", "primary_defect_class": "C1"},
    ]

    p = build_packet("C1", audit, whitelist, size=50,
                     created_note="2026-07-12",
                     audit_sha="3d806386", whitelist_sha="1c06d85a")

    # determinism / reproducibility
    p2 = build_packet("C1", audit, whitelist, size=50,
                      created_note="2026-07-12",
                      audit_sha="3d806386", whitelist_sha="1c06d85a")
    check(serialize_packet(p) == serialize_packet(p2),
          "reproducible: identical inputs -> byte-identical packet")
    check(p["manifest"]["packet_sha256"] == p2["manifest"]["packet_sha256"],
          "reproducible: identical packet_sha256")

    # all 6 present candidates drawn (size 50 >= 6); miss counted
    check(p["manifest"]["item_count"] == 6, "all present candidates included")
    check(p["manifest"]["candidate_locs_missing_from_whitelist"] == 1,
          "absent-from-whitelist candidate counted as miss")

    # coverage of all non-empty strata (floor of 1 each)
    alloc = p["manifest"]["strata_allocation"]
    check(alloc == {"seg1": 2, "seg2": 2, "seg3": 1, "seg4plus": 1},
          "stratified allocation covers every non-empty stratum")

    # blindness: closed key set, nothing forbidden, no leaked segment fields
    blind_ok = True
    for it in p["items"]:
        keys = set(it.keys())
        if keys != ITEM_KEYS:
            blind_ok = False
        if keys & FORBIDDEN_ITEM_KEYS:
            blind_ok = False
        for seg in it["current_segments"]:
            if set(seg.keys()) - set(SEGMENT_FIELDS):
                blind_ok = False
    check(blind_ok, "items are blind: closed key set, no disposition leak")

    # no ground-truth string anywhere in the serialized packet
    blob = serialize_packet(p)
    check("confirmed_defect" not in blob and "SECRET" not in blob,
          "serialized packet contains no ground-truth / debug leak")

    # row_hash actually binds to live content: mutate a row -> hash changes
    h_before = p["items"][0]["row_hash"]
    mutated = json.loads(json.dumps(whitelist))
    for r in mutated:
        if r["loc"] == p["items"][0]["loc"]:
            r["surface"] = "CHANGED"
    p3 = build_packet("C1", audit, mutated, size=50,
                      created_note="2026-07-12",
                      audit_sha="3d806386", whitelist_sha="1c06d85a")
    h_after = next(i["row_hash"] for i in p3["items"]
                   if i["loc"] == p["items"][0]["loc"])
    check(h_before != h_after, "row_hash changes when the live row changes")

    # sample-size cap
    small = build_packet("C1", audit, whitelist, size=3,
                         created_note="2026-07-12",
                         audit_sha="3d806386", whitelist_sha="1c06d85a")
    check(small["manifest"]["item_count"] == 3, "sample size cap honored")

    # created_note is a literal (never computed)
    check(p["manifest"]["created_note"] == "2026-07-12",
          "created_note passed through as literal string")

    print("SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="run the embedded self-test and exit")
    ap.add_argument("--class", dest="cls", help="defect class, e.g. C1 or C5")
    ap.add_argument("--audit", help="path to rich-seg-audit@2.jsonl")
    ap.add_argument("--whitelist", help="path to the live whitelist jsonl")
    ap.add_argument("--audit-sha", dest="audit_sha", default="",
                    help="short sha/commit id of the audit source (recorded)")
    ap.add_argument("--whitelist-sha", dest="whitelist_sha", default="",
                    help="short sha of the live whitelist (recorded)")
    ap.add_argument("--size", type=int, default=50, help="max items (default 50)")
    ap.add_argument("--created-note", dest="created_note", default="2026-07-12",
                    help="literal created note string (NOT computed)")
    ap.add_argument("--out", help="output packet path")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    for req in ("cls", "audit", "whitelist", "out"):
        if not getattr(args, req):
            ap.error("--%s is required (or use --self-test)" %
                     req.replace("cls", "class"))

    audit_rows = load_jsonl(args.audit)
    whitelist_rows = load_jsonl(args.whitelist)
    packet = build_packet(
        args.cls, audit_rows, whitelist_rows, args.size,
        args.created_note, args.audit_sha, args.whitelist_sha,
    )
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(serialize_packet(packet))
    m = packet["manifest"]
    print("wrote %s" % args.out)
    print("  class=%s items=%d packet_sha256=%s" %
          (m["class"], m["item_count"], m["packet_sha256"]))
    print("  strata_allocation=%s" % m["strata_allocation"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
