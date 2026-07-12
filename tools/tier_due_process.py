#!/usr/bin/env python3
"""Apply authoritative T3/T2 due process to the two T11 fact-ledger stores.

The writer is intentionally narrow: it appends revisions to rebind-cert and
funcword-cert and writes one review report.  Queue, crosswalk, whitelist, and
canonical-shadow artifacts are read-only protected surfaces.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from collections import Counter
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


ACTOR = "tools/tier_due_process.py"
METHOD = "t11_tier_due_process_v1"
CREATED_AT = "2026-07-12T00:00:00Z"
EXPECTED_DH = {"t3_host_a": 51, "t3_host_b": 10, "t4_packet": 5}
EXPECTED_LILLAHI = {"t2_normalize_to_preposition": 6}
PUBLIC_WHITELIST_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"

LANE_SHA256 = {
    "dh-t3-verdicts.jsonl": "4da0e679af70f009cf3463af29f1425428c9895364b2cab8af587d5e8965485b",
    "lillahi-t2-verdicts.jsonl": "3b00c3d74d190e06efb98f0a3f2dcaf8a97a53cd3cc9703226831c511f16cf43",
}

BASELINE_SHA256 = {
    "qamus/indexes/largelexicon/fact-ledger/rebind-cert/ledger.jsonl":
        "d3321fb63d5124c147631d255f903ac8c2f1d612bb4dc39744e9232d576b13ac",
    "qamus/indexes/largelexicon/fact-ledger/funcword-cert/ledger.jsonl":
        "bb9e16300a55b3ee92cab94d227c43a0bf8a5571c55c6df1826af8634c4a67a7",
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/rebind-votes-a.jsonl":
        "aa3eb85ae32c462fa96afe348c446bbf8e38a01043716efe5dc24c4ad55f9ea8",
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/rebind-votes-b.jsonl":
        "5ae0c7d86eb1bd435050cc318531ac528e497dd0996a439a3a96a58fb5b452e9",
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/funcword-votes-a.jsonl":
        "e2cd4d7d2dab7835d0714beac947d03dff98bd2bc0a50f8f05bd3d2008485bb8",
    "qamus/indexes/largelexicon/append-queue/class2/two-vote/funcword-votes-b.jsonl":
        "6e3e7777b96641b374bec98b433c67138a969ae19fee9e9910e055c1dcf43a60",
    "qamus/data/current/entries.jsonl":
        "b742fde5a8c1a6f04cdf104e0e12fb374ed0d5349eb6a3ace7e34ba2f9e1c15d",
    "qamus/indexes/quran-loc-surface/index.jsonl":
        "97efbaca345d5f23d9e9c699eef155f5bf4e06bb725e430729a8962b1573d227",
    "qamus/schemas/fact-ledger-row.schema.json":
        "18b08c751e425ab34aed525ac064474aa97566d534dd8590d950df27b46257d5",
    "nahw/evals/grammar-decision-gates.json":
        "ccc18bed9af049013cc7aa69b9eb1b27b4639f06c5afd90070a6bc406dd20c5f",
    "tools/build_funcword_two_vote_packets.py":
        "5d68d8eda69e3adb29c83fb50c5c3017601ce9a51aa827eb78bee318fecc2045",
}

REBINDS = ROOT / "qamus/indexes/largelexicon/fact-ledger/rebind-cert/ledger.jsonl"
FUNCWORDS = ROOT / "qamus/indexes/largelexicon/fact-ledger/funcword-cert/ledger.jsonl"
REPORT = ROOT / "qamus/indexes/largelexicon/fact-ledger/tier-due-process.report.json"
LOC_SURFACES = ROOT / "qamus/indexes/quran-loc-surface/index.jsonl"
VOTE_PATHS = {
    "rebind_a": ROOT / "qamus/indexes/largelexicon/append-queue/class2/two-vote/rebind-votes-a.jsonl",
    "rebind_b": ROOT / "qamus/indexes/largelexicon/append-queue/class2/two-vote/rebind-votes-b.jsonl",
    "funcword_a": ROOT / "qamus/indexes/largelexicon/append-queue/class2/two-vote/funcword-votes-a.jsonl",
    "funcword_b": ROOT / "qamus/indexes/largelexicon/append-queue/class2/two-vote/funcword-votes-b.jsonl",
}
PROTECTED_DIRS = {
    "append_queue": ROOT / "qamus/indexes/largelexicon/append-queue",
    "qword_crosswalk": ROOT / "qamus/indexes/largelexicon/qword-crosswalk",
    "canonical_shadow": ROOT / "qamus/indexes/largelexicon/canonical-hover-shadow-rm20",
}


def canonical_bytes(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return text.encode("utf-8")


def ledger_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) for row in rows)


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


def protected_hashes() -> dict[str, str]:
    result = {name: "sha256:" + tree_sha256(path) for name, path in PROTECTED_DIRS.items()}
    result["public_whitelist"] = "sha256:" + PUBLIC_WHITELIST_SHA256
    return result


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
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise DueProcessStop(f"{label} row missing {key}")
        if value in result:
            raise DueProcessStop(f"duplicate {label} {key}: {value}")
        result[value] = row
    return result


def current_facts(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[row["fact_id"]] = row
    return result


def state_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(
        row["certification_state"] for row in current_facts(rows).values()
    ).items()))


def validate_ledger(rows: Iterable[dict[str, Any]]) -> None:
    current: dict[str, dict[str, Any]] = {}
    certified_keys: dict[str, list[str]] = {}
    for number, row in enumerate(rows, 1):
        try:
            fact_ledger.validate_row(row, previous=current.get(row.get("fact_id")))
        except fact_ledger.ValidationError as exc:
            raise DueProcessStop(f"ledger validation failed at row {number}: {exc}") from exc
        current[row["fact_id"]] = row
    for row in current.values():
        if row["certification_state"] != "certified":
            continue
        key = json.dumps({
            "subject_identity": row["subject_identity"],
            "fact_type": row["fact_type"],
            "scope": row["scope"],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        certified_keys.setdefault(key, []).append(row["fact_id"])
    collisions = [ids for ids in certified_keys.values() if len(ids) > 1]
    if collisions:
        raise DueProcessStop(f"certified collisions remain: {collisions[:3]}")


def load_morphology() -> Morphology:
    return Morphology(read_jsonl(ENTRIES), read_json(BY_ROOT), read_json(BY_NORM_SURFACE))


def load_location_surfaces() -> dict[str, str]:
    rows = read_rows(LOC_SURFACES)
    return {row["loc"]: row["surface"] for row in rows}


def _root_alternatives(value: Any) -> set[str]:
    return {piece.strip() for piece in str(value or "").split("/") if piece.strip()}


def _surface_keys(surface: str) -> set[str]:
    keys = {norm_strict(surface), bare(surface)}
    for candidate in segment_candidates(surface):
        for segment in candidate.get("segments", []):
            if segment.get("role") == "stem":
                keys.update({norm_strict(segment.get("surface") or ""), bare(segment.get("surface") or "")})
    return {key for key in keys if key}


def _documented_keys(entry: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for surface in Morphology._documented_forms(entry):
        keys.update({norm_strict(surface), bare(surface)})
    return {key for key in keys if key}


def _noun_convention_overlap(target_keys: set[str], documented: set[str]) -> list[str]:
    """Match a blank-root dedicated noun through only its definite-article shape."""

    stripped: set[str] = set()
    for key in target_keys:
        if key.startswith("ال") and len(key) > 2:
            stripped.add(key[2:])
        for prefix in ("وال", "فال", "بال", "كال"):
            if key.startswith(prefix) and len(key) > len(prefix):
                stripped.add(key[len(prefix):])
    return sorted(stripped & documented)


def deterministic_winning_host_check(verdict: dict[str, Any], morphology: Morphology,
                                     surface: str) -> dict[str, Any]:
    winner_id = verdict.get("chosen_host_id")
    entry = morphology.entry.get(winner_id)
    if entry is None:
        raise DueProcessStop(f"{verdict['canonical_location']}: winning entry is absent: {winner_id}")
    expected_side = "host_a" if verdict.get("verdict") == "t3_host_a" else "host_b"
    stated = verdict.get(expected_side) or {}
    if stated.get("id") != winner_id:
        raise DueProcessStop(f"{verdict['canonical_location']}: verdict/winning-host mismatch")
    for field in ("headword", "root", "section"):
        if str(entry.get(field) or "") != str(stated.get(field) or ""):
            raise DueProcessStop(f"{verdict['canonical_location']}: winning entry {field} drift")

    target_keys = _surface_keys(surface)
    documented = _documented_keys(entry)
    exact_overlap = sorted(target_keys & documented)
    derived, fallback_eids = morphology.derive(surface)
    root_hits = sorted(_root_alternatives(entry.get("root")) & set(derived))
    noun_overlap: list[str] = []
    method: str | None = None
    if exact_overlap or winner_id in fallback_eids:
        method = "documented_form"
    elif root_hits:
        method = "root_derivation"
    elif not entry.get("root") and entry.get("section") == "noun":
        noun_overlap = _noun_convention_overlap(target_keys, documented)
        if noun_overlap:
            method = "noun_convention"
    passed = method is not None
    return {
        "passed": passed,
        "annotation": None if passed else "t4_packet_deterministic_fail",
        "method": method,
        "surface": surface,
        "winning_host_entry_id": winner_id,
        "winning_host_root": entry.get("root") or "",
        "target_surface_keys": sorted(target_keys),
        "documented_form_overlap": exact_overlap,
        "derived_root_overlap": root_hits,
        "derived_root_methods": {root: derived[root] for root in root_hits},
        "noun_convention_overlap": noun_overlap,
        "lookup_boundary": (
            "exact committed documented forms and legal clitic stems; rooted entries may use the "
            "committed deterministic root derivation; blank-root nouns require a dedicated-noun "
            "definite-article convention match"
        ),
    }


def _baseline_input_hashes() -> dict[str, str]:
    return {key.replace("/", "_").replace(".", "_").replace("-", "_"): "sha256:" + value
            for key, value in BASELINE_SHA256.items()}


def load_inputs(inputs_dir: Path) -> dict[str, Any]:
    inputs_dir = Path(inputs_dir)
    lane_paths = {name: inputs_dir / name for name in LANE_SHA256}
    for name, expected in LANE_SHA256.items():
        path = lane_paths[name]
        if not path.is_file():
            raise DueProcessStop(f"missing authoritative input: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise DueProcessStop(f"{name} sha256 drift: {actual} != {expected}")

    dh = read_rows(lane_paths["dh-t3-verdicts.jsonl"])
    lillahi = read_rows(lane_paths["lillahi-t2-verdicts.jsonl"])
    if Counter(row.get("verdict") for row in dh) != Counter(EXPECTED_DH):
        raise DueProcessStop("different_host verdict counts drift")
    if Counter(row.get("verdict") for row in lillahi) != Counter(EXPECTED_LILLAHI):
        raise DueProcessStop("lillahi verdict counts drift")
    if any(row.get("class") != "different_host" for row in dh):
        raise DueProcessStop("different_host input contains another class")
    if any(row.get("ssot_category") != "preposition" for row in lillahi):
        raise DueProcessStop("lillahi SSOT category drift")

    votes = {name: index_unique(read_rows(path), "packet_id", name)
             for name, path in VOTE_PATHS.items()}
    return {
        "dh_verdicts": dh,
        "lillahi_verdicts": lillahi,
        "votes": votes,
        "lane_hashes": {name: "sha256:" + sha256_file(path) for name, path in lane_paths.items()},
    }


def _prior_review(loc: str, rows: list[dict[str, Any]], fact_type: str) -> dict[str, Any]:
    matches = [
        row for row in current_facts(rows).values()
        if row.get("fact_type") == fact_type
        and row.get("certification_state") == "review_required"
        and row.get("subject_identity", {}).get("loc") == loc
    ]
    if len(matches) != 1:
        raise DueProcessStop(f"{loc}: expected one current {fact_type} review fact, found {len(matches)}")
    return matches[0]


def _evidence(prior: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    matches = [item for item in prior["evidence"] if item.get("evidence_id") == evidence_id]
    if len(matches) != 1:
        raise DueProcessStop(f"{prior['subject_identity']['loc']}: missing unique {evidence_id}")
    return copy.deepcopy(matches[0])


def _deterministic_evidence(verdict: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": "deterministic-winning-host",
        "type": "deterministic_derivation",
        "detail": (
            f"winning host {check['winning_host_entry_id']} passed by {check['method']}; "
            f"documented={check['documented_form_overlap']}; roots={check['derived_root_overlap']}; "
            f"noun_convention={check['noun_convention_overlap']}"
        ),
        "source_address": f"qamus/data/current/entries.jsonl#id={verdict['chosen_host_id']}",
    }


def _t3_evidence(verdict: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": "tier3-authoritative",
        "type": "two_vote",
        "detail": verdict["evidence"],
        "source_address": (
            "lane-input:dh-t3-verdicts.jsonl#packet_id=" + verdict["packet_id"]
        ),
    }


def _provenance(input_hashes: dict[str, str]) -> dict[str, Any]:
    return {
        "actor": ACTOR,
        "method": METHOD,
        "created_at": CREATED_AT,
        "input_hashes": input_hashes,
    }


def _reject(prior: dict[str, Any], reason: str, input_hashes: dict[str, str]) -> dict[str, Any]:
    row = copy.deepcopy(prior)
    row["certification_state"] = "rejected"
    row["supersedes"] = prior["fact_id"]
    row["provenance"] = _provenance(input_hashes)
    row["exceptions"] = list(row.get("exceptions") or []) + [{
        "type": "authoritative_tier_due_process_retirement",
        "reason": reason,
    }]
    fact_ledger.validate_row(row, previous=prior)
    return row


def _annotate(prior: dict[str, Any], *, annotation: str, verdict: dict[str, Any],
              input_hashes: dict[str, str], deterministic: dict[str, Any] | None = None) -> dict[str, Any]:
    row = copy.deepcopy(prior)
    row["certification_state"] = "review_required"
    row["supersedes"] = prior["fact_id"]
    row["provenance"] = _provenance(input_hashes)
    item = {
        "type": "tier_due_process_annotation",
        "annotation": annotation,
        "evidence_reference": "lane-input:dh-t3-verdicts.jsonl#packet_id=" + verdict["packet_id"],
        "verdict_evidence": verdict["evidence"],
    }
    if deterministic is not None:
        item["deterministic_check"] = deterministic
    row["exceptions"] = list(row.get("exceptions") or []) + [item]
    fact_ledger.validate_row(row, previous=prior)
    return row


def _new_lifecycle(prior: dict[str, Any], *, value: Any, alternatives: list[dict[str, Any]],
                   candidate_evidence: list[dict[str, Any]], winning_evidence: dict[str, Any],
                   winning_voter: str, authoritative_evidence: dict[str, Any],
                   authoritative_voter: str, exceptions: list[dict[str, Any]],
                   input_hashes: dict[str, str]) -> list[dict[str, Any]]:
    candidate = copy.deepcopy(prior)
    candidate["candidate_or_value"] = {
        "value": copy.deepcopy(value),
        "competing_alternatives": copy.deepcopy(alternatives),
        "semantic_tie": False,
    }
    candidate["evidence"] = copy.deepcopy(candidate_evidence)
    candidate["review_votes"] = []
    candidate["certification_state"] = "candidate"
    candidate["provenance"] = _provenance(input_hashes)
    candidate["exceptions"] = copy.deepcopy(exceptions)
    candidate["supersedes"] = None
    candidate["created_from"] = prior["fact_id"]
    candidate["fact_id"] = fact_ledger.compute_fact_id(candidate)
    if candidate["fact_id"] == prior["fact_id"]:
        raise DueProcessStop(f"{prior['subject_identity']['loc']}: replacement did not change fact identity")
    fact_ledger.validate_row(candidate, previous=None)

    review = copy.deepcopy(candidate)
    review["certification_state"] = "review_required"
    review["supersedes"] = candidate["fact_id"]
    review["evidence"] = list(candidate["evidence"]) + [copy.deepcopy(winning_evidence)]
    review["review_votes"] = [{
        "voter_id": winning_voter,
        "vote": "approve",
        "evidence_ref": winning_evidence["evidence_id"],
        "independent": True,
    }]
    fact_ledger.validate_row(review, previous=candidate)

    certified = copy.deepcopy(review)
    certified["certification_state"] = "certified"
    certified["supersedes"] = candidate["fact_id"]
    certified["evidence"] = list(review["evidence"]) + [copy.deepcopy(authoritative_evidence)]
    certified["review_votes"] = list(review["review_votes"]) + [{
        "voter_id": authoritative_voter,
        "vote": "approve",
        "evidence_ref": authoritative_evidence["evidence_id"],
        "independent": True,
    }]
    fact_ledger.validate_row(certified, previous=review)
    return [candidate, review, certified]


def _certify_existing_host(prior: dict[str, Any], verdict: dict[str, Any], check: dict[str, Any],
                           winner_side: str, input_hashes: dict[str, str]) -> dict[str, Any]:
    if prior["candidate_or_value"]["value"] != verdict["chosen_host_id"]:
        raise DueProcessStop(f"{verdict['canonical_location']}: existing fact value is not winning host")
    winner_evidence_id = "vote-A" if winner_side == "a" else "vote-B"
    losing_value = verdict["host_b" if winner_side == "a" else "host_a"]["id"]
    row = copy.deepcopy(prior)
    row["candidate_or_value"] = {
        "value": verdict["chosen_host_id"],
        "competing_alternatives": [{
            "value": losing_value,
            "reason": "losing engine vote preserved in the superseded review-required history",
        }],
        "semantic_tie": False,
    }
    row["certification_state"] = "certified"
    row["supersedes"] = prior["fact_id"]
    row["provenance"] = _provenance(input_hashes)
    row["evidence"] = [
        _deterministic_evidence(verdict, check),
        _evidence(prior, winner_evidence_id),
        _t3_evidence(verdict),
    ]
    row["review_votes"] = [
        {
            "voter_id": "reviewer-A:Opus" if winner_side == "a" else "reviewer-B:Codex",
            "vote": "approve",
            "evidence_ref": winner_evidence_id,
            "independent": True,
        },
        {
            "voter_id": "tier3:authoritative",
            "vote": "approve",
            "evidence_ref": "tier3-authoritative",
            "independent": True,
        },
    ]
    row["exceptions"] = list(row.get("exceptions") or []) + [{
        "type": "authoritative_t3_due_process",
        "winning_engine": winner_side.upper(),
        "losing_vote_preserved_in_history": True,
    }]
    fact_ledger.validate_row(row, previous=prior)
    return row


def _winning_vote_gate(verdict: dict[str, Any], votes: dict[str, dict[str, dict[str, Any]]]) -> tuple[str, dict[str, Any]]:
    side = "a" if verdict["verdict"] == "t3_host_a" else "b"
    vote = votes[f"rebind_{side}"].get(verdict["packet_id"])
    if vote is None:
        raise DueProcessStop(f"{verdict['packet_id']}: missing winning-engine vote")
    if vote.get("decision") != "rebind_to_host" or vote.get("host_entry_id") != verdict["chosen_host_id"]:
        raise DueProcessStop(f"{verdict['packet_id']}: winning-engine vote disagrees with T3 verdict")
    return side, vote


def _process_rebind(base_rows: list[dict[str, Any]], inputs: dict[str, Any], morphology: Morphology,
                    surfaces: dict[str, str], input_hashes: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter]:
    rows = list(base_rows)
    report_rows: list[dict[str, Any]] = []
    counts: Counter = Counter()
    for verdict in sorted(inputs["dh_verdicts"], key=lambda row: tuple(map(int, row["canonical_location"].split(":")))):
        loc = verdict["canonical_location"]
        prior = _prior_review(loc, rows, "governing_entry_analysis")
        counts[verdict["verdict"]] += 1
        if verdict["verdict"] == "t4_packet":
            annotated = _annotate(prior, annotation="t4_packet", verdict=verdict, input_hashes=input_hashes)
            rows.append(annotated)
            report_rows.append({
                "packet_id": verdict["packet_id"], "canonical_location": loc,
                "verdict": verdict["verdict"], "disposition": "review_required:t4_packet",
                "prior_fact_id": prior["fact_id"], "current_fact_id": prior["fact_id"],
                "evidence_reference": annotated["exceptions"][-1]["evidence_reference"],
            })
            continue

        side, _vote = _winning_vote_gate(verdict, inputs["votes"])
        check = deterministic_winning_host_check(verdict, morphology, surfaces[loc])
        if not check["passed"]:
            counts["deterministic_fail"] += 1
            annotated = _annotate(
                prior, annotation="t4_packet_deterministic_fail", verdict=verdict,
                input_hashes=input_hashes, deterministic=check,
            )
            rows.append(annotated)
            report_rows.append({
                "packet_id": verdict["packet_id"], "canonical_location": loc,
                "verdict": verdict["verdict"], "disposition": "review_required:t4_packet_deterministic_fail",
                "prior_fact_id": prior["fact_id"], "current_fact_id": prior["fact_id"],
                "deterministic_check": check,
            })
            continue

        counts["deterministic_pass"] += 1
        if prior["candidate_or_value"]["value"] == verdict["chosen_host_id"]:
            certified = _certify_existing_host(prior, verdict, check, side, input_hashes)
            rows.append(certified)
            new_fact_id = certified["fact_id"]
            lifecycle = "review_required->certified"
        else:
            rejected = _reject(
                prior, "winning host changes after deterministic + engine + T3 agreement", input_hashes
            )
            winner_evidence_id = "vote-A" if side == "a" else "vote-B"
            losing = verdict["host_b" if side == "a" else "host_a"]["id"]
            lifecycle_rows = _new_lifecycle(
                prior,
                value=verdict["chosen_host_id"],
                alternatives=[{"value": losing, "reason": "losing engine vote preserved in rejected history"}],
                candidate_evidence=[_deterministic_evidence(verdict, check)],
                winning_evidence=_evidence(prior, winner_evidence_id),
                winning_voter="reviewer-A:Opus" if side == "a" else "reviewer-B:Codex",
                authoritative_evidence=_t3_evidence(verdict),
                authoritative_voter="tier3:authoritative",
                exceptions=[{
                    "type": "authoritative_t3_due_process",
                    "winning_engine": side.upper(),
                    "losing_vote_preserved_in_rejected_history": True,
                }],
                input_hashes=input_hashes,
            )
            rows.extend([rejected, *lifecycle_rows])
            new_fact_id = lifecycle_rows[-1]["fact_id"]
            lifecycle = "review_required->rejected + candidate->review_required->certified"
        report_rows.append({
            "packet_id": verdict["packet_id"], "canonical_location": loc,
            "verdict": verdict["verdict"], "disposition": "certified",
            "winning_host_entry_id": verdict["chosen_host_id"], "winning_engine": side.upper(),
            "prior_fact_id": prior["fact_id"], "current_fact_id": new_fact_id,
            "lifecycle": lifecycle, "deterministic_check": check,
        })
    validate_ledger(rows)
    return rows, report_rows, counts


def _process_lillahi(base_rows: list[dict[str, Any]], inputs: dict[str, Any],
                     input_hashes: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = list(base_rows)
    report_rows: list[dict[str, Any]] = []
    for verdict in sorted(inputs["lillahi_verdicts"], key=lambda row: tuple(map(int, row["canonical_location"].split(":")))):
        loc = verdict["canonical_location"]
        prior = _prior_review(loc, rows, "function_word_analysis")
        vote_a = inputs["votes"]["funcword_a"].get(verdict["packet_id"])
        vote_b = inputs["votes"]["funcword_b"].get(verdict["packet_id"])
        if vote_a is None or vote_b is None:
            raise DueProcessStop(f"{verdict['packet_id']}: missing original function-word vote")
        a_category = vote_a.get("corrected_category") or vote_a.get("taxonomy_category")
        if a_category != verdict["a_category"] or vote_a.get("decision") != "reclassify":
            raise DueProcessStop(f"{verdict['packet_id']}: reviewer A framing drift")
        if (vote_b.get("taxonomy_category") != verdict["b_category"]
                or verdict["b_category"] != "preposition"
                or vote_b.get("decision") != "function_confirmed"):
            raise DueProcessStop(f"{verdict['packet_id']}: reviewer B/SSOT framing drift")

        rejected = _reject(prior, "T2 SSOT normalizes lillahi taxonomy to preposition", input_hashes)
        ssot_evidence = {
            "evidence_id": "tier2-ssot-authoritative",
            "type": "two_vote",
            "detail": verdict["ssot_citation"],
            "source_address": "tools/build_funcword_two_vote_packets.py#L184-L192,L546-L554",
        }
        lifecycle_rows = _new_lifecycle(
            prior,
            value={
                "taxonomy_category": "preposition",
                "governor_note": vote_b["governor_note"],
            },
            alternatives=copy.deepcopy(prior["candidate_or_value"]["competing_alternatives"]),
            candidate_evidence=[ssot_evidence],
            winning_evidence=_evidence(prior, "vote-B"),
            winning_voter="reviewer-B:Codex",
            authoritative_evidence=ssot_evidence,
            authoritative_voter="tier2:ssot-authoritative",
            exceptions=[{
                "type": "tier2_taxonomy_normalization",
                "annotation": "t2_normalized",
                "t2_normalized": True,
                "ssot_citation": verdict["ssot_citation"],
                "original_framings_preserved_in_rejected_history": True,
            }],
            input_hashes=input_hashes,
        )
        # Candidate already has the SSOT evidence; avoid a duplicate evidence_id at certification.
        lifecycle_rows[2]["evidence"] = [
            lifecycle_rows[0]["evidence"][0],
            lifecycle_rows[1]["evidence"][-1],
        ]
        fact_ledger.validate_row(lifecycle_rows[2], previous=lifecycle_rows[1])
        rows.extend([rejected, *lifecycle_rows])
        report_rows.append({
            "packet_id": verdict["packet_id"], "canonical_location": loc,
            "verdict": verdict["verdict"], "disposition": "certified:preposition",
            "prior_fact_id": prior["fact_id"], "current_fact_id": lifecycle_rows[-1]["fact_id"],
            "ssot_citation": verdict["ssot_citation"],
            "lifecycle": "review_required->rejected + candidate->review_required->certified",
        })
    validate_ledger(rows)
    return rows, report_rows


@dataclass
class BuildResult:
    rebind_rows: list[dict[str, Any]]
    funcword_rows: list[dict[str, Any]]
    report: dict[str, Any]

    def output_bytes(self) -> dict[str, bytes]:
        return {
            REBINDS.relative_to(ROOT).as_posix(): ledger_bytes(self.rebind_rows),
            FUNCWORDS.relative_to(ROOT).as_posix(): ledger_bytes(self.funcword_rows),
            REPORT.relative_to(ROOT).as_posix(): canonical_bytes(self.report, pretty=True),
        }


def _load_applied(inputs: dict[str, Any]) -> BuildResult:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    rebind = read_rows(REBINDS)
    funcword = read_rows(FUNCWORDS)
    expected_lane = inputs["lane_hashes"]
    checks = {
        "lane input hashes": report.get("input_hashes", {}).get("lane_inputs") == expected_lane,
        "rebind output sha": report.get("outputs", {}).get("rebind_cert_sha256") == "sha256:" + sha256_file(REBINDS),
        "funcword output sha": report.get("outputs", {}).get("funcword_cert_sha256") == "sha256:" + sha256_file(FUNCWORDS),
        "protected surfaces": report.get("protected_surface_assertion", {}).get("after") == protected_hashes(),
        "rebind states": report["ledger_arithmetic"]["rebind_cert"]["current_state_counts_after"] == state_counts(rebind),
        "funcword states": report["ledger_arithmetic"]["funcword_cert"]["current_state_counts_after"] == state_counts(funcword),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise DueProcessStop(f"installed due-process readback failed: {failed}")
    validate_ledger(rebind)
    validate_ledger(funcword)
    return BuildResult(rebind, funcword, report)


def build(inputs_dir: Path) -> BuildResult:
    inputs = load_inputs(inputs_dir)
    if REPORT.is_file():
        return _load_applied(inputs)

    for relative, expected in BASELINE_SHA256.items():
        actual = sha256_file(ROOT / relative)
        if actual != expected:
            raise DueProcessStop(f"baseline sha drift for {relative}: {actual} != {expected}")

    before_protected = protected_hashes()
    rebind_before = read_rows(REBINDS)
    funcword_before = read_rows(FUNCWORDS)
    input_hashes = {
        **_baseline_input_hashes(),
        "dh_t3_verdicts": inputs["lane_hashes"]["dh-t3-verdicts.jsonl"],
        "lillahi_t2_verdicts": inputs["lane_hashes"]["lillahi-t2-verdicts.jsonl"],
    }
    morphology = load_morphology()
    surfaces = load_location_surfaces()
    rebind_after, rebind_report, counts = _process_rebind(
        rebind_before, inputs, morphology, surfaces, input_hashes
    )
    funcword_after, funcword_report = _process_lillahi(funcword_before, inputs, input_hashes)
    after_protected = protected_hashes()
    if before_protected != after_protected:
        raise DueProcessStop("protected queue/crosswalk/whitelist/shadow surface changed during build")

    gate_counts = {
        "t3_host_a": counts["t3_host_a"],
        "t3_host_b": counts["t3_host_b"],
        "t4_packet": counts["t4_packet"],
        "deterministic_pass": counts["deterministic_pass"],
        "deterministic_fail": counts["deterministic_fail"],
        "lillahi_t2": len(funcword_report),
    }
    report = {
        "schema": "qamus.tier_due_process_report.v1",
        "generator": ACTOR,
        "method": METHOD,
        "created_at": CREATED_AT,
        "input_hashes": {
            "lane_inputs": inputs["lane_hashes"],
            "committed_inputs": input_hashes,
        },
        "gate_counts": gate_counts,
        "ledger_arithmetic": {
            "rebind_cert": {
                "physical_rows": [len(rebind_before), len(rebind_after)],
                "append_delta": len(rebind_after) - len(rebind_before),
                "current_state_counts_before": state_counts(rebind_before),
                "current_state_counts_after": state_counts(rebind_after),
            },
            "funcword_cert": {
                "physical_rows": [len(funcword_before), len(funcword_after)],
                "append_delta": len(funcword_after) - len(funcword_before),
                "current_state_counts_before": state_counts(funcword_before),
                "current_state_counts_after": state_counts(funcword_after),
            },
        },
        "protected_surface_assertion": {
            "before": before_protected,
            "after": after_protected,
            "observed": "byte_stable",
            "no_queue_crosswalk_whitelist_change": True,
        },
        "constant_hunks": [],
        "check_regressions_edited": False,
        "rows": rebind_report + funcword_report,
        "outputs": {
            "rebind_cert_sha256": "sha256:" + sha256_bytes(ledger_bytes(rebind_after)),
            "funcword_cert_sha256": "sha256:" + sha256_bytes(ledger_bytes(funcword_after)),
        },
    }
    return BuildResult(rebind_after, funcword_after, report)


def write_result(result: BuildResult) -> None:
    before = protected_hashes()
    outputs = result.output_bytes()
    for relative, payload in outputs.items():
        path = ROOT / relative
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
    after = protected_hashes()
    if before != after:
        raise DueProcessStop("protected queue/crosswalk/whitelist/shadow surface changed during write")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-dir", type=Path, default=ROOT / ".lane-inputs")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        first = build(args.inputs_dir)
        second = build(args.inputs_dir)
        if first.output_bytes() != second.output_bytes():
            raise DueProcessStop("deterministic double-run mismatch")
        if args.write:
            write_result(first)
            readback = build(args.inputs_dir)
            if readback.output_bytes() != first.output_bytes():
                raise DueProcessStop("post-write readback mismatch")
        print(json.dumps({
            "status": "PASS",
            "write": args.write,
            "gate_counts": first.report["gate_counts"],
            "ledger_arithmetic": first.report["ledger_arithmetic"],
            "protected_surface": first.report["protected_surface_assertion"]["observed"],
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, DueProcessStop, fact_ledger.ValidationError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
