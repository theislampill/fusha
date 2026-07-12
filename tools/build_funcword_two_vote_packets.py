#!/usr/bin/env python3
"""T11 — function-word two-vote packet builder (class-2 function lane).

Candidate-generation only: consumes the pre-passed v2 function-word queue
(``funcword-queue.v2.jsonl``) plus the canonical loc-surface index and the
canonical entries, and emits self-contained, sha-stamped two-vote *evidence*
packets for the function lane.  Zero canonical mutation, no votes, no
conclusions.

Function-word packets carry function-specific evidence (token identity,
particle class after the homograph pre-pass, taxonomy function candidates,
governor/scope evidence, and covering-entry snapshots) rather than overloading
the content-root fields used by the decidable competing-analysis lane.

Determinism: stdlib only, no wall-clock fields, byte-identical double build
(canonicalisation helpers are *imported* — never forked — from
``tools.build_two_vote_packets``).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import (never fork) the shared canonicalisation + hashing helpers so the
# byte layout matches every other two-vote artifact in the repo.
from tools.build_two_vote_packets import (  # noqa: E402
    canonical_bytes,
    canonical_rows_sha256,
    input_pin,
    loc_key,
    logical_path,
    render_jsonl,
    sha256_file,
    stable_sha256,
)

QUEUE = ROOT / "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.v2.jsonl"
LOC_SURFACE = ROOT / "qamus/indexes/quran-loc-surface/index.jsonl"
ENTRIES = ROOT / "qamus/data/current/entries.jsonl"
PREPASS_RULES = ROOT / "nahw/rules/funcword-homograph-prepass-rules.json"
GATE_SSOT = ROOT / "nahw/evals/grammar-decision-gates.json"

OUT_PACKETS = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-funcword.jsonl"
)
OUT_MANIFEST = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-funcword.manifest.json"
)

# Disjoint sibling lanes (used only to prove the function lane does not overlap).
DECIDABLE_PACKETS = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-decidable.jsonl"
)
REBIND_QUEUE = ROOT / (
    "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.jsonl"
)

PACKET_SCHEMA = "qamus.t11_funcword_two_vote_packet.v1"
EXPECTED_COUNT = 1043
CONTEXT_RADIUS = 4  # +/- 4 vocalized words

# The ten committed taxonomy categories a reviewer may land on.
TAXONOMY_CATEGORIES = (
    "preposition",
    "conjunction",
    "negation",
    "interrogative",
    "relative",
    "conditional",
    "emphasis",
    "lam_family",
    "ma_family",
    "other_particle",
)

# Deterministic map: queue particle_class -> (primary_taxonomy_category,
# [ (taxonomy_category, reading, note) ... ]).  The candidate readings encode
# the genuine multi-function ambiguity of each closed class.  For the three
# homograph-pre-passed classes the candidate taxonomy set is asserted equal to
# the pre-pass rule's calibration_categories (self-test, below).
CLASS_MAP: dict[str, dict[str, Any]] = {
    "preposition": {
        "primary": "preposition",
        "candidates": [
            ("preposition", "harf jarr",
             "governs the following noun in the genitive (jarr)"),
        ],
    },
    "conjunction": {
        "primary": "conjunction",
        "candidates": [
            ("conjunction", "harf atf",
             "coordinates the following term with a preceding one"),
        ],
    },
    "negation": {
        "primary": "negation",
        "candidates": [
            ("negation", "harf nafy",
             "negates the following predicate or clause"),
        ],
    },
    "interrogative": {
        "primary": "interrogative",
        "candidates": [
            ("interrogative", "adat istifham",
             "introduces a question over the following clause"),
        ],
    },
    "relative": {
        "primary": "relative",
        "candidates": [
            ("relative", "ism mawsul",
             "introduces a relative clause qualifying an antecedent"),
        ],
    },
    "conditional": {
        "primary": "conditional",
        "candidates": [
            ("conditional", "adat shart",
             "introduces the protasis; governs jazm on the conditioned verbs"),
        ],
    },
    "emphasis": {
        "primary": "emphasis",
        "candidates": [
            ("emphasis", "harf tawkid (inna/anna family)",
             "emphasises the following nominal sentence"),
        ],
    },
    "lam-family": {
        "primary": "lam_family",
        "candidates": [
            ("lam_family", "lam al-jarr",
             "genitive lam governing the following noun"),
            ("lam_family", "lam al-ta'lil",
             "causal lam before a subjunctive verb"),
            ("lam_family", "lam al-ibtida' / al-muzahlaqa",
             "emphatic lam on the predicate"),
            ("lam_family", "lam al-amr",
             "imperative lam governing jazm"),
        ],
    },
    "ma-family": {
        "primary": "ma_family",
        "candidates": [
            ("relative", "ma mawsula", "'that which' — relative"),
            ("interrogative", "ma istifhamiyya", "'what?' — interrogative"),
            ("negation", "ma nafiya", "negating ma"),
            ("conditional", "ma shartiyya", "conditional 'whatever'"),
            ("ma_family", "ma masdariyya / za'ida",
             "masdaric or redundant ma"),
        ],
    },
    "man-family": {
        "primary": "other_particle",
        "candidates": [
            ("conditional", "man shartiyya", "conditional 'whoever'"),
            ("interrogative", "man istifhamiyya", "'who?' — interrogative"),
            ("relative", "man mawsula", "'the one who' — relative"),
        ],
    },
    "in-light-family": {
        "primary": "other_particle",
        "candidates": [
            ("conditional", "in shartiyya", "conditional 'if'"),
            ("negation", "in nafiya", "negating in"),
        ],
    },
    "an-masdariyya": {
        "primary": "other_particle",
        "candidates": [
            ("other_particle", "an masdariyya",
             "subordinating an governing a subjunctive verb"),
        ],
    },
    "supplemental_function_target": {
        "primary": "other_particle",
        "candidates": [
            ("preposition", "lam al-jarr",
             "genitive lam (e.g. the fused lillah divine-name token)"),
            ("other_particle", "closed-class function target",
             "supplemental closed-class function token"),
        ],
    },
    "other": {
        "primary": "other_particle",
        "candidates": [
            ("other_particle", "function particle",
             "residual closed-class function token"),
        ],
    },
}

# prepass_rule -> calibration taxonomy categories (loaded from the SSOT at
# runtime; this literal is only the red-first self-test oracle).
_EXPECTED_PREPASS_CATS = {
    "man_fatha_not_min": {"conditional", "interrogative", "relative"},
    "in_light_not_inna": {"conditional", "negation"},
    "an_light_not_anna": {"other_particle"},
}


def load_jsonl_plain(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_loc_surface(path: Path) -> dict[str, str]:
    surfaces: dict[str, str] = {}
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            surfaces[row["loc"]] = row["surface"]
    return surfaces


def load_entries(path: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            eid = row.get("id") or row.get("entry_id")
            if eid:
                entries[eid] = row
    return entries


def load_prepass_categories(path: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(io.open(path, encoding="utf-8").read())
    out: dict[str, dict[str, Any]] = {}
    for rule in doc.get("rules", []):
        out[rule["rule_id"]] = {
            "rule_id": rule["rule_id"],
            "from_particle_class": rule.get("from_particle_class"),
            "after_particle_class": rule.get("after_particle_class"),
            "reason": rule.get("reason"),
            "calibration_categories": list(rule.get("calibration_categories") or []),
        }
    return out


def first_n_words(text: str, n: int = 4) -> str:
    return " ".join(str(text or "").split()[:n])


def function_candidates(row: dict[str, Any], prepass: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cls = row.get("particle_class_after") or row.get("particle_class")
    spec = CLASS_MAP.get(cls)
    if spec is None:
        raise ValueError(f"STOP: unmapped particle_class {cls!r} at "
                         f"{row['target']['canonical_location']}")
    cands = [
        {"taxonomy_category": cat, "reading": reading, "note": note}
        for (cat, reading, note) in spec["candidates"]
    ]
    # For pre-passed rows, the candidate taxonomy set MUST equal the rule's
    # calibration_categories — otherwise the pre-pass provenance is a lie.
    rule_id = row.get("prepass_rule")
    if rule_id:
        rule = prepass.get(rule_id)
        if rule is None:
            raise ValueError(f"STOP: unknown prepass_rule {rule_id!r}")
        derived = {c["taxonomy_category"] for c in cands}
        if derived != set(rule["calibration_categories"]):
            raise ValueError(
                f"STOP: candidate taxonomy set {sorted(derived)} != calibration "
                f"{sorted(rule['calibration_categories'])} for rule {rule_id}"
            )
    return cands


def ayah_context(loc: str, surfaces: dict[str, str]) -> list[dict[str, Any]]:
    surah, ayah, word = loc_key(loc)
    window: list[dict[str, Any]] = []
    for w in range(max(1, word - CONTEXT_RADIUS), word + CONTEXT_RADIUS + 1):
        wl = f"{surah}:{ayah}:{w}"
        if wl not in surfaces:
            continue
        window.append({
            "loc": wl,
            "surface": surfaces[wl],
            "is_target": wl == loc,
            "source_address": f"{logical_path(LOC_SURFACE)}#loc={wl}",
        })
    return window


def governor_scope(loc: str, surfaces: dict[str, str]) -> dict[str, Any]:
    surah, ayah, word = loc_key(loc)

    def tok(w: int) -> dict[str, Any] | None:
        wl = f"{surah}:{ayah}:{w}"
        if wl not in surfaces:
            return None
        return {"loc": wl, "surface": surfaces[wl],
                "source_address": f"{logical_path(LOC_SURFACE)}#loc={wl}"}

    prev = tok(word - 1)
    governs = [t for t in (tok(word + 1), tok(word + 2)) if t is not None]
    return {
        "attaches_to_prev": prev,
        "governs_or_scopes_next": governs,
        "note": (
            "For a preposition/lam-jarr the immediately-following noun is the "
            "genitive object; for negation/emphasis/conditional the scope is the "
            "following clause. Positions are candidate evidence, not a conclusion."
        ),
    }


def covering_entry_evidence(row: dict[str, Any], entries: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], str]:
    cov = row.get("coverage") or {}
    eid = cov.get("entry_id")
    if not eid or eid not in entries:
        return (
            {
                "covering_entry": None,
                "authoring_needed": bool(cov.get("authoring_needed")),
                "note": "no covering function entry — needs_entry candidate",
            },
            "needs_entry_candidate",
        )
    entry = entries[eid]
    refs: list[str] = []
    for usage in entry.get("usage") or []:
        for ex in usage.get("examples") or []:
            ref = ex.get("ref")
            if ref and ref not in refs:
                refs.append(ref)
    senses_snapshot = [
        {"n": s.get("n"), "gloss_first_4_words": first_n_words(s.get("gloss"))}
        for s in (entry.get("senses") or [])
    ]
    evidence = {
        "entry_id": eid,
        "entry_address": cov.get("covering_entry_address"),
        "section": entry.get("section"),
        "headword": entry.get("headword"),
        "translit": entry.get("translit"),
        "category": entry.get("category"),
        "total_uses": entry.get("total_uses"),
        "refs": refs[:8],
        "senses_snapshot": senses_snapshot,
        "definition_first_4_words": first_n_words(entry.get("definition")),
    }
    return evidence, "unique"


def response_schema(
    packet_id: str,
    candidate_cats: list[str],
    evidence_hashes: dict[str, str],
) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "decision",
            "confidence",
            "gate",
            "abstention_or_blocker",
            "evidence_hashes",
            "packet_id",
        ],
        "properties": {
            "decision": {
                "enum": [
                    "function_confirmed",
                    "reclassify",
                    "needs_entry",
                    "abstention",
                ]
            },
            "taxonomy_category": {"type": ["string", "null"], "enum": [None, *candidate_cats]},
            "governor_note": {"type": ["string", "null"]},
            "corrected_category": {"type": ["string", "null"], "enum": [None, *TAXONOMY_CATEGORIES]},
            "rationale": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "source_address": {"type": "string", "minLength": 1},
                    "exact_reason": {"type": "string", "minLength": 1},
                },
                "required": ["source_address", "exact_reason"],
            },
            "needs_entry_reason": {"type": ["string", "null"]},
            "abstention_or_blocker": {"type": ["string", "null"]},
            "confidence": {"enum": ["high", "medium", "low", "abstain"]},
            "gate": {"const": "two_vote_required"},
            "evidence_hashes": {"const": evidence_hashes},
            "packet_id": {"const": packet_id},
        },
        "allOf": [
            {
                "if": {"properties": {"decision": {"const": "function_confirmed"}}},
                "then": {
                    "properties": {
                        "taxonomy_category": {"enum": candidate_cats},
                        "governor_note": {"type": "string", "minLength": 1},
                    },
                    "required": ["taxonomy_category", "governor_note"],
                },
            },
            {
                "if": {"properties": {"decision": {"const": "reclassify"}}},
                "then": {
                    "properties": {
                        "corrected_category": {"enum": list(TAXONOMY_CATEGORIES)},
                    },
                    "required": ["corrected_category", "rationale"],
                },
            },
            {
                "if": {"properties": {"decision": {"const": "needs_entry"}}},
                "then": {"required": ["needs_entry_reason"]},
            },
            {
                "if": {"properties": {"decision": {"const": "abstention"}}},
                "then": {
                    "properties": {"abstention_or_blocker": {"type": "string", "minLength": 1}},
                    "required": ["abstention_or_blocker"],
                },
            },
        ],
    }


def build_packet(
    rank: int,
    row: dict[str, Any],
    surfaces: dict[str, str],
    entries: dict[str, dict[str, Any]],
    prepass: dict[str, dict[str, Any]],
    gate_ssot_sha: str,
) -> dict[str, Any]:
    loc = row["target"]["canonical_location"]
    surah, ayah, _w = loc_key(loc)

    token_identity = {
        "canonical_location": loc,
        "surface": surfaces[loc],  # fully-vocalized, from the loc-surface index
        "norm_strict": row["target"].get("norm_strict"),
        "source_address": f"{logical_path(LOC_SURFACE)}#loc={loc}",
    }

    cls_after = row.get("particle_class_after") or row.get("particle_class")
    particle_class = {
        "class": cls_after,
        "class_before_prepass": row.get("particle_class_before"),
        "class_after_prepass": cls_after,
        "primary_taxonomy_category": CLASS_MAP[cls_after]["primary"],
        "function_head": (row.get("function_evidence") or {}).get("function_head"),
        "function_evidence_source": (row.get("function_evidence") or {}).get("source"),
    }
    rule_id = row.get("prepass_rule")
    if rule_id:
        rule = prepass[rule_id]
        particle_class["prepass_rule"] = rule_id
        particle_class["prepass_provenance"] = {
            "rule_id": rule_id,
            "reason": rule["reason"],
            "calibration_categories": rule["calibration_categories"],
            "source_address": f"{logical_path(PREPASS_RULES)}#rule_id={rule_id}",
        }
    else:
        particle_class["prepass_rule"] = None
        particle_class["prepass_provenance"] = None

    candidates = function_candidates(row, prepass)
    candidate_cats: list[str] = []
    for c in candidates:
        if c["taxonomy_category"] not in candidate_cats:
            candidate_cats.append(c["taxonomy_category"])

    context = ayah_context(loc, surfaces)
    governor = governor_scope(loc, surfaces)
    covering, mapping_status = covering_entry_evidence(row, entries)

    gate = {
        "tier": "two_vote_required",
        "rank": 1,
        "requires": "two independent checks that AGREE on BOTH the conclusion AND the reasoning",
        "triggers": ["referent_sensitive_gloss", "advanced_nahw"],
        "source_address": f"{logical_path(GATE_SSOT)}#gates/two_vote_required",
    }

    evidence_hashes = {
        "queue_row_sha256": stable_sha256(row),
        "token_identity_sha256": stable_sha256(token_identity),
        "particle_class_sha256": stable_sha256(particle_class),
        "function_candidates_sha256": stable_sha256(candidates),
        "ayah_context_sha256": stable_sha256(context),
        "governor_scope_sha256": stable_sha256(governor),
        "covering_entry_sha256": stable_sha256(covering),
        "gate_ssot_sha256": gate_ssot_sha,
    }

    packet_id = f"t11-class2-funcword:{rank:03d}:{loc}"

    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "packet_id": packet_id,
        "selection_rank": rank,
        "canonical_location": loc,
        "ayah": f"{surah}:{ayah}",
        "decision_kind": (
            "which_function_reading_governs_this_particle_token"
            "_OR_reclassify_OR_needs_entry_OR_abstention"
        ),
        "packet_status": "evidence_packet_only_no_votes_no_conclusions",
        "candidate_only": True,
        "no_live_payload": True,
        "mapping_status": mapping_status,
        "resolution_lane": row.get("resolution_lane"),
        "review_state": "pending",
        "token_identity": token_identity,
        "particle_class": particle_class,
        "function_candidates": candidates,
        "alternatives": candidate_cats,
        "ayah_context_window": context,
        "governor_scope_evidence": governor,
        "covering_entry_evidence": covering,
        "gate": gate,
        "abstention_or_blocker": None,
        "evidence_hashes": evidence_hashes,
        "required_response_schema": response_schema(packet_id, candidate_cats, evidence_hashes),
    }

    # Divine-name boundary rows: surface the lam-jarr + divine-name ruling.
    if row.get("boundary_route"):
        packet["boundary_route"] = row["boundary_route"]
        packet["boundary_note"] = row.get("boundary_note")
        packet["boundary_ruling"] = (
            "O2 boundary: the fused lam-jarr + divine name is kept as a "
            "divine-name entry token in the function pilot; reviewers see the "
            "lam-jarr + divine_name_entry route explicitly."
        )

    packet["packet_sha256"] = stable_sha256(
        {k: v for k, v in packet.items() if k != "packet_sha256"}
    )
    return packet


def validate_packet(packet: dict[str, Any]) -> None:
    for key in (
        "schema", "packet_id", "canonical_location", "token_identity",
        "particle_class", "function_candidates", "gate", "evidence_hashes",
        "required_response_schema", "packet_sha256",
    ):
        if key not in packet:
            raise ValueError(f"packet missing {key}: {packet.get('packet_id')}")
    if not packet["function_candidates"]:
        raise ValueError(f"empty function_candidates: {packet['packet_id']}")
    if packet["gate"]["tier"] != "two_vote_required":
        raise ValueError(f"wrong gate tier: {packet['packet_id']}")
    # echo-hash integrity
    const_hashes = packet["required_response_schema"]["properties"]["evidence_hashes"]["const"]
    if const_hashes != packet["evidence_hashes"]:
        raise ValueError(f"evidence_hashes echo mismatch: {packet['packet_id']}")
    if packet["required_response_schema"]["properties"]["packet_id"]["const"] != packet["packet_id"]:
        raise ValueError(f"packet_id echo mismatch: {packet['packet_id']}")
    supplied = packet["packet_sha256"]
    recomputed = stable_sha256({k: v for k, v in packet.items() if k != "packet_sha256"})
    if supplied != recomputed:
        raise ValueError(f"packet_sha256 mismatch: {packet['packet_id']}")


def build_all() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queue = load_jsonl_plain(QUEUE)
    surfaces = load_loc_surface(LOC_SURFACE)
    entries = load_entries(ENTRIES)
    prepass = load_prepass_categories(PREPASS_RULES)
    gate_ssot_sha = sha256_file(GATE_SSOT)

    ordered = sorted(queue, key=lambda r: loc_key(r["target"]["canonical_location"]))
    packets: list[dict[str, Any]] = []
    for rank, row in enumerate(ordered, 1):
        packet = build_packet(rank, row, surfaces, entries, prepass, gate_ssot_sha)
        validate_packet(packet)
        packets.append(packet)

    if len(packets) != EXPECTED_COUNT:
        raise ValueError(f"STOP: expected {EXPECTED_COUNT} packets, built {len(packets)}")

    manifest = build_manifest(queue, packets)
    return packets, manifest


def _lane_locations(path: Path, target_nested: bool) -> set[str]:
    locs: set[str] = set()
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if target_nested:
                loc = (row.get("target") or {}).get("canonical_location")
            else:
                loc = row.get("canonical_location")
            if loc:
                locs.add(loc)
    return locs


def build_manifest(queue: list[dict[str, Any]], packets: list[dict[str, Any]]) -> dict[str, Any]:
    fw_locs = {p["canonical_location"] for p in packets}
    dec_locs = _lane_locations(DECIDABLE_PACKETS, target_nested=False)
    rebind_locs = _lane_locations(REBIND_QUEUE, target_nested=True)

    boundary = [p for p in packets if p.get("boundary_route")]

    manifest = {
        "schema": "qamus.t11_funcword_packets_manifest.v1",
        "generator": "tools/build_funcword_two_vote_packets.py",
        "candidate_only": True,
        "lane": "class2_function_word_two_vote",
        "decision_object": (
            "which_function_reading_governs_the_particle_token"
            "_OR_reclassify_OR_needs_entry_OR_abstention"
        ),
        "determinism": {
            "double_build_required": True,
            "stdlib_only": True,
            "wall_clock_fields": False,
            "canonicalisation": "imported from tools.build_two_vote_packets",
        },
        "packet_count": len(packets),
        "count_assertion": len(packets) == EXPECTED_COUNT,
        "input_sha_pins": {
            "funcword_queue_v2": sha256_file(QUEUE),
            "loc_surfaces": sha256_file(LOC_SURFACE),
            "entries": sha256_file(ENTRIES),
            "prepass_rules": sha256_file(PREPASS_RULES),
            "gate_ssot": sha256_file(GATE_SSOT),
        },
        "inputs": {
            "funcword_queue_v2": input_pin(QUEUE, queue),
            "loc_surfaces": {"path": logical_path(LOC_SURFACE), "sha256": sha256_file(LOC_SURFACE)},
            "entries": {"path": logical_path(ENTRIES), "sha256": sha256_file(ENTRIES)},
            "prepass_rules": {"path": logical_path(PREPASS_RULES), "sha256": sha256_file(PREPASS_RULES)},
            "gate_ssot": {"path": logical_path(GATE_SSOT), "sha256": sha256_file(GATE_SSOT)},
        },
        "outputs": {
            "packets": {
                "path": logical_path(OUT_PACKETS),
                "row_count": len(packets),
                "canonical_rows_sha256": canonical_rows_sha256(packets),
                "bytes_sha256": stable_sha256(
                    render_jsonl(packets).decode("utf-8")
                ),
            },
        },
        "boundary_route_rows": {
            "count": len(boundary),
            "route": "divine_name_entry",
            "locations": sorted((p["canonical_location"] for p in boundary), key=loc_key),
        },
        "disjointness_proof": {
            "funcword_count": len(fw_locs),
            "decidable_count": len(dec_locs),
            "rebind_count": len(rebind_locs),
            "overlap_counts": {
                "funcword_decidable": len(fw_locs & dec_locs),
                "funcword_rebind": len(fw_locs & rebind_locs),
            },
            "all_pairwise_overlaps_zero": not (fw_locs & dec_locs) and not (fw_locs & rebind_locs),
        },
        "response_gate": {
            "tier": "two_vote_required",
            "decision_enum": ["function_confirmed", "reclassify", "needs_entry", "abstention"],
            "confidence_enum": ["high", "medium", "low", "abstain"],
        },
    }
    manifest["manifest_sha256"] = stable_sha256(manifest)
    return manifest


def write_outputs(packets: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    OUT_PACKETS.parent.mkdir(parents=True, exist_ok=True)
    with io.open(OUT_PACKETS, "wb") as handle:
        handle.write(render_jsonl(packets))
    with io.open(OUT_MANIFEST, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        handle.write("\n")


def self_test() -> None:
    """Red-first: prove tampering is caught, then prove the clean build passes."""
    surfaces = load_loc_surface(LOC_SURFACE)
    entries = load_entries(ENTRIES)
    prepass = load_prepass_categories(PREPASS_RULES)
    gate_sha = sha256_file(GATE_SSOT)
    queue = load_jsonl_plain(QUEUE)
    sample = queue[0]

    packet = build_packet(1, sample, surfaces, entries, prepass, gate_sha)

    # RED 1: mutate an evidence field without recomputing the sha -> must fail.
    tampered = json.loads(json.dumps(packet, ensure_ascii=False))
    tampered["token_identity"]["surface"] = "TAMPERED"
    try:
        validate_packet(tampered)
    except ValueError:
        pass
    else:
        raise AssertionError("RED-1 FAILED: tampered packet_sha256 not caught")

    # RED 2: break the echo-hash const -> must fail.
    tampered2 = json.loads(json.dumps(packet, ensure_ascii=False))
    tampered2["required_response_schema"]["properties"]["evidence_hashes"]["const"] = {}
    tampered2["packet_sha256"] = stable_sha256(
        {k: v for k, v in tampered2.items() if k != "packet_sha256"}
    )
    try:
        validate_packet(tampered2)
    except ValueError:
        pass
    else:
        raise AssertionError("RED-2 FAILED: echo-hash mismatch not caught")

    # RED 3: a prepassed row whose candidate set is forced wrong -> must fail.
    prepassed = next((r for r in queue if r.get("prepass_rule")), None)
    if prepassed is not None:
        bad_prepass = {k: dict(v) for k, v in prepass.items()}
        bad_prepass[prepassed["prepass_rule"]]["calibration_categories"] = ["preposition"]
        try:
            function_candidates(prepassed, bad_prepass)
        except ValueError:
            pass
        else:
            raise AssertionError("RED-3 FAILED: calibration mismatch not caught")

    # GREEN: clean packet validates, and a re-build is byte-identical.
    validate_packet(packet)
    p_again = build_packet(1, sample, surfaces, entries, prepass, gate_sha)
    if canonical_bytes(packet) != canonical_bytes(p_again):
        raise AssertionError("GREEN FAILED: build not deterministic")

    # Oracle: pre-pass calibration categories match the committed literal.
    loaded = {rid: set(v["calibration_categories"]) for rid, v in prepass.items()}
    if loaded != _EXPECTED_PREPASS_CATS:
        raise AssertionError(f"GREEN FAILED: prepass cats drift {loaded}")

    print("SELF-TEST OK: RED-1/RED-2/RED-3 caught; GREEN clean + deterministic")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run red-first self-test only")
    parser.add_argument("--check", action="store_true",
                        help="build in-memory and verify count/disjointness without writing")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0

    packets, manifest = build_all()
    dj = manifest["disjointness_proof"]
    if not dj["all_pairwise_overlaps_zero"]:
        raise SystemExit("STOP: function lane overlaps a sibling lane")
    if not manifest["count_assertion"]:
        raise SystemExit("STOP: packet count assertion failed")

    if args.check:
        print(f"CHECK OK: {manifest['packet_count']} packets, "
              f"boundary_route={manifest['boundary_route_rows']['count']}, "
              f"overlaps={dj['overlap_counts']}")
        return 0

    write_outputs(packets, manifest)
    print(f"WROTE {len(packets)} packets -> {logical_path(OUT_PACKETS)}")
    print(f"WROTE manifest -> {logical_path(OUT_MANIFEST)} sha={manifest['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
