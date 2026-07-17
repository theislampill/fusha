#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the canonical occurrence-to-appearance index.

The sibling whitelist is the reader surface: every row contributes one reader
appearance keyed by its canonical ``loc``.  Entry-page metadata on those rows
and exact/conservatively reconciled entry-store examples add entry-example
appearances.  The builder never mutates either input source.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
import re
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WHITELIST = os.path.join(REPO_ROOT, "..", "data", "rh_live_01_beta_whitelist.jsonl")
DEFAULT_ENTRIES = os.path.join(REPO_ROOT, "..", "data", "entries.jsonl")
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "qamus", "indexes", "occurrence-appearances.jsonl")

_LOC_RE = re.compile(r"^\d+:\d+:\d+$")
_SOURCE_KEY_RE = re.compile(r"^([A-Za-z]+)0*(\d+)$")


class DuplicateAnalysisError(ValueError):
    """Raised when one canonical location carries divergent projections."""


@dataclass
class BuildResult:
    records: list[dict]
    stats: dict


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


def projection_payload(row):
    """Return exactly the analysis-bearing fields used by ``projection_hash``."""

    glosses = row["glosses"] if "glosses" in row else {
        "token_contribution_gloss": row.get("token_contribution_gloss"),
        "contextual_phrase_gloss": row.get("contextual_phrase_gloss"),
    }
    facts = row["facts"] if "facts" in row else {
        "sarf_facts": row.get("sarf_facts"),
        "nahw_facts": row.get("nahw_facts"),
    }
    return {
        "segments": row.get("segments"),
        "glosses": glosses,
        "morphline": row.get("morphline"),
        "root": row.get("root"),
        "facts": facts,
    }


def projection_hash(row):
    """Hash the canonical JSON representation of the current analysis projection."""

    encoded = json.dumps(
        projection_payload(row),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_identity(value):
    """Normalize n0002/n002 to the same source-key identity."""

    if not isinstance(value, str):
        return None
    value = value.strip().strip("/")
    match = _SOURCE_KEY_RE.fullmatch(value)
    if not match:
        return None
    return match.group(1).lower(), int(match.group(2))


def _url_path(value):
    if not isinstance(value, str) or not value.strip():
        return ""
    value = value.strip().split("#", 1)[0].split("?", 1)[0]
    if "://" in value:
        value = value.split("://", 1)[1]
        value = value.split("/", 1)[1] if "/" in value else ""
    return value.strip("/")


def _entry_resolver(entries):
    by_id = {}
    by_source = {}
    for entry in entries:
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        by_id[entry_id] = entry
        for source_key in entry.get("source_keys") or []:
            identity = _source_identity(source_key)
            if identity is None:
                continue
            previous = by_source.get(identity)
            if previous and previous != entry_id:
                raise ValueError(
                    f"source key {source_key!r} maps to multiple entry ids: {previous}, {entry_id}"
                )
            by_source[identity] = entry_id
    return by_id, by_source


def _resolve_entry_candidate(value, by_id, by_source):
    """Resolve an entry id or source-key alias against the typed entry index."""

    candidate = str(value or "").strip()
    if not candidate:
        return None
    if candidate in by_id:
        return candidate
    identity = _source_identity(candidate)
    if identity in by_source:
        return by_source[identity]
    return candidate


def resolve_entry_id(row, by_id, by_source):
    """Resolve the entry id carried by a whitelist row, if any."""

    direct = str(row.get("entry_id") or "").strip()
    if direct:
        return _resolve_entry_candidate(direct, by_id, by_source)

    url_path = _url_path(row.get("entry_url"))
    if url_path.startswith("e/") and url_path[2:]:
        return _resolve_entry_candidate(url_path[2:], by_id, by_source)

    for candidate in (row.get("source_key"), url_path):
        identity = _source_identity(candidate)
        if identity in by_source:
            return by_source[identity]
    return None


def _has_entry_page_signal(row):
    """Recognize explicit entry-page evidence without treating card_ref alone as one."""

    if str(row.get("entry_id") or "").strip():
        return True
    url_path = _url_path(row.get("entry_url"))
    if url_path and url_path != "_canonical/loc-only":
        return True
    if str(row.get("source_key") or "").strip():
        return True
    if str(row.get("graph_source_key") or "").strip():
        return True
    if row.get("example_card_index") is not None or row.get("example_en") not in (None, ""):
        return True
    flags = row.get("flags") or {}
    return bool(flags.get("entry_example_scope") or flags.get("entry_example_scope_only"))


def _appearance(surface_kind, *, entry_id=None, emphasis=None):
    result = {"surface_kind": surface_kind}
    if entry_id:
        result["entry_id"] = entry_id
    if emphasis is not None:
        result["emphasis"] = emphasis
    return result


def _appearance_sort_key(appearance):
    return (
        appearance.get("surface_kind") != "reader",
        json.dumps(appearance, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def _add_appearance(state, appearance):
    if appearance not in state["appearances"]:
        state["appearances"].append(appearance)
    if appearance.get("entry_id"):
        state["entry_ids"].add(appearance["entry_id"])


def _parse_ref(value):
    if not isinstance(value, str):
        return None
    ref = value.strip()
    for prefix in ("quran:", "wbw:"):
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
    parts = ref.split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _loc_parts(loc):
    return tuple(int(part) for part in loc.split(":"))


def build_index(whitelist_rows, entries):
    """Build records and stats from already-decoded whitelist and entry rows."""

    whitelist_rows = list(whitelist_rows)
    entries = list(entries)
    by_id, by_source = _entry_resolver(entries)
    states = {}
    by_ayah = defaultdict(list)
    stats = Counter({
        "whitelist_rows": len(whitelist_rows),
        "entry_signal_rows": 0,
        "entry_id_resolved_rows": 0,
        "entry_id_unresolved_rows": 0,
        "entry_store_entries": len(entries),
        "entry_store_examples": 0,
        "entry_store_exact_loc_refs": 0,
        "entry_store_ayah_refs": 0,
        "entry_store_matched_refs": 0,
        "entry_store_unresolved_refs": 0,
    })

    for row in whitelist_rows:
        loc = str(row.get("loc") or "").strip()
        if not _LOC_RE.fullmatch(loc):
            raise ValueError(f"invalid canonical loc: {loc!r}")
        current_hash = projection_hash(row)
        state = states.setdefault(loc, {
            "loc": loc,
            "projection_hash": current_hash,
            "hashes": set(),
            "appearances": [],
            "entry_ids": set(),
            "source_entry_id": None,
        })
        state["hashes"].add(current_hash)
        if state["hashes"] != {state["projection_hash"]}:
            hashes = ", ".join(sorted(state["hashes"]))
            raise DuplicateAnalysisError(f"loc {loc} has divergent projection hashes: {hashes}")

        _add_appearance(state, _appearance("reader"))
        entry_id = resolve_entry_id(row, by_id, by_source)
        if _has_entry_page_signal(row):
            stats["entry_signal_rows"] += 1
            if entry_id:
                stats["entry_id_resolved_rows"] += 1
                state["source_entry_id"] = entry_id
            else:
                stats["entry_id_unresolved_rows"] += 1
            _add_appearance(state, _appearance("entry_example", entry_id=entry_id))

        surah, ayah, _word = _loc_parts(loc)
        by_ayah[(surah, ayah)].append(loc)

    # The entry store has ayah-only refs today.  Use those refs to strengthen an
    # already explicit entry-page relationship, or an exact three-part ref; do
    # not claim that every word in an ayah is an example for the entry.
    for entry in entries:
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        entry_source_id = entry_id
        for usage in entry.get("usage") or []:
            for example in usage.get("examples") or []:
                stats["entry_store_examples"] += 1
                parsed = _parse_ref(example.get("ref"))
                if parsed is None:
                    stats["entry_store_unresolved_refs"] += 1
                    continue
                if len(parsed) == 3:
                    stats["entry_store_exact_loc_refs"] += 1
                    loc = ":".join(str(part) for part in parsed)
                    candidate_locs = [loc] if loc in states else []
                else:
                    stats["entry_store_ayah_refs"] += 1
                    candidate_locs = [
                        loc for loc in by_ayah.get(parsed, [])
                        if states[loc]["source_entry_id"] == entry_source_id
                        or entry_source_id in states[loc]["entry_ids"]
                    ]
                if not candidate_locs:
                    stats["entry_store_unresolved_refs"] += 1
                    continue
                stats["entry_store_matched_refs"] += 1
                for loc in candidate_locs:
                    _add_appearance(states[loc], _appearance("entry_example", entry_id=entry_id))

    records = []
    for loc in sorted(states, key=_loc_parts):
        state = states[loc]
        appearances = sorted(state["appearances"], key=_appearance_sort_key)
        records.append({
            "loc": loc,
            "unique": True,
            "appearances": appearances,
            "appearance_count": len(appearances),
            "entry_relationships": sorted(state["entry_ids"]),
            "projection_hash": state["projection_hash"],
        })

    stats["unique_occurrences"] = len(records)
    stats["reader_appearances"] = sum(
        sum(appearance.get("surface_kind") == "reader" for appearance in record["appearances"])
        for record in records
    )
    stats["entry_example_appearances"] = sum(
        sum(appearance.get("surface_kind") == "entry_example" for appearance in record["appearances"])
        for record in records
    )
    stats["total_appearances"] = sum(record["appearance_count"] for record in records)
    stats["occurrences_with_entry_relationships"] = sum(
        bool(record["entry_relationships"]) for record in records
    )
    stats["total_entry_relationships"] = sum(
        len(record["entry_relationships"]) for record in records
    )
    stats["distinct_entry_relationships"] = len({
        entry_id
        for record in records
        for entry_id in record["entry_relationships"]
    })
    return BuildResult(records=records, stats=dict(stats))


def write_jsonl(records, output_path):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ))
            handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--whitelist", default=DEFAULT_WHITELIST)
    parser.add_argument("--entries", default=DEFAULT_ENTRIES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    result = build_index(_read_jsonl(args.whitelist), _read_jsonl(args.entries))
    write_jsonl(result.records, args.output)
    print("occurrence appearance index built")
    print(json.dumps(result.stats, ensure_ascii=False, sort_keys=True))
    print(f"output={os.path.abspath(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
