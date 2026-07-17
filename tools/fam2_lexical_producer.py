"""FAM2 entry-backed lexical formation producer.

This module is deliberately narrow.  It accepts a caller-supplied entry set,
looks up exact written forms, and applies only the named formation patterns in
the committed FAM2 registry.  A label, English gloss, or morphline can route a
row to a typed abstention, but can never create a formation fact.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.typed_claim_contract import learner_statement_for, validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATTERN_REGISTRY = ROOT / "qamus" / "examples" / "fam2-lexical" / "pattern-registry.jsonl"
PROJECTOR_ID = "sarf.fam2.lexical_formation.v1"
PRODUCER_ID = "tools.fam2_lexical_producer"
VERSION = "1.0.0"
SCHEMA = "qamus.typed_claim_contract.v1"
CALIBRATION_ARTIFACT = "qamus/examples/fam2-lexical/calibration-sample.jsonl"
UNRESOLVED_ARTIFACT = "qamus/examples/fam2-lexical/unresolved-sample.jsonl"

SUBSHAPES = {
    "broken_plural",
    "sound_masculine_plural",
    "sound_feminine_plural",
    "dual",
    "nisba_adjective",
    "elative",
}

PROJECTION_STATUS = {
    "entry_lookup_missing": "source_gap",
    "pattern_unresolved": "producer_pending",
    "source_gap": "source_gap",
    "orthography_mismatch": "blocked",
    "homograph_ambiguity": "blocked",
    "pos_mismatch": "blocked",
}

_ARABIC_MARKS = {ch for ch in map(chr, range(0x0600, 0x0700)) if unicodedata.category(ch) == "Mn"}
_TANWIN = {"ً", "ٌ", "ٍ"}
_ARTICLE_PREFIXES = ("ال", "ٱل")
_CASE_MARKS = _ARABIC_MARKS | {"ۭ"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(value)
    return rows


def load_pattern_registry(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(path or DEFAULT_PATTERN_REGISTRY)
    seen: set[str] = set()
    for row in rows:
        pattern_id = row.get("pattern_id")
        if not isinstance(pattern_id, str) or not pattern_id:
            raise ValueError("FAM2 pattern registry requires pattern_id")
        if pattern_id in seen:
            raise ValueError(f"duplicate FAM2 pattern id: {pattern_id}")
        seen.add(pattern_id)
        if row.get("sub_shape") not in SUBSHAPES:
            raise ValueError(f"unsupported FAM2 pattern sub-shape: {pattern_id}")
        if row.get("orthography_policy") not in {
            "exact_written_pair",
            "exact_stem_and_suffix",
            "named_ta_marbuta_rule_only",
            "exact_base_and_suffix",
        }:
            raise ValueError(f"FAM2 pattern lacks a defensive orthography policy: {pattern_id}")
    return rows


def _registry_records(registry: Any = None) -> list[dict[str, Any]]:
    if registry is None:
        return load_pattern_registry()
    if isinstance(registry, (str, Path)):
        return load_pattern_registry(Path(registry))
    if isinstance(registry, Sequence) and not isinstance(registry, (str, bytes)):
        rows = [row for row in registry if isinstance(row, dict) and row.get("pattern_id")]
        return rows or load_pattern_registry()
    raise TypeError("pattern registry must be a path or a sequence of registry objects")


def _pattern_by_id(pattern_id: str, registry: Any = None) -> dict[str, Any] | None:
    return next((row for row in _registry_records(registry) if row.get("pattern_id") == pattern_id), None)


def _is_mark(value: str) -> bool:
    return unicodedata.category(value) == "Mn"


def _strip_case(value: str) -> str:
    """Remove only terminal case/tanwin marks, retaining internal vocalism."""

    text = unicodedata.normalize("NFC", str(value or ""))
    chars = list(text)
    tanwin_seen = False
    if chars and chars[-1] == "ا":
        mark_window = chars[max(0, len(chars) - 4) : -1]
        tanwin_seen = any(mark in _TANWIN for mark in mark_window)
        if tanwin_seen:
            chars.pop()
    while chars and _is_mark(chars[-1]):
        if chars[-1] in _TANWIN:
            tanwin_seen = True
        chars.pop()
    if tanwin_seen and chars and chars[-1] == "ا":
        chars.pop()
    return "".join(chars)


def _article_info(value: str) -> tuple[bool, str, str]:
    text = _strip_case(value)
    for prefix in _ARTICLE_PREFIXES:
        if text.startswith(prefix):
            body = text[len(prefix) :]
            while body and _is_mark(body[0]):
                body = body[1:]
            return True, prefix, body
    return False, "", text


def _without_initial_assimilation_shadda(value: str) -> str:
    chars = list(_strip_case(value))
    for index, char in enumerate(chars):
        if _is_mark(char):
            continue
        mark_index = index + 1
        while mark_index < len(chars) and _is_mark(chars[mark_index]):
            if chars[mark_index] == "ّ":
                del chars[mark_index]
                return "".join(chars)
            mark_index += 1
        return "".join(chars)
    return "".join(chars)


def _has_initial_shadda(value: str) -> bool:
    chars = list(_strip_case(value))
    for index, char in enumerate(chars):
        if _is_mark(char):
            continue
        return "ّ" in chars[index + 1 : index + 4]
    return False


def _letters(value: str) -> str:
    return "".join(char for char in _strip_case(value) if not _is_mark(char))


def _tokens(value: str) -> list[tuple[str, frozenset[str]]]:
    tokens: list[tuple[str, frozenset[str]]] = []
    for char in _strip_case(value):
        if _is_mark(char):
            if tokens:
                tokens[-1] = (tokens[-1][0], frozenset(set(tokens[-1][1]) | {char}))
            continue
        tokens.append((char, frozenset()))
    return tokens


def _surface_relation(target: str, documented: str, *, allow_assimilation: bool = False) -> str | None:
    """Return an allowed relation, or an orthography failure marker."""

    target_norm = _strip_case(target)
    documented_norm = _strip_case(documented)
    if target_norm == documented_norm:
        return "exact"

    target_has_article, target_article, target_body = _article_info(target_norm)
    documented_has_article, documented_article, documented_body = _article_info(documented_norm)
    if target_has_article and documented_has_article:
        if target_body == documented_body and target_article != documented_article:
            return "orthography_mismatch"
        return None
    if target_body == documented_body and target_has_article != documented_has_article:
        return "article_structural"
    if allow_assimilation:
        target_assimilated = _without_initial_assimilation_shadda(target_norm)
        documented_assimilated = _without_initial_assimilation_shadda(documented_norm)
        if target_assimilated == documented_assimilated:
            return "article_assimilation"

    # A letter-for-letter or mark-for-mark near miss is never repaired by
    # norm_strict: it is an orthographic defeater for this producer.
    if _letters(target_norm) == _letters(documented_norm):
        return "orthography_mismatch"
    return None


def _form_rows(entry: Mapping[str, Any]) -> list[dict[str, str]]:
    entry_id = str(entry.get("id") or entry.get("entry_id") or "")
    rows: list[dict[str, str]] = []
    headword = entry.get("headword")
    if isinstance(headword, str) and headword:
        rows.append({"surface": headword, "address": f"entry:{entry_id}:headword"})
    usages = entry.get("usage") or entry.get("usages") or []
    if isinstance(usages, list):
        for usage_index, usage in enumerate(usages):
            if not isinstance(usage, Mapping):
                continue
            forms = usage.get("forms") or []
            if not isinstance(forms, list):
                continue
            for form_index, form in enumerate(forms):
                if isinstance(form, str) and form:
                    rows.append({
                        "surface": form,
                        "address": f"entry:{entry_id}:usage[{usage_index}].forms[{form_index}]",
                    })
    return rows


def _entry_map(entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    if isinstance(entries, Mapping):
        result = {}
        for key, value in entries.items():
            if isinstance(value, Mapping):
                result[str(key)] = value
        return result
    result = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        entry_id = entry.get("id") or entry.get("entry_id")
        if entry_id:
            result[str(entry_id)] = entry
    return result


def _find_form_matches(
    forms: Sequence[dict[str, str]],
    target: str,
    *,
    allow_assimilation: bool = False,
) -> tuple[list[dict[str, str]], bool]:
    matches: list[dict[str, str]] = []
    orthographic_near_miss = False
    for form in forms:
        relation = _surface_relation(target, form["surface"], allow_assimilation=allow_assimilation)
        if relation in {"exact", "article_structural", "article_assimilation"}:
            match = dict(form)
            match["relation"] = relation
            matches.append(match)
        elif relation == "orthography_mismatch":
            orthographic_near_miss = True
    return matches, orthographic_near_miss


def _template_match(singular: str, plural: str, matcher: str) -> bool:
    singular_tokens = _tokens(singular)
    plural_tokens = _tokens(plural)

    def marks(token: tuple[str, frozenset[str]], expected: set[str] | None) -> bool:
        return expected is None or set(token[1]) == expected

    if matcher == "template_fa3il_fu3alaa":
        if len(singular_tokens) != 4 or len(plural_tokens) != 5:
            return False
        if singular_tokens[2][0] != "ي" or plural_tokens[3][0] != "ا" or plural_tokens[4][0] != "ء":
            return False
        if not marks(singular_tokens[0], {"َ"}) or not marks(singular_tokens[1], {"ِ"}):
            return False
        if not marks(plural_tokens[0], {"ُ"}) or not marks(plural_tokens[1], {"َ"}) or not marks(plural_tokens[2], {"َ"}):
            return False
        return singular_tokens[0][0] == plural_tokens[0][0] and singular_tokens[1][0] == plural_tokens[1][0] and singular_tokens[3][0] == plural_tokens[2][0]

    if matcher == "template_fi3l_af3aal":
        if len(singular_tokens) != 3 or len(plural_tokens) != 5:
            return False
        if plural_tokens[0][0] != "أ" or plural_tokens[3][0] != "ا":
            return False
        if not marks(singular_tokens[0], {"ِ"}) or not marks(singular_tokens[1], {"ْ"}):
            return False
        if not marks(plural_tokens[0], {"َ"}) or not marks(plural_tokens[1], {"ْ"}) or not marks(plural_tokens[2], {"َ"}):
            return False
        return singular_tokens[0][0] == plural_tokens[1][0] and singular_tokens[1][0] == plural_tokens[2][0] and singular_tokens[2][0] == plural_tokens[4][0]

    if matcher == "template_fa3ul_fi3aal":
        if len(singular_tokens) != 3 or len(plural_tokens) != 4:
            return False
        if plural_tokens[2][0] != "ا":
            return False
        if not marks(singular_tokens[0], {"َ"}) or not marks(singular_tokens[1], {"ُ"}):
            return False
        if not marks(plural_tokens[0], {"ِ"}) or not marks(plural_tokens[1], {"َ"}):
            return False
        return singular_tokens[0][0] == plural_tokens[0][0] and singular_tokens[1][0] == plural_tokens[1][0] and singular_tokens[2][0] == plural_tokens[3][0]

    if matcher == "suffix_masc_plural":
        plural_letters = _letters(plural)
        return any(plural_letters.endswith(suffix) and plural_letters[:-len(suffix)] == _letters(singular) for suffix in ("ون", "ين"))

    if matcher == "suffix_fem_plural":
        singular_letters = _letters(singular)
        plural_letters = _letters(plural)
        return singular_letters.endswith("ة") and plural_letters == singular_letters[:-1] + "ات"

    if matcher == "suffix_dual":
        singular_letters = _letters(singular)
        plural_letters = _letters(plural)
        if singular_letters.endswith("ة"):
            return plural_letters in {singular_letters[:-1] + "تان", singular_letters[:-1] + "تين"}
        return plural_letters in {singular_letters + "ان", singular_letters + "ين"}

    if matcher == "suffix_nisba":
        return _letters(plural).startswith(_letters(singular)) and _letters(plural)[len(_letters(singular)) :] == "ي"

    if matcher == "explicit_elative_pair":
        return bool(_strip_case(singular) and _strip_case(plural))
    return False


def match_registered_pattern(
    singular: str,
    plural: str,
    pattern_id: str,
    registry: Any = None,
) -> dict[str, Any] | None:
    """Match one exact written pair against one named FAM2 pattern."""

    pattern = _pattern_by_id(pattern_id, registry)
    if pattern is None:
        return None
    if _template_match(singular, plural, str(pattern.get("matcher", ""))):
        return {
            "pattern_id": pattern_id,
            "sub_shape": pattern["sub_shape"],
            "pair_name": pattern["pair_name"],
            "singular_surface": _strip_case(singular),
            "plural_surface": _strip_case(plural),
            "matcher": pattern["matcher"],
            "registry_version": pattern.get("version", VERSION),
        }
    return None


def _lexical_surface(row: Mapping[str, Any]) -> str:
    explicit = row.get("lexical_surface")
    if isinstance(explicit, str) and explicit:
        return explicit
    segments = row.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, Mapping):
                continue
            if segment.get("role") in {"lexical_host", "nominal_host", "host", "noun", "adjective"} and segment.get("surface"):
                return str(segment["surface"])
    return str(row.get("surface") or "")


def _loc(row: Mapping[str, Any]) -> str:
    value = str(row.get("loc") or row.get("quran_loc") or "")
    value = value.removeprefix("quran:")
    if not re.fullmatch(r"[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}", value):
        raise ValueError(f"invalid FAM2 Quran location: {value!r}")
    return value


def _entry_pair_candidates(
    entry: Mapping[str, Any],
    target: str,
    *,
    pattern: Mapping[str, Any],
    allow_assimilation: bool,
    explicit_pair: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    forms = _form_rows(entry)
    plural_matches, plural_near_miss = _find_form_matches(forms, target, allow_assimilation=allow_assimilation)
    if not plural_matches:
        return None, "orthography_mismatch" if plural_near_miss else "entry_lookup_missing"
    singular_target = None
    if explicit_pair:
        singular_target = explicit_pair.get("base_surface") or explicit_pair.get("singular_surface")
    matcher = str(pattern.get("matcher", ""))
    candidates = forms
    for plural_form in plural_matches:
        plural_for_match = _article_info(_strip_case(plural_form["surface"]))[2]
        for singular_form in candidates:
            if _strip_case(singular_form["surface"]) == _strip_case(plural_form["surface"]):
                continue
            if singular_target and _surface_relation(singular_target, singular_form["surface"]) != "exact":
                continue
            singular_for_match = _article_info(_strip_case(singular_form["surface"]))[2]
            if not _template_match(singular_for_match, plural_for_match, matcher):
                continue
            matched = match_registered_pattern(
                singular_for_match,
                plural_for_match,
                str(pattern["pattern_id"]),
            )
            if matched is None:
                continue
            matched.update({
                "entry_id": str(entry.get("id") or entry.get("entry_id")),
                "entry_singular_surface": singular_form["surface"],
                "entry_plural_surface": plural_form["surface"],
                "singular_address": singular_form["address"],
                "plural_address": plural_form["address"],
            })
            return matched, None
    return None, "entry_lookup_missing"


def _pattern_ids_for_row(row: Mapping[str, Any], target: str, registry: Sequence[Mapping[str, Any]]) -> list[str]:
    explicit = row.get("explicit_pair")
    if isinstance(explicit, Mapping) and explicit.get("pattern_id"):
        return [str(explicit["pattern_id"])]
    label = str(row.get("label_claim") or "").lower()
    letters = _letters(target)
    result: list[str] = []
    if letters.endswith(("ون", "ين")):
        result.append("sound_masc.base_to_una")
    if letters.endswith("ات"):
        result.append("sound_fem.ta_to_at")
    if letters.endswith(("ان", "ين")):
        result.append("dual.base_to_aani")
    if "masculine" in label and "sound_masc.base_to_una" not in result:
        result.insert(0, "sound_masc.base_to_una")
    if "feminine" in label and "sound_fem.ta_to_at" not in result:
        result.insert(0, "sound_fem.ta_to_at")
    if "dual" in label and "dual.base_to_aani" not in result:
        result.insert(0, "dual.base_to_aani")
    if "nisba" in label:
        result.insert(0, "nisba.base_to_iyy")
    if "elative" in label:
        result.insert(0, "elative.adjective_to_af3al")
    if "broken" in label or not result:
        result.extend(str(item["pattern_id"]) for item in registry if item.get("sub_shape") == "broken_plural")
    return result


def _explicit_pair_shape(pair: Mapping[str, Any]) -> str | None:
    pattern_id = str(pair.get("pattern_id") or "")
    if pattern_id.startswith("broken."):
        return "broken_plural"
    if pattern_id.startswith("sound_masc"):
        return "sound_masculine_plural"
    if pattern_id.startswith("sound_fem"):
        return "sound_feminine_plural"
    if pattern_id.startswith("dual."):
        return "dual"
    if pattern_id.startswith("nisba."):
        return "nisba_adjective"
    if pattern_id.startswith("elative."):
        return "elative"
    derived = _letters(str(pair.get("derived_surface") or pair.get("plural_surface") or ""))
    if derived.endswith("ي"):
        return "nisba_adjective"
    if derived.startswith("أ") and len(derived) >= 4:
        return "elative"
    return None


def _resolve_match(
    row: Mapping[str, Any],
    entry: Mapping[str, Any] | None,
    registry: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    if isinstance(row.get("ambiguity"), Mapping):
        return None, "homograph_ambiguity"
    if row.get("ambiguity_flags") and any(
        flag in {"entry_join_multiple_entries", "homograph", "noun_adjective_ambiguity"}
        for flag in row.get("ambiguity_flags", [])
    ):
        return None, "homograph_ambiguity"
    if entry is None:
        return None, "entry_lookup_missing"
    forms = _form_rows(entry)
    if not forms:
        return None, "entry_lookup_missing"
    target = _lexical_surface(row)
    if not target:
        return None, "source_gap"
    explicit = row.get("explicit_pair")
    if isinstance(explicit, Mapping):
        singular_target = explicit.get("base_surface") or explicit.get("singular_surface")
        plural_target = explicit.get("derived_surface") or explicit.get("plural_surface")
        if not isinstance(singular_target, str) or not isinstance(plural_target, str):
            return None, "pattern_unresolved"
        if _strip_case(plural_target) != _strip_case(target):
            return None, "orthography_mismatch"
        singular_direct = [form for form in forms if _strip_case(form["surface"]) == _strip_case(singular_target)]
        plural_direct = [form for form in forms if _strip_case(form["surface"]) == _strip_case(plural_target)]
        if not singular_direct or not plural_direct:
            return None, "orthography_mismatch"
        shape = _explicit_pair_shape(explicit)
        if shape is None:
            return None, "pattern_unresolved"
        pattern_id = explicit.get("pattern_id")
        if not pattern_id:
            pattern_id = {
                "nisba_adjective": "nisba.base_to_iyy",
                "elative": "elative.adjective_to_af3al",
            }.get(shape)
        pattern = _pattern_by_id(str(pattern_id), registry) if pattern_id else None
        if pattern is None:
            return None, "pattern_unresolved"
        matched = match_registered_pattern(
            _strip_case(singular_target),
            _strip_case(plural_target),
            str(pattern_id),
            registry,
        )
        if matched is None:
            return None, "orthography_mismatch"
        matched.update({
            "entry_id": str(entry.get("id") or entry.get("entry_id")),
            "entry_singular_surface": singular_direct[0]["surface"],
            "entry_plural_surface": plural_direct[0]["surface"],
            "singular_address": singular_direct[0]["address"],
            "plural_address": plural_direct[0]["address"],
        })
        return matched, ""

    allow_assimilation = _has_initial_shadda(target) or any(
        isinstance(segment, Mapping) and segment.get("role") == "definite_article"
        for segment in row.get("segments", [])
        if isinstance(row.get("segments"), list)
    )
    pattern_ids = _pattern_ids_for_row(row, target, registry)
    saw_orthography = False
    for pattern_id in pattern_ids:
        pattern = _pattern_by_id(pattern_id, registry)
        if pattern is None:
            continue
        matched, blocker = _entry_pair_candidates(
            entry,
            target,
            pattern=pattern,
            allow_assimilation=allow_assimilation,
        )
        if matched:
            return matched, ""
        saw_orthography = saw_orthography or blocker == "orthography_mismatch"
    if saw_orthography:
        return None, "orthography_mismatch"
    if not pattern_ids:
        return None, "pattern_unresolved"
    target_matches, _ = _find_form_matches(forms, target, allow_assimilation=allow_assimilation)
    non_target_forms = [
        form for form in forms
        if not any(_strip_case(form["surface"]) == _strip_case(match["surface"]) for match in target_matches)
    ]
    if row.get("morphline"):
        return None, "source_gap"
    if not target_matches or not non_target_forms:
        return None, "entry_lookup_missing"
    return None, "pattern_unresolved"


def _addresses(loc: str, match: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {"address": f"quran:{loc}", "source_kind": "quran_token"},
        {"address": str(match["singular_address"]), "source_kind": "qamus_entry_field"},
        {"address": str(match["plural_address"]), "source_kind": "qamus_entry_field"},
        {"address": f"registry:fam2-lexical:pattern:{match['pattern_id']}", "source_kind": "review_artifact"},
    ]


def _span(surface: str) -> dict[str, Any]:
    return {
        "span_id": "occurrence",
        "start": 0,
        "end": len(surface),
        "surface": surface,
        "role": "lexical_formation_occurrence",
    }


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
    return {
        "fact_id": fact_id,
        "fact_type": fact_type,
        "fact_value": value,
        "surface_spans": [_span(surface)],
        "ownership": {
            "primary": {"owner_id": "fam2-lexical-formation", "owner_type": "producer"},
            "secondary": [
                {"owner_id": "qamus-entry-source", "owner_type": "source_owner"},
                {"owner_id": "sarf-formation-registry", "owner_type": "rule_owner"},
            ],
        },
        "source": source,
        "source_address": source_address,
        "certification": certification,
        "evidence": evidence,
        "evidence_mode": evidence_mode,
        "source_evidence": {
            "structured_source_fact": {
                "source_record_id": f"fam2:occurrence:{value['occurrence']['loc']}",
                "entry_id": value.get("entry_id"),
                "source_fields": copy.deepcopy(value.get("source_fields", [])),
            },
            "source_addresses": source_addresses,
        },
        "derivation_chain": derivation_chain,
        "dependencies": dependencies,
        "contradiction_records": [],
        "producer": {"id": PRODUCER_ID, "version": VERSION},
        "rule_projector": {
            "rule_id": rule_id,
            "projector_id": PROJECTOR_ID,
            "version": VERSION,
        },
        "guards": guards,
        "defeaters": defeaters,
        "unresolved_blockers": unresolved_blockers,
        "dependent_fact_ids": dependent_fact_ids,
        "dependent_projection_ids": [projection_id],
    }


def _build_positive_record(
    row: Mapping[str, Any],
    match: Mapping[str, Any],
    pattern: Mapping[str, Any],
) -> dict[str, Any]:
    loc = _loc(row)
    surface = str(row.get("surface") or "")
    lexical_surface = _strip_case(_lexical_surface(row))
    projection_id = f"fam2.lexical.{loc.replace(':', '.')}.v1"
    source_addresses = _addresses(loc, match)
    pair_value = {
        "occurrence": {"loc": loc, "surface": surface},
        "entry_id": str(match["entry_id"]),
        "singular_surface": match["singular_surface"],
        "plural_surface": match["plural_surface"],
        "entry_singular_surface": match["entry_singular_surface"],
        "entry_plural_surface": match["entry_plural_surface"],
        "pair_role": "entry_backed_singular_plural",
        "source_fields": [match["singular_address"], match["plural_address"]],
    }
    pair_fact_id = "sha256:" + _sha256({"fact_type": "entry_form_pair", "value": pair_value, "surface": surface})
    pair_fact = _base_fact(
        fact_id=pair_fact_id,
        fact_type="entry_form_pair",
        value=pair_value,
        surface=surface,
        source={"source_id": f"entry:{match['entry_id']}", "source_kind": "qamus_entry_field"},
        source_address={"address": match["singular_address"], "source_kind": "qamus_entry_field"},
        source_addresses=source_addresses,
        evidence_mode="direct_source_attestation",
        certification={"status": "candidate", "reason": "Entry form pair is source-addressed for calibration only."},
        evidence={
            "status": "source_addressed_candidate",
            "confidence": "high",
            "evidence_ids": [match["singular_address"], match["plural_address"]],
            "summary": "The supplied Qamus entry contains the exact singular and plural written forms.",
        },
        rule_id="fam2.entry_form_pair",
        projection_id=projection_id,
        guards=[
            {"guard_id": "fam2.entry_lookup_exact", "reason": "Both forms are read from one caller-supplied entry."},
            {"guard_id": "fam2.surface_span_exact", "reason": "The full written occurrence span is retained without repainting."},
            {"guard_id": "fam2.candidate_only", "reason": "The record cannot authorize whitelist or renderer mutation."},
        ],
        defeaters=[],
        unresolved_blockers=[],
        dependencies={"fact_ids": [], "source_addresses": source_addresses},
        derivation_chain=[],
        dependent_fact_ids=[],
    )
    proof = {
        "passed": True,
        "algorithm": "entry_form_pair_then_named_pattern_match",
        "input_surface": lexical_surface,
        "output_surface": match["plural_surface"],
        "steps": [
            {"step_id": "lookup_singular", "operation": "read_entry_form", "source_address": match["singular_address"]},
            {"step_id": "lookup_plural", "operation": "read_entry_form", "source_address": match["plural_address"]},
            {"step_id": "named_pattern", "operation": "match_registered_pattern", "pattern_id": match["pattern_id"]},
            {"step_id": "bind_occurrence", "operation": "retain_exact_written_span", "surface_span_id": "occurrence"},
        ],
        "source_addresses": source_addresses,
    }
    formation_value = {
        "occurrence": {"loc": loc, "surface": surface},
        "written_span": {"start": 0, "end": len(surface), "surface": surface},
        "sub_shape": match["sub_shape"],
        "pattern_id": match["pattern_id"],
        "pattern_pair": {
            "singular": pattern["singular_pattern"],
            "plural": pattern["plural_pattern"],
            "name": pattern["pair_name"],
        },
        "entry_id": str(match["entry_id"]),
        "singular_surface": match["singular_surface"],
        "plural_surface": match["plural_surface"],
        "source_fields": [match["singular_address"], match["plural_address"]],
        "reconstruction_proof": proof,
    }
    formation_fact_id = "sha256:" + _sha256({"fact_type": "formation_evidence", "value": formation_value, "surface": surface})
    formation_fact = _base_fact(
        fact_id=formation_fact_id,
        fact_type="formation_evidence",
        value=formation_value,
        surface=surface,
        source={"source_id": f"registry:fam2-lexical:pattern:{match['pattern_id']}", "source_kind": "review_artifact"},
        source_address={"address": f"registry:fam2-lexical:pattern:{match['pattern_id']}", "source_kind": "review_artifact"},
        source_addresses=source_addresses,
        evidence_mode="paired_form_inference",
        certification={"status": "candidate", "reason": "Named pattern match remains a calibration candidate pending owner review."},
        evidence={
            "status": "source_addressed_candidate",
            "confidence": "high",
            "evidence_ids": [pair_fact_id, f"registry:{match['pattern_id']}"],
            "summary": "The named pattern reconstructs the entry-backed pair; no English gloss or morphline participates.",
        },
        rule_id=f"fam2.pattern.{match['pattern_id']}",
        projection_id=projection_id,
        guards=[
            {"guard_id": "fam2.entry_backed_singular", "reason": "The singular is present in the same entry as the observed plural."},
            {"guard_id": "fam2.named_pattern_pair", "reason": "The pattern id and written pair are matched by the registered projector."},
            {"guard_id": "fam2.exact_written_orthography", "reason": "Hamza seats, tāʾ marbūṭa, and defective spellings are not normalized."},
            {"guard_id": "fam2.no_label_inference", "reason": "A label alone cannot create this typed fact."},
            {"guard_id": "fam2.candidate_only", "reason": "No public materialization or live mutation is authorized."},
        ],
        defeaters=[],
        unresolved_blockers=[],
        dependencies={"fact_ids": [pair_fact_id], "source_addresses": source_addresses},
        derivation_chain=[{
            "step_id": "fam2.formation.from.entry_pair",
            "operation": "apply_named_pattern_to_entry_backed_pair",
            "input_fact_ids": [pair_fact_id],
            "input_source_addresses": source_addresses,
            "output": f"formation_evidence:{match['pattern_id']}:{match['plural_surface']}",
        }],
        dependent_fact_ids=[],
    )
    pair_fact["dependent_fact_ids"] = [formation_fact_id]
    record = {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam2:lexical:{loc}",
        "record_type": "projection_input",
        "canonical_occurrence": {
            "occurrence_id": f"quran:{loc}",
            "quran_loc": loc,
            "wbw_loc": f"wbw:{loc}",
            "surface": surface,
            "surface_length": len(surface),
            "entry_id": str(match["entry_id"]),
            "card_id": f"fam2:{match['entry_id']}",
        },
        "facts": [pair_fact, formation_fact],
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
                "text": "This formation claim is bound to an entry-backed pair and a named registered pattern.",
                "language": "en",
                "fact_bindings": [
                    {"fact_id": formation_fact_id, "fact_field": "fact_value.sub_shape", "surface_span_ids": ["occurrence"]},
                    {"fact_id": formation_fact_id, "fact_field": "fact_value.pattern_id", "surface_span_ids": ["occurrence"]},
                    {"fact_id": formation_fact_id, "fact_field": "fact_value.pattern_pair.name", "surface_span_ids": ["occurrence"]},
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


def _build_unresolved_record(row: Mapping[str, Any], blocker: str) -> dict[str, Any]:
    loc = _loc(row)
    surface = str(row.get("surface") or "")
    projection_status = PROJECTION_STATUS.get(blocker, "blocked")
    projection_id = f"fam2.lexical.{loc.replace(':', '.')}.pending.v1"
    source_id = f"fam2:occurrence:{loc}"
    value = {
        "occurrence": {"loc": loc, "surface": surface},
        "written_span": {"start": 0, "end": len(surface), "surface": surface},
        "status": "unresolved",
        "route": blocker,
        "reason_codes": [blocker],
        "requested_label": row.get("label_claim"),
        "entry_id": row.get("entry_id"),
        "source_fields": ["surface", "label_claim"],
    }
    fact_id = "sha256:" + _sha256({"fact_type": "formation_pending", "value": value, "surface": surface})
    quran_address = {"address": f"quran:{loc}", "source_kind": "quran_token"}
    fact = _base_fact(
        fact_id=fact_id,
        fact_type="formation_pending",
        value=value,
        surface=surface,
        source={"source_id": source_id, "source_kind": "quran_token"},
        source_address=quran_address,
        source_addresses=[quran_address],
        evidence_mode="unresolved",
        certification={"status": "pending", "reason": f"FAM2 route is {blocker}; no formation fact was emitted."},
        evidence={
            "status": "blocked",
            "confidence": "unknown",
            "evidence_ids": [f"fam2:unresolved:{loc}:{blocker}"],
            "summary": "The producer abstained because the exact formation prerequisites are incomplete.",
        },
        rule_id="fam2.abstain_without_formation_evidence",
        projection_id=projection_id,
        guards=[
            {"guard_id": "fam2.abstain_typed_route", "reason": "The family route is preserved as an explicit unresolved blocker."},
            {"guard_id": "fam2.no_label_inference", "reason": "A label, English gloss, or morphline cannot create a formation fact."},
            {"guard_id": "fam2.candidate_only", "reason": "No public materialization or live mutation is authorized."},
        ],
        defeaters=[{
            "defeater_id": blocker,
            "reason": f"The producer encountered the typed FAM2 blocker {blocker}.",
            "fact_ids": [],
        }],
        unresolved_blockers=[{"blocker_id": blocker, "reason": f"FAM2 formation route: {blocker}."}],
        dependencies={"fact_ids": [], "source_addresses": [quran_address]},
        derivation_chain=[],
        dependent_fact_ids=[],
    )
    record = {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam2:lexical:pending:{loc}",
        "record_type": "unresolved_projection",
        "canonical_occurrence": {
            "occurrence_id": f"quran:{loc}",
            "quran_loc": loc,
            "wbw_loc": f"wbw:{loc}",
            "surface": surface,
            "surface_length": len(surface),
            **({"entry_id": str(row["entry_id"])} if row.get("entry_id") else {}),
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
    pattern_registry: Any = None,
) -> dict[str, Any]:
    """Produce one candidate or typed unresolved F-A contract record."""

    registry = _registry_records(pattern_registry)
    entry = _entry_map(entries).get(str(row.get("entry_id"))) if row.get("entry_id") else None
    match, blocker = _resolve_match(row, entry, registry)
    if match is None:
        record = _build_unresolved_record(row, blocker)
    else:
        pattern = _pattern_by_id(str(match["pattern_id"]), registry)
        if pattern is None:
            record = _build_unresolved_record(row, "pattern_unresolved")
        else:
            record = _build_positive_record(row, match, pattern)
    errors = validate_formation_record(record)
    if errors:
        raise ValueError("generated FAM2 record failed validation: " + "; ".join(errors))
    return record


def validate_formation_record(record: Mapping[str, Any]) -> list[str]:
    errors = list(validate_contract_record(dict(record)))
    if errors:
        return errors
    projection = record["projection"]
    facts = record["facts"]
    formation = [fact for fact in facts if fact.get("fact_type") == "formation_evidence"]
    pairs = [fact for fact in facts if fact.get("fact_type") == "entry_form_pair"]
    pending = [fact for fact in facts if fact.get("fact_type") == "formation_pending"]
    if projection["status"] == "candidate":
        if len(formation) != 1 or len(pairs) != 1 or pending:
            errors.append("candidate FAM2 record must contain one entry_form_pair and one formation_evidence")
        if formation and pairs:
            fact = formation[0]
            pair = pairs[0]
            value = fact["fact_value"]
            if pair["fact_id"] not in fact["dependencies"]["fact_ids"]:
                errors.append("formation_evidence does not depend on the entry_form_pair")
            if not value.get("pattern_id") or not value.get("pattern_pair", {}).get("name"):
                errors.append("formation_evidence lacks a named pattern pair")
            if value.get("reconstruction_proof", {}).get("passed") is not True:
                errors.append("formation_evidence reconstruction proof did not pass")
            payload = projection.get("public_payload") or {}
            learner_copy = payload.get("learner_copy") or {}
            if payload.get("authorization_state") != "pre_apply_not_authorized":
                errors.append("FAM2 candidate does not carry pre_apply_not_authorized")
            if learner_copy.get("n_lang_clean") is not True:
                errors.append("generated FAM2 learner copy is not N-LANG clean")
            if "Ṣarf — how this piece forms the word" not in learner_copy.get("sarf", ""):
                errors.append("generated learner copy lacks the public Ṣarf label")
            if "Naḥw — what this piece does here" not in learner_copy.get("nahw", ""):
                errors.append("generated learner copy lacks the public Naḥw label")
            if projection["materialization_target"]["live_mutation_allowed"]:
                errors.append("FAM2 candidate enables live mutation")
    elif projection["status"] in {"source_gap", "producer_pending", "blocked"}:
        if formation:
            errors.append("unresolved FAM2 record must not contain formation_evidence")
        if len(pending) != 1:
            errors.append("unresolved FAM2 record must contain one formation_pending fact")
        if not any(fact.get("unresolved_blockers") for fact in facts):
            errors.append("unresolved FAM2 record lacks a typed blocker")
        if projection.get("claim") is not None:
            errors.append("unresolved FAM2 record carries a claim")
        if (projection.get("public_payload") or {}).get("authorization_state") != "pre_apply_not_authorized":
            errors.append("unresolved FAM2 record does not carry pre_apply_not_authorized")
    else:
        errors.append(f"unsupported FAM2 projection status {projection.get('status')!r}")
    return errors


def select_calibration_rows(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]] | None = None,
    *,
    limit: int | None = 40,
) -> list[dict[str, Any]]:
    source_by_loc = {
        str(row.get("loc") or row.get("quran_loc", "")).removeprefix("quran:"): row
        for row in (source_rows or [])
    }
    family_rows: list[dict[str, Any]] = []
    for row in strat_rows:
        if row.get("morphology_family") != "lexical_nouns_adjectives":
            continue
        loc = _loc(row)
        merged = copy.deepcopy(dict(source_by_loc.get(loc) or row))
        # Stratification is the owner boundary; the read-only source row only
        # supplies the exact occurrence, segments, and entry address.
        merged.update({
            "loc": loc,
            "quran_loc": f"quran:{loc}",
            "wbw_loc": f"wbw:{loc}",
            "morphology_family": row.get("morphology_family"),
            "part_of_speech": row.get("part_of_speech"),
            "morphology_family_basis": copy.deepcopy(row.get("morphology_family_basis", [])),
        })
        family_rows.append(merged)
    if limit is not None and len(family_rows) < limit:
        raise ValueError(f"FAM2 calibration requires {limit} family rows; found {len(family_rows)}")
    verdict_locs = {
        str(row.get("loc") or row.get("quran_loc", "")).removeprefix("quran:")
        for row in verdict_rows
    }
    missing = [str(row.get("loc") or row.get("quran_loc")) for row in family_rows if str(row.get("loc") or row.get("quran_loc", "")).removeprefix("quran:") not in verdict_locs]
    if missing:
        raise ValueError(f"v575 verdicts missing FAM2 locations: {missing[:5]}")
    ordered = sorted(family_rows, key=lambda row: _loc(row))
    return ordered if limit is None else ordered[:limit]


def build_calibration_packet(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]] | None = None,
    *,
    limit: int = 40,
    pattern_registry: Any = None,
) -> dict[str, Any]:
    all_rows = select_calibration_rows(strat_rows, verdict_rows, source_rows, limit=None)
    all_records = [produce_record(row, entries=entries, pattern_registry=pattern_registry) for row in all_rows]
    candidates = [record for record in all_records if record["projection"]["status"] == "candidate"]
    unresolved = [record for record in all_records if record["projection"]["status"] != "candidate"]
    records = (candidates + unresolved)[:limit]
    return {
        "records": records,
        "summary": {
            "family": "lexical_nouns_adjectives",
            "sample_size": len(records),
            "family_population": len(all_records),
            "candidate_count": sum(record["projection"]["status"] == "candidate" for record in records),
            "unresolved_count": sum(record["projection"]["status"] != "candidate" for record in records),
            "candidate_mode": "pre_apply_not_authorized",
            "materialization": "none",
            "source_inputs": "caller-supplied stratified rows, verdict rows, and entry records",
        },
    }


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
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
        "sufaha_proof": output_dir / "sufaha-proof.json",
        "sufaha_canary": output_dir / "sufaha-label-only-abstention.json",
        "fixture_positive": output_dir / "fixture-formation-facts.jsonl",
        "fixture_unresolved": output_dir / "fixture-unresolved-records.jsonl",
    }
    write_jsonl(paths["sample"], records)
    write_jsonl(paths["positive"], positive)
    write_jsonl(paths["unresolved"], unresolved)
    paths["summary"].write_text(json.dumps(packet["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    fixture_dir = ROOT / "qamus" / "examples" / "fam2-lexical"
    fixture_entries = _read_jsonl(fixture_dir / "entry-fixtures.jsonl")
    fixture_rows = {
        item["fixture_id"]: item["row"]
        for item in _read_jsonl(fixture_dir / "producer-fixtures.jsonl")
    }
    fixture_records = [
        produce_record(row, entries=fixture_entries)
        for row in fixture_rows.values()
    ]
    write_jsonl(
        paths["fixture_positive"],
        [record for record in fixture_records if record["projection"]["status"] == "candidate"],
    )
    write_jsonl(
        paths["fixture_unresolved"],
        [record for record in fixture_records if record["projection"]["status"] != "candidate"],
    )
    for fixture_id, key in (("sufaha-proof", "sufaha_proof"), ("sufaha-label-only-canary", "sufaha_canary")):
        paths[key].write_text(
            json.dumps(
                produce_record(fixture_rows[fixture_id], entries=fixture_entries),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return paths


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stratified", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--whitelist", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pattern-registry", type=Path, default=DEFAULT_PATTERN_REGISTRY)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args(argv)
    packet = build_calibration_packet(
        _read_jsonl(args.stratified),
        _read_jsonl(args.verdicts),
        _read_jsonl(args.entries),
        _read_jsonl(args.whitelist),
        limit=args.limit,
        pattern_registry=args.pattern_registry,
    )
    paths = write_calibration_packet(packet, args.output_dir)
    print(json.dumps({"summary": packet["summary"], "artifacts": sorted(path.name for path in paths.values())}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
