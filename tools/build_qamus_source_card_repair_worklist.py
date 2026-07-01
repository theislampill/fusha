#!/usr/bin/env python3
"""Build source-card/example repair worklists from largelexicon repair packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from largelexicon_common import (
    PUBLIC_BOUNDARY,
    QWORD_DENOMINATOR_SOURCE_REPAIR,
    SOURCE_CARD_REPAIR_META,
    SOURCE_CARD_REPAIR_WORKLIST,
    freshness,
    repo_rel,
    sha256_file,
    write_json,
    write_jsonl,
)


def _repair_rows(source_path: Path = QWORD_DENOMINATOR_SOURCE_REPAIR) -> list[dict[str, Any]]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for index, repair in enumerate(source.get("repairs") or [], start=1):
        source_keys = repair.get("source_keys") or []
        source_key = source_keys[0] if source_keys else None
        hint = repair.get("repair_hint") or {}
        row = {
            "schema": "qamus/source-card-example-repair-worklist@1",
            "row_id": f"source-card-repair:{source_key or 'unknown'}:{repair.get('entry_id')}:{index:03d}",
            "entry_id": repair.get("entry_id"),
            "source_key": source_key,
            "source_keys": source_keys,
            "headword": repair.get("headword"),
            "forms": repair.get("forms") or [],
            "section": repair.get("section"),
            "total_uses": repair.get("total_uses"),
            "source_photo_ref": hint.get("source_photo_page_image"),
            "candidate_quran_ref": hint.get("candidate_quran_ref"),
            "source_card_text_status": "needs_owner_or_source_confirmation",
            "canonical_crosswalk_status": "not_started_source_card_missing",
            "repair_status": "owner_source_confirmation_required",
            "required_decision": "confirm_or_edit_source_card_example_before_qword_regeneration",
            "allowed_decisions": ["accept", "edit", "reject", "needs_scholar_after_source_fix"],
            "next_action": repair.get("next_action"),
            "private_evidence_policy": "raw external evidence, image-derived text, and acquisition responses stay private; public projection is Qamus-authored only",
            "source_dependencies": [
                {"kind": "qword_denominator_source_repair", "id": repair.get("entry_id"), "source_key": source_key},
                {"kind": "entry", "id": repair.get("entry_id")},
            ],
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "live_mutation_allowed": False,
        }
        rows.append(row)
    return rows


def build(out_path: Path = SOURCE_CARD_REPAIR_WORKLIST) -> dict[str, Any]:
    rows = _repair_rows()
    write_jsonl(out_path, rows)
    meta = {
        "schema": "qamus/source-card-example-repair-worklist-meta@1",
        **freshness(status="active", stale_after="qamus_qword_denominator_source_repair_change"),
        "row_count": len(rows),
        "worklist_path": repo_rel(out_path),
        "worklist_sha256": sha256_file(out_path),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "first_required_repair": "n993",
        "claim_boundary": "source-card repair worklist only; not live Qamus mutation or hover deployment",
    }
    write_json(SOURCE_CARD_REPAIR_META, meta)
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=SOURCE_CARD_REPAIR_WORKLIST)
    args = parser.parse_args()
    meta = build(args.out)
    print(
        json.dumps(
            {
                "ok": True,
                "row_count": meta["row_count"],
                "worklist_path": meta["worklist_path"],
                "worklist_sha256": meta["worklist_sha256"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
