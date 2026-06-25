#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for deterministic hover decision batch generation."""
import json
import tempfile
from pathlib import Path

import build_bulk_deterministic_hover_decisions as B
import validate_bulk_deterministic_hover_decisions as V


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    good = {
        "loc": "10:30:2",
        "surface_ar": "تَبْلُوا۟",
        "strict_nk": "تبلوا",
        "qac_root": "بلو",
        "qac_pos": "V",
        "qamus_entry_candidate": "e919504a83fa",
        "qamus_entry_headword": "ٱبْتَلَى",
        "qamus_entry_match_type": "exact_form",
        "pos_agreement": "agree",
        "suggested_lane": "auto_resolve_deterministic",
        "deterministic_resolvable": True,
        "deterministic_reason": "single sense, POS-agree, no homograph",
        "proposed_gloss": "to test exhaustively",
        "risk": "low",
        "gate": "auto_rule",
        "public_payload_allowed": "yes",
        "public_provenance_clean": True,
        "blocker_if_not_resolved": "single sense, POS-agree, no homograph",
    }
    skip = dict(good)
    skip["loc"] = "1:2:3"
    skip["deterministic_resolvable"] = False
    skip["gate"] = "two_vote"
    skip["proposed_gloss"] = None

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        table = root / "table.jsonl"
        out = root / "batch.jsonl"
        prov = root / "batch.provenance.jsonl"
        write_jsonl(table, [good, skip])
        result = B.build_batch(str(table), str(out), str(prov))
        assert result["rows"] == 1, result
        public = read_jsonl(out)
        provenance = read_jsonl(prov)
        assert public == [{
            "loc": "10:30:2",
            "gloss": "to test exhaustively",
            "surface": "تَبْلُوا۟",
            "key": "تبلوا",
            "state_id": "state:tok:10:30:2",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "decision_state": "bulk_deterministic_auto_rule",
        }]
        assert provenance[0]["review_status"] == "auto_rule_certified"
        assert V.validate_files(str(out), str(prov), str(table)) == []

        public[0]["gloss"] = "QAC says test"
        write_jsonl(out, public)
        errors = V.validate_files(str(out), str(prov), str(table))
        assert any("external source name" in e for e in errors), errors

    print("bulk deterministic hover decision self-test OK")


if __name__ == "__main__":
    main()
