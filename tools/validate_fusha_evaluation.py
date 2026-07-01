"""Validate P4 eval/split/model-card artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Fusha P4 eval artifacts.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    split_dir = ROOT / "fusha" / "parser" / "splits"
    model_card = ROOT / "fusha" / "parser" / "model-cards" / "rule-ranked-baseline.model-card.json"
    report = ROOT / "fusha" / "parser" / "eval" / "parser-stack-smoke-report.json"
    for path in [
        split_dir / "qamus-mode-a-dev.jsonl",
        split_dir / "qamus-mode-a-test.jsonl",
        split_dir / "quranic-function-token-test.jsonl",
        model_card,
        report,
    ]:
        if not path.exists():
            errors.append(f"missing eval artifact: {path}")
    if not errors:
        split_units = []
        for split_path in sorted(split_dir.glob("*.jsonl")):
            for row in read_jsonl(split_path):
                split_units.append((split_path.name, row["unit_id"]))
                if not row.get("source_ledger_refs"):
                    errors.append(f"{split_path}:{row.get('unit_id')}: missing source_ledger_refs")
                if row.get("domain") == "ud_transfer" and "classical_gold" in row.get("allowed_tasks", []):
                    errors.append(f"{split_path}:{row.get('unit_id')}: transfer split claims classical_gold")
        seen_units = {}
        for split_name, unit_id in split_units:
            if unit_id in seen_units:
                errors.append(f"unit {unit_id} appears in both {seen_units[unit_id]} and {split_name}")
            seen_units[unit_id] = split_name
        card = read_json(model_card)
        if card.get("claim") != "rule-ranked smoke baseline only":
            errors.append("model card must keep rule-ranked smoke baseline claim")
        if card.get("trained_model") is not False:
            errors.append("model card must state trained_model=false")
        eval_report = read_json(report)
        if eval_report.get("live_qamus_progress_claimed") is not False:
            errors.append("eval report must not claim live Qamus progress")
        if eval_report.get("aggregate_claim") != "no aggregate NLP-stack score":
            errors.append("eval report must reject aggregate-only scoring")
    result = {
        "ok": not errors,
        "errors": errors,
        "claim": "P4 smoke evidence only; no release/merge/install performed",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
