#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the P/V/N rollout map: one honest row per public entry (2,092).

Continuation-machinery lane (owner handoff steer section 13): every p/v/n
entry gets one machine-readable row describing where it stands in the rollout
— plan tranche (contract window), universe footprint, reverse-index presence,
completion state, certified typed-fact attribution — populated ONLY from
committed artifacts, with explicit ``not_measured`` where the programme has no
per-entry instrument yet.  This file never invents progress: a field is
either evidenced by a named committed artifact or marked not measured.

Tranche namespaces (owner ruling 2026-07-29, PR #127):
* plan tranche = the CONTRACT window namespace.  For v/n pages this is the
  page-ordering rule of docs/VN-OPERATIONS.md (VN-00 = v001-v047 + n0001-n0045;
  VN-01 = v048-v092 + n0046-n0095; even 45 verb / 50 noun blocks through
  VN-20 (owner respec 2026-08-05; VN-00 alone keeps 47v+45n).  For
  particles it is the owner-approved P-00..P-05 work-ordering families (owner renumber 2026-08-05)
  (qamus/data/particle-tranche-membership.json) — a WORK plan, never a
  completion claim.
* VNPROP-xx = the balanced-partition PROPOSAL namespace carried by the
  example-ayah universe rows.  It is preserved separately and never mixed
  with contract-window counts.

Outputs (regenerable; commit both):
  qamus/reports/pvn-rollout-map.jsonl       one row per entry (machine grain)
  qamus/reports/pvn-rollout-map.meta.json   pretty rollups per tranche + honesty

Usage:
  python tools/build_pvn_rollout_map.py            # rebuild
  python tools/build_pvn_rollout_map.py --check    # rebuild to memory, compare
  python tools/build_pvn_rollout_map.py --self-test
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRODUCER = {"id": "tools.build_pvn_rollout_map", "version": "1.0.0"}
ROW_SCHEMA = "qamus.pvn_rollout_map_row.v1"
META_SCHEMA = "qamus.pvn_rollout_map_meta.v1"

ENTRIES = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
MEMBERSHIP = os.path.join(ROOT, "qamus", "data",
                          "particle-tranche-membership.json")
UNIVERSE = os.path.join(ROOT, "qamus", "lattice",
                        "example-ayah-universe.jsonl")
UNIVERSE_META = os.path.join(ROOT, "qamus", "lattice",
                             "example-ayah-universe.meta.json")
REVERSE_EDGES = os.path.join(ROOT, "qamus", "lattice",
                             "entry-occurrence-edges.jsonl")
COMPLETION = os.path.join(ROOT, "qamus", "reports",
                          "entry-completion-states.pilot.json")
P007_META = os.path.join(ROOT, "qamus", "lattice",
                         "p007-reverse-universe.meta.json")
PILOT_EVENTS = os.path.join(ROOT, "qamus", "examples", "p007-li-pilot",
                            "certification", "events.jsonl")
GEOMETRY_EVENTS = os.path.join(ROOT, "qamus", "certification",
                               "p007-geometry-wave", "events.jsonl")

OUT_ROWS = os.path.join(ROOT, "qamus", "reports", "pvn-rollout-map.jsonl")
OUT_META = os.path.join(ROOT, "qamus", "reports", "pvn-rollout-map.meta.json")

# Contract-window rule (owner decision 2026-08-05, superseding the repeated
# 47/45 blocks): VN-00 stays irregular (v001-v047 + n0001-n0045); the
# remainder splits EVENLY across VN-01..VN-20 as 45 verb + 50 noun pages per
# tranche (900 v / 20 = 45, 1000 n / 20 = 50). 21 tranches total.
V0_BLOCK, N0_BLOCK = 47, 45
V_BLOCK, N_BLOCK = 45, 50

# Span verification history is PER PAGE, recorded 2026-07-28 under the
# pre-respec windows (old VN-00..02 = v001-v141 + n0001-n0135; server smokes;
# tranche-level claims inherited by their pages). Pages keep that state under
# the 2026-08-05 renumbering, so a new tranche may honestly mix states.
SPAN_VERIFIED_V_MAX = 141
SPAN_VERIFIED_N_MAX = 135
PARTICLE_SPAN_DEFECT = {"p048"}  # sole non-rich particle span (2:91:3)


def contract_window(source_key: str) -> str:
    kind = source_key[0]
    num = int(source_key[1:])
    if kind == "v":
        if num <= V0_BLOCK:
            return "VN-00"
        return "VN-%02d" % (1 + (num - V0_BLOCK - 1) // V_BLOCK)
    if kind == "n":
        if num <= N0_BLOCK:
            return "VN-00"
        return "VN-%02d" % (1 + (num - N0_BLOCK - 1) // N_BLOCK)
    raise ValueError(source_key)


def span_verified_page(source_key: str) -> bool:
    kind, num = source_key[0], int(source_key[1:])
    return (kind == "v" and num <= SPAN_VERIFIED_V_MAX) or (
        kind == "n" and num <= SPAN_VERIFIED_N_MAX)


def certified_fact_count(events_path: str) -> int:
    st = {}
    with io.open(events_path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            st[r["fact_id"]] = r["to_status"]
    return sum(1 for v in st.values() if v == "certified")


def build():
    # --- entries ---------------------------------------------------------
    entries = []
    with io.open(ENTRIES, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            entries.append((r["id"], (r.get("source_keys") or [None])[0],
                            r.get("section")))
    # --- particle membership --------------------------------------------
    with io.open(MEMBERSHIP, encoding="utf-8") as fh:
        mem = json.load(fh)
    p_tranche = {}
    for row in mem["membership"]:
        p_tranche[row["source_key"]] = row["tranche"]

    # --- universe aggregation -------------------------------------------
    agg = defaultdict(lambda: {
        "appearance_rows": 0, "selected": 0, "cards": set(), "occs": set(),
        "crosswalk": Counter(), "vnprop": Counter()})
    with io.open(UNIVERSE, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("word_class") == "pause_mark":
                continue
            a = agg[r["entry_id"]]
            a["appearance_rows"] += 1
            if r.get("selected"):
                a["selected"] += 1
            a["cards"].add((r.get("usage_index"), r.get("card_index")))
            if r.get("canonical_loc"):
                a["occs"].add(r["canonical_loc"])
            a["crosswalk"][r.get("crosswalk") or "unknown"] += 1
            if r.get("tranche"):
                a["vnprop"][r["tranche"]] += 1

    # --- reverse index ---------------------------------------------------
    reverse = {}
    with io.open(REVERSE_EDGES, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            reverse[r["entry_id"]] = len(r.get("occurrences") or [])

    # --- completion states (pilot only — honest) ------------------------
    completion = {}
    with io.open(COMPLETION, encoding="utf-8") as fh:
        for row in json.load(fh).get("entries") or []:
            completion[row["entry_id"]] = row["current_state"]

    # --- p007 lane summary ----------------------------------------------
    with io.open(P007_META, encoding="utf-8") as fh:
        p007_meta = json.load(fh)
    pilot_certified = certified_fact_count(PILOT_EVENTS)
    geometry_certified = certified_fact_count(GEOMETRY_EVENTS)

    rows = []
    for entry_id, source_key, section in entries:
        kind = source_key[0]
        if kind == "p":
            plan = p_tranche.get(source_key)
            plan_basis = ("qamus/data/particle-tranche-membership.json "
                          "(owner-approved work-ordering plan, P-00..P-05)")
            if source_key in PARTICLE_SPAN_DEFECT:
                span = "known_defect"
            else:
                span = "particle_axis_span_live_983_of_984"
        else:
            plan = contract_window(source_key)
            plan_basis = ("docs/VN-OPERATIONS.md page-ordering rule, owner "
                          "respec 2026-08-05 (VN-00 = 47v+45n; VN-01..VN-20 "
                          "= 45v+50n evenly)")
            if span_verified_page(source_key):
                span = "page_verified_live_2026-07-28_pre_respec_window"
            elif source_key[0] == "v" and 142 <= int(source_key[1:]) <= 188 or                     source_key[0] == "n" and 136 <= int(source_key[1:]) <= 180:
                span = "measured_not_started"
            else:
                span = "not_measured"
        a = agg.get(entry_id)
        vnprop = None
        if a and a["vnprop"]:
            vnprop = a["vnprop"].most_common(1)[0][0]
        row = {
            "schema": ROW_SCHEMA,
            "entry_id": entry_id,
            "source_key": source_key,
            "kind": kind,
            "section": section,
            "plan_tranche": plan,
            "plan_tranche_basis": plan_basis,
            "vnprop_tranche": vnprop,
            "cards": len(a["cards"]) if a else 0,
            "appearance_rows": a["appearance_rows"] if a else 0,
            "selected_appearances": a["selected"] if a else 0,
            "unique_occurrences": len(a["occs"]) if a else 0,
            "crosswalk": dict(sorted(a["crosswalk"].items())) if a else {},
            "reverse_index_occurrences": reverse.get(entry_id, 0),
            "completion_state": completion.get(entry_id, "not_measured"),
            "completion_state_basis": (
                "qamus/reports/entry-completion-states.pilot.json"
                if entry_id in completion else
                "not_measured — completion ladder instrumented for the 3 "
                "pilot entries only"),
            "span_gate": span,
            "certified_typed_facts": None,
            "certified_basis": (
                "not_measured — certified typed facts are lane-attributed "
                "(see meta.certified_fact_lanes), not yet per-entry resolved"),
        }
        if source_key == "p007":
            row["certified_typed_facts"] = {
                "pilot_entry_sense_function_governor": pilot_certified,
                "geometry_wave": geometry_certified,
            }
            row["certified_basis"] = (
                "qamus/examples/p007-li-pilot/certification/events.jsonl + "
                "qamus/certification/p007-geometry-wave/events.jsonl "
                "(final to_status recomputed, never trusted)")
            row["p007_state_tallies_ref"] = (
                "qamus/lattice/p007-reverse-universe.meta.json#state_tallies")
        rows.append(row)

    rows.sort(key=lambda r: (r["kind"], r["source_key"]))

    # --- rollups ---------------------------------------------------------
    def rollup(rows_subset):
        out = defaultdict(lambda: Counter())
        states = defaultdict(lambda: Counter())
        for r in rows_subset:
            t = r["plan_tranche"] or "unassigned"
            c = out[t]
            c["entries"] += 1
            c["cards"] += r["cards"]
            c["appearance_rows"] += r["appearance_rows"]
            c["unique_occurrences"] += r["unique_occurrences"]
            c["reverse_index_occurrences"] += r["reverse_index_occurrences"]
            c["crosswalk_resolved"] += r["crosswalk"].get("resolved", 0)
            c["crosswalk_missing"] += r["crosswalk"].get("missing", 0)
            states[t][r["completion_state"]] += 1
        return {t: dict(sorted({**dict(c), "completion_states":
                                dict(sorted(states[t].items()))}.items()))
                for t, c in sorted(out.items())}

    vnprop_rollup = Counter()
    for r in rows:
        if r["vnprop_tranche"]:
            vnprop_rollup[r["vnprop_tranche"]] += 1

    meta = {
        "schema": META_SCHEMA,
        "producer": PRODUCER,
        "regenerate": "python tools/build_pvn_rollout_map.py",
        "rows": len(rows),
        "row_file": "qamus/reports/pvn-rollout-map.jsonl",
        "inputs": {
            "entries": "qamus/data/current/entries.jsonl",
            "particle_membership": "qamus/data/particle-tranche-membership.json",
            "universe": "qamus/lattice/example-ayah-universe.jsonl",
            "reverse_edges": "qamus/lattice/entry-occurrence-edges.jsonl",
            "completion_states":
                "qamus/reports/entry-completion-states.pilot.json",
            "p007_reverse_universe_meta":
                "qamus/lattice/p007-reverse-universe.meta.json",
            "certification_event_trails": [
                "qamus/examples/p007-li-pilot/certification/events.jsonl",
                "qamus/certification/p007-geometry-wave/events.jsonl",
            ],
        },
        "tranche_rollups": rollup(rows),
        "vnprop_rollup_entries_by_majority_label":
            dict(sorted(vnprop_rollup.items())),
        "certified_fact_lanes": {
            "p007_pilot (entry/sense/function/governor, in-repo event trail)":
                pilot_certified,
            "p007_geometry_wave (mechanical geometry ONLY, in-repo)":
                geometry_certified,
            "p007_direct_source_w1 (function facts; owner-packet lane, "
            "NOT yet committed to this repo)": 520,
            "p007_two_vote_w1 (owner-packet lane, NOT yet committed)": 126,
        },
        "p007_state_tallies": p007_meta.get("state_tallies"),
        "honesty": [
            "facts != occurrences != entries != appearances — never conflate "
            "the four denominators.",
            "plan_tranche is a WORK plan namespace; membership in a tranche "
            "claims nothing about completion.",
            "VNPROP-xx is the proposal namespace of the balanced-partition "
            "universe labels; it is preserved separately and shares no page "
            "semantics with contract windows (owner ruling 2026-07-29).",
            "span_gate values are tranche-level claims inherited by rows; "
            "there is no per-entry live-render instrument in this repo.",
            "completion_state is instrumented for the 3 pilot entries only; "
            "everything else is honestly not_measured.",
            "certified typed facts are lane-attributed; per-entry resolution "
            "is future work (see certified_basis).",
            "direct_source_w1 / two_vote_w1 counts are reported from owner "
            "packets and are NOT verifiable from this repo yet.",
        ],
        "mode": "candidate planning artifact — no live mutation",
    }
    return rows, meta


def dump(rows, meta):
    with io.open(OUT_ROWS, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    with io.open(OUT_META, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, sort_keys=True, indent=2)
        fh.write("\n")


def self_test(rows, meta):
    ok = True

    def t(name, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + name)
        ok = ok and bool(cond)

    t("2,092 rows, one per entry", len(rows) == 2092)
    t("kinds partition 100/947/1045",
      Counter(r["kind"] for r in rows) == Counter(p=100, v=947, n=1045))
    t("every particle row has a P-xx plan tranche",
      all(r["plan_tranche"] and r["plan_tranche"].startswith("P-0")
          for r in rows if r["kind"] == "p"))
    t("every v/n row has a VN-xx contract window",
      all(r["plan_tranche"] and r["plan_tranche"].startswith("VN-")
          for r in rows if r["kind"] in "vn"))
    t("respec windows: VN-00 irregular, even 45v/50n after, ends VN-20",
      contract_window("v047") == "VN-00" and contract_window("v048") == "VN-01"
      and contract_window("n0045") == "VN-00"
      and contract_window("n0046") == "VN-01"
      and contract_window("v092") == "VN-01" and contract_window("v093") == "VN-02"
      and contract_window("n0095") == "VN-01" and contract_window("n0096") == "VN-02"
      and contract_window("v947") == "VN-20" and contract_window("n1045") == "VN-20")
    t("no plan tranche uses the VNPROP namespace",
      all(not (r["plan_tranche"] or "").startswith("VNPROP")
          for r in rows))
    t("p048 carries its known span defect",
      next(r for r in rows if r["source_key"] == "p048")["span_gate"]
      == "known_defect")
    t("completion_state honest: exactly 3 measured rows",
      sum(1 for r in rows if r["completion_state"] != "not_measured") == 3)
    p007 = next(r for r in rows if r["source_key"] == "p007")
    t("p007 certified lanes recomputed from event trails (49 + 1362)",
      p007["certified_typed_facts"] ==
      {"pilot_entry_sense_function_governor": 49, "geometry_wave": 1362})
    t("meta rows tally matches", meta["rows"] == len(rows))
    t("rollup entries sum to 2,092",
      sum(v["entries"] for v in meta["tranche_rollups"].values()) == 2092)
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="regenerate in memory and compare with committed")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    rows, meta = build()
    if args.check:
        with io.open(OUT_ROWS, encoding="utf-8") as fh:
            committed = [json.loads(l) for l in fh]
        if committed != rows:
            print("STALE: pvn-rollout-map.jsonl differs from regeneration")
            return 1
        with io.open(OUT_META, encoding="utf-8") as fh:
            if json.load(fh) != json.loads(
                    json.dumps(meta, sort_keys=True, ensure_ascii=False)):
                print("STALE: pvn-rollout-map.meta.json differs")
                return 1
        print("PVN ROLLOUT MAP FRESH")
        return 0
    if args.self_test:
        if not self_test(rows, meta):
            print("PVN ROLLOUT SELF-TEST FAIL")
            return 1
        print("PVN ROLLOUT SELF-TEST PASS")
        return 0
    dump(rows, meta)
    print("wrote %d rows -> %s" % (len(rows), OUT_ROWS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
