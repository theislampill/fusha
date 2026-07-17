#!/usr/bin/env python3
"""Validate the committed PROOF-V candidate packet without mutating inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unicodedata
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import build_typed_edge_crosswalk as edge_builder
from tools import fact_projectors
from tools import fd_compiler
from tools import normalize_ar
from tools import proofv_verb_producer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "qamus" / "examples" / "proof-verb"
# External corpus paths are never defaulted (repo self-containment): without
# explicit --whitelist/--entries the gate runs on the committed packet fixtures.

TARGET_LOC = "19:43:10"
TARGET_SURFACE = "فَٱتَّبِعْنِىٓ"
TARGET_KEY = normalize_ar.norm_strict(TARGET_SURFACE)
FALLBACK_KEY = normalize_ar.norm_strict("تَوَكَّلْتُ")
NEAREST_LOC = "28:50:12"
ENTRY_ID = "5d89e690256d"
EXPECTED_WRITTEN_LETTERS = ["ف", "ٱ", "ت", "ب", "ع", "ن", "ى"]
EXPECTED_CLASSES = [
    "qg-result-fa",
    "qg-verb-prefix",
    "qg-root-radical",
    "qg-root-radical",
    "qg-root-radical",
    "qg-protective-nun",
    "qg-object-pronoun",
]
EXPECTED_FACT_TYPES = {
    "proofv_surface_observation",
    "proofv_lexeme_crosswalk",
    "proofv_letter_ownership",
    "derived_verb_evidence",
    "protective_nun",
    "object_pronoun",
    "nahw_dependency",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no} is not an object")
            rows.append(value)
    return rows


def _loc(row: dict[str, Any]) -> str:
    return str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:")


def _check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def _fact_map(facts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("fact_type")): item
        for item in facts.get("facts") or []
        if isinstance(item, dict) and item.get("fact_type")
    }


def _validate_source_survey(
    errors: list[str],
    source_occurrence: dict[str, Any],
    selection: dict[str, Any],
    whitelist_path: Path | None,
    output_dir: Path,
) -> None:
    fixture_mode = whitelist_path is None
    try:
        if fixture_mode:
            fixture_rows = _jsonl(output_dir / "whitelist-survey-fixture.jsonl")
            rows = [item.get("row") or {} for item in fixture_rows]
            fixture_lines = {
                _loc(item.get("row") or {}): item.get("source_line")
                for item in fixture_rows
            }
        else:
            rows = _jsonl(whitelist_path)
            fixture_lines = {}
    except Exception as exc:  # pragma: no cover - surfaced as a gate failure
        errors.append(f"cannot read whitelist: {exc}")
        return
    target_rows = [row for row in rows if normalize_ar.norm_strict(str(row.get("surface") or "")) == TARGET_KEY]
    fallback_rows = [row for row in rows if normalize_ar.norm_strict(str(row.get("surface") or "")) == FALLBACK_KEY]
    _check(errors, len(target_rows) == 1, f"surface survey target count is {len(target_rows)}, expected 1")
    _check(errors, len(fallback_rows) == 7, f"fallback surface survey count is {len(fallback_rows)}, expected 7")
    if target_rows:
        target = target_rows[0]
        _check(errors, str(target.get("surface")) == TARGET_SURFACE, "source surface was normalized or rewritten")
        _check(errors, _loc(target) == TARGET_LOC, "survey target location is not 19:43:10")
        _check(errors, source_occurrence.get("source_line") >= 1, "source line was not recorded")
        if source_occurrence.get("source_line"):
            if fixture_mode:
                _check(
                    errors,
                    fixture_lines.get(TARGET_LOC) == source_occurrence["source_line"],
                    "recorded source line disagrees with the committed survey fixture",
                )
            else:
                with whitelist_path.open(encoding="utf-8") as handle:
                    actual = next((line_no for line_no, line in enumerate(handle, 1) if line_no == source_occurrence["source_line"]), None)
                _check(errors, actual == source_occurrence["source_line"], "recorded source line cannot be reread")
        _check(errors, source_occurrence.get("surface") == target.get("surface"), "source occurrence differs from surveyed row")
    _check(errors, selection.get("chosen_surface") == TARGET_SURFACE, "selection does not preserve the exact target surface")
    _check(errors, selection.get("chosen_loc") == TARGET_LOC, "selection location is not the surveyed target")
    _check(errors, selection.get("chosen_occurrence_is_card_selected") is False, "selection incorrectly calls the target card-selected")
    _check(errors, (selection.get("chosen_occurrence_chain") or {}).get("status") == "reader_only_source_gap", "selection does not record reader-only target status")
    fallback = selection.get("fallback_comparison") or {}
    _check(errors, fallback.get("occurrence_count") == len(fallback_rows), "fallback comparison is stale")


def _validate_graph(errors: list[str], graph: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    ids: set[str] = set()
    for index, edge in enumerate(graph, 1):
        prefix = f"graph edge {index}"
        _check(errors, edge.get("schema") == edge_builder.SCHEMA, f"{prefix} schema is wrong")
        edge_id = str(edge.get("edge_id") or "")
        _check(errors, bool(edge_id) and edge_id not in ids, f"{prefix} id is missing or duplicated")
        ids.add(edge_id)
        edge_type = edge.get("edge_type")
        _check(errors, edge_type in edge_builder.EDGE_TYPE_SET, f"{prefix} has an unknown edge type")
        status = edge.get("status")
        _check(errors, status in edge_builder.STATUS_SET, f"{prefix} has an unknown status")
        for endpoint in ("from", "to"):
            node_id = str(edge.get(f"{endpoint}_node_id") or "")
            node_type = edge.get(f"{endpoint}_node_type")
            _check(errors, ":" in node_id and node_type == node_id.split(":", 1)[0], f"{prefix} has an untyped {endpoint} endpoint")
        _check(errors, isinstance(edge.get("evidence"), list), f"{prefix} evidence is not a list")
        _check(errors, isinstance(edge.get("guards"), list), f"{prefix} guards are not a list")

    chain = manifest.get("chain") or {}
    entry = f"entry:{ENTRY_ID}"
    sense = f"sense:{ENTRY_ID}:s1"
    card = str(chain.get("card") or "")
    selected = str(chain.get("selected_word") or "")
    nearest = f"occurrence:{NEAREST_LOC}"
    target = f"occurrence:{TARGET_LOC}"
    target_appearance = f"appearance:{TARGET_LOC}:1"
    by_type = {}
    for edge in graph:
        by_type.setdefault(edge.get("edge_type"), []).append(edge)

    def has(edge_type: str, from_id: str, to_id: str, status: str | None = None) -> bool:
        return any(
            edge.get("from_node_id") == from_id
            and edge.get("to_node_id") == to_id
            and (status is None or edge.get("status") == status)
            for edge in by_type.get(edge_type, [])
        )

    _check(errors, has("sense_entry_edge", sense, entry, "deterministic_exact"), "nearest chain lacks sense-to-entry edge")
    _check(errors, has("source_card_edge", selected, card, "deterministic_exact"), "nearest chain lacks selected-word-to-card edge")
    _check(errors, has("selected_example_edge", card, nearest, "deterministic_exact"), "nearest chain lacks card-to-occurrence edge")
    _check(errors, has("canonical_occurrence_edge", selected, nearest, "deterministic_exact"), "nearest chain lacks canonical occurrence edge")
    _check(errors, has("form_entry_edge", selected, entry, "deterministic_exact"), "nearest chain lacks documented-form edge")
    _check(errors, has("lexeme_entry_edge", selected, entry, "deterministic_exact"), "nearest chain lacks lexeme-entry edge")
    _check(errors, has("rendered_appearance_edge", target, target_appearance, "deterministic_exact"), "target lacks rendered appearance edge")
    gap_edges = [edge for edge in by_type.get("decision_evidence_edge", []) if edge.get("from_node_id") == target]
    _check(errors, len(gap_edges) == 1, "target does not have exactly one decision-evidence source gap")
    if gap_edges:
        _check(errors, gap_edges[0].get("to_node_id") == selected, "target source gap points to the wrong selected word")
        _check(errors, gap_edges[0].get("status") == "source_gap", "target decision evidence is not source_gap")
    target_edges = [edge for edge in graph if edge.get("from_node_id") == target or edge.get("to_node_id") == target]
    _check(errors, {edge.get("edge_type") for edge in target_edges} <= {"rendered_appearance_edge", "decision_evidence_edge"}, "target gained an unproven lexeme/card/form edge")
    _check(errors, not any("s2:" in str(edge) for edge in graph), "nearest graph chain leaked another selected-word sense")

    manifest_edges = {
        (item.get("edge_id"), item.get("edge_type"), item.get("from"), item.get("to"), item.get("status"))
        for item in manifest.get("edge_enumeration") or []
    }
    actual_edges = {
        (item.get("edge_id"), item.get("edge_type"), item.get("from_node_id"), item.get("to_node_id"), item.get("status"))
        for item in graph
    }
    _check(errors, actual_edges == manifest_edges, "manifest edge enumeration differs from typed graph")


def _validate_crosswalk(errors: list[str], forward: dict[str, Any], reverse: dict[str, Any], selection: dict[str, Any]) -> None:
    _check(errors, forward.get("schema") == "qamus.lexeme_entry_crosswalk.forward.v1", "forward crosswalk schema is wrong")
    _check(errors, reverse.get("schema") == "qamus.lexeme_entry_crosswalk.reverse.v1", "reverse crosswalk schema is wrong")
    _check(errors, forward.get("crosswalk_status") == "deterministic_exact", "forward crosswalk is not deterministic_exact")
    _check(errors, forward.get("occurrence_id") == NEAREST_LOC, "forward crosswalk chose the wrong nearest occurrence")
    _check(errors, forward.get("matched_entry_ids") == [ENTRY_ID], "forward crosswalk matched an unexpected entry")
    _check(errors, reverse.get("entry_id") == ENTRY_ID, "reverse crosswalk points to the wrong entry")
    _check(errors, NEAREST_LOC in (reverse.get("occurrence_ids") or []), "reverse crosswalk is not reciprocal")
    nearest = selection.get("nearest_card_selected_same_lexeme") or {}
    _check(errors, nearest.get("selected_word_id") == forward.get("selected_word_id"), "selection and forward crosswalk disagree on selected word")
    _check(errors, forward.get("selected_word_id") in (reverse.get("selected_word_ids") or []), "selected word is missing from reverse crosswalk")
    _check(errors, TARGET_LOC not in (reverse.get("occurrence_ids") or []), "target reader occurrence was laundered into reverse crosswalk")


def _validate_facts(errors: list[str], facts: dict[str, Any], manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _check(errors, facts.get("schema") == proofv_verb_producer.PROOF_SCHEMA, "canonical facts schema is wrong")
    _check(errors, facts.get("candidate_mode") == "pre_apply_not_authorized", "canonical facts are not candidate-mode")
    _check(errors, facts.get("status") == "candidate_with_source_gaps", "canonical facts status is not candidate_with_source_gaps")
    _check(errors, facts.get("materialization_allowed") is False, "canonical facts enable materialization")
    producer_errors = proofv_verb_producer.validate_proofv_facts(facts)
    errors.extend(f"producer validator: {error}" for error in producer_errors)
    fact_map = _fact_map(facts)
    _check(errors, set(fact_map) == EXPECTED_FACT_TYPES, "canonical facts do not enumerate the seven required fact types")
    _check(errors, len(facts.get("facts") or []) == 7, "canonical facts count is not seven")
    for fact in facts.get("facts") or []:
        _check(errors, (fact.get("certification") or {}).get("status") in {"candidate", "pending"}, f"fact {fact.get('fact_type')} has an invalid certification status")
        _check(errors, (fact.get("source") or {}).get("source_kind") == (fact.get("source_address") or {}).get("source_kind"), f"fact {fact.get('fact_type')} has mismatched source kinds")
        _check(errors, str(fact.get("fact_id") or "").startswith("sha256:"), f"fact {fact.get('fact_type')} has no fact id")
    record = facts.get("record") or {}
    projection = record.get("projection") or {}
    _check(errors, record.get("record_type") == "projection_input", "facts record is not a projection input")
    _check(errors, projection.get("status") == "candidate", "projection status is not candidate")
    _check(errors, projection.get("unresolved_status") is None, "projection exposes an unsupported unresolved status")
    _check(errors, (record.get("canonical_occurrence") or {}).get("surface") == TARGET_SURFACE, "record canonical surface is not exact")
    _check(errors, not any((fact.get("certification") or {}).get("status") == "certified" for fact in facts.get("facts") or []), "a PROOF-V fact is incorrectly certified")

    derived = fact_map.get("derived_verb_evidence", {}).get("fact_value") or {}
    _check(errors, derived.get("form") == "VIII", "derived fact is not Form VIII")
    _check(errors, derived.get("voice") == "active", "derived fact voice is not active")
    _check(errors, derived.get("person") == "2", "derived fact person is not 2")
    _check(errors, derived.get("gender") == "masculine", "derived fact gender is not masculine")
    _check(errors, derived.get("number") == "singular", "derived fact number is not singular")
    _check(errors, derived.get("tense_aspect") == "imperative", "derived fact is not imperative")
    _check(errors, (derived.get("hamzat_al_wasl") or {}).get("class") == "hamzat_al_wasl", "hamzat al-waṣl class is missing")
    _check(errors, (derived.get("hamzat_al_wasl") or {}).get("governed") is True, "hamzat al-waṣl is not marked governed")
    _check(errors, derived.get("root") == ["ت", "ب", "ع"], "derived root is not ت ب ع")
    additions = derived.get("derivational_additions") or []
    _check(errors, len(additions) == 1 and additions[0].get("marker_class") == "derivative_infix_form_viii_t", "Form VIII infix registry record is missing")
    gemination = derived.get("gemination") or {}
    _check(errors, gemination.get("treatment") == "C_shared_written_letter", "Treatment-C gemination is missing")
    _check(errors, gemination.get("idgham_classification") in {"A_clean_split", "B_shared_letter_clean_split", "C_fused_boundary", "D_ambiguous_boundary"}, "idghām A-D classification is missing")
    _check(errors, gemination.get("idgham_classification") == "B_shared_letter_clean_split", "shared-letter idghām is not classified as B")
    _check(errors, gemination.get("split_authorized") is False and gemination.get("split_tone") is False, "geminate split was incorrectly authorized")
    _check(errors, (derived.get("root_radicals") or [])[0].get("shared_written_letter") is True, "root first radical is not marked inside the shared written letter")
    _check(errors, (derived.get("weak_root_defeater") or {}).get("status") == "none_triggered", "weak-root defeater state is missing")

    ownership = (fact_map.get("proofv_letter_ownership", {}).get("fact_value") or {}).get("letter_ownership") or []
    _check(errors, [item.get("base_letter_index") for item in ownership] == list(range(7)), "letter ownership does not cover base-letter indices 0..6")
    _check(errors, [item.get("display_class") for item in ownership] == EXPECTED_CLASSES, "letter display classes do not match the required primary ownership")
    _check(errors, [item.get("written_letter") for item in ownership] == EXPECTED_WRITTEN_LETTERS, "written base letters are not all accounted for")
    _check(errors, all(item.get("primary_display") is True for item in ownership), "not every base letter has a primary display")
    _check(errors, len({item.get("base_letter_index") for item in ownership}) == 7, "a base letter has more than one primary ownership record")
    _check(errors, all(item.get("primary_plane") == ("nahw" if index == 0 else "sarf") for index, item in enumerate(ownership)), "Naḥw color ownership is not limited to overt fā")
    _check(errors, (fact_map.get("proofv_letter_ownership", {}).get("fact_value") or {}).get("diacritics_policy") == "hover_only", "diacritics are not hover-only")
    _check(errors, (fact_map.get("proofv_letter_ownership", {}).get("fact_value") or {}).get("nahw_colour_policy") == "overt_letters_only", "Naḥw color policy is missing")
    _check(errors, set((ownership[2] if len(ownership) > 2 else {}).get("shared_roles") or []) == {"root_radical_1", "derivative_infix"}, "shared t roles are not explicit")
    nun = fact_map.get("protective_nun", {}).get("fact_value") or {}
    _check(errors, nun.get("typed_kind") == "sarf.protective_nun" and nun.get("particle") is False, "protective nūn is not typed as sarf.protective_nun")
    _check(errors, "particle" not in str(nun.get("class")), "protective nūn is painted as a particle")
    pronoun = fact_map.get("object_pronoun", {}).get("fact_value") or {}
    _check(errors, pronoun.get("typed_kind") == "sarf.object_pronoun" and pronoun.get("person") == "1" and pronoun.get("number") == "singular", "attached 1cs object pronoun is missing")
    nahw = fact_map.get("nahw_dependency", {}).get("fact_value") or {}
    _check(errors, (fact_map.get("nahw_dependency", {}).get("certification") or {}).get("status") == "pending", "missing Naḥw evidence was not left pending")
    _check(errors, nahw.get("status") == "unresolved" and nahw.get("governor") is None, "exact Naḥw governor was invented or omitted")
    _check(errors, (nahw.get("relationship") or {}).get("status") == "unresolved" and (nahw.get("relationship") or {}).get("role") == "object", "unresolved object relation is not explicit")
    _check(errors, nahw.get("route") == "scholar-packet:nahw-governor-object:19:43:10", "Naḥw source-gap route is missing")
    uncertainty = facts.get("uncertainty") or {}
    _check(errors, uncertainty.get("status") == "source_gap" and len(uncertainty.get("routes") or []) == 2, "uncertainty routes are not visible")
    _check(errors, (manifest.get("fact_enumeration") or {}).keys() == fact_map.keys(), "manifest fact enumeration differs from canonical facts")
    return fact_map


def _validate_payload(errors: list[str], payload: dict[str, Any], facts: dict[str, dict[str, Any]]) -> None:
    _check(errors, payload.get("schema") == "qamus.proofv.shared_compiler_payload.v1", "payload schema is wrong")
    compiler = payload.get("compiler") or {}
    _check(errors, set(compiler.get("input_fact_types") or []) == set(facts), "shared compiler did not enumerate canonical fact types")
    _check(errors, set(compiler.get("input_fact_ids") or []) == {str(fact.get("fact_id")) for fact in facts.values()}, "shared compiler did not enumerate canonical fact ids")
    _check(errors, payload.get("candidate_status") == "candidate_with_source_gaps", "payload is not candidate-with-source-gaps")
    _check(errors, payload.get("live_mutation_allowed") is False and payload.get("public_materialization_allowed") is False, "payload enables mutation or publication")
    _check(errors, payload.get("authorization_state") == "pre_apply_not_authorized", "payload authorization state is not pre-apply")
    at_rest = payload.get("at_rest") or {}
    _check(errors, at_rest.get("surface") == TARGET_SURFACE, "at-rest surface is not byte-exact")
    _check(errors, (at_rest.get("exact_reconstruction") or {}).get("passed") is True, "at-rest reconstruction did not pass")
    ownership = (facts.get("proofv_letter_ownership", {}).get("fact_value") or {}).get("letter_ownership") or []
    spans = at_rest.get("spans") or []
    _check(errors, len(spans) == 7 and len(spans) == len(ownership), "at-rest spans do not cover seven letters")
    if len(spans) == len(ownership):
        _check(errors, "".join(str(span.get("surface") or "") for span in spans) == TARGET_SURFACE, "at-rest spans do not reconstruct the raw surface")
        for index, (span, owner) in enumerate(zip(spans, ownership)):
            _check(errors, span.get("surface") == owner.get("surface"), f"at-rest span {index} differs from canonical ownership")
            _check(errors, span.get("display_class") == owner.get("display_class"), f"at-rest span {index} changes display class")
            _check(errors, span.get("primary_plane") == owner.get("primary_plane"), f"at-rest span {index} changes color plane")
            _check(errors, all(unicodedata.category(mark) == "Mn" for mark in span.get("marks_hover_only") or []), f"at-rest span {index} exposes a non-mark hover item")

    compact = payload.get("compact") or {}
    expanded = payload.get("expanded") or {}
    payload_id = payload.get("payload_id")
    _check(errors, bool(payload_id), "payload id is missing")
    _check(errors, compact.get("payload_id") == payload_id and expanded.get("payload_id") == payload_id, "compact/expanded payload identity differs")
    _check(errors, str(compact.get("text") or "").startswith("PENDING"), "compact view does not show uncertainty")
    _check(errors, expanded.get("surface") == TARGET_SURFACE, "expanded surface is not exact")
    _check(errors, (expanded.get("sarf") or {}).get("label") == "Ṣarf — how this piece forms the word", "public Ṣarf label is wrong")
    _check(errors, (expanded.get("nahw") or {}).get("label") == "Naḥw — what this piece does here", "public Naḥw label is wrong")
    _check(errors, (expanded.get("nahw") or {}).get("status") == "unresolved", "expanded Naḥw view is not unresolved")
    _check(errors, (expanded.get("nahw") or {}).get("route") == "scholar-packet:nahw-governor-object:19:43:10", "expanded Naḥw route is missing")
    _check(errors, len((expanded.get("sarf") or {}).get("segments") or []) == 7, "expanded Ṣarf view does not contain seven segments")
    hover = payload.get("hover") or {}
    _check(errors, hover.get("src") == "qamus" and hover.get("kind") == "authored" and hover.get("lang") == "en", "public hover provenance is wrong")
    _check(errors, "informed_by" not in hover, "public hover leaks internal provenance")
    _check(errors, hover.get("status") == "pending" and str(hover.get("text") or "").startswith("PENDING"), "hover uncertainty is not visible")
    appearances = payload.get("per_appearance") or []
    _check(errors, len(appearances) == 1, "per-appearance payload does not cover the target appearance")
    for appearance in appearances:
        _check(errors, appearance.get("payload_id") == payload_id and appearance.get("same_payload_identity") is True, "per-appearance payload identity failed")
        _check(errors, appearance.get("surface") == TARGET_SURFACE, "per-appearance surface changed")
    readback = payload.get("readback") or {}
    _check(errors, readback.get("same_payload_identity") is True and readback.get("exact_reconstruction") is True, "payload readback did not pass")
    _check(errors, readback.get("surface") == TARGET_SURFACE and readback.get("reconstructed_surface") == TARGET_SURFACE, "payload readback surface changed")
    _check(errors, payload.get("shared_carrier_view", {}).get("generated_from_facts") is True, "shared compiler did not consume facts")
    _check(errors, payload.get("shared_carrier_view", {}).get("n_lang_clean") is True, "shared compiler learner copy is not N-LANG-clean")
    learner_text = [
        compact.get("text", ""),
        (expanded.get("sarf") or {}).get("text", ""),
        (expanded.get("nahw") or {}).get("text", ""),
    ]
    for segment in (expanded.get("sarf") or {}).get("segments") or []:
        learner_text.extend([segment.get("sarf_text", ""), segment.get("nahw_text", "")])
    _check(errors, fd_compiler._fd2_n_lang_clean(learner_text), "learner-facing copy fails the shared N-LANG guard")


def _validate_render_and_manifest(errors: list[str], render: dict[str, Any], manifest: dict[str, Any], output_dir: Path) -> None:
    _check(errors, render.get("schema") == "qamus.proofv.render_proof.v1", "render-proof schema is wrong")
    _check(errors, render.get("render_mode") == "fixture_payload_readback", "render-proof mode is not the local fixture readback")
    for key in ("exact_reconstruction", "compact_present", "expanded_present", "same_payload_identity", "uncertainty_visible"):
        _check(errors, render.get(key) is True, f"render-proof gate {key} did not pass")
    _check(errors, render.get("live_mutation_allowed") is False and render.get("public_materialization_allowed") is False, "render-proof enables mutation")
    _check(errors, render.get("png_local_only") is True and render.get("tracked_png") is False, "render-proof PNG policy is wrong")
    _check(errors, (render.get("browser_render") or {}).get("status") == "not_run" and render.get("font_check") is None, "render-proof makes an unrecorded browser/font claim")
    _check(errors, manifest.get("schema") == "qamus.proofv.manifest.v1", "manifest schema is wrong")
    _check(errors, manifest.get("candidate_mode") is True, "manifest is not candidate-mode")
    _check(errors, manifest.get("live_mutation_allowed") is False and manifest.get("public_materialization_allowed") is False, "manifest enables mutation")
    for relative in [manifest.get("selection_artifact"), *(manifest.get("chain") or {}).values()]:
        if isinstance(relative, str) and relative.endswith((".json", ".jsonl")):
            _check(errors, (output_dir / relative).is_file(), f"manifest references missing artifact {relative}")
    descriptors = manifest.get("payload_descriptors") or {}
    _check(errors, all(descriptors.get(key) is True for key in ("at_rest", "compact", "expanded_sarf", "expanded_nahw", "hover", "per_appearance", "readback")), "manifest payload descriptors are incomplete")
    _check(errors, descriptors.get("candidate_status") == "candidate_with_source_gaps", "manifest payload candidate status is wrong")
    pngs = [path for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".png"]
    _check(errors, not pngs, "a PNG is tracked or present in the proof packet")


def validate_packet(output_dir: Path, whitelist_path: Path, entries_path: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "source-selection.json",
        "source-occurrence.json",
        "canonical-facts.json",
        "typed-edge-graph.jsonl",
        "crosswalk-forward.json",
        "crosswalk-reverse.json",
        "shared-compiler-payload.json",
        "render-proof.json",
        "PROOFV-MANIFEST.json",
    ]
    missing = [name for name in required if not (output_dir / name).is_file()]
    if missing:
        return ["missing required artifact(s): " + ", ".join(missing)]
    try:
        selection = _json(output_dir / "source-selection.json")
        source_occurrence = _json(output_dir / "source-occurrence.json")
        facts = _json(output_dir / "canonical-facts.json")
        graph = _jsonl(output_dir / "typed-edge-graph.jsonl")
        forward = _json(output_dir / "crosswalk-forward.json")
        reverse = _json(output_dir / "crosswalk-reverse.json")
        payload = _json(output_dir / "shared-compiler-payload.json")
        render = _json(output_dir / "render-proof.json")
        manifest = _json(output_dir / "PROOFV-MANIFEST.json")
    except Exception as exc:
        return [f"cannot load proof packet: {exc}"]

    _check(errors, selection.get("schema") == "qamus.proofv.selection.v1", "selection schema is wrong")
    _check(errors, source_occurrence.get("schema") == "qamus.proofv.source_occurrence.v1", "source occurrence schema is wrong")
    _check(errors, source_occurrence.get("surface") == TARGET_SURFACE, "source occurrence surface is not exact")
    _check(errors, source_occurrence.get("loc") == TARGET_LOC, "source occurrence location is wrong")
    _check(errors, source_occurrence.get("gloss_fields_excluded") is True and source_occurrence.get("read_only") is True, "source occurrence is not read-only/gloss-free")
    _validate_source_survey(errors, source_occurrence, selection, whitelist_path, output_dir)
    _validate_crosswalk(errors, forward, reverse, selection)
    _validate_graph(errors, graph, manifest)
    fact_map = _validate_facts(errors, facts, manifest)
    _validate_payload(errors, payload, fact_map)
    _validate_render_and_manifest(errors, render, manifest, output_dir)

    try:
        if entries_path is None:
            entry_fixture = _json(output_dir / "entry-fixture.json")
            entries = [entry_fixture]
        else:
            entries = _jsonl(entries_path)
        entry = next((row for row in entries if str(row.get("id")) == ENTRY_ID), None)
        _check(errors, isinstance(entry, dict), "nearest entry is absent from entries.jsonl")
        if entry:
            _check(errors, " ".join(str(entry.get("root") or "").split()) == "ت ب ع", "nearest entry root is not ت ب ع")
            _check(errors, bool(entry.get("senses")) and str(entry["senses"][0].get("ar") or ""), "nearest entry lacks its documented sense surface")
    except Exception as exc:  # pragma: no cover - surfaced as a gate failure
        errors.append(f"cannot read entries: {exc}")
    _check(errors, fact_projectors.REGISTRY.contract(fact_projectors.PROOFV_VERB_PROJECTOR_ID)["gate_tier"] == "two_vote_required", "PROOF-V projector is not two-vote gated")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--whitelist", type=Path, default=None, help="external corpus (optional; committed fixture used when absent)")
    parser.add_argument("--entries", type=Path, default=None, help="external entries (optional; committed fixture used when absent)")
    parser.add_argument("--self-test", action="store_true", help="run the complete local packet gate")
    args = parser.parse_args(argv)
    errors = validate_packet(args.output_dir, args.whitelist, args.entries)
    if errors:
        print("PROOF-V VALIDATION FAIL")
        for error in errors:
            print("- " + error)
        return 1
    print("PROOF-V VALIDATION PASS (chain, facts, payload, render proof, candidate gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
