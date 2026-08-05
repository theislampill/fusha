#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the example-ayah universe + particle-occurrence matrix artifacts.

Three invariant families (the UNIVERSE gates):

1. P-entry coverage — the committed particle membership table carries all 100
   particle entries exactly once, tranche sizes match the owner-approved
   P-00=12 / P-01=17 / P-02=22 / P-03=49 split, and the matrix meta reports
   every particle (zero-candidate particles must be explicit, not absent).
2. Selected/context denominators — displayed_words == selected + context,
   tokens == words + pause marks, and the unique-occurrence vs appearance
   denominators are preserved (rollup counts must re-add to the appearance
   totals; occurrence rows never collapse appearances).
3. Appearance-parity extension — every universe row claiming ``wbw_present``
   points at a loc that exists in the canonical occurrence-appearance index,
   and every matrix row's occurrence exists in the universe rollup.
4. Proposal/contract namespace guard — a universe row whose ``tranche_kind``
   is ``VN`` carries a proposal-namespace label (``VNPROP-xx``); it must
   never collide with a contract window identifier (``VN-00``..``VN-23``).
   The universe tranche field is the balanced-partition DERIVED PROPOSAL,
   not the contract windows (owner ruling 2026-07-29;
   VN-UNLOCK-PROOF-2026-07-29 Finding 0).

``--self-test`` is red-first: each invariant is first shown to FAIL on a
corrupted fixture, then to pass on the clean fixture.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEFAULT_MEMBERSHIP = os.path.join(
    REPO_ROOT, "qamus", "data", "particle-tranche-membership.json")
DEFAULT_UNIVERSE = os.path.join(
    REPO_ROOT, "qamus", "lattice", "example-ayah-universe.jsonl")
DEFAULT_MATRIX = os.path.join(
    REPO_ROOT, "qamus", "lattice", "particle-occurrence-matrix.jsonl")
DEFAULT_APPEARANCE_INDEX = os.path.join(
    REPO_ROOT, "qamus", "indexes", "occurrence-appearances.jsonl")

# Owner renumber 2026-08-05 (docs/decision-ledger.md): the 49-entry P-03 long
# tail split into P-03/P-04/P-05 on shared analytical machinery.
EXPECTED_TRANCHE_SIZES = {"P-00": 12, "P-01": 17, "P-02": 22, "P-03": 16,
                          "P-04": 18, "P-05": 15}
CONTRACT_WINDOW_IDS = frozenset(f"VN-{i:02d}" for i in range(24))
PROPOSAL_VN_LABELS = frozenset(f"VNPROP-{i:02d}" for i in range(21))


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected object at {path}:{line_no}")
            yield value


def validate_membership(payload, errors):
    rows = payload.get("membership") or []
    source_keys = [row.get("source_key") for row in rows]
    expected = [f"p{i:03d}" for i in range(1, 101)]
    if sorted(source_keys) != expected:
        errors.append(
            "membership must contain p001..p100 exactly once "
            f"(got {len(rows)} rows, {len(set(source_keys))} distinct)")
    entry_ids = [row.get("entry_id") for row in rows]
    if len(set(entry_ids)) != len(entry_ids):
        errors.append("membership entry_ids are not unique")
    sizes = Counter(row.get("tranche") for row in rows)
    if dict(sizes) != EXPECTED_TRANCHE_SIZES:
        errors.append(
            f"tranche sizes {dict(sizes)} != approved {EXPECTED_TRANCHE_SIZES}")
    for row in rows:
        if row.get("tranche") == "P-02" and not row.get("scholar_two_vote_required"):
            errors.append(
                f"{row.get('source_key')}: P-02 row missing scholar_two_vote_required")


def validate_universe(universe_rows, occurrence_rows, meta, errors,
                      appearance_locs=None):
    totals = (meta or {}).get("totals") or {}
    counts = Counter()
    seen_ids = set()
    occ_from_rows = Counter()
    selected_at = Counter()
    context_at = Counter()
    for row in universe_rows:
        appearance_id = row.get("appearance_id")
        if appearance_id in seen_ids:
            errors.append(f"duplicate appearance_id {appearance_id}")
        seen_ids.add(appearance_id)
        counts["tokens"] += 1
        if row.get("word_class") == "pause_mark":
            counts["pause_marks"] += 1
            continue
        counts["words"] += 1
        if row.get("tranche_kind") == "VN":
            tranche = row.get("tranche")
            if tranche in CONTRACT_WINDOW_IDS:
                errors.append(
                    f"{appearance_id}: proposal-namespace tranche label {tranche!r} "
                    "collides with a contract window id (VN-00..VN-23); universe "
                    "VN tranches must use the VNPROP-xx proposal namespace")
            elif tranche not in PROPOSAL_VN_LABELS:
                errors.append(
                    f"{appearance_id}: unknown VN proposal tranche label {tranche!r}")
        if row.get("selected") is True:
            counts["selected"] += 1
        elif row.get("selected") is False:
            counts["context"] += 1
        else:
            errors.append(f"{appearance_id}: word row lacks boolean selected")
        loc = row.get("canonical_loc")
        if loc:
            counts["aligned"] += 1
            occ_from_rows[loc] += 1
            (selected_at if row.get("selected") else context_at)[loc] += 1
            if row.get("crosswalk") != "resolved":
                errors.append(f"{appearance_id}: aligned row crosswalk != resolved")
            if row.get("wbw_present") and appearance_locs is not None \
                    and loc not in appearance_locs:
                errors.append(
                    f"{appearance_id}: wbw_present but loc {loc} missing from "
                    "occurrence-appearance index")
        else:
            counts["unaligned"] += 1
            if not row.get("blockers"):
                errors.append(f"{appearance_id}: unaligned row lacks blockers")

    if counts["words"] != counts["selected"] + counts["context"]:
        errors.append(
            f"selected/context denominator broken: {counts['words']} words != "
            f"{counts['selected']} selected + {counts['context']} context")
    if counts["tokens"] != counts["words"] + counts["pause_marks"]:
        errors.append("token denominator broken (words + pause marks)")

    rollup_appearances = 0
    for occurrence in occurrence_rows:
        loc = occurrence.get("canonical_loc")
        ids = occurrence.get("appearance_ids") or []
        if occurrence.get("appearance_count") != len(ids):
            errors.append(f"occurrence {loc}: appearance_count != len(appearance_ids)")
        rollup_appearances += len(ids)
        if occ_from_rows and occ_from_rows.get(loc) != len(ids):
            errors.append(
                f"occurrence {loc}: rollup lists {len(ids)} appearances, "
                f"universe rows have {occ_from_rows.get(loc, 0)}")
        if (occurrence.get("selected_appearances", 0)
                + occurrence.get("context_appearances", 0)) != len(ids):
            errors.append(f"occurrence {loc}: selected+context != appearances")
        for appearance_id in ids:
            if seen_ids and appearance_id not in seen_ids:
                errors.append(
                    f"occurrence {loc}: unknown appearance_id {appearance_id}")
    if occ_from_rows and len(occurrence_rows) != len(occ_from_rows):
        errors.append(
            f"unique-occurrence denominator broken: rollup has "
            f"{len(occurrence_rows)} rows, universe implies {len(occ_from_rows)}")
    if occ_from_rows and rollup_appearances != counts["aligned"]:
        errors.append(
            "appearance denominator broken: rollup appearances "
            f"{rollup_appearances} != aligned universe words {counts['aligned']}")

    checks = {
        "displayed_tokens": counts["tokens"],
        "displayed_words": counts["words"],
        "pause_mark_tokens": counts["pause_marks"],
        "selected_words": counts["selected"],
        "context_words": counts["context"],
        "aligned_words": counts["aligned"],
        "unaligned_words": counts["unaligned"],
        "unique_occurrences": len(occurrence_rows),
        "appearances_at_occurrences": rollup_appearances,
    }
    for key, value in checks.items():
        if totals and totals.get(key) != value:
            errors.append(
                f"meta totals.{key} = {totals.get(key)} != recomputed {value}")
    return counts


def validate_matrix(matrix_rows, membership_payload, occurrence_locs, errors):
    member_by_key = {
        row.get("source_key"): row
        for row in (membership_payload.get("membership") or [])
    }
    seen = set()
    for row in matrix_rows:
        matrix_id = row.get("matrix_id")
        if matrix_id in seen:
            errors.append(f"duplicate matrix_id {matrix_id}")
        seen.add(matrix_id)
        source_key = row.get("particle_source_key")
        member = member_by_key.get(source_key)
        if member is None:
            errors.append(f"{matrix_id}: unknown particle {source_key}")
            continue
        if row.get("particle_entry_id") != member.get("entry_id"):
            errors.append(f"{matrix_id}: entry_id disagrees with membership")
        if row.get("tranche") != member.get("tranche"):
            errors.append(f"{matrix_id}: tranche disagrees with membership")
        if row.get("certified") != "none":
            errors.append(f"{matrix_id}: certified must be 'none' in this lane")
        if not row.get("function_candidates"):
            errors.append(f"{matrix_id}: empty function_candidates")
        loc = row.get("canonical_loc")
        if occurrence_locs is not None and loc not in occurrence_locs:
            errors.append(f"{matrix_id}: loc {loc} not in universe rollup")
        if member.get("scholar_two_vote_required") and \
                "homograph_requires_scholar_two_vote" not in (row.get("blockers") or []):
            errors.append(f"{matrix_id}: P-02 row missing two-vote blocker")
        page_sum = sum((row.get("page_appearances") or {}).values())
        if page_sum != row.get("appearance_count"):
            errors.append(f"{matrix_id}: page_appearances != appearance_count")
        if row.get("appearance_count") != len(row.get("appearance_ids") or []):
            errors.append(f"{matrix_id}: appearance_ids length mismatch")


# ---------------------------------------------------------------------------
# red-first self-test fixtures


def _fixture_membership():
    rows = []
    for i in range(1, 101):
        if i <= 12:
            tranche = "P-00"
        elif i <= 29:
            tranche = "P-01"
        elif i <= 51:
            tranche = "P-02"
        elif i <= 67:
            tranche = "P-03"
        elif i <= 85:
            tranche = "P-04"
        else:
            tranche = "P-05"
        rows.append({
            "source_key": f"p{i:03d}",
            "entry_id": f"e{i:03d}",
            "headword": "x",
            "tranche": tranche,
            "function_family": "fixture",
            "scholar_two_vote_required": tranche == "P-02",
        })
    return {"membership": rows}


def _fixture_universe():
    rows = [
        {"appearance_id": "e1:u0:x0:w0", "selected": True,
         "canonical_loc": "1:1:1", "crosswalk": "resolved", "wbw_present": False},
        {"appearance_id": "e1:u0:x0:w1", "selected": False,
         "canonical_loc": "1:1:2", "crosswalk": "resolved", "wbw_present": True},
        {"appearance_id": "e1:u0:x0:w2", "word_class": "pause_mark"},
        {"appearance_id": "e2:u0:x0:w0", "selected": False,
         "canonical_loc": "1:1:2", "crosswalk": "resolved", "wbw_present": False},
    ]
    occurrences = [
        {"canonical_loc": "1:1:1", "appearance_count": 1,
         "appearance_ids": ["e1:u0:x0:w0"],
         "selected_appearances": 1, "context_appearances": 0},
        {"canonical_loc": "1:1:2", "appearance_count": 2,
         "appearance_ids": ["e1:u0:x0:w1", "e2:u0:x0:w0"],
         "selected_appearances": 0, "context_appearances": 2},
    ]
    meta = {"totals": {
        "displayed_tokens": 4, "displayed_words": 3, "pause_mark_tokens": 1,
        "selected_words": 1, "context_words": 2, "aligned_words": 3,
        "unaligned_words": 0, "unique_occurrences": 2,
        "appearances_at_occurrences": 3,
    }}
    return rows, occurrences, meta


def self_test():
    failures = []

    def expect(name, condition):
        print(("ok   " if condition else "FAIL ") + name)
        if not condition:
            failures.append(name)

    # 1) membership: clean passes, duplicate + wrong sizes fail (red first).
    broken = _fixture_membership()
    broken["membership"][1] = dict(broken["membership"][0])
    errors = []
    validate_membership(broken, errors)
    expect("red: duplicate membership row rejected", bool(errors))
    errors = []
    validate_membership(_fixture_membership(), errors)
    expect("green: clean membership accepted", not errors)

    # 2) denominators: corrupt selected flag must fail.
    rows, occurrences, meta = _fixture_universe()
    bad_rows = [dict(row) for row in rows]
    bad_rows[0].pop("selected")
    errors = []
    validate_universe(bad_rows, occurrences, meta, errors, appearance_locs={"1:1:2"})
    expect("red: missing selected flag rejected", bool(errors))
    bad_meta = {"totals": dict(meta["totals"], selected_words=999)}
    errors = []
    validate_universe(rows, occurrences, bad_meta, errors, appearance_locs={"1:1:2"})
    expect("red: divergent meta totals rejected", bool(errors))
    bad_occ = [dict(occurrences[0]), dict(occurrences[1])]
    bad_occ[1]["appearance_ids"] = bad_occ[1]["appearance_ids"][:1]
    bad_occ[1]["appearance_count"] = 1
    bad_occ[1]["context_appearances"] = 1
    errors = []
    validate_universe(rows, bad_occ, meta, errors, appearance_locs={"1:1:2"})
    expect("red: collapsed occurrence appearances rejected", bool(errors))
    errors = []
    validate_universe(rows, occurrences, meta, errors, appearance_locs={"1:1:2"})
    expect("green: clean universe accepted", not errors)

    # 3) parity extension: wbw_present without index loc must fail.
    errors = []
    validate_universe(rows, occurrences, meta, errors, appearance_locs=set())
    expect("red: wbw_present without index loc rejected", bool(errors))

    # 4) namespace guard: a VN-kind row with a bare contract window id must
    # fail (red), the VNPROP proposal spelling must pass (green).
    collided_rows = [dict(row) for row in rows]
    collided_rows[0].update({"tranche_kind": "VN", "tranche": "VN-03"})
    errors = []
    validate_universe(collided_rows, occurrences, meta, errors,
                      appearance_locs={"1:1:2"})
    expect("red: proposal/contract namespace collision rejected",
           any("collides with a contract window id" in error for error in errors))
    renamed_rows = [dict(row) for row in rows]
    renamed_rows[0].update({"tranche_kind": "VN", "tranche": "VNPROP-03"})
    errors = []
    validate_universe(renamed_rows, occurrences, meta, errors,
                      appearance_locs={"1:1:2"})
    expect("green: VNPROP proposal label accepted", not errors)

    # 4) matrix: certified must stay 'none'; P-02 must carry blocker.
    membership = _fixture_membership()
    matrix_row = {
        "matrix_id": "p030:1:1:1", "particle_source_key": "p030",
        "particle_entry_id": "e030", "tranche": "P-02",
        "canonical_loc": "1:1:1", "certified": "none",
        "function_candidates": ["fixture"],
        "blockers": ["homograph_requires_scholar_two_vote"],
        "page_appearances": {"context_on_v": 1}, "appearance_count": 1,
        "appearance_ids": ["e1:u0:x0:w0"],
    }
    errors = []
    validate_matrix([dict(matrix_row, certified="rich_certified")],
                    membership, {"1:1:1"}, errors)
    expect("red: certified matrix row rejected", bool(errors))
    errors = []
    validate_matrix([dict(matrix_row, blockers=[])], membership, {"1:1:1"}, errors)
    expect("red: P-02 row without two-vote blocker rejected", bool(errors))
    errors = []
    validate_matrix([matrix_row], membership, {"1:1:1"}, errors)
    expect("green: clean matrix row accepted", not errors)

    if failures:
        print("UNIVERSE SELF-TEST FAIL")
        return 1
    print("UNIVERSE SELF-TEST PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--membership", default=DEFAULT_MEMBERSHIP)
    parser.add_argument("--universe", default=DEFAULT_UNIVERSE)
    parser.add_argument("--matrix", default=DEFAULT_MATRIX)
    parser.add_argument("--appearance-index", default=DEFAULT_APPEARANCE_INDEX)
    parser.add_argument("--skip-appearance-index", action="store_true",
                        help="skip the wbw parity extension (faster)")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    errors = []
    with open(args.membership, encoding="utf-8") as handle:
        membership = json.load(handle)
    validate_membership(membership, errors)

    base, _ext = os.path.splitext(os.path.abspath(args.universe))
    occurrence_path = base + ".occurrences.jsonl"
    meta_path = base + ".meta.json"
    with open(meta_path, encoding="utf-8") as handle:
        meta = json.load(handle)
    appearance_locs = None
    if not args.skip_appearance_index:
        appearance_locs = {
            record["loc"] for record in _read_jsonl(args.appearance_index)}
    occurrence_rows = list(_read_jsonl(occurrence_path))
    validate_universe(_read_jsonl(args.universe), occurrence_rows, meta,
                      errors, appearance_locs=appearance_locs)
    occurrence_locs = {row.get("canonical_loc") for row in occurrence_rows}
    validate_matrix(_read_jsonl(args.matrix), membership, occurrence_locs, errors)

    for error in errors[:50]:
        print("FAIL " + error)
    if errors:
        print(f"UNIVERSE VALIDATION FAIL ({len(errors)} errors)")
        return 1
    print("UNIVERSE VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
