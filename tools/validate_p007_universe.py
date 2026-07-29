#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P007_GEOMETRY_WAVE gate — red-first validator for the authoritative p007
reverse universe and the geometry-only certification wave.

Gates (mechanical, stdlib only, no network, no live reads):

1. Row-schema completeness — ``qamus/lattice/p007-reverse-universe.jsonl``
   carries exactly one row per p007 matrix row (2,999, distinct matrix ids)
   with the owner's full row schema: canonical loc, token surfaces + universe
   alignment (misaligned forbidden), morpheme span on every geometry row (and
   ONLY on geometry rows), host, candidate/certified edges, sense edge state,
   function/governor/governed/case/attachment states with evidence-policy
   routing, review state, projection state, every page appearance by P/V/N
   (recomputed from the committed ayah universe), reverse trace refs, and an
   exact blocker on every non-rejected row.  RM-09: no operator absolute paths
   anywhere in the artifact.
2. State-tally honesty — every one of the 11 ``P007_*`` tallies in the meta
   sidecar is RECOMPUTED from the universe rows + certification stores and
   must equal the asserted value; asserted-but-not-recomputable tallies fail.
3. Geometry-cert scope — the wave typed facts and every certified fact in the
   hash-chained store are geometry fact types ONLY; the gate FAILS if any
   geometry-wave fact claims identity, function, sense, governor, case or
   meaning (by fact_type or by fact_value key); the store trail validates via
   ``tools/certify_typed_fact.py`` and certifies exactly the expected
   454 x 3 fact ids; per-row geometry (span, boundary, NFC reconstruction) is
   recomputed from the committed quran-loc-surface index and must match the
   certified fact values byte-for-byte.
4. Partition-consistency — every row's partition/route/defeater equals the
   committed classification; geometry certification appears on exactly the
   deterministic-attachment-geometry rows; rejected rows carry a defeater and
   no blocker; pilot-certified facets appear on exactly the 12 pilot rows.

Red-first: ``--self-test`` mutates each gated property in a temp copy and
requires the validator to reject it, then requires the committed artifacts to
pass.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.build_p007_geometry_wave import (  # noqa: E402
    GEOMETRY_PARTITION,
    GEOMETRY_FACT_TYPES,
    alignment_tier,
    clitic_geometry,
    fact_ids_for,
    nfc,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCOPE = "P007_GEOMETRY_WAVE"
ENTRY_ID = "b10a1ee04666"
EXPECTED_ROWS = 2999
EXPECTED_GEOMETRY_ROWS = 454
EXPECTED_FACTS = EXPECTED_GEOMETRY_ROWS * 3
EXPECTED_PILOT = 12

LATTICE = os.path.join(ROOT, "qamus", "lattice")
DEFAULT_UNIVERSE = os.path.join(LATTICE, "p007-reverse-universe.jsonl")
DEFAULT_META = os.path.join(LATTICE, "p007-reverse-universe.meta.json")
DEFAULT_WAVE_DIR = os.path.join(ROOT, "qamus", "certification", "p007-geometry-wave")
CLASSIFICATION = os.path.join(LATTICE, "p007-population-classification.jsonl")
LOC_INDEX = os.path.join(ROOT, "qamus", "indexes", "quran-loc-surface", "index.jsonl")
AYAH_UNIVERSE = os.path.join(LATTICE, "example-ayah-universe.jsonl")
PILOT_LOCATIONS = os.path.join(ROOT, "qamus", "examples", "p007-li-pilot", "locations.json")

# Any of these on a geometry-wave fact is an owner-boundary violation: the
# wave may certify mechanics only, never identity/function/sense/meaning.
FORBIDDEN_FACT_TYPES = {
    "contextual_function", "governor_relation", "case_mood_governor",
    "irab_rendering", "clitic_host_segmentation", "sense_selection",
    "particle_identity", "root", "singular_pattern", "plural_pattern",
}
FORBIDDEN_VALUE_KEYS = {
    "function", "contextual_function", "sense", "sense_n", "governor",
    "governed_expression", "case", "case_or_mood", "irab", "meaning",
    "gloss", "particle_entry", "root",
}

REQUIRED_ROW_FIELDS = (
    "schema", "matrix_id", "occurrence_id", "canonical_loc", "surface",
    "universe_surface", "universe_alignment", "partition", "route",
    "rung1_eligible", "host_visible", "edges", "geometry_certification",
    "evidence_policy", "mcp_evidence_refs", "review_state",
    "projection_state", "appearances", "reverse_trace_refs", "mode",
)
REQUIRED_EDGE_FACETS = (
    "entry_candidate_edge", "entry_certified_edge", "sense_edge",
    "attachment", "function", "governor", "governed_expression", "case",
)
TALLY_KEYS = (
    "P007_OCCURRENCES_DISCOVERED", "P007_CANDIDATES_DISPOSITIONED",
    "P007_ENTRY_LINKS_CERTIFIED", "P007_SENSE_EDGES_CERTIFIED",
    "P007_GEOMETRY_CERTIFIED", "P007_FUNCTION_CERTIFIED",
    "P007_GOVERNOR_CASE_CERTIFIED", "P007_DIRECT_SOURCE_FUNCTION_QUEUE",
    "P007_TWO_VOTE_QUEUE", "P007_SCHOLAR_QUEUE", "P007_REJECTED_CLOSED",
)

_ABS_PATH = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:/|/home/|/Users/|\\\\\\\\")


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


class Caches:
    """Committed reference inputs shared across validate() runs."""

    def __init__(self):
        self.loc_index = None
        self.appearance_classes = None
        self.classification = None
        self.pilot_locs = None

    def load(self):
        if self.loc_index is None:
            self.loc_index = {row["loc"]: row["surface"] for row in read_jsonl(LOC_INDEX)}
        if self.appearance_classes is None:
            self.appearance_classes = {}
            with io.open(AYAH_UNIVERSE, encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        row = json.loads(line)
                        appearance_id = row.get("appearance_id")
                        if appearance_id:
                            self.appearance_classes[appearance_id] = (
                                row.get("entry_type") or "").upper()
        if self.classification is None:
            self.classification = {row["matrix_id"]: row for row in read_jsonl(CLASSIFICATION)}
        if self.pilot_locs is None:
            locations = read_json(PILOT_LOCATIONS)
            self.pilot_locs = {occ["occurrence_id"].split(":", 1)[1]
                               for occ in locations["occurrences"]}
        return self


def validate(universe_path=DEFAULT_UNIVERSE, meta_path=DEFAULT_META,
             wave_dir=DEFAULT_WAVE_DIR, caches=None):
    errors = []

    def err(message):
        errors.append(message)

    for path in (universe_path, meta_path,
                 os.path.join(wave_dir, "typed-facts.jsonl"),
                 os.path.join(wave_dir, "events.jsonl"),
                 os.path.join(wave_dir, "spot-check.json"),
                 CLASSIFICATION, LOC_INDEX, AYAH_UNIVERSE):
        if not os.path.exists(path):
            err("missing artifact: %s" % os.path.relpath(path, ROOT))
    if errors:
        return errors

    caches = (caches or Caches()).load()
    rows = read_jsonl(universe_path)
    meta = read_json(meta_path)
    facts = read_jsonl(os.path.join(wave_dir, "typed-facts.jsonl"))
    spot = read_json(os.path.join(wave_dir, "spot-check.json"))

    # ---- gate 1: row-schema completeness ---------------------------------
    if len(rows) != EXPECTED_ROWS:
        err("universe must carry exactly %d rows (found %d)" % (EXPECTED_ROWS, len(rows)))
    matrix_ids = [row.get("matrix_id") for row in rows]
    if len(set(matrix_ids)) != len(matrix_ids):
        err("universe matrix ids are not distinct")

    geometry_rows = []
    pilot_seen = set()
    tallies = {
        "partitions": {}, "geometry_rows": 0, "entry_certified": 0,
        "sense_certified": 0, "function_certified": 0, "gov_case_certified": 0,
        "direct_queue": 0, "two_vote_queue": 0, "scholar_queue": 0,
        "rejected": 0, "appearances": 0,
        "by_page_class": {"P": 0, "V": 0, "N": 0},
    }
    for row in rows:
        loc = row.get("canonical_loc") or "<no-loc>"
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                err("%s: missing row field %s" % (loc, field))
        raw = json.dumps(row, ensure_ascii=False)
        if _ABS_PATH.search(raw):
            err("%s: RM-09 violation — operator/server absolute path in row" % loc)
        edges = row.get("edges") or {}
        for facet in REQUIRED_EDGE_FACETS:
            if facet not in edges:
                err("%s: missing edge facet %s" % (loc, facet))
        for facet in ("attachment", "function", "governor",
                      "governed_expression", "case"):
            facet_row = edges.get(facet) or {}
            if not facet_row.get("state") or "evidence_policy" not in facet_row:
                err("%s: facet %s must record state + evidence-policy routing"
                    % (loc, facet))

        partition = row.get("partition")
        tallies["partitions"][partition] = tallies["partitions"].get(partition, 0) + 1
        is_geometry = partition == GEOMETRY_PARTITION
        if is_geometry:
            tallies["geometry_rows"] += 1
            geometry_rows.append(row)
        # universe alignment
        universe_surface = caches.loc_index.get(loc)
        if universe_surface is None:
            err("%s: no surface in the committed loc index" % loc)
        else:
            if row.get("universe_surface") != nfc(universe_surface):
                err("%s: universe_surface does not match the committed index" % loc)
            tier = alignment_tier(universe_surface, row.get("surface") or "")
            if tier != row.get("universe_alignment"):
                err("%s: universe_alignment %r does not recompute (%r)"
                    % (loc, row.get("universe_alignment"), tier))
            if tier == "misaligned":
                err("%s: matrix surface fails rasm alignment with the universe" % loc)
        # morpheme span only (and always) on geometry rows
        if is_geometry and not row.get("morpheme_span"):
            err("%s: geometry row has no morpheme_span" % loc)
        if not is_geometry and row.get("morpheme_span") is not None:
            err("%s: non-geometry row claims a morpheme_span" % loc)
        geometry_certification = row.get("geometry_certification") or {}
        if is_geometry and geometry_certification.get("state") != "certified":
            err("%s: geometry row does not reference its geometry certification" % loc)
        if not is_geometry and geometry_certification.get("state") not in (None, "none"):
            err("%s: non-geometry row claims geometry certification" % loc)
        # blocker: exact on every non-rejected row; never on rejected rows
        if partition == "rejected-false-candidate":
            if row.get("blocker") is not None:
                err("%s: rejected row must carry no blocker (terminal defeater)" % loc)
            if not (row.get("defeater") or "").strip():
                err("%s: rejected row has no defeater" % loc)
            tallies["rejected"] += 1
        else:
            if not (row.get("blocker") or "").strip():
                err("%s: non-rejected row must carry its exact blocker" % loc)
        # appearances recomputed from the committed ayah universe
        appearances = row.get("appearances") or {}
        ids = appearances.get("ids") or []
        if appearances.get("count") != len(ids):
            err("%s: appearance count does not match its id list" % loc)
        recomputed = {"P": 0, "V": 0, "N": 0}
        for appearance_id in ids:
            page_class = caches.appearance_classes.get(appearance_id)
            if page_class not in recomputed:
                err("%s: appearance %s not joinable to the ayah universe"
                    % (loc, appearance_id))
                continue
            recomputed[page_class] += 1
        if appearances.get("by_page_class") != recomputed:
            err("%s: by_page_class %r does not recompute (%r)"
                % (loc, appearances.get("by_page_class"), recomputed))
        tallies["appearances"] += len(ids)
        for page_class, count in recomputed.items():
            tallies["by_page_class"][page_class] += count
        # pilot-certified facets
        entry_certified = (edges.get("entry_certified_edge") or {}).get("state") == "certified"
        if entry_certified:
            tallies["entry_certified"] += 1
            pilot_seen.add(loc)
            if loc not in caches.pilot_locs:
                err("%s: entry_certified_edge outside the pilot 12" % loc)
        if (edges.get("sense_edge") or {}).get("state") == "certified":
            tallies["sense_certified"] += 1
        if (edges.get("function") or {}).get("state") == "certified":
            tallies["function_certified"] += 1
        if (edges.get("governor") or {}).get("state") == "certified" \
                and (edges.get("case") or {}).get("state") == "certified":
            tallies["gov_case_certified"] += 1
        if (edges.get("function") or {}).get("state") == "pending" \
                and (edges.get("function") or {}).get("evidence_policy") == "direct_source":
            tallies["direct_queue"] += 1
        if partition == "two-vote-required":
            tallies["two_vote_queue"] += 1
        if partition == "scholar-required":
            tallies["scholar_queue"] += 1

    if pilot_seen != caches.pilot_locs:
        err("entry-certified rows must be exactly the pilot 12 (found %d)"
            % len(pilot_seen))

    # ---- gate 4 (partition-consistency; interleaved here for one pass) ---
    for row in rows:
        cls_row = caches.classification.get(row.get("matrix_id"))
        if cls_row is None:
            err("%s: no classification row" % row.get("matrix_id"))
            continue
        for field in ("partition", "route", "defeater", "rung1_eligible",
                      "canonical_loc", "occurrence_id"):
            if row.get(field) != cls_row.get(field):
                err("%s: %s %r differs from the classification (%r)"
                    % (row.get("matrix_id"), field, row.get(field), cls_row.get(field)))
        if row.get("review_state") != cls_row.get("partition"):
            err("%s: review_state must equal the partition" % row.get("matrix_id"))
    missing_cls = set(caches.classification) - set(matrix_ids)
    if missing_cls:
        err("universe is missing %d classification row(s), e.g. %s"
            % (len(missing_cls), sorted(missing_cls)[0]))

    # ---- gate 3: geometry-cert scope + store + recompute ------------------
    fact_by_id = {fact.get("fact_id"): fact for fact in facts}
    expected_fact_ids = set()
    for row in geometry_rows:
        expected_fact_ids.update(fact_ids_for(row["canonical_loc"]).values())
    if set(fact_by_id) != expected_fact_ids:
        err("typed-facts.jsonl fact ids differ from the %d geometry rows x 3 "
            "(found %d, expected %d)"
            % (len(geometry_rows), len(fact_by_id), len(expected_fact_ids)))
    for fact_id, fact in sorted(fact_by_id.items()):
        fact_type = fact.get("fact_type")
        if fact_type in FORBIDDEN_FACT_TYPES:
            err("%s: OWNER-BOUNDARY VIOLATION — geometry-wave fact claims "
                "%s (identity/function facts are not certifiable by this wave)"
                % (fact_id, fact_type))
        elif fact_type not in GEOMETRY_FACT_TYPES:
            err("%s: fact_type %r is not a geometry fact type" % (fact_id, fact_type))
        bad_keys = FORBIDDEN_VALUE_KEYS & set((fact.get("fact_value") or {}).keys())
        if bad_keys:
            err("%s: OWNER-BOUNDARY VIOLATION — fact_value carries %s"
                % (fact_id, ", ".join(sorted(bad_keys))))
        if _ABS_PATH.search(json.dumps(fact, ensure_ascii=False)):
            err("%s: RM-09 violation — absolute path in fact" % fact_id)

    # per-row mechanical recompute against the certified fact values
    for row in geometry_rows:
        loc = row["canonical_loc"]
        universe_surface = caches.loc_index.get(loc)
        if universe_surface is None:
            continue
        geometry, reason = clitic_geometry(universe_surface)
        if geometry is None:
            err("%s: geometry no longer deterministic: %s" % (loc, reason))
            continue
        ids = fact_ids_for(loc)
        geom_fact = fact_by_id.get(ids["geom"])
        if geom_fact is not None:
            value = geom_fact.get("fact_value") or {}
            for field in ("component_surface", "char_span", "base_letter_span"):
                if value.get(field) != geometry[field]:
                    err("%s: certified %s %r does not recompute (%r)"
                        % (loc, field, value.get(field), geometry[field]))
        recon_fact = fact_by_id.get(ids["recon"])
        if recon_fact is not None:
            value = recon_fact.get("fact_value") or {}
            if nfc((value.get("clitic") or "") + (value.get("remainder") or "")) \
                    != nfc(universe_surface):
                err("%s: NFC reconstruction clitic+remainder does not rebuild "
                    "the universe surface" % loc)
        bound_fact = fact_by_id.get(ids["bound"])
        if bound_fact is not None:
            value = bound_fact.get("fact_value") or {}
            if value.get("boundary_char_index") != geometry["char_span"]["end"] \
                    or value.get("host_remainder_surface") != geometry["host_remainder_surface"] \
                    or value.get("host_base_letter_count") != geometry["host_base_letter_count"]:
                err("%s: token/host boundary fact does not recompute" % loc)
        span = row.get("morpheme_span") or {}
        if span and (span.get("char_span") != geometry["char_span"]
                     or span.get("component_surface") != geometry["component_surface"]):
            err("%s: universe morpheme_span does not recompute" % loc)

    # the hash-chained store: valid trail, exact certified set, geometry-only
    certify = os.path.join(ROOT, "tools", "certify_typed_fact.py")
    result = subprocess.run([sys.executable, certify, "--validate", wave_dir],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=ROOT)
    if result.returncode != 0 or "certification event trail is valid" not in (result.stdout or ""):
        err("geometry store trail validation failed: %s"
            % ((result.stdout or "") + (result.stderr or "")).strip()[:400])
    certified_ids = set()
    status_by_id = {}
    for event in read_jsonl(os.path.join(wave_dir, "events.jsonl")):
        fact_id = event.get("fact_id")
        status_by_id[fact_id] = event.get("to_status")
        if event.get("event_type") == "register":
            registered_type = (event.get("fact") or {}).get("fact_type")
            if registered_type not in GEOMETRY_FACT_TYPES:
                err("store registered a non-geometry fact %s (%s)"
                    % (fact_id, registered_type))
            committed = fact_by_id.get(fact_id)
            if committed is not None and event.get("fact") != committed:
                err("store register payload for %s forks from typed-facts.jsonl" % fact_id)
    certified_ids = {fact_id for fact_id, status in status_by_id.items()
                     if status == "certified"}
    if certified_ids != expected_fact_ids:
        err("store must certify exactly the %d geometry facts (found %d)"
            % (len(expected_fact_ids), len(certified_ids)))

    # spot check honesty
    if len(spot.get("rows", [])) < 20:
        err("spot-check.json must record at least 20 manually reviewed rows")
    for spot_row in spot.get("rows", []):
        if spot_row.get("verdict") != "verified":
            err("spot-check row %s is not verified" % spot_row.get("canonical_loc"))
        if spot_row.get("canonical_loc") not in {row["canonical_loc"] for row in geometry_rows}:
            err("spot-check row %s is not a geometry row" % spot_row.get("canonical_loc"))

    # ---- gate 2: state-tally honesty (recomputed, never asserted) ---------
    state_tallies = (meta or {}).get("state_tallies") or {}
    if sorted(state_tallies) != sorted(TALLY_KEYS):
        err("meta must carry exactly the 11 P007_* state tallies (found %d: %s)"
            % (len(state_tallies), ", ".join(sorted(state_tallies))))
    expected = {
        "P007_OCCURRENCES_DISCOVERED": {"complete": True, "rows": len(rows)},
        "P007_CANDIDATES_DISPOSITIONED": {"complete": True, "rows": len(rows),
                                          "partitions": tallies["partitions"]},
        "P007_ENTRY_LINKS_CERTIFIED": {"rows": tallies["entry_certified"]},
        "P007_SENSE_EDGES_CERTIFIED": {"rows": tallies["sense_certified"]},
        "P007_GEOMETRY_CERTIFIED": {"rows": tallies["geometry_rows"],
                                    "facts": len(certified_ids)},
        "P007_FUNCTION_CERTIFIED": {"rows": tallies["function_certified"]},
        "P007_GOVERNOR_CASE_CERTIFIED": {"rows": tallies["gov_case_certified"]},
        "P007_DIRECT_SOURCE_FUNCTION_QUEUE": {"rows": tallies["direct_queue"]},
        "P007_TWO_VOTE_QUEUE": {"rows": tallies["two_vote_queue"]},
        "P007_SCHOLAR_QUEUE": {"rows": tallies["scholar_queue"]},
        "P007_REJECTED_CLOSED": {"rows": tallies["rejected"]},
    }
    for key, recomputed_tally in expected.items():
        asserted = state_tallies.get(key)
        if not isinstance(asserted, dict):
            continue
        for field, value in recomputed_tally.items():
            if asserted.get(field) != value:
                err("tally %s.%s asserted %r but recomputes to %r"
                    % (key, field, asserted.get(field), value))
    if meta.get("rows") != len(rows):
        err("meta rows %r does not recompute (%d)" % (meta.get("rows"), len(rows)))
    if meta.get("appearances_total") != tallies["appearances"]:
        err("meta appearances_total %r does not recompute (%d)"
            % (meta.get("appearances_total"), tallies["appearances"]))
    if meta.get("appearances_by_page_class") != tallies["by_page_class"]:
        err("meta appearances_by_page_class does not recompute (%r vs %r)"
            % (meta.get("appearances_by_page_class"), tallies["by_page_class"]))
    if _ABS_PATH.search(json.dumps(meta, ensure_ascii=False)):
        err("meta: RM-09 violation — operator/server absolute path")

    # hard expectations of this wave (drift alarms, not tunables)
    if tallies["geometry_rows"] != EXPECTED_GEOMETRY_ROWS:
        err("geometry partition must hold exactly %d rows (found %d)"
            % (EXPECTED_GEOMETRY_ROWS, tallies["geometry_rows"]))
    if tallies["entry_certified"] != EXPECTED_PILOT:
        err("entry-links-certified must stay exactly %d (pilot) in this wave"
            % EXPECTED_PILOT)
    return errors


# ---------------------------------------------------------------------------
# red-first self-test
# ---------------------------------------------------------------------------

def _copy_wave(tmp_root):
    universe = os.path.join(tmp_root, "p007-reverse-universe.jsonl")
    meta = os.path.join(tmp_root, "p007-reverse-universe.meta.json")
    wave_dir = os.path.join(tmp_root, "wave")
    shutil.copy(DEFAULT_UNIVERSE, universe)
    shutil.copy(DEFAULT_META, meta)
    shutil.copytree(DEFAULT_WAVE_DIR, wave_dir)
    return universe, meta, wave_dir


def _mutate_jsonl(path, mutate_rows):
    rows = read_jsonl(path)
    rows = mutate_rows(rows)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")


def _mutate_json(path, mutate):
    data = read_json(path)
    mutate(data)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=1)
        handle.write("\n")


def self_test():
    failures = []
    caches = Caches().load()

    def expect_red(name, mutator):
        with tempfile.TemporaryDirectory(prefix="p007-universe-") as tmp_root:
            universe, meta, wave_dir = _copy_wave(tmp_root)
            mutator(universe, meta, wave_dir)
            errors = validate(universe, meta, wave_dir, caches=caches)
            status = "ok  " if errors else "FAIL"
            print("%s red: %s" % (status, name))
            if not errors:
                failures.append(name)

    def drop_row(universe, meta, wave_dir):
        _mutate_jsonl(universe, lambda rows: rows[:-1])

    def flip_partition(universe, meta, wave_dir):
        def mutate(rows):
            for row in rows:
                if row["partition"] == "two-vote-required":
                    row["partition"] = "direct-source-attested-function"
                    row["review_state"] = row["partition"]
                    break
            return rows
        _mutate_jsonl(universe, mutate)

    def inflate_tally(universe, meta, wave_dir):
        _mutate_json(meta, lambda data: data["state_tallies"]
                     ["P007_GEOMETRY_CERTIFIED"].__setitem__("rows", 455))

    def claim_entry_cert_outside_pilot(universe, meta, wave_dir):
        def mutate(rows):
            for row in rows:
                if row["partition"] == GEOMETRY_PARTITION \
                        and row["edges"]["entry_certified_edge"].get("state") != "certified":
                    row["edges"]["entry_certified_edge"] = {
                        "state": "certified", "entry_id": ENTRY_ID}
                    break
            return rows
        _mutate_jsonl(universe, mutate)

    def smuggle_identity_fact(universe, meta, wave_dir):
        def mutate(rows):
            forged = json.loads(json.dumps(rows[0]))
            forged["fact_id"] = "fact:p007geo:forged:func"
            forged["fact_type"] = "contextual_function"
            rows.append(forged)
            return rows
        _mutate_jsonl(os.path.join(wave_dir, "typed-facts.jsonl"), mutate)

    def smuggle_identity_value(universe, meta, wave_dir):
        def mutate(rows):
            rows[0]["fact_value"]["function"] = "jarr-preposition"
            return rows
        _mutate_jsonl(os.path.join(wave_dir, "typed-facts.jsonl"), mutate)

    def corrupt_span(universe, meta, wave_dir):
        def mutate(rows):
            for row in rows:
                if row.get("fact_type") == "attachment_geometry":
                    row["fact_value"]["char_span"]["end"] += 1
                    break
            return rows
        _mutate_jsonl(os.path.join(wave_dir, "typed-facts.jsonl"), mutate)

    def strip_defeater(universe, meta, wave_dir):
        def mutate(rows):
            for row in rows:
                if row["partition"] == "rejected-false-candidate":
                    row["defeater"] = ""
                    break
            return rows
        _mutate_jsonl(universe, mutate)

    def null_blocker(universe, meta, wave_dir):
        def mutate(rows):
            for row in rows:
                if row["partition"] == "two-vote-required":
                    row["blocker"] = None
                    break
            return rows
        _mutate_jsonl(universe, mutate)

    def break_store_chain(universe, meta, wave_dir):
        path = os.path.join(wave_dir, "events.jsonl")
        with io.open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        del lines[5]
        with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)

    def fork_morpheme_span(universe, meta, wave_dir):
        def mutate(rows):
            for row in rows:
                if row.get("morpheme_span"):
                    row["morpheme_span"]["char_span"]["end"] += 1
                    break
            return rows
        _mutate_jsonl(universe, mutate)

    def absolute_path_smuggled(universe, meta, wave_dir):
        def mutate(rows):
            rows[0]["reverse_trace_refs"].append(
                "C:/operator/secret/lane/evidence.jsonl")
            return rows
        _mutate_jsonl(universe, mutate)

    expect_red("row dropped -> completeness fails", drop_row)
    expect_red("partition flipped -> classification consistency fails", flip_partition)
    expect_red("meta tally inflated -> honesty fails (recomputed, not asserted)", inflate_tally)
    expect_red("entry cert claimed outside pilot -> fails", claim_entry_cert_outside_pilot)
    expect_red("identity fact smuggled into the wave -> owner boundary fails", smuggle_identity_fact)
    expect_red("function key smuggled into a fact value -> owner boundary fails", smuggle_identity_value)
    expect_red("char span corrupted -> mechanical recompute fails", corrupt_span)
    expect_red("defeater stripped from a rejected row -> fails", strip_defeater)
    expect_red("blocker nulled on a queued row -> fails", null_blocker)
    expect_red("store event deleted -> hash chain fails", break_store_chain)
    expect_red("universe morpheme span forked -> recompute fails", fork_morpheme_span)
    expect_red("absolute path smuggled -> RM-09 gate fails", absolute_path_smuggled)

    green_errors = validate(caches=caches)
    if green_errors:
        print("FAIL green: committed universe must validate")
        for error in green_errors[:20]:
            print("  ", error)
        failures.append("green")
    else:
        print("ok   green: committed universe validates")

    if failures:
        print("P007 UNIVERSE SELF-TEST FAIL (%d)" % len(failures))
        return 1
    print("P007 UNIVERSE SELF-TEST PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    errors = validate()
    if errors:
        print("P007 UNIVERSE VALIDATION FAIL (%d)" % len(errors))
        for error in errors[:50]:
            print("  ", error)
        return 1
    print("P007 UNIVERSE VALIDATION PASS — %s: 2,999 rows / 454 geometry rows / "
          "%d geometry facts certified (mechanics only), 11 P007_* tallies "
          "recomputed honest, partition-consistent, RM-09 clean" % (SCOPE, EXPECTED_FACTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
