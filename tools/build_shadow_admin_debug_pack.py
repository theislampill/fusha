#!/usr/bin/env python3
"""Build a read-only static admin/debug pack from a Qamus shadow graph.

The pack is deliberately static and local: it consumes existing shadow outputs
and writes review artifacts only. It does not discover live paths, rebuild WBW,
start services, or apply hover/entry changes.
"""

import argparse
import html
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict


PHASE3_VIEWS = {
    "hover_inspector",
    "entry_backlinks",
    "parse_family_view",
    "blocker_queue",
    "repair_preview",
    "rich_hover_preview",
}

PUBLIC_BOUNDARY = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "internal_provenance_public": False,
    "external_source_names_public": False,
    "public_fields": ["gloss", "src", "kind", "lang"],
    "private_fields": ["internal_evidence", "adapter_labels", "reviewer_notes"],
}


def load_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise SystemExit("%s:%d invalid JSON: %s" % (path, line_no, exc))
    return rows


def load_jsonl_by_id(path):
    rows = load_jsonl(path)
    return {row.get("id"): row for row in rows if row.get("id")}, rows


def dump_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def rel_file(shadow_dir, name):
    path = os.path.join(shadow_dir, name)
    if not os.path.exists(path):
        raise SystemExit("missing shadow artifact: %s" % path)
    return path


def normalize_quran_loc(value):
    if value.startswith("quran:"):
        return value
    if re.match(r"^\d{1,3}:\d{1,3}:\d{1,3}$", value):
        return "quran:%s" % value
    raise SystemExit("expected quran:S:A:W or S:A:W, got %s" % value)


def wbw_from_quran(quran_loc):
    return "wbw:%s" % quran_loc.split(":", 1)[1]


def ensure_safe_out_dir(out_dir, shadow_dir):
    out_abs = os.path.abspath(out_dir)
    shadow_abs = os.path.abspath(shadow_dir)
    if out_abs == shadow_abs:
        raise SystemExit("refusing to write admin debug pack over shadow graph directory")
    if out_abs.startswith(shadow_abs + os.sep):
        raise SystemExit("refusing to write admin debug pack inside shadow graph directory")
    dangerous_bits = ("\\qamus-service\\entries", "\\qamus_wbw\\build", "\\public", "\\www", "\\public_html")
    lowered = out_abs.lower()
    if any(bit in lowered for bit in dangerous_bits) or lowered.startswith("/srv/"):
        raise SystemExit("refusing likely live/runtime output path: %s" % out_dir)
    os.makedirs(out_abs, exist_ok=True)


def index_parse_rows(parse_rows):
    parse_by_id = {}
    parse_by_token = {}
    entry_to_parse = defaultdict(set)
    entry_to_tokens = defaultdict(set)
    component_entry_to_parse = defaultdict(set)
    component_entry_to_tokens = defaultdict(set)
    for row in parse_rows:
        parse_by_id[row.get("id")] = row
        seen_locs = row.get("seen_locs") or []
        for loc in seen_locs:
            parse_by_token[loc] = row
        entries = set(row.get("candidate_entries") or [])
        parse_obj = row.get("canonical_parse_object") or {}
        if parse_obj.get("resolved_qamus_entry_id"):
            entries.add(parse_obj["resolved_qamus_entry_id"])
        for entry in entries:
            entry_to_parse[entry].add(row.get("id"))
            for loc in seen_locs:
                entry_to_tokens[entry].add(loc)
        for entry in row.get("component_candidate_entries") or []:
            component_entry_to_parse[entry].add(row.get("id"))
            for loc in seen_locs:
                component_entry_to_tokens[entry].add(loc)
    return (
        parse_by_id,
        parse_by_token,
        entry_to_parse,
        entry_to_tokens,
        component_entry_to_parse,
        component_entry_to_tokens,
    )


def decision_indexes(decisions):
    by_quran = defaultdict(list)
    by_wbw = defaultdict(list)
    by_parse = defaultdict(list)
    for row in decisions:
        if row.get("quran_loc"):
            by_quran[row["quran_loc"]].append(row)
        if row.get("wbw_loc"):
            by_wbw[row["wbw_loc"]].append(row)
        if row.get("parse_id"):
            by_parse[row["parse_id"]].append(row)
    return by_quran, by_wbw, by_parse


def entry_candidates_from_parse(parse_row):
    parse_obj = parse_row.get("canonical_parse_object") or {}
    return {
        "whole_token_candidates": parse_row.get("candidate_entries") or [],
        "component_candidates": parse_row.get("component_candidate_entries") or [],
        "component_candidate_joins": parse_row.get("component_candidate_join_statuses") or [],
        "raw_whole_token_candidates": parse_obj.get("qamus_entry_candidates") or [],
        "raw_component_candidates": parse_obj.get("qamus_component_candidates") or [],
    }


def build_hover_inspector(quran_loc, token_by_id, hover_by_id, parse_by_token, decisions_by_quran):
    quran_id = normalize_quran_loc(quran_loc)
    wbw_id = wbw_from_quran(quran_id)
    token = token_by_id.get(quran_id)
    hover = hover_by_id.get(wbw_id)
    parse_row = parse_by_token.get(quran_id)
    decisions = decisions_by_quran.get(quran_id, [])
    parse_obj = (parse_row or {}).get("canonical_parse_object") or {}
    gates = (parse_row or {}).get("gates") or []
    family_class = (parse_row or {}).get("family_class")
    family_size = (parse_row or {}).get("family_size", 0)
    propagation_allowed = bool((parse_row or {}).get("propagation_allowed"))
    return {
        "view": "hover_inspector",
        "public_exposable": False,
        "quran_loc": quran_id,
        "wbw_loc": wbw_id,
        "surface": (token or hover or parse_obj).get("surface") or parse_obj.get("surface_raw"),
        "status": (token or {}).get("status") or (hover or {}).get("status"),
        "current_visible_hover": decisions[-1].get("gloss") if decisions else None,
        "parse_id": (parse_row or {}).get("id"),
        "parse_key_family_size": family_size,
        "family_class": family_class,
        "gate": parse_obj.get("gate"),
        "gates": gates,
        "propagation_allowed": propagation_allowed,
        "blocker": (token or {}).get("blocker") or parse_obj.get("blocker"),
        "grammar_triggers": parse_obj.get("grammar_triggers") or [],
        "token_internal_segments": parse_obj.get("token_internal_segments") or [],
        "entry_candidates": entry_candidates_from_parse(parse_row or {}),
        "decision_ids": [row.get("id") for row in decisions],
        "public_boundary": PUBLIC_BOUNDARY,
        "edit_scopes": {
            "token_only": {
                "allowed_for_preview": True,
                "affected_token_count": 1,
                "required_gate": "token_review",
            },
            "parse_key_family": {
                "allowed_for_preview": True,
                "affected_token_count": family_size,
                "required_gate": "auto_safe_after_preview" if propagation_allowed else (gates[0] if gates else "human_review_required"),
                "family_propagation_allowed": propagation_allowed,
            },
        },
    }


def build_entry_view(entry_id, entry_by_id, entry_to_parse, entry_to_tokens, parse_by_id, decisions_by_parse, max_samples):
    entry = entry_by_id.get(entry_id, {})
    token_locs = sorted(entry_to_tokens.get(entry_id, set()))
    parse_ids = sorted(pid for pid in entry_to_parse.get(entry_id, set()) if pid)
    gate_counts = Counter()
    blocker_counts = Counter()
    dependent_hovers = []
    for parse_id in parse_ids:
        parse_row = parse_by_id.get(parse_id) or {}
        gate_counts.update(parse_row.get("gates") or [])
        for blocker in parse_row.get("blockers") or []:
            blocker_counts[blocker] += 1
        for loc in parse_row.get("seen_locs") or []:
            dependent_hovers.append(wbw_from_quran(loc))
    return {
        "view": "entry_backlinks",
        "public_exposable": False,
        "entry_id": entry_id,
        "candidate_scope": "whole_token_or_resolved_entry",
        "headword": entry.get("headword"),
        "section": entry.get("section"),
        "dependent_token_count": len(token_locs),
        "dependent_hover_count": len(set(dependent_hovers)),
        "parse_key_count": len(parse_ids),
        "gate_counts": dict(sorted(gate_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "sample_tokens": token_locs[:max_samples],
        "sample_hover_slots": sorted(set(dependent_hovers))[:max_samples],
        "sample_parse_keys": parse_ids[:max_samples],
        "repair_preview_stub": {
            "scope": "entry_sense",
            "live_mutation_allowed": False,
            "required_before_apply": True,
            "affected_token_count": len(token_locs),
            "affected_hover_count": len(set(dependent_hovers)),
            "rollback_strategy": "no_apply_preview_only",
        },
        "public_boundary": PUBLIC_BOUNDARY,
    }


def build_parse_family_view(parse_row, decisions_by_parse, max_samples):
    parse_obj = parse_row.get("canonical_parse_object") or {}
    seen = parse_row.get("seen_locs") or []
    return {
        "view": "parse_family_view",
        "public_exposable": False,
        "parse_id": parse_row.get("id"),
        "family_size": parse_row.get("family_size"),
        "family_class": parse_row.get("family_class"),
        "propagation_allowed": parse_row.get("propagation_allowed"),
        "gates": parse_row.get("gates") or [],
        "surface": parse_obj.get("surface_raw"),
        "norm_strict": parse_obj.get("norm_strict"),
        "grammar_triggers": parse_obj.get("grammar_triggers") or [],
        "candidate_entries": parse_row.get("candidate_entries") or [],
        "component_candidate_entries": parse_row.get("component_candidate_entries") or [],
        "seen_locs_sample": seen[:max_samples],
        "hover_slots_sample": [wbw_from_quran(loc) for loc in seen[:max_samples]],
        "decision_ids": [row.get("id") for row in decisions_by_parse.get(parse_row.get("id"), [])],
        "public_boundary": PUBLIC_BOUNDARY,
    }


def build_blocker_queue(blocker_rows, token_by_id, parse_by_token, max_blockers, max_samples):
    queues = []
    for row in blocker_rows[:max_blockers]:
        tokens = row.get("tokens") or []
        parse_ids = Counter()
        pos_counts = Counter()
        for token in tokens:
            parse_row = parse_by_token.get(token) or {}
            parse_ids[parse_row.get("id")] += 1
            parse_obj = parse_row.get("canonical_parse_object") or {}
            pos_counts[parse_obj.get("pos") or "unknown"] += 1
        queues.append({
            "blocker": row.get("id"),
            "count": row.get("count"),
            "sample_tokens": tokens[:max_samples],
            "sample_surfaces": [(token_by_id.get(tok) or {}).get("surface") for tok in tokens[:max_samples]],
            "parse_key_count": len([pid for pid in parse_ids if pid]),
            "pos_counts": dict(sorted(pos_counts.items())),
            "public_exposable": False,
        })
    return {
        "view": "blocker_queue",
        "public_exposable": False,
        "blocker_classes": queues,
        "public_boundary": PUBLIC_BOUNDARY,
    }


def render_html(pack):
    rows = []
    rows.append("<!doctype html><meta charset='utf-8'><title>Qamus Shadow Admin Debug Pack</title>")
    rows.append("<style>body{font-family:system-ui,sans-serif;margin:2rem;line-height:1.45}pre{background:#111827;color:#f9fafb;padding:1rem;overflow:auto}code{background:#eef2ff;padding:.1rem .25rem}</style>")
    rows.append("<h1>Qamus Shadow Admin Debug Pack</h1>")
    rows.append("<p>Read-only scaffold. No live mutation allowed.</p>")
    rows.append("<ul>")
    for view in sorted(PHASE3_VIEWS):
        rows.append("<li><code>%s</code></li>" % html.escape(view))
    rows.append("</ul>")
    rows.append("<h2>Summary</h2>")
    rows.append("<pre>%s</pre>" % html.escape(json.dumps(pack.get("summary"), ensure_ascii=False, indent=2, sort_keys=True)))
    rows.append("<h2>Token Inspectors</h2>")
    for item in pack.get("hover_inspectors", []):
        rows.append("<h3>%s</h3><pre>%s</pre>" % (
            html.escape(item.get("quran_loc") or ""),
            html.escape(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True)),
        ))
    rows.append("<h2>Entry Backlinks</h2>")
    for item in pack.get("entry_backlinks", []):
        rows.append("<h3>%s</h3><pre>%s</pre>" % (
            html.escape(item.get("entry_id") or ""),
            html.escape(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True)),
        ))
    rows.append("<h2>Parse Families</h2>")
    for item in pack.get("parse_family_views", []):
        rows.append("<h3>%s</h3><pre>%s</pre>" % (
            html.escape(item.get("parse_id") or ""),
            html.escape(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True)),
        ))
    rows.append("<h2>Blocker Queue</h2><pre>%s</pre>" % html.escape(json.dumps(pack.get("blocker_queue"), ensure_ascii=False, indent=2, sort_keys=True)))
    return "\n".join(rows) + "\n"


def build_pack(shadow_dir, out_dir, sample_tokens=None, sample_entries=None, max_samples=12, max_blockers=20):
    ensure_safe_out_dir(out_dir, shadow_dir)
    token_by_id, token_rows = load_jsonl_by_id(rel_file(shadow_dir, "token-index.jsonl"))
    hover_by_id, hover_rows = load_jsonl_by_id(rel_file(shadow_dir, "hover-index.jsonl"))
    entry_by_id, entry_rows = load_jsonl_by_id(rel_file(shadow_dir, "entry-index.jsonl"))
    decision_rows = load_jsonl(rel_file(shadow_dir, "decision-index.jsonl"))
    parse_rows = load_jsonl(rel_file(shadow_dir, "parse-keys.jsonl"))
    blocker_rows = load_jsonl(rel_file(shadow_dir, "blocker-index.jsonl"))
    (
        parse_by_id,
        parse_by_token,
        entry_to_parse,
        entry_to_tokens,
        _component_entry_to_parse,
        _component_entry_to_tokens,
    ) = index_parse_rows(parse_rows)
    decisions_by_quran, _decisions_by_wbw, decisions_by_parse = decision_indexes(decision_rows)

    if not sample_tokens:
        sample_tokens = ["quran:33:63:1", "quran:22:18:17", "quran:2:21:1"]
    sample_tokens = [normalize_quran_loc(token) for token in sample_tokens]
    hover_inspectors = []
    inspected_tokens = set()

    def add_hover_inspector(token):
        token = normalize_quran_loc(token)
        if token in inspected_tokens:
            return
        hover_inspectors.append(
            build_hover_inspector(token, token_by_id, hover_by_id, parse_by_token, decisions_by_quran)
        )
        inspected_tokens.add(token)

    for token in sample_tokens:
        add_hover_inspector(token)

    inferred_entries = []
    for inspector in hover_inspectors:
        candidates = inspector.get("entry_candidates") or {}
        inferred_entries.extend(candidates.get("whole_token_candidates") or [])
    entry_ids = list(dict.fromkeys((sample_entries or []) + inferred_entries))
    entry_backlinks = [
        build_entry_view(entry_id, entry_by_id, entry_to_parse, entry_to_tokens, parse_by_id, decisions_by_parse, max_samples)
        for entry_id in entry_ids[:max_samples * 2]
    ]
    # Entry/sense repair previews need a complete exact-address chain for the
    # sample blast-radius tokens, not just the initially requested examples.
    for entry in entry_backlinks:
        for token in entry.get("sample_tokens") or []:
            add_hover_inspector(token)

    parse_family_views = []
    seen_parse_ids = set()
    for inspector in hover_inspectors:
        parse_id = inspector.get("parse_id")
        if parse_id and parse_id in parse_by_id and parse_id not in seen_parse_ids:
            parse_family_views.append(build_parse_family_view(parse_by_id[parse_id], decisions_by_parse, max_samples))
            seen_parse_ids.add(parse_id)

    blocker_queue = build_blocker_queue(blocker_rows, token_by_id, parse_by_token, max_blockers, max_samples)
    pack = {
        "version": "qamus-shadow-admin-debug-pack@1",
        "public_exposable": False,
        "live_mutation_allowed": False,
        "source_shadow_dir": os.path.abspath(shadow_dir),
        "views": sorted(PHASE3_VIEWS),
        "summary": {
            "token_rows": len(token_rows),
            "hover_rows": len(hover_rows),
            "entry_rows": len(entry_rows),
            "decision_rows": len(decision_rows),
            "parse_rows": len(parse_rows),
            "blocker_classes": len(blocker_rows),
            "sample_token_count": len(sample_tokens),
            "sample_entry_count": len(entry_backlinks),
        },
        "hover_inspectors": hover_inspectors,
        "entry_backlinks": entry_backlinks,
        "parse_family_views": parse_family_views,
        "blocker_queue": blocker_queue,
        "public_boundary": PUBLIC_BOUNDARY,
    }
    dump_json(os.path.join(out_dir, "admin-debug-pack.json"), pack)
    with io.open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_html(pack))
    return pack


def self_test():
    with tempfile.TemporaryDirectory(prefix="shadow-admin-debug-") as td:
        shadow = os.path.join(td, "shadow")
        out = os.path.join(td, "out")
        os.makedirs(shadow)
        def wjsonl(name, rows):
            with io.open(os.path.join(shadow, name), "w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        wjsonl("token-index.jsonl", [
            {"id": "quran:33:63:1", "loc": "33:63:1", "surface": "يَسْأَلُكَ", "status": "resolved", "parse_id": "parse:ask"},
        ])
        wjsonl("hover-index.jsonl", [
            {"id": "wbw:33:63:1", "loc": "33:63:1", "surface": "يَسْأَلُكَ", "status": "resolved"},
        ])
        wjsonl("entry-index.jsonl", [
            {"id": "qamus:v:ask", "entry_id": "ask", "headword": "سَأَلَ", "section": "verb"},
        ])
        wjsonl("decision-index.jsonl", [
            {"id": "decision:tok:33:63:1", "quran_loc": "quran:33:63:1", "wbw_loc": "wbw:33:63:1", "parse_id": "parse:ask", "gloss": "ask you"},
        ])
        wjsonl("parse-keys.jsonl", [
            {
                "id": "parse:ask",
                "family_size": 1,
                "family_class": "two_vote_required",
                "gates": ["two_vote_required"],
                "candidate_entries": ["qamus:v:ask"],
                "component_candidate_entries": ["qamus:p:kaf"],
                "seen_locs": ["quran:33:63:1"],
                "propagation_allowed": False,
                "canonical_parse_object": {
                    "surface_raw": "يَسْأَلُكَ",
                    "norm_strict": "يسالك",
                    "gate": "two_vote_required",
                    "grammar_triggers": ["suffix_pronoun"],
                    "token_internal_segments": [
                        {"role": "imperfect_prefix", "surface": "يَ"},
                        {"role": "verb_stem", "surface": "سْأَلُ"},
                        {"role": "object_pronoun", "surface": "كَ"},
                    ],
                    "qamus_entry_candidates": [{"entry_address": "qamus:v:ask"}],
                    "qamus_component_candidates": [{"entry_address": "qamus:p:kaf", "source": "rich_wbw_segment"}],
                },
            }
        ])
        wjsonl("blocker-index.jsonl", [{"id": "blocker:suffix", "count": 1, "tokens": ["quran:33:63:1"]}])
        pack = build_pack(shadow, out, sample_tokens=["33:63:1"])
        if not os.path.exists(os.path.join(out, "index.html")):
            print("SELF-TEST FAIL: missing index.html")
            return 1
        if not os.path.exists(os.path.join(out, "admin-debug-pack.json")):
            print("SELF-TEST FAIL: missing admin-debug-pack.json")
            return 1
        if not PHASE3_VIEWS.issubset(set(pack.get("views") or [])):
            print("SELF-TEST FAIL: missing views")
            return 1
        inspector = pack["hover_inspectors"][0]
        if inspector["quran_loc"] != "quran:33:63:1" or inspector["wbw_loc"] != "wbw:33:63:1":
            print("SELF-TEST FAIL: identity chain broken")
            return 1
        if inspector["edit_scopes"]["parse_key_family"]["family_propagation_allowed"]:
            print("SELF-TEST FAIL: two-vote parse family should not propagate")
            return 1
        if any(item.get("entry_id") == "qamus:p:kaf" for item in pack.get("entry_backlinks") or []):
            print("SELF-TEST FAIL: component candidate leaked into entry backlinks")
            return 1
        if pack["entry_backlinks"][0].get("candidate_scope") != "whole_token_or_resolved_entry":
            print("SELF-TEST FAIL: entry backlink scope missing")
            return 1
        if pack.get("live_mutation_allowed"):
            print("SELF-TEST FAIL: pack permits live mutation")
            return 1
    print("PASS — shadow admin debug pack self-test")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-dir")
    parser.add_argument("--out-dir")
    parser.add_argument("--sample-token", action="append", default=[])
    parser.add_argument("--sample-entry", action="append", default=[])
    parser.add_argument("--max-samples", type=int, default=12)
    parser.add_argument("--max-blockers", type=int, default=20)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.shadow_dir or not args.out_dir:
        raise SystemExit("provide --shadow-dir and --out-dir")
    pack = build_pack(
        args.shadow_dir,
        args.out_dir,
        sample_tokens=args.sample_token,
        sample_entries=args.sample_entry,
        max_samples=args.max_samples,
        max_blockers=args.max_blockers,
    )
    print(json.dumps(pack["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
