#!/usr/bin/env python3
"""Build the FB1 clitic-pronoun calibration packet.

The producer is intentionally narrow: it accepts source-addressed structured
segments, emits F-A typed candidate facts, and routes anything that needs a
linguistic guess to an explicit unresolved record. It never writes a corpus or
public materialization.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Optional

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import lattice_projectors  # noqa: E402
from tools import typed_claim_contract as tcc  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "qamus.typed_claim_contract.v1"
CONTRACT_VERSION = "1.0.0"
PRODUCER_ID = "tools.build_clitic_pronoun_producer"
PRODUCER_VERSION = "1.0.0"
PROJECTOR_ID = "sarf.fb1_clitic_pronoun_composition.v1"
RULE_ID = "sarf.clitic_pronoun_composition.calibration"

_FUNCTION_CLASSES = {
    "qg-article",
    "qg-conjunction",
    "qg-emphasis",
    "qg-lam",
    "qg-negation",
    "qg-particle",
    "qg-preposition",
    "qg-question",
    "qg-result-fa",
}
_FUNCTION_ROLES = {
    "condition_answer_fa",
    "conjunction",
    "definite_article",
    "emphasis_particle",
    "exception_particle",
    "ina_attached_pronoun",
    "inna_particle",
    "interrogative_hamza",
    "lam_prefix",
    "linking_fa",
    "negation_particle",
    "preposition",
    "prefix_conjunction",
    "prefix_preposition",
    "prefix_result_fa",
    "prefix_result_or_conjunction",
    "question_particle",
    "subordinating_particle",
}
_PRONOUN_ROLE_MARKERS = ("pronoun", "possessive", "subject_marker", "object")
_IDGHAM_CLASSES = {
    "A_clean_split",
    "B_shared_letter_clean_split",
    "C_fused_boundary",
    "D_ambiguous_boundary",
}
_PROJECTION_ARTIFACT = "fb1-clitic-pronoun-calibration.jsonl"


class ProducerError(ValueError):
    """Raised when a producer input cannot be represented safely."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strip_quran_prefix(value: object) -> str:
    text = str(value or "")
    return text[6:] if text.startswith("quran:") else text


def _loc(row: dict[str, Any]) -> str:
    loc = _strip_quran_prefix(row.get("quran_loc") or row.get("loc"))
    if not re.fullmatch(r"[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}", loc):
        raise ProducerError("missing or invalid Quran occurrence address")
    return loc


def _surface(row: dict[str, Any]) -> str:
    surface = row.get("surface")
    if not isinstance(surface, str) or not surface:
        raise ProducerError("missing written surface")
    return surface


def _occurrence(row: dict[str, Any]) -> dict[str, Any]:
    loc = _loc(row)
    surface = _surface(row)
    occurrence: dict[str, Any] = {
        "occurrence_id": "quran:" + loc,
        "quran_loc": loc,
        "wbw_loc": "wbw:" + loc,
        "surface": surface,
        "surface_length": len(surface),
    }
    for key in ("entry_id", "card_id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            occurrence[key] = value
    return occurrence


def _source_ref(row: dict[str, Any], loc: str) -> dict[str, str]:
    source_kind = row.get("_fb1_source_kind") or row.get("source_kind") or "corpus_record"
    source_id = row.get("_fb1_source_id") or row.get("source_id") or "fb1-calibration-input"
    address = row.get("_fb1_source_address") or row.get("source_address")
    if isinstance(address, dict):
        address = address.get("address")
    if not isinstance(address, str) or not address:
        address = "corpus:fb1-calibration-input#loc=" + loc
    if source_kind not in {"quran_token", "qamus_entry_field", "corpus_record", "construction", "review_artifact"}:
        raise ProducerError("invalid source kind")
    return {"source_id": str(source_id), "source_kind": source_kind, "address": address}


def _minimal_segment(segment: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in ("segment_index", "surface", "role", "class", "label", "typed_kind"):
        if key in segment and segment[key] is not None:
            output[key] = segment[key]
    return output


def _source_row_hash(row: dict[str, Any]) -> str:
    safe = {
        "loc": row.get("loc") or row.get("quran_loc"),
        "surface": row.get("surface"),
        "segments": [_minimal_segment(s) for s in row.get("segments", []) if isinstance(s, dict)],
        "idgham_boundary": row.get("idgham_boundary"),
        "protective_nun": row.get("protective_nun"),
    }
    return _hash(safe)


def _safe_role(role: object) -> str:
    value = str(role or "").strip().lower()
    value = re.sub(r"[^a-z0-9_:-]+", "_", value)
    if not value or not re.match(r"^[a-z]", value):
        raise ProducerError("segment role is required and must be a typed identifier")
    return value


def _sorted_segments(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw = row.get("segments")
    if not isinstance(raw, list) or not raw:
        raise ProducerError("structured source segments are required")
    segments = [copy.deepcopy(item) for item in raw if isinstance(item, dict)]
    if len(segments) != len(raw):
        raise ProducerError("every segment must be a structured object")
    try:
        segments.sort(key=lambda item: int(item["segment_index"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ProducerError("segment_index is required for every segment") from exc
    indexes = [int(item["segment_index"]) for item in segments]
    if indexes != list(range(len(indexes))):
        raise ProducerError("segment indexes must be contiguous from zero")
    for item in segments:
        item["segment_index"] = int(item["segment_index"])
        item["role"] = _safe_role(item.get("role"))
        if not isinstance(item.get("surface"), str) or not item["surface"]:
            raise ProducerError("every segment needs an exact written surface")
        if not isinstance(item.get("class"), str) or not item["class"]:
            raise ProducerError("every segment needs a typed class")
    return segments


def _reconstruct(surface: str, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    cursor = 0
    surface_bytes = surface.encode("utf-8")
    for segment in segments:
        piece = segment["surface"]
        end = cursor + len(piece)
        if surface[cursor:end] != piece:
            raise ProducerError("segment surfaces do not form an exact written split")
        if surface[cursor:end].encode("utf-8") != piece.encode("utf-8"):
            raise ProducerError("segment boundary is not UTF-8 byte exact")
        spans.append(
            {
                "span_id": "span:%d:%s" % (segment["segment_index"], segment["role"]),
                "start": cursor,
                "end": end,
                "surface": piece,
                "role": segment["role"],
            }
        )
        cursor = end
    joined = "".join(item["surface"] for item in segments)
    if cursor != len(surface) or joined != surface or joined.encode("utf-8") != surface_bytes:
        raise ProducerError("segment reconstruction is not exact in Unicode and UTF-8 bytes")
    return spans, {
        "byte_exact": True,
        "unicode_length": len(surface),
        "utf8_length": len(surface_bytes),
        "utf8_sha256": hashlib.sha256(surface_bytes).hexdigest(),
        "joined_segment_surfaces": joined,
        "span_count": len(spans),
    }


def _contains_shadda_at_boundary(segment_surface: str) -> bool:
    # A shadda in the first few written code points after a segment boundary is
    # an orthographic warning only. It is never itself proof of idgham.
    return "\u0651" in segment_surface[:4]


def _bare_arabic(value: str) -> str:
    stripped = "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if not (
            (unicodedata.category(char).startswith("M") and ord(char) not in {0x0654, 0x0655})
            or char == "ـ"
        )
    )
    return unicodedata.normalize("NFC", stripped)


def _function_ambiguity(segments: Iterable[dict[str, Any]], surface: str) -> bool:
    candidates = [surface] + [str(segment.get("surface", "")) for segment in segments]
    return any(_bare_arabic(candidate) in {"لا", "إلا"} for candidate in candidates)


def _is_function_segment(segment: dict[str, Any]) -> bool:
    role = str(segment.get("role", ""))
    klass = str(segment.get("class", ""))
    return role in _FUNCTION_ROLES or klass in _FUNCTION_CLASSES


def _is_closed_class_row(row: dict[str, Any], segments: list[dict[str, Any]]) -> bool:
    return bool(segments) and all(_is_function_segment(segment) or _is_pronoun_segment(segment) for segment in segments)


def _is_pronoun_segment(segment: dict[str, Any]) -> bool:
    role = str(segment.get("role", ""))
    klass = str(segment.get("class", ""))
    return any(marker in role for marker in _PRONOUN_ROLE_MARKERS) or "pronoun" in klass


def _root_claim_present(row: dict[str, Any], segments: list[dict[str, Any]]) -> bool:
    for key in ("root", "root_claim", "root_claim_values"):
        value = row.get(key)
        if value not in (None, "", [], {}):
            return True
    for segment in segments:
        if segment.get("root") not in (None, "", [], {}):
            return True
    sarf = row.get("sarf_facts")
    if isinstance(sarf, dict):
        if sarf.get("root") not in (None, "", [], {}):
            return True
        base = sarf.get("root_base_form")
        if isinstance(base, dict) and base.get("root") not in (None, "", [], {}):
            return True
        morphline = sarf.get("morphline")
    else:
        morphline = row.get("morphline")
    if isinstance(morphline, str):
        # This is a defeater detector, not a root parser. A morphline can only
        # make a closed-class row abstain; it can never create a root fact.
        if re.search(r"(?:^|[·;])\s*root\s+", morphline, flags=re.IGNORECASE):
            return True
    return False


def _idgham_boundary(row: dict[str, Any], segments: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], Optional[tuple[str, str]]]:
    metadata = row.get("idgham_boundary")
    if metadata is None:
        metadata = row.get("idgham")
    if metadata is not None and not isinstance(metadata, dict):
        return None, ("idgham_boundary_metadata_shape", "sarf.idgham_boundary_review")
    if isinstance(metadata, dict):
        boundary_class = metadata.get("boundary_class")
        if boundary_class not in _IDGHAM_CLASSES:
            return None, ("idgham_boundary_class_unknown", "sarf.idgham_boundary_review")
        if boundary_class in {"C_fused_boundary", "D_ambiguous_boundary"}:
            return None, (
                "idgham_" + boundary_class,
                str(metadata.get("route") or "sarf.idgham_boundary_review"),
            )
        if metadata.get("byte_clean") is not True:
            return None, ("idgham_boundary_not_byte_clean", "sarf.idgham_boundary_review")
        return {
            "boundary_class": boundary_class,
            "byte_clean": True,
            "source_fact_id": str(metadata.get("source_fact_id") or "fb1-source-idgham-boundary"),
        }, None

    # Only the article + sun-letter surface shape is treated as a boundary
    # warning here. Shadda elsewhere is a lexical surface observation and does
    # not authorize an idgham claim.
    for index, segment in enumerate(segments[1:], 1):
        previous = segments[index - 1]
        if previous.get("role") == "definite_article" and _contains_shadda_at_boundary(segment["surface"]):
            return None, ("idgham_D_ambiguous_boundary", "sarf.idgham_boundary_review")
    return None, None


def _protective_nun_info(row: dict[str, Any], segments: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], Optional[tuple[str, str]]]:
    explicit = []
    for segment in segments:
        role = str(segment.get("role", ""))
        klass = str(segment.get("class", ""))
        typed_kind = segment.get("typed_kind")
        if role == "protective_nun" or klass == "qg-protective-nun" or typed_kind == "sarf.protective_nun":
            explicit.append(segment)
    if any(str(item.get("role")) in _FUNCTION_ROLES or str(item.get("class")) in _FUNCTION_CLASSES for item in explicit):
        return None, ("protective_nun_particle_misclassification", "sarf.protective_nun_review")

    metadata = row.get("protective_nun")
    if metadata is not None and not isinstance(metadata, dict):
        return None, ("protective_nun_metadata_shape", "sarf.protective_nun_review")
    if isinstance(metadata, dict) and metadata.get("byte_clean") is not True:
        return None, ("protective_nun_fused_boundary", "sarf.protective_nun_review")
    if isinstance(metadata, dict) and metadata.get("byte_clean") is True and not explicit:
        piece = metadata.get("surface")
        if not isinstance(piece, str) or not piece:
            return None, ("protective_nun_surface_missing", "sarf.protective_nun_review")
        return {
            "segment_index": int(metadata.get("segment_index", 900)),
            "surface": piece,
            "role": "protective_nun",
            "class": "qg-protective-nun",
            "typed_kind": "sarf.protective_nun",
        }, None
    return (explicit[0] if explicit else None), None


def _ownership(kind: str) -> dict[str, Any]:
    primary_id = {
        "function": "fb1.nahw.function_word",
        "host": "fb1.sarf.host",
        "clitic": "fb1.sarf.clitic_pronoun",
        "protective": "fb1.sarf.protective_nun",
        "composition": "fb1.sarf.clitic_pronoun",
        "unresolved": "fb1.fb1_calibration",
    }.get(kind, "fb1.fb1_calibration")
    primary_type = "domain_owner" if kind != "unresolved" else "producer_lane"
    secondary = [
        {"owner_id": "fa.typed_claim_contract", "owner_type": "contract"},
        {"owner_id": "fb1.calibration_packet", "owner_type": "scope"},
    ]
    if kind in {"function", "composition", "unresolved"}:
        secondary.insert(0, {"owner_id": "fb1.nahw", "owner_type": "secondary_domain_owner"})
    return {
        "primary": {"owner_id": primary_id, "owner_type": primary_type},
        "secondary": secondary,
    }


def _source_evidence(source: dict[str, str], structured: dict[str, Any]) -> dict[str, Any]:
    return {
        "structured_source_fact": structured,
        "source_addresses": [{"address": source["address"], "source_kind": source["source_kind"]}],
    }


def _guards(*, abstained: bool = False) -> list[dict[str, str]]:
    suffix = "abstained" if abstained else "passed"
    return [
        {"guard_id": "fb1.closed_class_function_word", "reason": "closed-class root guard " + suffix},
        {"guard_id": "fb1.surface_byte_exact", "reason": "written-span reconstruction " + suffix},
        {"guard_id": "fb1.idgham_boundary_A_to_D", "reason": "idgham boundary discipline " + suffix},
        {"guard_id": "fb1.protective_nun_typed", "reason": "protective-nun typing guard " + suffix},
        {"guard_id": "fb1.no_gloss_or_morphline_inference", "reason": "source fields restricted to typed structure"},
    ]


def _fact_id(fact: dict[str, Any]) -> str:
    identity = copy.deepcopy(fact)
    identity.pop("fact_id", None)
    return _hash(identity)


def _base_fact(
    *,
    fact_type: str,
    fact_value: dict[str, Any],
    spans: list[dict[str, Any]],
    ownership_kind: str,
    source: dict[str, str],
    evidence_status: str,
    confidence: str,
    evidence_mode: str,
    evidence_ids: list[str],
    evidence_summary: str,
    structured_source_fact: dict[str, Any],
    certification_status: str,
    certification_reason: str,
    dependencies: dict[str, Any],
    guards: list[dict[str, str]],
    defeaters: list[dict[str, Any]],
    blockers: list[dict[str, str]],
    projection_id: str,
    dependent_fact_ids: list[str],
) -> dict[str, Any]:
    fact = {
        "fact_id": "",
        "fact_type": fact_type,
        "fact_value": fact_value,
        "surface_spans": spans,
        "ownership": _ownership(ownership_kind),
        "source": {"source_id": source["source_id"], "source_kind": source["source_kind"]},
        "source_address": {"address": source["address"], "source_kind": source["source_kind"]},
        "certification": {"status": certification_status, "reason": certification_reason},
        "evidence": {
            "status": evidence_status,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
            "summary": evidence_summary,
        },
        "evidence_mode": evidence_mode,
        "source_evidence": _source_evidence(source, structured_source_fact),
        "derivation_chain": [],
        "dependencies": dependencies,
        "contradiction_records": [],
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "rule_projector": {"rule_id": RULE_ID, "projector_id": PROJECTOR_ID, "version": PRODUCER_VERSION},
        "guards": guards,
        "defeaters": defeaters,
        "unresolved_blockers": blockers,
        "dependent_fact_ids": dependent_fact_ids,
        "dependent_projection_ids": [projection_id],
    }
    fact["fact_id"] = _fact_id(fact)
    return fact


def _projection(projection_id: str, status: str) -> dict[str, Any]:
    return {
        "projection_id": projection_id,
        "status": status,
        "unresolved_status": None if status == "candidate" else status,
        "learner_visible": False,
        "materialization_target": {
            "artifact": _PROJECTION_ARTIFACT,
            "field": "facts" if status == "candidate" else "unresolved_queue",
            "public_materialization_allowed": False,
            "live_mutation_allowed": False,
        },
        "claim": None,
    }


def _unresolved_status(reasons: list[str]) -> str:
    if any(reason in {"closed_class_root_claim", "protective_nun_particle_misclassification", "family_mismatch"} for reason in reasons):
        return "blocked"
    return "source_gap"


def _unresolved_record(
    row: dict[str, Any],
    occurrence: dict[str, Any],
    source: dict[str, str],
    reasons: list[str],
    route: str,
    *,
    reconstruction: Optional[dict[str, Any]] = None,
    segments: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    loc = occurrence["quran_loc"]
    projection_id = "fb1:projection:" + loc
    status = _unresolved_status(reasons)
    full_span = {
        "span_id": "span:unresolved:surface",
        "start": 0,
        "end": len(occurrence["surface"]),
        "surface": occurrence["surface"],
        "role": "unresolved_surface",
    }
    safe_segments = [_minimal_segment(item) for item in (segments or [])]
    fact_value: dict[str, Any] = {
        "typed_kind": "fb1.unresolved_clitic_pronoun_composition",
        "occurrence": {
            "quran_loc": occurrence["quran_loc"],
            "wbw_loc": occurrence["wbw_loc"],
            "surface": occurrence["surface"],
        },
        "status": status,
        "reason_codes": reasons,
        "route": route,
        "source_segment_snapshot": safe_segments,
        "reconstruction_proof": reconstruction or {"byte_exact": False},
    }
    idgham_reason = next((reason for reason in reasons if reason.startswith("idgham_")), None)
    if idgham_reason:
        fact_value["boundary_class"] = idgham_reason.removeprefix("idgham_")
    blockers = [{"blocker_id": "fb1." + reason, "reason": reason} for reason in reasons]
    defeaters = [
        {"defeater_id": "fb1." + reason, "reason": "projection abstained: " + reason, "fact_ids": []}
        for reason in reasons
    ]
    fact = _base_fact(
        fact_type="unresolved_clitic_composition",
        fact_value=fact_value,
        spans=[full_span],
        ownership_kind="unresolved",
        source=source,
        evidence_status="blocked",
        confidence="unknown",
        evidence_mode="unresolved",
        evidence_ids=["fb1:unresolved:" + loc],
        evidence_summary="typed source gap; no linguistic claim emitted",
        structured_source_fact={
            "source_row_hash": _source_row_hash(row),
            "surface": occurrence["surface"],
            "segments": safe_segments,
            "reason_codes": reasons,
        },
        certification_status="blocked" if status == "blocked" else "pending",
        certification_reason="unresolved blocker; no certification transition",
        dependencies={
            "fact_ids": [],
            "source_addresses": [{"address": source["address"], "source_kind": source["source_kind"]}],
        },
        guards=_guards(abstained=True),
        defeaters=defeaters,
        blockers=blockers,
        projection_id=projection_id,
        dependent_fact_ids=[],
    )
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "contract_id": "fa:fb1:" + loc,
        "record_type": "unresolved_projection",
        "canonical_occurrence": occurrence,
        "facts": [fact],
        "projection": _projection(projection_id, status),
    }
    _validate_output(record)
    return record


def _validate_output(record: dict[str, Any]) -> None:
    errors = tcc.validate_contract_record(record)
    if errors:
        raise ProducerError("F-A output validation failed: " + "; ".join(errors))


def _component_kind(segment: dict[str, Any]) -> tuple[str, str]:
    role = segment["role"]
    klass = str(segment.get("class", ""))
    if role == "protective_nun" or klass == "qg-protective-nun" or segment.get("typed_kind") == "sarf.protective_nun":
        return "protective_nun", "protective"
    if _is_pronoun_segment(segment):
        return "clitic_component", "clitic"
    if _is_function_segment(segment):
        return "function_component", "function"
    return "host_component", "host"


def produce_record(row: dict[str, Any]) -> dict[str, Any]:
    """Produce one governed candidate or unresolved record without mutating row."""

    source_row = copy.deepcopy(row)
    try:
        occurrence = _occurrence(source_row)
        source = _source_ref(source_row, occurrence["quran_loc"])
    except ProducerError:
        # The F-A schema itself needs a canonical occurrence. Inputs without one
        # cannot safely become a governed record, so callers must repair the
        # source envelope before retrying.
        raise

    family = source_row.get("morphology_family", source_row.get("family"))
    if family not in (None, "clitic_pronoun_compositions"):
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            ["family_mismatch"],
            "fb1.family_scope_review",
        )

    verdict = source_row.get("_fb1_verdict", source_row.get("v575_verdict"))
    if verdict not in (None, "verified"):
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            ["input_verdict_not_verified"],
            "fb1.input_verdict_review",
        )

    try:
        segments = _sorted_segments(source_row)
    except ProducerError as exc:
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            ["missing_structured_segments"],
            "fb1.source_segmentation_review",
            reconstruction={"byte_exact": False, "error_code": str(exc)},
        )

    try:
        spans, reconstruction = _reconstruct(occurrence["surface"], segments)
    except ProducerError as exc:
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            ["surface_reconstruction"],
            "fb1.surface_boundary_review",
            reconstruction={"byte_exact": False, "error_code": str(exc)},
            segments=segments,
        )

    if _function_ambiguity(segments, occurrence["surface"]):
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            ["function_ambiguity"],
            "nahw.function_word_review",
            reconstruction=reconstruction,
            segments=segments,
        )

    if _is_closed_class_row(source_row, segments) and _root_claim_present(source_row, segments):
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            ["closed_class_root_claim"],
            "nahw.function_word_review",
            reconstruction=reconstruction,
            segments=segments,
        )

    idgham, idgham_failure = _idgham_boundary(source_row, segments)
    if idgham_failure:
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            [idgham_failure[0]],
            idgham_failure[1],
            reconstruction=reconstruction,
            segments=segments,
        )

    protective, protective_failure = _protective_nun_info(source_row, segments)
    if protective_failure:
        return _unresolved_record(
            source_row,
            occurrence,
            source,
            [protective_failure[0]],
            protective_failure[1],
            reconstruction=reconstruction,
            segments=segments,
        )

    projection_id = "fb1:projection:" + occurrence["quran_loc"]
    source_hash = _source_row_hash(source_row)
    candidate_defeater = [
        {
            "defeater_id": "fb1.candidate_only",
            "reason": "calibration candidate requires independent owner review",
            "fact_ids": [],
        }
    ]
    facts: list[dict[str, Any]] = []
    span_by_index = {segment["segment_index"]: spans[i] for i, segment in enumerate(segments)}
    fact_by_index: dict[int, dict[str, Any]] = {}
    for segment in segments:
        fact_type, ownership_kind = _component_kind(segment)
        typed_kind = segment.get("typed_kind")
        if fact_type == "protective_nun":
            typed_kind = "sarf.protective_nun"
        elif typed_kind is None:
            typed_kind = {
                "clitic": "sarf.clitic_component",
                "function": "nahw.function_component",
                "host": "sarf.host_component",
            }[ownership_kind]
        value: dict[str, Any] = {
            "typed_kind": typed_kind,
            "occurrence": {
                "quran_loc": occurrence["quran_loc"],
                "wbw_loc": occurrence["wbw_loc"],
                "surface": occurrence["surface"],
            },
            "segment_index": segment["segment_index"],
            "role": segment["role"],
            "class": segment["class"],
            "surface": segment["surface"],
            "reconstruction_proof": reconstruction,
        }
        if isinstance(segment.get("label"), str) and segment["label"]:
            value["label"] = segment["label"]
        fact = _base_fact(
            fact_type=fact_type,
            fact_value=value,
            spans=[span_by_index[segment["segment_index"]]],
            ownership_kind=ownership_kind,
            source=source,
            evidence_status="source_addressed_candidate",
            confidence="medium",
            evidence_mode="direct_source_attestation",
            evidence_ids=["fb1:source:%s:segment:%d" % (occurrence["quran_loc"], segment["segment_index"])],
            evidence_summary="typed source segment with exact written span",
            structured_source_fact={
                "source_row_hash": source_hash,
                "segment": _minimal_segment(segment),
            },
            certification_status="candidate",
            certification_reason="calibration candidate; no certification transition",
            dependencies={
                "fact_ids": [],
                "source_addresses": [{"address": source["address"], "source_kind": source["source_kind"]}],
            },
            guards=_guards(),
            defeaters=copy.deepcopy(candidate_defeater),
            blockers=[],
            projection_id=projection_id,
            dependent_fact_ids=[],
        )
        facts.append(fact)
        fact_by_index[segment["segment_index"]] = fact

    additional_fact_ids: list[str] = []
    if idgham is not None:
        boundary_indices = [segments[0]["segment_index"], segments[1]["segment_index"]] if len(segments) > 1 else [segments[0]["segment_index"]]
        idgham_value = {
            "typed_kind": "sarf.idgham_boundary",
            "occurrence": {
                "quran_loc": occurrence["quran_loc"],
                "wbw_loc": occurrence["wbw_loc"],
                "surface": occurrence["surface"],
            },
            "boundary_class": idgham["boundary_class"],
            "byte_clean": True,
            "boundary_segment_indexes": boundary_indices,
            "reconstruction_proof": reconstruction,
        }
        idgham_fact = _base_fact(
            fact_type="idgham_boundary",
            fact_value=idgham_value,
            spans=[span_by_index[index] for index in boundary_indices],
            ownership_kind="composition",
            source=source,
            evidence_status="source_addressed_candidate",
            confidence="low",
            evidence_mode="direct_source_attestation",
            evidence_ids=["fb1:idgham:%s" % occurrence["quran_loc"]],
            evidence_summary="explicit A/B idgham boundary attestation with byte-clean spans",
            structured_source_fact={
                "source_row_hash": source_hash,
                "idgham_boundary": idgham,
            },
            certification_status="candidate",
            certification_reason="calibration candidate; idgham owner review remains required",
            dependencies={
                "fact_ids": [],
                "source_addresses": [{"address": source["address"], "source_kind": source["source_kind"]}],
            },
            guards=_guards(),
            defeaters=copy.deepcopy(candidate_defeater),
            blockers=[],
            projection_id=projection_id,
            dependent_fact_ids=[],
        )
        facts.append(idgham_fact)
        additional_fact_ids.append(idgham_fact["fact_id"])

    if protective is not None and protective["segment_index"] not in fact_by_index:
        # Explicit metadata may carry a clean protective-nun span in addition to
        # a broader object-pronoun segment. It is still a typed sarf fact, never
        # a particle fact; the span must be found byte-exactly in the occurrence.
        start = occurrence["surface"].find(protective["surface"])
        if start < 0:
            return _unresolved_record(
                source_row,
                occurrence,
                source,
                ["protective_nun_surface_not_found"],
                "sarf.protective_nun_review",
                reconstruction=reconstruction,
                segments=segments,
            )
        protective_span = {
            "span_id": "span:%d:protective_nun" % protective["segment_index"],
            "start": start,
            "end": start + len(protective["surface"]),
            "surface": protective["surface"],
            "role": "protective_nun",
        }
        protective_fact = _base_fact(
            fact_type="protective_nun",
            fact_value={
                "typed_kind": "sarf.protective_nun",
                "occurrence": {
                    "quran_loc": occurrence["quran_loc"],
                    "wbw_loc": occurrence["wbw_loc"],
                    "surface": occurrence["surface"],
                },
                "segment_index": protective["segment_index"],
                "role": "protective_nun",
                "class": "qg-protective-nun",
                "surface": protective["surface"],
                "reconstruction_proof": reconstruction,
            },
            spans=[protective_span],
            ownership_kind="protective",
            source=source,
            evidence_status="source_addressed_candidate",
            confidence="medium",
            evidence_mode="direct_source_attestation",
            evidence_ids=["fb1:protective-nun:%s" % occurrence["quran_loc"]],
            evidence_summary="explicit structured protective-nun source span",
            structured_source_fact={"source_row_hash": source_hash, "protective_nun": protective},
            certification_status="candidate",
            certification_reason="calibration candidate; no certification transition",
            dependencies={
                "fact_ids": [],
                "source_addresses": [{"address": source["address"], "source_kind": source["source_kind"]}],
            },
            guards=_guards(),
            defeaters=copy.deepcopy(candidate_defeater),
            blockers=[],
            projection_id=projection_id,
            dependent_fact_ids=[],
        )
        facts.append(protective_fact)
        additional_fact_ids.append(protective_fact["fact_id"])

    component_facts = [fact for fact in facts if fact["fact_type"] in {"clitic_component", "function_component", "host_component", "protective_nun"}]
    composition_dependencies = [fact["fact_id"] for fact in component_facts] + additional_fact_ids
    composition = _base_fact(
        fact_type="clitic_composition",
        fact_value={
            "typed_kind": "sarf.clitic_pronoun_composition",
            "occurrence": {
                "quran_loc": occurrence["quran_loc"],
                "wbw_loc": occurrence["wbw_loc"],
                "surface": occurrence["surface"],
            },
            "component_fact_ids": [fact["fact_id"] for fact in component_facts],
            "component_roles": [segment["role"] for segment in segments],
            "reconstruction_proof": reconstruction,
            "boundary_policy": "idgham A/B only; C/D unresolved",
        },
        spans=spans,
        ownership_kind="composition",
        source=source,
        evidence_status="source_addressed_candidate",
        confidence="medium",
        evidence_mode="direct_source_attestation",
        evidence_ids=["fb1:composition:%s" % occurrence["quran_loc"]],
        evidence_summary="source-addressed composition reconstructed from typed segments",
        structured_source_fact={
            "source_row_hash": source_hash,
            "segments": [_minimal_segment(segment) for segment in segments],
            "reconstruction_proof": reconstruction,
        },
        certification_status="candidate",
        certification_reason="calibration candidate; no certification transition",
        dependencies={
            "fact_ids": composition_dependencies,
            "source_addresses": [{"address": source["address"], "source_kind": source["source_kind"]}],
        },
        guards=_guards(),
        defeaters=copy.deepcopy(candidate_defeater),
        blockers=[],
        projection_id=projection_id,
        dependent_fact_ids=composition_dependencies,
    )
    facts.append(composition)
    record = {
        "schema": SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "contract_id": "fa:fb1:" + occurrence["quran_loc"],
        "record_type": "projection_input",
        "canonical_occurrence": occurrence,
        "facts": facts,
        "projection": _projection(projection_id, "candidate"),
    }
    _validate_output(record)
    return record


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProducerError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ProducerError(f"{path}:{line_number}: expected an object")
        rows.append(value)
    return rows


def _merge_external_rows(strat_path: Path, verdicts_path: Path, corpus_path: Path) -> list[dict[str, Any]]:
    strat_rows = [row for row in _load_jsonl(strat_path) if row.get("morphology_family", row.get("family")) == "clitic_pronoun_compositions"]
    verdicts = {str(row.get("loc")): row for row in _load_jsonl(verdicts_path)}
    corpus = {str(row.get("loc")): row for row in _load_jsonl(corpus_path)}
    merged: list[dict[str, Any]] = []
    for strat in strat_rows:
        loc = str(strat.get("loc", ""))
        verdict = verdicts.get(loc)
        source = corpus.get(loc)
        if source is None:
            merged.append(
                {
                    "loc": loc,
                    "quran_loc": "quran:" + loc,
                    "wbw_loc": "wbw:" + loc,
                    "surface": strat.get("surface", ""),
                    "morphology_family": "clitic_pronoun_compositions",
                    "_fb1_source_id": corpus_path.name,
                    "_fb1_source_address": "corpus:%s#loc=%s" % (corpus_path.name, loc),
                    "_fb1_verdict": (verdict or {}).get("verdict"),
                }
            )
            continue
        row = copy.deepcopy(source)
        row["morphology_family"] = "clitic_pronoun_compositions"
        row["quran_loc"] = "quran:" + loc
        row["wbw_loc"] = "wbw:" + loc
        row["_fb1_source_id"] = corpus_path.name
        row["_fb1_source_address"] = "corpus:%s#loc=%s" % (corpus_path.name, loc)
        row["_fb1_verdict"] = (verdict or {}).get("verdict")
        row["_fb1_strat_tags"] = _selection_tags(strat, row)
        merged.append(row)
    return merged


def _selection_tags(strat: dict[str, Any], row: dict[str, Any]) -> list[str]:
    roles = {str(item.get("role", "")) for item in row.get("segments", []) if isinstance(item, dict)}
    roles.update(str(item.get("role", "")) for item in strat.get("clitic_parts", []) if isinstance(item, dict))
    classes = {str(item.get("class", "")) for item in row.get("segments", []) if isinstance(item, dict)}
    tags: list[str] = []
    if any("object" in role for role in roles) or "qg-object-pronoun" in classes:
        tags.append("attached_object_pronoun")
    if any("possessive" in role for role in roles) or "qg-possessive-pronoun" in classes:
        tags.append("attached_possessive_pronoun")
    if any("subject" in role or "subject_marker" in role for role in roles) or "qg-subject-pronoun" in classes:
        tags.append("attached_subject_pronoun")
    if len(row.get("segments", [])) >= 2 and any(_is_function_segment(item) for item in row.get("segments", [])):
        tags.append("proclitic_combination")
    if any(item.get("role") == "protective_nun" or item.get("typed_kind") == "sarf.protective_nun" for item in row.get("segments", [])):
        tags.append("protective_nun_attested")
    elif any(
        "object" in str(item.get("role", "")) and _bare_arabic(str(item.get("surface", ""))) in {"ني", "نى", "نِ"}
        for item in row.get("segments", [])
    ):
        tags.append("protective_nun_context")
    for index, segment in enumerate(row.get("segments", [])[1:], 1):
        if (
            row.get("segments", [])[index - 1].get("role") == "definite_article"
            and _contains_shadda_at_boundary(str(segment.get("surface", "")))
        ):
            tags.append("boundary_ambiguous_idgham")
            break
    if _function_ambiguity(row.get("segments", []), str(row.get("surface", ""))):
        tags.append("function_word_ambiguity")
    return sorted(set(tags))


def select_calibration_sample(rows: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    if size < 40:
        raise ProducerError("calibration sample size must be at least 40")
    enriched = [copy.deepcopy(row) for row in rows]
    for row in enriched:
        row.setdefault("_fb1_strat_tags", _selection_tags(row, row))
    selected: list[dict[str, Any]] = []
    selected_locs: set[str] = set()
    required = [
        "attached_object_pronoun",
        "attached_possessive_pronoun",
        "attached_subject_pronoun",
        "proclitic_combination",
        "protective_nun_context",
        "boundary_ambiguous_idgham",
    ]
    for tag in required:
        for row in sorted(enriched, key=lambda item: _loc(item)):
            if _loc(row) not in selected_locs and tag in row.get("_fb1_strat_tags", []):
                selected.append(row)
                selected_locs.add(_loc(row))
                break
    for row in sorted(enriched, key=lambda item: _loc(item)):
        if len(selected) >= size:
            break
        if _loc(row) not in selected_locs:
            selected.append(row)
            selected_locs.add(_loc(row))
    if len(selected) < 40:
        raise ProducerError("family input did not yield the required 40-row calibration sample")
    return selected[:size]


def _fixture_row_for_commit(row: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in ("loc", "quran_loc", "wbw_loc", "surface", "entry_id", "card_id", "morphology_family", "family", "source_id", "source_kind", "source_address", "idgham_boundary", "protective_nun", "calibration_tags"):
        if key in row and row[key] not in (None, "", []):
            output[key] = row[key]
    output.setdefault("morphology_family", "clitic_pronoun_compositions")
    output["segments"] = [_minimal_segment(item) for item in row.get("segments", []) if isinstance(item, dict)]
    output.setdefault("source_id", "rh_live_01_beta_whitelist.jsonl")
    output.setdefault("source_kind", "corpus_record")
    output.setdefault("source_address", "corpus:rh_live_01_beta_whitelist.jsonl#loc=" + str(row.get("loc")))
    output["calibration_tags"] = list(row.get("_fb1_strat_tags") or row.get("calibration_tags") or [])
    return output


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _fixture_dir() -> Path:
    return ROOT / "qamus" / "examples" / "fb1-clitic-pronoun"


def run_self_test(fixtures: Optional[Path] = None) -> int:
    directory = fixtures or _fixture_dir()
    positives = _load_jsonl(directory / "positive.jsonl")
    negatives = _load_jsonl(directory / "negative.jsonl")
    errors: list[str] = []
    if len(positives) < 6:
        errors.append("positive fixture count is below six")
    if len(negatives) < 6:
        errors.append("negative fixture count is below six")
    positive_records: list[dict[str, Any]] = []
    for index, fixture in enumerate(positives, 1):
        try:
            record = produce_record(fixture)
        except Exception as exc:  # pragma: no cover - self-test reports the exact fixture
            errors.append(f"positive[{index}] raised {type(exc).__name__}: {exc}")
            continue
        positive_records.append(record)
        if record["projection"]["status"] != "candidate":
            errors.append(f"positive[{index}] did not produce candidate")
    for index, fixture in enumerate(negatives, 1):
        try:
            record = produce_record(fixture)
        except Exception as exc:  # pragma: no cover - self-test reports the exact fixture
            errors.append(f"negative[{index}] raised {type(exc).__name__}: {exc}")
            continue
        if record["projection"]["status"] == "candidate":
            errors.append(f"negative[{index}] falsely projected candidate")
        if not any(fact.get("unresolved_blockers") for fact in record["facts"]):
            errors.append(f"negative[{index}] lacks typed unresolved blocker")
    if positive_records and not any(
        fact["fact_type"] == "protective_nun" and fact["fact_value"].get("typed_kind") == "sarf.protective_nun"
        for record in positive_records
        for fact in record["facts"]
    ):
        errors.append("positive fixtures lack an explicit sarf.protective_nun fact")
    if errors:
        for error in errors:
            print("FAIL — " + error)
        return 1
    print(
        "FB1 CLITIC PRONOUN PRODUCER SELF-TEST PASS "
        f"({len(positives)} positive, {len(negatives)} adversarial negatives)"
    )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fixtures", type=Path, help="fixture directory for --self-test")
    parser.add_argument("--input", type=Path, help="committed or caller-supplied merged JSONL rows")
    parser.add_argument("--strat", type=Path, help="external STRAT JSONL input")
    parser.add_argument("--verdicts", type=Path, help="external v575 verdict JSONL input")
    parser.add_argument("--corpus", type=Path, help="external corpus JSONL input")
    parser.add_argument("--sample-size", type=int, default=48)
    parser.add_argument("--write-sample-input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_test(args.fixtures)
    if args.input and any(value is not None for value in (args.strat, args.verdicts, args.corpus)):
        parser.error("--input cannot be combined with --strat/--verdicts/--corpus")
    if bool(args.strat) != bool(args.verdicts) or bool(args.strat) != bool(args.corpus):
        parser.error("--strat, --verdicts, and --corpus must be supplied together")
    if not args.input and not args.strat:
        parser.error("one of --input or the external --strat/--verdicts/--corpus set is required")
    if args.strat:
        rows = select_calibration_sample(_merge_external_rows(args.strat, args.verdicts, args.corpus), args.sample_size)
        if args.write_sample_input:
            write_jsonl(args.write_sample_input, [_fixture_row_for_commit(row) for row in rows])
    else:
        rows = _load_jsonl(args.input)
    records = [produce_record(row) for row in rows]
    if args.output:
        write_jsonl(args.output, records)
    else:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    candidates = sum(record["projection"]["status"] == "candidate" for record in records)
    unresolved = len(records) - candidates
    print(f"FB1 calibration packet: {len(records)} rows, {candidates} candidate, {unresolved} unresolved", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
