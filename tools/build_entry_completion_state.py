#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the HONEST entry-transclusion completion state for pilot entries.

Owner steer §16: every p/v/n entry is a first-class knowledge node walking a
12-state completion ladder (qamus/schemas/entry-completion-states.schema.json).
This builder is deliberately a STUB in ambition and strict in honesty: it
computes the CURRENT state of three pilot entries (p007 lam, one verb, one
noun) from committed artifacts only, claims a state reached only when it can
cite evidence addresses, and never claims certification-dependent states from
candidate-only artifacts.

Pilot entries:
  p007 -> b10a1ee04666  (qamus/data/particle-tranche-membership.json)
  verb -> 00107b99a50e  (section=verb in qamus/data/current/entries.jsonl)
  noun -> 001242c409ae  (section=noun in qamus/data/current/entries.jsonl)

Usage:
  python tools/build_entry_completion_state.py            # rebuild pilot report
  python tools/build_entry_completion_state.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PRODUCER = {"id": "tools.build_entry_completion_state", "version": "1.0.0"}
SCHEMA_PATH = os.path.join(ROOT, "qamus", "schemas",
                           "entry-completion-states.schema.json")
DEFAULT_OUTPUT = os.path.join(ROOT, "qamus", "reports",
                              "entry-completion-states.pilot.json")

ENTRIES_PATH = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
MEMBERSHIP_PATH = os.path.join(ROOT, "qamus", "data",
                               "particle-tranche-membership.json")
ENTRY_OCC_PATH = os.path.join(ROOT, "qamus", "lattice",
                              "entry-occurrence-edges.jsonl")
LEXEME_JOIN_PATH = os.path.join(ROOT, "qamus", "lattice",
                                "lexeme-join-edges.jsonl")
PARTICLE_MATRIX_PATH = os.path.join(ROOT, "qamus", "lattice",
                                    "particle-occurrence-matrix.jsonl")

GENERATED_FROM = [
    "qamus/data/current/entries.jsonl",
    "qamus/data/particle-tranche-membership.json",
    "qamus/lattice/entry-occurrence-edges.jsonl",
    "qamus/lattice/lexeme-join-edges.jsonl",
    "qamus/lattice/particle-occurrence-matrix.jsonl",
]

PILOTS = [
    ("b10a1ee04666", "p", "p007"),
    ("00107b99a50e", "v", ""),
    ("001242c409ae", "n", ""),
]

STATE_LADDER = [
    "entry_registered",
    "entry_membership_known",
    "forms_documented",
    "senses_enumerated",
    "root_family_mapped",
    "occurrences_discovered",
    "occurrence_links_candidate",
    "occurrence_links_certified",
    "appearances_projected",
    "reverse_index_published",
    "teaching_assets_derived",
    "fully_transcluded",
]


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _ev(address, method):
    return {"address": address, "method": method}


def _entry_states(entry, kind, source_key, *, membership_row, root_sharers,
                  occurrence_count, candidate_link_count, matrix_count):
    entry_id = entry["id"]
    states = []
    blockers = []

    def state(name, reached, evidence=None, note=None):
        row = {"state": name, "reached": bool(reached)}
        if reached:
            row["evidence"] = evidence or []
        if note:
            row["note"] = note
        states.append(row)

    state("entry_registered", True,
          [_ev("entry:%s" % entry_id, "entry_store_row")])
    if kind == "p":
        state("entry_membership_known", membership_row is not None,
              [_ev("qamus/data/particle-tranche-membership.json#%s" % source_key,
                   "owner_approved_particle_membership")])
    else:
        state("entry_membership_known", bool(entry.get("section")),
              [_ev("entry:%s:section" % entry_id, "entry_store_section")],
              note="section=%s" % entry.get("section"))
    forms = [form for usage in (entry.get("usage") or [])
             if isinstance(usage, dict)
             for form in (usage.get("forms") or []) if str(form).strip()]
    headword = str(entry.get("headword") or "").strip()
    state("forms_documented", bool(forms or headword),
          ([_ev("entry:%s:usage[*].forms" % entry_id, "documented_entry_form")]
           if forms else []) +
          ([_ev("entry:%s:headword" % entry_id, "entry_headword")]
           if headword else []),
          note=None if forms else "headword only; no per-usage forms yet")
    senses = [s for s in (entry.get("senses") or []) if isinstance(s, dict)]
    state("senses_enumerated", bool(senses),
          [_ev("entry:%s:senses" % entry_id, "entry_sense_identity")])
    root = " ".join(str(entry.get("root") or "").split())
    if not root:
        # Root-family is vacuously satisfied for rootless-by-design entries
        # (particles): root sharing NEVER entails entry identity, and there is
        # no root to share.
        state("root_family_mapped", True,
              [_ev("entry:%s:root" % entry_id, "rootless_by_design_vacuous")],
              note="particle entry has no root; root-family relation not applicable")
    else:
        state("root_family_mapped", root_sharers >= 0,
              [_ev("entry:%s:root" % entry_id, "root_agreement_only")],
              note="%d other entr%s share this root; relation only, never identity"
              % (root_sharers, "y" if root_sharers == 1 else "ies"))
    occ_reached = occurrence_count > 0 or matrix_count > 0
    occ_evidence = []
    if occurrence_count:
        occ_evidence.append(_ev("qamus/lattice/entry-occurrence-edges.jsonl#%s"
                                % entry_id, "entry_occurrence_edge_rows"))
    if matrix_count:
        occ_evidence.append(_ev("qamus/lattice/particle-occurrence-matrix.jsonl#%s"
                                % entry_id, "particle_candidate_matrix_rows"))
    state("occurrences_discovered", occ_reached, occ_evidence,
          note="%d occurrence-edge row(s), %d candidate matrix row(s)"
          % (occurrence_count, matrix_count))
    link_reached = candidate_link_count > 0 or matrix_count > 0
    link_evidence = []
    if candidate_link_count:
        link_evidence.append(_ev("qamus/lattice/lexeme-join-edges.jsonl#%s"
                                 % entry_id, "lexeme_join_candidate_rows"))
    if matrix_count:
        link_evidence.append(_ev("qamus/lattice/particle-occurrence-matrix.jsonl#%s"
                                 % entry_id, "particle_candidate_matrix_rows"))
    state("occurrence_links_candidate", link_reached, link_evidence,
          note="candidate-only; nothing here is a certification")
    # HONEST: none of the pilot entries has a certified occurrence linkage in
    # the committed fact trail; the remaining ladder states stay unreached.
    state("occurrence_links_certified", False,
          note="no certified occurrence linkage in the committed fact trail")
    blockers.append("occurrence links are candidate-only; certification requires "
                    "the evidence-bundle rung (and two-vote for i'rab-bearing "
                    "conclusions) in tools/certify_typed_fact.py")
    state("appearances_projected", False,
          note="no per-entry canonical projection consumption recorded yet")
    state("reverse_index_published", False,
          note="entry page does not yet publish a certified reverse occurrence list")
    state("teaching_assets_derived", False,
          note="no rules/drills cite certified occurrences of this entry yet")
    state("fully_transcluded", False)
    blockers.append("full transclusion requires certified links, projected "
                    "appearances, a published reverse index and teaching assets")

    reached_prefix = STATE_LADDER[0]
    for name in STATE_LADDER:
        row = next(s for s in states if s["state"] == name)
        if row["reached"]:
            reached_prefix = name
        else:
            break
    return {
        "schema": "qamus.entry_completion_state.v1",
        "entry_id": entry_id,
        "entry_kind": kind,
        **({"source_key": source_key} if source_key else {}),
        "honest": True,
        "states": states,
        "current_state": reached_prefix,
        "blockers": blockers,
    }


def build_report():
    entries_by_id = {}
    roots = {}
    for row in _read_jsonl(ENTRIES_PATH):
        entries_by_id[row.get("id")] = row
        root = " ".join(str(row.get("root") or "").split())
        if root:
            roots.setdefault(root, set()).add(row.get("id"))
    with open(MEMBERSHIP_PATH, encoding="utf-8") as handle:
        membership = {row.get("source_key"): row
                      for row in json.load(handle).get("membership") or []}
    occurrence_counts = {}
    for row in _read_jsonl(ENTRY_OCC_PATH):
        occurrence_counts[row.get("entry_id")] = len(row.get("occurrences") or [])
    wanted = {entry_id for entry_id, _, _ in PILOTS}
    candidate_links = {entry_id: 0 for entry_id in wanted}
    with open(LEXEME_JOIN_PATH, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("entry_id") in wanted:
                candidate_links[row["entry_id"]] += 1
    matrix_counts = {entry_id: 0 for entry_id in wanted}
    if os.path.exists(PARTICLE_MATRIX_PATH):
        with open(PARTICLE_MATRIX_PATH, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("particle_entry_id") in wanted:
                    matrix_counts[row["particle_entry_id"]] += 1
    result = []
    for entry_id, kind, source_key in PILOTS:
        entry = entries_by_id.get(entry_id)
        if entry is None:
            raise SystemExit("pilot entry %s missing from the entry store" % entry_id)
        root = " ".join(str(entry.get("root") or "").split())
        sharers = len(roots.get(root, set()) - {entry_id}) if root else 0
        result.append(_entry_states(
            entry, kind, source_key,
            membership_row=membership.get(source_key) if kind == "p" else None,
            root_sharers=sharers,
            occurrence_count=occurrence_counts.get(entry_id, 0),
            candidate_link_count=candidate_links.get(entry_id, 0),
            matrix_count=matrix_counts.get(entry_id, 0)))
    return {
        "schema": "qamus.entry_completion_state_report.v1",
        "generated_from": list(GENERATED_FROM),
        "producer": dict(PRODUCER),
        "entries": result,
    }


def validate_report(report):
    """Hand-rolled structural validation against the committed schema intent."""

    errors = []
    with open(SCHEMA_PATH, encoding="utf-8") as handle:
        schema = json.load(handle)
    ladder = schema["$defs"]["state_id"]["enum"]
    if ladder != STATE_LADDER:
        errors.append("builder ladder diverges from the committed schema enum")
    if report.get("schema") != "qamus.entry_completion_state_report.v1":
        errors.append("report schema tag wrong")
    for row in report.get("entries") or []:
        entry_id = row.get("entry_id")
        if row.get("honest") is not True:
            errors.append("%s: honest must be literally true" % entry_id)
        names = [s.get("state") for s in row.get("states") or []]
        if names != ladder:
            errors.append("%s: states are not exactly the 12 ladder states" % entry_id)
        prefix_broken = False
        highest = ladder[0]
        for state in row.get("states") or []:
            if state.get("reached"):
                if not state.get("evidence"):
                    errors.append("%s: state %s reached without evidence"
                                  % (entry_id, state.get("state")))
                if not prefix_broken:
                    highest = state["state"]
            else:
                prefix_broken = True
        if row.get("current_state") != highest:
            errors.append("%s: current_state %r is not the reached ladder prefix %r"
                          % (entry_id, row.get("current_state"), highest))
        certified = next((s for s in row.get("states") or []
                          if s.get("state") == "occurrence_links_certified"), {})
        if certified.get("reached"):
            errors.append("%s: claims certified links — the stub has no certified "
                          "trail evidence and must stay honest" % entry_id)
    return errors


def self_test():
    report = build_report()
    errors = validate_report(report)
    # Red-first: a dishonest mutation must be caught.
    forged = json.loads(json.dumps(report))
    for state in forged["entries"][0]["states"]:
        if state["state"] == "occurrence_links_certified":
            state["reached"] = True
            state["evidence"] = [_ev("wish:thinking", "aspiration")]
    if not validate_report(forged):
        errors.append("red-first: forged certified claim was not detected")
    forged2 = json.loads(json.dumps(report))
    forged2["entries"][0]["states"][2]["reached"] = True
    forged2["entries"][0]["states"][2].pop("evidence", None)
    if not validate_report(forged2):
        errors.append("red-first: reached-without-evidence was not detected")
    if errors:
        print("ENTRY COMPLETION SELF-TEST FAIL")
        for item in errors[:10]:
            print("  -", item)
        return 1
    print("ENTRY COMPLETION SELF-TEST PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    report = build_report()
    errors = validate_report(report)
    if errors:
        print("ENTRY COMPLETION STATE FAIL")
        for item in errors[:10]:
            print("  -", item)
        return 1
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print("ENTRY COMPLETION STATE PASS (%d entries -> %s)"
          % (len(report["entries"]), os.path.relpath(args.output, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
