#!/usr/bin/env python3
"""Certify the T11 function-word wave without materializing compiler inputs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402


QUEUE_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "class2" / "two-vote"
PACKETS_PATH = QUEUE_DIR / "packets-funcword.jsonl"
PACKET_MANIFEST_PATH = QUEUE_DIR / "packets-funcword.manifest.json"
FUNCWORD_QUEUE_PATH = QUEUE_DIR.parent / "funcword-queue.v2.jsonl"
APPEND_QUEUE_PATH = QUEUE_DIR.parent.parent / "append-queue.jsonl"
LEDGER_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "fact-ledger" / "funcword-cert"
REPORT_PATH = QUEUE_DIR / "funcword-certification.report.json"
MANIFEST_PATH = QUEUE_DIR / "funcword-certification.manifest.json"

SOURCE_TO_OUTPUT = {
    "funcword-analysis.json": "funcword-analysis.json",
    "votes-a.jsonl": "funcword-votes-a.jsonl",
    "votes-b.jsonl": "funcword-votes-b.jsonl",
}
SOURCE_SHA256 = {
    "funcword-analysis.json": "71c6c6017d5386e4e616ff58e0b7757f962228246214ee58d417056229fbaf60",
    "votes-a.jsonl": "e2cd4d7d2dab7835d0714beac947d03dff98bd2bc0a50f8f05bd3d2008485bb8",
    "votes-b.jsonl": "6e3e7777b96641b374bec98b433c67138a969ae19fee9e9910e055c1dcf43a60",
}
PUBLIC_ANALYSIS_SHA256 = "b5befe978d7a6748a7fc8ce0a39e18802a472cc38a0b2a824527f79167152ace"
REPO_INPUT_SHA256 = {
    PACKETS_PATH.name: "fa01441d1f901323663b2852b67384818740ff6b3976fdf0654e2de65305b575",
    PACKET_MANIFEST_PATH.name: "bfc7c30765222e93326ffcc00fef1251c1e9cd2abd3b934e7e96f060f770b050",
    FUNCWORD_QUEUE_PATH.name: "a40aabf38e3337e1b5ccbffa411df702c89a8fb8f2e2660218414bca220d5bd7",
    APPEND_QUEUE_PATH.name: "d726cfeb033796f25f5ffa31d9f3df876d75638b080d43f9b155b47bac62a364",
}
EXPECTED = {
    "packets": 1_043,
    "ordinary_certified": 862,
    "t2_normalized": 26,
    "certified": 888,
    "disagreements": 155,
    "history_rows": 2_974,
}
FACT_TYPE = "function_word_analysis"
GATE_TRIGGER = "advanced_nahw"
ACTOR = "tools/certify_funcword_wave.py"
METHOD = "T11 function-word engine-diverse two-vote certification with binding T2 normalization"
CREATED_AT = "2026-07-12T00:00:00Z"
VOTER_IDS = {"A": "reviewer-A:Opus", "B": "reviewer-B:Codex"}

SHADOW_PATHS = (
    ROOT / "qamus" / "data" / "current" / "entries.jsonl",
    ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "append-queue.jsonl",
    ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "class2" / "funcword-queue.v2.jsonl",
    ROOT / "qamus" / "indexes" / "largelexicon" / "append-queue" / "class2" / "rebind-queue.v2.jsonl",
    ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-crosswalk.manifest.json",
    ROOT / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk",
)


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
    if all((QUEUE_DIR / output).is_file() for output in SOURCE_TO_OUTPUT.values()):
        return QUEUE_DIR
    raise CertificationStop("function-word certification inputs are unavailable")


def resolve_source_paths(source_dir: Path) -> dict[str, Path]:
    canonical_paths = {name: source_dir / output for name, output in SOURCE_TO_OUTPUT.items()}
    if all(path.is_file() for path in canonical_paths.values()):
        return canonical_paths
    source_paths = {name: source_dir / name for name in SOURCE_TO_OUTPUT}
    if all(path.is_file() for path in source_paths.values()):
        return source_paths
    raise CertificationStop(f"incomplete function-word certification input set in {source_dir}")


def _public_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Replace tranche-local filenames while preserving the assembler decision record."""
    public = copy.deepcopy(analysis)
    public["inputs"]["reviewer_a"] = {
        "file": "funcword-votes-a.jsonl",
        "rows": 1_043,
        "source_tranches": 2,
    }
    public["inputs"]["reviewer_b"] = {"file": "funcword-votes-b.jsonl", "rows": 1_043}
    return public


def vote_category(vote: dict[str, Any]) -> str | None:
    if vote["decision"] == "reclassify":
        return vote.get("corrected_category")
    if vote["decision"] == "function_confirmed":
        return vote.get("taxonomy_category")
    return None


def vote_reason(vote: dict[str, Any]) -> str:
    if vote.get("governor_note"):
        return str(vote["governor_note"])
    rationale = vote.get("rationale") or {}
    if rationale.get("exact_reason"):
        return str(rationale["exact_reason"])
    if vote.get("needs_entry_reason"):
        return str(vote["needs_entry_reason"])
    if vote.get("abstention_or_blocker"):
        return str(vote["abstention_or_blocker"])
    return "review decision preserved in the committed vote artifact"


def decision_value(vote: dict[str, Any]) -> dict[str, Any]:
    return {
        "taxonomy_category": vote_category(vote),
        "governor_note": vote_reason(vote),
    }


def agreed_value(vote_a: dict[str, Any], vote_b: dict[str, Any]) -> dict[str, Any]:
    category_a = vote_category(vote_a)
    category_b = vote_category(vote_b)
    if not category_a or category_a != category_b:
        raise CertificationStop(f"{vote_a['packet_id']}: agreeing category is absent or differs")
    return {
        "taxonomy_category": category_a,
        "governor_note": (
            f"Reviewer A (Opus): {vote_reason(vote_a)} | "
            f"Reviewer B (Codex): {vote_reason(vote_b)}"
        ),
    }


def validate_inputs(source_dir: Path) -> dict[str, Any]:
    source_paths = resolve_source_paths(source_dir)
    for name, path in source_paths.items():
        actual = sha256_path(path)
        allowed = {SOURCE_SHA256[name]}
        if name == "funcword-analysis.json":
            allowed.add(PUBLIC_ANALYSIS_SHA256)
        if actual not in allowed:
            raise CertificationStop(f"SHA-256 mismatch for {path}: {actual} not in {sorted(allowed)}")
        if name.endswith(".jsonl") and sha256_bytes(canonical_jsonl_bytes(path)) != SOURCE_SHA256[name]:
            raise CertificationStop(f"canonical SHA-256 mismatch for {path}")
    for path in (PACKETS_PATH, PACKET_MANIFEST_PATH, FUNCWORD_QUEUE_PATH, APPEND_QUEUE_PATH):
        _require_sha(path, REPO_INPUT_SHA256[path.name])

    analysis = json.loads(source_paths["funcword-analysis.json"].read_text(encoding="utf-8"))
    packets = index_unique(load_jsonl(PACKETS_PATH), "packet_id", "packets")
    votes_a = index_unique(load_jsonl(source_paths["votes-a.jsonl"]), "packet_id", "votes-a")
    votes_b = index_unique(load_jsonl(source_paths["votes-b.jsonl"]), "packet_id", "votes-b")
    append_queue = index_unique(load_jsonl(APPEND_QUEUE_PATH), "canonical_location", "append-queue")
    summary = analysis.get("summary", {})
    expected_summary = {
        "abstention_pairs": 0,
        "agree_conclusion_reasoning_incompatible": 0,
        "certified_candidates": 862,
        "disagreements_by_class": {
            "abstention-vs-decision": 7,
            "confirmed-vs-needs_entry": 26,
            "different-category": 66,
            "other": 56,
        },
        "disagreements_total": 155,
        "same_category_different_kind_T2": 26,
    }
    if summary != expected_summary:
        raise CertificationStop(f"assembler summary differs: {summary}")
    validation = analysis.get("validation", {})
    echo = validation.get("echo_check", {})
    if (
        validation.get("hard_findings") != []
        or validation.get("hard_findings_count") != 0
        or validation.get("packet_id_set_identical") is not True
        or any(value != 0 for value in echo.values())
    ):
        raise CertificationStop("assembler validation is not clean")

    ordinary_ids = analysis.get("certified_candidate_ids", [])
    t2 = index_unique(analysis.get("t2_same_category_different_kind", []), "packet_id", "T2 rows")
    disagreements = index_unique(analysis.get("disagreement_rows", []), "packet_id", "disagreements")
    if len(ordinary_ids) != EXPECTED["ordinary_certified"] or len(set(ordinary_ids)) != len(ordinary_ids):
        raise CertificationStop("ordinary certified packet ids do not reconcile")
    if len(t2) != EXPECTED["t2_normalized"] or len(disagreements) != EXPECTED["disagreements"]:
        raise CertificationStop("T2/disagreement counts do not reconcile")
    classes = Counter(row.get("class") for row in disagreements.values())
    if classes != Counter(expected_summary["disagreements_by_class"]):
        raise CertificationStop(f"disagreement classes differ: {dict(classes)}")
    packet_ids = set(packets)
    ordinary_set = set(ordinary_ids)
    certified_set = ordinary_set | set(t2)
    if not (packet_ids == set(votes_a) == set(votes_b)):
        raise CertificationStop("packet and vote packet-id sets differ")
    if certified_set & set(disagreements) or certified_set | set(disagreements) != packet_ids:
        raise CertificationStop("certified and disagreement partitions do not cover exactly 1,043 packets")

    for packet_id, packet in packets.items():
        vote_a = votes_a[packet_id]
        vote_b = votes_b[packet_id]
        loc = packet["canonical_location"]
        if vote_a.get("canonical_location") != loc or vote_b.get("canonical_location") != loc:
            raise CertificationStop(f"{packet_id}: vote location mismatch")
        if packet.get("packet_sha256") != vote_a.get("packet_sha256") or packet.get("packet_sha256") != vote_b.get("packet_sha256"):
            raise CertificationStop(f"{packet_id}: packet SHA echo mismatch")
        if packet.get("evidence_hashes") != vote_a.get("evidence_hashes") or packet.get("evidence_hashes") != vote_b.get("evidence_hashes"):
            raise CertificationStop(f"{packet_id}: evidence hashes differ")
        carriers = append_queue.get(loc, {}).get("bound_carriers", [])
        if not any(all(row.get(key) for key in ("entry_id", "card_id", "qword_row_id")) for row in carriers):
            raise CertificationStop(f"{packet_id}: no complete D-13 carrier")
        if packet_id in ordinary_set:
            if vote_a["decision"] != vote_b["decision"] or vote_category(vote_a) != vote_category(vote_b):
                raise CertificationStop(f"{packet_id}: ordinary agreement differs")
        elif packet_id in t2:
            detail = t2[packet_id]
            if (
                detail.get("class") != "same-category-different-kind"
                or detail.get("direction") != "A_reclassify_B_confirmed"
                or vote_a["decision"] != "reclassify"
                or vote_b["decision"] != "function_confirmed"
                or vote_category(vote_a) != vote_category(vote_b)
            ):
                raise CertificationStop(f"{packet_id}: binding T2 normalization contract differs")

    divine_rows = analysis.get("divine_name_rows", {}).get("rows", [])
    if Counter(row.get("outcome") for row in divine_rows) != Counter({"certified-candidate": 5, "disagreement": 6}):
        raise CertificationStop("divine-name boundary split differs")
    divine_disagreements = [row for row in divine_rows if row.get("outcome") == "disagreement"]
    if any((row.get("a_category"), row.get("b_category")) != ("lam_family", "preposition") for row in divine_disagreements):
        raise CertificationStop("divine-name disagreements are not the six lam/preposition splits")

    return {
        "analysis": analysis,
        "packets": packets,
        "votes_a": votes_a,
        "votes_b": votes_b,
        "append_queue": append_queue,
        "ordinary_certified_packet_ids": ordinary_set,
        "t2_packet_ids": set(t2),
        "t2_rows": t2,
        "certified_packet_ids": certified_set,
        "disagreements": disagreements,
        "source_paths": source_paths,
    }


def evidence(evidence_id: str, evidence_type: str, detail: str, source_address: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "type": evidence_type,
        "detail": detail,
        "source_address": source_address,
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


def carrier_identity(loc: str, carrier: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": carrier["entry_id"],
        "card_id": carrier["card_id"],
        "qword_row_id": carrier["qword_row_id"],
    }


def packet_evidence(packet: dict[str, Any], detail: str | None = None) -> dict[str, Any]:
    packet_id = packet["packet_id"]
    return evidence(
        "packet",
        "source_quote",
        detail or f"packet_id={packet_id}; packet_sha256={packet['packet_sha256']}; gate=two_vote_required",
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/packets-funcword.jsonl#packet_id={packet_id}",
    )


def vote_evidence(vote: dict[str, Any], label: str) -> dict[str, Any]:
    filename = "funcword-votes-a.jsonl" if label == "A" else "funcword-votes-b.jsonl"
    framing = {
        "decision": vote["decision"],
        "taxonomy_category": vote_category(vote),
        "governor_note": vote_reason(vote),
    }
    return evidence(
        f"vote-{label}",
        "two_vote",
        canonical(framing),
        f"qamus/indexes/largelexicon/append-queue/class2/two-vote/{filename}#packet_id={vote['packet_id']}",
    )


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


def decision_lineage(packet: dict[str, Any], vote_a: dict[str, Any], vote_b: dict[str, Any], route: str) -> str:
    return "sha256:" + sha256_bytes(canonical({
        "packet_id": packet["packet_id"],
        "packet_sha256": packet["packet_sha256"],
        "reviewer_a": vote_a,
        "reviewer_b": vote_b,
        "route": route,
    }).encode("utf-8"))


def t2_annotation(vote_a: dict[str, Any], vote_b: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "type": "t2_normalization",
        "t2_normalized": True,
        "shared_taxonomy_category": vote_category(vote_a),
        "reviewer_a_framing": {
            "decision": vote_a["decision"],
            "governor_note": vote_reason(vote_a),
        },
        "reviewer_b_framing": {
            "decision": vote_b["decision"],
            "governor_note": vote_reason(vote_b),
        },
    }]


def base_row(*, packet: dict[str, Any], carrier: dict[str, Any], value: dict[str, Any], alternatives: list[dict[str, Any]],
             row_evidence: list[dict[str, Any]], annotations: list[dict[str, Any]],
             input_hashes: dict[str, str], created_from: str) -> dict[str, Any]:
    packet_id = packet["packet_id"]
    loc = packet["canonical_location"]
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": carrier_identity(loc, carrier),
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
        "exceptions": annotations,
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": created_from,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def append_certified(store: fact_ledger.FactLedgerStore, *, packet: dict[str, Any],
                     vote_a: dict[str, Any], vote_b: dict[str, Any], t2: bool,
                     append_row: dict[str, Any], input_hashes: dict[str, str]) -> tuple[str, dict[str, Any]]:
    packet_ev = packet_evidence(packet)
    annotations = t2_annotation(vote_a, vote_b) if t2 else []
    carrier = select_representative_carrier(packet["canonical_location"], append_row)
    candidate = base_row(
        packet=packet,
        carrier=carrier,
        value=agreed_value(vote_a, vote_b),
        alternatives=[],
        row_evidence=[packet_ev],
        annotations=annotations,
        input_hashes=input_hashes,
        created_from=decision_lineage(packet, vote_a, vote_b, "t2_normalized" if t2 else "ordinary_agreement"),
    )
    store.append(candidate)
    store.transition(candidate["fact_id"], "review_required")
    store.transition(
        candidate["fact_id"],
        "certified",
        review_votes=reviewer_votes(vote_a, vote_b),
        evidence=[packet_ev, vote_evidence(vote_a, "A"), vote_evidence(vote_b, "B")],
    )
    return candidate["fact_id"], carrier


def append_disagreement(store: fact_ledger.FactLedgerStore, *, packet: dict[str, Any],
                        vote_a: dict[str, Any], vote_b: dict[str, Any], detail: dict[str, Any],
                        append_row: dict[str, Any], input_hashes: dict[str, str]) -> tuple[str, dict[str, Any]]:
    value_a = decision_value(vote_a)
    value_b = decision_value(vote_b)
    packet_ev = packet_evidence(
        packet,
        f"two-vote disagreement ({detail['class']}): {canonical(value_a)} / {canonical(value_b)}; never resolved",
    )
    carrier = select_representative_carrier(packet["canonical_location"], append_row)
    candidate = base_row(
        packet=packet,
        carrier=carrier,
        value=value_a,
        alternatives=[
            {"value": value_a, "reason": "reviewer A (Opus) framing"},
            {"value": value_b, "reason": "reviewer B (Codex) framing"},
        ],
        row_evidence=[packet_ev],
        annotations=[],
        input_hashes=input_hashes,
        created_from=decision_lineage(packet, vote_a, vote_b, f"disagreement:{detail['class']}"),
    )
    store.append(candidate)
    store.transition(
        candidate["fact_id"],
        "review_required",
        review_votes=reviewer_votes(vote_a, vote_b),
        evidence=[packet_ev, vote_evidence(vote_a, "A"), vote_evidence(vote_b, "B")],
    )
    return candidate["fact_id"], carrier


def _input_descriptor(path: Path, sha: str | None = None) -> dict[str, Any]:
    return {"path": relative(path), "sha256": sha or sha256_path(path)}


def _snapshot_path(path: Path) -> dict[str, str]:
    if path.is_file():
        return {relative(path): sha256_path(path)}
    if path.is_dir():
        return {
            relative(child): sha256_path(child)
            for child in sorted(item for item in path.rglob("*") if item.is_file())
        }
    raise CertificationStop(f"shadow surface is missing: {path}")


def shadow_snapshot() -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in SHADOW_PATHS:
        snapshot.update(_snapshot_path(path))
    return snapshot


def _shadow_assertion() -> dict[str, Any]:
    return {
        "expected": "byte_stable",
        "observed": "byte_stable",
        "method": "SHA-256 snapshot before and after canonical install",
        "reason": "facts are not materialized and carry no materialization targets",
        "paths": [relative(path) for path in SHADOW_PATHS],
    }


def build_report(*, data: dict[str, Any], row_reports: list[dict[str, Any]],
                 history: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    packet_manifest = json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))
    outputs = {source: QUEUE_DIR / output for source, output in SOURCE_TO_OUTPUT.items()}
    return {
        "schema": "qamus/t11-funcword-certification@1",
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
            "funcword_queue_v2_read_only": _input_descriptor(FUNCWORD_QUEUE_PATH, REPO_INPUT_SHA256[FUNCWORD_QUEUE_PATH.name]),
            "append_queue_carriers_read_only": _input_descriptor(APPEND_QUEUE_PATH, REPO_INPUT_SHA256[APPEND_QUEUE_PATH.name]),
            "votes_a": {**_input_descriptor(outputs["votes-a.jsonl"], SOURCE_SHA256["votes-a.jsonl"]),
                        "source_sha256": SOURCE_SHA256["votes-a.jsonl"], "source_tranches": 2},
            "votes_b": {**_input_descriptor(outputs["votes-b.jsonl"], SOURCE_SHA256["votes-b.jsonl"]),
                        "source_sha256": SOURCE_SHA256["votes-b.jsonl"]},
            "assembler_analysis": {"path": relative(outputs["funcword-analysis.json"]),
                                   "source_sha256": SOURCE_SHA256["funcword-analysis.json"]},
            "entries": packet_manifest["inputs"]["entries"],
            "grammar_gate_ssot": packet_manifest["inputs"]["gate_ssot"],
            "fact_ledger_schema_current": _input_descriptor(fact_ledger.SCHEMA_PATH),
        },
        "counts": {
            "packets_reviewed": EXPECTED["packets"],
            "ordinary_certified": EXPECTED["ordinary_certified"],
            "t2_normalized_certified": EXPECTED["t2_normalized"],
            "certified_total": EXPECTED["certified"],
            "current_states": dict(sorted(Counter(row["certification_state"] for row in current).items())),
            "history_states": dict(sorted(Counter(row["certification_state"] for row in history).items())),
            "history_rows": len(history),
            "disagreements": dict(sorted(Counter(
                row["class"] for row in data["disagreements"].values()
            ).items())),
            "divine_name_rows": {"certified": 5, "review_required": 6},
        },
        "row_arithmetic": "888*3 + 155*2 = 2974",
        "registry_delta": {
            "id": FACT_TYPE,
            "gate_trigger": GATE_TRIGGER,
            "schema_changed": True,
        },
        "determinism": {
            "fixed_created_at": CREATED_AT,
            "wall_clock_fields": False,
            "packet_order": "lexicographic_packet_id",
            "representative_carrier_rule": "lexicographically_first_complete_bound_qword_row_id",
            "double_build_required": True,
        },
        "mutation_boundaries": {
            "queue_changed": False,
            "crosswalk_changed": False,
            "whitelist_changed": False,
            "materialized": False,
        },
        "shadow_surface_assertion": _shadow_assertion(),
        "assembler_summary": data["analysis"]["summary"],
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
        "funcword_queue_v2": "sha256:" + REPO_INPUT_SHA256[FUNCWORD_QUEUE_PATH.name],
        "append_queue_carriers": "sha256:" + REPO_INPUT_SHA256[APPEND_QUEUE_PATH.name],
        "votes_a": "sha256:" + SOURCE_SHA256["votes-a.jsonl"],
        "votes_a_source": "sha256:" + SOURCE_SHA256["votes-a.jsonl"],
        "votes_b": "sha256:" + SOURCE_SHA256["votes-b.jsonl"],
        "votes_b_source": "sha256:" + SOURCE_SHA256["votes-b.jsonl"],
        "assembler_analysis_source": "sha256:" + SOURCE_SHA256["funcword-analysis.json"],
        "entries": "sha256:" + packet_manifest["inputs"]["entries"]["sha256"],
        "grammar_gate_ssot": "sha256:" + sha256_path(fact_ledger.GATE_PATH),
        "fact_ledger_schema": "sha256:" + sha256_path(fact_ledger.SCHEMA_PATH),
    }

    row_reports: list[dict[str, Any]] = []
    for packet_id in sorted(data["packets"]):
        packet = data["packets"][packet_id]
        vote_a = data["votes_a"][packet_id]
        vote_b = data["votes_b"][packet_id]
        row_hashes = dict(base_hashes)
        row_hashes["packet_row"] = "sha256:" + packet["packet_sha256"]
        if packet_id in data["certified_packet_ids"]:
            is_t2 = packet_id in data["t2_packet_ids"]
            fact_id, carrier = append_certified(
                store, packet=packet, vote_a=vote_a, vote_b=vote_b,
                t2=is_t2, append_row=data["append_queue"][packet["canonical_location"]],
                input_hashes=row_hashes,
            )
            state = "certified"
            value = agreed_value(vote_a, vote_b)
        else:
            is_t2 = False
            fact_id, carrier = append_disagreement(
                store, packet=packet, vote_a=vote_a, vote_b=vote_b,
                detail=data["disagreements"][packet_id],
                append_row=data["append_queue"][packet["canonical_location"]],
                input_hashes=row_hashes,
            )
            state = "review_required"
            value = decision_value(vote_a)
        row_reports.append({
            "canonical_location": packet["canonical_location"],
            "packet_id": packet_id,
            "ledger_fact_id": fact_id,
            "ledger_state": state,
            "value": value,
            "reviewer_a_decision": vote_a["decision"],
            "reviewer_b_decision": vote_b["decision"],
            "t2_normalized": is_t2,
            "selected_carrier": carrier_identity(packet["canonical_location"], carrier),
        })

    errors = store.validate_all()
    if errors:
        raise CertificationStop("generated ledger validation failed: " + "; ".join(errors[:5]))
    history = store.query(current_only=False)
    current = store.query(current_only=True)
    if len(history) != EXPECTED["history_rows"]:
        raise CertificationStop(f"history row count is {len(history)}, expected 2,974")
    if Counter(row["certification_state"] for row in history) != Counter({
        "candidate": 1_043, "review_required": 1_043, "certified": 888,
    }):
        raise CertificationStop("history state counts differ")
    if Counter(row["certification_state"] for row in current) != Counter({
        "certified": 888, "review_required": 155,
    }):
        raise CertificationStop("current state counts differ")
    if any(row["certification_state"] == "materialized" or row["materialization_targets"] for row in current):
        raise CertificationStop("generated facts unexpectedly materialize")
    if sum(any(item.get("t2_normalized") is True for item in row["exceptions"]) for row in current) != 26:
        raise CertificationStop("T2 annotation count differs")
    store.flush()
    durable_store = fact_ledger.FactLedgerStore(ledger_dir)
    durable_errors = durable_store.validate_all()
    if durable_errors:
        raise CertificationStop("durable ledger validation failed: " + "; ".join(durable_errors[:5]))

    source_paths = data["source_paths"]
    for source_name, output_name in SOURCE_TO_OUTPUT.items():
        destination = artifact_dir / output_name
        if source_name == "funcword-analysis.json":
            destination.write_bytes(pretty(_public_analysis(data["analysis"])))
        else:
            destination.write_bytes(canonical_jsonl_bytes(source_paths[source_name]))
    report = build_report(data=data, row_reports=row_reports, history=history, current=current)
    report_bytes = pretty(report)
    (artifact_dir / REPORT_PATH.name).write_bytes(report_bytes)
    ledger_bytes = (ledger_dir / fact_ledger.LEDGER_NAME).read_bytes()
    output_paths = {source: artifact_dir / output for source, output in SOURCE_TO_OUTPUT.items()}
    manifest = {
        "schema": "qamus.t11_funcword_certification_manifest.v1",
        "scope": "certification_only_no_materialization_no_live_payload",
        "generated_by": ACTOR,
        "created_at": CREATED_AT,
        "candidate_only": True,
        "no_live_payload": True,
        "determinism": report["determinism"],
        "input_sha_pins": {
            "packets": REPO_INPUT_SHA256[PACKETS_PATH.name],
            "packet_manifest": REPO_INPUT_SHA256[PACKET_MANIFEST_PATH.name],
            "funcword_queue_v2_read_only": REPO_INPUT_SHA256[FUNCWORD_QUEUE_PATH.name],
            "append_queue_carriers_read_only": REPO_INPUT_SHA256[APPEND_QUEUE_PATH.name],
            "votes_a_source": SOURCE_SHA256["votes-a.jsonl"],
            "votes_a_canonical": SOURCE_SHA256["votes-a.jsonl"],
            "votes_b_source": SOURCE_SHA256["votes-b.jsonl"],
            "votes_b_canonical": SOURCE_SHA256["votes-b.jsonl"],
            "assembler_analysis_source": SOURCE_SHA256["funcword-analysis.json"],
            "assembler_analysis_canonical": PUBLIC_ANALYSIS_SHA256,
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
        "registry_delta": report["registry_delta"],
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
    before = shadow_snapshot()
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
    after = shadow_snapshot()
    if after != before:
        changed = sorted(set(before) | set(after))
        changed = [path for path in changed if before.get(path) != after.get(path)]
        raise CertificationStop("shadow surface changed during install: " + ", ".join(changed[:10]))


def _self_test(source_dir: Path) -> int:
    schema = fact_ledger.load_schema()
    registry = {row["id"]: row for row in schema["x-fact-type-registry"]["types"]}
    if registry.get(FACT_TYPE, {}).get("gate_trigger") != GATE_TRIGGER:
        raise CertificationStop("function_word_analysis registry gate differs")
    if FACT_TYPE not in fact_ledger._two_vote_fact_types(schema, fact_ledger.GATE_PATH):
        raise CertificationStop("function_word_analysis is not fail-closed two-vote")
    with tempfile.TemporaryDirectory(prefix="funcword-cert-self-test-") as temp:
        deterministic_build(source_dir, Path(temp))
    print("certify_funcword_wave self-test OK")
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
        with tempfile.TemporaryDirectory(prefix="funcword-cert-") as temp:
            bundle = deterministic_build(source_dir, Path(temp))
            if args.write:
                install_bundle(bundle)
        print("certify_funcword_wave %s OK" % ("write" if args.write else "check"))
        return 0
    except (CertificationStop, fact_ledger.ValidationError, OSError, ValueError, KeyError) as exc:
        print("certify_funcword_wave FAIL:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
