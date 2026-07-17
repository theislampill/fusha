#!/usr/bin/env python3
"""FC1 naḥw dependency producer and bounded calibration packet builder.

The producer owns sentence-level dependency evidence only.  It never owns a
root, lemma, form, voice, or any other morphological assertion, and its public
payload preserves the canonical surface byte-for-byte (Unicode code-point for
code-point).  The calibration command accepts external corpus paths explicitly
and writes only repo-shaped F-A contracts and summary artifacts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.typed_claim_contract import (  # noqa: E402
    EVIDENCE_MODES,
    learner_statement_for,
    validate_contract_record,
)


SCHEMA = "qamus.typed_claim_contract.v1"
CONTRACT_VERSION = "1.0.0"
PRODUCER_ID = "tools.fc_nahw_producer"
PROJECTOR_ID = "fc.nahw_dependency_projection.v1"
VERSION = "1.0.0"
FACT_TYPE = "nahw_dependency"
UNRESOLVED_STATUS = "syntax_pending"
LOC_RE = re.compile(r"^[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}$")
QURAN_LOC_RE = re.compile(r"^quran:[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}$")
WBW_LOC_RE = re.compile(r"^wbw:[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}$")

ROLE_PRIORITY = {
    "subject": 0,
    "object": 1,
    "preposition_to_governed": 2,
    "case": 3,
    "mood": 4,
    "pronoun_attachment": 5,
    "agreement": 6,
    "other": 7,
}

# These keys are morphology-owned.  A recursive check keeps a future input
# field from smuggling sarf into a naḥw fact under a nested object.
MORPHOLOGY_KEYS = {
    "root",
    "lemma",
    "pos",
    "part_of_speech",
    "form",
    "derived_form",
    "voice",
    "morphology",
    "sarf",
    "sarf_note",
    "pattern",
    "morphline",
}

NAHW_FACT_KEYS = {
    "role",
    "governor",
    "governor_loc",
    "governed_occurrence",
    "relationship",
    "relationship_evidence",
    "case_or_mood",
    "case_effect",
    "ending",
    "attachment",
    "function",
    "referent",
}

TERMINAL_MARKS = {
    "َ",
    "ً",
    "ُ",
    "ٌ",
    "ِ",
    "ٍ",
    "ْ",
    "ّ",
    "ٓ",
    "ۡ",
    "ۭ",
    "ۥ",
    "ۦ",
    "۟",
    "۠",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def surface_is_preserved(source_surface: str, projected_surface: str) -> bool:
    """Return true only when the projected surface is exactly the source surface."""

    return isinstance(source_surface, str) and isinstance(projected_surface, str) and source_surface == projected_surface


def _as_loc(value: Any) -> str:
    text = str(value or "")
    if text.startswith("quran:"):
        return text[6:]
    if text.startswith("wbw:"):
        return text[4:]
    return text


def _quran_address(loc: str) -> str:
    return loc if loc.startswith("quran:") else f"quran:{loc}"


def _wbw_address(loc: str) -> str:
    return loc if loc.startswith("wbw:") else f"wbw:{loc}"


def _require_loc(value: Any, field: str) -> str:
    loc = _as_loc(value)
    if not LOC_RE.fullmatch(loc):
        raise ValueError(f"{field} must be a bare Quran location, got {value!r}")
    return loc


def _source_surface(row: dict[str, Any]) -> str:
    surface = row.get("surface")
    if not isinstance(surface, str) or not surface:
        raise ValueError("canonical occurrence surface is required")
    return surface


def _occurrence(value: Any, *, field: str, default_loc: str | None = None, default_surface: str | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an exact occurrence object")
    occurrence_id = value.get("occurrence_id")
    if not isinstance(occurrence_id, str) or not QURAN_LOC_RE.fullmatch(occurrence_id):
        raise ValueError(f"{field}.occurrence_id must be quran:<surah>:<ayah>:<word>")
    surface = value.get("surface")
    if not isinstance(surface, str) or not surface:
        raise ValueError(f"{field}.surface is required")
    result = {
        "occurrence_id": occurrence_id,
        "surface": surface,
    }
    if "span_id" in value:
        result["span_id"] = value["span_id"]
    if "span_ids" in value:
        result["span_ids"] = list(value["span_ids"] or [])
    if default_loc is not None and occurrence_id != _quran_address(default_loc):
        # The caller may use a cross-occurrence governor, so this is an
        # informational branch rather than a rejection.  Exactness is checked
        # by the fact validator against the canonical occurrence where needed.
        pass
    local_component = isinstance(value.get("span_id"), str) or bool(value.get("span_ids"))
    if default_surface is not None and occurrence_id == _quran_address(default_loc or "") and not local_component and surface != default_surface:
        raise ValueError(f"{field}.surface does not match the canonical occurrence")
    return result


def _validated_spans(row: dict[str, Any], surface: str) -> list[dict[str, Any]]:
    supplied = row.get("surface_spans")
    if not supplied:
        return [{
            "span_id": "token",
            "start": 0,
            "end": len(surface),
            "surface": surface,
            "role": "governed_token",
        }]
    if not isinstance(supplied, list):
        raise ValueError("surface_spans must be a list")
    spans: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, span in enumerate(supplied):
        if not isinstance(span, dict):
            raise ValueError(f"surface_spans[{index}] must be an object")
        span_id = span.get("span_id")
        start = span.get("start")
        end = span.get("end")
        role = span.get("role")
        if not isinstance(span_id, str) or not span_id or span_id in seen:
            raise ValueError(f"surface_spans[{index}] requires a unique span_id")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            raise ValueError(f"surface_spans[{index}] start/end must be integers")
        if start < 0 or end <= start or end > len(surface):
            raise ValueError(f"surface_spans[{index}] is outside the canonical surface")
        if surface[start:end] != span.get("surface"):
            raise ValueError(f"surface_spans[{index}] does not reproduce exact source text")
        if not isinstance(role, str) or not re.fullmatch(r"^[a-z][a-z0-9_:-]*$", role):
            raise ValueError(f"surface_spans[{index}].role is invalid")
        seen.add(span_id)
        spans.append({
            "span_id": span_id,
            "start": start,
            "end": end,
            "surface": span["surface"],
            "role": role,
        })
    return spans


def _contains_morphology_key(value: Any, path: str = "fact_value") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in MORPHOLOGY_KEYS:
                return f"{path}.{key}"
            found = _contains_morphology_key(child, f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _contains_morphology_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _status_reason(value: Any, field: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{field} must be an object"]
    status = value.get("status")
    if status not in {"visible", "estimated", "not_applicable", "observed", "unresolved"}:
        errors.append(f"{field}.status must be visible/estimated/not_applicable/observed/unresolved")
    if status in {"estimated", "not_applicable", "unresolved"} and not _nonempty_text(value.get("reason")):
        errors.append(f"{field}.{status} requires a non-empty reason")
    return errors


def validate_dependency_fact(fact: dict[str, Any]) -> list[str]:
    """Return semantic errors for one positive FC1 dependency fact.

    F-A validates the closed envelope.  This function adds the producer-owned
    naḥw invariants that are intentionally not part of the shared schema.
    """

    errors: list[str] = []
    if not isinstance(fact, dict):
        return ["dependency fact must be an object"]
    if fact.get("fact_type") != FACT_TYPE:
        errors.append("fact_type must be nahw_dependency")
    value = fact.get("fact_value")
    if not isinstance(value, dict):
        return errors + ["fact_value must be an object"]
    morphology_path = _contains_morphology_key(value)
    if morphology_path:
        errors.append(f"naḥw fact leaks morphology-owned field at {morphology_path}")

    role = value.get("role")
    if not _nonempty_text(role):
        errors.append("a positive naḥw fact requires an explicit role")

    governor = value.get("governor")
    if not isinstance(governor, dict):
        errors.append("a naḥw role requires an exact governor occurrence")
    else:
        if not QURAN_LOC_RE.fullmatch(str(governor.get("occurrence_id", ""))):
            errors.append("governor occurrence_id must be an exact quran address")
        if not _nonempty_text(governor.get("surface")):
            errors.append("governor occurrence must carry its exact surface")

    governed = value.get("governed_occurrence")
    if not isinstance(governed, dict):
        errors.append("a naḥw role requires an exact governed occurrence")
    else:
        if not QURAN_LOC_RE.fullmatch(str(governed.get("occurrence_id", ""))):
            errors.append("governed occurrence_id must be an exact quran address")
        if not _nonempty_text(governed.get("surface")):
            errors.append("governed occurrence must carry its exact surface")

    if not _nonempty_text(value.get("relationship")):
        errors.append("a naḥw role requires a named relationship")
    relationship_evidence = value.get("relationship_evidence")
    if not isinstance(relationship_evidence, dict):
        errors.append("a naḥw role requires relationship evidence")
    else:
        if not _nonempty_text(relationship_evidence.get("source_field")):
            errors.append("relationship evidence requires its source field")
        if not _nonempty_text(relationship_evidence.get("summary")):
            errors.append("relationship evidence requires a summary")

    if role == "pronoun_attachment":
        referent = value.get("referent")
        if not isinstance(referent, dict):
            errors.append("pronoun attachment requires a typed referent field or an explicit unresolved referent")
        elif referent.get("status") not in {"observed", "candidate", "unresolved"}:
            errors.append("pronoun referent status must remain observed/candidate/unresolved")
        elif referent.get("status") == "unresolved" and not _nonempty_text(referent.get("reason")):
            errors.append("unresolved pronoun referent requires a reason")

    case_or_mood = value.get("case_or_mood")
    if not isinstance(case_or_mood, dict):
        errors.append("case_or_mood is required, including an explicit not_applicable state")
    else:
        applicability = case_or_mood.get("applicability")
        if applicability not in {"case", "mood", "case_and_mood", "not_applicable"}:
            errors.append("case_or_mood.applicability is invalid")
        if applicability != "not_applicable" and not _nonempty_text(case_or_mood.get("value")):
            errors.append("applicable case_or_mood requires a value")
        errors.extend(_status_reason(case_or_mood, "case_or_mood"))
        if applicability in {"case", "mood", "case_and_mood"} and not isinstance(governor, dict):
            errors.append("case/mood claims cannot survive without an exact governor")

    ending = value.get("ending")
    if not isinstance(ending, dict):
        errors.append("ending is required, including an explicit not_applicable state")
    else:
        errors.extend(_status_reason(ending, "ending"))
        if ending.get("status") == "visible" and not _nonempty_text(ending.get("value")):
            errors.append("visible ending requires the visible ending value")

    source_surface = value.get("source_surface")
    projected_surface = value.get("projected_surface")
    if not surface_is_preserved(source_surface, projected_surface):
        errors.append("naḥw projection must preserve the canonical lexical surface exactly")

    source = fact.get("source")
    source_address = fact.get("source_address")
    certification = fact.get("certification")
    evidence = fact.get("evidence")
    if not isinstance(source, dict) or not _nonempty_text(source.get("source_id")):
        errors.append("source and source_id are required")
    if not isinstance(source_address, dict) or not _nonempty_text(source_address.get("address")):
        errors.append("source_address is required")
    if not isinstance(certification, dict) or certification.get("status") not in {
        "candidate", "review_required", "certified", "pending", "blocked", "rejected"
    } or not _nonempty_text((certification or {}).get("reason")):
        errors.append("source certification status and reason are required")
    if not isinstance(evidence, dict) or evidence.get("status") not in {
        "unknown", "observed", "source_addressed_candidate", "two_vote", "certified", "blocked"
    }:
        errors.append("evidence status is required")
    if fact.get("evidence_mode") not in EVIDENCE_MODES - {"unresolved"}:
        errors.append("positive naḥw evidence_mode cannot be unresolved")
    if isinstance(ending, dict) and ending.get("status") == "estimated" and isinstance(certification, dict) and certification.get("status") == "certified":
        errors.append("estimated endings cannot be certified")
    return errors


def _source_details(input_row: dict[str, Any], source_record_id: str, loc: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str]:
    source_input = input_row.get("source") or {}
    if not isinstance(source_input, dict):
        raise ValueError("source must be an object")
    source_kind = source_input.get("source_kind", "corpus_record")
    if source_kind not in {"quran_token", "qamus_entry_field", "corpus_record", "construction", "review_artifact"}:
        raise ValueError(f"unsupported source kind {source_kind!r}")
    source_id = source_input.get("source_id") or source_record_id
    source = {"source_id": str(source_id), "source_kind": source_kind}
    source_address = {
        "address": _quran_address(loc) if source_kind == "quran_token" else str(source_id),
        "source_kind": source_kind,
    }
    certification = copy.deepcopy(input_row.get("certification") or {
        "status": "candidate",
        "reason": "source-addressed calibration evidence remains candidate-only",
    })
    evidence = copy.deepcopy(input_row.get("evidence") or {
        "status": "source_addressed_candidate",
        "confidence": "medium",
        "evidence_ids": [f"fc1:{loc}"],
        "summary": "source-addressed naḥw calibration evidence",
    })
    mode = input_row.get("evidence_mode", "direct_source_attestation")
    return source, source_address, certification, evidence, mode


def _source_addresses(input_row: dict[str, Any], loc: str, source_record_id: str, source_kind: str) -> list[dict[str, str]]:
    supplied = input_row.get("source_addresses")
    addresses: list[dict[str, str]] = []
    if isinstance(supplied, list):
        for address in supplied:
            if not isinstance(address, dict) or not _nonempty_text(address.get("address")):
                raise ValueError("source_addresses must contain exact address objects")
            kind = address.get("source_kind")
            if kind not in {"quran_token", "qamus_entry_field", "corpus_record", "construction", "review_artifact"}:
                raise ValueError(f"unsupported source address kind {kind!r}")
            addresses.append({"address": str(address["address"]), "source_kind": kind})
    if not addresses:
        addresses = [{
            "address": _quran_address(loc),
            "source_kind": "quran_token",
        }]
    # A source-addressed fact must always retain its canonical occurrence.
    canonical = {"address": _quran_address(loc), "source_kind": "quran_token"}
    if canonical not in addresses:
        addresses.insert(0, canonical)
    return addresses


def _projection_id(loc: str) -> str:
    return f"fc1.nahw.{loc.replace(':', '.')}.v1"


def _fact_id(fact_type: str, fact_value: dict[str, Any], spans: list[dict[str, Any]], source_address: dict[str, Any], mode: str) -> str:
    return "sha256:" + _sha256({
        "fact_type": fact_type,
        "fact_value": fact_value,
        "surface_spans": spans,
        "source_address": source_address,
        "evidence_mode": mode,
    })


def _copy_nahw_value(nahw_fact: dict[str, Any], *, source_surface: str, projected_surface: str) -> dict[str, Any]:
    forbidden = _contains_morphology_key(nahw_fact)
    if forbidden:
        raise ValueError(f"naḥw input contains morphology-owned field at {forbidden}")
    value: dict[str, Any] = {}
    for key in NAHW_FACT_KEYS:
        if key in nahw_fact:
            value[key] = copy.deepcopy(nahw_fact[key])
    value["source_surface"] = source_surface
    value["projected_surface"] = projected_surface
    return value


def _positive_fact_parts(input_row: dict[str, Any], source_record_id: str) -> tuple[str, dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str, list[dict[str, str]]]:
    loc = _require_loc(input_row.get("quran_loc") or input_row.get("loc"), "quran_loc")
    surface = _source_surface(input_row)
    projected_surface = input_row.get("projected_surface", surface)
    if not surface_is_preserved(surface, projected_surface):
        raise ValueError("projected_surface must equal the canonical source surface exactly")
    nahw_fact = input_row.get("nahw_fact")
    if not isinstance(nahw_fact, dict):
        raise ValueError("nahw_fact must be a typed object")
    value = _copy_nahw_value(nahw_fact, source_surface=surface, projected_surface=projected_surface)
    if not _nonempty_text(value.get("role")):
        raise ValueError("bare roles are invalid")
    governor = _occurrence(value.get("governor"), field="nahw_fact.governor", default_loc=loc, default_surface=surface)
    governed = _occurrence(value.get("governed_occurrence"), field="nahw_fact.governed_occurrence", default_loc=loc, default_surface=surface)
    value["governor"] = governor
    value["governed_occurrence"] = governed
    spans = _validated_spans(input_row, surface)
    source, source_address, certification, evidence, mode = _source_details(input_row, source_record_id, loc)
    if mode not in EVIDENCE_MODES - {"unresolved"}:
        raise ValueError(f"positive fact has unsupported evidence_mode {mode!r}")
    addresses = _source_addresses(input_row, loc, source_record_id, source["source_kind"])
    return loc, value, spans, source, source_address, certification, evidence, mode, addresses


def build_dependency_fact(input_row: dict[str, Any], *, source_record_id: str, projection_id: str | None = None) -> dict[str, Any]:
    """Build one strict positive F-A naḥw dependency fact."""

    loc, value, spans, source, source_address, certification, evidence, mode, addresses = _positive_fact_parts(
        input_row, source_record_id
    )
    projection_id = projection_id or _projection_id(loc)
    fact = {
        "fact_id": _fact_id(FACT_TYPE, value, spans, source_address, mode),
        "fact_type": FACT_TYPE,
        "fact_value": value,
        "surface_spans": spans,
        "ownership": {
            "primary": {"owner_id": "fc1-nahw-owner", "owner_type": "producer_candidate"},
            "secondary": [{"owner_id": PRODUCER_ID, "owner_type": "producer"}],
        },
        "source": source,
        "source_address": source_address,
        "certification": certification,
        "evidence": evidence,
        "evidence_mode": mode,
        "source_evidence": {
            "structured_source_fact": {
                "source_record_id": str(source_record_id),
                "source_fields": [
                    "nahw_fact.role",
                    "nahw_fact.governor",
                    "nahw_fact.governed_occurrence",
                    "nahw_fact.relationship_evidence",
                ],
            },
            "source_addresses": addresses,
        },
        "derivation_chain": [],
        "dependencies": {"fact_ids": [], "source_addresses": addresses},
        "contradiction_records": [],
        "producer": {"id": PRODUCER_ID, "version": VERSION},
        "rule_projector": {
            "rule_id": f"fc1.nahw.{str(value['role']).replace('_', '-')}",
            "projector_id": PROJECTOR_ID,
            "version": VERSION,
        },
        "guards": [
            {
                "guard_id": "fc1.calibration_only",
                "reason": "This candidate is calibration-only and cannot authorize a public or live mutation.",
            },
            {
                "guard_id": "fc1.no_lexical_repaint",
                "reason": "Naḥw projections may add relations, explanations, brackets, or ending classes but must preserve the canonical surface.",
            },
        ],
        "defeaters": [],
        "unresolved_blockers": [],
        "dependent_fact_ids": [],
        "dependent_projection_ids": [projection_id],
    }
    errors = validate_dependency_fact(fact)
    if errors:
        raise ValueError("invalid naḥw dependency fact: " + "; ".join(errors))
    return fact


def _claim_bindings(fact: dict[str, Any]) -> list[dict[str, Any]]:
    spans = [span["span_id"] for span in fact["surface_spans"]]
    bindings = []
    for field in (
        "fact_value.role",
        "fact_value.governor",
        "fact_value.governed_occurrence",
        "fact_value.relationship_evidence",
        "fact_value.case_or_mood",
        "fact_value.ending",
    ):
        bindings.append({
            "fact_id": fact["fact_id"],
            "fact_field": field,
            "surface_span_ids": spans,
        })
    return bindings


def build_contract_record(input_row: dict[str, Any], *, source_record_id: str) -> dict[str, Any]:
    """Build and F-A validate one learner-visible candidate contract."""

    loc = _require_loc(input_row.get("quran_loc") or input_row.get("loc"), "quran_loc")
    surface = _source_surface(input_row)
    projection_id = _projection_id(loc)
    fact = build_dependency_fact(input_row, source_record_id=source_record_id, projection_id=projection_id)
    record = {
        "schema": SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "contract_id": f"fc1:nahw:{loc}",
        "record_type": "projection_input",
        "canonical_occurrence": {
            "occurrence_id": _quran_address(loc),
            "quran_loc": loc,
            "wbw_loc": _wbw_address(loc),
            "surface": surface,
            "surface_length": len(surface),
        },
        "facts": [fact],
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": "qamus/examples/fc1-nahw/calibrated-sample.jsonl",
                "field": "nahw_dependency",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "This candidate records a source-addressed naḥw dependency with its exact governor, governed occurrence, relation evidence, and ending state.",
                "language": "en",
                "fact_bindings": _claim_bindings(fact),
            },
            "learner_statement": "This candidate is a source-addressed syntax explanation pending owner review.",
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "relations": [{
                    "role": fact["fact_value"]["role"],
                    "governor": fact["fact_value"]["governor"],
                    "governed_occurrence": fact["fact_value"]["governed_occurrence"],
                    "relationship": fact["fact_value"]["relationship"],
                    "ending_status": fact["fact_value"]["ending"],
                }],
            },
        },
    }
    errors = validate_contract_record(record)
    if errors:
        raise ValueError("generated FC1 candidate failed F-A validation: " + "; ".join(errors))
    return record


def build_unresolved_record(input_row: dict[str, Any], *, blocker: str, source_record_id: str) -> dict[str, Any]:
    """Build a typed syntax-pending record without guessing a dependency."""

    loc = _require_loc(input_row.get("quran_loc") or input_row.get("loc"), "quran_loc")
    surface = _source_surface(input_row)
    projection_id = f"fc1.nahw.{loc.replace(':', '.')}.pending.v1"
    source, source_address, _certification, _evidence, _mode = _source_details(
        {**input_row, "certification": {"status": "pending", "reason": "syntax evidence is incomplete"},
         "evidence": {"status": "unknown", "confidence": "unknown", "evidence_ids": [f"fc1:pending:{loc}"], "summary": "no usable naḥw dependency evidence"},
         "evidence_mode": "unresolved"},
        source_record_id,
        loc,
    )
    addresses = _source_addresses(input_row, loc, source_record_id, source["source_kind"])
    spans = _validated_spans({}, surface)
    fact_value = {
        "status": "unresolved",
        "governor": None,
        "governed_occurrence": {"occurrence_id": _quran_address(loc), "surface": surface},
        "relationship_evidence": {"status": "missing", "source_field": "none", "summary": blocker},
        "case_or_mood": {"applicability": "not_applicable", "value": None, "status": "unresolved", "reason": blocker},
        "ending": {"value": None, "status": "unresolved", "reason": blocker},
        "source_surface": surface,
        "projected_surface": surface,
    }
    fact = {
        "fact_id": _fact_id(FACT_TYPE, fact_value, spans, source_address, "unresolved"),
        "fact_type": FACT_TYPE,
        "fact_value": fact_value,
        "surface_spans": spans,
        "ownership": {
            "primary": {"owner_id": "fc1-nahw-owner", "owner_type": "producer_pending"},
            "secondary": [{"owner_id": PRODUCER_ID, "owner_type": "producer"}],
        },
        "source": source,
        "source_address": source_address,
        "certification": {"status": "pending", "reason": "No exact governor and governed relationship has been certified."},
        "evidence": {
            "status": "unknown",
            "confidence": "unknown",
            "evidence_ids": [f"fc1:pending:{loc}"],
            "summary": "No usable naḥw dependency evidence; producer abstained.",
        },
        "evidence_mode": "unresolved",
        "source_evidence": {
            "structured_source_fact": {
                "source_record_id": str(source_record_id),
                "source_fields": [],
                "blocker": blocker,
            },
            "source_addresses": addresses,
        },
        "derivation_chain": [],
        "dependencies": {"fact_ids": [], "source_addresses": addresses},
        "contradiction_records": [],
        "producer": {"id": PRODUCER_ID, "version": VERSION},
        "rule_projector": {
            "rule_id": "fc1.nahw.abstain_without_dependency",
            "projector_id": PROJECTOR_ID,
            "version": VERSION,
        },
        "guards": [
            {
                "guard_id": "fc1.abstain_without_exact_governor",
                "reason": "No learner-visible naḥw role is emitted without an exact governor and governed occurrence.",
            },
        ],
        "defeaters": [],
        "unresolved_blockers": [{"blocker_id": "fc1.syntax_evidence_gap", "reason": blocker}],
        "dependent_fact_ids": [],
        "dependent_projection_ids": [projection_id],
    }
    record = {
        "schema": SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "contract_id": f"fc1:nahw:pending:{loc}",
        "record_type": "unresolved_projection",
        "canonical_occurrence": {
            "occurrence_id": _quran_address(loc),
            "quran_loc": loc,
            "wbw_loc": _wbw_address(loc),
            "surface": surface,
            "surface_length": len(surface),
        },
        "facts": [fact],
        "projection": {
            "projection_id": projection_id,
            "status": UNRESOLVED_STATUS,
            "unresolved_status": UNRESOLVED_STATUS,
            "learner_visible": True,
            "materialization_target": {
                "artifact": "qamus/examples/fc1-nahw/unresolved-sample.jsonl",
                "field": "nahw_dependency",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": None,
            "learner_statement": learner_statement_for(UNRESOLVED_STATUS),
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "relations": [],
                "status": UNRESOLVED_STATUS,
            },
        },
    }
    errors = validate_contract_record(record)
    if errors:
        raise ValueError("generated FC1 unresolved record failed F-A validation: " + "; ".join(errors))
    return record


# ---------------------------------------------------------------------------
# Calibration extraction


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(value)
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(_canonical_json(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def _pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _row_loc(row: dict[str, Any]) -> str:
    # The stratified and whitelist inputs use ``loc`` as the word-level join
    # key.  Some historical whitelist rows retain a different quran_loc alias;
    # accepting that alias as the primary key would merge two occurrences.
    return _require_loc(row.get("loc") or row.get("quran_loc"), "row.loc")


def _row_surface(row: dict[str, Any]) -> str:
    surface = row.get("surface")
    if not isinstance(surface, str) or not surface:
        raise ValueError(f"row {_row_loc(row)} has no surface")
    return surface


def _loc_parts(loc: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in loc.split(":"))  # type: ignore[return-value]


def _neighbor_loc(loc: str, delta: int) -> str | None:
    surah, ayah, word = _loc_parts(loc)
    next_word = word + delta
    if next_word <= 0:
        return None
    return f"{surah}:{ayah}:{next_word}"


def _nahw_notes(row: dict[str, Any]) -> list[tuple[str, str]]:
    """Collect source-addressable naḥw notes, excluding morphology-only notes."""

    notes: list[tuple[str, str]] = []
    facts = row.get("nahw_facts")
    if isinstance(facts, dict):
        for key in ("function", "attachment", "case_effect", "case_or_mood", "governor", "governor_loc"):
            value = facts.get(key)
            if isinstance(value, str) and value.strip():
                notes.append((f"nahw_facts.{key}", value.strip()))
    elif isinstance(facts, list):
        for index, value in enumerate(facts):
            if isinstance(value, str) and value.strip():
                notes.append((f"nahw_facts[{index}]", value.strip()))
    for index, segment in enumerate(row.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        note = segment.get("nahw_note")
        if isinstance(note, str) and note.strip():
            if note.strip().lower() == "nahw: function prefix preserved":
                continue
            notes.append((f"segments[{index}].nahw_note", note.strip()))
    # Preserve the first occurrence of a source note; duplicate segment notes
    # add no evidence and make reports less legible.
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for field, note in notes:
        if note not in seen:
            unique.append((field, note))
            seen.add(note)
    return unique


def _segment_spans(row: dict[str, Any]) -> list[dict[str, Any]] | None:
    surface = _row_surface(row)
    segments = row.get("segments") or []
    if not isinstance(segments, list) or not segments:
        return None
    spans: list[dict[str, Any]] = []
    cursor = 0
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict) or not isinstance(segment.get("surface"), str):
            return None
        part = segment["surface"]
        if not part or surface[cursor:cursor + len(part)] != part:
            return None
        role = str(segment.get("role") or f"segment_{index}")
        role = re.sub(r"[^A-Za-z0-9_:-]", "_", role).lower()
        if not role or not re.match(r"^[a-z]", role):
            role = f"segment_{index}"
        spans.append({
            "span_id": f"segment-{index}",
            "start": cursor,
            "end": cursor + len(part),
            "surface": part,
            "role": role,
        })
        cursor += len(part)
    if cursor != len(surface):
        return None
    return spans


def _segment_record(row: dict[str, Any], index: int) -> dict[str, Any] | None:
    segments = row.get("segments") or []
    if not isinstance(segments, list) or index < 0 or index >= len(segments):
        return None
    value = segments[index]
    return value if isinstance(value, dict) else None


def _segment_class(segment: dict[str, Any] | None) -> str:
    if not segment:
        return ""
    return " ".join(str(segment.get(key, "")).lower() for key in ("class", "role", "label"))


def _find_segment(spans: list[dict[str, Any]], row: dict[str, Any], predicate: Any) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for index, span in enumerate(spans):
        segment = _segment_record(row, index)
        if segment is not None and predicate(segment):
            return span, segment
    return None


def _first_note(notes: Sequence[tuple[str, str]]) -> tuple[str, str] | None:
    return notes[0] if notes else None


def _notes_text(notes: Sequence[tuple[str, str]]) -> str:
    return "; ".join(note for _field, note in notes)


def _has_note(notes: Sequence[tuple[str, str]], *needles: str) -> bool:
    text = _notes_text(notes).lower()
    return any(needle.lower() in text for needle in needles)


def _terminal_mark(surface: str) -> str | None:
    marks: list[str] = []
    for character in reversed(surface):
        if character in TERMINAL_MARKS or unicodedata.combining(character):
            marks.append(character)
            continue
        break
    if not marks:
        return None
    return "".join(reversed(marks))


def _case_or_mood(text: str, *, inferred_role: str | None = None, reason: str = "") -> dict[str, Any]:
    lowered = text.lower()
    if any(token in lowered for token in ("no case", "no mood", "particle", "not applicable")):
        return {
            "applicability": "not_applicable",
            "value": None,
            "status": "not_applicable",
            "reason": reason or "the source describes a function particle or an attached component rather than an independent inflection",
        }
    if any(token in lowered for token in ("jussive", "jazm", "مجزوم")):
        return {"applicability": "mood", "value": "jussive", "status": "observed", "reason": reason or "source note names the jussive mood"}
    if any(token in lowered for token in ("subjunctive", "nasb", "منصوب")):
        return {"applicability": "mood", "value": "subjunctive", "status": "observed", "reason": reason or "source note names the subjunctive mood"}
    if "indicative" in lowered or "مرفوع" in lowered and "mood" in lowered:
        return {"applicability": "mood", "value": "indicative", "status": "observed", "reason": reason or "source note names the indicative mood"}
    if any(token in lowered for token in ("genitive", "jarr", "مجرور", "genitive relation")):
        return {"applicability": "case", "value": "genitive", "status": "observed", "reason": reason or "source note names the genitive relation"}
    if any(token in lowered for token in ("accusative", "نصب", "منصوب")):
        return {"applicability": "case", "value": "accusative", "status": "observed", "reason": reason or "source note names the accusative position"}
    if any(token in lowered for token in ("nominative", "raf", "مرفوع")):
        return {"applicability": "case", "value": "nominative", "status": "observed", "reason": reason or "source note names the nominative position"}
    if inferred_role == "subject":
        return {"applicability": "case", "value": "nominative", "status": "estimated", "reason": reason or "subject relation supplies a case estimate; the source did not state the case explicitly"}
    if inferred_role == "object":
        return {"applicability": "case", "value": "accusative", "status": "estimated", "reason": reason or "object relation supplies a case estimate; the source did not state the case explicitly"}
    if inferred_role == "preposition_to_governed":
        return {"applicability": "case", "value": "genitive", "status": "estimated", "reason": reason or "preposition-to-governed relation supplies a genitive estimate; source case wording is incomplete"}
    return {
        "applicability": "not_applicable",
        "value": None,
        "status": "not_applicable",
        "reason": reason or "the source evidence does not state an independent case or mood for this relation",
    }


def _ending(surface: str, *, applicable: bool, reason: str) -> dict[str, Any]:
    if not applicable:
        return {"value": None, "status": "not_applicable", "reason": reason}
    mark = _terminal_mark(surface)
    if mark:
        return {"value": mark, "status": "visible", "reason": "terminal mark is visible on the source occurrence surface"}
    return {"value": None, "status": "estimated", "reason": reason or "the source occurrence is unvoweled at the ending; the ending is estimated and review-gated"}


def _occurrence_for_row(row: dict[str, Any], *, span: dict[str, Any] | None = None) -> dict[str, Any]:
    loc = _row_loc(row)
    result: dict[str, Any] = {
        "occurrence_id": _quran_address(loc),
        "surface": _row_surface(row) if span is None else span["surface"],
    }
    if span is not None:
        result["span_id"] = span["span_id"]
    return result


def _local_occurrence(row: dict[str, Any], span: dict[str, Any], *, governed: bool) -> dict[str, Any]:
    result = {
        "occurrence_id": _quran_address(_row_loc(row)),
        "surface": span["surface"],
        ("span_ids" if governed else "span_id"): [span["span_id"]] if governed else span["span_id"],
    }
    return result


def _input_candidate(
    row: dict[str, Any],
    corpus_by_loc: dict[str, dict[str, Any]],
    verdict: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    """Derive one conservative input row or explain why it is withheld."""

    loc = _row_loc(row)
    surface = _row_surface(row)
    source_surface_row = corpus_by_loc.get(loc)
    if source_surface_row is None:
        return None, "the read-only corpus has no exact source row"
    if _row_surface(source_surface_row) != surface:
        return None, "stratification and corpus surfaces differ; producer will not repaint either surface"
    notes = _nahw_notes(source_surface_row)
    if not notes:
        return None, "no source-addressable naḥw note is present"
    spans = _segment_spans(source_surface_row)
    if not spans:
        return None, "source segments cannot be aligned to the exact canonical surface"
    facts = source_surface_row.get("nahw_facts") if isinstance(source_surface_row.get("nahw_facts"), dict) else {}
    segments = source_surface_row.get("segments") or []

    role: str | None = None
    relationship: str | None = None
    governor: dict[str, Any] | None = None
    governed: dict[str, Any] | None = None
    case_text = _notes_text(notes)
    case_reason = "source-addressed note supplies the case/mood context"
    ending_surface = surface
    ending_applicable = False
    relationship_field = _first_note(notes)
    chosen_spans: list[dict[str, Any]] = []

    # Attached pronouns are handled first: the host component and pronoun
    # component are both exact spans in the same canonical occurrence.
    pronoun = _find_segment(spans, source_surface_row, lambda segment: "pronoun" in _segment_class(segment))
    pronoun_is_local_object = any("object" in _segment_class(_segment_record(source_surface_row, index)) for index in range(len(segments))) and any("verb" in _segment_class(_segment_record(source_surface_row, index)) for index in range(len(segments)))
    if pronoun and (_has_note(notes, "pronoun", "inna", "preposition", "possessive", "object/recipient")) and not facts.get("governor_loc") and not pronoun_is_local_object:
        pronoun_span, pronoun_segment = pronoun
        pronoun_index = next(i for i, item in enumerate(segments) if item is pronoun_segment)
        host_pair = None
        for index in range(pronoun_index - 1, -1, -1):
            candidate_segment = _segment_record(source_surface_row, index)
            if candidate_segment is not None:
                host_pair = (spans[index], candidate_segment)
                break
        if host_pair is not None:
            host_span, host_segment = host_pair
            role = "pronoun_attachment"
            host_text = _segment_class(host_segment)
            relationship = "pronoun_as_name_of_inna" if "inna" in case_text.lower() or "name position" in case_text.lower() else "attached_pronoun_complement"
            governor = _local_occurrence(source_surface_row, host_span, governed=False)
            governed = _local_occurrence(source_surface_row, pronoun_span, governed=True)
            chosen_spans = [host_span, pronoun_span]
            if "accusative" in case_text.lower() or "inna" in case_text.lower():
                case = _case_or_mood(case_text, reason=case_reason)
            else:
                case = _case_or_mood("not applicable", reason="the attached pronoun is represented as a component relation; no separate case ending is asserted")
            ending_payload = _ending(ending_surface, applicable=False, reason="the attached pronoun has no separate terminal case ending in this token")
            case_text = case_text or host_text
            return _candidate_input_row(
                row, source_surface_row, verdict, role, governor, governed, relationship,
                relationship_field, case, ending_payload, chosen_spans, notes,
            )

    # Local subject/object markers and agreement are exact component relations.
    subject_segment = _find_segment(spans, source_surface_row, lambda segment: "subject" in _segment_class(segment) or "subj" in str(segment.get("label", "")).lower())
    verb_segment = _find_segment(spans, source_surface_row, lambda segment: "verb" in _segment_class(segment) or "stem" in str(segment.get("label", "")).lower())
    if subject_segment and verb_segment and _has_note(notes, "subject", "agreement") and not facts.get("governor_loc"):
        subject_span, _subject = subject_segment
        verb_span, _verb = verb_segment
        role = "agreement" if _has_note(notes, "agreement") and not _has_note(notes, "subject of", "subject marker") else "subject"
        relationship = "subject_agreement" if role == "agreement" else "subject_of"
        governor = _local_occurrence(source_surface_row, verb_span, governed=False)
        governed = _local_occurrence(source_surface_row, subject_span, governed=True)
        chosen_spans = [verb_span, subject_span]
        case = _case_or_mood(case_text, inferred_role="subject", reason=case_reason)
        if case.get("applicability") == "case":
            case = _case_or_mood("not applicable", reason="the subject is an attached component; no independent case ending is asserted on this token")
        ending_payload = _ending(subject_span["surface"], applicable=False, reason="the subject marker is an attached component without a separate case ending")
        return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    object_segment = _find_segment(spans, source_surface_row, lambda segment: "object" in _segment_class(segment) or str(segment.get("label", "")).lower() == "obj")
    if object_segment and verb_segment and _has_note(notes, "object", "recipient") and not facts.get("governor_loc"):
        object_span, _object = object_segment
        verb_span, _verb = verb_segment
        role = "object"
        relationship = "object_of"
        governor = _local_occurrence(source_surface_row, verb_span, governed=False)
        governed = _local_occurrence(source_surface_row, object_span, governed=True)
        chosen_spans = [verb_span, object_span]
        case = _case_or_mood(case_text, inferred_role="object", reason=case_reason)
        object_is_pronoun = "pronoun" in _segment_class(object_segment[1])
        ending_payload = _ending(object_span["surface"], applicable=not object_is_pronoun, reason="the object pronoun is an attached component without a separate case ending")
        return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    # Definite article to noun is a local naḥw explanation, not a lexical
    # repaint.  It intentionally carries not_applicable case/mood.
    article = _find_segment(spans, source_surface_row, lambda segment: "article" in _segment_class(segment) or str(segment.get("label", "")).lower() == "art")
    noun = _find_segment(spans, source_surface_row, lambda segment: "noun" in _segment_class(segment) or str(segment.get("label", "")).lower() in {"n", "name"})
    if article and noun and _has_note(notes, "definiteness"):
        article_span, _article = article
        noun_span, _noun = noun
        role = "other"
        relationship = "definiteness_marker_to_noun"
        governor = _local_occurrence(source_surface_row, article_span, governed=False)
        governed = _local_occurrence(source_surface_row, noun_span, governed=True)
        chosen_spans = [article_span, noun_span]
        case = _case_or_mood("not applicable", reason="definiteness marking does not itself assert an independent case or mood")
        ending_payload = _ending(noun_span["surface"], applicable=False, reason="definiteness marking does not itself own the noun's case ending")
        return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    # A local preposition to a noun is stronger than an unanchored PP gloss.
    prep = _find_segment(spans, source_surface_row, lambda segment: "preposition" in _segment_class(segment) or str(segment.get("label", "")).lower() in {"p", "prep", "lam"})
    if prep and noun and _has_note(notes, "preposition", "jar-majrur", "governed noun"):
        prep_span, _prep = prep
        noun_span, _noun = noun
        role = "preposition_to_governed"
        relationship = "preposition_governs"
        governor = _local_occurrence(source_surface_row, prep_span, governed=False)
        governed = _local_occurrence(source_surface_row, noun_span, governed=True)
        chosen_spans = [prep_span, noun_span]
        case = _case_or_mood(case_text, inferred_role="preposition_to_governed", reason=case_reason)
        ending_payload = _ending(noun_span["surface"], applicable=True, reason="the governed noun has no visible ending in the source surface; the genitive ending is estimated")
        return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    # Explicit governor locations are accepted only when the source names the
    # exact quran location.  The common calibration witness is the prohibitive
    # particle governing an imperfect verb's mood.
    governor_loc = facts.get("governor_loc") if isinstance(facts, dict) else None
    if governor_loc:
        try:
            governor_loc = _require_loc(governor_loc, "nahw_facts.governor_loc")
        except ValueError:
            governor_loc = None
        if governor_loc and governor_loc in corpus_by_loc:
            governor_row = corpus_by_loc[governor_loc]
            role = "mood" if _has_note(notes, "mood", "jussive", "prohibitive", "governed") else "other"
            relationship = "mood_governed_by" if role == "mood" else "governed_by"
            governor = _occurrence_for_row(governor_row)
            governed = _occurrence_for_row(source_surface_row)
            chosen_spans = [{"span_id": "token", "start": 0, "end": len(surface), "surface": surface, "role": "governed_token"}]
            case = _case_or_mood(case_text, reason=case_reason)
            ending_payload = _ending(surface, applicable=True, reason="mood ending is not visible on the source surface; the ending is estimated from the exact governor")
            return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    # A note that says “subject of the preceding verb” gives an exact relative
    # occurrence once the preceding Quran word is looked up.  This is not a
    # nearest-verb guess: the source wording itself supplies the direction.
    if _has_note(notes, "subject of the preceding verb", "subject of preceding verb"):
        previous_loc = _neighbor_loc(loc, -1)
        if previous_loc and previous_loc in corpus_by_loc:
            previous_row = corpus_by_loc[previous_loc]
            role = "subject"
            relationship = "subject_of"
            governor = _occurrence_for_row(previous_row)
            governed = _occurrence_for_row(source_surface_row)
            chosen_spans = [{"span_id": "token", "start": 0, "end": len(surface), "surface": surface, "role": "governed_token"}]
            case = _case_or_mood(case_text, inferred_role="subject", reason=case_reason)
            ending_payload = _ending(surface, applicable=True, reason="subject relation supplies the nominative estimate; the ending is not visible on the source surface")
            return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    # A preposition-only token has an exact following occurrence, but its PP
    # head remains deliberately unasserted.  The relationship is therefore
    # limited to the preposition's governed occurrence, not wider attachment.
    if prep and _has_note(notes, "prepositional relation", "jar-majrur", "prepositional_lam", "governs a following"):
        next_loc = _neighbor_loc(loc, 1)
        if next_loc and next_loc in corpus_by_loc:
            next_row = corpus_by_loc[next_loc]
            role = "preposition_to_governed"
            relationship = "preposition_governs_following_occurrence"
            governor = _local_occurrence(source_surface_row, prep[0], governed=False)
            governed = _occurrence_for_row(next_row)
            chosen_spans = [prep[0]]
            case = _case_or_mood(case_text, inferred_role="preposition_to_governed", reason="the preposition supplies the genitive relation; the source does not certify wider PP attachment")
            ending_payload = _ending(_row_surface(next_row), applicable=True, reason="the governed occurrence has no visible terminal mark; its genitive ending is estimated and review-gated")
            return _candidate_input_row(row, source_surface_row, verdict, role, governor, governed, relationship, relationship_field, case, ending_payload, chosen_spans, notes)

    return None, "source notes do not identify a safe exact dependency pair"


def _candidate_input_row(
    strat_row: dict[str, Any],
    source_row: dict[str, Any],
    verdict: dict[str, Any] | None,
    role: str,
    governor: dict[str, Any],
    governed: dict[str, Any],
    relationship: str,
    relationship_field: tuple[str, str] | None,
    case: dict[str, Any],
    ending: dict[str, Any],
    chosen_spans: list[dict[str, Any]],
    notes: Sequence[tuple[str, str]],
) -> tuple[dict[str, Any], str]:
    loc = _row_loc(source_row)
    source_record_id = f"rh_live_01_beta_whitelist.jsonl#loc={loc}"
    evidence_ids = [f"fc1:nahw:{loc}"]
    if verdict is not None:
        evidence_ids.append(f"v575-verdicts.jsonl#loc={loc}")
    source_addresses: list[dict[str, str]] = [{"address": _quran_address(loc), "source_kind": "quran_token"}]
    for occurrence in (governor, governed):
        address = occurrence.get("occurrence_id")
        if isinstance(address, str) and QURAN_LOC_RE.fullmatch(address):
            item = {"address": address, "source_kind": "quran_token"}
            if item not in source_addresses:
                source_addresses.append(item)
    source_field = relationship_field[0] if relationship_field else "segments.nahw_note"
    summary = _notes_text(notes) or "source-addressed naḥw dependency note"
    fact = {
        "role": role,
        "governor": governor,
        "governed_occurrence": governed,
        "relationship": relationship,
        "relationship_evidence": {"source_field": source_field, "summary": summary},
        "case_or_mood": case,
        "ending": ending,
    }
    if role == "pronoun_attachment":
        # Attachment is source-addressed here; the source packet does not name
        # an exact antecedent occurrence for these rows.  Carry that gap as a
        # typed field rather than silently turning a pronoun into a referent
        # guess.
        fact["referent"] = {
            "value": None,
            "status": "unresolved",
            "reason": "the source identifies the attached pronoun but does not provide an exact referent occurrence",
        }
    if isinstance(source_row.get("nahw_facts"), dict):
        for key in ("attachment", "function", "case_effect"):
            if isinstance(source_row["nahw_facts"].get(key), str) and source_row["nahw_facts"][key].strip():
                fact[key] = source_row["nahw_facts"][key]
    # The fact builder will preserve only NAHW_FACT_KEYS and will add the exact
    # canonical source/projected surfaces itself.
    input_row = {
        "loc": loc,
        "quran_loc": loc,
        "wbw_loc": _wbw_address(loc),
        "surface": _row_surface(source_row),
        "surface_spans": chosen_spans,
        "nahw_fact": fact,
        "source": {"source_id": source_record_id, "source_kind": "corpus_record"},
        "source_addresses": source_addresses,
        "certification": {
            "status": "review_required" if ending.get("status") == "estimated" or case.get("status") == "estimated" else "candidate",
            "reason": "Calibration output is source-addressed but not owner-certified; estimated endings remain review-gated." if ending.get("status") == "estimated" else "Calibration output is source-addressed candidate evidence; no new certification was performed.",
        },
        "evidence": {
            "status": "source_addressed_candidate",
            "confidence": "medium" if len(source_addresses) > 1 else "low",
            "evidence_ids": evidence_ids,
            "summary": "Source-addressed naḥw notes from the read-only whitelist and stratified row.",
        },
        "evidence_mode": "direct_source_attestation",
        "projected_surface": _row_surface(source_row),
    }
    return input_row, "candidate"


def _candidate_priority(record: dict[str, Any]) -> tuple[int, str]:
    fact = record.get("facts", [{}])[0].get("fact_value", {})
    role = fact.get("role", "other")
    return ROLE_PRIORITY.get(str(role), ROLE_PRIORITY["other"]), record.get("canonical_occurrence", {}).get("quran_loc", "")


def _dedupe_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        loc = _row_loc(row)
        if loc in seen:
            raise ValueError(f"duplicate calibration location {loc}")
        seen.add(loc)
        result.append(row)
    return result


def _balanced_select(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(records) < limit:
        raise ValueError(f"only {len(records)} valid naḥw candidates were available; at least {limit} are required")
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(records, key=_candidate_priority):
        buckets[_candidate_priority(record)[0]].append(record)
    selected: list[dict[str, Any]] = []
    # Preserve every priority category that has evidence before filling the
    # packet in stable priority/location order.
    for priority in sorted(buckets):
        if len(selected) >= limit:
            break
        selected.append(buckets[priority].pop(0))
    remaining = sorted((record for bucket in buckets.values() for record in bucket), key=_candidate_priority)
    selected.extend(remaining[: max(0, limit - len(selected))])
    return selected


def build_calibration_packet(
    strat_rows: Sequence[dict[str, Any]],
    verdict_rows: Sequence[dict[str, Any]],
    corpus_rows: Sequence[dict[str, Any]],
    *,
    positive_limit: int = 30,
    unresolved_limit: int = 3,
) -> dict[str, Any]:
    """Build the bounded FC1 positive and abstention packet."""

    strat_rows = _dedupe_rows(strat_rows)
    verdict_by_loc: dict[str, dict[str, Any]] = {}
    for verdict in verdict_rows:
        loc = _row_loc(verdict)
        if loc in verdict_by_loc:
            raise ValueError(f"duplicate verdict location {loc}")
        verdict_by_loc[loc] = verdict
    corpus_by_loc: dict[str, dict[str, Any]] = {}
    for corpus in corpus_rows:
        loc = _row_loc(corpus)
        if loc in corpus_by_loc:
            raise ValueError(f"duplicate corpus location {loc}")
        corpus_by_loc[loc] = corpus
    if not verdict_by_loc.keys() >= {_row_loc(row) for row in strat_rows}:
        missing = sorted({_row_loc(row) for row in strat_rows} - verdict_by_loc.keys())
        raise ValueError(f"v575 verdict input is missing stratified locations: {missing[:5]}")
    if not corpus_by_loc.keys() >= {_row_loc(row) for row in strat_rows}:
        missing = sorted({_row_loc(row) for row in strat_rows} - corpus_by_loc.keys())
        raise ValueError(f"read-only corpus is missing stratified locations: {missing[:5]}")

    candidates: list[dict[str, Any]] = []
    rejected: list[tuple[dict[str, Any], str]] = []
    for strat in strat_rows:
        loc = _row_loc(strat)
        candidate_input, reason = _input_candidate(strat, corpus_by_loc, verdict_by_loc.get(loc))
        if candidate_input is None:
            rejected.append((strat, reason))
            continue
        try:
            candidates.append(build_contract_record(
                candidate_input,
                source_record_id=candidate_input["source"]["source_id"],
            ))
        except (TypeError, ValueError) as exc:
            rejected.append((strat, f"candidate failed closed producer validation: {exc}"))

    positives = _balanced_select(candidates, positive_limit)
    selected_positive_locs = {record["canonical_occurrence"]["quran_loc"] for record in positives}
    unresolved_inputs: list[tuple[dict[str, Any], str]] = []
    for row, reason in rejected:
        if _row_loc(row) not in selected_positive_locs:
            unresolved_inputs.append((row, reason))
        if len(unresolved_inputs) >= unresolved_limit:
            break
    if len(unresolved_inputs) < unresolved_limit:
        # Keep the negative packet deterministic even if a future source grows
        # enough evidence to make every row positive: these are explicit
        # no-evidence projections of selected corpus rows, not inferred facts.
        for row in strat_rows:
            if _row_loc(row) in selected_positive_locs or any(_row_loc(item[0]) == _row_loc(row) for item in unresolved_inputs):
                continue
            unresolved_inputs.append((row, "calibration negative intentionally omits usable dependency evidence"))
            if len(unresolved_inputs) >= unresolved_limit:
                break
    unresolved = [
        build_unresolved_record(
            {
                "loc": _row_loc(row),
                "quran_loc": _row_loc(row),
                "wbw_loc": _wbw_address(_row_loc(row)),
                "surface": _row_surface(row),
                "source": {"source_id": f"rh_live_01_beta_whitelist.jsonl#loc={_row_loc(row)}", "source_kind": "corpus_record"},
                "source_addresses": [{"address": _quran_address(_row_loc(row)), "source_kind": "quran_token"}],
            },
            blocker=reason,
            source_record_id=f"rh_live_01_beta_whitelist.jsonl#loc={_row_loc(row)}",
        )
        for row, reason in unresolved_inputs
    ]
    if len(unresolved) < unresolved_limit:
        raise ValueError(f"only {len(unresolved)} unresolved calibration records were built; at least {unresolved_limit} are required")

    evidence_modes = Counter(fact["evidence_mode"] for record in positives for fact in record["facts"])
    roles = Counter(record["facts"][0]["fact_value"].get("role", "unknown") for record in positives)
    estimated_endings = sum(record["facts"][0]["fact_value"].get("ending", {}).get("status") == "estimated" for record in positives)
    return {
        "positive": positives,
        "unresolved": unresolved,
        "summary": {
            "positive_count": len(positives),
            "unresolved_count": len(unresolved),
            "abstention_rate": len(unresolved) / (len(positives) + len(unresolved)),
            "source_stratified_row_count": len(strat_rows),
            "source_verdict_row_count": len(verdict_rows),
            "source_corpus_row_count": len(corpus_rows),
            "selected_positive_locations": sorted(selected_positive_locs),
            "rejected_evidence_locations_considered": len(rejected),
            "evidence_modes": dict(sorted(evidence_modes.items())),
            "roles": dict(sorted(roles.items())),
            "estimated_ending_count": estimated_endings,
            "calibration_scope": "455-row stratified packet only; no corpus-wide certification or publication claim",
        },
    }


def write_calibration_packet(packet: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Write only stable, path-free committed packet artifacts."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    positive_path = output_dir / "fc1-calibrated-sample.jsonl"
    unresolved_path = output_dir / "fc1-unresolved-sample.jsonl"
    summary_path = output_dir / "fc1-calibration-summary.json"
    positive_meta = output_dir / "fc1-calibrated-sample.meta.json"
    unresolved_meta = output_dir / "fc1-unresolved-sample.meta.json"
    _write_jsonl(positive_path, packet["positive"])
    _write_jsonl(unresolved_path, packet["unresolved"])
    positive_meta.write_text(_pretty_json({
        "artifact": "fc1-calibrated-sample.jsonl",
        "record_type": "projection_input",
        "count": len(packet["positive"]),
        "scope": "bounded FC1 calibration packet",
    }), encoding="utf-8", newline="\n")
    unresolved_meta.write_text(_pretty_json({
        "artifact": "fc1-unresolved-sample.jsonl",
        "record_type": "unresolved_projection",
        "count": len(packet["unresolved"]),
        "scope": "bounded FC1 calibration abstention packet",
    }), encoding="utf-8", newline="\n")
    summary_path.write_text(_pretty_json(packet["summary"]), encoding="utf-8", newline="\n")
    return {
        "positive": positive_path,
        "unresolved": unresolved_path,
        "positive_meta": positive_meta,
        "unresolved_meta": unresolved_meta,
        "summary": summary_path,
    }


def _self_test() -> list[str]:
    """Run the committed fixture boundary without needing external corpus data."""

    fixture_path = ROOT / "qamus" / "examples" / "fc1-nahw" / "producer-fixtures.jsonl"
    fixtures = _read_jsonl(fixture_path)
    errors: list[str] = []
    positives = [item for item in fixtures if item.get("expect") == "accept"]
    rejects = [item for item in fixtures if item.get("expect") == "reject"]
    unresolved = [item for item in fixtures if item.get("expect") == "unresolved"]
    if len(positives) < 5:
        errors.append("fixture boundary has fewer than five positive fixtures")
    if len(rejects) < 5:
        errors.append("fixture boundary has fewer than five adversarial fixtures")
    for fixture in positives:
        try:
            fact = build_dependency_fact(fixture["input"], source_record_id=f"fixture:{fixture['id']}")
            errors.extend(validate_dependency_fact(fact))
        except ValueError as exc:
            errors.append(f"positive fixture {fixture['id']} rejected: {exc}")
    for fixture in rejects:
        try:
            fact = build_dependency_fact(fixture["input"], source_record_id=f"fixture:{fixture['id']}")
        except ValueError:
            continue
        if not validate_dependency_fact(fact):
            errors.append(f"adversarial fixture {fixture['id']} was accepted")
    for fixture in unresolved:
        try:
            record = build_unresolved_record(
                fixture["input"], blocker="fixture blocker", source_record_id=f"fixture:{fixture['id']}"
            )
            errors.extend(validate_contract_record(record))
        except ValueError as exc:
            errors.append(f"unresolved fixture {fixture['id']} failed: {exc}")
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--strat-455", type=Path)
    parser.add_argument("--v575-verdicts", type=Path)
    parser.add_argument("--whitelist", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--positive-limit", type=int, default=30)
    parser.add_argument("--unresolved-limit", type=int, default=3)
    args = parser.parse_args(argv)
    if args.self_test:
        errors = _self_test()
        if errors:
            print("FC1 NAHW PRODUCER SELF-TEST FAIL")
            for error in errors:
                print(f"- {error}")
            return 1
        print("FC1 NAHW PRODUCER SELF-TEST PASS")
        return 0
    required = {"--strat-455": args.strat_455, "--v575-verdicts": args.v575_verdicts, "--whitelist": args.whitelist, "--output-dir": args.output_dir}
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error("calibration mode requires " + ", ".join(missing))
    try:
        packet = build_calibration_packet(
            _read_jsonl(args.strat_455),
            _read_jsonl(args.v575_verdicts),
            _read_jsonl(args.whitelist),
            positive_limit=args.positive_limit,
            unresolved_limit=args.unresolved_limit,
        )
        paths = write_calibration_packet(packet, args.output_dir)
    except (OSError, TypeError, ValueError) as exc:
        print(f"FC1 NAHW PRODUCER FAIL: {exc}")
        return 1
    print("FC1 NAHW CALIBRATION PACKET PASS")
    print(_canonical_json(packet["summary"]))
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
