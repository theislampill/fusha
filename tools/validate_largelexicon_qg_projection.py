#!/usr/bin/env python3
"""Validate largelexicon qg projection/candidate rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_mode_a import ALLOWED_QG_CLASSES
from largelexicon_common import public_boundary_errors, read_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "qamus" / "examples" / "largelexicon" / "hover-candidates.sample.jsonl"


SEGMENT_COVERAGE_VALUES = {"complete", "partial", "none"}


def _ordered_subset(pieces: list[str], surface: str) -> bool:
    pos = 0
    for piece in pieces:
        if not piece:
            continue
        idx = surface.find(piece, pos)
        if idx == -1:
            return False
        pos = idx + len(piece)
    return True


def validate(path: Path = DEFAULT_SAMPLE) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing projection sample: {path.relative_to(ROOT)}"]
    rows = read_jsonl(path)
    if len(rows) < 50:
        errors.append("projection sample must contain at least 50 rows")
    statuses: set[str] = set()
    for i, row in enumerate(rows, start=1):
        label = f"{path.name}:{i}"
        statuses.add(row.get("status") or "")
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"{label}: live_mutation_allowed must be false")
        segment_surface = row.get("segment_surface")
        segments = row.get("segments") or []
        collision = row.get("collision") or {}
        # R8: a withheld stem (collision, or a fully empty qg_segments row) is
        # not required to reconstruct visible_surface; every OTHER row still
        # must, so the concatenation invariant is not relaxed for them.
        if segment_surface is not None and not collision and segment_surface != row.get("visible_surface"):
            errors.append(f"{label}: segment_surface does not equal visible_surface")
        if not segments and row.get("token_contribution") is not None:
            errors.append(f"{label}: token_contribution must be null when segments is empty")
        bad = set(row.get("qg_classes") or []) - ALLOWED_QG_CLASSES
        if bad:
            errors.append(f"{label}: unsupported qg classes {sorted(bad)}")
        if row.get("status") not in {
            "candidate_for_executor_validation",
            "source_crosswalk_packet",
            "validator_packet",
            "parser_packet",
        }:
            errors.append(f"{label}: unsupported status {row.get('status')!r}")
        # I3 (resolved): segment_coverage is typed and must agree with the
        # collision/segments state it was derived from, never a stale or
        # unexamined value.
        coverage = row.get("segment_coverage")
        if coverage not in SEGMENT_COVERAGE_VALUES:
            errors.append(f"{label}: segment_coverage must be one of {sorted(SEGMENT_COVERAGE_VALUES)}, got {coverage!r}")
        elif collision:
            if coverage == "complete":
                errors.append(f"{label}: a collision row can never claim segment_coverage=complete")
            if coverage == "partial":
                if collision.get("scope") != "stem_identity":
                    errors.append(f"{label}: segment_coverage=partial requires collision.scope=stem_identity, got {collision.get('scope')!r}")
                if not segments or segment_surface is None:
                    errors.append(f"{label}: segment_coverage=partial requires non-null segment_surface from retained segments")
                elif not _ordered_subset([seg.get("surface", "") for seg in segments], row.get("visible_surface") or ""):
                    errors.append(f"{label}: segment_coverage=partial segment_surface is not an ordered subset of visible_surface")
                if row.get("token_contribution") is not None:
                    errors.append(f"{label}: segment_coverage=partial must keep token_contribution null")
            if coverage == "none" and (segments or segment_surface is not None):
                errors.append(f"{label}: segment_coverage=none must carry no segments and a null segment_surface")
        elif coverage != "complete":
            errors.append(f"{label}: a non-collision row must be segment_coverage=complete, got {coverage!r}")
        errors.extend(public_boundary_errors(row, label))
    if "source_crosswalk_packet" not in statuses:
        errors.append("sample should contain source_crosswalk_packet rows to prove non-live routing")
    if not any((row.get("collision") or {}).get("scope") == "stem_identity" for row in rows):
        errors.append("sample should contain a stem_identity collision row to prove partial coverage typing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon qg projection sample.")
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.sample))
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
