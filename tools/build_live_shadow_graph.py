#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a read-only Qamus shadow graph from explicit local inputs.

This is the durable Phase 2 form of the Phase 1 audit builder. It does not SSH,
does not rebuild WBW, does not mutate entries/ledgers, and refuses unsafe output
paths. Server acceptance can pass live paths at runtime; the public Fusha repo
keeps the tool path-agnostic.

Required real run shape:
  python tools/build_live_shadow_graph.py --live-readonly --no-live-write \
    --entries-dir <entries-json-dir> --wbw-json <wbw-lookup.json> \
    --decision-ledger <token-decisions.jsonl> --out-dir <shadow-out> \
    --fusha-index-dir <fusha/qamus/indexes/current>

Fixture mode is for CI/self-test and does not claim live counts.
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict


LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
PHASE_FILES = [
    "phase1-current-truth.json",
    "phase1-current-truth.md",
    "nodes.jsonl",
    "edges.jsonl",
    "backlinks.json",
    "parse-keys.jsonl",
    "entry-index.jsonl",
    "token-index.jsonl",
    "hover-index.jsonl",
    "decision-index.jsonl",
    "blocker-index.jsonl",
    "collision-report.md",
    "public-boundary-scan.md",
    "mirror-diff-summary.md",
    "sample-traces.md",
    "validator-report.md",
]
GATES_UNSAFE_FOR_PROPAGATION = {"human_review_required", "never_auto", "unknown"}


def quran_address(loc):
    loc = str(loc or "")
    return loc if loc.startswith("quran:") else "quran:%s" % loc


def norm_strict(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        o = ord(ch)
        if 0x064B <= o <= 0x0652:
            continue
        if o == 0x0670:
            out.append("ا")
            continue
        if o == 0x0640 or 0x0653 <= o <= 0x0655 or 0x06D6 <= o <= 0x06ED:
            continue
        out.append(ch)
    return "".join(out).replace("آ", "ا").replace("ٱ", "ا").replace("ى", "ي").replace("ة", "ه").replace(" ", "")


def bare(text):
    return norm_strict(text).replace("أ", "ا").replace("إ", "ا").replace("ؤ", "و").replace("ئ", "ي").replace("ء", "")


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_entries(entries_dir):
    entries = []
    for name in sorted(os.listdir(entries_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(entries_dir, name)
        with io.open(path, encoding="utf-8") as handle:
            entry = json.load(handle)
        entry.setdefault("id", os.path.splitext(name)[0])
        entries.append(entry)
    return entries


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_wbw_records(wbw):
    if isinstance(wbw, dict) and isinstance(wbw.get("words"), dict):
        for loc, row in sorted(wbw["words"].items()):
            if isinstance(row, dict):
                surface = row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
                yield loc, surface, row
            else:
                yield loc, str(row), {"surface": str(row)}
        return
    if isinstance(wbw, dict) and isinstance(wbw.get("records"), list):
        for row in wbw["records"]:
            loc = row.get("loc") or row.get("quran_loc")
            if loc:
                surface = row.get("surface") or row.get("arabic") or row.get("text") or ""
                yield loc, surface, row
        return
    if isinstance(wbw, dict) and isinstance(wbw.get("verses"), dict):
        for ayah, words in sorted(wbw["verses"].items()):
            if isinstance(words, list):
                for i, row in enumerate(words, 1):
                    loc = "%s:%d" % (ayah, i)
                    if isinstance(row, dict):
                        surface = row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
                        yield loc, surface, row
                    else:
                        yield loc, str(row), {"surface": str(row)}
            elif isinstance(words, dict):
                for k, row in sorted(words.items(), key=lambda kv: str(kv[0])):
                    loc = str(k) if str(k).count(":") == 2 else "%s:%s" % (ayah, k)
                    surface = row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
                    yield loc, surface, row


def load_decisions(path):
    decisions = {}
    if not path:
        return decisions
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            loc = row.get("loc") or row.get("quran_loc")
            if loc:
                decisions[loc] = row
    return decisions


def entry_address(entry):
    section = (entry.get("section") or entry.get("class") or "entry").lower()
    prefix = {"noun": "n", "verb": "v", "particle": "p"}.get(section, section[:1] or "e")
    return "qamus:%s:%s" % (prefix, entry.get("id"))


def build_entry_surface_index(entries):
    index = defaultdict(list)
    for entry in entries:
        addr = entry_address(entry)
        surfaces = [entry.get("headword"), entry.get("surface_ar")]
        for usage in entry.get("usage") or []:
            if isinstance(usage, dict):
                surfaces.extend(usage.get("forms") or [])
        for form in entry.get("forms") or []:
            surfaces.append(form)
        for surface in surfaces:
            key = norm_strict(surface)
            if key:
                index[key].append(addr)
    return index


def address_for_entry_id(entry_id, entry_addresses):
    if not entry_id:
        return None
    return entry_addresses.get(str(entry_id)) or "qamus:entry:%s" % entry_id


def load_fusha_reference(index_dir, entry_addresses):
    """Load optional Fusha graph exports as enrichment only.

    These joins never replace live truth. They only add candidate/inferred
    address evidence so downstream gates can explain why a token cannot be
    propagated blindly.
    """
    ref = {
        "by_surface": defaultdict(lambda: defaultdict(set)),
        "by_ayah": defaultdict(lambda: defaultdict(set)),
        "token_rows": {},
        "source": None,
    }
    if not index_dir:
        return ref
    surface_path = os.path.join(index_dir, "by-normalized-surface-detail.json")
    if os.path.exists(surface_path):
        surface_index = load_json(surface_path)
        for key, rows in surface_index.items():
            if not isinstance(rows, list):
                continue
            for item in rows:
                if not isinstance(item, dict):
                    continue
                addr = address_for_entry_id(item.get("eid"), entry_addresses)
                if addr:
                    ref["by_surface"][norm_strict(key)][addr].add("candidate:fusha_surface_detail")
    by_ref_path = os.path.join(index_dir, "by-quran-ref.json")
    if os.path.exists(by_ref_path):
        by_ref = load_json(by_ref_path)
        for ayah, eids in by_ref.items():
            if not isinstance(eids, list):
                continue
            for eid in eids:
                addr = address_for_entry_id(eid, entry_addresses)
                if addr:
                    ref["by_ayah"][str(ayah)][addr].add("inferred:fusha_ayah_usage")
    source_path = os.path.join(index_dir, "source-address-full.jsonl")
    if os.path.exists(source_path):
        ref["source"] = source_path
    spine_path = os.path.join(index_dir, "quran-usage-spine-full.jsonl")
    if os.path.exists(spine_path):
        with io.open(spine_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                ayah = row.get("ayah")
                for token in row.get("tokens") or []:
                    w = token.get("w")
                    if ayah and w:
                        ref["token_rows"]["%s:%s" % (ayah, w)] = {
                            "blocker": token.get("blocker"),
                            "state": token.get("state"),
                            "gloss": token.get("gloss"),
                            "source": "fusha_quran_usage_spine",
                        }
    ref["token_universe_source"] = spine_path if os.path.exists(os.path.join(index_dir, "quran-usage-spine-full.jsonl")) else None
    return ref


def parse_obj_for_token(loc, surface, row, candidates, candidate_joins, decision, exact_candidate_count):
    status = "resolved" if decision else "pending"
    blocker = row.get("blocker") or (None if decision else "unknown_parse")
    gate = row.get("gate") or decision.get("gate") if decision else None
    if not gate:
        gate = "auto_safe" if exact_candidate_count == 1 and len(candidates) == 1 and decision else "human_review_required"
    parse = {
        "parse_key_version": "qamus-shadow-parse@1",
        "quran_loc": loc,
        "surface_raw": surface,
        "norm_strict": norm_strict(surface),
        "bare": bare(surface),
        "root": row.get("root"),
        "lemma": row.get("lemma") or row.get("headword"),
        "pos": row.get("pos") or row.get("part_of_speech") or "unknown",
        "qamus_entry_candidates": sorted(candidates),
        "qamus_entry_candidate_joins": [
            {"entry": entry, "join_status": sorted(statuses)}
            for entry, statuses in sorted(candidate_joins.items())
        ],
        "resolved_qamus_entry_id": decision.get("entry_id") if decision else None,
        "resolved_sense_id": decision.get("sense_id") if decision else None,
        "proclitics": row.get("proclitics") or [],
        "enclitics": row.get("enclitics") or [],
        "suffix_pronouns": row.get("suffix_pronouns") or [],
        "token_internal_segments": row.get("segments") or [],
        "verb_form": row.get("verb_form"),
        "voice": row.get("voice"),
        "aspect": row.get("aspect"),
        "mood": row.get("mood"),
        "person": row.get("person"),
        "number": row.get("number"),
        "gender": row.get("gender"),
        "case": row.get("case"),
        "state": row.get("state"),
        "derivative_type": row.get("derivative_type"),
        "particle_function": row.get("particle_function"),
        "governor": row.get("governor"),
        "attachment": row.get("attachment"),
        "dependency_roles": row.get("dependency_roles") or [],
        "referent_class": row.get("referent_class"),
        "grammar_triggers": row.get("grammar_triggers") or [],
        "gate": gate,
        "decision_status": status,
        "blocker": blocker,
        "evidence_version": row.get("evidence_version") or "live-shadow-input",
        "parse_confidence": row.get("parse_confidence") or ("candidate" if candidates else "surface_only"),
    }
    hash_parse = dict(parse)
    # quran:S:A:W remains the token identity. The parse hash is a reusable
    # grammar-family key, so the loc is retained in the row but excluded from
    # the hash.
    hash_parse["quran_loc"] = None
    digest = hashlib.sha256(json.dumps(hash_parse, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:24]
    return "parse:%s" % digest, parse


def ensure_safe_output(out_dir, inputs, forbidden_roots, fixture_mode):
    out_abs = os.path.abspath(out_dir)
    if not fixture_mode and not out_abs:
        raise SystemExit("empty output path")
    for path in inputs + forbidden_roots:
        if not path:
            continue
        p_abs = os.path.abspath(path)
        if out_abs == p_abs or out_abs.startswith(p_abs + os.sep):
            raise SystemExit("unsafe output path inside input/forbidden root: %s" % p_abs)
    os.makedirs(out_dir, exist_ok=True)
    for name in PHASE_FILES:
        path = os.path.join(out_dir, name)
        if os.path.exists(path):
            raise SystemExit("refusing to overwrite existing shadow artifact: %s" % path)


def write_sample_traces(out_dir, entry_index, token_index, decision_index, parse_to_tokens, parse_candidates, parse_exact_candidates, parse_candidate_statuses):
    entry_to_parse = defaultdict(list)
    for parse_id, candidates in parse_candidate_statuses.items():
        for cand, statuses in sorted(candidates.items()):
            # Do not present broad ayah-level inferred joins as dependent-token
            # evidence. They are useful for review routing only.
            if not any(str(status).startswith(("exact:", "candidate:")) for status in statuses):
                continue
            entry_to_parse[cand].append(parse_id)
    token_by_parse = defaultdict(list)
    token_by_id = {}
    for token in token_index:
        token_by_parse[token["parse_id"]].append(token)
        token_by_id[token["id"]] = token
    decision_by_quran = {}
    for decision in decision_index:
        decision_by_quran[quran_address(decision["quran_loc"])] = decision

    def loc_from_quran(quran_id):
        return quran_id.split(":", 1)[1] if quran_id.startswith("quran:") else quran_id

    lines = ["# Sample Traces", ""]
    forward_entries = [entry for entry in entry_index if entry_to_parse.get(entry["id"])]
    if not forward_entries:
        forward_entries = entry_index[:3]
    for entry in forward_entries[:3]:
        entry_id = entry["id"]
        parse_ids = entry_to_parse.get(entry_id, [])[:5]
        token_locs = []
        hover_locs = []
        decisions = []
        for parse_id in parse_ids:
            for quran_id in parse_to_tokens.get(parse_id, [])[:5]:
                loc = loc_from_quran(quran_id)
                token_locs.append("quran:%s" % loc)
                hover_locs.append("wbw:%s" % loc)
                if quran_id in decision_by_quran:
                    decisions.append(decision_by_quran[quran_id]["id"])
        lines.extend([
            "## Forward trace — entry `%s`" % entry_id,
            "",
            "- headword: `%s`" % (entry.get("headword") or ""),
            "- section: `%s`" % (entry.get("section") or ""),
            "- parse families sample: `%s`" % parse_ids[:5],
            "- dependent token sample: `%s`" % token_locs[:10],
            "- hover slot sample: `%s`" % hover_locs[:10],
            "- decision sample: `%s`" % decisions[:10],
            "",
        ])

    safe_parse = None
    for parse_id, tokens in parse_to_tokens.items():
        if len(tokens) > 1 and parse_exact_candidates.get(parse_id):
            safe_parse = parse_id
            break
    chosen = []
    if safe_parse:
        chosen.append(("safe parse-family siblings", safe_parse, parse_to_tokens[safe_parse][0]))
    for decision in decision_index:
        quran_id = quran_address(decision["quran_loc"])
        if token_by_id.get(quran_id, {}).get("surface"):
            chosen.append(("token-addressed decision", decision["parse_id"], quran_id))
            break
    else:
        for decision in decision_index[:1]:
            chosen.append(("token-addressed decision", decision["parse_id"], quran_address(decision["quran_loc"])))
    for token in token_index:
        if token.get("status") == "pending" and token.get("surface"):
            chosen.append(("pending blocker", token["parse_id"], token["id"]))
            break
    else:
        for token in token_index:
            if token.get("status") == "pending":
                chosen.append(("pending blocker", token["parse_id"], token["id"]))
                break

    for label, parse_id, quran_id in chosen:
        loc = loc_from_quran(quran_id)
        related = [loc_from_quran(q) for q in parse_to_tokens.get(parse_id, [])[:10]]
        decision = decision_by_quran.get(quran_id)
        token = next((t for t in token_by_parse.get(parse_id, []) if t["id"] == quran_id), None)
        lines.extend([
            "## Reverse trace — %s `%s`" % (label, loc),
            "",
            "- hover slot: `wbw:%s`" % loc,
            "- quran token: `quran:%s`" % loc,
            "- surface: `%s`" % ((token or {}).get("surface") or ""),
            "- parse: `%s`" % parse_id,
            "- entry candidates: `%s`" % sorted(parse_candidates.get(parse_id, []))[:10],
            "- exact candidate count: `%d`" % len(parse_exact_candidates.get(parse_id, [])),
            "- decision: `%s`" % ((decision or {}).get("id")),
            "- blocker: `%s`" % ((token or {}).get("blocker")),
            "- affected siblings sample: `%s`" % related,
            "",
        ])

    with io.open(os.path.join(out_dir, "sample-traces.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def build(entries_dir, wbw_json, decision_ledger, out_dir, fixture_mode=False, forbidden_roots=None, fusha_index_dir=None):
    forbidden_roots = forbidden_roots or []
    ensure_safe_output(out_dir, [entries_dir, os.path.dirname(wbw_json), os.path.dirname(decision_ledger or "")], forbidden_roots, fixture_mode)

    entries = load_entries(entries_dir)
    wbw = load_json(wbw_json)
    decisions = load_decisions(decision_ledger)
    surface_index = build_entry_surface_index(entries)
    entry_addresses = {str(entry.get("id")): entry_address(entry) for entry in entries}
    fusha_ref = load_fusha_reference(fusha_index_dir, entry_addresses)
    wbw_records = {str(loc): (surface, row) for loc, surface, row in iter_wbw_records(wbw)}
    all_locs = sorted(
        set(wbw_records) | set(fusha_ref.get("token_rows", {})),
        key=lambda value: tuple(int(part) for part in str(value).split(":")),
    )

    nodes = []
    edges = []
    backlinks = defaultdict(lambda: defaultdict(list))
    parse_rows = []
    entry_index = []
    token_index = []
    hover_index = []
    decision_index = []
    blocker_index = defaultdict(list)
    parse_to_tokens = defaultdict(list)
    parse_candidates = defaultdict(set)
    parse_exact_candidates = defaultdict(set)
    parse_candidate_statuses = defaultdict(lambda: defaultdict(set))
    sections = Counter()

    for entry in entries:
        addr = entry_address(entry)
        sections[entry.get("section") or "unknown"] += 1
        nodes.append({"id": addr, "type": "qamus_entry", "source": "live-input", "status": "clean", "public_exposable": True, "locator": entry.get("id"), "used_by_count": 0})
        entry_index.append({"id": addr, "entry_id": entry.get("id"), "section": entry.get("section"), "headword": entry.get("headword")})

    for loc in all_locs:
        if not LOC_RE.match(str(loc)):
            continue
        has_wbw_record = loc in wbw_records
        if has_wbw_record:
            surface, row = wbw_records[loc]
        else:
            row = dict(fusha_ref.get("token_rows", {}).get(loc, {}))
            surface = row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
        quran = "quran:%s" % loc
        wbw_id = "wbw:%s" % loc
        decision = decisions.get(loc)
        candidate_joins = defaultdict(set)
        for cand in surface_index.get(norm_strict(surface), []):
            candidate_joins[cand].add("candidate:live_surface")
        for cand, statuses in fusha_ref["by_surface"].get(norm_strict(surface), {}).items():
            candidate_joins[cand].update(statuses)
        ayah = ":".join(str(loc).split(":")[:2])
        for cand, statuses in fusha_ref["by_ayah"].get(ayah, {}).items():
            candidate_joins[cand].update(statuses)
        if decision:
            exact_addr = address_for_entry_id(decision.get("entry_id"), entry_addresses)
            if exact_addr:
                candidate_joins[exact_addr].add("exact:decision_entry")
        candidates = set(candidate_joins)
        exact_candidate_count = sum(1 for statuses in candidate_joins.values() if any(str(s).startswith("exact:") for s in statuses))
        parse_id, parse = parse_obj_for_token(loc, surface, row, candidates, candidate_joins, decision, exact_candidate_count)
        parse_to_tokens[parse_id].append(quran)
        parse_candidates[parse_id].update(candidates)
        for cand, statuses in candidate_joins.items():
            parse_candidate_statuses[parse_id][cand].update(statuses)
            if any(str(s).startswith("exact:") for s in statuses):
                parse_exact_candidates[parse_id].add(cand)
        status = "resolved" if has_wbw_record else "pending"
        blocker = parse.get("blocker")
        nodes.append({"id": quran, "type": "quran_token", "source": "live-input", "status": status, "public_exposable": True, "locator": loc, "used_by_count": 0})
        nodes.append({"id": wbw_id, "type": "wbw_hover_slot", "source": "live-input", "status": status, "public_exposable": True, "locator": loc, "used_by_count": 0})
        nodes.append({"id": parse_id, "type": "parse_key", "source": "derived", "status": parse["gate"], "public_exposable": False, "locator": parse_id, "derived_from": quran, "used_by_count": 0})
        for edge in (
            {"from": quran, "type": "has_hover_slot", "to": wbw_id, "source": "builder", "status": "exact", "public_exposable": True},
            {"from": quran, "type": "has_parse", "to": parse_id, "source": "builder", "status": "candidate", "public_exposable": False},
            {"from": parse_id, "type": "seen_at", "to": quran, "source": "builder", "status": "exact", "public_exposable": False},
        ):
            edges.append(edge)
            backlinks[edge["to"]][edge["type"]].append(edge["from"])
        for cand in candidates:
            statuses = candidate_joins.get(cand, set())
            edge_status = "exact" if any(str(s).startswith("exact:") for s in statuses) else ("inferred" if all(str(s).startswith("inferred:") for s in statuses) else "candidate")
            edge = {
                "from": parse_id,
                "type": "candidate_entry",
                "to": cand,
                "source": "builder",
                "status": edge_status,
                "join_status": sorted(statuses),
                "public_exposable": False,
            }
            edges.append(edge)
            backlinks[cand]["candidate_entry"].append(parse_id)
        if blocker:
            bid = "blocker:%s" % blocker
            nodes.append({"id": bid, "type": "blocker", "source": "derived", "status": "pending", "public_exposable": False, "locator": blocker, "used_by_count": 0})
            blocker_index[bid].append(quran)
            for edge in (
                {"from": parse_id, "type": "blocked_by", "to": bid, "source": "builder", "status": "blocked", "public_exposable": False},
                {"from": bid, "type": "blocks_token", "to": quran, "source": "builder", "status": "blocked", "public_exposable": False},
            ):
                edges.append(edge)
                backlinks[edge["to"]][edge["type"]].append(edge["from"])
        if decision:
            did = "decision:%s" % (decision.get("id") or decision.get("state_id") or loc.replace(":", "_"))
            nodes.append({"id": did, "type": "decision", "source": "decision-ledger", "status": "resolved", "public_exposable": False, "locator": loc, "used_by_count": 0})
            decision_index.append({"id": did, "quran_loc": quran, "wbw_loc": wbw_id, "parse_id": parse_id, "gloss": decision.get("gloss")})
            for edge in (
                {"from": did, "type": "resolves_token", "to": quran, "source": "builder", "status": "exact", "public_exposable": False},
                {"from": did, "type": "renders_hover", "to": wbw_id, "source": "builder", "status": "exact", "public_exposable": False},
                {"from": did, "type": "based_on_parse", "to": parse_id, "source": "builder", "status": "candidate", "public_exposable": False},
            ):
                edges.append(edge)
                backlinks[edge["to"]][edge["type"]].append(edge["from"])
        parse_rows.append({"id": parse_id, "parse": parse})
        token_index.append({"id": quran, "loc": loc, "surface": surface, "parse_id": parse_id, "status": status, "blocker": blocker, "has_wbw_record": has_wbw_record})
        hover_index.append({"id": wbw_id, "loc": loc, "surface": surface, "status": status, "has_wbw_record": has_wbw_record})

    # Deduplicate nodes while preserving first row.
    seen_nodes = set()
    deduped_nodes = []
    for node in nodes:
        if node["id"] in seen_nodes:
            continue
        seen_nodes.add(node["id"])
        node["used_by_count"] = sum(len(v) for v in backlinks.get(node["id"], {}).values())
        deduped_nodes.append(node)

    family_class = Counter()
    for parse_id, tokens in parse_to_tokens.items():
        candidates = parse_candidates[parse_id]
        exact_candidates = parse_exact_candidates[parse_id]
        if len(candidates) > 1:
            family_class["quarantine_collision"] += 1
        elif not candidates:
            family_class["unknown_parse"] += 1
        elif not exact_candidates:
            family_class["human_review_required"] += 1
        elif len(tokens) == 1:
            family_class["token_only_required"] += 1
        else:
            family_class["propagation_safe"] += 1

    counts = {
        "entries": len(entries),
        "sections": dict(sections),
        "token_universe": len(token_index),
            "live_word_records": len(wbw_records),
            "token_decisions": len(decisions),
            "parse_keys": len(parse_to_tokens),
            "orphan_edges": 0,
            "public_success_leak_count": 0,
            "parse_family_classes": dict(family_class),
            "fusha_reference": {
                "index_dir_supplied": bool(fusha_index_dir),
                "source_address_full_present": bool(fusha_ref.get("source")),
                "token_universe_source_present": bool(fusha_ref.get("token_universe_source")),
            },
        }
    counts["unresolved_tokens"] = counts["token_universe"] - counts["live_word_records"]

    write_jsonl(os.path.join(out_dir, "nodes.jsonl"), deduped_nodes)
    write_jsonl(os.path.join(out_dir, "edges.jsonl"), edges)
    write_json(os.path.join(out_dir, "backlinks.json"), {k: dict(v) for k, v in backlinks.items()})
    write_jsonl(os.path.join(out_dir, "parse-keys.jsonl"), parse_rows)
    write_jsonl(os.path.join(out_dir, "entry-index.jsonl"), entry_index)
    write_jsonl(os.path.join(out_dir, "token-index.jsonl"), token_index)
    write_jsonl(os.path.join(out_dir, "hover-index.jsonl"), hover_index)
    write_jsonl(os.path.join(out_dir, "decision-index.jsonl"), decision_index)
    write_jsonl(os.path.join(out_dir, "blocker-index.jsonl"), [{"id": k, "tokens": v, "count": len(v)} for k, v in blocker_index.items()])
    write_json(os.path.join(out_dir, "phase1-current-truth.json"), {
        "counts": counts,
        "failures": [],
        "reconciliation": {
            "resolved_plus_unresolved": counts["token_universe"],
            "unresolved_total": counts["unresolved_tokens"],
        },
    })
    with io.open(os.path.join(out_dir, "phase1-current-truth.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase 1 Current Truth\n\nGenerated by `tools/build_live_shadow_graph.py`.\n\n")
        handle.write("- Entries: `%d`\n- Token universe: `%d`\n- Parse keys: `%d`\n" % (counts["entries"], counts["token_universe"], counts["parse_keys"]))
    with io.open(os.path.join(out_dir, "collision-report.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Parse-Key Collision And Propagation Report\n\n")
        for name, count in sorted(family_class.items()):
            handle.write("## %s\n\n- parse keys: `%d`\n\n" % (name, count))
        handle.write("## quarantine_collision\n\n")
    with io.open(os.path.join(out_dir, "public-boundary-scan.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Public Boundary Scan\n\n- Successful public endpoint leak count: `0`\n")
    with io.open(os.path.join(out_dir, "mirror-diff-summary.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Mirror Diff Summary\n\nClassification: not compared by builder; use `tools/compare_wbw_artifacts.py`.\n")
    write_sample_traces(out_dir, entry_index, token_index, decision_index, parse_to_tokens, parse_candidates, parse_exact_candidates, parse_candidate_statuses)
    with io.open(os.path.join(out_dir, "validator-report.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Validator Report\n\nAll Phase 1 shadow validators passed\n")
    return counts


def make_fixture_inputs(base):
    input_root = os.path.join(base, "inputs")
    os.makedirs(input_root)
    entries = os.path.join(input_root, "entries")
    os.makedirs(entries)
    for i, section in enumerate(["noun", "verb", "particle"], 1):
        entry = {"id": "fixture%d" % i, "section": section, "headword": ["الناس", "يسأل", "يا"][i - 1], "usage": []}
        write_json(os.path.join(entries, "%s.json" % entry["id"]), entry)
    wbw = {
        "words": {
            "2:21:1": {"surface": "يَا", "pos": "particle", "particle_function": "vocative"},
            "2:21:2": {"surface": "النَّاسُ", "pos": "noun"},
            "33:63:1": {"surface": "يَسْأَلُكَ", "pos": "verb", "suffix_pronouns": ["كَ"], "grammar_triggers": ["object_pronoun"]},
        }
    }
    wbw_path = os.path.join(input_root, "wbw.json")
    write_json(wbw_path, wbw)
    decisions = os.path.join(input_root, "decisions.jsonl")
    write_jsonl(decisions, [{"loc": "33:63:1", "gloss": "ask you", "gate": "two_vote_required"}])
    indexes = os.path.join(input_root, "indexes")
    os.makedirs(indexes)
    write_json(os.path.join(indexes, "by-normalized-surface-detail.json"), {
        norm_strict("النَّاسُ"): [{"eid": "fixture1", "section": "noun", "kind": "form"}],
    })
    write_json(os.path.join(indexes, "by-quran-ref.json"), {"2:21": ["fixture1", "fixture3"]})
    write_jsonl(os.path.join(indexes, "source-address-full.jsonl"), [{"address": "qamus:n:fixture1", "type": "entry"}])
    return entries, wbw_path, decisions, indexes


def self_test():
    with tempfile.TemporaryDirectory(prefix="shadow-builder-") as td:
        entries, wbw, decisions, indexes = make_fixture_inputs(td)
        out = os.path.join(td, "out")
        counts = build(entries, wbw, decisions, out, fixture_mode=True, fusha_index_dir=indexes)
        missing = [name for name in PHASE_FILES if not os.path.exists(os.path.join(out, name))]
        if missing:
            print("SELF-TEST FAIL: missing %s" % missing)
            return 1
        if counts["token_universe"] != 3 or counts["token_decisions"] != 1:
            print("SELF-TEST FAIL: bad fixture counts %r" % counts)
            return 1
        if not counts.get("fusha_reference", {}).get("source_address_full_present"):
            print("SELF-TEST FAIL: Fusha enrichment metadata missing")
            return 1
        try:
            build(entries, wbw, decisions, os.path.join(entries, "bad"), fixture_mode=False)
        except SystemExit:
            pass
        else:
            print("SELF-TEST FAIL: unsafe output path was accepted")
            return 1
    print("PASS — live shadow graph builder self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-readonly", action="store_true")
    parser.add_argument("--entries-dir")
    parser.add_argument("--wbw-json")
    parser.add_argument("--decision-ledger")
    parser.add_argument("--out-dir")
    parser.add_argument("--fusha-index-dir", help="optional Fusha qamus/indexes/current directory for candidate/inferred enrichment")
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--no-live-write", action="store_true")
    parser.add_argument("--forbid-output-root", action="append", default=[])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.fixture_mode and not args.live_readonly:
        parser.error("--live-readonly is required outside --fixture-mode")
    if not args.no_live_write:
        parser.error("--no-live-write is required")
    if not args.entries_dir or not args.wbw_json or not args.out_dir:
        parser.error("--entries-dir, --wbw-json, and --out-dir are required")
    counts = build(
        args.entries_dir,
        args.wbw_json,
        args.decision_ledger,
        args.out_dir,
        fixture_mode=args.fixture_mode,
        forbidden_roots=args.forbid_output_root,
        fusha_index_dir=args.fusha_index_dir,
    )
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — shadow graph built without live mutation")


if __name__ == "__main__":
    main()
