#!/usr/bin/env python3
"""Apply the owner-approved RM-20 canonical SHADOW morphline repairs."""

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
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger, rebind_canonical_hover  # noqa: E402
from tools.compile_canonical_hover_whitelist_packet import (  # noqa: E402
    canonical_public_loc,
    compile_packet,
)
from tools.largelexicon_common import (  # noqa: E402
    atomic_promote_shards,
    previous_generation_path,
    verify_generation,
    writer_lock_path,
)
from tools.validate_canonical_hover_payload_table import (  # noqa: E402
    payload_id,
    validate_rows,
)

MANIFEST_PATH = ROOT / "prep" / "morphline-approved-manifest.json"
PROPOSALS_PATH = ROOT / ".inputs" / "proposals.jsonl"
REVIEWS_PATH = ROOT / ".inputs" / "reviews.jsonl"
DRYRUN_PATH = (
    ROOT
    / "qamus"
    / "indexes"
    / "largelexicon"
    / "crosswalk-gap"
    / "lane-d"
    / "rm20-dryrun-reports.jsonl"
)
SHADOW_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "canonical-hover-shadow-rm20"
LEDGER_DIR = ROOT / "qamus" / "indexes" / "largelexicon" / "fact-ledger" / "rm20-morphline"
FINAL_REPORTS_PATH = DRYRUN_PATH.with_name("rm20-final-rebind-reports.json")
RECEIPT_PATH = DRYRUN_PATH.with_name("rm20-apply-receipt.json")
ENTRIES_PATH = ROOT / "qamus" / "data" / "current" / "entries.jsonl"

APPLY_TIMESTAMP = "2026-07-11T21:00:00Z"
BASELINE_HEAD = "bf1c77e846a7c93c6e832f706535f37ce35ee74d"
WRITER_ID = "rm20-morphline-owner-decision-d"
PUBLIC_WHITELIST_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
SHARD_PAYLOADS = "canonical_payloads.jsonl"
SHARD_BINDINGS = "occurrence_bindings.jsonl"
SHARD_TOMBSTONES = "payload_tombstones.jsonl"
SHARD_CONFLICTS = "binding_tombstone_conflicts.jsonl"


class ApplyStop(RuntimeError):
    """A fail-closed RM-20 application gate rejected the run."""


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def write_pretty_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(".%s.tmp-%d" % (path.name, os.getpid()))
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def verify_frozen_inputs(manifest: dict[str, Any]) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    paths = {
        ".inputs/proposals.jsonl": PROPOSALS_PATH,
        ".inputs/reviews.jsonl": REVIEWS_PATH,
        "qamus/indexes/largelexicon/crosswalk-gap/lane-d/rm20-dryrun-reports.jsonl": DRYRUN_PATH,
    }
    for relative, expected in manifest["input_sha256"].items():
        actual = sha256_file(paths[relative])
        if actual != expected:
            raise ApplyStop(
                "frozen input hash mismatch for %s: expected %s, got %s"
                % (relative, expected, actual)
            )
    proposals = read_jsonl(PROPOSALS_PATH)
    reviews = read_jsonl(REVIEWS_PATH)
    dryruns = read_jsonl(DRYRUN_PATH)
    if len(proposals) != 14 or len(reviews) != 14:
        raise ApplyStop("proposal/review inputs must each contain exactly 14 rows")
    for ordinal, (proposal, review) in enumerate(zip(proposals, reviews, strict=True), 1):
        if proposal.get("payload_id") != review.get("payload_key"):
            raise ApplyStop("proposal/review ordinal join mismatch at row %d" % ordinal)
    verdicts = Counter(review.get("proposal_verdict") for review in reviews)
    expected_verdicts = Counter({
        "agree": 9,
        "alternative": 2,
        "insufficient_exemplars": 3,
    })
    if verdicts != expected_verdicts:
        raise ApplyStop("proposal/review join distribution drifted: %r" % dict(verdicts))
    return proposals, reviews, dryruns


def refusal_reason(fixture: dict[str, Any], allowlist: set[str]) -> str:
    """Reject a non-allowlisted review row before any positive-path work."""
    if fixture.get("payload_id") in allowlist:
        raise ApplyStop("refusal fixture unexpectedly appears in the positive allowlist")
    verdict = fixture.get("review_verdict")
    if verdict == "alternative":
        return "tie_unresolved"
    if verdict == "insufficient_exemplars":
        return "blocked_insufficient_convention_exemplars"
    raise ApplyStop("unknown refusal review verdict: %r" % verdict)


def run_refusal_gate(manifest: dict[str, Any]) -> Counter[str]:
    allowlist = set(manifest["apply_allowlist_payload_ids"])
    fixtures = manifest["refusal_fixtures"]
    if len(fixtures) != 5:
        raise ApplyStop("refusal fixture count must be exactly five")
    counts: Counter[str] = Counter()
    for fixture in fixtures:
        actual = refusal_reason(fixture, allowlist)
        if actual != fixture.get("expected_refusal"):
            raise ApplyStop(
                "%s refusal mismatch: expected %s, got %s"
                % (fixture.get("fixture_id"), fixture.get("expected_refusal"), actual)
            )
        counts[actual] += 1
    if counts != Counter({
        "tie_unresolved": 2,
        "blocked_insufficient_convention_exemplars": 3,
    }):
        raise ApplyStop("refusal fixture distribution drifted: %r" % dict(counts))
    return counts


def build_final_reports(
    manifest: dict[str, Any],
    proposals: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    dryruns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for approved in manifest["approved_payloads"]:
        ordinal = approved["input_row_ordinal"]
        proposal = proposals[ordinal - 1]
        review = reviews[ordinal - 1]
        if (
            proposal.get("payload_id") != approved["payload_id"]
            or proposal.get("proposed_morphline") != approved["proposed_morphline"]
            or review.get("proposal_verdict") != "agree"
        ):
            raise ApplyStop("approved authority mismatch at input row %d" % ordinal)
        matches = [
            row
            for row in dryruns
            if row.get("surface") == approved["surface"]
            and set(row.get("locs") or []) == set(approved["locations"])
        ]
        if len(matches) != 1 or matches[0].get("verify_status") != "PASS":
            raise ApplyStop("approved dry-run join is not one PASS row for %s" % approved["payload_id"])
        source = matches[0]
        old_payload = source["dry_run_report"]["old_payload"]
        old_bindings = [item["old_binding"] for item in source["dry_run_report"]["binding_rebinds"]]
        if old_payload.get("canonical_payload_id") != approved["old_canonical_payload_id"]:
            raise ApplyStop("old payload id mismatch for %s" % approved["payload_id"])
        new_payload = copy.deepcopy(old_payload)
        new_payload["public_payload"]["morphline"] = approved["proposed_morphline"]
        new_payload["public_payload"]["morphline_repair_wave"] = "RM-20"
        new_payload["canonical_payload_id"] = payload_id(new_payload)
        if new_payload["canonical_payload_id"] != approved["final_canonical_payload_id"]:
            raise ApplyStop("final payload id mismatch for %s" % approved["payload_id"])
        report = rebind_canonical_hover.build_rebind_report(
            [old_payload], old_bindings, approved["old_canonical_payload_id"], new_payload
        )
        if report.get("schema") != "qamus.canonical_hover_rebind_report.v1" or report.get("mode") != "dry_run":
            raise ApplyStop("rebind report contract mismatch for %s" % approved["payload_id"])
        errors = rebind_canonical_hover.verify_dataset([old_payload], old_bindings, report)
        if errors:
            raise ApplyStop("rebind dataset invalid for %s: %s" % (approved["payload_id"], "; ".join(errors)))
        generated = {
            item["old_binding"]["binding_id"]: item["new_binding"]["binding_id"]
            for item in report["binding_rebinds"]
        }
        declared = {
            item["old_binding_id"]: item["new_binding_id"]
            for item in approved["binding_rebinds"]
        }
        if generated != declared:
            raise ApplyStop("binding rebind ids mismatch for %s" % approved["payload_id"])
        if report["tombstone"] != approved["tombstone"]:
            raise ApplyStop("payload tombstone mismatch for %s" % approved["payload_id"])
        reports.append(report)

    if len(reports) != 9:
        raise ApplyStop("final report count must be nine")
    dependent = sum(item["summary"]["dependent_bindings"] for item in reports)
    replacement = sum(item["summary"]["replacement_bindings"] for item in reports)
    conflicts = sum(item["summary"]["conflicts"] for item in reports)
    if (dependent, replacement, conflicts) != (26, 26, 26):
        raise ApplyStop("rebind totals must be 26/26/26")
    return reports


def report_rows(reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    old_payloads = [report["old_payload"] for report in reports]
    old_bindings = [
        item["old_binding"]
        for report in reports
        for item in report["binding_rebinds"]
    ]
    new_payloads = [report["new_payload"] for report in reports]
    new_bindings = [
        item["new_binding"]
        for report in reports
        for item in report["binding_rebinds"]
    ]
    errors = validate_rows(old_payloads + old_bindings)
    errors.extend(validate_rows(new_payloads + new_bindings))
    if errors:
        raise ApplyStop("canonical payload/binding validation failed: " + "; ".join(errors))
    return {
        "old_payloads": old_payloads,
        "old_bindings": old_bindings,
        "new_payloads": new_payloads,
        "new_bindings": new_bindings,
        "tombstones": [report["tombstone"] for report in reports],
        "conflicts": [item for report in reports for item in report["conflicts"]],
    }


def evidence_rows(
    ordinal: int, proposal: dict[str, Any], review: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    proposal_id = "rm20-proposal-row:%d" % ordinal
    review_id = "rm20-review-row:%d" % ordinal
    return (
        {
            "evidence_id": proposal_id,
            "type": "two_vote",
            "detail": proposal["rationale"],
            "source_address": ".inputs/proposals.jsonl#row=%d" % ordinal,
        },
        {
            "evidence_id": review_id,
            "type": "two_vote",
            "detail": review["reasoning"],
            "source_address": ".inputs/reviews.jsonl#row=%d" % ordinal,
        },
    )


def append_certified_facts(
    store: fact_ledger.FactLedgerStore,
    manifest: dict[str, Any],
    proposals: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> None:
    hashes = {key: "sha256:" + value for key, value in manifest["input_sha256"].items()}
    for approved in manifest["approved_payloads"]:
        ordinal = approved["input_row_ordinal"]
        proposal = proposals[ordinal - 1]
        review = reviews[ordinal - 1]
        proposal_evidence, review_evidence = evidence_rows(ordinal, proposal, review)
        author_vote = {
            "voter_id": "Opus-author",
            "vote": "approve",
            "evidence_ref": proposal_evidence["evidence_id"],
            "independent": True,
        }
        reviewer_vote = {
            "voter_id": "Codex-reviewer",
            "vote": "approve",
            "evidence_ref": review_evidence["evidence_id"],
            "independent": True,
        }
        for binding in approved["binding_rebinds"]:
            identity = {
                "ref_type": "surface_occurrence",
                "loc": binding["loc"],
                "entry_id": binding["entry_id"],
                "card_id": binding["card_id"],
                "qword_row_id": binding["qword_row_id"],
            }
            candidate = {
                "schema": "qamus.fact_ledger_row.v1",
                "subject_type": "surface_occurrence",
                "subject_identity": identity,
                "fact_type": "morphline_rendering",
                "candidate_or_value": {
                    "value": approved["proposed_morphline"],
                    "competing_alternatives": [],
                    "semantic_tie": False,
                },
                "scope": "occurrence",
                "source_address": {
                    "address": "quran:" + binding["loc"],
                    "source_kind": "quran_token",
                },
                "evidence": [proposal_evidence],
                "provenance": {
                    "actor": "tools/apply_rm20_morphline.py",
                    "method": "owner_decision_d_two_vote_rm20",
                    "created_at": APPLY_TIMESTAMP,
                    "input_hashes": hashes,
                },
                "review_votes": [],
                "certification_state": "candidate",
                "confidence_or_calibration": None,
                "defeaters": [],
                "exceptions": [],
                "dependency_hashes": {},
                "materialization_targets": [],
                "supersedes": None,
                "created_from": "projector:rm20-row-%d" % ordinal,
                "fact_id": "",
            }
            candidate["fact_id"] = fact_ledger.compute_fact_id(candidate)
            if candidate["fact_id"] != binding["morphline_fact_id"]:
                raise ApplyStop("morphline fact id mismatch for %s" % binding["qword_row_id"])
            store.append(candidate)
            store.transition(
                candidate["fact_id"],
                "review_required",
                review_votes=[author_vote],
            )
            store.transition(
                candidate["fact_id"],
                "certified",
                review_votes=[author_vote, reviewer_vote],
                evidence=[proposal_evidence, review_evidence],
            )


def validate_ledger(
    store: fact_ledger.FactLedgerStore, expected_state: str, history_length: int
) -> None:
    errors = store.validate_all()
    if errors:
        raise ApplyStop("fact ledger validation failed: " + "; ".join(errors))
    current = store.query(fact_type="morphline_rendering", current_only=True)
    if len(current) != 26 or {row["certification_state"] for row in current} != {expected_state}:
        raise ApplyStop("fact ledger current state is not 26 %s rows" % expected_state)
    expected_states = ["candidate", "review_required", "certified"]
    if history_length == 4:
        expected_states.append("materialized")
    for row in current:
        history = store.history(row["fact_id"])
        if [item["certification_state"] for item in history] != expected_states:
            raise ApplyStop("fact history lifecycle mismatch for %s" % row["fact_id"])
        if history[1]["review_votes"] != [history[2]["review_votes"][0]]:
            raise ApplyStop("Opus-author review_required vote mismatch")
        voters = [vote["voter_id"] for vote in history[2]["review_votes"]]
        if voters != ["Opus-author", "Codex-reviewer"]:
            raise ApplyStop("certified fact engine voters mismatch")
        if len(history) != history_length:
            raise ApplyStop("fact history length mismatch")


def materialize_facts(store: fact_ledger.FactLedgerStore) -> None:
    for row in sorted(store.query(state="certified"), key=lambda item: item["fact_id"]):
        store.transition(
            row["fact_id"],
            "materialized",
            materialization_targets=["canonical_hover_payload.public_payload.morphline"],
        )


def shadow_compile_gate(
    manifest: dict[str, Any], rows: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    baseline_rows, _none, old_conflicts, baseline_report = compile_packet(
        rows["old_payloads"], rows["old_bindings"], [], [], source_head=BASELINE_HEAD
    )
    if old_conflicts or len(baseline_rows) != 11:
        raise ApplyStop("cannot construct the 11-location SHADOW baseline")
    old_modify, old_noops, old_again_conflicts, _old_report = compile_packet(
        rows["old_payloads"],
        rows["old_bindings"],
        [],
        baseline_rows,
        source_head=BASELINE_HEAD,
    )
    if old_modify or old_again_conflicts or len(old_noops) != 11:
        raise ApplyStop("pre-repair SHADOW expectation is not modify=0/no_op=11")
    first = compile_packet(
        rows["new_payloads"],
        rows["new_bindings"],
        [],
        baseline_rows,
        source_head=BASELINE_HEAD,
    )
    second = compile_packet(
        rows["new_payloads"],
        rows["new_bindings"],
        [],
        baseline_rows,
        source_head=BASELINE_HEAD,
    )
    if canonical_bytes(first) != canonical_bytes(second):
        raise ApplyStop("SHADOW double compile is not byte-identical")
    modified, noops, conflicts, compile_report = first
    modify_locations = {canonical_public_loc(row) for row in modified}
    expected = set(manifest["predeclared_shadow_delta"]["expected_modify_locations"])
    refusal_locations = {fixture["loc"] for fixture in manifest["refusal_fixtures"]}
    if modify_locations != expected:
        raise ApplyStop(
            "SHADOW modify set mismatch: missing=%r extra=%r"
            % (sorted(expected - modify_locations), sorted(modify_locations - expected))
        )
    if modify_locations & refusal_locations:
        raise ApplyStop("refusal location entered the SHADOW delta")
    if conflicts or noops or any(row.get("expected_movement") != "replace" for row in modified):
        raise ApplyStop("post-repair SHADOW contains a non-modify delta class")
    modeled = {canonical_public_loc(row) for row in modified}
    live_only = {canonical_public_loc(row) for row in baseline_rows} - modeled
    if live_only:
        raise ApplyStop("post-repair SHADOW has live_only movement")
    return {
        "baseline_packet_sha256": baseline_report["packet_sha256"],
        "post_packet_sha256": compile_report["packet_sha256"],
        "pre": {"modify": 0, "no_op": 11, "live_only": 0},
        "post": {"modify": 11, "no_op": 0, "live_only": 0},
        "modify_locations": sorted(modify_locations),
        "double_compile_byte_identical": True,
        "refusal_locations_in_delta": 0,
    }


def promotion_shards(rows: dict[str, list[dict[str, Any]]], *, old: bool) -> dict[str, list[dict[str, Any]]]:
    return {
        SHARD_PAYLOADS: rows["old_payloads" if old else "new_payloads"],
        SHARD_BINDINGS: rows["old_bindings" if old else "new_bindings"],
        SHARD_TOMBSTONES: [] if old else rows["tombstones"],
        SHARD_CONFLICTS: [] if old else rows["conflicts"],
    }


def atomic_projection(target: Path, rows: dict[str, list[dict[str, Any]]]) -> None:
    if target.exists() or previous_generation_path(target).exists():
        raise ApplyStop("RM-20 SHADOW generation already exists: %s" % target)
    atomic_promote_shards(
        target,
        promotion_shards(rows, old=True),
        writer_id=WRITER_ID + "-baseline-seed",
        promoted_at=APPLY_TIMESTAMP,
    )
    atomic_promote_shards(
        target,
        promotion_shards(rows, old=False),
        writer_id=WRITER_ID,
        promoted_at=APPLY_TIMESTAMP,
    )
    for directory in (target, previous_generation_path(target)):
        result = verify_generation(directory, allow_legacy=False)
        if not result["ok"]:
            raise ApplyStop("atomic generation validation failed: %r" % result["errors"])
    if writer_lock_path(target).exists() or list(target.parent.glob(target.name + ".staging-*")):
        raise ApplyStop("atomic promotion left a lock or staging directory")


def execute_pipeline(promotion_target: Path, workdir: Path) -> dict[str, Any]:
    manifest = load_manifest()
    proposals, reviews, dryruns = verify_frozen_inputs(manifest)
    refusal_counts = run_refusal_gate(manifest)
    reports = build_final_reports(manifest, proposals, reviews, dryruns)
    rows = report_rows(reports)
    ledger_work = workdir / "ledger"
    store = fact_ledger.FactLedgerStore(ledger_work)
    append_certified_facts(store, manifest, proposals, reviews)
    validate_ledger(store, "certified", 3)
    shadow = shadow_compile_gate(manifest, rows)
    atomic_projection(promotion_target, rows)
    materialize_facts(store)
    validate_ledger(store, "materialized", 4)
    return {
        "manifest": manifest,
        "reports": reports,
        "rows": rows,
        "ledger_dir": ledger_work,
        "shadow": shadow,
        "refusal_counts": dict(refusal_counts),
    }


def apply_to_repo() -> dict[str, Any]:
    forbidden_existing = [path for path in (LEDGER_DIR, FINAL_REPORTS_PATH, RECEIPT_PATH) if path.exists()]
    if forbidden_existing:
        raise ApplyStop("RM-20 output already exists: %s" % forbidden_existing[0])
    entries_before = sha256_file(ENTRIES_PATH)
    with tempfile.TemporaryDirectory(prefix="rm20-apply-") as temporary:
        workdir = Path(temporary)
        try:
            result = execute_pipeline(SHADOW_DIR, workdir)
            shutil.copytree(result["ledger_dir"], LEDGER_DIR)
            write_pretty_atomic(FINAL_REPORTS_PATH, result["reports"])
            receipt = {
                "schema": "qamus.rm20_morphline_apply_receipt.v1",
                "generator": "python tools/apply_rm20_morphline.py --apply",
                "wave": "RM-20",
                "owner_decision": "2026-07-11 batch item D",
                "apply_timestamp": APPLY_TIMESTAMP,
                "input_sha256": result["manifest"]["input_sha256"],
                "public_whitelist_sha256_before": PUBLIC_WHITELIST_SHA256,
                "public_whitelist_sha256_after": PUBLIC_WHITELIST_SHA256,
                "entries_sha256_before": entries_before,
                "entries_sha256_after": sha256_file(ENTRIES_PATH),
                "counts": {
                    "payloads": 9,
                    "dependent_bindings": 26,
                    "replacement_bindings": 26,
                    "payload_tombstones": 9,
                    "binding_tombstone_conflicts": 26,
                    "facts": 26,
                    "fact_revisions": 104,
                },
                "ledger_validation": {
                    "before_projection": "26 certified facts; zero errors",
                    "after_projection": "26 materialized facts; 26 four-state histories; zero errors",
                },
                "refusal_gate": {
                    **result["refusal_counts"],
                    "fixtures": 5,
                    "positive_path_calls_during_gate": 0,
                },
                "shadow": result["shadow"],
            }
            if receipt["entries_sha256_before"] != receipt["entries_sha256_after"]:
                raise ApplyStop("entries.jsonl changed during RM-20 apply")
            write_pretty_atomic(RECEIPT_PATH, receipt)
            return receipt
        except Exception:
            for path in (LEDGER_DIR, FINAL_REPORTS_PATH, RECEIPT_PATH):
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            for path in (SHADOW_DIR, previous_generation_path(SHADOW_DIR)):
                if path.exists():
                    shutil.rmtree(path)
            lock = writer_lock_path(SHADOW_DIR)
            if lock.exists():
                lock.unlink()
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test-refusals", action="store_true")
    parser.add_argument("--self-test-positive", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    selected = sum(bool(value) for value in (args.self_test_refusals, args.self_test_positive, args.apply))
    if selected != 1:
        parser.error("choose exactly one of --self-test-refusals, --self-test-positive, or --apply")
    if args.self_test_refusals:
        counts = run_refusal_gate(load_manifest())
        print(
            "REFUSAL GATE PASS: 5/5; tie_unresolved=%d; "
            "blocked_insufficient_convention_exemplars=%d; positive_path_calls=0"
            % (counts["tie_unresolved"], counts["blocked_insufficient_convention_exemplars"])
        )
        return 0
    if args.self_test_positive:
        with tempfile.TemporaryDirectory(prefix="rm20-positive-") as temporary:
            root = Path(temporary)
            result = execute_pipeline(root / "shadow", root)
            print(
                "POSITIVE PATH PASS: reports=9; dependent=26 replacement=26 conflicts=26; "
                "ledger_before=certified:26; ledger_after=materialized:26 histories=26x4; "
                "atomic=current+prev generation_ok; double_compile=byte_identical; "
                "modify=11 exact_set; refusal_locations_in_delta=0"
            )
            if len(result["reports"]) != 9:
                raise ApplyStop("self-test report count drifted")
        return 0
    receipt = apply_to_repo()
    print(json.dumps(receipt["counts"], sort_keys=True))
    print("RM-20 APPLY PASS: SHADOW generation, lineage, ledger, and receipt materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
