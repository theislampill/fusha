#!/usr/bin/env python3
"""Compile the Q7 eight-canary, fixture-only pedagogical projection proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fact_ledger, fact_projectors


PRODUCER = "tools.tranche1_projection"
VERSION = "1.0.0"
SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PUBLIC_ROLE = {
    "definite_article": "ART",
    "derivative_prefix": "PFX",
    "verb_stem": "STEM",
    "active_participle_stem": "STEM",
    "noun_stem": "STEM",
    "plural_suffix": "SUFF",
    "subject_pronoun": "SUFF",
    "prepositional_lam": "PART",
    "proper_noun": "N",
}
MORPHOSYNTAX_ROLE = {
    "definite_article": "definite_article",
    "derivative_prefix": "other",
    "verb_stem": "stem",
    "active_participle_stem": "stem",
    "noun_stem": "stem",
    "plural_suffix": "other",
    "subject_pronoun": "subject_pronoun",
    "prepositional_lam": "preposition",
    "proper_noun": "stem",
}
DISPLAY_LABEL = {
    "definite_article": "ART",
    "other": "UNK",
    "stem": "STEM",
    "subject_pronoun": "PRON",
    "preposition": "P",
}


class TrancheCompileError(ValueError):
    """Raised when a source or policy invariant fails closed."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def raw_hash(raw: str) -> str:
    return "sha256:" + hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")


def _load_policy(path: Path) -> Dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "qamus.tranche1_canary_policy.v1":
        raise TrancheCompileError("unexpected canary policy schema")
    if policy.get("producer") != PRODUCER or policy.get("version") != VERSION:
        raise TrancheCompileError("canary policy producer/version mismatch")
    canaries = policy.get("canaries")
    if not isinstance(canaries, list) or len(canaries) != 8:
        raise TrancheCompileError("canary policy must contain exactly eight rows")
    locations = [row.get("loc") for row in canaries]
    if len(set(locations)) != 8:
        raise TrancheCompileError("canary policy locations must be unique")
    statuses = [row.get("status") for row in canaries]
    if statuses.count("candidate") != 4:
        raise TrancheCompileError("canary policy must contain exactly four candidates")
    for row in canaries:
        candidate = row.get("status") == "candidate"
        if candidate != (row.get("blocker") is None and row.get("route") is None):
            raise TrancheCompileError("candidate/queue routing mismatch at " + str(row.get("loc")))
    return policy


def _load_source_rows(path: Path, locations: set[str]) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    found: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            raw = line.rstrip("\r\n")
            if not raw:
                continue
            row = json.loads(raw)
            loc = row.get("loc")
            if loc not in locations:
                continue
            if loc in found:
                raise TrancheCompileError("duplicate source location: " + loc)
            found[loc] = (raw, row)
    missing = sorted(locations - set(found))
    if missing:
        raise TrancheCompileError("missing source locations: " + ", ".join(missing))
    return found


def _source_address(loc: str) -> Dict[str, str]:
    return {"address": "quran:%s / wbw:%s" % (loc, loc), "source_kind": "quran_token"}


def _materialization(artifact: str, field: str) -> Dict[str, Any]:
    return {"artifact": artifact, "field": field, "live_mutation_allowed": False}


def _full_materialization(artifact: str, field: str) -> Dict[str, Any]:
    return {
        "artifact": artifact,
        "field": field,
        "public_materialization_allowed": False,
        "live_mutation_allowed": False,
    }


def _fact_row(policy: Dict[str, Any], source_hash: str) -> Dict[str, Any]:
    loc = policy["loc"]
    target = "public-hover-projections.jsonl" if policy["status"] == "candidate" else "unresolved-queue.jsonl"
    row: Dict[str, Any] = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": {
            "ref_type": "surface_occurrence",
            "loc": loc,
            "entry_id": "tranche1-entry-" + loc.replace(":", "-"),
            "card_id": "tranche1-card-" + ":".join(loc.split(":")[:2]).replace(":", "-"),
            "qword_row_id": "tranche1-qword-" + loc.replace(":", "-"),
        },
        "fact_type": "surface_observation",
        "candidate_or_value": {
            "value": {
                "loc": loc,
                "surface": policy["surface"],
                "source_row_hash": source_hash,
                "policy_status": policy["status"],
            },
            "competing_alternatives": [],
        },
        "scope": "occurrence",
        "source_address": _source_address(loc),
        "evidence": [{
            "evidence_id": "tranche1-source-row-" + loc.replace(":", "-"),
            "type": "deterministic_derivation",
            "detail": "Exact fixture source-row observation.",
            "source_address": "quran:" + loc,
        }],
        "provenance": {
            "actor": PRODUCER,
            "method": "exact_source_row_observation",
            "created_at": "2026-07-16T00:00:00Z",
            "input_hashes": {"source_row": source_hash},
        },
        "review_votes": [],
        "certification_state": "candidate" if policy["status"] == "candidate" else "blocked",
        "confidence_or_calibration": None,
        "defeaters": [] if policy["status"] == "candidate" else [{
            "type": policy["status"],
            "detail": policy["blocker"],
            "fact_ids": [],
        }],
        "exceptions": [],
        "dependency_hashes": {"source_row": source_hash},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": "projector:" + policy["projector_id"],
        "materialization_target": _materialization(target, "segments" if policy["status"] == "candidate" else "queue"),
        "producer": PRODUCER,
        "projector_id": policy["projector_id"],
        "version": VERSION,
        "status": policy["status"],
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    row["fact_ids"] = [row["fact_id"]]
    errors = fact_ledger.validate_schema(row)
    if errors:
        raise TrancheCompileError("invalid fact row at %s: %s" % (loc, "; ".join(errors)))
    return row


def _public_segments(source_row: Dict[str, Any]) -> List[Dict[str, str]]:
    result = []
    for segment in source_row.get("segments") or []:
        role = PUBLIC_ROLE.get(segment.get("role"))
        if role is None:
            raise TrancheCompileError("no public role mapping for " + str(segment.get("role")))
        gloss = segment.get("gloss_contribution")
        qg_class = segment.get("class")
        if not gloss or not qg_class:
            raise TrancheCompileError("candidate segment lacks exact gloss/class mapping")
        result.append({
            "role": role,
            "surface": segment["surface"],
            "qg_class": qg_class,
            "gloss": gloss,
        })
    if "".join(row["surface"] for row in result) != source_row["surface"]:
        raise TrancheCompileError("candidate segment surfaces do not reconstruct " + source_row["loc"])
    return result


def _public_payload(source_row: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    segments = _public_segments(source_row)
    return {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "token_contribution_gloss": source_row["token_contribution_gloss"],
        "contextual_phrase_gloss": source_row.get("contextual_phrase_gloss"),
        "morphline": "+".join(row["role"] for row in segments),
        "segments": segments,
        "learner_explanation": policy["learner_explanation"],
    }


def _public_projection(
    source_row: Dict[str, Any], policy: Dict[str, Any], fact_ids: List[str]
) -> Dict[str, Any]:
    loc = policy["loc"]
    payload = _public_payload(source_row, policy)
    row = {
        "schema": "qamus/public-hover-projection@1",
        "row_id": "tranche1-row-" + loc.replace(":", "-"),
        "entry_id": source_row.get("entry_id") or "tranche1-entry-" + loc.replace(":", "-"),
        "card_id": "tranche1-card-" + str(source_row.get("card_ref") or ":".join(loc.split(":")[:2])).replace(":", "-"),
        "surface": source_row["surface"],
        "canonical_quran_loc": loc,
        "canonical_wbw_loc": loc,
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "public_gloss": source_row["token_contribution_gloss"],
        "token_contribution": source_row["token_contribution_gloss"],
        "contextual_phrase_gloss": source_row.get("contextual_phrase_gloss"),
        "segments": payload["segments"],
        "qg_classes": [segment["qg_class"] for segment in payload["segments"]],
        "morphline": payload["morphline"],
        "learner_explanation": payload["learner_explanation"],
        "source_segment_labels": list(policy["expected_segment_labels"]),
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_source_names_public": False,
            "internal_provenance_public": False,
        },
        "fact_ids": list(fact_ids),
        "status": "candidate",
        "source_address": _source_address(loc),
        "materialization_target": _materialization("public-hover-projections.jsonl", "segments"),
        "producer": PRODUCER,
        "projector_id": policy["projector_id"],
        "version": VERSION,
        "live_mutation_allowed": False,
    }
    if loc == "2:34:5":
        row["no_root_status"] = "proper_name_no_public_root"
    return row


def _surface_norm(surface: str) -> str:
    normalized = unicodedata.normalize("NFC", surface)
    return "".join(
        "ا" if char == "ٱ" else char
        for char in normalized
        if not char.isspace() and char != "ـ" and not ("\u06d6" <= char <= "\u06ed")
    )


def _canonical_payload(
    projection: Dict[str, Any], source_hash: str, source_commit: str
) -> Dict[str, Any]:
    loc = projection["canonical_quran_loc"]
    public_payload = {
        "src": projection["src"],
        "kind": projection["kind"],
        "lang": projection["lang"],
        "token_contribution_gloss": projection["token_contribution"],
        "contextual_phrase_gloss": projection.get("contextual_phrase_gloss"),
        "morphline": projection["morphline"],
        "segments": projection["segments"],
        "learner_explanation": projection["learner_explanation"],
    }
    return {
        "schema": "qamus.canonical_hover_payload.v2",
        "canonical_payload_id": "chp:" + row_hash(public_payload).split(":", 1)[1][:16],
        "payload_family": "source_address_exact",
        "surface_norm": _surface_norm(projection["surface"]),
        "root": None,
        "lemma_id": None,
        "lemma_status": "candidate",
        "pos": "unknown",
        "pattern": None,
        "sarf_certification": "candidate",
        "nahw_certification": "candidate",
        "public_payload": public_payload,
        "private_trace": {
            "loc": loc,
            "source_row_hash": source_hash,
            "source_commit": source_commit,
            "fixture_only": True,
        },
        "created_at": None,
        "updated_at": None,
        "fact_ids": projection["fact_ids"],
        "status": "candidate",
        "source_address": projection["source_address"],
        "materialization_target": _materialization("canonical-hover-payload.jsonl", "public_payload"),
        "producer": PRODUCER,
        "projector_id": projection["projector_id"],
        "version": VERSION,
    }


def _morphology_lattice(
    source_row: Dict[str, Any], policy: Dict[str, Any], fact_ids: List[str]
) -> Dict[str, Any]:
    features = {
        key: value
        for key, value in (policy.get("morphology_candidate") or {}).items()
        if key in {
            "verb_form", "voice", "aspect", "mood", "person", "number", "gender",
            "case", "state", "derivative_type", "particle_function",
        }
    }
    return {
        "token_ref": policy["loc"],
        "candidates": [{
            "lemma": None,
            "root": None,
            "pattern": None,
            "pos": policy["pos"],
            "features": features,
            "confidence": "low",
            "ambiguity_reason": "Fixture candidate only; no linguistic certification is asserted.",
            "evidence_class": "source_addressed_confirmable",
            "gate": "two_vote_required",
            "rank": 1,
            "score": 0,
            "segment_candidate_ref": 0,
        }],
        "top_rank": 1,
        "n_candidates": 1,
        "all_unvoweled_kept": True,
        "fact_ids": list(fact_ids),
        "status": "candidate",
        "source_address": _source_address(policy["loc"]),
        "materialization_target": _materialization("morphology-lattice.jsonl", "candidates"),
        "producer": PRODUCER,
        "projector_id": policy["projector_id"],
        "version": VERSION,
    }


def _display_class(role: str, pos: str) -> str:
    if role == "stem":
        if pos == "verb":
            return "qg-verb-stem"
        if pos == "proper_noun":
            return "qg-proper-noun"
        return "qg-noun-stem"
    return {
        "definite_article": "qg-article",
        "subject_pronoun": "qg-subject-pronoun",
        "preposition": "qg-preposition",
        "other": "qg-unknown",
    }[role]


def _sarf_block(policy: Dict[str, Any]) -> Dict[str, Any]:
    pos = policy["pos"]
    candidate = policy.get("morphology_candidate") or {}
    is_verb = pos == "verb"
    is_nominal = not is_verb
    return {
        "pos": "fiʿl" if is_verb else "ism",
        "root": None,
        "pattern": None,
        "verb_form": candidate.get("verb_form", "unknown") if is_verb else "not_applicable",
        "voice": candidate.get("voice", "unknown") if is_verb else "not_applicable",
        "tense_aspect": candidate.get("aspect", "unknown") if is_verb else "not_applicable",
        "mood": candidate.get("mood", "unknown") if is_verb else "not_applicable",
        "person": candidate.get("person", "unknown") if is_verb else "not_applicable",
        "number": candidate.get("number", "unknown") if is_verb else "not_applicable",
        "gender": candidate.get("gender", "unknown") if is_verb else "not_applicable",
        "noun_number": candidate.get("number", "unknown") if is_nominal else "not_applicable",
        "definiteness": candidate.get("state", "unknown") if is_nominal else "not_applicable",
        "case": candidate.get("case", "unknown") if is_nominal else "not_applicable",
        "derivative_type": (
            "proper_noun" if pos == "proper_noun"
            else "common_noun" if pos == "noun"
            else "unknown" if is_nominal
            else "not_applicable"
        ),
    }


def _morphosyntax_token(
    source_row: Dict[str, Any], policy: Dict[str, Any], fact_ids: List[str]
) -> Dict[str, Any]:
    loc = policy["loc"]
    segments = []
    display = []
    for index, source_segment in enumerate(source_row["segments"]):
        role = MORPHOSYNTAX_ROLE[source_segment["role"]]
        segment: Dict[str, Any] = {
            "role": role,
            "surface": source_segment["surface"],
            "gloss_contribution": source_segment["gloss_contribution"],
        }
        if role == "subject_pronoun":
            segment.update({"person": "3", "number": "plural", "gender": "masculine", "case": "none"})
        segments.append(segment)
        display.append({
            "segment_index": index,
            "role": role,
            "class": _display_class(role, policy["pos"]),
            "label": DISPLAY_LABEL[role],
        })
    if "".join(segment["surface"] for segment in segments) != source_row["surface"]:
        raise TrancheCompileError("morphosyntax segment parity failed at " + loc)
    syntax_candidate = loc == "2:34:5"
    return {
        "loc": loc,
        "wbw_loc": "wbw:" + loc,
        "surface": source_row["surface"],
        "key": source_row["surface"],
        "gloss": source_row["token_contribution_gloss"],
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "decision_state": "rich_candidate",
        "lemma": None,
        "root": None,
        "pos": policy["pos"],
        "sarf": _sarf_block(policy),
        "nahw": {
            "function": "prepositional relation with a proper name" if syntax_candidate else "candidate token contribution",
            "iʿrab_role": "candidate object of a preposition" if syntax_candidate else None,
            "governor": "internal prepositional lam" if syntax_candidate else None,
            "governed_by": None,
            "pp_attachment": None,
            "idafa_relation": None,
            "pronoun_referent": None,
            "clause_relation": None,
            "reasoning_summary": (
                "The prepositional relation and candidate case effect remain review-gated."
                if syntax_candidate else
                "The visible segment contributions remain review-gated candidates."
            ),
        },
        "segments": segments,
        "parse_key": {
            "key": "CANDIDATE-" + loc.replace(":", "-"),
            "summary": "Fixture-only candidate with exact visible segment boundaries.",
            "components": [
                {"label": label, "value": segment["gloss_contribution"]}
                for label, segment in zip(policy["expected_segment_labels"], segments)
            ],
        },
        "display": {"palette": "qamus-grammar-v1", "segments": display},
        "hover_contract": {
            "must_surface": [segment["gloss_contribution"] for segment in segments],
            "must_not_surface": ["untyped fallback"],
            "reason": "Every visible segment contribution must remain explicit in this fixture candidate.",
        },
        "learner_explanation": policy["learner_explanation"],
        "blocker": None,
        "evidence": {
            "labels": ["qamus:tranche1:fixture"],
            "gate": "two_vote_required",
            "reasoning": "Exact source-addressed fixture candidate; no certification transition performed.",
        },
        "public_boundary": {
            "public_gloss_src": "qamus",
            "public_gloss_kind": "authored",
            "public_gloss_lang": "en",
            "external_source_names_public": False,
        },
        "fact_ids": list(fact_ids),
        "status": "candidate",
        "source_address": _source_address(loc),
        "materialization_target": _materialization("morphosyntax-token.jsonl", "segments"),
        "producer": PRODUCER,
        "projector_id": policy["projector_id"],
        "version": VERSION,
    }


def _dependency_lattice(
    source_row: Dict[str, Any], policy: Dict[str, Any], fact_ids: List[str]
) -> Dict[str, Any]:
    loc = policy["loc"]
    if loc == "2:34:5":
        tokens = [
            {"ref": loc + "#lam", "surface": source_row["segments"][0]["surface"], "pos": "preposition", "case_visible": None},
            {"ref": loc + "#adam", "surface": source_row["segments"][1]["surface"], "pos": "proper_noun", "case_visible": "fatha candidate for jarr"},
        ]
        edges = [{
            "edge_id": "tranche1-2-34-5-lam-adam",
            "dependent": loc + "#adam",
            "candidate_head": loc + "#lam",
            "headless": False,
            "governor_type": "particle",
            "rel_label": "jar_majrur",
            "rel_label_ar": "majrur by a preposition (candidate)",
            "assigned_case_mood": "genitive",
            "governor_justification": "The prepositional lām is the candidate governor of the following proper name.",
            "justification_rule": "preposition_governs_genitive",
            "justification_confidence": "medium",
            "evidence_class": "source_addressed",
            "unresolved_alternatives": [],
            "contradiction_marker": False,
            "right_answer_wrong_reason_marker": False,
            "decision_status": "resolved",
            "gate": "two_vote_required",
            "route_to": {"lane": "nahw", "procedure": "nahw/procedures/preposition-pronoun.md"},
        }]
        by_decision = {"resolved": 1}
        unresolved = 0
    else:
        tokens = [{"ref": loc, "surface": source_row["surface"], "pos": "noun", "case_visible": None}]
        edges = [{
            "edge_id": "tranche1-5-2-12-pending",
            "dependent": loc,
            "candidate_head": None,
            "headless": False,
            "governor_type": "none",
            "rel_label": "null",
            "rel_label_ar": "not assigned",
            "assigned_case_mood": None,
            "governor_justification": "No governor or ending evidence is available; no case or role is asserted.",
            "justification_rule": "not_determinable",
            "justification_confidence": "low",
            "evidence_class": "unknown",
            "unresolved_alternatives": [],
            "contradiction_marker": False,
            "right_answer_wrong_reason_marker": False,
            "decision_status": "pending",
            "gate": "human_source_review_required",
            "route_to": dict(policy["route"]),
        }]
        by_decision = {"pending": 1}
        unresolved = 1
    return {
        "schema": "fusha/dependency-candidate-lattice@1",
        "input_mode": "source_addressed",
        "source_unit": {"address": "quran:" + loc, "scope": "in_scope_source_addressed"},
        "tokens": tokens,
        "edges": edges,
        "summary": {
            "live_writes": 0,
            "n_edges": len(edges),
            "n_unresolved": unresolved,
            "by_decision": by_decision,
        },
        "public_boundary": {
            "public_gloss_src": "qamus",
            "public_gloss_kind": "authored",
            "public_gloss_lang": "en",
            "external_source_names_public": False,
        },
        "source_boundary": {"heuristic_never_overrides_source": True, "quran_text_altered": False},
        "fact_ids": list(fact_ids),
        "status": policy["status"],
        "source_address": _source_address(loc),
        "materialization_target": _materialization("dependency-lattice.jsonl", "edges"),
        "producer": PRODUCER,
        "projector_id": policy["projector_id"],
        "version": VERSION,
    }


def _field_mappings(source_row: Dict[str, Any], candidate: bool) -> List[Dict[str, Any]]:
    if not candidate:
        return []
    return [{
        "segment_index": index,
        "source_gloss_field": "gloss_contribution",
        "source_class_field": "class",
        "public_gloss_field": "gloss",
        "public_class_field": "qg_class",
        "gloss": segment["gloss_contribution"],
        "qg_class": segment["class"],
    } for index, segment in enumerate(source_row["segments"])]


def compile_tranche(
    whitelist_path: Path,
    policy_path: Path,
    out_dir: Path,
    source_commit: str,
) -> Dict[str, Any]:
    """Compile deterministic artifacts without mutating the input corpus or runtime."""

    whitelist_path = Path(whitelist_path)
    policy_path = Path(policy_path)
    out_dir = Path(out_dir)
    if not SOURCE_COMMIT_RE.fullmatch(source_commit):
        raise TrancheCompileError("source_commit must be a 40-character lowercase Git SHA")
    policy_doc = _load_policy(policy_path)
    canaries = policy_doc["canaries"]
    source = _load_source_rows(whitelist_path, {row["loc"] for row in canaries})
    out_dir.mkdir(parents=True, exist_ok=True)

    source_lines: List[str] = []
    facts: List[Dict[str, Any]] = []
    morphology: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    morphosyntax: List[Dict[str, Any]] = []
    canonical: List[Dict[str, Any]] = []
    normalized: List[Dict[str, Any]] = []
    projections: List[Dict[str, Any]] = []
    queue: List[Dict[str, Any]] = []
    crosswalk: List[Dict[str, Any]] = []
    dom_expectations: List[Dict[str, Any]] = []
    renderer_rows: List[Dict[str, Any]] = []
    rich_rows: List[Dict[str, Any]] = []

    for canary in canaries:
        loc = canary["loc"]
        raw, source_row = source[loc]
        source_lines.append(raw)
        if source_row.get("surface") != canary["surface"]:
            raise TrancheCompileError("policy/source surface mismatch at " + loc)
        labels = [segment.get("label") for segment in source_row.get("segments") or []]
        if labels != canary["expected_segment_labels"]:
            raise TrancheCompileError("policy/source segment-label mismatch at " + loc)
        source_row_hash = raw_hash(raw)
        fact = _fact_row(canary, source_row_hash)
        facts.append(fact)
        fact_ids = [fact["fact_id"]]

        projected = fact_projectors.REGISTRY.run(
            canary["projector_id"],
            source_row=source_row,
            policy=canary,
            fact_ids=fact_ids,
        )
        projected.update({
            "canary_id": "tranche1:" + loc,
            "source_row_hash": source_row_hash,
            "source_commit": source_commit,
        })
        candidate = canary["status"] == "candidate"
        if candidate:
            public_row = _public_projection(source_row, canary, fact_ids)
            projections.append(public_row)
            payload = _public_payload(source_row, canary)
            projected["public_payload"] = payload
            projected["source_segment_labels"] = list(canary["expected_segment_labels"])
            if loc == "2:34:5":
                projected["no_root_status"] = "proper_name_no_public_root"
            canonical.append(_canonical_payload(public_row, source_row_hash, source_commit))
            morphology.append(_morphology_lattice(source_row, canary, fact_ids))
            morphosyntax.append(_morphosyntax_token(source_row, canary, fact_ids))
            renderer_rows.append({
                "loc": loc,
                "surface": source_row["surface"],
                "public_payload": payload,
                "fact_ids": fact_ids,
                "producer": PRODUCER,
                "projector_id": canary["projector_id"],
                "version": VERSION,
                "live_mutation_allowed": False,
            })
            rich_rows.append({
                "loc": loc,
                "surface": source_row["surface"],
                "token_contribution_gloss": source_row["token_contribution_gloss"],
                "contextual_phrase_gloss": source_row.get("contextual_phrase_gloss"),
                "morphline": payload["morphline"],
                "learner_explanation": canary["learner_explanation"],
                "no_root_reason": "proper_name_no_public_root" if loc == "2:34:5" else "pending_candidate",
                "segments": [{
                    "segment_index": index,
                    "surface": segment["surface"],
                    "role": source_segment["role"],
                    "label": source_segment["label"],
                    "class": segment["qg_class"],
                    "gloss_contribution": segment["gloss"],
                } for index, (segment, source_segment) in enumerate(zip(payload["segments"], source_row["segments"]))],
                "fact_ids": fact_ids,
                "status": "candidate",
                "producer": PRODUCER,
                "projector_id": canary["projector_id"],
                "version": VERSION,
            })
            output_artifact = "public-hover-projections.jsonl"
            output_row = public_row
        else:
            queue.append(projected)
            output_artifact = "unresolved-queue.jsonl"
            output_row = projected
        normalized.append(projected)
        output_hash = row_hash(output_row)
        crosswalk.append({
            "schema": "qamus.tranche1_projection_crosswalk.v1",
            "record_type": projected["record_type"],
            "canary_id": "tranche1:" + loc,
            "quran_loc": loc,
            "wbw_loc": "wbw:" + loc,
            "surface": source_row["surface"],
            "fact_ids": fact_ids,
            "status": canary["status"],
            "source_address": _source_address(loc),
            "source_row_hash": source_row_hash,
            "source_commit": source_commit,
            "materialization_target": _full_materialization(
                output_artifact,
                "segments" if candidate else "queue",
            ),
            "producer": PRODUCER,
            "projector_id": canary["projector_id"],
            "version": VERSION,
            "output_artifact": output_artifact,
            "output_row_hash": output_hash,
            "field_mappings": _field_mappings(source_row, candidate),
            "blocker": canary["blocker"],
            "route": canary["route"],
            "live_mutation_allowed": False,
        })
        dom_expectations.append({
            "schema": "qamus.tranche1_dom_consumption_expectation.v1",
            "loc": loc,
            "surface": source_row["surface"],
            "status": canary["status"],
            "fixture_only": True,
            "consumer_symbol": "fillRhLiveHover",
            "hover_expected": candidate,
            "silent_fallback_allowed": False,
            "expected_segment_labels": list(canary["expected_segment_labels"]) if candidate else [],
            "expected_qg_classes": [segment["class"] for segment in source_row["segments"]] if candidate else [],
            "expected_segment_glosses": [segment["gloss_contribution"] for segment in source_row["segments"]] if candidate else [],
            "blocker": canary["blocker"],
            "route": canary["route"],
            "live_dom_assertion_performed": False,
            "renderer_mutation_allowed": False,
            "live_mutation_allowed": False,
        })

    syntax_policy = {row["loc"]: row for row in canaries if row["fact_family"] == "nahw"}
    source_by_loc = {loc: row for loc, (_raw, row) in source.items()}
    fact_ids_by_loc = {row["subject_identity"]["loc"]: [row["fact_id"]] for row in facts}
    for loc in ("2:34:5", "5:2:12"):
        dependencies.append(_dependency_lattice(source_by_loc[loc], syntax_policy[loc], fact_ids_by_loc[loc]))

    (out_dir / "source-canaries.jsonl").write_text("\n".join(source_lines) + "\n", encoding="utf-8", newline="\n")
    artifacts = {
        "fact-ledger.jsonl": facts,
        "morphology-lattice.jsonl": morphology,
        "dependency-lattice.jsonl": dependencies,
        "morphosyntax-token.jsonl": morphosyntax,
        "canonical-hover-payload.jsonl": canonical,
        "normalized-public-payload.jsonl": normalized,
        "public-hover-projections.jsonl": projections,
        "unresolved-queue.jsonl": queue,
        "projection-crosswalk.jsonl": crosswalk,
        "dom-consumption.expectations.jsonl": dom_expectations,
        "renderer-completeness.jsonl": renderer_rows,
        "rich-hover-norm.jsonl": rich_rows,
    }
    for name, rows in artifacts.items():
        _write_jsonl(out_dir / name, rows)

    return {
        "schema": "qamus.tranche1_compile_summary.v1",
        "canonical_count": len(normalized),
        "candidate_count": len(projections),
        "queue_count": len(queue),
        "live_mutations": 0,
        "source_commit": source_commit,
        "source_corpus": str(whitelist_path),
        "output_dir": str(out_dir),
        "artifact_hashes": {
            name: raw_hash((out_dir / name).read_text(encoding="utf-8"))
            for name in ["source-canaries.jsonl", *artifacts]
        },
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile", help="compile the eight fixture canaries")
    compile_parser.add_argument("--whitelist", required=True, type=Path)
    compile_parser.add_argument("--policy", required=True, type=Path)
    compile_parser.add_argument("--out-dir", required=True, type=Path)
    compile_parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    if args.command == "compile":
        summary = compile_tranche(args.whitelist, args.policy, args.out_dir, args.source_commit)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
