#!/usr/bin/env python3
"""Focused regression tests for the T11 function-word certification writer."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import certify_funcword_wave as cert  # noqa: E402
from tools import fact_ledger  # noqa: E402


SOURCE_DIR = cert.resolve_source_dir()


def main() -> int:
    data = cert.validate_inputs(SOURCE_DIR)
    assert len(data["packets"]) == 1_043
    assert len(data["ordinary_certified_packet_ids"]) == 862
    assert len(data["t2_packet_ids"]) == 26
    assert len(data["certified_packet_ids"]) == 888
    assert len(data["disagreements"]) == 155
    assert Counter(row["class"] for row in data["disagreements"].values()) == Counter({
        "different-category": 66,
        "confirmed-vs-needs_entry": 26,
        "abstention-vs-decision": 7,
        "other": 56,
    })
    assert Counter(row["outcome"] for row in data["analysis"]["divine_name_rows"]["rows"]) == Counter({
        "certified-candidate": 5,
        "disagreement": 6,
    })

    with tempfile.TemporaryDirectory(prefix="test-funcword-cert-") as temp:
        bundle = cert.build_bundle(SOURCE_DIR, Path(temp) / "bundle")
        ledger_dir = Path(temp) / "ledger-readback"
        ledger_dir.mkdir()
        shutil.copyfile(bundle["ledger"], ledger_dir / fact_ledger.LEDGER_NAME)
        store = fact_ledger.FactLedgerStore(ledger_dir)
        assert store.validate_all() == []

        history = store.query(current_only=False)
        current = store.query(current_only=True)
        assert len(history) == 2_974
        assert Counter(row["certification_state"] for row in history) == Counter({
            "candidate": 1_043,
            "review_required": 1_043,
            "certified": 888,
        })
        assert Counter(row["certification_state"] for row in current) == Counter({
            "certified": 888,
            "review_required": 155,
        })
        assert all(row["fact_type"] == "function_word_analysis" for row in current)
        assert all(row["subject_type"] == "surface_occurrence" for row in current)
        assert all(row["certification_state"] != "materialized" for row in current)
        assert all(row["materialization_targets"] == [] for row in current)
        assert all(
            {vote["voter_id"] for vote in row["review_votes"]}
            == {"reviewer-A:Opus", "reviewer-B:Codex"}
            for row in current
        )

        t2_rows = [
            row for row in current
            if any(item.get("t2_normalized") is True for item in row["exceptions"])
        ]
        assert len(t2_rows) == 26
        assert all(row["certification_state"] == "certified" for row in t2_rows)
        assert all(
            row["candidate_or_value"]["value"]["taxonomy_category"]
            in {"conditional", "relative"}
            for row in t2_rows
        )
        assert all(
            {item["evidence_id"] for item in row["evidence"]}
            >= {"vote-A", "vote-B"}
            for row in t2_rows
        )

        divine_disagreements = {
            row["packet_id"]
            for row in data["analysis"]["divine_name_rows"]["rows"]
            if row["outcome"] == "disagreement"
        }
        current_by_packet = {
            row["evidence"][0]["source_address"].split("packet_id=", 1)[1]: row
            for row in current
        }
        assert all(
            current_by_packet[packet_id]["certification_state"] == "review_required"
            for packet_id in divine_disagreements
        )

        report = json.loads(bundle["report"].read_text(encoding="utf-8"))
        assert report["row_arithmetic"] == "888*3 + 155*2 = 2974"
        assert report["registry_delta"] == {
            "gate_trigger": "advanced_nahw",
            "id": "function_word_analysis",
            "schema_changed": True,
        }
        assert report["shadow_surface_assertion"]["observed"] == "byte_stable"

    print("certify_funcword_wave tests OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
