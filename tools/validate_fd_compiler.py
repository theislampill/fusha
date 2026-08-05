"""Validator for the bounded F-D compiler fixtures and 455-row dry-run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools import fact_ledger
from tools.fd_compiler import (
    METRIC_KEYS,
    PROJECTOR_ID,
    PRODUCER_ID,
    REPORT_SCHEMA,
    SCHEMA,
    SUFAHA_BODY,
    SUFAHA_SURFACE,
    VERDICT_SCHEMA,
    _canonical_json,
)
from tools.typed_claim_contract import validate_contract_record


FD_DIR = _ROOT / "qamus" / "examples" / "fd"
CONTRACT_SCHEMA = _ROOT / "qamus" / "schemas" / "typed-claim-contract.schema.json"
PAYLOAD_SCHEMA = _ROOT / "qamus" / "schemas" / "fd-normalized-public-payload.schema.json"
REPORT_SCHEMA_PATH = _ROOT / "qamus" / "schemas" / "fd-455-report.schema.json"
REGISTRY_PATH = _ROOT / "qamus" / "lattice" / "registered-projectors.json"


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _schema_errors(value: Any, path: Path) -> list[str]:
    errors: list[str] = []
    fact_ledger._validate_node(value, _load(path), "$", errors, _load(path))
    return errors


def _recursive_live_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        if "live_mutation_allowed" in value and value["live_mutation_allowed"] is not False:
            errors.append(f"{path}.live_mutation_allowed must be false")
        for key, child in value.items():
            errors.extend(_recursive_live_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_recursive_live_errors(child, f"{path}[{index}]"))
    return errors


def validate_sufaha_contract(contract: dict[str, Any]) -> list[str]:
    errors = validate_contract_record(contract)
    if errors:
        return errors
    expected_modes = {
        "singular_plural_relation": "direct_source_attestation",
        "plural_formation": "direct_source_attestation",
        "root": "cross_source_corroboration",
        "singular_pattern": "direct_source_attestation",
        "plural_pattern": "direct_source_attestation",
        "paired_y_removal": "paired_form_inference",
        "plural_lexical_body": "normalized_lexical_body",
        "case_ending": "direct_source_attestation",
        "governor_relation": "direct_source_attestation",
    }
    by_type = {fact["fact_type"]: fact for fact in contract["facts"]}
    for fact_type, mode in expected_modes.items():
        if by_type.get(fact_type, {}).get("evidence_mode") != mode:
            errors.append(f"fact {fact_type} has the wrong owner-mandated evidence mode")
    root_addresses = {
        address["address"]
        for address in by_type.get("root", {}).get("source_evidence", {}).get("source_addresses", [])
    }
    for required in ("qac:2:13:12:root", "qac:2:282:40:root", "entry:1ffcc554ec44:root"):
        if required not in root_addresses:
            errors.append(f"root fact is missing corroborating address {required}")
    if not any("#MCP:" in address for address in root_addresses):
        errors.append("root fact is missing an explicit MCP evidence address")
    paired = by_type.get("paired_y_removal", {})
    if not paired.get("derivation_chain"):
        errors.append("paired_y_removal must retain its derivation chain")
    elif not {by_type["singular_pattern"]["fact_id"], by_type["plural_pattern"]["fact_id"]}.issubset(
        set(paired.get("dependencies", {}).get("fact_ids", []))
    ):
        errors.append("paired_y_removal dependencies must include both certified pattern facts")
    tensions = contract.get("tension_records", [])
    if len(tensions) != 1 or tensions[0].get("status") != "unresolved":
        errors.append("Ṣufahāʾ fixture must carry exactly one unresolved tension record")
    for fact in contract["facts"]:
        for contradiction in fact.get("contradiction_records", []):
            if fact.get("certification", {}).get("status") != "certified":
                errors.append(f"tension attachment contaminated fact certification: {fact['fact_type']}")
    errors.extend(_recursive_live_errors(contract))
    return errors


def validate_payload(payload: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors = _schema_errors(payload, PAYLOAD_SCHEMA)
    errors.extend(_recursive_live_errors(payload))
    if payload.get("schema") != SCHEMA:
        errors.append("payload schema identifier drifted")
    if payload.get("canonical_identity", {}).get("surface") != SUFAHA_SURFACE:
        errors.append("payload canonical surface drifted")
    spans = payload.get("at_rest_spans", [])
    if "".join(str(span.get("surface", "")) for span in spans) != SUFAHA_SURFACE:
        errors.append("at-rest spans do not reconstruct the exact surface")
    if [(span.get("start"), span.get("end")) for span in spans] != [(0, 2), (2, 11), (11, 12)]:
        errors.append("at-rest span boundaries are not the required article/body/case run")
    known_ids = {fact["fact_id"] for fact in contract.get("facts", [])}
    for index, span in enumerate(spans):
        if not set(span.get("owner_fact_ids", [])).issubset(known_ids):
            errors.append(f"at_rest_spans[{index}] has an unknown fact owner")
    for index, component in enumerate(payload.get("components", [])):
        if not set(component.get("fact_ids", [])).issubset(known_ids):
            errors.append(f"components[{index}] has an unknown fact owner")
        if not all(component.get(key) for key in ("label", "visual_equivalent", "sarf", "nahw", "learner_text")):
            errors.append(f"components[{index}] is missing rich or learner-language fields")
    if payload.get("comparison", {}).get("root") != "س ف ه":
        errors.append("comparison does not expose root س ف ه")
    if payload.get("comparison", {}).get("singular", {}).get("pattern") != "فَعِيل":
        errors.append("comparison does not expose فَعِيل")
    if payload.get("comparison", {}).get("plural", {}).get("pattern") != "فُعَلَاء":
        errors.append("comparison does not expose فُعَلَاء")
    if payload.get("unresolved_tension", {}).get("status") != "unresolved":
        errors.append("unresolved jām id/mushtaq tension is not visible")
    if not payload.get("exact_reconstruction", {}).get("passed"):
        errors.append("exact reconstruction witness is not passing")
    if not payload.get("entry_linkage", {}).get("occurrence_to_entry") or not payload.get("entry_linkage", {}).get("entry_to_occurrence"):
        errors.append("entry reciprocity is incomplete")
    repeated = payload.get("repeated_appearance_parity", {})
    if repeated.get("page_trace_inferred"):
        errors.append("repeated page appearances must never be inferred")
    if not repeated.get("same_family_payload_id"):
        errors.append("family members do not share the generated family payload expectation")
    proof_ids = {point.get("id") for point in payload.get("proof_points", [])}
    required_proof_ids = {
        "canonical_identity", "at_rest_rich_projection", "rich_sarf_explanation", "rich_nahw_explanation",
        "singular_plural_comparison", "root_s_f_h", "singular_pattern_fa_iil", "plural_pattern_fu_alaa",
        "retained_radicals", "removed_ya", "introduced_alif_hamza", "lexical_body", "lexical_body_vs_case",
        "nominative_reason", "exact_governor", "non_colour_equivalents", "kawkab_mono_font",
        "exact_reconstruction", "repeated_appearance_parity", "entry_reciprocity", "provenance_projector",
        "unresolved_jamid_mushtaq",
    }
    if proof_ids != required_proof_ids:
        errors.append("the generated proof does not expose exactly the 22 owner points")
    source_clean = _canonical_json(payload)
    for forbidden in ("source_quotation", "evidence_verbatim", "MCP", "QAC"):
        if forbidden in source_clean:
            errors.append(f"public payload leaks internal evidence field {forbidden}")
    return errors


def validate_parity(parity: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    errors = _recursive_live_errors(parity)
    if parity.get("reconstructed_surface") != SUFAHA_SURFACE or not parity.get("exact_reconstruction_passed"):
        errors.append("parity fixture exact reconstruction failed")
    if not parity.get("entry_reciprocity", {}).get("occurrence_to_entry") or not parity.get("entry_reciprocity", {}).get("entry_to_occurrence"):
        errors.append("parity fixture is missing entry reciprocity")
    if parity.get("repeated_appearance_parity", {}).get("page_trace_inferred"):
        errors.append("parity fixture inferred page traces")
    if not parity.get("repeated_appearance_parity", {}).get("same_family_payload_id"):
        errors.append("parity fixture did not assert same-family payload consumption")
    if parity.get("same_payload_consumption", {}).get("payload_id") != "fd.family.sufaha.v1":
        errors.append("family payload ID drifted")
    return errors


def _flag_count(rows: Iterable[dict[str, Any]], flag: str) -> int:
    return sum(flag in row.get("flags", []) for row in rows)


def validate_candidate_report(report: dict[str, Any], verdicts: Sequence[dict[str, Any]]) -> list[str]:
    errors = _schema_errors(report, REPORT_SCHEMA_PATH)
    errors.extend(_recursive_live_errors(report))
    if report.get("schema") != REPORT_SCHEMA or report.get("verified_row_count") != 455:
        errors.append("455-row report identity/count is wrong")
    if len(verdicts) != 455:
        errors.append(f"candidate verdict count is {len(verdicts)}, expected 455")
    if len({row.get("loc") for row in verdicts}) != len(verdicts):
        errors.append("candidate verdict locations are not unique")
    for index, row in enumerate(verdicts):
        if row.get("schema") != VERDICT_SCHEMA:
            errors.append(f"verdict {index} has the wrong schema")
        if row.get("compile_mode") != "candidate":
            errors.append(f"verdict {index} is not candidate mode")
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"verdict {index} allows live mutation")
        if row.get("assigned_projector_id") != PROJECTOR_ID:
            errors.append(f"verdict {index} has no assigned F-D projector")
        if not row.get("primary_blocker"):
            errors.append(f"verdict {index} has no primary blocker")
    expected = {
        METRIC_KEYS[0]: sum(row.get("compile_status") == "compiled_review_queue" for row in verdicts),
        METRIC_KEYS[1]: _flag_count(verdicts, "linguistic_consistency"),
        METRIC_KEYS[2]: _flag_count(verdicts, "span_ownership"),
        METRIC_KEYS[3]: _flag_count(verdicts, "learner_language_fields"),
        METRIC_KEYS[4]: _flag_count(verdicts, "entry_linkage"),
        METRIC_KEYS[5]: _flag_count(verdicts, "projector"),
        METRIC_KEYS[6]: _flag_count(verdicts, "morphology_producer"),
        METRIC_KEYS[7]: _flag_count(verdicts, "nahw_producer"),
        METRIC_KEYS[8]: _flag_count(verdicts, "source_scholar_review"),
        METRIC_KEYS[9]: sum(bool(row.get("repeated_page_trace_covered")) for row in verdicts),
        METRIC_KEYS[10]: _flag_count(verdicts, "parity"),
        METRIC_KEYS[11]: _flag_count(verdicts, "exact_reconstruction"),
    }
    if report.get("metrics") != expected:
        errors.append("report metrics do not recompute from the per-row matrix")
    if sum(report.get("primary_blocker_counts", {}).values()) != len(verdicts):
        errors.append("primary blocker assignment does not cover every row")
    if report.get("projector_id") != PROJECTOR_ID or report.get("producer_id") != PRODUCER_ID:
        errors.append("report projector/producer lineage drifted")
    return errors


def validate_registry() -> list[str]:
    registry = _load(REGISTRY_PATH)
    matches = [item for item in registry.get("registered", []) if item.get("projector_id") == PROJECTOR_ID]
    errors: list[str] = []
    if len(matches) != 1:
        return [f"expected one registered {PROJECTOR_ID}, found {len(matches)}"]
    entry = matches[0].get("registry_entry", {})
    errors.extend(_schema_errors(entry, _ROOT / "qamus" / "schemas" / "projector-record.schema.json"))
    if matches[0].get("producer") != PRODUCER_ID or entry.get("producer") != PRODUCER_ID:
        errors.append("registered F-D projector producer drifted")
    return errors


def validate_fixtures(
    contract_path: Path = FD_DIR / "sufaha-contract.json",
    payload_path: Path = FD_DIR / "sufaha-normalized-public-payload.json",
    parity_path: Path = FD_DIR / "sufaha-parity-fixture.json",
    html_path: Path = FD_DIR / "sufaha-card.html",
    report_path: Path = _ROOT / "qamus/reports/calibration-455/fd-455-report.json",
    verdict_path: Path = _ROOT / "qamus/reports/calibration-455/fd-455-verdicts.jsonl",
) -> list[str]:
    errors: list[str] = []
    contract = _load(contract_path)
    payload = _load(payload_path)
    parity = _load(parity_path)
    report = _load(report_path)
    verdicts = _load_jsonl(verdict_path)
    errors.extend(validate_sufaha_contract(contract))
    errors.extend(validate_payload(payload, contract))
    errors.extend(validate_parity(parity, payload))
    errors.extend(validate_candidate_report(report, verdicts))
    errors.extend(validate_registry())
    html_text = Path(html_path).read_text(encoding="utf-8")
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    if embedded not in html_text:
        errors.append("HTML does not embed the generated normalized payload exactly")
    for marker in ("renderCompact(payload)", "renderExpanded(payload)", "document.fonts.check", "window.__reconCheck", "live_mutation_allowed=false"):
        if marker not in html_text:
            errors.append(f"HTML proof marker missing: {marker}")
    font_path = Path(html_path).parent / "assets" / "KawkabMono-Regular.woff2"
    if not font_path.is_file() or font_path.stat().st_size < 1000:
        errors.append("Kawkab Mono Qamus woff2 asset is missing")
    render_proof_path = Path(html_path).parent / "render-proof.json"
    screenshot_path = Path(html_path).parent / "sufaha-card.png"
    if not render_proof_path.is_file():
        errors.append("headless render proof is missing")
    else:
        render_proof = _load(render_proof_path)
        for key in ("font_check", "exact_reconstruction", "compact_present", "expanded_present", "same_payload_identity"):
            if render_proof.get(key) is not True:
                errors.append(f"headless render proof failed: {key}")
        if render_proof.get("live_mutation_allowed") is not False:
            errors.append("headless render proof allows live mutation")
    if screenshot_path.is_file() and screenshot_path.stat().st_size < 1000:
        errors.append("headless render screenshot exists but is truncated")
    # A MISSING screenshot is not a contract failure: repository policy ignores
    # *.png (screenshots are local-only artifacts), so fresh clones and CI have
    # none. The durable render attestation is the committed render-proof.json,
    # validated above (font_check, exact_reconstruction, compact/expanded
    # presence, same-payload identity, live_mutation_allowed=false).
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    errors = validate_fixtures()
    if errors:
        print("FD COMPILER VALIDATION FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("FD COMPILER SELF-TEST PASS (contract, payload, HTML, parity, registry, and 455-row matrix)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
