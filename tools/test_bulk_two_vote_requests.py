#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for bulk two-vote request packet generation."""
import json
import tempfile
from pathlib import Path

import build_bulk_two_vote_requests as B


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    row = {
        "loc": "7:157:2",
        "surface_ar": "يَتَّبِعُونَ",
        "strict_nk": "يتبعون",
        "blocker": "stem_base_unknown",
        "root_cause": "missing_form_variant_on_existing_entry",
        "qac_root": "تبع",
        "qac_pos": "V",
        "qamus_entry_candidate": "5d89e690256d",
        "qamus_entry_headword": "ٱتَّبَعَ",
        "qamus_entry_match_type": "root_match",
        "pos_agreement": "agree",
        "sarf_procedure": "procedures/verb-form.md",
        "nahw_procedure": None,
        "suggested_lane": "form_variant",
        "deterministic_resolvable": False,
        "risk": "medium",
        "gate": "two_vote",
        "public_payload_allowed": "yes",
        "public_provenance_clean": True,
        "ayah_context": "ٱلَّذِينَ يَتَّبِعُونَ ٱلرَّسُولَ",
        "blocker_if_not_resolved": "missing_form_variant_on_existing_entry: requires form_variant with two_vote gate",
    }
    owner = dict(row)
    owner["loc"] = "7:165:10"
    owner["gate"] = "owner"
    owner["suggested_lane"] = "new_entry_proposal"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        table = root / "table.jsonl"
        out = root / "requests.jsonl"
        manifest = root / "manifest.json"
        report = root / "requests.md"
        second = dict(row)
        second["loc"] = "7:158:3"
        second["suggested_lane"] = "token_irab"
        exclude = root / "exclude.jsonl"
        write_jsonl(table, [row, second, owner])
        write_jsonl(exclude, [{"loc": "7:157:2"}])
        summary = B.build_requests(
            str(table), str(out), str(manifest), limit=1000, chunk_size=1,
            report_md_path=str(report), exclude_loc_paths=[str(exclude)],
            only_lanes=["token_irab"],
        )
        assert summary["rows"] == 1, summary
        req = json.loads(out.read_text(encoding="utf-8").strip())
        assert req["loc"] == "7:158:3"
        assert req["vote_lenses"] == ["sarf-primary", "nahw-primary"]
        assert req["public_boundary"]["src"] == "qamus"
        assert req["public_boundary"]["kind"] == "authored"
        assert req["public_boundary"]["lang"] == "en"
        assert "owner" not in req["gate"]
        assert summary["excluded_locs"] == 1
        assert summary["only_lanes"] == ["token_irab"]
        assert (root / "requests_chunks" / "chunk_001.jsonl").exists()
        report_text = report.read_text(encoding="utf-8")
        assert summary["request_file"] in report_text
        assert "bulk_twovote_requests_batch_001.jsonl" not in report_text
    print("bulk two-vote request builder self-test OK")


if __name__ == "__main__":
    main()
