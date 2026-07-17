#!/usr/bin/env python3
"""Validate the committed PROOF-N noun proof packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam2_lexical_producer
from tools import proofn_noun_sufaha as proofn
from tools.build_typed_edge_crosswalk import build_graph, read_jsonl
from tools.validate_typed_edge_graph import CHECK_NAMES, validate_graph


REQUIRED_EDGE_TYPES = {
    "page_context_entry_edge",
    "source_card_edge",
    "selected_example_edge",
    "canonical_occurrence_edge",
    "display_local_to_canonical_crosswalk_edge",
    "projection_input_edge",
    "certified_fact_attachment_edge",
    "form_entry_edge",
    "lexeme_entry_edge",
    "sense_entry_edge",
    "root_family_edge",
    "shared_compiler_edge",
    "rich_projection_edge",
    "hover_structure_edge",
    "readback_target_edge",
    "rendered_appearance_edge",
    "decision_evidence_edge",
    "reverse_trace_edge",
    "source_evidence_edge",
}


def _fixture_typed_edge_report() -> dict[str, Any]:
    fixture_dir = proofn.ROOT / "qamus" / "examples" / "edges"
    entries = read_jsonl(fixture_dir / "entries.fixture.jsonl")
    ledger = read_jsonl(fixture_dir / "ledger.fixture.jsonl")
    whitelist = read_jsonl(fixture_dir / "whitelist.fixture.jsonl")
    appearances = read_jsonl(fixture_dir / "appearances.fixture.jsonl")
    facts = [
        row for row in read_jsonl(fixture_dir / "facts.fixture.jsonl")
        if row.get("fact_id") != "fact-orphan"
    ]
    bundle = build_graph(
        entries=entries,
        ledger_rows=ledger,
        whitelist_rows=whitelist,
        appearance_rows=appearances,
        fact_rows=facts,
    )
    return validate_graph(bundle, entries, ledger, whitelist, appearances, facts)


def _contains_forbidden_public_text(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(token in lowered for token in ("mcp", "qac", "evidence_verbatim", "source_quotation"))
    if isinstance(value, list):
        return any(_contains_forbidden_public_text(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_forbidden_public_text(item) for item in value.values())
    return False


def _tracked_pngs(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", "*.png"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except OSError:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _edge_map(edges: list[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    for edge in edges:
        result.setdefault(str(edge.get("edge_type")), []).append(edge)
    return result


def validate_proof(proof: Mapping[str, Any]) -> list[str]:
    """Return all proof-specific and boundary errors; never raise on a mutation."""

    errors: list[str] = []

    def error(message: str) -> None:
        errors.append(message)

    manifest = proof.get("manifest") or {}
    identity = manifest.get("identity") or {}
    contract = proof.get("contract") or {}
    payload = proof.get("payload") or {}
    edges = proof.get("edges") or []
    edge_map = _edge_map(edges)

    expected_identity = {
        "lexical_entry_id": proofn.LEXICAL_ENTRY_ID,
        "page_context_entry_id": proofn.PAGE_CONTEXT_ENTRY_ID,
        "canonical_location": proofn.SUFAHA_LOC,
        "surface": proofn.SUFAHA_SURFACE,
        "lexical_body": proofn.SUFAHA_BODY,
        "documented_plural_form": proofn.SUFAHA_BODY,
        "sense_node_id": proofn.SENSE_NODE_ID,
        "card_ref": "2:13",
        "card_node_id": proofn.CARD_NODE_ID,
        "selected_word_node_id": proofn.SELECTED_WORD_NODE_ID,
        "occurrence_node_id": proofn.OCCURRENCE_NODE_ID,
    }
    for key, expected in expected_identity.items():
        if identity.get(key) != expected:
            error(f"identity mismatch for {key}: expected {expected!r}")
    if manifest.get("mode") != "candidate":
        error("authorization boundary: manifest is not candidate mode")
    if manifest.get("authorization_state") != proofn.AUTHORIZATION_STATE:
        error("authorization boundary: manifest authorization is not pre_apply_not_authorized")
    split = manifest.get("source_identity_split") or {}
    if split.get("page_context_edge_target") != f"entry:{proofn.PAGE_CONTEXT_ENTRY_ID}":
        error("page-context identity split is missing")
    if split.get("lexeme_edge_target") != f"entry:{proofn.LEXICAL_ENTRY_ID}":
        error("lexeme identity split is missing")
    if split.get("page_context_retained_separately") is not True:
        error("page-context identity was not retained separately")

    occurrence = contract.get("canonical_occurrence") or {}
    if len(contract.get("facts") or []) != 11:
        error("certified fact count is not 11")
    for index, fact in enumerate(contract.get("facts") or [], 1):
        if fact.get("certification", {}).get("status") != "certified":
            error(f"certified fact {index} is not certified")
    if occurrence.get("occurrence_id") != "quran:2:13:12":
        error("canonical occurrence is not quran:2:13:12")
    if occurrence.get("surface") != proofn.SUFAHA_SURFACE:
        error("canonical occurrence surface is wrong")
    if occurrence.get("entry_id") != proofn.LEXICAL_ENTRY_ID:
        error("canonical occurrence is not attached to the lexical entry")
    tension = contract.get("tension_records") or []
    if not tension or tension[0].get("status") != "unresolved":
        error("jamid/mushtaq tension is not recorded unresolved")

    comparison = payload.get("comparison") or {}
    if comparison.get("singular", {}).get("surface") != "سَفِيه":
        error("singular form is missing")
    if comparison.get("plural", {}).get("surface") != "سُفَهَاء":
        error("plural form is missing")
    if comparison.get("root") != "س ف ه":
        error("root س ف ه is missing")
    if comparison.get("singular", {}).get("pattern") != "فَعِيل":
        error("singular pattern فَعِيل is missing")
    if comparison.get("plural", {}).get("pattern") != "فُعَلَاء":
        error("plural pattern فُعَلَاء is missing")
    if comparison.get("retained_radicals") != ["س", "ف", "ه"]:
        error("retained radicals are wrong")
    if comparison.get("removed") != "ي":
        error("removed singular-template ي is missing")
    if comparison.get("introduced") != ["ا", "ء"]:
        error("introduced plural-template letters are wrong")

    spans = payload.get("at_rest_spans") or []
    expected_spans = [
        (0, 2, "ال"),
        (2, 11, "سُّفَهَاء"),
        (11, 12, "ُ"),
    ]
    if [(span.get("start"), span.get("end"), span.get("surface")) for span in spans] != expected_spans:
        error("span reconstruction or lexical-body/case span boundary is wrong")
    if "".join(str(span.get("surface", "")) for span in spans) != proofn.SUFAHA_SURFACE:
        error("exact reconstruction failed")
    if payload.get("canonical_identity", {}).get("surface") != proofn.SUFAHA_SURFACE:
        error("payload canonical surface is wrong")

    payload_id = payload.get("payload_id")
    views = [payload.get("compact_view"), payload.get("expanded_view"), payload.get("rich_hover")]
    if not payload_id or any(not isinstance(view, dict) or view.get("payload_id") != payload_id for view in views):
        error("compact, expanded, and rich-hover payload identity is not shared")
    expanded = payload.get("expanded_view") or {}
    if proofn.PUBLIC_LABEL_SARF not in str(expanded.get("sarf", "")):
        error("N-LANG/public label missing: Ṣarf")
    if proofn.PUBLIC_LABEL_NAHW not in str(expanded.get("nahw", "")):
        error("N-LANG/public label missing: Naḥw")
    hover = payload.get("rich_hover") or {}
    if hover.get("n_lang_clean") is not True:
        error("N-LANG rich hover is not marked clean")
    public_fields = [
        hover.get("learner_explanation"),
        hover.get("sarf"),
        hover.get("nahw"),
        payload.get("compact_view", {}).get("learner_explanation"),
        payload.get("expanded_view", {}).get("sarf"),
        payload.get("expanded_view", {}).get("nahw"),
    ]
    if any(_contains_forbidden_public_text(value) for value in public_fields):
        error("N-LANG public field contains internal source/process language")
    if "آمَنَ" not in str(hover.get("nahw")) or "subject" not in str(hover.get("nahw")).lower():
        error("Naḥw projection does not retain the governor/subject relation")
    if "not part" not in " ".join(
        str(component.get("sarf", "")) for component in payload.get("components", [])
    ).lower():
        error("case mark is not explicitly separated from plural formation")

    if payload.get("authorization_state") != proofn.AUTHORIZATION_STATE:
        error("authorization boundary: payload is not pre_apply_not_authorized")
    if payload.get("live_mutation_allowed") is not False:
        error("authorization boundary: live mutation is enabled")
    materialization = payload.get("materialization") or {}
    if materialization.get("public_materialization_allowed") is not False:
        error("authorization boundary: public materialization is enabled")
    if (payload.get("readback_target") or {}).get("status") != proofn.READBACK_STATUS:
        error("readback target is not declared_not_measured")

    missing_types = REQUIRED_EDGE_TYPES - set(edge_map)
    for edge_type in sorted(missing_types):
        error(f"typed graph missing required edge type {edge_type}")
    for edge in edges:
        if edge.get("schema") != "qamus.graph_edge.v1":
            error(f"typed edge has the wrong schema: {edge.get('edge_id')}")
        if edge.get("status") not in {"candidate", "deterministic_exact"}:
            error(f"typed edge leaves candidate boundary: {edge.get('edge_id')}")
        if not edge.get("evidence"):
            error(f"typed edge has no evidence: {edge.get('edge_id')}")
        if not edge.get("from_node_id") or not edge.get("to_node_id"):
            error(f"typed edge has an untyped endpoint: {edge.get('edge_id')}")

    page_edges = edge_map.get("page_context_entry_edge", [])
    page_targets = {edge.get("to_node_id") for edge in page_edges}
    if page_targets != {f"entry:{proofn.PAGE_CONTEXT_ENTRY_ID}"}:
        error("page-context edge target is not the retained page-context entry")
    for edge in edge_map.get("lexeme_entry_edge", []):
        if edge.get("to_node_id") == f"entry:{proofn.PAGE_CONTEXT_ENTRY_ID}" or (edge.get("details") or {}).get("page_context_only"):
            error("page-context entry promoted to lexeme edge")
    lexeme_targets = {edge.get("to_node_id") for edge in edge_map.get("lexeme_entry_edge", [])}
    if lexeme_targets != {f"entry:{proofn.LEXICAL_ENTRY_ID}"}:
        error("lexeme edge does not resolve only to the documented lexical entry")
    attachment = edge_map.get("certified_fact_attachment_edge", [])
    if not attachment:
        error("certified fact attachment edge is missing")
    else:
        details = attachment[0].get("details") or {}
        if details.get("fact_count") != 11 or details.get("certified_fact_count") != 11:
            error("certified fact attachment count is not 11/11")
        if len(details.get("packet_addresses") or []) != 11:
            error("certified fact attachment does not carry all packet addresses")
    form_edges = edge_map.get("form_entry_edge", [])
    if not any((edge.get("details") or {}).get("form_address") == f"entry:{proofn.LEXICAL_ENTRY_ID}:usage[0].forms[1]" for edge in form_edges):
        error("form edge lacks the documented plural form address")
    if not any(
        (edge.get("details") or {}).get("sense_id") == proofn.SENSE_NODE_ID
        for edge in edge_map.get("sense_entry_edge", [])
    ):
        error("sense edge lacks sense identity")
    if not any(
        (edge.get("details") or {}).get("root") == "س ف ه"
        for edge in edge_map.get("root_family_edge", [])
    ):
        error("root-family edge lacks retained root")
    decision_edges = edge_map.get("decision_evidence_edge", [])
    if len(decision_edges) < 11:
        error("decision_evidence_edge records do not cover all 11 certified facts")
    if not all(edge.get("evidence") for edge in decision_edges):
        error("decision evidence backlink is empty")
    if len(edge_map.get("rendered_appearance_edge", [])) != 2:
        error("appearance parity edge count is not two")
    else:
        for edge in edge_map["rendered_appearance_edge"]:
            details = edge.get("details") or {}
            if details.get("canonical_surface") != proofn.SUFAHA_SURFACE:
                error("appearance edge has the wrong canonical surface")
            if details.get("payload_id") != payload_id or details.get("same_payload_id") is not True:
                error("appearance edge does not carry the shared payload id")
            if details.get("readback_target_status") != proofn.READBACK_STATUS:
                error("appearance edge makes an unmeasured readback claim")

    parity = payload.get("appearance_parity") or {}
    appearances = parity.get("appearances") or []
    if len(appearances) != 2 or parity.get("parity") is not True:
        error("appearance index parity is incomplete")
    if not all(item.get("same_payload_id") is True and item.get("payload_id") == payload_id for item in appearances):
        error("not every repeated appearance consumes the same payload")

    fam2 = proof.get("fam2_record") or {}
    if fam2.get("projection", {}).get("status") != "candidate":
        error("FAM2 formation record is not candidate")
    else:
        errors.extend(f"FAM2: {message}" for message in fam2_lexical_producer.validate_formation_record(fam2))

    render = proof.get("render_proof") or {}
    for key in ("font_check", "exact_reconstruction", "compact_present", "expanded_present", "same_payload_identity", "appearance_parity"):
        if render.get(key) is not True:
            error(f"render-proof pattern failed: {key}")
    if render.get("live_mutation_allowed") is not False:
        error("render-proof authorization boundary failed")
    if render.get("readback_target_status") != proofn.READBACK_STATUS:
        error("render-proof readback status is not declared_not_measured")

    if _tracked_pngs(proof.get("proof_dir", proofn.ROOT)):
        error("PNG policy: a PNG is tracked")

    fixture_report = _fixture_typed_edge_report()
    if not fixture_report.get("ok"):
        error("one or more existing typed-graph validators failed")
    if [check.get("name") for check in fixture_report.get("checks", [])] != CHECK_NAMES:
        error("the ten named typed-graph validators are not all present")
    if any(not check.get("ok") for check in fixture_report.get("checks", [])):
        error("the ten named typed-graph validators are not all passing")
    return errors


def validate_proofn_artifacts(proof_dir: Path | str = proofn.PROOF_DIR) -> list[str]:
    return validate_proof(proofn.load_proof_artifacts(proof_dir))


def _write_validation_reports(proof: Mapping[str, Any], fixture_report: Mapping[str, Any]) -> None:
    proof_dir = Path(proof["proof_dir"])
    proofn._write_json(proof_dir / "typed-edge-validation.json", fixture_report)
    errors = validate_proof(proof)
    proofn._write_json(proof_dir / "proofn-validation.json", {
        "schema": "qamus.proofn.validation.v1",
        "ok": not errors,
        "errors": errors,
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--proof-dir", type=Path, default=proofn.PROOF_DIR)
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.error("use --self-test")
    proof = proofn.load_proof_artifacts(args.proof_dir)
    fixture_report = _fixture_typed_edge_report()
    _write_validation_reports(proof, fixture_report)
    errors = validate_proof(proofn.load_proof_artifacts(args.proof_dir))
    if errors:
        print("PROOFN NOUN PROOF FAIL")
        print("\n".join(errors))
        return 1
    print("PROOFN NOUN PROOF PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
