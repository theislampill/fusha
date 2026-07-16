#!/usr/bin/env python3
"""F-A governed typed-claim contract helpers.

This module is intentionally stdlib-only. It validates a closed contract envelope,
normalizes ingestion aliases without mutating caller data, and keeps unresolved and
legacy records explicit instead of inventing linguistic facts.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable

from tools import fact_ledger


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCHEMA_PATH = ROOT / "qamus" / "schemas" / "typed-claim-contract.schema.json"
LEGACY_SCHEMA_PATH = ROOT / "qamus" / "schemas" / "legacy-valid-record.schema.json"
LANGUAGE_SCHEMA_PATH = ROOT / "qamus" / "schemas" / "unresolved-language-map.schema.json"
DEFAULT_LANGUAGE_MAP_PATH = ROOT / "qamus" / "examples" / "fa-contract" / "unresolved-language-map.json"

DEPRECATED_QG_ALIASES = {"qg-negative": "qg-negation"}
PUBLIC_UNRESOLVED_STATUSES = {
    "unresolved",
    "source_gap",
    "producer_pending",
    "syntax_pending",
    "blocked",
}
EVIDENCE_MODES = {
    "direct_source_attestation",
    "cross_source_corroboration",
    "deterministic_derivation_from_certified_facts",
    "paired_form_inference",
    "normalized_lexical_body",
    "owner_or_scholar_adjudication",
    "unresolved",
}
DERIVED_EVIDENCE_MODES = {
    "deterministic_derivation_from_certified_facts",
    "paired_form_inference",
}
PROSE_ONLY_ERROR = (
    "learner-visible claim lacks backing typed fact: "
    "a prose assertion is not itself a typed fact"
)
_CLASS_KEYS = {"qg_class", "qg_classes", "class", "classes", "display_class"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(value: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fact_ledger._validate_node(value, schema, "$", errors, schema)
    return errors


def _normalize_string(value: str, key: str | None) -> str:
    if key in _CLASS_KEYS:
        return DEPRECATED_QG_ALIASES.get(value, value)
    return value


def normalize_aliases(value: Any, *, _key: str | None = None) -> Any:
    """Return a deep-normalized copy of an ingestion value.

    Only class-bearing fields are rewritten. This prevents a prose mention or a
    source note from being silently changed while still normalizing nested
    qg_class/qg_classes fields at every projection boundary.
    """

    if isinstance(value, dict):
        return {
            key: normalize_aliases(child, _key=key)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [normalize_aliases(child, _key=_key) for child in value]
    if isinstance(value, str):
        return _normalize_string(value, _key)
    return copy.deepcopy(value)


def assert_no_deprecated_aliases(value: Any, path: str = "$") -> list[str]:
    """Return output errors when a deprecated identifier survives normalization."""

    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(assert_no_deprecated_aliases(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(assert_no_deprecated_aliases(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for deprecated in DEPRECATED_QG_ALIASES:
            if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(deprecated) + r"(?![A-Za-z0-9_-])", value):
                errors.append(f"{path}: deprecated alias {deprecated!r} must not be emitted")
    return errors


def _read_path(value: Any, path: str) -> tuple[bool, Any]:
    """Resolve a small dotted field path such as fact_value.surface."""

    current = value
    for part in path.split("."):
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[([0-9]+)\])?", part)
        if not match or not isinstance(current, dict) or match.group(1) not in current:
            return False, None
        current = current[match.group(1)]
        if match.group(2) is not None:
            index = int(match.group(2))
            if not isinstance(current, list) or index >= len(current):
                return False, None
            current = current[index]
    return True, current


def _surface_span_errors(
    occurrence: dict[str, Any],
    fact: dict[str, Any],
    fact_index: int,
) -> list[str]:
    errors: list[str] = []
    surface = occurrence.get("surface", "")
    if occurrence.get("surface_length") != len(surface):
        errors.append(
            f"facts[{fact_index}].surface_spans: occurrence surface_length does not match Unicode span units"
        )
    for span_index, span in enumerate(fact.get("surface_spans", [])):
        start = span.get("start")
        end = span.get("end")
        prefix = f"facts[{fact_index}].surface_spans[{span_index}]"
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            continue
        if start < 0 or end <= start or end > len(surface):
            errors.append(f"{prefix}: span is outside the canonical occurrence surface")
            continue
        if surface[start:end] != span.get("surface"):
            errors.append(f"{prefix}: exact surface span text does not match the occurrence")
    return errors


def _fact_map(row: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    facts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, fact in enumerate(row.get("facts", [])):
        fact_id = fact.get("fact_id")
        if fact_id in facts:
            errors.append(f"facts[{index}]: duplicate fact_id {fact_id}")
        else:
            facts[fact_id] = fact
    return facts, errors


def _validate_evidence_semantics(
    row: dict[str, Any],
    fact: dict[str, Any],
    fact_index: int,
    facts: dict[str, dict[str, Any]],
    tension_ids: dict[str, dict[str, Any]],
    expected_quran: str,
) -> list[str]:
    """Validate the additive F-D evidence carrier without certifying prose."""

    errors: list[str] = []
    prefix = f"facts[{fact_index}]"
    mode = fact.get("evidence_mode")
    if mode not in EVIDENCE_MODES:
        errors.append(f"{prefix}: evidence_mode is not a closed F-D value")

    source_evidence = fact.get("source_evidence")
    if not isinstance(source_evidence, dict):
        return errors
    source_addresses = source_evidence.get("source_addresses")
    if not isinstance(source_addresses, list) or not source_addresses:
        errors.append(f"{prefix}: source_evidence requires at least one exact source address")
    else:
        for address_index, address in enumerate(source_addresses):
            if not isinstance(address, dict):
                continue
            if not address.get("address"):
                errors.append(
                    f"{prefix}.source_evidence.source_addresses[{address_index}]: exact address is required"
                )

    representations = [
        key for key in ("source_quotation", "structured_source_fact") if key in source_evidence
    ]
    if len(representations) != 1:
        errors.append(f"{prefix}: source_evidence must carry exactly one quotation or structured source fact")

    derivation_chain = fact.get("derivation_chain")
    dependencies = fact.get("dependencies") or {}
    dependency_fact_ids = set(dependencies.get("fact_ids", [])) if isinstance(dependencies, dict) else set()
    if mode in DERIVED_EVIDENCE_MODES:
        if not isinstance(derivation_chain, list) or not derivation_chain:
            errors.append(f"{prefix}: {mode} requires a non-empty derivation_chain")
        for step_index, step in enumerate(derivation_chain or []):
            for input_id in step.get("input_fact_ids", []):
                if input_id not in facts:
                    errors.append(
                        f"{prefix}.derivation_chain[{step_index}]: input fact {input_id} is not present"
                    )
                if input_id not in dependency_fact_ids:
                    errors.append(
                        f"{prefix}.derivation_chain[{step_index}]: input fact {input_id} is not listed in dependencies"
                    )
    if mode == "cross_source_corroboration" and len(source_addresses or []) < 2:
        errors.append(f"{prefix}: cross_source_corroboration requires multiple source addresses")
    if mode == "unresolved" and fact.get("certification", {}).get("status") == "certified":
        errors.append(f"{prefix}: unresolved evidence cannot be certified")

    if isinstance(dependencies, dict):
        for dependency_id in dependencies.get("fact_ids", []):
            if dependency_id not in facts:
                errors.append(f"{prefix}: dependency fact {dependency_id} is not present")

    for contradiction_index, contradiction in enumerate(fact.get("contradiction_records", [])):
        tension_id = contradiction.get("tension_id")
        tension = tension_ids.get(tension_id)
        if tension is None:
            errors.append(
                f"{prefix}.contradiction_records[{contradiction_index}]: tension {tension_id} is not present"
            )
        elif contradiction.get("relation") == "attached_unresolved" and tension.get("status") != "unresolved":
            errors.append(
                f"{prefix}.contradiction_records[{contradiction_index}]: attached_unresolved requires an unresolved tension"
            )
    return errors


def _validate_projection_semantics(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    occurrence = row.get("canonical_occurrence") or {}
    facts, fact_errors = _fact_map(row)
    errors.extend(fact_errors)
    tension_records = row.get("tension_records", [])
    tension_ids: dict[str, dict[str, Any]] = {}
    if isinstance(tension_records, list):
        for tension_index, tension in enumerate(tension_records):
            tension_id = tension.get("tension_id") if isinstance(tension, dict) else None
            if tension_id in tension_ids:
                errors.append(f"tension_records[{tension_index}]: duplicate tension_id {tension_id}")
            else:
                tension_ids[tension_id] = tension
            if isinstance(tension, dict):
                for fact_id in tension.get("fact_ids", []):
                    if fact_id not in facts:
                        errors.append(
                            f"tension_records[{tension_index}]: fact {fact_id} is not present in this contract"
                        )
    expected_quran = f"quran:{occurrence.get('quran_loc', '')}"
    if occurrence.get("occurrence_id") != expected_quran:
        errors.append("canonical_occurrence: occurrence_id must equal quran:<quran_loc>")
    if occurrence.get("wbw_loc") != f"wbw:{occurrence.get('quran_loc', '')}":
        errors.append("canonical_occurrence: wbw_loc must equal wbw:<quran_loc>")
    if occurrence.get("surface_length") != len(occurrence.get("surface", "")):
        errors.append("canonical_occurrence: surface_length must use Unicode code-point length")

    for index, fact in enumerate(row.get("facts", [])):
        errors.extend(_surface_span_errors(occurrence, fact, index))
        errors.extend(_validate_evidence_semantics(row, fact, index, facts, tension_ids, expected_quran))
        source = fact.get("source") or {}
        source_address = fact.get("source_address") or {}
        if source.get("source_kind") != source_address.get("source_kind"):
            errors.append(f"facts[{index}]: source and source_address kinds must agree")
        if source_address.get("source_kind") == "quran_token" and source_address.get("address") != expected_quran:
            errors.append(f"facts[{index}]: quran source address must name the canonical occurrence")
        for dependent in fact.get("dependent_fact_ids", []):
            if dependent not in facts:
                errors.append(f"facts[{index}]: dependent fact {dependent} is not present in this contract")
        if not (fact.get("ownership") or {}).get("primary"):
            errors.append(f"facts[{index}]: primary ownership is required")
        if fact.get("certification", {}).get("status") == "certified" and fact.get("evidence", {}).get("status") != "certified":
            errors.append(f"facts[{index}]: certified facts require certified evidence status")

    projection = row.get("projection") or {}
    status = projection.get("status")
    unresolved_status = projection.get("unresolved_status")
    learner_visible = projection.get("learner_visible") is True
    claim = projection.get("claim")
    if status == "candidate":
        if unresolved_status is not None:
            errors.append("projection: candidate status cannot carry an unresolved status")
        if learner_visible and not isinstance(claim, dict):
            errors.append("projection: learner-visible candidate requires a typed claim envelope")
    else:
        if unresolved_status != status:
            errors.append("projection: unresolved status must match projection status")
        if learner_visible and claim is not None:
            errors.append("projection: unresolved learner output cannot carry a linguistic claim")
        if learner_visible:
            try:
                expected_statement = learner_statement_for(str(unresolved_status))
            except KeyError:
                errors.append(f"projection: unresolved language mapping missing for {unresolved_status!r}")
            else:
                if projection.get("learner_statement") != expected_statement:
                    errors.append("projection: learner_statement must come from the unresolved language mapping")
            if not any(fact.get("unresolved_blockers") for fact in row.get("facts", [])):
                errors.append("projection: learner-visible unresolved output requires an explicit blocker")

    if learner_visible and status == "candidate":
        if not isinstance(claim, dict):
            errors.append(PROSE_ONLY_ERROR)
            return errors
        bindings = claim.get("fact_bindings") or []
        if not bindings:
            errors.append(PROSE_ONLY_ERROR)
        for binding_index, binding in enumerate(bindings):
            fact_id = binding.get("fact_id")
            fact = facts.get(fact_id)
            prefix = f"projection.claim.fact_bindings[{binding_index}]"
            if fact is None:
                errors.append(f"{prefix}: fact_id {fact_id} is not present in facts")
                continue
            field_path = binding.get("fact_field", "")
            found, _ = _read_path(fact, field_path)
            if not found:
                errors.append(f"{prefix}: fact_field {field_path!r} is not present on the typed fact")
            span_ids = {span.get("span_id") for span in fact.get("surface_spans", [])}
            missing_spans = sorted(set(binding.get("surface_span_ids", [])) - span_ids)
            if missing_spans:
                errors.append(f"{prefix}: surface spans are not covered by the bound fact: {missing_spans}")
            if projection.get("projection_id") not in fact.get("dependent_projection_ids", []):
                errors.append(f"facts[{row['facts'].index(fact)}]: dependent_projection_ids omit the projection")
        public_payload = projection.get("public_payload")
        if isinstance(public_payload, dict) and isinstance(public_payload.get("segments"), list):
            rendered_surface = "".join(str(segment.get("surface", "")) for segment in public_payload["segments"])
            if rendered_surface != occurrence.get("surface"):
                errors.append("projection.public_payload.segments: surfaces do not concatenate exactly")
    return errors


def validate_contract_record(row: dict[str, Any]) -> list[str]:
    """Validate either a governed contract or a historical prose-shaped input."""

    if not isinstance(row, dict):
        return ["projection input must be a JSON object"]
    if row.get("schema") != "qamus.typed_claim_contract.v1":
        if any(key in row for key in ("learner_explanation", "token_contribution_gloss", "public_payload")):
            return [PROSE_ONLY_ERROR]
        return ["projection input does not use qamus.typed_claim_contract.v1"]
    normalized = normalize_aliases(row)
    errors = assert_no_deprecated_aliases(normalized)
    schema_errors = _schema_errors(normalized, _load_json(CONTRACT_SCHEMA_PATH))
    errors.extend(schema_errors)
    # Semantic joins assume the closed schema's object/list shape. Keep the
    # validator fail-closed if malformed input reaches a nested join: schema
    # errors remain visible and the shape failure is returned as validation
    # output instead of escaping as an exception.
    try:
        errors.extend(_validate_projection_semantics(normalized))
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        errors.append(
            "projection input failed semantic shape validation: "
            f"{type(exc).__name__}: {exc}"
        )
    return errors


def validate_legacy_record(row: dict[str, Any]) -> list[str]:
    if not isinstance(row, dict):
        return ["legacy record must be a JSON object"]
    errors = _schema_errors(row, _load_json(LEGACY_SCHEMA_PATH))
    if row.get("learner_visible") is not False:
        errors.append("legacy_valid record learner_visible must be false")
    if row.get("public_materialization_allowed") is not False:
        errors.append("legacy_valid record public_materialization_allowed must be false")
    errors.extend(assert_no_deprecated_aliases(row))
    return errors


def validate_unresolved_language_map(path: Path | None = None) -> dict[str, str]:
    map_path = Path(path or DEFAULT_LANGUAGE_MAP_PATH)
    payload = _load_json(map_path)
    errors = _schema_errors(payload, _load_json(LANGUAGE_SCHEMA_PATH))
    entries = payload.get("entries", [])
    mapping: dict[str, str] = {}
    for index, entry in enumerate(entries):
        status = entry.get("status")
        if status in mapping:
            errors.append(f"entries[{index}]: duplicate unresolved status {status!r}")
        mapping[status] = entry.get("learner_statement", "")
        statement = entry.get("learner_statement", "")
        if not re.search(r"[A-Za-z]", statement):
            errors.append(f"entries[{index}]: learner statement must be plain English")
        for forbidden in ("fact_id", "projector", "qg-", "legacy_valid"):
            if forbidden in statement:
                errors.append(f"entries[{index}]: learner statement leaks internal term {forbidden!r}")
    missing = sorted(PUBLIC_UNRESOLVED_STATUSES - set(mapping))
    if missing:
        errors.append("unresolved language mapping missing statuses: " + ", ".join(missing))
    if errors:
        raise ValueError("; ".join(errors))
    return mapping


def load_unresolved_language_map(path: Path | None = None) -> dict[str, str]:
    return validate_unresolved_language_map(path)


def learner_statement_for(status: str) -> str:
    mapping = load_unresolved_language_map()
    if status not in mapping:
        raise KeyError(status)
    return mapping[status]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows
