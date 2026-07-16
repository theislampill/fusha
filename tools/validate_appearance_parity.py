#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate occurrence-to-appearance projection parity.

The invariant is scoped to canonical occurrence identity: every appearance of
one ``loc`` inherits that location's projection hash.  A normalized surface
repeated at another location is a different occurrence and is not a failure.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
import os
import re
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INDEX = os.path.join(REPO_ROOT, "qamus", "indexes", "occurrence-appearances.jsonl")
# The corpus whitelist is an external artifact; it must be passed explicitly.
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

sys.path.insert(0, REPO_ROOT)
from tools.normalize_ar import norm  # noqa: E402


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str]
    records: int
    source_rows: int
    duplicate_source_rows: int
    divergent_locations: int
    allowed_same_surface_groups: int


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


def _projection_hash(row):
    from tools.build_occurrence_appearance_index import projection_hash

    return projection_hash(row)


def _validate_record(record, seen, errors):
    if not isinstance(record, dict):
        errors.append("index record is not an object")
        return
    loc = record.get("loc")
    if not isinstance(loc, str) or not re.fullmatch(r"\d+:\d+:\d+", loc):
        errors.append(f"invalid canonical loc: {loc!r}")
        return
    if loc in seen:
        errors.append(f"duplicate canonical record for loc {loc}")
    seen[loc] = record
    if record.get("unique") is not True:
        errors.append(f"loc {loc} does not declare unique=true")
    parent_hash = record.get("projection_hash")
    if not isinstance(parent_hash, str) or not _HASH_RE.fullmatch(parent_hash):
        errors.append(f"loc {loc} has an invalid projection_hash")
    appearances = record.get("appearances")
    if not isinstance(appearances, list):
        errors.append(f"loc {loc} appearances is not a list")
        appearances = []
    if record.get("appearance_count") != len(appearances):
        errors.append(f"loc {loc} appearance_count does not equal appearances length")
    if not any(isinstance(item, dict) and item.get("surface_kind") == "reader" for item in appearances):
        errors.append(f"loc {loc} has no reader appearance")

    appearance_entry_ids = set()
    for index, appearance in enumerate(appearances, 1):
        if not isinstance(appearance, dict):
            errors.append(f"loc {loc} appearance {index} is not an object")
            continue
        kind = appearance.get("surface_kind")
        if kind not in {"reader", "entry_example"}:
            errors.append(f"loc {loc} appearance {index} has unsupported surface_kind {kind!r}")
        entry_id = appearance.get("entry_id")
        if entry_id is not None:
            if not isinstance(entry_id, str) or not entry_id:
                errors.append(f"loc {loc} appearance {index} has an invalid entry_id")
            else:
                appearance_entry_ids.add(entry_id)
        appearance_hash = appearance.get("projection_hash")
        if appearance_hash is not None:
            if not isinstance(appearance_hash, str) or not _HASH_RE.fullmatch(appearance_hash):
                errors.append(f"loc {loc} appearance {index} has an invalid projection_hash")
            elif appearance_hash != parent_hash:
                errors.append(f"loc {loc} appearance {index} consumes a divergent projection_hash")

    relationships = record.get("entry_relationships")
    if not isinstance(relationships, list) or any(not isinstance(item, str) or not item for item in relationships):
        errors.append(f"loc {loc} entry_relationships is not a list of non-empty strings")
        relationships = []
    if relationships != sorted(set(relationships)):
        errors.append(f"loc {loc} entry_relationships is not sorted and unique")
    if set(relationships) != appearance_entry_ids:
        errors.append(f"loc {loc} entry_relationships disagree with appearance entry_ids")


def validate_records(records, source_rows=None):
    """Return a structural and source-backed parity report."""

    records = list(records)
    errors = []
    seen = {}
    for record in records:
        _validate_record(record, seen, errors)

    source_rows = list(source_rows or [])
    source_by_loc = defaultdict(list)
    surface_groups = defaultdict(set)
    for row in source_rows:
        loc = str(row.get("loc") or "")
        try:
            row_hash = _projection_hash(row)
        except Exception as exc:
            errors.append(f"source row {loc} cannot be hashed: {exc}")
            continue
        source_by_loc[loc].append(row_hash)
        # This is diagnostic only.  The same normalized surface at different
        # canonical locations is explicitly allowed, including across ayahs.
        surface_groups[norm(str(row.get("surface") or ""))].add(loc)

    duplicate_source_rows = 0
    divergent_locations = 0
    for loc, hashes in source_by_loc.items():
        if len(hashes) > 1:
            duplicate_source_rows += len(hashes) - 1
        if len(set(hashes)) > 1:
            divergent_locations += 1
            errors.append(f"divergent projection hashes for canonical loc {loc}")
        if loc not in seen:
            errors.append(f"source loc {loc} is missing from the index")
        elif set(hashes) != {seen[loc].get("projection_hash")}:
            errors.append(f"index projection_hash disagrees with source loc {loc}")

    for loc in seen:
        if source_rows and loc not in source_by_loc:
            errors.append(f"index loc {loc} is absent from the supplied source")

    allowed_same_surface_groups = sum(
        len(locs) > 1
        and any(source_by_loc[loc] and len(set(source_by_loc[loc])) > 0 for loc in locs)
        for locs in surface_groups.values()
    )
    return ValidationReport(
        ok=not errors,
        errors=errors,
        records=len(records),
        source_rows=len(source_rows),
        duplicate_source_rows=duplicate_source_rows,
        divergent_locations=divergent_locations,
        allowed_same_surface_groups=allowed_same_surface_groups,
    )


def render_report(report):
    lines = [
        "appearance parity report",
        f"  index records: {report.records}",
        f"  source rows: {report.source_rows}",
        f"  repeated source rows with identical analysis: {report.duplicate_source_rows}",
        f"  divergent canonical locations: {report.divergent_locations}",
        f"  same-normalized-surface/different-location groups allowed: {report.allowed_same_surface_groups}",
    ]
    if report.errors:
        lines.append(f"  errors: {len(report.errors)}")
        lines.extend(f"    FAIL {error}" for error in report.errors)
        lines.append("APPEARANCE PARITY FAIL")
    else:
        lines.append("  errors: 0")
        lines.append("APPEARANCE PARITY PASS")
    return "\n".join(lines)


def _fixture_row(loc, surface, analysis):
    return {
        "loc": loc,
        "surface": surface,
        "segments": [{"surface": surface, "gloss_contribution": analysis}],
        "token_contribution_gloss": analysis,
        "contextual_phrase_gloss": analysis,
        "morphline": analysis,
        "root": None,
        "sarf_facts": None,
        "nahw_facts": None,
    }


def self_test():
    from tools.build_occurrence_appearance_index import build_index, projection_hash

    failures = []
    fork_a = _fixture_row("1:1:1", "أ", "a")
    fork_b = _fixture_row("1:1:1", "أ", "the")
    fork_report = validate_records([], source_rows=[fork_a, fork_b])
    if fork_report.ok or not any("divergent" in error for error in fork_report.errors):
        failures.append("same-loc fork did not fail")
    else:
        print("ok   red-first same-loc fork rejected")

    same_surface_a = _fixture_row("39:63:3", "السَّمَاوَاتِ", "segmented")
    same_surface_b = _fixture_row("22:18:9", "ٱلسَّمَٰوَٰتِ", "fused")
    distinct_report = validate_records(
        build_index([same_surface_a, same_surface_b], []).records,
        source_rows=[same_surface_a, same_surface_b],
    )
    if not distinct_report.ok or distinct_report.allowed_same_surface_groups < 1:
        failures.append("same-surface different-location pair was rejected")
    else:
        print("ok   same-normalized-surface different-loc pair allowed")

    copy = {
        "loc": "1:1:1",
        "unique": True,
        "appearances": [{
            "surface_kind": "entry_example",
            "entry_id": "entry-a",
            "projection_hash": "0" * 64,
        }],
        "appearance_count": 1,
        "entry_relationships": ["entry-a"],
        "projection_hash": projection_hash(fork_a),
    }
    copy_report = validate_records([copy], source_rows=[fork_a])
    if copy_report.ok or not any("appearance" in error for error in copy_report.errors):
        failures.append("future entry-page copy hash mismatch did not fail")
    else:
        print("ok   future entry-page copy hash mismatch rejected")

    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("APPEARANCE PARITY SELF-TEST PASS — red-first fixtures hold")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--whitelist", default=None,
                        help="external corpus whitelist (explicit path; the corpus is "
                             "not repo-tracked, so there is no implicit default)")
    parser.add_argument("--structure-only", action="store_true",
                        help="validate the committed index's structural invariants "
                             "without a corpus (repo-self-contained harness mode)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    records = list(_read_jsonl(args.index))
    if args.structure_only:
        source_rows = []
    elif args.whitelist:
        source_rows = list(_read_jsonl(args.whitelist))
    else:
        parser.error("provide --whitelist PATH for a corpus parity run, "
                     "or --structure-only for the repo-self-contained check")
        return 2
    report = validate_records(records, source_rows=source_rows)
    print(render_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
