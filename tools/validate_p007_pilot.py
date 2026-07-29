#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P007_LI_NOUN_HOST_PILOT gate — red-first validator for the vertical-slice
closure under ``qamus/examples/p007-li-pilot/``.

Gates (all mechanical, stdlib only, no network, no live reads):

1. 12-location integrity — locations.json, family-selection.json, typed facts,
   projections, both two-vote files, morpheme occurrences and the reverse index
   all agree on exactly the same 12 canonical occurrence ids; 78 appearance
   links total (n:22 / v:54 / p:2); the 3 rejected false candidates each carry
   a defeater.
2. 49-fact table completeness — typed-facts.jsonl holds exactly the 12 x
   {seg,func,gov,case} + 1 entry-level rootlessness facts, each with an
   evidence policy (evidence_mode + source addresses + exactly one verbatim
   source quotation) — and the hash-chained certification store certifies all
   49 (``tools/certify_typed_fact.py`` trail validation + count).
3. Entry-transclusion closure — EVERY certified morpheme occurrence carries the
   explicit entry edge (-> entry:b10a1ee04666) AND sense edge
   (-> sense:b10a1ee04666:2) AND clitic_host_edge AND governor_edge AND
   governed_expression_edge; a generic 'preposition' class without the
   entry/sense edge does NOT satisfy transclusion. Certified edges carry
   evidence bundle refs; iʿrāb-bearing edges carry two-vote artifact refs;
   morpheme occurrences carry base-letter spans.
4. Parity hash stability — every canonical projection hash recomputes
   byte-identically (sorted-keys canonical JSON sha256); all 78 appearance
   hashes equal their occurrence's canonical hash; NFC-normalized segment
   concatenation equals the NFC token surface (the shadda/vowel-order lesson).
5. Reverse-trace closure — every projection's declared fact set exists and is
   certified; its two-vote artifact exists in BOTH the v1 file (consumed by the
   certifier) and the v1.1 migration; its MCP evidence anchor exists verbatim;
   its live row capture exists; the entry reverse index closes over the same
   12 occurrences and 78 appearances. Both two-vote files pass
   ``tools/validate_two_vote_artifacts.py`` and the v1.1 migration keeps vote
   substance untouched (segmentation, reason keys, governor, case value).
6. Production-difference honesty — the NOT-DEPLOYED table has all 12 rows,
   exactly 2 carve-fork verdicts and 12 colour-class deltas, and every row
   names a rollback unit.

Red-first: ``--self-test`` mutates each gated property in a temp copy and
requires the validator to reject it, then requires the committed pilot to pass.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PILOT_DIR = os.path.join(ROOT, "qamus", "examples", "p007-li-pilot")

SCOPE = "P007_LI_NOUN_HOST_PILOT"
ENTRY_ID = "b10a1ee04666"
ENTRY_NODE = "entry:%s" % ENTRY_ID
SENSE_NODE = "sense:%s:2" % ENTRY_ID
EXPECTED_OCCURRENCES = 12
EXPECTED_APPEARANCES = 78
EXPECTED_PAGE_CLASSES = {"context_on_n": 22, "context_on_v": 54, "context_on_p": 2}
EXPECTED_FACTS = 49
EXPECTED_REJECTED = 3
FACT_SUFFIXES = ("seg", "func", "gov", "case")
ROOTLESS_FACT = "fact:p00slice:entry_%s:rootless" % ENTRY_ID
REQUIRED_EDGE_KINDS = (
    "particle_entry_certified_edge",
    "particle_sense_certified_edge",
    "clitic_host_edge",
    "governor_edge",
    "governed_expression_edge",
)
IRAB_EDGE_KINDS = {"governor_edge", "governed_expression_edge"}
REVERSE_EDGE_KIND = "particle_entry_reverse_occurrence_edge"


def nfc(text):
    return unicodedata.normalize("NFC", text)


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def canonical_hash(projection):
    payload = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fact_ids_for(loc_key_us):
    return ["fact:p00slice:%s:%s" % (loc_key_us, suffix) for suffix in FACT_SUFFIXES]


def validate(pilot_dir):
    errors = []

    def err(message):
        errors.append(message)

    required_files = [
        "locations.json", "family-selection.json", "candidate-lattice.jsonl",
        "typed-facts.jsonl", "mcp-evidence.jsonl", "votes-a.jsonl",
        "votes-b.jsonl", "votes-b-mcp-calls.jsonl", "reviewer-b-worklist.json",
        "two-vote-artifacts.v1.jsonl", "two-vote-artifacts.v1_1.jsonl",
        "migration-provenance.json", "projections.jsonl", "parity-report.json",
        "reverse-trace.json", "morpheme-occurrences.jsonl",
        "transclusion-edges.jsonl", "entry-reverse-index.json",
        "production-difference.json", "vn-unlock.json", "live-rows.jsonl",
        os.path.join("certification", "events.jsonl"),
    ]
    for name in required_files:
        if not os.path.exists(os.path.join(pilot_dir, name)):
            err("missing pilot artifact: %s" % name)
    if errors:
        return errors

    locations = read_json(os.path.join(pilot_dir, "locations.json"))
    family = read_json(os.path.join(pilot_dir, "family-selection.json"))
    typed_facts = read_jsonl(os.path.join(pilot_dir, "typed-facts.jsonl"))
    projections = read_jsonl(os.path.join(pilot_dir, "projections.jsonl"))
    v1_rows = read_jsonl(os.path.join(pilot_dir, "two-vote-artifacts.v1.jsonl"))
    v11_rows = read_jsonl(os.path.join(pilot_dir, "two-vote-artifacts.v1_1.jsonl"))
    morphemes = read_jsonl(os.path.join(pilot_dir, "morpheme-occurrences.jsonl"))
    edges = read_jsonl(os.path.join(pilot_dir, "transclusion-edges.jsonl"))
    reverse_index = read_json(os.path.join(pilot_dir, "entry-reverse-index.json"))
    reverse_trace = read_json(os.path.join(pilot_dir, "reverse-trace.json"))
    production = read_json(os.path.join(pilot_dir, "production-difference.json"))
    mcp_evidence = read_jsonl(os.path.join(pilot_dir, "mcp-evidence.jsonl"))
    live_rows = read_jsonl(os.path.join(pilot_dir, "live-rows.jsonl"))

    # ---- gate 1: 12-location integrity -----------------------------------
    if locations.get("scope") != SCOPE:
        err("locations.json scope must be %s" % SCOPE)
    loc_ids = [occ["occurrence_id"] for occ in locations.get("occurrences", [])]
    if len(loc_ids) != EXPECTED_OCCURRENCES or len(set(loc_ids)) != EXPECTED_OCCURRENCES:
        err("locations.json must list exactly %d distinct occurrences (found %d)"
            % (EXPECTED_OCCURRENCES, len(loc_ids)))
    family_ids = [occ["occurrence_id"] for occ in family.get("occurrences", [])]
    if set(loc_ids) != set(family_ids):
        err("locations.json occurrence set differs from family-selection.json")
    projection_ids = [row["projection"]["occurrence_id"] for row in projections]
    if set(projection_ids) != set(loc_ids):
        err("projections.jsonl occurrence set differs from locations.json")
    for label, rows in (("v1", v1_rows), ("v1.1", v11_rows)):
        bundle_ids = [row["occurrence"]["quran_loc"] for row in rows]
        if set(bundle_ids) != set(loc_ids):
            err("two-vote %s occurrence set differs from locations.json" % label)
    total_appearances = 0
    for occ in locations.get("occurrences", []):
        ids = occ.get("appearance_ids", [])
        if len(ids) != occ.get("appearance_count"):
            err("%s appearance_count %r does not match its %d appearance links"
                % (occ["occurrence_id"], occ.get("appearance_count"), len(ids)))
        total_appearances += len(ids)
    if total_appearances != EXPECTED_APPEARANCES:
        err("total appearance links must be %d (found %d)" % (EXPECTED_APPEARANCES, total_appearances))
    page_classes = locations.get("population", {}).get("page_class_appearances")
    if page_classes != EXPECTED_PAGE_CLASSES:
        err("page-class appearance tally must be %r (found %r)" % (EXPECTED_PAGE_CLASSES, page_classes))
    rejected = locations.get("rejected_false_candidates", [])
    if len(rejected) != EXPECTED_REJECTED:
        err("exactly %d rejected false candidates required (found %d)" % (EXPECTED_REJECTED, len(rejected)))
    for row in rejected:
        if not (row.get("defeater") or "").strip():
            err("rejected candidate %s has no defeater" % row.get("occurrence_id"))
    if locations.get("not_deployed") is not True:
        err("locations.json must carry not_deployed: true (candidate mode)")

    # ---- gate 2: 49-fact completeness + certification store ---------------
    fact_by_id = {row["fact_id"]: row for row in typed_facts}
    expected_fact_ids = {ROOTLESS_FACT}
    for occurrence_id in loc_ids:
        loc_us = occurrence_id.split(":", 1)[1].replace(":", "_")
        expected_fact_ids.update(fact_ids_for(loc_us))
    if len(expected_fact_ids) != EXPECTED_FACTS:
        err("internal: expected fact-id set has %d members" % len(expected_fact_ids))
    missing = sorted(expected_fact_ids - set(fact_by_id))
    extra = sorted(set(fact_by_id) - expected_fact_ids)
    if missing:
        err("typed-facts.jsonl missing facts: %s" % ", ".join(missing[:5]))
    if extra:
        err("typed-facts.jsonl has unexpected facts: %s" % ", ".join(extra[:5]))
    for fact_id, fact in sorted(fact_by_id.items()):
        if not fact.get("evidence_mode"):
            err("%s has no evidence_mode (per-fact evidence policy required)" % fact_id)
        source_evidence = fact.get("source_evidence") or {}
        if not source_evidence.get("source_addresses"):
            err("%s has no source addresses" % fact_id)
        quotation = (source_evidence.get("source_quotation") or {}).get("text")
        if not (quotation or "").strip():
            err("%s has no verbatim source quotation" % fact_id)

    store_dir = os.path.join(pilot_dir, "certification")
    certify = os.path.join(ROOT, "tools", "certify_typed_fact.py")
    result = subprocess.run(
        [sys.executable, certify, "--validate", store_dir],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if result.returncode != 0 or "certification event trail is valid" not in (result.stdout or ""):
        err("certification store trail validation failed: %s"
            % ((result.stdout or "") + (result.stderr or "")).strip()[:400])
    result = subprocess.run(
        [sys.executable, certify, "--count", store_dir],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    try:
        certified_count = int((result.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        certified_count = -1
    if certified_count != EXPECTED_FACTS:
        err("certification store must certify exactly %d facts (found %d)"
            % (EXPECTED_FACTS, certified_count))

    # ---- gate 3: entry-transclusion closure -------------------------------
    morpheme_by_host = {}
    for row in morphemes:
        if row.get("schema") != "qamus.particle_morpheme_occurrence.v1":
            err("morpheme occurrence %r has wrong schema" % row.get("morpheme_occurrence_id"))
        span = row.get("base_letter_span") or {}
        if not (isinstance(span.get("start"), int) and isinstance(span.get("end"), int)
                and 0 <= span["start"] < span["end"]):
            err("morpheme occurrence %r has invalid base_letter_span" % row.get("morpheme_occurrence_id"))
        if not (row.get("component_surface") or "").strip():
            err("morpheme occurrence %r has no component_surface" % row.get("morpheme_occurrence_id"))
        morpheme_by_host[row.get("host_occurrence_id")] = row
    if set(morpheme_by_host) != set(loc_ids):
        err("morpheme-occurrences.jsonl host set differs from the 12 locations")

    edges_by_morpheme = {}
    reverse_edge_targets = set()
    for edge in edges:
        if edge.get("schema") != "qamus.graph_edge.v1":
            err("edge %r has wrong schema" % edge.get("edge_id"))
        details = edge.get("details") or {}
        if edge.get("status") == "certified" and not details.get("evidence_bundle_ref"):
            err("certified edge %r has no evidence_bundle_ref" % edge.get("edge_id"))
        kind = edge.get("edge_type")
        if kind in IRAB_EDGE_KINDS and edge.get("status") == "certified" \
                and not details.get("two_vote_artifact_ref"):
            err("certified iʿrāb-bearing edge %r has no two_vote_artifact_ref" % edge.get("edge_id"))
        if kind == "clitic_host_edge" and not details.get("component_surface"):
            err("clitic_host_edge %r has no component_surface" % edge.get("edge_id"))
        if kind == REVERSE_EDGE_KIND:
            if edge.get("from_node_id") != ENTRY_NODE:
                err("reverse occurrence edge %r must come from %s" % (edge.get("edge_id"), ENTRY_NODE))
            reverse_edge_targets.add((edge.get("to_node_id") or "").replace("occurrence:", "", 1))
            continue
        edges_by_morpheme.setdefault(edge.get("from_node_id"), {}).setdefault(kind, []).append(edge)

    for occurrence_id in loc_ids:
        morpheme = morpheme_by_host.get(occurrence_id)
        if morpheme is None:
            continue
        mocc_id = morpheme["morpheme_occurrence_id"]
        kinds = edges_by_morpheme.get(mocc_id, {})
        for kind in REQUIRED_EDGE_KINDS:
            rows = kinds.get(kind, [])
            if not rows:
                err("certified morpheme occurrence %s is missing its %s — a generic "
                    "'preposition' class without the entry/sense edge does not satisfy "
                    "entry transclusion" % (mocc_id, kind))
                continue
            if any(row.get("status") != "certified" for row in rows):
                err("%s on %s must be certified" % (kind, mocc_id))
        entry_edges = kinds.get("particle_entry_certified_edge", [])
        if entry_edges and any(row.get("to_node_id") != ENTRY_NODE for row in entry_edges):
            err("%s entry edge must target %s" % (mocc_id, ENTRY_NODE))
        sense_edges = kinds.get("particle_sense_certified_edge", [])
        if sense_edges and any(row.get("to_node_id") != SENSE_NODE for row in sense_edges):
            err("%s sense edge must target %s (p007 clitic sense لِـ)" % (mocc_id, SENSE_NODE))
    if reverse_edge_targets != set(loc_ids):
        err("entry reverse occurrence edges must cover exactly the 12 certified occurrences")

    # ---- gate 4: parity hash stability ------------------------------------
    for row in projections:
        projection = row["projection"]
        occurrence_id = projection["occurrence_id"]
        recomputed = canonical_hash(projection)
        if recomputed != row.get("projection_hash"):
            err("%s canonical projection hash does not recompute (stored %s, got %s)"
                % (occurrence_id, str(row.get("projection_hash"))[:12], recomputed[:12]))
        for appearance in row.get("appearances", []):
            if appearance.get("projection_hash") != row.get("projection_hash"):
                err("%s appearance %s forks from the canonical hash"
                    % (occurrence_id, appearance.get("appearance_id")))
        joined = nfc("".join(segment["surface"] for segment in projection["segments"]))
        if joined != nfc(projection["surface"]):
            err("%s NFC-joined segments %r do not rebuild the token surface %r"
                % (occurrence_id, joined, projection["surface"]))

    # ---- gate 5: reverse-trace closure ------------------------------------
    analyze_word_anchors = set()
    for record in mcp_evidence:
        if record.get("record") != "analyze_word":
            continue
        args = record.get("args")
        if isinstance(args, str):
            try:
                args = json.loads(args.replace("'", '"'))
            except ValueError:
                args = {}
        if isinstance(args, dict):
            analyze_word_anchors.add(
                "%s:%s:%s" % (args.get("surah"), args.get("ayah"), args.get("word_no")))
    live_blob = "\n".join(json.dumps(row, ensure_ascii=False) for row in live_rows)
    v1_by_id = {row["artifact_id"]: row for row in v1_rows}
    v11_by_id = {row["artifact_id"]: row for row in v11_rows}
    certified_fact_ids = set(fact_by_id)
    traced_projections = set()
    for record in reverse_trace:
        projection_id = record.get("projection_id") or ""
        traced_projections.add(projection_id)
        for fact_id in record.get("renders_from_facts", []):
            if fact_id not in certified_fact_ids:
                err("%s renders from unknown fact %s" % (projection_id, fact_id))
        artifact_ref = (record.get("two_vote_artifact") or "").split("#")[-1]
        if artifact_ref not in v1_by_id:
            err("%s cites a two-vote artifact absent from the v1 file: %s" % (projection_id, artifact_ref))
        if artifact_ref not in v11_by_id:
            err("%s cites a two-vote artifact absent from the v1.1 migration: %s" % (projection_id, artifact_ref))
        loc_digits = projection_id.replace("proj:p00slice:", "").replace("_", ":")
        if loc_digits not in analyze_word_anchors:
            err("%s has no verbatim MCP analyze_word anchor in mcp-evidence.jsonl" % projection_id)
        if '"%s"' % loc_digits not in live_blob and "'%s'" % loc_digits not in live_blob \
                and loc_digits not in live_blob:
            err("%s has no live row capture in live-rows.jsonl" % projection_id)
    expected_projection_ids = {
        "proj:p00slice:%s" % occurrence_id.split(":", 1)[1].replace(":", "_")
        for occurrence_id in loc_ids}
    if traced_projections != expected_projection_ids:
        err("reverse-trace.json must close over exactly the 12 canonical projections")

    validator = os.path.join(ROOT, "tools", "validate_two_vote_artifacts.py")
    for name in ("two-vote-artifacts.v1.jsonl", "two-vote-artifacts.v1_1.jsonl"):
        result = subprocess.run(
            [sys.executable, validator, os.path.join(pilot_dir, name)],
            capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        if result.returncode != 0:
            err("%s fails tools/validate_two_vote_artifacts.py:\n%s"
                % (name, ((result.stdout or "") + (result.stderr or "")).strip()[:600]))

    # v1 -> v1.1 substance equality (migration must not touch the votes).
    for artifact_id, v1_row in sorted(v1_by_id.items()):
        v11_row = v11_by_id.get(artifact_id)
        if v11_row is None:
            continue
        for index, (v1_vote, v11_vote) in enumerate(zip(v1_row["votes"], v11_row["votes"])):
            pairs = [
                ("segmentation", [
                    (s.get("segment_surface"), s.get("role")) for s in v1_vote["segmentation"]],
                 [(s.get("segment_surface"), s.get("role")) for s in v11_vote["segmentation"]]),
                ("reason_key", v1_vote.get("reason_key"), v11_vote.get("reason_key")),
                ("grammatical_reason", v1_vote.get("grammatical_reason"), v11_vote.get("grammatical_reason")),
                ("conclusion.contextual_function", v1_vote["conclusion"].get("contextual_function"),
                 v11_vote["conclusion"].get("contextual_function")),
                ("conclusion.governor", v1_vote["conclusion"].get("governor"),
                 v11_vote["conclusion"].get("governor")),
                ("conclusion.governed_expression", v1_vote["conclusion"].get("governed_expression"),
                 v11_vote["conclusion"].get("governed_expression")),
                ("conclusion.case_or_mood.value", v1_vote["conclusion"]["case_or_mood"].get("value"),
                 v11_vote["conclusion"]["case_or_mood"].get("value")),
            ]
            for label, before, after in pairs:
                if before != after:
                    err("%s votes[%d].%s changed during v1.1 migration (substance must be untouched)"
                        % (artifact_id, index, label))

    reverse_totals = reverse_index.get("totals", {})
    if reverse_totals.get("occurrences") != EXPECTED_OCCURRENCES \
            or reverse_totals.get("appearances") != EXPECTED_APPEARANCES:
        err("entry-reverse-index totals must be 12 occurrences / 78 appearances (found %r)" % reverse_totals)
    by_page_class = reverse_totals.get("by_page_class", {})
    if {"n": by_page_class.get("n"), "v": by_page_class.get("v"), "p": by_page_class.get("p")} != {
            "n": EXPECTED_PAGE_CLASSES["context_on_n"],
            "v": EXPECTED_PAGE_CLASSES["context_on_v"],
            "p": EXPECTED_PAGE_CLASSES["context_on_p"]}:
        err("entry-reverse-index page-class totals must be n:22 / v:54 / p:2 (found %r)" % by_page_class)
    if reverse_index.get("entry_id") != ENTRY_ID:
        err("entry-reverse-index must index entry %s" % ENTRY_ID)
    indexed = {occ["occurrence_id"] for occ in reverse_index.get("occurrences", [])}
    if indexed != set(loc_ids):
        err("entry-reverse-index occurrence set differs from the 12 locations")
    for occ in reverse_index.get("occurrences", []):
        grouped = occ.get("appearances_by_page_class", {})
        grouped_ids = sorted(a for ids in grouped.values() for a in ids)
        canonical = next((c for c in locations["occurrences"] if c["occurrence_id"] == occ["occurrence_id"]), None)
        if canonical is not None and grouped_ids != sorted(canonical["appearance_ids"]):
            err("entry-reverse-index appearance links for %s differ from locations.json" % occ["occurrence_id"])

    # ---- gate 6: production-difference honesty ----------------------------
    if production.get("not_deployed") is not True:
        err("production-difference.json must carry not_deployed: true")
    rows = production.get("rows", [])
    if {row.get("occurrence_id") for row in rows} != set(loc_ids):
        err("production-difference table must cover exactly the 12 occurrences")
    for row in rows:
        for field in ("current_public_carve", "candidate_carve", "current_colour_classes",
                      "candidate_colour_classes", "verdict", "required_change", "rollback_unit"):
            value = row.get(field)
            if value in (None, "", []):
                err("production-difference row %s is missing %s" % (row.get("occurrence_id"), field))
        if row.get("deployed") is not False:
            err("production-difference row %s must be marked deployed: false" % row.get("occurrence_id"))
    summary = production.get("summary", {})
    if summary.get("carve_forks") != 2:
        err("production-difference summary must record exactly the 2 live carve forks (found %r)"
            % summary.get("carve_forks"))
    if summary.get("colour_class_deltas") != 12:
        err("production-difference summary must record the 12 colour-class deltas (found %r)"
            % summary.get("colour_class_deltas"))

    return errors


# ---------------------------------------------------------------------------
# red-first self-test
# ---------------------------------------------------------------------------

def _copy_pilot(tmp_root):
    target = os.path.join(tmp_root, "p007-li-pilot")
    shutil.copytree(PILOT_DIR, target)
    return target


def _mutate_json(path, mutate):
    data = read_json(path)
    mutate(data)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False)
        handle.write("\n")


def _mutate_jsonl(path, mutate_rows):
    rows = read_jsonl(path)
    rows = mutate_rows(rows)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def self_test():
    failures = []

    def expect_red(name, mutator):
        with tempfile.TemporaryDirectory() as tmp_root:
            target = _copy_pilot(tmp_root)
            mutator(target)
            errors = validate(target)
            status = "ok  " if errors else "FAIL"
            print("%s red: %s" % (status, name))
            if not errors:
                failures.append(name)

    def drop_thirteenth_location(target):
        _mutate_json(os.path.join(target, "locations.json"),
                     lambda data: data["occurrences"].pop())

    def drop_fact(target):
        _mutate_jsonl(os.path.join(target, "typed-facts.jsonl"), lambda rows: rows[:-1])

    def drop_sense_edge(target):
        _mutate_jsonl(
            os.path.join(target, "transclusion-edges.jsonl"),
            lambda rows: [row for row in rows
                          if not (row["edge_type"] == "particle_sense_certified_edge"
                                  and row["details"]["occurrence_id"] == "quran:61:5:4")])

    def corrupt_projection_hash(target):
        def mutate(rows):
            rows[0]["projection"]["segments"][0]["colour_class"] = "qg-tampered"
            return rows
        _mutate_jsonl(os.path.join(target, "projections.jsonl"), mutate)

    def fork_appearance_hash(target):
        def mutate(rows):
            rows[0]["appearances"][0]["projection_hash"] = "0" * 64
            return rows
        _mutate_jsonl(os.path.join(target, "projections.jsonl"), mutate)

    def break_store_chain(target):
        path = os.path.join(target, "certification", "events.jsonl")
        with io.open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        del lines[3]
        with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)

    def drop_v11_bundle(target):
        _mutate_jsonl(os.path.join(target, "two-vote-artifacts.v1_1.jsonl"), lambda rows: rows[:-1])

    def touch_migration_substance(target):
        def mutate(rows):
            rows[0]["votes"][0]["conclusion"]["case_or_mood"]["value"] = "nasb"
            rows[0]["votes"][1]["conclusion"]["case_or_mood"]["value"] = "nasb"
            return rows
        _mutate_jsonl(os.path.join(target, "two-vote-artifacts.v1_1.jsonl"), mutate)

    def break_reverse_index(target):
        _mutate_json(os.path.join(target, "entry-reverse-index.json"),
                     lambda data: data["totals"].__setitem__("appearances", 77))

    def hide_deployment_flag(target):
        _mutate_json(os.path.join(target, "production-difference.json"),
                     lambda data: data.__setitem__("not_deployed", False))

    def strip_defeater(target):
        _mutate_json(os.path.join(target, "locations.json"),
                     lambda data: data["rejected_false_candidates"][0].__setitem__("defeater", ""))

    expect_red("13th location dropped -> 12-loc integrity fails", drop_thirteenth_location)
    expect_red("typed fact removed -> 49-fact completeness fails", drop_fact)
    expect_red("sense edge removed -> entry-transclusion closure fails", drop_sense_edge)
    expect_red("projection mutated -> parity hash stability fails", corrupt_projection_hash)
    expect_red("appearance hash forked -> parity fails", fork_appearance_hash)
    expect_red("certification event deleted -> hash chain fails", break_store_chain)
    expect_red("v1.1 bundle dropped -> reverse-trace closure fails", drop_v11_bundle)
    expect_red("v1.1 substance edited -> migration equality fails", touch_migration_substance)
    expect_red("reverse index totals off-by-one -> closure fails", break_reverse_index)
    expect_red("NOT-DEPLOYED flag flipped -> honesty gate fails", hide_deployment_flag)
    expect_red("defeater stripped -> rejected-candidate gate fails", strip_defeater)

    green_errors = validate(PILOT_DIR)
    if green_errors:
        print("FAIL green: committed pilot must validate")
        for error in green_errors[:20]:
            print("  ", error)
        failures.append("green")
    else:
        print("ok   green: committed pilot validates")

    if failures:
        print("P007 PILOT SELF-TEST FAIL (%d)" % len(failures))
        return 1
    print("P007 PILOT SELF-TEST PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pilot_dir", nargs="?", default=PILOT_DIR)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    errors = validate(args.pilot_dir)
    if errors:
        print("P007 PILOT VALIDATION FAIL (%d)" % len(errors))
        for error in errors:
            print("  ", error)
        return 1
    print("P007 PILOT VALIDATION PASS — %s: 12 occurrences / 78 appearances / 49 facts, "
          "entry+sense transclusion closed, parity stable, reverse trace closed, NOT-DEPLOYED" % SCOPE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
