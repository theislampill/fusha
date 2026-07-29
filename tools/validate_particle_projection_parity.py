#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable twin of docs/qamus/particle-projection-contract.md.

Invariant: every appearance of one canonical particle occurrence carries the
SAME projection hash — sha256 over the canonical typed-fact artifact
serialization — except for the closed permitted presentation-metadata
whitelist.  Also enforces the particle-edge certification structure of
qamus/schemas/particle-edge-ontology.schema.json (an EXTENSION of the one
canonical qamus.graph_edge.v1 vocabulary) and the homograph function-lattice
constraints, without a jsonschema dependency (repo style: hand-rolled named
validators, red-first self-test).

Usage:
    python tools/validate_particle_projection_parity.py BUNDLE.json [...]
    python tools/validate_particle_projection_parity.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_typed_edge_crosswalk import (  # noqa: E402
    EDGE_TYPE_SET,
    PARTICLE_EDGE_TYPES,
    STATUS_SET,
)

INPUT_SCHEMA = "qamus.particle_projection_parity_input.v1"
LATTICE_SCHEMA = "qamus.particle_function_lattice.v1"
EDGE_SCHEMA = "qamus.graph_edge.v1"
ONTOLOGY_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "qamus" / "schemas" / "particle-edge-ontology.schema.json"
)

# Closed whitelist — extending it is an owner decision recorded in the
# contract doc (§2.2), never a validator-side convenience.
PERMITTED_PRESENTATION_KEYS = frozenset({
    "selected_highlight",
    "entry_relationship",
    "focus",
    "navigation",
})

# Certified surfacing of these kinds is iʿrāb-bearing → two-vote required
# (docs/certification-authority.md §2 rung 4).
# coordination_edge is DELIBERATELY ABSENT (owner decision, flag B,
# 2026-07-29 steer §8): coordination is a typed Naḥw RELATION edge, not
# itself an iʿrāb class — it certifies at the bundle rung, while the
# COORDINATED ELEMENTS' case/mood/agreement/attachment facts remain
# iʿrāb-bearing through their own edges.
IRAB_BEARING_EDGE_TYPES = frozenset({
    "particle_function_edge",
    "governor_edge",
    "governed_expression_edge",
    "scope_edge",
    "condition_edge",
    "negation_scope_edge",
    "relative_antecedent_edge",
    "pronoun_referent_edge",
})
CANDIDATE_ONLY_EDGE_TYPES = frozenset({
    "particle_entry_candidate_edge",
    "particle_sense_candidate_edge",
})
CERTIFIED_ONLY_EDGE_TYPES = frozenset({
    "particle_entry_certified_edge",
    "particle_sense_certified_edge",
})

# Arabic technical iʿrāb formulas are private-side analysis prose and may not
# appear in the public teaching plane (contract §1.4).  Multi-word formulas
# only, to avoid flagging object-language Arabic being taught.
FORBIDDEN_IRAB_PROSE = (
    "مبتدأ مرفوع",
    "خبر مرفوع",
    "فاعل مرفوع",
    "مفعول به منصوب",
    "في محل جر",
    "في محل رفع",
    "في محل نصب",
    "وعلامة رفعه",
    "وعلامة نصبه",
    "وعلامة جره",
    "مجرور وعلامة",
)
TEACHING_PLANE_KEYS = (
    "contextual_gloss",
    "sarf_note",
    "nahw_note",
    "reason",
    "rootless_pedagogy",
)


def projection_hash(projection: dict) -> str:
    """sha256 over the canonical typed-fact artifact serialization (§2.1)."""
    basis = {
        key: value
        for key, value in projection.items()
        if key not in PERMITTED_PRESENTATION_KEYS
    }
    blob = json.dumps(basis, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _forked_keys(canonical: dict, rendered: dict) -> list[str]:
    keys = (set(canonical) | set(rendered)) - PERMITTED_PRESENTATION_KEYS
    return sorted(
        key for key in keys
        if canonical.get(key) != rendered.get(key)
    )


# --------------------------------------------------------------------------- #
# named checks — each appends "check_name: message" strings to errors
# --------------------------------------------------------------------------- #

def check_parity_hash_uniform(bundle, errors):
    occ = {row["occurrence_id"]: row for row in bundle.get("occurrences", [])}
    for app in bundle.get("appearances", []):
        occ_id = app.get("occurrence_id")
        canonical = occ.get(occ_id)
        if canonical is None:
            errors.append(
                "parity_hash_uniform: appearance %s references unknown occurrence %s"
                % (app.get("appearance_id"), occ_id))
            continue
        want = projection_hash(canonical.get("projection") or {})
        got = projection_hash(app.get("projection") or {})
        if want != got:
            forked = _forked_keys(canonical.get("projection") or {},
                                  app.get("projection") or {})
            errors.append(
                "parity_hash_uniform: appearance %s on page %s forks occurrence %s "
                "outside the permitted presentation whitelist (forked keys: %s)"
                % (app.get("appearance_id"), app.get("page_id"), occ_id,
                   ", ".join(forked) or "<serialization>"))


def check_artifact_per_occurrence(bundle, errors):
    occ_artifact = {}
    for row in bundle.get("occurrences", []):
        occ_artifact[row["occurrence_id"]] = row.get("artifact_id")
    artifact_owner = {}
    for occ_id, art in sorted(occ_artifact.items()):
        if art in artifact_owner:
            errors.append(
                "artifact_per_occurrence: occurrences %s and %s share artifact %s "
                "(same-surface sharing across occurrences is forbidden, contract §2.3)"
                % (artifact_owner[art], occ_id, art))
        else:
            artifact_owner[art] = occ_id
    for app in bundle.get("appearances", []):
        occ_id = app.get("occurrence_id")
        want = occ_artifact.get(occ_id)
        if want is not None and app.get("artifact_id") != want:
            errors.append(
                "artifact_per_occurrence: appearance %s carries artifact %s but its "
                "occurrence %s owns artifact %s"
                % (app.get("appearance_id"), app.get("artifact_id"), occ_id, want))


def check_rootless_pedagogy(bundle, errors):
    for row in bundle.get("occurrences", []):
        projection = row.get("projection") or {}
        if projection.get("kind") != "particle":
            continue
        if projection.get("root") in (None, ""):
            pedagogy = projection.get("rootless_pedagogy")
            if not (isinstance(pedagogy, str) and pedagogy.strip()):
                errors.append(
                    "rootless_pedagogy: rootless particle occurrence %s has no "
                    "rootless_pedagogy — a rootless particle must teach rootlessness, "
                    "never look incomplete (contract §1.3)" % row.get("occurrence_id"))


def check_no_irab_prose(bundle, errors):
    for row in bundle.get("occurrences", []) + bundle.get("appearances", []):
        projection = row.get("projection") or {}
        ident = row.get("occurrence_id") or row.get("appearance_id")
        for key in TEACHING_PLANE_KEYS:
            text = projection.get(key)
            if not isinstance(text, str):
                continue
            for formula in FORBIDDEN_IRAB_PROSE:
                if formula in text:
                    errors.append(
                        "no_irab_prose: %s field %r carries Arabic iʿrāb formula %r — "
                        "the teaching plane is learner-register English (contract §1.4)"
                        % (ident, key, formula))


def check_lattices(bundle, errors):
    for lattice in bundle.get("lattices", []):
        lid = lattice.get("lattice_id") or lattice.get("occurrence_id")
        if lattice.get("schema") != LATTICE_SCHEMA:
            errors.append("lattice_shape: %s has schema %r, expected %r"
                          % (lid, lattice.get("schema"), LATTICE_SCHEMA))
        candidates = lattice.get("mutually_exclusive_candidates") or []
        if not candidates:
            errors.append("lattice_shape: %s has no mutually_exclusive_candidates" % lid)
        certified = []
        for cand in candidates:
            cid = cand.get("candidate_id")
            if not cand.get("guards"):
                errors.append("lattice_guards: %s candidate %s has no guards" % (lid, cid))
            if not cand.get("defeaters"):
                errors.append(
                    "lattice_defeaters: %s candidate %s has no defeaters — every "
                    "candidate must be falsifiable" % (lid, cid))
            if cand.get("status") == "certified":
                certified.append(cand)
                if not cand.get("evidence_bundle_ref"):
                    errors.append(
                        "lattice_certified_bundle: %s candidate %s is certified without "
                        "an evidence_bundle_ref" % (lid, cid))
                if not cand.get("two_vote_artifact_ref"):
                    errors.append(
                        "lattice_certified_two_vote: %s candidate %s is certified without "
                        "a two_vote_artifact_ref (iʿrāb-bearing, rung 4)" % (lid, cid))
                if cand.get("evidence_mode") == "unresolved":
                    errors.append(
                        "lattice_certified_unresolved: %s candidate %s is certified with "
                        "evidence_mode unresolved" % (lid, cid))
        if len(certified) > 1:
            # Flag E (owner-decided): maxContains:1 applies ACROSS mutually
            # exclusive candidate analyses, unconditionally — layered functions
            # never live in this array.
            errors.append(
                "lattice_single_winner: %s has %d certified mutually exclusive "
                "candidates — at most one winner, unconditionally; genuine layered "
                "functions belong in compatible_functions" % (lid, len(certified)))
        exclusive_labels = {c.get("function_label") for c in candidates}
        for compat in lattice.get("compatible_functions") or []:
            fid = compat.get("function_id")
            if compat.get("function_label") in exclusive_labels:
                errors.append(
                    "lattice_compatible_contradiction: %s compatible function %s "
                    "duplicates mutually exclusive candidate label %r — a layered "
                    "function may not contradict the exclusive candidate set"
                    % (lid, fid, compat.get("function_label")))
            if compat.get("status") != "certified":
                continue
            if len(certified) != 1:
                errors.append(
                    "lattice_compatible_requires_winner: %s compatible function %s "
                    "is certified without exactly one certified winning analysis to "
                    "layer on" % (lid, fid))
            if not compat.get("evidence_bundle_ref"):
                errors.append(
                    "lattice_compatible_bundle: %s compatible function %s is certified "
                    "without its own evidence_bundle_ref" % (lid, fid))
            if not compat.get("review_ref"):
                errors.append(
                    "lattice_compatible_review: %s compatible function %s is certified "
                    "without an independent review_ref (flag E condition b)" % (lid, fid))
            if not compat.get("coexistence_source_support"):
                errors.append(
                    "lattice_compatible_coexistence: %s compatible function %s is "
                    "certified without explicit coexistence_source_support (flag E "
                    "condition a)" % (lid, fid))
            if compat.get("evidence_mode") == "unresolved":
                errors.append(
                    "lattice_compatible_unresolved: %s compatible function %s is "
                    "certified with evidence_mode unresolved" % (lid, fid))


def check_edges(bundle, errors):
    for edge in bundle.get("edges", []):
        eid = edge.get("edge_id")
        etype = edge.get("edge_type")
        status = edge.get("status")
        details = edge.get("details") or {}
        if edge.get("schema") != EDGE_SCHEMA:
            errors.append("edge_shape: %s has schema %r, expected %r (one vocabulary, "
                          "not a parallel graph)" % (eid, edge.get("schema"), EDGE_SCHEMA))
        if etype not in EDGE_TYPE_SET:
            errors.append("edge_shape: %s has unknown edge_type %r" % (eid, etype))
        if status not in STATUS_SET:
            errors.append("edge_shape: %s has unknown status %r" % (eid, status))
        if not edge.get("guards"):
            errors.append("edge_guards: %s has no satisfied guards" % eid)
        for field in ("occurrence_id", "surface", "evidence_mode", "fact_id"):
            if not details.get(field):
                errors.append("edge_details: %s missing details.%s" % (eid, field))
        if etype in CANDIDATE_ONLY_EDGE_TYPES:
            if status == "certified":
                errors.append(
                    "edge_candidate_separation: %s is a %s but carries status certified — "
                    "candidate/certified separation is structural" % (eid, etype))
            if details.get("evidence_bundle_ref") or details.get("two_vote_artifact_ref"):
                errors.append(
                    "edge_candidate_separation: %s is a %s but carries certification refs"
                    % (eid, etype))
        if etype in CERTIFIED_ONLY_EDGE_TYPES and status != "certified":
            errors.append("edge_certified_kind: %s is a %s but has status %r"
                          % (eid, etype, status))
        if status == "certified":
            if not details.get("evidence_bundle_ref"):
                errors.append(
                    "edge_certified_bundle: %s is certified without an "
                    "evidence_bundle_ref (reconstructible bundle required)" % eid)
            if details.get("evidence_mode") == "unresolved":
                errors.append(
                    "edge_certified_unresolved: %s is certified with evidence_mode "
                    "unresolved" % eid)
            if etype in IRAB_BEARING_EDGE_TYPES and not details.get("two_vote_artifact_ref"):
                errors.append(
                    "edge_irab_two_vote: %s (%s) is certified without a "
                    "two_vote_artifact_ref — iʿrāb-bearing conclusions require the "
                    "token-layer two-vote artifact (rung 4)" % (eid, etype))
        if etype == "clitic_host_edge" and not details.get("component_surface"):
            errors.append("edge_clitic_component: %s missing details.component_surface" % eid)


def check_vocabulary_sync(errors):
    """Drift gate: schema enum == PARTICLE_EDGE_TYPES ⊆ canonical EDGE_TYPE_SET."""
    try:
        with ONTOLOGY_SCHEMA_PATH.open(encoding="utf-8") as handle:
            schema = json.load(handle)
        enum = schema["$defs"]["particle_edge_type"]["enum"]
    except Exception as exc:
        errors.append("vocabulary_sync: cannot read ontology schema: %s" % exc)
        return
    if list(enum) != list(PARTICLE_EDGE_TYPES):
        errors.append(
            "vocabulary_sync: particle-edge-ontology.schema.json enum diverges from "
            "PARTICLE_EDGE_TYPES in tools/build_typed_edge_crosswalk.py")
    missing = [t for t in PARTICLE_EDGE_TYPES if t not in EDGE_TYPE_SET]
    if missing:
        errors.append(
            "vocabulary_sync: particle edge kinds missing from the canonical EDGE_TYPES "
            "vocabulary: %s" % ", ".join(missing))
    irab_enum = schema["$defs"].get("irab_bearing_edge_type", {}).get("enum") or []
    if set(irab_enum) != set(IRAB_BEARING_EDGE_TYPES):
        errors.append(
            "vocabulary_sync: iʿrāb-bearing kind set diverges between schema and validator")
    if "coordination_edge" in set(irab_enum) | set(IRAB_BEARING_EDGE_TYPES):
        errors.append(
            "vocabulary_sync: coordination_edge re-entered the iʿrāb-bearing set — "
            "owner decision flag B (2026-07-29 steer §8) classes coordination as a "
            "typed relation edge, certifiable at the bundle rung; reversing this is "
            "an owner decision, not a validator/schema edit")


def validate_bundle(bundle: dict) -> list[str]:
    errors: list[str] = []
    if bundle.get("schema") != INPUT_SCHEMA:
        errors.append("bundle_shape: schema is %r, expected %r"
                      % (bundle.get("schema"), INPUT_SCHEMA))
    check_parity_hash_uniform(bundle, errors)
    check_artifact_per_occurrence(bundle, errors)
    check_rootless_pedagogy(bundle, errors)
    check_no_irab_prose(bundle, errors)
    check_lattices(bundle, errors)
    check_edges(bundle, errors)
    check_vocabulary_sync(errors)
    return errors


# --------------------------------------------------------------------------- #
# red-first self-test
# --------------------------------------------------------------------------- #

def _green_projection() -> dict:
    return {
        "kind": "particle",
        "component_surface": "مَا",
        "segmentation": ["مَا"],
        "contextual_gloss": "what(ever) — introducing everything in the heavens",
        "particle_identity": "ma (entry b8e480aebafe)",
        "contextual_function": "mawsula (relative)",
        "sarf_note": "This particle is not built from a root — it is an indeclinable tool word that stands alone.",
        "nahw_note": "It stands for the things owned — the whole phrase that follows describes it.",
        "governor": "implied predicate of لله",
        "governed": "مَا فِي السَّمَاوَاتِ",
        "scope": "the following prepositional phrase",
        "attachment": None,
        "alternatives": ["masdariyya (rejected: no following verbal clause)"],
        "reason": "a following locative phrase and resumptive sense select the relative reading",
        "unresolved": [],
        "entry_link": "entry:b8e480aebafe",
        "root": None,
        "rootless_pedagogy": "This particle has no root: it is a tool word, complete as it is.",
        "selected_highlight": False,
        "entry_relationship": "reader",
        "focus": None,
        "navigation": [],
    }


def _green_bundle() -> dict:
    proj = _green_projection()
    reader_app = dict(proj)
    entry_app = dict(proj)
    entry_app.update({
        "selected_highlight": True,
        "entry_relationship": "own-entry-example",
        "focus": "example-card",
        "navigation": ["entry:b8e480aebafe"],
    })
    proj2 = dict(proj)
    proj2.update({
        "contextual_gloss": "what(ever) — everything in the earth",
        "governed": "مَا فِي الْأَرْضِ",
    })
    edge_base = {
        "schema": EDGE_SCHEMA,
        "guards": ["surface_exact", "occurrence_address_exact"],
        "evidence": [{"address": "quran:2:284:10", "method": "explicit_occurrence_address"}],
        "producer": {"id": "tools.validate_particle_projection_parity.selftest", "version": "1"},
    }
    return {
        "schema": INPUT_SCHEMA,
        "occurrences": [
            {"occurrence_id": "quran:2:284:10", "surface": "مَا",
             "artifact_id": "artifact:ma-2-284-10", "projection": proj},
            {"occurrence_id": "quran:2:284:2", "surface": "مَا",
             "artifact_id": "artifact:ma-2-284-2", "projection": proj2},
        ],
        "appearances": [
            {"appearance_id": "app:reader:2:284:10", "page_id": "reader:2:284",
             "occurrence_id": "quran:2:284:10", "artifact_id": "artifact:ma-2-284-10",
             "projection": reader_app},
            {"appearance_id": "app:entry:p-ma:x1", "page_id": "entry:b8e480aebafe",
             "occurrence_id": "quran:2:284:10", "artifact_id": "artifact:ma-2-284-10",
             "projection": entry_app},
        ],
        "edges": [
            dict(edge_base, edge_id="edge:aaaaaaaaaaaa",
                 edge_type="particle_entry_candidate_edge",
                 from_node_id="occurrence:2:284:10", from_node_type="occurrence",
                 to_node_id="entry:b8e480aebafe", to_node_type="entry",
                 status="candidate",
                 details={"occurrence_id": "quran:2:284:10", "surface": "مَا",
                          "evidence_mode": "cross_source_corroboration",
                          "fact_id": "sha256:selftest01"}),
            dict(edge_base, edge_id="edge:bbbbbbbbbbbb",
                 edge_type="governor_edge",
                 from_node_id="occurrence:2:284:10", from_node_type="occurrence",
                 to_node_id="occurrence:2:284:1", to_node_type="occurrence",
                 status="certified",
                 details={"occurrence_id": "quran:2:284:10", "surface": "مَا",
                          "evidence_mode": "direct_source_attestation",
                          "fact_id": "sha256:selftest02",
                          "evidence_bundle_ref": "fact-ledger:selftest02",
                          "two_vote_artifact_ref": "two-vote:selftest02"}),
            dict(edge_base, edge_id="edge:dddddddddddd",
                 edge_type="coordination_edge",
                 from_node_id="occurrence:2:284:10", from_node_type="occurrence",
                 to_node_id="occurrence:2:284:2", to_node_type="occurrence",
                 status="certified",
                 details={"occurrence_id": "quran:2:284:10", "surface": "مَا",
                          "evidence_mode": "direct_source_attestation",
                          "fact_id": "sha256:selftest06",
                          "evidence_bundle_ref": "fact-ledger:selftest06"}),
            dict(edge_base, edge_id="edge:cccccccccccc",
                 edge_type="clitic_host_edge",
                 from_node_id="occurrence:2:284:10", from_node_type="occurrence",
                 to_node_id="occurrence:2:284:10", to_node_type="occurrence",
                 status="deterministic_exact",
                 details={"occurrence_id": "quran:2:284:10", "surface": "مَا",
                          "component_surface": "مَا",
                          "evidence_mode": "direct_source_attestation",
                          "fact_id": "sha256:selftest03"}),
        ],
        "lattices": [
            {"schema": LATTICE_SCHEMA, "lattice_id": "lattice:ma:2:284:10",
             "occurrence_id": "quran:2:284:10", "surface": "مَا",
             "entry_id": "b8e480aebafe",
             "compatible_functions": [],
             "mutually_exclusive_candidates": [
                 {"candidate_id": "cand:mawsula", "function_label": "mawsula",
                  "contextual_gloss": "what(ever)",
                  "guards": ["followed_by_locative_phrase"],
                  "defeaters": ["a following finite verbal clause would select masdariyya"],
                  "status": "certified",
                  "evidence_mode": "direct_source_attestation",
                  "evidence_bundle_ref": "fact-ledger:selftest04",
                  "two_vote_artifact_ref": "two-vote:selftest04"},
                 {"candidate_id": "cand:nafiya", "function_label": "nafiya",
                  "contextual_gloss": "not",
                  "guards": ["clause_initial_negation_context"],
                  "defeaters": ["no negatable clause follows here"],
                  "status": "rejected",
                  "evidence_mode": "direct_source_attestation"},
             ]},
        ],
    }


def _self_test() -> int:
    failures = []

    def expect_green(name, bundle):
        errs = validate_bundle(bundle)
        ok = not errs
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            for err in errs:
                print("   ", err)
            failures.append(name)

    def expect_red(name, bundle, needle):
        errs = validate_bundle(bundle)
        ok = any(needle in err for err in errs)
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            print("    expected an error containing %r, got: %s" % (needle, errs))
            failures.append(name)

    expect_green("green: PROOF-P style bundle passes end to end", _green_bundle())

    # red 1 — forked segmentation across pages
    bad = _green_bundle()
    bad["appearances"][1]["projection"]["segmentation"] = ["مَ", "ا"]
    expect_red("red: forked segmentation across pages is a hash fork",
               bad, "parity_hash_uniform")

    # red 2 — forked gloss
    bad = _green_bundle()
    bad["appearances"][1]["projection"]["contextual_gloss"] = "not"
    expect_red("red: forked gloss across pages is a hash fork",
               bad, "parity_hash_uniform")

    # red 3 — forked contextual function
    bad = _green_bundle()
    bad["appearances"][0]["projection"]["contextual_function"] = "nafiya (negative)"
    expect_red("red: forked contextual function is a hash fork",
               bad, "parity_hash_uniform")

    # red 4 — permitted presentation metadata may differ (must stay green)
    good = _green_bundle()
    good["appearances"][0]["projection"]["focus"] = "inline"
    expect_green("green: permitted presentation metadata may differ", good)

    # red 5 — same-surface different-occurrence wrongly sharing one artifact
    bad = _green_bundle()
    bad["occurrences"][1]["artifact_id"] = "artifact:ma-2-284-10"
    expect_red("red: same-surface different-occurrence sharing an artifact",
               bad, "artifact_per_occurrence")

    # red 6 — appearance bound to the wrong occurrence's artifact
    bad = _green_bundle()
    bad["appearances"][0]["artifact_id"] = "artifact:ma-2-284-2"
    expect_red("red: appearance carrying another occurrence's artifact",
               bad, "artifact_per_occurrence")

    # red 7 — rootless particle rendered without rootlessness pedagogy
    bad = _green_bundle()
    for row in bad["occurrences"]:
        row["projection"].pop("rootless_pedagogy", None)
    for row in bad["appearances"]:
        row["projection"].pop("rootless_pedagogy", None)
    expect_red("red: rootless particle must teach rootlessness",
               bad, "rootless_pedagogy")

    # red 8 — Arabic iʿrāb prose in the teaching plane
    bad = _green_bundle()
    bad["occurrences"][0]["projection"]["nahw_note"] = "اسم موصول في محل جر"
    for app in bad["appearances"]:
        app["projection"]["nahw_note"] = "اسم موصول في محل جر"
    expect_red("red: Arabic iʿrāb formula in the teaching plane",
               bad, "no_irab_prose")

    # red 9 — two certified mutually exclusive candidates (flag E: unconditional)
    bad = _green_bundle()
    bad["lattices"][0]["mutually_exclusive_candidates"][1].update({
        "status": "certified",
        "evidence_bundle_ref": "fact-ledger:selftest05",
        "two_vote_artifact_ref": "two-vote:selftest05",
    })
    expect_red("red: two certified mutually exclusive candidates always fail",
               bad, "lattice_single_winner")

    # green 9b — a valid layered pair: certified winner + compatible function
    # with evidence bundle, independent review, and coexistence source support
    good = _green_bundle()
    good["lattices"][0]["compatible_functions"] = [{
        "function_id": "compat:tawkid",
        "function_label": "tawkid (emphatic layering)",
        "contextual_gloss": "adds emphasis alongside the relative reading",
        "status": "certified",
        "evidence_mode": "direct_source_attestation",
        "evidence_bundle_ref": "fact-ledger:compat01",
        "review_ref": "review:compat01",
        "coexistence_source_support": "tawjih source states both functions hold here",
    }]
    expect_green("green: valid layered pair via compatible_functions", good)

    # red 9c — layered function without coexistence source support
    bad = _green_bundle()
    bad["lattices"][0]["compatible_functions"] = [{
        "function_id": "compat:tawkid",
        "function_label": "tawkid (emphatic layering)",
        "contextual_gloss": "adds emphasis alongside the relative reading",
        "status": "certified",
        "evidence_mode": "direct_source_attestation",
        "evidence_bundle_ref": "fact-ledger:compat01",
        "review_ref": "review:compat01",
    }]
    expect_red("red: layered function without coexistence source support",
               bad, "lattice_compatible_coexistence")

    # red 9d — layered function contradicting the exclusive candidate set
    bad = _green_bundle()
    bad["lattices"][0]["compatible_functions"] = [{
        "function_id": "compat:nafiya",
        "function_label": "nafiya",
        "contextual_gloss": "not",
        "status": "certified",
        "evidence_mode": "direct_source_attestation",
        "evidence_bundle_ref": "fact-ledger:compat02",
        "review_ref": "review:compat02",
        "coexistence_source_support": "claimed",
    }]
    expect_red("red: layered function duplicating an exclusive candidate label",
               bad, "lattice_compatible_contradiction")

    # red 10 — certified lattice winner without two-vote artifact
    bad = _green_bundle()
    bad["lattices"][0]["mutually_exclusive_candidates"][0].pop("two_vote_artifact_ref")
    expect_red("red: certified function without two-vote artifact",
               bad, "lattice_certified_two_vote")

    # red 11 — candidate without defeaters
    bad = _green_bundle()
    bad["lattices"][0]["mutually_exclusive_candidates"][1]["defeaters"] = []
    expect_red("red: lattice candidate without defeaters", bad, "lattice_defeaters")

    # red 12 — certified iʿrāb-bearing edge without two-vote artifact
    bad = _green_bundle()
    bad["edges"][1]["details"].pop("two_vote_artifact_ref")
    expect_red("red: certified governor edge without two-vote artifact",
               bad, "edge_irab_two_vote")

    # green 12b / red 12c — flag B reclassification: a certified coordination
    # edge (relation rung) certifies WITHOUT a two-vote artifact (the green
    # bundle's edge:dddddddddddd carries none), while a governed-case edge
    # still requires it.
    good = _green_bundle()
    assert "two_vote_artifact_ref" not in good["edges"][2]["details"]
    expect_green("green: certified coordination edge without two-vote artifact",
                 good)
    bad = _green_bundle()
    bad["edges"][2]["edge_type"] = "governed_expression_edge"
    expect_red("red: governed-case edge still requires the two-vote artifact",
               bad, "edge_irab_two_vote")

    # red 13 — certified edge without evidence bundle
    bad = _green_bundle()
    bad["edges"][1]["details"].pop("evidence_bundle_ref")
    expect_red("red: certified edge without evidence bundle",
               bad, "edge_certified_bundle")

    # red 14 — candidate edge kind smuggling status certified
    bad = _green_bundle()
    bad["edges"][0]["status"] = "certified"
    bad["edges"][0]["details"]["evidence_bundle_ref"] = "fact-ledger:smuggled"
    expect_red("red: candidate edge kind may never be certified",
               bad, "edge_candidate_separation")

    # red 15 — unresolved evidence mode may never certify
    bad = _green_bundle()
    bad["edges"][1]["details"]["evidence_mode"] = "unresolved"
    expect_red("red: unresolved evidence mode may never certify",
               bad, "edge_certified_unresolved")

    # red 16 — clitic edge without the exact component surface
    bad = _green_bundle()
    bad["edges"][3]["details"].pop("component_surface")
    expect_red("red: clitic_host_edge without component surface",
               bad, "edge_clitic_component")

    if failures:
        print("\n%d SELF-TEST CASE(S) FAILED" % len(failures))
        return 1
    print("\nPARTICLE PROJECTION PARITY SELF-TEST PASS")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="*", help="parity input bundle JSON file(s)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not args.bundles:
        parser.error("provide bundle file(s) or --self-test")
    rc = 0
    for path in args.bundles:
        with open(path, encoding="utf-8") as handle:
            bundle = json.load(handle)
        errors = validate_bundle(bundle)
        if errors:
            rc = 1
            print("FAIL %s" % path)
            for err in errors:
                print("   ", err)
        else:
            print("ok   %s" % path)
    if rc == 0:
        print("PARTICLE PROJECTION PARITY VALIDATION PASS")
    return rc


if __name__ == "__main__":
    sys.exit(main())
