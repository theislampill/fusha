#!/usr/bin/env python3
"""Stable local CLI contract for the largelexicon parser/checker lane.

This is intentionally a local JSON/JSONL contract, not an HTTP service. It
keeps Mode A/B/C consumers on a narrow machine interface while the internals
continue to evolve.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fusha_morph_analyze import analyze_surface  # noqa: E402
from fusha_standalone_parse import parse_text  # noqa: E402
from project_largelexicon_qamus_hover_candidates import project as project_hover_file  # noqa: E402
from validate_rh_live_source_addressed_candidates import gate_file as gate_rh_live_candidates_file  # noqa: E402
from validate_largelexicon_qamus_mode_a import validate as validate_mode_a_file  # noqa: E402


def _read_json_or_jsonl(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []
    if not text.strip():
        return rows
    if text.lstrip().startswith("["):
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    for line in text.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _dump(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def _token_safety(parsed: dict) -> dict:
    tokens = parsed.get("tokens") or []
    gates = {tok.get("confidence_gate") for tok in tokens}
    if not tokens:
        gate = "blocked"
    elif len(tokens) == 1:
        gate = tokens[0].get("confidence_gate") or "blocked"
    elif "lexical_collision_requires_context" in gates:
        gate = "lexical_collision_requires_context"
    elif "pending_context" in gates:
        gate = "pending_context"
    elif "ambiguous" in gates:
        gate = "ambiguous"
    else:
        gate = "preview_candidate"
    route_map = {
        "lexical_collision_requires_context": ["sarf_collision_review", "nahw_function_review"],
        "pending_context": ["nahw_function_review"],
        "ambiguous": ["sarf_collision_review"],
        "blocked": ["validator_packet"],
    }
    preview_candidate = gate in {"preview_candidate", "likely_from_internal_pattern"} and bool(tokens)
    return {
        "analysis_status": "preview_candidate" if preview_candidate else "candidate_only",
        "safety_gate": gate,
        "safe_for_public_hover": False,
        "safe_for_qamus_executor_autopromote": False,
        "routes": route_map.get(gate, ["executor_validation_required"]),
    }


def analyze_token(args: argparse.Namespace) -> int:
    parsed = parse_text(args.surface, document_id=args.document_id or f"largelexicon-token:{args.surface}", db="largelexicon")
    morph = analyze_surface(args.surface, db_name="largelexicon")
    _dump(
        {
            "schema": "fusha/largelexicon-cli/analyze-token@1",
            "mode": args.mode,
            "surface": args.surface,
            **_token_safety(parsed),
            "parse": parsed,
            "morphology": morph,
            "claim": "source-clean candidate analysis; not live Qamus progress or arbitrary-text certification",
        }
    )
    return 0


def analyze_card(args: argparse.Namespace) -> int:
    rows = _read_json_or_jsonl(Path(args.input)) if args.input else [{"card_id": args.card_id or "stdin-card", "text": args.text}]
    out = []
    for row in rows:
        text = row.get("text") or row.get("card_text") or row.get("ar") or ""
        out.append(
            {
                "schema": "fusha/largelexicon-cli/analyze-card-row@1",
                "card_id": row.get("card_id"),
                "entry_id": row.get("entry_id"),
                "parse": parse_text(text, document_id=row.get("card_id"), db="largelexicon"),
                "claim": "card analysis candidate; source-address certification remains a Mode A gate",
            }
        )
        out[-1].update(_token_safety(out[-1]["parse"]))
    _dump({"schema": "fusha/largelexicon-cli/analyze-card@1", "rows": out})
    return 0


def project_hover(args: argparse.Namespace) -> int:
    result = project_hover_file(Path(args.input), Path(args.out))
    _dump({"schema": "fusha/largelexicon-cli/project-hover@1", **result})
    return 0


def validate_mode_a(args: argparse.Namespace) -> int:
    errors = validate_mode_a_file(Path(args.input))
    _dump({"schema": "fusha/largelexicon-cli/validate-mode-a@1", "ok": not errors, "errors": errors})
    return 1 if errors else 0


def gate_rh_live_candidates(args: argparse.Namespace) -> int:
    report = gate_rh_live_candidates_file(
        Path(args.input),
        Path(args.accepted_out) if args.accepted_out else None,
        Path(args.held_out) if args.held_out else None,
        Path(args.report_out) if args.report_out else None,
    )
    _dump({**report, "schema": "fusha/largelexicon-cli/gate-rh-live-candidates@1"})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Largelexicon local CLI contract.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyze-token")
    p.add_argument("--surface", required=True)
    p.add_argument("--mode", choices=["mode_a", "mode_b", "mode_c"], default="mode_c")
    p.add_argument("--document-id")
    p.set_defaults(func=analyze_token)

    p = sub.add_parser("analyze-card")
    p.add_argument("--input")
    p.add_argument("--text")
    p.add_argument("--card-id")
    p.set_defaults(func=analyze_card)

    p = sub.add_parser("project-hover")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=project_hover)

    p = sub.add_parser("validate-mode-a")
    p.add_argument("--input", required=True)
    p.set_defaults(func=validate_mode_a)

    p = sub.add_parser("gate-rh-live-candidates")
    p.add_argument("--input", required=True)
    p.add_argument("--accepted-out")
    p.add_argument("--held-out")
    p.add_argument("--report-out")
    p.set_defaults(func=gate_rh_live_candidates)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "command", None) == "analyze-card" and not (args.input or args.text):
        parser.error("analyze-card requires --input or --text")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
