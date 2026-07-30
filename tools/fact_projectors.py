#!/usr/bin/env python3
"""Registered, abstention-first projectors over the append-only fact ledger.

Projectors perform deterministic lookup against caller-supplied documented
forms or construction patterns. They create candidates only; review and
materialization remain explicit ledger transitions.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fact_ledger
from tools import normalize_ar


ROOT = Path(__file__).resolve().parents[1]
PROJECTOR_SCHEMA_PATH = ROOT / "qamus" / "schemas" / "projector-record.schema.json"
SARF_PROJECTOR_ID = "sarf.documented_form.v1"
NAHW_PROJECTOR_ID = "nahw.particle_function.v1"
# RM-40 staged paradigm-licensed generation. Distinct output_fact_type keeps it
# out of the documented-form lookup plane, and gate_tier is two_vote_required so
# a generated form can NEVER auto-promote the way a documented-form lookup can.
SARF_GENERATED_PROJECTOR_ID = "sarf.paradigm_generated.v1"
TRANCHE1_SARF_PROJECTOR_ID = "sarf.tranche1_fixture_projection.v1"
TRANCHE1_NAHW_PROJECTOR_ID = "nahw.tranche1_fixture_projection.v1"
FAM2_LEXICAL_PROJECTOR_ID = "sarf.fam2.lexical_formation.v1"
FAM3_NUMBER_PROJECTOR_ID = "sarf.fam3.number_formation.v1"
FAM4_FINITE_VERB_PROJECTOR_ID = "sarf.fam4.finite_verb.v1"
FAM5_DERIVED_VERB_PROJECTOR_ID = "sarf.fam5.derived_verb.v1"
PROOFV_VERB_PROJECTOR_ID = "sarf.proofv.verb.v1"
# A3 largelexicon bridge. Its gate_tier is never_auto_resolve: a carried-table
# lookup is candidate evidence about a written surface, never a certification of
# lexical identity, so this projector has NO path to certified or materialized.
LARGELEXICON_BRIDGE_PROJECTOR_ID = "largelexicon.carried_lexeme_candidate.v1"


class ProjectorValidationError(ValueError):
    """Raised when registration, projection, or review fails closed."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_gate_tiers() -> Dict[str, Dict[str, Any]]:
    """Load the gate SSOT at the exact path owned by the ledger module."""

    # Exercise the ledger's loader/mapping validation before consuming the SSOT.
    fact_ledger._two_vote_fact_types(fact_ledger.load_schema(), fact_ledger.GATE_PATH)
    with fact_ledger.GATE_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    gates = payload.get("gates")
    if not isinstance(gates, dict) or "two_vote_required" not in gates:
        raise ProjectorValidationError("gate SSOT lacks two_vote_required")
    return gates


def validate_projector_record(record: Dict[str, Any]) -> List[str]:
    with PROJECTOR_SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    errors: List[str] = []
    fact_ledger._validate_node(record, schema, "$", errors, schema)
    return errors


class ProjectorRegistry:
    """Small fail-closed registry of fact-family-specific projector functions."""

    def __init__(self) -> None:
        self._entries: Dict[str, tuple[Dict[str, Any], Callable[..., Dict[str, Any]]]] = {}

    def register(
        self, contract: Dict[str, Any], projector: Callable[..., Dict[str, Any]]
    ) -> None:
        errors = validate_projector_record(contract)
        if not contract.get("defeater_checks"):
            errors.append("defeater_checks must be non-empty")
        for name in contract.get("defeater_checks") or []:
            if not callable(globals().get(name)):
                errors.append("defeater check is not a callable function: " + name)
        if contract.get("gate_tier") not in load_gate_tiers():
            errors.append("gate_tier is absent from the gate SSOT")
        projector_id = contract.get("projector_id")
        if projector_id in self._entries:
            errors.append("projector_id is already registered")
        if errors:
            raise ProjectorValidationError("invalid projector contract: " + "; ".join(errors))
        self._entries[projector_id] = (copy.deepcopy(contract), projector)

    def list_contracts(self) -> List[Dict[str, Any]]:
        return [copy.deepcopy(self._entries[key][0]) for key in sorted(self._entries)]

    def contract(self, projector_id: str) -> Dict[str, Any]:
        if projector_id not in self._entries:
            raise ProjectorValidationError("unregistered projector: " + projector_id)
        return copy.deepcopy(self._entries[projector_id][0])

    def run(self, projector_id: str, **kwargs: Any) -> Dict[str, Any]:
        if projector_id not in self._entries:
            raise ProjectorValidationError("unregistered projector: " + projector_id)
        contract, projector = self._entries[projector_id]
        return projector(contract=copy.deepcopy(contract), **kwargs)


def _has_harakah(surface: str) -> bool:
    return any(0x064B <= ord(ch) <= 0x0652 for ch in unicodedata.normalize("NFC", surface))


def homograph_norm_key_collision(occurrence: Dict[str, Any], form: Dict[str, Any]) -> Optional[str]:
    surface = occurrence.get("surface", "")
    documented = form.get("surface", "")
    if (
        surface != documented
        and _has_harakah(surface)
        and _has_harakah(documented)
        and normalize_ar.norm_strict(surface) == normalize_ar.norm_strict(documented)
    ):
        return "vocalized surfaces collide after the strict key drops harakat/shadda"
    return None


def harakah_blind_sole_candidate(occurrence: Dict[str, Any], form: Dict[str, Any]) -> Optional[str]:
    surface = occurrence.get("surface", "")
    documented = form.get("surface", "")
    if not _has_harakah(surface) and _has_harakah(documented) and surface != documented:
        return "the sole lookup match is harakah-blind"
    return None


def liaison_clitic_mismatch(occurrence: Dict[str, Any], form: Dict[str, Any]) -> Optional[str]:
    if list(occurrence.get("clitics") or []) != list(form.get("clitics") or []):
        return "occurrence clitic segmentation differs from the documented form row"
    if bool(occurrence.get("liaison", False)) != bool(form.get("liaison", False)):
        return "occurrence liaison state differs from the documented form row"
    return None


def particle_vowel_distinction(
    occurrence: Dict[str, Any], pattern: Dict[str, Any]
) -> Optional[str]:
    surface = occurrence.get("surface", "")
    documented = pattern.get("particle_surface", "")
    if normalize_ar.norm_strict(surface) != normalize_ar.norm_strict(documented):
        return None
    if surface == documented:
        return None
    if normalize_ar.haraka_on(surface, "م") != normalize_ar.haraka_on(documented, "م"):
        return "content-letter vowel distinguishes man from min"
    return None


def la_family_ambiguity(occurrence: Dict[str, Any], pattern: Dict[str, Any]) -> Optional[str]:
    if normalize_ar.norm_strict(occurrence.get("surface", "")) != "لا":
        return None
    if pattern.get("competing_functions") and not occurrence.get("context"):
        return "la function has no deterministic nafiya/nahiya context signal"
    return None


def construction_context_mismatch(
    occurrence: Dict[str, Any], pattern: Dict[str, Any]
) -> Optional[str]:
    actual = occurrence.get("context") or {}
    required = pattern.get("context_equals") or {}
    if any(actual.get(key) != value for key, value in required.items()):
        return "occurrence context does not match the documented construction pattern"
    return None


def fam2_lexical_orthography_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named registration guard; FAM2 performs the exact pair check itself."""

    return None


def fam4_finite_verb_evidence_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named registry guard; FAM4 performs letter-level checks itself."""

    return None


def fam5_derived_verb_evidence_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named registry guard; FAM5 performs source and ownership checks itself."""

    return None


def proofv_verb_evidence_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named registry guard; PROOF-V keeps source gaps explicit."""

    return None


def largelexicon_bridge_abstention_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named registry guard; the bridge performs loc-first and collision checks itself."""

    return None


def project_largelexicon_carried_lexeme(
    *,
    contract: Dict[str, Any],
    crosswalk_row: Dict[str, Any],
    inputs: Any,
    carried: bool = True,
) -> Dict[str, Any]:
    """Run the A3 bridge as a registry call: candidate or abstention, never more."""

    from tools import largelexicon_fact_bridge as bridge

    record = bridge.bridge_row(crosswalk_row, inputs, carried=carried)
    errors = bridge.validate_records([record])
    if errors:
        raise ProjectorValidationError("bridge record is not a valid typed claim: " + "; ".join(errors[:3]))
    projection = record["projection"]
    candidates = [fact for fact in record["facts"] if fact["fact_type"] == "largelexicon_lexeme_candidate"]
    resolved = projection["status"] == "candidate"
    # The wrapper must never relabel the enclosed fact: it reports the evidence
    # mode the fact actually carries, and refuses to emit a disagreeing summary.
    modes = sorted({fact["evidence_mode"] for fact in candidates})
    if resolved and len(modes) != 1:
        raise ProjectorValidationError("bridge candidates disagree on evidence_mode: " + ",".join(modes))
    evidence_mode = modes[0] if modes else "unresolved"
    return {
        "projector_id": contract["projector_id"],
        "status": "candidate" if resolved else "abstained",
        "route": projection["status"],
        "candidate": {
            "fact_type": contract["output_fact_type"],
            "fact_ids": [fact["fact_id"] for fact in candidates],
            "candidates_preserved": len(candidates),
            "evidence_mode": evidence_mode,
        }
        if resolved
        else None,
        "preserved_candidate_fact_ids": [fact["fact_id"] for fact in candidates],
        "blockers": sorted(
            {
                blocker["blocker_id"]
                for fact in record["facts"]
                for blocker in fact.get("unresolved_blockers") or []
            }
        ),
        "evidence_mode": evidence_mode,
        "typed_claim_record": record,
        "certification_allowed": False,
        "materialization_allowed": False,
    }


def project_proofv_verb(
    *,
    contract: Dict[str, Any],
    source_row: Dict[str, Any],
    nearest: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Run the bounded PROOF-V producer without enabling materialization."""

    from tools import proofv_verb_producer

    proof = proofv_verb_producer.build_verb_facts(source_row, nearest=nearest)
    candidate = proof.get("status") == "candidate_with_source_gaps"
    return {
        "projector_id": contract["projector_id"],
        "status": "candidate" if candidate else "abstained",
        "route": proof.get("status"),
        "candidate": {
            "fact_type": "proofv_verb_evidence",
            "fact_ids": [fact.get("fact_id") for fact in proof.get("facts", []) if fact.get("fact_type") == "derived_verb_evidence"],
            "candidate_status": proof.get("status"),
            "evidence_mode": "cross_source_corroboration",
        } if candidate else None,
        "materialization_allowed": False,
    }


def project_fam4_finite_verb_pattern(
    *,
    contract: Dict[str, Any],
    surface: str,
    root: str | Iterable[str],
    pattern_id: str,
    affix_registry: Any = None,
) -> Dict[str, Any]:
    """Run the closed FAM4 Form-I matcher as a candidate-only registry call."""

    from tools import fam4_finite_verb_producer as fam4

    registry = fam4.load_affix_registry(affix_registry) if isinstance(affix_registry, (str, Path)) else (
        affix_registry or fam4.load_affix_registry()
    )
    pattern = next((item for item in registry if item.get("pattern_id") == pattern_id), None)
    if isinstance(root, str):
        radicals = [char for char in root if char not in " \t\n" and unicodedata.category(char) != "Mn"]
    else:
        radicals = [str(item) for item in root]
    matched = fam4._match_registered_pattern(surface, radicals, pattern or {}) if pattern else None
    if matched is None:
        return {
            "projector_id": contract["projector_id"],
            "status": "abstained",
            "route": "pattern_unresolved",
            "candidate": None,
            "materialization_allowed": False,
        }
    return {
        "projector_id": contract["projector_id"],
        "status": "candidate",
        "route": "entry_backed_form_i_pattern",
        "candidate": {
            "fact_type": "finite_verb_evidence",
            "pattern_id": pattern_id,
            "form": pattern["form"],
            "tense_aspect": pattern["tense_aspect"],
            "person": pattern["person"],
            "number": pattern["number"],
            "gender": pattern["gender"],
            "voice": pattern["voice"],
            "evidence_mode": "deterministic_derivation_from_certified_facts",
        },
        "materialization_allowed": False,
    }


def project_fam5_derived_verb_pattern(
    *,
    contract: Dict[str, Any],
    surface: str,
    root: str | Iterable[str],
    pattern_id: str,
    form_registry: Any = None,
    entry_surface: str | None = None,
    evidence_certified: bool = False,
    v575_verified: bool = False,
) -> Dict[str, Any]:
    """Run the closed FAM5 matcher only after caller-supplied evidence gates."""

    from tools import fam5_derived_verb_producer as fam5

    if not evidence_certified or not v575_verified or entry_surface != surface:
        return {
            "projector_id": contract["projector_id"],
            "status": "abstained",
            "route": "source_gap",
            "candidate": None,
            "materialization_allowed": False,
        }
    registry = fam5.load_derived_form_registry(form_registry) if isinstance(form_registry, (str, Path)) else (
        list(form_registry) if form_registry is not None else fam5.load_derived_form_registry()
    )
    if isinstance(root, str):
        radicals = [char for char in root if char not in " \t\n" and unicodedata.category(char) != "Mn"]
    else:
        radicals = [str(item) for item in root]
    pattern = next((item for item in registry if item.get("pattern_id") == pattern_id), None)
    matched = fam5._match_pattern(surface, radicals, pattern or {}, {"source_grounding": "entry_form_attestation"}) if pattern else None
    if matched is None:
        return {
            "projector_id": contract["projector_id"],
            "status": "abstained",
            "route": "template_unresolved",
            "candidate": None,
            "materialization_allowed": False,
        }
    return {
        "projector_id": contract["projector_id"],
        "status": "candidate",
        "route": "entry_backed_derived_form_pattern",
        "candidate": {
            "fact_type": "derived_verb_evidence",
            "pattern_id": pattern_id,
            "form": pattern["form"],
            "template": pattern["template"],
            "derivational_class": pattern.get("derivational_class"),
            "evidence_mode": "deterministic_derivation_from_certified_facts",
        },
        "materialization_allowed": False,
    }


def project_fam2_lexical_pattern(
    *,
    contract: Dict[str, Any],
    singular_surface: str,
    plural_surface: str,
    pattern_id: str,
    pattern_registry: Any = None,
) -> Dict[str, Any]:
    """Run the registered FAM2 pattern projector in candidate mode only."""

    from tools.fam2_lexical_producer import match_registered_pattern

    matched = match_registered_pattern(
        singular_surface,
        plural_surface,
        pattern_id,
        pattern_registry,
    )
    if matched is None:
        return {
            "projector_id": contract["projector_id"],
            "status": "abstained",
            "route": "pattern_unresolved",
            "candidate": None,
            "materialization_allowed": False,
        }
    return {
        "projector_id": contract["projector_id"],
        "status": "candidate",
        "route": "entry_backed_named_pattern_match",
        "candidate": {
            "fact_type": "formation_evidence",
            "pattern_id": matched["pattern_id"],
            "sub_shape": matched["sub_shape"],
            "singular_surface": matched["singular_surface"],
            "plural_surface": matched["plural_surface"],
            "evidence_mode": "paired_form_inference",
        },
        "materialization_allowed": False,
    }


def fam3_number_orthography_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named registration guard; FAM3 performs exact matching in its registry."""

    return None


def project_fam3_number_pattern(
    *,
    contract: Dict[str, Any],
    base_surface: str,
    observed_surface: str,
    pattern_id: str,
    context: Optional[Dict[str, Any]] = None,
    pattern_registry: Any = None,
) -> Dict[str, Any]:
    """Run the registered FAM3 number projector in candidate mode only."""

    from tools.fam3_number_producer import match_registered_number_pattern

    matched = match_registered_number_pattern(
        base_surface,
        observed_surface,
        pattern_id,
        context=context,
        registry=pattern_registry,
    )
    if matched is None:
        return {
            "projector_id": contract["projector_id"],
            "status": "abstained",
            "route": "pattern_unresolved",
            "candidate": None,
            "materialization_allowed": False,
        }
    return {
        "projector_id": contract["projector_id"],
        "status": "candidate",
        "route": "entry_backed_registered_number_pattern",
        "candidate": {
            "fact_type": "formation_evidence",
            "pattern_id": matched["pattern_id"],
            "sub_shape": matched["sub_shape"],
            "base_surface": matched["base_surface"],
            "observed_surface": matched["observed_surface"],
            "evidence_mode": "paired_form_inference",
        },
        "materialization_allowed": False,
    }


def _source_gate(
    store: fact_ledger.FactLedgerStore,
    source_fact: Dict[str, Any],
    contract: Dict[str, Any],
) -> None:
    if source_fact.get("certification_state") != "certified":
        raise ProjectorValidationError("projector input must be a certified source fact")
    if source_fact.get("fact_type") not in contract["input_fact_types"]:
        raise ProjectorValidationError("source fact type is outside the projector contract")
    errors = fact_ledger.validate_schema(source_fact)
    if errors or fact_ledger.compute_fact_id(source_fact) != source_fact.get("fact_id"):
        raise ProjectorValidationError("source fact is not a valid ledger fact")
    current = store.query(fact_id=source_fact["fact_id"])
    if not current or current[0] != source_fact:
        raise ProjectorValidationError("source fact is not the current ledger revision")


def _run_record(
    contract: Dict[str, Any], source_fact: Dict[str, Any], started_at: str, finished_at: str
) -> Dict[str, Any]:
    runtime_ms = round((_parse_time(finished_at) - _parse_time(started_at)).total_seconds() * 1000)
    if runtime_ms < 0:
        raise ProjectorValidationError("finished_at precedes started_at")
    return {
        "schema": "qamus.projector_record.v1",
        "record_type": "projection_run",
        "projector_id": contract["projector_id"],
        "version": contract["version"],
        "inputs": [{"fact_id": source_fact["fact_id"], "hash": _hash(source_fact)}],
        "candidates_generated": [],
        "abstentions": [],
        "certifications": [],
        "review_votes": [],
        "materializations": [],
        "superseded_dependents": [],
        "started_at": started_at,
        "finished_at": finished_at,
        "runtime_ms": runtime_ms,
        "resolution_method": contract["resolution_method"],
    }


def _prior_by_identity(prior_candidates: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        _canonical(item["subject_identity"]): item
        for item in prior_candidates
        if isinstance(item, dict) and item.get("subject_identity")
    }


def _candidate_row(
    *,
    contract: Dict[str, Any],
    source_fact: Dict[str, Any],
    occurrence: Dict[str, Any],
    value: Any,
    evidence_id: str,
    evidence_detail: str,
    derivation_hash: str,
    created_at: str,
    prior: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    identity = copy.deepcopy(occurrence["identity"])
    loc = identity["loc"]
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": identity,
        "fact_type": contract["output_fact_type"],
        "candidate_or_value": {
            "value": value,
            "competing_alternatives": [],
            "semantic_tie": False,
        },
        "scope": "occurrence",
        "source_address": {"address": "quran:" + loc, "source_kind": "quran_token"},
        "evidence": [
            {
                "evidence_id": evidence_id,
                "type": "deterministic_derivation",
                "detail": evidence_detail,
                "source_address": source_fact["source_address"]["address"],
            }
        ],
        "provenance": {
            "actor": contract["projector_id"],
            "method": contract["resolution_method"],
            "created_at": created_at,
            "input_hashes": {
                "source_fact": source_fact["fact_id"],
                "documented_row": derivation_hash,
            },
        },
        "review_votes": [],
        "certification_state": "candidate",
        "confidence_or_calibration": None,
        "defeaters": [],
        "exceptions": [],
        "dependency_hashes": {
            "source_fact": source_fact["fact_id"],
            "documented_row": derivation_hash,
        },
        "materialization_targets": [],
        "supersedes": None,
        "created_from": prior["fact_id"] if prior else "projector:" + contract["projector_id"],
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def _abstention(
    occurrence: Dict[str, Any], name: str, detail: str, resolution: str = "abstained"
) -> Dict[str, Any]:
    return {
        "subject_identity": copy.deepcopy(occurrence["identity"]),
        "defeater_name": name,
        "detail": detail,
        "resolution": resolution,
    }


def project_sarf_documented_forms(
    *,
    contract: Dict[str, Any],
    store: fact_ledger.FactLedgerStore,
    source_fact: Dict[str, Any],
    occurrences: Iterable[Dict[str, Any]],
    documented_forms: Iterable[Dict[str, Any]],
    created_at: str,
    started_at: str,
    finished_at: str,
    prior_candidates: Iterable[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    _source_gate(store, source_fact, contract)
    run = _run_record(contract, source_fact, started_at, finished_at)
    forms = list(documented_forms)
    prior = _prior_by_identity(prior_candidates)
    source_entry = source_fact["subject_identity"]["id"].split(":", 1)[-1]
    for occurrence in occurrences:
        matches = [
            form
            for form in forms
            if form.get("entry_id") == source_entry
            and normalize_ar.norm_strict(form.get("surface", ""))
            == normalize_ar.norm_strict(occurrence.get("surface", ""))
        ]
        if not matches:
            continue
        form = matches[0]
        fired = None
        for name, check in (
            ("homograph_norm_key_collision", homograph_norm_key_collision),
            ("harakah_blind_sole_candidate", harakah_blind_sole_candidate),
            ("liaison_clitic_mismatch", liaison_clitic_mismatch),
        ):
            detail = check(occurrence, form)
            if detail:
                fired = _abstention(occurrence, name, detail)
                break
        if fired:
            run["abstentions"].append(fired)
            continue
        previous = prior.get(_canonical(occurrence["identity"]))
        row = _candidate_row(
            contract=contract,
            source_fact=source_fact,
            occurrence=occurrence,
            value={
                "documented_form_id": form["form_id"],
                "sarf_form": form["sarf_form"],
                "source_value": source_fact["candidate_or_value"]["value"],
                "surface": occurrence["surface"],
            },
            evidence_id="ev-form-" + form["form_id"],
            evidence_detail="documented form row " + form["form_id"],
            derivation_hash=_hash(form),
            created_at=created_at,
            prior=previous,
        )
        store.append(row)
        run["candidates_generated"].append(row["fact_id"])
        if previous:
            run["superseded_dependents"].append(previous["fact_id"])
    errors = validate_projector_record(run)
    if errors:
        raise ProjectorValidationError("invalid projection run: " + "; ".join(errors))
    return run


def project_nahw_particle_functions(
    *,
    contract: Dict[str, Any],
    store: fact_ledger.FactLedgerStore,
    source_fact: Dict[str, Any],
    occurrences: Iterable[Dict[str, Any]],
    construction_patterns: Iterable[Dict[str, Any]],
    created_at: str,
    started_at: str,
    finished_at: str,
    prior_candidates: Iterable[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    _source_gate(store, source_fact, contract)
    run = _run_record(contract, source_fact, started_at, finished_at)
    patterns = list(construction_patterns)
    prior = _prior_by_identity(prior_candidates)
    for occurrence in occurrences:
        matches = [
            pattern
            for pattern in patterns
            if normalize_ar.norm_strict(pattern.get("particle_surface", ""))
            == normalize_ar.norm_strict(occurrence.get("surface", ""))
        ]
        if not matches:
            continue
        pattern = matches[0]
        vowel = particle_vowel_distinction(occurrence, pattern)
        if vowel:
            run["abstentions"].append(
                _abstention(occurrence, "particle_vowel_distinction", vowel)
            )
            continue
        la_tie = la_family_ambiguity(occurrence, pattern)
        if la_tie:
            run["abstentions"].append(
                _abstention(occurrence, "la_family_ambiguity", la_tie, "tie_unresolved")
            )
            continue
        mismatch = construction_context_mismatch(occurrence, pattern)
        if mismatch:
            run["abstentions"].append(
                _abstention(occurrence, "construction_context_mismatch", mismatch)
            )
            continue
        if pattern.get("function") != source_fact["candidate_or_value"]["value"]:
            continue
        previous = prior.get(_canonical(occurrence["identity"]))
        row = _candidate_row(
            contract=contract,
            source_fact=source_fact,
            occurrence=occurrence,
            value={
                "construction_pattern_id": pattern["pattern_id"],
                "function": pattern["function"],
                "surface": occurrence["surface"],
            },
            evidence_id="ev-pattern-" + pattern["pattern_id"],
            evidence_detail="documented construction pattern " + pattern["pattern_id"],
            derivation_hash=_hash(pattern),
            created_at=created_at,
            prior=previous,
        )
        store.append(row)
        run["candidates_generated"].append(row["fact_id"])
        if previous:
            run["superseded_dependents"].append(previous["fact_id"])
    errors = validate_projector_record(run)
    if errors:
        raise ProjectorValidationError("invalid projection run: " + "; ".join(errors))
    return run


def project_sarf_paradigm_generated(
    *,
    contract: Dict[str, Any],
    lexeme: Dict[str, Any],
    store_dir: Any,
    started_at: str,
    finished_at: str,
    baseline_forms: Iterable[Dict[str, Any]] = (),
    slots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """RM-40 paradigm-licensed generation: emit candidate rows into a disjoint store.

    Generated forms are candidates-never-facts. They are written to their own
    append-only ``generated-candidates`` store (never the sourced baseline table
    and never the fact ledger's certified plane). This projector's run record is
    inspectable like the documented-form projectors, but its candidates ride the
    two_vote_required gate and are not deployment-eligible (see
    ``build_append_queue.is_generation_deploy_eligible``).
    """
    from tools import fusha_paradigm_generate as generator

    lexeme_hash = _hash(lexeme)
    run = {
        "schema": "qamus.projector_record.v1",
        "record_type": "projection_run",
        "projector_id": contract["projector_id"],
        "version": contract["version"],
        "inputs": [{"fact_id": lexeme_hash, "hash": lexeme_hash}],
        "candidates_generated": [],
        "abstentions": [],
        "certifications": [],
        "review_votes": [],
        "materializations": [],
        "superseded_dependents": [],
        "started_at": started_at,
        "finished_at": finished_at,
        "runtime_ms": max(
            0, round((_parse_time(finished_at) - _parse_time(started_at)).total_seconds() * 1000)
        ),
        "resolution_method": contract["resolution_method"],
    }
    if str(lexeme.get("pos")) == "noun":
        rows = generator.generate_noun_plural(lexeme, baseline_forms=baseline_forms)
    else:
        rows = generator.generate_verb(lexeme, slots=slots, baseline_forms=baseline_forms)
    if rows:
        generator.write_candidates(store_dir, rows)
        run["candidates_generated"] = [row["candidate_id"] for row in rows]
    errors = validate_projector_record(run)
    if errors:
        raise ProjectorValidationError("invalid generation run: " + "; ".join(errors))
    return run


def review_and_materialize(
    store: fact_ledger.FactLedgerStore,
    fact_id: str,
    review_votes: List[Dict[str, Any]],
    target: str,
    run_record: Dict[str, Any],
) -> Dict[str, Any]:
    current = store.query(fact_id=fact_id)
    if not current:
        raise ProjectorValidationError("unknown candidate fact_id: " + fact_id)
    row = current[0]
    contracts = {
        contract["output_fact_type"]: contract for contract in REGISTRY.list_contracts()
    }
    contract = contracts.get(row["fact_type"])
    if contract is None:
        raise ProjectorValidationError("candidate has no registered projector contract")
    if contract["gate_tier"] == "never_auto_resolve":
        # Gate SSOT: never_auto_resolve means "reject — never ship; quarantine or
        # pending with the precise blocker". There is no vote count that opens it.
        raise ProjectorValidationError(
            "never_auto_resolve projectors may never certify or materialize: " + contract["projector_id"]
        )
    if contract["gate_tier"] == "two_vote_required":
        approvals = {
            vote["voter_id"]
            for vote in review_votes
            if vote.get("independent") and vote.get("vote") == "approve"
        }
        if len(approvals) < 2:
            raise ProjectorValidationError(
                "two independent approving votes are required by the gate SSOT"
            )
    store.transition(fact_id, "review_required", review_votes=review_votes)
    store.transition(fact_id, "certified", review_votes=review_votes)
    materialized = store.transition(
        fact_id, "materialized", materialization_targets=[target], review_votes=review_votes
    )
    run_record["review_votes"].extend(copy.deepcopy(review_votes))
    run_record["certifications"].append(fact_id)
    run_record["materializations"].append(fact_id)
    errors = validate_projector_record(run_record)
    if errors:
        raise ProjectorValidationError("invalid updated run record: " + "; ".join(errors))
    return materialized


def aggregate_projection_runs(runs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate caller-timestamped runs without consulting the wall clock."""

    rows = list(runs)
    candidate_count = sum(len(row.get("candidates_generated", [])) for row in rows)
    certification_count = sum(len(row.get("certifications", [])) for row in rows)
    abstention_count = sum(len(row.get("abstentions", [])) for row in rows)
    if not rows:
        hours = 0.0
    else:
        started = min(_parse_time(row["started_at"]) for row in rows)
        finished = max(_parse_time(row["finished_at"]) for row in rows)
        hours = (finished - started).total_seconds() / 3600
    return {
        "run_count": len(rows),
        "candidate_count": candidate_count,
        "certification_count": certification_count,
        "abstention_count": abstention_count,
        "elapsed_hours": hours,
        "facts_per_hour": candidate_count / hours if hours > 0 else None,
    }


def tranche1_fixture_policy_guard(*_args: Any, **_kwargs: Any) -> None:
    """Named contract guard; the lattice runner performs the actual checks."""

    return None


def project_tranche1_fixture(
    *,
    contract: Dict[str, Any],
    source_row: Dict[str, Any],
    policy: Dict[str, Any],
    fact_ids: List[str],
) -> Dict[str, Any]:
    """Delegate a fixture-only candidate or typed abstention to its lattice path."""

    from tools import lattice_projectors

    registered = {
        row["projector_id"]: row
        for row in lattice_projectors.load_registry()["registered"]
    }
    projector_id = contract["projector_id"]
    if projector_id not in registered:
        raise ProjectorValidationError("lattice registry lacks projector: " + projector_id)
    lattice_entry = registered[projector_id]
    embedded = lattice_entry["registry_entry"]
    for field in ("fact_family", "version", "producer"):
        if embedded.get(field) != contract.get(field):
            raise ProjectorValidationError(
                "fact/lattice projector contract mismatch for %s: %s" % (projector_id, field)
            )
    return lattice_projectors.run_tranche1_fixture_projector(
        lattice_entry,
        source_row,
        policy,
        fact_ids=fact_ids,
    )


SARF_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "projector_id": SARF_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["root_assignment", "sarf_form"],
    "output_fact_type": "sarf_form",
    "compatibility_class": (
        "occurrences whose norm_strict surface matches a documented form row "
        "for the certified lexeme; lookup only, with no generated morphology"
    ),
    "defeater_checks": [
        "homograph_norm_key_collision",
        "harakah_blind_sole_candidate",
        "liaison_clitic_mismatch",
    ],
    "gate_tier": "auto_safe",
    "version": "1.0.0",
    "resolution_method": "documented_form_lookup",
}

NAHW_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "projector_id": NAHW_PROJECTOR_ID,
    "fact_family": "nahw",
    "input_fact_types": ["particle_function"],
    "output_fact_type": "particle_function",
    "compatibility_class": (
        "occurrences of the same particle surface whose caller-supplied context "
        "matches a documented deterministic construction pattern"
    ),
    "defeater_checks": [
        "particle_vowel_distinction",
        "la_family_ambiguity",
        "construction_context_mismatch",
    ],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "documented_surface_context_lookup",
}

SARF_GENERATED_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "projector_id": SARF_GENERATED_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["root_assignment", "sarf_form"],
    "output_fact_type": "sarf_generated_form",
    "compatibility_class": (
        "regular paradigm cells synthesised for a certified lexeme (root+measure) "
        "that the documented-form baseline lacks; candidates-never-facts, written to "
        "a disjoint generated-candidates store, never merged into the sourced baseline"
    ),
    "defeater_checks": [
        "homograph_norm_key_collision",
        "harakah_blind_sole_candidate",
    ],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "paradigm_licensed_generation",
}

TRANCHE1_SARF_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.tranche1_projection",
    "projector_id": TRANCHE1_SARF_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["surface_observation"],
    "output_fact_type": "morphology_projection_candidate",
    "compatibility_class": "Q7 fixture rows whose exact surface and typed status pass the tranche-local policy guards",
    "defeater_checks": ["tranche1_fixture_policy_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "fixture_policy_projection",
}

TRANCHE1_NAHW_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.tranche1_projection",
    "projector_id": TRANCHE1_NAHW_PROJECTOR_ID,
    "fact_family": "nahw",
    "input_fact_types": ["surface_observation"],
    "output_fact_type": "syntax_projection_candidate",
    "compatibility_class": "Q7 fixture rows whose exact surface and typed status pass the tranche-local policy guards",
    "defeater_checks": ["tranche1_fixture_policy_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "fixture_policy_projection",
}

FAM2_LEXICAL_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.fam2_lexical_producer",
    "projector_id": FAM2_LEXICAL_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["entry_form_pair"],
    "output_fact_type": "formation_evidence",
    "compatibility_class": (
        "entry-backed lexical noun/adjective pairs whose exact written forms match one named FAM2 formation pattern; "
        "label-only, orthographic-variant, and unresolved pairs abstain"
    ),
    "defeater_checks": ["fam2_lexical_orthography_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "entry_backed_named_pattern_match",
}

FAM3_NUMBER_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.fam3_number_producer",
    "projector_id": FAM3_NUMBER_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["entry_base_attestation"],
    "output_fact_type": "formation_evidence",
    "compatibility_class": (
        "entry-backed number-word bases whose exact written surface and local context match one named FAM3 number pattern; "
        "labels, context-only joins, orthographic variants, and ambiguous homographs abstain"
    ),
    "defeater_checks": ["fam3_number_orthography_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "entry_backed_registered_number_pattern",
}

FAM4_FINITE_VERB_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.fam4_finite_verb_producer",
    "projector_id": FAM4_FINITE_VERB_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["entry_form_attestation"],
    "output_fact_type": "finite_verb_evidence",
    "compatibility_class": (
        "exact entry-backed Form-I finite-verb surfaces with letter-level root and owned affix reconstruction; "
        "derived, weak-root, non-finite, and label-only rows abstain"
    ),
    "defeater_checks": ["fam4_finite_verb_evidence_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "entry_backed_form_i_letter_reconstruction",
}

FAM5_DERIVED_VERB_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.fam5_derived_verb_producer",
    "projector_id": FAM5_DERIVED_VERB_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["entry_form_attestation"],
    "output_fact_type": "derived_verb_evidence",
    "compatibility_class": (
        "exact entry-backed derived-verb surfaces whose closed Form-II, Form-IV, Form-VIII, or quadriliteral registry pattern "
        "reconstructs root, derivational additions, inflection, weak operations, voice, and letter ownership; "
        "surface-template-only, weak-root, assimilation, gemination-boundary, hamzat-al-wasl, and ambiguous joins abstain"
    ),
    "defeater_checks": ["fam5_derived_verb_evidence_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "entry_backed_closed_derived_form_letter_reconstruction",
}

PROOFV_VERB_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.proofv_verb_producer",
    "projector_id": PROOFV_VERB_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["entry_form_attestation", "lexeme_entry_edge"],
    "output_fact_type": "proofv_verb_evidence",
    "compatibility_class": (
        "the one surveyed PROOF-V target occurrence with a caller-supplied same-lexeme crosswalk witness; "
        "direct target gaps remain visible and no candidate enables materialization"
    ),
    "defeater_checks": ["proofv_verb_evidence_guard"],
    "gate_tier": "two_vote_required",
    "version": "1.0.0",
    "resolution_method": "bounded_same_lexeme_crosswalk_candidate",
}

LARGELEXICON_BRIDGE_CONTRACT = {
    "schema": "qamus.projector_record.v1",
    "record_type": "registry_entry",
    "producer": "tools.largelexicon_fact_bridge",
    "projector_id": LARGELEXICON_BRIDGE_PROJECTOR_ID,
    "fact_family": "sarf",
    "input_fact_types": ["largelexicon_carried_crosswalk_row", "largelexicon_carried_form_row"],
    "output_fact_type": "largelexicon_lexeme_candidate",
    "compatibility_class": (
        "canonical occurrences addressed loc-first by an ACCEPTED carried target-schema crosswalk row, "
        "whose written surface is documented byte-exactly by carried lemma/form/stem rows; "
        "the crosswalk entry_id is page context and never a lexical edge, normalized-only matches, "
        "root-family relations, candidate graph edges, quarantined rows and multi-entry collisions all abstain"
    ),
    "defeater_checks": ["largelexicon_bridge_abstention_guard"],
    "gate_tier": "never_auto_resolve",
    "version": "1.0.0",
    "resolution_method": "carried_target_schema_loc_first_exact_surface_candidate",
}

REGISTRY = ProjectorRegistry()
REGISTRY.register(SARF_CONTRACT, project_sarf_documented_forms)
REGISTRY.register(NAHW_CONTRACT, project_nahw_particle_functions)
REGISTRY.register(SARF_GENERATED_CONTRACT, project_sarf_paradigm_generated)
REGISTRY.register(TRANCHE1_SARF_CONTRACT, project_tranche1_fixture)
REGISTRY.register(TRANCHE1_NAHW_CONTRACT, project_tranche1_fixture)
REGISTRY.register(FAM2_LEXICAL_CONTRACT, project_fam2_lexical_pattern)
REGISTRY.register(FAM3_NUMBER_CONTRACT, project_fam3_number_pattern)
REGISTRY.register(FAM4_FINITE_VERB_CONTRACT, project_fam4_finite_verb_pattern)
REGISTRY.register(FAM5_DERIVED_VERB_CONTRACT, project_fam5_derived_verb_pattern)
REGISTRY.register(PROOFV_VERB_CONTRACT, project_proofv_verb)
REGISTRY.register(LARGELEXICON_BRIDGE_CONTRACT, project_largelexicon_carried_lexeme)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    list_parser = subparsers.add_parser("list", help="list registered projector contracts")
    list_parser.add_argument("--json", action="store_true", help="emit inspectable JSON")
    args = parser.parse_args(argv)
    if args.command != "list":
        parser.error("the list command is required")
    contracts = REGISTRY.list_contracts()
    if args.json:
        print(json.dumps(contracts, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        for contract in contracts:
            print(
                "%s %s -> %s (%s)"
                % (
                    contract["projector_id"],
                    ",".join(contract["input_fact_types"]),
                    contract["output_fact_type"],
                    contract["gate_tier"],
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
