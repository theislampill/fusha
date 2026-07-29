#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry-transclusion ontology invariants (owner steer §3-§4, executable §15).

Every p/v/n entry is a first-class knowledge node.  This suite makes the
owner's 12 transclusion invariants executable against the EXISTING ontology
(qamus.graph_edge.v1 vocabulary in tools/build_typed_edge_crosswalk.py plus
the particle extension in qamus/schemas/particle-edge-ontology.schema.json) —
it EXTENDS that single vocabulary and deliberately introduces no new edge
kinds.

Owner-name -> repo-idiom mapping (the transclusion crosswalk):

  entry_has_lexeme                          -> lexeme_entry_edge
  entry_has_sense                           -> sense_entry_edge
  entry_documents_form                      -> form_entry_edge
  entry_root_family                         -> root_family_edge
  entry_has_example_card                    -> source_card_edge (+ card node)
  card_selects_occurrence                   -> selected_example_edge
  card_displays_context_occurrence          -> display_local_to_canonical_crosswalk_edge
  occurrence_instantiates_lexeme            -> lexeme_entry_edge (occurrence -> entry,
                                               certified attachment only)
  occurrence_realizes_form_of_entry         -> form_entry_edge
  occurrence_instantiates_entry_sense       -> sense_entry_edge (via sense node)
  occurrence_contains_morpheme              -> clitic_host_edge +
                                               qamus.particle_morpheme_occurrence.v1 node
  occurrence_shares_root_with_entry /
  occurrence_is_root_family_member          -> root_family_edge
                                               (guard root_agreement_never_lexeme_edge;
                                               DISTINCT from lexeme_entry_edge — root
                                               sharing NEVER entails entry identity)
  morpheme_occurrence_instantiates_particle_entry
                                            -> particle_entry_candidate_edge /
                                               particle_entry_certified_edge (since #115/#118)
  morpheme_occurrence_instantiates_particle_sense
                                            -> particle_sense_candidate_edge /
                                               particle_sense_certified_edge
  occurrence_has_public_appearance          -> rendered_appearance_edge /
                                               particle_occurrence_appearance_edge
  appearance_consumes_projection            -> details.projection_hash on the
                                               appearance edge (one canonical projection
                                               per occurrence; pages may differ only in
                                               page-role chrome)
  projection_derived_from_certified_facts   -> decision_evidence_edge +
                                               fact dependent_projection_ids
                                               (tools/certify_typed_fact.py)
  certified_fact_supported_by_evidence      -> source_evidence_edge / evidence[] +
                                               evidence-bundle requirement in
                                               tools/certify_typed_fact.py
  entry_reverse_lists_occurrence            -> particle_entry_reverse_occurrence_edge +
                                               lexeme-entry-crosswalk.reverse records
  rule_learned_from_occurrence              -> skill-rule-registry rows
                                               (evidence_addresses cite the occurrence)
  drill_uses_certified_occurrence           -> drill/teaching asset rows must cite a
                                               loc certified in the fact trail
  (page context)                            -> page_context_entry_edge, guards
                                               entry_id_is_verse_context +
                                               never_lexeme_edge (NON-lexical, always)

Each of the 12 tests is red-first: the invariant checker is exercised against
a healthy fixture (green) AND a deliberately corrupted fixture (must flag the
specific violation code).  Multi-entry tokens are first-class: one token may
carry several morpheme edges to different entries.

Wired into tools/check_regressions.py (ENTRYGRAPH gate).
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools import build_typed_edge_crosswalk as G  # noqa: E402
from tools import certify_typed_fact as CF  # noqa: E402

EDGE_SCHEMA = G.SCHEMA
# p007 (lam li-/la-) per qamus/data/particle-tranche-membership.json
P007_ENTRY = "b10a1ee04666"
# p002 (wa) per the same membership table
P_WA_ENTRY = "2fcbd8198aa6"
VERB_ENTRY = "00107b99a50e"
NOUN_ENTRY = "001242c409ae"

_LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")

PROJECTION_SCHEMA_PATH = os.path.join(
    _ROOT, "qamus", "schemas", "public-hover-projection.schema.json")
COMPLETION_SCHEMA_PATH = os.path.join(
    _ROOT, "qamus", "schemas", "entry-completion-states.schema.json")

# Fields of a projection that carry the stable public entry+occurrence links.
PROJECTION_LINK_FIELDS = ("row_id", "entry_id", "card_id", "canonical_quran_loc")


def _edge(edge_type, from_node_id, to_node_id, status, *, guards=(), evidence=(),
          details=None, edge_id=None):
    """Plain qamus.graph_edge.v1 row (same shape as build_typed_edge_crosswalk).

    Built directly (not via G.make_edge) only because the particle extension
    legitimately uses the morpheme-occurrence node type from
    qamus/schemas/particle-edge-ontology.schema.json.  The edge TYPE vocabulary
    is still asserted against the one canonical EDGE_TYPE_SET.
    """

    if edge_type not in G.EDGE_TYPE_SET:
        raise ValueError("unknown edge type (vocabulary fork): %r" % edge_type)
    if status not in G.STATUS_SET:
        raise ValueError("unknown status: %r" % status)
    row = {
        "schema": EDGE_SCHEMA,
        "edge_id": edge_id or ("edge:test:%s:%s>%s" % (edge_type, from_node_id, to_node_id)),
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "from_node_type": from_node_id.split(":", 1)[0],
        "to_node_id": to_node_id,
        "to_node_type": to_node_id.split(":", 1)[0],
        "status": status,
        "guards": sorted(guards),
        "evidence": [dict(item) for item in evidence],
        "producer": {"id": "tools.test_entry_transclusion_invariants", "version": "1"},
        "details": dict(details or {}),
    }
    return row


def _projection(row_id, entry_id, loc, surface, gloss):
    return {
        "schema": "qamus/public-hover-projection@1",
        "row_id": row_id,
        "entry_id": entry_id,
        "card_id": "card:%s:u1:x1" % entry_id,
        "surface": surface,
        "canonical_quran_loc": loc,
        "canonical_wbw_loc": loc,
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "public_gloss": gloss,
        "token_contribution": gloss,
        "segments": [{"surface": surface, "role": "stem"}],
        "qg_classes": [],
        "public_boundary": "public",
        "live_mutation_allowed": False,
    }


def healthy_fixture():
    """A small transclusion graph exercising every invariant, all healthy."""

    edges = []
    # locA: real p007 li- morpheme on a host token shown on a VERB entry page
    # and on the reader page (same occurrence, two public appearances).
    edges.append(_edge(
        "rendered_appearance_edge", "occurrence:2:255:1", "appearance:2:255:1:1",
        "deterministic_exact",
        guards=["canonical_projection_hash_present"],
        evidence=[{"address": "occurrence-appearances:2:255:1:appearances[0]",
                   "method": "existing_occurrence_appearance_index"}],
        details={"loc": "2:255:1", "appearance_index": 1, "page_id": "reader:2:255",
                 "projection_hash": "sha256:projA"}))
    edges.append(_edge(
        "rendered_appearance_edge", "occurrence:2:255:1", "appearance:2:255:1:2",
        "deterministic_exact",
        guards=["canonical_projection_hash_present"],
        evidence=[{"address": "occurrence-appearances:2:255:1:appearances[1]",
                   "method": "existing_occurrence_appearance_index"}],
        details={"loc": "2:255:1", "appearance_index": 2,
                 "page_id": "entry:%s" % VERB_ENTRY,
                 "projection_hash": "sha256:projA"}))
    # Morpheme occurrence m1: the li- prefix inside the host token at locA.
    morphemes = [
        {"schema": "qamus.particle_morpheme_occurrence.v1",
         "morpheme_occurrence_id": "m:2:255:1:li",
         "host_occurrence_id": "quran:2:255:1",
         "base_letter_span": {"start": 0, "end": 1},
         "component_surface": "لِ"},
        # Multi-entry token at locC: wa- + li- on one host.
        {"schema": "qamus.particle_morpheme_occurrence.v1",
         "morpheme_occurrence_id": "m:3:15:4:wa",
         "host_occurrence_id": "quran:3:15:4",
         "base_letter_span": {"start": 0, "end": 1},
         "component_surface": "وَ"},
        {"schema": "qamus.particle_morpheme_occurrence.v1",
         "morpheme_occurrence_id": "m:3:15:4:li",
         "host_occurrence_id": "quran:3:15:4",
         "base_letter_span": {"start": 1, "end": 2},
         "component_surface": "لِ"},
    ]
    for morpheme_id, entry_id in (("m:2:255:1:li", P007_ENTRY),
                                  ("m:3:15:4:wa", P_WA_ENTRY),
                                  ("m:3:15:4:li", P007_ENTRY)):
        edges.append(_edge(
            "particle_entry_candidate_edge",
            "morpheme-occurrence:%s" % morpheme_id, "entry:%s" % entry_id,
            "candidate",
            guards=["surface_exact", "occurrence_address_exact"],
            evidence=[{"address": "quran:%s" % morpheme_id.split(":", 1)[1].rsplit(":", 1)[0],
                       "method": "explicit_occurrence_address"}],
            details={"occurrence_id": "quran:" + morpheme_id.split(":", 1)[1].rsplit(":", 1)[0],
                     "surface": "لِ" if morpheme_id.endswith(":li") else "وَ",
                     "evidence_mode": "cross_source_corroboration",
                     "fact_id": "sha256:fixture-" + morpheme_id}))
        edges.append(_edge(
            "clitic_host_edge",
            "occurrence:" + morpheme_id.split(":", 1)[1].rsplit(":", 1)[0],
            "morpheme-occurrence:%s" % morpheme_id,
            "deterministic_exact",
            guards=["surface_exact"],
            evidence=[{"address": "quran:" + morpheme_id.split(":", 1)[1].rsplit(":", 1)[0],
                       "method": "explicit_occurrence_address"}],
            details={"occurrence_id": "quran:" + morpheme_id.split(":", 1)[1].rsplit(":", 1)[0],
                     "surface": "host", "component_surface": "لِ",
                     "evidence_mode": "direct_source_attestation",
                     "fact_id": "sha256:fixture-host-" + morpheme_id}))
    # Page context: the verse whitelist entry_id (a NOUN entry page context) —
    # a NON-lexical relation, guarded, never re-typed.
    edges.append(_edge(
        "page_context_entry_edge", "occurrence:2:255:1", "entry:%s" % NOUN_ENTRY,
        "deterministic_exact",
        guards=["entry_id_is_verse_context", "never_lexeme_edge"],
        evidence=[{"address": "whitelist:2:255:1:entry_id",
                   "method": "whitelist_entry_id_page_context"}],
        details={"loc": "2:255:1", "page_context_only": True}))
    # Certified documented form of the VERB entry at locF, with reverse listing.
    edges.append(_edge(
        "form_entry_edge", "occurrence:4:1:2", "entry:%s" % VERB_ENTRY,
        "certified",
        guards=["documented_form_or_source_evidence", "orthography_guard_v1"],
        evidence=[{"address": "entry:%s:usage[0].forms[0]" % VERB_ENTRY,
                   "method": "documented_entry_form"},
                  {"address": "occurrence:4:1:2", "method": "certified_fact_attachment"}],
        details={"loc": "4:1:2", "form_index": 1}))
    edges.append(_edge(
        "lexeme_entry_edge", "occurrence:4:1:2", "entry:%s" % VERB_ENTRY,
        "certified",
        guards=["certified_morphology_attached", "not_page_context_entry_id"],
        evidence=[{"address": "entry:%s:usage[0].forms[0]" % VERB_ENTRY,
                   "method": "documented_entry_form"},
                  {"address": "occurrence:4:1:2", "method": "certified_fact_attachment"}],
        details={"origin": "certified_occurrence_crosswalk"}))
    edges.append(_edge(
        "sense_entry_edge", "sense:%s:s1" % VERB_ENTRY, "entry:%s" % VERB_ENTRY,
        "certified",
        guards=["sense_identity_required"],
        evidence=[{"address": "entry:%s:senses[0]" % VERB_ENTRY,
                   "method": "sense_identity_from_documented_form"}],
        details={"sense_id": "sense:%s:s1" % VERB_ENTRY}))
    # Root family: same root, DIFFERENT entry — relation only, never identity.
    edges.append(_edge(
        "root_family_edge", "occurrence:4:1:2", "entry:%s" % NOUN_ENTRY,
        "candidate",
        guards=["root_agreement_never_lexeme_edge"],
        evidence=[{"address": "entry:%s:root" % NOUN_ENTRY,
                   "method": "root_agreement_only"}],
        details={"root": "خ د ع"}))
    # Card / source chain for the certified occurrence (reverse trace target).
    edges.append(_edge(
        "source_card_edge",
        "selected-word:%s:s1:u1:f1:o4:1:2" % VERB_ENTRY,
        "card:%s:u1:x1" % VERB_ENTRY,
        "deterministic_exact",
        guards=["card_identity_from_ledger"],
        evidence=[{"address": "card:12:3", "method": "ledger_source_card_identity"}],
        details={"card_ref": "12:3"}))
    edges.append(_edge(
        "selected_example_edge", "card:%s:u1:x1" % VERB_ENTRY, "occurrence:4:1:2",
        "deterministic_exact",
        guards=["selected_example_is_not_page_context"],
        evidence=[{"address": "card:12:3:example", "method": "ledger_display_local_example"}],
        details={"card_ref": "12:3"}))
    edges.append(_edge(
        "source_evidence_edge", "occurrence:4:1:2", "source:card-photo:12:3",
        "deterministic_exact",
        guards=["photo_is_source_evidence"],
        evidence=[{"address": "card:12:3:photo", "method": "ledger_source_photo"}],
        details={"occurrence_id": "quran:4:1:2", "surface": "form",
                 "evidence_mode": "direct_source_attestation",
                 "fact_id": "sha256:fixture-src"}))

    projections = [
        _projection("row:2:255:1", P007_ENTRY, "2:255:1", "لِلَّهِ", "to/for God"),
        # Same surface مَا, two DIFFERENT occurrences — glosses may differ.
        _projection("row:2:284:10", P007_ENTRY, "2:284:10", "مَا", "what(ever)"),
        _projection("row:2:284:2", P007_ENTRY, "2:284:2", "مَا", "not"),
        _projection("row:4:1:2", VERB_ENTRY, "4:1:2", "خَدَعَ", "he deceived"),
    ]

    return {
        "edges": edges,
        "morpheme_occurrences": morphemes,
        "projections": projections,
        # Morphology facts: base-letter spans that are RADICAL (lexical root
        # letters) per host occurrence.  locB لَبِثَ: initial lam is a radical.
        "radical_spans": {"quran:2:259:2": [(0, 1)]},
        # Owner expectation: these morpheme->entry links MUST exist (multi-entry
        # token support: one token, several morphemes, several entries; the
        # host at 2:255:1 is displayed on a VERB entry page and the link must
        # exist regardless of page type).
        "expected_particle_links": [
            ("m:2:255:1:li", P007_ENTRY),
            ("m:3:15:4:wa", P_WA_ENTRY),
            ("m:3:15:4:li", P007_ENTRY),
        ],
        # Certified documented forms that MUST be reflected as entry/form edges.
        "certified_documented_forms": [("4:1:2", VERB_ENTRY)],
        # Reverse crosswalk records (entry -> occurrences), the entry page list.
        "reverse": [{"entry_id": VERB_ENTRY, "occurrence_ids": ["4:1:2"]}],
        # Teaching assets: rules and drills citing their source occurrences.
        "rules": [{"skill_rule_id": "RULE-LI-001",
                   "evidence_addresses": ["quran:2:255:1"],
                   "positive_examples": ["quran:2:255:1"]}],
        "drills": [{"drill_id": "DRILL-001", "occurrence_loc": "4:1:2"}],
        # Locs whose entry linkage is certified (drill denominator).
        "certified_locs": ["4:1:2"],
    }


# --------------------------------------------------------------------------- #
# Invariant checker: returns a list of (code, message) violations.
# --------------------------------------------------------------------------- #

def entry_transclusion_violations(fixture):
    violations = []

    def flag(code, message):
        violations.append((code, message))

    edges = fixture.get("edges") or []
    morphemes = {m["morpheme_occurrence_id"]: m
                 for m in fixture.get("morpheme_occurrences") or []}

    # V01 — one occurrence, one projection: every public appearance of the
    # same occurrence consumes the SAME canonical projection hash.
    hashes = {}
    for edge in edges:
        if edge["edge_type"] not in ("rendered_appearance_edge",
                                     "particle_occurrence_appearance_edge"):
            continue
        details = edge.get("details") or {}
        occurrence = edge["from_node_id"]
        item = details.get("projection_hash")
        if not item:
            flag("V01_projection_fork_across_pages",
                 "%s appearance without projection_hash" % occurrence)
            continue
        hashes.setdefault(occurrence, set()).add(item)
    for occurrence, found in sorted(hashes.items()):
        if len(found) > 1:
            flag("V01_projection_fork_across_pages",
                 "%s consumed by appearances with %d different projection hashes"
                 % (occurrence, len(found)))

    # V02 — projections are keyed by occurrence, never by surface: a row_id
    # must never serve two different canonical locs, and every projection row
    # must carry its own canonical loc.  (Same surface at DIFFERENT
    # occurrences legitimately may differ — that is the healthy fixture.)
    rows_by_id = {}
    for row in fixture.get("projections") or []:
        loc = str(row.get("canonical_quran_loc") or "")
        if not loc:
            flag("V02_projection_row_shared_across_occurrences",
                 "projection %r has no canonical occurrence loc" % row.get("row_id"))
            continue
        prior = rows_by_id.setdefault(row.get("row_id"), loc)
        if prior != loc:
            flag("V02_projection_row_shared_across_occurrences",
                 "projection row %r reused for locs %s and %s"
                 % (row.get("row_id"), prior, loc))

    # V03 — a lexical (radical) letter is never claimed as a particle
    # morpheme: any particle edge whose morpheme span overlaps a radical span
    # of the host is a false transclusion.
    radical = fixture.get("radical_spans") or {}
    for edge in edges:
        if not edge["edge_type"].startswith("particle_entry"):
            continue
        if edge["from_node_type"] != "morpheme-occurrence":
            continue
        morpheme = morphemes.get(edge["from_node_id"].split(":", 1)[1])
        if morpheme is None:
            flag("V03_radical_letter_claimed_as_particle",
                 "%s has no morpheme-occurrence identity row" % edge["edge_id"])
            continue
        span = morpheme["base_letter_span"]
        for start, end in radical.get(morpheme["host_occurrence_id"], []):
            if span["start"] < end and start < span["end"]:
                flag("V03_radical_letter_claimed_as_particle",
                     "%s claims radical letters [%d,%d) of %s as particle %s"
                     % (edge["edge_id"], span["start"], span["end"],
                        morpheme["host_occurrence_id"], edge["to_node_id"]))

    # V04/V07 — expected morpheme links exist (page type never blocks a real
    # morpheme link; one token may link to SEVERAL entries via separate
    # morphemes), and sibling morphemes never overlap.
    have_links = {(e["from_node_id"].split(":", 1)[1], e["to_node_id"].split(":", 1)[1])
                  for e in edges
                  if e["edge_type"].startswith("particle_entry")
                  and e["from_node_type"] == "morpheme-occurrence"}
    for morpheme_id, entry_id in fixture.get("expected_particle_links") or []:
        if (morpheme_id, entry_id) not in have_links:
            flag("V04_missing_particle_morpheme_edge",
                 "expected morpheme link %s -> entry:%s is missing"
                 % (morpheme_id, entry_id))
    by_host = {}
    for morpheme in morphemes.values():
        by_host.setdefault(morpheme["host_occurrence_id"], []).append(morpheme)
    for host, items in sorted(by_host.items()):
        items = sorted(items, key=lambda m: (m["base_letter_span"]["start"],
                                             m["base_letter_span"]["end"]))
        for first, second in zip(items, items[1:]):
            if second["base_letter_span"]["start"] < first["base_letter_span"]["end"]:
                flag("V07_morpheme_span_overlap",
                     "morphemes %s and %s overlap on %s"
                     % (first["morpheme_occurrence_id"],
                        second["morpheme_occurrence_id"], host))

    # V05 — root sharing never entails entry identity: a lexeme/form edge whose
    # ONLY evidence is root agreement is a forbidden promotion, and every
    # root_family_edge must carry the structural guard.
    for edge in edges:
        if edge["edge_type"] == "root_family_edge":
            if "root_agreement_never_lexeme_edge" not in (edge.get("guards") or []):
                flag("V05_root_agreement_promoted_to_lexeme",
                     "%s lacks the root_agreement_never_lexeme_edge guard"
                     % edge["edge_id"])
        if edge["edge_type"] in ("lexeme_entry_edge", "form_entry_edge"):
            methods = {item.get("method") for item in edge.get("evidence") or []}
            if methods and methods <= {"root_agreement_only"}:
                flag("V05_root_agreement_promoted_to_lexeme",
                     "%s asserts entry identity on root agreement alone"
                     % edge["edge_id"])

    # V06 — a certified documented form is reflected as an entry/form edge.
    for loc, entry_id in fixture.get("certified_documented_forms") or []:
        found = any(
            edge["edge_type"] in ("form_entry_edge", "lexeme_entry_edge")
            and edge["status"] == "certified"
            and edge["from_node_id"] == "occurrence:%s" % loc
            and edge["to_node_id"] == "entry:%s" % entry_id
            for edge in edges)
        if not found:
            flag("V06_certified_form_without_entry_edge",
                 "certified documented form at %s has no certified edge to entry:%s"
                 % (loc, entry_id))

    # V08 — the page-context entry_id is never a lexical assertion: the
    # page-context edge stays guarded, and no lexeme/form edge may be sourced
    # from the whitelist page-context entry_id.
    page_pairs = set()
    for edge in edges:
        if edge["edge_type"] == "page_context_entry_edge":
            guards = set(edge.get("guards") or [])
            if not {"entry_id_is_verse_context", "never_lexeme_edge"} <= guards:
                flag("V08_page_context_promoted_to_lexical",
                     "%s lost its verse-context guards" % edge["edge_id"])
            page_pairs.add((edge["from_node_id"], edge["to_node_id"]))
    for edge in edges:
        if edge["edge_type"] in ("lexeme_entry_edge", "form_entry_edge",
                                 "sense_entry_edge"):
            methods = {item.get("method") for item in edge.get("evidence") or []}
            if "whitelist_entry_id_page_context" in methods:
                flag("V08_page_context_promoted_to_lexical",
                     "%s re-types the page-context entry_id as a lexical edge"
                     % edge["edge_id"])

    # V10 — reverse trace: every certified occurrence->entry lexeme edge is
    # listed on the entry's reverse record, and the occurrence reaches source
    # evidence (a source/card chain with at least one evidence address).
    reverse = {row["entry_id"]: set(row.get("occurrence_ids") or [])
               for row in fixture.get("reverse") or []}
    for edge in edges:
        if edge["edge_type"] != "lexeme_entry_edge" or edge["status"] != "certified":
            continue
        if edge["from_node_type"] != "occurrence":
            continue
        loc = edge["from_node_id"].split(":", 1)[1]
        entry_id = edge["to_node_id"].split(":", 1)[1]
        if loc not in reverse.get(entry_id, set()):
            flag("V10_reverse_trace_broken",
                 "entry:%s reverse record does not list certified occurrence %s"
                 % (entry_id, loc))
        has_source = any(
            other["edge_type"] in ("source_evidence_edge", "source_card_edge",
                                   "source_photo_edge", "selected_example_edge")
            and (other["from_node_id"] == edge["from_node_id"]
                 or other["to_node_id"] == edge["from_node_id"])
            and (other.get("evidence") or [])
            for other in edges)
        if not has_source:
            flag("V10_reverse_trace_broken",
                 "certified occurrence %s reaches no source evidence" % loc)

    # V11 — teaching assets cite their source occurrences; drills only ever
    # use certified occurrences.
    for rule in fixture.get("rules") or []:
        cites = [addr for addr in (rule.get("evidence_addresses") or [])
                 + (rule.get("positive_examples") or [])
                 if str(addr).startswith("quran:")]
        if not cites:
            flag("V11_teaching_asset_without_source_occurrence",
                 "rule %r cites no source occurrence" % rule.get("skill_rule_id"))
    certified_locs = set(fixture.get("certified_locs") or [])
    for drill in fixture.get("drills") or []:
        if drill.get("occurrence_loc") not in certified_locs:
            flag("V11_drill_uses_uncertified_occurrence",
                 "drill %r uses non-certified occurrence %r"
                 % (drill.get("drill_id"), drill.get("occurrence_loc")))

    # V12 — the public website payload carries stable entry+occurrence links,
    # checked at schema level against the committed projection contract.
    try:
        with open(PROJECTION_SCHEMA_PATH, encoding="utf-8") as handle:
            contract = json.load(handle)
        required = set(contract.get("required") or [])
    except OSError:
        required = set()
        flag("V12_payload_contract_violation",
             "projection contract schema is missing from the repository")
    for field in PROJECTION_LINK_FIELDS:
        if required and field not in required:
            flag("V12_payload_contract_violation",
                 "projection contract no longer requires %r" % field)
    loc_pattern = None
    if required:
        loc_pattern = ((contract.get("properties") or {})
                       .get("canonical_quran_loc") or {}).get("pattern")
    for row in fixture.get("projections") or []:
        for field in PROJECTION_LINK_FIELDS:
            if not str(row.get(field) or ""):
                flag("V12_payload_contract_violation",
                     "projection %r lacks stable link field %r"
                     % (row.get("row_id"), field))
        loc = str(row.get("canonical_quran_loc") or "")
        pattern = loc_pattern or _LOC_RE.pattern
        if loc and not re.match(pattern, loc):
            flag("V12_payload_contract_violation",
                 "projection %r loc %r is not a canonical occurrence address"
                 % (row.get("row_id"), loc))

    return violations


def _codes(violations):
    return {code for code, _ in violations}


class EntryTransclusionInvariantTests(unittest.TestCase):
    """The owner's 12 executable invariants (steer §15), each red-first."""

    def setUp(self):
        self.fixture = healthy_fixture()

    def assert_green(self, fixture=None):
        violations = entry_transclusion_violations(fixture or self.fixture)
        self.assertEqual(violations, [], "healthy fixture must be violation-free")

    def assert_red(self, fixture, code):
        codes = _codes(entry_transclusion_violations(fixture))
        self.assertIn(code, codes,
                      "corrupted fixture must trip %s (got %s)" % (code, sorted(codes)))

    # 1. Same occurrence on several pages -> ONE projection.
    def test_01_same_occurrence_many_pages_one_projection(self):
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        for edge in corrupted["edges"]:
            if (edge["edge_type"] == "rendered_appearance_edge"
                    and edge["details"].get("appearance_index") == 2):
                edge["details"]["projection_hash"] = "sha256:projFORKED"
        self.assert_red(corrupted, "V01_projection_fork_across_pages")

    # 2. Same surface, different occurrences -> may legitimately differ,
    #    because projections are keyed by occurrence, never by surface.
    def test_02_same_surface_different_occurrences_may_differ(self):
        # Healthy fixture already contains ما at 2:284:10 ("what") and at
        # 2:284:2 ("not") with different glosses — this must be green.
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        # Corruption: the builder keys by surface and reuses one row for both.
        corrupted["projections"][2]["row_id"] = corrupted["projections"][1]["row_id"]
        self.assert_red(corrupted, "V02_projection_row_shared_across_occurrences")

    # 3. A lexical (radical) letter that merely looks like a particle is NOT
    #    linked to p007.
    def test_03_radical_letter_not_linked_to_p007(self):
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        corrupted["morpheme_occurrences"].append(
            {"schema": "qamus.particle_morpheme_occurrence.v1",
             "morpheme_occurrence_id": "m:2:259:2:falseli",
             "host_occurrence_id": "quran:2:259:2",  # لَبِثَ — lam is a radical
             "base_letter_span": {"start": 0, "end": 1},
             "component_surface": "لَ"})
        corrupted["edges"].append(_edge(
            "particle_entry_candidate_edge",
            "morpheme-occurrence:m:2:259:2:falseli", "entry:%s" % P007_ENTRY,
            "candidate",
            guards=["surface_exact"],
            evidence=[{"address": "quran:2:259:2", "method": "clitic_prefix_normalized"}],
            details={"occurrence_id": "quran:2:259:2", "surface": "لَ",
                     "evidence_mode": "unresolved", "fact_id": "sha256:false"}))
        self.assert_red(corrupted, "V03_radical_letter_claimed_as_particle")

    # 4. A REAL p007 morpheme is linked even when its host is displayed on a
    #    verb or noun entry page.
    def test_04_real_morpheme_linked_on_v_and_n_pages(self):
        # Healthy: host 2:255:1 appears on entry:<verb> page AND keeps its link.
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        corrupted["edges"] = [
            edge for edge in corrupted["edges"]
            if not (edge["edge_type"] == "particle_entry_candidate_edge"
                    and edge["from_node_id"] == "morpheme-occurrence:m:2:255:1:li")]
        self.assert_red(corrupted, "V04_missing_particle_morpheme_edge")

    # 5. Root sharing NEVER entails verb-entry identity.
    def test_05_root_sharing_is_not_entry_identity(self):
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        corrupted["edges"].append(_edge(
            "lexeme_entry_edge", "occurrence:4:1:2", "entry:%s" % NOUN_ENTRY,
            "candidate",
            guards=["orthography_guard_v1"],
            evidence=[{"address": "entry:%s:root" % NOUN_ENTRY,
                       "method": "root_agreement_only"}],
            details={"root": "خ د ع"}))
        self.assert_red(corrupted, "V05_root_agreement_promoted_to_lexeme")
        # Guard-stripping the root_family_edge is the same violation.
        stripped = copy.deepcopy(self.fixture)
        for edge in stripped["edges"]:
            if edge["edge_type"] == "root_family_edge":
                edge["guards"] = []
        self.assert_red(stripped, "V05_root_agreement_promoted_to_lexeme")

    # 6. A certified documented form is reflected as an entry/form edge.
    def test_06_certified_documented_form_has_entry_edge(self):
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        corrupted["edges"] = [
            edge for edge in corrupted["edges"]
            if not (edge["edge_type"] in ("form_entry_edge", "lexeme_entry_edge")
                    and edge["from_node_id"] == "occurrence:4:1:2")]
        self.assert_red(corrupted, "V06_certified_form_without_entry_edge")

    # 7. One token -> several entries via separate, non-overlapping morphemes.
    def test_07_multi_entry_token_separate_morphemes(self):
        # Healthy: host 3:15:4 links to BOTH the wa entry and p007.
        self.assert_green()
        collapsed = copy.deepcopy(self.fixture)
        collapsed["edges"] = [
            edge for edge in collapsed["edges"]
            if not (edge["edge_type"] == "particle_entry_candidate_edge"
                    and edge["from_node_id"] == "morpheme-occurrence:m:3:15:4:wa")]
        self.assert_red(collapsed, "V04_missing_particle_morpheme_edge")
        overlapping = copy.deepcopy(self.fixture)
        for morpheme in overlapping["morpheme_occurrences"]:
            if morpheme["morpheme_occurrence_id"] == "m:3:15:4:li":
                morpheme["base_letter_span"] = {"start": 0, "end": 2}
        self.assert_red(overlapping, "V07_morpheme_span_overlap")

    # 8. The page-context entry_id never becomes a lexical edge.
    def test_08_page_context_never_lexical(self):
        self.assert_green()
        corrupted = copy.deepcopy(self.fixture)
        corrupted["edges"].append(_edge(
            "lexeme_entry_edge", "occurrence:2:255:1", "entry:%s" % NOUN_ENTRY,
            "candidate",
            guards=["orthography_guard_v1"],
            evidence=[{"address": "whitelist:2:255:1:entry_id",
                       "method": "whitelist_entry_id_page_context"}],
            details={"origin": "page_context_retype"}))
        self.assert_red(corrupted, "V08_page_context_promoted_to_lexical")
        stripped = copy.deepcopy(self.fixture)
        for edge in stripped["edges"]:
            if edge["edge_type"] == "page_context_entry_edge":
                edge["guards"] = ["entry_id_is_verse_context"]
        self.assert_red(stripped, "V08_page_context_promoted_to_lexical")

    # 9. Revoking a certified fact invalidates dependent projections
    #    (certify_typed_fact revocation cascade, consumed — not re-derived).
    def test_09_revocation_invalidates_dependents(self):
        with tempfile.TemporaryDirectory(prefix="entrygraph-revoke-") as td:
            store = CF.TypedFactCertificationStore(os.path.join(td, "store"))
            actor = "lane:entry-transclusion-invariants"
            ts = "2026-07-28T00:00:00Z"
            root = CF._synthetic_fact("81", "singular_pattern",
                                      "direct_source_attestation")
            other = CF._synthetic_fact(
                "82", "root", "cross_source_corroboration",
                addresses=[{"address": "quran:2:13:82", "source_kind": "quran_token"},
                           {"address": "entry:fixture82:root",
                            "source_kind": "qamus_entry_field"}])
            derived = CF._synthetic_fact(
                "83", "paired_y_removal",
                "deterministic_derivation_from_certified_facts",
                dependency_ids=[root["fact_id"], other["fact_id"]],
                chain_inputs=[root["fact_id"], other["fact_id"]])
            for fact in (root, other, derived):
                store.register(fact, contract_id="fixture:contract",
                               actor=actor, timestamp=ts)
                store.transition(fact["fact_id"], "review_required", actor=actor,
                                 timestamp=ts, reason="bundle assembled")
            store.transition(root["fact_id"], "certified", actor=actor,
                             timestamp=ts, reason="attestation bundle complete")
            store.transition(other["fact_id"], "certified", actor=actor,
                             timestamp=ts, reason="two source families agree")
            store.transition(derived["fact_id"], "certified", actor=actor,
                             timestamp=ts, reason="all inputs certified")
            # Green: revoking the root cascades to the derived projection fact.
            events = store.revoke(root["fact_id"], actor=actor, timestamp=ts,
                                  reason="source capture corrected")
            statuses = store.status_by_id()
            self.assertEqual(statuses[root["fact_id"]], "review_required")
            self.assertEqual(statuses[derived["fact_id"]], "review_required",
                             "dependent projection fact must be de-certified")
            self.assertEqual(statuses[other["fact_id"]], "certified",
                             "unrelated fact must be untouched")
            self.assertTrue(any(event.get("event_type") == "revoke_cascade"
                                for event in events))
            self.assertEqual(store.validate_trail(), [])
            # Red-first: a forged revoke WITHOUT the cascade must be detected.
            forged_dir = os.path.join(td, "forged")
            forged = CF.TypedFactCertificationStore(forged_dir)
            for fact in (root, other, derived):
                forged.register(fact, contract_id="fixture:contract",
                                actor=actor, timestamp=ts)
                forged.transition(fact["fact_id"], "review_required", actor=actor,
                                  timestamp=ts, reason="bundle assembled")
            forged.transition(root["fact_id"], "certified", actor=actor,
                              timestamp=ts, reason="attestation bundle complete")
            forged.transition(other["fact_id"], "certified", actor=actor,
                              timestamp=ts, reason="two source families agree")
            forged.transition(derived["fact_id"], "certified", actor=actor,
                              timestamp=ts, reason="all inputs certified")
            forged._append_event({
                "event_type": "revoke",
                "fact_id": root["fact_id"],
                "from_status": "certified",
                "to_status": "review_required",
                "actor": actor,
                "timestamp": ts,
                "reason": "forged revoke without cascade",
            })
            errors = forged.validate_trail()
            self.assertTrue(errors,
                            "a revoke without its cascade must invalidate the trail")

    # 10. The reverse trace reaches entry, occurrence, source and evidence.
    def test_10_reverse_trace_reaches_source_evidence(self):
        self.assert_green()
        broken_reverse = copy.deepcopy(self.fixture)
        broken_reverse["reverse"] = [{"entry_id": VERB_ENTRY, "occurrence_ids": []}]
        self.assert_red(broken_reverse, "V10_reverse_trace_broken")
        broken_source = copy.deepcopy(self.fixture)
        broken_source["edges"] = [
            edge for edge in broken_source["edges"]
            if edge["edge_type"] not in ("source_evidence_edge", "source_card_edge",
                                         "selected_example_edge")]
        self.assert_red(broken_source, "V10_reverse_trace_broken")

    # 11. Rules and teaching assets cite their source occurrence; drills only
    #     ever use certified occurrences.
    def test_11_teaching_assets_cite_source_occurrence(self):
        self.assert_green()
        uncited = copy.deepcopy(self.fixture)
        uncited["rules"][0]["evidence_addresses"] = ["book:page-12"]
        uncited["rules"][0]["positive_examples"] = []
        self.assert_red(uncited, "V11_teaching_asset_without_source_occurrence")
        uncertified = copy.deepcopy(self.fixture)
        uncertified["drills"][0]["occurrence_loc"] = "2:259:2"
        self.assert_red(uncertified, "V11_drill_uses_uncertified_occurrence")

    # 12. The website payload carries stable entry+occurrence links
    #     (schema-level check against the committed projection contract).
    def test_12_public_payload_carries_stable_links(self):
        self.assert_green()
        # The committed contract itself must require the link fields.
        with open(PROJECTION_SCHEMA_PATH, encoding="utf-8") as handle:
            contract = json.load(handle)
        for field in PROJECTION_LINK_FIELDS:
            self.assertIn(field, contract.get("required") or [],
                          "projection contract must require %r" % field)
        corrupted = copy.deepcopy(self.fixture)
        del corrupted["projections"][0]["entry_id"]
        corrupted["projections"][0]["entry_id"] = ""
        self.assert_red(corrupted, "V12_payload_contract_violation")
        bad_loc = copy.deepcopy(self.fixture)
        bad_loc["projections"][3]["canonical_quran_loc"] = "page-44"
        self.assert_red(bad_loc, "V12_payload_contract_violation")


class OntologyVocabularyTests(unittest.TestCase):
    """The mapping table targets exist in the ONE canonical vocabulary."""

    REPO_IDIOM_TARGETS = [
        "lexeme_entry_edge", "sense_entry_edge", "form_entry_edge",
        "root_family_edge", "source_card_edge", "selected_example_edge",
        "display_local_to_canonical_crosswalk_edge", "canonical_occurrence_edge",
        "rendered_appearance_edge", "decision_evidence_edge",
        "citation_form_display_edge", "page_context_entry_edge",
        # particle extension (#115/#118) — morpheme-level transclusion:
        "particle_entry_candidate_edge", "particle_entry_certified_edge",
        "particle_sense_candidate_edge", "particle_sense_certified_edge",
        "clitic_host_edge", "particle_occurrence_appearance_edge",
        "particle_entry_reverse_occurrence_edge", "source_evidence_edge",
        "decision_or_two_vote_edge",
    ]

    def test_all_mapped_edge_kinds_exist_in_one_vocabulary(self):
        for kind in self.REPO_IDIOM_TARGETS:
            self.assertIn(kind, G.EDGE_TYPE_SET,
                          "mapped edge kind %r missing from EDGE_TYPES" % kind)

    def test_morpheme_occurrence_identity_exists_in_particle_ontology(self):
        path = os.path.join(_ROOT, "qamus", "schemas",
                            "particle-edge-ontology.schema.json")
        with open(path, encoding="utf-8") as handle:
            schema = json.load(handle)
        defs = schema.get("$defs") or {}
        self.assertIn("particle_morpheme_occurrence", defs,
                      "morpheme-occurrence identity node must stay in the ontology")
        self.assertIn("morpheme-occurrence",
                      (defs.get("node_type") or {}).get("enum") or [])

    def test_completion_state_schema_and_pilot_are_honest(self):
        with open(COMPLETION_SCHEMA_PATH, encoding="utf-8") as handle:
            schema = json.load(handle)
        states = ((schema.get("$defs") or {}).get("state_id") or {}).get("enum") or []
        self.assertEqual(len(states), 12, "exactly 12 entry completion states")
        pilot_path = os.path.join(_ROOT, "qamus", "reports",
                                  "entry-completion-states.pilot.json")
        with open(pilot_path, encoding="utf-8") as handle:
            pilot = json.load(handle)
        entries = {row["entry_id"]: row for row in pilot.get("entries") or []}
        for entry_id in (P007_ENTRY, VERB_ENTRY, NOUN_ENTRY):
            self.assertIn(entry_id, entries)
            row = entries[entry_id]
            self.assertIs(row.get("honest"), True)
            self.assertIn(row.get("current_state"), states)
            self.assertEqual([s["state"] for s in row.get("states") or []], states)
            # Honesty: no state may be claimed reached without evidence.
            for state in row["states"]:
                if state.get("reached"):
                    self.assertTrue(state.get("evidence"),
                                    "%s claims %s without evidence"
                                    % (entry_id, state["state"]))


if __name__ == "__main__":
    unittest.main()
