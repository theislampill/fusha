#!/usr/bin/env python3
"""Append-only GAP-N12 migration for the legacy p007 two-vote facts.

The historical p007 store certified 36 occurrence-specific Naḥw facts by
location before exact vote-to-claim binding existed.  This builder preserves
those events, revokes their effective state, registers versioned successor
facts whose complete values are projected from the already-reviewed v1.1
artifacts, and certifies the successors through the current transition engine.

It also regenerates the current 49-fact table, transclusion-edge references and
reverse traces.  No live or website state is read or mutated.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_p007_li_pilot  # noqa: E402
from tools import certify_typed_fact as certifier  # noqa: E402

PILOT_DIR = ROOT / "qamus" / "examples" / "p007-li-pilot"
EVENTS_REL = Path("certification") / "events.jsonl"
META_REL = Path("certification") / "claim-binding-migration.json"
FACTS_REL = Path("typed-facts.jsonl")
REVERSE_REL = Path("reverse-trace.json")
EDGES_REL = Path("transclusion-edges.jsonl")
PROJECTIONS_REL = Path("projections.jsonl")
PARITY_REL = Path("parity-report.json")
REVERSE_INDEX_REL = Path("entry-reverse-index.json")
PRODUCTION_REL = Path("production-difference.json")
VN_UNLOCK_REL = Path("vn-unlock.json")
VOTES_REL = Path("two-vote-artifacts.v1_1.jsonl")
MIGRATED_TYPES: Tuple[Tuple[str, str], ...] = (
    ("contextual_function", "func"),
    ("governor_relation", "gov"),
    ("case_mood_governor", "case"),
)
ACTOR = "lane:sol-gap-n12-claim-binding-migration"
TIMESTAMP = "2026-08-02T18:00:00Z"
CONTRACT_ID = "fd:p00slice:li-jarr-noun-family"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _canonical(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _projection_hash(projection: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(projection).encode("utf-8")).hexdigest()


def _loc_suffix(quran_loc: str) -> str:
    return quran_loc.split(":", 1)[1].replace(":", "_")


def successor_id(legacy_id: str) -> str:
    return legacy_id + ":v2"


def successor_fact(legacy: Dict[str, Any], vote_row: Dict[str, Any]) -> Dict[str, Any]:
    fact = copy.deepcopy(legacy)
    fact["fact_id"] = successor_id(str(legacy["fact_id"]))
    value = certifier._two_vote_expected_fact_value(
        str(legacy["fact_type"]), vote_row["votes"][0], str(vote_row["schema"])
    )
    if value is None:
        raise certifier.CertificationError(
            "no exact successor projection for %s" % legacy["fact_id"]
        )
    fact["fact_value"] = value
    return fact


def _migration_rows(pilot_dir: Path, state: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    votes = _read_jsonl(pilot_dir / VOTES_REL)
    rows: List[Dict[str, Any]] = []
    for vote_row in sorted(votes, key=lambda row: row["occurrence"]["quran_loc"]):
        loc = _loc_suffix(vote_row["occurrence"]["quran_loc"])
        for fact_type, suffix in MIGRATED_TYPES:
            legacy_id = "fact:p00slice:%s:%s" % (loc, suffix)
            legacy_entry = state.get(legacy_id)
            if legacy_entry is None:
                raise certifier.CertificationError("missing legacy fact %s" % legacy_id)
            legacy = legacy_entry.get("fact") or {}
            if legacy.get("fact_type") != fact_type:
                raise certifier.CertificationError(
                    "%s has type %r, expected %s"
                    % (legacy_id, legacy.get("fact_type"), fact_type)
                )
            rows.append({
                "artifact_id": vote_row["artifact_id"],
                "legacy_fact_id": legacy_id,
                "successor_fact": successor_fact(legacy, vote_row),
                "vote_row": vote_row,
            })
    if len(rows) != 36:
        raise certifier.CertificationError(
            "p007 claim-binding migration requires exactly 36 rows (found %d)" % len(rows)
        )
    return rows


def _replace_ids(value: Any, replacements: Dict[str, str]) -> Any:
    if isinstance(value, list):
        return [_replace_ids(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_ids(item, replacements) for key, item in value.items()}
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def _write_current_artifacts(pilot_dir: Path,
                             state: Dict[str, Dict[str, Any]],
                             rows: List[Dict[str, Any]]) -> None:
    replacements = {
        row["legacy_fact_id"]: row["successor_fact"]["fact_id"] for row in rows
    }
    current_rows = _read_jsonl(pilot_dir / FACTS_REL)
    successor_by_legacy = {
        row["legacy_fact_id"]: state[row["successor_fact"]["fact_id"]]["fact"]
        for row in rows
    }
    successor_by_id = {
        fact["fact_id"]: fact for fact in successor_by_legacy.values()
    }
    rewritten: List[Dict[str, Any]] = []
    for fact in current_rows:
        replacement = (
            successor_by_legacy.get(fact["fact_id"])
            or successor_by_id.get(fact["fact_id"])
            or (state.get(fact["fact_id"]) or {}).get("fact")
        )
        rewritten.append(copy.deepcopy(replacement if replacement is not None else fact))
    if len(rewritten) != 49 or len({row["fact_id"] for row in rewritten}) != 49:
        raise certifier.CertificationError("migration must retain exactly 49 current facts")
    _write_jsonl(pilot_dir / FACTS_REL, rewritten)

    traces = json.loads((pilot_dir / REVERSE_REL).read_text(encoding="utf-8"))
    traces = _replace_ids(traces, replacements)
    for trace in traces:
        trace["two_vote_artifact"] = trace["two_vote_artifact"].replace(
            "two-vote-artifacts.jsonl#", "two-vote-artifacts.v1_1.jsonl#"
        )
    build_p007_li_pilot.write_text(
        str(pilot_dir / REVERSE_REL), build_p007_li_pilot.dump_json(traces)
    )

    # v1.1 deliberately excludes free-prose governor.relation from the exact
    # comparable claim.  It also certifies contextual function, not dictionary
    # sense identity.  Regenerate the public-shaped candidate projection so it
    # cannot out-speak the successor facts, then re-hash all 78 appearances.
    projections = _read_jsonl(pilot_dir / PROJECTIONS_REL)
    hashes_by_loc: Dict[str, str] = {}
    for row in projections:
        projection = row["projection"]
        hover = (projection.get("hover_cards") or [{}])[0]
        governor = hover.get("governor")
        if isinstance(governor, dict):
            governor.pop("relation", None)
        identity = hover.get("particle_identity")
        if isinstance(identity, dict):
            sense = identity.pop("sense", None)
            if sense is not None:
                identity["sense_candidate"] = sense
            identity["sense_state"] = "candidate_pending"
        plane = projection.setdefault("certification_plane", {})
        plane.pop("governor", None)
        plane["governor_identity"] = "certified"
        plane["governor_relation"] = "unresolved"
        plane["sense"] = "candidate_pending"
        unresolved = projection.get("unresolved_dependencies")
        if not isinstance(unresolved, list):
            unresolved = []
        for blocker in (
            "occurrence_to_sense_certification",
            "governor_relation_governed_key",
        ):
            if blocker not in unresolved:
                unresolved.append(blocker)
        projection["unresolved_dependencies"] = unresolved
        digest = _projection_hash(projection)
        row["projection_hash"] = digest
        for appearance in row.get("appearances") or []:
            appearance["projection_hash"] = digest
        hashes_by_loc[projection["occurrence_id"].replace("quran:", "", 1)] = digest
    _write_jsonl(pilot_dir / PROJECTIONS_REL, projections)

    parity = json.loads((pilot_dir / PARITY_REL).read_text(encoding="utf-8"))
    for occurrence in parity.get("occurrences") or []:
        occurrence["canonical_hash"] = hashes_by_loc[occurrence["loc"]]
    _write_json(pilot_dir / PARITY_REL, parity)

    locations = build_p007_li_pilot.read_json(str(pilot_dir / "locations.json"))
    votes = build_p007_li_pilot.read_jsonl(str(pilot_dir / VOTES_REL))
    artifacts_by_loc = {row["occurrence"]["quran_loc"]: row for row in votes}
    edges = build_p007_li_pilot.build_edges(locations, artifacts_by_loc)
    build_p007_li_pilot.write_jsonl(str(pilot_dir / EDGES_REL), edges)

    all_appearances = [
        appearance_id
        for occurrence in locations["occurrences"]
        for appearance_id in occurrence["appearance_ids"]
    ]
    page_classes = build_p007_li_pilot.load_appearance_page_classes(all_appearances)
    reverse_index = build_p007_li_pilot.build_reverse_index(locations, page_classes)
    build_p007_li_pilot.write_text(
        str(pilot_dir / REVERSE_INDEX_REL),
        build_p007_li_pilot.dump_json(reverse_index),
    )

    production = build_p007_li_pilot.build_production_difference(locations, parity)
    build_p007_li_pilot.write_text(
        str(pilot_dir / PRODUCTION_REL),
        build_p007_li_pilot.dump_json(production),
    )

    vn_unlock = json.loads((pilot_dir / VN_UNLOCK_REL).read_text(encoding="utf-8"))
    blockers = [
        "occurrence_to_sense_certification",
        "governor_relation_governed_key",
    ]
    direct = vn_unlock.setdefault("family_direct", {})
    direct["projection_state"] = "candidate_pending"
    direct["unresolved_dependencies"] = blockers
    ceiling = vn_unlock.setdefault("pattern_ceiling_li_kasra_clitic", {})
    ceiling["projection_state"] = "candidate_ceiling_only"
    ceiling["unresolved_dependencies"] = blockers
    ceiling["note"] = (
        "candidate ceiling only: each row still needs per-occurrence host-noun, "
        "entry/sense and governor-relation evidence; lam+verb ta'lil and lexical-lam "
        "rivals remain excluded per occurrence"
    )
    vn_unlock["not_deployed"] = True
    _write_json(pilot_dir / VN_UNLOCK_REL, vn_unlock)


def _build_meta(pilot_dir: Path, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    store = certifier.TypedFactCertificationStore(pilot_dir / "certification")
    events = store._events()
    migration_events = [event for event in events if event.get("actor") == ACTOR]
    revoke_event_by_fact = {
        event["fact_id"]: event for event in migration_events
        if event.get("event_type") == "revoke"
    }
    certify_event_by_fact = {
        event["fact_id"]: event for event in migration_events
        if event.get("to_status") == "certified"
    }
    statuses = store.status_by_id()
    mappings = [{
        "affected_projection_ids": row["successor_fact"].get("dependent_projection_ids") or [],
        "artifact_id": row["artifact_id"],
        "fact_type": row["successor_fact"]["fact_type"],
        "legacy_fact_id": row["legacy_fact_id"],
        "legacy_effective_status": statuses.get(row["legacy_fact_id"]),
        "legacy_revoke_event_id": (
            revoke_event_by_fact.get(row["legacy_fact_id"]) or {}
        ).get("event_id"),
        "successor_fact_id": row["successor_fact"]["fact_id"],
        "successor_effective_status": statuses.get(row["successor_fact"]["fact_id"]),
        "successor_certification_event_id": (
            certify_event_by_fact.get(row["successor_fact"]["fact_id"]) or {}
        ).get("event_id"),
    } for row in rows]
    return {
        "schema": "qamus.p007_claim_binding_migration.v1",
        "generator": "tools/migrate_p007_claim_binding.py",
        "authority_gap": "GAP-N12",
        "posture": "append_only_legacy_revocation_and_exact_successor_certification",
        "downstream_projection_posture": {
            "governor_identity": "certified_exact_v1_1",
            "governor_relation": "unresolved_uncompared_prose_withheld",
            "sense_identity": "candidate_pending_separate_fact_required",
            "appearance_hashes_regenerated": 78,
            "not_deployed": True,
        },
        "source_vote_bundle": VOTES_REL.as_posix(),
        "legacy_facts_revoked": sum(
            item["legacy_effective_status"] == "review_required" for item in mappings
        ),
        "exact_successors_certified": sum(
            item["successor_effective_status"] == "certified" for item in mappings
        ),
        "migration_event_count": len(migration_events),
        "dependency_rebind_event_count": sum(
            event.get("event_type") == "dependency_rebind" for event in migration_events
        ),
        "migration_event_sequence": {
            "first": min((event["seq"] for event in migration_events), default=None),
            "last": max((event["seq"] for event in migration_events), default=None),
        },
        "final_event_sha256": _sha256(_canonical(events[-1])) if events else None,
        "mappings": mappings,
        "not_deployed": True,
    }


def _rebind_segment_dependencies(store: certifier.TypedFactCertificationStore,
                                 rows: List[Dict[str, Any]]) -> None:
    desired_by_segment: Dict[str, List[str]] = {}
    for row in rows:
        legacy_id = row["legacy_fact_id"]
        segment_id = legacy_id.rsplit(":", 1)[0] + ":seg"
        desired_by_segment.setdefault(segment_id, []).append(
            row["successor_fact"]["fact_id"]
        )
    state = store.state()
    pending: List[Tuple[str, List[str]]] = []
    for segment_id, desired in sorted(desired_by_segment.items()):
        entry = state.get(segment_id)
        if entry is None:
            raise certifier.CertificationError(
                "missing segmentation fact for dependency rebind: %s" % segment_id
            )
        current = (entry.get("fact") or {}).get("dependent_fact_ids") or []
        legacy = [fact_id.removesuffix(":v2") for fact_id in desired]
        if current == desired:
            continue
        if current != legacy:
            raise certifier.CertificationError(
                "divergent dependency index on %s" % segment_id
            )
        pending.append((segment_id, desired))
    for segment_id, desired in pending:
        store.rebind_dependents(
            segment_id,
            desired,
            actor=ACTOR,
            timestamp=TIMESTAMP,
            reason="GAP-N12: reverse dependency index rebound to exact v1.1 successors",
        )


def apply_migration(pilot_dir: Path) -> Dict[str, Any]:
    store = certifier.TypedFactCertificationStore(pilot_dir / "certification")
    state = store.state()
    rows = _migration_rows(pilot_dir, state)
    legacy_statuses = {state[row["legacy_fact_id"]]["status"] for row in rows}
    successor_entries = [state.get(row["successor_fact"]["fact_id"]) for row in rows]
    if legacy_statuses == {"certified"} and all(entry is None for entry in successor_entries):
        for row in rows:
            store.revoke(
                row["legacy_fact_id"], actor=ACTOR, timestamp=TIMESTAMP,
                reason="GAP-N12: legacy location-only certification replaced by exact v1.1 claim",
            )
        for row in rows:
            fact = row["successor_fact"]
            store.register(
                fact, contract_id=CONTRACT_ID, actor=ACTOR, timestamp=TIMESTAMP
            )
            store.transition(
                fact["fact_id"], "review_required", actor=ACTOR, timestamp=TIMESTAMP,
                reason="GAP-N12 exact successor assembled from frozen v1.1 votes",
            )
            store.transition(
                fact["fact_id"], "certified", actor=ACTOR, timestamp=TIMESTAMP,
                reason="GAP-N12 exact fact value, reason, occurrence and surface bound",
                two_vote_bundle=(pilot_dir / VOTES_REL, row["artifact_id"]),
                packet_dir=pilot_dir,
            )
    else:
        expected_legacy = all(
            state[row["legacy_fact_id"]]["status"] == "review_required" for row in rows
        )
        expected_successors = all(
            entry is not None and entry["status"] == "certified"
            for entry in successor_entries
        )
        if not (expected_legacy and expected_successors):
            raise certifier.CertificationError(
                "partial or divergent GAP-N12 migration state; refusing to append"
            )

    _rebind_segment_dependencies(store, rows)
    state = store.state()
    _write_current_artifacts(pilot_dir, state, rows)
    meta = _build_meta(pilot_dir, rows)
    _write_json(pilot_dir / META_REL, meta)
    trail_errors = store.validate_trail()
    if trail_errors:
        raise certifier.CertificationError(
            "migrated certification trail invalid: " + "; ".join(trail_errors[:5])
        )
    return meta


def check_fresh(pilot_dir: Path) -> List[str]:
    watched = (
        EVENTS_REL,
        META_REL,
        FACTS_REL,
        REVERSE_REL,
        EDGES_REL,
        PROJECTIONS_REL,
        PARITY_REL,
        REVERSE_INDEX_REL,
        PRODUCTION_REL,
        VN_UNLOCK_REL,
    )
    with tempfile.TemporaryDirectory() as td:
        candidate = Path(td) / "p007-li-pilot"
        shutil.copytree(pilot_dir, candidate)
        apply_migration(candidate)
        drift = []
        for relative in watched:
            actual = pilot_dir / relative
            expected = candidate / relative
            if not actual.exists() or actual.read_bytes() != expected.read_bytes():
                drift.append(relative.as_posix())
        return drift


def self_test(pilot_dir: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        candidate = Path(td) / "p007-li-pilot"
        shutil.copytree(pilot_dir, candidate)
        apply_migration(candidate)
        if check_fresh(candidate):
            raise certifier.CertificationError("self-test migrated copy is not fresh")
        facts = _read_jsonl(candidate / FACTS_REL)
        migrated = next(row for row in facts if row["fact_id"].endswith(":v2"))
        migrated["fact_value"] = {"mutated": True}
        _write_jsonl(candidate / FACTS_REL, facts)
        if FACTS_REL.as_posix() not in check_fresh(candidate):
            raise certifier.CertificationError("self-test did not detect typed-fact drift")
        projections = _read_jsonl(candidate / PROJECTIONS_REL)
        projections[0]["projection"]["hover_cards"][0]["governor"]["relation"] = "muta-alliq"
        _write_jsonl(candidate / PROJECTIONS_REL, projections)
        if PROJECTIONS_REL.as_posix() not in check_fresh(candidate):
            raise certifier.CertificationError("self-test did not detect projection drift")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot-dir", type=Path, default=PILOT_DIR)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            meta = apply_migration(args.pilot_dir)
            print(
                "P007 CLAIM-BINDING MIGRATION APPLIED (%d legacy revoked / %d exact certified)"
                % (meta["legacy_facts_revoked"], meta["exact_successors_certified"])
            )
        elif args.check:
            drift = check_fresh(args.pilot_dir)
            if drift:
                print("P007 CLAIM-BINDING MIGRATION DRIFT: " + ", ".join(drift))
                return 1
            print("P007 CLAIM-BINDING MIGRATION FRESH")
        else:
            self_test(args.pilot_dir)
            print("P007 CLAIM-BINDING MIGRATION SELF-TEST PASS")
    except (certifier.CertificationError, OSError, ValueError, KeyError) as exc:
        print("P007 CLAIM-BINDING MIGRATION FAIL: %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
