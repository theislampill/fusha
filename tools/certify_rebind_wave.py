#!/usr/bin/env python3
"""Certify the T11 rebind wave without materializing or mutating compiler inputs.

The writer follows the class-2 H-write precedent: it builds an isolated
FactLedgerStore twice, validates it, compares every emitted byte, and installs
only ``ledger.jsonl`` plus reviewer-facing certification artifacts.  The
store's disposable ``index.json`` is never committed.
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
ACTOR = "tools/certify_rebind_wave.py"
METHOD = "T11 rebind engine-diverse two-vote certification"
CREATED_AT = "2026-07-11T00:00:00Z"

QUEUE_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "class2" / "two-vote"
PACKETS_PATH = QUEUE_DIR / "packets-rebind.jsonl"
PACKET_MANIFEST_PATH = QUEUE_DIR / "packets-rebind.manifest.json"
APPEND_QUEUE_PATH = ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "append-queue.jsonl"
LEDGER_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "fact-ledger" / "rebind-cert"
REPORT_PATH = QUEUE_DIR / "rebind-certification.report.json"
MANIFEST_PATH = QUEUE_DIR / "rebind-certification.manifest.json"

SOURCE_TO_OUTPUT = {
    "votes-a.jsonl": "rebind-votes-a.jsonl",
    "votes-b.jsonl": "rebind-votes-b.jsonl",
    "rebind-analysis.json": "rebind-analysis.json",
    "rb-cert-audit.jsonl": "rebind-cert-audit.jsonl",
}
SOURCE_SHA256 = {
    "votes-a.jsonl": "aac09116a823a501b73705047b7d875ed7ab3adb46c42c7dc38cd93f20d23a15",
    "votes-b.jsonl": "5ae0c7d86eb1bd435050cc318531ac528e497dd0996a439a3a96a58fb5b452e9",
    "rebind-analysis.json": "89e96bdc143058f38cf89084e0495194d60c8e8f902fe755bb07cc25fe486e65",
    "rb-cert-audit.jsonl": "3eb2ecdd00778c9373a73ca99bfd83a253f171d62ca48a0919aa7c2ed5151a3e",
}
CANONICAL_SHA256 = {
    "votes-a.jsonl": "aa3eb85ae32c462fa96afe348c446bbf8e38a01043716efe5dc24c4ad55f9ea8",
    "votes-b.jsonl": "5ae0c7d86eb1bd435050cc318531ac528e497dd0996a439a3a96a58fb5b452e9",
    "rb-cert-audit.jsonl": "7be859e1c7d2948b1e51b25049a8bc1538d498ab6b205fa1ab0533fd86f6cd44",
}
PUBLIC_ANALYSIS_SHA256 = "b42c190c8f440ded549fcec8303ce5f025165f86ca2fe9d71a7cd263116f3ab9"
REPO_INPUT_SHA256 = {
    "packets-rebind.jsonl": "55819cedd30fa2db19df2647fd4c6438bfe7e47f7d71044d9f2e0a8d4974b3a4",
    "packets-rebind.manifest.json": "95a0377b1e10cb49c6b63a7d6846264d5e899aa869ca66d4405c61d9dc64e1f2",
    "append-queue.jsonl": "d726cfeb033796f25f5ffa31d9f3df876d75638b080d43f9b155b47bac62a364",
}
EXPECTED = {
    "packets": 1_248,
    "certified": 1_173,
    "rebind_same_host": 1_167,
    "authoring_both": 6,
    "disagreements": 75,
    "different_host": 66,
    "rebind_vs_authoring": 8,
    "abstention_vs_decision": 1,
    "history_rows": 3_669,
}
VOTER_IDS = {"A": "reviewer-A:Opus", "B": "reviewer-B:Codex"}


class CertificationStop(RuntimeError):
    """Fail-closed input, reconciliation, or output error."""


class BufferedFactLedgerStore(fact_ledger.FactLedgerStore):
    """FactLedgerStore semantics with one durable write for a disposable build."""

    def __init__(self, directory: Path):
        super().__init__(directory)
        self._buffered_rows: list[dict[str, Any]] = []
        self._buffered_current: dict[str, dict[str, Any]] = {}
        self._flushing = False

    def _rows(self) -> list[dict[str, Any]]:
        return list(self._buffered_rows)

    def _current(self, rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return self._buffered_current

    def _append_line(self, row: dict[str, Any]) -> None:
        stored = copy.deepcopy(row)
        self._buffered_rows.append(stored)
        self._buffered_current[stored["fact_id"]] = stored

    def rebuild_index(self) -> dict[str, Any]:
        if self._flushing:
            return super().rebuild_index()
        return {"schema": "qamus.fact_ledger_index.v1", "facts": {}, "current": {}}

    def flush(self) -> None:
        payload = "".join(canonical(row) + "\n" for row in self._buffered_rows)
        with self.ledger_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        self._flushing = True
        try:
            self.rebuild_index()
        finally:
            self._flushing = False


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


def canonical_jsonl_bytes(path: Path) -> bytes:
    return ("\n".join(path.read_text(encoding="utf-8").splitlines()) + "\n").encode("utf-8")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _require_sha(path: Path, expected: str) -> None:
    actual = sha256_path(path)
    if actual != expected:
        raise CertificationStop(f"SHA-256 mismatch for {path}: {actual} != {expected}")


def resolve_source_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    lane_inputs = ROOT / ".lane-inputs"
    if all((lane_inputs / name).is_file() for name in SOURCE_TO_OUTPUT):
        return lane_inputs
    if all((QUEUE_DIR / name).is_file() for name in SOURCE_TO_OUTPUT.values()):
        return QUEUE_DIR
    raise CertificationStop("rebind certification inputs are absent from .lane-inputs and the canonical queue")


def resolve_source_paths(source_dir: Path) -> dict[str, Path]:
    source_dir = source_dir.resolve()
    canonical_paths = {
        source: source_dir / output for source, output in SOURCE_TO_OUTPUT.items()
    }
    if all(path.is_file() for path in canonical_paths.values()):
        return canonical_paths
    source_paths = {name: source_dir / name for name in SOURCE_TO_OUTPUT}
    if all(path.is_file() for path in source_paths.values()):
        return source_paths
    raise CertificationStop(f"incomplete rebind certification input set in {source_dir}")


def _public_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Remove local checkout paths while preserving the assembler result."""
    public = copy.deepcopy(analysis)
    inputs = public["inputs"]
    inputs["packets_file"] = "packets-rebind.jsonl"
    inputs["reviewer_a_files"] = ["rebind-votes-a.jsonl"]
    inputs["reviewer_a_source_tranches"] = 3
    inputs["reviewer_b_file"] = "rebind-votes-b.jsonl"
    return public


def validate_inputs(source_dir: Path) -> dict[str, Any]:
    source_paths = resolve_source_paths(source_dir)
    for name, path in source_paths.items():
        actual = sha256_path(path)
        allowed = {SOURCE_SHA256[name]}
        if name.endswith(".jsonl"):
            allowed.add(CANONICAL_SHA256[name])
        elif name == "rebind-analysis.json":
            allowed.add(PUBLIC_ANALYSIS_SHA256)
        if actual not in allowed:
            raise CertificationStop(f"SHA-256 mismatch for {path}: {actual} not in {sorted(allowed)}")
        if name.endswith(".jsonl"):
            actual = sha256_bytes(canonical_jsonl_bytes(path))
            if actual != CANONICAL_SHA256[name]:
                raise CertificationStop(f"canonical SHA-256 mismatch for {path}: {actual}")
    for path in (PACKETS_PATH, PACKET_MANIFEST_PATH, APPEND_QUEUE_PATH):
        _require_sha(path, REPO_INPUT_SHA256[path.name])

    analysis = json.loads(source_paths["rebind-analysis.json"].read_text(encoding="utf-8"))
    packets = index_unique(load_jsonl(PACKETS_PATH), "packet_id", "packets")
    votes_a = index_unique(load_jsonl(source_paths["votes-a.jsonl"]), "packet_id", "votes-a")
    votes_b = index_unique(load_jsonl(source_paths["votes-b.jsonl"]), "packet_id", "votes-b")
    audit = index_unique(load_jsonl(source_paths["rb-cert-audit.jsonl"]), "packet_id", "audit")
    append_queue = index_unique(load_jsonl(APPEND_QUEUE_PATH), "canonical_location", "append-queue")

    validation = analysis.get("validation", {})
    if validation.get("hard_findings") != [] or not all(
        validation.get(key) is True for key in (
            "a_rows_ok", "b_rows_ok", "packet_rows_ok", "packet_id_sets_identical",
            "packet_sha256_echo_ok", "evidence_hashes_echo_ok", "canonical_location_echo_ok",
        )
    ):
        raise CertificationStop("assembler validation is not clean")
    agreement = analysis.get("agreement", {})
    required_agreement = {
        "total_packets": 1_248,
        "agree_total": 1_173,
        "rebind_same_host": 1_167,
        "authoring_both": 6,
        "abstention_both": 0,
        "disagree_total": 75,
    }
    if any(agreement.get(key) != value for key, value in required_agreement.items()):
        raise CertificationStop(f"assembler agreement counts differ: {agreement}")
    if not analysis.get("rerun_proof", {}).get("double_build_byte_identical"):
        raise CertificationStop("assembler rerun proof is not byte-identical")

    certified_ids = analysis.get("certified_candidates", {}).get("packet_ids", [])
    disagreements = analysis.get("disagreements", {}).get("detail", [])
    if len(certified_ids) != EXPECTED["certified"] or len(set(certified_ids)) != len(certified_ids):
        raise CertificationStop("certified packet ids do not reconcile to 1,173 unique rows")
    disagreement_index = index_unique(disagreements, "packet_id", "disagreements")
    classes = Counter(row.get("class") for row in disagreements)
    if classes != Counter({"different_host": 66, "rebind_vs_authoring": 8, "abstention_vs_decision": 1}):
        raise CertificationStop(f"disagreement classes differ: {dict(classes)}")
    packet_ids = set(packets)
    if not (packet_ids == set(votes_a) == set(votes_b)):
        raise CertificationStop("packet and vote packet-id sets differ")
    if set(certified_ids) | set(disagreement_index) != packet_ids or set(certified_ids) & set(disagreement_index):
        raise CertificationStop("certified and disagreement partitions do not cover exactly 1,248 packets")
    if set(audit) != set(certified_ids):
        raise CertificationStop("audit rows do not cover exactly the 1,173 agreed packets")
    if Counter(row.get("verdict") for row in audit.values()) != Counter({
        "ownership_supported": 1_153,
        "ownership_suspect": 7,
        "underivable": 7,
        "not_applicable": 6,
    }):
        raise CertificationStop("audit verdict counts differ from the post-ANDON ownership gate")

    certified_set = set(certified_ids)
    kind_counts: Counter[str] = Counter()
    for packet_id, packet in packets.items():
        vote_a = votes_a[packet_id]
        vote_b = votes_b[packet_id]
        loc = packet["canonical_location"]
        if vote_a.get("canonical_location") != loc or vote_b.get("canonical_location") != loc:
            raise CertificationStop(f"{packet_id}: vote location mismatch")
        if packet.get("packet_sha256") != vote_a.get("packet_sha256") or packet.get("packet_sha256") != vote_b.get("packet_sha256"):
            raise CertificationStop(f"{packet_id}: packet SHA echo mismatch")
        if vote_a.get("evidence_hashes") != packet.get("evidence_hashes") or vote_b.get("evidence_hashes") != packet.get("evidence_hashes"):
            raise CertificationStop(f"{packet_id}: evidence hashes differ")
        carriers = append_queue.get(loc, {}).get("bound_carriers", [])
        if not any(all(row.get(key) for key in ("entry_id", "card_id", "qword_row_id")) for row in carriers):
            raise CertificationStop(f"{packet_id}: no complete D-13 carrier")
        if packet_id in certified_set:
            if vote_a["decision"] != vote_b["decision"]:
                raise CertificationStop(f"{packet_id}: certified decision kinds differ")
            if vote_a["decision"] == "rebind_to_host":
                if not vote_a.get("host_entry_id") or vote_a.get("host_entry_id") != vote_b.get("host_entry_id"):
                    raise CertificationStop(f"{packet_id}: agreed host differs")
                kind_counts["rebind_same_host"] += 1
            elif vote_a["decision"] == "requires_authoring":
                kind_counts["authoring_both"] += 1
            else:
                raise CertificationStop(f"{packet_id}: unsupported agreed decision {vote_a['decision']}")
    if kind_counts != Counter({"rebind_same_host": 1_167, "authoring_both": 6}):
        raise CertificationStop(f"agreed decision kinds differ: {dict(kind_counts)}")

    return {
        "analysis": analysis,
        "packets": packets,
        "votes_a": votes_a,
        "votes_b": votes_b,
        "audit": audit,
        "append_queue": append_queue,
        "certified_packet_ids": certified_ids,
        "disagreements": disagreement_index,
        "source_paths": source_paths,
    }


def _carrier_identity(loc: str, carrier: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": carrier["entry_id"],
        "card_id": carrier["card_id"],
        "qword_row_id": carrier["qword_row_id"],
    }


def select_representative_carrier(loc: str, append_row: dict[str, Any]) -> dict[str, Any]:
    carriers = [
        row for row in append_row.get("bound_carriers", [])
        if all(row.get(key) for key in ("entry_id", "card_id", "qword_row_id"))
    ]
    carriers.sort(key=lambda row: row["qword_row_id"])
    if not carriers:
        raise CertificationStop(f"{loc}: no complete bound carrier")
    return carriers[0]


def evidence(evidence_id: str, evidence_type: str, detail: str, source_address: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "type": evidence_type,
        "detail": detail,
        "source_address": source_address,
    }


def vote_value(vote: dict[str, Any]) -> str:
    decision = vote["decision"]
    if decision == "rebind_to_host":
        return str(vote["host_entry_id"])
    if decision == "requires_authoring":
        return "requires_authoring"
    if decision == "retain_current_binding":
        return "retain_current_binding"
    if decision == "abstention":
        return "pending"
    raise CertificationStop(f"unknown vote decision: {decision}")


def vote_reason(vote: dict[str, Any]) -> str:
    reasons = [
        str(item["exact_reason"])
        for key in ("sarf_evidence", "nahw_evidence")
        for item in vote.get(key, [])
        if item.get("exact_reason")
    ]
    if vote.get("requires_authoring_note"):
        reasons.append(str(vote["requires_authoring_note"]))
    retain = vote.get("retain_rationale") or {}
    if retain.get("exact_reason"):
        reasons.append(str(retain["exact_reason"]))
    if vote.get("abstention_or_blocker"):
        reasons.append(str(vote["abstention_or_blocker"]))
    return " | ".join(reasons) or "review decision preserved in the committed vote artifact"


def packet_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    packet_id = packet["packet_id"]
    return evidence(
        "packet", "source_quote",
        f"packet_id={packet_id}; packet_sha256={packet['packet_sha256']}; gate=two_vote_required",
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-rebind.jsonl#packet_id={packet_id}",
    )


def vote_evidence(vote: dict[str, Any], label: str) -> dict[str, Any]:
    filename = "rebind-votes-a.jsonl" if label == "A" else "rebind-votes-b.jsonl"
    return evidence(
        f"vote-{label}", "two_vote", vote_reason(vote),
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/{filename}#packet_id={vote['packet_id']}",
    )


def audit_exception(audit_row: dict[str, Any]) -> list[dict[str, Any]]:
    verdict = audit_row["verdict"]
    if verdict not in {"ownership_suspect", "underivable"}:
        return []
    disposition = (
        "benign_rootless_convention" if verdict == "ownership_suspect"
        else "documented_underivable_particle"
    )
    return [{
        "type": "rebind_cert_audit_annotation",
        "disposition": disposition,
        "audit_verdict": verdict,
        "reason": audit_row["reason"],
        "audit_row_sha256": sha256_bytes(canonical(audit_row).encode("utf-8")),
        "source_address": (
            "qamus/indexes/largelexicon/append-queue/class2/two-vote/"
            f"rebind-cert-audit.jsonl#packet_id={audit_row['packet_id']}"
        ),
    }]


def decision_lineage(packet: dict[str, Any], vote_a: dict[str, Any], vote_b: dict[str, Any],
                     audit_row: dict[str, Any] | None) -> str:
    return "sha256:" + sha256_bytes(canonical({
        "packet_id": packet["packet_id"],
        "packet_sha256": packet["packet_sha256"],
        "reviewer_a": vote_a,
        "reviewer_b": vote_b,
        "audit": audit_row,
    }).encode("utf-8"))


def base_row(*, loc: str, carrier: dict[str, Any], value: str,
             alternatives: list[dict[str, Any]], row_evidence: list[dict[str, Any]],
             exceptions: list[dict[str, Any]], input_hashes: dict[str, str],
             created_from: str) -> dict[str, Any]:
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
        "exceptions": exceptions,
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": created_from,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def reviewer_votes(vote_a: dict[str, Any], vote_b: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "voter_id": VOTER_IDS[label],
            "vote": "abstain" if vote["decision"] == "abstention" else "approve",
            "evidence_ref": f"vote-{label}",
            "independent": True,
        }
        for label, vote in (("A", vote_a), ("B", vote_b))
    ]


def append_certified(store: fact_ledger.FactLedgerStore, *, packet: dict[str, Any],
                     vote_a: dict[str, Any], vote_b: dict[str, Any], audit_row: dict[str, Any],
                     append_row: dict[str, Any], input_hashes: dict[str, str]) -> tuple[str, dict[str, Any]]:
    loc = packet["canonical_location"]
    carrier = select_representative_carrier(loc, append_row)
    value = vote_value(vote_a)
    packet_ev = packet_evidence(packet)
    candidate = base_row(
        loc=loc, carrier=carrier, value=value, alternatives=[], row_evidence=[packet_ev],
        exceptions=audit_exception(audit_row), input_hashes=input_hashes,
        created_from=decision_lineage(packet, vote_a, vote_b, audit_row),
    )
    store.append(candidate)
    store.transition(candidate["fact_id"], "review_required")
    store.transition(
        candidate["fact_id"], "certified",
        review_votes=reviewer_votes(vote_a, vote_b),
        evidence=[packet_ev, vote_evidence(vote_a, "A"), vote_evidence(vote_b, "B")],
    )
    return candidate["fact_id"], carrier


def append_disagreement(store: fact_ledger.FactLedgerStore, *, packet: dict[str, Any],
                        vote_a: dict[str, Any], vote_b: dict[str, Any], detail: dict[str, Any],
                        append_row: dict[str, Any], input_hashes: dict[str, str]) -> tuple[str, dict[str, Any]]:
    loc = packet["canonical_location"]
    carrier = select_representative_carrier(loc, append_row)
    value_a = vote_value(vote_a)
    value_b = vote_value(vote_b)
    candidate_value = value_a if vote_a["decision"] != "abstention" else value_b
    alternatives = [
        {"value": value_a, "reason": "reviewer A (Opus) conclusion"},
        {"value": value_b, "reason": "reviewer B (Codex) conclusion"},
    ]
    packet_ev = evidence(
        "packet", "source_quote",
        f"two-vote disagreement ({detail['class']}): {value_a!r} / {value_b!r}; never resolved",
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-rebind.jsonl#packet_id={packet['packet_id']}",
    )
    candidate = base_row(
        loc=loc, carrier=carrier, value=candidate_value, alternatives=alternatives,
        row_evidence=[packet_ev], exceptions=[], input_hashes=input_hashes,
        created_from=decision_lineage(packet, vote_a, vote_b, None),
    )
    store.append(candidate)
    store.transition(
        candidate["fact_id"], "review_required",
        review_votes=reviewer_votes(vote_a, vote_b),
        evidence=[packet_ev, vote_evidence(vote_a, "A"), vote_evidence(vote_b, "B")],
    )
    return candidate["fact_id"], carrier


def _input_descriptor(path: Path, sha: str | None = None) -> dict[str, Any]:
    return {"path": relative(path), "sha256": sha or sha256_path(path)}


def _shadow_assertion() -> dict[str, Any]:
    return {
        "expected": "byte_stable",
        "reason": "certified facts are not materialized and carry no materialization targets",
        "untouched": [
            "qamus/indexes/largelexicon/qword-crosswalk/",
            "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json",
            "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.v2.jsonl",
            "qamus/indexes/largelexicon/append-queue/class2/funcword-queue.v2.jsonl",
            "WBW and hover-whitelist compiler inputs",
        ],
    }


def build_report(*, data: dict[str, Any], row_reports: list[dict[str, Any]],
                 history: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    current_states = Counter(row["certification_state"] for row in current)
    history_states = Counter(row["certification_state"] for row in history)
    exception_counts = Counter(
        item["disposition"] for row in current for item in row.get("exceptions", [])
    )
    outputs = {source: QUEUE_DIR / output for source, output in SOURCE_TO_OUTPUT.items()}
    packet_manifest = json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "schema": "qamus/t11-rebind-certification@1",
        "state": "finalized",
        "scope": "certification_only_no_materialization_no_live_payload",
        "certified_at": CREATED_AT,
        "generated_by": ACTOR,
        "candidate_only": True,
        "no_live_payload": True,
        "fact_type": FACT_TYPE,
        "ledger_store": relative(LEDGER_DIR / fact_ledger.LEDGER_NAME),
        "inputs": {
            "packets": _input_descriptor(PACKETS_PATH, REPO_INPUT_SHA256[PACKETS_PATH.name]),
            "packet_manifest": _input_descriptor(PACKET_MANIFEST_PATH, REPO_INPUT_SHA256[PACKET_MANIFEST_PATH.name]),
            "append_queue_carriers": _input_descriptor(APPEND_QUEUE_PATH, REPO_INPUT_SHA256[APPEND_QUEUE_PATH.name]),
            "votes_a": {**_input_descriptor(outputs["votes-a.jsonl"], CANONICAL_SHA256["votes-a.jsonl"]),
                        "source_sha256": SOURCE_SHA256["votes-a.jsonl"]},
            "votes_b": {**_input_descriptor(outputs["votes-b.jsonl"], CANONICAL_SHA256["votes-b.jsonl"]),
                        "source_sha256": SOURCE_SHA256["votes-b.jsonl"]},
            "assembler_analysis": {"path": relative(outputs["rebind-analysis.json"]),
                                   "source_sha256": SOURCE_SHA256["rebind-analysis.json"]},
            "ownership_audit": {**_input_descriptor(outputs["rb-cert-audit.jsonl"], CANONICAL_SHA256["rb-cert-audit.jsonl"]),
                                "source_sha256": SOURCE_SHA256["rb-cert-audit.jsonl"]},
            "entries": packet_manifest["inputs"]["entries"],
            "grammar_gate_ssot": packet_manifest["inputs"]["grammar_gate_ssot"],
            "fact_ledger_schema_current": _input_descriptor(fact_ledger.SCHEMA_PATH),
        },
        "counts": {
            "packets_reviewed": 1_248,
            "current_states": dict(sorted(current_states.items())),
            "history_states": dict(sorted(history_states.items())),
            "history_rows": len(history),
            "certified_rebind_same_host": 1_167,
            "certified_requires_authoring": 6,
            "disagreements": {"different_host": 66, "rebind_vs_authoring": 8, "abstention": 1},
            "exceptions": dict(sorted(exception_counts.items())),
        },
        "row_arithmetic": "1173*3 + 75*2 = 3669",
        "registry_delta": {
            "id": FACT_TYPE,
            "gate_trigger": GATE_TRIGGER,
            "schema_changed": False,
            "reason": "reuse registered fail-closed governing-entry analysis fact type",
        },
        "determinism": {
            "fixed_created_at": CREATED_AT,
            "wall_clock_fields": False,
            "representative_carrier_rule": "lexicographically_first_complete_bound_qword_row_id",
            "double_build_required": True,
        },
        "mutation_boundaries": {
            "crosswalk_changed": False,
            "whitelist_changed": False,
            "v2_queue_changed": False,
            "materialized": False,
        },
        "shadow_surface_assertion": _shadow_assertion(),
        "assembler_agreement": data["analysis"]["agreement"],
        "assembler_rerun_proof": data["analysis"]["rerun_proof"],
        "rows": row_reports,
    }


def build_bundle(source_dir: Path, bundle_root: Path) -> dict[str, Path]:
    data = validate_inputs(source_dir)
    ledger_dir = bundle_root / "ledger"
    artifact_dir = bundle_root / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    store = BufferedFactLedgerStore(ledger_dir)
    packet_manifest = json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))
    base_hashes = {
        "packets": "sha256:" + REPO_INPUT_SHA256[PACKETS_PATH.name],
        "packet_manifest": "sha256:" + REPO_INPUT_SHA256[PACKET_MANIFEST_PATH.name],
        "append_queue_carriers": "sha256:" + REPO_INPUT_SHA256[APPEND_QUEUE_PATH.name],
        "votes_a": "sha256:" + CANONICAL_SHA256["votes-a.jsonl"],
        "votes_a_source": "sha256:" + SOURCE_SHA256["votes-a.jsonl"],
        "votes_b": "sha256:" + CANONICAL_SHA256["votes-b.jsonl"],
        "votes_b_source": "sha256:" + SOURCE_SHA256["votes-b.jsonl"],
        "assembler_analysis_source": "sha256:" + SOURCE_SHA256["rebind-analysis.json"],
        "ownership_audit": "sha256:" + CANONICAL_SHA256["rb-cert-audit.jsonl"],
        "ownership_audit_source": "sha256:" + SOURCE_SHA256["rb-cert-audit.jsonl"],
        "entries": "sha256:" + packet_manifest["inputs"]["entries"]["sha256"],
        "grammar_gate_ssot": "sha256:" + sha256_path(fact_ledger.GATE_PATH),
        "fact_ledger_schema": "sha256:" + sha256_path(fact_ledger.SCHEMA_PATH),
    }

    certified = set(data["certified_packet_ids"])
    row_reports: list[dict[str, Any]] = []
    for packet_id in sorted(data["packets"]):
        packet = data["packets"][packet_id]
        vote_a = data["votes_a"][packet_id]
        vote_b = data["votes_b"][packet_id]
        loc = packet["canonical_location"]
        row_hashes = dict(base_hashes)
        row_hashes["packet_row"] = "sha256:" + packet["packet_sha256"]
        if packet_id in certified:
            audit_row = data["audit"][packet_id]
            fact_id, carrier = append_certified(
                store, packet=packet, vote_a=vote_a, vote_b=vote_b,
                audit_row=audit_row, append_row=data["append_queue"][loc], input_hashes=row_hashes,
            )
            state = "certified"
            exception = audit_exception(audit_row)
        else:
            detail = data["disagreements"][packet_id]
            fact_id, carrier = append_disagreement(
                store, packet=packet, vote_a=vote_a, vote_b=vote_b, detail=detail,
                append_row=data["append_queue"][loc], input_hashes=row_hashes,
            )
            state = "review_required"
            exception = []
        row_reports.append({
            "canonical_location": loc,
            "packet_id": packet_id,
            "ledger_fact_id": fact_id,
            "ledger_state": state,
            "value": vote_value(vote_a) if vote_a["decision"] != "abstention" else vote_value(vote_b),
            "reviewer_a_decision": vote_a["decision"],
            "reviewer_b_decision": vote_b["decision"],
            "selected_carrier": _carrier_identity(loc, carrier),
            "exception_disposition": exception[0]["disposition"] if exception else None,
        })

    errors = store.validate_all()
    if errors:
        raise CertificationStop("generated ledger validation failed: " + "; ".join(errors[:5]))
    history = store.query(current_only=False)
    current = store.query(current_only=True)
    if len(history) != EXPECTED["history_rows"]:
        raise CertificationStop(f"history row count is {len(history)}, expected 3,669")
    if Counter(row["certification_state"] for row in history) != Counter({
        "candidate": 1_248, "review_required": 1_248, "certified": 1_173,
    }):
        raise CertificationStop("history state counts differ")
    if Counter(row["certification_state"] for row in current) != Counter({
        "certified": 1_173, "review_required": 75,
    }):
        raise CertificationStop("current state counts differ")
    if any(row["certification_state"] == "materialized" or row["materialization_targets"] for row in current):
        raise CertificationStop("generated facts unexpectedly materialize")
    store.flush()
    durable_store = fact_ledger.FactLedgerStore(ledger_dir)
    durable_errors = durable_store.validate_all()
    if durable_errors:
        raise CertificationStop("durable ledger validation failed: " + "; ".join(durable_errors[:5]))

    source_paths = data["source_paths"]
    for source_name, output_name in SOURCE_TO_OUTPUT.items():
        destination = artifact_dir / output_name
        if source_name == "rebind-analysis.json":
            destination.write_bytes(pretty(_public_analysis(data["analysis"])))
        else:
            destination.write_bytes(canonical_jsonl_bytes(source_paths[source_name]))

    report = build_report(data=data, row_reports=row_reports, history=history, current=current)
    report_bytes = pretty(report)
    (artifact_dir / REPORT_PATH.name).write_bytes(report_bytes)
    ledger_bytes = (ledger_dir / fact_ledger.LEDGER_NAME).read_bytes()
    output_paths = {source: artifact_dir / output for source, output in SOURCE_TO_OUTPUT.items()}
    manifest = {
        "schema": "qamus.t11_rebind_certification_manifest.v1",
        "scope": "certification_only_no_materialization_no_live_payload",
        "generated_by": ACTOR,
        "created_at": CREATED_AT,
        "candidate_only": True,
        "no_live_payload": True,
        "determinism": report["determinism"],
        "input_sha_pins": {
            "packets": REPO_INPUT_SHA256[PACKETS_PATH.name],
            "packet_manifest": REPO_INPUT_SHA256[PACKET_MANIFEST_PATH.name],
            "append_queue_carriers": REPO_INPUT_SHA256[APPEND_QUEUE_PATH.name],
            "votes_a_source": SOURCE_SHA256["votes-a.jsonl"],
            "votes_a_canonical": CANONICAL_SHA256["votes-a.jsonl"],
            "votes_b_source": SOURCE_SHA256["votes-b.jsonl"],
            "votes_b_canonical": CANONICAL_SHA256["votes-b.jsonl"],
            "assembler_analysis_source": SOURCE_SHA256["rebind-analysis.json"],
            "ownership_audit_source": SOURCE_SHA256["rb-cert-audit.jsonl"],
            "ownership_audit_canonical": CANONICAL_SHA256["rb-cert-audit.jsonl"],
            "entries": packet_manifest["inputs"]["entries"]["sha256"],
            "grammar_gate_ssot": sha256_path(fact_ledger.GATE_PATH),
            "fact_ledger_schema_current": sha256_path(fact_ledger.SCHEMA_PATH),
        },
        "outputs": {
            "ledger": {
                "path": relative(LEDGER_DIR / fact_ledger.LEDGER_NAME),
                "sha256": sha256_bytes(ledger_bytes),
                "revision_rows": len(history),
                "current_facts": len(current),
            },
            "report": {"path": relative(REPORT_PATH), "sha256": sha256_bytes(report_bytes)},
            **{
                SOURCE_TO_OUTPUT[source]: {
                    "path": relative(QUEUE_DIR / SOURCE_TO_OUTPUT[source]),
                    "sha256": sha256_path(path),
                }
                for source, path in output_paths.items()
            },
        },
        "counts": report["counts"],
        "row_arithmetic": report["row_arithmetic"],
        "mutation_boundaries": report["mutation_boundaries"],
        "shadow_surface_assertion": report["shadow_surface_assertion"],
    }
    (artifact_dir / MANIFEST_PATH.name).write_bytes(pretty(manifest))
    return {
        "ledger": ledger_dir / fact_ledger.LEDGER_NAME,
        "report": artifact_dir / REPORT_PATH.name,
        "manifest": artifact_dir / MANIFEST_PATH.name,
        **{SOURCE_TO_OUTPUT[source]: path for source, path in output_paths.items()},
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
        **{output: QUEUE_DIR / output for output in SOURCE_TO_OUTPUT.values()},
    }
    for name, destination in destinations.items():
        atomic_install(bundle[name], destination)
    index_path = LEDGER_DIR / fact_ledger.INDEX_NAME
    if index_path.exists():
        index_path.unlink()


def _self_test(source_dir: Path) -> int:
    schema = fact_ledger.load_schema()
    registry = {row["id"]: row for row in schema["x-fact-type-registry"]["types"]}
    if registry.get(FACT_TYPE, {}).get("gate_trigger") != GATE_TRIGGER:
        raise CertificationStop("governing_entry_analysis registry gate differs")
    if FACT_TYPE not in fact_ledger._two_vote_fact_types(schema, fact_ledger.GATE_PATH):
        raise CertificationStop("governing_entry_analysis is not fail-closed two-vote")
    with tempfile.TemporaryDirectory(prefix="rebind-cert-self-test-") as temp:
        deterministic_build(source_dir, Path(temp))
    print("certify_rebind_wave self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
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
        with tempfile.TemporaryDirectory(prefix="rebind-cert-") as temp:
            bundle = deterministic_build(source_dir, Path(temp))
            if args.write:
                install_bundle(bundle)
        print("certify_rebind_wave %s OK" % ("write" if args.write else "check"))
        return 0
    except (CertificationStop, fact_ledger.ValidationError, OSError, ValueError, KeyError) as exc:
        print("certify_rebind_wave FAIL:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
