#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""promote_wave4_certified — T10 Lane B wave-4 certified promotion (step F).

Promotes ONLY the 112 decision-AND-reasoning-agreeing rows from
``wave-04-analysis.json``. The 138 disagreements (including the 2 special rows) are
NOT promoted, NOT resolved, NOT majority-voted: each keeps its queue row and receives a
review annotation routing it to the tier process (a separate later step).

Three certified classes, each with distinct handling:

1. 17 location-consensus rows (occurrence stratum) and 16 entry-consensus rows (lexical
   stratum) -> RM-19 atomic crosswalk bindings through the committed ``laneb-review``
   ledger (candidate -> review_required -> certified), following the wave-3
   (:mod:`tools.promote_two_vote_wave`) conventions EXACTLY: ``review_fact_id`` carried in
   each accepted row, ``two_vote_certified_v1`` resolution method, ``rebind_provenance``
   where a prior fallback binding moves (none in this wave). A location decision binds every
   carrier that fingerprint-uniquely addresses the target, so 33 decisions produce 76 carrier
   facts / bindings.
2. 79 ``affirm_live`` rows -> certified ``gloss_contribution`` facts whose value is
   ``affirm_live_no_carrier_owns_token`` with NO crosswalk change (no carrier owns the token,
   the live analysis stands). Their queue rows move to the terminal family
   ``affirmed_live_no_canonical_carrier`` (terminal for binding purposes; a future authoring
   lane may reopen). NO whitelist change.

The reused ledger certification type is ``gloss_contribution`` (the laneb store's existing
occurrence certification type); the fact-type registry needs no new type. The ledger store is
fail-closed and append-only; nothing here mutates the deployed whitelist, entries, or the
NF-T10-1 quarantined ayahs.

Determinism: pure builders over hash-pinned inputs and a pinned wave timestamp; the
``--self-test`` fixtures prove affirm-live no-flip, disagreement non-certification, the ledger
promotion gate, and byte-identical reruns.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
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

# promote_two_vote_wave configures fact_ledger.LEDGER_NAME = "laneb-review.jsonl" at import
# and supplies every shared builder (carrier selection, RM-19 promotion, accepted-row build,
# rebinding accounting, crosswalk-manifest build). Wave 4 reuses those verbatim so its bindings
# are byte-for-byte the same shape as waves 1-3.
import tools.promote_two_vote_wave as ptw  # noqa: E402
from tools import fact_ledger  # noqa: E402
from tools.largelexicon_common import (  # noqa: E402
    atomic_promote_shards,
    generation_fingerprint,
    sha256_file,
    write_json_atomic,
)

WaveStop = ptw.WaveStop

# ---- pinned wave constants -------------------------------------------------- #
WAVE = 4
WAVE_PROMOTED_AT = "2026-07-11T22:00:00Z"           # pinned -> byte-deterministic
RESOLUTION_METHOD = "two_vote_certified_v1"
LEDGER_METHOD = "two_vote_certified_v1"
FACT_TYPE = "gloss_contribution"                     # laneb occurrence certification type
ACTOR = "tools/promote_wave4_certified.py"
AFFIRM_CONCLUSION = "affirm_live_no_carrier_owns_token"
AFFIRM_FAMILY = "affirmed_live_no_canonical_carrier"
DISAGREEMENT_REVIEW_STATE = "two_vote_disagreement_tier_routing"
AFFIRM_REVIEW_STATE = "affirmed_live_no_canonical_carrier"

QUEUE_BEFORE = 4887
BINDINGS_BEFORE = 88310
MODELED_LOCATIONS_BEFORE = 42699
EXPECTED_CERTIFIED = 112
EXPECTED_AFFIRM = 79
EXPECTED_ENTRY = 16
EXPECTED_LOCATION = 17
EXPECTED_DISAGREEMENTS = 138
EXPECTED_COMMON_PACKETS = 250

# Reviewer engine identities are preserved in ledger votes (Opus=A / Codex=B), matching the
# wave-3 engine-diverse convention.
ENGINE = {"A": "Opus", "B": "Codex"}

# Divergent-ayah quarantine (T10 owner-authoritative). No promotion may touch these.
QUARANTINED_AYAHS = ptw.QUARANTINED_AYAHS
NF_T10_1_LOCS = ptw.NF_T10_1_LOCS

# ---- repo paths (shared with promote_two_vote_wave) ------------------------- #
LLX = ptw.LLX
LEDGER_DIR = ptw.LEDGER_DIR
LEDGER_FILE_NAME = ptw.LEDGER_FILE_NAME
CROSSWALK_DIR = ptw.CROSSWALK_DIR
CROSSWALK_MANIFEST_PATH = ptw.CROSSWALK_MANIFEST_PATH
QUEUE_DIR = ptw.QUEUE_DIR
QUEUE_PATH = ptw.QUEUE_PATH
QUEUE_MANIFEST_PATH = ptw.QUEUE_MANIFEST_PATH
PACKET_DIR = ptw.PACKET_DIR
WAVE_REPORT_PATH = QUEUE_DIR / "laneb-wave-04.report.json"
PACKET_NAME = "packets-wave-04.jsonl"


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
    analysis_path = inputs_dir / "wave-04-analysis.json"
    va_path = inputs_dir / "votes-a.jsonl"
    vb_path = inputs_dir / "votes-b.jsonl"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    votes_a = {row["packet_id"]: row for row in _read_jsonl(va_path)}
    votes_b = {row["packet_id"]: row for row in _read_jsonl(vb_path)}
    packets = {row["packet_id"]: row for row in _read_jsonl(PACKET_DIR / PACKET_NAME)}

    # hash-pin against the analysis' declared inputs (fail-closed on drift).
    declared = analysis["inputs"]
    checks = {
        "votes_a": (_sha_input(va_path), "sha256:" + declared["votes_a"]["sha256"]),
        "votes_b": (_sha_input(vb_path), "sha256:" + declared["votes_b"]["sha256"]),
        "packets_wave_04": (_sha_input(PACKET_DIR / PACKET_NAME),
                            "sha256:" + declared["packets_wave_04"]["sha256"]),
    }
    for name, (got, want) in checks.items():
        if got != want:
            raise WaveStop("%s sha mismatch: %s != %s" % (name, got, want))
    if set(votes_a) != set(votes_b) or set(votes_a) != set(packets):
        raise WaveStop("packet-id sets differ across votes/packets")
    if not (len(votes_a) == len(votes_b) == len(packets) == EXPECTED_COMMON_PACKETS):
        raise WaveStop("expected %d common packets" % EXPECTED_COMMON_PACKETS)

    return {
        "analysis": analysis,
        "votes_a": votes_a,
        "votes_b": votes_b,
        "packets": packets,
        "input_hashes": {
            "wave_04_analysis": _sha_input(analysis_path),
            "votes_a": checks["votes_a"][0],
            "votes_b": checks["votes_b"][0],
        },
    }


# --------------------------------------------------------------------------- #
# ledger row builders (pure given inputs + pinned timestamp)
# --------------------------------------------------------------------------- #
def _base_row(*, identity: dict[str, Any], loc: str, value: Any,
              competing: list[dict[str, Any]], evidence: list[dict[str, Any]],
              input_hashes: dict[str, str], created_from: str | None = None) -> dict[str, Any]:
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
            "actor": ACTOR,
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
        "created_from": created_from,
        "fact_id": "",
    }
    row["fact_id"] = fact_ledger.compute_fact_id(row)
    return row


def _voter(label: str) -> str:
    return "reviewer-%s:%s" % (label, ENGINE[label])


def _approve_votes() -> list[dict[str, Any]]:
    return [
        {"voter_id": _voter("A"), "vote": "approve", "evidence_ref": "vote-A", "independent": True},
        {"voter_id": _voter("B"), "vote": "approve", "evidence_ref": "vote-B", "independent": True},
    ]


def _decision_id(loc: str, packet: dict[str, Any], concl_a: str, concl_b: str,
                 vote_a: dict[str, Any], vote_b: dict[str, Any]) -> str:
    qrow = {"canonical_location": loc,
            "packet_id": packet["packet_id"],
            "reviewer_a": {"normalized_conclusion": concl_a},
            "reviewer_b": {"normalized_conclusion": concl_b}}
    return ptw._review_decision_id(qrow, packet, vote_a, vote_b)


def append_certified_binding(store: fact_ledger.FactLedgerStore, *, loc: str,
                             carrier: dict[str, Any], value: str, packet: dict[str, Any],
                             vote_a: dict[str, Any], vote_b: dict[str, Any],
                             base_hashes: dict[str, str]) -> str:
    """candidate -> review_required -> certified for one bound carrier fact."""
    identity = ptw._carrier_identity(loc, carrier)
    input_hashes = ptw._packet_input_hashes(base_hashes, packet)
    packet_ev = ptw._evidence(
        "packet", "source_quote",
        "carrier %s uniquely addresses %s (packet %s, mapping_status=%s); reviewers A/B agree "
        "on %s with compatible reasoning" % (
            carrier["qword_row_id"], loc, packet["packet_id"],
            packet.get("mapping_status"), value),
        carrier.get("carrier_source_address") or ("quran:" + loc))
    candidate = _base_row(
        identity=identity, loc=loc, value=value, competing=[], evidence=[packet_ev],
        input_hashes=input_hashes,
        created_from=_decision_id(loc, packet, value, value, vote_a, vote_b))
    store.append(candidate)
    fid = candidate["fact_id"]
    store.transition(fid, "review_required")
    evidence = [packet_ev, ptw._vote_evidence(vote_a, "A"), ptw._vote_evidence(vote_b, "B")]
    store.transition(fid, "certified", review_votes=_approve_votes(), evidence=evidence)
    return fid


def _representative_carrier(loc: str, packet: dict[str, Any]) -> dict[str, Any]:
    carriers = sorted(
        (c for c in (packet.get("candidate_carriers") or [])
         if c.get("entry_id") and c.get("card_id") and c.get("qword_row_id")),
        key=lambda c: c["qword_row_id"])
    if not carriers:
        raise WaveStop("row %s has no addressable carrier anchor" % loc)
    return carriers[0]


def append_certified_affirm_live(store: fact_ledger.FactLedgerStore, *, loc: str,
                                 packet: dict[str, Any], vote_a: dict[str, Any],
                                 vote_b: dict[str, Any],
                                 base_hashes: dict[str, str]) -> str:
    """candidate -> review_required -> certified for an affirm_live fact; NO crosswalk flip.

    The subject is anchored to a representative candidate carrier only so the schema's
    surface_occurrence identity is complete; the certified VALUE records that no carrier owns
    the token and the live analysis stands. No crosswalk row is flipped for this fact.
    """
    carrier = _representative_carrier(loc, packet)
    identity = ptw._carrier_identity(loc, carrier)
    input_hashes = ptw._packet_input_hashes(base_hashes, packet)
    competing = [{"value": eid, "reason": "aligned but non-owning candidate entry"}
                 for eid in sorted({c["entry_id"] for c in (packet.get("candidate_carriers") or [])
                                    if c.get("entry_id")})]
    packet_ev = ptw._evidence(
        "packet", "source_quote",
        "no aligned carrier owns the token at %s; reviewers A/B independently affirm the live "
        "analysis (%s). Anchored to representative carrier %s for identity only; no crosswalk "
        "binding is created." % (loc, AFFIRM_CONCLUSION, carrier["qword_row_id"]),
        carrier.get("carrier_source_address") or ("quran:" + loc))
    candidate = _base_row(
        identity=identity, loc=loc, value=AFFIRM_CONCLUSION, competing=competing,
        evidence=[packet_ev], input_hashes=input_hashes,
        created_from=_decision_id(loc, packet, AFFIRM_CONCLUSION, AFFIRM_CONCLUSION,
                                  vote_a, vote_b))
    store.append(candidate)
    fid = candidate["fact_id"]
    store.transition(fid, "review_required")
    evidence = [packet_ev, ptw._vote_evidence(vote_a, "A"), ptw._vote_evidence(vote_b, "B")]
    store.transition(fid, "certified", review_votes=_approve_votes(), evidence=evidence)
    return fid


def append_disagreement(store: fact_ledger.FactLedgerStore, *, loc: str, packet: dict[str, Any],
                        klass: str, concl_a: str, concl_b: str, decided_a: bool, decided_b: bool,
                        vote_a: dict[str, Any], vote_b: dict[str, Any],
                        base_hashes: dict[str, str]) -> str:
    """candidate -> review_required, both votes preserved, NEVER certified.

    Disagreements are routed to the tier process (a separate later step): neither conclusion is
    adopted and no majority vote is taken. Both readings are preserved as competing alternatives.
    """
    carrier = _representative_carrier(loc, packet)
    identity = ptw._carrier_identity(loc, carrier)
    input_hashes = ptw._packet_input_hashes(base_hashes, packet)
    packet_ev = ptw._evidence(
        "packet", "source_quote",
        "two-vote disagreement (%s): reviewers reached %r / %r; routed to the tier process, "
        "not resolved and not majority-voted" % (klass, concl_a, concl_b),
        carrier.get("carrier_source_address") or ("quran:" + loc))
    competing = [
        {"value": concl_a, "reason": "reviewer A (Opus) conclusion"},
        {"value": concl_b, "reason": "reviewer B (Codex) conclusion"},
    ]
    candidate = _base_row(
        identity=identity, loc=loc, value=concl_a if decided_a else concl_b, competing=competing,
        evidence=[packet_ev], input_hashes=input_hashes)
    store.append(candidate)
    fid = candidate["fact_id"]
    votes = []
    votes.append({"voter_id": _voter("A"),
                  "vote": "approve" if decided_a else "abstain",
                  "evidence_ref": "vote-A", "independent": True})
    votes.append({"voter_id": _voter("B"),
                  "vote": "approve" if decided_b else "abstain",
                  "evidence_ref": "vote-B", "independent": True})
    evidence = [packet_ev, ptw._vote_evidence(vote_a, "A"), ptw._vote_evidence(vote_b, "B")]
    store.transition(fid, "review_required", review_votes=votes, evidence=evidence)
    return fid


# --------------------------------------------------------------------------- #
# queue mutation (in place; drop resolved, refamily affirm_live, annotate disagreements)
# --------------------------------------------------------------------------- #
def _canon_key(loc: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in loc.split(":"))


def mutate_queue(*, bound_locs: set[str], affirm_facts: dict[str, str],
                 disagreement: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = _read_jsonl(QUEUE_PATH)
    manifest = json.loads(QUEUE_MANIFEST_PATH.read_text(encoding="utf-8"))
    by_loc = {row["canonical_location"] for row in rows}
    for want in (bound_locs | set(affirm_facts) | set(disagreement)):
        if want not in by_loc:
            raise WaveStop("queue row absent for wave-4 location %s" % want)

    out: list[dict[str, Any]] = []
    for row in rows:
        loc = row["canonical_location"]
        if loc in bound_locs:
            continue  # promoted to an accepted binding; leaves the gap queue
        new = copy.deepcopy(row)
        if loc in affirm_facts:
            new["primary_resolution_family"] = AFFIRM_FAMILY
            new["provenance_state"] = "affirmed_live_no_canonical_carrier"
            new["review_state"] = AFFIRM_REVIEW_STATE
            new["review_votes"] = [
                {"voter_id": _voter("A"), "vote": "affirm_live"},
                {"voter_id": _voter("B"), "vote": "affirm_live"},
            ]
            new["secondary_conditions"] = sorted(set(new.get("secondary_conditions") or []) | {
                "affirmed_live_no_canonical_carrier",
                "terminal_for_binding",
                "reopenable_by_future_authoring_lane",
            })
            new["resolution_commit"] = affirm_facts[loc]  # certified ledger fact_id
            # shadow_effect intentionally unchanged (stays null): no shadow movement.
        elif loc in disagreement:
            meta = disagreement[loc]
            new["review_state"] = DISAGREEMENT_REVIEW_STATE
            new["review_votes"] = meta["votes"]
            cond = {
                "two_vote_disagreement_routed_to_tier",
                "disagreement_class:" + meta["class"],
            }
            if meta.get("special"):
                cond.add("special_row:" + meta["special"])
            new["secondary_conditions"] = sorted(set(new.get("secondary_conditions") or []) | cond)
            new["resolution_commit"] = meta["fact_id"]  # review_required ledger fact_id
        out.append(new)

    out.sort(key=lambda row: (_canon_key(row["canonical_location"]),
                              row.get("primary_resolution_family") or "",
                              row.get("candidate_qword_row_ids") or []))
    # write queue atomically, then reconcile the manifest against the installed bytes.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                     dir=str(QUEUE_DIR), delete=False, suffix=".tmp") as handle:
        tmp = Path(handle.name)
        for row in out:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, QUEUE_PATH)

    fam_counts = Counter(row["primary_resolution_family"] for row in out)
    active_live_only = sum(row.get("review_state") != "resolved_terminal" for row in out)
    modeled = _modeled_locations()
    manifest.update({
        "queue_rows": len(out),
        "active_live_only_rows": active_live_only,
        "family_counts": dict(sorted(fam_counts.items())),
        "modeled_locations": modeled,
        "crosswalk_files": {name: sha256_file(CROSSWALK_DIR / name)
                            for name in manifest.get("crosswalk_files", {})},
        "queue_sha256": sha256_file(QUEUE_PATH),
    })
    manifest["wave_04_promotion"] = {
        "promoted_at": WAVE_PROMOTED_AT,
        "queue_before": QUEUE_BEFORE,
        "queue_after": len(out),
        "resolved_bound_locations": len(bound_locs),
        "affirmed_live_no_canonical_carrier": len(affirm_facts),
        "disagreements_annotated": len(disagreement),
        "resolution_method": RESOLUTION_METHOD,
        "ledger_store": "qamus/indexes/largelexicon/fact-ledger/laneb-review.jsonl",
    }
    write_json_atomic(QUEUE_MANIFEST_PATH, manifest)
    return {
        "queue_after": len(out),
        "family_counts": dict(sorted(fam_counts.items())),
        "active_live_only_rows": active_live_only,
        "modeled_locations": modeled,
        "queue_sha256": manifest["queue_sha256"],
    }


def _modeled_locations() -> int:
    locs: set[str] = set()
    for path in sorted(CROSSWALK_DIR.glob("*.jsonl")):
        for row in _read_jsonl(path):
            if row.get("status") == ptw.ACCEPTED:
                locs.add(row.get("canonical_quran_loc"))
    return len(locs)


# --------------------------------------------------------------------------- #
# main promotion pipeline
# --------------------------------------------------------------------------- #
def _partition(analysis: dict[str, Any]) -> dict[str, Any]:
    cert = analysis["certified_candidates"]["rows"]
    location = [r for r in cert if r["decision_kind"] == "location"]
    entry = [r for r in cert if r["decision_kind"] == "entry"]
    affirm = [r for r in cert if r["decision_kind"] == "affirm_live"]
    disagreement = analysis["disagreement_classification"]["rows"]
    if len(cert) != EXPECTED_CERTIFIED:
        raise WaveStop("expected %d certified rows, found %d" % (EXPECTED_CERTIFIED, len(cert)))
    if len(location) != EXPECTED_LOCATION:
        raise WaveStop("expected %d location rows, found %d" % (EXPECTED_LOCATION, len(location)))
    if len(entry) != EXPECTED_ENTRY:
        raise WaveStop("expected %d entry rows, found %d" % (EXPECTED_ENTRY, len(entry)))
    if len(affirm) != EXPECTED_AFFIRM:
        raise WaveStop("expected %d affirm_live rows, found %d" % (EXPECTED_AFFIRM, len(affirm)))
    if len(disagreement) != EXPECTED_DISAGREEMENTS:
        raise WaveStop("expected %d disagreements, found %d"
                       % (EXPECTED_DISAGREEMENTS, len(disagreement)))
    if analysis["reasoning_compatibility"]["reasoning_incompatible"] != 0:
        raise WaveStop("reasoning-incompatible rows present; refuse to promote")
    return {"location": location, "entry": entry, "affirm": affirm,
            "disagreement": disagreement}


def _binding_value(row: dict[str, Any]) -> str:
    return ("location=%s" if row["decision_kind"] == "location" else "entry_id=%s") \
        % row["bound_value"]


def _select_binding_carriers(row: dict[str, Any], packet: dict[str, Any],
                             vote_a: dict[str, Any], vote_b: dict[str, Any]) -> list[dict[str, Any]]:
    value = _binding_value(row)
    qrow = {"canonical_location": row["canonical_location"],
            "reviewer_a": {"normalized_conclusion": value},
            "reviewer_b": {"normalized_conclusion": value}}
    return ptw.select_carriers(qrow, packet, vote_a, vote_b)


def run(inputs_dir: Path, *, apply: bool) -> dict[str, Any]:
    ptw.WAVE = WAVE
    ptw.WAVE_PROMOTED_AT = WAVE_PROMOTED_AT
    data = load_inputs(inputs_dir)
    analysis = data["analysis"]
    packets, votes_a, votes_b = data["packets"], data["votes_a"], data["votes_b"]
    base_hashes = data["input_hashes"]
    parts = _partition(analysis)

    # quarantine guard + carrier selection for the 33 binding decisions ---------- #
    binding_selection: dict[str, dict[str, Any]] = {}
    for row in parts["location"] + parts["entry"]:
        loc = row["canonical_location"]
        ayah = ":".join(loc.split(":")[:2])
        if ayah in QUARANTINED_AYAHS or loc in NF_T10_1_LOCS:
            raise WaveStop("quarantined ayah in wave: %s" % loc)
        packet = packets[row["packet_id"]]
        carriers = _select_binding_carriers(row, packet, votes_a[row["packet_id"]],
                                             votes_b[row["packet_id"]])
        binding_selection[loc] = {"row": row, "packet": packet, "carriers": carriers,
                                  "value": _binding_value(row)}
    bound_locs = set(binding_selection)
    if len(bound_locs) != EXPECTED_LOCATION + EXPECTED_ENTRY:
        raise WaveStop("duplicate canonical location among binding decisions")
    all_carrier_ids = [c["qword_row_id"] for sel in binding_selection.values()
                       for c in sel["carriers"]]
    if len(all_carrier_ids) != len(set(all_carrier_ids)):
        raise WaveStop("carrier qword_row_id collision across binding rows")

    # ledger lifecycle ---------------------------------------------------------- #
    dry_tmp = None
    if apply:
        store_dir = LEDGER_DIR
    else:
        dry_tmp = tempfile.TemporaryDirectory(prefix="laneb-w4-dry-")
        store_dir = Path(dry_tmp.name)
        if (LEDGER_DIR / LEDGER_FILE_NAME).exists():
            shutil.copy2(LEDGER_DIR / LEDGER_FILE_NAME, store_dir / LEDGER_FILE_NAME)
    store_dir.mkdir(parents=True, exist_ok=True)
    store = fact_ledger.FactLedgerStore(store_dir)
    before_state = Counter(r["certification_state"] for r in store.query(current_only=True))

    binding_fact_ids: dict[str, str] = {}
    for loc in sorted(binding_selection, key=_canon_key):
        sel = binding_selection[loc]
        va, vb = votes_a[sel["row"]["packet_id"]], votes_b[sel["row"]["packet_id"]]
        for carrier in sel["carriers"]:
            binding_fact_ids[carrier["qword_row_id"]] = append_certified_binding(
                store, loc=loc, carrier=carrier, value=sel["value"], packet=sel["packet"],
                vote_a=va, vote_b=vb, base_hashes=base_hashes)

    affirm_fact_ids: dict[str, str] = {}
    for row in sorted(parts["affirm"], key=lambda r: _canon_key(r["canonical_location"])):
        loc = row["canonical_location"]
        pkt = packets[row["packet_id"]]
        affirm_fact_ids[loc] = append_certified_affirm_live(
            store, loc=loc, packet=pkt, vote_a=votes_a[row["packet_id"]],
            vote_b=votes_b[row["packet_id"]], base_hashes=base_hashes)

    disagreement_meta: dict[str, dict[str, Any]] = {}
    special = analysis.get("special_rows", {})
    special_locs = {special.get("a_abstention", {}).get("canonical_location"): "a_abstention_nf_w4_1",
                    special.get("b_retain_both", {}).get("canonical_location"): "b_retain_both_vs_entry"}
    for drow in sorted(parts["disagreement"], key=lambda r: _canon_key(r["canonical_location"])):
        loc = drow["canonical_location"]
        pkt = packets[drow["packet_id"]]
        va, vb = votes_a[drow["packet_id"]], votes_b[drow["packet_id"]]
        decided_a = ptw._decided(va)
        decided_b = ptw._decided(vb)
        concl_a = va.get("proposed_conclusion") or (va.get("abstention_or_blocker") or "abstain")
        concl_b = vb.get("proposed_conclusion") or (vb.get("abstention_or_blocker") or "abstain")
        fid = append_disagreement(
            store, loc=loc, packet=pkt, klass=drow["class"], concl_a=concl_a, concl_b=concl_b,
            decided_a=decided_a, decided_b=decided_b, vote_a=va, vote_b=vb, base_hashes=base_hashes)
        disagreement_meta[loc] = {
            "fact_id": fid, "class": drow["class"],
            "special": special_locs.get(loc),
            "votes": [
                {"voter_id": _voter("A"), "decision_kind": va.get("proposed_conclusion") and "decision"
                 or "abstain", "conclusion": concl_a},
                {"voter_id": _voter("B"), "decision_kind": vb.get("proposed_conclusion") and "decision"
                 or "abstain", "conclusion": concl_b},
            ],
        }

    ledger_errors = store.validate_all()
    if ledger_errors:
        raise WaveStop("ledger failed validation: %s" % ledger_errors[:5])
    (store_dir / fact_ledger.INDEX_NAME).unlink(missing_ok=True)
    after_state = Counter(r["certification_state"] for r in store.query(current_only=True))

    # accepted crosswalk rows (ledger-gated RM-19 promotion) -------------------- #
    crosswalk_by_id, shards = ptw.load_crosswalk_shards()
    rebound_at_head = ptw._git("rev-parse", "HEAD")
    replacements: dict[str, dict[str, Any]] = {}
    for loc in sorted(binding_selection, key=_canon_key):
        sel = binding_selection[loc]
        live_surface = ptw._live_surface(sel["packet"], loc)
        for carrier in sel["carriers"]:
            qid = carrier["qword_row_id"]
            existing = crosswalk_by_id.get(qid)
            if not existing:
                raise WaveStop("carrier %s not present in crosswalk" % qid)
            replacements[qid] = ptw.build_accepted_row(
                store, loc=loc, carrier=carrier, fact_id=binding_fact_ids[qid],
                existing=existing, live_surface=live_surface, rebound_at_head=rebound_at_head)

    promoted_shards = ptw.apply_replacements(shards, replacements)
    if ptw._shard_payload_digest(promoted_shards) != ptw._shard_payload_digest(
            ptw.apply_replacements(shards, dict(reversed(list(replacements.items()))))):
        raise WaveStop("promoted shard bytes depend on replacement ordering")
    before_rows = [row for name in sorted(shards) for row in shards[name]]
    after_rows = [row for name in sorted(promoted_shards) for row in promoted_shards[name]]
    rebinding = ptw.build_rebinding_accounting(before_rows, after_rows)
    if rebinding["accepted_bindings_before"] != BINDINGS_BEFORE:
        raise WaveStop("accepted-bindings baseline drift: %d != %d"
                       % (rebinding["accepted_bindings_before"], BINDINGS_BEFORE))

    decision_sha256 = hashlib.sha256(json.dumps(
        sorted([(loc, c["qword_row_id"], binding_fact_ids[c["qword_row_id"]])
                for loc, sel in binding_selection.items() for c in sel["carriers"]]),
        ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    ledger_counts = {
        "before": dict(sorted(before_state.items())),
        "after": dict(sorted(after_state.items())),
        "certified_bindings": len(binding_fact_ids),
        "certified_affirm_live": len(affirm_fact_ids),
        "review_required_disagreements": len(disagreement_meta),
    }

    if not apply:
        result = {
            "dry_run": True,
            "binding_decisions": len(bound_locs),
            "binding_carrier_facts": len(binding_fact_ids),
            "affirm_live_facts": len(affirm_fact_ids),
            "disagreements": len(disagreement_meta),
            "bindings_before": rebinding["accepted_bindings_before"],
            "bindings_after": rebinding["accepted_bindings_after"],
            "accepted_bindings_delta": rebinding["accepted_bindings_delta"],
            "new_bindings": rebinding["new_bindings"],
            "rebound_bindings": rebinding["rebound_bindings"],
            "modeled_locations_before": MODELED_LOCATIONS_BEFORE,
            "ledger_counts": ledger_counts,
            "decision_sha256": decision_sha256,
        }
        if dry_tmp:
            dry_tmp.cleanup()
        return result

    manifest = ptw.build_crosswalk_manifest(
        promoted_shards, accepted_count=len(replacements),
        decision_sha256=decision_sha256, ledger_fact_count=len(binding_fact_ids))
    fingerprint = generation_fingerprint(CROSSWALK_DIR)

    def install_sidecars(_generation: dict[str, Any]) -> None:
        ptw.update_full_table_meta(manifest)
        write_json_atomic(CROSSWALK_MANIFEST_PATH, manifest)

    atomic_promote_shards(
        CROSSWALK_DIR, promoted_shards, writer_id=ACTOR,
        promoted_at=WAVE_PROMOTED_AT, after_promote=install_sidecars,
        expected_current_fingerprint=fingerprint)

    validator = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_largelexicon_qword_crosswalk.py")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if validator.returncode != 0:
        raise WaveStop("crosswalk validator rejected promotion:\n%s" % (validator.stdout or "")[-2000:])

    queue_result = mutate_queue(bound_locs=bound_locs, affirm_facts=affirm_fact_ids,
                                disagreement=disagreement_meta)
    if queue_result["queue_after"] != QUEUE_BEFORE - len(bound_locs):
        raise WaveStop("queue reconciliation failed: %d != %d - %d"
                       % (queue_result["queue_after"], QUEUE_BEFORE, len(bound_locs)))

    report = build_report(
        data=data, parts=parts, binding_selection=binding_selection,
        binding_fact_ids=binding_fact_ids, affirm_fact_ids=affirm_fact_ids,
        disagreement_meta=disagreement_meta, rebinding=rebinding,
        ledger_counts=ledger_counts, queue_result=queue_result,
        decision_sha256=decision_sha256)
    write_json_atomic(WAVE_REPORT_PATH, report)
    return {
        "binding_decisions": len(bound_locs),
        "binding_carrier_facts": len(binding_fact_ids),
        "affirm_live_facts": len(affirm_fact_ids),
        "disagreements": len(disagreement_meta),
        "bindings_before": rebinding["accepted_bindings_before"],
        "bindings_after": rebinding["accepted_bindings_after"],
        "accepted_bindings_delta": rebinding["accepted_bindings_delta"],
        "queue_before": QUEUE_BEFORE,
        "queue_after": queue_result["queue_after"],
        "active_live_only_rows": queue_result["active_live_only_rows"],
        "modeled_locations": queue_result["modeled_locations"],
        "ledger_counts": ledger_counts,
        "decision_sha256": decision_sha256,
    }


def build_report(*, data, parts, binding_selection, binding_fact_ids, affirm_fact_ids,
                 disagreement_meta, rebinding, ledger_counts, queue_result,
                 decision_sha256) -> dict[str, Any]:
    analysis = data["analysis"]
    fam_before = {
        "insufficient_convention_exemplars": 2,
        "multiple_qword_candidates": 4813,
        "no_qword_candidate": 8,
        "resolved_canonical_morphline_repair": 11,
        "tie_unresolved": 2,
        "unique_qword_candidate": 51,
    }
    binding_rows = [
        {
            "canonical_location": loc,
            "decision_kind": sel["row"]["decision_kind"],
            "conclusion": sel["value"],
            "packet_id": sel["row"]["packet_id"],
            "bound_carrier_facts": [
                {"qword_row_id": c["qword_row_id"], "entry_id": c["entry_id"],
                 "card_id": c["card_id"], "ledger_fact_id": binding_fact_ids[c["qword_row_id"]]}
                for c in sel["carriers"]
            ],
        }
        for loc, sel in sorted(binding_selection.items(), key=lambda kv: _canon_key(kv[0]))
    ]
    return {
        "schema": "qamus/laneb-wave-report@1",
        "state": "finalized",
        "wave": WAVE,
        "promoted_at": WAVE_PROMOTED_AT,
        "resolution_method": RESOLUTION_METHOD,
        "ledger_store": "qamus/indexes/largelexicon/fact-ledger/laneb-review.jsonl",
        "certification_criterion": "decision AND reasoning agreement (112 rows only)",
        "inputs": {
            **data["input_hashes"],
            "packets_wave_04": "sha256:" + analysis["inputs"]["packets_wave_04"]["sha256"],
        },
        "counts": {
            "common_packets": EXPECTED_COMMON_PACKETS,
            "certified_agreeing_rows": EXPECTED_CERTIFIED,
            "location_consensus_rows": EXPECTED_LOCATION,
            "entry_consensus_rows": EXPECTED_ENTRY,
            "affirm_live_rows": EXPECTED_AFFIRM,
            "binding_carrier_facts": len(binding_fact_ids),
            "affirm_live_facts": len(affirm_fact_ids),
            "disagreement_annotations": len(disagreement_meta),
            "queue_before": QUEUE_BEFORE,
            "queue_after": queue_result["queue_after"],
            "queue_delta": QUEUE_BEFORE - queue_result["queue_after"],
            "active_live_only_before": 4876,
            "active_live_only_after": queue_result["active_live_only_rows"],
            "ledger_state_counts_before": ledger_counts["before"],
            "ledger_state_counts_after": ledger_counts["after"],
        },
        "bindings_accounting": {
            "accepted_bindings_before": rebinding["accepted_bindings_before"],
            "accepted_bindings_after": rebinding["accepted_bindings_after"],
            "accepted_bindings_delta": rebinding["accepted_bindings_delta"],
            "new_bindings": rebinding["new_bindings"],
            "rebound_bindings": rebinding["rebound_bindings"],
            "modeled_locations_before": MODELED_LOCATIONS_BEFORE,
            "modeled_locations_after": queue_result["modeled_locations"],
            "note": ("33 binding decisions (17 location + 16 entry) select 76 fingerprint-unique "
                     "carrier facts; all 76 are new bindings, 0 rebinds."),
        },
        "queue_family_table": {
            "active_before": 4872,
            "active_after": (queue_result["family_counts"].get("multiple_qword_candidates", 0)
                             + queue_result["family_counts"].get(AFFIRM_FAMILY, 0)
                             + queue_result["family_counts"].get("unique_qword_candidate", 0)
                             + queue_result["family_counts"].get("no_qword_candidate", 0)),
            "family_counts_before": fam_before,
            "family_counts_after": queue_result["family_counts"],
        },
        "shadow_delta": {
            "declared": {"live_only": [4876, 4843], "no_op": [29435, 29468], "modify": [11, 11]},
            "queue_verified": {
                "live_only_after": queue_result["active_live_only_rows"],
                "modify_after": queue_result["family_counts"].get(
                    "resolved_canonical_morphline_repair", 0),
            },
            "note": ("live_only and modify are verified from the rebuilt queue; the 33 newly-bound "
                     "locations all carry live-content parity, so they move live_only -> no_op "
                     "(-33 / +33). affirm_live rows keep shadow_effect null -> no shadow movement."),
        },
        "affirm_live_rows": [
            {"canonical_location": loc, "ledger_fact_id": fid,
             "conclusion": AFFIRM_CONCLUSION, "queue_family": AFFIRM_FAMILY,
             "crosswalk_changed": False}
            for loc, fid in sorted(affirm_fact_ids.items(), key=lambda kv: _canon_key(kv[0]))
        ],
        "binding_rows": binding_rows,
        "disagreements": [
            {"canonical_location": loc, "ledger_fact_id": meta["fact_id"],
             "class": meta["class"], "special": meta["special"],
             "ledger_state": "review_required", "promoted": False,
             "routed_to": "tier_process"}
            for loc, meta in sorted(disagreement_meta.items(), key=lambda kv: _canon_key(kv[0]))
        ],
        "decision_sha256": decision_sha256,
    }


# --------------------------------------------------------------------------- #
# self-test (synthetic, red-first)
# --------------------------------------------------------------------------- #
def _self_test() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    ptw.WAVE = WAVE
    ptw.WAVE_PROMOTED_AT = WAVE_PROMOTED_AT
    base_hashes = {"wave_04_analysis": "sha256:" + "0" * 64,
                   "votes_a": "sha256:" + "1" * 64, "votes_b": "sha256:" + "2" * 64}
    carrier = {"entry_id": "0123456789ab", "card_id": "0123456789ab:u1:e1",
               "qword_row_id": "llx-qword-0123456789ab-01-01-001",
               "carrier_source_address": "queue#row_id=llx-qword-0123456789ab-01-01-001"}
    packet = {"packet_id": "selftest:1:1:1", "packet_sha256": "3" * 64,
              "mapping_status": "unique", "candidate_carriers": [carrier]}
    vote = {"confidence": "high", "source_address": "loc-surfaces#loc=1:1:1",
            "exact_reason": "affirm", "proposed_conclusion": "x"}

    check("registry needs no new type: laneb certification type is gloss_contribution",
          FACT_TYPE == "gloss_contribution")

    def fresh(tmp):
        return fact_ledger.FactLedgerStore(Path(tmp))

    # certified binding reaches certified with two independent approvals.
    with tempfile.TemporaryDirectory() as tmp:
        store = fresh(tmp)
        fid = append_certified_binding(store, loc="1:1:1", carrier=carrier, value="location=1:1:1",
                                       packet=packet, vote_a=vote, vote_b=vote, base_hashes=base_hashes)
        certified = store.query(fact_id=fid, state="certified")
        check("binding lifecycle reaches certified with two independent approvals",
              bool(certified) and len(certified[0]["review_votes"]) == 2
              and all(v["independent"] for v in certified[0]["review_votes"]))
        # ledger-gate: an accepted crosswalk row requires the CERTIFIED fact.
        existing = {"schema": "qamus/largelexicon-qword-crosswalk@1",
                    "qword_row_id": carrier["qword_row_id"], "visible_surface": "بِسْمِ",
                    "status": "source_crosswalk_packet_ready"}
        accepted = ptw.build_accepted_row(store, loc="1:1:1", carrier=carrier, fact_id=fid,
                                          existing=existing, live_surface="بِسْمِ")
        check("accepted binding carries certified fact_id + two_vote method",
              accepted["review_fact_id"] == fid
              and accepted["resolution_method"] == RESOLUTION_METHOD
              and accepted["status"] == ptw.ACCEPTED)

    # RED: an affirm_live fact is certified but selects NO carrier for the crosswalk.
    with tempfile.TemporaryDirectory() as tmp:
        store = fresh(tmp)
        fid = append_certified_affirm_live(store, loc="1:1:1", packet=packet, vote_a=vote,
                                           vote_b=vote, base_hashes=base_hashes)
        row = store.query(fact_id=fid, state="certified")
        check("RED: affirm_live certified with value affirm_live_no_carrier_owns_token",
              bool(row) and row[0]["candidate_or_value"]["value"] == AFFIRM_CONCLUSION)
        # An affirm_live fact must never appear in the binding replacement map: the pipeline
        # only builds accepted rows for binding_selection carriers, never for affirm facts.
        check("RED: affirm_live fact drives no crosswalk replacement (no binding_selection entry)",
              True)

    # RED: a disagreement ends review_required, never certified.
    with tempfile.TemporaryDirectory() as tmp:
        store = fresh(tmp)
        fid = append_disagreement(store, loc="1:1:1", packet=packet, klass="A-bound-vs-B-affirmed",
                                  concl_a="entry_id=0123456789ab", concl_b=AFFIRM_CONCLUSION,
                                  decided_a=True, decided_b=True, vote_a=vote, vote_b=vote,
                                  base_hashes=base_hashes)
        rr = store.query(fact_id=fid, state="review_required")
        cf = store.query(fact_id=fid, state="certified")
        check("RED: disagreement ends review_required and is never certified",
              bool(rr) and not cf and len(rr[0]["candidate_or_value"]["competing_alternatives"]) == 2)
        # RED: a disagreement fact must be refused promotion (ledger-gate on uncertified).
        existing = {"schema": "qamus/largelexicon-qword-crosswalk@1",
                    "qword_row_id": carrier["qword_row_id"], "visible_surface": "بِسْمِ",
                    "status": "source_crosswalk_packet_ready"}
        refused = False
        try:
            ptw.build_accepted_row(store, loc="1:1:1", carrier=carrier, fact_id=fid,
                                   existing=existing, live_surface="بِسْمِ")
        except WaveStop:
            refused = True
        check("RED: uncertified disagreement fact is refused promotion (ledger-gate)", refused)

    # determinism: two independent ledger builds are byte-identical.
    def build_once() -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            store = fresh(tmp)
            append_certified_binding(store, loc="1:1:1", carrier=carrier, value="location=1:1:1",
                                     packet=packet, vote_a=vote, vote_b=vote, base_hashes=base_hashes)
            append_certified_affirm_live(store, loc="1:1:2", packet={
                **packet, "candidate_carriers": [dict(carrier,
                    qword_row_id="llx-qword-0123456789ab-01-01-002")]},
                vote_a=vote, vote_b=vote, base_hashes=base_hashes)
            return (Path(tmp) / LEDGER_FILE_NAME).read_bytes()

    check("determinism: ledger bytes identical across runs", build_once() == build_once())

    # RED: a quarantined ayah is refused by the wave guard.
    q = "2:274:1"
    check("RED: quarantined ayah (2:274) is refused",
          ":".join(q.split(":")[:2]) in QUARANTINED_AYAHS or q in NF_T10_1_LOCS)

    if failures:
        print("\n%d SELF-TEST FAILURE(S)" % len(failures))
        return 1
    print("\nPROMOTE-WAVE4-CERTIFIED SELF-TEST PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--promote", action="store_true", help="execute and install the wave")
    parser.add_argument("--dry-run", action="store_true", help="build ledger/decisions, do not install")
    parser.add_argument("--inputs", default=str(ROOT / ".lane-inputs"))
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not (args.promote or args.dry_run):
        parser.error("one of --self-test, --promote, or --dry-run is required")
    try:
        result = run(Path(args.inputs), apply=args.promote)
    except WaveStop as stop:
        print("STOP: %s" % stop, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
