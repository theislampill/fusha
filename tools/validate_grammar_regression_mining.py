#!/usr/bin/env python3
"""Validate the Phase 3.25 GrammarProblems regression-mining ledger.

The ledger classifies every existing GrammarProblems-derived eval case into the
Phase 3.25 issue buckets without copying the original prompt/answer text into a
second artifact.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "nahw" / "evals" / "grammar-problems-phase3p25-mining.jsonl"
DEFAULT_EVAL = ROOT / "nahw" / "evals" / "grammar-problems-derived-eval.jsonl"

CLASSIFICATIONS = {
    "already_covered_issue_1",
    "already_covered_issue_2",
    "already_covered_issue_3",
    "new_root_cause_cluster",
    "correct_positive_regression",
}

REQUIRED_FIELDS = {
    "phase",
    "source_eval_id",
    "batch_id",
    "batch_index",
    "case_index",
    "level",
    "bloom",
    "format",
    "depth",
    "topic",
    "required_gate",
    "classification",
    "issue_cluster",
    "status",
    "next_action",
    "needs_new_issue",
}

FORBIDDEN_COPY_FIELDS = {
    "question_ar",
    "question_en",
    "expected_answer",
    "expected_reasoning",
}


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: row is not an object")
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def eval_ids(path: Path) -> list[str]:
    rows = load_jsonl(path)
    ids: list[str] = []
    for row in rows:
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path}:{row.get('_line_no')}: eval row lacks string id")
        ids.append(case_id)
    return ids


def validate_rows(rows: Iterable[dict], expected_ids: list[str] | None = None) -> tuple[bool, list[str], Counter]:
    errors: list[str] = []
    counts: Counter = Counter()
    seen: list[str] = []
    row_count = 0

    for row in rows:
        row_count += 1
        line = row.get("_line_no", "?")
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            errors.append(f"line {line}: missing fields {missing}")

        forbidden = sorted(FORBIDDEN_COPY_FIELDS & set(row))
        if forbidden:
            errors.append(f"line {line}: forbidden copied fields present {forbidden}")

        phase = row.get("phase")
        if phase != "3.25":
            errors.append(f"line {line}: phase must be 3.25, got {phase!r}")

        case_id = row.get("source_eval_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"line {line}: source_eval_id must be a non-empty string")
        else:
            seen.append(case_id)

        batch_id = row.get("batch_id")
        if not isinstance(batch_id, str) or not re.fullmatch(r"GP25-B\d{3}", batch_id):
            errors.append(f"line {line}: batch_id must match GP25-B###")

        for field in ("batch_index", "case_index"):
            value = row.get(field)
            if not isinstance(value, int) or value < 1:
                errors.append(f"line {line}: {field} must be a positive integer")
        if isinstance(row.get("case_index"), int) and row["case_index"] > 12:
            errors.append(f"line {line}: case_index must keep batches small (<=12)")

        classification = row.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"line {line}: invalid classification {classification!r}")
        else:
            counts[f"classification:{classification}"] += 1

        issue_cluster = row.get("issue_cluster")
        if not isinstance(issue_cluster, str) or not issue_cluster.strip():
            errors.append(f"line {line}: issue_cluster must be non-empty")

        needs_new_issue = row.get("needs_new_issue")
        if not isinstance(needs_new_issue, bool):
            errors.append(f"line {line}: needs_new_issue must be boolean")
        elif classification == "new_root_cause_cluster":
            if not needs_new_issue:
                errors.append(f"line {line}: new_root_cause_cluster requires needs_new_issue=true")
            if not row.get("proposed_issue_id"):
                errors.append(f"line {line}: new_root_cause_cluster requires proposed_issue_id")
        elif needs_new_issue:
            errors.append(f"line {line}: needs_new_issue=true only allowed for new_root_cause_cluster")

        if row.get("status") not in {
            "phase3p25_batch_ready",
            "phase3p25_positive_control",
            "phase3p25_new_issue_required",
        }:
            errors.append(f"line {line}: invalid status {row.get('status')!r}")

        for text_field in ("topic", "required_gate", "next_action"):
            if not isinstance(row.get(text_field), str) or not row.get(text_field).strip():
                errors.append(f"line {line}: {text_field} must be a non-empty string")

    if row_count == 0:
        errors.append("ledger is empty")

    if expected_ids is not None:
        expected = Counter(expected_ids)
        actual = Counter(seen)
        if actual != expected:
            missing = sorted((expected - actual).elements())
            extra = sorted((actual - expected).elements())
            dupes = sorted(k for k, v in actual.items() if v > 1)
            errors.append(
                "source_eval_id coverage mismatch: "
                f"missing={missing[:10]} extra={extra[:10]} dupes={dupes[:10]}"
            )

    for required in (
        "already_covered_issue_1",
        "already_covered_issue_2",
        "already_covered_issue_3",
        "correct_positive_regression",
    ):
        if counts[f"classification:{required}"] == 0:
            errors.append(f"ledger lacks required classification bucket {required}")

    return not errors, errors, counts


def run_self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        eval_path = root / "eval.jsonl"
        ledger_path = root / "ledger.jsonl"
        eval_rows = [{"id": f"GP-T-{i:03d}"} for i in range(1, 5)]
        ledger_rows = [
            {
                "phase": "3.25",
                "source_eval_id": "GP-T-001",
                "batch_id": "GP25-B001",
                "batch_index": 1,
                "case_index": 1,
                "level": "ajurrumiyyah",
                "bloom": "recall",
                "format": "objective",
                "depth": "direct",
                "topic": "jar_majrur",
                "required_gate": "auto_safe",
                "classification": "correct_positive_regression",
                "issue_cluster": "Positive regression control",
                "status": "phase3p25_positive_control",
                "next_action": "keep auto-safe only when other gates agree",
                "needs_new_issue": False,
            },
            {
                "phase": "3.25",
                "source_eval_id": "GP-T-002",
                "batch_id": "GP25-B001",
                "batch_index": 1,
                "case_index": 2,
                "level": "qatr_al_nada",
                "bloom": "analysis",
                "format": "essay",
                "depth": "deep",
                "topic": "signs_of_irab",
                "required_gate": "two_vote_required",
                "classification": "already_covered_issue_1",
                "issue_cluster": "Issue #1 - right answer with wrong reasoning",
                "status": "phase3p25_batch_ready",
                "next_action": "exercise answer plus reasoning gate",
                "needs_new_issue": False,
            },
            {
                "phase": "3.25",
                "source_eval_id": "GP-T-003",
                "batch_id": "GP25-B001",
                "batch_index": 1,
                "case_index": 3,
                "level": "awdah_al_masalik",
                "bloom": "application",
                "format": "objective",
                "depth": "direct",
                "topic": "idafa",
                "required_gate": "two_vote_required",
                "classification": "already_covered_issue_2",
                "issue_cluster": "Issue #2 - function and attachment ambiguity",
                "status": "phase3p25_batch_ready",
                "next_action": "exercise attachment gate",
                "needs_new_issue": False,
            },
            {
                "phase": "3.25",
                "source_eval_id": "GP-T-004",
                "batch_id": "GP25-B001",
                "batch_index": 1,
                "case_index": 4,
                "level": "ajurrumiyyah",
                "bloom": "understanding",
                "format": "objective",
                "depth": "direct",
                "topic": "building_present_verb",
                "required_gate": "two_vote_required",
                "classification": "already_covered_issue_3",
                "issue_cluster": "Issue #3 - morphosyntax preservation",
                "status": "phase3p25_batch_ready",
                "next_action": "exercise form and mood preservation",
                "needs_new_issue": False,
            },
        ]
        eval_path.write_text("\n".join(json.dumps(r) for r in eval_rows) + "\n", encoding="utf-8")
        ledger_path.write_text("\n".join(json.dumps(r) for r in ledger_rows) + "\n", encoding="utf-8")
        ok, errors, _ = validate_rows(load_jsonl(ledger_path), eval_ids(eval_path))
        assert ok, errors

        bad = ledger_rows[:3]
        ledger_path.write_text("\n".join(json.dumps(r) for r in bad) + "\n", encoding="utf-8")
        ok, errors, _ = validate_rows(load_jsonl(ledger_path), eval_ids(eval_path))
        assert not ok and "coverage mismatch" in "\n".join(errors)

        bad_copy = dict(ledger_rows[0])
        bad_copy["question_en"] = "copied prompt"
        ledger_path.write_text(json.dumps(bad_copy) + "\n", encoding="utf-8")
        ok, errors, _ = validate_rows(load_jsonl(ledger_path), ["GP-T-001"])
        assert not ok and "forbidden copied fields" in "\n".join(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", nargs="?", default=str(DEFAULT_LEDGER))
    parser.add_argument("--eval", default=str(DEFAULT_EVAL), help="GrammarProblems-derived eval JSONL")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        print("validate_grammar_regression_mining self-test OK")
        return 0

    ledger = Path(args.ledger)
    eval_path = Path(args.eval)
    rows = load_jsonl(ledger)
    expected = eval_ids(eval_path) if eval_path.exists() else None
    ok, errors, counts = validate_rows(rows, expected)
    if not ok:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "OK",
        f"rows={len(rows)}",
        " ".join(f"{k}={v}" for k, v in sorted(counts.items())),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
