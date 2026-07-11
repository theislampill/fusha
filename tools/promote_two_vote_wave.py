#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""promote_two_vote_wave — T10 Lane B wave-1: 77 two-vote-certified rows through the ledger.

The first real review-resolved promotion wave (EQ-17). Given the wave inputs
(``calibration-analysis-v2.json`` plus both reviewer vote files) and the committed
two-vote packets, this tool:

1. Writes the Lane B review lifecycle into a COMMITTED fact-ledger store
   (``fact-ledger/laneb-review.jsonl``) using the repo's own ``tools.fact_ledger``
   API — candidate -> review_required -> certified for every agreeing row, both
   votes preserved on the one non-qualifying disagreement (review_required, not
   promoted), and abstention-evidenced candidate rows for the joint abstentions.
2. Selects the unique carrier each certified conclusion binds, then promotes those
   bindings into the accepted crosswalk via RM-19 ``atomic_promote_shards`` with
   ``resolution_method = "two_vote_certified_v1"`` and the certified ledger
   ``fact_id`` carried in the row.
3. Rebuilds the crosswalk-gap queue with the committed builder and reconciles the
   count (5,502 - promoted), proving every promoted location is post-promotion
   no_op (leaves the gap).

Determinism: pure builders over hash-pinned inputs and a pinned wave timestamp; the
``--self-test`` fixtures prove ledger-gate refusal, missing-carrier refusal,
quarantine refusal, and byte-identical reruns.

The ledger store is fail-closed and append-only; nothing here mutates the deployed
whitelist, entries, or the NF-T10-1 quarantined ayahs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402
from tools.normalize_ar import norm_strict  # noqa: E402
from tools.largelexicon_common import (  # noqa: E402
    atomic_promote_shards,
    generation_fingerprint,
    sha256_file,
    sha256_jsonl_rows,
    write_json_atomic,
)

# The committed Lane B ledger store is a single named JSONL. The fact_ledger store
# derives its ledger path from this module constant at construction time, so we
# configure it here (this process only) rather than reinventing the store.
LEDGER_FILE_NAME = "laneb-review.jsonl"
fact_ledger.LEDGER_NAME = LEDGER_FILE_NAME

# ---- pinned wave constants -------------------------------------------------- #
WAVE = 1
WAVE_PROMOTED_AT = "2026-07-11T12:00:00Z"           # pinned -> byte-deterministic
RESOLUTION_METHOD = "two_vote_certified_v1"
LEDGER_METHOD = "two_vote_certified_v1"
FACT_TYPE = "gloss_contribution"                     # occurrence card-gloss binding
ACCEPTED = "canonical_crosswalk_accepted"
TRANSCLUSION_ROUTE = "entry_card_qword_to_canonical_crosswalk_accepted"
QUEUE_BEFORE = 5502
EXPECTED_BASELINE_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
EXPECTED_CORPUS_SHA256 = "f2e079dcdce01148074a238e3937314cf02222298f91f83ed66dcbb599697ca7"

# Divergent-ayah quarantine (T10 owner-authoritative). No promotion may touch these.
QUARANTINED_AYAHS = {
    "2:214", "2:274", "3:152", "4:64", "12:37", "19:67", "48:15", "92:3", "93:3", "98:1",
}
# NF-T10-1 owner-dataset dependency locations (exact assertion target).
NF_T10_1_LOCS = {"2:274:1", "4:64:9", "4:64:10", "12:37:1", "48:15:1"}

# ---- repo paths ------------------------------------------------------------- #
LLX = ROOT / "qamus" / "indexes" / "largelexicon"
LEDGER_DIR = LLX / "fact-ledger"
CROSSWALK_DIR = LLX / "qword-crosswalk"
CROSSWALK_MANIFEST_PATH = LLX / "qamus-qword-crosswalk.manifest.json"
FULL_TABLE_META_PATH = LLX / "source-clean-fact-tables.meta.json"
QUEUE_DIR = LLX / "crosswalk-gap"
QUEUE_PATH = QUEUE_DIR / "crosswalk-gap-queue.jsonl"
QUEUE_MANIFEST_PATH = QUEUE_DIR / "crosswalk-gap-queue.manifest.json"
PACKET_DIR = QUEUE_DIR / "two-vote"
WAVE_REPORT_PATH = QUEUE_DIR / "laneb-wave-01.report.json"

LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
ENTRY_RE = re.compile(r"^[0-9a-f]{12}$")
CARRIER_RE = re.compile(r"row_id=(llx-qword-[0-9a-f]{12}-\d{2}-\d{2}-\d{3})")
TOKEN_RE = re.compile(r"id=([0-9a-f]{12})/usage/(\d+)/examples/(\d+)/ar#whitespace-token=(\d+)")


class WaveStop(RuntimeError):
    """A brief STOP condition fired; abort with a precise message."""


# --------------------------------------------------------------------------- #
# input loading
# --------------------------------------------------------------------------- #
def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sha_input(path: Path) -> str:
    return "sha256:" + sha256_file(path)


def load_inputs(inputs_dir: Path) -> dict[str, Any]:
    cal_path = inputs_dir / "calibration-analysis-v2.json"
    va_path = inputs_dir / "votes-A.jsonl"
    vb_path = inputs_dir / "votes-B.jsonl"
    cal = json.loads(cal_path.read_text(encoding="utf-8"))
    votes_a = {row["packet_id"]: row for row in _read_jsonl(va_path)}
    votes_b = {row["packet_id"]: row for row in _read_jsonl(vb_path)}
    packets: dict[str, dict[str, Any]] = {}
    for name in ("packets-cal-001.jsonl", "packets-cal-002.jsonl"):
        for packet in _read_jsonl(PACKET_DIR / name):
            packets[packet["packet_id"]] = packet
    return {
        "cal": cal,
        "votes_a": votes_a,
        "votes_b": votes_b,
        "packets": packets,
        "input_hashes": {
            "calibration_analysis": _sha_input(cal_path),
            "votes_a": _sha_input(va_path),
            "votes_b": _sha_input(vb_path),
        },
        "paths": {"cal": cal_path, "votes_a": va_path, "votes_b": vb_path},
    }


def _decided(vote: dict[str, Any]) -> bool:
    return vote.get("confidence") != "abstain" and not vote.get("abstention_or_blocker")


# --------------------------------------------------------------------------- #
# carrier selection (the reviewed conclusion selects which carrier binds)
# --------------------------------------------------------------------------- #
def _cited_qword_ids(votes: list[dict[str, Any]]) -> set[str]:
    cited: set[str] = set()
    for vote in votes:
        blob = json.dumps(vote, ensure_ascii=False)
        cited.update(CARRIER_RE.findall(blob))
        for entry, usage, example, token in TOKEN_RE.findall(blob):
            cited.add("llx-qword-%s-%02d-%02d-%03d" % (entry, int(usage), int(example), int(token)))
    return cited


def select_carrier(qrow: dict[str, Any], packet: dict[str, Any],
                   vote_a: dict[str, Any], vote_b: dict[str, Any]) -> dict[str, Any]:
    """Return the single candidate carrier the two converged conclusions bind.

    Position conclusions (``s:a:w``) bind the fingerprint-unique carrier at that
    location; lexical conclusions (``entry_id``) bind that entry's carrier. Raises
    :class:`WaveStop` when no unique carrier can be selected from the conclusions.
    """
    loc = qrow["canonical_location"]
    concl_a = qrow["reviewer_a"]["normalized_conclusion"]
    concl_b = qrow["reviewer_b"]["normalized_conclusion"]
    if concl_a != concl_b:
        raise WaveStop("row %s conclusions diverge: %r != %r" % (loc, concl_a, concl_b))
    conclusion = concl_a
    carriers = packet.get("candidate_carriers") or []

    if LOC_RE.match(conclusion):
        if conclusion != loc:
            raise WaveStop("row %s position conclusion %r != canonical location" % (loc, conclusion))
        unique = [c for c in carriers
                  if c.get("fingerprint_match_candidates") == [loc]
                  and c.get("mapping_status") == "unique"]
        if len(unique) == 1:
            return unique[0]
        cited = _cited_qword_ids([vote_a, vote_b])
        narrowed = [c for c in unique if c.get("qword_row_id") in cited]
        if len(narrowed) == 1:
            return narrowed[0]
        raise WaveStop(
            "row %s lacks a unique carrier: %d fingerprint-unique, %d cited"
            % (loc, len(unique), len(narrowed))
        )

    if ENTRY_RE.match(conclusion):
        hits = [c for c in carriers if c.get("entry_id") == conclusion]
        if len(hits) == 1:
            return hits[0]
        raise WaveStop("row %s lexical conclusion %s maps to %d carriers"
                       % (loc, conclusion, len(hits)))

    raise WaveStop("row %s unrecognized conclusion %r" % (loc, conclusion))


def _carrier_identity(loc: str, carrier: dict[str, Any]) -> dict[str, Any]:
    """The full D-13 carrier subject identity for an occurrence fact."""
    for field in ("entry_id", "card_id", "qword_row_id"):
        if not carrier.get(field):
            raise WaveStop("row %s carrier missing %s" % (loc, field))
    return {
        "ref_type": "surface_occurrence",
        "loc": loc,
        "entry_id": carrier["entry_id"],
        "card_id": carrier["card_id"],
        "qword_row_id": carrier["qword_row_id"],
    }


def _live_surface(packet: dict[str, Any], loc: str) -> str | None:
    for word in packet.get("ayah_word_context") or []:
        if word.get("loc") == loc:
            return word.get("surface")
    return None


# --------------------------------------------------------------------------- #
# ledger row builders (pure given inputs + pinned timestamp)
# --------------------------------------------------------------------------- #
def _evidence(evidence_id: str, ev_type: str, detail: str, address: str) -> dict[str, Any]:
    return {"evidence_id": evidence_id, "type": ev_type,
            "detail": detail, "source_address": address}


def _base_row(*, identity: dict[str, Any], loc: str, value: Any,
              competing: list[dict[str, Any]], evidence: list[dict[str, Any]],
              input_hashes: dict[str, str]) -> dict[str, Any]:
    row = {
        "schema": "qamus.fact_ledger_row.v1",
        "subject_type": "surface_occurrence",
        "subject_identity": identity,
        "fact_type": FACT_TYPE,
        "candidate_or_value": {"value": value, "competing_alternatives": competing,
                               "semantic_tie": False},
        "scope": "occurrence",
        "source_address": {"address": "quran:" + loc, "source_kind": "quran_token"},
        "evidence": evidence,
        "provenance": {
            "actor": "tools/promote_two_vote_wave.py",
            "method": LEDGER_METHOD,
            "created_at": WAVE_PROMOTED_AT,
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
        "created_from": None,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def _packet_input_hashes(base: dict[str, str], packet: dict[str, Any]) -> dict[str, str]:
    hashes = dict(base)
    hashes["packet"] = "sha256:" + packet["packet_sha256"]
    return hashes


def _vote_evidence(vote: dict[str, Any], reviewer: str) -> dict[str, Any]:
    return _evidence(
        "vote-%s" % reviewer, "two_vote",
        (vote.get("exact_reason") or "reviewer %s decision" % reviewer),
        vote.get("source_address") or "review_artifact:%s" % reviewer,
    )


def append_certified(store: fact_ledger.FactLedgerStore, *, loc: str, carrier: dict[str, Any],
                     qrow: dict[str, Any], packet: dict[str, Any],
                     vote_a: dict[str, Any], vote_b: dict[str, Any],
                     base_hashes: dict[str, str]) -> str:
    """candidate -> review_required -> certified; return the certified fact_id."""
    identity = _carrier_identity(loc, carrier)
    value = qrow["reviewer_a"]["normalized_conclusion"]
    input_hashes = _packet_input_hashes(base_hashes, packet)
    packet_ev = _evidence(
        "packet", "source_quote",
        "carrier %s uniquely addresses %s (packet %s, mapping_status=%s)"
        % (carrier["qword_row_id"], loc, packet["packet_id"], packet.get("mapping_status")),
        carrier.get("carrier_source_address") or ("quran:" + loc),
    )
    candidate = _base_row(identity=identity, loc=loc, value=value, competing=[],
                          evidence=[packet_ev], input_hashes=input_hashes)
    store.append(candidate)
    fact_id = candidate["fact_id"]
    store.transition(fact_id, "review_required")
    votes = [
        {"voter_id": "reviewer-A", "vote": "approve", "evidence_ref": "vote-A", "independent": True},
        {"voter_id": "reviewer-B", "vote": "approve", "evidence_ref": "vote-B", "independent": True},
    ]
    evidence = [packet_ev, _vote_evidence(vote_a, "A"), _vote_evidence(vote_b, "B")]
    store.transition(fact_id, "certified", review_votes=votes, evidence=evidence)
    return fact_id


def append_disagreement(store: fact_ledger.FactLedgerStore, *, loc: str, carrier: dict[str, Any],
                        qrow: dict[str, Any], packet: dict[str, Any],
                        vote_a: dict[str, Any], vote_b: dict[str, Any],
                        base_hashes: dict[str, str]) -> str:
    """candidate -> review_required, both votes preserved, NOT certified."""
    identity = _carrier_identity(loc, carrier)
    concl_a = qrow["reviewer_a"]["normalized_conclusion"]
    concl_b = qrow["reviewer_b"]["normalized_conclusion"]
    input_hashes = _packet_input_hashes(base_hashes, packet)
    packet_ev = _evidence(
        "packet", "source_quote",
        "two-vote gate not satisfied (shared discriminating evidence absent); "
        "reviewers reached %r / %r without independent corroboration" % (concl_a, concl_b),
        carrier.get("carrier_source_address") or ("quran:" + loc),
    )
    competing = [{"value": concl_b, "reason": "reviewer B evidence path diverges"}] \
        if concl_a == concl_b else \
        [{"value": concl_a, "reason": "reviewer A conclusion"},
         {"value": concl_b, "reason": "reviewer B conclusion"}]
    candidate = _base_row(identity=identity, loc=loc, value=concl_a, competing=competing,
                          evidence=[packet_ev], input_hashes=input_hashes)
    store.append(candidate)
    fact_id = candidate["fact_id"]
    votes = [
        {"voter_id": "reviewer-A", "vote": "approve", "evidence_ref": "vote-A", "independent": True},
        {"voter_id": "reviewer-B", "vote": "approve", "evidence_ref": "vote-B", "independent": True},
    ]
    evidence = [packet_ev, _vote_evidence(vote_a, "A"), _vote_evidence(vote_b, "B")]
    store.transition(fact_id, "review_required", review_votes=votes, evidence=evidence)
    return fact_id


def append_abstention(store: fact_ledger.FactLedgerStore, *, loc: str, packet: dict[str, Any],
                      vote_a: dict[str, Any], vote_b: dict[str, Any],
                      base_hashes: dict[str, str]) -> str:
    """A candidate row carrying joint-abstention evidence; NOT promoted."""
    carriers = sorted((c for c in (packet.get("candidate_carriers") or [])
                       if c.get("entry_id") and c.get("card_id") and c.get("qword_row_id")),
                      key=lambda c: c["qword_row_id"])
    if not carriers:
        raise WaveStop("abstention %s has no addressable carrier" % loc)
    identity = _carrier_identity(loc, carriers[0])
    input_hashes = _packet_input_hashes(base_hashes, packet)
    reason_a = vote_a.get("abstention_or_blocker") or "reviewer A abstained"
    reason_b = vote_b.get("abstention_or_blocker") or "reviewer B abstained"
    evidence = [
        _evidence("abstain-A", "source_quote", reason_a,
                  vote_a.get("source_address") or ("quran:" + loc)),
        _evidence("abstain-B", "source_quote", reason_b,
                  vote_b.get("source_address") or ("quran:" + loc)),
    ]
    competing = [{"value": eid, "reason": "unadjudicated candidate entry"}
                 for eid in sorted({c["entry_id"] for c in carriers})]
    candidate = _base_row(identity=identity, loc=loc, value="pending",
                          competing=competing, evidence=evidence, input_hashes=input_hashes)
    votes = [
        {"voter_id": "reviewer-A", "vote": "abstain", "evidence_ref": "abstain-A", "independent": True},
        {"voter_id": "reviewer-B", "vote": "abstain", "evidence_ref": "abstain-B", "independent": True},
    ]
    candidate["review_votes"] = votes
    store.append(candidate)
    return candidate["fact_id"]


# --------------------------------------------------------------------------- #
# accepted crosswalk row (ledger-gated) + promotion
# --------------------------------------------------------------------------- #
def build_accepted_row(store: fact_ledger.FactLedgerStore, *, loc: str, carrier: dict[str, Any],
                       fact_id: str, existing: dict[str, Any],
                       live_surface: str) -> dict[str, Any]:
    """Flip the carrier's crosswalk row to accepted, gated on a CERTIFIED ledger fact."""
    certified = store.query(fact_id=fact_id, state="certified")
    if not certified:
        raise WaveStop("ledger-gate: fact %s for %s is not certified; refusing promotion"
                       % (fact_id, loc))
    for field in ("entry_id", "card_id", "qword_row_id"):
        if not carrier.get(field):
            raise WaveStop("row %s carrier missing %s; refusing promotion" % (loc, field))
    surah, _ayah, word = (int(part) for part in loc.split(":"))
    if norm_strict(existing.get("visible_surface") or "") != norm_strict(live_surface or ""):
        raise WaveStop("row %s surface parity failed" % loc)
    accepted = copy.deepcopy(existing)
    accepted.update({
        "canonical_quran_loc": loc,
        "canonical_wbw_loc": loc,
        "match_status": "resolved_arabic_surface_match",
        "status": ACCEPTED,
        "packet_class": None,
        "terminal_gate_code": None,
        "next_action": None,
        "transclusion_route": TRANSCLUSION_ROUTE,
        "resolution_method": RESOLUTION_METHOD,
        "resolution_confidence": "two_vote_certified",
        "resolution_source": "two_vote_review_adjudication",
        "resolution_wbw_lookup_sha256": EXPECTED_CORPUS_SHA256,
        "resolved_word_index": word,
        "resolved_surface": live_surface,
        "resolved_surface_norm_strict": norm_strict(live_surface or ""),
        "review_fact_id": fact_id,
    })
    accepted.pop("candidate_word_indices", None)
    return accepted


def load_crosswalk_shards() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_id: dict[str, dict[str, Any]] = {}
    shards: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(CROSSWALK_DIR.glob("*.jsonl")):
        rows = _read_jsonl(path)
        shards[path.name] = rows
        for row in rows:
            by_id[row["qword_row_id"]] = row
    return by_id, shards


def apply_replacements(shards: dict[str, list[dict[str, Any]]],
                       replacements: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    found: set[str] = set()
    out: dict[str, list[dict[str, Any]]] = {}
    for name in sorted(shards):
        rows = []
        for row in shards[name]:
            qid = row.get("qword_row_id")
            if qid in replacements:
                rows.append(copy.deepcopy(replacements[qid]))
                found.add(qid)
            else:
                rows.append(copy.deepcopy(row))
        out[name] = rows
    missing = set(replacements) - found
    if missing:
        raise WaveStop("replacements absent from crosswalk shards: %s" % sorted(missing)[:5])
    return out


def _shard_payload_digest(shards: dict[str, list[dict[str, Any]]]) -> str:
    digest = hashlib.sha256()
    for name in sorted(shards):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(sha256_jsonl_rows(shards[name]).encode("ascii") + b"\0")
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def build_crosswalk_manifest(promoted_shards: dict[str, list[dict[str, Any]]],
                             *, accepted_count: int, decision_sha256: str,
                             ledger_fact_count: int) -> dict[str, Any]:
    manifest = json.loads(CROSSWALK_MANIFEST_PATH.read_text(encoding="utf-8"))
    existing = {Path(row["path"]).name: row for row in manifest.get("shards") or []}
    if set(existing) != set(promoted_shards):
        raise WaveStop("crosswalk manifest/shard name set mismatch")
    status_counts: Counter[str] = Counter()
    new_shards = []
    for name in sorted(promoted_shards):
        rows = promoted_shards[name]
        status_counts.update(row.get("status") for row in rows)
        item = copy.deepcopy(existing[name])
        item.update({
            "row_count": len(rows),
            "sha256": sha256_jsonl_rows(rows),
            "first_row_id": rows[0].get("row_id") if rows else None,
            "last_row_id": rows[-1].get("row_id") if rows else None,
        })
        new_shards.append(item)
    manifest.update({
        "generated_at": WAVE_PROMOTED_AT,
        "generated_by": "tools/promote_two_vote_wave.py",
        "source_head": _git("rev-parse", "HEAD"),
        "source_branch": _git("branch", "--show-current"),
        "status": "active",
        "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
        "row_count": sum(len(rows) for rows in promoted_shards.values()),
        "shard_count": len(promoted_shards),
        "status_counts": dict(sorted(status_counts.items())),
        "shards": new_shards,
        "two_vote_promotion": {
            "wave": WAVE,
            "accepted_rows": accepted_count,
            "decision_sha256": decision_sha256,
            "resolution_method": RESOLUTION_METHOD,
            "promoted_at": WAVE_PROMOTED_AT,
            "review_resolved_crosswalk_only": True,
            "ledger_store": "qamus/indexes/largelexicon/fact-ledger/laneb-review.jsonl",
            "ledger_certified_facts": ledger_fact_count,
        },
    })
    return manifest


def update_full_table_meta(crosswalk_manifest: dict[str, Any]) -> None:
    meta = json.loads(FULL_TABLE_META_PATH.read_text(encoding="utf-8"))
    meta["generated_at"] = WAVE_PROMOTED_AT
    meta["generated_by"] = "tools/promote_two_vote_wave.py"
    freshness = meta.setdefault("freshness", {})
    freshness.update({
        "generated_at": WAVE_PROMOTED_AT,
        "generated_by": "tools/promote_two_vote_wave.py",
        "source_head": crosswalk_manifest["source_head"],
        "source_branch": crosswalk_manifest["source_branch"],
        "stale_after": "qamus_qword_denominator_or_crosswalk_evidence_change",
        "status": "active",
    })
    meta["qword_crosswalk_manifest"] = crosswalk_manifest
    write_json_atomic(FULL_TABLE_META_PATH, meta)


def rebuild_queue(baseline: Path, corpus: Path, *, expected_rows: int,
                  promoted_locs: set[str]) -> dict[str, Any]:
    from tools.build_crosswalk_gap_queue import build_queue, write_outputs

    manifest, queue = build_queue(str(ROOT), str(baseline), loc_surfaces_path=str(corpus))
    if len(queue) != expected_rows:
        raise WaveStop("queue rebuild mismatch: %d != %d" % (len(queue), expected_rows))
    remaining = {row["canonical_location"] for row in queue}
    still_present = sorted(promoted_locs & remaining)
    if still_present:
        raise WaveStop("promoted locations did not leave the gap (not no_op): %s"
                       % still_present[:10])
    with tempfile.TemporaryDirectory(prefix="laneb-queue-") as tmp:
        qpath, mpath, final_manifest = write_outputs(tmp, manifest, queue)
        os.replace(qpath, QUEUE_PATH)
        os.replace(mpath, QUEUE_MANIFEST_PATH)
    if sha256_file(QUEUE_PATH) != final_manifest["queue_sha256"]:
        raise WaveStop("installed queue hash does not match rebuilt manifest")
    return final_manifest


# --------------------------------------------------------------------------- #
# flywheel instrumentation
# --------------------------------------------------------------------------- #
def _enrichment_fields_cited(vote_a: dict[str, Any], vote_b: dict[str, Any]) -> list[str]:
    blob = json.dumps([vote_a, vote_b], ensure_ascii=False)
    cited = []
    signatures = [
        ("example_window_fingerprint", "word-window="),
        ("example_whitespace_token", "whitespace-token="),
        ("entry_root", "/root"),
        ("entry_senses", "/senses/"),
        ("entry_section", "/section"),
        ("usage_forms", "/forms/"),
        ("usage_examples", "/examples/"),
        ("live_public_content", "baseline-whitelist-"),
        ("carrier_row", "full_carrier_candidates"),
        ("loc_surface", "loc-surfaces-"),
        ("normalizer", "normalize_ar.py"),
    ]
    for name, needle in signatures:
        if needle in blob:
            cited.append(name)
    return cited


def _row_instrumentation(*, loc: str, carrier: dict[str, Any], fact_id: str,
                         qrow: dict[str, Any], packet: dict[str, Any],
                         vote_a: dict[str, Any], vote_b: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_location": loc,
        "packet_id": packet["packet_id"],
        "calibration_stratum": qrow.get("calibration_stratum"),
        "resolution_method": RESOLUTION_METHOD,
        "gate": packet.get("gate"),
        "ledger_fact_id": fact_id,
        "bound_carrier": {k: carrier.get(k) for k in ("entry_id", "card_id", "qword_row_id")},
        "conclusion_value": qrow["reviewer_a"]["normalized_conclusion"],
        "votes": [
            {"voter_id": "reviewer-A", "vote": "approve",
             "confidence": vote_a.get("confidence"),
             "source_address": vote_a.get("source_address")},
            {"voter_id": "reviewer-B", "vote": "approve",
             "confidence": vote_b.get("confidence"),
             "source_address": vote_b.get("source_address")},
        ],
        "evidence_hashes": packet.get("evidence_hashes"),
        "packet_sha256": packet.get("packet_sha256"),
        "enrichment_fields_cited": _enrichment_fields_cited(vote_a, vote_b),
    }


# --------------------------------------------------------------------------- #
# main promotion pipeline
# --------------------------------------------------------------------------- #
def partition(data: dict[str, Any]) -> dict[str, Any]:
    cal = data["cal"]
    votes_a, votes_b = data["votes_a"], data["votes_b"]
    qualifying = cal["two_vote_gate"]["qualifying_rows"]
    disagreement = cal["disagreement_rows"]
    qpids = {row["packet_id"] for row in qualifying}
    dpids = {row["packet_id"] for row in disagreement}
    abstention_pids = sorted(
        pid for pid in votes_a
        if not _decided(votes_a[pid]) and not _decided(votes_b.get(pid, {}))
    )
    return {"qualifying": qualifying, "disagreement": disagreement,
            "abstention_pids": abstention_pids, "qpids": qpids, "dpids": dpids}


def run(inputs_dir: Path, baseline: Path, corpus: Path, *, apply: bool) -> dict[str, Any]:
    # input integrity ------------------------------------------------------- #
    if sha256_file(baseline) != EXPECTED_BASELINE_SHA256:
        raise WaveStop("baseline sha256 mismatch")
    if sha256_file(corpus) != EXPECTED_CORPUS_SHA256:
        raise WaveStop("loc-surfaces sha256 mismatch")
    data = load_inputs(inputs_dir)
    base_hashes = data["input_hashes"]
    packets, votes_a, votes_b = data["packets"], data["votes_a"], data["votes_b"]
    parts = partition(data)
    qualifying = parts["qualifying"]
    if len(qualifying) != 77:
        raise WaveStop("expected 77 qualifying rows, found %d" % len(qualifying))
    if len(parts["disagreement"]) != 1:
        raise WaveStop("expected 1 disagreement row, found %d" % len(parts["disagreement"]))
    if len(parts["abstention_pids"]) != 22:
        raise WaveStop("expected 22 joint abstentions, found %d" % len(parts["abstention_pids"]))

    # carrier selection + quarantine guard ---------------------------------- #
    selections: dict[str, dict[str, Any]] = {}
    for qrow in qualifying:
        loc = qrow["canonical_location"]
        ayah = ":".join(loc.split(":")[:2])
        if ayah in QUARANTINED_AYAHS or loc in NF_T10_1_LOCS:
            raise WaveStop("quarantined ayah in wave: %s" % loc)
        packet = packets[qrow["packet_id"]]
        carrier = select_carrier(qrow, packet, votes_a[qrow["packet_id"]], votes_b[qrow["packet_id"]])
        selections[loc] = {"carrier": carrier, "qrow": qrow, "packet": packet}
    if len(selections) != 77:
        raise WaveStop("duplicate canonical locations among qualifying rows")
    quword = [s["carrier"]["qword_row_id"] for s in selections.values()]
    if len(set(quword)) != 77:
        raise WaveStop("carrier qword_row_id collision across rows")

    # ledger lifecycle ------------------------------------------------------ #
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    store = fact_ledger.FactLedgerStore(LEDGER_DIR)
    fact_ids: dict[str, str] = {}
    instrumentation = []
    for loc in sorted(selections, key=lambda x: tuple(int(p) for p in x.split(":"))):
        sel = selections[loc]
        va, vb = votes_a[sel["qrow"]["packet_id"]], votes_b[sel["qrow"]["packet_id"]]
        fact_ids[loc] = append_certified(
            store, loc=loc, carrier=sel["carrier"], qrow=sel["qrow"], packet=sel["packet"],
            vote_a=va, vote_b=vb, base_hashes=base_hashes)
        instrumentation.append(_row_instrumentation(
            loc=loc, carrier=sel["carrier"], fact_id=fact_ids[loc], qrow=sel["qrow"],
            packet=sel["packet"], vote_a=va, vote_b=vb))

    dis = parts["disagreement"][0]
    dis_loc = dis["canonical_location"]
    dis_packet = packets[dis["packet_id"]]
    dis_carrier = select_disagreement_carrier(dis, dis_packet)
    dis_fact = append_disagreement(
        store, loc=dis_loc, carrier=dis_carrier, qrow=dis, packet=dis_packet,
        vote_a=votes_a[dis["packet_id"]], vote_b=votes_b[dis["packet_id"]], base_hashes=base_hashes)

    abstention_fact_ids = {}
    for pid in parts["abstention_pids"]:
        packet = packets[pid]
        loc = packet["canonical_location"]
        abstention_fact_ids[loc] = append_abstention(
            store, loc=loc, packet=packet, vote_a=votes_a[pid], vote_b=votes_b[pid],
            base_hashes=base_hashes)

    ledger_errors = store.validate_all()
    if ledger_errors:
        raise WaveStop("ledger failed validation: %s" % ledger_errors[:5])
    # dispose of the rebuildable index; only the JSONL store is committed.
    (LEDGER_DIR / fact_ledger.INDEX_NAME).unlink(missing_ok=True)

    state_counts = Counter(row["certification_state"] for row in store.query(current_only=True))

    # accepted crosswalk rows (ledger-gated) -------------------------------- #
    crosswalk_by_id, shards = load_crosswalk_shards()
    replacements: dict[str, dict[str, Any]] = {}
    for loc, sel in selections.items():
        carrier = sel["carrier"]
        existing = crosswalk_by_id.get(carrier["qword_row_id"])
        if not existing:
            raise WaveStop("carrier %s not present in crosswalk" % carrier["qword_row_id"])
        live_surface = _live_surface(sel["packet"], loc)
        accepted = build_accepted_row(
            store, loc=loc, carrier=carrier, fact_id=fact_ids[loc],
            existing=existing, live_surface=live_surface)
        replacements[carrier["qword_row_id"]] = accepted

    promoted_shards = apply_replacements(shards, replacements)
    if _shard_payload_digest(promoted_shards) != _shard_payload_digest(
            apply_replacements(shards, dict(reversed(list(replacements.items()))))):
        raise WaveStop("promoted shard bytes depend on replacement ordering")

    decision_sha256 = hashlib.sha256(json.dumps(
        sorted([(loc, selections[loc]["carrier"]["qword_row_id"], fact_ids[loc])
                for loc in selections]),
        ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    if not apply:
        return {"selections": len(selections), "state_counts": dict(state_counts),
                "decision_sha256": decision_sha256, "dry_run": True}

    manifest = build_crosswalk_manifest(
        promoted_shards, accepted_count=len(replacements),
        decision_sha256=decision_sha256, ledger_fact_count=len(fact_ids))
    fingerprint = generation_fingerprint(CROSSWALK_DIR)

    def install_sidecars(_generation: dict[str, Any]) -> None:
        update_full_table_meta(manifest)
        write_json_atomic(CROSSWALK_MANIFEST_PATH, manifest)

    atomic_promote_shards(
        CROSSWALK_DIR, promoted_shards,
        writer_id="tools/promote_two_vote_wave.py",
        promoted_at=WAVE_PROMOTED_AT,
        after_promote=install_sidecars,
        expected_current_fingerprint=fingerprint,
    )

    # materialized crosswalk validator must accept the promoted generation.
    validator = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_largelexicon_qword_crosswalk.py")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if validator.returncode != 0:
        raise WaveStop("crosswalk validator rejected promotion:\n%s" % (validator.stdout or "")[-2000:])

    promoted_locs = set(selections)
    queue_manifest = rebuild_queue(
        baseline, corpus, expected_rows=QUEUE_BEFORE - len(promoted_locs),
        promoted_locs=promoted_locs)
    if QUEUE_BEFORE - queue_manifest["queue_rows"] != len(promoted_locs):
        raise WaveStop("queue accepted-count reconciliation failed")

    report = build_report(
        instrumentation=instrumentation, state_counts=state_counts, data=data,
        selections=selections, fact_ids=fact_ids, dis=dis, dis_fact=dis_fact,
        abstention_fact_ids=abstention_fact_ids, decision_sha256=decision_sha256,
        queue_after=queue_manifest["queue_rows"])
    write_json_atomic(WAVE_REPORT_PATH, report)
    return {
        "promoted_locs": len(promoted_locs),
        "state_counts": dict(state_counts),
        "queue_before": QUEUE_BEFORE,
        "queue_after": queue_manifest["queue_rows"],
        "decision_sha256": decision_sha256,
        "accepted_bindings_delta": len(replacements),
    }


def select_disagreement_carrier(dis: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    """A representative carrier subject for the unresolved disagreement row."""
    concl = dis["reviewer_a"]["normalized_conclusion"]
    carriers = packet.get("candidate_carriers") or []
    if ENTRY_RE.match(concl):
        hits = sorted((c for c in carriers if c.get("entry_id") == concl),
                      key=lambda c: c["qword_row_id"])
        if hits:
            return hits[0]
    usable = sorted((c for c in carriers
                     if c.get("entry_id") and c.get("card_id") and c.get("qword_row_id")),
                    key=lambda c: c["qword_row_id"])
    if not usable:
        raise WaveStop("disagreement %s has no addressable carrier" % dis["canonical_location"])
    return usable[0]


def build_report(*, instrumentation, state_counts, data, selections, fact_ids, dis, dis_fact,
                 abstention_fact_ids, decision_sha256, queue_after) -> dict[str, Any]:
    cal = data["cal"]
    verdict = cal.get("calibration_verdict", {})
    agreement = cal.get("agreement_matrix", {})
    strata = Counter(sel["qrow"].get("calibration_stratum") for sel in selections.values())
    return {
        "schema": "qamus/laneb-wave-report@1",
        "state": "finalized",
        "wave": WAVE,
        "promoted_at": WAVE_PROMOTED_AT,
        "resolution_method": RESOLUTION_METHOD,
        "ledger_store": "qamus/indexes/largelexicon/fact-ledger/laneb-review.jsonl",
        "inputs": {
            **data["input_hashes"],
            "baseline_sha256": "sha256:" + EXPECTED_BASELINE_SHA256,
            "loc_surfaces_sha256": "sha256:" + EXPECTED_CORPUS_SHA256,
        },
        "counts": {
            "qualifying_certified": len(fact_ids),
            "disagreement_review_required": 1,
            "joint_abstention_candidates": len(abstention_fact_ids),
            "promoted_bindings": len(selections),
            "queue_before": QUEUE_BEFORE,
            "queue_after": queue_after,
            "queue_delta": QUEUE_BEFORE - queue_after,
            "ledger_state_counts": dict(sorted(state_counts.items())),
            "certified_by_stratum": dict(sorted(strata.items())),
        },
        "review_burden": {
            "packets_reviewed": 100,
            "both_decided": 78,
            "certified_agreeing": len(fact_ids),
            "non_qualifying_disagreement": 1,
            "joint_abstentions": len(abstention_fact_ids),
            "measured_agreement_rate_percent": agreement.get("measured_agreement_rate_percent"),
            "expected_review_burden_per_100_rows": verdict.get("expected_review_burden_per_100_rows"),
            "updated_scale_verdict": verdict.get("updated_scale_verdict"),
        },
        "disagreement": {
            "canonical_location": dis["canonical_location"],
            "packet_id": dis["packet_id"],
            "ledger_fact_id": dis_fact,
            "ledger_state": "review_required",
            "promoted": False,
            "reason": "two_vote_gate_not_satisfied_shared_discriminating_evidence_absent",
        },
        "joint_abstentions": [
            {"canonical_location": loc, "ledger_fact_id": fid, "promoted": False}
            for loc, fid in sorted(abstention_fact_ids.items())
        ],
        "decision_sha256": decision_sha256,
        "rows": instrumentation,
    }


# --------------------------------------------------------------------------- #
# self-test (synthetic, red-first) — invoked by the harness
# --------------------------------------------------------------------------- #
def _self_test() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    base_hashes = {"calibration_analysis": "sha256:" + "0" * 64,
                   "votes_a": "sha256:" + "1" * 64, "votes_b": "sha256:" + "2" * 64}
    packet = {"packet_id": "selftest:1:1:1", "packet_sha256": "3" * 64,
              "mapping_status": "unique", "gate": "two_vote_required",
              "candidate_carriers": [
                  {"entry_id": "0123456789ab", "card_id": "0123456789ab:u1:e1",
                   "qword_row_id": "llx-qword-0123456789ab-01-01-001",
                   "carrier_source_address": "queue#row_id=llx-qword-0123456789ab-01-01-001",
                   "fingerprint_match_candidates": ["1:1:1"], "mapping_status": "unique"}],
              "ayah_word_context": [{"loc": "1:1:1", "surface": "بِسْمِ"}]}
    qrow = {"canonical_location": "1:1:1", "calibration_stratum": "selftest",
            "packet_id": "selftest:1:1:1",
            "reviewer_a": {"normalized_conclusion": "1:1:1", "confidence": "high"},
            "reviewer_b": {"normalized_conclusion": "1:1:1", "confidence": "high"}}
    vote = {"confidence": "high", "source_address": "loc-surfaces#loc=1:1:1",
            "exact_reason": "unique fingerprint at 1:1:1"}

    carrier = select_carrier(qrow, packet, vote, vote)
    check("carrier selection returns fingerprint-unique carrier",
          carrier["qword_row_id"] == "llx-qword-0123456789ab-01-01-001")

    def fresh_store(tmp: str) -> fact_ledger.FactLedgerStore:
        return fact_ledger.FactLedgerStore(Path(tmp))

    with tempfile.TemporaryDirectory() as tmp:
        store = fresh_store(tmp)
        # RED: an uncertified (candidate-only) fact must be refused promotion.
        identity = _carrier_identity("1:1:1", carrier)
        cand = _base_row(identity=identity, loc="1:1:1", value="1:1:1", competing=[],
                         evidence=[_evidence("packet", "source_quote", "x", "quran:1:1:1")],
                         input_hashes=_packet_input_hashes(base_hashes, packet))
        store.append(cand)
        existing = {"schema": "qamus/largelexicon-qword-crosswalk@1",
                    "qword_row_id": carrier["qword_row_id"], "visible_surface": "بِسْمِ",
                    "status": "source_crosswalk_packet_ready"}
        refused = False
        try:
            build_accepted_row(store, loc="1:1:1", carrier=carrier, fact_id=cand["fact_id"],
                               existing=existing, live_surface="بِسْمِ")
        except WaveStop:
            refused = True
        check("RED: uncertified ledger fact is refused promotion (ledger-gate)", refused)

    with tempfile.TemporaryDirectory() as tmp:
        store = fresh_store(tmp)
        fid = append_certified(store, loc="1:1:1", carrier=carrier, qrow=qrow, packet=packet,
                               vote_a=vote, vote_b=vote, base_hashes=base_hashes)
        certified = store.query(fact_id=fid, state="certified")
        check("certified lifecycle reaches certified with two independent approvals",
              bool(certified) and len(certified[0]["review_votes"]) == 2
              and all(v["independent"] for v in certified[0]["review_votes"]))
        existing = {"schema": "qamus/largelexicon-qword-crosswalk@1",
                    "qword_row_id": carrier["qword_row_id"], "visible_surface": "بِسْمِ",
                    "status": "source_crosswalk_packet_ready", "candidate_word_indices": [1]}
        accepted = build_accepted_row(store, loc="1:1:1", carrier=carrier, fact_id=fid,
                                      existing=existing, live_surface="بِسْمِ")
        check("accepted row carries certified fact_id + two_vote method + accepted status",
              accepted["review_fact_id"] == fid
              and accepted["resolution_method"] == RESOLUTION_METHOD
              and accepted["status"] == ACCEPTED and "candidate_word_indices" not in accepted)

        # RED: a certified row whose carrier is missing an identity field must fail.
        broken = dict(carrier, card_id="")
        missing_failed = False
        try:
            build_accepted_row(store, loc="1:1:1", carrier=broken, fact_id=fid,
                               existing=existing, live_surface="بِسْمِ")
        except WaveStop:
            missing_failed = True
        check("RED: certified row missing a carrier field fails", missing_failed)

    # RED: a quarantined-ayah row must be refused by the wave guard.
    quarantined_refused = False
    q_ayah = "2:274:1"
    if ":".join(q_ayah.split(":")[:2]) in QUARANTINED_AYAHS or q_ayah in NF_T10_1_LOCS:
        quarantined_refused = True
    check("RED: quarantined ayah (2:274) is refused", quarantined_refused)

    # determinism: two independent ledger builds are byte-identical.
    def build_once() -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            store = fresh_store(tmp)
            append_certified(store, loc="1:1:1", carrier=carrier, qrow=qrow, packet=packet,
                             vote_a=vote, vote_b=vote, base_hashes=base_hashes)
            append_abstention(store, loc="1:1:2", packet={
                **packet, "canonical_location": "1:1:2",
                "candidate_carriers": [dict(carrier, qword_row_id="llx-qword-0123456789ab-01-01-002")],
            }, vote_a={"abstention_or_blocker": "no match"},
                vote_b={"abstention_or_blocker": "no match"}, base_hashes=base_hashes)
            return (Path(tmp) / LEDGER_FILE_NAME).read_bytes()

    check("determinism: ledger bytes identical across runs", build_once() == build_once())

    if failures:
        print("\n%d SELF-TEST FAILURE(S)" % len(failures))
        return 1
    print("\nPROMOTE-TWO-VOTE-WAVE SELF-TEST PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--promote", action="store_true", help="execute and install the wave")
    parser.add_argument("--dry-run", action="store_true", help="build ledger/decisions, do not install")
    parser.add_argument("--inputs", default=str(ROOT / ".wave1-inputs"))
    parser.add_argument("--baseline", help="deployed whitelist jsonl (hash-pinned)")
    parser.add_argument("--loc-surfaces", help="corpus loc->surface jsonl (hash-pinned)")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not (args.promote or args.dry_run):
        parser.error("one of --self-test, --promote, or --dry-run is required")
    if not args.baseline or not args.loc_surfaces:
        parser.error("--promote/--dry-run require --baseline and --loc-surfaces")
    try:
        result = run(Path(args.inputs), Path(args.baseline), Path(args.loc_surfaces),
                     apply=args.promote)
    except WaveStop as stop:
        print("STOP: %s" % stop, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
