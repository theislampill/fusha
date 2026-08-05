#!/usr/bin/env python3
"""Build the owner-facing tranche-001 before/current candidate snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fusha_standalone_parse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(
    "curriculum/l1l6/reports/tranche-001-candidate-snapshot.json"
)
ANALYSIS_DATABASE = "largelexicon"
ANALYSIS_DATABASE_SOURCE = (
    "fusha/lexicon/largelexicon/lemma-source.full.jsonl"
)


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _parse(surface: str) -> dict:
    token = fusha_standalone_parse.parse_text(
        surface, db=ANALYSIS_DATABASE
    )["tokens"][0]
    segments = token.get("qg_segments") or []
    return {
        "analysis_database": ANALYSIS_DATABASE,
        "analysis_database_source": ANALYSIS_DATABASE_SOURCE,
        "roles": [row.get("role") for row in segments],
        "segments": segments,
        "hover_preview": token.get("hover_preview"),
    }


def build() -> dict:
    mulk = _parse("ٱلْمُلْكُ")
    relative = _parse("ٱلَّذِينَ")
    quranan = _parse("قُرْءَانًا")

    ma_row = next(
        row
        for row in _jsonl(ROOT / "nahw/evals/ma-function-occurrence-eval.jsonl")
        if row.get("source_address") == "quran:2:284:2"
    )
    wrv_row = next(
        row
        for row in _jsonl(
            ROOT / "curriculum/drills/keys/weak-root-voice-runtime.keys.jsonl"
        )
        if row.get("id") == "WRV-13-mudaaf-jussive-licensed-shapes"
    )

    mulk_roles = mulk["roles"]
    probes = [
        {
            "probe_id": "mulk-final-kaf",
            "surface": "ٱلْمُلْكُ",
            "before": {
                "defect": "article or root-final kaf could be swallowed by a false clitic split",
                "regression_source": "sarf/evals/false-clitic-split-eval.jsonl#FCS-001",
            },
            "after": mulk,
            "status": (
                "improved"
                if mulk_roles == ["definite_article", "stem"]
                else "analysis_gap_detected"
                if not mulk_roles
                else "regression_detected"
            ),
            "next_owner": (
                None
                if mulk_roles == ["definite_article", "stem"]
                else "tools/fusha_pattern_engine.py"
            ),
        },
        {
            "probe_id": "relative-alladhina",
            "surface": "ٱلَّذِينَ",
            "before": {
                "defect": "lexical relative could be split as article plus remnant",
                "regression_source": "tools/test_fusha_orthography.py#F4LexicalizedRelativeContractionTests",
            },
            "after": relative,
            "status": (
                "improved" if relative["roles"] == ["stem"] else "regression_detected"
            ),
        },
        {
            "probe_id": "quranan-tanwin",
            "surface": "قُرْءَانًا",
            "occurrence_id": "quran:13:31:3",
            "before": {
                "defect": "tanwin support alif could be parsed as the pronoun na",
                "regression_source": "tools/test_fusha_orthography.py#test_quranan_never_produces_a_subject_pronoun",
            },
            "after": quranan,
            "status": (
                "improved"
                if not ({"subject_pronoun", "object_pronoun"} & set(quranan["roles"]))
                else "regression_detected"
            ),
        },
        {
            "probe_id": "ma-rivals",
            "surface": ma_row["surface"],
            "occurrence_id": ma_row["source_address"],
            "before": {
                "defect": "same surface could be forced to one contextual function",
                "regression_source": "nahw/evals/ma-function-occurrence-eval.jsonl#ma-occ-005",
            },
            "after": {
                "decision": ma_row["expected_decision"],
                "rivals": ma_row["expected_rivals"],
                "defect": ma_row["expected_defect"],
            },
            "status": "rivals_preserved",
        },
        {
            "probe_id": "geminate-jussive-rivals",
            "surface": "لَمْ يَمُدَّ / لَمْ يَمْدُدْ",
            "before": {
                "defect": "one licensed jussive realization contradicted another learner surface",
                "regression_source": "tools/test_weak_root_voice_runtime.py#GeminateJussiveInventoryNoContradiction",
            },
            "after": {
                "runtime_item_id": wrv_row["id"],
                "held": wrv_row.get("two_vote_required") is True,
                "licensed_forms": ["لَمْ يَمُدَّ", "لَمْ يَمْدُدْ"],
                "remediation_route": wrv_row["remediation_route"],
            },
            "status": "rivals_preserved_held",
        },
    ]
    return {
        "schema": "curriculum.l1l6_tranche_candidate_snapshot.v1",
        "generator": "tools/build_tranche_candidate_snapshot.py",
        "tranche_id": "tranche-001",
        "posture": "candidate_owner_demo_not_public_projection",
        "public_projection_eligible": False,
        "analysis_database": ANALYSIS_DATABASE,
        "analysis_database_source": ANALYSIS_DATABASE_SOURCE,
        "probes": probes,
        "summary": {
            "probes": len(probes),
            "improved": sum(row["status"] == "improved" for row in probes),
            "rivals_preserved": sum(
                row["status"].startswith("rivals_preserved") for row in probes
            ),
            "regressions_detected": sum(
                row["status"] == "regression_detected" for row in probes
            ),
            "analysis_gaps_detected": sum(
                row["status"] == "analysis_gap_detected" for row in probes
            ),
        },
    }


def _payload() -> bytes:
    return (
        json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / OUTPUT
    payload = _payload()
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        print("wrote %s (%d bytes)" % (OUTPUT.as_posix(), len(payload)))
        return 0
    if args.check:
        if not path.exists() or path.read_bytes() != payload:
            print("FAIL: tranche candidate snapshot is stale")
            return 1
        print("OK: tranche candidate snapshot byte-identical to recompute")
        return 0
    print(payload.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
