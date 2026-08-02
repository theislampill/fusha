#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P007_LI_NOUN_HOST_PILOT — deterministic derived-artifact generator.

Turns the committed primary pilot artifacts under
``qamus/examples/p007-li-pilot/`` (12 certified morpheme occurrences of the
jarr clitic li- on noun hosts, 78 entry-page appearances, 49 typed facts,
hash-chained certification store, two-vote bundles, projections, live
read-only captures) into the DERIVED repository machinery:

* ``locations.json``            — the 12-location table + 78 appearance links +
                                  candidate-lattice pre-selection + rejected
                                  false candidates with defeaters + exact
                                  exceptions.
* ``morpheme-occurrences.jsonl``— 12 ``qamus.particle_morpheme_occurrence.v1``
                                  identity nodes with base-letter spans.
* ``transclusion-edges.jsonl``  — per occurrence the explicit entry-transclusion
                                  closure: certified entry edge + candidate sense edge +
                                  clitic_host_edge + governor_edge +
                                  governed_expression_edge (+ the entry reverse
                                  occurrence edge), all ``qamus.graph_edge.v1``.
* ``entry-reverse-index.json``  — p007 entry -> 12 certified morpheme occurrences
                                  -> 78 appearances grouped by page class;
                                  dictionary sense remains candidate-pending.
* ``two-vote-artifacts.v1_1.jsonl`` + ``migration-provenance.json`` — the
                                  v1 two-vote bundles migrated to
                                  ``qamus.two_vote_artifact.v1.1`` (governed
                                  enums + registry keys); vote substance is
                                  untouched, every representational mapping is
                                  recorded in the provenance file.
* ``production-difference.json``— the NOT-DEPLOYED production-difference table
                                  (current public carve vs candidate carve,
                                  colour classes, verdict, affected pages,
                                  required change, rollback unit).

Stdlib only. Deterministic: same inputs -> byte-identical outputs.
Validated red-first by ``tools/validate_p007_pilot.py`` (wired into
``tools/check_regressions.py``).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PILOT_DIR = os.path.join(ROOT, "qamus", "examples", "p007-li-pilot")
UNIVERSE = os.path.join(ROOT, "qamus", "lattice", "example-ayah-universe.jsonl")

SCOPE = "P007_LI_NOUN_HOST_PILOT"
ENTRY_ID = "b10a1ee04666"
SOURCE_KEY = "p007"
SENSE_N = 2
SENSE_NODE = "sense:%s:%d" % (ENTRY_ID, SENSE_N)
ENTRY_NODE = "entry:%s" % ENTRY_ID
PRODUCER = {"id": "tools.build_p007_li_pilot", "version": "1"}
MIGRATION_DATE = "2026-07-29"

# Arabic combining marks (haraka/shadda/sukun/madda/dagger etc.) — used only to
# count base (rasm) letters for base_letter_span.
_COMBINING = set(
    "ًٌٍَُِّْٕٓٔ"
    "ٰٖٗ٘ۖۗۘۙۚۛۜ"
    "ۣ۟۠ۡۢۤۥۦ۪ۧۨ"
    "ۭ۫۬"
)


def base_letters(text):
    return [ch for ch in text if ch not in _COMBINING]


def nfc(text):
    return unicodedata.normalize("NFC", text)


def loc_key(quran_loc):
    return quran_loc.split(":", 1)[1]  # "S:A:W"


def loc_us(quran_loc):
    return loc_key(quran_loc).replace(":", "_")


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


def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ": "), indent=1)


def write_text(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def edge_id(edge_type, from_node, to_node):
    digest = hashlib.sha256(("%s|%s|%s" % (edge_type, from_node, to_node)).encode("utf-8")).hexdigest()
    return "edge:%s" % digest[:12]


def load_appearance_page_classes(appearance_ids):
    """Join appearance ids to their page class (entry_type n/v/p) via the
    committed example-ayah universe lattice."""
    wanted = set(appearance_ids)
    classes = {}
    with io.open(UNIVERSE, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            appearance_id = row.get("appearance_id")
            if appearance_id in wanted:
                classes[appearance_id] = row.get("entry_type")
    return classes


# ---------------------------------------------------------------------------
# derived artifact builders
# ---------------------------------------------------------------------------

def build_locations(family, lattice, projections):
    lattice_by_loc = {row["occurrence_id"]: row for row in lattice}
    proj_by_loc = {row["projection"]["occurrence_id"]: row for row in projections}
    occurrences = []
    for occ in family["occurrences"]:
        occurrence_id = occ["occurrence_id"]
        surface = occ["surface"]
        projection = proj_by_loc[occurrence_id]["projection"]
        clitic_segment = projection["segments"][0]
        lattice_row = lattice_by_loc[occurrence_id]
        occurrences.append({
            "matrix_id": occ["matrix_id"],
            "occurrence_id": occurrence_id,
            "surface": surface,
            "host_visible": occ["host_visible"],
            "morpheme": {
                "morpheme_occurrence_id": "mocc:%s:%s" % (SOURCE_KEY, loc_key(occurrence_id)),
                "component_surface": clitic_segment["surface"],
                "base_letter_span": {"start": 0, "end": len(base_letters(clitic_segment["surface"]))},
                "char_span": {"start": clitic_segment["char_start"], "end": clitic_segment["char_end"]},
            },
            "segments": [
                {
                    "surface": segment["surface"],
                    "role": segment["role"],
                    "colour_class": segment["colour_class"],
                    "char_start": segment["char_start"],
                    "char_end": segment["char_end"],
                }
                for segment in projection["segments"]
            ],
            "appearance_count": occ["appearance_count"],
            "page_appearances": occ["page_appearances"],
            "appearance_ids": occ["appearance_ids"],
            "lattice_preselection": {
                "segmentation_candidates": lattice_row["segmentation_candidates"],
                "entry_candidates": lattice_row["entry_candidates"],
                "function_candidates": lattice_row["function_candidates"],
                "resolution": lattice_row["resolution"],
            },
        })
    rejected = []
    for row in lattice:
        if row["resolution"] == "in_family":
            continue
        rejected.append({
            "occurrence_id": row["occurrence_id"],
            "surface": row["surface"],
            "defeater": row["rejection_reason"],
            "mcp_evidence_ref": "mcp-evidence.jsonl#analyze_word:%s" % loc_key(row["occurrence_id"]),
        })
    exceptions = [
        {
            "id": "nfc-shadda-vowel-order",
            "locs": ["quran:12:31:24", "quran:24:35:44", "quran:24:31:23"],
            "detail": "Repo lattice surfaces store vowel-before-shadda; the live rich whitelist stores shadda-before-vowel. NFC-equivalent — every span/parity comparison MUST NFC-normalize first.",
        },
        {
            "id": "fused-wasla-elision",
            "locs": ["quran:12:31:24"],
            "detail": "لِلَّهِ: the wasla alif of the Name is elided in the rasm after the clitic; the host segment starts inside the fused writing (char_start -1 sentinel in the projection); the clitic letter owns the first lam.",
        },
        {
            "id": "diptote-jarr-sign-fatha",
            "locs": ["quran:2:34:5"],
            "detail": "لِءَادَمَ: jarr sign is fatha because the name is ممنوع من الصرف; reason key jarr-clitic-li-majrur-fatha-diptote.",
        },
        {
            "id": "same-surface-distinct-artifacts",
            "locs": ["quran:24:35:44", "quran:2:187:63"],
            "detail": "Identical surface لِلنَّاسِ at two occurrences stays two distinct canonical artifacts (particle-projection-contract §2.3); live even carves the two differently — the exact per-surface fork the contract kills.",
        },
        {
            "id": "fronted-predicate-governor-representation",
            "locs": ["quran:9:120:3", "quran:4:11:5"],
            "detail": "For fronted-predicate rows the case governor is the preposition itself (relation preposition-governs-majrur); governor null with a case claim is validator-invalid. Both reviewers re-voted and endorsed the representation.",
        },
    ]
    return {
        "schema": "qamus.p007_li_pilot.locations.v1",
        "scope": SCOPE,
        "entry_id": ENTRY_ID,
        "source_key": SOURCE_KEY,
        "sense_n": SENSE_N,
        "not_deployed": True,
        "population": {
            "occurrences": len(occurrences),
            "appearances": sum(o["appearance_count"] for o in occurrences),
            "page_class_appearances": family["counts"]["family_page_class_appearances"],
            "false_candidates_examined": family["counts"]["false_candidates_examined"],
        },
        "occurrences": occurrences,
        "rejected_false_candidates": rejected,
        "exceptions": exceptions,
    }


def build_morpheme_occurrences(locations):
    rows = []
    for occ in locations["occurrences"]:
        morpheme = occ["morpheme"]
        rows.append({
            "schema": "qamus.particle_morpheme_occurrence.v1",
            "morpheme_occurrence_id": morpheme["morpheme_occurrence_id"],
            "host_occurrence_id": occ["occurrence_id"],
            "base_letter_span": morpheme["base_letter_span"],
            "component_surface": morpheme["component_surface"],
            "producer": PRODUCER,
        })
    return rows


def build_edges(locations, artifacts_by_loc):
    """Entry-transclusion closure: per certified morpheme occurrence the
    explicit entry + sense instantiation edges (owner steer: a generic
    'preposition' class without the entry/sense edge does NOT satisfy
    transclusion), attachment geometry, governor and governed expression."""
    edges = []
    for occ in locations["occurrences"]:
        occurrence_id = occ["occurrence_id"]
        surface = occ["surface"]
        key = loc_key(occurrence_id)
        mocc = "mocc:%s:%s" % (SOURCE_KEY, key)
        component = occ["morpheme"]["component_surface"]
        seg_fact = "fact:p00slice:%s:seg" % key.replace(":", "_")
        func_fact = "fact:p00slice:%s:func:v2" % key.replace(":", "_")
        gov_fact = "fact:p00slice:%s:gov:v2" % key.replace(":", "_")
        case_fact = "fact:p00slice:%s:case:v2" % key.replace(":", "_")
        bundle = "qamus/examples/p007-li-pilot/certification/events.jsonl#%s"
        two_vote_ref = artifacts_by_loc[occurrence_id]["artifact_id"]
        occurrence_node = "occurrence:%s" % occurrence_id
        governor = artifacts_by_loc[occurrence_id]["votes"][0]["conclusion"]["governor"]
        governor_loc = governor.get("loc")
        if governor_loc and governor_loc != occurrence_id:
            governor_node = "occurrence:%s" % governor_loc
            governor_node_type = "occurrence"
        else:
            # fronted-predicate rows: the case governor is the preposition itself
            governor_node = mocc
            governor_node_type = "morpheme-occurrence"

        def make(edge_type, from_node, from_type, to_node, to_type, fact_id,
                 evidence_mode, guards, irab=False, with_component=False,
                 status="certified"):
            details = {
                "occurrence_id": occurrence_id,
                "surface": surface,
                "evidence_mode": evidence_mode,
                "fact_id": fact_id,
            }
            if status == "certified":
                details["evidence_bundle_ref"] = bundle % fact_id
            if with_component:
                details["component_surface"] = component
            if irab:
                details["two_vote_artifact_ref"] = two_vote_ref
            return {
                "schema": "qamus.graph_edge.v1",
                "edge_id": edge_id(edge_type, from_node, to_node),
                "edge_type": edge_type,
                "from_node_id": from_node,
                "from_node_type": from_type,
                "to_node_id": to_node,
                "to_node_type": to_type,
                "status": status,
                "guards": guards,
                "evidence": [{"address": occurrence_id, "method": "explicit_occurrence_address"}],
                "details": details,
                "producer": PRODUCER,
            }

        # morpheme_occurrence_instantiates_particle_entry (ontology kind:
        # particle_entry_certified_edge, morpheme-occurrence -> entry)
        edges.append(make(
            "particle_entry_certified_edge", mocc, "morpheme-occurrence",
            ENTRY_NODE, "entry", seg_fact, "direct_source_attestation",
            ["entry_transclusion_instantiates", "surface_exact", "occurrence_address_exact"],
            with_component=True))
        # The function fact proves this occurrence's jarr function, not its
        # dictionary sense identity.  Preserve sense 2 as a candidate until a
        # separate certified entry/sense fact exists; never launder the
        # function fact into a certified sense edge.
        edges.append(make(
            "particle_sense_candidate_edge", mocc, "morpheme-occurrence",
            SENSE_NODE, "sense", func_fact, "unresolved",
            ["candidate_sense_from_function", "requires_separate_sense_certification"],
            with_component=True, status="candidate"))
        # attachment geometry
        edges.append(make(
            "clitic_host_edge", mocc, "morpheme-occurrence",
            occurrence_node, "occurrence", seg_fact, "direct_source_attestation",
            ["attachment_geometry_only", "surface_exact"], with_component=True))
        # governor (iʿrāb-bearing -> two-vote artifact required)
        edges.append(make(
            "governor_edge", mocc, "morpheme-occurrence",
            governor_node, governor_node_type, gov_fact, "direct_source_attestation",
            ["two_vote_verified_agreement"], irab=True))
        # governed expression (iʿrāb-bearing)
        edges.append(make(
            "governed_expression_edge", mocc, "morpheme-occurrence",
            occurrence_node, "occurrence", case_fact, "direct_source_attestation",
            ["two_vote_verified_agreement"], irab=True))
        # reverse plumbing: entry -> occurrence
        edges.append(make(
            "particle_entry_reverse_occurrence_edge", ENTRY_NODE, "entry",
            occurrence_node, "occurrence", seg_fact,
            "deterministic_derivation_from_certified_facts",
            ["reverse_index_closure"]))
    return edges


def build_reverse_index(locations, page_classes):
    occurrences = []
    totals = {"n": 0, "v": 0, "p": 0}
    for occ in locations["occurrences"]:
        by_class = {"n": [], "v": [], "p": []}
        for appearance_id in occ["appearance_ids"]:
            page_class = page_classes.get(appearance_id)
            if page_class not in by_class:
                raise SystemExit(
                    "appearance %s has unknown page class %r (universe join failed)"
                    % (appearance_id, page_class))
            by_class[page_class].append(appearance_id)
        for page_class, ids in by_class.items():
            totals[page_class] += len(ids)
        occurrences.append({
            "occurrence_id": occ["occurrence_id"],
            "morpheme_occurrence_id": occ["morpheme"]["morpheme_occurrence_id"],
            "surface": occ["surface"],
            "appearance_count": occ["appearance_count"],
            "appearances_by_page_class": by_class,
        })
    return {
        "schema": "qamus.p007_li_pilot.entry_reverse_index.v1",
        "scope": SCOPE,
        "entry_id": ENTRY_ID,
        "source_key": SOURCE_KEY,
        "sense_n_candidate": SENSE_N,
        "sense_state": "candidate_pending",
        "sense_blocker": "no separately certified occurrence-to-sense fact",
        "occurrences": occurrences,
        "totals": {
            "occurrences": len(occurrences),
            "appearances": sum(o["appearance_count"] for o in occurrences),
            "by_page_class": totals,
        },
    }


# v1 -> v1.1 representational mappings (substance untouched; every mapping is
# recorded in migration-provenance.json).
SIGN_MAP = {"fatha-mamnu-min-sarf": "fatha"}
FUNCTION_KEY = "harf-jarr-lam-fused"


def migrate_two_vote(v1_rows):
    migrated = []
    mappings = []
    for row in v1_rows:
        new_row = json.loads(json.dumps(row, ensure_ascii=False))
        new_row["schema"] = "qamus.two_vote_artifact.v1.1"
        for vote in new_row["votes"]:
            vote["lexical_target"] = "clitic_entry"
            conclusion = vote["conclusion"]
            conclusion["function"] = FUNCTION_KEY
            conclusion["attachment_key"] = None
            case = conclusion["case_or_mood"]
            original_sign = case["sign"]
            if original_sign in SIGN_MAP:
                case["sign"] = SIGN_MAP[original_sign]
                mappings.append({
                    "artifact_id": row["artifact_id"],
                    "vote_id": vote["vote_id"],
                    "field": "conclusion.case_or_mood.sign",
                    "from": original_sign,
                    "to": SIGN_MAP[original_sign],
                    "reason": "v1.1 governed sign enum; the diptote rationale is carried by reason_key jarr-clitic-li-majrur-fatha-diptote and the grammatical_reason prose",
                })
            case["mood_basis"] = "governed"
        migrated.append(new_row)
    return migrated, mappings


def build_migration_provenance(mappings):
    return {
        "schema": "qamus.p007_li_pilot.two_vote_migration.v1",
        "scope": SCOPE,
        "migrated_on": MIGRATION_DATE,
        "migrated_by": PRODUCER,
        "from_file": "two-vote-artifacts.v1.jsonl",
        "to_file": "two-vote-artifacts.v1_1.jsonl",
        "from_schema": "qamus.two_vote_artifact.v1",
        "to_schema": "qamus.two_vote_artifact.v1.1",
        "substance_untouched": True,
        "certification_consumed": "two-vote-artifacts.v1.jsonl (the hash-chained certification store consumed the v1 bundles; the v1.1 file is the governed-vocabulary migration of the same votes)",
        "field_decisions": [
            {
                "field": "votes[*].lexical_target",
                "value": "clitic_entry",
                "reason": "every vote's lexical_identity addresses the clitic's own dictionary entry b10a1ee04666 (لِـ), never the whole fused token",
            },
            {
                "field": "votes[*].conclusion.function",
                "value": FUNCTION_KEY,
                "reason": "registered function key for the token-internal preposition lam fused with its majrur; matches both votes' contextual_function prose 'jarr-clitic-li-preposition-on-noun-host' (kept verbatim as uncompared elaboration)",
            },
            {
                "field": "votes[*].conclusion.attachment_key",
                "value": None,
                "reason": "no registered attachment key exactly matches every row's attachment claim (muta'alliq-to-verb / muta'alliq-to-exclamative / khabar-kana-muqaddam / khabar-muqaddam); rather than force a near-miss key, attachment stays prose-only (uncompared in v1.1) — the v1 file retains the compared-prose agreement",
            },
            {
                "field": "votes[*].conclusion.case_or_mood.mood_basis",
                "value": "governed",
                "reason": "every case claim is jarr assigned by the preposition (an operator) — mood_basis governed; the governor field was already non-null on all 12 rows",
            },
        ],
        "value_mappings": mappings,
        "registry_keys_added": [
            "jarr-clitic-li-majrur-visible-kasra",
            "jarr-clitic-li-majrur-fatha-diptote",
        ],
    }


VERDICTS = {
    "quran:2:187:63": ("wrong", "live folds the assimilated article into the host (لِ | لنَّاسِ); the candidate carve separates clitic | article | host"),
    "quran:4:11:5": ("wrong", "live folds the assimilated article into the host (لِ | لذَّكَرِ); the candidate carve separates clitic | article | host"),
    "quran:5:3:9": ("incomplete", "live clitic and host role labels are EMPTY; colour class qg-preposition is legacy-coarse"),
    "quran:9:120:3": ("incomplete", "live clitic and host role labels are EMPTY; colour class qg-preposition is legacy-coarse"),
}


def build_production_difference(locations, parity):
    deltas_by_loc = {"quran:%s" % row["loc"]: row for row in parity["live_deltas"]}
    rows = []
    for occ in locations["occurrences"]:
        occurrence_id = occ["occurrence_id"]
        delta = deltas_by_loc[occurrence_id]
        verdict, verdict_reason = VERDICTS.get(
            occurrence_id,
            ("legacy-coarse", "carve agrees (NFC); live colour classes / role labels predate the particle-projection contract"),
        )
        rows.append({
            "occurrence_id": occurrence_id,
            "surface": occ["surface"],
            "current_public_carve": [segment[0] for segment in delta["live_segments"]],
            "candidate_carve": [segment[0] for segment in delta["projection_segments"]],
            "current_colour_classes": [segment[2] for segment in delta["live_segments"]],
            "candidate_colour_classes": [segment[2] for segment in delta["projection_segments"]],
            "current_role_labels": [segment[1] for segment in delta["live_segments"]],
            "candidate_role_labels": [segment[1] for segment in delta["projection_segments"]],
            "boundary_match_nfc": delta.get("boundary_match_nfc", delta["boundary_match"]),
            "verdict": verdict,
            "verdict_reason": verdict_reason,
            "deltas": delta["deltas"],
            "affected_pages": sorted({appearance_id.split(":", 1)[0] for appearance_id in occ["appearance_ids"]}),
            "affected_appearance_count": occ["appearance_count"],
            "required_change": "no live change authorized; resolve the candidate sense identity and governor-relation label before any public application for %s" % occurrence_id,
            "projection_state": "candidate_pending",
            "unresolved_dependencies": [
                "occurrence_to_sense_certification",
                "governor_relation_governed_key",
            ],
            "rollback_unit": "live rich-whitelist row for %s (single-row revert)" % occurrence_id,
            "deployed": False,
        })
    return {
        "schema": "qamus.p007_li_pilot.production_difference.v1",
        "scope": SCOPE,
        "not_deployed": True,
        "summary": {
            "rows": len(rows),
            "carve_forks": sum(1 for row in rows if row["verdict"] == "wrong"),
            "colour_class_deltas": sum(
                1 for row in rows
                if row["current_colour_classes"] != row["candidate_colour_classes"]
                or any("colour class" in delta for delta in row["deltas"])),
        },
        "rows": rows,
    }


def generate(pilot_dir=PILOT_DIR):
    family = read_json(os.path.join(pilot_dir, "family-selection.json"))
    lattice = read_jsonl(os.path.join(pilot_dir, "candidate-lattice.jsonl"))
    projections = read_jsonl(os.path.join(pilot_dir, "projections.jsonl"))
    parity = read_json(os.path.join(pilot_dir, "parity-report.json"))
    v1_rows = read_jsonl(os.path.join(pilot_dir, "two-vote-artifacts.v1.jsonl"))
    artifacts_by_loc = {row["occurrence"]["quran_loc"]: row for row in v1_rows}

    locations = build_locations(family, lattice, projections)
    write_text(os.path.join(pilot_dir, "locations.json"), dump_json(locations))

    morphemes = build_morpheme_occurrences(locations)
    write_jsonl(os.path.join(pilot_dir, "morpheme-occurrences.jsonl"), morphemes)

    edges = build_edges(locations, artifacts_by_loc)
    write_jsonl(os.path.join(pilot_dir, "transclusion-edges.jsonl"), edges)

    all_appearances = [a for occ in locations["occurrences"] for a in occ["appearance_ids"]]
    page_classes = load_appearance_page_classes(all_appearances)
    reverse_index = build_reverse_index(locations, page_classes)
    write_text(os.path.join(pilot_dir, "entry-reverse-index.json"), dump_json(reverse_index))

    migrated, mappings = migrate_two_vote(v1_rows)
    write_jsonl(os.path.join(pilot_dir, "two-vote-artifacts.v1_1.jsonl"), migrated)
    provenance = build_migration_provenance(mappings)
    write_text(os.path.join(pilot_dir, "migration-provenance.json"), dump_json(provenance))

    production_difference = build_production_difference(locations, parity)
    write_text(os.path.join(pilot_dir, "production-difference.json"), dump_json(production_difference))

    return {
        "locations": len(locations["occurrences"]),
        "appearances": locations["population"]["appearances"],
        "morpheme_occurrences": len(morphemes),
        "edges": len(edges),
        "two_vote_v11": len(migrated),
        "production_rows": len(production_difference["rows"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot-dir", default=PILOT_DIR)
    args = parser.parse_args(argv)
    stats = generate(args.pilot_dir)
    print("P007_LI_NOUN_HOST_PILOT derived artifacts written:")
    for key, value in sorted(stats.items()):
        print("  %s: %d" % (key, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
