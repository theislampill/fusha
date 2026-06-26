#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query a read-only Qamus shadow admin/debug pack.

This is the Phase 3 CLI counterpart to the static admin/debug scaffold. It
answers exact-address traces from an already-built pack; it does not discover
live paths, rebuild artifacts, or apply edits.
"""
import argparse
import io
import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "shadow_admin_debug_pack.sample.json")
QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE = re.compile(r"^parse:")


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dump(obj):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def wbw_from_quran(quran_loc):
    return "wbw:%s" % quran_loc.split(":", 1)[1]


def quran_from_wbw(wbw_loc):
    return "quran:%s" % wbw_loc.split(":", 1)[1]


def normalize_token(value):
    if QURAN.match(value):
        return value
    if WBW.match(value):
        return quran_from_wbw(value)
    if re.match(r"^\d{1,3}:\d{1,3}:\d{1,3}$", value):
        return "quran:%s" % value
    raise SystemExit("expected quran:S:A:W, wbw:S:A:W, or S:A:W; got %s" % value)


def build_indexes(pack):
    inspectors_by_quran = {}
    inspectors_by_wbw = {}
    entries_by_id = {}
    parses_by_id = {}
    parse_to_entries = {}
    parse_to_inspectors = {}

    for row in pack.get("hover_inspectors") or []:
        if row.get("quran_loc"):
            inspectors_by_quran[row["quran_loc"]] = row
        if row.get("wbw_loc"):
            inspectors_by_wbw[row["wbw_loc"]] = row
        parse_id = row.get("parse_id")
        if parse_id:
            parse_to_inspectors.setdefault(parse_id, []).append(row)

    for row in pack.get("entry_backlinks") or []:
        if row.get("entry_id"):
            entries_by_id[row["entry_id"]] = row
        for parse_id in row.get("sample_parse_keys") or []:
            parse_to_entries.setdefault(parse_id, set()).add(row.get("entry_id"))

    for row in pack.get("parse_family_views") or []:
        if row.get("parse_id"):
            parses_by_id[row["parse_id"]] = row
            for entry_id in (row.get("candidate_entries") or []) + (row.get("component_candidate_entries") or []):
                parse_to_entries.setdefault(row["parse_id"], set()).add(entry_id)

    return {
        "inspectors_by_quran": inspectors_by_quran,
        "inspectors_by_wbw": inspectors_by_wbw,
        "entries_by_id": entries_by_id,
        "parses_by_id": parses_by_id,
        "parse_to_entries": parse_to_entries,
        "parse_to_inspectors": parse_to_inspectors,
    }


def public_boundary(pack):
    return pack.get("public_boundary") or {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "external_source_names_public": False,
        "internal_provenance_public": False,
    }


def reverse_trace(pack, token):
    indexes = build_indexes(pack)
    quran_loc = normalize_token(token)
    wbw_loc = wbw_from_quran(quran_loc)
    inspector = indexes["inspectors_by_quran"].get(quran_loc) or indexes["inspectors_by_wbw"].get(wbw_loc)
    if not inspector:
        raise SystemExit("token not present in pack: %s" % token)
    parse_id = inspector.get("parse_id")
    parse_view = indexes["parses_by_id"].get(parse_id)
    candidate_entry_ids = []
    candidates = inspector.get("entry_candidates") or {}
    candidate_entry_ids.extend(candidates.get("whole_token_candidates") or [])
    candidate_entry_ids.extend(candidates.get("component_candidates") or [])
    if parse_id in indexes["parse_to_entries"]:
        candidate_entry_ids.extend(sorted(indexes["parse_to_entries"][parse_id]))
    seen = set()
    entries = []
    for entry_id in candidate_entry_ids:
        if not entry_id or entry_id in seen:
            continue
        seen.add(entry_id)
        row = indexes["entries_by_id"].get(entry_id)
        entries.append(row or {"entry_id": entry_id, "status": "candidate_not_in_sample_pack"})
    family = parse_view or {}
    return {
        "trace": "hover_slot_to_token_to_parse_to_entry",
        "read_only": True,
        "live_mutation_allowed": False,
        "quran_loc": quran_loc,
        "wbw_loc": wbw_loc,
        "surface": inspector.get("surface"),
        "current_visible_hover": inspector.get("current_visible_hover"),
        "parse_id": parse_id,
        "decision_ids": inspector.get("decision_ids") or [],
        "gate": inspector.get("gate"),
        "gates": inspector.get("gates") or [],
        "propagation_allowed": inspector.get("propagation_allowed"),
        "grammar_triggers": inspector.get("grammar_triggers") or [],
        "token_internal_segments": inspector.get("token_internal_segments") or [],
        "entry_candidates": entries,
        "parse_family": {
            "family_size": family.get("family_size"),
            "family_class": family.get("family_class"),
            "seen_locs_sample": family.get("seen_locs_sample") or [],
            "hover_slots_sample": family.get("hover_slots_sample") or [],
            "candidate_entries": family.get("candidate_entries") or [],
            "component_candidate_entries": family.get("component_candidate_entries") or [],
            "propagation_allowed": family.get("propagation_allowed"),
        },
        "edit_scopes": inspector.get("edit_scopes") or {},
        "public_boundary": public_boundary(pack),
    }


def forward_trace(pack, entry_id):
    indexes = build_indexes(pack)
    if not str(entry_id).startswith("qamus:"):
        raise SystemExit("entry must start with qamus:<id>; got %s" % entry_id)
    entry = indexes["entries_by_id"].get(entry_id)
    if not entry:
        # The pack may include a parse-family candidate not expanded into an entry
        # backlinks sample. Keep that distinction explicit for future UI.
        candidate_parses = [
            parse_id for parse_id, entry_ids in indexes["parse_to_entries"].items()
            if entry_id in entry_ids
        ]
        if not candidate_parses:
            raise SystemExit("entry not present in pack: %s" % entry_id)
        entry = {"entry_id": entry_id, "status": "candidate_not_in_sample_pack", "sample_parse_keys": candidate_parses}
    parse_ids = entry.get("sample_parse_keys") or []
    parse_views = [indexes["parses_by_id"].get(parse_id) for parse_id in parse_ids if indexes["parses_by_id"].get(parse_id)]
    token_locs = list(entry.get("sample_tokens") or [])
    hover_slots = list(entry.get("sample_hover_slots") or [])
    for parse_view in parse_views:
        for loc in parse_view.get("seen_locs_sample") or []:
            if loc not in token_locs:
                token_locs.append(loc)
        for loc in parse_view.get("hover_slots_sample") or []:
            if loc not in hover_slots:
                hover_slots.append(loc)
    inspectors = [
        indexes["inspectors_by_quran"].get(loc)
        for loc in token_locs
        if indexes["inspectors_by_quran"].get(loc)
    ]
    return {
        "trace": "entry_to_tokens_to_parse_to_decisions_to_hover_slots",
        "read_only": True,
        "live_mutation_allowed": False,
        "entry": entry,
        "dependent_token_locations": token_locs,
        "dependent_hover_slots": hover_slots,
        "parse_families": parse_views,
        "hover_inspectors": inspectors,
        "public_boundary": public_boundary(pack),
    }


def parse_trace(pack, parse_id):
    if not PARSE.match(parse_id):
        raise SystemExit("parse id must start with parse:<id>")
    indexes = build_indexes(pack)
    parse_view = indexes["parses_by_id"].get(parse_id)
    if not parse_view:
        raise SystemExit("parse not present in pack: %s" % parse_id)
    entries = []
    for entry_id in sorted(indexes["parse_to_entries"].get(parse_id, set())):
        entries.append(indexes["entries_by_id"].get(entry_id) or {"entry_id": entry_id, "status": "candidate_not_in_sample_pack"})
    return {
        "trace": "parse_to_family_to_entries_to_hover_slots",
        "read_only": True,
        "live_mutation_allowed": False,
        "parse_family": parse_view,
        "entries": entries,
        "hover_inspectors": indexes["parse_to_inspectors"].get(parse_id, []),
        "public_boundary": public_boundary(pack),
    }


def self_test():
    pack = load_json(SAMPLE)
    token_trace = reverse_trace(pack, "33:63:1")
    if token_trace["quran_loc"] != "quran:33:63:1" or token_trace["wbw_loc"] != "wbw:33:63:1":
        print("SELF-TEST FAIL: reverse token identity mismatch")
        return 1
    if token_trace["live_mutation_allowed"] is not False:
        print("SELF-TEST FAIL: reverse trace permits live mutation")
        return 1
    if token_trace["parse_family"]["propagation_allowed"] is not False:
        print("SELF-TEST FAIL: gated parse family should not propagate")
        return 1
    entry_trace = forward_trace(pack, "qamus:5935ecfb1ec5")
    if "quran:33:63:1" not in entry_trace["dependent_token_locations"]:
        print("SELF-TEST FAIL: forward trace missing token")
        return 1
    parse_trace_obj = parse_trace(pack, "parse:aaaaaaaa")
    if parse_trace_obj["parse_family"]["parse_id"] != "parse:aaaaaaaa":
        print("SELF-TEST FAIL: parse trace mismatch")
        return 1
    print("PASS — shadow admin debug pack query self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", default=SAMPLE, help="admin-debug-pack.json path")
    parser.add_argument("--token", help="quran:S:A:W, wbw:S:A:W, or S:A:W")
    parser.add_argument("--entry", help="qamus:<id>")
    parser.add_argument("--parse", dest="parse_id", help="parse:<id>")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    selected = [bool(args.token), bool(args.entry), bool(args.parse_id)]
    if sum(selected) != 1:
        parser.error("provide exactly one of --token, --entry, or --parse")
    pack = load_json(args.pack)
    if pack.get("live_mutation_allowed") is not False:
        raise SystemExit("refusing pack with live_mutation_allowed != false")
    if args.token:
        dump(reverse_trace(pack, args.token))
    elif args.entry:
        dump(forward_trace(pack, args.entry))
    else:
        dump(parse_trace(pack, args.parse_id))


if __name__ == "__main__":
    main()
