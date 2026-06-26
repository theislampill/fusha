#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for source-only Phase 4 draft token-decision ledgers."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = os.path.join(ROOT, "tools", "build_phase4_draft_token_decision_ledger.py")
VALIDATOR = os.path.join(ROOT, "tools", "validate_phase4_draft_token_decision_ledger.py")
PLAN_SAMPLE = os.path.join(ROOT, "qamus", "examples", "phase4_hover_decision_plan.sample.jsonl")
SAMPLE_OUT = os.path.join(ROOT, "qamus", "examples", "phase4_draft_token_decision_ledger.sample.jsonl")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", env=env, capture_output=True)


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    assert os.path.exists(BUILDER), "builder missing"
    assert os.path.exists(VALIDATOR), "validator missing"
    builder = load_module(BUILDER, "phase4_draft_token_decision_builder")
    validator = load_module(VALIDATOR, "phase4_draft_token_decision_validator")

    with tempfile.TemporaryDirectory(prefix="phase4-draft-ledger-test-") as td:
        out = os.path.join(td, "draft-token-decisions.jsonl")
        summary = builder.build_draft_ledger(PLAN_SAMPLE, out)
        assert summary["draft_rows"] == 2, summary
        rows = read_jsonl(out)
        assert len(rows) == 2
        first = rows[0]
        assert first["phase"] == "phase4_draft_token_decision_ledger"
        assert first["status"] == "draft_not_applied"
        assert first["token_decision"]["loc"] == "22:18:17"
        assert first["token_decision"]["src"] == "qamus"
        assert first["token_decision"]["kind"] == "authored"
        assert first["token_decision"]["lang"] == "en"
        assert first["identity"]["quran_loc"] == "quran:22:18:17"
        assert first["identity"]["wbw_loc"] == "wbw:22:18:17"
        assert first["apply_policy"]["apply_allowed"] is False
        assert first["apply_policy"]["live_mutation_allowed"] is False
        assert first["apply_policy"]["draft_only"] is True
        assert first["apply_policy"]["append_only_ledger_required"] is True
        assert first["plan_lineage"]["source_plan_id"] == "phase4-hover-decision-plan:22_18_17:c0ffee12"
        count, errors = validator.validate(out, plan_jsonl=PLAN_SAMPLE)
        assert count == 2
        assert errors == [], errors

        bad = os.path.join(td, "bad.jsonl")
        bad_row = dict(first)
        bad_row["token_decision"] = dict(first["token_decision"])
        bad_row["token_decision"]["gloss"] = "copied from QAC"
        builder.write_jsonl(bad, [bad_row])
        _count, bad_errors = validator.validate(bad, plan_jsonl=PLAN_SAMPLE)
        assert bad_errors, "validator must reject public source leakage"

    built = run([sys.executable, BUILDER, PLAN_SAMPLE, "--out-jsonl", SAMPLE_OUT])
    assert built.returncode == 0, built.stderr or built.stdout
    checked = run([sys.executable, VALIDATOR, SAMPLE_OUT, "--plan-jsonl", PLAN_SAMPLE])
    assert checked.returncode == 0, checked.stderr or checked.stdout
    print("Phase 4 draft token-decision ledger self-test OK")


if __name__ == "__main__":
    main()
