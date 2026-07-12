#!/usr/bin/env python3
"""Disposition the wave-4 A-bound/B-affirmed tranche through authoritative T3.

This writer follows ``promote_wave4_certified.py`` for affirm-live rows but adds
the missing deterministic ownership gate.  It never changes a crosswalk or
shadow artifact: passing rows remain physical queue rows, are refamilied to
``affirmed_live_no_canonical_carrier``, and receive a certified append-only
``gloss_contribution`` lifecycle.  A failing row remains review-required and
gets a named ``t4_packet``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402
from tools.enrich_rebind_queue import (  # noqa: E402
    BY_NORM_SURFACE,
    BY_ROOT,
    ENTRIES,
    Morphology,
    read_json,
    read_jsonl,
)
from tools.fusha_text_check import segment_candidates  # noqa: E402
from tools.normalize_ar import bare, norm_strict  # noqa: E402


class DueProcessStop(RuntimeError):
    """Fail-closed stop for drift or an invalid due-process transition."""


ACTOR = "tools/promote_wave4_affirm_live_t3.py"
METHOD = "wave4_affirm_live_t3_due_process_v1"
PROMOTED_AT = "2026-07-12T00:00:00Z"
AFFIRM_VALUE = "affirm_live_no_carrier_owns_token"
AFFIRM_FAMILY = "affirmed_live_no_canonical_carrier"
AFFIRM_REVIEW_STATE = "affirmed_live_no_canonical_carrier"
T3_CONCLUSION = "t3_confirms_affirm_live"
EXPECTED_ROWS = 136
QUEUE_ROWS_BEFORE = 4854
ACTIVE_LIVE_ONLY_BEFORE = 4843
EXPECTED_CURRENT_LEDGER = {"candidate": 213, "certified": 1521, "review_required": 160}
INPUT_SHA256 = {
    "t3-verdicts.jsonl": "cd2ae1fb527e36cce20f1c61f4010062f469b7b15b04954138900b70ba1f9de5",
    "votes-a.jsonl": "eae6df36cb915de523fa817bd80861a95f586411caa873370d9e2e5bf29015b2",
    "votes-b.jsonl": "5224cd3848c0600acaf1c9fb330d788b5052cd7badf3df5407239f88aebf8002",
}

QUEUE_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "crosswalk-gap"
QUEUE_PATH = QUEUE_DIR / "crosswalk-gap-queue.jsonl"
QUEUE_MANIFEST_PATH = QUEUE_DIR / "crosswalk-gap-queue.manifest.json"
PACKETS_PATH = QUEUE_DIR / "two-vote" / "packets-wave-04.jsonl"
REPORT_PATH = QUEUE_DIR / "laneb-wave-04-affirm-live-t3.report.json"
LEDGER_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "fact-ledger"
LEDGER_PATH = LEDGER_DIR / "laneb-review.jsonl"
SHADOW_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "canonical-hover-shadow-rm20"
CROSSWALK_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk"


def canonical_bytes(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return text.encode("utf-8")


def ledger_jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) for row in rows)


def queue_jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            raise DueProcessStop(f"blank JSONL row at {path}:{number}")
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise DueProcessStop(f"invalid JSON at {path}:{number}: {exc}") from exc
    return rows


def index_unique(rows: Iterable[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise DueProcessStop(f"{label} row missing {key}")
        if value in out:
            raise DueProcessStop(f"duplicate {label} {key}: {value}")
        out[value] = row
    return out


def load_morphology() -> Morphology:
    return Morphology(read_jsonl(ENTRIES), read_json(BY_ROOT), read_json(BY_NORM_SURFACE))


def root_alternatives(value: Any) -> set[str]:
    return {part.strip() for part in str(value or "").split("/") if part.strip()}


def surface_keys(surface: str) -> set[str]:
    keys = {norm_strict(surface), bare(surface)}
    for candidate in segment_candidates(surface):
        for segment in candidate.get("segments", []):
            if segment.get("role") == "stem":
                keys.add(norm_strict(segment.get("surface") or ""))
                keys.add(bare(segment.get("surface") or ""))
    return {key for key in keys if key}


def target_ownership(packet: dict[str, Any], morphology: Morphology) -> dict[str, Any]:
    target_self = packet["morphology_record"]["target_self"]
    surface = target_self["surface"]["value"]
    keys = surface_keys(surface)
    roots = root_alternatives(target_self["root"]["value"])
    root_evidence: dict[str, set[str]] = defaultdict(set)
    for root in roots:
        root_evidence[root].add("packet_target_self")
    documented_eids: set[str] = set()
    for key in keys:
        for root in morphology.form_roots.get(key, ()):
            for alternative in root_alternatives(root):
                roots.add(alternative)
                root_evidence[alternative].add("documented_form_lookup")
        documented_eids.update(morphology.form_eids.get(key, ()))
    return {
        "surface": surface,
        "surface_keys": sorted(keys),
        "root_candidates": sorted(roots),
        "root_evidence": {root: sorted(methods) for root, methods in sorted(root_evidence.items())},
        "documented_entry_ids": sorted(documented_eids),
        "lookup_boundary": (
            "packet target_self plus exact documented headword/sense/usage forms and legal clitic stems; "
            "broad normalized usage-quote fallback and fuzzy root skeleton recall are excluded"
        ),
    }


def bound_carriers(packet: dict[str, Any]) -> list[dict[str, Any]]:
    loc = packet["canonical_location"]
    carriers = [
        carrier
        for carrier in packet.get("candidate_carriers", [])
        if loc in (carrier.get("fingerprint_match_candidates") or [])
    ]
    carriers.sort(key=lambda row: row["qword_row_id"])
    if not carriers:
        raise DueProcessStop(f"A-bound location {loc} has no fingerprint-bound carrier")
    return carriers


def _embedded_documented_keys(carrier: dict[str, Any], morphology: Morphology) -> set[str]:
    entry = morphology.entry.get(carrier.get("entry_id"))
    surfaces: list[str] = []
    if entry:
        surfaces.extend(Morphology._documented_forms(entry))
    content = carrier.get("candidate_entry_content") or {}
    for sense in content.get("senses") or []:
        for piece in str((sense.get("content") or {}).get("ar") or "").split("/"):
            surfaces.append(piece)
    for usage in content.get("matching_usage_examples") or []:
        surfaces.extend(str(form) for form in usage.get("usage_forms") or [])
    keys: set[str] = set()
    for surface in surfaces:
        keys.update((norm_strict(surface), bare(surface)))
    return {key for key in keys if key}


def deterministic_zero_overlap(packet: dict[str, Any], morphology: Morphology) -> dict[str, Any]:
    target = target_ownership(packet, morphology)
    target_roots = set(target["root_candidates"])
    target_keys = set(target["surface_keys"])
    target_eids = set(target["documented_entry_ids"])
    overlaps: list[dict[str, Any]] = []
    carrier_checks: list[dict[str, Any]] = []
    for carrier in bound_carriers(packet):
        content = carrier["candidate_entry_content"]
        declared_root = content["root"]["value"]
        carrier_roots = root_alternatives(declared_root)
        shared_roots = sorted(target_roots & carrier_roots)
        blank_noun = not carrier_roots and content["section"]["value"] == "noun"
        documented_keys = _embedded_documented_keys(carrier, morphology) if blank_noun else set()
        blank_form_overlap = blank_noun and (
            carrier["entry_id"] in target_eids or bool(target_keys & documented_keys)
        )
        if shared_roots:
            overlaps.append({
                "carrier_qword_row_id": carrier["qword_row_id"],
                "entry_id": carrier["entry_id"],
                "overlap_kind": "root",
                "values": shared_roots,
            })
        if blank_form_overlap:
            overlaps.append({
                "carrier_qword_row_id": carrier["qword_row_id"],
                "entry_id": carrier["entry_id"],
                "overlap_kind": "blank_root_noun_documented_form",
                "values": sorted(target_keys & documented_keys),
            })
        carrier_checks.append({
            "qword_row_id": carrier["qword_row_id"],
            "entry_id": carrier["entry_id"],
            "declared_roots": sorted(carrier_roots),
            "blank_root_noun": blank_noun,
            "root_overlap": shared_roots,
            "documented_form_overlap": bool(blank_form_overlap),
        })
    passed = not overlaps
    return {
        "passed": passed,
        "failed_gate": None if passed else "gate_1_deterministic_zero_overlap",
        "target_surface": target["surface"],
        "target_root_candidates": target["root_candidates"],
        "target_root_evidence": target["root_evidence"],
        "target_documented_entry_ids": target["documented_entry_ids"],
        "lookup_boundary": target["lookup_boundary"],
        "bound_carrier_count": len(carrier_checks),
        "carrier_checks": carrier_checks,
        "overlaps": overlaps,
    }


def evaluate_triple_gate(packet: dict[str, Any], vote_b: dict[str, Any],
                         t3: dict[str, Any], morphology: Morphology) -> dict[str, Any]:
    deterministic = deterministic_zero_overlap(packet, morphology)
    gate_2 = vote_b.get("proposed_conclusion") == AFFIRM_VALUE
    gate_3 = t3.get("verdict") == T3_CONCLUSION
    failed = deterministic["failed_gate"]
    if failed is None and not gate_2:
        failed = "gate_2_b_vote"
    if failed is None and not gate_3:
        failed = "gate_3_t3_verdict"
    return {
        "passed": failed is None,
        "failed_gate": failed,
        "gates": {
            "gate_1_deterministic_zero_overlap": deterministic,
            "gate_2_b_vote": {
                "passed": gate_2,
                "actual": vote_b.get("proposed_conclusion"),
                "required": AFFIRM_VALUE,
            },
            "gate_3_t3_verdict": {
                "passed": gate_3,
                "actual": t3.get("verdict"),
                "required": T3_CONCLUSION,
            },
        },
    }


def _carrier_identity(loc: str, carrier: dict[str, Any]) -> dict[str, str]:
    return {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": carrier["entry_id"],
        "card_id": carrier["card_id"],
        "qword_row_id": carrier["qword_row_id"],
    }


def current_facts(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for row in rows:
        current[row["fact_id"]] = row
    return current


def state_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(row["certification_state"] for row in current_facts(rows).values()).items()))


def validate_final_ledger(rows: Iterable[dict[str, Any]]) -> None:
    current: dict[str, dict[str, Any]] = {}
    for number, row in enumerate(rows, 1):
        previous = current.get(row["fact_id"])
        try:
            fact_ledger.validate_row(row, previous=previous)
        except fact_ledger.ValidationError as exc:
            raise DueProcessStop(f"ledger validation failed at row {number}: {exc}") from exc
        current[row["fact_id"]] = row
    certified_by_collision_key: dict[str, list[str]] = defaultdict(list)
    for row in current.values():
        if row["certification_state"] != "certified":
            continue
        key = json.dumps({
            "subject_identity": row["subject_identity"],
            "fact_type": row["fact_type"],
            "scope": row["scope"],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        certified_by_collision_key[key].append(row["fact_id"])
    collisions = [ids for ids in certified_by_collision_key.values() if len(ids) > 1]
    if collisions:
        raise DueProcessStop(f"final ledger has certified value collisions: {collisions[:3]}")


def prior_review_fact(loc: str, ledger_rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [
        row for row in current_facts(ledger_rows).values()
        if row["subject_identity"].get("loc") == loc
        and row["fact_type"] == "gloss_contribution"
        and row["certification_state"] == "review_required"
        and any(
            alt.get("value") == AFFIRM_VALUE
            for alt in row["candidate_or_value"].get("competing_alternatives", [])
        )
    ]
    if len(matches) != 1:
        raise DueProcessStop(f"{loc}: expected one current A-bound/B-affirmed review fact, found {len(matches)}")
    return matches[0]


def _base_fact(loc: str, packet: dict[str, Any], prior: dict[str, Any],
               gate: dict[str, Any], input_hashes: dict[str, str]) -> dict[str, Any]:
    carrier = sorted(bound_carriers(packet), key=lambda row: row["qword_row_id"])[0]
    competing = [{
        "value": prior["candidate_or_value"]["value"],
        "reason": "reviewer A contrary binding conclusion preserved in prior fact history",
    }]
    deterministic = gate["gates"]["gate_1_deterministic_zero_overlap"]
    evidence = [{
        "evidence_id": "deterministic-zero-overlap",
        "type": "deterministic_derivation",
        "detail": (
            f"target roots {deterministic['target_root_candidates']} have zero ownership overlap "
            f"with all {deterministic['bound_carrier_count']} A-bound carriers; exact documented-form "
            "and blank-root noun checks also found zero overlap"
        ),
        "source_address": f"{PACKETS_PATH.relative_to(ROOT).as_posix()}#packet_id={packet['packet_id']}",
    }]
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": _carrier_identity(loc, carrier),
        "fact_type": "gloss_contribution",
        "candidate_or_value": {
            "value": AFFIRM_VALUE,
            "competing_alternatives": competing,
            "semantic_tie": False,
        },
        "scope": "occurrence",
        "source_address": {"address": "quran:" + loc, "source_kind": "quran_token"},
        "evidence": evidence,
        "provenance": {
            "actor": ACTOR,
            "method": METHOD,
            "created_at": PROMOTED_AT,
            "input_hashes": input_hashes,
        },
        "review_votes": [],
        "certification_state": "candidate",
        "confidence_or_calibration": None,
        "defeaters": [],
        "exceptions": [{
            "type": "prior_disagreement_fact",
            "fact_id": prior["fact_id"],
            "disposition": "retired_after_authoritative_t3_due_process",
            "reviewer_a_contrary_vote_preserved": True,
        }],
        "dependency_hashes": {},
        "materialization_targets": [],
        "supersedes": None,
        "created_from": prior["fact_id"],
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def append_pass_lifecycle(ledger_rows: list[dict[str, Any]], *, loc: str,
                          packet: dict[str, Any], vote_b: dict[str, Any],
                          t3: dict[str, Any], gate: dict[str, Any],
                          input_hashes: dict[str, str]) -> tuple[list[dict[str, Any]], str, str]:
    prior = prior_review_fact(loc, ledger_rows)
    retired = copy.deepcopy(prior)
    retired["certification_state"] = "rejected"
    retired["supersedes"] = prior["fact_id"]
    retired["exceptions"] = list(retired.get("exceptions") or []) + [{
        "type": "authoritative_t3_due_process_retirement",
        "reason": "deterministic zero-overlap, reviewer B affirm-live, and authoritative T3 agree",
    }]
    fact_ledger.validate_row(retired, previous=prior)

    candidate = _base_fact(loc, packet, prior, gate, input_hashes)
    fact_ledger.validate_row(candidate, previous=None)
    review = copy.deepcopy(candidate)
    review["certification_state"] = "review_required"
    review["supersedes"] = candidate["fact_id"]
    review["evidence"] = list(candidate["evidence"]) + [{
        "evidence_id": "vote-B",
        "type": "two_vote",
        "detail": vote_b["exact_reason"],
        "source_address": vote_b["source_address"],
    }]
    review["review_votes"] = [{
        "voter_id": "reviewer-B:Codex",
        "vote": "approve",
        "evidence_ref": "vote-B",
        "independent": True,
    }]
    fact_ledger.validate_row(review, previous=candidate)
    certified = copy.deepcopy(review)
    certified["certification_state"] = "certified"
    certified["supersedes"] = candidate["fact_id"]
    certified["evidence"] = list(review["evidence"]) + [{
        "evidence_id": "tier3-authoritative",
        "type": "two_vote",
        "detail": f"authoritative tier verdict {t3['verdict']} for packet {packet['packet_id']}",
        "source_address": f"lane-input:t3-verdicts.jsonl#packet_id={packet['packet_id']}",
    }]
    certified["review_votes"] = list(review["review_votes"]) + [{
        "voter_id": "tier3:authoritative",
        "vote": "approve",
        "evidence_ref": "tier3-authoritative",
        "independent": True,
    }]
    fact_ledger.validate_row(certified, previous=review)
    return [retired, candidate, review, certified], certified["fact_id"], prior["fact_id"]


def mutate_queue(queue_rows: list[dict[str, Any]], gates: dict[str, dict[str, Any]],
                 certified: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    found: set[str] = set()
    for row in queue_rows:
        loc = row["canonical_location"]
        if loc not in gates:
            out.append(copy.deepcopy(row))
            continue
        found.add(loc)
        new = copy.deepcopy(row)
        gate = gates[loc]
        if gate["passed"]:
            new["primary_resolution_family"] = AFFIRM_FAMILY
            new["provenance_state"] = AFFIRM_FAMILY
            new["review_state"] = AFFIRM_REVIEW_STATE
            new["review_votes"] = [
                {
                    "voter_id": "reviewer-A:Opus",
                    "decision_kind": "preserved_contrary_vote",
                    "conclusion": loc,
                },
                {
                    "voter_id": "reviewer-B:Codex",
                    "decision_kind": "decision",
                    "conclusion": AFFIRM_VALUE,
                },
                {
                    "voter_id": "tier3:authoritative",
                    "decision_kind": "decision",
                    "conclusion": T3_CONCLUSION,
                },
            ]
            new["secondary_conditions"] = sorted(set(new.get("secondary_conditions") or []) | {
                AFFIRM_FAMILY,
                "authoritative_t3_due_process",
                "deterministic_zero_ownership_overlap",
                "reopenable_by_future_authoring_lane",
                "terminal_for_binding",
            })
            new["resolution_commit"] = certified[loc]
            new.pop("t4_packet", None)
        else:
            new["t4_packet"] = {
                "schema": "qamus.wave4_affirm_live_t4_packet.v1",
                "failed_gate": gate["failed_gate"],
                "gate_results": gate["gates"],
                "status": "review_required",
            }
        out.append(new)
    missing = set(gates) - found
    if missing:
        raise DueProcessStop(f"queue missing tranche locations: {sorted(missing)[:5]}")
    out.sort(key=lambda row: tuple(int(part) for part in row["canonical_location"].split(":")))
    return out


def update_manifest(manifest: dict[str, Any], queue_rows: list[dict[str, Any]],
                    queue_payload: bytes, pass_count: int, fail_count: int,
                    report_sha256: str) -> dict[str, Any]:
    updated = copy.deepcopy(manifest)
    families = Counter(row["primary_resolution_family"] for row in queue_rows)
    active = sum(row.get("review_state") != "resolved_terminal" for row in queue_rows)
    updated["queue_rows"] = len(queue_rows)
    updated["active_live_only_rows"] = active
    updated["family_counts"] = dict(sorted(families.items()))
    updated["queue_sha256"] = sha256_bytes(queue_payload)
    updated["wave_04_affirm_live_t3_due_process"] = {
        "promoted_at": PROMOTED_AT,
        "gate_pass": pass_count,
        "gate_fail": fail_count,
        "queue_before": QUEUE_ROWS_BEFORE,
        "queue_after": len(queue_rows),
        "active_live_only_before": ACTIVE_LIVE_ONLY_BEFORE,
        "active_live_only_after": active,
        "resolution_method": METHOD,
        "report": REPORT_PATH.relative_to(ROOT).as_posix(),
        "report_sha256": report_sha256,
        "ledger_store": LEDGER_PATH.relative_to(ROOT).as_posix(),
    }
    return updated


@dataclass
class BuildResult:
    queue_rows: list[dict[str, Any]]
    ledger_rows: list[dict[str, Any]]
    manifest: dict[str, Any]
    report: dict[str, Any]

    def output_bytes(self) -> dict[str, bytes]:
        return {
            QUEUE_PATH.relative_to(ROOT).as_posix(): queue_jsonl_bytes(self.queue_rows),
            LEDGER_PATH.relative_to(ROOT).as_posix(): ledger_jsonl_bytes(self.ledger_rows),
            QUEUE_MANIFEST_PATH.relative_to(ROOT).as_posix(): canonical_bytes(self.manifest, pretty=True),
            REPORT_PATH.relative_to(ROOT).as_posix(): canonical_bytes(self.report, pretty=True),
        }


def load_applied_result(input_hashes: dict[str, str]) -> BuildResult:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(QUEUE_MANIFEST_PATH.read_text(encoding="utf-8"))
    queue_rows = read_rows(QUEUE_PATH)
    ledger_rows = read_rows(LEDGER_PATH)
    marker = manifest.get("wave_04_affirm_live_t3_due_process") or {}
    report_payload = canonical_bytes(report, pretty=True)
    checks = {
        "report input hashes": report.get("inputs") == input_hashes,
        "report sha256": marker.get("report_sha256") == sha256_bytes(report_payload),
        "queue sha256": manifest.get("queue_sha256") == sha256_file(QUEUE_PATH),
        "physical queue rows": len(queue_rows) == report["queue_arithmetic"]["physical_rows"][1],
        "active-live-only rows": (
            sum(row.get("review_state") != "resolved_terminal" for row in queue_rows)
            == report["queue_arithmetic"]["active_live_only_rows"][1]
        ),
        "ledger current states": (
            state_counts(ledger_rows) == report["ledger_arithmetic"]["current_state_counts_after"]
        ),
        "canonical shadow tree": (
            tree_sha256(SHADOW_DIR)
            == report["shadow_assertion"]["canonical_shadow_tree_sha256_after"]
        ),
        "qword crosswalk tree": (
            tree_sha256(CROSSWALK_DIR)
            == report["shadow_assertion"]["qword_crosswalk_tree_sha256_after"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise DueProcessStop(f"installed due-process tranche failed readback: {failed}")
    validate_final_ledger(ledger_rows)
    report["generator"] = ACTOR
    report_payload = canonical_bytes(report, pretty=True)
    desired_queue = queue_jsonl_bytes(queue_rows)
    manifest["queue_sha256"] = sha256_bytes(desired_queue)
    manifest["wave_04_affirm_live_t3_due_process"]["report_sha256"] = sha256_bytes(report_payload)
    return BuildResult(queue_rows, ledger_rows, manifest, report)


def build(inputs_dir: Path, *, enforce_input_hashes: bool = True) -> BuildResult:
    inputs_dir = Path(inputs_dir)
    input_paths = {name: inputs_dir / name for name in INPUT_SHA256}
    for name, path in input_paths.items():
        if not path.is_file():
            raise DueProcessStop(f"missing input {path}")
        actual = sha256_file(path)
        if enforce_input_hashes and actual != INPUT_SHA256[name]:
            raise DueProcessStop(f"{name} sha256 drift: {actual} != {INPUT_SHA256[name]}")
    input_hashes = {name.replace(".jsonl", "").replace("-", "_"): "sha256:" + sha256_file(path)
                    for name, path in input_paths.items()}
    input_hashes.update({
        "packets_wave_04": "sha256:" + sha256_file(PACKETS_PATH),
        "entries": "sha256:" + sha256_file(ROOT / ENTRIES),
    })
    installed_manifest = json.loads(QUEUE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if (
        enforce_input_hashes
        and installed_manifest.get("wave_04_affirm_live_t3_due_process")
        and REPORT_PATH.is_file()
    ):
        return load_applied_result(input_hashes)

    t3_by_loc = index_unique(read_rows(input_paths["t3-verdicts.jsonl"]), "canonical_location", "T3")
    vote_a_by_loc = index_unique(read_rows(input_paths["votes-a.jsonl"]), "canonical_location", "vote A")
    vote_b_by_loc = index_unique(read_rows(input_paths["votes-b.jsonl"]), "canonical_location", "vote B")
    packet_by_loc = index_unique(read_rows(PACKETS_PATH), "canonical_location", "packet")
    if len(t3_by_loc) != EXPECTED_ROWS:
        raise DueProcessStop(f"expected {EXPECTED_ROWS} authoritative T3 rows, found {len(t3_by_loc)}")
    tranche_locs = set(t3_by_loc)
    if not tranche_locs <= set(vote_a_by_loc) or not tranche_locs <= set(vote_b_by_loc):
        raise DueProcessStop("T3 locations are not fully covered by both blind-vote files")
    if not tranche_locs <= set(packet_by_loc):
        raise DueProcessStop("T3 locations are not fully covered by wave-4 packets")

    morphology = load_morphology()
    gates: dict[str, dict[str, Any]] = {}
    ordered_locs = sorted(tranche_locs, key=lambda loc: tuple(int(part) for part in loc.split(":")))
    for loc in ordered_locs:
        packet = packet_by_loc[loc]
        vote_a, vote_b, t3 = vote_a_by_loc[loc], vote_b_by_loc[loc], t3_by_loc[loc]
        if not (packet["packet_id"] == vote_a["packet_id"] == vote_b["packet_id"] == t3["packet_id"]):
            raise DueProcessStop(f"{loc}: packet_id join mismatch")
        if vote_a.get("proposed_conclusion") != loc or t3.get("a_binding") != loc:
            raise DueProcessStop(f"{loc}: tranche is not an A-bound row")
        derived_carrier_roots = sorted({
            root
            for carrier in bound_carriers(packet)
            for root in root_alternatives(carrier["candidate_entry_content"]["root"]["value"])
        })
        if derived_carrier_roots != sorted(t3.get("aligning_carrier_roots") or []):
            raise DueProcessStop(f"{loc}: T3 aligning carrier roots drift from packet")
        gates[loc] = evaluate_triple_gate(packet, vote_b, t3, morphology)

    queue_before = read_rows(QUEUE_PATH)
    if len(queue_before) != QUEUE_ROWS_BEFORE:
        raise DueProcessStop(f"physical queue baseline drift: {len(queue_before)} != {QUEUE_ROWS_BEFORE}")
    active_before = sum(row.get("review_state") != "resolved_terminal" for row in queue_before)
    if active_before != ACTIVE_LIVE_ONLY_BEFORE:
        raise DueProcessStop(f"active_live_only baseline drift: {active_before} != {ACTIVE_LIVE_ONLY_BEFORE}")
    ledger_before = read_rows(LEDGER_PATH)
    ledger_states_before = state_counts(ledger_before)
    if ledger_states_before != EXPECTED_CURRENT_LEDGER:
        raise DueProcessStop(
            f"current ledger baseline drift: {ledger_states_before} != {EXPECTED_CURRENT_LEDGER}"
        )

    ledger_after = list(ledger_before)
    certified: dict[str, str] = {}
    retired: dict[str, str] = {}
    for loc in ordered_locs:
        if not gates[loc]["passed"]:
            continue
        appended, certified_id, prior_id = append_pass_lifecycle(
            ledger_after,
            loc=loc,
            packet=packet_by_loc[loc],
            vote_b=vote_b_by_loc[loc],
            t3=t3_by_loc[loc],
            gate=gates[loc],
            input_hashes={**input_hashes, "packet": "sha256:" + packet_by_loc[loc]["packet_sha256"]},
        )
        ledger_after.extend(appended)
        certified[loc] = certified_id
        retired[loc] = prior_id
    validate_final_ledger(ledger_after)

    queue_after = mutate_queue(queue_before, gates, certified)
    physical_after = len(queue_after)
    active_after = sum(row.get("review_state") != "resolved_terminal" for row in queue_after)
    if physical_after != QUEUE_ROWS_BEFORE or active_after != ACTIVE_LIVE_ONLY_BEFORE:
        raise DueProcessStop(
            "F-convention violation: affirm-live refamily must preserve physical and active-live-only counts"
        )

    pass_count = sum(result["passed"] for result in gates.values())
    fail_count = EXPECTED_ROWS - pass_count
    family_before = dict(sorted(Counter(row["primary_resolution_family"] for row in queue_before).items()))
    family_after = dict(sorted(Counter(row["primary_resolution_family"] for row in queue_after).items()))
    shadow_before = tree_sha256(SHADOW_DIR)
    crosswalk_before = tree_sha256(CROSSWALK_DIR)
    report = {
        "schema": "qamus.laneb-wave4-affirm-live-t3-report.v1",
        "state": "finalized",
        "generator": ACTOR,
        "promoted_at": PROMOTED_AT,
        "resolution_method": METHOD,
        "inputs": input_hashes,
        "counts": {
            "tranche_rows": EXPECTED_ROWS,
            "gate_pass": pass_count,
            "gate_fail": fail_count,
            "certified_affirm_live_facts": len(certified),
            "prior_review_required_facts_retired": len(retired),
            "t4_packets": fail_count,
        },
        "queue_arithmetic": {
            "physical_rows": [QUEUE_ROWS_BEFORE, physical_after],
            "active_live_only_rows": [ACTIVE_LIVE_ONLY_BEFORE, active_after],
            "active_live_only_definition": "queue row review_state is not resolved_terminal",
            "family_counts_before": family_before,
            "family_counts_after": family_after,
            "convention": (
                "PR #72 F convention: affirm-live rows remain physical queue rows and retain a non-"
                "resolved_terminal review_state, so refamilies do not reduce physical or active-live-only counts"
            ),
        },
        "ledger_arithmetic": {
            "current_state_counts_before": ledger_states_before,
            "current_state_counts_after": state_counts(ledger_after),
            "appended_rows": len(ledger_after) - len(ledger_before),
            "per_pass_append": (
                "retire prior review_required assertion as rejected; append candidate -> review_required -> "
                "certified affirm-live lifecycle, linked by created_from"
            ),
        },
        "shadow_assertion": {
            "byte_stable": True,
            "canonical_shadow_tree_sha256_before": shadow_before,
            "canonical_shadow_tree_sha256_after": shadow_before,
            "qword_crosswalk_tree_sha256_before": crosswalk_before,
            "qword_crosswalk_tree_sha256_after": crosswalk_before,
            "reason": "affirm-live only; no crosswalk, whitelist, or canonical-shadow mutation",
        },
        "gate_results": [
            {
                "canonical_location": loc,
                "packet_id": packet_by_loc[loc]["packet_id"],
                "passed": gates[loc]["passed"],
                "failed_gate": gates[loc]["failed_gate"],
                "deterministic_check": gates[loc]["gates"]["gate_1_deterministic_zero_overlap"],
                "b_vote": gates[loc]["gates"]["gate_2_b_vote"],
                "t3_verdict": gates[loc]["gates"]["gate_3_t3_verdict"],
                "prior_review_fact_id": retired.get(loc),
                "certified_fact_id": certified.get(loc),
            }
            for loc in ordered_locs
        ],
    }
    report_payload = canonical_bytes(report, pretty=True)
    manifest_before = json.loads(QUEUE_MANIFEST_PATH.read_text(encoding="utf-8"))
    queue_payload = queue_jsonl_bytes(queue_after)
    manifest_after = update_manifest(
        manifest_before,
        queue_after,
        queue_payload,
        pass_count,
        fail_count,
        sha256_bytes(report_payload),
    )
    return BuildResult(queue_after, ledger_after, manifest_after, report)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(result: BuildResult) -> None:
    payloads = result.output_bytes()
    backup = {ROOT / rel: (ROOT / rel).read_bytes() if (ROOT / rel).exists() else None
              for rel in payloads}
    try:
        for rel, payload in payloads.items():
            _atomic_write(ROOT / rel, payload)
    except Exception:
        for path, payload in backup.items():
            if payload is None:
                path.unlink(missing_ok=True)
            else:
                _atomic_write(path, payload)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-dir", type=Path, default=ROOT / ".lane-inputs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        import unittest

        suite = unittest.defaultTestLoader.loadTestsFromName(
            "tools.test_promote_wave4_affirm_live_t3"
        )
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    result = build(args.inputs_dir)
    if not args.dry_run:
        apply(result)
    print(json.dumps({
        "dry_run": args.dry_run,
        "gate_pass": result.report["counts"]["gate_pass"],
        "gate_fail": result.report["counts"]["gate_fail"],
        "queue_physical": result.report["queue_arithmetic"]["physical_rows"],
        "queue_active_live_only": result.report["queue_arithmetic"]["active_live_only_rows"],
        "ledger_current_after": result.report["ledger_arithmetic"]["current_state_counts_after"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
