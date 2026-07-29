#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Certification store reconciliation pass (stdlib only).

Executes docs/certification-store-reconciliation.md: enumerates every
currently-certified token-layer fact-ledger row (tools/fact_ledger.py stores,
``certification_state``), derives the deterministic typed-claim mapping id,
detects duplicates/conflicts across the token stores and against the
typed-claim plane (tools/certify_typed_fact.py event trail,
``certification.status``), mechanically re-verifies ONE bounded family's
recorded evidence against its ladder rung, and emits
``qamus/reports/certification-store-reconciliation.jsonl`` + meta.

Hard rules enforced here and red-tested in --self-test:

* NO double-counting — every certified count names its store (plane) and
  migration status; an unlabeled merged tally is refused;
* NO auto-promotion — ``imported_certified`` is never assigned by this tool;
  only tools/certify_typed_fact.py writes typed-claim certified;
* NO conflict auto-win — a disagreement between stores maps to
  ``conflict`` / review_required; a resolver picking a winner is refused.

The report is deterministic (no timestamps in rows; meta derives entirely from
committed inputs), so check_regressions can regenerate and diff it.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import certify_typed_fact  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROW_SCHEMA = "qamus.cert_store_reconciliation.v1"
META_SCHEMA = "qamus.cert_store_reconciliation_meta.v1"

FACT_LEDGER_BASE = ROOT / "qamus" / "indexes" / "largelexicon" / "fact-ledger"

# Token-layer stores that carry (or carried) certified rows. rm20-morphline is
# enumerated for completeness but is materialized-only (0 currently certified).
TOKEN_STORES = ("c2-decidable", "funcword-cert", "rebind-cert", "rm20-morphline")

# docs/certification-store-reconciliation.md section 2 — all three land on the
# two-vote rung (rung 4) of docs/certification-authority.md section 2.
FACT_TYPE_MAP = {
    "function_word_analysis": "contextual_function",
    "governing_entry_analysis": "governor_relation",
    "morphline_rendering": "irab_rendering",
}

MIGRATION_STATUSES = (
    "unmapped",
    "mapped_unverified",
    "mapped_verified",
    "imported_certified",
    "conflict",
)

# Bounded worked family (doc section 7): funcword-cert, one entry, 8 rows.
FAMILY_STORE = "funcword-cert"
FAMILY_ENTRY_ID = "014e23727379"
FAMILY_MAX_ROWS = 25

REPORT_PATH = ROOT / "qamus" / "reports" / "certification-store-reconciliation.jsonl"
META_PATH = ROOT / "qamus" / "reports" / "certification-store-reconciliation.meta.json"


class ReconciliationError(ValueError):
    """Raised when a contract rule (double-count, auto-promotion, auto-win) is violated."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Token-layer enumeration
# ---------------------------------------------------------------------------

def load_current_rows(ledger_path: Path) -> Dict[str, Dict[str, Any]]:
    """Fold a fact-ledger jsonl to its current row per fact_id (last wins)."""

    current: Dict[str, Dict[str, Any]] = {}
    with ledger_path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                raise ReconciliationError(
                    "%s: blank ledger line %d" % (ledger_path, number))
            row = json.loads(line)
            current[row["fact_id"]] = row
    return current


def enumerate_certified(base: Path = FACT_LEDGER_BASE,
                        stores: Iterable[str] = TOKEN_STORES
                        ) -> Dict[str, List[Dict[str, Any]]]:
    """Return currently-certified rows per store (rm20 contributes zero)."""

    certified: Dict[str, List[Dict[str, Any]]] = {}
    for store in stores:
        ledger = base / store / "ledger.jsonl"
        rows = load_current_rows(ledger) if ledger.exists() else {}
        certified[store] = sorted(
            (row for row in rows.values()
             if row.get("certification_state") == "certified"),
            key=lambda row: (
                _loc_sort_key(row.get("subject_identity", {}).get("loc")),
                row.get("fact_id", ""),
            ),
        )
    return certified


def _loc_sort_key(loc: Optional[str]) -> Tuple[int, int, int]:
    try:
        surah, ayah, token = (int(part) for part in str(loc).split(":"))
        return (surah, ayah, token)
    except (ValueError, AttributeError):
        return (999, 999, 999)


# ---------------------------------------------------------------------------
# Mapping derivation (doc section 2)
# ---------------------------------------------------------------------------

def map_fact_type(token_fact_type: str) -> str:
    typed = FACT_TYPE_MAP.get(token_fact_type)
    if typed is None:
        raise ReconciliationError(
            "token fact_type %r has no declared typed-claim mapping; extend the "
            "doc section 2 table before reconciling it" % token_fact_type)
    return typed


def derive_typed_fact_id(row: Dict[str, Any]) -> str:
    """Deterministic typed-claim fact id for a token-layer row (doc section 2)."""

    core = {
        "plane": "typed_claim",
        "migration": "token_layer_v1",
        "subject_identity": row["subject_identity"],
        "fact_type": map_fact_type(row["fact_type"]),
        "scope": row["scope"],
        "value": (row.get("candidate_or_value") or {}).get("value"),
    }
    return _sha256_text(_canonical(core))


def duplicate_key(row: Dict[str, Any]) -> str:
    return _canonical({
        "loc": (row.get("subject_identity") or {}).get("loc"),
        "typed_fact_type": map_fact_type(row["fact_type"]),
    })


# ---------------------------------------------------------------------------
# Contract guards (red-tested)
# ---------------------------------------------------------------------------

def assert_labeled_count(entry: Dict[str, Any]) -> Dict[str, Any]:
    """A certified count must name its plane/store and migration status scope.

    Refuses any tally that merges the token-layer and typed-claim planes into
    one unlabeled number (doc section 8).
    """

    required = {"plane", "stores", "state_field", "migration_statuses", "count"}
    missing = required - set(entry)
    if missing:
        raise ReconciliationError(
            "double-count guard: certified count is missing labels %s — a "
            "certified count must name its store and mapping status"
            % ", ".join(sorted(missing)))
    if entry["plane"] not in {"token_layer", "typed_claim"}:
        raise ReconciliationError(
            "double-count guard: plane %r is not a single plane; a count may "
            "never sum across certification planes" % (entry["plane"],))
    return entry


def assign_migration_status(status: str, *, verification: Optional[Dict[str, Any]]) -> str:
    """Fail closed on auto-promotion (doc sections 4 and 6).

    ``imported_certified`` is only writable by tools/certify_typed_fact.py after
    consuming a validated bundle; this reconciler may never assign it, and
    ``mapped_verified`` requires an attached passing verification record.
    """

    if status not in MIGRATION_STATUSES:
        raise ReconciliationError("unknown migration status %r" % status)
    if status == "imported_certified":
        raise ReconciliationError(
            "auto-promotion refused: only tools/certify_typed_fact.py may "
            "produce imported_certified (typed-claim certified), never the "
            "reconciler")
    if status == "mapped_verified":
        if not verification or verification.get("result") != "pass":
            raise ReconciliationError(
                "auto-promotion refused: mapped_verified requires a passing "
                "recorded-evidence verification record")
    return status


def resolve_conflict(group: List[Dict[str, Any]], *, auto_resolve: bool = False) -> str:
    """Conflicting stores never auto-win (doc section 5)."""

    if auto_resolve:
        raise ReconciliationError(
            "conflict auto-win refused: disagreement between certification "
            "stores routes to review_required; no store wins mechanically")
    return "conflict"


# ---------------------------------------------------------------------------
# Bounded-family verification (doc section 7)
# ---------------------------------------------------------------------------

def _load_jsonl_by_packet_id(path: Path) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            packet_id = row.get("packet_id")
            if packet_id:
                result[packet_id] = row
    return result


def verify_family_row(row: Dict[str, Any], *, repo_root: Path = ROOT) -> Dict[str, Any]:
    """Re-verify one row's recorded evidence against rung 4's recorded shape.

    Checks (doc section 7): committed evidence files, packet resolution +
    packet_sha256 binding to provenance.input_hashes.packet_row, both votes
    bound to the same packet_sha256, and two independent engine-diverse
    approvals. Returns {"result": "pass"|"fail", "checks": [...], "failures": [...]}.
    """

    checks: List[str] = []
    failures: List[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append(name)
        if not ok:
            failures.append(name + (": " + detail if detail else ""))

    evidence = {item.get("evidence_id"): item for item in row.get("evidence", [])}
    check("evidence_carries_packet_and_both_votes",
          {"packet", "vote-A", "vote-B"} <= set(evidence),
          "found %s" % sorted(evidence))

    files: Dict[str, Path] = {}
    for evidence_id in ("packet", "vote-A", "vote-B"):
        item = evidence.get(evidence_id) or {}
        address = str(item.get("source_address") or "")
        file_part, _, fragment = address.partition("#")
        path = repo_root / file_part
        committed = bool(file_part) and not os.path.isabs(file_part) and path.exists()
        check("evidence_file_committed_in_repo:%s" % evidence_id, committed, file_part)
        if committed:
            files[evidence_id] = path

    packet_id = None
    fragment = str((evidence.get("packet") or {}).get("source_address") or "").partition("#")[2]
    if fragment.startswith("packet_id="):
        packet_id = fragment[len("packet_id="):]
    check("packet_address_names_packet_id", packet_id is not None)

    expected_sha = str(
        (row.get("provenance") or {}).get("input_hashes", {}).get("packet_row") or "")
    packet_row = None
    if packet_id and "packet" in files:
        packet_row = _load_jsonl_by_packet_id(files["packet"]).get(packet_id)
    check("packet_row_resolves_in_committed_file", packet_row is not None,
          str(packet_id))
    if packet_row is not None:
        check("packet_sha256_matches_provenance_input_hash",
              "sha256:" + str(packet_row.get("packet_sha256")) == expected_sha,
              "packet %s vs provenance %s" % (packet_row.get("packet_sha256"), expected_sha))
        for vote_id in ("vote-A", "vote-B"):
            vote_row = (
                _load_jsonl_by_packet_id(files[vote_id]).get(packet_id)
                if vote_id in files else None
            )
            check("vote_row_resolves:%s" % vote_id, vote_row is not None)
            if vote_row is not None:
                check("vote_bound_to_same_packet_sha256:%s" % vote_id,
                      vote_row.get("packet_sha256") == packet_row.get("packet_sha256"))

    approvals = [
        vote for vote in row.get("review_votes", [])
        if vote.get("independent") and vote.get("vote") == "approve"
    ]
    voter_ids = {vote.get("voter_id") for vote in approvals}
    engines = {str(vote.get("voter_id", "")).partition(":")[2] for vote in approvals}
    check("two_independent_approvals_distinct_voters", len(voter_ids) >= 2,
          str(sorted(voter_ids)))
    check("approvals_engine_diverse", len(engines) >= 2, str(sorted(engines)))

    return {
        "rung": "two_vote_required",
        "result": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
    }


def select_family(certified: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rows = [
        row for row in certified.get(FAMILY_STORE, [])
        if (row.get("subject_identity") or {}).get("entry_id") == FAMILY_ENTRY_ID
    ]
    if len(rows) > FAMILY_MAX_ROWS:
        raise ReconciliationError(
            "worked family exceeds the bounded size (%d > %d)"
            % (len(rows), FAMILY_MAX_ROWS))
    return rows


# ---------------------------------------------------------------------------
# Report build
# ---------------------------------------------------------------------------

def build_report(base: Path = FACT_LEDGER_BASE,
                 typed_store_dir: Optional[Path] = None,
                 repo_root: Path = ROOT) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    certified = enumerate_certified(base)

    # Typed-claim plane certified set (absent store = zero certified).
    typed_dir = typed_store_dir if typed_store_dir is not None else certify_typed_fact.DEFAULT_STORE_DIR
    typed_certified_ids: List[str] = []
    if (Path(typed_dir) / certify_typed_fact.EVENTS_NAME).exists():
        typed_store = certify_typed_fact.TypedFactCertificationStore(typed_dir)
        trail_errors = typed_store.validate_trail()
        if trail_errors:
            raise ReconciliationError(
                "typed-claim event trail is invalid: " + "; ".join(trail_errors[:3]))
        typed_certified_ids = typed_store.certified_fact_ids()
    typed_certified = set(typed_certified_ids)

    # Duplicate groups across token stores (same loc + typed predicate).
    groups: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for store, rows in certified.items():
        for row in rows:
            groups.setdefault(duplicate_key(row), []).append((store, row))

    family_ids = {row["fact_id"] for row in select_family(certified)}

    report: List[Dict[str, Any]] = []
    duplicate_count = 0
    conflict_count = 0
    verified_pass = 0
    verified_fail = 0
    for store in TOKEN_STORES:
        for row in certified.get(store, []):
            key = duplicate_key(row)
            siblings = [
                {"token_store": other_store, "token_fact_id": other["fact_id"]}
                for other_store, other in groups[key]
                if other["fact_id"] != row["fact_id"]
            ]
            typed_fact_id = derive_typed_fact_id(row)
            verification: Optional[Dict[str, Any]] = None
            if siblings:
                duplicate_count += 1
                values = {
                    _canonical((other.get("candidate_or_value") or {}).get("value"))
                    for _, other in groups[key]
                }
                if len(values) > 1:
                    conflict_count += 1
                    status = resolve_conflict([other for _, other in groups[key]])
                else:
                    status = assign_migration_status(
                        "mapped_unverified", verification=None)
            elif typed_fact_id in typed_certified:
                # Recognized from the certify_typed_fact event trail itself —
                # the import already happened there; the reconciler records the
                # join but never *assigns* this status (assign_migration_status
                # refuses it by design).
                status = "imported_certified"
            else:
                if row["fact_id"] in family_ids:
                    verification = verify_family_row(row, repo_root=repo_root)
                    verification["family"] = "%s:entry:%s" % (FAMILY_STORE, FAMILY_ENTRY_ID)
                    verification["import_eligible_pending_bundle_conversion"] = (
                        verification["result"] == "pass")
                    if verification["result"] == "pass":
                        verified_pass += 1
                        status = assign_migration_status(
                            "mapped_verified", verification=verification)
                    else:
                        verified_fail += 1
                        status = assign_migration_status(
                            "mapped_unverified", verification=None)
                else:
                    status = assign_migration_status(
                        "mapped_unverified", verification=None)
            identity = row.get("subject_identity") or {}
            entry: Dict[str, Any] = {
                "schema": ROW_SCHEMA,
                "token_store": store,
                "token_fact_id": row["fact_id"],
                "token_fact_type": row["fact_type"],
                "token_state": row["certification_state"],
                "loc": identity.get("loc"),
                "entry_id": identity.get("entry_id"),
                "card_id": identity.get("card_id"),
                "qword_row_id": identity.get("qword_row_id"),
                "scope": row.get("scope"),
                "typed_fact_type": map_fact_type(row["fact_type"]),
                "typed_fact_id": typed_fact_id,
                "typed_plane_status": (
                    "certified" if typed_fact_id in typed_certified else "absent"
                ),
                "migration_status": status,
                "duplicate_group": siblings or None,
                "verification": verification,
            }
            report.append(entry)

    counts = [
        assert_labeled_count({
            "plane": "token_layer",
            "stores": [store],
            "state_field": "certification_state",
            "migration_statuses": sorted({
                item["migration_status"] for item in report
                if item["token_store"] == store
            }) or ["n/a"],
            "count": len(certified.get(store, [])),
        })
        for store in TOKEN_STORES
    ]
    counts.append(assert_labeled_count({
        "plane": "typed_claim",
        "stores": ["qamus/certification/typed-fact-store"],
        "state_field": "certification.status",
        "migration_statuses": ["imported_certified"],
        "count": len(typed_certified_ids),
    }))

    status_counts: Dict[str, int] = {}
    for item in report:
        status_counts[item["migration_status"]] = status_counts.get(
            item["migration_status"], 0) + 1

    meta = {
        "schema": META_SCHEMA,
        "contract": "docs/certification-store-reconciliation.md",
        "canonical_plane": "typed_claim",
        "token_layer_role": "historical evidence store; importable, never auto-promoted",
        "writers": {
            "typed_claim_certified": "tools/certify_typed_fact.py (only writer)",
            "token_layer": "tools/fact_ledger.py (legacy store authority; frozen for new certifications)",
        },
        "certified_counts_labeled": counts,
        "no_double_count_rule": (
            "a certified count must name its plane/store and migration status; "
            "sums across planes are refused"
        ),
        "mapping_rows": len(report),
        "migration_status_counts": status_counts,
        "duplicate_rows": duplicate_count,
        "conflict_rows": conflict_count,
        "worked_family": {
            "family": "%s:entry:%s" % (FAMILY_STORE, FAMILY_ENTRY_ID),
            "rows": len(family_ids),
            "verified_pass": verified_pass,
            "verified_fail": verified_fail,
            "verdict": (
                "recorded evidence meets rung-4 recorded-shape checks; "
                "import-eligible pending qamus.two_vote_artifact.v1 bundle conversion"
                if family_ids and verified_fail == 0 and verified_pass == len(family_ids)
                else "family verification incomplete or failing — see rows"
            ),
        },
        "input_hashes": {
            "%s/ledger.jsonl" % store: _sha256_file(base / store / "ledger.jsonl")
            for store in TOKEN_STORES
            if (base / store / "ledger.jsonl").exists()
        },
    }
    return report, meta


def write_report(report: List[Dict[str, Any]], meta: Dict[str, Any],
                 report_path: Path = REPORT_PATH, meta_path: Path = META_PATH) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in report:
            handle.write(_canonical(row) + "\n")
    with meta_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def check_committed(report_path: Path = REPORT_PATH, meta_path: Path = META_PATH) -> List[str]:
    """Regenerate deterministically and diff against the committed artifacts."""

    errors: List[str] = []
    report, meta = build_report()
    expected_report = "".join(_canonical(row) + "\n" for row in report)
    expected_meta = json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    for path, expected in ((report_path, expected_report), (meta_path, expected_meta)):
        if not path.exists():
            errors.append("missing committed artifact: %s" % path)
        elif path.read_text(encoding="utf-8").replace("\r\n", "\n") != expected:
            errors.append("committed artifact drifted from a deterministic re-run: %s" % path)
    return errors


# ---------------------------------------------------------------------------
# Red-first self-test
# ---------------------------------------------------------------------------

def _expect_refusal(label: str, needle: str, callable_, *args: Any, **kwargs: Any) -> bool:
    try:
        callable_(*args, **kwargs)
    except ReconciliationError as exc:
        if needle in str(exc):
            return True
        print("SELF-TEST FAIL %s: expected refusal containing %r, got: %s"
              % (label, needle, exc))
        return False
    print("SELF-TEST FAIL %s: call was accepted but must be refused" % label)
    return False


def _mini_row(loc: str, fact_type: str, value: Any, state: str = "certified") -> Dict[str, Any]:
    identity = {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": "fixture-entry",
        "card_id": "fixture-card",
        "qword_row_id": "fixture-qword",
    }
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": identity,
        "fact_type": fact_type,
        "candidate_or_value": {"value": value, "competing_alternatives": []},
        "scope": "occurrence",
        "certification_state": state,
        "evidence": [],
        "provenance": {"input_hashes": {}},
        "review_votes": [],
    }
    row["fact_id"] = _sha256_text(_canonical({"fixture": [loc, fact_type, _canonical(value)]}))
    return row


def self_test() -> int:
    # Red 1: double-count — an unlabeled or cross-plane tally is refused.
    if not _expect_refusal(
            "double-count-unlabeled", "must name its store and mapping status",
            assert_labeled_count, {"count": 2619}):
        return 1
    if not _expect_refusal(
            "double-count-cross-plane", "never sum across certification planes",
            assert_labeled_count, {
                "plane": "token_layer+typed_claim",
                "stores": ["funcword-cert", "typed-fact-store"],
                "state_field": "mixed",
                "migration_statuses": ["mapped_unverified"],
                "count": 2620,
            }):
        return 1

    # Red 2: auto-promotion — the reconciler may never mint imported_certified,
    # and mapped_verified without a passing verification record is refused.
    if not _expect_refusal(
            "auto-promotion-imported", "only tools/certify_typed_fact.py",
            assign_migration_status, "imported_certified", verification=None):
        return 1
    if not _expect_refusal(
            "auto-promotion-unverified", "requires a passing",
            assign_migration_status, "mapped_verified",
            verification={"result": "fail"}):
        return 1

    # Red 3: conflict auto-win — resolving a store disagreement by picking a
    # winner is refused; the only legal outcome is conflict/review_required.
    conflicting = [
        _mini_row("2:1:1", "function_word_analysis", {"taxonomy_category": "preposition"}),
        _mini_row("2:1:1", "function_word_analysis", {"taxonomy_category": "other_particle"}),
    ]
    if not _expect_refusal(
            "conflict-auto-win", "no store wins mechanically",
            resolve_conflict, conflicting, auto_resolve=True):
        return 1
    if resolve_conflict(conflicting) != "conflict":
        print("SELF-TEST FAIL: a store disagreement must map to conflict")
        return 1

    # Red 4: an unmapped token fact_type fails closed instead of guessing.
    if not _expect_refusal(
            "unmapped-fact-type", "no declared typed-claim mapping",
            map_fact_type, "mystery_analysis"):
        return 1

    # Green: synthetic mini-stores round-trip with correct statuses and a
    # detected conflict that is NOT auto-resolved.
    with tempfile.TemporaryDirectory(prefix="storerec-") as td:
        base = Path(td) / "fact-ledger"
        rows_by_store = {
            "funcword-cert": [
                _mini_row("2:1:1", "function_word_analysis", {"taxonomy_category": "preposition"}),
                _mini_row("2:1:2", "function_word_analysis", {"taxonomy_category": "other_particle"}),
            ],
            "rebind-cert": [
                # Same loc+predicate as funcword 2:1:1 with a DIFFERENT value → conflict.
                _mini_row("2:1:1", "function_word_analysis", {"taxonomy_category": "conjunction"}),
                _mini_row("3:1:1", "governing_entry_analysis", {"governor": "fixture"}),
            ],
            "c2-decidable": [],
            "rm20-morphline": [],
        }
        for store, rows in rows_by_store.items():
            store_dir = base / store
            store_dir.mkdir(parents=True)
            with (store_dir / "ledger.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(_canonical(row) + "\n")
        report, meta = build_report(base=base, typed_store_dir=Path(td) / "absent-typed-store")
        if len(report) != 4:
            print("SELF-TEST FAIL: expected 4 mapping rows, got %d" % len(report))
            return 1
        by_key = {(item["token_store"], item["loc"]): item for item in report}
        if by_key[("funcword-cert", "2:1:1")]["migration_status"] != "conflict":
            print("SELF-TEST FAIL: divergent duplicate must be conflict")
            return 1
        if by_key[("rebind-cert", "2:1:1")]["migration_status"] != "conflict":
            print("SELF-TEST FAIL: both sides of a conflict must carry conflict status")
            return 1
        if by_key[("funcword-cert", "2:1:2")]["migration_status"] != "mapped_unverified":
            print("SELF-TEST FAIL: a clean row must be mapped_unverified (honest first pass)")
            return 1
        if meta["conflict_rows"] != 2 or meta["duplicate_rows"] != 2:
            print("SELF-TEST FAIL: meta duplicate/conflict tallies wrong: %s"
                  % {k: meta[k] for k in ("conflict_rows", "duplicate_rows")})
            return 1
        if any(item["migration_status"] == "imported_certified" for item in report):
            print("SELF-TEST FAIL: reconciler minted imported_certified")
            return 1
        for count in meta["certified_counts_labeled"]:
            assert_labeled_count(count)
        # Determinism: a second run is byte-identical.
        report2, meta2 = build_report(base=base, typed_store_dir=Path(td) / "absent-typed-store")
        if _canonical(report) != _canonical(report2) or _canonical(meta) != _canonical(meta2):
            print("SELF-TEST FAIL: report generation is not deterministic")
            return 1

    # Green: family verification on a real committed row passes, and a
    # tampered copy fails (non-constant discriminator).
    certified = enumerate_certified()
    family = select_family(certified)
    if not family:
        print("SELF-TEST FAIL: worked family %s:%s is empty" % (FAMILY_STORE, FAMILY_ENTRY_ID))
        return 1
    verdict = verify_family_row(family[0])
    if verdict["result"] != "pass":
        print("SELF-TEST FAIL: committed family row fails verification:", verdict["failures"][:3])
        return 1
    tampered = copy.deepcopy(family[0])
    tampered["provenance"]["input_hashes"]["packet_row"] = "sha256:" + "0" * 64
    if verify_family_row(tampered)["result"] != "fail":
        print("SELF-TEST FAIL: tampered packet hash must fail verification")
        return 1
    tampered2 = copy.deepcopy(family[0])
    tampered2["review_votes"][1]["voter_id"] = tampered2["review_votes"][0]["voter_id"]
    if verify_family_row(tampered2)["result"] != "fail":
        print("SELF-TEST FAIL: engine-identical votes must fail verification")
        return 1

    print("STORE RECONCILIATION SELF-TEST PASS")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="run the red-first offline self-test")
    parser.add_argument("--write", action="store_true",
                        help="regenerate the committed report + meta")
    parser.add_argument("--check", action="store_true",
                        help="regenerate to memory and diff against the committed artifacts")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return self_test()
        if args.write:
            report, meta = build_report()
            write_report(report, meta)
            print("wrote %d mapping row(s) to %s" % (len(report), REPORT_PATH.relative_to(ROOT)))
            print("worked family verdict: %s" % meta["worked_family"]["verdict"])
            return 0
        if args.check:
            errors = check_committed()
            if errors:
                for error in errors:
                    print("ERROR " + error, file=sys.stderr)
                return 1
            print("OK: committed reconciliation report matches a deterministic re-run")
            return 0
        parser.error("one of --self-test, --write, --check is required")
    except (OSError, json.JSONDecodeError, ReconciliationError,
            certify_typed_fact.CertificationError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
