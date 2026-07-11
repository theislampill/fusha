#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build and verify an RM-20 canonical-hover repair report without applying it.

The merged infrastructure already supplies the lineage foundations RM-20 needs:
``fact_ledger.FactLedgerStore`` retains append-only history and requires revision
``supersedes`` links; the projectors record ``created_from`` and enumerate
``superseded_dependents``; canonical-hover payload and binding IDs are recomputed
by ``validate_canonical_hover_payload_table``; and the @2 binding schema permits a
replacement binding to name the prior binding in ``supersedes``.  This tool only
orchestrates those existing contracts into a deterministic, self-contained repair
report.  It never mutates payload, binding, ledger, or production data.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import sys
from collections import Counter
from typing import Any, Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate_canonical_hover_payload_table import (  # noqa: E402
    binding_id,
    payload_id,
    validate_binding,
    validate_payload,
)

REPORT_SCHEMA = "qamus.canonical_hover_rebind_report.v1"
TOMBSTONE_REASON = "payload_repaired_pending_binding_rebind"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(rows: Iterable[dict[str, Any]]) -> str:
    ordered = sorted((copy.deepcopy(row) for row in rows), key=_canonical)
    return hashlib.sha256(_canonical(ordered).encode("utf-8")).hexdigest()


def read_jsonl(path: str) -> list[dict[str, Any]]:
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("%s:%d: invalid JSON: %s" % (path, number, exc)) from exc
    return rows


def read_json(path: str) -> dict[str, Any]:
    with io.open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("%s: expected one JSON object" % path)
    return value


def dump_review(path: str, value: dict[str, Any]) -> None:
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def _path_identity(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def build_rebind_report(
    payloads: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
    old_payload_id: str,
    new_payload: dict[str, Any],
) -> dict[str, Any]:
    """Return a deterministic dry-run report; do not change any input row."""
    old_matches = [row for row in payloads if row.get("canonical_payload_id") == old_payload_id]
    if len(old_matches) != 1:
        raise ValueError("old payload %r must occur exactly once (found %d)" % (
            old_payload_id, len(old_matches)))
    new_errors = validate_payload(new_payload)
    if new_errors:
        raise ValueError("new payload is invalid: " + "; ".join(new_errors))
    new_payload_id = payload_id(new_payload)
    if new_payload_id == old_payload_id:
        raise ValueError("new payload content must produce a different canonical_payload_id")

    dependents = sorted(
        (row for row in bindings if row.get("canonical_payload_id") == old_payload_id),
        key=lambda row: row.get("binding_id") or "",
    )
    rebinds = []
    conflicts = []
    for old_binding in dependents:
        if old_binding.get("schema") != "qamus.canonical_hover_occurrence_binding.v2":
            raise ValueError("dependent binding %r must use the @2 schema for supersedes lineage" % (
                old_binding.get("binding_id"),))
        replacement = copy.deepcopy(old_binding)
        replacement["canonical_payload_id"] = new_payload_id
        replacement["supersedes"] = old_binding.get("binding_id")
        replacement["binding_id"] = binding_id(replacement)
        rebinds.append({
            "old_binding": copy.deepcopy(old_binding),
            "new_binding": replacement,
        })
        conflicts.append({
            "binding_id": old_binding.get("binding_id"),
            "reason": TOMBSTONE_REASON,
            "replacement_binding_id": replacement["binding_id"],
            "tombstone_payload_id": old_payload_id,
        })

    return {
        "schema": REPORT_SCHEMA,
        "mode": "dry_run",
        "input_fingerprints": {
            "bindings_sha256": _fingerprint(bindings),
            "payloads_sha256": _fingerprint(payloads),
        },
        "old_payload": copy.deepcopy(old_matches[0]),
        "new_payload": copy.deepcopy(new_payload),
        "payload_edge": {
            "canonical_payload_id": new_payload_id,
            "supersedes": old_payload_id,
        },
        "tombstone": {
            "canonical_payload_id": old_payload_id,
            "reason": TOMBSTONE_REASON,
            "replacement_canonical_payload_id": new_payload_id,
        },
        "binding_rebinds": rebinds,
        "conflicts": conflicts,
        "summary": {
            "conflicts": len(conflicts),
            "dependent_bindings": len(dependents),
            "replacement_bindings": len(rebinds),
        },
    }


def verify_dataset(
    payloads: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
    report: dict[str, Any] | None = None,
) -> list[str]:
    """Return errors under the live-payload-or-explicit-tombstone-conflict rule."""
    errors: list[str] = []
    payload_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(payloads):
        row_errors = validate_payload(row)
        errors.extend("payload[%d]: %s" % (index, error) for error in row_errors)
        row_id = row.get("canonical_payload_id")
        if row_id in payload_by_id:
            errors.append("duplicate canonical_payload_id %r" % row_id)
        else:
            payload_by_id[row_id] = row

    binding_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(bindings):
        reference = row.get("canonical_payload_id")
        payload_map = ({reference: payload_by_id[reference].get("lemma_status")}
                       if reference in payload_by_id else None)
        row_errors = validate_binding(row, payload_map)
        errors.extend("binding[%d]: %s" % (index, error) for error in row_errors)
        row_id = row.get("binding_id")
        if row_id in binding_by_id:
            errors.append("duplicate binding_id %r" % row_id)
        else:
            binding_by_id[row_id] = row

    tombstone_id = None
    conflicts: list[dict[str, Any]] = []
    replacement_payloads: dict[str, dict[str, Any]] = {}
    if report is not None:
        if report.get("schema") != REPORT_SCHEMA:
            errors.append("repair report schema must be %s" % REPORT_SCHEMA)
        if report.get("mode") != "dry_run":
            errors.append("repair report mode must be dry_run")
        expected_fingerprints = {
            "bindings_sha256": _fingerprint(bindings),
            "payloads_sha256": _fingerprint(payloads),
        }
        if report.get("input_fingerprints") != expected_fingerprints:
            errors.append("repair report input fingerprints do not match the verified rows")

        edge = report.get("payload_edge") or {}
        tombstone = report.get("tombstone") or {}
        old_payload_id = edge.get("supersedes")
        new_payload_id = edge.get("canonical_payload_id")
        tombstone_id = tombstone.get("canonical_payload_id")
        if not old_payload_id or not new_payload_id:
            errors.append("payload supersedes edge requires old_payload_id and new_payload_id")
        if (tombstone_id != old_payload_id
                or tombstone.get("replacement_canonical_payload_id") != new_payload_id):
            errors.append("tombstone must match the payload supersedes edge")
        if report.get("old_payload") != payload_by_id.get(old_payload_id):
            errors.append("repair report old_payload does not match the verified payload row")

        new_payload_value = report.get("new_payload")
        if not isinstance(new_payload_value, dict):
            errors.append("repair report new_payload must be an object")
            new_payload: dict[str, Any] = {}
        else:
            new_payload = new_payload_value
            new_errors = validate_payload(new_payload)
            errors.extend("new_payload: %s" % error for error in new_errors)
            if new_payload.get("canonical_payload_id") != new_payload_id:
                errors.append("new_payload does not terminate the payload supersedes edge")
            replacement_payloads[new_payload.get("canonical_payload_id")] = new_payload

        actual_dependents = {
            row_id: row for row_id, row in binding_by_id.items()
            if row.get("canonical_payload_id") == old_payload_id
        }
        rebinds = report.get("binding_rebinds")
        if not isinstance(rebinds, list):
            errors.append("repair report binding_rebinds must be an array")
            rebinds = []
        reported_ids: list[str] = []
        replacement_by_old: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(rebinds):
            if not isinstance(item, dict):
                errors.append("binding_rebinds[%d] must be an object" % index)
                continue
            old_binding = item.get("old_binding") or {}
            new_binding = item.get("new_binding") or {}
            old_id = old_binding.get("binding_id")
            reported_ids.append(old_id)
            if old_binding != actual_dependents.get(old_id):
                errors.append("binding_rebinds[%d] old_binding does not match an input dependent" % index)
            if new_binding.get("supersedes") != old_id:
                errors.append("binding_rebinds[%d] missing binding supersedes edge %r -> replacement" % (
                    index, old_id))
            if new_binding.get("canonical_payload_id") != new_payload_id:
                errors.append("binding_rebinds[%d] replacement does not reference new payload" % index)
            if new_binding.get("binding_id") != binding_id(new_binding):
                errors.append("binding_rebinds[%d] replacement binding_id is not content-addressed" % index)
            new_errors = validate_binding(
                new_binding,
                {new_payload_id: new_payload.get("lemma_status")},
            )
            errors.extend("binding_rebinds[%d]: %s" % (index, error) for error in new_errors)
            expected = copy.deepcopy(actual_dependents.get(old_id) or {})
            if expected:
                expected["canonical_payload_id"] = new_payload_id
                expected["supersedes"] = old_id
                expected["binding_id"] = binding_id(expected)
                if new_binding != expected:
                    errors.append("binding_rebinds[%d] replacement differs beyond rebind lineage" % index)
            replacement_by_old[old_id] = new_binding

        missing = sorted(set(actual_dependents) - set(reported_ids))
        extra = sorted(set(reported_ids) - set(actual_dependents))
        duplicates = sorted(row_id for row_id, count in Counter(reported_ids).items() if count > 1)
        if missing:
            errors.append("repair report missing dependent bindings: %s" % ", ".join(missing))
        if extra:
            errors.append("repair report contains non-dependent bindings: %s" % ", ".join(extra))
        if duplicates:
            errors.append("repair report duplicates dependent bindings: %s" % ", ".join(duplicates))

        report_conflicts = report.get("conflicts")
        if not isinstance(report_conflicts, list):
            errors.append("repair report conflicts must be an array")
            report_conflicts = []
        conflicts = [item for item in report_conflicts if isinstance(item, dict)]
        if len(conflicts) != len(report_conflicts):
            errors.append("every repair report conflict must be an object")
        conflict_ids = [item.get("binding_id") for item in conflicts]
        duplicate_conflicts = sorted(
            row_id for row_id, count in Counter(conflict_ids).items() if count > 1
        )
        if duplicate_conflicts:
            errors.append("repair report duplicates tombstone conflicts: %s" % (
                ", ".join(duplicate_conflicts)))
        for item in conflicts:
            old_id = item.get("binding_id")
            replacement = replacement_by_old.get(old_id) or {}
            if (item.get("reason") != TOMBSTONE_REASON
                    or item.get("tombstone_payload_id") != tombstone_id
                    or item.get("replacement_binding_id") != replacement.get("binding_id")):
                errors.append("binding %r has an invalid tombstone conflict" % old_id)

        expected_summary = {
            "conflicts": len(conflicts),
            "dependent_bindings": len(actual_dependents),
            "replacement_bindings": len(rebinds),
        }
        if report.get("summary") != expected_summary:
            errors.append("repair report summary does not match its rows")

    live_payload_ids = set(payload_by_id) | set(replacement_payloads)
    if tombstone_id is not None:
        live_payload_ids.discard(tombstone_id)
    valid_conflicts = {
        item.get("binding_id")
        for item in conflicts
        if item.get("tombstone_payload_id") == tombstone_id
        and item.get("reason") == TOMBSTONE_REASON
    }
    for row in bindings:
        if (row.get("canonical_payload_id") not in live_payload_ids
                and row.get("binding_id") not in valid_conflicts):
            errors.append(
                "binding %r must reference a live payload or explicit tombstone conflict" % (
                    row.get("binding_id"),)
            )
    return errors


def lineage_maps(report: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """Return old-to-new and new-to-old lineage maps from a report."""
    forward = {
        report["payload_edge"]["supersedes"]: report["payload_edge"]["canonical_payload_id"]
    }
    for item in report["binding_rebinds"]:
        forward[item["old_binding"]["binding_id"]] = item["new_binding"]["binding_id"]
    return forward, {new: old for old, new in forward.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run a canonical-hover payload repair and verify lineage integrity."
    )
    parser.add_argument("--payloads", required=True, help="canonical payload JSONL")
    parser.add_argument("--bindings", required=True, help="occurrence binding JSONL")
    parser.add_argument("--old-payload-id")
    parser.add_argument("--new-payload", help="replacement payload JSON object")
    parser.add_argument("--out", help="pretty JSON dry-run report")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--report", help="optional dry-run report to include in verification")
    args = parser.parse_args(argv)

    if not args.verify and args.out:
        output_identity = _path_identity(args.out)
        input_paths = [args.payloads, args.bindings]
        if args.new_payload:
            input_paths.append(args.new_payload)
        aliases = [path for path in input_paths if _path_identity(path) == output_identity]
        if aliases:
            parser.error("--out must not overwrite an input path: %s" % aliases[0])

    payloads = read_jsonl(args.payloads)
    bindings = read_jsonl(args.bindings)
    if args.verify:
        report = read_json(args.report) if args.report else None
        errors = verify_dataset(payloads, bindings, report)
        if errors:
            for error in errors:
                print("ERROR " + error)
            return 1
        print("PASS - %d payloads, %d bindings satisfy live-payload-or-tombstone-conflict" % (
            len(payloads), len(bindings)))
        return 0

    if not (args.old_payload_id and args.new_payload and args.out):
        parser.error("dry-run mode requires --old-payload-id, --new-payload, and --out")
    report = build_rebind_report(
        payloads, bindings, args.old_payload_id, read_json(args.new_payload)
    )
    dump_review(args.out, report)
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
