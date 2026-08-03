#!/usr/bin/env python3
"""Project largelexicon Mode A worklist rows into candidate/packet rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_mode_a import ALLOWED_QG_CLASSES
from fusha_standalone_parse import parse_text
from largelexicon_common import PUBLIC_BOUNDARY, read_jsonl, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "qamus" / "examples" / "mode_a_all_qword" / "largelexicon-qamus-mode-a-worklist.sample.jsonl"
DEFAULT_OUT = ROOT / "qamus" / "examples" / "largelexicon" / "hover-candidates.sample.jsonl"


def _project(row: dict) -> dict:
    parsed = parse_text(row["visible_surface"], document_id=row["row_id"], db="largelexicon")
    token = (parsed.get("tokens") or [{}])[0]
    segments = token.get("qg_segments") or []
    collision = token.get("collision")
    parser_gate = token.get("confidence_gate")
    missing_source = not row.get("canonical_quran_loc") or not row.get("canonical_wbw_loc")
    bad_classes = sorted({seg.get("class") for seg in segments if seg.get("class") not in ALLOWED_QG_CLASSES})
    if collision:
        # I3 (resolved): a withheld stem must never be asked to reconstruct the
        # full visible_surface and never carries a gloss, but a `stem_identity`
        # collision already retains only an ordered, non-overlapping, already-
        # safe (class-neutralized) SUBSET of qg_segments (parser R7 /
        # _scope_collision_segments) -- the projector no longer discards that
        # real, already-abstained partial coverage. Any other scope (whole_token,
        # or no scope key at all, e.g. competing_segmentation/unsafe_bare_match)
        # empties qg_segments upstream, so there is nothing safe to concatenate.
        token_contribution = None
        if collision.get("scope") == "stem_identity" and segments:
            segment_surface = "".join(seg.get("surface", "") for seg in segments)
            segment_coverage = "partial"
        else:
            segment_surface = None
            segment_coverage = "none"
        status = "parser_packet"
        route = "executor_parser_or_sarf_nahw_packet_ready"
    else:
        segment_surface = "".join(seg.get("surface", "") for seg in segments)
        segment_coverage = "complete"
        token_contribution = (token.get("hover_preview") or {}).get("token_contribution_gloss")
        if bad_classes:
            status = "validator_packet"
            route = "executor_validator_patch_ready"
        elif missing_source:
            status = "source_crosswalk_packet"
            route = "executor_source_crosswalk_patch_ready"
        elif parser_gate in {"likely_from_internal_pattern", "pending_context"}:
            status = "candidate_for_executor_validation"
            route = "executor_validation_queue"
        else:
            status = "parser_packet"
            route = "executor_parser_or_sarf_nahw_packet_ready"
    return {
        "schema": "qamus/largelexicon-hover-candidate@1",
        "row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "qword_index": row["qword_index"],
        "visible_surface": row["visible_surface"],
        "segment_surface": segment_surface,
        "segment_coverage": segment_coverage,
        "segments": segments,
        "qg_classes": [seg.get("class") for seg in segments],
        "token_contribution": token_contribution,
        "collision": collision,
        "parser_gate": parser_gate,
        "status": status,
        "route": route,
        "canonical_quran_loc": row.get("canonical_quran_loc"),
        "canonical_wbw_loc": row.get("canonical_wbw_loc"),
        "source_crosswalk_required": missing_source,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "live_mutation_allowed": False,
        "claim": "candidate or packet for Qamus executor; not live Qamus progress",
    }


def project(input_path: Path, output_path: Path) -> dict:
    rows = read_jsonl(input_path)
    projected = [_project(row) for row in rows]
    write_jsonl(output_path, projected)
    counts: dict[str, int] = {}
    for row in projected:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    try:
        out = str(output_path.relative_to(ROOT))
    except ValueError:
        out = str(output_path)
    return {"rows": len(projected), "counts": counts, "out": out}


def _row(surface: str) -> dict:
    return {
        "row_id": "self-test-" + surface, "entry_id": "self-test", "card_id": "self-test:c1",
        "qword_index": 1, "visible_surface": surface,
        "canonical_quran_loc": "quran:1:1:1", "canonical_wbw_loc": "quran-wbw:1:1:1",
    }


def _self_test() -> list[str]:
    """I3 (red-first): segment_coverage must type complete/partial/none and
    segment_surface must be the ordered concatenation of only the already-safe
    retained segments for a stem_identity collision -- never the full visible
    surface, and never a leftover null when real partial coverage exists."""
    failures: list[str] = []

    complete = _project(_row("بالله"))
    if complete.get("segment_coverage") != "complete" or complete.get("segment_surface") != "بالله":
        failures.append("complete: بالله must be segment_coverage=complete, segment_surface=بالله, got %r/%r"
                         % (complete.get("segment_coverage"), complete.get("segment_surface")))

    partial_prep = _project(_row("بِهِمُ"))
    if partial_prep.get("segment_coverage") != "partial" or partial_prep.get("segment_surface") != "بِ":
        failures.append("partial: بِهِمُ must retain only the preposition span (segment_surface=بِ), got coverage=%r surface=%r"
                         % (partial_prep.get("segment_coverage"), partial_prep.get("segment_surface")))
    if partial_prep.get("token_contribution") is not None:
        failures.append("partial: بِهِمُ must keep token_contribution null under collision")

    partial_clitic = _project(_row("أَعْمَٰلَهُمْ"))
    if partial_clitic.get("segment_coverage") != "partial" or partial_clitic.get("segment_surface") != "هُمْ":
        failures.append("partial: أَعْمَٰلَهُمْ must retain only the clitic_undetermined suffix, got coverage=%r surface=%r"
                         % (partial_clitic.get("segment_coverage"), partial_clitic.get("segment_surface")))

    none_cov = _project(_row("لما"))
    if none_cov.get("segment_coverage") != "none" or none_cov.get("segment_surface") is not None:
        failures.append("none: لما (competing_segmentation, no retained segments) must be coverage=none, surface=null, got %r/%r"
                         % (none_cov.get("segment_coverage"), none_cov.get("segment_surface")))

    # unknown-role mutation (red-first): an untriaged qg role must be withheld
    # by the parser's own _scope_collision_segments (fail-closed), and the
    # projector must recompute coverage from whatever segments actually survive
    # that withholding rather than trusting a stale/cached count. Simulate the
    # post-withholding state directly (parse_text already guarantees no
    # untriaged role reaches qg_segments) and confirm coverage tracks it.
    from fusha_standalone_parse import _scope_collision_segments

    untriaged = _scope_collision_segments([
        {"role": "totally_untriaged_future_role", "surface": "x", "class": "qg-noun"},
    ])
    if untriaged:
        failures.append("unknown-role mutation: an untriaged role must be withheld, not retained: %r" % untriaged)
    # With every segment withheld, a stem_identity row degrades to no retained
    # coverage at all -- recomputing must yield none/null, not a stale partial.
    empty_after_withholding = [] if not untriaged else untriaged
    surface_after = "".join(seg.get("surface", "") for seg in empty_after_withholding)
    coverage_after = "partial" if empty_after_withholding else "none"
    if coverage_after != "none" or surface_after:
        failures.append("unknown-role mutation: coverage must recompute to none/null once the only segment is withheld")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Project largelexicon Qamus hover candidates.")
    parser.add_argument("--input", default=str(DEFAULT_IN))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        failures = _self_test()
        for f in failures:
            print("FAIL " + f)
        if not failures:
            print("ok   project_largelexicon_qamus_hover_candidates self-test: segment_coverage typing")
        return 1 if failures else 0
    result = project(Path(args.input), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
