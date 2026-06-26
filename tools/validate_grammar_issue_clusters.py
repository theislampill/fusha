#!/usr/bin/env python3
"""Validate Phase 3.5 GrammarProblems issue-cluster coverage."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLUSTERS = ROOT / "nahw" / "rules" / "grammar-problems-issue-clusters.json"
DEFAULT_MINING = ROOT / "nahw" / "evals" / "grammar-problems-phase3p25-mining.jsonl"

REQUIRED_CLUSTER_FIELDS = {
    "id",
    "label",
    "bug_class",
    "gate",
    "production_rule",
    "sarf_lesson",
    "nahw_lesson",
    "learner_explanation",
    "procedure_links",
    "drill_links",
    "regression_links",
    "validator_links",
    "future_action",
}

REQUIRED_CLASSIFICATIONS = {
    "already_covered_issue_1",
    "already_covered_issue_2",
    "already_covered_issue_3",
    "correct_positive_regression",
    "new_root_cause_cluster",
}


def repo_path_exists(relpath: str) -> bool:
    return (ROOT / Path(*relpath.split("/"))).exists()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected object")
    return data


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def validate(clusters_path: Path, mining_path: Path) -> tuple[bool, list[str], Counter]:
    errors: list[str] = []
    counts: Counter = Counter()

    data = load_json(clusters_path)
    if data.get("schema") != "fusha/grammar-problems-issue-clusters@1":
        errors.append("schema must be fusha/grammar-problems-issue-clusters@1")
    if data.get("phase") != "3.5":
        errors.append("phase must be 3.5")

    classification_map = data.get("classification_map")
    if not isinstance(classification_map, dict):
        errors.append("classification_map must be an object")
        classification_map = {}
    missing_classifications = sorted(REQUIRED_CLASSIFICATIONS - set(classification_map))
    if missing_classifications:
        errors.append(f"classification_map missing {missing_classifications}")

    clusters = data.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        errors.append("clusters must be a non-empty array")
        clusters = []

    by_id: dict[str, dict] = {}
    for index, cluster in enumerate(clusters, 1):
        if not isinstance(cluster, dict):
            errors.append(f"cluster {index}: not an object")
            continue
        missing = sorted(REQUIRED_CLUSTER_FIELDS - set(cluster))
        if missing:
            errors.append(f"cluster {index}: missing fields {missing}")
        cluster_id = cluster.get("id")
        if not isinstance(cluster_id, str) or not cluster_id:
            errors.append(f"cluster {index}: id must be non-empty")
            continue
        if cluster_id in by_id:
            errors.append(f"duplicate cluster id {cluster_id}")
        by_id[cluster_id] = cluster
        counts[f"cluster:{cluster_id}"] += 1

        for link_field in ("procedure_links", "drill_links", "regression_links", "validator_links"):
            links = cluster.get(link_field)
            if not isinstance(links, list) or not links:
                errors.append(f"{cluster_id}: {link_field} must be non-empty")
                continue
            for relpath in links:
                if not isinstance(relpath, str) or not relpath:
                    errors.append(f"{cluster_id}: {link_field} has non-string path")
                elif not repo_path_exists(relpath):
                    errors.append(f"{cluster_id}: linked file missing: {relpath}")

    for classification, cluster_id in classification_map.items():
        if cluster_id not in by_id:
            errors.append(f"classification {classification} maps to missing cluster {cluster_id}")

    mining_rows = load_jsonl(mining_path)
    if not mining_rows:
        errors.append("mining ledger is empty")
    for row in mining_rows:
        classification = row.get("classification")
        if classification not in classification_map:
            errors.append(f"line {row.get('_line_no')}: unmapped classification {classification!r}")
            continue
        cluster_id = classification_map[classification]
        if cluster_id not in by_id:
            errors.append(f"line {row.get('_line_no')}: mapped cluster {cluster_id!r} missing")
        counts[f"classification:{classification}"] += 1
        counts[f"mapped_cluster:{cluster_id}"] += 1

    for required in (
        "already_covered_issue_1",
        "already_covered_issue_2",
        "already_covered_issue_3",
        "correct_positive_regression",
    ):
        if counts[f"classification:{required}"] == 0:
            errors.append(f"mining ledger has no rows for {required}")

    # Reserved new-cluster lane can be zero, but it must be mapped and documented.
    if classification_map.get("new_root_cause_cluster") != "new_root_cause_required":
        errors.append("new_root_cause_cluster must map to new_root_cause_required")

    return not errors, errors, counts


def run_self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        clusters = root / "clusters.json"
        mining = root / "mining.jsonl"
        clusters.write_text(
            json.dumps(
                {
                    "schema": "fusha/grammar-problems-issue-clusters@1",
                    "phase": "3.5",
                    "classification_map": {
                        "already_covered_issue_1": "issue_1_wrong_reasoning",
                        "already_covered_issue_2": "issue_2_function_attachment",
                        "already_covered_issue_3": "issue_3_morphosyntax_preservation",
                        "correct_positive_regression": "positive_regression_control",
                        "new_root_cause_cluster": "new_root_cause_required",
                    },
                    "clusters": [
                        {
                            "id": "issue_1_wrong_reasoning",
                            "label": "Issue #1",
                            "bug_class": "right_answer_wrong_irab_reasoning",
                            "gate": "two_vote_required",
                            "production_rule": "rule",
                            "sarf_lesson": "sarf",
                            "nahw_lesson": "nahw",
                            "learner_explanation": "learn",
                            "procedure_links": ["nahw/procedures/grammar-risk-gate.md"],
                            "drill_links": ["nahw/drills/grammar-reasoning-safety.md"],
                            "regression_links": ["nahw/evals/grammar-problems-phase3p25-mining.jsonl"],
                            "validator_links": ["tools/validate_grammar_issue_clusters.py"],
                            "future_action": "act",
                        },
                        {
                            "id": "issue_2_function_attachment",
                            "label": "Issue #2",
                            "bug_class": "function_attachment_ambiguity",
                            "gate": "two_vote_required",
                            "production_rule": "rule",
                            "sarf_lesson": "sarf",
                            "nahw_lesson": "nahw",
                            "learner_explanation": "learn",
                            "procedure_links": ["nahw/procedures/grammar-risk-gate.md"],
                            "drill_links": ["nahw/drills/grammar-reasoning-safety.md"],
                            "regression_links": ["nahw/evals/grammar-problems-phase3p25-mining.jsonl"],
                            "validator_links": ["tools/validate_grammar_issue_clusters.py"],
                            "future_action": "act",
                        },
                        {
                            "id": "issue_3_morphosyntax_preservation",
                            "label": "Issue #3",
                            "bug_class": "morphosyntax_preservation_failure",
                            "gate": "two_vote_required",
                            "production_rule": "rule",
                            "sarf_lesson": "sarf",
                            "nahw_lesson": "nahw",
                            "learner_explanation": "learn",
                            "procedure_links": ["nahw/procedures/grammar-risk-gate.md"],
                            "drill_links": ["nahw/drills/grammar-reasoning-safety.md"],
                            "regression_links": ["nahw/evals/grammar-problems-phase3p25-mining.jsonl"],
                            "validator_links": ["tools/validate_grammar_issue_clusters.py"],
                            "future_action": "act",
                        },
                        {
                            "id": "positive_regression_control",
                            "label": "Positive",
                            "bug_class": "positive_regression_control",
                            "gate": "auto_safe_if_other_conditions_met",
                            "production_rule": "rule",
                            "sarf_lesson": "sarf",
                            "nahw_lesson": "nahw",
                            "learner_explanation": "learn",
                            "procedure_links": ["nahw/procedures/grammar-risk-gate.md"],
                            "drill_links": ["nahw/drills/grammar-reasoning-safety.md"],
                            "regression_links": ["nahw/evals/grammar-problems-phase3p25-mining.jsonl"],
                            "validator_links": ["tools/validate_grammar_issue_clusters.py"],
                            "future_action": "act",
                        },
                        {
                            "id": "new_root_cause_required",
                            "label": "New",
                            "bug_class": "new_root_cause_cluster",
                            "gate": "human_review_required",
                            "production_rule": "rule",
                            "sarf_lesson": "sarf",
                            "nahw_lesson": "nahw",
                            "learner_explanation": "learn",
                            "procedure_links": ["nahw/procedures/grammar-risk-gate.md"],
                            "drill_links": ["nahw/drills/grammar-reasoning-safety.md"],
                            "regression_links": ["nahw/evals/grammar-problems-phase3p25-mining.jsonl"],
                            "validator_links": ["tools/validate_grammar_issue_clusters.py"],
                            "future_action": "act",
                        },
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        mining.write_text(
            "\n".join(
                json.dumps({"classification": c}, sort_keys=True)
                for c in (
                    "already_covered_issue_1",
                    "already_covered_issue_2",
                    "already_covered_issue_3",
                    "correct_positive_regression",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        ok, errors, counts = validate(clusters, mining)
        assert ok, errors
        assert counts["classification:already_covered_issue_1"] == 1

        bad = json.loads(clusters.read_text(encoding="utf-8"))
        bad["classification_map"].pop("already_covered_issue_2")
        clusters.write_text(json.dumps(bad), encoding="utf-8")
        ok, errors, _ = validate(clusters, mining)
        assert not ok and "classification_map missing" in "\n".join(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clusters", nargs="?", default=str(DEFAULT_CLUSTERS))
    parser.add_argument("--mining", default=str(DEFAULT_MINING))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        print("validate_grammar_issue_clusters self-test OK")
        return 0

    ok, errors, counts = validate(Path(args.clusters), Path(args.mining))
    if not ok:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OK", " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
