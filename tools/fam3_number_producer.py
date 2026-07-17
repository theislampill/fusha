"""Candidate-only formation producer for the stratified number-word family.

The producer is intentionally conservative. A number label is never evidence:
the observed surface must join to the caller-supplied whitelist entry and the
same entry must expose a base that a registered number rule can reconstruct.
Missing, ambiguous, or orthographically unsafe joins become typed unresolved
records instead of claims.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fam2_lexical_producer as fam2
from tools.build_entry_card_word_ledger import WhitelistIndex
from tools.typed_claim_contract import learner_statement_for, validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATTERN_REGISTRY = ROOT / "qamus" / "examples" / "fam3-numbers" / "pattern-registry.jsonl"
PROJECTOR_ID = "sarf.fam3.number_formation.v1"
PRODUCER_ID = "tools.fam3_number_producer"
VERSION = "1.0.0"
SCHEMA = "qamus.typed_claim_contract.v1"
CALIBRATION_ARTIFACT = "qamus/examples/fam3-numbers/calibration-sample.jsonl"
UNRESOLVED_ARTIFACT = "qamus/examples/fam3-numbers/unresolved-records.jsonl"

NUMBER_SUBSHAPES = {
    "bare_cardinal",
    "gender_polarity_cardinal",
    "ordinals",
    "compound_11_19",
    "tens",
    "fractions",
    "first_last_edge",
    "other_number_form",
    "unclassified",
}

PROJECTION_STATUS = {
    "entry_lookup_missing": "source_gap",
    "source_gap": "source_gap",
    "orthography_mismatch": "blocked",
    "homograph_ambiguity": "blocked",
    "gender_polarity_mismatch": "blocked",
    "counted_noun_evidence_missing": "source_gap",
    "compound_context_missing": "source_gap",
    "pattern_unresolved": "producer_pending",
    "surface_not_number_word": "producer_pending",
    "unsupported_number_shape": "producer_pending",
}

_NUMBER_LETTERS = {
    "أحد",
    "واحد",
    "إحدى",
    "اثنان",
    "اثنين",
    "اثنا",
    "اثنتا",
    "اثنتين",
    "مثنى",
    "ثلاث",
    "ثلاثة",
    "ثلاثون",
    "أربع",
    "أربعة",
    "أربعين",
    "خمس",
    "خمسة",
    "خمسين",
    "ست",
    "ستة",
    "ستين",
    "سبع",
    "سبعة",
    "سبعين",
    "ثمان",
    "ثماني",
    "ثمانى",
    "ثمانية",
    "ثمانين",
    "تسع",
    "تسعة",
    "تسعين",
    "عشر",
    "عشرة",
    "عشرين",
    "ألف",
    "ألوف",
    "آلاف",
    "ألفين",
    "مائة",
    "مائتين",
    "مئتين",
    "ثاني",
    "ثانى",
    "ثالث",
    "رابع",
    "خامس",
    "سادس",
    "سابع",
    "ثامن",
    "تاسع",
    "عاشر",
    "أول",
    "آخر",
    "اخر",
    "نصف",
    "ثلث",
    "ثلثي",
    "ربع",
    "سدس",
    "ثمن",
}
_TENS_PREFIXES = ("ثلاث", "أربع", "خمس", "ست", "سبع", "ثمان", "تسع", "عشر")
_ORDINAL_LETTERS = {
    "أول",
    "آخر",
    "اخر",
    "ثاني",
    "ثانى",
    "ثالث",
    "رابع",
    "خامس",
    "سادس",
    "سابع",
    "ثامن",
    "تاسع",
    "عاشر",
}
_FRACTION_LETTERS = {"نصف", "ثلث", "ثلثي", "ربع", "سدس", "ثمن"}
_NUMBER_ORTHO_ALIASES = {
    "ثمنى": "ثماني",
    "ثمنين": "ثمانين",
    "ثلثون": "ثلاثون",
    "ثنتين": "اثنتين",
    "ثنين": "اثنين",
}
_ORDINAL_PAIRS = {
    ("اثنان", "ثاني"),
    ("ثلاث", "ثالث"),
    ("أربع", "رابع"),
    ("خمس", "خامس"),
    ("ست", "سادس"),
    ("سبع", "سابع"),
    ("ثمان", "ثامن"),
    ("تسع", "تاسع"),
    ("عشر", "عاشر"),
}
_PAIRWISE_PAIRS = {( "اثنان", "مثنى")}
_ALLOWED_RELATIONS = {"exact", "article_structural", "article_assimilation"}
_HOMOGRAPH_FLAGS = {
    "entry_join_multiple_entries",
    "homograph",
    "noun_adjective_ambiguity",
    "number_noun_homograph",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return fam2._read_jsonl(Path(path))


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _registry_records(registry: Any = None) -> list[dict[str, Any]]:
    if registry is None:
        return load_pattern_registry()
    if isinstance(registry, (str, Path)):
        return load_pattern_registry(Path(registry))
    if isinstance(registry, Sequence) and not isinstance(registry, (str, bytes)):
        return [dict(row) for row in registry if isinstance(row, Mapping)]
    raise TypeError("number pattern registry must be a path or a sequence of registry objects")


def load_pattern_registry(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(path or DEFAULT_PATTERN_REGISTRY)
    seen: set[str] = set()
    allowed_policies = {
        "exact_written_pair",
        "exact_stem_and_suffix",
        "named_ta_marbuta_rule_only",
        "exact_base_and_suffix",
    }
    required = {"pattern_id", "sub_shape", "pair_name", "matcher", "orthography_policy"}
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"FAM3 number pattern lacks fields: {sorted(missing)}")
        pattern_id = row["pattern_id"]
        if not isinstance(pattern_id, str) or not pattern_id or pattern_id in seen:
            raise ValueError(f"invalid or duplicate FAM3 number pattern id: {pattern_id!r}")
        seen.add(pattern_id)
        if row["sub_shape"] not in NUMBER_SUBSHAPES:
            raise ValueError(f"unsupported FAM3 number pattern sub-shape: {pattern_id}")
        if row["orthography_policy"] not in allowed_policies:
            raise ValueError(f"FAM3 number pattern lacks a defensive orthography policy: {pattern_id}")
    return rows


def _pattern_by_id(pattern_id: str, registry: Any = None) -> dict[str, Any] | None:
    return next((row for row in _registry_records(registry) if row.get("pattern_id") == pattern_id), None)


def _loc(row: Mapping[str, Any]) -> str:
    value = str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:")
    if not re.fullmatch(r"[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}", value):
        raise ValueError(f"invalid FAM3 Quran location: {value!r}")
    return value


def _surface(row: Mapping[str, Any]) -> str:
    return str(row.get("surface") or "")


def _letters(value: str) -> str:
    return fam2._letters(value)


def _shape_letters(value: str) -> str:
    """Classify Qurʾānic orthographic carriers without changing evidence."""

    letters = _letters(value).replace("ٱ", "ا")
    return _NUMBER_ORTHO_ALIASES.get(letters, letters)


def _entry_evidence_rows(entry: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return headword, sense, and form addresses without importing gloss text."""

    rows = list(fam2._form_rows(entry))
    entry_id = str(entry.get("id") or entry.get("entry_id") or "")
    for sense_index, sense in enumerate(entry.get("senses") or []):
        if not isinstance(sense, Mapping):
            continue
        surface = sense.get("ar")
        if isinstance(surface, str) and surface:
            rows.append({
                "surface": surface,
                "address": f"entry:{entry_id}:senses[{sense_index}].ar",
            })
    return rows


def _entry_map(entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return fam2._entry_map(entries)


def _entry_surface_matches(entry: Mapping[str, Any], target: str) -> tuple[list[dict[str, str]], bool]:
    direct: list[dict[str, str]] = []
    orthography_near_miss = False
    for form in _entry_evidence_rows(entry):
        relation = fam2._surface_relation(target, form["surface"], allow_assimilation=False)
        if relation in _ALLOWED_RELATIONS:
            item = dict(form)
            item["relation"] = relation
            direct.append(item)
        elif relation == "orthography_mismatch":
            orthography_near_miss = True
        elif _shape_letters(target) == _shape_letters(form["surface"]) and _letters(target) != _letters(form["surface"]):
            orthography_near_miss = True
    return direct, orthography_near_miss


def _base_surface(entry: Mapping[str, Any], target: str) -> tuple[str, str] | None:
    entry_id = str(entry.get("id") or entry.get("entry_id") or "")
    headword = entry.get("headword")
    if isinstance(headword, str) and headword.strip():
        parts = [part.strip() for part in headword.split("/") if part.strip()]
        if parts:
            for part in parts:
                if fam2._surface_relation(target, part) in _ALLOWED_RELATIONS:
                    return part, f"entry:{entry_id}:headword"
            return parts[0], f"entry:{entry_id}:headword"
    for sense_index, sense in enumerate(entry.get("senses") or []):
        if isinstance(sense, Mapping) and isinstance(sense.get("ar"), str) and sense["ar"]:
            return sense["ar"], f"entry:{entry_id}:senses[{sense_index}].ar"
    return None


def _numberish(surface: str) -> bool:
    letters = _shape_letters(surface)
    return letters in _NUMBER_LETTERS


def _context_rows(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = row.get("context_rows") or row.get("_context_rows") or []
    return [dict(value) for value in values if isinstance(value, Mapping)]


def _loc_parts(loc: str) -> tuple[int, int, int] | None:
    try:
        return tuple(int(part) for part in loc.split(":"))  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def _adjacent_context(row: Mapping[str, Any], *, predicate) -> list[dict[str, Any]]:
    target = _loc_parts(_loc(row))
    if target is None:
        return []
    result = []
    for context in _context_rows(row):
        context_loc = str(context.get("loc") or context.get("quran_loc") or "").removeprefix("quran:")
        parts = _loc_parts(context_loc)
        if parts is None or parts[:2] != target[:2] or abs(parts[2] - target[2]) != 1:
            continue
        if predicate(context):
            result.append(context)
    return result


def _ashar_component(surface: str) -> bool:
    return _shape_letters(surface) in {"عشر", "عشرة"}


def _single_digit_component(surface: str) -> bool:
    return _shape_letters(surface) in {
        "أحد",
        "اثنا",
        "اثني",
        "اثنتا",
        "اثنتي",
        "ثلاث",
        "ثلاثة",
        "أربع",
        "أربعة",
        "خمس",
        "خمسة",
        "ست",
        "ستة",
        "سبع",
        "سبعة",
        "ثمان",
        "ثماني",
        "ثمانية",
        "تسع",
        "تسعة",
    }


def _compound_partner(row: Mapping[str, Any]) -> dict[str, Any] | None:
    target = _surface(row)
    if _ashar_component(target):
        matches = _adjacent_context(row, predicate=lambda item: _single_digit_component(str(item.get("surface") or "")))
    elif _single_digit_component(target):
        matches = _adjacent_context(row, predicate=lambda item: _ashar_component(str(item.get("surface") or "")))
    else:
        matches = []
    return matches[0] if len(matches) == 1 else None


def _counted_noun_context(row: Mapping[str, Any]) -> dict[str, Any] | None:
    explicit = row.get("counted_noun")
    if isinstance(explicit, Mapping):
        return dict(explicit)
    matches = _adjacent_context(
        row,
        predicate=lambda item: item.get("role") == "counted_noun" or item.get("counted_noun_gender") in {"masculine", "feminine"},
    )
    return matches[0] if len(matches) == 1 else None


def classify_sub_shape(row: Mapping[str, Any]) -> str:
    """Classify from the written form and local context, never from a label."""

    surface = _surface(row)
    letters = _shape_letters(surface)
    if not _numberish(surface):
        return "unclassified"
    if letters in _FRACTION_LETTERS:
        return "fractions"
    if letters in {"أول", "آخر", "اخر"}:
        return "first_last_edge"
    if letters in _ORDINAL_LETTERS:
        return "ordinals"
    if _compound_partner(row) is not None:
        return "compound_11_19"
    if letters.endswith(("ون", "ين")) and any(letters.startswith(prefix) for prefix in _TENS_PREFIXES):
        return "tens"
    if letters in {"ثماني"}:
        return "gender_polarity_cardinal"
    if letters.endswith("ة") and letters[:-1] in {
        "ثلاث",
        "أربع",
        "خمس",
        "ست",
        "سبع",
        "ثماني",
        "تسع",
        "عشر",
    }:
        return "gender_polarity_cardinal"
    if letters in {"مثنى", "ألوف", "آلاف", "ألفين", "مائة", "مائتين", "مئتين", "اثنتين", "اثنين"}:
        return "other_number_form"
    return "bare_cardinal"


def _gender_polarity_status(row: Mapping[str, Any], base_surface: str, target: str) -> str | None:
    context = _counted_noun_context(row)
    if context is None:
        return "counted_noun_evidence_missing"
    counted_gender = context.get("counted_noun_gender")
    if counted_gender not in {"masculine", "feminine"}:
        return "counted_noun_evidence_missing"
    target_gender = "feminine" if _shape_letters(target).endswith("ة") else "masculine"
    expected_gender = "feminine" if counted_gender == "masculine" else "masculine"
    return None if target_gender == expected_gender else "gender_polarity_mismatch"


def _pattern_match_result(
    base_surface: str,
    observed_surface: str,
    pattern: Mapping[str, Any],
    *,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    base_letters = _letters(base_surface)
    observed_letters = _letters(observed_surface)
    matcher = str(pattern.get("matcher") or "")
    if matcher == "base_exact":
        if fam2._surface_relation(observed_surface, base_surface) not in _ALLOWED_RELATIONS:
            return None
    elif matcher == "base_plus_ta_marbuta":
        if observed_letters != base_letters + "ة":
            return None
    elif matcher == "explicit_ordinal_pair":
        if (base_letters, observed_letters) not in _ORDINAL_PAIRS:
            return None
    elif matcher == "adjacent_cardinal_ashar":
        partner = (context or {}).get("compound_partner")
        if not isinstance(partner, Mapping):
            return None
        partner_letters = _letters(str(partner.get("surface") or ""))
        if _ashar_component(observed_surface) and not _single_digit_component(str(partner.get("surface") or "")):
            return None
        if _single_digit_component(observed_surface) and not _ashar_component(str(partner.get("surface") or "")):
            return None
        if partner_letters == observed_letters:
            return None
    elif matcher == "suffix_tens_exact_entry_form":
        if not observed_letters.endswith(("ون", "ين")) or observed_letters[:-2] != base_letters:
            return None
    elif matcher == "explicit_pairwise_form":
        if (base_letters, observed_letters) not in _PAIRWISE_PAIRS:
            return None
    elif matcher == "exact_entry_variant":
        if not bool((context or {}).get("entry_direct")) or observed_letters == base_letters:
            return None
    else:
        return None
    return {
        "pattern_id": str(pattern["pattern_id"]),
        "sub_shape": str(pattern["sub_shape"]),
        "pair_name": str(pattern["pair_name"]),
        "base_pattern": str(pattern.get("base_pattern") or "entry-backed base"),
        "surface_pattern": str(pattern.get("surface_pattern") or "registered number form"),
        "base_surface": fam2._strip_case(base_surface),
        "observed_surface": fam2._strip_case(observed_surface),
        "matcher": matcher,
        "registry_version": str(pattern.get("version") or VERSION),
    }


def match_registered_number_pattern(
    base_surface: str,
    observed_surface: str,
    pattern_id: str,
    context: Mapping[str, Any] | None = None,
    registry: Any = None,
) -> dict[str, Any] | None:
    pattern = _pattern_by_id(pattern_id, registry)
    if pattern is None:
        return None
    return _pattern_match_result(base_surface, observed_surface, pattern, context=context)


def _pattern_ids_for_shape(sub_shape: str, registry: Sequence[Mapping[str, Any]]) -> list[str]:
    return [str(row["pattern_id"]) for row in registry if row.get("sub_shape") == sub_shape]


def _safe_joined_entry_id(row: Mapping[str, Any]) -> str | None:
    candidates = row.get("_joined_entry_ids") or row.get("entry_candidate_ids") or []
    if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)):
        values = sorted({str(value) for value in candidates if value})
        if len(values) == 1:
            return values[0]
        if len(values) > 1:
            return None
    value = row.get("_joined_entry_id") or row.get("entry_id")
    return str(value) if value else None


def _has_ambiguity(row: Mapping[str, Any]) -> bool:
    if isinstance(row.get("ambiguity"), Mapping):
        return True
    flags = row.get("ambiguity_flags") or []
    return any(str(flag) in _HOMOGRAPH_FLAGS for flag in flags)


def _context_source_addresses(loc: str, row: Mapping[str, Any]) -> list[dict[str, str]]:
    addresses = [{"address": f"whitelist:loc={loc}", "source_kind": "corpus_record"}]
    for context in _context_rows(row):
        context_loc = str(context.get("loc") or context.get("quran_loc") or "").removeprefix("quran:")
        if re.fullmatch(r"\d{1,3}:\d{1,3}:\d{1,3}", context_loc):
            addresses.append({"address": f"quran:{context_loc}", "source_kind": "quran_token"})
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for address in addresses:
        unique[(address["address"], address["source_kind"])] = address
    return list(unique.values())


def _source_addresses(loc: str, entry_id: str, match: Mapping[str, Any], row: Mapping[str, Any]) -> list[dict[str, str]]:
    addresses = [
        {"address": f"quran:{loc}", "source_kind": "quran_token"},
        *_context_source_addresses(loc, row),
        {"address": f"entry:{entry_id}:headword", "source_kind": "qamus_entry_field"},
        {"address": str(match["matched_address"]), "source_kind": "qamus_entry_field"},
        {"address": str(match["base_address"]), "source_kind": "qamus_entry_field"},
        {"address": f"registry:fam3-numbers:pattern:{match['pattern_id']}", "source_kind": "review_artifact"},
    ]
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for address in addresses:
        unique[(address["address"], address["source_kind"])] = address
    return list(unique.values())


def _span(surface: str) -> dict[str, Any]:
    return fam2._span(surface)


def _relabel_fact(fact: dict[str, Any], *, source_record_id: str) -> dict[str, Any]:
    fact["ownership"]["primary"] = {"owner_id": "fam3-number-formation", "owner_type": "producer"}
    fact["ownership"]["secondary"] = [
        {"owner_id": "qamus-entry-source", "owner_type": "source_owner"},
        {"owner_id": "sarf-number-pattern-registry", "owner_type": "rule_owner"},
        {"owner_id": "vnmap-context-join", "owner_type": "join_owner"},
    ]
    fact["producer"] = {"id": PRODUCER_ID, "version": VERSION}
    fact["rule_projector"]["projector_id"] = PROJECTOR_ID
    fact["rule_projector"]["version"] = VERSION
    structured = fact.get("source_evidence", {}).get("structured_source_fact")
    if isinstance(structured, dict):
        structured["source_record_id"] = source_record_id
    return fact


def _base_fact(
    *,
    fact_id: str,
    fact_type: str,
    value: dict[str, Any],
    surface: str,
    source: dict[str, str],
    source_address: dict[str, str],
    source_addresses: list[dict[str, str]],
    evidence_mode: str,
    certification: dict[str, str],
    evidence: dict[str, Any],
    rule_id: str,
    projection_id: str,
    guards: list[dict[str, str]],
    defeaters: list[dict[str, Any]],
    unresolved_blockers: list[dict[str, str]],
    dependencies: dict[str, Any],
    derivation_chain: list[dict[str, Any]],
    dependent_fact_ids: list[str],
) -> dict[str, Any]:
    fact = fam2._base_fact(
        fact_id=fact_id,
        fact_type=fact_type,
        value=value,
        surface=surface,
        source=source,
        source_address=source_address,
        source_addresses=source_addresses,
        evidence_mode=evidence_mode,
        certification=certification,
        evidence=evidence,
        rule_id=rule_id,
        projection_id=projection_id,
        guards=guards,
        defeaters=defeaters,
        unresolved_blockers=unresolved_blockers,
        dependencies=dependencies,
        derivation_chain=derivation_chain,
        dependent_fact_ids=dependent_fact_ids,
    )
    return _relabel_fact(fact, source_record_id=f"fam3:occurrence:{value['occurrence']['loc']}")


def _resolve_match(
    row: Mapping[str, Any],
    entries: Mapping[str, Mapping[str, Any]],
    registry: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str, str]:
    sub_shape = classify_sub_shape(row)
    if _has_ambiguity(row) or len(row.get("entry_candidate_ids") or []) > 1:
        return None, "homograph_ambiguity", sub_shape
    if sub_shape == "unclassified":
        return None, "surface_not_number_word", sub_shape
    entry_id = _safe_joined_entry_id(row)
    if not entry_id:
        return None, "entry_lookup_missing", sub_shape
    entry = entries.get(entry_id)
    if entry is None:
        return None, "entry_lookup_missing", sub_shape
    target = _surface(row)
    evidence_rows, orthography_near_miss = _entry_surface_matches(entry, target)
    if not evidence_rows:
        if orthography_near_miss:
            return None, "orthography_mismatch", sub_shape
        if not _entry_evidence_rows(entry):
            return None, "source_gap", sub_shape
        return None, "entry_lookup_missing", sub_shape
    base = _base_surface(entry, target)
    if base is None:
        return None, "source_gap", sub_shape
    matched = next((item for item in evidence_rows if item.get("relation") == "exact"), evidence_rows[0])
    if sub_shape == "gender_polarity_cardinal":
        gender_status = _gender_polarity_status(row, base[0], target)
        if gender_status:
            return None, gender_status, sub_shape
    partner = _compound_partner(row)
    if sub_shape == "compound_11_19" and partner is None:
        return None, "compound_context_missing", sub_shape
    pattern_context: dict[str, Any] = {
        "entry_direct": True,
        "compound_partner": partner,
    }
    if partner is not None:
        partner_entry_id = str(partner.get("entry_id") or "")
        partner_entry = entries.get(partner_entry_id)
        partner_matches = _entry_surface_matches(partner_entry, str(partner.get("surface") or "")) if partner_entry else ([], False)
        if not partner_matches[0]:
            return None, "entry_lookup_missing", sub_shape
        pattern_context["compound_partner_source_address"] = partner_matches[0][0]["address"]
    for pattern_id in _pattern_ids_for_shape(sub_shape, registry):
        pattern = _pattern_by_id(pattern_id, registry)
        if pattern is None:
            continue
        pattern_match = _pattern_match_result(base[0], target, pattern, context=pattern_context)
        if pattern_match is not None:
            pattern_match.update({
                "entry_id": entry_id,
                "matched_surface": matched["surface"],
                "matched_address": matched["address"],
                "matched_relation": matched["relation"],
                "base_surface": base[0],
                "base_address": base[1],
                "entry_headword": str(entry.get("headword") or ""),
                "compound_partner": copy.deepcopy(partner) if partner else None,
            })
            return pattern_match, "", sub_shape
    return None, "pattern_unresolved", sub_shape


def _build_positive_record(row: Mapping[str, Any], match: Mapping[str, Any], pattern: Mapping[str, Any]) -> dict[str, Any]:
    loc = _loc(row)
    surface = _surface(row)
    entry_id = str(match["entry_id"])
    projection_id = f"fam3.number.{loc.replace(':', '.')}.v1"
    source_addresses = _source_addresses(loc, entry_id, match, row)
    base_value = {
        "occurrence": {"loc": loc, "surface": surface},
        "entry_id": entry_id,
        "base_surface": match["base_surface"],
        "observed_surface": match["observed_surface"],
        "matched_surface": match["matched_surface"],
        "matched_relation": match["matched_relation"],
        "source_fields": [match["base_address"], match["matched_address"]],
        "base_role": "entry_backed_number_base",
    }
    base_fact_id = "sha256:" + fam2._sha256({"fact_type": "entry_base_attestation", "value": base_value, "surface": surface})
    base_fact = _base_fact(
        fact_id=base_fact_id,
        fact_type="entry_base_attestation",
        value=base_value,
        surface=surface,
        source={"source_id": f"entry:{entry_id}", "source_kind": "qamus_entry_field"},
        source_address={"address": match["base_address"], "source_kind": "qamus_entry_field"},
        source_addresses=source_addresses,
        evidence_mode="direct_source_attestation",
        certification={"status": "candidate", "reason": "The joined entry supplies the base for calibration only."},
        evidence={
            "status": "source_addressed_candidate",
            "confidence": "high",
            "evidence_ids": [match["base_address"], match["matched_address"]],
            "summary": "The same caller-supplied entry contains the observed number surface and its base field.",
        },
        rule_id="fam3.entry_base_attestation",
        projection_id=projection_id,
        guards=[
            {"guard_id": "fam3.whitelist_entry_context_only", "reason": "The whitelist entry_id is a context edge until the observed surface matches the entry."},
            {"guard_id": "fam3.entry_surface_exact", "reason": "The observed surface is matched against an exact entry headword, sense, or form."},
            {"guard_id": "fam3.surface_span_exact", "reason": "The full written occurrence span is retained without repainting."},
            {"guard_id": "fam3.candidate_only", "reason": "The record cannot authorize source or public mutation."},
        ],
        defeaters=[],
        unresolved_blockers=[],
        dependencies={"fact_ids": [], "source_addresses": source_addresses},
        derivation_chain=[],
        dependent_fact_ids=[],
    )
    proof_steps = [
        {"step_id": "lookup_entry_base", "operation": "read_entry_base_field", "source_address": match["base_address"]},
        {"step_id": "lookup_observed_surface", "operation": "read_entry_surface_field", "source_address": match["matched_address"]},
        {"step_id": "named_number_pattern", "operation": "match_registered_number_pattern", "pattern_id": match["pattern_id"]},
        {"step_id": "bind_occurrence", "operation": "retain_exact_written_span", "surface_span_id": "occurrence"},
    ]
    if match.get("compound_partner"):
        proof_steps.insert(2, {
            "step_id": "bind_compound_partner",
            "operation": "read_adjacent_number_component",
            "source_address": f"quran:{match['compound_partner'].get('loc')}",
        })
    proof = {
        "passed": True,
        "algorithm": "entry_backed_base_then_registered_number_pattern",
        "input_surface": match["base_surface"],
        "output_surface": surface,
        "steps": proof_steps,
        "source_addresses": source_addresses,
    }
    formation_value = {
        "occurrence": {"loc": loc, "surface": surface},
        "written_span": {"start": 0, "end": len(surface), "surface": surface},
        "sub_shape": match["sub_shape"],
        "pattern_id": match["pattern_id"],
        "pattern_pair": {
            "base": match["base_pattern"],
            "surface": match["surface_pattern"],
            "name": match["pair_name"],
        },
        "entry_id": entry_id,
        "base_surface": match["base_surface"],
        "observed_surface": match["observed_surface"],
        "source_fields": [match["base_address"], match["matched_address"]],
        "counted_noun": copy.deepcopy(_counted_noun_context(row)) if match["sub_shape"] == "gender_polarity_cardinal" else None,
        "compound_partner": copy.deepcopy(match.get("compound_partner")),
        "reconstruction_proof": proof,
    }
    formation_fact_id = "sha256:" + fam2._sha256({"fact_type": "formation_evidence", "value": formation_value, "surface": surface})
    formation_fact = _base_fact(
        fact_id=formation_fact_id,
        fact_type="formation_evidence",
        value=formation_value,
        surface=surface,
        source={"source_id": f"registry:fam3-numbers:pattern:{match['pattern_id']}", "source_kind": "review_artifact"},
        source_address={"address": f"registry:fam3-numbers:pattern:{match['pattern_id']}", "source_kind": "review_artifact"},
        source_addresses=source_addresses,
        evidence_mode="paired_form_inference",
        certification={"status": "candidate", "reason": "The named number rule remains a calibration candidate pending owner review."},
        evidence={
            "status": "source_addressed_candidate",
            "confidence": "high",
            "evidence_ids": [base_fact_id, f"registry:{match['pattern_id']}"],
            "summary": "The registered number rule reconstructs the observed surface from the entry-backed base.",
        },
        rule_id=f"fam3.pattern.{match['pattern_id']}",
        projection_id=projection_id,
        guards=[
            {"guard_id": "fam3.entry_backed_base", "reason": "The base is sourced from the same joined entry as the observed surface."},
            {"guard_id": "fam3.named_number_pattern", "reason": "The pattern id and written form are matched by the registered number projector."},
            {"guard_id": "fam3.exact_written_orthography", "reason": "Hamza seats, tāʾ marbūṭa, and defective spellings are not normalized."},
            {"guard_id": "fam3.no_label_inference", "reason": "A label, gloss, or morphline cannot create this typed fact."},
            {"guard_id": "fam3.candidate_only", "reason": "No public materialization or live mutation is authorized."},
        ],
        defeaters=[],
        unresolved_blockers=[],
        dependencies={"fact_ids": [base_fact_id], "source_addresses": source_addresses},
        derivation_chain=[{
            "step_id": "fam3.formation.from.entry_base",
            "operation": "apply_registered_number_pattern_to_entry_base",
            "input_fact_ids": [base_fact_id],
            "input_source_addresses": source_addresses,
            "output": f"formation_evidence:{match['pattern_id']}:{surface}",
        }],
        dependent_fact_ids=[],
    )
    base_fact["dependent_fact_ids"] = [formation_fact_id]
    record = {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam3:number:{loc}",
        "record_type": "projection_input",
        "canonical_occurrence": {
            "occurrence_id": f"quran:{loc}",
            "quran_loc": loc,
            "wbw_loc": f"wbw:{loc}",
            "surface": surface,
            "surface_length": len(surface),
            "entry_id": entry_id,
            "card_id": f"fam3:{entry_id}",
        },
        "facts": [base_fact, formation_fact],
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": CALIBRATION_ARTIFACT,
                "field": "formation",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "This number-word formation claim is bound to an entry-backed base and a named registered number rule.",
                "language": "en",
                "fact_bindings": [
                    {"fact_id": base_fact_id, "fact_field": "fact_value.base_surface", "surface_span_ids": ["occurrence"]},
                    {"fact_id": formation_fact_id, "fact_field": "fact_value.sub_shape", "surface_span_ids": ["occurrence"]},
                    {"fact_id": formation_fact_id, "fact_field": "fact_value.pattern_id", "surface_span_ids": ["occurrence"]},
                    {"fact_id": formation_fact_id, "fact_field": "fact_value.reconstruction_proof.output_surface", "surface_span_ids": ["occurrence"]},
                ],
            },
            "learner_statement": None,
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "formation_fact_id": formation_fact_id,
                "segments": [{"surface": surface, "role": "lexical_host"}],
            },
        },
    }
    from tools.fd_compiler import build_formation_learner_view

    learner_view = build_formation_learner_view(record)
    record["projection"]["learner_statement"] = learner_view["learner_explanation"]
    record["projection"]["public_payload"]["learner_copy"] = learner_view
    return record


def _build_unresolved_record(row: Mapping[str, Any], blocker: str, sub_shape: str) -> dict[str, Any]:
    loc = _loc(row)
    surface = _surface(row)
    projection_status = PROJECTION_STATUS.get(blocker, "blocked")
    projection_id = f"fam3.number.{loc.replace(':', '.')}.pending.v1"
    entry_id = _safe_joined_entry_id(row)
    value = {
        "occurrence": {"loc": loc, "surface": surface},
        "written_span": {"start": 0, "end": len(surface), "surface": surface},
        "status": "unresolved",
        "observed_sub_shape": sub_shape,
        "route": blocker,
        "reason_codes": [blocker],
        "requested_label": row.get("label_claim"),
        "entry_id": entry_id,
        "source_fields": ["surface", "label_claim", "entry_id"],
    }
    fact_id = "sha256:" + fam2._sha256({"fact_type": "number_formation_pending", "value": value, "surface": surface})
    quran_address = {"address": f"quran:{loc}", "source_kind": "quran_token"}
    source_addresses = [quran_address, *_context_source_addresses(loc, row)]
    fact = _base_fact(
        fact_id=fact_id,
        fact_type="number_formation_pending",
        value=value,
        surface=surface,
        source={"source_id": f"fam3:occurrence:{loc}", "source_kind": "quran_token"},
        source_address=quran_address,
        source_addresses=source_addresses,
        evidence_mode="unresolved",
        certification={"status": "pending", "reason": f"FAM3 route is {blocker}; no number formation fact was emitted."},
        evidence={
            "status": "blocked",
            "confidence": "unknown",
            "evidence_ids": [f"fam3:unresolved:{loc}:{blocker}"],
            "summary": "The producer abstained because the exact number formation prerequisites are incomplete.",
        },
        rule_id="fam3.abstain_without_number_formation_evidence",
        projection_id=projection_id,
        guards=[
            {"guard_id": "fam3.abstain_typed_route", "reason": "The family route is preserved as an explicit unresolved blocker."},
            {"guard_id": "fam3.no_label_inference", "reason": "A label, gloss, or morphline cannot create a number formation fact."},
            {"guard_id": "fam3.candidate_only", "reason": "No public materialization or live mutation is authorized."},
        ],
        defeaters=[{"defeater_id": blocker, "reason": f"The producer encountered the typed FAM3 blocker {blocker}.", "fact_ids": []}],
        unresolved_blockers=[{"blocker_id": blocker, "reason": f"FAM3 number formation route: {blocker}."}],
        dependencies={"fact_ids": [], "source_addresses": source_addresses},
        derivation_chain=[],
        dependent_fact_ids=[],
    )
    record = {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam3:number:pending:{loc}",
        "record_type": "unresolved_projection",
        "canonical_occurrence": {
            "occurrence_id": f"quran:{loc}",
            "quran_loc": loc,
            "wbw_loc": f"wbw:{loc}",
            "surface": surface,
            "surface_length": len(surface),
            **({"entry_id": entry_id} if entry_id else {}),
        },
        "facts": [fact],
        "projection": {
            "projection_id": projection_id,
            "status": projection_status,
            "unresolved_status": projection_status,
            "learner_visible": True,
            "materialization_target": {
                "artifact": UNRESOLVED_ARTIFACT,
                "field": "formation",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": None,
            "learner_statement": learner_statement_for(projection_status),
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "status": projection_status,
                "route": blocker,
                "segments": [{"surface": surface, "role": "lexical_host"}],
            },
        },
    }
    return record


def produce_record(
    row: Mapping[str, Any],
    *,
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    whitelist_rows: Sequence[Mapping[str, Any]] | None = None,
    pattern_registry: Any = None,
) -> dict[str, Any]:
    registry = _registry_records(pattern_registry)
    entry_map = _entry_map(entries)
    prepared = copy.deepcopy(dict(row))
    if whitelist_rows is not None:
        index = WhitelistIndex(whitelist_rows)
        if not prepared.get("_joined_entry_id") and not prepared.get("entry_id"):
            rows = index.by_loc.get(_loc(prepared), [])
            joined_ids = sorted({str(value.get("entry_id")) for value in rows if value.get("entry_id")})
            prepared["_joined_entry_ids"] = joined_ids
            if len(joined_ids) == 1:
                prepared["_joined_entry_id"] = joined_ids[0]
        if "context_rows" not in prepared and "_context_rows" not in prepared:
            safe_context = []
            card = ":".join(_loc(prepared).split(":")[:2])
            for value in index.rows:
                value_loc = str(value.get("loc") or "").removeprefix("quran:")
                if ":".join(value_loc.split(":")[:2]) != card or value_loc == _loc(prepared):
                    continue
                safe_context.append({
                    "loc": value_loc,
                    "surface": value.get("surface") or value.get("displayed_qword_surface"),
                    "entry_id": value.get("entry_id"),
                    "qword_index": value.get("qword_index"),
                    "card_ref": value.get("card_ref"),
                })
            prepared["_context_rows"] = safe_context
    match, blocker, sub_shape = _resolve_match(prepared, entry_map, registry)
    if match is None:
        record = _build_unresolved_record(prepared, blocker, sub_shape)
    else:
        pattern = _pattern_by_id(str(match["pattern_id"]), registry)
        if pattern is None:
            record = _build_unresolved_record(prepared, "pattern_unresolved", sub_shape)
        else:
            record = _build_positive_record(prepared, match, pattern)
    errors = validate_number_record(record)
    if errors:
        raise ValueError("generated FAM3 record failed validation: " + "; ".join(errors))
    return record


def validate_number_record(record: Mapping[str, Any]) -> list[str]:
    errors = list(validate_contract_record(dict(record)))
    if errors:
        return errors
    projection = record["projection"]
    facts = record["facts"]
    formation = [fact for fact in facts if fact.get("fact_type") == "formation_evidence"]
    bases = [fact for fact in facts if fact.get("fact_type") == "entry_base_attestation"]
    pending = [fact for fact in facts if fact.get("fact_type") == "number_formation_pending"]
    if projection["status"] == "candidate":
        if len(formation) != 1 or len(bases) != 1 or pending:
            errors.append("candidate FAM3 record must contain one entry_base_attestation and one formation_evidence")
        if formation and bases:
            formation_fact = formation[0]
            base_fact = bases[0]
            value = formation_fact["fact_value"]
            if base_fact["fact_id"] not in formation_fact["dependencies"]["fact_ids"]:
                errors.append("formation_evidence does not depend on entry_base_attestation")
            if value.get("sub_shape") not in NUMBER_SUBSHAPES or not value.get("pattern_id"):
                errors.append("formation_evidence lacks a registered number shape and pattern")
            if value.get("reconstruction_proof", {}).get("passed") is not True:
                errors.append("number reconstruction proof did not pass")
            if formation_fact.get("evidence_mode") != "paired_form_inference":
                errors.append("number formation must use paired_form_inference")
            payload = projection.get("public_payload") or {}
            learner_copy = payload.get("learner_copy") or {}
            if payload.get("authorization_state") != "pre_apply_not_authorized":
                errors.append("FAM3 candidate does not carry pre_apply_not_authorized")
            if learner_copy.get("n_lang_clean") is not True:
                errors.append("generated FAM3 learner copy is not N-LANG clean")
            if "Ṣarf — how this piece forms the word" not in learner_copy.get("sarf", ""):
                errors.append("generated learner copy lacks the public Ṣarf label")
            if "Naḥw — what this piece does here" not in learner_copy.get("nahw", ""):
                errors.append("generated learner copy lacks the public Naḥw label")
            if projection["materialization_target"]["public_materialization_allowed"]:
                errors.append("FAM3 candidate enables public materialization")
            if projection["materialization_target"]["live_mutation_allowed"]:
                errors.append("FAM3 candidate enables live mutation")
    elif projection["status"] in {"source_gap", "producer_pending", "blocked"}:
        if formation or bases:
            errors.append("unresolved FAM3 record must not contain base or formation evidence")
        if len(pending) != 1:
            errors.append("unresolved FAM3 record must contain one number_formation_pending fact")
        if not any(fact.get("unresolved_blockers") for fact in facts):
            errors.append("unresolved FAM3 record lacks a typed blocker")
        if projection.get("claim") is not None:
            errors.append("unresolved FAM3 record carries a claim")
        if (projection.get("public_payload") or {}).get("authorization_state") != "pre_apply_not_authorized":
            errors.append("unresolved FAM3 record does not carry pre_apply_not_authorized")
    else:
        errors.append(f"unsupported FAM3 projection status {projection.get('status')!r}")
    return errors


def select_calibration_rows(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    whitelist_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    verdict_locs = {_loc(row) for row in verdict_rows}
    index = WhitelistIndex(whitelist_rows)
    family_rows = [row for row in strat_rows if row.get("morphology_family") == "number_words"]
    missing = [_loc(row) for row in family_rows if _loc(row) not in verdict_locs]
    if missing:
        raise ValueError(f"v575 verdicts missing FAM3 locations: {missing[:5]}")
    rows = []
    for source in sorted(family_rows, key=_loc):
        loc = _loc(source)
        joined = index.by_loc.get(loc, [])
        merged = copy.deepcopy(dict(source))
        merged.update({"loc": loc, "quran_loc": f"quran:{loc}", "wbw_loc": f"wbw:{loc}"})
        joined_ids = sorted({str(item.get("entry_id")) for item in joined if item.get("entry_id")})
        merged["_joined_entry_ids"] = joined_ids
        if len(joined_ids) == 1:
            merged["_joined_entry_id"] = joined_ids[0]
        rows.append(merged)
    if len(rows) != 57:
        raise ValueError(f"FAM3 calibration requires exactly 57 family rows; found {len(rows)}")
    return rows


def build_calibration_packet(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    whitelist_rows: Sequence[Mapping[str, Any]],
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    *,
    pattern_registry: Any = None,
) -> dict[str, Any]:
    rows = select_calibration_rows(strat_rows, verdict_rows, whitelist_rows)
    entry_map = _entry_map(entries)
    whitelist_index = WhitelistIndex(whitelist_rows)
    availability = Counter(str(row.get("entry_evidence_availability") or "unreported") for row in rows)
    ambiguity_rows = sum(
        1
        for row in rows
        if any(str(flag) in _HOMOGRAPH_FLAGS for flag in (row.get("ambiguity_flags") or []))
    )
    exact_match_rows = 0
    orthography_near_rows = 0
    no_exact_match_rows = 0
    for row in rows:
        target = _surface(row)
        joined_ids = sorted({str(item.get("entry_id")) for item in whitelist_index.by_loc.get(_loc(row), []) if item.get("entry_id")})
        matches = []
        near = False
        for entry_id in joined_ids:
            entry = entry_map.get(entry_id)
            if entry is None:
                continue
            entry_matches, entry_near = _entry_surface_matches(entry, target)
            matches.extend(entry_matches)
            near = near or entry_near
        if matches:
            exact_match_rows += 1
        elif near:
            orthography_near_rows += 1
        else:
            no_exact_match_rows += 1
    source_survey = {
        "family_rows": len(rows),
        "whitelist_rows_with_joined_entry_id": sum(
            1 for row in rows if whitelist_index.by_loc.get(_loc(row))
        ),
        "joined_entry_ambiguity_rows": ambiguity_rows,
        "entry_evidence_availability": dict(sorted(availability.items())),
        "exact_surface_entry_match_rows": exact_match_rows,
        "orthography_near_miss_rows": orthography_near_rows,
        "rows_without_exact_entry_surface_match": no_exact_match_rows,
        "entry_id_semantics": "whitelist entry_id is a verse-context edge; exact observed-surface match is required before base use",
    }
    records = [
        produce_record(row, entries=entry_map, whitelist_rows=whitelist_rows, pattern_registry=pattern_registry)
        for row in rows
    ]
    candidates = [record for record in records if record["projection"]["status"] == "candidate"]
    unresolved = [record for record in records if record["projection"]["status"] != "candidate"]
    populations: dict[str, dict[str, int]] = defaultdict(lambda: {"population": 0, "candidate_count": 0, "abstention_count": 0})
    for record in records:
        fact = next(
            (item for item in record["facts"] if item.get("fact_type") in {"formation_evidence", "number_formation_pending"}),
            record["facts"][0],
        )
        value = fact.get("fact_value") or {}
        sub_shape = value.get("sub_shape") or value.get("observed_sub_shape") or "unclassified"
        item = populations[str(sub_shape)]
        item["population"] += 1
        if record["projection"]["status"] == "candidate":
            item["candidate_count"] += 1
        else:
            item["abstention_count"] += 1
    for sub_shape in sorted(NUMBER_SUBSHAPES):
        populations.setdefault(sub_shape, {"population": 0, "candidate_count": 0, "abstention_count": 0})
    summary = {
        "family": "number_words",
        "sample_size": len(records),
        "family_population": len(records),
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "candidate_mode": "pre_apply_not_authorized",
        "materialization": "none",
        "sub_shape_populations": dict(sorted(populations.items())),
        "source_survey": source_survey,
        "verdict_coverage": "57/57 exact locations present",
        "source_inputs": "caller-supplied stratified rows, verdict rows, whitelist rows, and entry records",
    }
    return {"records": records, "summary": summary}


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def write_calibration_packet(packet: Mapping[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = list(packet["records"])
    positive = [record for record in records if record["projection"]["status"] == "candidate"]
    unresolved = [record for record in records if record["projection"]["status"] != "candidate"]
    paths = {
        "sample": output_dir / "calibration-sample.jsonl",
        "positive": output_dir / "formation-facts.jsonl",
        "unresolved": output_dir / "unresolved-records.jsonl",
        "summary": output_dir / "calibration-summary.json",
        "fixture_positive": output_dir / "fixture-formation-facts.jsonl",
        "fixture_unresolved": output_dir / "fixture-unresolved-records.jsonl",
    }
    _write_jsonl(paths["sample"], records)
    _write_jsonl(paths["positive"], positive)
    _write_jsonl(paths["unresolved"], unresolved)
    paths["summary"].write_text(json.dumps(packet["summary"], ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    fixture_dir = ROOT / "qamus" / "examples" / "fam3-numbers"
    fixture_entries = _read_jsonl(fixture_dir / "entry-fixtures.jsonl")
    fixture_patterns = load_pattern_registry(fixture_dir / "pattern-registry.jsonl")
    fixture_rows = [item["row"] for item in _read_jsonl(fixture_dir / "producer-fixtures.jsonl")]
    fixture_records = [produce_record(row, entries=fixture_entries, pattern_registry=fixture_patterns) for row in fixture_rows]
    _write_jsonl(paths["fixture_positive"], [record for record in fixture_records if record["projection"]["status"] == "candidate"])
    _write_jsonl(paths["fixture_unresolved"], [record for record in fixture_records if record["projection"]["status"] != "candidate"])
    return paths


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stratified", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--whitelist", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pattern-registry", type=Path, default=DEFAULT_PATTERN_REGISTRY)
    args = parser.parse_args(argv)
    pattern_registry = load_pattern_registry(args.pattern_registry)
    packet = build_calibration_packet(
        _read_jsonl(args.stratified),
        _read_jsonl(args.verdicts),
        _read_jsonl(args.whitelist),
        _read_jsonl(args.entries),
        pattern_registry=pattern_registry,
    )
    paths = write_calibration_packet(packet, args.output_dir)
    print(json.dumps({"summary": packet["summary"], "artifacts": sorted(path.name for path in paths.values())}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
