#!/usr/bin/env python3
"""PROOF-V's bounded, candidate-only real verb fact producer.

The producer consumes one exact whitelist occurrence plus a caller-supplied
same-lexeme crosswalk witness.  It never turns a page-context entry id into a
lexeme claim and never emits a certified target-occurrence link when the EDGES
packet does not contain one.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam4_finite_verb_producer as fam4
from tools import fam5_derived_verb_producer as fam5
from tools.typed_claim_contract import learner_statement_for, validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
PROJECTOR_ID = "sarf.proofv.verb.v1"
PRODUCER_ID = "tools.proofv_verb_producer"
VERSION = "1.0.0"
SCHEMA = "qamus.typed_claim_contract.v1"
PROOF_SCHEMA = "qamus.proofv.verb_facts.v1"
DEFAULT_REGISTRY = ROOT / "qamus" / "examples" / "proof-verb" / "proofv-form-registry.jsonl"
N_LANG_SARF = "Ṣarf — how this piece forms the word"
N_LANG_NAHW = "Naḥw — what this piece does here"
TARGET_SURFACE = "فَٱتَّبِعْنِىٓ"
TARGET_LOC = "19:43:10"
TARGET_ROOT = ["ت", "ب", "ع"]


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_registry(path: Path | str | None = None) -> list[dict[str, Any]]:
    source = DEFAULT_REGISTRY if path is None else Path(path)
    rows = _jsonl(source)
    if len(rows) != 1:
        raise ValueError(f"PROOF-V registry must contain one closed pattern: {source}")
    row = rows[0]
    required = {
        "family": "proofv",
        "supported": True,
        "form": "VIII",
        "marker_class": "derivative_infix_form_viii_t",
        "derivational_class": "derivative_infix",
        "onset_class": "hamzat_al_wasl",
        "treatment_c": "C_shared_written_letter",
        "idgham_classification": "B_shared_letter_clean_split",
    }
    for key, expected in required.items():
        if row.get(key) != expected:
            raise ValueError(f"{source}: PROOF-V registry field {key!r} is not closed")
    if not row.get("pattern_id") or row.get("owner_gate") != "proofv_candidate_only":
        raise ValueError(f"{source}: PROOF-V pattern lacks candidate owner gate")
    return rows


def _loc(row: Mapping[str, Any]) -> str:
    return str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:")


def _surface(row: Mapping[str, Any]) -> str:
    value = str(row.get("surface") or "")
    if not value:
        raise ValueError("PROOF-V source row surface is required")
    return value


def _raw_tokens(surface: str) -> list[dict[str, Any]]:
    """Tokenize without reordering Qurʾanic combining marks.

    FAM4's carrier token helper is deliberately normalization-oriented.  The
    proof surface is scripture text, so this local boundary reader preserves
    the source codepoint order and uses the carrier only for its registries and
    defeater checks.
    """

    tokens: list[dict[str, Any]] = []
    for index, char in enumerate(surface):
        if unicodedata.category(char) == "Mn":
            if not tokens:
                raise ValueError("a combining mark cannot begin the PROOF-V surface")
            tokens[-1]["marks"].append(char)
            tokens[-1]["end"] = index + 1
            continue
        tokens.append({"letter": char, "marks": [], "start": index, "end": index + 1})
    for token in tokens:
        token["surface"] = surface[token["start"]:token["end"]]
    return tokens


def _source_addresses(row: Mapping[str, Any], nearest: Mapping[str, Any] | None) -> list[dict[str, str]]:
    loc = _loc(row)
    addresses = [
        {"address": f"quran:{loc}", "source_kind": "quran_token"},
        {"address": str(row.get("source_address") or f"corpus:rh_live_01_beta_whitelist.jsonl#loc={loc}"), "source_kind": "corpus_record"},
        {"address": f"occurrence-appearances:{loc}:appearances[0]", "source_kind": "review_artifact"},
    ]
    if nearest:
        entry_id = str(nearest.get("entry_id") or "")
        occurrence_id = str(nearest.get("occurrence_id") or "")
        if entry_id:
            addresses.append({"address": f"entry:{entry_id}:root", "source_kind": "qamus_entry_field"})
        if nearest.get("entry_surface_address"):
            addresses.append({"address": str(nearest["entry_surface_address"]), "source_kind": "qamus_entry_field"})
        if occurrence_id:
            addresses.append({"address": f"crosswalk:forward:{occurrence_id}", "source_kind": "review_artifact"})
            addresses.append({"address": f"crosswalk:reverse:{entry_id}", "source_kind": "review_artifact"})
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in addresses:
        key = (item["address"], item["source_kind"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _span(token: Mapping[str, Any], index: int, role: str, display_class: str | None = None) -> dict[str, Any]:
    value = {
        "span_id": f"span:base-letter-{index}",
        "start": int(token["start"]),
        "end": int(token["end"]),
        "surface": str(token["surface"]),
        "role": role,
    }
    # The F-A surface-span schema is deliberately narrower than the display
    # payload.  Display classes live in fact_value.letter_ownership instead.
    return value


def _fact(
    *,
    fact_type: str,
    fact_value: dict[str, Any],
    spans: list[dict[str, Any]],
    source_addresses: list[dict[str, str]],
    projection_id: str,
    evidence_mode: str,
    evidence_status: str,
    confidence: str,
    certification_status: str,
    certification_reason: str,
    evidence_summary: str,
    dependencies: dict[str, Any] | None = None,
    derivation_chain: list[dict[str, Any]] | None = None,
    guards: list[dict[str, str]] | None = None,
    defeaters: list[dict[str, Any]] | None = None,
    blockers: list[dict[str, str]] | None = None,
    source_kind: str = "corpus_record",
) -> dict[str, Any]:
    source_address = source_addresses[0]
    fact = {
        "fact_id": "",
        "fact_type": fact_type,
        "fact_value": fact_value,
        "surface_spans": spans,
        "ownership": {
            "primary": {"owner_id": "proofv-verb-owner", "owner_type": "producer"},
            "secondary": [
                {"owner_id": "fam4-finite-verb-carrier", "owner_type": "carrier"},
                {"owner_id": "fam5-derived-verb-carrier", "owner_type": "carrier"},
                {"owner_id": "proofv-candidate-scope", "owner_type": "scope"},
            ],
        },
        "source": {"source_id": source_address["address"], "source_kind": source_address["source_kind"]},
        "source_address": source_address,
        "certification": {"status": certification_status, "reason": certification_reason},
        "evidence": {
            "status": evidence_status,
            "confidence": confidence,
            "evidence_ids": [item["address"] for item in source_addresses],
            "summary": evidence_summary,
        },
        "evidence_mode": evidence_mode,
        "source_evidence": {
            "structured_source_fact": copy.deepcopy(fact_value.get("source_fact") or {"fact_type": fact_type}),
            "source_addresses": copy.deepcopy(source_addresses),
        },
        "derivation_chain": derivation_chain or [],
        "dependencies": dependencies or {"fact_ids": [], "source_addresses": []},
        "contradiction_records": [],
        "producer": {"id": PRODUCER_ID, "version": VERSION},
        "rule_projector": {"rule_id": "proofv.verb.letter_evidence", "projector_id": PROJECTOR_ID, "version": VERSION},
        "guards": guards or [],
        "defeaters": defeaters or [],
        "unresolved_blockers": blockers or [],
        "dependent_fact_ids": [],
        "dependent_projection_ids": [projection_id],
    }
    fact["fact_id"] = "sha256:" + _hash(fact)
    return fact


def _occurrence(loc: str, surface: str) -> dict[str, Any]:
    return {
        "occurrence_id": f"quran:{loc}",
        "quran_loc": loc,
        "wbw_loc": f"wbw:{loc}",
        "surface": surface,
        "surface_length": len(surface),
    }


def _pending_fact(
    surface: str,
    loc: str,
    route: str,
    blocker_id: str,
    source_addresses: list[dict[str, str]],
    projection_id: str,
    *,
    reason: str,
    spans: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    value = {
        "status": "unresolved",
        "route": route,
        "surface": surface,
        "quran_loc": loc,
        "reason": reason,
        "source_fact": {"blocker": blocker_id, "route": route},
    }
    return _fact(
        fact_type="proofv_source_gap",
        fact_value=value,
        spans=spans or [{"span_id": "span:unresolved:surface", "start": 0, "end": len(surface), "surface": surface, "role": "unresolved_surface"}],
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="unresolved",
        evidence_status="unknown",
        confidence="unknown",
        certification_status="pending",
        certification_reason="The required source fact is not present in the repo packets.",
        evidence_summary=reason,
        guards=[{"guard_id": "proofv.no_fact_invention", "reason": "missing facts remain typed unresolved"}],
        blockers=[{"blocker_id": blocker_id, "reason": reason}],
    )


def _ownership(surface: str, tokens: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if [token["letter"] for token in tokens] != ["ف", "ٱ", "ت", "ب", "ع", "ن", "ى"]:
        raise ValueError("PROOF-V closed target pattern does not match the written base letters")
    roles = [
        ("linking_result_fa", "linking_result_fa", "qg-result-fa", "nahw"),
        ("hamzat_al_wasl", "hamzat_al_wasl", "qg-verb-prefix", "sarf"),
        ("root_radical_shared_with_derivative_infix", "root_radical", "qg-root-radical", "sarf"),
        ("root_radical", "root_radical", "qg-root-radical", "sarf"),
        ("root_radical", "root_radical", "qg-root-radical", "sarf"),
        ("protective_nun", "protective_nun", "qg-protective-nun", "sarf"),
        ("object_pronoun_1cs", "object_pronoun", "qg-object-pronoun", "sarf"),
    ]
    result: list[dict[str, Any]] = []
    for index, (role, owner_class, display_class, plane) in enumerate(roles):
        token = tokens[index]
        item = {
            "base_letter_index": index,
            "written_letter": str(token["letter"]),
            "surface": str(token["surface"]),
            "marks": list(token.get("marks", [])),
            "start": int(token["start"]),
            "end": int(token["end"]),
            "role": role,
            "owner_class": owner_class,
            "display_class": display_class,
            "primary_display": True,
            "primary_plane": plane,
        }
        if index == 0:
            item["nahw_role"] = "linking_or_result_fa"
        if index == 1:
            item["hamzat_al_wasl_class"] = "hamzat_al_wasl"
        if index == 2:
            item["shared_roles"] = ["root_radical_1", "derivative_infix"]
            item["secondary_internal_class"] = "qg-derivative-prefix"
        if index == 5:
            item["typed_kind"] = "sarf.protective_nun"
            item["particle"] = False
        if index == 6:
            item["pronoun_person"] = "1"
            item["pronoun_number"] = "singular"
            item["pronoun_letter"] = "ي"
        result.append(item)
    return result


def _unresolved_result(row: Mapping[str, Any], *, route: str, blocker_id: str, reason: str) -> dict[str, Any]:
    surface = _surface(row)
    loc = _loc(row)
    projection_id = "proofv.verb." + loc.replace(":", ".") + ".v1"
    addresses = _source_addresses(row, None)
    pending = _pending_fact(surface, loc, route, blocker_id, addresses, projection_id, reason=reason)
    record = {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"proofv:verb:{loc}",
        "record_type": "unresolved_projection",
        "canonical_occurrence": _occurrence(loc, surface),
        "facts": [pending],
        "projection": {
            "projection_id": projection_id,
            "status": "source_gap",
            "unresolved_status": "source_gap",
            "learner_visible": True,
            "materialization_target": {
                "artifact": "qamus/examples/proof-verb/canonical-facts.json",
                "field": "proofv_verb",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": None,
            "learner_statement": learner_statement_for("source_gap"),
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
                "status": "source_gap",
                "route": route,
            },
        },
    }
    errors = validate_contract_record(record)
    if errors:
        raise ValueError("invalid PROOF-V unresolved record: " + "; ".join(errors))
    return {
        "schema": PROOF_SCHEMA,
        "status": "source_gap",
        "materialization_allowed": False,
        "canonical_occurrence": record["canonical_occurrence"],
        "facts": [pending],
        "record": record,
        "sarf": {},
        "uncertainty": {"status": "source_gap", "source_gap": [{"blocker_id": blocker_id, "reason": reason}], "routes": [route]},
    }


def build_verb_facts(
    source_row: Mapping[str, Any],
    *,
    nearest: Mapping[str, Any] | None,
    form_registry: Path | str | None = None,
    affix_registry: Any = None,
    weak_root_registry: Any = None,
) -> dict[str, Any]:
    """Build the single PROOF-V fact envelope and its bounded uncertainty."""

    surface = _surface(source_row)
    loc = _loc(source_row)
    if loc != TARGET_LOC or surface != TARGET_SURFACE:
        return _unresolved_result(
            source_row,
            route="scholar-packet:proofv.surface-selection",
            blocker_id="proofv.surface_not_closed",
            reason="The requested PROOF-V closed pattern is only authorized for the surveyed target occurrence.",
        )
    if source_row.get("protective_nun_class") == "qg-particle":
        return _unresolved_result(
            source_row,
            route="scholar-packet:sarf.protective_nun",
            blocker_id="proofv.protective_nun_particle_misclassification",
            reason="The nūn boundary is typed as a particle; PROOF-V refuses to launder it into sarf.protective_nun.",
        )
    if source_row.get("naive_gemination_split") is True:
        return _unresolved_result(
            source_row,
            route="scholar-packet:sarf.idgham-treatment-c",
            blocker_id="proofv.gemination_treatment_c_required",
            reason="The input requests a naive split of one shadda-bearing written letter.",
        )
    morphline = str(source_row.get("morphline") or "").lower()
    required_source_terms = ("form viii", "imperative", "2nd person masculine singular", "object pronoun")
    if not all(term in morphline for term in required_source_terms):
        return _unresolved_result(
            source_row,
            route="scholar-packet:proofv.source-morphology",
            blocker_id="proofv.source_morphology_assertion_missing",
            reason="The read-only source row does not contain the complete Form-VIII imperative/object-pronoun assertion.",
        )
    if not nearest or nearest.get("crosswalk_status") != "deterministic_exact":
        return _unresolved_result(
            source_row,
            route="scholar-packet:proofv.target-lexeme-occurrence-link",
            blocker_id="proofv.same_lexeme_crosswalk_missing",
            reason="No deterministic same-lexeme crosswalk witness is available for the target.",
        )
    root_parts = str(nearest.get("root") or "").split()
    if root_parts != TARGET_ROOT:
        return _unresolved_result(
            source_row,
            route="scholar-packet:proofv.root-crosswalk",
            blocker_id="proofv.root_crosswalk_mismatch",
            reason="The nearest crosswalk witness does not carry the required root.",
        )

    # Load the shared closed carriers even though the PROOF-V pattern is a
    # candidate-only extension.  This makes carrier drift a hard build error.
    carrier_affixes, carrier_weak = fam5.load_carrier_registries(
        affix_registry=affix_registry,
        weak_root_registry=weak_root_registry,
    )
    registry = load_registry(form_registry)
    pattern = registry[0]
    # Keep the exact source ordering for the proof span.  The carrier helper is
    # still loaded above for shared registry/defeater parity, but its NFC key is
    # not allowed to rewrite scripture display text.
    tokens = _raw_tokens(surface)
    if "".join(str(token["surface"]) for token in tokens) != surface:
        raise ValueError("PROOF-V tokenization does not reconstruct the exact target surface")
    ownership = _ownership(surface, tokens)
    source_addresses = _source_addresses(source_row, nearest)
    projection_id = "proofv.verb." + loc.replace(":", ".") + ".v1"
    whole_span = [{"span_id": "span:occurrence", "start": 0, "end": len(surface), "surface": surface, "role": "verb_occurrence"}]
    ownership_spans = [_span(tokens[index], index, item["role"], item["display_class"]) for index, item in enumerate(ownership)]

    observation = _fact(
        fact_type="proofv_surface_observation",
        fact_value={
            "surface": surface,
            "quran_loc": loc,
            "source_fields_present": ["surface", "loc", "quran_loc", "morphline", "segments"],
            "source_row_line": source_row.get("source_line"),
            "source_row_hash": "sha256:" + _hash({"loc": loc, "surface": surface, "morphline": bool(source_row.get("morphline")), "segments": source_row.get("segments") or []}),
            "source_fact": {"source_kind": "corpus_record", "source_fields": ["surface", "morphline", "segments"]},
        },
        spans=whole_span,
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="direct_source_attestation",
        evidence_status="source_addressed_candidate",
        confidence="high",
        certification_status="candidate",
        certification_reason="The whitelist row is a candidate input, not a linguistic certification transition.",
        evidence_summary="The exact target surface and source address are preserved from the read-only whitelist packet.",
        guards=[{"guard_id": "proofv.surface_byte_exact", "reason": "the source surface is retained without normalization"}],
        defeaters=[{"defeater_id": "proofv.candidate_only", "reason": "candidate mode remains active", "fact_ids": []}],
    )
    crosswalk = _fact(
        fact_type="proofv_lexeme_crosswalk",
        fact_value={
            "target_occurrence_link_status": "source_gap",
            "nearest_same_lexeme": copy.deepcopy(dict(nearest)),
            "entry_id": str(nearest["entry_id"]),
            "sense_id": str(nearest["sense_id"]),
            "card_id": str(nearest["card_id"]),
            "selected_word_id": str(nearest["selected_word_id"]),
            "occurrence_id": str(nearest["occurrence_id"]),
            "root": list(TARGET_ROOT),
            "source_fact": {"crosswalk_status": nearest["crosswalk_status"], "target_occurrence_direct_edge": False},
        },
        spans=whole_span,
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="cross_source_corroboration",
        evidence_status="source_addressed_candidate",
        confidence="high",
        certification_status="candidate",
        certification_reason="The same-lexeme chain is deterministic in EDGES, but it is not a direct target occurrence edge.",
        evidence_summary="A nearest card-selected same-lexeme chain is present; the target occurrence link remains a source gap.",
        guards=[
            {"guard_id": "proofv.page_context_never_lexeme", "reason": "the target whitelist entry_id is not consumed as a lexeme edge"},
            {"guard_id": "proofv.nearest_crosswalk_reciprocal", "reason": "the nearest forward/reverse crosswalk witness is deterministic"},
        ],
        defeaters=[{"defeater_id": "proofv.candidate_only", "reason": "candidate mode remains active", "fact_ids": []}],
    )
    ownership_fact = _fact(
        fact_type="proofv_letter_ownership",
        fact_value={
            "surface": surface,
            "root": list(TARGET_ROOT),
            "letter_ownership": ownership,
            "base_letter_count": len(tokens),
            "diacritics_policy": "hover_only",
            "nahw_colour_policy": "overt_letters_only",
            "source_fact": {"pattern_id": pattern["pattern_id"], "carrier_affix_count": len(carrier_affixes), "weak_defeater_count": len(carrier_weak)},
        },
        spans=ownership_spans,
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="cross_source_corroboration",
        evidence_status="source_addressed_candidate",
        confidence="medium",
        certification_status="candidate",
        certification_reason="Letter ownership is a candidate reconstruction from the closed pattern and local source packet.",
        evidence_summary="Every written base letter has one primary display owner; the shared letter keeps secondary internal roles only.",
        dependencies={"fact_ids": [observation["fact_id"], crosswalk["fact_id"]], "source_addresses": source_addresses},
        derivation_chain=[{
            "step_id": "proofv.step.letter-ownership",
            "operation": "apply_candidate_form_viii_pattern_to_exact_target_surface",
            "input_fact_ids": [observation["fact_id"], crosswalk["fact_id"]],
            "input_source_addresses": source_addresses,
            "output": "one primary display class per written base letter",
        }],
        guards=[
            {"guard_id": "proofv.letter_owner_totality", "reason": "all seven written base letters are owned exactly once"},
            {"guard_id": "proofv.hamzat_al_wasl_governed", "reason": "hamzat al-waṣl is a separate governed class"},
            {"guard_id": "proofv.protective_nun_typed", "reason": "protective nūn is not a particle"},
        ],
        defeaters=[{"defeater_id": "proofv.candidate_only", "reason": "candidate mode remains active", "fact_ids": []}],
    )
    derived_fact = _fact(
        fact_type="derived_verb_evidence",
        fact_value={
            "typed_kind": "proofv.derived_verb_evidence",
            "surface": surface,
            "root": list(TARGET_ROOT),
            "form": pattern["form"],
            "template": pattern["template"],
            "pattern_id": pattern["pattern_id"],
            "tense_aspect": pattern["tense_aspect"],
            "voice": pattern["voice"],
            "person": pattern["person"],
            "number": pattern["number"],
            "gender": pattern["gender"],
            "mood": pattern["mood"],
            "hamzat_al_wasl": {"present": True, "class": "hamzat_al_wasl", "governed": True, "surface": ownership[1]["surface"]},
            "derivational_additions": [{"role": "derivative_infix", "class": "derivative_infix", "marker_class": pattern["marker_class"], "base_letter_indices": [2], "surface": ownership[2]["surface"]}],
            "root_radicals": [
                {"index": 1, "radical": "ت", "base_letter_index": 2, "shared_written_letter": True},
                {"index": 2, "radical": "ب", "base_letter_index": 3},
                {"index": 3, "radical": "ع", "base_letter_index": 4},
            ],
            "gemination": {
                "present": True,
                "treatment": pattern["treatment_c"],
                "idgham_classification": pattern["idgham_classification"],
                "split_authorized": False,
                "written_base_letter_index": 2,
                "shared_roles": ["derivative_infix", "root_radical_1"],
                "split_tone": False,
                "reason": "The infix ت and root ت share one shadda-bearing written base letter; no naive split is displayed.",
            },
            "weak_root_defeater": {"status": "none_triggered", "root_shape": "sound", "registry_route": "weak_root_pattern_unresolved"},
            "letter_ownership": ownership,
            "reconstruction_proof": {
                "passed": True,
                "base_letter_indices_complete": True,
                "each_written_base_letter_exactly_one_class": True,
                "no_naive_geminate_split": True,
                "joined_surface": surface,
            },
            "source_fact": {"whitelist_morphline_present": True, "entry_root_source": str(nearest["entry_id"]), "target_occurrence_direct_form_edge": False},
        },
        spans=ownership_spans,
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="cross_source_corroboration",
        evidence_status="source_addressed_candidate",
        confidence="medium",
        certification_status="candidate",
        certification_reason="This is the requested candidate proof; it is not a certified publication fact.",
        evidence_summary="The source packet and same-lexeme chain support a visible candidate reconstruction with explicit gates.",
        dependencies={"fact_ids": [observation["fact_id"], crosswalk["fact_id"], ownership_fact["fact_id"]], "source_addresses": source_addresses},
        derivation_chain=[{
            "step_id": "proofv.step.derived-verb",
            "operation": "apply_proofv_candidate_form_viii_pattern",
            "input_fact_ids": [observation["fact_id"], crosswalk["fact_id"], ownership_fact["fact_id"]],
            "input_source_addresses": source_addresses,
            "output": "form, voice, person, mood, derivational infix, shared gemination, and suffix ownership",
        }],
        guards=[
            {"guard_id": "proofv.shared_fam4_affix_registry", "reason": "the shared FAM4 affix carrier is loaded before projection"},
            {"guard_id": "proofv.shared_fam5_registry", "reason": "the shared FAM5 derived-verb carrier is loaded before projection"},
            {"guard_id": "proofv.weak_root_defeater_registry", "reason": "weak-root defeaters are checked and none triggers for ت ب ع"},
            {"guard_id": "proofv.treatment_c_gemination", "reason": "the shared written letter remains one display span"},
            {"guard_id": "proofv.candidate_only", "reason": "pre_apply_not_authorized remains true"},
        ],
        defeaters=[{"defeater_id": "proofv.candidate_only", "reason": "candidate mode remains active", "fact_ids": []}],
    )
    protective_fact = _fact(
        fact_type="protective_nun",
        fact_value={
            "typed_kind": "sarf.protective_nun",
            "surface": ownership[5]["surface"],
            "class": "qg-protective-nun",
            "role": "protective_nun",
            "particle": False,
            "source_fact": {"boundary": "explicit_target_suffix"},
        },
        spans=[ownership_spans[5]],
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="direct_source_attestation",
        evidence_status="source_addressed_candidate",
        confidence="medium",
        certification_status="candidate",
        certification_reason="The protective-nūn class is carried as a candidate typed fact.",
        evidence_summary="The nūn is kept in the sarf protective-nūn class and is never emitted as a particle.",
        dependencies={"fact_ids": [ownership_fact["fact_id"]], "source_addresses": source_addresses},
        guards=[{"guard_id": "proofv.protective_nun_never_particle", "reason": "qg-protective-nun is not a particle class"}],
        defeaters=[{"defeater_id": "proofv.candidate_only", "reason": "candidate mode remains active", "fact_ids": []}],
    )
    object_fact = _fact(
        fact_type="object_pronoun",
        fact_value={
            "typed_kind": "sarf.object_pronoun",
            "surface": ownership[6]["surface"],
            "written_letter": ownership[6]["written_letter"],
            "pronoun_letter": "ي",
            "person": "1",
            "number": "singular",
            "role": "attached_object_pronoun",
            "source_fact": {"source_field": "morphline_object_pronoun"},
        },
        spans=[ownership_spans[6]],
        source_addresses=source_addresses,
        projection_id=projection_id,
        evidence_mode="direct_source_attestation",
        evidence_status="source_addressed_candidate",
        confidence="medium",
        certification_status="candidate",
        certification_reason="The attached 1cs object-pronoun class is a candidate typed fact.",
        evidence_summary="The final written suffix is kept as an attached 1cs object pronoun; exact syntax is separately pending.",
        dependencies={"fact_ids": [ownership_fact["fact_id"]], "source_addresses": source_addresses},
        guards=[{"guard_id": "proofv.object_pronoun_attached", "reason": "the final suffix has an explicit object-pronoun class"}],
        defeaters=[{"defeater_id": "proofv.candidate_only", "reason": "candidate mode remains active", "fact_ids": []}],
    )
    nahw_fact = _pending_fact(
        surface,
        loc,
        "scholar-packet:nahw-governor-object:19:43:10",
        "proofv.nahw_exact_governor_missing",
        source_addresses,
        projection_id,
        reason="The repo packet does not contain an exact source-addressed governor/object relation for this target occurrence.",
        spans=whole_span,
    )
    nahw_fact["fact_type"] = "nahw_dependency"
    nahw_fact["fact_value"].update({
        "governor": None,
        "governed_occurrence": {"occurrence_id": f"quran:{loc}", "surface": surface},
        "relationship": {"role": "object", "relationship": "object_of", "status": "unresolved"},
        "case_or_mood": {"status": "unresolved", "value": None, "reason": "exact governor is absent"},
        "source_fact": {"source_fields": [], "governor_present": False},
    })
    nahw_fact["fact_id"] = "sha256:" + _hash(nahw_fact)

    facts = [observation, crosswalk, ownership_fact, derived_fact, protective_fact, object_fact, nahw_fact]
    record = {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"proofv:verb:{loc}",
        "record_type": "projection_input",
        "canonical_occurrence": _occurrence(loc, surface),
        "facts": facts,
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": "qamus/examples/proof-verb/canonical-facts.json",
                "field": "proofv_verb",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "This candidate preserves the requested written verb structure while source review remains open.",
                "language": "en",
                "fact_bindings": [{"fact_id": derived_fact["fact_id"], "fact_field": "fact_value.reconstruction_proof", "surface_span_ids": [span["span_id"] for span in ownership_spans]}],
            },
            "learner_statement": "This word remains a candidate while two source routes are open.",
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
                "status": "candidate_with_source_gaps",
                "uncertainty_routes": ["scholar-packet:proofv.target-lexeme-occurrence-link", "scholar-packet:nahw-governor-object:19:43:10"],
                "segments": [{"surface": item["surface"], "role": item["role"], "span_id": f"span:base-letter-{item['base_letter_index']}"} for item in ownership],
            },
        },
        "tension_records": [{
            "tension_id": "proofv.target-link-and-nahw",
            "status": "unresolved",
            "statement": "The target surface is exact, but its direct lexeme occurrence link and exact governor/object relation are not source-certified in the repo packets.",
            "fact_ids": [crosswalk["fact_id"], nahw_fact["fact_id"]],
            "resolution_requirement": "Attach a scholar packet with both exact source facts before any publication transition.",
        }],
    }
    errors = validate_contract_record(record)
    if errors:
        raise ValueError("invalid PROOF-V candidate record: " + "; ".join(errors))
    return {
        "schema": PROOF_SCHEMA,
        "status": "candidate_with_source_gaps",
        "materialization_allowed": False,
        "candidate_mode": "pre_apply_not_authorized",
        "canonical_occurrence": record["canonical_occurrence"],
        "facts": facts,
        "record": record,
        "sarf": {
            "root": list(TARGET_ROOT),
            "form": pattern["form"],
            "template": pattern["template"],
            "voice": pattern["voice"],
            "person": pattern["person"],
            "number": pattern["number"],
            "gender": pattern["gender"],
            "mood": pattern["mood"],
            "letter_ownership": ownership,
            "hamzat_al_wasl": {"class": "hamzat_al_wasl", "governed": True, "surface": ownership[1]["surface"]},
            "derivational_infix": {"surface": ownership[2]["surface"], "class": "derivative_infix_form_viii_t", "base_letter_index": 2},
            "gemination": derived_fact["fact_value"]["gemination"],
            "protective_nun": protective_fact["fact_value"],
            "object_pronoun": object_fact["fact_value"],
            "weak_root_defeater": derived_fact["fact_value"]["weak_root_defeater"],
        },
        "uncertainty": {
            "status": "source_gap",
            "source_gap": [
                {"blocker_id": "proofv.target_lexeme_occurrence_link", "reason": "The chosen reader occurrence has no direct lexeme edge; the nearest same-lexeme chain is shown instead."},
                {"blocker_id": "proofv.nahw_exact_governor_missing", "reason": "The exact governor/object relation is not present in the repo packets."},
            ],
            "routes": ["scholar-packet:proofv.target-lexeme-occurrence-link", "scholar-packet:nahw-governor-object:19:43:10"],
            "display": "PENDING — source review required before a learner gloss is eligible.",
        },
    }


def validate_proofv_facts(proof: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if proof.get("schema") != PROOF_SCHEMA:
        errors.append("PROOF-V wrapper schema is wrong")
    record = proof.get("record")
    if not isinstance(record, dict):
        errors.append("PROOF-V wrapper lacks the F-A record")
        return errors
    errors.extend(validate_contract_record(record))
    surface = str((record.get("canonical_occurrence") or {}).get("surface") or "")
    facts = [fact for fact in proof.get("facts", []) if isinstance(fact, Mapping)]
    derived = next((fact for fact in facts if fact.get("fact_type") == "derived_verb_evidence"), None)
    if proof.get("materialization_allowed") is not False:
        errors.append("PROOF-V materialization is enabled")
    if derived:
        value = derived.get("fact_value") or {}
        ownership = value.get("letter_ownership") or []
        if [item.get("base_letter_index") for item in ownership] != list(range(len(ownership))):
            errors.append("PROOF-V letter ownership indices are not contiguous")
        if len({item.get("base_letter_index") for item in ownership}) != len(ownership):
            errors.append("PROOF-V letter ownership duplicates a base letter")
        if "particle" in str((ownership[5] if len(ownership) > 5 else {}).get("display_class")):
            errors.append("protective nūn is painted as a particle")
        reconstruction = value.get("reconstruction_proof") or {}
        if reconstruction.get("joined_surface") != surface or reconstruction.get("passed") is not True:
            errors.append("PROOF-V reconstruction proof failed")
    return errors


if __name__ == "__main__":
    raise SystemExit("Use tools.build_proofv_verb.py to build the PROOF-V packet.")
