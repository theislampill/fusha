#!/usr/bin/env python3
"""Typed, fail-closed, append-only Qamus fact ledger (stdlib only).

The caller supplies the store directory. It contains ``ledger.jsonl`` and a
compact, disposable ``index.json``. State changes append revisions; no ledger
line is edited in place. This module does not project or consume facts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "qamus" / "schemas" / "fact-ledger-row.schema.json"
GATE_PATH = ROOT / "nahw" / "evals" / "grammar-decision-gates.json"
LEDGER_NAME = "ledger.jsonl"
INDEX_NAME = "index.json"

IDENTITY_CORE_FIELDS = (
    "subject_type",
    "subject_identity",
    "fact_type",
    "scope",
)

TRANSITIONS = {
    "candidate": {"review_required", "blocked", "invalid"},
    "review_required": {"certified", "rejected", "tie_unresolved"},
    "certified": {"superseded", "materialized"},
    "rejected": set(),
    "tie_unresolved": set(),
    "blocked": set(),
    "invalid": set(),
    "superseded": set(),
    "materialized": set(),
    "conflicted": set(),
}


class ValidationError(ValueError):
    """Raised when a row, transition, or ledger fails closed validation."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def identity_core(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return the stable semantic identity used by ``fact_id``.

    Review alternatives and all evidence/state/lineage metadata are excluded.
    Scope is included because an occurrence fact and a global fact are not the
    same assertion even when their visible value happens to match.
    """

    core = {name: row.get(name) for name in IDENTITY_CORE_FIELDS}
    core["value"] = (row.get("candidate_or_value") or {}).get("value")
    return core


def compute_fact_id(row: Dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(identity_core(row)).encode("utf-8")).hexdigest()
    return "sha256:" + digest


def load_schema(path: os.PathLike[str] | str = SCHEMA_PATH) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        schema = json.load(handle)
    if schema.get("type") != "object" or "x-fact-type-registry" not in schema:
        raise ValidationError("fact ledger schema is missing its open fact-type registry")
    return schema


def _type_ok(value: Any, expected: Any) -> bool:
    choices = expected if isinstance(expected, list) else [expected]
    for item in choices:
        if item == "null" and value is None:
            return True
        if item == "object" and isinstance(value, dict):
            return True
        if item == "array" and isinstance(value, list):
            return True
        if item == "string" and isinstance(value, str):
            return True
        if item == "boolean" and isinstance(value, bool):
            return True
        if item == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if item == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
    return False


def _resolve_ref(root: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValidationError("external schema refs are not supported: %s" % ref)
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _validate_node(value: Any, spec: Dict[str, Any], path: str,
                   errors: List[str], root: Dict[str, Any]) -> None:
    if "$ref" in spec:
        _validate_node(value, _resolve_ref(root, spec["$ref"]), path, errors, root)
        return
    for keyword in ("oneOf", "anyOf"):
        if keyword in spec:
            branch_errors = []
            for branch in spec[keyword]:
                candidate: List[str] = []
                _validate_node(value, branch, path, candidate, root)
                branch_errors.append(candidate)
            matches = sum(not candidate for candidate in branch_errors)
            if keyword == "oneOf" and matches != 1:
                errors.append("%s: must match exactly one schema branch" % path)
            if keyword == "anyOf" and matches < 1:
                errors.append("%s: must match at least one schema branch" % path)
            return
    if "type" in spec and not _type_ok(value, spec["type"]):
        errors.append("%s: expected type %r, got %s" % (path, spec["type"], type(value).__name__))
        return
    if "const" in spec and value != spec["const"]:
        errors.append("%s: %r != const %r" % (path, value, spec["const"]))
    if "enum" in spec and value not in spec["enum"]:
        errors.append("%s: %r not in enum" % (path, value))
    if isinstance(value, str):
        if "minLength" in spec and len(value) < spec["minLength"]:
            errors.append("%s: shorter than minLength %d" % (path, spec["minLength"]))
        if "pattern" in spec and not re.search(spec["pattern"], value):
            errors.append("%s: %r does not match /%s/" % (path, value, spec["pattern"]))
    if isinstance(value, list):
        if "minItems" in spec and len(value) < spec["minItems"]:
            errors.append("%s: fewer than minItems %d" % (path, spec["minItems"]))
        if "items" in spec:
            for index, item in enumerate(value):
                _validate_node(item, spec["items"], "%s[%d]" % (path, index), errors, root)
    if isinstance(value, dict):
        if "minProperties" in spec and len(value) < spec["minProperties"]:
            errors.append("%s: fewer than minProperties %d" % (path, spec["minProperties"]))
        properties = spec.get("properties", {})
        for required in spec.get("required", []):
            if required not in value:
                errors.append("%s: missing required key %r" % (path, required))
        additional = spec.get("additionalProperties", True)
        for key, item in value.items():
            child = "%s.%s" % (path, key)
            if key in properties:
                _validate_node(item, properties[key], child, errors, root)
            elif additional is False:
                errors.append("%s: additional property not allowed" % child)
            elif isinstance(additional, dict):
                _validate_node(item, additional, child, errors, root)


def validate_schema(row: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> List[str]:
    schema = schema or load_schema()
    errors: List[str] = []
    _validate_node(row, schema, "$", errors, schema)
    return errors


def _two_vote_fact_types(schema: Dict[str, Any], gate_path: os.PathLike[str] | str) -> set[str]:
    with open(gate_path, encoding="utf-8") as handle:
        gates = json.load(handle)
    try:
        triggers = set(gates["gates"]["two_vote_required"]["trigger_when_ANY"])
    except (KeyError, TypeError) as exc:
        raise ValidationError("grammar-decision-gates.json cannot supply two_vote_required triggers") from exc
    result = set()
    for entry in schema["x-fact-type-registry"]["types"]:
        trigger = entry.get("gate_trigger")
        if trigger:
            if trigger not in triggers:
                raise ValidationError(
                    "fact type %s maps to missing gate SSOT trigger %s" % (entry["id"], trigger)
                )
            result.add(entry["id"])
    return result


def _has_semantic_tie(row: Dict[str, Any]) -> bool:
    candidate = row.get("candidate_or_value") or {}
    return bool(candidate.get("semantic_tie")) or any(
        bool(alt.get("semantic_tie"))
        for alt in candidate.get("competing_alternatives", [])
        if isinstance(alt, dict)
    )


def _is_collision_revision(row: Dict[str, Any]) -> bool:
    return any(
        item.get("type") == "certified_collision" and len(item.get("fact_ids", [])) >= 2
        for item in row.get("defeaters", [])
        if isinstance(item, dict)
    )


def _is_tier_annotation_revision(row: Dict[str, Any], previous: Dict[str, Any]) -> bool:
    """Allow an append-only T4 annotation without changing review disposition."""

    if previous.get("certification_state") != "review_required":
        return False
    prior_exceptions = previous.get("exceptions") or []
    next_exceptions = row.get("exceptions") or []
    if next_exceptions[:len(prior_exceptions)] != prior_exceptions:
        return False
    added = next_exceptions[len(prior_exceptions):]
    if not added or any(item.get("type") != "tier_due_process_annotation" for item in added):
        return False
    stable_ignoring = {"exceptions", "provenance", "supersedes"}
    return all(
        row.get(key) == value
        for key, value in previous.items()
        if key not in stable_ignoring
    )


def validate_row(row: Dict[str, Any], *, previous: Optional[Dict[str, Any]] = None,
                 schema: Optional[Dict[str, Any]] = None,
                 gate_path: os.PathLike[str] | str = GATE_PATH) -> None:
    """Validate structure, semantic invariants, and (when supplied) transition."""

    schema = schema or load_schema()
    identity = row.get("subject_identity")
    carrier_fields = {"loc", "entry_id", "card_id", "qword_row_id"}
    if row.get("subject_type") == "surface_occurrence" and (
        not isinstance(identity, dict) or not carrier_fields <= set(identity)
    ):
        raise ValidationError("surface occurrence requires the full D-13 carrier object")
    if row.get("scope") == "occurrence" and (
        row.get("subject_type") != "surface_occurrence"
        or not isinstance(identity, dict)
        or not carrier_fields <= set(identity)
    ):
        raise ValidationError("occurrence-scoped fact requires the full D-13 carrier object")
    errors = validate_schema(row, schema)
    if errors:
        raise ValidationError("schema validation failed: " + "; ".join(errors))

    expected_id = compute_fact_id(row)
    if row["fact_id"] != expected_id:
        raise ValidationError("fact_id does not match the content-addressed identity/type/value core")

    identity = row["subject_identity"]
    if identity.get("ref_type") != row["subject_type"]:
        raise ValidationError("subject_identity.ref_type must match subject_type")

    if re.match(r"^(?:deployed|materialized)(?::|/)", row["source_address"]["address"], re.I):
        raise ValidationError("a deployed row is not an admissible source address")

    if row["fact_type"] in {"case_mood_governor", "irab_rendering"} and row["scope"] != "occurrence":
        if "syntactic_compatibility_relation" not in row["dependency_hashes"]:
            raise ValidationError(
                "non-occurrence case/governor fact requires a certified syntactic compatibility relation hash"
            )

    state = row["certification_state"]
    evidence_types = {item["type"] for item in row["evidence"]}
    if "statistical_signal" in evidence_types and state != "candidate":
        raise ValidationError("statistical_signal evidence may support candidate state only")
    if state in {"certified", "materialized"}:
        if not row["evidence"]:
            raise ValidationError("certification requires non-empty evidence")
    if _has_semantic_tie(row) and state in {"certified", "rejected"}:
        raise ValidationError("a true semantic tie must end in tie_unresolved, not deterministic adjudication")

    if state == "certified" and row["fact_type"] in _two_vote_fact_types(schema, gate_path):
        approvals = [
            vote for vote in row["review_votes"]
            if vote["independent"] and vote["vote"] == "approve"
        ]
        if len({vote["voter_id"] for vote in approvals}) < 2:
            raise ValidationError("certification requires at least two independent approving votes")
        evidence_ids = {item["evidence_id"] for item in row["evidence"]}
        if any(vote["evidence_ref"] not in evidence_ids for vote in approvals):
            raise ValidationError("every approving vote evidence_ref must resolve to evidence[]")

    calibration = row["confidence_or_calibration"]
    if calibration is not None:
        evidence_ids = {item["evidence_id"] for item in row["evidence"]}
        if any(ref not in evidence_ids for ref in calibration["basis_evidence_refs"]):
            raise ValidationError("confidence/calibration basis_evidence_refs must resolve to evidence[]")

    if previous is None:
        if state != "candidate" or row["supersedes"] is not None:
            raise ValidationError("a new fact must begin as candidate with supersedes=null")
    else:
        if row["fact_id"] != previous["fact_id"] or row["supersedes"] != previous["fact_id"]:
            raise ValidationError("state revision must preserve fact_id and supersede its prior fact_id")
        prior = previous["certification_state"]
        if state == "conflicted" and _is_collision_revision(row):
            if prior not in {"review_required", "certified"}:
                raise ValidationError("collision assignment requires a review_required or certified fact")
        elif state == prior == "review_required" and _is_tier_annotation_revision(row, previous):
            pass
        elif state not in TRANSITIONS.get(prior, set()):
            raise ValidationError("illegal transition: %s -> %s" % (prior, state))


def _collision_key(row: Dict[str, Any]) -> str:
    return _canonical({
        "subject_identity": row["subject_identity"],
        "fact_type": row["fact_type"],
        "scope": row["scope"],
    })


class FactLedgerStore:
    """Append-only JSONL store with a deterministic rebuildable index."""

    def __init__(self, directory: os.PathLike[str] | str,
                 schema_path: os.PathLike[str] | str = SCHEMA_PATH,
                 gate_path: os.PathLike[str] | str = GATE_PATH):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.directory / LEDGER_NAME
        self.index_path = self.directory / INDEX_NAME
        self.schema = load_schema(schema_path)
        self.gate_path = Path(gate_path)
        _two_vote_fact_types(self.schema, self.gate_path)

    def _rows(self) -> List[Dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        rows = []
        with self.ledger_path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    raise ValidationError("blank ledger line %d" % number)
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValidationError("invalid JSON on ledger line %d: %s" % (number, exc)) from exc
        return rows

    @staticmethod
    def _current(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        current: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            current[row["fact_id"]] = row
        return current

    def _append_line(self, row: Dict[str, Any]) -> None:
        with self.ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical(row) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _collision_rows(self, proposed: Dict[str, Any], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        key = _collision_key(proposed)
        return sorted(
            [
                row for fact_id, row in self._current(rows).items()
                if fact_id != proposed["fact_id"]
                and row["certification_state"] == "certified"
                and _collision_key(row) == key
            ],
            key=lambda item: item["fact_id"],
        )

    def append(self, row: Dict[str, Any]) -> Dict[str, Any]:
        proposed = copy.deepcopy(row)
        rows = self._rows()
        current = self._current(rows)
        previous = current.get(proposed.get("fact_id"))
        validate_row(
            proposed, previous=previous, schema=self.schema, gate_path=self.gate_path
        )

        collisions = self._collision_rows(proposed, rows) if proposed["certification_state"] == "certified" else []
        if collisions:
            involved = sorted([proposed["fact_id"]] + [item["fact_id"] for item in collisions])
            defeater = {"type": "certified_collision", "fact_ids": involved}
            revisions = []
            for old in collisions:
                revision = copy.deepcopy(old)
                revision["certification_state"] = "conflicted"
                revision["supersedes"] = old["fact_id"]
                revision["defeaters"] = list(revision["defeaters"]) + [defeater]
                validate_row(revision, previous=old, schema=self.schema, gate_path=self.gate_path)
                revisions.append(revision)
            proposed["certification_state"] = "conflicted"
            proposed["supersedes"] = previous["fact_id"] if previous else proposed["fact_id"]
            proposed["defeaters"] = list(proposed["defeaters"]) + [defeater]
            validate_row(proposed, previous=previous, schema=self.schema, gate_path=self.gate_path)
            for revision in revisions + [proposed]:
                self._append_line(revision)
        else:
            self._append_line(proposed)
        self.rebuild_index()
        return proposed

    def transition(self, fact_id: str, state: str, **updates: Any) -> Dict[str, Any]:
        current = self._current(self._rows()).get(fact_id)
        if current is None:
            raise ValidationError("unknown fact_id: %s" % fact_id)
        row = copy.deepcopy(current)
        row.update(copy.deepcopy(updates))
        row["certification_state"] = state
        row["supersedes"] = fact_id
        if compute_fact_id(row) != fact_id:
            raise ValidationError("a transition cannot change the identity/type/value core")
        return self.append(row)

    def rebuild_index(self) -> Dict[str, Any]:
        rows = self._rows()
        facts: Dict[str, List[int]] = {}
        current: Dict[str, int] = {}
        for number, row in enumerate(rows, 1):
            facts.setdefault(row["fact_id"], []).append(number)
            current[row["fact_id"]] = number
        index = {"schema": "qamus.fact_ledger_index.v1", "facts": facts, "current": current}
        payload = _canonical(index) + "\n"
        fd, name = tempfile.mkstemp(prefix="index-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.index_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return index

    def query(self, *, fact_id: Optional[str] = None, fact_type: Optional[str] = None,
              state: Optional[str] = None, current_only: bool = True) -> List[Dict[str, Any]]:
        rows = self._rows()
        if current_only:
            rows = list(self._current(rows).values())
        return [
            row for row in rows
            if (fact_id is None or row["fact_id"] == fact_id)
            and (fact_type is None or row["fact_type"] == fact_type)
            and (state is None or row["certification_state"] == state)
        ]

    def history(self, fact_id: str) -> List[Dict[str, Any]]:
        return self.query(fact_id=fact_id, current_only=False)

    def validate_all(self) -> List[str]:
        errors: List[str] = []
        current: Dict[str, Dict[str, Any]] = {}
        for number, row in enumerate(self._rows(), 1):
            try:
                validate_row(
                    row,
                    previous=current.get(row.get("fact_id")),
                    schema=self.schema,
                    gate_path=self.gate_path,
                )
            except ValidationError as exc:
                errors.append("line %d: %s" % (number, exc))
            current[row.get("fact_id")] = row
        certified_by_key: Dict[str, List[str]] = {}
        for fact_id, row in current.items():
            if row.get("certification_state") == "certified":
                certified_by_key.setdefault(_collision_key(row), []).append(fact_id)
        for fact_ids in certified_by_key.values():
            if len(fact_ids) > 1:
                errors.append("certified collision remains unresolved: %s" % ", ".join(sorted(fact_ids)))
        return errors


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _self_test() -> None:
    base = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "rule",
        "subject_identity": {"ref_type": "rule", "id": "self-test"},
        "fact_type": "calibration",
        "candidate_or_value": {"value": "pending", "competing_alternatives": []},
        "scope": "rule_global",
        "source_address": {"address": "rule:self-test", "source_kind": "rule"},
        "evidence": [],
        "provenance": {
            "actor": "fact-ledger-self-test",
            "method": "inline",
            "created_at": "1970-01-01T00:00:00Z",
            "input_hashes": {"self-test": "sha256:" + "0" * 64},
        },
        "review_votes": [],
        "certification_state": "candidate",
        "confidence_or_calibration": None,
        "defeaters": [],
        "exceptions": [],
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": None,
        "fact_id": "",
    }
    base["fact_id"] = compute_fact_id(base)
    with tempfile.TemporaryDirectory() as directory:
        store = FactLedgerStore(directory)
        store.append(base)
        store.transition(base["fact_id"], "blocked")
        if store.validate_all() or len(store.history(base["fact_id"])) != 2:
            raise ValidationError("self-test round trip failed")
    print("fact_ledger self-test OK")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run an offline store smoke test")
    subparsers = parser.add_subparsers(dest="command")

    append_parser = subparsers.add_parser("append", help="validate and append one JSON row")
    append_parser.add_argument("--directory", required=True)
    append_parser.add_argument("--row", required=True, help="JSON file path, or - for stdin")

    validate_parser = subparsers.add_parser("validate", help="validate every ledger row and collision state")
    validate_parser.add_argument("--directory", required=True)

    query_parser = subparsers.add_parser("query", help="query current rows (or all revisions)")
    query_parser.add_argument("--directory", required=True)
    query_parser.add_argument("--fact-id")
    query_parser.add_argument("--fact-type")
    query_parser.add_argument("--state")
    query_parser.add_argument("--all", action="store_true", help="include all revisions")

    history_parser = subparsers.add_parser("history", help="show all revisions for a fact_id")
    history_parser.add_argument("--directory", required=True)
    history_parser.add_argument("--fact-id", required=True)

    args = parser.parse_args(argv)
    try:
        if args.self_test:
            _self_test()
            return 0
        if not args.command:
            parser.error("a command or --self-test is required")
        store = FactLedgerStore(args.directory)
        if args.command == "append":
            if args.row == "-":
                row = json.load(sys.stdin)
            else:
                with open(args.row, encoding="utf-8") as handle:
                    row = json.load(handle)
            _print_json(store.append(row))
        elif args.command == "validate":
            errors = store.validate_all()
            if errors:
                for error in errors:
                    print("ERROR " + error, file=sys.stderr)
                return 1
            print("OK: %d ledger row(s) valid" % len(store.query(current_only=False)))
        elif args.command == "query":
            _print_json(store.query(
                fact_id=args.fact_id,
                fact_type=args.fact_type,
                state=args.state,
                current_only=not args.all,
            ))
        elif args.command == "history":
            _print_json(store.history(args.fact_id))
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
