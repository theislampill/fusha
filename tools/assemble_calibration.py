#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble Reviewer-A + Reviewer-B dispositions over a blind calibration packet.

Given one immutable packet (from ``build_calibration_packet.py``) and two
reviewer disposition files, this tool merges dispositions on matching
``(packet_id, row_hash)`` and flags AGREEMENT vs DISAGREEMENT across the
adjudication dimensions:

    conclusion, source_identity, morphology_reasoning, rule_ids,
    defeaters, gate, alternative_treatment

Rules
-----
* Deterministic; stdlib only; no clocks/RNG.
* Matching key is (packet_id, row_hash) -- the packet's blind identity.
* A disposition referencing a row_hash NOT in the packet is reported as an
  integrity error (packets are immutable; reviewers must review the frozen set).
* DISAGREEMENTS route to authoritative escalation.  This tool NEVER
  majority-votes or picks a winner (there are only two reviewers by design, and
  the safe direction is to escalate, never to average).

Disposition record schema (JSONL, one object per line)
------------------------------------------------------
    {
      "packet_id": "...", "row_hash": "...",
      "conclusion": "defect|valid|<label>",
      "source_identity": "<canonical source>",
      "morphology_reasoning": "<free text>",
      "rule_ids": ["...", ...],
      "defeaters": ["...", ...],
      "gate": "pass|block|escalate|...",
      "alternative_treatment": "<free text or ''>"
    }

Run ``--self-test`` to validate agreement / disagreement / missing / integrity.
"""

import argparse
import hashlib
import json
import re
import sys

ASSEMBLER_VERSION = "calibration-assembler/1"

# Dimensions compared.  "set" = order-insensitive list; "text" = normalized
# free text; "scalar" = normalized string equality.
DIMENSIONS = [
    ("conclusion", "scalar"),
    ("source_identity", "scalar"),
    ("morphology_reasoning", "text"),
    ("rule_ids", "set"),
    ("defeaters", "set"),
    ("gate", "scalar"),
    ("alternative_treatment", "text"),
]


def norm_scalar(v):
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v).strip().lower())


def norm_text(v):
    if v is None:
        return ""
    s = str(v).lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_set(v):
    if v is None:
        return frozenset()
    if isinstance(v, (list, tuple, set)):
        return frozenset(norm_scalar(x) for x in v)
    return frozenset([norm_scalar(v)])


def dim_equal(kind, a, b):
    if kind == "scalar":
        return norm_scalar(a) == norm_scalar(b)
    if kind == "text":
        return norm_text(a) == norm_text(b)
    if kind == "set":
        return norm_set(a) == norm_set(b)
    raise ValueError("unknown kind %r" % kind)


def canonical_json(obj):
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def index_dispositions(rows):
    idx = {}
    for r in rows:
        key = (r.get("packet_id"), r.get("row_hash"))
        idx[key] = r
    return idx


def assemble(packet, review_a, review_b):
    manifest = packet["manifest"]
    items = packet["items"]

    # integrity: recompute packet_sha256 over items
    recomputed = hashlib.sha256(canonical_json(items)).hexdigest()
    packet_intact = recomputed == manifest.get("packet_sha256")

    valid_keys = set((it["packet_id"], it["row_hash"]) for it in items)
    a_idx = index_dispositions(review_a)
    b_idx = index_dispositions(review_b)

    orphan_a = sorted(str(k) for k in a_idx if k not in valid_keys)
    orphan_b = sorted(str(k) for k in b_idx if k not in valid_keys)

    results = []
    counts = {
        "agreement": 0,
        "disagreement": 0,
        "missing_reviewer": 0,
    }

    for it in items:
        key = (it["packet_id"], it["row_hash"])
        a = a_idx.get(key)
        b = b_idx.get(key)
        entry = {
            "packet_id": it["packet_id"],
            "row_hash": it["row_hash"],
            "loc": it.get("loc"),
        }
        if a is None or b is None:
            entry["routing"] = "missing_reviewer"
            entry["present"] = {
                "reviewer_a": a is not None,
                "reviewer_b": b is not None,
            }
            counts["missing_reviewer"] += 1
            results.append(entry)
            continue

        per_dim = {}
        all_agree = True
        for name, kind in DIMENSIONS:
            eq = dim_equal(kind, a.get(name), b.get(name))
            per_dim[name] = {
                "agree": eq,
                "reviewer_a": a.get(name),
                "reviewer_b": b.get(name),
            }
            if not eq:
                all_agree = False
        entry["per_dimension"] = per_dim
        entry["agreement"] = all_agree
        if all_agree:
            entry["routing"] = "agreement"
            counts["agreement"] += 1
        else:
            entry["routing"] = "escalate_authoritative"
            entry["disagreeing_dimensions"] = [
                name for name, _ in DIMENSIONS if not per_dim[name]["agree"]
            ]
            counts["disagreement"] += 1
        results.append(entry)

    summary = {
        "assembler_version": ASSEMBLER_VERSION,
        "packet_id": manifest.get("packet_id"),
        "packet_sha256": manifest.get("packet_sha256"),
        "packet_sha256_recomputed": recomputed,
        "packet_intact": packet_intact,
        "class": manifest.get("class"),
        "item_count": len(items),
        "counts": counts,
        "escalations": counts["disagreement"],
        "reviewer_a_orphan_dispositions": orphan_a,
        "reviewer_b_orphan_dispositions": orphan_b,
        "dimensions": [d for d, _ in DIMENSIONS],
        "policy": (
            "disagreements route to authoritative escalation; never "
            "majority-voted or averaged"
        ),
    }
    return {"summary": summary, "results": results}


def serialize(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


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

    items = [
        {"item_id": "C1-000", "loc": "2:1:1", "row_hash": "h1",
         "surface": "a", "current_segments": [], "stratum": "seg1",
         "packet_id": "PKT"},
        {"item_id": "C1-001", "loc": "2:1:2", "row_hash": "h2",
         "surface": "b", "current_segments": [], "stratum": "seg1",
         "packet_id": "PKT"},
        {"item_id": "C1-002", "loc": "2:2:1", "row_hash": "h3",
         "surface": "c", "current_segments": [], "stratum": "seg2",
         "packet_id": "PKT"},
    ]
    packet_sha = hashlib.sha256(canonical_json(items)).hexdigest()
    packet = {"manifest": {"packet_id": "PKT", "packet_sha256": packet_sha,
                           "class": "C1"}, "items": items}

    def disp(rh, **kw):
        base = {
            "packet_id": "PKT", "row_hash": rh,
            "conclusion": "defect", "source_identity": "src-x",
            "morphology_reasoning": "The stem swallowed the prefix.",
            "rule_ids": ["R1", "R2"], "defeaters": ["D1"],
            "gate": "block", "alternative_treatment": "",
        }
        base.update(kw)
        return base

    # h1 -> full agreement (reviewers phrase morphology differently but same
    # normalized text is not required to match; here identical after norm)
    # h2 -> disagreement on conclusion + gate
    # h3 -> A only (missing reviewer B)
    review_a = [
        disp("h1"),
        disp("h2", conclusion="defect", gate="block"),
        disp("h3"),
    ]
    review_b = [
        disp("h1", rule_ids=["R2", "R1"],  # set order-insensitive -> agree
              morphology_reasoning="the  stem swallowed the prefix"),  # punct/ws
        disp("h2", conclusion="valid", gate="pass"),
        # h3 missing from B
        # an orphan disposition referencing an unknown row_hash
        disp("h_unknown"),
    ]

    out = assemble(packet, review_a, review_b)
    s = out["summary"]
    check(s["packet_intact"] is True, "packet integrity verified (sha match)")
    check(s["counts"]["agreement"] == 1, "one full-agreement item")
    check(s["counts"]["disagreement"] == 1, "one disagreement item")
    check(s["counts"]["missing_reviewer"] == 1, "one missing-reviewer item")

    by_hash = {r["row_hash"]: r for r in out["results"]}
    check(by_hash["h1"]["routing"] == "agreement",
          "h1 routes to agreement (set + text normalized)")
    check(by_hash["h2"]["routing"] == "escalate_authoritative",
          "h2 disagreement routes to authoritative escalation")
    check(set(by_hash["h2"]["disagreeing_dimensions"]) ==
          {"conclusion", "gate"}, "h2 flags exactly conclusion + gate")
    check(by_hash["h3"]["routing"] == "missing_reviewer",
          "h3 routes to missing_reviewer")
    check(s["reviewer_b_orphan_dispositions"] and
          "h_unknown" in s["reviewer_b_orphan_dispositions"][0],
          "orphan disposition (unknown row_hash) flagged")

    # determinism
    out2 = assemble(packet, review_a, review_b)
    check(serialize(out) == serialize(out2), "assembler output deterministic")

    # tamper detection: mutating an item breaks integrity
    bad = {"manifest": dict(packet["manifest"]),
           "items": [dict(i) for i in items]}
    bad["items"][0]["surface"] = "TAMPERED"
    out3 = assemble(bad, review_a, review_b)
    check(out3["summary"]["packet_intact"] is False,
          "tampered packet detected (sha mismatch)")

    print("SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="run the embedded self-test and exit")
    ap.add_argument("--packet", help="path to the calibration packet json")
    ap.add_argument("--review-a", dest="review_a",
                    help="path to Reviewer-A dispositions (jsonl)")
    ap.add_argument("--review-b", dest="review_b",
                    help="path to Reviewer-B dispositions (jsonl)")
    ap.add_argument("--out", help="output assembled json path")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    for req in ("packet", "review_a", "review_b", "out"):
        if not getattr(args, req):
            ap.error("--%s is required (or use --self-test)" %
                     req.replace("_", "-"))

    with open(args.packet, "r", encoding="utf-8") as fh:
        packet = json.load(fh)
    review_a = load_jsonl(args.review_a)
    review_b = load_jsonl(args.review_b)
    out = assemble(packet, review_a, review_b)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(serialize(out))
    s = out["summary"]
    print("wrote %s" % args.out)
    print("  packet_intact=%s counts=%s" % (s["packet_intact"], s["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
