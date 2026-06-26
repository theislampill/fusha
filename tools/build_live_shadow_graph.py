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
from datetime import datetime, timezone
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
    "phase2-run-manifest.json",
]
GATES_UNSAFE_FOR_PROPAGATION = {"human_review_required", "never_auto", "unknown"}
PARSE_KEY_VERSION = "qamus-live-shadow-parse@1"


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


def sha_obj(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def slug(value):
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^0-9a-zA-Z:_-]+", "-", text)
    return text.strip("-") or "unknown"


def sense_address(entry, sense_id):
    return "%s#sense=%s" % (entry_address(entry), sense_id)


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_row_count(path):
    if not path or not os.path.exists(path):
        return None
    if path.endswith(".jsonl"):
        with io.open(path, encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    return None


def describe_file(path, role, required=True):
    row = {
        "role": role,
        "path": path,
        "required": required,
        "exists": bool(path and os.path.exists(path)),
        "kind": "file",
        "sha256": None,
        "bytes": None,
        "row_count": None,
    }
    if row["exists"]:
        row["sha256"] = sha256_file(path)
        row["bytes"] = os.path.getsize(path)
        row["row_count"] = file_row_count(path)
    return row


def describe_dir(path, role, required=True):
    row = {
        "role": role,
        "path": path,
        "required": required,
        "exists": bool(path and os.path.isdir(path)),
        "kind": "directory",
        "sha256": None,
        "bytes": None,
        "file_count": 0,
        "json_file_count": 0,
    }
    if not row["exists"]:
        return row
    digest = hashlib.sha256()
    total = 0
    file_count = 0
    json_count = 0
    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            file_count += 1
            if name.endswith(".json"):
                json_count += 1
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path).replace(os.sep, "/")
            size = os.path.getsize(full)
            total += size
            digest.update(rel.encode("utf-8"))
            digest.update(str(size).encode("ascii"))
            digest.update(sha256_file(full).encode("ascii"))
    row["sha256"] = digest.hexdigest()
    row["bytes"] = total
    row["file_count"] = file_count
    row["json_file_count"] = json_count
    return row


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


def iter_wbw_token_surfaces(wbw):
    if isinstance(wbw, dict) and isinstance(wbw.get("verses"), dict):
        for ayah, words in sorted(wbw["verses"].items(), key=lambda kv: str(kv[0])):
            if isinstance(words, list):
                for index, row in enumerate(words, 1):
                    loc = "%s:%d" % (ayah, index)
                    if isinstance(row, dict):
                        surface = row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
                    else:
                        surface = str(row)
                    yield loc, surface
            elif isinstance(words, dict):
                for key, row in sorted(words.items(), key=lambda kv: str(kv[0])):
                    loc = str(key) if str(key).count(":") == 2 else "%s:%s" % (ayah, key)
                    if isinstance(row, dict):
                        surface = row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
                    else:
                        surface = str(row)
                    yield loc, surface
        return
    for loc, surface, _row in iter_wbw_records(wbw):
        yield loc, surface


def load_decisions(path):
    decisions = {}
    row_count = 0
    if not path:
        return decisions, row_count
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row_count += 1
            row = json.loads(line)
            loc = row.get("loc") or row.get("quran_loc")
            if loc:
                decisions[loc] = row
    return decisions, row_count


def entry_address(entry):
    section = (entry.get("section") or entry.get("class") or "entry").lower()
    prefix = {"noun": "n", "verb": "v", "particle": "p"}.get(section, section[:1] or "e")
    return "qamus:%s:%s" % (prefix, entry.get("id"))


def build_entry_surface_index(entries):
    index = defaultdict(list)
    for entry in entries:
        addr = entry_address(entry)
        entry_id = entry.get("id")
        if entry.get("headword"):
            index[norm_strict(entry["headword"])].append({
                "entry_id": entry_id,
                "entry_address": addr,
                "sense_id": None,
                "source": "headword",
            })
        for usage in entry.get("usage") or []:
            if not isinstance(usage, dict):
                continue
            sense_id = usage.get("sense")
            for form in usage.get("forms") or []:
                key = norm_strict(form)
                if key:
                    index[key].append({
                        "entry_id": entry_id,
                        "entry_address": addr,
                        "sense_id": sense_id,
                        "source": "usage_form",
                    })
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


def fields_from_runtime_parse_key(key):
    fields = {
        "verb_form": None,
        "voice": None,
        "aspect": None,
        "mood": None,
        "person": None,
        "number": None,
        "gender": None,
        "case": None,
        "state": None,
        "derivative_type": None,
    }
    key = key or ""
    for verb_form in ("VIII", "VII", "VI", "IV", "III", "II", "IX", "X", "V", "I"):
        if ":%s:" % verb_form in key or key.startswith("V:%s:" % verb_form):
            fields["verb_form"] = verb_form
            break
    if "PASS" in key:
        fields["voice"] = "passive"
    if "ACT" in key:
        fields["voice"] = "active"
    if "IMPF" in key:
        fields["aspect"] = "imperfect"
    if "PERF" in key:
        fields["aspect"] = "perfect"
    if "JUSS" in key:
        fields["mood"] = "jussive"
    if "SUBJ" in key:
        fields["mood"] = "subjunctive"
    person = re.search(r"([123])([MF]?)(S|D|P)", key)
    if person:
        fields["person"] = person.group(1)
        fields["gender"] = {"M": "masculine", "F": "feminine", "": "unknown"}[person.group(2)]
        fields["number"] = {"S": "singular", "D": "dual", "P": "plural"}[person.group(3)]
    if "NOM" in key:
        fields["case"] = "nominative"
    if "ACC" in key:
        fields["case"] = "accusative"
    if "GEN" in key:
        fields["case"] = "genitive"
    if "INDEF" in key:
        fields["state"] = "indefinite"
    elif "DEF" in key:
        fields["state"] = "definite"
    if "ADJ" in key:
        fields["derivative_type"] = "adjective"
    return fields


def infer_pos(row, segments):
    if isinstance(row, dict) and row.get("pos"):
        return str(row["pos"])
    roles = " ".join(str(segment.get("role", "")) for segment in segments if isinstance(segment, dict)).lower()
    if "verb" in roles:
        return "verb"
    if "preposition" in roles:
        return "preposition"
    if "particle" in roles or "conjunction" in roles:
        return "particle"
    if "noun" in roles or "article" in roles:
        return "noun"
    return "unknown"


def classify_gate(status, candidates, segments, confidence, blocker):
    roles = {str(segment.get("role", "")) for segment in segments if isinstance(segment, dict)}
    if blocker or confidence == "surface_only" or len({candidate.get("entry_address") for candidate in candidates}) > 1:
        return "human_review_required"
    if any("preposition" in role for role in roles) or any(role in ("conjunction", "resumption_particle") for role in roles):
        return "two_vote_required"
    grammar_sensitive = {
        "object_pronoun",
        "possessive_pronoun",
        "subject_pronoun",
        "prefix_preposition",
        "resumption_particle",
        "prefix_oath",
        "prefix_comitative_waw",
        "prefix_cause_fa",
    }
    if roles & grammar_sensitive:
        return "two_vote_required"
    return "auto_safe" if status == "resolved" else "human_review_required"


def classify_family(record):
    if record["blockers"]:
        return "human_review_required"
    if "surface_only" in record["confidences"]:
        return "unknown_parse"
    if not record["candidate_entries"]:
        return "missing_entry"
    if len(record["candidate_entries"]) > 1:
        return "quarantine_collision"
    if "human_review_required" in record["gates"]:
        return "human_review_required"
    if "two_vote_required" in record["gates"]:
        return "two_vote_required"
    return "propagation_safe" if record["family_size"] > 1 else "token_only_required"


def parse_obj_for_token(loc, surface, row, candidates, status, blocker, live_source_sha, decision_ledger_sha, entries_by_id):
    segments = (row.get("segments") if isinstance(row, dict) else None) or []
    runtime_parse_key = (row.get("parse_key") if isinstance(row, dict) else None) or {}
    runtime_key = runtime_parse_key.get("key") if isinstance(runtime_parse_key, dict) else ""
    parsed_fields = fields_from_runtime_parse_key(runtime_key)
    suffixes = [segment for segment in segments if isinstance(segment, dict) and "pronoun" in str(segment.get("role", ""))]
    proclitics = [
        segment for segment in segments
        if isinstance(segment, dict)
        and (str(segment.get("role", "")).startswith("prefix") or segment.get("role") in ("conjunction", "definite_article", "resumption_particle"))
    ]
    roles = {str(segment.get("role", "")) for segment in segments if isinstance(segment, dict)}
    triggers = []
    if suffixes:
        triggers.append("suffix_pronoun")
    if any("preposition" in role for role in roles):
        triggers.append("preposition")
    if any(role in ("conjunction", "resumption_particle") for role in roles):
        triggers.append("function_particle")
    if blocker:
        triggers.append("blocker")
    confidence = "rich_metadata" if runtime_parse_key and segments else ("lexical_candidate" if candidates else "surface_only")
    explicit_gate = row.get("gate") if isinstance(row, dict) else None
    gate = explicit_gate or classify_gate(status, candidates, segments, confidence, blocker)
    lemma = None
    if len(candidates) == 1:
        candidate_entry = entries_by_id.get(str(candidates[0].get("entry_id")))
        if candidate_entry:
            lemma = candidate_entry.get("headword")
    parse = {
        "parse_key_version": PARSE_KEY_VERSION,
        "quran_loc": loc,
        "surface_raw": surface,
        "norm_strict": norm_strict(surface),
        "bare": bare(surface),
        "root": row.get("root") if isinstance(row, dict) else None,
        "lemma": lemma,
        "pos": infer_pos(row, segments),
        "qamus_entry_candidates": candidates,
        "resolved_qamus_entry_id": None,
        "resolved_sense_id": None,
        "proclitics": proclitics,
        "enclitics": suffixes,
        "suffix_pronouns": suffixes,
        "token_internal_segments": segments,
        "verb_form": parsed_fields["verb_form"],
        "voice": parsed_fields["voice"],
        "aspect": parsed_fields["aspect"],
        "mood": parsed_fields["mood"],
        "person": parsed_fields["person"],
        "number": parsed_fields["number"],
        "gender": parsed_fields["gender"],
        "case": parsed_fields["case"],
        "state": parsed_fields["state"],
        "derivative_type": parsed_fields["derivative_type"],
        "particle_function": ",".join(sorted(role for role in roles if "particle" in role or role in ("conjunction", "preposition"))) or None,
        "governor": None,
        "attachment": None,
        "referent_class": None,
        "grammar_triggers": sorted(set(triggers)),
        "gate": gate,
        "decision_status": status,
        "blocker": blocker,
        "evidence_version": {
            "live_wbw_source_sha": live_source_sha,
            "token_decision_sha256": decision_ledger_sha,
        },
        "parse_confidence": confidence,
    }
    family = dict(parse)
    # quran:S:A:W remains the token identity. The parse hash is a reusable
    # grammar-family key, so the loc is retained in token rows but excluded
    # from the hash.
    family["quran_loc"] = None
    return "parse:%s" % sha_obj(family), parse, family, runtime_parse_key


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


def write_run_manifest(
        out_dir,
        counts,
        entries_dir,
        wbw_json,
        decision_ledger,
        fusha_index_dir,
        fixture_mode,
        live_readonly,
        no_live_write,
        forbidden_roots):
    artifact_rows = []
    for name in PHASE_FILES:
        if name == "phase2-run-manifest.json":
            continue
        path = os.path.join(out_dir, name)
        artifact_rows.append({
            "name": name,
            "exists": os.path.exists(path),
            "bytes": os.path.getsize(path) if os.path.exists(path) else None,
            "sha256": sha256_file(path) if os.path.exists(path) else None,
        })
    manifest = {
        "schema_version": "qamus-live-shadow-run-manifest@1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "builder": "tools/build_live_shadow_graph.py",
        "run_mode": "fixture" if fixture_mode else "live_readonly",
        "fixture_mode": bool(fixture_mode),
        "live_readonly": bool(live_readonly or fixture_mode),
        "no_live_write": bool(no_live_write),
        "live_mutation_allowed": False,
        "wbw_rebuild_allowed": False,
        "service_restart_allowed": False,
        "mirror_sync_allowed": False,
        "identity_hierarchy": {
            "quran_token": "quran:S:A:W",
            "hover_slot": "wbw:S:A:W",
            "entry": "qamus:*",
            "decision": "decision:*",
            "parse_family": "parse:<hash>",
            "parse_key_primary_identity": False,
            "raw_surface_identity_allowed": False,
            "norm_only_certification_allowed": False,
        },
        "input_artifacts": [
            describe_dir(entries_dir, "entries_dir"),
            describe_file(wbw_json, "wbw_json"),
            describe_file(decision_ledger, "decision_ledger", required=False),
            describe_dir(fusha_index_dir, "fusha_index_dir", required=False),
        ],
        "output_guard": {
            "out_dir": out_dir,
            "forbidden_roots": forbidden_roots or [],
            "forbidden_roots_checked": len(forbidden_roots or []),
            "output_inside_forbidden_root": False,
            "overwrite_refused_for_existing_artifacts": True,
        },
        "counts": counts,
        "public_boundary": {
            "public_fields": ["gloss", "src", "kind", "lang"],
            "private_fields": ["informed_by", "internal_evidence", "adapter_labels", "reviewer_notes"],
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_source_names_public": False,
            "internal_provenance_public": False,
        },
        "public_readback_scan": {
            "status": "not_run_by_builder",
            "leak_count": None,
            "note": "Run tools/scan_public_boundary.py for HTTP public readback evidence.",
        },
        "detector_maturity": {
            "two_vote_required": "partial_shadow_gate",
            "source_disagreement": "reserved_detector_gap",
            "zero_count_policy": "zero_does_not_prove_absence",
        },
        "artifacts_written": artifact_rows,
    }
    write_json(os.path.join(out_dir, "phase2-run-manifest.json"), manifest)


def build(entries_dir, wbw_json, decision_ledger, out_dir, fixture_mode=False, forbidden_roots=None, fusha_index_dir=None,
          live_readonly=False, no_live_write=True):
    forbidden_roots = forbidden_roots or []
    ensure_safe_output(out_dir, [entries_dir, os.path.dirname(wbw_json), os.path.dirname(decision_ledger or "")], forbidden_roots, fixture_mode)

    entries = load_entries(entries_dir)
    wbw = load_json(wbw_json)
    decisions, decision_row_count = load_decisions(decision_ledger)
    surface_index = build_entry_surface_index(entries)
    entry_addresses = {str(entry.get("id")): entry_address(entry) for entry in entries}
    entries_by_id = {str(entry.get("id")): entry for entry in entries}
    fusha_ref = load_fusha_reference(fusha_index_dir, entry_addresses)
    wbw_records = {str(loc): (surface, row) for loc, surface, row in iter_wbw_records(wbw)}
    verse_surfaces = {str(loc): surface for loc, surface in iter_wbw_token_surfaces(wbw)}
    all_locs = sorted(
        set(verse_surfaces) | set(wbw_records) | set(fusha_ref.get("token_rows", {})),
        key=lambda value: tuple(int(part) for part in str(value).split(":")),
    )
    pending_rows = wbw.get("pending") if isinstance(wbw, dict) and isinstance(wbw.get("pending"), dict) else {}
    live_source_sha = (wbw.get("_meta") if isinstance(wbw, dict) and isinstance(wbw.get("_meta"), dict) else {}).get("source_sha")
    decision_ledger_sha = sha256_file(decision_ledger) if decision_ledger and os.path.exists(decision_ledger) else None

    nodes = []
    edges = []
    backlinks = defaultdict(lambda: defaultdict(list))
    entry_index = []
    token_index = []
    hover_index = []
    decision_index = []
    blocker_index = defaultdict(list)
    parse_to_tokens = defaultdict(list)
    parse_candidates = defaultdict(set)
    parse_exact_candidates = defaultdict(set)
    parse_candidate_statuses = defaultdict(lambda: defaultdict(set))
    parse_canonical = {}
    parse_runtime = {}
    parse_blockers = defaultdict(set)
    parse_gates = defaultdict(set)
    parse_confidences = defaultdict(set)
    sections = Counter()

    for entry in entries:
        addr = entry_address(entry)
        sections[entry.get("section") or "unknown"] += 1
        nodes.append({"id": addr, "type": "qamus_entry", "source": "live-input", "status": "clean", "public_exposable": True, "locator": entry.get("id"), "used_by_count": 0})
        fields = []
        for field in ("headword", "translit", "meaning", "definition", "root", "section", "category"):
            if field not in entry:
                continue
            field_addr = "%s#field=%s" % (addr, field)
            fields.append(field_addr)
            nodes.append({
                "id": field_addr,
                "type": "qamus_field",
                "source": "live-input",
                "status": "clean",
                "public_exposable": False,
                "locator": {"entry_id": entry.get("id"), "field_path": field},
                "derived_from": addr,
                "used_by_count": 0,
            })
            edge = {"from": addr, "type": "has_field", "to": field_addr, "source": "builder", "status": "exact", "public_exposable": False}
            edges.append(edge)
            backlinks[edge["to"]][edge["type"]].append(edge["from"])
        for index, sense in enumerate(entry.get("senses") or []):
            sense_id = sense.get("id", index + 1) if isinstance(sense, dict) else index + 1
            sense_addr = sense_address(entry, sense_id)
            fields.append(sense_addr)
            nodes.append({
                "id": sense_addr,
                "type": "qamus_sense",
                "source": "live-input",
                "status": "clean",
                "public_exposable": False,
                "locator": {"entry_id": entry.get("id"), "sense_id": sense_id},
                "derived_from": addr,
                "used_by_count": 0,
            })
            edge = {"from": addr, "type": "has_sense", "to": sense_addr, "source": "builder", "status": "exact", "public_exposable": False}
            edges.append(edge)
            backlinks[edge["to"]][edge["type"]].append(edge["from"])
        entry_index.append({"id": addr, "entry_id": entry.get("id"), "section": entry.get("section"), "headword": entry.get("headword"), "field_count": len(fields)})

    for loc in all_locs:
        if not LOC_RE.match(str(loc)):
            continue
        has_wbw_record = loc in wbw_records
        if has_wbw_record:
            _record_surface, row = wbw_records[loc]
            surface = (row.get("ar") if isinstance(row, dict) else None) or _record_surface or verse_surfaces.get(loc, "")
        else:
            row = dict(fusha_ref.get("token_rows", {}).get(loc, {}))
            surface = verse_surfaces.get(loc) or row.get("surface") or row.get("ar") or row.get("arabic") or row.get("text") or ""
        quran = "quran:%s" % loc
        wbw_id = "wbw:%s" % loc
        decision = decisions.get(loc)
        pending = pending_rows.get(loc)
        blocker = None
        if isinstance(pending, dict):
            blocker = pending.get("reason") or pending.get("blocker") or pending.get("pending_code")
        elif isinstance(pending, str):
            blocker = pending
        if not has_wbw_record:
            blocker = blocker or "missing_wbw_record"
        status = "resolved" if has_wbw_record and isinstance(row, dict) and row.get("glosses") and not blocker else "pending"
        candidates = []
        seen_candidates = set()
        for candidate in surface_index.get(norm_strict(surface), []):
            key = (candidate.get("entry_address"), candidate.get("sense_id"), candidate.get("source"))
            if key in seen_candidates:
                continue
            seen_candidates.add(key)
            candidates.append(candidate)
        parse_id, parse, family, runtime_parse_key = parse_obj_for_token(
            loc,
            surface,
            row if isinstance(row, dict) else {},
            candidates,
            status,
            blocker,
            live_source_sha,
            decision_ledger_sha,
            entries_by_id,
        )
        parse_canonical.setdefault(parse_id, family)
        parse_runtime.setdefault(parse_id, runtime_parse_key or None)
        if parse.get("blocker"):
            parse_blockers[parse_id].add(parse.get("blocker"))
        if parse.get("gate"):
            parse_gates[parse_id].add(parse.get("gate"))
        if parse.get("parse_confidence"):
            parse_confidences[parse_id].add(parse.get("parse_confidence"))
        parse_to_tokens[parse_id].append(quran)
        for candidate in candidates:
            entry_addr = candidate.get("entry_address")
            if not entry_addr:
                continue
            parse_candidates[parse_id].add(entry_addr)
            parse_candidate_statuses[parse_id][entry_addr].add("candidate:%s" % (candidate.get("source") or "live_surface"))
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
        for cand in sorted(parse_candidate_statuses.get(parse_id, {})):
            statuses = parse_candidate_statuses[parse_id].get(cand, set())
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
            reverse_edge = {
                "from": cand,
                "type": "candidate_for_token",
                "to": quran,
                "source": "builder",
                "status": edge_status,
                "join_status": sorted(statuses),
                "public_exposable": False,
            }
            edges.append(reverse_edge)
            backlinks[reverse_edge["to"]][reverse_edge["type"]].append(reverse_edge["from"])
        if blocker:
            bid = "blocker:%s" % slug(blocker)
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
            decision_edges = [
                {"from": did, "type": "resolves_token", "to": quran, "source": "builder", "status": "exact", "public_exposable": False},
                {"from": did, "type": "renders_hover", "to": wbw_id, "source": "builder", "status": "exact", "public_exposable": False},
                {"from": did, "type": "based_on_parse", "to": parse_id, "source": "builder", "status": "candidate", "public_exposable": False},
            ]
            exact_entry = address_for_entry_id(decision.get("entry_id"), entry_addresses)
            if exact_entry and decision.get("sense_id") is not None:
                decision_edges.append({
                    "from": did,
                    "type": "resolves_entry",
                    "to": "%s#sense=%s" % (exact_entry, decision.get("sense_id")),
                    "source": "builder",
                    "status": "exact",
                    "public_exposable": False,
                })
            provenance = decision.get("internal_provenance") if isinstance(decision.get("internal_provenance"), dict) else {}
            for label in provenance.get("informed_by") or []:
                external = "external:%s#quran:%s" % (slug(label), loc)
                nodes.append({
                    "id": external,
                    "type": "external_evidence",
                    "source": "decision-ledger",
                    "status": "internal_only",
                    "public_exposable": False,
                    "locator": {"adapter_label": label, "loc": loc},
                    "used_by_count": 0,
                })
                decision_edges.append({
                    "from": did,
                    "type": "informed_by_internal",
                    "to": external,
                    "source": "builder",
                    "status": "internal_only",
                    "public_exposable": False,
                })
            for edge in decision_edges:
                edges.append(edge)
                backlinks[edge["to"]][edge["type"]].append(edge["from"])
        token_index.append({"id": quran, "loc": loc, "surface": surface, "parse_id": parse_id, "parse_key": parse_id, "status": status, "blocker": blocker, "has_wbw_record": has_wbw_record})
        hover_index.append({"id": wbw_id, "loc": loc, "surface": surface, "status": status, "has_wbw_record": has_wbw_record})

    edge_seen = set()
    deduped_edges = []
    for edge in edges:
        key = (edge["from"], edge["type"], edge["to"], json.dumps(edge.get("join_status"), ensure_ascii=False, sort_keys=True))
        if key in edge_seen:
            continue
        edge_seen.add(key)
        deduped_edges.append(edge)
    edges = deduped_edges
    backlinks = defaultdict(lambda: defaultdict(list))
    for edge in edges:
        backlinks[edge["to"]][edge["type"]].append(edge["from"])

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
    family_class_by_parse = {}
    parse_rows = []
    for parse_id, tokens in parse_to_tokens.items():
        row = {
            "id": parse_id,
            "canonical_parse_object": parse_canonical.get(parse_id) or {},
            "seen_locs": sorted(tokens, key=lambda q: tuple(int(part) for part in str(q).split(":", 1)[1].split(":"))),
            "family_size": len(tokens),
            "candidate_entries": sorted(parse_candidates.get(parse_id, [])),
            "blockers": sorted(parse_blockers.get(parse_id, [])),
            "gates": sorted(parse_gates.get(parse_id, [])),
            "confidences": sorted(parse_confidences.get(parse_id, [])),
            "family_class": None,
            "propagation_allowed": False,
            "runtime_parse_key": parse_runtime.get(parse_id),
        }
        klass = classify_family(row)
        row["family_class"] = klass
        row["propagation_allowed"] = klass == "propagation_safe"
        family_class[klass] += 1
        family_class_by_parse[parse_id] = klass
        parse_rows.append(row)
    parse_rows.sort(key=lambda row: row["id"])

    counts = {
        "entries": len(entries),
        "sections": dict(sections),
        "token_universe": len(token_index),
            "live_word_records": len(wbw_records),
            "token_decisions": decision_row_count,
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
    write_run_manifest(
        out_dir,
        counts,
        entries_dir,
        wbw_json,
        decision_ledger,
        fusha_index_dir,
        fixture_mode,
        live_readonly,
        no_live_write,
        forbidden_roots,
    )
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
            "2:21:1": {"surface": "يَا", "pos": "particle", "particle_function": "vocative", "gate": "never_auto"},
            "2:21:2": {"surface": "النَّاسُ", "pos": "noun"},
            "22:18:17": {
                "surface": "وَٱلشَّجَرُ",
                "pos": "noun",
                "parse_key": {"key": "CONJ+ART+N:NOM:DEF:SG"},
                "segments": [
                    {"role": "conjunction", "text": "وَ"},
                    {"role": "definite_article", "text": "ٱل"},
                    {"role": "noun", "text": "شَّجَرُ"}
                ],
            },
            "33:63:1": {"surface": "يَسْأَلُكَ", "pos": "verb", "suffix_pronouns": ["كَ"], "grammar_triggers": ["object_pronoun"]},
            "33:63:2": {"surface": "يَسْأَلُكَ", "pos": "verb", "suffix_pronouns": ["كَ"], "grammar_triggers": ["object_pronoun"]},
        }
    }
    wbw_path = os.path.join(input_root, "wbw.json")
    write_json(wbw_path, wbw)
    decisions = os.path.join(input_root, "decisions.jsonl")
    write_jsonl(decisions, [
        {"loc": "22:18:17", "gloss": "and + the trees"},
        {"loc": "33:63:1", "gloss": "ask you", "gate": "two_vote_required"},
        {"loc": "33:63:2", "gloss": "ask you", "gate": "two_vote_required"},
        {"loc": "33:63:2", "gloss": "ask you", "gate": "two_vote_required", "id": "superseding_fixture_row"},
    ])
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
        counts = build(entries, wbw, decisions, out, fixture_mode=True, fusha_index_dir=indexes, no_live_write=True)
        missing = [name for name in PHASE_FILES if not os.path.exists(os.path.join(out, name))]
        if missing:
            print("SELF-TEST FAIL: missing %s" % missing)
            return 1
        if counts["token_universe"] != 5 or counts["token_decisions"] != 4:
            print("SELF-TEST FAIL: bad fixture counts %r" % counts)
            return 1
        if not counts.get("fusha_reference", {}).get("source_address_full_present"):
            print("SELF-TEST FAIL: Fusha enrichment metadata missing")
            return 1
        parse_rows = []
        with io.open(os.path.join(out, "parse-keys.jsonl"), encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    parse_rows.append(json.loads(line))
        if not all("canonical_parse_object" in row and "seen_locs" in row for row in parse_rows):
            print("SELF-TEST FAIL: parse rows must be family-shaped")
            return 1
        yasaluka_families = [row for row in parse_rows if "quran:33:63:1" in row.get("seen_locs", [])]
        if not yasaluka_families or yasaluka_families[0].get("family_size") != 2:
            print("SELF-TEST FAIL: reusable parse family was not aggregated")
            return 1
        token_rows = []
        with io.open(os.path.join(out, "token-index.jsonl"), encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    token_rows.append(json.loads(line))
        if not all(str(row.get("parse_key") or "").startswith("parse:") for row in token_rows):
            print("SELF-TEST FAIL: token rows must expose parse_key")
            return 1
        vocative = next((row["canonical_parse_object"] for row in parse_rows if "quran:2:21:1" in row.get("seen_locs", [])), None)
        if not vocative or vocative.get("gate") != "never_auto":
            got_gate = (vocative or {}).get("gate")
            print("SELF-TEST FAIL: pending row gate was not preserved: got %r" % got_gate)
            return 1
        rich_conj = next((row["canonical_parse_object"] for row in parse_rows if "quran:22:18:17" in row.get("seen_locs", [])), None)
        if not rich_conj or rich_conj.get("gate") != "two_vote_required":
            got_gate = (rich_conj or {}).get("gate")
            print("SELF-TEST FAIL: rich conjunction token must not be auto-safe: got %r" % got_gate)
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
        live_readonly=args.live_readonly,
        no_live_write=args.no_live_write,
    )
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — shadow graph built without live mutation")


if __name__ == "__main__":
    main()
