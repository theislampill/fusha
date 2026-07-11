#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lane D: build self-contained morphline authoring packets + RM-20 dry-run reports.

The merged Lane D plan proved that the 15 empty-morphline locations (32 occurrence
bindings) admit no deterministic class->morphline text projection; every binding is
verdict ``requires_authoring``.  This tool prepares the REVIEWED repair without
authoring anything or touching any crosswalk / ledger / whitelist:

  1. reads the hash-pinned baseline whitelist (972263b5...) and, for each target
     binding, assembles a self-contained packet -- the live hover row, its segments,
     the citing entry's documented material AT THE EXACT AYAH ADDRESS, and a pointer
     to >=10 nearest-analog live rows (same segment-class shape) that carry non-empty
     morphlines as convention exemplars;
  2. writes those convention exemplars (deterministically selected, most-representative
     first) to a sibling file so authors can study the live convention;
  3. runs tools/rebind_canonical_hover.py in dry-run to report exactly which occurrence
     bindings each RM-20 repair would touch (blast radius), and self-verifies each
     report with the tool's own verify_dataset.

NO value that a LATER independent author must supply (proposed_morphline, rationale,
confidence) is ever fabricated: the packet declares the response schema and pins the
evidence, nothing more.  A placeholder trap in --self-test enforces this.

Deterministic; stdlib only; source-clean.  Outputs are the four authorized Lane D
paths only.  Run --self-test before trusting the build.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate_canonical_hover_payload_table import (  # noqa: E402
    payload_id,
    binding_id,
    validate_payload,
    validate_binding,
)
from tools import rebind_canonical_hover as rebind  # noqa: E402

# --- pinned inputs --------------------------------------------------------
BASELINE_WHITELIST_SHA = (
    "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
)
DEFAULT_WHITELIST = os.path.join("C:\\", "workspace", "ai",
                                 "baseline-whitelist-972263b5.jsonl")
PLAN_PATH = os.path.join(ROOT, "qamus", "indexes", "largelexicon",
                         "crosswalk-gap", "lane-d-morphline-plan.jsonl")
ENTRIES_PATH = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")

# --- authorized outputs ---------------------------------------------------
OUT_DIR = os.path.join(ROOT, "qamus", "indexes", "largelexicon",
                       "crosswalk-gap", "lane-d")
OUT_PACKETS = os.path.join(OUT_DIR, "authoring-packets.jsonl")
OUT_EXEMPLARS = os.path.join(OUT_DIR, "convention-exemplars.jsonl")
OUT_RM20 = os.path.join(OUT_DIR, "rm20-dryrun-reports.jsonl")

PACKET_SCHEMA = "qamus.lane_d_morphline_author_packet.v1"
EXEMPLAR_SCHEMA = "qamus.lane_d_convention_exemplar.v1"
RM20_SCHEMA = "qamus.lane_d_rm20_dryrun.v1"
PAYLOAD_SCHEMA = "qamus.canonical_hover_payload.v2"
BINDING_SCHEMA = "qamus.canonical_hover_occurrence_binding.v2"

# Nearest-analog convention exemplars: aim for a dozen; a binding whose segment-class
# shape yields fewer than this many non-empty-morphline live rows fails the brief's
# stop condition and is reported (never fabricated up to count).
EXEMPLAR_TARGET = 12
EXEMPLAR_MINIMUM = 10

# Placeholder trap: unambiguous stand-in tokens that must never appear in a value.
# Chosen so they cannot collide with real Arabic surfaces or English glosses / the
# authoring-schema prose this tool legitimately emits.
PLACEHOLDER_TOKENS = (
    "todo", "tbd", "fixme", "placeholder", "lorem", "xxxx", "<fill>", "fill_me",
    "fill-me", "dummy", "tk_tk", "to-be-filled", "to_be_filled", "???",
)
# Fields a LATER author supplies; they must never carry a value inside a packet body.
AUTHOR_ANSWER_KEYS = ("proposed_morphline", "rationale", "confidence")


# --- small io helpers -----------------------------------------------------
def read_jsonl(path: str) -> list[dict[str, Any]]:
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("%s:%d: invalid JSON: %s" % (path, number, exc)) from exc
    return rows


def write_jsonl(path: str, rows: list[dict[str, Any]]) -> None:
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_canonical(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def sha_file(path: str) -> str:
    digest = hashlib.sha256()
    with io.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short(prefix: str, value: Any) -> str:
    return prefix + sha_canonical(value)[:12]


# --- shape + segment helpers ---------------------------------------------
def segment_class_shape(segments: list[dict[str, Any]]) -> list[str]:
    return [seg.get("class") for seg in (segments or [])]


def to_canonical_segments(wl_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map baseline whitelist segments to canonical-hover payload segments."""
    out = []
    for seg in wl_segments or []:
        out.append({
            "role": seg.get("role") or "",
            "surface": seg.get("surface"),
            "qg_class": seg.get("class"),
            "gloss": seg.get("gloss_contribution"),
        })
    return out


# --- placeholder trap -----------------------------------------------------
def find_placeholders(value: Any, path: str = "") -> list[str]:
    """Return dotted paths whose string value contains a placeholder token."""
    hits: list[str] = []
    if isinstance(value, dict):
        for key, sub in value.items():
            hits.extend(find_placeholders(sub, "%s.%s" % (path, key)))
    elif isinstance(value, list):
        for index, sub in enumerate(value):
            hits.extend(find_placeholders(sub, "%s[%d]" % (path, index)))
    elif isinstance(value, str):
        low = value.lower()
        for token in PLACEHOLDER_TOKENS:
            if token in low:
                hits.append("%s -> %r (token %r)" % (path.lstrip("."), value, token))
    return hits


def find_author_answer_values(value: Any, path: str = "",
                              under_schema: bool = False) -> list[str]:
    """Return paths where an author-answer key carries a value in the packet body.

    The declarative ``author_response_schema`` subtree is exempt: it *names* the
    fields as a spec (their descriptions are allowed), it does not answer them.
    """
    hits: list[str] = []
    if isinstance(value, dict):
        for key, sub in value.items():
            child_schema = under_schema or (key == "author_response_schema")
            if key in AUTHOR_ANSWER_KEYS and not under_schema and sub is not None:
                hits.append("%s.%s = %r" % (path, key, sub))
            hits.extend(find_author_answer_values(sub, "%s.%s" % (path, key), child_schema))
    elif isinstance(value, list):
        for index, sub in enumerate(value):
            hits.extend(find_author_answer_values(sub, "%s[%d]" % (path, index), under_schema))
    return hits


# --- exemplar selection ---------------------------------------------------
def select_exemplars(rows_by_shape: dict[tuple, list[dict[str, Any]]],
                     shape: tuple) -> list[dict[str, Any]]:
    """Deterministically pick the most-representative non-empty-morphline live rows.

    Ordering: distinct morphline strings ranked by (occurrence count DESC, morphline
    ASC); for each, the representative live row is the one with the lexicographically
    smallest loc.  Take up to EXEMPLAR_TARGET distinct conventions.  Fully determined
    by the pinned baseline; independent of input order.
    """
    rows = rows_by_shape.get(shape, [])
    by_morphline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_morphline[row["morphline"]].append(row)
    counts = {ml: len(rs) for ml, rs in by_morphline.items()}
    ordered_morphlines = sorted(counts, key=lambda ml: (-counts[ml], ml))
    exemplars = []
    for rank, morphline in enumerate(ordered_morphlines[:EXEMPLAR_TARGET], 1):
        rep = min(by_morphline[morphline], key=lambda r: r["loc"])
        exemplars.append({
            "schema": EXEMPLAR_SCHEMA,
            "segment_class_shape": list(shape),
            "rank": rank,
            "exemplar_id": short("ex:", {"shape": list(shape), "loc": rep["loc"],
                                         "morphline": morphline}),
            "exemplar_loc": rep["loc"],
            "exemplar_surface": rep.get("surface"),
            "exemplar_morphline": morphline,
            "exemplar_morphline_occurrences": counts[morphline],
            "exemplar_segments": rep.get("segments"),
            "selection_key": "(-occurrences,morphline,min_loc)",
        })
    return exemplars


# --- entry material -------------------------------------------------------
def entry_material(entry: dict[str, Any], loc: str) -> dict[str, Any]:
    ayah = ":".join(loc.split(":")[:2])
    documented = []
    for group in entry.get("usage") or []:
        for example in group.get("examples") or []:
            if example.get("ref") == ayah:
                documented.append({
                    "ref": example.get("ref"),
                    "ar": example.get("ar"),
                    "en": example.get("en"),
                })
    return {
        "entry_id": entry.get("id"),
        "headword": entry.get("headword"),
        "root": entry.get("root"),
        "root_translit": entry.get("root_translit"),
        "translit": entry.get("translit"),
        "category": entry.get("category"),
        "section": entry.get("section"),
        "definition": entry.get("definition"),
        "meaning": entry.get("meaning"),
        "notes": entry.get("notes"),
        "senses": entry.get("senses"),
        "documented_at_address": {"ayah": ayah, "examples": documented},
    }


AUTHOR_RESPONSE_SCHEMA = {
    "note": ("Filled ONLY by a LATER independent author under the RM-20 two-vote gate; "
             "this packet supplies inputs and evidence, never an answer."),
    "gate": ("two_vote required (both votes must agree on value AND reason) per "
             "lane-cd.summary repair_wave_design.gate_step"),
    "fields": {
        "proposed_morphline": {
            "type": "string",
            "must_follow": ("the documented morphline convention: a narrative description "
                            "of the whole token's grammatical composition, matching the "
                            "register of the cited convention exemplars"),
        },
        "rationale": {
            "type": "string",
            "must_cite": ["convention exemplar ids / addresses",
                          "this binding's own segments"],
        },
        "abstention_or_blocker": {"type": ["string", "null"]},
        "confidence": {"type": "number", "range": [0, 1]},
        "evidence_hashes": {"type": "array",
                            "note": "author echoes the packet evidence_hashes actually used"},
    },
}


# --- build ----------------------------------------------------------------
def build(whitelist_path: str) -> tuple[list, list, list, dict]:
    actual_sha = sha_file(whitelist_path)
    if actual_sha != BASELINE_WHITELIST_SHA:
        raise ValueError("baseline whitelist sha mismatch: expected %s got %s"
                         % (BASELINE_WHITELIST_SHA, actual_sha))

    plan = read_jsonl(PLAN_PATH)
    target_locs = {row["loc"] for row in plan}
    target_shapes = {tuple(segment_class_shape(row["evidence"]["live_segments"]))
                     for row in plan}

    entry_ids = {row["entry_id"] for row in plan}
    entries: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(ENTRIES_PATH):
        if row.get("id") in entry_ids:
            entries[row["id"]] = row

    # one pass over the pinned baseline: capture target rows + shape exemplar pools
    wl_by_loc: dict[str, dict[str, Any]] = {}
    rows_by_shape: dict[tuple, list[dict[str, Any]]] = {s: [] for s in target_shapes}
    with io.open(whitelist_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            loc = row.get("loc")
            if loc in target_locs:
                wl_by_loc[loc] = row
            shape = tuple(segment_class_shape(row.get("segments")))
            if shape in rows_by_shape and (row.get("morphline") or "").strip():
                if loc not in target_locs:  # never let a target seed its own exemplars
                    rows_by_shape[shape].append(row)

    exemplars_by_shape = {shape: select_exemplars(rows_by_shape, shape)
                          for shape in target_shapes}

    # exemplars file (deterministic order)
    exemplar_rows = []
    for shape in sorted(target_shapes):
        exemplar_rows.extend(exemplars_by_shape[shape])

    # packets, one per binding
    packets = []
    for plan_row in plan:
        loc = plan_row["loc"]
        wl = wl_by_loc[loc]
        shape = tuple(segment_class_shape(plan_row["evidence"]["live_segments"]))
        exemplars = exemplars_by_shape[shape]
        entry = entries[plan_row["entry_id"]]
        mat = entry_material(entry, loc)

        live_row = {
            "schema": wl.get("schema"),
            "loc": wl.get("loc"),
            "quran_loc": wl.get("quran_loc"),
            "wbw_loc": wl.get("wbw_loc"),
            "card_ref": wl.get("card_ref"),
            "surface": wl.get("surface"),
            "surface_norm": wl.get("surface"),
            "morphline": wl.get("morphline"),
            "token_contribution_gloss": wl.get("token_contribution_gloss"),
            "contextual_phrase_gloss": wl.get("contextual_phrase_gloss"),
            "learner_explanation": wl.get("learner_explanation"),
            "public_preview": wl.get("public_preview"),
            "segments": wl.get("segments"),
        }

        sufficient = len(exemplars) >= EXEMPLAR_MINIMUM
        blocker = None
        if not sufficient:
            blocker = {
                "reason": "insufficient_convention_exemplars",
                "detail": ("only %d exact segment-class-shape %s live rows carry a "
                           "non-empty morphline in the hash-pinned baseline; the brief "
                           "requires >=%d structurally-analogous exemplars"
                           % (len(exemplars), list(shape), EXEMPLAR_MINIMUM)),
                "available": len(exemplars),
                "required": EXEMPLAR_MINIMUM,
                "stop_condition": "BRIEF: STOP if fewer than 10 structurally-analogous exemplars",
            }

        exemplar_ids = [ex["exemplar_id"] for ex in exemplars]
        evidence_hashes = {
            "baseline_whitelist_sha256": BASELINE_WHITELIST_SHA,
            "live_row_sha256": sha_canonical(wl),
            "entry_material_sha256": sha_canonical(mat),
            "plan_row_sha256": sha_canonical(plan_row),
            "convention_exemplars_sha256": sha_canonical(exemplars),
        }

        packet = {
            "schema": PACKET_SCHEMA,
            "wave": "RM-20",
            "review_route": plan_row.get("review_route"),
            "packet_id": short("pkt:", {
                "loc": loc, "entry_id": plan_row["entry_id"],
                "card_id": plan_row["card_id"], "qword_row_id": plan_row["qword_row_id"]}),
            "carrier": {
                "loc": loc,
                "entry_id": plan_row["entry_id"],
                "card_id": plan_row["card_id"],
                "qword_row_id": plan_row["qword_row_id"],
            },
            "target_segment_class_shape": list(shape),
            "derivability_verdict": plan_row.get("derivability_verdict"),
            "live_row": live_row,
            "segments": wl.get("segments"),
            "entry_material": mat,
            "convention_exemplars": {
                "segment_class_shape": list(shape),
                "exemplar_count": len(exemplars),
                "minimum_required": EXEMPLAR_MINIMUM,
                "sufficient": sufficient,
                "exemplar_ids": exemplar_ids,
                "source_file": "convention-exemplars.jsonl",
            },
            "author_response_schema": AUTHOR_RESPONSE_SCHEMA,
            "abstention_or_blocker": blocker,
            "evidence_hashes": evidence_hashes,
        }
        packets.append(packet)

    packets.sort(key=lambda p: (p["carrier"]["loc"], p["carrier"]["card_id"],
                                p["carrier"]["qword_row_id"]))

    # RM-20 dry-run reports, one per DISTINCT canonical payload (the true repair unit).
    # Content-addressed payloads collapse byte-identical live rows across locations, so
    # two of the fifteen surfaces recur (بِوَٰلِدَيْهِ, لِلَّهِ); a single repair of the
    # shared payload rebinds every occurrence at every location it serves. Grouping by
    # payload (not loc) reports the true blast radius rather than splitting it.
    payload_by_id: dict[str, dict[str, Any]] = {}
    bindings_by_payload: dict[str, list[dict[str, Any]]] = defaultdict(list)
    locs_by_payload: dict[str, set] = defaultdict(set)
    for plan_row in plan:
        loc = plan_row["loc"]
        wl = wl_by_loc[loc]
        old_payload = build_payload(wl)
        old_id = old_payload["canonical_payload_id"]
        payload_by_id.setdefault(old_id, old_payload)
        bindings_by_payload[old_id].append(
            build_binding(old_id, wl, plan_row, entries[plan_row["entry_id"]]))
        locs_by_payload[old_id].add(loc)

    rm20_rows = []
    for old_id in sorted(payload_by_id):
        old_payload = payload_by_id[old_id]
        bindings = sorted(bindings_by_payload[old_id], key=lambda b: b["binding_id"])
        shape = tuple(segment_class_shape(old_payload["public_payload"]["segments"]))

        new_payload = copy.deepcopy(old_payload)
        # Dry-run preview marker: any authored morphline supersedes the empty-morphline
        # payload; the touched OLD bindings (the blast radius) are text-independent.
        # We stamp the repair wave (a truthful provenance fact, not a morphline value)
        # so the superseding payload has a distinct content address without inventing
        # linguistic content the two-vote authoring lane must supply.
        new_payload["public_payload"]["morphline_repair_wave"] = "RM-20"
        new_payload["canonical_payload_id"] = payload_id(new_payload)

        report = rebind.build_rebind_report([old_payload], bindings, old_id, new_payload)
        verify_errors = rebind.verify_dataset([old_payload], bindings, report)
        if verify_errors:
            raise AssertionError("RM-20 dry-run verify failed for %s: %s"
                                 % (old_id, verify_errors))

        rebind_by_old = {item["old_binding"]["binding_id"]: item["new_binding"]["binding_id"]
                         for item in report["binding_rebinds"]}
        touched = []
        for b in bindings:
            touched.append({
                "loc": b["canonical_wbw_loc"],
                "entry_id": b["entry_id"],
                "card_id": b["card_id"],
                "qword_row_id": b["qword_row_id"],
                "old_binding_id": b["binding_id"],
                "new_binding_id": rebind_by_old[b["binding_id"]],
            })
        touched.sort(key=lambda t: (t["loc"], t["card_id"], t["qword_row_id"]))

        rm20_rows.append({
            "schema": RM20_SCHEMA,
            "wave": "RM-20",
            "locs": sorted(locs_by_payload[old_id]),
            "segment_class_shape": list(shape),
            "surface": old_payload["surface_norm"],
            "old_payload_id": old_id,
            "new_payload_id": new_payload["canonical_payload_id"],
            "new_payload_marker": ("public_payload.morphline_repair_wave=RM-20 "
                                   "(dry-run rebind preview; authored morphline deferred "
                                   "to the two-vote lane; touched OLD bindings are "
                                   "text-independent)"),
            "bindings_touched": touched,
            "summary": report["summary"],
            "verify_status": "PASS",
            "dry_run_report": report,
        })

    build_report = {
        "packets": len(packets),
        "locations": len({l for r in rm20_rows for l in r["locs"]}),
        "distinct_payloads": len(rm20_rows),
        "bindings_covered": sum(r["summary"]["dependent_bindings"] for r in rm20_rows),
        "shared_payloads": sorted(
            {"payload_id": r["old_payload_id"], "surface": r["surface"], "locs": r["locs"]}[
                "surface"] for r in rm20_rows if len(r["locs"]) > 1),
        "exemplar_rows": len(exemplar_rows),
        "exemplars_by_shape": {"|".join(s): len(exemplars_by_shape[s])
                               for s in sorted(target_shapes)},
        "insufficient_exemplar_bindings": sorted(
            p["carrier"]["card_id"] + "@" + p["carrier"]["loc"]
            for p in packets if p["abstention_or_blocker"]),
        "baseline_whitelist_sha256": actual_sha,
    }
    return packets, exemplar_rows, rm20_rows, build_report


def build_payload(wl: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": PAYLOAD_SCHEMA,
        "payload_family": "source_address_exact",
        "surface_norm": wl.get("surface"),
        "root": None,
        "lemma_id": None,
        "lemma_status": "missing",
        "pos": None,
        "pattern": None,
        "sarf_certification": "missing",
        "nahw_certification": "missing",
        "public_payload": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "token_contribution_gloss": wl.get("token_contribution_gloss"),
            "contextual_phrase_gloss": wl.get("contextual_phrase_gloss"),
            "morphline": wl.get("morphline") or "",
            "segments": to_canonical_segments(wl.get("segments")),
            "learner_explanation": wl.get("learner_explanation"),
        },
    }
    payload["canonical_payload_id"] = payload_id(payload)
    errors = validate_payload(payload)
    if errors:
        raise AssertionError("constructed payload invalid at %s: %s" % (wl.get("loc"), errors))
    return payload


def _card_indices(card_id: str) -> tuple[Any, Any]:
    sense_index = card_index = None
    try:
        parts = card_id.split(":")
        for part in parts:
            if part.startswith("u") and part[1:].isdigit():
                sense_index = int(part[1:])
            elif part.startswith("e") and part[1:].isdigit():
                card_index = int(part[1:])
    except Exception:
        pass
    return sense_index, card_index


def build_binding(payload_id_value: str, wl: dict[str, Any],
                  plan_row: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    loc = plan_row["loc"]
    surface = wl.get("surface")
    sense_index, card_index = _card_indices(plan_row["card_id"])
    dep = sha_canonical({"whitelist_row": wl, "entry_id": entry.get("id"),
                         "qword_row_id": plan_row["qword_row_id"]})
    binding = {
        "schema": BINDING_SCHEMA,
        "canonical_payload_id": payload_id_value,
        "entry_id": plan_row["entry_id"],
        "entry_url": None,
        "source_key": "qamus",
        "sense_index": sense_index,
        "card_index": card_index,
        "card_id": plan_row["card_id"],
        "qword_row_id": plan_row["qword_row_id"],
        "source_dependency_sha256": dep,
        "visible_surface": surface,
        "canonical_quran_loc": loc,
        "canonical_wbw_loc": loc,
        "exact_transclusion_group_key": "quran:%s|%s" % (loc, surface),
        "binding_status": "accepted",
        "binding_gate": "source_address_exact",
        "reason": "source_address_exact_ok",
        "exception_id": None,
    }
    binding["binding_id"] = binding_id(binding)
    errors = validate_binding(binding, {payload_id_value: "missing"})
    if errors:
        raise AssertionError("constructed binding invalid at %s: %s" % (loc, errors))
    return binding


# --- self-test ------------------------------------------------------------
def _synthetic_shape_pool():
    shape = ("qg-preposition",)
    rows = []
    # 3 distinct morphlines with descending frequency + a same-morphline dup at
    # differing locs so we can assert min-loc representative selection.
    freq = {"preposition - no lexical root": 5,
            "built preposition - no root": 3,
            "preposition fi - function token": 1}
    idx = 0
    for morphline, n in freq.items():
        for k in range(n):
            idx += 1
            rows.append({"loc": "%02d:%02d:%02d" % (idx, k, 1), "surface": "sfx",
                         "morphline": morphline,
                         "segments": [{"class": "qg-preposition", "surface": "sfx",
                                       "gloss_contribution": "x", "role": "", "label": "",
                                       "segment_index": 0}]})
    return {shape: rows}, shape


def self_test() -> int:
    # 1. exemplar-selection determinism + ordering
    pool, shape = _synthetic_shape_pool()
    a = select_exemplars(pool, shape)
    b = select_exemplars(copy.deepcopy(pool), shape)
    if a != b:
        print("SELF-TEST FAIL exemplar determinism"); return 1
    occ = [ex["exemplar_morphline_occurrences"] for ex in a]
    if occ != sorted(occ, reverse=True):
        print("SELF-TEST FAIL exemplar ordering not by descending occurrence:", occ); return 1
    if [ex["exemplar_morphline"] for ex in a][0] != "preposition - no lexical root":
        print("SELF-TEST FAIL exemplar rank-1 not most frequent"); return 1
    # representative loc is the min loc for its morphline
    top = a[0]
    mins = min(r["loc"] for r in pool[shape] if r["morphline"] == top["exemplar_morphline"])
    if top["exemplar_loc"] != mins:
        print("SELF-TEST FAIL representative not min-loc"); return 1
    # ordering is input-order independent
    shuffled = {shape: list(reversed(pool[shape]))}
    if select_exemplars(shuffled, shape) != a:
        print("SELF-TEST FAIL exemplar input-order dependence"); return 1

    # 2. placeholder trap catches a planted token and passes a clean packet
    clean = {"live_row": {"morphline": "", "learner_explanation": "'to purify' - a particle."},
             "author_response_schema": AUTHOR_RESPONSE_SCHEMA,
             "carrier": {"loc": "5:6:56"}}
    if find_placeholders(clean):
        print("SELF-TEST FAIL clean packet flagged:", find_placeholders(clean)); return 1
    planted = copy.deepcopy(clean)
    planted["live_row"]["morphline"] = "TODO author me"
    if not find_placeholders(planted):
        print("SELF-TEST FAIL placeholder not caught"); return 1

    # 3. author-answer trap: schema spec is exempt, body value is not
    if find_author_answer_values(clean):
        print("SELF-TEST FAIL schema spec wrongly flagged:", find_author_answer_values(clean)); return 1
    leaky = copy.deepcopy(clean)
    leaky["proposed_morphline"] = "purpose lam + verb"
    if not find_author_answer_values(leaky):
        print("SELF-TEST FAIL author-answer value not caught"); return 1

    # 4. RM-20 dry-run mechanics on synthetic payload/bindings verify clean
    wl = {"loc": "2:2:2", "surface": "الكتاب", "morphline": "",
          "token_contribution_gloss": "the book", "contextual_phrase_gloss": None,
          "learner_explanation": "article + noun",
          "segments": [{"class": "definite_article", "surface": "ال", "gloss_contribution": "the",
                        "role": "", "label": "", "segment_index": 0},
                       {"class": "qg-noun", "surface": "كتاب", "gloss_contribution": "book",
                        "role": "", "label": "", "segment_index": 1}]}
    entry = {"id": "n0030"}
    old = build_payload(wl)
    pr1 = {"loc": "2:2:2", "entry_id": "n0030", "card_id": "n0030:u1:e1",
           "qword_row_id": "q1"}
    pr2 = {"loc": "2:2:2", "entry_id": "n0030", "card_id": "n0030:u1:e2",
           "qword_row_id": "q2"}
    binds = [build_binding(old["canonical_payload_id"], wl, pr1, entry),
             build_binding(old["canonical_payload_id"], wl, pr2, entry)]
    new = copy.deepcopy(old)
    new["public_payload"]["morphline_repair_wave"] = "RM-20"
    new["canonical_payload_id"] = payload_id(new)
    if new["canonical_payload_id"] == old["canonical_payload_id"]:
        print("SELF-TEST FAIL marker did not change payload id"); return 1
    report = rebind.build_rebind_report([old], binds, old["canonical_payload_id"], new)
    if rebind.verify_dataset([old], binds, report):
        print("SELF-TEST FAIL rm20 verify:", rebind.verify_dataset([old], binds, report)); return 1
    if report["summary"]["dependent_bindings"] != 2:
        print("SELF-TEST FAIL rm20 dependent count"); return 1

    # 5. stop-condition detection: <10 exemplars is insufficient, >=10 sufficient
    if EXEMPLAR_MINIMUM <= len(a) < EXEMPLAR_TARGET + 1 and len(a) >= EXEMPLAR_MINIMUM:
        pass
    small = {("qg-lam",): pool[shape][:2]}
    if len(select_exemplars(small, ("qg-lam",))) >= EXEMPLAR_MINIMUM:
        print("SELF-TEST FAIL small pool wrongly sufficient"); return 1

    print("PASS - build_morphline_author_packets self-test")
    return 0


def _assert_build_invariants(packets, exemplar_rows, rm20_rows, report) -> None:
    if len(packets) != 32:
        raise AssertionError("expected 32 packets, got %d" % len(packets))
    covered = sum(r["summary"]["dependent_bindings"] for r in rm20_rows)
    if covered != 32:
        raise AssertionError("expected 32 bindings covered, got %d" % covered)
    all_touched = [(t["loc"], t["card_id"], t["qword_row_id"])
                   for r in rm20_rows for t in r["bindings_touched"]]
    if len(set(all_touched)) != 32:
        raise AssertionError("expected 32 distinct touched bindings, got %d"
                             % len(set(all_touched)))
    for packet in packets:
        placeholders = find_placeholders({k: v for k, v in packet.items()
                                          if k != "author_response_schema"})
        if placeholders:
            raise AssertionError("placeholder in packet %s: %s"
                                 % (packet["packet_id"], placeholders))
        answers = find_author_answer_values(packet)
        if answers:
            raise AssertionError("author-answer value in packet %s: %s"
                                 % (packet["packet_id"], answers))
        for key in ("carrier", "live_row", "entry_material", "convention_exemplars",
                    "evidence_hashes", "author_response_schema"):
            if key not in packet:
                raise AssertionError("packet %s missing %s" % (packet["packet_id"], key))
        for field in ("loc", "entry_id", "card_id", "qword_row_id"):
            if not packet["carrier"].get(field):
                raise AssertionError("packet %s carrier missing %s"
                                     % (packet["packet_id"], field))
        if not packet["entry_material"]["documented_at_address"]["examples"]:
            raise AssertionError("packet %s has no documented material at its address"
                                 % packet["packet_id"])
        for name, digest in packet["evidence_hashes"].items():
            if not (isinstance(digest, str) and len(digest) == 64):
                raise AssertionError("packet %s bad evidence hash %s"
                                     % (packet["packet_id"], name))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--whitelist", default=DEFAULT_WHITELIST,
                        help="hash-pinned baseline whitelist local copy (972263b5...)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    packets, exemplar_rows, rm20_rows, report = build(args.whitelist)
    _assert_build_invariants(packets, exemplar_rows, rm20_rows, report)
    os.makedirs(OUT_DIR, exist_ok=True)
    write_jsonl(OUT_PACKETS, packets)
    write_jsonl(OUT_EXEMPLARS, exemplar_rows)
    write_jsonl(OUT_RM20, rm20_rows)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
