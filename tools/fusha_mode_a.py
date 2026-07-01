"""Fixture-first Qamus Mode A analysis helpers.

Mode A is the source-addressed Qamus/RH-LIVE lane.  This module intentionally
does not claim arbitrary-text parsing.  It turns a visible Qamus qword row into
the small set of artifacts needed for a public-safe hover projection plus a
private trace and reverse edge manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

PUBLIC_BOUNDARY = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "external_source_names_public": False,
    "internal_provenance_public": False,
}

FRESHNESS_KEYS = {
    "generated_at",
    "generated_by",
    "source_head",
    "source_branch",
    "supersedes",
    "stale_after",
    "status",
}

ALLOWED_QG_CLASSES = {
    "qg-adjective",
    "qg-article",
    "qg-case",
    "qg-conjunction",
    "qg-derivative-prefix",
    "qg-dual-suffix",
    "qg-lam",
    "qg-ma-particle",
    "qg-negative",
    "qg-noun",
    "qg-noun-stem",
    "qg-object-pronoun",
    "qg-oath",
    "qg-particle",
    "qg-plural-suffix",
    "qg-preposition",
    "qg-pronoun",
    "qg-proper-noun",
    "qg-relative",
    "qg-result",
    "qg-result-fa",
    "qg-subject-pronoun",
    "qg-verb",
    "qg-verb-prefix",
    "qg-verb-stem",
    "qg-vocative",
}

FORBIDDEN_PUBLIC_SUBSTRINGS = {
    "mcp",
    "tafsir",
    "qac",
    "quran.com",
    "quranic arabic corpus",
    "/srv/",
    "c:\\",
    "source photo",
    "source-photo",
    "ocr",
    "codex",
}

ARABIC_DIACRITICS = set("\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0653\u0654\u0655\u0670")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            clean = {k: v for k, v in row.items() if k != "_line_no"}
            handle.write(json.dumps(clean, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def repo_path(path_value: str | Path, base: Path | None = None) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (base or REPO_ROOT) / path


def has_arabic_diacritic(text: str) -> bool:
    return any(ch in ARABIC_DIACRITICS for ch in text)


def _segment(surface: str, role: str, qg_class: str, gloss: str) -> dict[str, str]:
    return {
        "surface": surface,
        "role": role,
        "qg_class": qg_class,
        "gloss": gloss,
    }


def _default_segments(surface: str) -> list[dict[str, str]]:
    return [_segment(surface, "token", "qg-noun-stem", surface)]


def analyze_surface(surface: str) -> dict[str, Any]:
    """Return conservative authored analysis for the Mode A smoke surfaces."""

    table: dict[str, dict[str, Any]] = {
        "مَن": {
            "segments": [_segment("مَن", "relative_or_conditional", "qg-relative", "whoever")],
            "morphology": {"pos": "function_token", "root": None, "form": None},
            "syntax": {"function": "relative_or_conditional_pronoun", "gate": "nahw_reviewed_fixture"},
            "hover": "whoever",
        },
        "كَانَ": {
            "segments": [_segment("كَانَ", "verb_stem", "qg-verb-stem", "was")],
            "morphology": {"pos": "verb", "root": "ك و ن", "form": "I perfect active 3ms"},
            "syntax": {"function": "defective_verb", "gate": "sarf_nahw_fixture"},
            "hover": "was",
        },
        "عَدُوًّا": {
            "segments": [_segment("عَدُوًّا", "noun_host", "qg-noun-stem", "enemy")],
            "morphology": {"pos": "noun", "root": "ع د و", "form": "accusative indefinite"},
            "syntax": {"function": "predicate_or_complement", "gate": "nahw_reviewed_fixture"},
            "hover": "enemy",
        },
        "لِّلَّهِ": {
            "segments": [
                _segment("لِّ", "preposition", "qg-preposition", "to / against"),
                _segment("لَّهِ", "divine_name_host", "qg-proper-noun", "Allah"),
            ],
            "morphology": {"pos": "preposition_plus_proper_name", "root": None, "form": "lam + proper name"},
            "syntax": {"function": "preposition_with_majrur_host", "gate": "nahw_reviewed_fixture"},
            "hover": "to Allah / against Allah",
        },
        "وَمَلَـٰٓئِكَتِهِ": {
            "segments": [
                _segment("وَ", "conjunction", "qg-conjunction", "and"),
                _segment("مَلَـٰٓئِكَتِ", "noun_host", "qg-noun-stem", "angels"),
                _segment("هِ", "possessive_pronoun", "qg-pronoun", "His"),
            ],
            "morphology": {"pos": "conjunction_plus_noun_plus_pronoun", "root": "م ل ك", "form": "plural + 3ms possessive"},
            "syntax": {"function": "conjoined_majrur_with_possessive", "gate": "nahw_reviewed_fixture"},
            "hover": "and His angels",
        },
        "وَرُسُلِهِۦ": {
            "segments": [
                _segment("وَ", "conjunction", "qg-conjunction", "and"),
                _segment("رُسُلِ", "noun_host", "qg-noun-stem", "messengers"),
                _segment("هِۦ", "possessive_pronoun", "qg-pronoun", "His"),
            ],
            "morphology": {"pos": "conjunction_plus_noun_plus_pronoun", "root": "ر س ل", "form": "plural + 3ms possessive"},
            "syntax": {"function": "conjoined_majrur_with_possessive", "gate": "nahw_reviewed_fixture"},
            "hover": "and His messengers",
        },
        "وَجِبْرِيلَ": {
            "segments": [
                _segment("وَ", "conjunction", "qg-conjunction", "and"),
                _segment("جِبْرِيلَ", "proper_name_host", "qg-proper-noun", "Gabriel"),
            ],
            "morphology": {"pos": "conjunction_plus_proper_name", "root": None, "form": "proper name"},
            "syntax": {"function": "conjoined_proper_name", "gate": "nahw_reviewed_fixture"},
            "hover": "and Gabriel",
        },
        "وَمِيكَىٰلَ": {
            "segments": [
                _segment("وَ", "conjunction", "qg-conjunction", "and"),
                _segment("مِيكَىٰلَ", "proper_name_host", "qg-proper-noun", "Michael"),
            ],
            "morphology": {"pos": "conjunction_plus_proper_name", "root": None, "form": "proper name"},
            "syntax": {"function": "conjoined_proper_name", "gate": "nahw_reviewed_fixture"},
            "hover": "and Michael",
        },
        "فَإِنَّ": {
            "segments": [
                _segment("فَ", "result_particle", "qg-result", "then / so"),
                _segment("إِنَّ", "emphasis_particle", "qg-particle", "indeed"),
            ],
            "morphology": {"pos": "particle_cluster", "root": None, "form": "fa + inna"},
            "syntax": {"function": "result_plus_emphasis", "gate": "nahw_reviewed_fixture"},
            "hover": "then indeed",
        },
        "ٱللَّهَ": {
            "segments": [_segment("ٱللَّهَ", "proper_name_host", "qg-proper-noun", "Allah")],
            "morphology": {"pos": "proper_name", "root": None, "form": "accusative divine name"},
            "syntax": {"function": "subject_or_inna_noun_by_context", "gate": "nahw_reviewed_fixture"},
            "hover": "Allah",
        },
        "عَدُوٌّ": {
            "segments": [_segment("عَدُوٌّ", "noun_host", "qg-noun-stem", "enemy")],
            "morphology": {"pos": "noun", "root": "ع د و", "form": "nominative indefinite"},
            "syntax": {"function": "predicate", "gate": "nahw_reviewed_fixture"},
            "hover": "enemy",
        },
        "لِّلْكَـٰفِرِينَ": {
            "segments": [
                _segment("لِّ", "preposition", "qg-preposition", "to / for"),
                _segment("لْ", "definite_article", "qg-article", "the"),
                _segment("كَـٰفِرِينَ", "noun_host", "qg-noun-stem", "disbelievers"),
            ],
            "morphology": {"pos": "preposition_plus_definite_plural_noun", "root": "ك ف ر", "form": "lam + article + sound plural"},
            "syntax": {"function": "preposition_with_majrur_host", "gate": "nahw_reviewed_fixture"},
            "hover": "for the disbelievers",
        },
        "أَمْ": {
            "segments": [_segment("أَمْ", "interrogative_or_disjunctive_particle", "qg-particle", "or / rather")],
            "morphology": {"pos": "function_token", "root": None, "form": None},
            "syntax": {"function": "am_particle_requires_context", "gate": "nahw_reviewed_fixture"},
            "hover": "or / rather",
        },
        "لَهُمْ": {
            "segments": [
                _segment("لَ", "preposition", "qg-preposition", "for / belongs to"),
                _segment("هُمْ", "pronoun_host", "qg-pronoun", "them"),
            ],
            "morphology": {"pos": "preposition_plus_pronoun", "root": None, "form": "lam + 3mp pronoun"},
            "syntax": {"function": "preposition_with_attached_pronoun", "gate": "nahw_reviewed_fixture"},
            "hover": "for them / belongs to them",
        },
        "تَعْبُدُوا۟": {
            "segments": [
                _segment("تَ", "imperfect_prefix", "qg-verb-prefix", "you all"),
                _segment("عْبُدُ", "verb_stem", "qg-verb-stem", "worship"),
                _segment("وا۟", "subject_marker", "qg-subject-pronoun", "you all"),
            ],
            "morphology": {"pos": "verb", "root": "ع ب د", "form": "I imperfect active/jussive 2mp"},
            "syntax": {"function": "governed_imperfect_verb", "gate": "sarf_nahw_fixture"},
            "hover": "you all worship",
        },
        "ٱلْمُبْطِلُونَ": {
            "segments": [
                _segment("ٱلْ", "definite_article", "qg-article", "the"),
                _segment("مُ", "derivative_prefix", "qg-derivative-prefix", "one who"),
                _segment("بْطِلُ", "participle_host", "qg-adjective", "falsifies"),
                _segment("ونَ", "plural_suffix", "qg-plural-suffix", "plural"),
            ],
            "morphology": {"pos": "active_participle", "root": "ب ط ل", "form": "definite active participle masculine plural"},
            "syntax": {"function": "nominal_participle_by_context", "gate": "sarf_nahw_fixture"},
            "hover": "the falsifiers",
        },
        "أَيَّانَ": {
            "segments": [_segment("أَيَّانَ", "interrogative_time_particle", "qg-particle", "when?")],
            "morphology": {"pos": "function_token", "root": None, "form": None},
            "syntax": {"function": "interrogative_adverbial_particle", "gate": "nahw_reviewed_fixture"},
            "hover": "when?",
        },
    }
    result = table.get(surface, None)
    if result is None:
        result = {
            "segments": _default_segments(surface),
            "morphology": {"pos": "unclassified_fixture_token", "root": None, "form": None},
            "syntax": {"function": "fixture_unclassified", "gate": "manual_review_required"},
            "hover": surface,
        }
    return result


def analyze_source_row(row: dict[str, Any]) -> dict[str, Any]:
    surface = row["displayed_surface"]
    analysis = analyze_surface(surface)
    segments = analysis["segments"]
    return {
        "schema": "fusha/mode-a-analysis@1",
        "row_id": row["row_id"],
        "source_row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "surface": surface,
        "canonical_quran_loc": row["canonical_quran_loc"],
        "canonical_wbw_loc": row["canonical_wbw_loc"],
        "segment_surface": "".join(seg["surface"] for seg in segments),
        "segments": segments,
        "morphology": analysis["morphology"],
        "syntax": analysis["syntax"],
        "public_hover": analysis["hover"],
        "learner_explanation": _learner_explanation(surface, analysis),
        "public_boundary": PUBLIC_BOUNDARY,
        "mode_a_scope": "fixture_thin_slice_only",
    }


def _learner_explanation(surface: str, analysis: dict[str, Any]) -> str:
    pieces = [seg["role"] for seg in analysis["segments"]]
    if len(pieces) == 1:
        return f"{surface} contributes {analysis['hover']} in this source-addressed fixture."
    return f"{surface} is taught as {' + '.join(pieces)}; the hover preserves each visible piece."


def make_public_projection(row: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "qamus/public-hover-projection@1",
        "row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "surface": row["displayed_surface"],
        "canonical_quran_loc": row["canonical_quran_loc"],
        "canonical_wbw_loc": row["canonical_wbw_loc"],
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "public_gloss": analysis["public_hover"],
        "token_contribution": analysis["public_hover"],
        "morphline": _morphline(analysis),
        "segments": analysis["segments"],
        "qg_classes": [seg["qg_class"] for seg in analysis["segments"]],
        "learner_explanation": analysis["learner_explanation"],
        "public_boundary": PUBLIC_BOUNDARY,
        "live_mutation_allowed": False,
    }


def _morphline(analysis: dict[str, Any]) -> str:
    morphology = analysis["morphology"]
    root = morphology.get("root")
    form = morphology.get("form")
    pos = morphology.get("pos")
    if root and form:
        return f"root {root} · {form}"
    if form:
        return form
    return str(pos)


def make_private_trace(row: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "qamus/private-trace@1",
        "row_id": row["row_id"],
        "source_row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "internal_evidence": {
            "source_addressed_fixture": True,
            "sarf_gate": analysis["morphology"],
            "nahw_gate": analysis["syntax"],
            "external_source_labels": [],
        },
        "decision_backlink": f"mode-a-thin-slice:{row['row_id']}",
        "public_boundary": PUBLIC_BOUNDARY,
        "review_state": "fixture_only_not_live_certification",
    }


def make_edge_manifest(row: dict[str, Any]) -> dict[str, Any]:
    rendered_target = f"{row['entry_id']}#{row['card_id']}#{row['qword_index']}"
    forward = [
        f"entry:{row['entry_id']}",
        f"sense:{row['entry_id']}:{row['sense_index']}",
        f"card:{row['card_id']}",
        f"qword:{row['row_id']}",
        f"quran:{row['canonical_quran_loc']}",
        f"wbw:{row['canonical_wbw_loc']}",
        f"payload:{row['row_id']}",
        f"rendered:{rendered_target}",
    ]
    return {
        "schema": "qamus/source-edge-manifest@1",
        "row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "forward_trace": forward,
        "reverse_trace": list(reversed(forward)),
        "rendered_span_target": rendered_target,
        "source_photo_trace_status": row.get("source_photo_trace_status", "fixture_verified"),
        "source_address_crosswalk": row.get("source_address_crosswalk"),
        "orphan_payload": False,
        "orphan_rendered_span": False,
    }


def make_rendered_fixture(row: dict[str, Any], public_projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "qamus/rendered-readback-fixture@1",
        "row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "rendered_span_target": f"{row['entry_id']}#{row['card_id']}#{row['qword_index']}",
        "text_content": row["displayed_surface"],
        "expected_surface": row["displayed_surface"],
        "hover_present": True,
        "qg_classes": public_projection["qg_classes"],
        "live_readback": False,
        "fixture_readback_pass": True,
    }


def make_flywheel_artifact(row: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    routes = ["qamus_mode_a_validator", "curriculum"]
    if analysis["morphology"].get("pos") in {"verb", "active_participle", "preposition_plus_definite_plural_noun"}:
        routes.append("sarf")
    if analysis["syntax"].get("gate"):
        routes.append("nahw")
    return {
        "schema": "qamus/flywheel-artifact@1",
        "row_id": row["row_id"],
        "entry_id": row["entry_id"],
        "card_id": row["card_id"],
        "routes": sorted(set(routes)),
        "reusable_lesson": analysis["learner_explanation"],
        "future_unlock": "turn repeated qword coloring/hover defects into reusable sarf/nahw/parser fixtures",
    }


def materialize(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, int]:
    analyses: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    rendered: list[dict[str, Any]] = []
    flywheel: list[dict[str, Any]] = []
    for row in rows:
        analysis = analyze_source_row(row)
        projection = make_public_projection(row, analysis)
        analyses.append(analysis)
        projections.append(projection)
        traces.append(make_private_trace(row, analysis))
        edges.append(make_edge_manifest(row))
        rendered.append(make_rendered_fixture(row, projection))
        flywheel.append(make_flywheel_artifact(row, analysis))
    write_jsonl(out_dir / "analysis.jsonl", analyses)
    write_jsonl(out_dir / "public-hover-projection.jsonl", projections)
    write_jsonl(out_dir / "private-trace.jsonl", traces)
    write_jsonl(out_dir / "source-edge-manifest.jsonl", edges)
    write_jsonl(out_dir / "rendered-readback.fixture.jsonl", rendered)
    write_jsonl(out_dir / "flywheel-artifacts.jsonl", flywheel)
    return {
        "source_rows": len(rows),
        "analysis_rows": len(analyses),
        "public_projection_rows": len(projections),
        "private_trace_rows": len(traces),
        "edge_manifest_rows": len(edges),
        "rendered_fixture_rows": len(rendered),
        "flywheel_rows": len(flywheel),
    }


def load_bundle(bundle_path: Path) -> dict[str, Any]:
    bundle = read_json(bundle_path)
    base = bundle_path.parent
    bundle["_base_dir"] = str(base)
    return bundle


def bundle_artifact_path(bundle: dict[str, Any], key: str) -> Path:
    artifacts = bundle["artifacts"]
    base = Path(bundle["_base_dir"])
    return repo_path(artifacts[key], base=base)


def main_materialize(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize Qamus Mode A thin-slice artifacts.")
    parser.add_argument("--source-rows", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    rows = read_jsonl(Path(args.source_rows))
    counts = materialize(rows, Path(args.out_dir))
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_materialize())
