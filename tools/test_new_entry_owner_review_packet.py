#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for the new-entry owner review packet builder."""
import json
import tempfile
from pathlib import Path

import build_new_entry_owner_review_packet as B


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proposals = root / "proposals.jsonl"
        out_json = root / "packet.json"
        out_md = root / "packet.md"
        write_jsonl(proposals, [
            {
                "proposed_entry_id": "PROPOSE:aaa",
                "root": "ا ا ا",
                "headword_candidate": "آ",
                "forms_observed": ["آ"],
                "example_locs": ["1:1:1"],
                "occurrences": 3,
                "expected_coverage_unlock": 3,
                "definition_draft": "",
                "why_existing_insufficient": "no Qamus entry",
                "sarf_procedure": "procedures/qamus-entry-authoring.md",
                "nahw_procedure": "qamus-entry-authoring",
                "gate": "owner",
                "public_provenance_clean": True,
            },
            {
                "proposed_entry_id": "PROPOSE:bbb",
                "root": "ب ب ب",
                "headword_candidate": "ب",
                "forms_observed": ["ب"],
                "example_locs": ["2:2:2"],
                "occurrences": 9,
                "expected_coverage_unlock": 9,
                "definition_draft": "",
                "why_existing_insufficient": "no Qamus entry",
                "sarf_procedure": "procedures/qamus-entry-authoring.md",
                "nahw_procedure": "qamus-entry-authoring",
                "gate": "owner",
                "public_provenance_clean": True,
            },
        ])
        summary = B.build_packet(str(proposals), str(out_json), str(out_md))
        assert summary["proposal_count"] == 2
        assert summary["coverage_unlock"] == 12
        packet = json.loads(out_json.read_text(encoding="utf-8"))
        assert packet["proposals"][0]["root"] == "ب ب ب"
        assert "# New Entry Owner Review Packet 002" in out_md.read_text(encoding="utf-8")
    print("new-entry owner review packet self-test OK")


if __name__ == "__main__":
    main()
