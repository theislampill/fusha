#!/usr/bin/env python3
"""FAM5 source-grounded derived-verb producer.

This module is deliberately an adapter over the FAM4 finite-verb carrier.  It
adds a closed, calibration-scoped derived-form registry and emits only
entry-backed candidate facts.  A surface shape, label, or root hint never
creates a template fact by itself.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam4_finite_verb_producer as fam4
from tools.typed_claim_contract import learner_statement_for, validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
PROJECTOR_ID = "sarf.fam5.derived_verb.v1"
PRODUCER_ID = "tools.fam5_derived_verb_producer"
VERSION = "1.0.0"
SCHEMA = "qamus.typed_claim_contract.v1"
FACTS_ARTIFACT = "qamus/examples/fam5-derived-verbs/generated/derived-verb-facts.jsonl"
UNRESOLVED_ARTIFACT = "qamus/examples/fam5-derived-verbs/generated/unresolved-records.jsonl"
SUMMARY_ARTIFACT = "qamus/examples/fam5-derived-verbs/generated/calibration-summary.json"
DEFAULT_REGISTRY = ROOT / "qamus" / "examples" / "fam5-derived-verbs" / "derived-form-registry.jsonl"
DEFAULT_FAM4_PACKET = ROOT / "qamus" / "examples" / "fam4-finite-verbs" / "generated" / "calibration-sample.jsonl"

PROJECTION_STATUS = {
    "source_gap": "source_gap",
    "template_unresolved": "producer_pending",
    "weak_root_pattern_unresolved": "producer_pending",
    "owner_gated": "blocked",
    "entry_join_ambiguity": "blocked",
    "input_verdict_not_verified": "blocked",
    "surface_not_derived_verb": "blocked",
}

SUPPORTED_FORMS = {"II", "IV", "VIII", "quadriliteral"}
REQUIRED_MARKER_CLASSES = {
    "II": "derivative_form_ii_shadda",
    "IV": "derivative_prefix_form_iv_hamza",
    "VIII": "derivative_infix_form_viii_t",
    "quadriliteral": "quadriliteral_root",
}
FAM4_DERIVED_LOCS = {"4:72:4", "5:3:41", "12:51:21", "14:26:6"}
N_LANG_SARF = "Ṣarf — how this piece forms the word"
N_LANG_NAHW = "Naḥw — what this piece does here"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_derived_form_registry(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load the closed registry and reject ungoverned marker classes."""

    source = DEFAULT_REGISTRY if path is None else Path(path)
    rows = _jsonl(source)
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        pattern_id = str(row.get("pattern_id") or "")
        form = str(row.get("form") or "")
        if row.get("family") != "derived_verbs":
            raise ValueError(f"{source}:{index}: registry family must be derived_verbs")
        if not pattern_id or pattern_id in seen:
            raise ValueError(f"{source}:{index}: pattern_id must be present and unique")
        seen.add(pattern_id)
        if row.get("supported") is not True or form not in SUPPORTED_FORMS:
            raise ValueError(f"{source}:{index}: unsupported or out-of-scope derived form {form!r}")
        expected_marker = REQUIRED_MARKER_CLASSES[form]
        if row.get("marker_class") != expected_marker:
            raise ValueError(f"{source}:{index}: D-3 marker class mismatch for {form}")
        if form in {"II", "IV", "VIII"} and not row.get("derivational_class"):
            raise ValueError(f"{source}:{index}: derivational class is required")
        if form == "VIII" and row.get("onset_class") != "hamzat_al_wasl":
            raise ValueError(f"{source}:{index}: Form-VIII onset must be governed hamzat al-wasl")
    return rows


def load_carrier_registries(
    *,
    affix_registry: Any = None,
    weak_root_registry: Any = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load the FAM4 registries that remain shared carrier gates."""

    affixes = fam4.load_affix_registry(affix_registry) if isinstance(affix_registry, (str, Path)) else (
        list(affix_registry) if affix_registry is not None else fam4.load_affix_registry()
    )
    weak = fam4.load_weak_root_registry(weak_root_registry) if isinstance(weak_root_registry, (str, Path)) else (
        list(weak_root_registry) if weak_root_registry is not None else fam4.load_weak_root_registry()
    )
    return affixes, weak


def _loc(row: Mapping[str, Any]) -> str:
    return fam4._loc(row)


def _tokens(surface: str) -> list[dict[str, Any]]:
    """Reuse FAM4 token grouping while preserving the caller's mark order."""

    tokens = fam4._tokens(surface)
    for token in tokens:
        start = int(token["start"])
        end = int(token["end"])
        if 0 <= start < end <= len(surface):
            token["surface"] = surface[start:end]
            token["marks"] = [char for char in surface[start + 1 : end] if unicodedata.category(char) == "Mn"]
    return tokens


def _entry_map(entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return fam4._entry_map(entries)


def _source_addresses(
    loc: str,
    row: Mapping[str, Any],
    match: Mapping[str, Any] | None = None,
    pattern_id: str | None = None,
) -> list[dict[str, str]]:
    addresses: list[dict[str, str]] = [{"address": f"quran:{loc}", "source_kind": "quran_token"}]
    if match:
        addresses.append({"address": str(match["entry_surface_address"]), "source_kind": "qamus_entry_field"})
    if pattern_id:
        addresses.append({"address": f"registry:fam5-derived-verbs:pattern:{pattern_id}", "source_kind": "review_artifact"})
    if row.get("whitelist_entry_id"):
        addresses.append({"address": f"corpus:whitelist:{loc}", "source_kind": "corpus_record"})
    if row.get("v575_source_address"):
        addresses.append({"address": str(row["v575_source_address"]), "source_kind": "review_artifact"})
    raw = row.get("source_addresses")
    if isinstance(raw, list):
        for address in raw:
            if isinstance(address, Mapping) and address.get("address") and address.get("source_kind"):
                addresses.append({"address": str(address["address"]), "source_kind": str(address["source_kind"])})
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for address in addresses:
        key = (address["address"], address["source_kind"])
        if key not in seen:
            seen.add(key)
            unique.append(address)
    return unique


def _projection_id(loc: str) -> str:
    return "fam5.derived_verb." + loc.replace(":", ".") + ".v1"


def _common_occurrence(loc: str, surface: str, entry_id: str | None = None) -> dict[str, Any]:
    occurrence = fam4._common_occurrence(loc, surface, entry_id)
    return occurrence


def _base_fact(
    *,
    fact_type: str,
    fact_value: dict[str, Any],
    spans: list[dict[str, Any]],
    source: dict[str, str],
    source_address: dict[str, str],
    evidence_status: str,
    confidence: str,
    evidence_mode: str,
    evidence_ids: list[str],
    evidence_summary: str,
    source_addresses: list[dict[str, str]],
    certification_status: str,
    certification_reason: str,
    dependencies: dict[str, Any],
    derivation_chain: list[dict[str, Any]],
    guards: list[dict[str, str]],
    defeaters: list[dict[str, Any]],
    blockers: list[dict[str, str]],
    projection_id: str,
) -> dict[str, Any]:
    """Use FAM4's F-A envelope builder, then bind ownership to FAM5."""

    fact = fam4._base_fact(
        fact_type=fact_type,
        fact_value=fact_value,
        spans=spans,
        source=source,
        source_address=source_address,
        evidence_status=evidence_status,
        confidence=confidence,
        evidence_mode=evidence_mode,
        evidence_ids=evidence_ids,
        evidence_summary=evidence_summary,
        source_addresses=source_addresses,
        certification_status=certification_status,
        certification_reason=certification_reason,
        dependencies=dependencies,
        derivation_chain=derivation_chain,
        guards=guards,
        defeaters=defeaters,
        blockers=blockers,
        projection_id=projection_id,
    )
    fact["ownership"] = {
        "primary": {"owner_id": "fam5-derived-verb-producer", "owner_type": "producer"},
        "secondary": [
            {"owner_id": "qamus-entry-source", "owner_type": "source_owner"},
            {"owner_id": "sarf-derived-verb-registry", "owner_type": "rule_owner"},
        ],
    }
    fact["producer"] = {"id": PRODUCER_ID, "version": VERSION}
    fact["rule_projector"] = {
        "rule_id": "fam5.derived_verb.letter_evidence",
        "projector_id": PROJECTOR_ID,
        "version": VERSION,
    }
    fact["fact_id"] = fam4._fact_id(fact)
    return fact


def _pattern_shape(pattern: Mapping[str, Any]) -> str:
    return str(pattern.get("pattern_id") or "").replace(".", "_")


def _token_matches_letters(tokens: Sequence[Mapping[str, Any]], indices: Sequence[int], radicals: Sequence[str]) -> bool:
    return len(radicals) == len(indices) and all(tokens[index]["letter"] == radical for index, radical in zip(indices, radicals))


def _match_pattern(
    surface: str,
    radicals: Sequence[str],
    pattern: Mapping[str, Any],
    row: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Match only the explicit, source-certified shapes in the FAM5 registry."""

    if pattern.get("supported") is not True:
        return None
    tokens = _tokens(surface)
    letters = [token["letter"] for token in tokens]
    pattern_id = str(pattern.get("pattern_id") or "")
    root_indices: list[int] = []
    shared_root_indices: dict[int, list[int]] = {}
    prefix_indices: list[int] = []
    suffix_indices: list[int] = []
    form = str(pattern.get("form") or "")

    if pattern_id == "derived.form_ii.perfect_active.3ms":
        root_indices = [0, 1, 2]
        passed = len(tokens) == 3 and _token_matches_letters(tokens, root_indices, radicals)
        passed = passed and fam4._has_mark(tokens[0], "َ") and fam4._has_mark(tokens[1], "ّ") and fam4._has_mark(tokens[2], "َ")
        if passed:
            shared_root_indices[1] = [2, "form_ii_reduplication"]
    elif pattern_id == "derived.form_ii.imperfect_active.3ms.energic":
        root_indices = [2, 3, 4]
        prefix_indices = [0, 1]
        suffix_indices = [5]
        boundary = row.get("energic_boundary")
        passed = (
            len(tokens) == 6
            and letters[:2] == ["ل", "ي"]
            and _token_matches_letters(tokens, root_indices, radicals)
            and letters[5] == "ن"
            and fam4._has_mark(tokens[3], "ّ")
            and isinstance(boundary, Mapping)
            and boundary.get("surface") == tokens[5]["surface"]
            and bool(boundary.get("source_address"))
            and boundary.get("byte_clean") is True
        )
        if passed:
            shared_root_indices[3] = [2, "form_ii_reduplication"]
    elif pattern_id == "derived.form_iv.perfect_active.1cs":
        root_indices = [1, 2, 3]
        prefix_indices = [0]
        suffix_indices = [4]
        passed = (
            len(tokens) == 5
            and letters[0] == "أ"
            and _token_matches_letters(tokens, root_indices, radicals)
            and letters[4] == "ت"
            and fam4._marks_are(tokens[0], "َ")
            and fam4._marks_are(tokens[1], "ْ")
            and fam4._marks_are(tokens[2], "َ")
            and fam4._marks_are(tokens[3], "ْ")
            and fam4._marks_are(tokens[4], "ُ")
        )
    elif pattern_id == "derived.form_iv.perfect_active.3mp":
        root_indices = [1, 2, 3]
        prefix_indices = [0]
        suffix_indices = [4, 5]
        passed = (
            len(tokens) == 6
            and letters[0] == "أ"
            and _token_matches_letters(tokens, root_indices, radicals)
            and letters[4:] == ["و", "ا"]
            and fam4._marks_are(tokens[0], "َ")
            and fam4._marks_are(tokens[1], "ْ")
            and fam4._marks_are(tokens[2], "َ")
            and fam4._marks_are(tokens[3], "ُ")
        )
    elif pattern_id == "derived.form_viii.perfect_passive.3fs":
        root_indices = [1, 3, 3]
        prefix_indices = [0, 2]
        suffix_indices = [4]
        passed = (
            len(tokens) == 5
            and letters[0] == "ٱ"
            and letters[1] == radicals[0]
            and letters[2] == "ت"
            and letters[3] == radicals[1] == radicals[2]
            and letters[4] == "ت"
            and fam4._marks_are(tokens[1], "ْ")
            and fam4._has_mark(tokens[3], "ّ")
            and fam4._marks_are(tokens[4], "ْ")
        )
        if passed:
            shared_root_indices[3] = [2, 3]
    elif pattern_id == "quadriliteral.perfect_active.3ms":
        root_indices = [0, 1, 2, 3]
        passed = len(tokens) == 4 and _token_matches_letters(tokens, root_indices, radicals)
        passed = passed and fam4._has_mark(tokens[0], "َ") and fam4._has_mark(tokens[1], "ْ")
    else:
        return None
    if not passed:
        return None
    return {
        "pattern": copy.deepcopy(dict(pattern)),
        "tokens": tokens,
        "root_indices": root_indices,
        "prefix_indices": prefix_indices,
        "suffix_indices": suffix_indices,
        "shared_root_indices": shared_root_indices,
        "form": form,
    }


def _segment(
    token: Mapping[str, Any],
    *,
    base_index: int,
    span_id: str,
    role: str,
    owner_class: str,
    display_class: str,
    shared_radicals: list[int] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "span_id": span_id,
        "start": int(token["start"]),
        "end": int(token["end"]),
        "surface": str(token["surface"]),
        "base_letter_index": base_index,
        "letter": str(token["letter"]),
        "marks": list(token.get("marks", [])),
        "role": role,
        "owner_class": owner_class,
        "class": display_class,
    }
    if shared_radicals:
        value["shared_radical_indices"] = list(shared_radicals)
    return value


def _segment_data(match_info: Mapping[str, Any]) -> dict[str, Any]:
    pattern = match_info["pattern"]
    tokens = list(match_info["tokens"])
    root_indices = list(match_info["root_indices"])
    prefix_indices = list(match_info.get("prefix_indices") or [])
    suffix_indices = list(match_info.get("suffix_indices") or [])
    shared = match_info.get("shared_root_indices") or {}
    form = str(pattern.get("form") or "")
    segments: list[dict[str, Any]] = []
    ownership: list[dict[str, Any]] = []
    root_radicals: list[dict[str, Any]] = []
    derivational_additions: list[dict[str, Any]] = []
    inflectional_prefixes: list[dict[str, Any]] = []
    inflectional_suffixes: list[dict[str, Any]] = []
    used: set[int] = set()

    def add(
        index: int,
        role: str,
        owner_class: str,
        display_class: str,
        *,
        shared_radicals: list[int] | None = None,
    ) -> None:
        if index in used:
            return
        used.add(index)
        segment = _segment(
            tokens[index],
            base_index=index,
            span_id=f"span:base-letter-{index}",
            role=role,
            owner_class=owner_class,
            display_class=display_class,
            shared_radicals=shared_radicals,
        )
        segments.append(segment)
        ownership.append({
            "base_letter_index": index,
            "letter": segment["letter"],
            "surface": segment["surface"],
            "start": segment["start"],
            "end": segment["end"],
            "owner_class": owner_class,
            "role": role,
            "display_class": display_class,
            "marks": segment["marks"],
            **({"shared_radical_indices": shared_radicals} if shared_radicals else {}),
        })

    if form == "VIII":
        add(0, "hamzat_al_wasl", "hamzat_al_wasl", "qg-verb-prefix")
        add(1, "root_radical", "root_radical", "qg-root-radical")
        add(2, "derivative_infix", "derivative_infix", "qg-derivative-prefix")
        add(3, "root_radical_shared_2_3", "root_radical", "qg-root-radical", shared_radicals=[2, 3])
        add(4, "inflectional_suffix_feminine", "inflectional_suffix", "qg-subject-pronoun")
        derivational_additions.append({
            "role": "derivative_infix",
            "class": "derivative_infix",
            "marker_class": "derivative_infix_form_viii_t",
            "surface": tokens[2]["surface"],
            "base_letter_indices": [2],
            "source_role": "Form-VIII infix ت",
        })
        inflectional_suffixes.append({"role": "feminine_suffix", "class": "inflectional_suffix", "surface": tokens[4]["surface"], "base_letter_indices": [4]})
    elif form == "IV":
        add(0, "derivative_prefix", "derivative_prefix", "qg-derivative-prefix")
        derivational_additions.append({
            "role": "derivative_prefix",
            "class": "derivative_prefix",
            "marker_class": "derivative_prefix_form_iv_hamza",
            "surface": tokens[0]["surface"],
            "base_letter_indices": [0],
            "source_role": "Form-IV prefix أ",
        })
        for radical_number, index in enumerate(root_indices, 1):
            add(index, "root_radical", "root_radical", "qg-root-radical")
            root_radicals.append({
                "index": radical_number,
                "radical": str(pattern.get("root_radicals", [""])[radical_number - 1]),
                "surface": tokens[index]["surface"],
                "start": tokens[index]["start"],
                "end": tokens[index]["end"],
                "span_id": f"span:base-letter-{index}",
            })
        for index in suffix_indices:
            add(index, "subject_suffix", "inflectional_suffix", "qg-subject-pronoun")
            inflectional_suffixes.append({"role": "subject_suffix", "class": "inflectional_suffix", "surface": tokens[index]["surface"], "base_letter_indices": [index]})
    elif form == "II":
        if prefix_indices:
            add(0, "nahw_overlay_prefix", "nahw_overlay", "qg-preposition")
            add(1, "inflectional_prefix", "inflectional_prefix", "qg-verb-person-prefix")
            inflectional_prefixes.append({"role": "person_prefix", "class": "inflectional_prefix", "surface": "".join(tokens[index]["surface"] for index in prefix_indices), "base_letter_indices": prefix_indices})
        for radical_number, index in enumerate(root_indices, 1):
            shared_radicals = [radical_number] if index in shared else None
            add(index, "root_radical", "root_radical", "qg-root-radical", shared_radicals=shared_radicals)
            root_radicals.append({
                "index": radical_number,
                "radical": str(pattern.get("root_radicals", [""])[radical_number - 1]),
                "surface": tokens[index]["surface"],
                "start": tokens[index]["start"],
                "end": tokens[index]["end"],
                "span_id": f"span:base-letter-{index}",
            })
        if not prefix_indices:
            derivational_additions.append({
                "role": "derivative_marker",
                "class": "derivative_marker",
                "marker_class": "derivative_form_ii_shadda",
                "surface": tokens[root_indices[1]]["surface"],
                "base_letter_indices": [root_indices[1]],
                "source_role": "Form-II gemination mark on the second root realization",
            })
        if suffix_indices:
            for index in suffix_indices:
                add(index, "energic_suffix", "inflectional_suffix", "qg-verb-prefix")
            inflectional_suffixes.append({"role": "energic_nun", "class": "inflectional_suffix", "surface": "".join(tokens[index]["surface"] for index in suffix_indices), "base_letter_indices": suffix_indices})
    else:  # quadriliteral
        for radical_number, index in enumerate(root_indices, 1):
            add(index, "root_radical", "root_radical", "qg-root-radical")
            root_radicals.append({
                "index": radical_number,
                "radical": str(pattern.get("root_radicals", [""])[radical_number - 1]),
                "surface": tokens[index]["surface"],
                "start": tokens[index]["start"],
                "end": tokens[index]["end"],
                "span_id": f"span:base-letter-{index}",
            })

    if form == "VIII":
        root_radicals = [
            {"index": 1, "radical": str(pattern.get("root_radicals", [""])[0]), "surface": tokens[1]["surface"], "start": tokens[1]["start"], "end": tokens[1]["end"], "span_id": "span:base-letter-1"},
            {"index": 2, "radical": str(pattern.get("root_radicals", [""])[1]), "surface": tokens[3]["surface"], "start": tokens[3]["start"], "end": tokens[3]["end"], "span_id": "span:base-letter-3", "shared_written_letter": True},
            {"index": 3, "radical": str(pattern.get("root_radicals", [""])[2]), "surface": tokens[3]["surface"], "start": tokens[3]["start"], "end": tokens[3]["end"], "span_id": "span:base-letter-3", "shared_written_letter": True},
        ]
    elif form == "II" and not root_radicals:
        root_radicals = [
            {"index": index + 1, "radical": str(pattern.get("root_radicals", [""])[index]), "surface": tokens[token_index]["surface"], "start": tokens[token_index]["start"], "end": tokens[token_index]["end"], "span_id": f"span:base-letter-{token_index}"}
            for index, token_index in enumerate(root_indices)
        ]
    segments.sort(key=lambda item: item["base_letter_index"])
    ownership.sort(key=lambda item: item["base_letter_index"])
    spans = [
        {key: value for key, value in segment.items() if key in {"span_id", "start", "end", "surface", "role"}}
        for segment in segments
    ]
    gemination: dict[str, Any] | None = None
    if form == "VIII":
        gemination = {
            "present": True,
            "treatment": "C_shared_written_letter",
            "idgham_classification": "B_shared_letter_clean_split",
            "split_authorized": False,
            "written_base_letter_index": 3,
            "shared_radical_indices": [2, 3],
            "reason": "The shadda-bearing ثّ is one written base letter; the two root roles share its span and are not naively split.",
        }
    elif form == "II":
        gemination = {
            "present": True,
            "treatment": "C_shared_written_letter",
            "idgham_classification": "A_clean_split",
            "split_authorized": False,
            "written_base_letter_index": root_indices[1],
            "shared_radical_indices": [2, "form_ii_reduplication"],
            "reason": "The second-root shadda is retained as a governed marker on one written base letter.",
        }
    return {
        "tokens": tokens,
        "segments": segments,
        "spans": spans,
        "letter_ownership": ownership,
        "root_radicals": root_radicals,
        "derivational_additions": derivational_additions,
        "inflectional_prefixes": inflectional_prefixes,
        "inflectional_suffixes": inflectional_suffixes,
        "gemination": gemination,
    }


def _learner_copy(segments: Sequence[Mapping[str, Any]], pattern_id: str) -> dict[str, Any]:
    segment_summary = " ".join(f"{segment.get('surface')}[{segment.get('role')}]" for segment in segments)
    return {
        "payload_id": "fd.fam5.payload:" + fam4._hash({"pattern_id": pattern_id, "segments": list(segments)})[:16],
        "sarf": f"{N_LANG_SARF}: the source-addressed {pattern_id} owns the written segments {segment_summary}.",
        "nahw": f"{N_LANG_NAHW}: syntactic overlays, including the energic boundary when present, remain separately governed.",
        "n_lang_clean": True,
    }


def _pattern_value(pattern: Mapping[str, Any], radicals: Sequence[str], row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pattern_id": str(pattern["pattern_id"]),
        "form": str(pattern["form"]),
        "template": str(pattern.get("template") or ""),
        "marker_class": str(pattern.get("marker_class") or ""),
        "derivational_class": str(pattern.get("derivational_class") or "none"),
        "derivational_additions_certified": True,
        "tense_aspect": str(pattern.get("tense_aspect") or ""),
        "voice": str(pattern.get("voice") or ""),
        "person": str(pattern.get("person") or ""),
        "number": str(pattern.get("number") or ""),
        "gender": str(pattern.get("gender") or ""),
        "mood": str(pattern.get("mood") or "not_asserted"),
        "root_radicals": list(radicals),
        "source_grounding": str(row.get("source_grounding") or "entry_form_attestation"),
    }


def _build_candidate(
    row: Mapping[str, Any],
    match: Mapping[str, Any],
    match_info: Mapping[str, Any],
) -> dict[str, Any]:
    loc = _loc(row)
    surface = str(row.get("surface") or "")
    entry = match["entry"]
    entry_id = str(match["entry_id"])
    radicals = fam4._root_radicals(entry)
    pattern = dict(match_info["pattern"])
    pattern["root_radicals"] = radicals
    data = _segment_data({**match_info, "pattern": pattern})
    source_addresses = _source_addresses(loc, row, match, str(pattern["pattern_id"]))
    projection_id = _projection_id(loc)
    base_value = {
        "typed_kind": "fam5.entry_form_attestation",
        "occurrence": {"quran_loc": loc, "surface": surface},
        "entry_id": entry_id,
        "entry_surface": match["entry_surface"],
        "entry_surface_address": match["entry_surface_address"],
        "entry_relation": match["relation"],
        "root": " ".join(radicals),
        "whitelist_entry_id": row.get("whitelist_entry_id"),
        "source_fact": {
            "entry_id": entry_id,
            "entry_surface": match["entry_surface"],
            "entry_surface_address": match["entry_surface_address"],
            "entry_relation": match["relation"],
            "whitelist_entry_id": row.get("whitelist_entry_id"),
        },
    }
    base_fact = _base_fact(
        fact_type="entry_form_attestation",
        fact_value=base_value,
        spans=[{"span_id": "span:occurrence", "start": 0, "end": len(surface), "surface": surface, "role": "derived_verb_occurrence"}],
        source={"source_id": f"entry:{entry_id}", "source_kind": "qamus_entry_field"},
        source_address={"address": str(match["entry_surface_address"]), "source_kind": "qamus_entry_field"},
        evidence_status="source_addressed_candidate",
        confidence="high",
        evidence_mode="direct_source_attestation",
        evidence_ids=[str(match["entry_surface_address"])],
        evidence_summary="The caller-supplied entry contains the exact observed derived-verb form.",
        source_addresses=source_addresses,
        certification_status="candidate",
        certification_reason="Entry attestation is candidate-only and not a publication transition.",
        dependencies={"fact_ids": [], "source_addresses": []},
        derivation_chain=[],
        guards=[
            {"guard_id": "fam5.entry_surface_exact", "reason": "observed surface equals a caller-supplied entry form"},
            {"guard_id": "fam5.source_grounding_required", "reason": "template labels and surface shape are not source evidence"},
        ],
        defeaters=[],
        blockers=[],
        projection_id=projection_id,
    )
    gemination = copy.deepcopy(data["gemination"])
    if pattern["form"] == "VIII":
        assimilation = {
            "status": "not_asserted",
            "written_shape_preserved": True,
            "reason": "This row certifies the exact Form-VIII entry surface; no generalized assimilation rule is exported.",
        }
    else:
        assimilation = {"status": "not_present_or_not_asserted", "written_shape_preserved": True}
    hamzat = {
        "present": pattern["form"] == "VIII",
        "class": "hamzat_al_wasl" if pattern["form"] == "VIII" else None,
        "surface": data["segments"][0]["surface"] if pattern["form"] == "VIII" else None,
        "governed": pattern["form"] == "VIII",
        "source_address": f"registry:fam5-derived-verbs:pattern:{pattern['pattern_id']}",
    }
    mood = {
        "status": "source_addressed" if pattern.get("mood") else "not_asserted",
        "value": pattern.get("mood") or "not_asserted",
        "public_label": N_LANG_NAHW,
        "emitted_as_sarf": pattern.get("mood") == "energic",
    }
    derived_value = {
        "typed_kind": "fam5.derived_verb_evidence",
        "occurrence": {"quran_loc": loc, "surface": surface},
        "entry_id": entry_id,
        "entry_surface": match["entry_surface"],
        "entry_surface_address": match["entry_surface_address"],
        "entry_relation": match["relation"],
        "root": " ".join(radicals),
        "root_radicals": data["root_radicals"],
        "template": _pattern_value(pattern, radicals, row),
        "form": pattern["form"],
        "tense_aspect": pattern.get("tense_aspect"),
        "voice": pattern.get("voice"),
        "person": pattern.get("person"),
        "number": pattern.get("number"),
        "gender": pattern.get("gender"),
        "mood": mood,
        "derivational_additions": data["derivational_additions"],
        "inflectional_prefixes": data["inflectional_prefixes"],
        "inflectional_suffixes": data["inflectional_suffixes"],
        "weak_letter_operations": {"status": "none_asserted", "source_grounded": True},
        "assimilation": assimilation,
        "gemination": gemination,
        "hamzat_al_wasl": hamzat,
        "letter_ownership": data["letter_ownership"],
        "surface_segments": data["segments"],
        "reconstruction_proof": {
            "passed": "".join(segment["surface"] for segment in data["segments"]) == surface,
            "surface": surface,
            "segments": copy.deepcopy(data["segments"]),
            "source_addresses": copy.deepcopy(source_addresses),
            "each_written_base_letter_exactly_one_class": len(data["letter_ownership"]) == len(data["tokens"]),
            "base_letter_indices_complete": [item["base_letter_index"] for item in data["letter_ownership"]] == list(range(len(data["tokens"]))),
            "no_naive_geminate_split": pattern["form"] != "VIII" or sum(1 for item in data["segments"] if item["letter"] == "ث") == 1,
        },
        "source_fact": {
            "entry_id": entry_id,
            "entry_surface_address": match["entry_surface_address"],
            "registry_pattern_id": pattern["pattern_id"],
            "root_radical_spans": [item["span_id"] for item in data["root_radicals"]],
            "derivational_addition_spans": [item["base_letter_indices"] for item in data["derivational_additions"]],
            "inflectional_prefix_spans": [item["base_letter_indices"] for item in data["inflectional_prefixes"]],
            "inflectional_suffix_spans": [item["base_letter_indices"] for item in data["inflectional_suffixes"]],
        },
    }
    derived_fact = _base_fact(
        fact_type="derived_verb_evidence",
        fact_value=derived_value,
        spans=data["spans"],
        source={"source_id": f"construction:fam5:{loc}", "source_kind": "construction"},
        source_address={"address": f"construction:fam5:{loc}", "source_kind": "construction"},
        evidence_status="source_addressed_candidate",
        confidence="high",
        evidence_mode="deterministic_derivation_from_certified_facts",
        evidence_ids=[str(pattern["pattern_id"]), str(match["entry_surface_address"])],
        evidence_summary="The closed FAM5 registry reconstructs the entry-backed derived form at letter level.",
        source_addresses=source_addresses,
        certification_status="candidate",
        certification_reason="Derived-verb morphology remains a candidate and is not materialized.",
        dependencies={"fact_ids": [base_fact["fact_id"]], "source_addresses": copy.deepcopy(source_addresses)},
        derivation_chain=[{
            "step_id": "fam5.step.entry-plus-derived-template",
            "operation": "apply_closed_derived_form_pattern_to_certified_entry_surface",
            "input_fact_ids": [base_fact["fact_id"]],
            "input_source_addresses": copy.deepcopy(source_addresses),
            "output": "root, derived additions, inflectional affixes, weak operations, voice, person-number-gender, mood, and letter ownership",
        }],
        guards=[
            {"guard_id": "fam5.root_letter_level", "reason": "entry radicals occupy exact written base-letter ownership records"},
            {"guard_id": "fam5.d3_derivational_class_separation", "reason": "Form-IV prefix and Form-VIII infix have their own derivational classes"},
            {"guard_id": "fam5.template_registry_closed", "reason": "only an attested, source-certified registry pattern can emit"},
            {"guard_id": "fam5.reconstruction_exact", "reason": "segment concatenation equals the canonical occurrence surface"},
            {"guard_id": "fam5.letter_owner_totality", "reason": "each written base letter has exactly one owner class"},
            {"guard_id": "fam5.gemination_treatment_c", "reason": "gemination remains a shared-written-letter record with A-D classification"},
            {"guard_id": "fam5.hamzat_al_wasl_governed", "reason": "Form-VIII hamzat al-wasl is separately typed"},
            {"guard_id": "fam5.nahw_overlay_separate", "reason": "syntactic function labels are not merged into Ṣarf"},
            {"guard_id": "fam5.candidate_only", "reason": "pre_apply_not_authorized remains true"},
        ],
        defeaters=[],
        blockers=[],
        projection_id=projection_id,
    )
    spans = [str(span["span_id"]) for span in data["spans"]]
    learner = _learner_copy(data["segments"], str(pattern["pattern_id"]))
    return {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam5:derived-verb:{loc}",
        "record_type": "projection_input",
        "canonical_occurrence": _common_occurrence(loc, surface, entry_id),
        "facts": [base_fact, derived_fact],
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {"artifact": FACTS_ARTIFACT, "field": "derived_verb", "public_materialization_allowed": False, "live_mutation_allowed": False},
            "claim": {
                "text": "The written occurrence has a candidate source-addressed derived-verb structure with explicit letter ownership.",
                "language": "en",
                "fact_bindings": [{"fact_id": derived_fact["fact_id"], "fact_field": "fact_value.template.form", "surface_span_ids": spans}],
            },
            "learner_statement": None,
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
                "status": "candidate",
                "route": "entry_backed_derived_form_pattern",
                "segments": data["segments"],
                "learner_copy": learner,
                "nahw_overlay": {"public_label": N_LANG_NAHW, "visible": False, "status": "separate_overlay"},
            },
        },
    }


def _route_reason(route: str, blocker_id: str, row: Mapping[str, Any]) -> str:
    reasons = {
        "source_gap": "No exact source-grounded entry form is available; a surface or label cannot certify a derived template.",
        "template_unresolved": "The observed shape requires a guarded derived-form decision that this calibration producer cannot certify.",
        "weak_root_pattern_unresolved": "A weak-root operation is required but no source-grounded transformation rule is registered.",
        "owner_gated": "The FAM4 carrier routed this derived-form marker to the derived_verbs owner; no claim is emitted here without the required owner fact.",
        "entry_join_ambiguity": "More than one exact entry join remains and the producer will not choose a root or template.",
    }
    return reasons.get(route, f"FAM5 abstained via typed route {route} for {row.get('surface')!r}; no derived-verb claim is emitted.") + f" Blocker: {blocker_id}."


def _build_unresolved(
    row: Mapping[str, Any],
    route: str,
    *,
    match: Mapping[str, Any] | None = None,
    near_match: Mapping[str, Any] | None = None,
    blocker_id: str | None = None,
) -> dict[str, Any]:
    loc = _loc(row)
    surface = str(row.get("surface") or "")
    projection_id = _projection_id(loc)
    status = PROJECTION_STATUS.get(route, "producer_pending")
    blocker = blocker_id or f"fam5.{route}"
    reason = _route_reason(route, blocker, row)
    entry_context = {
        "entry_id": str(match["entry_id"]) if match else None,
        "entry_surface": match.get("entry_surface") if match else None,
        "entry_surface_address": match.get("entry_surface_address") if match else None,
        "entry_relation": match.get("relation") if match else None,
        "near_entry_id": str(near_match["entry_id"]) if near_match else None,
        "near_entry_surface": near_match.get("entry_surface") if near_match else None,
        "near_entry_surface_address": near_match.get("entry_surface_address") if near_match else None,
        "near_entry_relation": near_match.get("relation") if near_match else None,
        "whitelist_entry_id": row.get("whitelist_entry_id"),
    }
    source_addresses = _source_addresses(loc, row, match or near_match)
    observed_tokens = _tokens(surface)
    observed_ownership = [
        {
            "base_letter_index": index,
            "letter": token["letter"],
            "surface": token["surface"],
            "start": token["start"],
            "end": token["end"],
            "owner_class": "unresolved_surface_letter",
            "role": "unresolved_observed_letter",
            "marks": list(token.get("marks", [])),
        }
        for index, token in enumerate(observed_tokens)
    ]
    value = {
        "typed_kind": "fam5.unresolved_derived_verb",
        "occurrence": {"quran_loc": loc, "surface": surface},
        "route": route,
        "observed_sub_shape": str(row.get("template_id") or row.get("template_hypothesis") or "derived_form_unresolved"),
        "template_hypothesis": row.get("template_id") or row.get("label_claim"),
        "root_hint": row.get("root_hint") or row.get("existing_root_values"),
        "entry_context": entry_context,
        "owner_marker": row.get("owner_marker") or row.get("fam4_owner_marker"),
        "source_situation": {
            "v575_verdict": row.get("_v575_verdict", row.get("v575_verdict")),
            "source_grounding": row.get("source_grounding"),
            "source_addresses": copy.deepcopy(source_addresses),
        },
        "letter_ownership": observed_ownership,
        "surface_tokens": observed_ownership,
        "surface_preserved": True,
        "reconstruction_proof": {
            "passed": False,
            "reason": route,
            "surface": surface,
            "observed_base_letters_complete": [item["base_letter_index"] for item in observed_ownership] == list(range(len(observed_tokens))),
        },
        "source_fact": {"observed_surface": surface, "route": route, "blocker_id": blocker, "whitelist_entry_id": row.get("whitelist_entry_id")},
    }
    fact = _base_fact(
        fact_type="derived_verb_pending",
        fact_value=value,
        spans=[{"span_id": "span:unresolved:surface", "start": 0, "end": len(surface), "surface": surface, "role": "unresolved_derived_verb_surface"}],
        source={"source_id": f"quran:{loc}", "source_kind": "quran_token"},
        source_address={"address": f"quran:{loc}", "source_kind": "quran_token"},
        evidence_status="blocked",
        confidence="unknown",
        evidence_mode="unresolved",
        evidence_ids=[f"fam5:unresolved:{loc}:{route}"],
        evidence_summary="Typed abstention; no derived-verb morphology claim is emitted.",
        source_addresses=source_addresses,
        certification_status="blocked" if status == "blocked" else "pending",
        certification_reason=reason,
        dependencies={"fact_ids": [], "source_addresses": []},
        derivation_chain=[],
        guards=[
            {"guard_id": "fam5.no_surface_template_inference", "reason": "a surface template or label cannot certify a typed derived-form fact"},
            {"guard_id": "fam5.candidate_only", "reason": "pre_apply_not_authorized remains true"},
        ],
        defeaters=[{"defeater_id": blocker, "reason": reason, "fact_ids": []}],
        blockers=[{"blocker_id": blocker, "reason": reason}],
        projection_id=projection_id,
    )
    return {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam5:derived-verb:pending:{loc}",
        "record_type": "unresolved_projection",
        "canonical_occurrence": _common_occurrence(loc, surface),
        "facts": [fact],
        "projection": {
            "projection_id": projection_id,
            "status": status,
            "unresolved_status": status,
            "learner_visible": True,
            "materialization_target": {"artifact": UNRESOLVED_ARTIFACT, "field": "derived_verb_unresolved", "public_materialization_allowed": False, "live_mutation_allowed": False},
            "claim": None,
            "learner_statement": learner_statement_for(status),
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
                "status": status,
                "route": route,
                "segments": [{"surface": surface, "role": "unresolved_derived_verb_surface", "span_id": "span:unresolved:surface"}],
            },
        },
    }


def _template_special_route(row: Mapping[str, Any], surface: str) -> tuple[str, str] | None:
    if row.get("template_claim_only") or row.get("source_grounding") == "surface_template_only":
        return "source_gap", "fam5.source_gap"
    if row.get("assimilation_claim") and "ٱصْط" in surface:
        return "template_unresolved", "fam5.assimilation_unresolved"
    if row.get("naive_gemination_split"):
        return "template_unresolved", "fam5.gemination_treatment_c_required"
    if row.get("voice_claim") == "passive" and surface.startswith("أَ"):
        return "template_unresolved", "fam5.voice_diacritic_mismatch"
    if row.get("force_triliteral"):
        return "template_unresolved", "fam5.quadriliteral_not_triliteral"
    if row.get("hamzat_al_wasl_claim") is False and (surface.startswith("ا") or surface.startswith("ٱ")):
        return "template_unresolved", "fam5.hamzat_al_wasl_unresolved"
    if row.get("template_id", "").startswith("derived.form_ii.imperfect") and not row.get("energic_boundary") and surface.endswith("نَّ"):
        return "template_unresolved", "fam5.energic_boundary_unresolved"
    return None


def produce_record(
    row: Mapping[str, Any],
    *,
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    form_registry: Sequence[Mapping[str, Any]] | Path | str | None = None,
    affix_registry: Any = None,
    weak_root_registry: Any = None,
) -> dict[str, Any]:
    """Produce one source-grounded candidate or typed unresolved record."""

    source_row = copy.deepcopy(dict(row))
    surface = str(source_row.get("surface") or "")
    if not surface:
        raise ValueError("FAM5 row surface is required")
    registry = load_derived_form_registry(form_registry) if isinstance(form_registry, (str, Path)) or form_registry is None else list(form_registry)
    carrier_affixes, carrier_weak_registry = load_carrier_registries(
        affix_registry=affix_registry,
        weak_root_registry=weak_root_registry,
    )
    loc = _loc(source_row)
    verdict = source_row.get("_v575_verdict", source_row.get("v575_verdict", source_row.get("verdict")))
    if verdict not in (None, "verified"):
        record = _build_unresolved(source_row, "input_verdict_not_verified", blocker_id="fam5.input_verdict_not_verified")
    elif source_row.get("morphology_family") not in (None, "derived_verbs") or source_row.get("part_of_speech") not in (None, "verb"):
        record = _build_unresolved(source_row, "surface_not_derived_verb", blocker_id="fam5.surface_not_derived_verb")
    else:
        special = _template_special_route(source_row, surface)
        if special:
            record = _build_unresolved(source_row, special[0], blocker_id=special[1])
        else:
            entry_map = _entry_map(entries)
            expected_entry_id = str(source_row.get("entry_id")) if source_row.get("entry_id") else None
            matches, orthography_near_miss, near_matches = fam4._entry_matches(surface, entry_map, expected_entry_id)
            owner_marker = source_row.get("owner_marker") or source_row.get("fam4_owner_marker")
            carrier_radicals = fam4._root_radicals(matches[0]["entry"]) if len(matches) == 1 else fam4._root_hint(source_row)
            carrier_marker = fam4._owner_gate_route(surface, carrier_radicals, carrier_affixes)
            if not owner_marker:
                owner_marker = carrier_marker
            if source_row.get("fam4_route") == "owner_gated" and not owner_marker:
                owner_marker = "derived_form_owner_registry"
            if len(matches) > 1:
                record = _build_unresolved(source_row, "entry_join_ambiguity", blocker_id="fam5.entry_join_ambiguity")
            elif not matches:
                if owner_marker:
                    record = _build_unresolved(source_row, "owner_gated", near_match=near_matches[0] if near_matches else None, blocker_id="fam5.owner_gated")
                else:
                    route = "orthography_mismatch" if orthography_near_miss else "source_gap"
                    if route == "orthography_mismatch":
                        route = "source_gap"
                    record = _build_unresolved(source_row, route, near_match=near_matches[0] if near_matches else None, blocker_id="fam5.source_gap")
            else:
                match = matches[0]
                entry = match["entry"]
                radicals = fam4._root_radicals(entry)
                if str(entry.get("section") or "verb") != "verb":
                    record = _build_unresolved(source_row, "surface_not_derived_verb", match=match, blocker_id="fam5.surface_not_derived_verb")
                elif len(radicals) == 4 and source_row.get("force_triliteral"):
                    record = _build_unresolved(source_row, "template_unresolved", match=match, blocker_id="fam5.quadriliteral_not_triliteral")
                elif fam4._weak_defeater(radicals, surface, carrier_weak_registry) and not source_row.get("weak_letter_operations"):
                    record = _build_unresolved(source_row, "weak_root_pattern_unresolved", match=match, blocker_id="fam5.weak_root_pattern_unresolved")
                else:
                    match_info: dict[str, Any] | None = None
                    for pattern in registry:
                        candidate = _match_pattern(surface, radicals, pattern, source_row)
                        if candidate:
                            match_info = candidate
                            break
                    if match_info is None:
                        if surface.startswith("ا") and "جْت" in surface:
                            blocker = "fam5.hamzat_al_wasl_unresolved"
                        elif "ٱصْط" in surface:
                            blocker = "fam5.assimilation_unresolved"
                        else:
                            blocker = "fam5.template_unresolved"
                        record = _build_unresolved(source_row, "template_unresolved", match=match, blocker_id=blocker)
                    else:
                        record = _build_candidate(source_row, match, match_info)
    errors = validate_derived_verb_record(record)
    if errors:
        raise ValueError(f"generated FAM5 record failed validation for {loc}: " + "; ".join(errors))
    return record


def validate_derived_verb_record(record: Mapping[str, Any]) -> list[str]:
    errors = list(validate_contract_record(dict(record)))
    if errors:
        return errors
    projection = record["projection"]
    facts = record["facts"]
    derived = [fact for fact in facts if fact.get("fact_type") == "derived_verb_evidence"]
    base = [fact for fact in facts if fact.get("fact_type") == "entry_form_attestation"]
    pending = [fact for fact in facts if fact.get("fact_type") == "derived_verb_pending"]
    payload = projection.get("public_payload") or {}
    if projection["status"] == "candidate":
        if len(derived) != 1 or len(base) != 1 or pending:
            errors.append("candidate FAM5 record must contain one entry attestation and one derived_verb_evidence fact")
        if derived:
            value = derived[0].get("fact_value") or {}
            template = value.get("template") or {}
            proof = value.get("reconstruction_proof") or {}
            if template.get("form") not in SUPPORTED_FORMS:
                errors.append("FAM5 candidate uses an unregistered form")
            if proof.get("passed") is not True:
                errors.append("FAM5 reconstruction proof did not pass")
            ownership = value.get("letter_ownership") or []
            surface = record["canonical_occurrence"]["surface"]
            tokens = fam4._tokens(surface)
            indices = [item.get("base_letter_index") for item in ownership]
            if len(ownership) != len(tokens) or indices != list(range(len(tokens))) or not all(item.get("owner_class") for item in ownership):
                errors.append("FAM5 letter ownership is not total and unique")
            if proof.get("each_written_base_letter_exactly_one_class") is not True or proof.get("base_letter_indices_complete") is not True:
                errors.append("FAM5 reconstruction proof lacks exact base-letter ownership")
            if template.get("form") == "quadriliteral" and len(template.get("root_radicals") or []) != 4:
                errors.append("FAM5 quadriliteral candidate lacks four typed root radicals")
            if template.get("form") == "VIII":
                gemination = value.get("gemination") or {}
                if gemination.get("treatment") != "C_shared_written_letter" or gemination.get("split_authorized") is not False:
                    errors.append("FAM5 Form-VIII gemination lacks Treatment-C shared-letter discipline")
                if sum(1 for segment in value.get("surface_segments", []) if segment.get("letter") == "ث") != 1:
                    errors.append("FAM5 Form-VIII geminated letter was naively split")
                if (value.get("hamzat_al_wasl") or {}).get("class") != "hamzat_al_wasl":
                    errors.append("FAM5 Form-VIII hamzat al-wasl is not governed")
            if template.get("form") == "IV":
                additions = value.get("derivational_additions") or []
                if not any(item.get("marker_class") == "derivative_prefix_form_iv_hamza" and item.get("class") == "derivative_prefix" for item in additions):
                    errors.append("FAM5 Form-IV prefix lacks its D-3 derivational class")
            if template.get("form") == "VIII":
                additions = value.get("derivational_additions") or []
                if not any(item.get("marker_class") == "derivative_infix_form_viii_t" and item.get("class") == "derivative_infix" for item in additions):
                    errors.append("FAM5 Form-VIII infix lacks its D-3 derivational class")
            if base and base[0]["fact_id"] not in derived[0].get("dependencies", {}).get("fact_ids", []):
                errors.append("FAM5 derived fact does not depend on entry attestation")
            if derived[0].get("evidence_mode") != "deterministic_derivation_from_certified_facts":
                errors.append("FAM5 derived fact lacks deterministic derivation evidence mode")
        if payload.get("authorization_state") != "pre_apply_not_authorized":
            errors.append("FAM5 candidate is not pre_apply_not_authorized")
        if payload.get("public_materialization_allowed") is not False or payload.get("live_mutation_allowed") is not False:
            errors.append("FAM5 candidate enables mutation")
        learner = payload.get("learner_copy") or {}
        if learner.get("n_lang_clean") is not True:
            errors.append("FAM5 learner copy is not N-LANG clean")
        if not str(learner.get("sarf", "")).startswith(N_LANG_SARF):
            errors.append("FAM5 learner copy lacks public Ṣarf label")
        if not str(learner.get("nahw", "")).startswith(N_LANG_NAHW):
            errors.append("FAM5 learner copy lacks public Naḥw label")
    else:
        if derived or base or len(pending) != 1:
            errors.append("unresolved FAM5 record must contain exactly one derived_verb_pending fact")
        if projection.get("claim") is not None:
            errors.append("unresolved FAM5 record carries a linguistic claim")
        if pending:
            route = (pending[0].get("fact_value") or {}).get("route")
            if not route or payload.get("route") != route:
                errors.append("unresolved FAM5 route is not preserved in public payload")
            value = pending[0].get("fact_value") or {}
            observed = value.get("letter_ownership") or []
            tokens = fam4._tokens(record["canonical_occurrence"]["surface"])
            if len(observed) != len(tokens) or [item.get("base_letter_index") for item in observed] != list(range(len(tokens))):
                errors.append("unresolved FAM5 fact does not preserve all observed base letters")
        if not any(fact.get("unresolved_blockers") for fact in facts):
            errors.append("unresolved FAM5 record lacks a typed blocker")
        if payload.get("authorization_state") != "pre_apply_not_authorized":
            errors.append("unresolved FAM5 record is not pre_apply_not_authorized")
        if payload.get("public_materialization_allowed") is not False or payload.get("live_mutation_allowed") is not False:
            errors.append("unresolved FAM5 record enables mutation")
    return errors


def _merge_verdicts(rows: Sequence[Mapping[str, Any]], verdicts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_loc = {str(item.get("loc") or item.get("quran_loc") or "").removeprefix("quran:"): item for item in verdicts}
    merged: list[dict[str, Any]] = []
    for row in rows:
        if row.get("morphology_family") != "derived_verbs":
            continue
        item = copy.deepcopy(dict(row))
        loc = _loc(item)
        item["loc"] = loc
        item["quran_loc"] = loc
        verdict = by_loc.get(loc)
        if verdict:
            item["_v575_verdict"] = verdict.get("verdict")
            item["v575_source_address"] = f"v575-verdict:{loc}"
        item["template_hypothesis"] = {
            "3:141:4": "derived.form_iv.perfect_active.3mp",
            "42:20:3": "derived.form_iv.imperfect_active.3ms.weak_middle",
            "42:20:12": "derived.form_iv.imperfect_active.3ms.weak_middle",
        }.get(loc)
        merged.append(item)
    return merged


def select_working_rows(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    fam4_rows: Sequence[Mapping[str, Any]],
    whitelist_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge the three STRAT rows with the four FAM4 owner-gated rows."""

    rows = _merge_verdicts(strat_rows, verdict_rows)
    for record in fam4_rows:
        occurrence = record.get("canonical_occurrence") or {}
        loc = str(occurrence.get("quran_loc") or "")
        if loc not in FAM4_DERIVED_LOCS:
            continue
        surface = str(occurrence.get("surface") or "")
        pending = next((fact for fact in record.get("facts", []) if fact.get("fact_type") == "finite_verb_pending"), None)
        candidate = next((fact for fact in record.get("facts", []) if fact.get("fact_type") == "finite_verb_evidence"), None)
        value = (pending or candidate or {}).get("fact_value") or {}
        entry_context = value.get("entry_context") or {}
        template = (candidate or {}).get("fact_value", {}).get("pattern_id") if candidate else None
        if not template:
            template = {
                "derivative_form_ii_shadda": "derived.form_ii.imperfect_active.3ms.energic",
                "derivative_prefix_form_iv_hamza": "derived.form_iv.perfect_active.1cs",
                "quadriliteral_root": "quadriliteral.perfect_active.3ms",
                "derivative_infix_form_viii_t": "derived.form_viii.perfect_passive.3fs",
            }.get(value.get("owner_marker"), value.get("observed_sub_shape"))
        row = {
            "loc": loc,
            "quran_loc": loc,
            "surface": surface,
            "part_of_speech": "verb",
            "morphology_family": "derived_verbs",
            "_v575_verdict": "verified",
            "v575_source_address": f"v575-verdict:{loc}",
            "source_packet": "fam4-derived-form-routing",
            "fam4_route": value.get("route") or "candidate",
            "owner_marker": value.get("owner_marker"),
            "whitelist_entry_id": value.get("whitelist_entry_id"),
            "entry_id": value.get("entry_id") or entry_context.get("entry_id") or occurrence.get("entry_id"),
            "template_hypothesis": template or value.get("observed_sub_shape"),
            "source_grounding": "entry_form_attestation" if candidate or entry_context.get("entry_id") else "fam4_owner_packet",
        }
        rows.append(row)
    whitelist_by_loc = {str(item.get("loc") or item.get("quran_loc") or "").removeprefix("quran:"): item for item in (whitelist_rows or [])}
    for row in rows:
        edge = whitelist_by_loc.get(row["loc"])
        if edge and not row.get("whitelist_entry_id"):
            row["whitelist_entry_id"] = edge.get("entry_id") or edge.get("id")
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique[_loc(row)] = row
    selected = [unique[loc] for loc in sorted(unique)]
    if len(selected) != 7:
        raise ValueError(f"FAM5 working set must contain exactly seven rows, got {len(selected)}")
    return selected


def _form_class(row: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    derived = next((fact for fact in record.get("facts", []) if fact.get("fact_type") == "derived_verb_evidence"), None)
    if derived:
        return str((derived.get("fact_value") or {}).get("template", {}).get("form") or "unknown")
    value = next((fact.get("fact_value") or {} for fact in record.get("facts", []) if fact.get("fact_type") == "derived_verb_pending"), {})
    hypothesis = str(value.get("template_hypothesis") or value.get("observed_sub_shape") or row.get("template_hypothesis") or "unknown")
    if "quadriliteral" in hypothesis:
        return "quadriliteral"
    if "viii" in hypothesis.lower() or "form_viii" in hypothesis.lower():
        return "VIII"
    if "ii" in hypothesis.lower() or "form_ii" in hypothesis.lower():
        return "II"
    if "iv" in hypothesis.lower() or "form_iv" in hypothesis.lower():
        return "IV"
    return "unknown"


def build_calibration_packet(
    rows: Sequence[Mapping[str, Any]],
    *,
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    form_registry: Sequence[Mapping[str, Any]] | Path | str | None = None,
) -> dict[str, Any]:
    registry = load_derived_form_registry(form_registry)
    records = [produce_record(row, entries=entries, form_registry=registry) for row in rows]
    by_form: dict[str, Counter[str]] = defaultdict(Counter)
    row_outcomes: list[dict[str, Any]] = []
    for row, record in zip(rows, records):
        status = str(record["projection"]["status"])
        form = _form_class(row, record)
        by_form[form]["population"] += 1
        by_form[form]["candidate"] += int(status == "candidate")
        by_form[form]["abstention"] += int(status != "candidate")
        pending = next((fact for fact in record["facts"] if fact.get("fact_type") == "derived_verb_pending"), None)
        candidate = next((fact for fact in record["facts"] if fact.get("fact_type") == "derived_verb_evidence"), None)
        row_outcomes.append({
            "loc": _loc(row),
            "surface": row.get("surface"),
            "form_class": form,
            "status": status,
            "route": (pending or {}).get("fact_value", {}).get("route") if pending else "entry_backed_derived_form_pattern",
            "pattern_id": (candidate or {}).get("fact_value", {}).get("template", {}).get("pattern_id") if candidate else None,
            "entry_id": (candidate or {}).get("fact_value", {}).get("entry_id") if candidate else (pending or {}).get("fact_value", {}).get("entry_context", {}).get("entry_id"),
            "source_addresses": next(iter(record["facts"]), {}).get("source_evidence", {}).get("source_addresses", []),
            "blockers": [blocker for fact in record["facts"] for blocker in fact.get("unresolved_blockers", [])],
            "template_hypothesis": row.get("template_hypothesis") or row.get("label_claim"),
        })
    total = len(records)
    candidates = sum(record["projection"]["status"] == "candidate" for record in records)
    return {
        "producer": {"id": PRODUCER_ID, "version": VERSION, "projector_id": PROJECTOR_ID},
        "mode": "candidate_only",
        "authorization_state": "pre_apply_not_authorized",
        "working_set_count": total,
        "candidate_count": candidates,
        "abstention_count": total - candidates,
        "abstention_rate": (total - candidates) / total if total else 1.0,
        "forms": {form: dict(counter) for form, counter in sorted(by_form.items())},
        "source_survey": [
            {"loc": _loc(row), "surface": row.get("surface"), "letters": [{"letter": token["letter"], "marks": token["marks"], "start": token["start"], "end": token["end"]} for token in _tokens(str(row.get("surface") or ""))], "template_hypothesis": row.get("template_hypothesis") or row.get("label_claim"), "source_situation": row.get("source_grounding") or row.get("entry_evidence_availability") or "not_recorded"}
            for row in rows
        ],
        "row_outcomes": row_outcomes,
        "records": records,
    }


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_calibration_packet(packet: Mapping[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = list(packet["records"])
    candidate_records = [record for record in records if record["projection"]["status"] == "candidate"]
    unresolved_records = [record for record in records if record["projection"]["status"] != "candidate"]
    paths = {
        "sample": output_dir / "calibration-sample.jsonl",
        "facts": output_dir / "derived-verb-facts.jsonl",
        "unresolved": output_dir / "unresolved-records.jsonl",
        "summary": output_dir / "calibration-summary.json",
    }
    write_jsonl(paths["sample"], records)
    write_jsonl(paths["facts"], [fact for record in candidate_records for fact in record["facts"] if fact.get("fact_type") in {"entry_form_attestation", "derived_verb_evidence"}])
    write_jsonl(paths["unresolved"], unresolved_records)
    with paths["summary"].open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({key: value for key, value in packet.items() if key != "records"}, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return paths


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stratified", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--fam4-packet", type=Path, default=DEFAULT_FAM4_PACKET)
    parser.add_argument("--whitelist", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    rows = select_working_rows(_jsonl(args.stratified), _jsonl(args.verdicts), _jsonl(args.fam4_packet), _jsonl(args.whitelist) if args.whitelist else None)
    packet = build_calibration_packet(rows, entries=_jsonl(args.entries), form_registry=args.registry)
    paths = write_calibration_packet(packet, args.output_dir)
    print(json.dumps({"working_set_count": packet["working_set_count"], "candidate_count": packet["candidate_count"], "abstention_count": packet["abstention_count"], "paths": {key: str(value) for key, value in paths.items()}}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
