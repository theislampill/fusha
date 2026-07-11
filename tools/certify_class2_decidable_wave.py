#!/usr/bin/env python3
"""Certify the T11 class-2 decidable two-vote wave without materializing it.

The writer builds an isolated FactLedgerStore in a temporary directory, validates
the complete store, and installs only ``ledger.jsonl`` plus reviewer-facing
artifacts.  The disposable ``index.json`` never enters the repository.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402


FACT_TYPE = "governing_entry_analysis"
GATE_TRIGGER = "advanced_nahw"
ACTOR = "tools/certify_class2_decidable_wave.py"
METHOD = "T11 class-2 decidable engine-diverse two-vote certification"
CREATED_AT = "2026-07-11T00:00:00Z"

QUEUE_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "class2" / "two-vote"
PACKETS_PATH = QUEUE_DIR / "packets-decidable.jsonl"
PACKET_MANIFEST_PATH = QUEUE_DIR / "packets-decidable.manifest.json"
LEDGER_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "fact-ledger" / "c2-decidable"
REPORT_PATH = QUEUE_DIR / "certification-decidable.report.json"
MANIFEST_PATH = QUEUE_DIR / "certification-decidable.manifest.json"
INPUT_NAMES = ("votes-a.jsonl", "votes-b.jsonl", "c2-decidable-analysis.json")

EXPECTED_SHA256 = {
    "votes-a.jsonl": "3dc17f2409ca0e003c787060417a83e80d50d35dac068123bb77e2ae6192b209",
    "votes-b.jsonl": "ddc6e4e1aa7f9d9456424dec6f0644bd1f816cf183d40f10c69b05eba473bb51",
    "c2-decidable-analysis.json": "dda1601d2152095f48fe9dc3be88a790d459e36031cce5dc77919bc296f60d91",
    "packets-decidable.jsonl": "ecb34710f3ef93726ab1633d79a8de7fc88d9735c8b0833c47fd1062e0b67740",
    "packets-decidable.manifest.json": "589c48a33f5adb4a012e0286c75ac31269174ddd6c354738b1e9ba6bf949609f",
}
CANONICAL_SHA256 = {
    **EXPECTED_SHA256,
    # Reviewer B's delivered file used CRLF.  The repo's eol=lf policy stores
    # the same 493 JSON records canonically with LF; retain both pins.
    "votes-b.jsonl": "40b09e07e69e6a5d83ca88cf639ff4775a035b13845f25dc34f3603ab1b9aa9e",
}

EXPECTED_COUNTS = {
    "total_rows": 493,
    "certified": 491,
    "candidate": 2,
    "same_section_different_root_certified": 376,
    "verb_vs_noun_certified": 115,
}
ABSTENTION_LOCS = {"4:101:4", "22:47:6"}
VOTER_IDS = {"A": "reviewer-A:Opus", "B": "reviewer-B:Codex"}


class CertificationStop(RuntimeError):
    """Fail-closed input, reconciliation, or output error."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise CertificationStop(f"{path}: blank JSONL line {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CertificationStop(f"{path}: invalid JSONL line {number}: {exc}") from exc
        if not isinstance(row, dict):
            raise CertificationStop(f"{path}: JSONL line {number} is not an object")
        rows.append(row)
    return rows


def index_unique(rows: Iterable[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise CertificationStop(f"{label}: row missing {key}")
        if value in result:
            raise CertificationStop(f"{label}: duplicate {key} {value}")
        result[value] = row
    return result


def verify_sha(path: Path, expected: str) -> str:
    actual = sha256_path(path)
    if actual != expected:
        raise CertificationStop(f"SHA-256 mismatch for {path}: {actual} != {expected}")
    return actual


def canonical_input_bytes(name: str, path: Path) -> bytes:
    if name.endswith(".jsonl"):
        return ("\n".join(path.read_text(encoding="utf-8").splitlines()) + "\n").encode("utf-8")
    return path.read_bytes()


def resolve_source_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    private_inputs = ROOT / ".inputs"
    if all((private_inputs / name).is_file() for name in INPUT_NAMES):
        return private_inputs
    if all((QUEUE_DIR / name).is_file() for name in INPUT_NAMES):
        return QUEUE_DIR
    raise CertificationStop("votes and analysis are absent from both .inputs and the canonical queue directory")


def _carrier_identity(loc: str, carrier: dict[str, Any]) -> dict[str, Any]:
    for field in ("entry_id", "card_id", "qword_row_id"):
        if not carrier.get(field):
            raise CertificationStop(f"{loc}: carrier missing {field}")
    return {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": carrier["entry_id"],
        "card_id": carrier["card_id"],
        "qword_row_id": carrier["qword_row_id"],
    }


def select_representative_carrier(packet: dict[str, Any], entry_id: str | None = None) -> dict[str, Any]:
    loc = packet["canonical_location"]
    carriers = [
        row for row in packet.get("candidate_carriers", [])
        if (entry_id is None or row.get("entry_id") == entry_id)
        and row.get("entry_id") and row.get("card_id") and row.get("qword_row_id")
    ]
    carriers.sort(key=lambda row: row["qword_row_id"])
    if not carriers:
        target = entry_id if entry_id is not None else "any complete carrier"
        raise CertificationStop(f"{loc}: packet has no complete carrier for {target}")
    return carriers[0]


def evidence(evidence_id: str, evidence_type: str, detail: str, source_address: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "type": evidence_type,
        "detail": detail,
        "source_address": source_address,
    }


def vote_reason(vote: dict[str, Any]) -> str:
    rationale = vote.get("rationale")
    if isinstance(rationale, dict) and rationale.get("exact_reason"):
        return str(rationale["exact_reason"])
    return str(vote.get("abstention_or_blocker") or "review decision preserved in the committed vote artifact")


def base_row(*, loc: str, carrier: dict[str, Any], value: Any,
             alternatives: list[dict[str, Any]], row_evidence: list[dict[str, Any]],
             input_hashes: dict[str, str], created_from: str | None) -> dict[str, Any]:
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": _carrier_identity(loc, carrier),
        "fact_type": FACT_TYPE,
        "candidate_or_value": {
            "value": value,
            "competing_alternatives": alternatives,
            "semantic_tie": False,
        },
        "scope": "occurrence",
        "source_address": {"address": f"quran:{loc}", "source_kind": "quran_token"},
        "evidence": row_evidence,
        "provenance": {
            "actor": ACTOR,
            "method": METHOD,
            "created_at": CREATED_AT,
            "input_hashes": input_hashes,
        },
        "review_votes": [],
        "certification_state": "candidate",
        "confidence_or_calibration": None,
        "defeaters": [],
        "exceptions": [],
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": created_from,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def decision_lineage(packet: dict[str, Any], vote_a: dict[str, Any], vote_b: dict[str, Any]) -> str:
    payload = canonical({
        "packet_id": packet["packet_id"],
        "packet_sha256": packet["packet_sha256"],
        "reviewer_a": vote_a,
        "reviewer_b": vote_b,
    }).encode("utf-8")
    return "sha256:" + sha256_bytes(payload)


def packet_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    packet_id = packet["packet_id"]
    packet_sha = packet["packet_sha256"]
    return evidence(
        "packet",
        "source_quote",
        f"packet_id={packet_id}; packet_sha256={packet_sha}; gate=two_vote_required",
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-decidable.jsonl#packet_id={packet_id}",
    )


def vote_evidence(vote: dict[str, Any], label: str) -> dict[str, Any]:
    filename = "votes-a.jsonl" if label == "A" else "votes-b.jsonl"
    return evidence(
        f"vote-{label}",
        "two_vote",
        vote_reason(vote),
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/{filename}#packet_id={vote['packet_id']}",
    )


def append_certified(store: fact_ledger.FactLedgerStore, *, decision: dict[str, Any],
                     packet: dict[str, Any], vote_a: dict[str, Any], vote_b: dict[str, Any],
                     input_hashes: dict[str, str]) -> tuple[str, dict[str, Any]]:
    loc = decision["canonical_location"]
    value = decision["governing_entry_id"]
    carrier = select_representative_carrier(packet, value)
    alternatives = [
        {"value": item, "reason": "retained by both reviewers"}
        for item in decision.get("retained_alternatives", [])
    ]
    packet_ev = packet_evidence(packet)
    candidate = base_row(
        loc=loc,
        carrier=carrier,
        value=value,
        alternatives=alternatives,
        row_evidence=[packet_ev],
        input_hashes=input_hashes,
        created_from=decision_lineage(packet, vote_a, vote_b),
    )
    store.append(candidate)
    store.transition(candidate["fact_id"], "review_required")
    votes = [
        {"voter_id": VOTER_IDS["A"], "vote": "approve", "evidence_ref": "vote-A", "independent": True},
        {"voter_id": VOTER_IDS["B"], "vote": "approve", "evidence_ref": "vote-B", "independent": True},
    ]
    store.transition(
        candidate["fact_id"],
        "certified",
        review_votes=votes,
        evidence=[packet_ev, vote_evidence(vote_a, "A"), vote_evidence(vote_b, "B")],
    )
    return candidate["fact_id"], carrier


def append_abstention(store: fact_ledger.FactLedgerStore, *, abstention: dict[str, Any],
                      packet: dict[str, Any], vote_a: dict[str, Any], vote_b: dict[str, Any],
                      input_hashes: dict[str, str]) -> tuple[str, dict[str, Any]]:
    loc = abstention["canonical_location"]
    carrier = select_representative_carrier(packet)
    competing = [
        {"value": entry_id, "reason": "bound entry does not address the target surface"}
        for entry_id in sorted({row["entry_id"] for row in packet["candidate_carriers"] if row.get("entry_id")})
    ]
    row_evidence = [
        evidence(
            "abstain-A", "two_vote", str(vote_a["abstention_or_blocker"]),
            f"qamus/indexes/largelexicon/append-queue/class2/two-vote/votes-a.jsonl#packet_id={packet['packet_id']}",
        ),
        evidence(
            "abstain-B", "two_vote", str(vote_b["abstention_or_blocker"]),
            f"qamus/indexes/largelexicon/append-queue/class2/two-vote/votes-b.jsonl#packet_id={packet['packet_id']}",
        ),
    ]
    candidate = base_row(
        loc=loc,
        carrier=carrier,
        value="pending",
        alternatives=competing,
        row_evidence=row_evidence,
        input_hashes=input_hashes,
        created_from=decision_lineage(packet, vote_a, vote_b),
    )
    candidate["review_votes"] = [
        {"voter_id": VOTER_IDS["A"], "vote": "abstain", "evidence_ref": "abstain-A", "independent": True},
        {"voter_id": VOTER_IDS["B"], "vote": "abstain", "evidence_ref": "abstain-B", "independent": True},
    ]
    store.append(candidate)
    return candidate["fact_id"], carrier


def validate_inputs(source_dir: Path) -> dict[str, Any]:
    source_paths = {name: source_dir / name for name in INPUT_NAMES}
    for name, path in source_paths.items():
        if not path.is_file():
            raise CertificationStop(f"missing input: {path}")
        actual = sha256_path(path)
        allowed = {EXPECTED_SHA256[name], CANONICAL_SHA256[name]}
        if actual not in allowed:
            raise CertificationStop(f"SHA-256 mismatch for {path}: {actual} not in {sorted(allowed)}")
        canonical_sha = sha256_bytes(canonical_input_bytes(name, path))
        if canonical_sha != CANONICAL_SHA256[name]:
            raise CertificationStop(
                f"canonical SHA-256 mismatch for {path}: {canonical_sha} != {CANONICAL_SHA256[name]}"
            )
    verify_sha(PACKETS_PATH, EXPECTED_SHA256[PACKETS_PATH.name])
    verify_sha(PACKET_MANIFEST_PATH, EXPECTED_SHA256[PACKET_MANIFEST_PATH.name])

    analysis = json.loads(source_paths["c2-decidable-analysis.json"].read_text(encoding="utf-8"))
    packets = load_jsonl(PACKETS_PATH)
    votes_a = load_jsonl(source_paths["votes-a.jsonl"])
    votes_b = load_jsonl(source_paths["votes-b.jsonl"])
    if not analysis.get("validation", {}).get("valid"):
        raise CertificationStop("assembler analysis is not valid")
    summary = analysis.get("summary", {})
    required_summary = {
        "total_rows": 493,
        "certified_candidates": 491,
        "joint_abstentions": 2,
        "disagreements": 0,
        "incompatible_reasoning": 0,
        "data_findings": 0,
        "both_decided_agreement_percent": 100.0,
    }
    for key, expected in required_summary.items():
        if summary.get(key) != expected:
            raise CertificationStop(f"analysis summary {key}={summary.get(key)!r}, expected {expected!r}")
    if not (len(packets) == len(votes_a) == len(votes_b) == EXPECTED_COUNTS["total_rows"]):
        raise CertificationStop("packet/vote row counts do not reconcile to 493")
    return {
        "analysis": analysis,
        "packets": index_unique(packets, "packet_id", "packets"),
        "votes_a": index_unique(votes_a, "packet_id", "votes-a"),
        "votes_b": index_unique(votes_b, "packet_id", "votes-b"),
        "source_paths": source_paths,
    }


def verify_decision(decision: dict[str, Any], packet: dict[str, Any],
                    vote_a: dict[str, Any], vote_b: dict[str, Any], *, abstention: bool) -> None:
    loc = decision["canonical_location"]
    if packet.get("canonical_location") != loc:
        raise CertificationStop(f"{loc}: packet location mismatch")
    if packet.get("packet_sha256") != vote_a.get("packet_sha256") or packet.get("packet_sha256") != vote_b.get("packet_sha256"):
        raise CertificationStop(f"{loc}: packet SHA does not agree across packet and votes")
    if vote_a.get("canonical_location") != loc or vote_b.get("canonical_location") != loc:
        raise CertificationStop(f"{loc}: vote location mismatch")
    if vote_a.get("gate") != "two_vote_required" or vote_b.get("gate") != "two_vote_required":
        raise CertificationStop(f"{loc}: vote gate is not two_vote_required")
    if abstention:
        if vote_a.get("decision") != "abstention" or vote_b.get("decision") != "abstention":
            raise CertificationStop(f"{loc}: joint abstention does not preserve two abstain decisions")
        if vote_a.get("governing_entry_id") is not None or vote_b.get("governing_entry_id") is not None:
            raise CertificationStop(f"{loc}: abstention unexpectedly supplies a governing entry")
    else:
        value = decision["governing_entry_id"]
        if vote_a.get("decision") != "governing_entry" or vote_b.get("decision") != "governing_entry":
            raise CertificationStop(f"{loc}: certified row lacks two governing_entry decisions")
        if vote_a.get("governing_entry_id") != value or vote_b.get("governing_entry_id") != value:
            raise CertificationStop(f"{loc}: reviewer governing entries diverge")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def input_descriptor(path: Path, *, sha: str | None = None) -> dict[str, Any]:
    return {"path": relative(path), "sha256": sha or sha256_path(path)}


def build_report(*, analysis: dict[str, Any], row_reports: list[dict[str, Any]],
                 current_rows: list[dict[str, Any]], source_paths: dict[str, Path]) -> dict[str, Any]:
    states = Counter(row["certification_state"] for row in current_rows)
    certified_strata = Counter(row["pilot_stratum"] for row in row_reports if row["ledger_state"] == "certified")
    abstentions = [row for row in row_reports if row["ledger_state"] == "candidate"]
    schema_sha = sha256_path(fact_ledger.SCHEMA_PATH)
    packet_manifest = json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))
    inputs = {
        "packets": input_descriptor(PACKETS_PATH, sha=EXPECTED_SHA256[PACKETS_PATH.name]),
        "packet_manifest": input_descriptor(PACKET_MANIFEST_PATH, sha=EXPECTED_SHA256[PACKET_MANIFEST_PATH.name]),
        "votes_a": {
            **input_descriptor(source_paths["votes-a.jsonl"], sha=CANONICAL_SHA256["votes-a.jsonl"]),
            "source_sha256": EXPECTED_SHA256["votes-a.jsonl"],
        },
        "votes_b": {
            **input_descriptor(source_paths["votes-b.jsonl"], sha=CANONICAL_SHA256["votes-b.jsonl"]),
            "source_sha256": EXPECTED_SHA256["votes-b.jsonl"],
        },
        "assembler_analysis": input_descriptor(source_paths["c2-decidable-analysis.json"], sha=EXPECTED_SHA256["c2-decidable-analysis.json"]),
        "entries": packet_manifest["inputs"]["entries"],
        "grammar_gate_ssot": packet_manifest["inputs"]["grammar_gate_ssot"],
        "fact_ledger_schema_current": input_descriptor(fact_ledger.SCHEMA_PATH, sha=schema_sha),
    }
    return {
        "schema": "qamus/t11-class2-decidable-certification@1",
        "state": "finalized",
        "scope": "analysis_only_no_promotion",
        "certified_at": CREATED_AT,
        "generated_by": ACTOR,
        "candidate_only": True,
        "no_live_payload": True,
        "fact_type": FACT_TYPE,
        "ledger_store": "qamus/indexes/largelexicon/fact-ledger/c2-decidable/ledger.jsonl",
        "inputs": inputs,
        "counts": {
            "packets_reviewed": EXPECTED_COUNTS["total_rows"],
            "certified": states.get("certified", 0),
            "candidate": states.get("candidate", 0),
            "review_required": states.get("review_required", 0),
            "materialized": states.get("materialized", 0),
            "conflicted": states.get("conflicted", 0),
            "joint_abstentions": len(abstentions),
            "certified_by_stratum": dict(sorted(certified_strata.items())),
        },
        "registry_delta": {
            "id": FACT_TYPE,
            "gate_trigger": GATE_TRIGGER,
            "previous_packet_schema_sha256": packet_manifest["inputs"]["fact_ledger_schema"]["sha256"],
            "current_schema_sha256": schema_sha,
            "packets_rebuilt_or_repinned": False,
            "reason": "additive fail-closed two-vote gate registration; packet content remains valid",
        },
        "determinism": {
            "fixed_created_at": CREATED_AT,
            "wall_clock_fields": False,
            "representative_carrier_rule": "lexicographically_first_complete_qword_row_id_within_governing_entry",
            "double_build_required": True,
        },
        "joint_abstentions": [
            {
                "canonical_location": row["canonical_location"],
                "packet_id": row["packet_id"],
                "ledger_fact_id": row["ledger_fact_id"],
                "ledger_state": "candidate",
                "value": "pending",
                "reviewer_a_blocker": row["reviewer_a_blocker"],
                "reviewer_b_blocker": row["reviewer_b_blocker"],
                "route": "class2_rebind_authoring_lane",
                "rebind_queue_mutated": False,
                "promoted": False,
            }
            for row in abstentions
        ],
        "shadow_surface_assertion": {
            "expected": "byte_stable",
            "reason": "certified facts are not materialized and carry no materialization targets",
            "untouched": [
                "qamus/indexes/largelexicon/qword-crosswalk/",
                "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json",
                "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.jsonl",
                "WBW and hover-whitelist compiler inputs",
            ],
        },
        "assembler_summary": analysis["summary"],
        "rows": row_reports,
    }


def build_bundle(source_dir: Path, bundle_root: Path) -> dict[str, Any]:
    data = validate_inputs(source_dir)
    analysis = data["analysis"]
    packets = data["packets"]
    votes_a = data["votes_a"]
    votes_b = data["votes_b"]
    source_paths = data["source_paths"]

    ledger_dir = bundle_root / "ledger"
    artifact_dir = bundle_root / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    store = fact_ledger.FactLedgerStore(ledger_dir)
    base_hashes = {
        "packets": "sha256:" + EXPECTED_SHA256[PACKETS_PATH.name],
        "votes_a": "sha256:" + CANONICAL_SHA256["votes-a.jsonl"],
        "votes_a_source": "sha256:" + EXPECTED_SHA256["votes-a.jsonl"],
        "votes_b": "sha256:" + CANONICAL_SHA256["votes-b.jsonl"],
        "votes_b_source": "sha256:" + EXPECTED_SHA256["votes-b.jsonl"],
        "assembler_analysis": "sha256:" + EXPECTED_SHA256["c2-decidable-analysis.json"],
        "entries": "sha256:" + json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))["inputs"]["entries"]["sha256"],
        "grammar_gate_ssot": "sha256:" + sha256_path(fact_ledger.GATE_PATH),
        "fact_ledger_schema": "sha256:" + sha256_path(fact_ledger.SCHEMA_PATH),
    }

    decisions: list[tuple[str, bool, dict[str, Any]]] = []
    decisions.extend((row["packet_id"], False, row) for row in analysis["certified_candidates"])
    decisions.extend((row["packet_id"], True, row) for row in analysis["joint_abstentions"])
    decisions.sort(key=lambda item: item[0])
    if len(decisions) != EXPECTED_COUNTS["total_rows"]:
        raise CertificationStop("analysis decisions do not reconcile to 493")

    row_reports: list[dict[str, Any]] = []
    seen_locs: set[str] = set()
    for packet_id, is_abstention, decision in decisions:
        packet = packets.get(packet_id)
        vote_a = votes_a.get(packet_id)
        vote_b = votes_b.get(packet_id)
        if packet is None or vote_a is None or vote_b is None:
            raise CertificationStop(f"{packet_id}: missing packet or vote")
        verify_decision(decision, packet, vote_a, vote_b, abstention=is_abstention)
        loc = decision["canonical_location"]
        if loc in seen_locs:
            raise CertificationStop(f"duplicate canonical location {loc}")
        seen_locs.add(loc)
        row_hashes = dict(base_hashes)
        row_hashes["packet_row"] = "sha256:" + packet["packet_sha256"]
        if is_abstention:
            fact_id, carrier = append_abstention(
                store, abstention=decision, packet=packet, vote_a=vote_a, vote_b=vote_b,
                input_hashes=row_hashes,
            )
            row_reports.append({
                "canonical_location": loc,
                "packet_id": packet_id,
                "pilot_stratum": packet["pilot_stratum"],
                "ledger_fact_id": fact_id,
                "ledger_state": "candidate",
                "value": "pending",
                "selected_carrier": _carrier_identity(loc, carrier),
                "reviewer_a_blocker": vote_a["abstention_or_blocker"],
                "reviewer_b_blocker": vote_b["abstention_or_blocker"],
            })
        else:
            fact_id, carrier = append_certified(
                store, decision=decision, packet=packet, vote_a=vote_a, vote_b=vote_b,
                input_hashes=row_hashes,
            )
            row_reports.append({
                "canonical_location": loc,
                "packet_id": packet_id,
                "pilot_stratum": decision["pilot_stratum"],
                "ledger_fact_id": fact_id,
                "ledger_state": "certified",
                "value": decision["governing_entry_id"],
                "selected_carrier": _carrier_identity(loc, carrier),
            })

    errors = store.validate_all()
    if errors:
        raise CertificationStop("generated ledger validation failed: " + "; ".join(errors[:5]))
    current_rows = store.query(current_only=True)
    states = Counter(row["certification_state"] for row in current_rows)
    if states != Counter({"certified": 491, "candidate": 2}):
        raise CertificationStop(f"generated current-state counts are wrong: {dict(states)}")
    abstention_locs = {
        row["subject_identity"]["loc"] for row in current_rows
        if row["certification_state"] == "candidate"
    }
    if abstention_locs != ABSTENTION_LOCS:
        raise CertificationStop(f"abstention locations are wrong: {sorted(abstention_locs)}")

    for name, source_path in source_paths.items():
        (artifact_dir / name).write_bytes(canonical_input_bytes(name, source_path))
    report = build_report(
        analysis=analysis,
        row_reports=row_reports,
        current_rows=current_rows,
        source_paths={name: QUEUE_DIR / name for name in INPUT_NAMES},
    )
    report_bytes = pretty(report)
    (artifact_dir / REPORT_PATH.name).write_bytes(report_bytes)
    ledger_bytes = (ledger_dir / fact_ledger.LEDGER_NAME).read_bytes()
    manifest = {
        "schema": "qamus.t11_class2_decidable_certification_manifest.v1",
        "scope": "certification_only_no_materialization_no_live_payload",
        "generated_by": ACTOR,
        "created_at": CREATED_AT,
        "candidate_only": True,
        "no_live_payload": True,
        "determinism": {
            "double_build_required": True,
            "wall_clock_fields": False,
            "canonical_jsonl": True,
            "representative_carrier_rule": "lexicographically_first_complete_qword_row_id_within_governing_entry",
        },
        "input_sha_pins": {
            "packets": EXPECTED_SHA256[PACKETS_PATH.name],
            "packet_manifest": EXPECTED_SHA256[PACKET_MANIFEST_PATH.name],
            "votes_a": EXPECTED_SHA256["votes-a.jsonl"],
            "votes_a_canonical": CANONICAL_SHA256["votes-a.jsonl"],
            "votes_b": EXPECTED_SHA256["votes-b.jsonl"],
            "votes_b_canonical": CANONICAL_SHA256["votes-b.jsonl"],
            "assembler_analysis": EXPECTED_SHA256["c2-decidable-analysis.json"],
            "entries": json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))["inputs"]["entries"]["sha256"],
            "grammar_gate_ssot": sha256_path(fact_ledger.GATE_PATH),
            "fact_ledger_schema_current": sha256_path(fact_ledger.SCHEMA_PATH),
        },
        "outputs": {
            "ledger": {
                "path": "qamus/indexes/largelexicon/fact-ledger/c2-decidable/ledger.jsonl",
                "sha256": sha256_bytes(ledger_bytes),
                "revision_rows": len(store.query(current_only=False)),
                "current_facts": len(current_rows),
            },
            "report": {
                "path": relative(REPORT_PATH),
                "sha256": sha256_bytes(report_bytes),
            },
            "votes_a": {"path": relative(QUEUE_DIR / "votes-a.jsonl"), "sha256": CANONICAL_SHA256["votes-a.jsonl"]},
            "votes_b": {"path": relative(QUEUE_DIR / "votes-b.jsonl"), "sha256": CANONICAL_SHA256["votes-b.jsonl"]},
            "assembler_analysis": {
                "path": relative(QUEUE_DIR / "c2-decidable-analysis.json"),
                "sha256": EXPECTED_SHA256["c2-decidable-analysis.json"],
            },
        },
        "counts": report["counts"],
        "shadow_surface_assertion": report["shadow_surface_assertion"],
    }
    (artifact_dir / MANIFEST_PATH.name).write_bytes(pretty(manifest))
    return {
        "ledger": ledger_dir / fact_ledger.LEDGER_NAME,
        "report": artifact_dir / REPORT_PATH.name,
        "manifest": artifact_dir / MANIFEST_PATH.name,
        **{name: artifact_dir / name for name in INPUT_NAMES},
    }


def compare_bundles(first: dict[str, Path], second: dict[str, Path]) -> None:
    if set(first) != set(second):
        raise CertificationStop("determinism bundles have different file sets")
    for name in sorted(first):
        if first[name].read_bytes() != second[name].read_bytes():
            raise CertificationStop(f"determinism failure: {name} differs between builds")


def deterministic_build(source_dir: Path, work_root: Path) -> dict[str, Path]:
    first = build_bundle(source_dir, work_root / "first")
    second = build_bundle(source_dir, work_root / "second")
    compare_bundles(first, second)
    return first


def atomic_install(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(source.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def install_bundle(bundle: dict[str, Path]) -> None:
    destinations = {
        "ledger": LEDGER_DIR / fact_ledger.LEDGER_NAME,
        "report": REPORT_PATH,
        "manifest": MANIFEST_PATH,
        **{name: QUEUE_DIR / name for name in INPUT_NAMES},
    }
    for name, destination in destinations.items():
        atomic_install(bundle[name], destination)
    index_path = LEDGER_DIR / fact_ledger.INDEX_NAME
    if index_path.exists():
        index_path.unlink()


def synthetic_row() -> dict[str, Any]:
    carrier = {"entry_id": "0123456789ab", "card_id": "0123456789ab:u1:e1", "qword_row_id": "qword-1"}
    row = base_row(
        loc="1:1:1", carrier=carrier, value="0123456789ab", alternatives=[],
        row_evidence=[evidence("vote-A", "two_vote", "synthetic vote", "review:A")],
        input_hashes={"fixture": "sha256:" + "1" * 64}, created_from=None,
    )
    return row


def _self_test(source_dir: Path | None = None) -> int:
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        print(("ok   " if condition else "FAIL ") + name)
        if not condition:
            failures.append(name)

    schema = fact_ledger.load_schema()
    registry = {row["id"]: row for row in schema["x-fact-type-registry"]["types"]}
    check("gated governing_entry_analysis registry entry is loaded",
          registry.get(FACT_TYPE, {}).get("gate_trigger") == GATE_TRIGGER)
    check("governing_entry_analysis is a fail-closed two-vote fact type",
          FACT_TYPE in fact_ledger._two_vote_fact_types(schema, fact_ledger.GATE_PATH))

    with tempfile.TemporaryDirectory() as temp:
        store = fact_ledger.FactLedgerStore(Path(temp) / "gate")
        row = store.append(synthetic_row())
        store.transition(row["fact_id"], "review_required")
        rejected = False
        try:
            store.transition(
                row["fact_id"], "certified",
                review_votes=[{
                    "voter_id": VOTER_IDS["A"], "vote": "approve",
                    "evidence_ref": "vote-A", "independent": True,
                }],
            )
        except fact_ledger.ValidationError as exc:
            rejected = "independent approving votes" in str(exc)
        check("ledger gate refuses fewer than two independent approvals", rejected)

        incomplete = synthetic_row()
        incomplete["subject_identity"].pop("card_id")
        incomplete["fact_id"] = fact_ledger.compute_fact_id(incomplete)
        rejected = False
        try:
            fact_ledger.validate_row(incomplete)
        except fact_ledger.ValidationError as exc:
            rejected = "full D-13 carrier" in str(exc)
        check("ledger refuses an incomplete D-13 carrier", rejected)

        try:
            resolved = resolve_source_dir(source_dir)
            bundle = deterministic_build(resolved, Path(temp) / "double")
            ledger_dir = Path(temp) / "inspect"
            ledger_dir.mkdir()
            shutil.copyfile(bundle["ledger"], ledger_dir / fact_ledger.LEDGER_NAME)
            generated = fact_ledger.FactLedgerStore(ledger_dir)
            rows = generated.query(current_only=True)
            states = Counter(row["certification_state"] for row in rows)
            held = [row for row in rows if row["certification_state"] == "candidate"]
            check("double build is byte-identical", True)
            check("generated ledger has 491 certified and 2 candidate facts",
                  states == Counter({"certified": 491, "candidate": 2}))
            check("joint abstentions remain pending candidates with two abstain votes",
                  {row["subject_identity"]["loc"] for row in held} == ABSTENTION_LOCS
                  and all(row["candidate_or_value"]["value"] == "pending" for row in held)
                  and all({vote["vote"] for vote in row["review_votes"]} == {"abstain"} for row in held))
            check("no generated fact is materialized",
                  all(row["certification_state"] != "materialized" and row["materialization_targets"] == [] for row in rows))
        except (CertificationStop, fact_ledger.ValidationError, OSError, ValueError) as exc:
            print("SELF-TEST BUILD ERROR:", exc)
            failures.append("deterministic real-input build")

    if failures:
        print("certify_class2_decidable_wave self-test FAIL:", ", ".join(failures))
        return 1
    print("certify_class2_decidable_wave self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="directory containing votes-a, votes-b, and analysis")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check", action="store_true", help="build twice and validate without installing")
    parser.add_argument("--write", action="store_true", help="build twice, validate, and install canonical artifacts")
    args = parser.parse_args(argv)
    if sum(bool(value) for value in (args.self_test, args.check, args.write)) != 1:
        parser.error("choose exactly one of --self-test, --check, or --write")
    try:
        source_dir = resolve_source_dir(args.source_dir)
        if args.self_test:
            return _self_test(source_dir)
        with tempfile.TemporaryDirectory(prefix="c2-decidable-cert-") as temp:
            bundle = deterministic_build(source_dir, Path(temp))
            if args.write:
                install_bundle(bundle)
        print("certify_class2_decidable_wave %s OK" % ("write" if args.write else "check"))
        return 0
    except (CertificationStop, fact_ledger.ValidationError, OSError, ValueError) as exc:
        print("certify_class2_decidable_wave FAIL:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
