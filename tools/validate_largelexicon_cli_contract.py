#!/usr/bin/env python3
"""Validate the stable local largelexicon CLI/JSONL consumer contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "fusha_largelexicon_cli.py"
WORKLIST = ROOT / "qamus" / "examples" / "mode_a_all_qword" / "largelexicon-qamus-mode-a-worklist.sample.jsonl"


def _run(args: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        data = json.loads(proc.stdout)
    except Exception:
        data = {"stdout": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, data


def validate() -> list[str]:
    errors: list[str] = []
    code, data = _run(["analyze-token", "--surface", "خَاضُوا", "--mode", "mode_c"])
    if code != 0 or data.get("schema") != "fusha/largelexicon-cli/analyze-token@1":
        errors.append("analyze-token did not return the expected schema")
    token = ((data.get("parse") or {}).get("tokens") or [{}])[0]
    if token.get("confidence_gate") not in {"likely_from_internal_pattern", "pending_context"}:
        errors.append(f"analyze-token unexpected confidence gate {token.get('confidence_gate')!r}")
    if (data.get("parse") or {}).get("summary", {}).get("live_writes") != 0:
        errors.append("analyze-token must report zero live writes")
    if data.get("safe_for_qamus_executor_autopromote") is not False:
        errors.append("analyze-token must not autopromote arbitrary parser output")

    code, data = _run(["analyze-token", "--surface", "الله", "--mode", "mode_c"])
    if code != 0:
        errors.append("analyze-token failed for Allah collision smoke")
    if data.get("safe_for_public_hover") is not False or data.get("safe_for_qamus_executor_autopromote") is not False:
        errors.append("Allah analyze-token must remain non-autopromotable without source-address proof")
    if data.get("safety_gate") not in {"likely_from_internal_pattern", "lexical_collision_requires_context", "pending_context", "ambiguous"}:
        errors.append(f"Allah analyze-token unexpected safety gate {data.get('safety_gate')!r}")

    code, data = _run(["analyze-token", "--surface", "من", "--mode", "mode_c"])
    token = ((data.get("parse") or {}).get("tokens") or [{}])[0]
    top = (token.get("morphology_candidates") or [{}])[0]
    if top.get("pos") == "verb" or top.get("lemma") == "مَنَّ":
        errors.append("من must not top-rank the verb مَنَّ in arbitrary largelexicon CLI output")
    if data.get("safety_gate") not in {"pending_context", "lexical_collision_requires_context", "ambiguous"}:
        errors.append(f"من analyze-token should route to a context/ambiguity gate, got {data.get('safety_gate')!r}")

    code, data = _run(["analyze-card", "--text", "إنما الأعمال بالنيات", "--card-id", "smoke-card"])
    if code != 0 or data.get("schema") != "fusha/largelexicon-cli/analyze-card@1":
        errors.append("analyze-card did not return the expected schema")
    if not data.get("rows"):
        errors.append("analyze-card must return at least one row")
    if any(row.get("safe_for_qamus_executor_autopromote") is not False for row in data.get("rows") or []):
        errors.append("analyze-card rows must not autopromote parser output")

    code, data = _run(["validate-mode-a", "--input", str(WORKLIST)])
    if code != 0 or not data.get("ok"):
        errors.append("validate-mode-a CLI path failed on the bundled worklist sample")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "hover.jsonl"
        code, data = _run(["project-hover", "--input", str(WORKLIST), "--out", str(out)])
        if code != 0 or data.get("schema") != "fusha/largelexicon-cli/project-hover@1":
            errors.append("project-hover did not return the expected schema")
        if not out.exists() or out.stat().st_size == 0:
            errors.append("project-hover did not write a candidate JSONL file")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon CLI contract.")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
