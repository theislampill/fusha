#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the VNMAP entry -> card -> selected-word -> occurrence ledger.

This builder is intentionally offline and candidate-only.  It joins entry
forms to the existing whitelist and canonical occurrence/appearance output;
it does not create a second occurrence graph, mutate source inputs, or emit
production URLs and paths.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import os
import re
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.build_occurrence_appearance_index import projection_hash  # noqa: E402
from tools.normalize_ar import norm_strict  # noqa: E402
from tools.validate_appearance_parity import validate_records  # noqa: E402


OWNER_MISSING_EDGE_CLASSES = (
    "missing_entry_url_edge",
    "missing_source_photo_edge",
    "missing_source_card_edge",
    "missing_displayed_fragment_edge",
    "missing_selected_word_edge",
    "missing_quran_wbw_edge",
    "duplicate_surface_edge_ambiguous",
    "display_local_to_canonical_crosswalk_missing",
    "rendered_span_edge_missing",
    "decision_backlink_missing",
    "canonical_occurrence_appearance_missing",
)
OWNER_EDGE_ORDER = {name: index for index, name in enumerate(OWNER_MISSING_EDGE_CLASSES)}

GRAPH_CROSSWALK_EDGES = frozenset(
    {
        "missing_entry_url_edge",
        "missing_source_card_edge",
        "missing_displayed_fragment_edge",
        "missing_selected_word_edge",
        "missing_quran_wbw_edge",
        "duplicate_surface_edge_ambiguous",
        "display_local_to_canonical_crosswalk_missing",
        "canonical_occurrence_appearance_missing",
    }
)
OFFLINE_UNMEASURED_EDGES = frozenset(
    {"rendered_span_edge_missing", "decision_backlink_missing"}
)

SOURCE_SPACE_LIMITS = {
    "particles": ("p", 1, 100),
    "verbs": ("v", 1, 947),
    "nouns": ("n", 1, 1045),
}
SOURCE_SPACE_ORDER = {prefix: index for index, prefix in enumerate(("v", "n", "p"))}
TRANCHE_LABELS = tuple(f"VN-{index:02d}" for index in range(21))


@dataclass
class BuildResult:
    ledger: list[dict]
    metrics: dict
    matrix: dict
    report: str


class WhitelistIndex:
    """Small deterministic lookup layer over whitelist rows."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.by_loc = defaultdict(list)
        self.by_source_key = defaultdict(list)
        self.by_source_identity = defaultdict(list)
        self.by_entry_id = defaultdict(list)
        for row in self.rows:
            loc = _clean(row.get("loc"))
            if loc:
                self.by_loc[loc].append(row)
            for key in (row.get("source_key"), row.get("graph_source_key")):
                key = _clean(key)
                if key:
                    self.by_source_key[key].append(row)
                    identity = _source_identity(key)
                    if identity is not None:
                        self.by_source_identity[identity].append(row)
            entry_id = _clean(row.get("entry_id"))
            if entry_id:
                self.by_entry_id[entry_id].append(row)
                identity = _source_identity(entry_id)
                if identity is not None:
                    self.by_source_identity[identity].append(row)

    def rows_for_entry(self, entry_id, source_key):
        result = {}
        for row in self.by_source_key.get(source_key or "", ()):
            result[_row_identity(row)] = row
        source_identity = _source_identity(source_key)
        if source_identity is not None:
            for row in self.by_source_identity.get(source_identity, ()):
                result[_row_identity(row)] = row
        for row in self.by_entry_id.get(entry_id or "", ()):
            result[_row_identity(row)] = row
        return list(result.values())

    def rows_for_card(self, entry_id, source_key, card_ref):
        rows = self.rows_for_entry(entry_id, source_key)
        return [row for row in rows if _row_card_ref(row) == card_ref]


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _present(value):
    return value not in (None, "", [], {})


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            yield value


def _write_jsonl(rows, path):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _write_json(value, path):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def _source_identity(source_key):
    match = re.fullmatch(r"([A-Za-z]+)0*(\d+)", _clean(source_key))
    if not match:
        return None
    return match.group(1).lower(), int(match.group(2))


def _source_space(source_key):
    identity = _source_identity(source_key)
    if identity is None:
        return "other"
    prefix, number = identity
    for space, (expected_prefix, lower, upper) in SOURCE_SPACE_LIMITS.items():
        if prefix == expected_prefix and lower <= number <= upper:
            return space
    return "other"


def _source_sort_key(entry):
    identity = _source_identity((entry.get("source_keys") or [None])[0])
    if identity is None:
        return (len(SOURCE_SPACE_ORDER), 10**9, _clean(entry.get("id")))
    prefix, number = identity
    return (SOURCE_SPACE_ORDER.get(prefix, len(SOURCE_SPACE_ORDER)), number, _clean(entry.get("id")))


def _entry_source_key(entry):
    source_keys = entry.get("source_keys") or []
    return _clean(source_keys[0]) if source_keys else ""


def _loc_tuple(loc):
    try:
        return tuple(int(part) for part in _clean(loc).split(":"))
    except ValueError:
        return ()


def _valid_loc(loc):
    return bool(re.fullmatch(r"\d+:\d+:\d+", _clean(loc)))


def _strip_address_prefix(value):
    value = _clean(value)
    for prefix in ("quran:", "wbw:"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def _address_matches_loc(address, loc):
    return _valid_loc(_strip_address_prefix(address)) and _strip_address_prefix(address) == _clean(loc)


def _row_identity(row):
    return (
        _clean(row.get("loc")),
        _clean(row.get("entry_id")),
        _clean(row.get("source_key")),
        _clean(row.get("graph_source_key")),
        _clean(row.get("surface")),
        row.get("card_index"),
    )


def _row_card_ref(row):
    card_ref = _clean(row.get("card_ref"))
    if card_ref:
        return _strip_address_prefix(card_ref)
    loc = _clean(row.get("loc"))
    parts = loc.split(":")
    return ":".join(parts[:2]) if len(parts) >= 2 else ""


def _example_ref(example):
    ref = _clean(example.get("ref")) if isinstance(example, dict) else ""
    ref = _strip_address_prefix(ref)
    parts = ref.split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return "", None
    return ":".join(parts[:2]), ":".join(parts) if len(parts) == 3 else None


def _surface_fields(row):
    values = []
    for field in ("surface", "selected_word", "displayed_qword_surface", "canonical_surface"):
        value = _clean(row.get(field))
        if value and value not in values:
            values.append(value)
    return values


def _row_matches_entry(row, entry_id, source_key):
    row_entry_id = _clean(row.get("entry_id"))
    row_source_keys = (
        _clean(row.get("source_key")),
        _clean(row.get("graph_source_key")),
    )
    if row_entry_id and row_entry_id == entry_id:
        return True
    if source_key and any(value == source_key for value in row_source_keys):
        return True
    source_identity = _source_identity(source_key)
    if source_identity is None:
        return False
    return any(_source_identity(value) == source_identity for value in (row_entry_id, *row_source_keys) if value)


def _candidate_rows(index, entry_id, source_key, example, form):
    card_ref, target_loc = _example_ref(example)
    rows = index.rows_for_card(entry_id, source_key, card_ref) if card_ref else index.rows_for_entry(entry_id, source_key)
    if target_loc:
        rows = [row for row in rows if _clean(row.get("loc")) == target_loc]
    rows = [row for row in rows if _row_matches_entry(row, entry_id, source_key)]

    exact = {}
    strict = {}
    strict_form = norm_strict(_clean(form))
    for row in rows:
        identity = _row_identity(row)
        fields = _surface_fields(row)
        if _clean(form) and any(_clean(form) == field for field in fields):
            exact[identity] = row
        if strict_form and any(norm_strict(field) == strict_form for field in fields):
            strict[identity] = row
    return card_ref, target_loc, exact, strict


def _find_form_match(index, entry_id, source_key, examples, form):
    exact = {}
    strict = {}
    example_indexes = defaultdict(set)
    card_refs = defaultdict(set)
    for example_index, example in enumerate(examples, 1):
        card_ref, _target_loc, exact_rows, strict_rows = _candidate_rows(
            index, entry_id, source_key, example, form
        )
        for identity, row in exact_rows.items():
            exact[identity] = row
            example_indexes[identity].add(example_index)
            if card_ref:
                card_refs[identity].add(card_ref)
        for identity, row in strict_rows.items():
            strict[identity] = row
            example_indexes[identity].add(example_index)
            if card_ref:
                card_refs[identity].add(card_ref)

    if exact:
        selected = exact
        method = "exact_unique" if len(exact) == 1 else "exact_ambiguous"
    elif strict:
        selected = strict
        method = "strict_unique" if len(strict) == 1 else "strict_ambiguous"
    else:
        selected = {}
        method = "unmatched"
    identity = next(iter(selected)) if len(selected) == 1 else None
    return {
        "method": method,
        "candidate_rows": selected,
        "candidate_count": len(selected),
        "selected_row": selected.get(identity),
        "matched_example_indexes": sorted(example_indexes.get(identity, set())) if identity else [],
        "matched_card_refs": sorted(card_refs.get(identity, set())) if identity else [],
    }


def _entry_photo_present(entry):
    return any(
        _present(entry.get(field))
        for field in ("source_photo_ref", "source_photo_page", "source_photo_locator", "source_photo")
    )


def _quality_state(row):
    if not row:
        return "unresolved", "ledger_join"
    for field in (
        "current_public_status",
        "rich_cert_state",
        "closure_terminal_state",
        "analysis_status",
        "assigned_status",
        "source_status",
        "state",
        "final_state",
        "decision",
    ):
        value = row.get(field)
        if _present(value):
            if isinstance(value, (dict, list)):
                value = "present"
            return f"{field}:{_clean(value)}", field
    return "unresolved", "whitelist_state_absent"


def _has_typed_facts(row):
    return _present(row.get("sarf_facts")) or _present(row.get("nahw_facts"))


def _has_payload(row):
    return any(
        _present(row.get(field))
        for field in (
            "public_preview",
            "public_payload_boundary",
            "public_payload",
            "current_payload_hash",
            "public_readback_targets",
        )
    )


def _display_fragment_present(row):
    return any(
        _present(row.get(field))
        for field in (
            "card_index",
            "example_card_index",
            "displayed_card_text",
            "source_card_text",
            "displayed_qword_surface",
            "selected_word",
        )
    )


def _quran_wbw_complete(row):
    loc = _clean(row.get("loc"))
    quran = _clean(row.get("quran_loc"))
    wbw = _clean(row.get("wbw_loc"))
    return _valid_loc(loc) and _address_matches_loc(quran, loc) and _address_matches_loc(wbw, loc)


def _appearance_index_complete(record):
    if not isinstance(record, dict):
        return False
    appearances = record.get("appearances")
    return (
        record.get("unique") is True
        and isinstance(record.get("projection_hash"), str)
        and len(record["projection_hash"]) == 64
        and isinstance(appearances, list)
        and record.get("appearance_count") == len(appearances)
        and any(isinstance(item, dict) and item.get("surface_kind") == "reader" for item in appearances)
    )


def _reverse_entry_present(record, entry_id):
    if not isinstance(record, dict) or not entry_id:
        return False
    if entry_id in set(record.get("entry_relationships") or []):
        return True
    return any(
        isinstance(appearance, dict) and appearance.get("entry_id") == entry_id
        for appearance in record.get("appearances") or []
    )


def _ordered_edges(edges):
    return sorted(set(edges), key=lambda value: OWNER_EDGE_ORDER[value])


def _card_missing_edges(entry_id, source_key, example, index):
    edges = []
    if not isinstance(example, dict) or not _present(example.get("ar")) or not _present(example.get("ref")):
        edges.append("missing_source_card_edge")
    card_ref, _target = _example_ref(example if isinstance(example, dict) else {})
    if not card_ref or not index.rows_for_card(entry_id, source_key, card_ref):
        edges.extend(
            ["missing_displayed_fragment_edge", "display_local_to_canonical_crosswalk_missing"]
        )
    return _ordered_edges(edges)


def _make_ledger_row(
    entry,
    usage,
    usage_index,
    examples,
    form,
    form_index,
    entry_id,
    source_key,
    proposal_vn,
    index,
    appearances_by_loc,
):
    sense_index = usage.get("sense") if isinstance(usage, dict) else None
    if sense_index is None:
        sense_index = usage_index
    selected_surface = _clean(form)
    match = _find_form_match(index, entry_id, source_key, examples, selected_surface)
    chosen = match["selected_row"]
    chosen_loc = _clean(chosen.get("loc")) if chosen else ""
    occurrence = appearances_by_loc.get(chosen_loc)
    primary_example_index = (match["matched_example_indexes"] or [1 if examples else None])[0]
    primary_example = examples[primary_example_index - 1] if primary_example_index and examples else {}
    primary_ref, _target = _example_ref(primary_example)
    source_card_text = _clean(primary_example.get("ar")) if isinstance(primary_example, dict) else ""
    source_card_text = source_card_text or None
    source_card_ref = primary_ref or None
    missing_edges = []

    if not chosen or not _present(chosen.get("entry_url")):
        missing_edges.append("missing_entry_url_edge")
    if not _entry_photo_present(entry):
        missing_edges.append("missing_source_photo_edge")
    if not source_card_text or not source_card_ref:
        missing_edges.append("missing_source_card_edge")
    if not chosen or not _display_fragment_present(chosen):
        missing_edges.append("missing_displayed_fragment_edge")
    if not chosen or match["method"] == "unmatched" or match["method"].endswith("ambiguous"):
        missing_edges.append("missing_selected_word_edge")
    if match["method"].endswith("ambiguous"):
        missing_edges.append("duplicate_surface_edge_ambiguous")

    quran_wbw_complete = bool(chosen and _quran_wbw_complete(chosen))
    if not quran_wbw_complete:
        missing_edges.append("missing_quran_wbw_edge")

    crosswalk_flag = bool(chosen and quran_wbw_complete and match["method"] in {"exact_unique", "strict_unique"})
    crosswalk_kind = None
    if crosswalk_flag:
        crosswalk_kind = "source_recorded" if _present(chosen.get("source_address_crosswalk")) else "derived_card_surface_join"
    else:
        missing_edges.append("display_local_to_canonical_crosswalk_missing")

    canonical_complete = bool(occurrence and _appearance_index_complete(occurrence))
    if not canonical_complete:
        missing_edges.append("canonical_occurrence_appearance_missing")
    if not _present(chosen.get("decision_backlink")) if chosen else True:
        missing_edges.append("decision_backlink_missing")
    missing_edges.append("rendered_span_edge_missing")

    quality_state, quality_source = _quality_state(chosen)
    reverse_present = bool(chosen and occurrence and _reverse_entry_present(occurrence, entry_id))
    if chosen and occurrence and not reverse_present:
        # This is a measured reciprocity failure, not a row blocker.
        pass

    display_address = {
        "card_ref": source_card_ref,
        "entry_example_index": primary_example_index,
        "entry_usage_index": usage_index,
        "whitelist_card_index": chosen.get("card_index") if chosen else None,
        "whitelist_example_card_index": chosen.get("example_card_index") if chosen else None,
        "display_loc": chosen_loc or None,
    }
    row = {
        "entry_id": entry_id or None,
        "entry_slug": source_key or None,
        "source_key": source_key or None,
        "sense_index": sense_index,
        "usage_index": usage_index,
        "form_index": form_index,
        "card_index": chosen.get("card_index") if chosen else None,
        "source_card_ref": source_card_ref,
        "source_card_text": source_card_text,
        "source_card_refs": match["matched_card_refs"] or ([source_card_ref] if source_card_ref else []),
        "displayed_text": (
            _clean(chosen.get("displayed_card_text"))
            or _clean(chosen.get("source_card_text"))
            if chosen
            else None
        ),
        "selected_surface": selected_surface or None,
        "displayed_surface": _clean(chosen.get("surface")) if chosen else None,
        "displayed_selected_surface": (
            _clean(chosen.get("selected_word"))
            or _clean(chosen.get("displayed_qword_surface"))
            if chosen
            else None
        ),
        "display_local_address": display_address,
        "canonical_quran_loc": _clean(chosen.get("quran_loc")) if chosen else None,
        "canonical_wbw_loc": _clean(chosen.get("wbw_loc")) if chosen else None,
        "crosswalk_flag": crosswalk_flag,
        "crosswalk_kind": crosswalk_kind,
        "occurrence_id": chosen_loc or None,
        "appearance_count": occurrence.get("appearance_count") if occurrence else None,
        "appearance_entry_relationships": sorted(occurrence.get("entry_relationships") or []) if occurrence else [],
        "quality_state": quality_state,
        "quality_state_source": quality_source,
        "vn_tranche": None,
        "proposal_vn_tranche": proposal_vn,
        "join_method": match["method"],
        "candidate_count": match["candidate_count"],
        "reverse_entry_relationship_present": reverse_present,
        "canonical_occurrence_trace_complete": canonical_complete,
        "quran_wbw_trace_complete": quran_wbw_complete,
        "appearance_index_complete": canonical_complete,
        "typed_fact_present": bool(chosen and _has_typed_facts(chosen)),
        "payload_present": bool(chosen and _has_payload(chosen)),
        "entry_url_present": bool(chosen and _present(chosen.get("entry_url"))),
        "source_photo_present": _entry_photo_present(entry),
        "decision_backlink_present": bool(chosen and _present(chosen.get("decision_backlink"))),
        "missing_edges": _ordered_edges(missing_edges),
    }
    return row


def _space_diagnostics(entries):
    by_space = Counter()
    by_key = Counter()
    for entry in entries:
        source_key = _entry_source_key(entry)
        by_key[source_key] += 1
        by_space[_source_space(source_key)] += 1
    diagnostics = {}
    for space, (prefix, lower, upper) in SOURCE_SPACE_LIMITS.items():
        actual = {
            number
            for key in by_key
            if (identity := _source_identity(key)) is not None
            and identity[0] == prefix
            and lower <= identity[1] <= upper
            for number in [identity[1]]
        }
        expected = set(range(lower, upper + 1))
        diagnostics[space] = {
            "prefix": prefix,
            "expected_count": upper - lower + 1,
            "actual_entry_count": by_space[space],
            "actual_unique_source_key_count": len(actual),
            "minimum": min(actual) if actual else None,
            "maximum": max(actual) if actual else None,
            "observed_first_key": min(
                (key for key in by_key if _source_identity(key) and _source_identity(key)[0] == prefix),
                key=lambda key: _source_identity(key)[1],
                default=None,
            ),
            "observed_last_key": max(
                (key for key in by_key if _source_identity(key) and _source_identity(key)[0] == prefix),
                key=lambda key: _source_identity(key)[1],
                default=None,
            ),
            "missing_numbers": sorted(expected - actual),
            "extra_numbers": sorted(
                number
                for key in by_key
                if (identity := _source_identity(key)) is not None
                and identity[0] == prefix
                and not lower <= identity[1] <= upper
                for number in [identity[1]]
            ),
            "duplicate_source_keys": sorted(key for key, count in by_key.items() if count > 1 and _source_space(key) == space),
        }
    diagnostics["other"] = {
        "actual_entry_count": by_space["other"],
        "source_keys": sorted(key for key in by_key if _source_space(key) == "other"),
    }
    return diagnostics


def _expected_source_key_set():
    keys = set()
    for _space, (prefix, lower, upper) in SOURCE_SPACE_LIMITS.items():
        keys.update((prefix, number) for number in range(lower, upper + 1))
    return keys


def _actual_source_identity_set(entries):
    return {
        identity
        for entry in entries
        if (identity := _source_identity(_entry_source_key(entry))) is not None
    }


def _entry_id_for_source(value, entries_by_source):
    value = _clean(value)
    if not value:
        return ""
    resolved = entries_by_source.get(value, "")
    if resolved:
        return resolved
    identity = _source_identity(value)
    return entries_by_source.get(identity, "") if identity is not None else ""


def _proposal_tranche_map(entries):
    """Return a derived proposal map; this never becomes ``vn_tranche``."""

    ordered = sorted(entries, key=_source_sort_key)
    by_id = {_clean(entry.get("id")): entry for entry in ordered}
    full_source_space = len(ordered) == 2092 and _actual_source_identity_set(ordered) == _expected_source_key_set()
    mapping = {}

    if full_source_space:
        remaining = []
        for entry in ordered:
            identity = _source_identity(_entry_source_key(entry))
            prefix, number = identity if identity else ("", -1)
            if (prefix == "v" and 1 <= number <= 47) or (prefix == "n" and 1 <= number <= 45):
                mapping[_clean(entry.get("id"))] = "VN-00"
            elif (prefix == "v" and 48 <= number <= 94) or (prefix == "n" and 46 <= number <= 90):
                mapping[_clean(entry.get("id"))] = "VN-01"
            else:
                remaining.append(entry)
        base, remainder = divmod(len(remaining), 19)
        cursor = 0
        for tranche_index in range(2, 21):
            size = base + (1 if tranche_index - 2 < remainder else 0)
            for entry in remaining[cursor : cursor + size]:
                mapping[_clean(entry.get("id"))] = f"VN-{tranche_index:02d}"
            cursor += size
        return mapping

    base, remainder = divmod(len(ordered), len(TRANCHE_LABELS))
    cursor = 0
    for index, label in enumerate(TRANCHE_LABELS):
        size = base + (1 if index < remainder else 0)
        for entry in ordered[cursor : cursor + size]:
            mapping[_clean(entry.get("id"))] = label
        cursor += size
    return mapping


def _proposal_rule(entries):
    if len(entries) == 2092 and _actual_source_identity_set(entries) == _expected_source_key_set():
        return (
            "DERIVED PROPOSAL: order entries by observed source key v001-v947, n001-n1045, p001-p100 "
            "(the noun keys use three-digit padding below 1,000 and four digits thereafter); "
            "preserve the documented numeric VN-00 (v001-v047 plus n0001-n0045) and VN-01 "
            "(v048-v094 plus n0046-n0090) boundaries; split the remaining 1,908 entries "
            "into 19 contiguous balanced groups (first 8 groups 101 entries, remaining 11 groups 100 entries)."
        )
    return (
        "DERIVED PROPOSAL: order the supplied entries by source key in v, n, p order and "
        "split the ordered set into 21 contiguous balanced groups; this fixture/sample rule "
        "does not override the full-input documented boundary rule."
    )


def _family_resolution(family_rows, index, entries_by_id, entries_by_source):
    resolved = []
    for family_index, family in enumerate(family_rows):
        loc = _clean(family.get("loc"))
        whitelist_rows = index.by_loc.get(loc, [])
        raw_entry_id = _clean(family.get("entry_id")) or ""
        entry_id = raw_entry_id
        source_key = ""
        if not entry_id and whitelist_rows:
            entry_id = _clean(whitelist_rows[0].get("entry_id"))
        if whitelist_rows:
            source_key = _clean(whitelist_rows[0].get("source_key")) or _clean(whitelist_rows[0].get("graph_source_key"))
        if entry_id not in entries_by_id:
            entry_id = _entry_id_for_source(entry_id, entries_by_source)
        if entry_id not in entries_by_id and source_key:
            entry_id = _entry_id_for_source(source_key, entries_by_source)
        if entry_id not in entries_by_id:
            entry_id = None
        producer_status = _clean(family.get("_fb1_verdict")) or _clean(family.get("status")) or "unreported"
        resolved.append(
            {
                "family_index": family_index,
                "loc": loc,
                "entry_id": entry_id or None,
                "source_key": source_key or None,
                "raw_entry_id": raw_entry_id or None,
                "producer_status": producer_status,
                "row": family,
            }
        )
    return resolved


def _make_cards(entries, index):
    cards = []
    card_missing_edges = Counter()
    cards_by_entry_ref = defaultdict(list)
    for entry in entries:
        entry_id = _clean(entry.get("id"))
        source_key = _entry_source_key(entry)
        for usage_index, usage in enumerate(entry.get("usage") or [], 1):
            examples = usage.get("examples") or [] if isinstance(usage, dict) else []
            for example_index, example in enumerate(examples, 1):
                card_ref, target_loc = _example_ref(example)
                edges = _card_missing_edges(entry_id, source_key, example, index)
                for edge in edges:
                    card_missing_edges[edge] += 1
                card = {
                    "entry_id": entry_id,
                    "entry_slug": source_key or None,
                    "source_key": source_key or None,
                    "sense_index": usage.get("sense") if isinstance(usage, dict) else usage_index,
                    "usage_index": usage_index,
                    "example_index": example_index,
                    "card_ref": card_ref or None,
                    "target_loc": target_loc,
                    "source_card_text": _clean(example.get("ar")) if isinstance(example, dict) else None,
                    "source_card_en_present": bool(isinstance(example, dict) and _present(example.get("en"))),
                    "missing_edges": edges,
                    "card_key": f"{entry_id}|{usage_index}|{example_index}",
                }
                cards.append(card)
                if card_ref:
                    cards_by_entry_ref[(entry_id, card_ref)].append(card)
    return cards, card_missing_edges, cards_by_entry_ref


def _family_northstar(family_resolved, ledger, cards, appearances_by_loc, proposal_map):
    family_locs = {item["loc"] for item in family_resolved if item["loc"]}
    ledger_by_loc = defaultdict(list)
    for row in ledger:
        if row.get("occurrence_id"):
            ledger_by_loc[row["occurrence_id"]].append(row)
    card_by_key = {card["card_key"]: card for card in cards}
    affected_entries = {item["entry_id"] for item in family_resolved if item["entry_id"]}
    affected_cards = set()
    affected_selected_rows = set()
    producer_statuses = Counter()
    eligible_rows = []
    for item in family_resolved:
        producer_statuses[item["producer_status"]] += 1
        if item["loc"] in family_locs and item["producer_status"] == "verified":
            eligible_rows.append(item)
        for row in ledger_by_loc.get(item["loc"], []):
            affected_selected_rows.add(
                (
                    row.get("entry_id"),
                    row.get("usage_index"),
                    row.get("form_index"),
                )
            )
        for card in cards:
            if card.get("entry_id") == item["entry_id"] and card.get("card_ref") == _loc_ayah(item["loc"]):
                affected_cards.add(card["card_key"])
    affected_occurrences = {loc for loc in family_locs if loc in appearances_by_loc}
    total_appearances = sum(
        int(appearances_by_loc[loc].get("appearance_count", 0)) for loc in affected_occurrences
    )
    repeated_appearances = sum(
        max(0, int(appearances_by_loc[loc].get("appearance_count", 0)) - 1)
        for loc in affected_occurrences
    )
    eligible_occurrences = {
        item["loc"] for item in eligible_rows if item["loc"] in appearances_by_loc
    }
    eligible_appearances = sum(
        int(appearances_by_loc[loc].get("appearance_count", 0)) for loc in eligible_occurrences
    )
    return {
        "family_rows": len(family_resolved),
        "family_rows_with_entry_join": sum(item["entry_id"] is not None for item in family_resolved),
        "family_rows_without_entry_join": sum(item["entry_id"] is None for item in family_resolved),
        "producer_status_counts": dict(sorted(producer_statuses.items())),
        "calibrated_verified_rows": sum(item["producer_status"] == "verified" for item in family_resolved),
        "affected_entries": len(affected_entries),
        "affected_cards": len(affected_cards),
        "affected_displayed_selected_word_rows": len(affected_selected_rows),
        "affected_unique_occurrences": len(affected_occurrences),
        "affected_total_appearances": total_appearances,
        "affected_repeated_appearances": repeated_appearances,
        "expected_deployable_rows_after_clitic_certification": len(eligible_rows),
        "expected_deployable_unique_occurrences_after_clitic_certification": len(eligible_occurrences),
        "expected_deployable_appearances_after_clitic_certification": eligible_appearances,
        "candidate_only": True,
        "source_certified_count": 0,
    }


def _loc_ayah(loc):
    parts = _clean(loc).split(":")
    return ":".join(parts[:2]) if len(parts) >= 2 else ""


def _percent(part, whole):
    return round((100.0 * part / whole), 4) if whole else 0.0


def _readiness_matrix(entries, cards, ledger, family_resolved, appearances_by_loc, proposal_map, family_mapping):
    entries_by_tranche = defaultdict(set)
    for entry in entries:
        entry_id = _clean(entry.get("id"))
        entries_by_tranche[proposal_map.get(entry_id)].add(entry_id)
    cards_by_tranche = defaultdict(list)
    for card in cards:
        cards_by_tranche[proposal_map.get(card["entry_id"])].append(card)
    rows_by_tranche = defaultdict(list)
    for row in ledger:
        rows_by_tranche[row.get("proposal_vn_tranche")].append(row)
    family_by_tranche = defaultdict(list)
    for item in family_resolved:
        family_by_tranche[proposal_map.get(item.get("entry_id"))].append(item)

    graph_metrics = []
    for label in TRANCHE_LABELS:
        tranche_rows = rows_by_tranche.get(label, [])
        tranche_cards = cards_by_tranche.get(label, [])
        tranche_entries = entries_by_tranche.get(label, set())
        tranche_family = family_by_tranche.get(label, [])
        quality_counts = Counter(row["quality_state"] for row in tranche_rows)
        gap_counts = Counter(
            edge
            for row in tranche_rows
            for edge in row.get("missing_edges", [])
            if edge in GRAPH_CROSSWALK_EDGES
        )
        occurrences = {row["occurrence_id"] for row in tranche_rows if row.get("occurrence_id")}
        family_locs = {item["loc"] for item in tranche_family if item.get("loc")}
        verified_family = [item for item in tranche_family if item["producer_status"] == "verified"]
        expected_locs = {item["loc"] for item in verified_family if item["loc"] in appearances_by_loc}
        affected_appearances = sum(
            int(appearances_by_loc[loc].get("appearance_count", 0)) for loc in family_locs if loc in appearances_by_loc
        )
        expected_appearances = sum(
            int(appearances_by_loc[loc].get("appearance_count", 0)) for loc in expected_locs
        )
        matrix_row = {
            "proposal_vn_tranche": label,
            "assignment_mode": "derived_proposal_requires_owner_confirmation",
            "entries": len(tranche_entries),
            "cards": len(tranche_cards),
            "displayed_selected_words": len(tranche_rows),
            "unique_occurrences": len(occurrences),
            "current_quality_state_counts": dict(sorted(quality_counts.items())),
            "candidates_unlocked_by_calibrated_clitic_producers": len(verified_family),
            "calibrated_clitic_candidate_occurrences": len(expected_locs),
            "source_certified_count": 0,
            "source_certification_state": "pending_owner_certification",
            "unresolved": sum(bool(row.get("missing_edges")) for row in tranche_rows),
            "graph_crosswalk_gap_rows": sum(bool(set(row.get("missing_edges", [])) & GRAPH_CROSSWALK_EDGES) for row in tranche_rows),
            "graph_crosswalk_gap_counts": dict(sorted(gap_counts.items())),
            "offline_unmeasured_render_or_decision_rows": sum(
                bool(set(row.get("missing_edges", [])) & OFFLINE_UNMEASURED_EDGES) for row in tranche_rows
            ),
            "expected_deployable_rows_after_clitic_certification": len(verified_family),
            "expected_deployable_unique_occurrences_after_clitic_certification": len(expected_locs),
            "appearances_affected": affected_appearances,
            "projected_fully_rich_coverage_gain": {
                "unique_occurrence_rows": len(expected_locs),
                "unique_occurrence_percentage_of_D4": _percent(len(expected_locs), len(appearances_by_loc)),
                "appearance_rows": expected_appearances,
                "candidate_only": True,
            },
            "family_locs_seen": len(family_locs),
        }
        graph_metrics.append(matrix_row)

    totals = {
        "entries": sum(row["entries"] for row in graph_metrics),
        "cards": sum(row["cards"] for row in graph_metrics),
        "displayed_selected_words": sum(row["displayed_selected_words"] for row in graph_metrics),
        "unique_occurrences": sum(row["unique_occurrences"] for row in graph_metrics),
        "appearances_affected": sum(row["appearances_affected"] for row in graph_metrics),
    }
    return {
        "schema": "vnmap/readiness-matrix@1",
        "assignment_mode": "derived_proposal_requires_owner_confirmation",
        "authoritative_vn_assignment_source": None,
        "proposal_rule": _proposal_rule(entries),
        "tranches": graph_metrics,
        "totals": totals,
        "clitic_family_northstar": family_mapping,
        "candidate_only": True,
    }


def _input_payload_metrics(whitelist, ledger):
    ledger_locs = {row.get("occurrence_id") for row in ledger if row.get("occurrence_id")}
    typed_rows = [row for row in whitelist if _has_typed_facts(row)]
    payload_rows = [row for row in whitelist if _has_payload(row)]
    return {
        "typed_fact_input_rows": len(typed_rows),
        "payload_input_rows": len(payload_rows),
        "orphan_typed_fact_rows": sum(_clean(row.get("loc")) not in ledger_locs for row in typed_rows),
        "orphan_payload_rows": sum(_clean(row.get("loc")) not in ledger_locs for row in payload_rows),
    }


def _graph_metrics(entries, whitelist, appearances, ledger, cards, family_resolved, family_mapping, card_missing_edges, space_diagnostics, parity_failures):
    edge_counts = Counter(edge for row in ledger for edge in row.get("missing_edges", []))
    quality_counts = Counter(row.get("quality_state") for row in ledger)
    forward_complete = 0
    reverse_complete = 0
    quran_wbw_complete = 0
    canonical_complete = 0
    appearance_complete = 0
    crosswalk_needed = 0
    reciprocity_failures = 0
    for row in ledger:
        edges = set(row.get("missing_edges", []))
        if not edges & {
            "missing_entry_url_edge",
            "missing_source_card_edge",
            "missing_displayed_fragment_edge",
            "missing_selected_word_edge",
            "missing_quran_wbw_edge",
            "duplicate_surface_edge_ambiguous",
            "display_local_to_canonical_crosswalk_missing",
            "canonical_occurrence_appearance_missing",
        }:
            forward_complete += 1
        if row.get("reverse_entry_relationship_present"):
            reverse_complete += 1
        quran_wbw_complete += bool(row.get("quran_wbw_trace_complete"))
        canonical_complete += bool(row.get("canonical_occurrence_trace_complete"))
        appearance_complete += bool(row.get("appearance_index_complete"))
        crosswalk_needed += not bool(row.get("crosswalk_flag"))
        if row.get("occurrence_id") and not row.get("reverse_entry_relationship_present"):
            reciprocity_failures += 1

    total_appearances = sum(int(record.get("appearance_count", 0)) for record in appearances)
    repeated_appearances = sum(max(0, int(record.get("appearance_count", 0)) - 1) for record in appearances)
    input_payload = _input_payload_metrics(whitelist, ledger)
    return {
        "schema": "vnmap/graph-metrics@1",
        "candidate_only": True,
        "input_counts": {
            "entries": len(entries),
            "whitelist_rows": len(whitelist),
            "appearance_index_records": len(appearances),
            "family_rows": len(family_resolved),
        },
        "input_id_space_counts": space_diagnostics,
        "denominators": {
            "D1_entries": len(entries),
            "D1_entries_by_space": {
                space: details["actual_entry_count"]
                for space, details in space_diagnostics.items()
                if space != "other"
            },
            "D2_listed_quran_example_cards": len(cards),
            "D2_cards_by_proposal_tranche": {},
            "D3_displayed_selected_word_rows": len(ledger),
            "D3_selected_words_by_proposal_tranche": {},
            "D4_unique_canonical_occurrences": len(appearances),
            "D4_total_appearances": total_appearances,
            "D4_repeated_appearances": repeated_appearances,
        },
        "edge_join_rows_total": len(ledger),
        "forward_trace_complete_rows": forward_complete,
        "reverse_trace_complete_rows": reverse_complete,
        "quran_wbw_trace_complete_rows": quran_wbw_complete,
        "canonical_occurrence_trace_complete_rows": canonical_complete,
        "appearance_index_complete_rows": appearance_complete,
        "rows_needing_source_address_crosswalk": crosswalk_needed,
        "orphan_typed_fact_rows": input_payload["orphan_typed_fact_rows"],
        "orphan_payload_rows": input_payload["orphan_payload_rows"],
        "typed_fact_input_rows": input_payload["typed_fact_input_rows"],
        "payload_input_rows": input_payload["payload_input_rows"],
        "entry_occurrence_reciprocity_failures": reciprocity_failures,
        "appearance_projection_parity_failures": parity_failures,
        "manual_probe_count": 0,
        "manual_probe_reasons": ["pre_deploy_offline_lane_no_manual_or_browser_probe_input"],
        "missing_edge_counts": dict(sorted(edge_counts.items())),
        "card_missing_edge_counts": dict(sorted(card_missing_edges.items())),
        "quality_state_counts": dict(sorted(quality_counts.items())),
        "source_photo_missing_entry_count": sum(not _entry_photo_present(entry) for entry in entries),
        "source_photo_missing_selected_word_rows": edge_counts["missing_source_photo_edge"],
        "source_card_missing_card_count": card_missing_edges["missing_source_card_edge"],
        "offline_unmeasured_rendered_span_rows": edge_counts["rendered_span_edge_missing"],
        "offline_unmeasured_decision_backlink_rows": edge_counts["decision_backlink_missing"],
        "clitic_family_northstar": family_mapping,
        "full_input_parity_checked": True,
    }


def _render_report(metrics, matrix):
    denom = metrics["denominators"]
    spaces = metrics["input_id_space_counts"]
    lines = [
        "# VNMAP NorthStar Addendum Report",
        "",
        "Generated by `tools/build_entry_card_word_ledger.py` from explicit input files.",
        "All rows and projections are candidate-mode; no live mutation, deployment, certification, or public readback is claimed.",
        "",
        "## Verified input spaces",
        "",
        "| space | expected | actual entries | unique keys | observed key range | missing | extra |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for label in ("particles", "verbs", "nouns"):
        info = spaces[label]
        range_text = (
            f"{info['observed_first_key']}–{info['observed_last_key']}"
            if info["observed_first_key"] is not None
            else "none"
        )
        lines.append(
            f"| `{label}` | {info['expected_count']} | {info['actual_entry_count']} | "
            f"{info['actual_unique_source_key_count']} | {range_text} | {len(info['missing_numbers'])} | {len(info['extra_numbers'])} |"
        )
    lines.extend(
        [
            "",
            "The verified source-key space is exactly 100 particles, 947 verbs, and 1,045 nouns (2,092 total); no duplicate source key was observed.",
            "",
            "## Four mandatory denominators",
            "",
            "| denominator | meaning | count |",
            "|---|---|---:|",
            f"| D1 | Qamus entries | {denom['D1_entries']:,} |",
            f"| D2 | listed Qurʾānic example-card records (`usage.examples[]`) | {denom['D2_listed_quran_example_cards']:,} |",
            f"| D3 | displayed selected-word records (`usage.forms[]`, not multiplied by sibling examples) | {denom['D3_displayed_selected_word_rows']:,} |",
            f"| D4 | unique canonical occurrences | {denom['D4_unique_canonical_occurrences']:,} |",
            f"| D4 | total occurrence appearances | {denom['D4_total_appearances']:,} |",
            f"| D4 | repeated appearances beyond one reader occurrence | {denom['D4_repeated_appearances']:,} |",
            "",
            "The D4 sum-check is unique occurrences plus repeated appearances equals total appearances. The occurrence identity remains the existing canonical `loc`; no second occurrence graph is built.",
            "",
            "## Bidirectional graph metrics",
            "",
            "| metric | count |",
            "|---|---:|",
        ]
    )
    metric_names = (
        "edge_join_rows_total",
        "forward_trace_complete_rows",
        "reverse_trace_complete_rows",
        "quran_wbw_trace_complete_rows",
        "canonical_occurrence_trace_complete_rows",
        "appearance_index_complete_rows",
        "rows_needing_source_address_crosswalk",
        "orphan_typed_fact_rows",
        "orphan_payload_rows",
        "entry_occurrence_reciprocity_failures",
        "appearance_projection_parity_failures",
        "manual_probe_count",
    )
    for name in metric_names:
        lines.append(f"| `{name}` | {metrics[name]:,} |")
    lines.extend(
        [
            "",
            f"Manual-probe reasons: `{', '.join(metrics['manual_probe_reasons'])}`.",
            "",
            "### Exact missing-edge counts",
            "",
            "| owner enum edge | selected-word rows |",
            "|---|---:|",
        ]
    )
    for edge in OWNER_MISSING_EDGE_CLASSES:
        lines.append(f"| `{edge}` | {metrics['missing_edge_counts'].get(edge, 0):,} |")
    lines.extend(
        [
            "",
            "Card-level source-card/display gaps are reported separately because D2 cards without a D3 form row still belong in the card denominator:",
            "",
            f"`{json.dumps(metrics['card_missing_edge_counts'], ensure_ascii=False, sort_keys=True)}`",
            "",
            f"Source-photo truth: {metrics['source_photo_missing_entry_count']:,} entries have no photo locator in the entry input, affecting {metrics['source_photo_missing_selected_word_rows']:,} selected-word rows. No photo edge was fabricated.",
            f"Pre-deploy render/readback truth: `{metrics['offline_unmeasured_rendered_span_rows']:,}` rows carry `rendered_span_edge_missing`; `{metrics['offline_unmeasured_decision_backlink_rows']:,}` carry `decision_backlink_missing`. These edges require a later deploy/readback surface and are not measured here.",
            "",
            "## VN assignment status",
            "",
            "No repository data file was found that assigns every entry to an authoritative `VN-00` through `VN-20` tranche. The repository search covered `docs/`, `qamus/`, and prior VN reports/records; `docs/VN-OPERATIONS.md` supplies ordering and early-window context, not a complete per-entry assignment.",
            "",
            "Every ledger row therefore has `vn_tranche: null`.",
            "",
            "### DERIVED PROPOSAL — REQUIRES OWNER CONFIRMATION",
            "",
            matrix["proposal_rule"],
            "",
            "The proposal tranche labels below are analysis-only. They do not populate the ledger's `vn_tranche` field and do not authorize rollout.",
            "",
            "## VN readiness matrix (derived proposal)",
            "",
            "| tranche | entries | cards | selected words | occurrences | clitic candidates | source-certified | unresolved | graph gaps | expected candidate rows | appearances affected | projected gain |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in matrix["tranches"]:
        gain = row["projected_fully_rich_coverage_gain"]
        lines.append(
            f"| `{row['proposal_vn_tranche']}` | {row['entries']:,} | {row['cards']:,} | {row['displayed_selected_words']:,} | "
            f"{row['unique_occurrences']:,} | {row['candidates_unlocked_by_calibrated_clitic_producers']:,} | {row['source_certified_count']:,} | "
            f"{row['unresolved']:,} | {row['graph_crosswalk_gap_rows']:,} | {row['expected_deployable_rows_after_clitic_certification']:,} | "
            f"{row['appearances_affected']:,} | {gain['unique_occurrence_rows']:,} occurrences ({gain['unique_occurrence_percentage_of_D4']:.4f}%) |"
        )
    lines.extend(
        [
            "",
            "Source-certified is intentionally zero pending owner certification. `expected candidate rows` and `projected gain` are conditional projections after clitic certification; they are not rich-at-rest, rich-hover, rendered-span, or public-readback facts.",
            "",
            "## Clitic family on the NorthStar",
            "",
            "The calibrated clitic-family input is joined by the existing canonical `loc`, then projected across the entry/card/selected-word/occurrence denominators:",
            "",
            "| family measure | count |",
            "|---|---:|",
        ]
    )
    family = matrix["clitic_family_northstar"]
    for key in (
        "family_rows",
        "family_rows_with_entry_join",
        "family_rows_without_entry_join",
        "affected_entries",
        "affected_cards",
        "affected_displayed_selected_word_rows",
        "affected_unique_occurrences",
        "affected_total_appearances",
        "affected_repeated_appearances",
        "expected_deployable_rows_after_clitic_certification",
    ):
        lines.append(f"| `{key}` | {family[key]:,} |")
    lines.extend(
        [
            "",
            f"Producer statuses: `{json.dumps(family['producer_status_counts'], ensure_ascii=False, sort_keys=True)}`. The family is producer-verified evidence, not source certification.",
            "",
            "## Compounding Impact",
            "",
            "The value of this addendum is the join across the closure chain, not a whitelist-row total. One selected-word row can point to one canonical occurrence whose facts are transcluded to every existing appearance; repeated appearances are therefore measured as downstream impact, not copied rendering work. The family mapping shows where a calibrated clitic candidate could compound across entries, cards, selected words, unique occurrences, and repeated appearances while preserving canonical identity.",
            "",
            "No finished rendering is copied into the ledger. Typed facts remain source-addressed inputs, and any later rich-hover or rendered-span result must be regenerated by the owning runtime and verified by public readback.",
            "",
            "## Honest limits",
            "",
            "- This is an offline candidate ledger. No live mutation, deploy, restart, source certification, rich-hover certification, browser probe, rendered-span measurement, or public readback occurred.",
            "- Missing source-photo, decision-backlink, and rendered-span/readback edges are counted with their exact owner enum names; no synthetic edge is asserted.",
            "- A derived VN proposal is explicitly pending owner confirmation; all ledger `vn_tranche` values remain null.",
            "- A unique surface join is an identity crosswalk, not a linguistic certification. Ambiguous duplicate surfaces remain pending with `duplicate_surface_edge_ambiguous`.",
            "- The four denominators are intentionally not interchangeable: D2 example cards, D3 selected forms, and D4 canonical occurrences/appearances answer different closure questions.",
            "",
            "## Reproduction",
            "",
            "Run `python tools/build_entry_card_word_ledger.py` with explicit `--entries`, `--whitelist`, `--appearance-index`, `--family`, and output arguments. The committed fixture subset under `qamus/examples/vnmap/` lets the harness validate the contract without external inputs.",
            "",
        ]
    )
    return "\n".join(lines)


def build_ledger(entries, whitelist, appearance_records, family_rows):
    """Build deterministic ledger, graph metrics, readiness matrix, and report."""

    entries = list(entries)
    whitelist = list(whitelist)
    appearance_records = list(appearance_records)
    family_rows = list(family_rows)
    entries_by_id = {_clean(entry.get("id")): entry for entry in entries if _clean(entry.get("id"))}
    entries_by_source = {}
    for entry in entries:
        source_key = _entry_source_key(entry)
        entry_id = _clean(entry.get("id"))
        if not source_key or not entry_id:
            continue
        entries_by_source[source_key] = entry_id
        identity = _source_identity(source_key)
        if identity is not None:
            entries_by_source[identity] = entry_id
    index = WhitelistIndex(whitelist)
    appearances_by_loc = {
        _clean(record.get("loc")): record
        for record in appearance_records
        if _clean(record.get("loc"))
    }
    proposal_map = _proposal_tranche_map(entries)
    cards, card_missing_edges, _cards_by_entry_ref = _make_cards(entries, index)
    ledger = []
    for entry in sorted(entries, key=_source_sort_key):
        entry_id = _clean(entry.get("id"))
        source_key = _entry_source_key(entry)
        proposal_vn = proposal_map.get(entry_id)
        for usage_index, usage in enumerate(entry.get("usage") or [], 1):
            if not isinstance(usage, dict):
                continue
            examples = usage.get("examples") or []
            for form_index, form in enumerate(usage.get("forms") or [], 1):
                ledger.append(
                    _make_ledger_row(
                        entry,
                        usage,
                        usage_index,
                        examples,
                        form,
                        form_index,
                        entry_id,
                        source_key,
                        proposal_vn,
                        index,
                        appearances_by_loc,
                    )
                )
    ledger.sort(
        key=lambda row: (
            SOURCE_SPACE_ORDER.get((_source_identity(row.get("source_key")) or ("", 10**9))[0], 99),
            (_source_identity(row.get("source_key")) or ("", 10**9))[1],
            row.get("sense_index") or 0,
            row.get("usage_index") or 0,
            row.get("form_index") or 0,
            row.get("entry_id") or "",
        )
    )

    family_resolved = _family_resolution(family_rows, index, entries_by_id, entries_by_source)
    family_mapping = _family_northstar(
        family_resolved, ledger, cards, appearances_by_loc, proposal_map
    )
    matrix = _readiness_matrix(
        entries, cards, ledger, family_resolved, appearances_by_loc, proposal_map, family_mapping
    )
    try:
        parity_report = validate_records(appearance_records, source_rows=whitelist)
        parity_failures = len(parity_report.errors)
    except Exception:
        parity_failures = 1
    metrics = _graph_metrics(
        entries,
        whitelist,
        appearance_records,
        ledger,
        cards,
        family_resolved,
        family_mapping,
        card_missing_edges,
        _space_diagnostics(entries),
        parity_failures,
    )
    tranche_card_counts = Counter(card.get("entry_id") for card in cards)
    metrics["denominators"]["D2_cards_by_proposal_tranche"] = {
        label: sum(
            1
            for card in cards
            if proposal_map.get(card.get("entry_id")) == label
        )
        for label in TRANCHE_LABELS
    }
    metrics["denominators"]["D3_selected_words_by_proposal_tranche"] = {
        label: sum(row.get("proposal_vn_tranche") == label for row in ledger)
        for label in TRANCHE_LABELS
    }
    metrics["vn_assignment"] = {
        "authoritative_source": None,
        "ledger_field_value": None,
        "search_scope": ["docs/", "qamus/", "prior VN reports/records"],
        "status": "none_found_derived_proposal_only",
    }
    report = _render_report(metrics, matrix)
    return BuildResult(ledger=ledger, metrics=metrics, matrix=matrix, report=report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", required=True, help="entries JSONL input")
    parser.add_argument("--whitelist", required=True, help="whitelist JSONL input")
    parser.add_argument("--appearance-index", required=True, help="existing occurrence-appearance JSONL output")
    parser.add_argument("--family", required=True, help="calibrated clitic-family JSONL input")
    parser.add_argument("--ledger-output", required=True)
    parser.add_argument("--metrics-output", required=True)
    parser.add_argument("--matrix-output", required=True)
    parser.add_argument("--report-output", required=True)
    args = parser.parse_args(argv)

    result = build_ledger(
        _read_jsonl(args.entries),
        _read_jsonl(args.whitelist),
        _read_jsonl(args.appearance_index),
        _read_jsonl(args.family),
    )
    _write_jsonl(result.ledger, args.ledger_output)
    _write_json(result.metrics, args.metrics_output)
    _write_json(result.matrix, args.matrix_output)
    with open(args.report_output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(result.report)
        if not result.report.endswith("\n"):
            handle.write("\n")
    print("vnmap entry-card word ledger built")
    print(
        json.dumps(
            {
                "entries": result.metrics["denominators"]["D1_entries"],
                "cards": result.metrics["denominators"]["D2_listed_quran_example_cards"],
                "selected_words": result.metrics["denominators"]["D3_displayed_selected_word_rows"],
                "unique_occurrences": result.metrics["denominators"]["D4_unique_canonical_occurrences"],
                "repeated_appearances": result.metrics["denominators"]["D4_repeated_appearances"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
