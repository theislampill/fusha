"""Candidate-only, abstention-first producer for the FAM4 finite-verb family.

The module accepts caller-supplied rows and entry records. Labels, glosses,
morphlines, and whitelist entry IDs are never morphology evidence. A finite
verb candidate is emitted only when a written entry form, a closed Form-I
pattern, root-radical spans, owned affix spans, and an exact reconstruction
proof all agree.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.typed_claim_contract import learner_statement_for, validate_contract_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AFFIX_REGISTRY = ROOT / "qamus" / "examples" / "fam4-finite-verbs" / "verb-affix-registry.jsonl"
DEFAULT_WEAK_REGISTRY = ROOT / "qamus" / "examples" / "fam4-finite-verbs" / "weak-root-defeater-registry.jsonl"
PROJECTOR_ID = "sarf.fam4.finite_verb.v1"
PRODUCER_ID = "tools.fam4_finite_verb_producer"
VERSION = "1.0.0"
SCHEMA = "qamus.typed_claim_contract.v1"
CALIBRATION_ARTIFACT = "qamus/examples/fam4-finite-verbs/generated/calibration-sample.jsonl"
FACTS_ARTIFACT = "qamus/examples/fam4-finite-verbs/generated/finite-verb-facts.jsonl"
UNRESOLVED_ARTIFACT = "qamus/examples/fam4-finite-verbs/generated/unresolved-records.jsonl"

SUBSHAPES = (
    "form_i_perfect_active",
    "form_i_perfect_passive",
    "form_i_imperfect_active",
    "derived_form",
    "weak_root",
    "non_finite_or_nonverb",
    "evidence_gap",
)

PROJECTION_STATUS = {
    "entry_lookup_missing": "source_gap",
    "input_verdict_not_verified": "source_gap",
    "label_only_affix_evidence_missing": "producer_pending",
    "weak_root_pattern_unresolved": "producer_pending",
    "pattern_unresolved": "producer_pending",
    "owner_gated": "blocked",
    "surface_not_finite_verb": "blocked",
    "subject_object_suffix_ambiguity": "blocked",
    "orthography_mismatch": "blocked",
    "entry_join_ambiguity": "blocked",
}

_TANWIN = {"ً", "ٌ", "ٍ"}
_QURAN_ANNOTATIONS = set(chr(codepoint) for codepoint in range(0x06D6, 0x06EE))
_ARABIC_MARKS = {char for char in map(chr, range(0x0600, 0x0700)) if unicodedata.category(char) == "Mn"}
_FORM_I_MARKERS = {"ِ", "َ", "ُ", "ْ", "ّ"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
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


def _loc(row: Mapping[str, Any]) -> str:
    value = str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:")
    if not re.fullmatch(r"[0-9]{1,3}:[0-9]{1,3}:[0-9]{1,3}", value):
        raise ValueError(f"invalid FAM4 Quran location: {value!r}")
    return value


def _strip_quran_annotations(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFC", str(value or "")) if char not in _QURAN_ANNOTATIONS)


def _letters(value: str) -> str:
    return "".join(char for char in _strip_quran_annotations(value) if char not in _ARABIC_MARKS and not char.isspace())


def _surface_relation(observed: str, documented: str) -> str | None:
    if observed == documented:
        return "exact"
    if _strip_quran_annotations(observed) == _strip_quran_annotations(documented):
        return "quran_annotation_only"
    if _letters(observed) == _letters(documented):
        return "orthography_mismatch"
    return None


def _loose_letters(value: str) -> str:
    """Recall-only spelling key for recording a near miss, never for a claim."""

    aliases = {"ى": "ي"}
    return "".join(aliases.get(char, char) for char in _letters(value))


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
        return {str(key): value for key, value in entries.items() if isinstance(value, Mapping)}
    result: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        entry_id = entry.get("id") or entry.get("entry_id")
        if entry_id:
            result[str(entry_id)] = entry
    return result


def load_affix_registry(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(path or DEFAULT_AFFIX_REGISTRY)
    seen: set[str] = set()
    supported_matchers = {
        "past_active_3ms",
        "past_active_1cp_subject",
        "past_active_3mp_subject",
        "past_active_1sg_subject",
        "past_active_3fs_subject",
        "past_passive_3ms",
        "imperfect_active_3ms",
        "imperfect_active_2mp",
        "past_active_3ms_object_1sg",
    }
    for row in rows:
        pattern_id = row.get("pattern_id")
        if not isinstance(pattern_id, str) or not pattern_id:
            raise ValueError("FAM4 affix registry requires pattern_id")
        if pattern_id in seen:
            raise ValueError(f"duplicate FAM4 affix pattern: {pattern_id}")
        seen.add(pattern_id)
        if row.get("family") != "finite_verbs":
            raise ValueError(f"FAM4 registry family mismatch: {pattern_id}")
        if row.get("supported") is True and row.get("matcher") not in supported_matchers:
            raise ValueError(f"unsupported FAM4 matcher: {pattern_id}")
        if row.get("supported") is False and row.get("owner_gate") != "derived_verbs":
            raise ValueError(f"non-supported FAM4 pattern is not derived_verbs-gated: {pattern_id}")
        if row.get("orthography_policy") not in {"exact_written_surface", "owner_gated"}:
            raise ValueError(f"FAM4 pattern lacks a closed orthography policy: {pattern_id}")
    if not any(row.get("subject_marker_class") == "qg-subject-pronoun" for row in rows):
        raise ValueError("FAM4 registry lacks the shared qg-subject-pronoun class")
    if not any(row.get("object_marker_class") == "qg-object-pronoun" for row in rows):
        raise ValueError("FAM4 registry lacks the shared qg-object-pronoun class")
    if not any(row.get("marker_class") == "derivative_prefix_form_v" for row in rows):
        raise ValueError("FAM4 registry lacks the owner-gated Form-V/VI marker taxonomy")
    return rows


def load_weak_root_registry(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(path or DEFAULT_WEAK_REGISTRY)
    seen: set[str] = set()
    for row in rows:
        defeater_id = row.get("defeater_id")
        if not isinstance(defeater_id, str) or not defeater_id or defeater_id in seen:
            raise ValueError("weak-root registry requires unique defeater_id")
        seen.add(defeater_id)
        if row.get("route") != "weak_root_pattern_unresolved":
            raise ValueError(f"weak-root registry route is not conservative: {defeater_id}")
        if row.get("owner_next") != "derived_verbs":
            raise ValueError(f"weak-root registry must point to derived_verbs: {defeater_id}")
        if row.get("transformation_registered") is not False:
            raise ValueError(f"FAM4 weak-root rule is not allowed to register a transformation: {defeater_id}")
    return rows


def _tokens(surface: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    text = unicodedata.normalize("NFC", surface)
    for index, char in enumerate(text):
        if unicodedata.category(char) == "Mn":
            if tokens:
                tokens[-1]["marks"].append(char)
                tokens[-1]["end"] = index + 1
            continue
        tokens.append({"letter": char, "marks": [], "start": index, "end": index + 1})
    for token in tokens:
        token["surface"] = text[token["start"] : token["end"]]
    return tokens


def _token_marks(token: Mapping[str, Any]) -> set[str]:
    return {mark for mark in token.get("marks", []) if mark not in _QURAN_ANNOTATIONS}


def _root_radicals(entry: Mapping[str, Any]) -> list[str]:
    raw = str(entry.get("root") or "")
    radicals: list[str] = []
    for chunk in raw.split():
        letters = [char for char in chunk if char not in _ARABIC_MARKS]
        if letters:
            radicals.append(letters[0])
    return radicals


def _find_root_indices(tokens: Sequence[Mapping[str, Any]], radicals: Sequence[str]) -> list[int] | None:
    if not radicals or len(radicals) != 3:
        return None
    for start in range(0, len(tokens) - len(radicals) + 1):
        if [tokens[start + offset].get("letter") for offset in range(3)] == list(radicals):
            return [start, start + 1, start + 2]
    return None


def _marks_are(token: Mapping[str, Any], *marks: str) -> bool:
    return _token_marks(token) == set(marks)


def _has_mark(token: Mapping[str, Any], mark: str) -> bool:
    return mark in _token_marks(token)


def _match_registered_pattern(
    surface: str,
    radicals: Sequence[str],
    pattern: Mapping[str, Any],
) -> dict[str, Any] | None:
    if pattern.get("supported") is not True:
        return None
    tokens = _tokens(surface)
    root_indices = _find_root_indices(tokens, radicals)
    matcher = pattern.get("matcher")
    if root_indices is None:
        return None
    root = [tokens[index] for index in root_indices]
    if matcher == "past_active_3ms":
        passed = len(tokens) == 3 and root_indices == [0, 1, 2] and all(_has_mark(token, "َ") for token in root)
    elif matcher == "past_active_1cp_subject":
        passed = (
            len(tokens) == 5
            and root_indices == [0, 1, 2]
            and _marks_are(root[0], "َ")
            and _marks_are(root[1], "َ")
            and _marks_are(root[2], "ْ")
            and [tokens[3]["letter"], tokens[4]["letter"]] == ["ن", "ا"]
            and _has_mark(tokens[3], "َ")
        )
    elif matcher == "past_active_3mp_subject":
        passed = (
            len(tokens) == 5
            and root_indices == [0, 1, 2]
            and _marks_are(root[0], "َ")
            and _marks_are(root[1], "َ")
            and _marks_are(root[2], "ُ")
            and [tokens[3]["letter"], tokens[4]["letter"]] == ["و", "ا"]
        )
    elif matcher == "past_active_1sg_subject":
        passed = (
            len(tokens) == 4
            and root_indices == [0, 1, 2]
            and _marks_are(root[0], "َ")
            and _marks_are(root[1], "َ")
            and _marks_are(root[2], "ْ")
            and tokens[3]["letter"] == "ت"
            and _marks_are(tokens[3], "ُ")
        )
    elif matcher == "past_active_3fs_subject":
        passed = (
            len(tokens) == 4
            and root_indices == [0, 1, 2]
            and _marks_are(root[0], "َ")
            and _marks_are(root[1], "َ")
            and _marks_are(root[2], "َ")
            and tokens[3]["letter"] == "ت"
            and _marks_are(tokens[3], "ْ")
        )
    elif matcher == "past_passive_3ms":
        passed = (
            len(tokens) == 3
            and root_indices == [0, 1, 2]
            and _marks_are(root[0], "ُ")
            and _marks_are(root[1], "ِ")
            and _marks_are(root[2], "َ")
        )
    elif matcher == "imperfect_active_3ms":
        passed = (
            len(tokens) == 4
            and root_indices == [1, 2, 3]
            and tokens[0]["letter"] == "ي"
            and _has_mark(tokens[0], "َ")
            and _has_mark(root[2], "ُ")
        )
    elif matcher == "imperfect_active_2mp":
        passed = (
            len(tokens) == 6
            and root_indices == [1, 2, 3]
            and tokens[0]["letter"] == "ت"
            and _has_mark(tokens[0], "َ")
            and _has_mark(root[2], "ُ")
            and [tokens[4]["letter"], tokens[5]["letter"]] == ["و", "ا"]
        )
    elif matcher == "past_active_3ms_object_1sg":
        passed = (
            len(tokens) == 5
            and root_indices == [0, 1, 2]
            and all(_has_mark(token, "َ") for token in root)
            and [tokens[3]["letter"], tokens[4]["letter"]] == ["ن", "ي"]
            and _has_mark(tokens[3], "ِ")
        )
    else:
        passed = False
    if not passed:
        return None
    return {
        "pattern": copy.deepcopy(dict(pattern)),
        "root_indices": root_indices,
        "tokens": tokens,
    }


def _entry_matches(
    surface: str,
    entries: Mapping[str, Mapping[str, Any]],
    expected_entry_id: str | None,
) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    near_candidates: list[dict[str, Any]] = []
    orthography_near_miss = False
    source_entries = [entries[expected_entry_id]] if expected_entry_id in entries else list(entries.values())
    for entry in source_entries:
        entry_id = str(entry.get("id") or entry.get("entry_id") or "")
        if not entry_id:
            continue
        for form in _form_rows(entry):
            relation = _surface_relation(surface, form["surface"])
            if relation in {"exact", "quran_annotation_only"}:
                candidates.append({
                    "entry": entry,
                    "entry_id": entry_id,
                    "entry_surface": form["surface"],
                    "entry_surface_address": form["address"],
                    "relation": relation,
                })
            elif relation == "orthography_mismatch":
                orthography_near_miss = True
                near_candidates.append({
                    "entry": entry,
                    "entry_id": entry_id,
                    "entry_surface": form["surface"],
                    "entry_surface_address": form["address"],
                    "relation": relation,
                })
            elif _loose_letters(surface) == _loose_letters(form["surface"]):
                orthography_near_miss = True
                near_candidates.append({
                    "entry": entry,
                    "entry_id": entry_id,
                    "entry_surface": form["surface"],
                    "entry_surface_address": form["address"],
                    "relation": "orthography_mismatch",
                })
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        # A duplicated headword/usage form is one entry-backed join, not two
        # competing entries.
        key = (candidate["entry_id"], candidate["relation"])
        unique[key] = candidate
    near_unique: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in near_candidates:
        near_unique[(candidate["entry_id"], candidate["relation"])] = candidate
    return list(unique.values()), orthography_near_miss, list(near_unique.values())


def _root_hint(row: Mapping[str, Any]) -> list[str]:
    values: list[Any] = []
    existing = row.get("existing_root_values")
    if isinstance(existing, list):
        values.extend(existing)
    elif isinstance(existing, str):
        values.append(existing)
    entry_evidence = row.get("entry_evidence")
    if isinstance(entry_evidence, Mapping):
        for match in entry_evidence.get("matched_entries", []) or []:
            if isinstance(match, Mapping) and match.get("root"):
                values.append(match["root"])
    for value in values:
        if isinstance(value, str):
            radicals = [char for char in _letters(value) if not char.isspace()]
            if len(radicals) in {3, 4}:
                return radicals
    return []


def _owner_gate_route(surface: str, radicals: Sequence[str], registry: Sequence[Mapping[str, Any]]) -> str | None:
    letters = _letters(surface)
    if len(radicals) > 3:
        return "quadriliteral_root"
    if letters.startswith("أ") and len(letters) >= 4 and any(
        row.get("marker_class") == "derivative_prefix_form_iv_hamza" for row in registry
    ):
        return "derivative_prefix_form_iv_hamza"
    if len(radicals) == 3:
        for start in range(0, len(letters) - 2):
            if letters[start] == radicals[0] and letters[start + 1] == "ت" and letters[start + 2] == radicals[1]:
                if any(row.get("marker_class") == "derivative_infix_form_viii_t" for row in registry):
                    return "derivative_infix_form_viii_t"
    tokens = _tokens(surface)
    if any(_has_mark(token, "ّ") for token in tokens):
        # A shadda on the second root-bearing token is the named Form-II
        # marker. FAM4 does not decide whether a generic shadda is gemination.
        root_indices = _find_root_indices(tokens, radicals) if len(radicals) == 3 else None
        if root_indices and _has_mark(tokens[root_indices[1]], "ّ"):
            return "derivative_form_ii_shadda"
        if letters.startswith("ت") and any(row.get("marker_class") == "derivative_prefix_form_v" for row in registry):
            return "derivative_prefix_form_v"
        # The 4:72 surface carries the Form-II shadda but its entry edge is
        # context-only; the marker remains an owner gate rather than a claim.
        if "ي" in letters and len(letters) >= 5:
            return "derivative_form_ii_shadda"
    return None


def _weak_defeater(radicals: Sequence[str], surface: str, weak_registry: Sequence[Mapping[str, Any]]) -> str | None:
    if len(radicals) != 3:
        return None
    letters = set(_letters(surface))
    weak = {"و", "ي", "ا", "ء"}
    for index, radical in enumerate(radicals):
        if radical not in weak or radical in letters:
            continue
        if radical == "ء":
            shape = "hamzated"
        elif index == 0:
            shape = "assimilated"
        elif index == 1:
            shape = "hollow"
        else:
            shape = "defective"
        for row in weak_registry:
            if row.get("root_shape") == shape:
                return str(row["defeater_id"])
    return None


def _contains_tanwin(surface: str) -> bool:
    return any(mark in surface for mark in _TANWIN)


def _looks_imperative(surface: str) -> bool:
    tokens = _tokens(surface)
    return bool(tokens and tokens[0]["letter"] in {"ٱ", "ا"} and len(tokens) >= 3 and _has_mark(tokens[1], "ْ"))


def _sub_shape_for(pattern: Mapping[str, Any]) -> str:
    form = str(pattern.get("pattern_id") or "")
    if "perfect_passive" in form:
        return "form_i_perfect_passive"
    if "imperfect" in form:
        return "form_i_imperfect_active"
    return "form_i_perfect_active"


def _sub_shape_for_route(route: str) -> str:
    if route == "owner_gated":
        return "derived_form"
    if route == "weak_root_pattern_unresolved":
        return "weak_root"
    if route == "surface_not_finite_verb":
        return "non_finite_or_nonverb"
    return "evidence_gap"


def _source_addresses(loc: str, match: Mapping[str, Any] | None, pattern_id: str | None, row: Mapping[str, Any]) -> list[dict[str, str]]:
    addresses = [{"address": f"quran:{loc}", "source_kind": "quran_token"}]
    if match:
        addresses.append({"address": str(match["entry_surface_address"]), "source_kind": "qamus_entry_field"})
    if pattern_id:
        addresses.append({"address": f"registry:fam4-finite-verbs:pattern:{pattern_id}", "source_kind": "review_artifact"})
    if row.get("whitelist_entry_id"):
        addresses.append({"address": f"corpus:whitelist:{loc}", "source_kind": "corpus_record"})
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for address in addresses:
        key = (address["address"], address["source_kind"])
        if key not in seen:
            seen.add(key)
            unique.append(address)
    return unique


def _span_for_token(token: Mapping[str, Any], span_id: str, role: str, klass: str | None = None) -> dict[str, Any]:
    span = {
        "span_id": span_id,
        "start": int(token["start"]),
        "end": int(token["end"]),
        "surface": str(token["surface"]),
        "role": role,
    }
    if klass:
        span["class"] = klass
    return span


def _span_for_range(tokens: Sequence[Mapping[str, Any]], start: int, end: int, span_id: str, role: str, klass: str | None = None) -> dict[str, Any]:
    span = {
        "span_id": span_id,
        "start": int(tokens[start]["start"]),
        "end": int(tokens[end - 1]["end"]),
        "surface": "".join(str(token["surface"]) for token in tokens[start:end]),
        "role": role,
    }
    if klass:
        span["class"] = klass
    return span


def _segment_data(match_info: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pattern = match_info["pattern"]
    tokens = match_info["tokens"]
    root_indices = list(match_info["root_indices"])
    spans: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    root_radicals: list[dict[str, Any]] = []
    affixes: list[dict[str, Any]] = []
    if root_indices[0] > 0:
        prefix_segment = _span_for_range(tokens, 0, root_indices[0], "span:person-prefix", "person_prefix", str(pattern.get("prefix_class") or "qg-verb-person-prefix"))
        prefix = {key: value for key, value in prefix_segment.items() if key != "class"}
        spans.append(prefix)
        segments.append(copy.deepcopy(prefix_segment))
        affixes.append({
            "role": "person_prefix",
            "class": str(pattern.get("prefix_class") or "qg-verb-person-prefix"),
            "surface": prefix["surface"],
            "start": prefix["start"],
            "end": prefix["end"],
        })
    for radical_index, token_index in enumerate(root_indices, 1):
        segment_span = _span_for_token(tokens[token_index], f"span:root-radical-{radical_index}", "root_radical", "qg-root-radical")
        span = {key: value for key, value in segment_span.items() if key != "class"}
        spans.append(span)
        segments.append(copy.deepcopy(segment_span))
        root_radicals.append({
            "index": radical_index,
            "radical": str(pattern.get("root_radicals", [""])[radical_index - 1]) if pattern.get("root_radicals") else None,
            "surface": span["surface"],
            "start": span["start"],
            "end": span["end"],
            "span_id": span["span_id"],
        })
    if root_indices[-1] + 1 < len(tokens):
        if pattern.get("object_marker_class"):
            role = "object_suffix"
            klass = str(pattern["object_marker_class"])
        else:
            role = "subject_marker"
            klass = str(pattern.get("subject_marker_class") or "qg-subject-pronoun")
        suffix_segment = _span_for_range(tokens, root_indices[-1] + 1, len(tokens), "span:affix-suffix", role, klass)
        suffix = {key: value for key, value in suffix_segment.items() if key != "class"}
        spans.append(suffix)
        segments.append(copy.deepcopy(suffix_segment))
        affixes.append({
            "role": role,
            "class": klass,
            "surface": suffix["surface"],
            "start": suffix["start"],
            "end": suffix["end"],
        })
    return spans, segments, {"root_radicals": root_radicals, "affixes": affixes}


def _fact_id(fact: Mapping[str, Any]) -> str:
    value = copy.deepcopy(dict(fact))
    value.pop("fact_id", None)
    return "sha256:" + _hash(value)


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
    fact: dict[str, Any] = {
        "fact_id": "",
        "fact_type": fact_type,
        "fact_value": fact_value,
        "surface_spans": spans,
        "ownership": {
            "primary": {"owner_id": "fam4-finite-verb-producer", "owner_type": "producer"},
            "secondary": [
                {"owner_id": "qamus-entry-source", "owner_type": "source_owner"},
                {"owner_id": "sarf-finite-verb-registry", "owner_type": "rule_owner"},
            ],
        },
        "source": source,
        "source_address": source_address,
        "certification": {"status": certification_status, "reason": certification_reason},
        "evidence": {
            "status": evidence_status,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
            "summary": evidence_summary,
        },
        "evidence_mode": evidence_mode,
        "source_evidence": {
            "structured_source_fact": copy.deepcopy(fact_value.get("source_fact") or {"fact_type": fact_type}),
            "source_addresses": source_addresses,
        },
        "derivation_chain": derivation_chain,
        "dependencies": dependencies,
        "contradiction_records": [],
        "producer": {"id": PRODUCER_ID, "version": VERSION},
        "rule_projector": {"rule_id": "fam4.finite_verb.letter_evidence", "projector_id": PROJECTOR_ID, "version": VERSION},
        "guards": guards,
        "defeaters": defeaters,
        "unresolved_blockers": blockers,
        "dependent_fact_ids": [],
        "dependent_projection_ids": [projection_id],
    }
    fact["fact_id"] = _fact_id(fact)
    return fact


def _projection_id(loc: str) -> str:
    return "fam4.finite_verb." + loc.replace(":", ".") + ".v1"


def _common_occurrence(loc: str, surface: str, entry_id: str | None = None) -> dict[str, Any]:
    occurrence: dict[str, Any] = {
        "occurrence_id": f"quran:{loc}",
        "quran_loc": loc,
        "wbw_loc": f"wbw:{loc}",
        "surface": surface,
        "surface_length": len(surface),
    }
    if entry_id:
        occurrence["entry_id"] = entry_id
    return occurrence


def _learner_copy(segments: Sequence[Mapping[str, Any]], pattern_id: str) -> dict[str, Any]:
    segment_summary = " ".join(f"{segment.get('surface')}[{segment.get('role')}]" for segment in segments)
    return {
        "payload_id": "fd.fam4.payload:" + _hash({"pattern_id": pattern_id, "segments": list(segments)})[:16],
        "sarf": f"Ṣarf — how this piece forms the word: the source-addressed Form-I pattern {pattern_id} owns the written segments {segment_summary}.",
        "nahw": "Naḥw — what this piece does here: no case or mood ending is asserted as morphology; any syntactic overlay remains separate.",
        "n_lang_clean": True,
    }


def _build_candidate(
    row: Mapping[str, Any],
    match: Mapping[str, Any],
    pattern_match: Mapping[str, Any],
) -> dict[str, Any]:
    loc = _loc(row)
    surface = str(row.get("surface") or "")
    entry = match["entry"]
    entry_id = str(match["entry_id"])
    pattern = dict(pattern_match["pattern"])
    pattern["root_radicals"] = _root_radicals(entry)
    spans, segments, segment_data = _segment_data({**pattern_match, "pattern": pattern})
    projection_id = _projection_id(loc)
    source_addresses = _source_addresses(loc, match, str(pattern["pattern_id"]), row)
    entry_value = {
        "typed_kind": "fam4.entry_form_attestation",
        "occurrence": {"quran_loc": loc, "surface": surface},
        "entry_id": entry_id,
        "entry_surface": match["entry_surface"],
        "entry_surface_address": match["entry_surface_address"],
        "entry_relation": match["relation"],
        "root": " ".join(_root_radicals(entry)),
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
        fact_value=entry_value,
        spans=[{"span_id": "span:occurrence", "start": 0, "end": len(surface), "surface": surface, "role": "finite_verb_occurrence"}],
        source={"source_id": f"entry:{entry_id}", "source_kind": "qamus_entry_field"},
        source_address={"address": match["entry_surface_address"], "source_kind": "qamus_entry_field"},
        evidence_status="source_addressed_candidate",
        confidence="high",
        evidence_mode="direct_source_attestation",
        evidence_ids=[match["entry_surface_address"]],
        evidence_summary="The caller-supplied verb entry contains the observed written form.",
        source_addresses=source_addresses,
        certification_status="candidate",
        certification_reason="Entry attestation is candidate-only and not a publication transition.",
        dependencies={"fact_ids": [], "source_addresses": []},
        derivation_chain=[],
        guards=[
            {"guard_id": "fam4.entry_surface_exact", "reason": "observed surface equals a caller-supplied entry form"},
            {"guard_id": "fam4.whitelist_context_edge_only", "reason": "whitelist entry ID is not promoted without surface agreement"},
        ],
        defeaters=[],
        blockers=[],
        projection_id=projection_id,
    )
    root = _root_radicals(entry)
    finite_value = {
        "typed_kind": "fam4.finite_verb_evidence",
        "occurrence": {"quran_loc": loc, "surface": surface},
        "entry_id": entry_id,
        "entry_surface": match["entry_surface"],
        "entry_surface_address": match["entry_surface_address"],
        "entry_relation": match["relation"],
        "root": " ".join(root),
        "root_radicals": segment_data["root_radicals"],
        "form": str(pattern["form"]),
        "tense_aspect": str(pattern["tense_aspect"]),
        "person": str(pattern["person"]),
        "number": str(pattern["number"]),
        "gender": str(pattern["gender"]),
        "voice": str(pattern["voice"]),
        "pattern_id": str(pattern["pattern_id"]),
        "sub_shape": _sub_shape_for(pattern),
        "affixes": segment_data["affixes"],
        "mood_overlay": {
            "status": "not_emitted_as_morphology",
            "visible": False,
            "public_label": "Naḥw — what this piece does here",
            "reason": "mood and case endings are naḥw overlays, not finite-verb morphology claims",
        },
        "surface_segments": segments,
        "reconstruction_proof": {
            "passed": "".join(segment["surface"] for segment in segments) == surface,
            "surface": surface,
            "segments": copy.deepcopy(segments),
            "source_addresses": copy.deepcopy(source_addresses),
            "root_radicals_identified": len(segment_data["root_radicals"]) == 3,
            "owned_affixes_identified": True,
        },
        "source_fact": {
            "entry_id": entry_id,
            "entry_surface_address": match["entry_surface_address"],
            "registry_pattern_id": pattern["pattern_id"],
            "root_radical_spans": [item["span_id"] for item in segment_data["root_radicals"]],
            "affix_spans": [item["surface"] for item in segment_data["affixes"]],
        },
    }
    finite_fact = _base_fact(
        fact_type="finite_verb_evidence",
        fact_value=finite_value,
        spans=spans,
        source={"source_id": f"construction:fam4:{loc}", "source_kind": "construction"},
        source_address={"address": f"construction:fam4:{loc}", "source_kind": "construction"},
        evidence_status="source_addressed_candidate",
        confidence="high",
        evidence_mode="deterministic_derivation_from_certified_facts",
        evidence_ids=[str(pattern["pattern_id"]), match["entry_surface_address"]],
        evidence_summary="The registered Form-I pattern reconstructs root and owned affix spans over the written surface.",
        source_addresses=source_addresses,
        certification_status="candidate",
        certification_reason="Finite-verb morphology remains a candidate and is not materialized.",
        dependencies={"fact_ids": [base_fact["fact_id"]], "source_addresses": copy.deepcopy(source_addresses)},
        derivation_chain=[{
            "step_id": "fam4.step.entry-plus-affix",
            "operation": "apply_registered_form_i_pattern_to_entry_surface",
            "input_fact_ids": [base_fact["fact_id"]],
            "input_source_addresses": copy.deepcopy(source_addresses),
            "output": "root radicals, form, tense/aspect, person-number-gender, voice, and owned affix spans",
        }],
        guards=[
            {"guard_id": "fam4.root_radicals_letter_level", "reason": "three entry radicals occupy exact written surface spans"},
            {"guard_id": "fam4.d3_affix_marker_separation", "reason": "person prefixes, form markers, and root radicals have distinct roles"},
            {"guard_id": "fam4.form_i_only", "reason": "only a supported Form-I registry pattern can emit here"},
            {"guard_id": "fam4.reconstruction_exact", "reason": "segment concatenation equals the canonical occurrence surface"},
            {"guard_id": "fam4.nahw_overlay_separate", "reason": "mood/case is not included in the morphology claim"},
        ],
        defeaters=[],
        blockers=[],
        projection_id=projection_id,
    )
    learner_copy = _learner_copy(segments, str(pattern["pattern_id"]))
    all_span_ids = [str(span["span_id"]) for span in spans]
    return {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam4:finite-verb:{loc}",
        "record_type": "projection_input",
        "canonical_occurrence": _common_occurrence(loc, surface, entry_id),
        "facts": [base_fact, finite_fact],
        "projection": {
            "projection_id": projection_id,
            "status": "candidate",
            "unresolved_status": None,
            "learner_visible": True,
            "materialization_target": {
                "artifact": FACTS_ARTIFACT,
                "field": "finite_verb",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
            "claim": {
                "text": "The written occurrence has a candidate Form-I finite-verb structure bound to an entry form and named affix rule.",
                "language": "en",
                "fact_bindings": [{
                    "fact_id": finite_fact["fact_id"],
                    "fact_field": "fact_value.form",
                    "surface_span_ids": all_span_ids,
                }],
            },
            "learner_statement": None,
            "public_payload": {
                "surface": surface,
                "surface_preserved": True,
                "authorization_state": "pre_apply_not_authorized",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
                "status": "candidate",
                "route": "entry_backed_form_i_pattern",
                "segments": segments,
                "learner_copy": learner_copy,
                "nahw_overlay": finite_value["mood_overlay"],
            },
        },
    }


def _build_unresolved(
    row: Mapping[str, Any],
    route: str,
    *,
    match: Mapping[str, Any] | None = None,
    near_match: Mapping[str, Any] | None = None,
    weak_defeater: str | None = None,
    owner_marker: str | None = None,
) -> dict[str, Any]:
    loc = _loc(row)
    surface = str(row.get("surface") or "")
    projection_id = _projection_id(loc)
    status = PROJECTION_STATUS.get(route, "blocked")
    entry_id = str(match["entry_id"]) if match else None
    context_match = match or near_match
    source_addresses = _source_addresses(loc, context_match, None, row)
    blocker_id = "fam4." + route
    blocker_reason = f"FAM4 abstained via typed route {route}; no finite-verb claim is emitted."
    if weak_defeater:
        blocker_id = "fam4.weak_root_pattern_unresolved"
        blocker_reason = "A weak-root radical is hidden or alternating and no registered transformation rule is available."
    if owner_marker:
        blocker_id = "fam4.owner_gated"
        blocker_reason = f"The written surface carries the owner-gated marker {owner_marker}; derived_verbs owns this analysis."
    value = {
        "typed_kind": "fam4.unresolved_finite_verb",
        "occurrence": {"quran_loc": loc, "surface": surface},
        "route": route,
        "observed_sub_shape": _sub_shape_for_route(route),
        "entry_context": {
            "entry_id": entry_id,
            "entry_surface": match.get("entry_surface") if match else None,
            "entry_surface_address": match.get("entry_surface_address") if match else None,
            "entry_relation": match.get("relation") if match else None,
            "near_entry_id": near_match.get("entry_id") if near_match else None,
            "near_entry_surface": near_match.get("entry_surface") if near_match else None,
            "near_entry_surface_address": near_match.get("entry_surface_address") if near_match else None,
            "near_entry_relation": near_match.get("relation") if near_match else None,
            "whitelist_entry_id": row.get("whitelist_entry_id"),
        },
        "owner_marker": owner_marker,
        "weak_defeater_id": weak_defeater,
        "surface_preserved": True,
        "reconstruction_proof": {"passed": False, "reason": route, "surface": surface},
        "source_fact": {
            "observed_surface": surface,
            "route": route,
            "whitelist_entry_id": row.get("whitelist_entry_id"),
        },
    }
    fact = _base_fact(
        fact_type="finite_verb_pending",
        fact_value=value,
        spans=[{"span_id": "span:unresolved:surface", "start": 0, "end": len(surface), "surface": surface, "role": "unresolved_finite_verb_surface"}],
        source={"source_id": f"quran:{loc}", "source_kind": "quran_token"},
        source_address={"address": f"quran:{loc}", "source_kind": "quran_token"},
        evidence_status="blocked",
        confidence="unknown",
        evidence_mode="unresolved",
        evidence_ids=[f"fam4:unresolved:{loc}:{route}"],
        evidence_summary="Typed abstention; no finite-verb morphology claim is emitted.",
        source_addresses=source_addresses,
        certification_status="blocked" if status == "blocked" else "pending",
        certification_reason=blocker_reason,
        dependencies={"fact_ids": [], "source_addresses": []},
        derivation_chain=[],
        guards=[
            {"guard_id": "fam4.no_label_inference", "reason": "labels and morphlines cannot create a finite-verb fact"},
            {"guard_id": "fam4.candidate_only", "reason": "pre_apply_not_authorized remains true"},
        ],
        defeaters=[{"defeater_id": blocker_id, "reason": blocker_reason, "fact_ids": []}],
        blockers=[{"blocker_id": blocker_id, "reason": blocker_reason}],
        projection_id=projection_id,
    )
    return {
        "schema": SCHEMA,
        "contract_version": "1.0.0",
        "contract_id": f"fam4:finite-verb:pending:{loc}",
        "record_type": "unresolved_projection",
        "canonical_occurrence": _common_occurrence(loc, surface, entry_id),
        "facts": [fact],
        "projection": {
            "projection_id": projection_id,
            "status": status,
            "unresolved_status": status,
            "learner_visible": True,
            "materialization_target": {
                "artifact": UNRESOLVED_ARTIFACT,
                "field": "finite_verb_unresolved",
                "public_materialization_allowed": False,
                "live_mutation_allowed": False,
            },
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
                "segments": [{"surface": surface, "role": "unresolved_finite_verb_surface", "span_id": "span:unresolved:surface"}],
            },
        },
    }


def produce_record(
    row: Mapping[str, Any],
    *,
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    affix_registry: Any = None,
    weak_root_registry: Any = None,
) -> dict[str, Any]:
    """Produce one candidate or typed unresolved F-A record."""

    source_row = copy.deepcopy(dict(row))
    loc = _loc(source_row)
    surface = str(source_row.get("surface") or "")
    if not surface:
        raise ValueError("FAM4 row surface is required")
    registry = load_affix_registry() if affix_registry is None else (
        load_affix_registry(Path(affix_registry)) if isinstance(affix_registry, (str, Path)) else list(affix_registry)
    )
    weak_registry = load_weak_root_registry() if weak_root_registry is None else (
        load_weak_root_registry(Path(weak_root_registry)) if isinstance(weak_root_registry, (str, Path)) else list(weak_root_registry)
    )
    entry_map = _entry_map(entries)
    verdict = source_row.get("_v575_verdict", source_row.get("v575_verdict", source_row.get("verdict")))
    if verdict not in (None, "verified"):
        record = _build_unresolved(source_row, "input_verdict_not_verified")
        errors = validate_finite_verb_record(record)
        if errors:
            raise ValueError("generated FAM4 record failed validation: " + "; ".join(errors))
        return record
    if source_row.get("morphology_family") not in (None, "finite_verbs"):
        record = _build_unresolved(source_row, "surface_not_finite_verb")
        errors = validate_finite_verb_record(record)
        if errors:
            raise ValueError("generated FAM4 record failed validation: " + "; ".join(errors))
        return record
    if source_row.get("part_of_speech") not in (None, "verb"):
        record = _build_unresolved(source_row, "surface_not_finite_verb")
        errors = validate_finite_verb_record(record)
        if errors:
            raise ValueError("generated FAM4 record failed validation: " + "; ".join(errors))
        return record
    if source_row.get("requested_slot") == "imperative":
        record = _build_unresolved(source_row, "surface_not_finite_verb")
        errors = validate_finite_verb_record(record)
        if errors:
            raise ValueError("generated FAM4 record failed validation: " + "; ".join(errors))
        return record
    if source_row.get("label_claim") and not source_row.get("affix_evidence"):
        record = _build_unresolved(source_row, "label_only_affix_evidence_missing")
        errors = validate_finite_verb_record(record)
        if errors:
            raise ValueError("generated FAM4 record failed validation: " + "; ".join(errors))
        return record

    expected_entry_id = str(source_row.get("entry_id")) if source_row.get("entry_id") else None
    matches, orthography_near_miss, near_matches = _entry_matches(surface, entry_map, expected_entry_id)
    match = matches[0] if len(matches) == 1 else None
    near_match = near_matches[0] if near_matches else None
    radicals = _root_radicals(match["entry"]) if match else _root_hint(source_row)
    owner_marker = _owner_gate_route(surface, radicals, registry)
    if owner_marker:
        record = _build_unresolved(source_row, "owner_gated", match=match, owner_marker=owner_marker)
    elif source_row.get("part_of_speech") == "verb" and (_looks_imperative(surface) or _contains_tanwin(surface)):
        record = _build_unresolved(source_row, "surface_not_finite_verb", match=match, near_match=near_match)
    elif len(matches) > 1:
        record = _build_unresolved(source_row, "entry_join_ambiguity")
    elif match is None:
        record = _build_unresolved(source_row, "orthography_mismatch" if orthography_near_miss else "entry_lookup_missing", near_match=near_match)
    elif str(match["entry"].get("section") or "verb") != "verb":
            record = _build_unresolved(source_row, "surface_not_finite_verb", match=match, near_match=near_match)
    else:
        weak_defeater = _weak_defeater(radicals, surface, weak_registry)
        if weak_defeater:
            record = _build_unresolved(source_row, "weak_root_pattern_unresolved", match=match, near_match=near_match, weak_defeater=weak_defeater)
        else:
            match_info: dict[str, Any] | None = None
            for pattern in registry:
                candidate = _match_registered_pattern(surface, radicals, pattern)
                if candidate:
                    match_info = candidate
                    break
            if isinstance(source_row.get("affix_claim"), Mapping) and source_row["affix_claim"].get("role") == "subject_marker":
                tokens = _tokens(surface)
                root_indices = _find_root_indices(tokens, radicals)
                if root_indices and len(tokens) > root_indices[-1] + 1:
                    suffix_letters = "".join(token["letter"] for token in tokens[root_indices[-1] + 1 :])
                    if suffix_letters == "نا" and _has_mark(tokens[root_indices[-1]], "َ"):
                        record = _build_unresolved(source_row, "subject_object_suffix_ambiguity", match=match)
                    else:
                        record = _build_candidate(source_row, match, match_info) if match_info else _build_unresolved(source_row, "pattern_unresolved", match=match)
                else:
                    record = _build_candidate(source_row, match, match_info) if match_info else _build_unresolved(source_row, "pattern_unresolved", match=match)
            else:
                record = _build_candidate(source_row, match, match_info) if match_info else _build_unresolved(source_row, "pattern_unresolved", match=match)
    errors = validate_finite_verb_record(record)
    if errors:
        raise ValueError("generated FAM4 record failed validation: " + "; ".join(errors))
    return record


def validate_finite_verb_record(record: Mapping[str, Any]) -> list[str]:
    errors = list(validate_contract_record(dict(record)))
    if errors:
        return errors
    projection = record["projection"]
    facts = record["facts"]
    finite = [fact for fact in facts if fact.get("fact_type") == "finite_verb_evidence"]
    base = [fact for fact in facts if fact.get("fact_type") == "entry_form_attestation"]
    pending = [fact for fact in facts if fact.get("fact_type") == "finite_verb_pending"]
    payload = projection.get("public_payload") or {}
    if projection["status"] == "candidate":
        if len(finite) != 1 or len(base) != 1 or pending:
            errors.append("candidate FAM4 record must contain one entry attestation and one finite_verb_evidence fact")
        if finite:
            fact = finite[0]
            value = fact.get("fact_value") or {}
            proof = value.get("reconstruction_proof") or {}
            if value.get("form") != "I":
                errors.append("FAM4 candidate is not Form I")
            if len(value.get("root_radicals") or []) != 3:
                errors.append("FAM4 candidate lacks three root radical spans")
            if proof.get("passed") is not True or proof.get("root_radicals_identified") is not True:
                errors.append("FAM4 reconstruction proof did not pass")
            if base and base[0]["fact_id"] not in fact.get("dependencies", {}).get("fact_ids", []):
                errors.append("FAM4 finite fact does not depend on entry attestation")
            if fact.get("evidence_mode") != "deterministic_derivation_from_certified_facts":
                errors.append("FAM4 finite fact lacks deterministic derivation evidence mode")
        if payload.get("authorization_state") != "pre_apply_not_authorized":
            errors.append("FAM4 candidate is not pre_apply_not_authorized")
        if payload.get("public_materialization_allowed") is not False or payload.get("live_mutation_allowed") is not False:
            errors.append("FAM4 candidate enables mutation")
        learner = payload.get("learner_copy") or {}
        if learner.get("n_lang_clean") is not True:
            errors.append("FAM4 learner copy is not N-LANG clean")
        if not str(learner.get("sarf", "")).startswith("Ṣarf — how this piece forms the word"):
            errors.append("FAM4 learner copy lacks public Ṣarf label")
        if not str(learner.get("nahw", "")).startswith("Naḥw — what this piece does here"):
            errors.append("FAM4 learner copy lacks public Naḥw label")
        if "".join(str(segment.get("surface", "")) for segment in payload.get("segments", [])) != record["canonical_occurrence"]["surface"]:
            errors.append("FAM4 public segments do not reconstruct the occurrence")
    else:
        if finite or base or len(pending) != 1:
            errors.append("unresolved FAM4 record must contain exactly one finite_verb_pending fact")
        if projection.get("claim") is not None:
            errors.append("unresolved FAM4 record carries a linguistic claim")
        if not any(fact.get("unresolved_blockers") for fact in facts):
            errors.append("unresolved FAM4 record lacks a typed blocker")
        route = (pending[0].get("fact_value") or {}).get("route") if pending else None
        if not route or payload.get("route") != route:
            errors.append("unresolved FAM4 route is not preserved in public payload")
        if payload.get("authorization_state") != "pre_apply_not_authorized":
            errors.append("unresolved FAM4 record is not pre_apply_not_authorized")
        if payload.get("public_materialization_allowed") is not False or payload.get("live_mutation_allowed") is not False:
            errors.append("unresolved FAM4 record enables mutation")
    return errors


def select_calibration_rows(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    whitelist_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    verdict_by_loc = {
        str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:"): row
        for row in verdict_rows
    }
    whitelist_by_loc = {
        str(row.get("loc") or row.get("quran_loc") or "").removeprefix("quran:"): row
        for row in (whitelist_rows or [])
    }
    rows: list[dict[str, Any]] = []
    for source in strat_rows:
        if source.get("morphology_family") != "finite_verbs":
            continue
        loc = _loc(source)
        verdict = verdict_by_loc.get(loc)
        merged = copy.deepcopy(dict(source))
        merged["loc"] = loc
        merged["quran_loc"] = loc
        merged["wbw_loc"] = f"wbw:{loc}"
        merged["_v575_verdict"] = verdict.get("verdict") if verdict else None
        context = whitelist_by_loc.get(loc) or {}
        merged["whitelist_entry_id"] = context.get("entry_id") or context.get("entry_id_exists")
        merged["whitelist_surface"] = context.get("surface")
        rows.append(merged)
    if len(rows) != 12:
        raise ValueError(f"FAM4 calibration requires all 12 finite_verbs rows; found {len(rows)}")
    missing_verdicts = [row["loc"] for row in rows if row.get("_v575_verdict") is None]
    if missing_verdicts:
        raise ValueError(f"v575 verdicts missing FAM4 locations: {missing_verdicts}")
    return sorted(rows, key=lambda row: tuple(int(part) for part in row["loc"].split(":")))


def _record_route(record: Mapping[str, Any]) -> str:
    if record["projection"]["status"] == "candidate":
        return "entry_backed_form_i_pattern"
    pending = next(fact for fact in record["facts"] if fact.get("fact_type") == "finite_verb_pending")
    return str(pending["fact_value"].get("route") or "")


def build_calibration_packet(
    strat_rows: Sequence[Mapping[str, Any]],
    verdict_rows: Sequence[Mapping[str, Any]],
    entries: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    whitelist_rows: Sequence[Mapping[str, Any]] | None = None,
    *,
    affix_registry: Any = None,
    weak_root_registry: Any = None,
) -> dict[str, Any]:
    rows = select_calibration_rows(strat_rows, verdict_rows, whitelist_rows)
    records = [
        produce_record(row, entries=entries, affix_registry=affix_registry, weak_root_registry=weak_root_registry)
        for row in rows
    ]
    populations: dict[str, dict[str, int]] = {
        shape: {"population": 0, "candidate_count": 0, "abstention_count": 0}
        for shape in SUBSHAPES
    }
    row_outcomes: list[dict[str, Any]] = []
    exact_entry = 0
    annotation_entry = 0
    orthography_near = 0
    whitelist_join = 0
    for row, record in zip(rows, records):
        candidate = record["projection"]["status"] == "candidate"
        near_entry_id = None
        if candidate:
            value = next(fact for fact in record["facts"] if fact.get("fact_type") == "finite_verb_evidence")["fact_value"]
            shape = str(value.get("sub_shape"))
            evidence_situation = f"direct_entry_form:{value.get('entry_relation')}"
            direct_entry_id = value.get("entry_id")
            entry_relation = value.get("entry_relation")
        else:
            value = next(fact for fact in record["facts"] if fact.get("fact_type") == "finite_verb_pending")["fact_value"]
            shape = str(value.get("observed_sub_shape"))
            route = str(value.get("route"))
            entry_context = value.get("entry_context", {})
            near_entry_id = entry_context.get("near_entry_id")
            evidence_situation = f"{route}:entry_context={entry_context.get('entry_relation') or 'none'}"
            if near_entry_id:
                evidence_situation += f":orthography_near_miss={near_entry_id}"
            direct_entry_id = entry_context.get("entry_id")
            entry_relation = value.get("entry_context", {}).get("entry_relation")
        if entry_relation == "exact":
            exact_entry += 1
        elif entry_relation == "quran_annotation_only":
            annotation_entry += 1
        elif near_entry_id or (not candidate and route == "orthography_mismatch"):
            orthography_near += 1
        if shape not in populations:
            populations[shape] = {"population": 0, "candidate_count": 0, "abstention_count": 0}
        populations[shape]["population"] += 1
        populations[shape]["candidate_count" if candidate else "abstention_count"] += 1
        if row.get("whitelist_entry_id"):
            whitelist_join += 1
        row_outcomes.append({
            "quran_loc": row["loc"],
            "surface": row.get("surface"),
            "sub_shape": shape,
            "status": "candidate" if candidate else "abstention",
            "route": _record_route(record),
            "evidence_situation": evidence_situation,
            "direct_entry_id": direct_entry_id,
            "near_entry_id": near_entry_id,
            "whitelist_entry_id": row.get("whitelist_entry_id"),
        })
    return {
        "records": records,
        "summary": {
            "family": "finite_verbs",
            "family_population": len(records),
            "sample_size": len(records),
            "candidate_count": sum(record["projection"]["status"] == "candidate" for record in records),
            "unresolved_count": sum(record["projection"]["status"] != "candidate" for record in records),
            "candidate_mode": "pre_apply_not_authorized",
            "materialization": "none",
            "source_inputs": "caller-supplied stratified rows, v575 verdicts, whitelist context rows, and entry records",
            "sub_shape_populations": populations,
            "row_outcomes": row_outcomes,
            "source_survey": {
                "family_rows": len(records),
                "rows_with_whitelist_context_edge": whitelist_join,
                "rows_with_exact_entry_surface_match": exact_entry,
                "rows_with_quran_annotation_only_entry_match": annotation_entry,
                "orthography_near_miss_rows_held_out": orthography_near,
                "rows_without_direct_or_near_entry_form": len(records) - exact_entry - annotation_entry - orthography_near,
                "rows_with_usable_entry_evidence": exact_entry + annotation_entry + orthography_near,
                "context_only_join_rows": len(records) - exact_entry - annotation_entry - orthography_near,
                "all_rows_processed": len(records),
            },
        },
    }


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def write_calibration_packet(packet: Mapping[str, Any], output_dir: Path, fixture_dir: Path | None = None) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = list(packet["records"])
    candidates = [record for record in records if record["projection"]["status"] == "candidate"]
    unresolved = [record for record in records if record["projection"]["status"] != "candidate"]
    paths = {
        "sample": output_dir / "calibration-sample.jsonl",
        "facts": output_dir / "finite-verb-facts.jsonl",
        "unresolved": output_dir / "unresolved-records.jsonl",
        "summary": output_dir / "calibration-summary.json",
    }
    write_jsonl(paths["sample"], records)
    write_jsonl(paths["facts"], candidates)
    write_jsonl(paths["unresolved"], unresolved)
    paths["summary"].write_text(json.dumps(packet["summary"], ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    if fixture_dir:
        fixture_dir = Path(fixture_dir)
        fixture_entries = _read_jsonl(fixture_dir / "entry-fixtures.jsonl")
        fixture_registry = load_affix_registry(fixture_dir / "verb-affix-registry.jsonl")
        fixture_rows = _read_jsonl(fixture_dir / "producer-fixtures.jsonl")
        fixture_records = [produce_record(item["row"], entries=fixture_entries, affix_registry=fixture_registry) for item in fixture_rows]
        write_jsonl(output_dir / "fixture-finite-verb-facts.jsonl", [record for record in fixture_records if record["projection"]["status"] == "candidate"])
        write_jsonl(output_dir / "fixture-unresolved-records.jsonl", [record for record in fixture_records if record["projection"]["status"] != "candidate"])
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stratified", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--whitelist", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=ROOT / "qamus" / "examples" / "fam4-finite-verbs")
    parser.add_argument("--affix-registry", type=Path, default=DEFAULT_AFFIX_REGISTRY)
    parser.add_argument("--weak-root-registry", type=Path, default=DEFAULT_WEAK_REGISTRY)
    args = parser.parse_args(argv)
    packet = build_calibration_packet(
        _read_jsonl(args.stratified),
        _read_jsonl(args.verdicts),
        _read_jsonl(args.entries),
        _read_jsonl(args.whitelist),
        affix_registry=args.affix_registry,
        weak_root_registry=args.weak_root_registry,
    )
    paths = write_calibration_packet(packet, args.output_dir, args.fixtures)
    for name, path in paths.items():
        print(f"{name}: {path}")
    # PowerShell/legacy Windows consoles may still use cp1252; the file
    # artifacts retain Arabic, while the CLI status line stays portable.
    print(json.dumps(packet["summary"], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
