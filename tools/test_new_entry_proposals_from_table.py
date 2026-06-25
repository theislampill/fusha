#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for building new-entry proposals from the triangulation table."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main():
    row = {
        "loc": "99:9:9",
        "surface_ar": "بَبَبًا",
        "root_cause": "missing_qamus_entry_candidate",
        "qac_root": "ب ب ب",
        "qac_pos": "N",
        "suggested_lane": "new_entry_proposal",
        "gate": "owner",
        "public_provenance_clean": True,
        "sarf_procedure": "procedures/qamus-entry-authoring.md",
        "nahw_procedure": None,
        "blocker_if_not_resolved": "missing_qamus_entry_candidate: owner must author a new Qamus entry before hover resolution",
    }
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        table = root / "table.jsonl"
        out = root / "proposals.jsonl"
        write_jsonl(table, [row])
        cmd = [
            sys.executable,
            "tools/build_new_entry_proposals.py",
            "--from",
            str(table),
            "--out",
            str(out),
            "--min-occ",
            "1",
        ]
        subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])
        proposals = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        assert len(proposals) == 1, proposals
        proposal = proposals[0]
        assert proposal["root"] == "ب ب ب"
        assert proposal["gate"] == "owner"
        assert proposal["public_provenance_clean"] is True
        assert proposal["definition_draft"] == ""
        assert proposal["affected_token_count"] == 1
        assert proposal["expected_coverage_unlock"] == 1
        assert proposal["sarf_procedure"] == "procedures/qamus-entry-authoring.md"
        assert proposal["why_existing_insufficient"].startswith("no Qamus entry")
    print("new-entry proposal --from triangulation-table self-test OK")


if __name__ == "__main__":
    main()
