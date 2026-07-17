#!/usr/bin/env python3
"""Deterministic validators for the qamus typed-edge graph bundle."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_typed_edge_crosswalk import (
    EDGE_TYPE_SET,
    NODE_TYPE_SET,
    SCHEMA,
    STATUS_SET,
    _card_id_for_row,
    _entry_indexes,
    _entry_id,
    _loc_from_row,
    _text,
    bare,
    entry_node,
    occurrence_node,
    read_jsonl,
    _selected_id_for_row,
)


CHECK_NAMES = [
    "no_page_context_to_lexeme_promotion",
    "selected_word_exact_card_backlink",
    "certified_occurrence_reverse_entry_reciprocity",
    "form_edges_cite_documented_evidence",
    "sense_edges_cite_sense_identity",
    "ambiguous_duplicate_surface_abstention",
    "display_local_exact_canonical_surface",
    "canonical_correction_reaches_repeated_appearances",
    "no_orphaned_typed_fact_or_projection",
    "exact_reconstruction_valid",
]


def _edge_list(bundle):
    return list(bundle.get("edges") or [])


def _is_node_id(value: str) -> bool:
    return isinstance(value, str) and value.split(":", 1)[0] in NODE_TYPE_SET and ":" in value


def _run_check(name, function):
    errors = []
    try:
        function(errors)
    except Exception as exc:  # validators report malformed data instead of crashing
        errors.append(f"{name}: validator error: {exc}")
    return {"name": name, "ok": not errors, "errors": errors}


def validate_graph(bundle, entries, ledger_rows, whitelist_rows, appearance_rows, fact_rows):
    """Run the ten named checks and return a JSON-serializable report."""

    edges = _edge_list(bundle)
    _, exact, _, _ = _entry_indexes(list(entries or []))
    page_pairs = set()
    page_entry_ids = set()
    source_surface = {}
    for row in whitelist_rows or []:
        loc = _text(row.get("loc") or row.get("quran_loc"))
        entry_id = _entry_id(row.get("entry_id"))
        if loc and entry_id:
            page_pairs.add((loc, entry_node(entry_id)))
            page_entry_ids.add(entry_node(entry_id))
        if loc and _text(row.get("surface")):
            source_surface[loc] = _text(row.get("surface"))

    checks = []

    def check_page_context(errors):
        for item in edges:
            if item.get("schema") != SCHEMA:
                errors.append(f"invalid edge schema: {item.get('edge_id')}")
            if item.get("edge_type") not in EDGE_TYPE_SET:
                errors.append(f"unknown edge type: {item.get('edge_id')}")
            if item.get("status") not in STATUS_SET:
                errors.append(f"unknown edge status: {item.get('edge_id')}")
            if not _is_node_id(item.get("from_node_id")) or not _is_node_id(item.get("to_node_id")):
                errors.append(f"untyped edge endpoint: {item.get('edge_id')}")
            if item.get("edge_type") != "lexeme_entry_edge":
                continue
            details = item.get("details") or {}
            if details.get("page_context_only") or details.get("page_context_origin"):
                errors.append(f"page-context edge promoted to lexeme: {item.get('edge_id')}")
            if item.get("from_node_type") == "occurrence":
                loc = item["from_node_id"].split(":", 1)[1]
                if (loc, item.get("to_node_id")) in page_pairs:
                    errors.append(f"page-context occurrence consumed as lexeme: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[0], check_page_context))

    def check_cards(errors):
        source_edges = {
            item["from_node_id"]: item
            for item in edges
            if item.get("edge_type") == "source_card_edge"
        }
        for row in ledger_rows or []:
            entry_id = _entry_id(row.get("entry_id"))
            if not entry_id:
                errors.append("selected word has no source entry id")
                continue
            selected_id = _selected_id_for_row(row)
            edge = source_edges.get(selected_id)
            expected = _card_id_for_row(row, entry_id, int(row.get("usage_index") or 1))
            if not edge or edge.get("to_node_id") != expected:
                errors.append(f"selected word missing exact card backlink: {selected_id}")

    checks.append(_run_check(CHECK_NAMES[1], check_cards))

    def check_reverse(errors):
        reverse = {entry_node(item.get("entry_id")): item for item in (bundle.get("reverse") or [])}
        for item in edges:
            if item.get("edge_type") != "lexeme_entry_edge" or item.get("status") != "certified":
                continue
            if item.get("from_node_type") != "occurrence":
                continue
            entry_record = reverse.get(item.get("to_node_id"))
            loc = item["from_node_id"].split(":", 1)[1]
            if not entry_record or loc not in set(entry_record.get("occurrence_ids") or []):
                errors.append(f"certified occurrence missing reverse entry backlink: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[2], check_reverse))

    def check_forms(errors):
        for item in edges:
            if item.get("edge_type") != "form_entry_edge":
                continue
            if item.get("status") in {"source_gap", "rejected"}:
                continue
            evidence = item.get("evidence") or []
            details = item.get("details") or {}
            if not evidence or not any(_text(ev.get("address")) for ev in evidence):
                errors.append(f"form edge lacks documented/source evidence: {item.get('edge_id')}")
            if not details.get("form_address") and not any(
                "entry:" in _text(ev.get("address")) or "source" in _text(ev.get("method"))
                for ev in evidence
            ):
                errors.append(f"form edge evidence is not a form/source address: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[3], check_forms))

    def check_senses(errors):
        for item in edges:
            if item.get("edge_type") != "sense_entry_edge":
                continue
            details = item.get("details") or {}
            sense_id = _text(details.get("sense_id"))
            if item.get("from_node_type") != "sense" or not sense_id or sense_id != item.get("from_node_id"):
                errors.append(f"sense edge lacks sense identity: {item.get('edge_id')}")
            if not item.get("evidence"):
                errors.append(f"sense edge lacks evidence: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[4], check_senses))

    def check_duplicates(errors):
        for item in edges:
            if item.get("edge_type") != "lexeme_entry_edge" or item.get("from_node_type") != "selected-word":
                continue
            details = item.get("details") or {}
            collision_set = details.get("collision_set") or []
            surface = _text(details.get("surface"))
            if not surface:
                continue
            collision_ids = {form["entry_id"] for form in exact.get(bare(surface), [])}
            if len(collision_ids) > 1 or len(collision_set) > 1:
                if item.get("status") != "ambiguous":
                    errors.append(f"duplicate surface promoted: {item.get('edge_id')}")
                if set(collision_set) != collision_ids and len(collision_ids) > 1:
                    errors.append(f"duplicate collision set incomplete: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[5], check_duplicates))

    def check_display(errors):
        for item in edges:
            if item.get("edge_type") != "display_local_to_canonical_crosswalk_edge":
                continue
            details = item.get("details") or {}
            loc = item.get("to_node_id", "").split(":", 1)[1] if item.get("to_node_type") == "occurrence" else ""
            expected = source_surface.get(loc)
            if item.get("status") not in {"source_gap", "rejected"}:
                if not details.get("exact_surface") or not _text(details.get("local_surface")):
                    errors.append(f"display-local edge is not exact: {item.get('edge_id')}")
                if expected and details.get("canonical_surface") != expected:
                    errors.append(f"display-local surface mismatch: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[6], check_display))

    def check_appearances(errors):
        rendered = defaultdict(list)
        for item in edges:
            if item.get("edge_type") == "rendered_appearance_edge":
                rendered[item.get("from_node_id")].append(item)
        for record in appearance_rows or []:
            loc = _text(record.get("loc"))
            occurrence = occurrence_node(loc)
            expected = record.get("appearances") or []
            actual = rendered.get(occurrence, [])
            if len(actual) != len(expected):
                errors.append(f"appearance propagation count mismatch: {loc}")
                continue
            expected_surface = _text(record.get("canonical_surface") or record.get("surface"))
            for item in actual:
                if expected_surface and (item.get("details") or {}).get("canonical_surface") != expected_surface:
                    errors.append(f"canonical correction did not propagate: {item.get('edge_id')}")
                if not _text((item.get("details") or {}).get("projection_hash")):
                    errors.append(f"appearance lacks projection hash: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[7], check_appearances))

    def check_orphans(errors):
        attached = {
            _text((item.get("details") or {}).get("fact_id"))
            for item in edges
            if item.get("edge_type") == "decision_evidence_edge"
        }
        for fact in fact_rows or []:
            fact_id = _text(fact.get("fact_id") or fact.get("id") or fact.get("fact_key"))
            if fact_id and fact_id not in attached:
                errors.append(f"orphaned typed fact or projection: {fact_id}")

    checks.append(_run_check(CHECK_NAMES[8], check_orphans))

    def check_reconstruction(errors):
        for item in edges:
            if item.get("edge_type") != "display_local_to_canonical_crosswalk_edge":
                continue
            if item.get("status") in {"source_gap", "rejected"}:
                continue
            details = item.get("details") or {}
            if details.get("reconstruction_exact") is not True:
                errors.append(f"exact reconstruction failed: {item.get('edge_id')}")

    checks.append(_run_check(CHECK_NAMES[9], check_reconstruction))
    errors = [error for check in checks for error in check["errors"]]
    return {"ok": not errors, "checks": checks, "errors": errors}


def _fixture_self_test() -> bool:
    fixture_dir = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "edges"
    entries = read_jsonl(fixture_dir / "entries.fixture.jsonl")
    ledger = read_jsonl(fixture_dir / "ledger.fixture.jsonl")
    whitelist = read_jsonl(fixture_dir / "whitelist.fixture.jsonl")
    appearances = read_jsonl(fixture_dir / "appearances.fixture.jsonl")
    facts = [row for row in read_jsonl(fixture_dir / "facts.fixture.jsonl") if row.get("fact_id") != "fact-orphan"]
    from tools.build_typed_edge_crosswalk import build_graph

    bundle = build_graph(
        entries=entries,
        ledger_rows=ledger,
        whitelist_rows=whitelist,
        appearance_rows=appearances,
        fact_rows=facts,
    )
    report = validate_graph(bundle, entries, ledger, whitelist, appearances, facts)
    if not report["ok"]:
        print("\n".join(report["errors"]))
        return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--graph")
    parser.add_argument("--forward")
    parser.add_argument("--reverse")
    parser.add_argument("--entries")
    parser.add_argument("--ledger")
    parser.add_argument("--whitelist")
    parser.add_argument("--appearances")
    parser.add_argument("--fact", action="append", default=[])
    args = parser.parse_args(argv)
    if args.self_test:
        if _fixture_self_test():
            print("TYPED EDGE GRAPH SELF-TEST PASS")
            return 0
        print("TYPED EDGE GRAPH SELF-TEST FAIL")
        return 1
    required = [args.graph, args.forward, args.reverse, args.entries, args.ledger, args.whitelist, args.appearances]
    if all(required):
        bundle = {
            "edges": read_jsonl(args.graph),
            "forward": read_jsonl(args.forward),
            "reverse": read_jsonl(args.reverse),
        }
        entries = read_jsonl(args.entries)
        ledger = read_jsonl(args.ledger)
        whitelist = read_jsonl(args.whitelist)
        appearances = read_jsonl(args.appearances)
        facts = []
        for path in args.fact:
            facts.extend(read_jsonl(path))
        report = validate_graph(bundle, entries, ledger, whitelist, appearances, facts)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["ok"] else 1
    parser.error("use --self-test or provide graph, projection, and source inputs")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
