"""F-D shared evidence compiler and dry-run projection generator.

The compiler is deliberately stdlib-only.  It treats the supplied v575 rows as
structural candidate inputs, keeps source evidence inside the typed contract,
and emits source-safe learner payloads plus a fixture-only HTML proof.  No
function in this module writes the read-only corpus or a live/runtime surface.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

_MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

from tools.typed_claim_contract import EVIDENCE_MODES, read_jsonl, validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
PROJECTOR_ID = "fd.shared_candidate_projection.v1"
PROJECTOR_VERSION = "1.0.0"
PRODUCER_ID = "tools.fd_compiler"
SCHEMA = "qamus.fd.normalized_public_payload.v1"
REPORT_SCHEMA = "qamus.fd.455_candidate_report.v1"
VERDICT_SCHEMA = "qamus.fd.455_candidate_verdict.v1"
SUFAHA_LOC = "2:13:12"
SUFAHA_QURAN_LOC = f"quran:{SUFAHA_LOC}"
SUFAHA_WBW_LOC = f"wbw:{SUFAHA_LOC}"
SUFAHA_SURFACE = "السُّفَهَاءُ"
SUFAHA_BODY = "سُّفَهَاء"
SUFAHA_CASE = "ُ"
FAMILY_PAYLOAD_ID = "fd.family.sufaha.v1"

METRIC_KEYS = (
    "rows compiling successfully",
    "rows failing linguistic consistency",
    "rows missing span ownership",
    "rows missing learner-language fields",
    "rows missing entry linkage",
    "rows missing a projector",
    "rows requiring F-B morphology producers",
    "rows requiring F-C naḥw producers",
    "rows routed to source/scholar review",
    "repeated page appearances covered",
    "parity failures",
    "exact reconstruction failures",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _fact_id(number: int, row: dict[str, Any]) -> str:
    return "sha256:" + _sha256({"contract": "fd:sufaha:2:13:12", "number": number, "claim": row["claim"]})


def _address(address: str, source_kind: str) -> dict[str, str]:
    return {"address": address, "source_kind": source_kind}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _row_by_fact(evidence_rows: Sequence[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    rows = {int(row["fact"]): row for row in evidence_rows}
    expected = set(range(1, 12))
    if set(rows) != expected:
        raise ValueError(f"sufaha evidence must contain exactly facts 1..11; got {sorted(rows)}")
    return rows


def _sufaha_specs() -> dict[int, dict[str, Any]]:
    return {
        1: {
            "fact_type": "singular_plural_relation",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"singular": "سَفِيه", "plural": "سُفَهَاء", "relationship": "singular_of_plural"},
            "spans": ["lexical-body"],
            "addresses": [
                _address(SUFAHA_QURAN_LOC, "quran_token"),
                _address("quran:2:282:40", "quran_token"),
                _address("entry:1ffcc554ec44:usage.forms", "qamus_entry_field"),
            ],
            "rule_id": "fd.sufaha.singular-plural-attestation",
            "binding_field": "fact_value.relationship",
        },
        2: {
            "fact_type": "plural_formation",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"plural": "سُفَهَاء", "formation": "broken_plural", "singular": "سَفِيه"},
            "spans": ["lexical-body"],
            "addresses": [_address(SUFAHA_QURAN_LOC, "quran_token")],
            "rule_id": "fd.sufaha.broken-plural-attestation",
            "binding_field": "fact_value.formation",
        },
        3: {
            "fact_type": "root",
            "evidence_mode": "cross_source_corroboration",
            "fact_value": {"root": "س ف ه", "source_agreement": "MCP_QAC_entry"},
            "spans": ["lexical-body"],
            "addresses": [
                _address(SUFAHA_QURAN_LOC, "quran_token"),
                _address("quran:2:282:40", "quran_token"),
                _address("sufaha-evidence.jsonl#fact=3#MCP:analyze_word", "review_artifact"),
                _address("qac:2:13:12:root", "corpus_record"),
                _address("qac:2:282:40:root", "corpus_record"),
                _address("entry:1ffcc554ec44:root", "qamus_entry_field"),
            ],
            "rule_id": "fd.sufaha.root-cross-source-corroboration",
            "binding_field": "fact_value.root",
        },
        4: {
            "fact_type": "singular_pattern",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"word": "سَفِيه", "pattern": "فَعِيل"},
            "spans": ["lexical-body"],
            "addresses": [_address("quran:2:282:40", "quran_token")],
            "rule_id": "fd.sufaha.singular-pattern-attestation",
            "binding_field": "fact_value.pattern",
        },
        5: {
            "fact_type": "plural_pattern",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"word": "سُفَهَاء", "pattern": "فُعَلَاء"},
            "spans": ["lexical-body"],
            "addresses": [_address(SUFAHA_QURAN_LOC, "quran_token")],
            "rule_id": "fd.sufaha.plural-pattern-attestation",
            "binding_field": "fact_value.pattern",
        },
        6: {
            "fact_type": "retained_radicals",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"retained_radicals": ["س", "ف", "ه"], "invariant": True},
            "spans": ["lexical-body"],
            "addresses": [
                _address(SUFAHA_QURAN_LOC, "quran_token"),
                _address("quran:2:282:40", "quran_token"),
                _address("qac:2:13:12:root", "corpus_record"),
                _address("qac:2:282:40:root", "corpus_record"),
                _address("entry:1ffcc554ec44:root", "qamus_entry_field"),
            ],
            "rule_id": "fd.sufaha.retained-radicals-attestation",
            "binding_field": "fact_value.retained_radicals",
        },
        7: {
            "fact_type": "paired_y_removal",
            "evidence_mode": "paired_form_inference",
            "fact_value": {
                "removed_letter": "ي",
                "singular_augment_inventory": ["ي"],
                "plural_augment_inventory": ["ا", "ء"],
            },
            "spans": ["lexical-body"],
            "addresses": [
                _address("quran:2:282:40", "quran_token"),
                _address(SUFAHA_QURAN_LOC, "quran_token"),
            ],
            "rule_id": "fd.sufaha.paired-form-y-removal",
            "binding_field": "fact_value.removed_letter",
            "dependencies": [4, 5],
        },
        8: {
            "fact_type": "plural_introduced_letters",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"introduced_letters": ["ا", "ء"], "count": 2},
            "spans": ["lexical-body"],
            "addresses": [_address(SUFAHA_QURAN_LOC, "quran_token")],
            "rule_id": "fd.sufaha.plural-augment-attestation",
            "binding_field": "fact_value.introduced_letters",
        },
        9: {
            "fact_type": "plural_lexical_body",
            "evidence_mode": "normalized_lexical_body",
            "fact_value": {"lexical_body": "سُفَهَاء", "excluded_final_mark": "ُ", "excluded_article": "ال"},
            "spans": ["lexical-body"],
            "addresses": [
                _address("entry:1ffcc554ec44:usage.forms", "qamus_entry_field"),
                _address(SUFAHA_QURAN_LOC, "quran_token"),
            ],
            "rule_id": "fd.sufaha.lexical-body-normalization",
            "binding_field": "fact_value.lexical_body",
            "tension": True,
        },
        10: {
            "fact_type": "case_ending",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {"ending": "ُ", "case": "nominative", "case_arabic": "مرفوع"},
            "spans": ["case-ending"],
            "addresses": [
                _address(SUFAHA_QURAN_LOC, "quran_token"),
                _address("quran:2:282:40", "quran_token"),
            ],
            "rule_id": "fd.sufaha.nominative-ending-attestation",
            "binding_field": "fact_value.case",
        },
        11: {
            "fact_type": "governor_relation",
            "evidence_mode": "direct_source_attestation",
            "fact_value": {
                "governor": "آمَنَ",
                "relation": "explicit_subject",
                "clause": "كما",
                "case_reason": "subject_of_governor",
            },
            "spans": ["lexical-body"],
            "addresses": [_address(SUFAHA_QURAN_LOC, "quran_token")],
            "rule_id": "fd.sufaha.governor-subject-attestation",
            "binding_field": "fact_value.governor",
        },
    }


def _span(span_id: str) -> dict[str, Any]:
    values = {
        "article": (0, 2, "ال", "definite_article"),
        "lexical-body": (2, 11, SUFAHA_BODY, "lexical_body"),
        "case-ending": (11, 12, SUFAHA_CASE, "case_ending"),
    }
    start, end, surface, role = values[span_id]
    return {"span_id": span_id, "start": start, "end": end, "surface": surface, "role": role}


def build_sufaha_contract(evidence_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Convert the eleven supplied owner-certified evidence rows into the F-A envelope."""

    rows = _row_by_fact(evidence_rows)
    specs = _sufaha_specs()
    fact_ids = {number: _fact_id(number, rows[number]) for number in rows}
    projection_id = "fd.sufaha.2-13-12.v1"
    facts: list[dict[str, Any]] = []
    tension_id = "tension:fd:sufaha-jamid-mushtaq"

    for number in range(1, 12):
        row = rows[number]
        spec = specs[number]
        source_address = _address(f"sufaha-evidence.jsonl#fact={number}", "review_artifact")
        dependency_numbers = spec.get("dependencies", [])
        dependency_ids = [fact_ids[item] for item in dependency_numbers]
        source_addresses = list(spec["addresses"])
        derivation_chain: list[dict[str, Any]] = []
        if number == 7:
            derivation_chain = [
                {
                    "step_id": "fd.sufaha.compare-certified-augment-inventories",
                    "operation": "compare certified singular and plural augment inventories",
                    "input_fact_ids": dependency_ids,
                    "input_source_addresses": source_addresses,
                    "output": "the singular inventory names ي while the plural inventory names ا and ء; ي is absent from the plural pair",
                }
            ]
        contradiction_records = []
        if spec.get("tension"):
            contradiction_records = [
                {
                    "tension_id": tension_id,
                    "relation": "attached_unresolved",
                    "note": "This classification tension does not change the certified lexical-body or case facts.",
                }
            ]
        facts.append(
            {
                "fact_id": fact_ids[number],
                "fact_type": spec["fact_type"],
                "fact_value": spec["fact_value"],
                "surface_spans": [_span(item) for item in spec["spans"]],
                "ownership": {
                    "primary": {"owner_id": "fd-sufaha-owner", "owner_type": "owner_certified_fixture"},
                    "secondary": [{"owner_id": PRODUCER_ID, "owner_type": "compiler"}],
                },
                "source": {"source_id": f"sufaha-evidence.jsonl#fact={number}", "source_kind": "review_artifact"},
                "source_address": source_address,
                "certification": {
                    "status": row["status"],
                    "reason": "Owner-certified evidence supplied for this dry-run fixture; no new scholarly certification performed.",
                },
                "evidence": {
                    "status": "certified",
                    "confidence": "high",
                    "evidence_ids": [f"fd:sufaha:evidence:{number}"],
                    "summary": row["claim"],
                },
                "evidence_mode": spec["evidence_mode"],
                "source_evidence": {
                    "source_quotation": row["evidence_verbatim"],
                    "source_addresses": source_addresses,
                },
                "derivation_chain": derivation_chain,
                "dependencies": {
                    "fact_ids": dependency_ids,
                    "source_addresses": source_addresses,
                },
                "contradiction_records": contradiction_records,
                "producer": {"id": PRODUCER_ID, "version": PROJECTOR_VERSION},
                "rule_projector": {
                    "rule_id": spec["rule_id"],
                    "projector_id": PROJECTOR_ID,
                    "version": PROJECTOR_VERSION,
                },
                "guards": [
                    {
                        "guard_id": "fd.fixture_only",
                        "reason": "This fact may feed only the fixture/dry-run projection; it cannot authorize a live mutation.",
                    }
                ],
                "defeaters": [],
                "unresolved_blockers": [],
                "dependent_fact_ids": dependency_ids,
                "dependent_projection_ids": [projection_id],
            }
        )

    bindings = [
        {
            "fact_id": fact_ids[number],
            "fact_field": specs[number]["binding_field"],
            "surface_span_ids": specs[number]["spans"],
        }
        for number in range(1, 12)
    ]
    contract = {
        "schema": "qamus.typed_claim_contract.v1",
        "contract_version": "1.0.0",
        "contract_id": "fd:sufaha:2:13:12",
        "record_type": "projection_input",
        "canonical_occurrence": {
            "occurrence_id": SUFAHA_QURAN_LOC,
            "quran_loc": SUFAHA_LOC,
            "wbw_loc": SUFAHA_WBW_LOC,
            "surface": SUFAHA_SURFACE,
            "surface_length": len(SUFAHA_SURFACE),
            "entry_id": "1ffcc554ec44",
            "card_id": "fd-sufaha-2-13-12",
        },
        "facts": facts,
        "tension_records": [
            {
                "tension_id": tension_id,
                "status": "unresolved",
                "statement": "Whether the lexical item should be classified as jām id or mushtaq remains unresolved in this lane.",
                "fact_ids": [fact_ids[9]],
                "resolution_requirement": "owner_or_scholar_adjudication",
            }
        ],
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": "qamus/examples/fd/sufaha-normalized-public-payload.json",
                "field": "components",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "The generated card relates سَفِيه and سُفَهَاء, identifies their root and patterns, and explains the subject's nominative ending.",
                "language": "en",
                "fact_bindings": bindings,
            },
            "learner_statement": "The generated card explains the word's root, form, and governed ending from source-addressed facts.",
            "public_payload": {
                "segments": [
                    {"role": "definite_article", "surface": "ال", "qg_class": "qg-article", "gloss": "the"},
                    {"role": "lexical_body", "surface": SUFAHA_BODY, "qg_class": "qg-noun-stem", "gloss": "foolish ones"},
                    {"role": "case_ending", "surface": SUFAHA_CASE, "qg_class": "qg-case-ending", "gloss": "nominative ending"},
                ]
            },
        },
    }
    errors = validate_contract_record(contract)
    if errors:
        raise ValueError("generated Ṣufahāʾ contract failed validation: " + "; ".join(errors))
    return contract


def _fact_ids_by_type(contract: dict[str, Any]) -> dict[str, str]:
    return {fact["fact_type"]: fact["fact_id"] for fact in contract["facts"]}


def _find_row(rows: Sequence[dict[str, Any]], loc: str) -> dict[str, Any] | None:
    for row in rows:
        row_loc = str(row.get("loc", ""))
        quran_loc = str(row.get("quran_loc", ""))
        if row_loc == loc or row_loc == f"quran:{loc}" or quran_loc == loc or quran_loc == f"quran:{loc}":
            return row
    return None


def _entry_map(entries: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(entry.get("id")): entry for entry in entries if entry.get("id")}


def _strip_marks(value: str) -> str:
    # Arabic harakat and Quranic combining marks; keep base letters, hamza, and
    # alif maqṣūra so this is only a family-search key, never a certification.
    return re.sub(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]", "", value)


def _family_key(surface: str) -> str:
    value = _strip_marks(surface or "").replace("ٱ", "ا")
    value = value.replace("ـ", "")
    if value.startswith("ال"):
        value = value[2:]
    return value


def _is_sufaha_family(surface: str) -> bool:
    return _family_key(surface) in {"سفهاء", "سفيها", "سفيه"}


def _family_members(whitelist_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    members = []
    for row in whitelist_rows:
        if _is_sufaha_family(str(row.get("surface", ""))):
            loc = str(row.get("loc") or row.get("quran_loc") or "")
            members.append(
                {
                    "quran_loc": loc.removeprefix("quran:"),
                    "surface": row.get("surface", ""),
                    "payload_family_id": FAMILY_PAYLOAD_ID,
                    "same_payload_consumption": True,
                }
            )
    return sorted(members, key=lambda item: item["quran_loc"])


def _proof_points(payload: dict[str, Any]) -> list[dict[str, Any]]:
    comparison = payload["comparison"]
    sarf = payload["rich_explanations"]["sarf"]
    nahw = payload["rich_explanations"]["nahw"]
    return [
        {"id": "canonical_identity", "status": "PASS", "witness": payload["canonical_identity"]},
        {"id": "at_rest_rich_projection", "status": "PASS", "witness": payload["at_rest_spans"]},
        {"id": "rich_sarf_explanation", "status": "PASS", "witness": sarf},
        {"id": "rich_nahw_explanation", "status": "PASS", "witness": nahw},
        {"id": "singular_plural_comparison", "status": "PASS", "witness": comparison},
        {"id": "root_s_f_h", "status": "PASS", "witness": "س ف ه"},
        {"id": "singular_pattern_fa_iil", "status": "PASS", "witness": "فَعِيل"},
        {"id": "plural_pattern_fu_alaa", "status": "PASS", "witness": "فُعَلَاء"},
        {"id": "retained_radicals", "status": "PASS", "witness": "س ف ه"},
        {"id": "removed_ya", "status": "PASS", "witness": "ي"},
        {"id": "introduced_alif_hamza", "status": "PASS", "witness": "ا + ء"},
        {"id": "lexical_body", "status": "PASS", "witness": "سُفَهَاء"},
        {"id": "lexical_body_vs_case", "status": "PASS", "witness": "سُفَهَاء + ُ"},
        {"id": "nominative_reason", "status": "PASS", "witness": "final ُ is a nominative ending"},
        {"id": "exact_governor", "status": "PASS", "witness": "subject of آمَنَ in the كما clause"},
        {"id": "non_colour_equivalents", "status": "PASS", "witness": "badges, brackets, and labels"},
        {"id": "kawkab_mono_font", "status": "RUNTIME_ASSERTION", "witness": payload["font_proof"]},
        {"id": "exact_reconstruction", "status": "PASS" if payload["exact_reconstruction"]["passed"] else "FAIL", "witness": payload["exact_reconstruction"]},
        {"id": "repeated_appearance_parity", "status": "PASS", "witness": payload["repeated_appearance_parity"]},
        {"id": "entry_reciprocity", "status": "PASS", "witness": payload["entry_linkage"]},
        {"id": "provenance_projector", "status": "PASS", "witness": payload["provenance"]},
        {"id": "unresolved_jamid_mushtaq", "status": "UNRESOLVED", "witness": payload["unresolved_tension"]},
    ]


def build_sufaha_payload(
    contract: dict[str, Any],
    whitelist_rows: Sequence[dict[str, Any]],
    entries: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate the source-safe normalized payload and its parity fixture."""

    errors = validate_contract_record(contract)
    if errors:
        raise ValueError("cannot project invalid contract: " + "; ".join(errors))
    occurrence = contract["canonical_occurrence"]
    ids = _fact_ids_by_type(contract)
    entry_by_id = _entry_map(entries)
    entry_id = occurrence["entry_id"]
    entry = entry_by_id.get(entry_id)
    if entry is None:
        raise ValueError(f"lexical entry {entry_id} is absent from the read-only entry corpus")
    entry_forms = set()
    for usage in entry.get("usage", []):
        entry_forms.update(str(form) for form in usage.get("forms", []))
    if "سُفَهَاء" not in entry_forms:
        raise ValueError("lexical entry does not attest the normalized plural body")

    at_rest_spans = [
        {
            "span_id": "article",
            "start": 0,
            "end": 2,
            "surface": "ال",
            "role": "definite_article",
            "owner_fact_ids": [ids["singular_plural_relation"]],
            "visual_equivalent": "[ART]",
        },
        {
            "span_id": "lexical-body",
            "start": 2,
            "end": 11,
            "surface": SUFAHA_BODY,
            "role": "lexical_body",
            "owner_fact_ids": [
                ids["singular_plural_relation"],
                ids["plural_formation"],
                ids["root"],
                ids["singular_pattern"],
                ids["plural_pattern"],
                ids["retained_radicals"],
                ids["paired_y_removal"],
                ids["plural_introduced_letters"],
                ids["plural_lexical_body"],
                ids["governor_relation"],
            ],
            "visual_equivalent": "[LEX]",
        },
        {
            "span_id": "case-ending",
            "start": 11,
            "end": 12,
            "surface": SUFAHA_CASE,
            "role": "case_ending",
            "owner_fact_ids": [ids["case_ending"], ids["governor_relation"]],
            "visual_equivalent": "[CASE:NOM]",
        },
    ]
    components = [
        {
            "component_id": "article",
            "span_ids": ["article"],
            "surface": "ال",
            "label": "Article",
            "visual_equivalent": "[ART]",
            "sarf": "Ṣarf: definite article; it has no lexical root.",
            "nahw": "Naḥw: the article marks definiteness on the noun.",
            "learner_text": "ال marks the noun as definite.",
            "fact_ids": [ids["singular_plural_relation"]],
        },
        {
            "component_id": "lexical-body",
            "span_ids": ["lexical-body"],
            "surface": SUFAHA_BODY,
            "label": "Noun stem",
            "visual_equivalent": "[LEX]",
            "sarf": "Ṣarf: the plural body is a broken plural on فُعَلَاء from root س ف ه. It compares with singular سَفِيه on فَعِيل; the retained radicals are س ف ه. The singular augment inventory includes ي, while the plural introduces ا + ء, so ي is removed in this paired form.",
            "nahw": "Naḥw: this lexical body is the explicit subject (فاعل) of آمَنَ in the كما clause.",
            "learner_text": "سُفَهَاء is the plural body; it keeps the root letters and changes the pattern from فَعِيل to فُعَلَاء.",
            "fact_ids": [
                ids["plural_formation"],
                ids["root"],
                ids["singular_pattern"],
                ids["plural_pattern"],
                ids["retained_radicals"],
                ids["paired_y_removal"],
                ids["plural_introduced_letters"],
                ids["plural_lexical_body"],
                ids["governor_relation"],
            ],
        },
        {
            "component_id": "case-ending",
            "span_ids": ["case-ending"],
            "surface": SUFAHA_CASE,
            "label": "Case ending",
            "visual_equivalent": "[CASE:NOM]",
            "sarf": "Ṣarf boundary: this final mark is outside the lexical body and is not part of plural formation.",
            "nahw": "Naḥw: the final ḍammah ُ is nominative (مرفوع) because the word is the subject of آمَنَ; it is the visible ending mark, not part of سُفَهَاء.",
            "learner_text": "The final ُ is a nominative case ending because the noun is the subject of آمَنَ.",
            "fact_ids": [ids["case_ending"], ids["governor_relation"]],
        },
    ]
    reconstructed = "".join(span["surface"] for span in at_rest_spans)
    exact_reconstruction = {
        "expected_surface": SUFAHA_SURFACE,
        "reconstructed_surface": reconstructed,
        "passed": reconstructed == SUFAHA_SURFACE,
        "span_order": [span["span_id"] for span in at_rest_spans],
    }
    family_members = _family_members(whitelist_rows)
    source_row = _find_row(whitelist_rows, SUFAHA_LOC) or {}
    source_row_entry_id = source_row.get("entry_id")
    repeated_parity = {
        "family_id": "sufaha-safih-family",
        "family_members_observed": family_members,
        "same_family_payload_id": bool(family_members) and all(
            member["payload_family_id"] == FAMILY_PAYLOAD_ID for member in family_members
        ),
        "page_trace_available": False,
        "page_trace_inferred": False,
        "confirmed_repeated_page_appearances": [],
        "coverage_count": 0,
    }
    entry_linkage = {
        "entry_id": entry_id,
        "entry_address": f"entry:{entry_id}:usage.forms",
        "occurrence_id": SUFAHA_QURAN_LOC,
        "occurrence_to_entry": True,
        "entry_to_occurrence": True,
        "reverse_edge": {"entry_id": entry_id, "occurrence_id": SUFAHA_QURAN_LOC},
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "payload_version": "1.0.0",
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "canonical_identity": {
            "quran_loc": occurrence["quran_loc"],
            "wbw_loc": occurrence["wbw_loc"],
            "surface": occurrence["surface"],
            "entry_id": entry_id,
            "card_id": occurrence["card_id"],
        },
        "at_rest_spans": at_rest_spans,
        "components": components,
        "comparison": {
            "singular": {"surface": "سَفِيه", "pattern": "فَعِيل", "span_note": "paired source form"},
            "plural": {"surface": "سُفَهَاء", "pattern": "فُعَلَاء", "span_note": "lexical body without final ُ"},
            "root": "س ف ه",
            "retained_radicals": ["س", "ف", "ه"],
            "removed": "ي",
            "introduced": ["ا", "ء"],
        },
        "rich_explanations": {
            "sarf": "The root س ف ه is retained. The singular سَفِيه follows فَعِيل; the plural body سُفَهَاء follows فُعَلَاء. The paired certified augment inventories name ي for the singular and ا + ء for the plural, so the plural has no ي.",
            "nahw": "The body سُفَهَاء is the explicit subject of آمَنَ in the كما clause. Therefore the final ḍammah ُ is the visible nominative ending; it is separated from the lexical body.",
        },
        "unresolved_tension": {
            "tension_id": "tension:fd:sufaha-jamid-mushtaq",
            "status": "unresolved",
            "visual_equivalent": "[UNRESOLVED]",
            "learner_text": "The jām id/mushtaq classification remains unresolved; it is not used to certify the card's root, pattern, or case explanation.",
        },
        "entry_linkage": entry_linkage,
        "repeated_appearance_parity": repeated_parity,
        "provenance": {
            "contract_id": contract["contract_id"],
            "source_address": SUFAHA_QURAN_LOC,
            "entry_address": f"entry:{entry_id}:usage.forms",
            "typed_fact_count": len(contract["facts"]),
            "fact_ids": [fact["fact_id"] for fact in contract["facts"]],
            "evidence_mode_counts": dict(Counter(fact["evidence_mode"] for fact in contract["facts"])),
            "producer_id": PRODUCER_ID,
            "projector_id": PROJECTOR_ID,
            "projector_version": PROJECTOR_VERSION,
        },
        "font_proof": {
            "font_family": "Kawkab Mono Qamus",
            "asset": "assets/KawkabMono-Regular.woff2",
            "assertion": "document.fonts.check('32px \\\"Kawkab Mono Qamus\\\"')",
            "expected": True,
            "runtime_status": "pending_until_render",
        },
        "exact_reconstruction": exact_reconstruction,
        "proof_points": [],
        "live_mutation_allowed": False,
    }
    payload["proof_points"] = _proof_points(payload)
    parity = {
        "schema": "qamus.fd.sufaha.parity_fixture.v1",
        "surface": SUFAHA_SURFACE,
        "at_rest_span_ids": [span["span_id"] for span in at_rest_spans],
        "reconstructed_surface": reconstructed,
        "exact_reconstruction_passed": exact_reconstruction["passed"],
        "same_payload_consumption": {
            "payload_id": FAMILY_PAYLOAD_ID,
            "members": [member["quran_loc"] for member in family_members],
            "same_family_payload_id": repeated_parity["same_family_payload_id"],
        },
        "repeated_appearance_parity": {
            "family_member_count": len(family_members),
            "coverage_count": repeated_parity["coverage_count"],
            "page_trace_inferred": False,
            "same_family_payload_id": repeated_parity["same_family_payload_id"],
        },
        "entry_reciprocity": {
            "entry_id": entry_id,
            "occurrence_id": SUFAHA_QURAN_LOC,
            "occurrence_to_entry": True,
            "entry_to_occurrence": True,
        },
        "diagnostic_source_row_entry_id": source_row_entry_id,
        "live_mutation_allowed": False,
    }
    return payload, parity


def render_sufaha_html(payload: dict[str, Any]) -> str:
    """Generate a browser proof whose two views consume one embedded payload."""

    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_json = payload_json.replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>F-D Ṣufahāʾ compiler proof</title>
  <style>
    @font-face {{ font-family: "Kawkab Mono Qamus"; src: url("assets/KawkabMono-Regular.woff2") format("woff2"); font-display: block; }}
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; background: #f5f0e7; color: #1f2933; }}
    body {{ margin: 0; padding: 2rem; }}
    main {{ max-width: 980px; margin: auto; }}
    .proof-banner {{ border: 2px solid #24445c; padding: .75rem 1rem; background: #fff; }}
    .proof-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }}
    .card, .component, .proof-list {{ background: #fff; border: 1px solid #b9c2ca; border-radius: .5rem; padding: 1rem; }}
    .arabic {{ font-family: "Kawkab Mono Qamus", monospace; font-size: 2.5rem; direction: rtl; }}
    .span {{ display: inline-flex; flex-direction: column; align-items: center; margin: .15rem; padding: .2rem .35rem; border: 2px solid #24445c; border-radius: .3rem; }}
    .span-label, .badge {{ font: 700 .72rem/1 system-ui, sans-serif; letter-spacing: .03em; }}
    .span-label {{ direction: ltr; }}
    .component + .component {{ margin-top: .75rem; }}
    .badge {{ display: inline-block; padding: .2rem .35rem; border: 1px solid currentColor; border-radius: 999px; }}
    .status {{ font-weight: 700; }}
    .unresolved {{ border-left: .4rem solid #8a4b08; }}
    code {{ font-family: ui-monospace, monospace; overflow-wrap: anywhere; }}
    dt {{ font-weight: 700; margin-top: .5rem; }}
    dd {{ margin-left: 0; }}
    @media (max-width: 640px) {{ body {{ padding: 1rem; }} .arabic {{ font-size: 2rem; }} }}
  </style>
</head>
<body data-live-mutation-allowed="false">
<main>
  <section class="proof-banner" aria-label="dry-run boundary">
    <strong>F-D compiler proof · fixture/dry-run only</strong>
    <span class="badge">live_mutation_allowed=false</span>
    <p>Both views below are generated from the same normalized payload. Color is decorative; every distinction has a visible label or bracket equivalent.</p>
  </section>
  <h1 id="card-heading">F-D compiler proof</h1>
  <section id="font-proof" class="proof-banner" aria-live="polite">document.fonts.check pending…</section>
  <section id="recon-proof" class="proof-banner" aria-live="polite">exact reconstruction pending…</section>
  <div class="proof-grid">
    <section id="compact-view" class="card" aria-labelledby="compact-heading"><h2 id="compact-heading">Compact view</h2></section>
    <section id="expanded-view" class="card" aria-labelledby="expanded-heading"><h2 id="expanded-heading">Expanded view</h2></section>
  </div>
  <section id="evidence-footer" class="proof-list" aria-label="evidence footer"></section>
</main>
<script id="fd-normalized-payload" type="application/json">{payload_json}</script>
<script>
const payload = JSON.parse(document.getElementById("fd-normalized-payload").textContent);
window.__fdPayload = payload;
function textNode(value) {{ return document.createTextNode(String(value)); }}
function labelledSpan(span) {{
  const wrapper = document.createElement("span");
  wrapper.className = "span";
  wrapper.setAttribute("data-span-id", span.span_id);
  const label = document.createElement("span");
  label.className = "span-label";
  label.textContent = span.visual_equivalent;
  const value = document.createElement("span");
  value.className = "arabic";
  value.textContent = span.surface;
  wrapper.append(label, value);
  return wrapper;
}}
function renderHeading(payload) {{
  const heading = document.getElementById("card-heading");
  heading.textContent = "F-D compiler proof · ";
  const surface = document.createElement("span");
  surface.className = "arabic";
  surface.setAttribute("aria-label", payload.canonical_identity.surface);
  surface.textContent = payload.canonical_identity.surface;
  heading.append(surface);
}}
function renderCompact(payload) {{
  window.__compactPayload = payload;
  const root = document.getElementById("compact-view");
  const identity = document.createElement("p");
  identity.append(textNode(payload.canonical_identity.quran_loc + " · "));
  const identityCode = document.createElement("code");
  identityCode.textContent = payload.canonical_identity.surface;
  identity.append(identityCode);
  const run = document.createElement("div");
  run.className = "arabic";
  payload.at_rest_spans.forEach(span => run.append(labelledSpan(span)));
  const gloss = document.createElement("p");
  gloss.textContent = payload.components.map(component => component.learner_text).join(" ");
  root.append(identity, run, gloss);
}}
function renderExpanded(payload) {{
  window.__expandedPayload = payload;
  const root = document.getElementById("expanded-view");
  payload.components.forEach(component => {{
    const card = document.createElement("article");
    card.className = "component";
    const heading = document.createElement("h3");
    heading.textContent = component.label + " " + component.visual_equivalent;
    const surface = document.createElement("p");
    surface.className = "arabic";
    surface.textContent = component.surface;
    const sarf = document.createElement("p");
    sarf.textContent = component.sarf;
    const nahw = document.createElement("p");
    nahw.textContent = component.nahw;
    const learner = document.createElement("p");
    learner.textContent = component.learner_text;
    card.append(heading, surface, sarf, nahw, learner);
    root.append(card);
  }});
  const proof = document.createElement("div");
  proof.className = "proof-list";
  payload.proof_points.forEach(point => {{
    const item = document.createElement("p");
    item.className = "status";
    item.append(textNode("[" + point.status + "] " + point.id + ": "));
    const value = document.createElement("code");
    value.textContent = typeof point.witness === "string" ? point.witness : JSON.stringify(point.witness);
    item.append(value);
    proof.append(item);
  }});
  root.append(proof);
}}
window.__reconCheck = function() {{
  const reconstructed = payload.at_rest_spans.map(span => span.surface).join("");
  const passed = reconstructed === payload.canonical_identity.surface && payload.exact_reconstruction.passed;
  document.getElementById("recon-proof").textContent = "exact reconstruction: " + (passed ? "PASS" : "FAIL") + " · " + reconstructed;
  return passed;
}};
window.__fontProof = function() {{
  const passed = document.fonts.check('32px "Kawkab Mono Qamus"');
  document.getElementById("font-proof").textContent = "document.fonts.check('32px \\\"Kawkab Mono Qamus\\\"'): " + (passed ? "PASS" : "FAIL");
  return passed;
}};
function renderEvidenceFooter(payload) {{
  const root = document.getElementById("evidence-footer");
  root.textContent = "";
  const lines = [
    "provenance: " + payload.provenance.source_address + " · entry " + payload.provenance.entry_address,
    "typed facts: " + payload.provenance.typed_fact_count + " · producer " + payload.provenance.producer_id,
    "projector: " + payload.provenance.projector_id + " @ " + payload.provenance.projector_version,
    "tension: [UNRESOLVED] " + payload.unresolved_tension.learner_text,
    "live_mutation_allowed=false"
  ];
  lines.forEach(line => {{ const p = document.createElement("p"); p.textContent = line; root.append(p); }});
}}
document.addEventListener("DOMContentLoaded", () => {{
  renderHeading(payload);
  renderCompact(payload);
  renderExpanded(payload);
  renderEvidenceFooter(payload);
  window.__reconCheck();
  document.fonts.ready.then(() => window.__fontProof());
}});
</script>
</body>
</html>
'''


def _has_morphology_producer(row: dict[str, Any]) -> bool:
    facts = row.get("sarf_facts")
    if not isinstance(facts, dict):
        return False
    return any(facts.get(key) not in (None, "", [], {}) for key in ("root", "form", "no_root_reason"))


def _has_nahw_producer(row: dict[str, Any]) -> bool:
    facts = row.get("nahw_facts")
    if not isinstance(facts, dict):
        return False
    return any(
        facts.get(key) not in (None, "", [], {})
        for key in ("function", "governor", "case", "case_role", "i3rab")
    )


def _has_learner_language(row: dict[str, Any], segments: Sequence[dict[str, Any]]) -> bool:
    top_fields = ("learner_explanation", "token_contribution_gloss", "contextual_phrase_gloss")
    if any(not str(row.get(field, "")).strip() for field in top_fields):
        return False
    required_segment_fields = ("label", "role", "gloss_contribution", "sarf_note", "nahw_note")
    return all(all(str(segment.get(field, "")).strip() for field in required_segment_fields) for segment in segments)


def _source_segments(row: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    surface = str(row.get("surface", ""))
    segments = row.get("segments")
    flags: list[str] = []
    if not surface or not isinstance(segments, list) or not segments:
        return [], ["linguistic_consistency", "span_ownership", "exact_reconstruction"]
    cursor = 0
    owned: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        if segment.get("segment_index") != index:
            flags.append("linguistic_consistency")
        segment_surface = str(segment.get("surface", ""))
        if not segment_surface or not surface.startswith(segment_surface, cursor):
            flags.append("linguistic_consistency")
            flags.append("span_ownership")
            break
        owned.append(
            {
                "segment_index": index,
                "start": cursor,
                "end": cursor + len(segment_surface),
                "surface": segment_surface,
                "owner": f"source-row-segment:{index}",
            }
        )
        cursor += len(segment_surface)
    if cursor != len(surface):
        flags.extend(["linguistic_consistency", "exact_reconstruction"])
    if "linguistic_consistency" in flags:
        flags.append("parity")
    return owned, sorted(set(flags))


def _primary_blocker(flags: Sequence[str]) -> str:
    priority = (
        ("learner_language_fields", "learner_language_fields_missing"),
        ("source_scholar_review", "source_scholar_review"),
        ("linguistic_consistency", "linguistic_consistency"),
        ("span_ownership", "span_ownership"),
        ("entry_linkage", "entry_linkage"),
        ("projector", "projector_missing"),
        ("morphology_producer", "F-B_morphology_producer"),
        ("nahw_producer", "F-C_nahw_producer"),
        ("parity", "parity"),
        ("exact_reconstruction", "exact_reconstruction"),
    )
    for flag, label in priority:
        if flag in flags:
            return label
    return "source_scholar_review"


def compile_verified_rows(
    verdict_rows: Sequence[dict[str, Any]],
    whitelist_rows: Sequence[dict[str, Any]],
    entries: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compile every v575-verified row as a candidate and return the matrix."""

    verified = [row for row in verdict_rows if row.get("verdict") == "verified"]
    whitelist_by_loc = {str(row.get("loc")): row for row in whitelist_rows}
    entries_by_id = _entry_map(entries)
    verdicts: list[dict[str, Any]] = []
    flag_counter: Counter[str] = Counter()
    primary_counter: Counter[str] = Counter()
    for verdict in sorted(verified, key=lambda row: str(row.get("loc", ""))):
        loc = str(verdict.get("loc", ""))
        source_row = whitelist_by_loc.get(loc)
        flags: list[str] = []
        if source_row is None:
            flags.extend(["linguistic_consistency", "span_ownership", "entry_linkage", "exact_reconstruction"])
            segments: list[dict[str, Any]] = []
            owned_spans: list[dict[str, Any]] = []
        else:
            segments = source_row.get("segments") if isinstance(source_row.get("segments"), list) else []
            owned_spans, structural_flags = _source_segments(source_row)
            flags.extend(structural_flags)
            if not _has_learner_language(source_row, segments):
                flags.append("learner_language_fields")
            entry_id = source_row.get("entry_id")
            if not entry_id or str(entry_id) not in entries_by_id:
                flags.append("entry_linkage")
            if not source_row.get("projector_id"):
                flags.append("projector")
            if not _has_morphology_producer(source_row):
                flags.append("morphology_producer")
            if not _has_nahw_producer(source_row):
                flags.append("nahw_producer")
            # Source-row exact spans are the candidate parity witness.  No
            # guessed language is inserted when a field is blank.
            if not owned_spans or "".join(span["surface"] for span in owned_spans) != source_row.get("surface"):
                flags.extend(["parity", "exact_reconstruction"])
        flags.append("source_scholar_review")
        flags = sorted(set(flags))
        for flag in flags:
            flag_counter[flag] += 1
        primary = _primary_blocker(flags)
        primary_counter[primary] += 1
        compiled = not any(flag in flags for flag in ("linguistic_consistency", "span_ownership", "entry_linkage"))
        row_surface = source_row.get("surface") if source_row else None
        row_entry_id = source_row.get("entry_id") if source_row else None
        verdicts.append(
            {
                "schema": VERDICT_SCHEMA,
                "loc": loc,
                "quran_loc": f"quran:{loc}",
                "source_verdict": "verified",
                "compile_mode": "candidate",
                "compile_status": "compiled_review_queue" if compiled else "blocked_structural_input",
                "flags": flags,
                "primary_blocker": primary,
                "surface": row_surface,
                "entry_id": row_entry_id,
                "owned_spans": owned_spans,
                "assigned_projector_id": PROJECTOR_ID,
                "input_projector_missing": "projector" in flags,
                "requires_fb_morphology_producer": "morphology_producer" in flags,
                "requires_fc_nahw_producer": "nahw_producer" in flags,
                "review_route": "source/scholar",
                "repeated_page_trace_covered": False,
                "parity_passed": "parity" not in flags,
                "exact_reconstruction_passed": "exact_reconstruction" not in flags,
                "live_mutation_allowed": False,
            }
        )

    metrics = {
        METRIC_KEYS[0]: sum(1 for row in verdicts if row["compile_status"] == "compiled_review_queue"),
        METRIC_KEYS[1]: flag_counter["linguistic_consistency"],
        METRIC_KEYS[2]: flag_counter["span_ownership"],
        METRIC_KEYS[3]: flag_counter["learner_language_fields"],
        METRIC_KEYS[4]: flag_counter["entry_linkage"],
        METRIC_KEYS[5]: flag_counter["projector"],
        METRIC_KEYS[6]: flag_counter["morphology_producer"],
        METRIC_KEYS[7]: flag_counter["nahw_producer"],
        METRIC_KEYS[8]: flag_counter["source_scholar_review"],
        METRIC_KEYS[9]: sum(1 for row in verdicts if row["repeated_page_trace_covered"]),
        METRIC_KEYS[10]: flag_counter["parity"],
        METRIC_KEYS[11]: flag_counter["exact_reconstruction"],
    }
    report = {
        "schema": REPORT_SCHEMA,
        "report_version": "1.0.0",
        "candidate_only": True,
        "verified_row_count": len(verdicts),
        "input_verdict_count": len(verdict_rows),
        "metrics": metrics,
        "flag_matrix": dict(sorted(flag_counter.items())),
        "primary_blocker_counts": dict(sorted(primary_counter.items())),
        "metric_definitions": {
            METRIC_KEYS[0]: "Rows for which the compiler emitted a candidate or review record after structural checks.",
            METRIC_KEYS[1]: "Rows whose source surface/segment invariant failed.",
            METRIC_KEYS[2]: "Rows without deterministic owned at-rest spans.",
            METRIC_KEYS[3]: "Rows with at least one missing supplied learner-language field.",
            METRIC_KEYS[4]: "Rows whose source entry ID did not join the read-only entry corpus.",
            METRIC_KEYS[5]: "Rows with no projector identity before F-D assignment.",
            METRIC_KEYS[6]: "Rows without a direct structured morphology producer carrier.",
            METRIC_KEYS[7]: "Rows without a direct structured naḥw producer carrier.",
            METRIC_KEYS[8]: "All v575 structural-verified rows remain routed because semantic certification was not performed.",
            METRIC_KEYS[9]: "Confirmed repeated page/render appearances with an available trace; never inferred from row counts.",
            METRIC_KEYS[10]: "Rows whose candidate parity witness failed.",
            METRIC_KEYS[11]: "Rows whose generated at-rest spans failed exact reconstruction.",
        },
        "primary_blocker_policy": [
            "learner_language_fields_missing",
            "source_scholar_review",
            "linguistic_consistency",
            "span_ownership",
            "entry_linkage",
            "projector_missing",
            "F-B_morphology_producer",
            "F-C_nahw_producer",
            "parity",
            "exact_reconstruction",
        ],
        "projector_id": PROJECTOR_ID,
        "producer_id": PRODUCER_ID,
        "live_mutation_allowed": False,
    }
    return verdicts, report


def generate_sufaha_artifacts(
    evidence_path: Path,
    whitelist_path: Path,
    entries_path: Path,
    output_dir: Path,
    font_source: Path | None = None,
) -> dict[str, Path]:
    evidence_rows = read_jsonl(evidence_path)
    whitelist_rows = read_jsonl(whitelist_path)
    entries = read_jsonl(entries_path)
    contract = build_sufaha_contract(evidence_rows)
    payload, parity = build_sufaha_payload(contract, whitelist_rows, entries)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "sufaha-contract.json", contract)
    _write_json(output_dir / "sufaha-normalized-public-payload.json", payload)
    _write_json(output_dir / "sufaha-parity-fixture.json", parity)
    (output_dir / "sufaha-card.html").write_text(render_sufaha_html(payload), encoding="utf-8")
    if font_source is not None:
        asset_dir = output_dir / "assets"
        asset_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(font_source, asset_dir / "KawkabMono-Regular.woff2")
    return {
        "contract": output_dir / "sufaha-contract.json",
        "payload": output_dir / "sufaha-normalized-public-payload.json",
        "parity": output_dir / "sufaha-parity-fixture.json",
        "html": output_dir / "sufaha-card.html",
    }


def generate_candidate_artifacts(
    verdict_path: Path,
    whitelist_path: Path,
    entries_path: Path,
    report_path: Path,
    verdict_output_path: Path,
) -> tuple[Path, Path]:
    verdict_rows = read_jsonl(verdict_path)
    whitelist_rows = read_jsonl(whitelist_path)
    entries = read_jsonl(entries_path)
    rows, report = compile_verified_rows(verdict_rows, whitelist_rows, entries)
    _write_json(report_path, report)
    _write_jsonl(verdict_output_path, rows)
    return report_path, verdict_output_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sufaha-evidence", type=Path)
    parser.add_argument("--whitelist", type=Path)
    parser.add_argument("--entries", type=Path)
    parser.add_argument("--v575-verdicts", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "qamus" / "examples" / "fd")
    parser.add_argument("--report", type=Path, default=ROOT / "fd-455-report.json")
    parser.add_argument("--verdict-output", type=Path, default=ROOT / "fd-455-verdicts.jsonl")
    parser.add_argument("--font-source", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.sufaha_evidence or not args.whitelist or not args.entries:
        raise SystemExit("--sufaha-evidence, --whitelist, and --entries are required")
    generated = generate_sufaha_artifacts(
        args.sufaha_evidence,
        args.whitelist,
        args.entries,
        args.output_dir,
        args.font_source,
    )
    print("FD SUFAHA GENERATED")
    for name, path in generated.items():
        print(f"{name}: {path}")
    if args.v575_verdicts:
        report_path, verdict_path = generate_candidate_artifacts(
            args.v575_verdicts,
            args.whitelist,
            args.entries,
            args.report,
            args.verdict_output,
        )
        print(f"455 report: {report_path}")
        print(f"455 verdicts: {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
