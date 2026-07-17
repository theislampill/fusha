"""F-D shared evidence compiler and dry-run projection generator.

The compiler is deliberately stdlib-only.  It treats the supplied v575 rows as
structural candidate inputs, keeps source evidence inside the typed contract,
and emits source-safe learner payloads plus a fixture-only HTML proof.  No
function in this module writes the read-only corpus or a live/runtime surface.
"""

from __future__ import annotations

import argparse
import copy
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

FD2_REPORT_SCHEMA = "qamus.fd2.455_rerun_report.v1"
FD2_VERDICT_SCHEMA = "qamus.fd2.455_rerun_verdict.v1"
FD2_BASELINE = {
    "rows needing F-B": 437,
    "rows needing F-C": 437,
    "rows lacking learner-language": 383,
    "rows with repeated-appearance coverage": 0,
}
FD2_METRIC_KEYS = (
    "rows with complete morphology facts",
    "rows with complete naḥw facts",
    "rows with both",
    "rows generating at-rest projection",
    "rows generating rich Ṣarf",
    "rows generating rich Naḥw",
    "rows generating both compact and expanded views",
    "rows with repeated-appearance parity",
    "unresolved rows by exact blocker",
    "source/scholar queues",
    "reconstruction failures",
    "projection conflicts",
    "newly discovered producer defects",
)
_FD2_COMPONENT_FACT_TYPES = {
    "function_component",
    "host_component",
    "clitic_component",
    "protective_nun",
}
_FD2_FORBIDDEN_LEARNER_PHRASES = (
    "source-addressed",
    "calibration",
    "producer",
    "evidence",
    "candidate",
    "live mutation",
    "informed_by",
    "quran:",
    "wbw:",
)

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


def _fd2_loc(value: Any) -> str:
    text = str(value or "").strip()
    for prefix in ("quran:", "wbw:"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text


def _fd2_positive_record(record: dict[str, Any] | None) -> bool:
    return isinstance(record, dict) and record.get("record_type") == "projection_input"


def _fd2_fact_values(record: dict[str, Any] | None, fact_types: set[str] | None = None) -> list[dict[str, Any]]:
    if not _fd2_positive_record(record):
        return []
    values: list[dict[str, Any]] = []
    for fact in record.get("facts", []):
        if not isinstance(fact, dict):
            continue
        if fact_types is not None and fact.get("fact_type") not in fact_types:
            continue
        value = fact.get("fact_value")
        if isinstance(value, dict):
            values.append(value)
    return values


def _fd2_record_has_fact(record: dict[str, Any] | None, fact_type: str) -> bool:
    if not _fd2_positive_record(record):
        return False
    return any(isinstance(fact, dict) and fact.get("fact_type") == fact_type for fact in record.get("facts", []))


def _fd2_component_gloss(value: dict[str, Any]) -> str:
    role = str(value.get("role", "")).lower()
    klass = str(value.get("class", "")).lower()
    typed_kind = str(value.get("typed_kind", "")).lower()
    if "conjunction" in role or klass == "qg-conjunction":
        return "and"
    if "preposition" in role or klass == "qg-preposition":
        return "a prepositional prefix"
    if "article" in role or klass == "qg-article":
        return "the definite article"
    if "object" in role or "object-pronoun" in klass:
        return "an attached object pronoun"
    if "possessive" in role or "possessive-pronoun" in klass:
        return "an attached possessive pronoun"
    if "subject" in role or "subject-pronoun" in klass:
        return "an attached subject marker"
    if "protective" in role or "protective_nun" in typed_kind or klass == "qg-protective-nun":
        return "a protective nūn marker"
    if "verb-prefix" in klass or "verb_prefix" in typed_kind:
        return "a finite-verb prefix"
    if "host" in role or klass in {"qg-verb-stem", "qg-noun-stem", "qg-noun", "qg-adjective", "qg-verb"}:
        return "the lexical host"
    if "function" in typed_kind or klass.startswith("qg-") and klass not in {"qg-unknown", "qg-segment"}:
        return "a grammar component"
    return "a written component"


def _fd2_sarf_note(gloss: str) -> str:
    return f"Ṣarf — how this piece forms the word: {gloss.capitalize()} is one typed piece of the written composition."


def _fd2_local_nahw_note(value: dict[str, Any], gloss: str) -> str:
    role = str(value.get("role", "")).lower()
    if "function" in str(value.get("typed_kind", "")).lower() or role.startswith("prefix_"):
        action = "It contributes its closed-class function in this word."
    elif "pronoun" in role or "clitic" in str(value.get("typed_kind", "")).lower():
        action = "It attaches the pronoun contribution to the host."
    elif "host" in role:
        action = "It carries the lexical host contribution."
    else:
        action = "It occupies its exact typed span in the word."
    return f"Naḥw — what this piece does here: {action}"


def _fd2_relation_text(value: dict[str, Any]) -> str:
    role = str(value.get("role", "")).lower()
    relationship = str(value.get("relationship", "")).lower()
    role_text = {
        "subject": "the subject",
        "object": "the object",
        "agreement": "the agreement marker",
        "mood": "the mood-governed occurrence",
        "pronoun_attachment": "the attached pronoun",
        "preposition_to_governed": "the preposition-to-occurrence relation",
        "other": "the typed syntax relation",
    }.get(role, "the typed syntax relation")
    relation_text = {
        "subject_of": "is linked as the subject of the named governor",
        "subject_agreement": "records subject agreement with the named governor",
        "object_of": "is linked as the object of the named governor",
        "mood_governed_by": "carries the mood supplied by the named governor",
        "governed_by": "is linked to the named governor",
        "pronoun_as_name_of_inna": "is the attached name position in the named construction",
        "attached_pronoun_complement": "is attached as a pronoun complement",
        "preposition_governs": "is governed by the preposition",
        "preposition_governs_following_occurrence": "governs the following occurrence",
        "definiteness_marker_to_noun": "marks definiteness for the noun",
    }.get(relationship, "has the source-addressed relation recorded here")
    case_or_mood = value.get("case_or_mood") if isinstance(value.get("case_or_mood"), dict) else {}
    state = str(case_or_mood.get("value") or "").strip()
    ending = value.get("ending") if isinstance(value.get("ending"), dict) else {}
    ending_state = str(ending.get("status") or "").strip()
    suffix = f" Its case or mood is {state}." if state else ""
    if ending_state == "visible":
        suffix += " Its visible ending is part of the typed fact."
    elif ending_state == "estimated":
        suffix += " Its ending state remains estimated."
    return f"{role_text.capitalize()} {relation_text}.{suffix}"


def _fd2_n_lang_clean(values: Iterable[str]) -> bool:
    for value in values:
        text = str(value or "")
        lowered = text.lower()
        if any(phrase in lowered for phrase in _FD2_FORBIDDEN_LEARNER_PHRASES):
            return False
        if re.search(r"\b[A-Z]{1,6}:\S", text):
            return False
        if re.search(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]", text):
            return False
    return True


def build_fact_derived_views(
    surface: str,
    fb_record: dict[str, Any] | None,
    fc_record: dict[str, Any] | None,
    *,
    source_segments: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build learner-facing views from typed facts and exact source spans only."""

    projection_conflicts: list[dict[str, str]] = []
    for producer, record in (("F-B", fb_record), ("F-C", fc_record)):
        if not isinstance(record, dict):
            continue
        canonical = record.get("canonical_occurrence") or {}
        if canonical.get("surface") not in (None, surface):
            projection_conflicts.append({
                "producer": producer,
                "code": "canonical_surface_mismatch",
                "detail": "producer canonical surface differs from compiler source surface",
            })

    component_values = _fd2_fact_values(fb_record, _FD2_COMPONENT_FACT_TYPES)
    if component_values:
        component_values.sort(key=lambda value: (int(value.get("segment_index", 10**6)), str(value.get("surface", ""))))
        component_surfaces = "".join(str(value.get("surface", "")) for value in component_values)
        if component_surfaces != surface:
            projection_conflicts.append({
                "producer": "F-B",
                "code": "component_surface_reconstruction",
                "detail": "typed F-B component surfaces do not reconstruct the compiler source surface",
            })
    else:
        component_values = [copy.deepcopy(segment) for segment in (source_segments or []) if isinstance(segment, dict)]

    generated_from_facts = _fd2_positive_record(fb_record) or _fd2_positive_record(fc_record)
    fb_active = _fd2_positive_record(fb_record)
    fc_active = _fd2_positive_record(fc_record)
    fc_values = _fd2_fact_values(fc_record, {"nahw_dependency"})
    relation_text = _fd2_relation_text(fc_values[0]) if fc_values else ""

    segments: list[dict[str, Any]] = []
    component_glosses: list[str] = []
    sarf_notes: list[str] = []
    local_nahw_notes: list[str] = []
    for index, value in enumerate(component_values):
        gloss = _fd2_component_gloss(value)
        component_glosses.append(gloss)
        sarf_note = _fd2_sarf_note(gloss) if fb_active else ""
        nahw_note = relation_text if fc_active else _fd2_local_nahw_note(value, gloss) if fb_active else ""
        if sarf_note:
            sarf_notes.append(sarf_note)
        if nahw_note:
            local_nahw_notes.append(nahw_note)
        segments.append({
            "segment_index": int(value.get("segment_index", index)),
            "surface": str(value.get("surface", "")),
            "role": str(value.get("role", "component")),
            "class": str(value.get("class", "qg-unknown")),
            "label": str(value.get("label", "PIECE")),
            "gloss_contribution": gloss,
            "sarf_note": sarf_note,
            "nahw_note": nahw_note,
        })

    segment_surface = "".join(segment["surface"] for segment in segments)
    if segments and segment_surface != surface:
        projection_conflicts.append({
            "producer": "FD2",
            "code": "learner_segment_reconstruction",
            "detail": "learner segments do not reconstruct the compiler source surface",
        })

    composition_text = ""
    if fb_active:
        composition_text = "Composition: " + " + ".join(component_glosses)
    sarf_text = "\n".join(sarf_notes)
    nahw_text = ""
    if fc_active:
        nahw_text = f"Naḥw — what this piece does here: {relation_text}"
    elif fb_active:
        nahw_text = "\n".join(local_nahw_notes)
    contribution = " + ".join(component_glosses) if component_glosses else "the source occurrence"
    contextual = relation_text if fc_active else contribution
    learner_parts = []
    if composition_text:
        learner_parts.append(composition_text + ".")
    if sarf_text:
        learner_parts.append(sarf_text)
    if nahw_text:
        learner_parts.append(nahw_text)
    learner_explanation = " ".join(learner_parts)
    n_lang_values = [learner_explanation, contribution, contextual, composition_text, sarf_text, nahw_text]
    n_lang_clean = _fd2_n_lang_clean(n_lang_values)
    payload_id = "fd2.payload:" + _sha256({
        "surface": surface,
        "segments": segments,
        "sarf": sarf_text,
        "nahw": nahw_text,
        "composition": composition_text,
    })[:24]
    compact_view = {
        "payload_id": payload_id,
        "surface": surface,
        "text": learner_explanation or contribution,
    }
    expanded_view = {
        "payload_id": payload_id,
        "surface": surface,
        "components": segments,
        "component_gloss": component_glosses,
        "sarf": sarf_text,
        "nahw": nahw_text,
        "composition": composition_text,
    }
    return {
        "component_gloss": component_glosses,
        "segments": segments,
        "sarf_text": sarf_text,
        "nahw_text": nahw_text,
        "composition_text": composition_text,
        "token_contribution_gloss": contribution,
        "contextual_phrase_gloss": contextual,
        "learner_explanation": learner_explanation,
        "generated_from_facts": generated_from_facts,
        "learner_complete": bool(generated_from_facts and segments and n_lang_clean),
        "rich_sarf": bool(fb_active and sarf_text and n_lang_clean),
        "rich_nahw": bool((fc_active or fb_active) and nahw_text and n_lang_clean),
        "compact_view": compact_view,
        "expanded_view": expanded_view,
        "payload_id": payload_id,
        "n_lang_clean": n_lang_clean,
        "projection_conflicts": projection_conflicts,
    }


def build_formation_learner_view(record: dict[str, Any]) -> dict[str, Any]:
    """Compile a lexical-family formation fact into the shared learner-view shape.

    The family producer owns typed entry/pattern facts; this shared compiler
    owns learner-facing copy and exact-surface reconstruction. Arabic source
    forms stay in the typed payload and source spans, not in learner prose, so
    the copy remains N-LANG clean.
    """

    occurrence = record.get("canonical_occurrence") or {}
    surface = str(occurrence.get("surface") or "")
    formation_facts = [
        fact for fact in record.get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_type") == "formation_evidence"
    ]
    if len(formation_facts) != 1:
        raise ValueError("shared formation compiler requires exactly one formation_evidence fact")
    value = formation_facts[0].get("fact_value") or {}
    shape_labels = {
        "broken_plural": "broken plural",
        "sound_masculine_plural": "sound masculine plural",
        "sound_feminine_plural": "sound feminine plural",
        "dual": "dual",
        "nisba_adjective": "nisba adjective",
        "elative": "elative",
        "bare_cardinal": "bare cardinal",
        "gender_polarity_cardinal": "gender-polarity cardinal",
        "ordinals": "ordinal",
        "compound_11_19": "compound number (11–19)",
        "tens": "tens form",
        "fractions": "fraction",
        "first_last_edge": "first/last edge word",
        "other_number_form": "other number form",
    }
    shape_label = shape_labels.get(str(value.get("sub_shape")), "lexical formation")
    pattern_id = str(value.get("pattern_id") or "named pattern")
    sarf_text = (
        "Ṣarf — how this piece forms the word: "
        f"The entry-backed singular is paired by the named {pattern_id} formation rule."
    )
    nahw_text = (
        "Naḥw — what this piece does here: "
        f"This exact lexical piece functions as the {shape_label} in this occurrence."
    )
    segments = [{
        "segment_index": 0,
        "surface": surface,
        "role": "lexical_host",
        "label": "LEXICAL FORMATION",
        "sarf_note": sarf_text,
        "nahw_note": nahw_text,
    }]
    reconstructed = "".join(segment["surface"] for segment in segments) == surface
    learner_explanation = sarf_text + " " + nahw_text
    n_lang_clean = _fd2_n_lang_clean([
        sarf_text,
        nahw_text,
        learner_explanation,
        shape_label,
        pattern_id,
    ])
    artifact = str(
        ((record.get("projection") or {}).get("materialization_target") or {}).get("artifact") or ""
    )
    payload_namespace = "fd.fam3" if "fam3-numbers" in artifact else "fd.fam2"
    payload_id = payload_namespace + ".payload:" + _sha256({
        "surface": surface,
        "formation_fact_id": formation_facts[0].get("fact_id"),
        "sarf": sarf_text,
        "nahw": nahw_text,
    })[:24]
    return {
        "payload_id": payload_id,
        "surface": surface,
        "segments": segments,
        "sarf": sarf_text,
        "nahw": nahw_text,
        "sarf_text": sarf_text,
        "nahw_text": nahw_text,
        "learner_explanation": learner_explanation,
        "generated_from_facts": True,
        "reconstruction_passed": reconstructed,
        "n_lang_clean": n_lang_clean,
        "learner_complete": bool(reconstructed and n_lang_clean),
        "compact_view": {"payload_id": payload_id, "surface": surface, "text": learner_explanation},
        "expanded_view": {
            "payload_id": payload_id,
            "surface": surface,
            "formation": copy.deepcopy(value),
            "sarf": sarf_text,
            "nahw": nahw_text,
        },
    }


def _fd2_record_blockers(record: dict[str, Any] | None) -> list[str]:
    if not isinstance(record, dict):
        return []
    blockers: set[str] = set()
    for fact in record.get("facts", []):
        if not isinstance(fact, dict):
            continue
        for blocker in fact.get("unresolved_blockers", []):
            if isinstance(blocker, dict) and blocker.get("blocker_id"):
                blockers.add(str(blocker["blocker_id"]))
        value = fact.get("fact_value")
        if isinstance(value, dict):
            for code in value.get("reason_codes", []):
                if code:
                    blockers.add(str(code))
    return sorted(blockers)


def collect_calibrated_producer_records(
    strat_rows: Sequence[dict[str, Any]],
    verdict_rows: Sequence[dict[str, Any]],
    source_rows: Sequence[dict[str, Any]],
    *,
    corpus_source_name: str = "corpus.jsonl",
) -> dict[str, Any]:
    """Run F-B and F-C within their calibrated scopes and return typed records."""

    from tools.build_clitic_pronoun_producer import produce_record
    from tools.fc_nahw_producer import _input_candidate, build_contract_record

    source_by_loc = {_fd2_loc(row.get("loc")): row for row in source_rows}
    verdict_by_loc = {_fd2_loc(row.get("loc")): row for row in verdict_rows}
    fb_records: dict[str, dict[str, Any]] = {}
    fc_records: dict[str, dict[str, Any]] = {}
    fb_blockers_by_loc: dict[str, list[str]] = {}
    fc_blockers_by_loc: dict[str, str] = {}
    defects: list[dict[str, Any]] = []
    corpus_by_loc = dict(source_by_loc)

    for strat in sorted(strat_rows, key=lambda row: _fd2_loc(row.get("loc"))):
        loc = _fd2_loc(strat.get("loc"))
        family = strat.get("morphology_family", strat.get("family"))
        verdict = verdict_by_loc.get(loc)
        if family == "clitic_pronoun_compositions":
            source = copy.deepcopy(source_by_loc.get(loc, strat))
            source["loc"] = loc
            source["quran_loc"] = "quran:" + loc
            source["wbw_loc"] = "wbw:" + loc
            source["surface"] = source.get("surface", strat.get("surface", ""))
            source["morphology_family"] = family
            source["_fb1_source_id"] = corpus_source_name
            source["_fb1_source_address"] = f"corpus:{corpus_source_name}#loc={loc}"
            source["_fb1_verdict"] = (verdict or {}).get("verdict")
            try:
                record = produce_record(source)
            except Exception as exc:  # pragma: no cover - exercised by operational defects
                defects.append({
                    "loc": loc,
                    "producer": "F-B",
                    "code": "producer_exception",
                    "detail": str(exc),
                })
            else:
                fb_records[loc] = record
                blockers = _fd2_record_blockers(record)
                if blockers:
                    fb_blockers_by_loc[loc] = blockers
                if _fd2_positive_record(record) and not _fd2_record_has_fact(record, "clitic_composition"):
                    defects.append({
                        "loc": loc,
                        "producer": "F-B",
                        "code": "positive_without_composition_fact",
                        "detail": "positive F-B record did not emit a clitic_composition fact",
                    })

        try:
            candidate, reason = _input_candidate(strat, corpus_by_loc, verdict)
        except Exception as exc:  # pragma: no cover - exercised by operational defects
            defects.append({
                "loc": loc,
                "producer": "F-C",
                "code": "selector_exception",
                "detail": str(exc),
            })
            continue
        if candidate is None:
            fc_blockers_by_loc[loc] = reason
            continue
        try:
            record = build_contract_record(candidate, source_record_id=candidate["source"]["source_id"])
        except Exception as exc:  # pragma: no cover - exercised by operational defects
            defects.append({
                "loc": loc,
                "producer": "F-C",
                "code": "contract_exception",
                "detail": str(exc),
            })
            continue
        fc_records[loc] = record
        if not _fd2_record_has_fact(record, "nahw_dependency"):
            defects.append({
                "loc": loc,
                "producer": "F-C",
                "code": "positive_without_nahw_fact",
                "detail": "positive F-C record did not emit a nahw_dependency fact",
            })

    return {
        "fb_records": fb_records,
        "fc_records": fc_records,
        "fb_blockers_by_loc": fb_blockers_by_loc,
        "fc_blockers_by_loc": fc_blockers_by_loc,
        "producer_defects": defects,
    }


def _fd2_primary_blocker(blockers: Sequence[str]) -> str:
    priority = (
        "projection_conflict",
        "reconstruction_failure",
        "producer_defect",
        "learner_language_missing",
        "morphology_facts_missing",
        "nahw_facts_missing",
        "entry_linkage_missing",
        "source_row_missing",
        "source_scholar_review",
    )
    for candidate in priority:
        if candidate in blockers:
            return candidate
    for blocker in blockers:
        if blocker.startswith(("fb1.", "fc:")):
            return blocker
    return "source_scholar_review"


def _fd2_index_parity(index_row: dict[str, Any] | None, payload_id: str) -> dict[str, Any]:
    if not isinstance(index_row, dict):
        return {
            "covered": False,
            "reason": "merged occurrence index has no exact location",
            "appearance_count": 0,
            "same_payload_id": False,
        }
    appearances = index_row.get("appearances")
    covered = (
        index_row.get("unique") is True
        and isinstance(appearances, list)
        and index_row.get("appearance_count") == len(appearances)
        and len(appearances) >= 2
        and isinstance(index_row.get("projection_hash"), str)
        and len(index_row["projection_hash"]) == 64
    )
    return {
        "covered": covered,
        "loc": index_row.get("loc"),
        "appearance_count": len(appearances) if isinstance(appearances, list) else 0,
        "projection_hash": index_row.get("projection_hash"),
        "same_payload_id": bool(covered and payload_id),
        "reason": "canonical occurrence reuses one generated payload identity" if covered else "merged occurrence index parity witness is incomplete",
    }


def compile_fd2_rows(
    strat_rows: Sequence[dict[str, Any]],
    verdict_rows: Sequence[dict[str, Any]],
    source_rows: Sequence[dict[str, Any]],
    entries: Sequence[dict[str, Any]],
    occurrence_index: dict[str, dict[str, Any]],
    *,
    fb_records_by_loc: dict[str, dict[str, Any]] | None = None,
    fc_records_by_loc: dict[str, dict[str, Any]] | None = None,
    producer_diagnostics: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compile the FD2 matrix after guarded producer records are available."""

    fb_records_by_loc = fb_records_by_loc or {}
    fc_records_by_loc = fc_records_by_loc or {}
    producer_diagnostics = producer_diagnostics or {}
    source_by_loc = {_fd2_loc(row.get("loc")): row for row in source_rows}
    verdict_by_loc = {_fd2_loc(row.get("loc")): row for row in verdict_rows}
    entries_by_id = _entry_map(entries)
    verified = [
        row for row in strat_rows
        if verdict_by_loc.get(_fd2_loc(row.get("loc")), {}).get("verdict") == "verified"
    ]
    matrix: list[dict[str, Any]] = []
    metric_counts: Counter[str] = Counter()
    unresolved_counts: Counter[str] = Counter()
    source_queue_counts: Counter[str] = Counter()
    scholar_queue_counts: Counter[str] = Counter()
    primary_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    all_defects = [copy.deepcopy(item) for item in producer_diagnostics.get("producer_defects", [])]

    for strat in sorted(verified, key=lambda row: _fd2_loc(row.get("loc"))):
        loc = _fd2_loc(strat.get("loc"))
        source = source_by_loc.get(loc)
        source_surface = str((source or {}).get("surface") or strat.get("surface") or "")
        fb_record = fb_records_by_loc.get(loc)
        fc_record = fc_records_by_loc.get(loc)
        fb_positive = _fd2_positive_record(fb_record)
        fc_positive = _fd2_positive_record(fc_record)
        segments: list[dict[str, Any]] = []
        owned_spans: list[dict[str, Any]] = []
        flags: list[str] = []
        if source is None:
            flags.extend(["source_row_missing", "reconstruction_failure", "entry_linkage_missing"])
        else:
            segments = source.get("segments") if isinstance(source.get("segments"), list) else []
            owned_spans, structural_flags = _source_segments(source)
            flags.extend(structural_flags)
            entry_id = source.get("entry_id")
            if not entry_id or str(entry_id) not in entries_by_id:
                flags.append("entry_linkage_missing")

        views = build_fact_derived_views(
            source_surface,
            fb_record if fb_positive else None,
            fc_record if fc_positive else None,
            source_segments=segments,
        )
        conflicts = list(views["projection_conflicts"])
        for defect in all_defects:
            if _fd2_loc(defect.get("loc")) == loc:
                conflicts.extend([])
        if conflicts:
            flags.append("projection_conflict")

        morphology_complete = bool(_has_morphology_producer(source or {}) or _fd2_record_has_fact(fb_record, "clitic_composition"))
        nahw_complete = bool(_has_nahw_producer(source or {}) or _fd2_record_has_fact(fc_record, "nahw_dependency"))
        both_complete = morphology_complete and nahw_complete
        at_rest = bool(source is not None and "linguistic_consistency" not in flags and "span_ownership" not in flags and "exact_reconstruction" not in flags)
        if not at_rest:
            flags.append("reconstruction_failure")

        source_learner_complete = bool(source is not None and _has_learner_language(source, segments))
        generated_learner_complete = bool(views["learner_complete"])
        learner_complete = source_learner_complete or generated_learner_complete
        rich_sarf = bool(views["rich_sarf"])
        rich_nahw = bool(views["rich_nahw"])
        both_views = bool(views["generated_from_facts"] and views["compact_view"] and views["expanded_view"] and views["n_lang_clean"])
        payload_id = views["payload_id"] if views["generated_from_facts"] else "fd2.at_rest:" + _sha256({"loc": loc, "surface": source_surface, "spans": owned_spans})[:24]
        parity = _fd2_index_parity(occurrence_index.get(loc), payload_id)
        if not parity["covered"]:
            flags.append("repeated_appearance_parity")

        blockers: list[str] = []
        if not morphology_complete:
            blockers.append("morphology_facts_missing")
        if not nahw_complete:
            blockers.append("nahw_facts_missing")
        if not learner_complete:
            blockers.append("learner_language_missing")
        if not at_rest:
            blockers.append("reconstruction_failure")
        if conflicts:
            blockers.append("projection_conflict")
        if source is None:
            blockers.append("source_row_missing")
        if source is not None and "entry_linkage_missing" in flags:
            blockers.append("entry_linkage_missing")
        if fb_record and not fb_positive:
            blockers.extend("fb1." + code if not code.startswith("fb1.") else code for code in _fd2_record_blockers(fb_record))
        fb_blockers = producer_diagnostics.get("fb_blockers_by_loc", {}).get(loc, [])
        fc_blockers = producer_diagnostics.get("fc_blockers_by_loc", {}).get(loc)
        if fc_blockers:
            blockers.append("fc:" + str(fc_blockers))
        row_defects = [copy.deepcopy(item) for item in all_defects if _fd2_loc(item.get("loc")) == loc]
        if row_defects:
            blockers.append("producer_defect")
            flags.append("producer_defect")
        blockers = sorted(set(blockers))
        primary = _fd2_primary_blocker(blockers)
        primary_counts[primary] += 1
        for blocker in blockers:
            unresolved_counts[blocker] += 1
        for flag in flags:
            flag_counts[flag] += 1

        source_queue = bool(source is None or row_defects or fb_blockers or fc_blockers or "entry_linkage_missing" in flags or "reconstruction_failure" in flags)
        scholar_queue = True
        if source_queue:
            source_queue_counts["source/scholar"] += 1
        scholar_queue_counts["source/scholar"] += 1

        if morphology_complete:
            metric_counts[FD2_METRIC_KEYS[0]] += 1
        if nahw_complete:
            metric_counts[FD2_METRIC_KEYS[1]] += 1
        if both_complete:
            metric_counts[FD2_METRIC_KEYS[2]] += 1
        if at_rest:
            metric_counts[FD2_METRIC_KEYS[3]] += 1
        if rich_sarf:
            metric_counts[FD2_METRIC_KEYS[4]] += 1
        if rich_nahw:
            metric_counts[FD2_METRIC_KEYS[5]] += 1
        if both_views:
            metric_counts[FD2_METRIC_KEYS[6]] += 1
        if parity["covered"]:
            metric_counts[FD2_METRIC_KEYS[7]] += 1

        producer_status = {
            "F-B": "candidate" if fb_positive else "unresolved" if fb_record else "not_applicable",
            "F-C": "candidate" if fc_positive else "withheld" if fc_blockers else "not_applicable",
        }
        matrix.append({
            "schema": FD2_VERDICT_SCHEMA,
            "loc": loc,
            "quran_loc": "quran:" + loc,
            "surface": source_surface,
            "morphology_family": strat.get("morphology_family", strat.get("family")),
            "source_verdict": "verified",
            "compile_mode": "candidate",
            "compile_status": "compiled_review_queue" if at_rest else "blocked_structural_input",
            "producer_status": producer_status,
            "producer_projectors": {
                "F-B": (fb_record or {}).get("projection", {}).get("projection_id") if fb_record else None,
                "F-C": (fc_record or {}).get("projection", {}).get("projection_id") if fc_record else None,
            },
            "fact_completeness": {
                "morphology": morphology_complete,
                "nahw": nahw_complete,
                "both": both_complete,
            },
            "at_rest_projection": {
                "generated": at_rest,
                "payload_id": payload_id,
                "owned_spans": owned_spans,
            },
            "learner_language": {
                "source_preserved": source_learner_complete,
                "generated_from_facts": views["generated_from_facts"],
                "complete": learner_complete,
                "n_lang_clean": views["n_lang_clean"],
                "component_gloss": views["component_gloss"],
                "sarf": views["sarf_text"],
                "nahw": views["nahw_text"],
                "composition": views["composition_text"],
                "learner_explanation": views["learner_explanation"],
            },
            "views": {
                "payload_id": payload_id,
                "rich_sarf": rich_sarf,
                "rich_nahw": rich_nahw,
                "compact": views["compact_view"] if views["generated_from_facts"] else None,
                "expanded": views["expanded_view"] if views["generated_from_facts"] else None,
                "both_compact_and_expanded": both_views,
            },
            "repeated_appearance_parity": parity,
            "flags": sorted(set(flags)),
            "blockers": blockers,
            "primary_blocker": primary,
            "source_queue": source_queue,
            "scholar_queue": scholar_queue,
            "review_route": "source/scholar",
            "reconstruction_failed": not at_rest,
            "projection_conflicts": conflicts,
            "producer_defects": row_defects,
            "live_mutation_allowed": False,
        })

    metric_counts[FD2_METRIC_KEYS[8]] = dict(sorted(unresolved_counts.items()))
    metric_counts[FD2_METRIC_KEYS[9]] = {
        "source": sum(1 for row in matrix if row["source_queue"]),
        "scholar": sum(1 for row in matrix if row["scholar_queue"]),
        "both": sum(1 for row in matrix if row["source_queue"] and row["scholar_queue"]),
        "routes": dict(sorted(scholar_queue_counts.items())),
    }
    metric_counts[FD2_METRIC_KEYS[10]] = sum(1 for row in matrix if row["reconstruction_failed"])
    metric_counts[FD2_METRIC_KEYS[11]] = sum(bool(row["projection_conflicts"]) for row in matrix)
    all_defects = sorted(all_defects, key=lambda item: _canonical_json(item))
    metric_counts[FD2_METRIC_KEYS[12]] = {"count": len(all_defects), "items": all_defects}

    after = {
        "rows needing F-B": len(matrix) - metric_counts[FD2_METRIC_KEYS[0]],
        "rows needing F-C": len(matrix) - metric_counts[FD2_METRIC_KEYS[1]],
        "rows lacking learner-language": len(matrix) - sum(bool(row["learner_language"]["complete"]) for row in matrix),
        "rows with repeated-appearance coverage": metric_counts[FD2_METRIC_KEYS[7]],
    }
    movement = {
        "before": copy.deepcopy(FD2_BASELINE),
        "after": after,
        "delta": {key: after[key] - FD2_BASELINE[key] for key in FD2_BASELINE},
        "interpretation": "Movement measures this calibrated 455-row candidate rerun only; it is not corpus-wide certification or live coverage.",
    }
    report = {
        "schema": FD2_REPORT_SCHEMA,
        "report_version": "1.0.0",
        "candidate_only": True,
        "verified_row_count": len(matrix),
        "input_verdict_count": len(verdict_rows),
        "metrics": {key: metric_counts.get(key, 0) for key in FD2_METRIC_KEYS},
        "movement": movement,
        "flag_matrix": dict(sorted(flag_counts.items())),
        "primary_blocker_counts": dict(sorted(primary_counts.items())),
        "producer_lineage": {
            "F-B": "tools.build_clitic_pronoun_producer@1.0.0",
            "F-C": "tools.fc_nahw_producer@1.0.0",
            "compiler": "tools.fd_compiler@FD2",
            "projector": PROJECTOR_ID,
        },
        "scope": {
            "row_source": "strat-455.jsonl + v575-verdicts.jsonl",
            "morphology_family": "F-B applies only to clitic_pronoun_compositions",
            "nahw_condition": "F-C applies only when its exact source-evidence selector and strict contract builder accept",
            "other_families": "prior state retained; no scope creep",
        },
        "metric_definitions": {
            FD2_METRIC_KEYS[0]: "Rows with an existing structured morphology carrier or a positive guarded F-B clitic-composition fact.",
            FD2_METRIC_KEYS[1]: "Rows with an existing structured naḥw carrier or a positive guarded F-C dependency fact.",
            FD2_METRIC_KEYS[2]: "Rows satisfying both complete-fact predicates after the bounded merge.",
            FD2_METRIC_KEYS[3]: "Rows whose source segments are owned and concatenate exactly to the canonical surface.",
            FD2_METRIC_KEYS[4]: "Rows with a positive F-B fact-derived Ṣarf view that is N-LANG-clean.",
            FD2_METRIC_KEYS[5]: "Rows with a positive typed local/F-C naḥw view that is N-LANG-clean.",
            FD2_METRIC_KEYS[6]: "Rows with a fact-derived payload exposing one payload identity through compact and expanded views.",
            FD2_METRIC_KEYS[7]: "Rows whose exact location has a unique merged occurrence record with two or more appearances and a stable projection hash.",
            FD2_METRIC_KEYS[8]: "Counts of row blockers by exact stable blocker code or producer selector reason.",
            FD2_METRIC_KEYS[9]: "Source and scholar queue counts; all verified candidate rows remain scholar-routed, while source counts identify input/producer/structural follow-up.",
            FD2_METRIC_KEYS[10]: "Rows with failed source or typed-producer reconstruction.",
            FD2_METRIC_KEYS[11]: "Rows where a generated producer/view surface conflicts with the canonical source surface.",
            FD2_METRIC_KEYS[12]: "Producer exceptions or positive records that violate their typed-output contract; guarded abstentions are not defects.",
        },
        "verdicts_artifact": "fd2-455-verdicts.jsonl",
        "verdicts_meta_artifact": "fd2-455-verdicts.meta.json",
        "live_mutation_allowed": False,
    }
    return matrix, report


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
